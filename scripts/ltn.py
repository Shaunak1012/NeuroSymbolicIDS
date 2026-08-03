import numpy as np
import pandas as pd
import pickle
import os
import tensorflow as tf
import tensorflow.keras.backend as K
from tensorflow.keras import layers, models, callbacks, Input
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import (
    classification_report, average_precision_score,
    roc_auc_score, precision_recall_curve, confusion_matrix
)
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns

# =========================
# PATHS (see scripts/paths.py)
# =========================
import paths
import behavior

tf.random.set_seed(42)
np.random.seed(42)

# =========================
# LOAD RAW FEATURES + LABELS
# (same as cnn3.py — we retrain from scratch with Hybrid Loss)
# =========================
print("Loading features...")
X_train_full = pd.read_csv(os.path.join(paths.PROCESSED, "features_train.csv")).values
X_test_raw   = pd.read_csv(os.path.join(paths.PROCESSED, "features_test.csv")).values

y_train_str = np.load(os.path.join(paths.PROCESSED, "labels_train_multiclass.npy"), allow_pickle=True)
y_test_str  = np.load(os.path.join(paths.PROCESSED, "labels_test_multiclass.npy"),  allow_pickle=True)

# =========================
# LABELS
# =========================
train_classes     = sorted(set(y_train_str))
zero_day_classes  = sorted(set(y_test_str) - set(y_train_str))
n_classes         = len(train_classes)

print(f"\nTrain classes ({n_classes}): {train_classes}")
print(f"Zero-day classes          : {zero_day_classes}")

le = LabelEncoder()
le.fit(train_classes)
y_train_enc = le.transform(y_train_str)

def encode_test(labels, le):
    encoded = np.full(len(labels), -1, dtype=int)
    known   = np.isin(labels, le.classes_)
    encoded[known] = le.transform(labels[known])
    return encoded

y_test_enc = encode_test(y_test_str, le)
benign_idx  = train_classes.index('BENIGN')

# Binary labels
y_train_bin = (y_train_str != 'BENIGN').astype(int)
y_test_bin  = (y_test_str  != 'BENIGN').astype(int)

# Attack-family masks for SAT axioms (used during training)
dos_classes     = [c for c in train_classes if 'DoS' in c or 'Heartbleed' in c]
patator_classes = [c for c in train_classes if 'Patator' in c]
print(f"DoS family     : {dos_classes}")
print(f"Patator family : {patator_classes}")

# =========================
# TRAIN / VAL SPLIT
# =========================
X_train, X_val, y_train, y_val = train_test_split(
    X_train_full, y_train_enc,
    test_size=0.2, random_state=42, stratify=y_train_enc
)
_, _, y_train_str_split, y_val_str_split = train_test_split(
    X_train_full, y_train_str,
    test_size=0.2, random_state=42, stratify=y_train_enc
)
_, _, y_train_b, y_val_b = train_test_split(
    X_train_full, y_train_bin,
    test_size=0.2, random_state=42, stratify=y_train_bin
)

# =========================
# BEHAVIOUR GROUNDING
# Compute fuzzy behaviour confidences on the RAW (unscaled) training split —
# these weight the behaviour-grounded SAT axioms (Ax3, Ax4). Must run BEFORE
# scaling, since behaviour thresholds are defined in raw feature space.
# =========================
_beh_thr   = behavior.load_thresholds()
_beh_train = behavior.abstract_behaviours(X_train, _beh_thr)   # X_train still raw here
# Ax3 weight: LargePackets AND HighEntropy (product fuzzy-AND) -> transfers to DDoS
b_ax3 = (_beh_train["LargePackets"] * _beh_train["HighEntropy"]).astype(np.float32)
# Ax4 weight: BurstTraffic -> transfers to DoS/flood
b_ax4 = _beh_train["BurstTraffic"].astype(np.float32)
print(f"\nBehaviour grounding (train split, n={len(b_ax3):,}):")
print(f"  Ax3 weight (LargePkt^HighEntropy)  mean={b_ax3.mean():.4f}")
print(f"  Ax4 weight (BurstTraffic)          mean={b_ax4.mean():.4f}")

# =========================
# SCALING
# =========================
scaler  = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_val   = scaler.transform(X_val)
X_test  = scaler.transform(X_test_raw)

with open(os.path.join(paths.MODELS, "scaler_ltn.pkl"), "wb") as f:
    pickle.dump(scaler, f)

# =========================
# CLASS WEIGHTS
# =========================
classes          = np.unique(y_train)
weights          = compute_class_weight(class_weight='balanced', classes=classes, y=y_train)
class_weight_dict = dict(zip(classes.astype(int), weights))

print("\nClass weights:")
for idx, w in class_weight_dict.items():
    print(f"  {le.classes_[idx]:<35} {w:.4f}")

# =========================
# RESHAPE for 1D CNN
# =========================
n_features = X_train.shape[1]
X_train_r  = X_train.reshape(X_train.shape[0], n_features, 1)
X_val_r    = X_val.reshape(X_val.shape[0],     n_features, 1)
X_test_r   = X_test.reshape(X_test.shape[0],   n_features, 1)

# =========================
# FUZZY LOGIC OPERATORS
# (Product fuzzy logic — as used in the base paper)
# =========================
def fuzzy_and(a, b):
    """Product t-norm: a * b"""
    return a * b

def fuzzy_not(a):
    """Standard negation: 1 - a"""
    return 1.0 - a

def fuzzy_forall(values, p=2):
    """
    ApME aggregator from the base paper (Eq. 3):
    forall quantifier — sensitive to errors (low truth values)
    p=2 as used in the paper
    """
    errors     = tf.pow(1.0 - values, p)
    mean_error = tf.reduce_mean(errors)
    return 1.0 - tf.pow(mean_error, 1.0 / p)

# =========================
# SAT LOSS  (behaviour-grounded — see docs/implementation/ltn_current.md)
#
# Ax1, Ax2 are supervised consistency anchors (label-based):
#   Ax1: ∀x_benign  P(x, benign)      — benign flows score high for benign
#   Ax2: ∀x_attack  ¬P(x, benign)     — attack flows score low for benign
#
# Ax3, Ax4 are BEHAVIOUR-grounded (input-derived, not label tautologies). Each
# flow's contribution is weighted by a fuzzy behaviour confidence b(x) ∈ [0,1]
# from behavior.py, so the rule constrains the model wherever the *behaviour*
# holds — which transfers to unseen (zero-day) attacks that share the behaviour:
#   Ax3: LargePackets(x) ∧ HighEntropy(x) → ¬benign(x)   (transfers to DDoS)
#   Ax4: BurstTraffic(x)                  → ¬benign(x)   (transfers to DoS/flood)
#
# Aggregation uses a soft (behaviour-weighted) mean of per-flow attack-score
# errors; n is the soft count Σ b(x).
# =========================

def compute_sat_loss(softmax_out, y_str_batch, b_ax3_batch, b_ax4_batch,
                     benign_idx, n_classes, p=2):
    # Clip to avoid log(0) and pow(0, 1/p) = nan
    softmax_out = tf.clip_by_value(softmax_out, 1e-7, 1.0 - 1e-7)

    p_benign_score = softmax_out[:, benign_idx]
    p_attack_score = 1.0 - p_benign_score

    is_benign = tf.constant((y_str_batch == 'BENIGN').astype(np.float32))
    is_attack = tf.constant((y_str_batch != 'BENIGN').astype(np.float32))

    # AXIOM 1 (anchor): benign flows score high for benign class
    n_benign  = tf.maximum(tf.reduce_sum(is_benign), 1.0)
    errors_ax1 = tf.pow(1.0 - p_benign_score, p) * is_benign
    ax1_sat   = 1.0 - tf.pow(
        tf.clip_by_value(tf.reduce_sum(errors_ax1) / n_benign, 0.0, 1.0), 1.0/p)

    # AXIOM 2 (anchor): attack flows score low for benign class
    n_attack  = tf.maximum(tf.reduce_sum(is_attack), 1.0)
    errors_ax2 = tf.pow(1.0 - p_attack_score, p) * is_attack
    ax2_sat   = 1.0 - tf.pow(
        tf.clip_by_value(tf.reduce_sum(errors_ax2) / n_attack, 0.0, 1.0), 1.0/p)

    # AXIOM 3 (behaviour): LargePackets ∧ HighEntropy -> not benign
    w3   = tf.constant(b_ax3_batch, dtype=tf.float32)
    n_w3 = tf.maximum(tf.reduce_sum(w3), 1.0)
    errors_ax3 = tf.pow(1.0 - p_attack_score, p) * w3
    ax3_sat   = 1.0 - tf.pow(
        tf.clip_by_value(tf.reduce_sum(errors_ax3) / n_w3, 0.0, 1.0), 1.0/p)

    # AXIOM 4 (behaviour): BurstTraffic -> not benign
    w4   = tf.constant(b_ax4_batch, dtype=tf.float32)
    n_w4 = tf.maximum(tf.reduce_sum(w4), 1.0)
    errors_ax4 = tf.pow(1.0 - p_attack_score, p) * w4
    ax4_sat   = 1.0 - tf.pow(
        tf.clip_by_value(tf.reduce_sum(errors_ax4) / n_w4, 0.0, 1.0), 1.0/p)

    sat_agg  = (2.0*ax1_sat + 2.0*ax2_sat + ax3_sat + ax4_sat) / 6.0
    sat_loss = tf.clip_by_value(1.0 - sat_agg, 0.0, 1.0)
    return sat_loss, ax1_sat, ax2_sat, ax3_sat, ax4_sat

# =========================
# FOCAL LOSS (our improvement over plain CE in the paper)
# =========================
def categorical_focal_loss(alpha_weights, gamma=2.0):
    alpha_t = tf.constant(alpha_weights, dtype=tf.float32)
    n_cls   = len(alpha_weights)

    def loss(y_true, y_pred):
        y_true_int = tf.cast(y_true, tf.int32)
        y_pred     = tf.clip_by_value(y_pred, 1e-7, 1.0 - 1e-7)
        pt         = tf.reduce_sum(y_pred * tf.one_hot(y_true_int, n_cls), axis=-1)
        pt         = tf.clip_by_value(pt, 1e-7, 1.0 - 1e-7)
        alpha_s    = tf.gather(alpha_t, y_true_int)
        focal_w    = tf.pow(1.0 - pt, gamma)
        focal_w    = tf.clip_by_value(focal_w, 0.0, 100.0)
        loss_val   = -alpha_s * focal_w * tf.math.log(pt)
        loss_val   = tf.where(tf.math.is_nan(loss_val),
                              tf.zeros_like(loss_val), loss_val)
        return tf.reduce_mean(loss_val)

    return loss

alpha_arr  = np.array([class_weight_dict.get(i, 1.0) for i in range(n_classes)])
alpha_arr  = alpha_arr / alpha_arr.mean()
alpha_list = alpha_arr.tolist()

# =========================
# CNN ARCHITECTURE
# Same as cnn3.py — we retrain it with Hybrid Loss
# =========================
def build_cnn(n_features, n_classes):
    inp = Input(shape=(n_features, 1), name="input")

    x = layers.Conv1D(32, 3, activation='relu', padding='same', name="conv1")(inp)
    x = layers.BatchNormalization(name="bn1")(x)
    x = layers.MaxPooling1D(2, name="pool1")(x)

    x = layers.Conv1D(64, 3, activation='relu', padding='same', name="conv2")(x)
    x = layers.BatchNormalization(name="bn2")(x)
    x = layers.MaxPooling1D(2, name="pool2")(x)

    x = layers.Conv1D(128, 3, activation='relu', padding='same', name="conv3")(x)
    x = layers.BatchNormalization(name="bn3")(x)
    x = layers.MaxPooling1D(2, name="pool3")(x)

    x = layers.Flatten(name="flatten")(x)

    x = layers.Dense(64, activation='relu',
                     kernel_regularizer=tf.keras.regularizers.l2(1e-4),
                     name="embedding")(x)
    x = layers.Dropout(0.4, name="drop1")(x)

    x = layers.Dense(32, activation='relu',
                     kernel_regularizer=tf.keras.regularizers.l2(1e-4),
                     name="dense2")(x)
    x = layers.Dropout(0.3, name="drop2")(x)

    out = layers.Dense(n_classes, activation='softmax', name="output")(x)
    return models.Model(inputs=inp, outputs=out, name="ltn_cnn")

cnn = build_cnn(n_features, n_classes)
cnn.summary()

optimizer = tf.keras.optimizers.Adam(learning_rate=3e-4, clipnorm=1.0)
focal_loss_fn = categorical_focal_loss(alpha_list, gamma=2.0)

# =========================
# HYBRID LOSS TRAINING LOOP
# Hybrid Loss = Focal CE Loss + omega * SAT Loss
# omega starts at 0.5 and adapts during training
# (base paper uses omega=1 with plain CE; we use adaptive omega with focal CE)
# =========================
# Env-var overrides for a quick smoke test, e.g.:
#   LTN_SUBSET=50000 LTN_EPOCHS=2 python scripts/ltn.py
EPOCHS     = int(os.environ.get("LTN_EPOCHS", "50"))
BATCH_SIZE = 256
OMEGA      = 0.1    # SAT loss weight (base paper uses 1.0; we start lower)
PATIENCE   = 8

_SUBSET = int(os.environ.get("LTN_SUBSET", "0"))
if _SUBSET > 0:
    _SUBSET = min(_SUBSET, X_train_r.shape[0])
    print(f"\n[SMOKE TEST] limiting training to first {_SUBSET:,} rows, {EPOCHS} epochs")
    X_train_r = X_train_r[:_SUBSET]
    y_train   = y_train[:_SUBSET]
    y_train_str_split = y_train_str_split[:_SUBSET]
    b_ax3 = b_ax3[:_SUBSET]
    b_ax4 = b_ax4[:_SUBSET]

best_val_acc  = 0.0
best_epoch    = 0
no_improve    = 0
omega         = OMEGA

history = {
    'loss': [], 'val_loss': [],
    'accuracy': [], 'val_accuracy': [],
    'ce_loss': [], 'sat_loss': [],
    'ax1_sat': [], 'ax2_sat': [], 'ax3_sat': [], 'ax4_sat': []
}

n_train   = X_train_r.shape[0]
n_batches = int(np.ceil(n_train / BATCH_SIZE))

print(f"\n{'='*60}")
print(f"HYBRID-LTN TRAINING")
print(f"  Epochs={EPOCHS}, Batch={BATCH_SIZE}, omega={OMEGA}")
print(f"  Focal Loss gamma=2.0 + SAT Loss (4 axioms)")
print(f"{'='*60}")

for epoch in range(1, EPOCHS + 1):

    # Shuffle training data (behaviour weights shuffled in lockstep)
    perm       = np.random.permutation(n_train)
    X_shuf     = X_train_r[perm]
    y_shuf     = y_train[perm]
    y_str_shuf = y_train_str_split[perm]
    b3_shuf    = b_ax3[perm]
    b4_shuf    = b_ax4[perm]

    epoch_ce, epoch_sat = [], []
    epoch_ax1, epoch_ax2, epoch_ax3, epoch_ax4 = [], [], [], []
    epoch_total = []

    for b in range(n_batches):
        start = b * BATCH_SIZE
        end   = min(start + BATCH_SIZE, n_train)

        X_batch     = tf.constant(X_shuf[start:end], dtype=tf.float32)
        y_batch     = tf.constant(y_shuf[start:end], dtype=tf.float32)
        y_str_batch = y_str_shuf[start:end]
        b3_batch    = b3_shuf[start:end]
        b4_batch    = b4_shuf[start:end]

        with tf.GradientTape() as tape:
            softmax_out = cnn(X_batch, training=True)
            softmax_out = tf.clip_by_value(softmax_out, 1e-7, 1.0 - 1e-7)
            ce_loss     = focal_loss_fn(y_batch, softmax_out)
            sat_loss, ax1, ax2, ax3, ax4 = compute_sat_loss(
                softmax_out, y_str_batch, b3_batch, b4_batch, benign_idx, n_classes
            )
            total_loss = ce_loss + omega * sat_loss

        # Skip batch entirely if any nan
        if (tf.math.is_nan(total_loss) or
            tf.math.is_nan(ce_loss) or
            tf.math.is_nan(sat_loss)):
            continue

        grads = tape.gradient(total_loss, cnn.trainable_variables)
        grads = [tf.where(tf.math.is_nan(g), tf.zeros_like(g), g)
                 if g is not None else g for g in grads]
        grads, _ = tf.clip_by_global_norm(grads, 1.0)
        optimizer.apply_gradients(zip(grads, cnn.trainable_variables))

        epoch_ce.append(float(ce_loss))
        epoch_sat.append(float(sat_loss))
        epoch_ax1.append(float(ax1))
        epoch_ax2.append(float(ax2))
        epoch_ax3.append(float(ax3))
        epoch_ax4.append(float(ax4))
        epoch_total.append(float(total_loss))

    # Validation accuracy
    val_probs    = cnn(tf.constant(X_val_r, dtype=tf.float32), training=False)
    val_preds    = tf.argmax(val_probs, axis=1).numpy()
    val_acc      = (val_preds == y_val).mean()

    val_ce_loss  = focal_loss_fn(
        tf.constant(y_val, dtype=tf.float32),
        val_probs
    ).numpy()

    mean_ce  = np.mean(epoch_ce)
    mean_sat = np.mean(epoch_sat)
    mean_tot = np.mean(epoch_total)

    history['loss'].append(mean_tot)
    history['val_loss'].append(float(val_ce_loss))
    history['accuracy'].append(float((np.argmax(
        cnn(tf.constant(X_train_r[:5000], dtype=tf.float32), training=False
        ).numpy(), axis=1) == y_train[:5000]).mean()))
    history['val_accuracy'].append(float(val_acc))
    history['ce_loss'].append(mean_ce)
    history['sat_loss'].append(mean_sat)
    history['ax1_sat'].append(np.mean(epoch_ax1))
    history['ax2_sat'].append(np.mean(epoch_ax2))
    history['ax3_sat'].append(np.mean(epoch_ax3))
    history['ax4_sat'].append(np.mean(epoch_ax4))

    # Checkpoint
    if val_acc > best_val_acc:
        best_val_acc = val_acc
        best_epoch   = epoch
        no_improve   = 0
        cnn.save(os.path.join(paths.MODELS, "ltn_model_best.keras"))
        marker = " ★ saved"
    else:
        no_improve += 1
        marker = ""

    # Adaptive omega — increase SAT weight if axiom satisfaction is low
    mean_ax_sat = np.mean([np.mean(epoch_ax1), np.mean(epoch_ax2),
                           np.mean(epoch_ax3), np.mean(epoch_ax4)])
    if mean_ax_sat < 0.7 and omega < 1.0:
        omega = min(omega + 0.05, 1.0)
    elif mean_ax_sat > 0.9 and omega > 0.3:
        omega = max(omega - 0.02, 0.3)

    if epoch % 5 == 0 or epoch == 1:
        print(f"  Epoch {epoch:3d}/{EPOCHS} | "
              f"Loss={mean_tot:.4f} (CE={mean_ce:.4f}, SAT={mean_sat:.4f}) | "
              f"Val Acc={val_acc:.4f} | "
              f"Ax=[{np.mean(epoch_ax1):.3f},{np.mean(epoch_ax2):.3f},"
              f"{np.mean(epoch_ax3):.3f},{np.mean(epoch_ax4):.3f}] | "
              f"ω={omega:.2f}{marker}")

    if no_improve >= PATIENCE:
        print(f"\n  Early stopping at epoch {epoch} "
              f"(no improvement for {PATIENCE} epochs)")
        break

print(f"\nBest Val Accuracy : {best_val_acc:.4f} at epoch {best_epoch}")

# Save final model too
cnn.save(os.path.join(paths.MODELS, "ltn_model_final.keras"))

# =========================
# RESTORE BEST MODEL
# =========================
cnn = tf.keras.models.load_model(
    os.path.join(paths.MODELS, "ltn_model_best.keras"),
    custom_objects={"loss": categorical_focal_loss(alpha_list, gamma=2.0)}
)

# =========================
# TEST EVALUATION
# (Base paper: discard LTN wrapper, evaluate CNN directly)
# =========================
print(f"\n{'='*60}")
print("EVALUATION — CNN trained with Hybrid-LTN Loss")
print(f"{'='*60}")

y_prob      = cnn.predict(X_test_r, batch_size=512, verbose=1)  # (N, n_classes)
y_pred_mc   = np.argmax(y_prob, axis=1)
y_prob_atk  = 1.0 - y_prob[:, benign_idx]                        # P(attack)
y_pred_bin  = (y_prob_atk > 0.5).astype(int)

# Load CNN baseline scores if available (for comparison)
cnn_baseline_path = os.path.join(paths.PREDICTIONS, "y_prob_test_bin.npy")
has_baseline      = os.path.exists(cnn_baseline_path)
if has_baseline:
    cnn_base_prob = np.load(cnn_baseline_path)
    cnn_base_prauc = average_precision_score(y_test_bin, cnn_base_prob)
    print(f"\nCNN baseline (cnn3.py) PR-AUC : {cnn_base_prauc:.4f}")
else:
    print("\nCNN baseline scores not found — run eval.py first for comparison")

# Binary metrics
ltn_prauc = average_precision_score(y_test_bin, y_prob_atk)
ltn_roc   = roc_auc_score(y_test_bin, y_prob_atk)

print(f"Hybrid-LTN CNN PR-AUC        : {ltn_prauc:.4f}")
print(f"Hybrid-LTN CNN ROC-AUC       : {ltn_roc:.4f}")

if has_baseline:
    delta = ltn_prauc - cnn_base_prauc
    print(f"Improvement over baseline     : {delta:+.4f} "
          f"({'✓ IMPROVED' if delta > 0 else '✗ no gain'})")

# Binary classification report
print(f"\n{'='*60}")
print("BINARY REPORT (Benign vs Any Attack including Zero-Day)")
print(f"{'='*60}")
print(classification_report(
    y_test_bin, y_pred_bin,
    target_names=["Benign", "Attack"], digits=4, zero_division=0
))

cm = confusion_matrix(y_test_bin, y_pred_bin)
tn, fp, fn, tp = cm.ravel()
print(f"  TN={tn:,}  FP={fp:,}  FN={fn:,}  TP={tp:,}")
print(f"  FPR : {fp/(fp+tn):.4f}")
print(f"  FNR : {fn/(fn+tp):.4f}  (missed attacks)")

# Known class report
print(f"\n{'='*60}")
print("MULTICLASS REPORT (known classes only)")
print(f"{'='*60}")
known_mask = y_test_enc != -1
if known_mask.sum() > 0:
    print(classification_report(
        y_test_enc[known_mask], y_pred_mc[known_mask],
        labels=list(range(n_classes)),
        target_names=train_classes, digits=4, zero_division=0
    ))

# Zero-day recall
print(f"\n{'='*60}")
print("ZERO-DAY FAMILY RECALL")
print(f"{'='*60}")
if has_baseline:
    print(f"  {'Family':<35} {'Baseline':>10} {'Hybrid-LTN':>12}")
    print(f"  {'-'*35} {'-'*10} {'-'*12}")
else:
    print(f"  {'Family':<35} {'Recall':>10}")
    print(f"  {'-'*35} {'-'*10}")

for attack in zero_day_classes:
    mask  = y_test_str == attack
    total = mask.sum()
    if total == 0:
        continue
    r_ltn = (y_pred_bin[mask] == 1).sum() / total
    if has_baseline:
        r_cnn = (cnn_base_prob[mask] > 0.5).sum() / total
        delta = r_ltn - r_cnn
        print(f"  {attack:<35} {r_cnn:>10.4f} {r_ltn:>12.4f}  "
              f"({delta:+.4f}) (n={total:,})")
    else:
        print(f"  {attack:<35} {r_ltn:>10.4f}  (n={total:,})")

# =========================
# SAVE OUTPUTS
# =========================
np.save(os.path.join(paths.ARRAYS, "X_test_ltn.npy"),     X_test_r)
np.save(os.path.join(paths.PREDICTIONS, "y_prob_ltn_test.npy"), y_prob)
np.save(os.path.join(paths.PREDICTIONS, "y_prob_ltn_bin.npy"),  y_prob_atk)

with open(os.path.join(paths.METADATA_LEGACY, "ltn_history.pkl"), "wb") as f:
    pickle.dump(history, f)

# Save label encoder and class info
with open(os.path.join(paths.MODELS, "label_encoder.pkl"), "wb") as f:
    pickle.dump(le, f)
# NOTE: METADATA_LEGACY, not METADATA — superseded temporal split (see paths.py).
np.save(os.path.join(paths.METADATA_LEGACY, "class_names.npy"),      np.array(train_classes))
np.save(os.path.join(paths.METADATA_LEGACY, "zero_day_classes.npy"), np.array(zero_day_classes))
np.save(os.path.join(paths.ARRAYS, "y_test_ltn_bin.npy"),   y_test_bin)
np.save(os.path.join(paths.ARRAYS, "y_test_ltn_mc.npy"),    y_test_enc)

# =========================
# EXTRACT EMBEDDINGS for KG Reasoning module
# =========================
embedding_model = models.Model(
    inputs=cnn.input,
    outputs=cnn.get_layer("embedding").output,
    name="ltn_embedding_extractor"
)

print("\nExtracting embeddings for KG Reasoning...")
X_train_emb = embedding_model.predict(X_train_r, batch_size=512, verbose=1)
X_val_emb   = embedding_model.predict(X_val_r,   batch_size=512, verbose=1)
X_test_emb  = embedding_model.predict(X_test_r,  batch_size=512, verbose=1)

np.save(os.path.join(paths.EMBEDDINGS, "X_train_ltn_emb.npy"), X_train_emb)
np.save(os.path.join(paths.EMBEDDINGS, "X_val_ltn_emb.npy"),   X_val_emb)
np.save(os.path.join(paths.EMBEDDINGS, "X_test_ltn_emb.npy"),  X_test_emb)

print(f"  Train emb : {X_train_emb.shape}")
print(f"  Val emb   : {X_val_emb.shape}")
print(f"  Test emb  : {X_test_emb.shape}")

# =========================
# PLOTS
# =========================
fig = plt.figure(figsize=(20, 14))
gs  = gridspec.GridSpec(3, 3, figure=fig)

# 1. Accuracy curves
ax1 = fig.add_subplot(gs[0, 0])
ax1.plot(history['accuracy'],     label='Train Acc', color='steelblue')
ax1.plot(history['val_accuracy'], label='Val Acc',   color='orange', linestyle='--')
ax1.set_title("Accuracy — Hybrid-LTN CNN")
ax1.set_xlabel("Epoch"); ax1.legend(); ax1.grid(alpha=0.3)

# 2. Loss curves
ax2 = fig.add_subplot(gs[0, 1])
ax2.plot(history['ce_loss'],  label='Focal CE Loss', color='steelblue')
ax2.plot(history['sat_loss'], label='SAT Loss',      color='tomato')
ax2.plot(history['loss'],     label='Total Loss',    color='green', linestyle='--')
ax2.set_title("Hybrid Loss Components")
ax2.set_xlabel("Epoch"); ax2.legend(); ax2.grid(alpha=0.3)

# 3. Axiom satisfaction over training
ax3 = fig.add_subplot(gs[0, 2])
ax3.plot(history['ax1_sat'], label='Ax1: Benign→Benign',    color='steelblue')
ax3.plot(history['ax2_sat'], label='Ax2: Attack→¬Benign',   color='tomato')
ax3.plot(history['ax3_sat'], label='Ax3: LargePkt∧HighEntropy→¬Benign', color='green')
ax3.plot(history['ax4_sat'], label='Ax4: BurstTraffic→¬Benign',         color='purple')
ax3.axhline(0.9, color='black', linestyle='--', alpha=0.4, label='0.9 target')
ax3.set_title("Axiom Satisfaction During Training")
ax3.set_xlabel("Epoch"); ax3.set_ylabel("Satisfaction [0,1]")
ax3.legend(fontsize=7); ax3.grid(alpha=0.3); ax3.set_ylim(0, 1)

# 4. PR Curve
ax4 = fig.add_subplot(gs[1, 0])
prec, rec, _ = precision_recall_curve(y_test_bin, y_prob_atk)
ax4.plot(rec, prec, color='green', label=f'Hybrid-LTN PR-AUC={ltn_prauc:.4f}')
if has_baseline:
    prec_b, rec_b, _ = precision_recall_curve(y_test_bin, cnn_base_prob)
    ax4.plot(rec_b, prec_b, color='steelblue',
             linestyle='--', label=f'CNN baseline PR-AUC={cnn_base_prauc:.4f}')
ax4.set_title("PR Curve — Binary Zero-Day Detection")
ax4.set_xlabel("Recall"); ax4.set_ylabel("Precision")
ax4.legend(); ax4.grid(alpha=0.3)

# 5. Confusion matrix
ax5 = fig.add_subplot(gs[1, 1])
sns.heatmap(cm, annot=True, fmt=',', cmap='Greens', ax=ax5,
            xticklabels=["Benign","Attack"], yticklabels=["Benign","Attack"])
ax5.set_title("Binary Confusion Matrix — Hybrid-LTN")
ax5.set_xlabel("Predicted"); ax5.set_ylabel("True")

# 6. Zero-day recall comparison
ax6 = fig.add_subplot(gs[1, 2])
zd_names, r_ltn_list, r_cnn_list = [], [], []
for attack in zero_day_classes:
    mask  = y_test_str == attack
    total = mask.sum()
    if total == 0:
        continue
    zd_names.append(f"{attack}\n(n={total:,})")
    r_ltn_list.append((y_pred_bin[mask] == 1).sum() / total)
    if has_baseline:
        r_cnn_list.append((cnn_base_prob[mask] > 0.5).sum() / total)

x     = np.arange(len(zd_names))
width = 0.35
if has_baseline:
    ax6.bar(x - width/2, r_cnn_list, width, label='CNN baseline',
            color='steelblue', alpha=0.8)
    ax6.bar(x + width/2, r_ltn_list, width, label='Hybrid-LTN',
            color='green', alpha=0.8)
    ax6.legend()
else:
    ax6.bar(x, r_ltn_list, color='green', alpha=0.8)
ax6.set_xticks(x); ax6.set_xticklabels(zd_names, fontsize=7)
ax6.axhline(0.5, color='black', linestyle='--', alpha=0.5)
ax6.set_title("Zero-Day Family Recall")
ax6.set_ylabel("Recall"); ax6.set_ylim(0, 1); ax6.grid(alpha=0.3)

# 7. Score distribution
ax7 = fig.add_subplot(gs[2, 0:2])
is_benign  = y_test_bin == 0
is_known   = (y_test_bin == 1) & np.isin(y_test_str, train_classes)
is_zeroday = (y_test_bin == 1) & ~np.isin(y_test_str, train_classes)
ax7.hist(y_prob_atk[is_benign],  bins=60, alpha=0.5, color='steelblue',
         label=f'Benign (n={is_benign.sum():,})',        density=True)
ax7.hist(y_prob_atk[is_known],   bins=60, alpha=0.5, color='orange',
         label=f'Known attack (n={is_known.sum():,})',   density=True)
ax7.hist(y_prob_atk[is_zeroday], bins=60, alpha=0.5, color='tomato',
         label=f'Zero-day (n={is_zeroday.sum():,})',     density=True)
ax7.axvline(0.5, color='black', linestyle='--')
ax7.set_title("P(Attack) Score Distribution by Category — Hybrid-LTN")
ax7.set_xlabel("P(Attack)"); ax7.set_ylabel("Density"); ax7.legend()

# 8. Summary text box
ax8 = fig.add_subplot(gs[2, 2])
ax8.axis('off')
summary = (
    f"HYBRID-LTN SUMMARY\n"
    f"{'─'*30}\n"
    f"PR-AUC  : {ltn_prauc:.4f}\n"
    f"ROC-AUC : {ltn_roc:.4f}\n"
    f"FPR     : {fp/(fp+tn):.4f}\n"
    f"FNR     : {fn/(fn+tp):.4f}\n"
)
if has_baseline:
    summary += (
        f"\nBaseline PR-AUC: {cnn_base_prauc:.4f}\n"
        f"Improvement    : {ltn_prauc - cnn_base_prauc:+.4f}\n"
    )
summary += (
    f"\nAxioms:\n"
    f"  Ax1 Benign→Benign        : {history['ax1_sat'][-1]:.4f}\n"
    f"  Ax2 Attack→¬Benign       : {history['ax2_sat'][-1]:.4f}\n"
    f"  Ax3 LgPkt∧HiEnt→¬Benign  : {history['ax3_sat'][-1]:.4f}\n"
    f"  Ax4 Burst→¬Benign        : {history['ax4_sat'][-1]:.4f}\n"
    f"\nBest epoch : {best_epoch}/{EPOCHS}\n"
    f"Best val acc: {best_val_acc:.4f}"
)
ax8.text(0.05, 0.95, summary, transform=ax8.transAxes,
         fontsize=9, verticalalignment='top', fontfamily='monospace',
         bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.3))

plt.suptitle(
    f"Hybrid-LTN Evaluation — CICIDS Zero-Day Detection\n"
    f"PR-AUC={ltn_prauc:.4f} | ROC-AUC={ltn_roc:.4f}",
    fontsize=13, fontweight='bold'
)
plt.tight_layout()
plt.savefig(os.path.join(paths.FIGURES, "ltn_eval.png"), dpi=150, bbox_inches='tight')
plt.show()
print("\nPlot saved: ltn_eval.png")

# =========================
# FINAL SUMMARY
# =========================
print(f"\n{'='*60}")
print("HYBRID-LTN FINAL SUMMARY")
print(f"{'='*60}")
if has_baseline:
    print(f"  CNN baseline PR-AUC : {cnn_base_prauc:.4f}")
print(f"  Hybrid-LTN PR-AUC   : {ltn_prauc:.4f}")
print(f"  Hybrid-LTN ROC-AUC  : {ltn_roc:.4f}")
print(f"  FNR (missed attacks): {fn/(fn+tp):.4f}")
print(f"\n  Final axiom satisfaction:")
print(f"    Ax1 (Benign→Benign)             : {history['ax1_sat'][-1]:.4f}")
print(f"    Ax2 (Attack→¬Benign)            : {history['ax2_sat'][-1]:.4f}")
print(f"    Ax3 (LargePkt∧HighEntropy→¬Ben) : {history['ax3_sat'][-1]:.4f}")
print(f"    Ax4 (BurstTraffic→¬Benign)      : {history['ax4_sat'][-1]:.4f}")
print(f"\n  Outputs for next stage (KG Reasoning):")
print(f"    ltn_model_best.keras     — best trained model")
print(f"    y_prob_ltn_bin.npy       — P(attack) scores")
print(f"    X_train_ltn_emb.npy      — embeddings for KG")
print(f"    X_test_ltn_emb.npy       — embeddings for KG")
print(f"{'='*60}")
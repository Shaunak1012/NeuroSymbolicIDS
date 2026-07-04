"""
cnn_paper.py — Phase 1 neural pillar. Trains the 1D CNN on the PAPER-aligned split
(data/processed/paper/), with the log1p transform, and evaluates via metrics.py
(zero-day-only binary as the headline). Produces loadable Keras-2 models + embeddings.

Smoke test:  CNN_SUBSET=50000 CNN_EPOCHS=2 python scripts/cnn_paper.py

Outputs:
  models/cnn_paper_best.keras  models/scaler_paper.pkl  models/label_encoder_paper.pkl
  outputs/embeddings/X_{train,val,test}_cnn_paper_emb.npy
  outputs/predictions/y_prob_cnn_paper_test.npy   (P(attack))
  outputs/metadata/cnn_paper_history.pkl
"""
import os
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
import pickle
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models, callbacks, Input
import tensorflow.keras.backend as K
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.utils.class_weight import compute_class_weight

import paths, config, features, metrics, tracking

cfg = config.get()
SEED = cfg["seed"]
tf.random.set_seed(SEED); np.random.seed(SEED)
PAPER = os.path.join(paths.PROCESSED, cfg["paths"]["paper_subdir"])
TFM = cfg["protocol"]["feature_transform"]

EPOCHS = int(os.environ.get("CNN_EPOCHS", "50"))
SUBSET = int(os.environ.get("CNN_SUBSET", "0"))

# ---- load paper split ----
def load(split):
    X = np.load(os.path.join(PAPER, f"X_{split}.npy"))
    y = np.load(os.path.join(PAPER, f"y_{split}_mc.npy"), allow_pickle=True)
    return X, y

X_tr, y_tr = load("train"); X_val, y_val = load("val"); X_te, y_te = load("test")
zero_day = set(np.load(os.path.join(PAPER, "zero_day_classes.npy"), allow_pickle=True).tolist())
print(f"train {X_tr.shape} | val {X_val.shape} | test {X_te.shape}")

if SUBSET > 0:
    print(f"[SMOKE] subset {SUBSET} rows, {EPOCHS} epochs")
    idx = np.random.RandomState(SEED).choice(len(X_tr), min(SUBSET, len(X_tr)), replace=False)
    X_tr, y_tr = X_tr[idx], y_tr[idx]

# ---- feature transform (log1p) + scale ----
X_tr = features.transform(X_tr, TFM); X_val = features.transform(X_val, TFM); X_te = features.transform(X_te, TFM)
assert np.isfinite(X_tr).all(), "non-finite after transform!"
scaler = StandardScaler().fit(X_tr)
X_tr, X_val, X_te = scaler.transform(X_tr), scaler.transform(X_val), scaler.transform(X_te)

# ---- labels: encode 9 known classes; zero-day (test only) -> -1 ----
le = LabelEncoder().fit(y_tr)          # train has only the 9 known classes
n_classes = len(le.classes_)
y_tr_e, y_val_e = le.transform(y_tr), le.transform(y_val)
benign_idx = list(le.classes_).index("BENIGN")

nfeat = X_tr.shape[1]
X_tr = X_tr.reshape(-1, nfeat, 1); X_val = X_val.reshape(-1, nfeat, 1); X_te = X_te.reshape(-1, nfeat, 1)

# ---- focal loss (categorical) ----
cw = compute_class_weight("balanced", classes=np.unique(y_tr_e), y=y_tr_e)
alpha = (np.array([dict(zip(np.unique(y_tr_e), cw)).get(i, 1.0) for i in range(n_classes)]))
alpha = (alpha / alpha.mean()).astype(np.float32)

def focal(alpha_w, gamma=2.0):
    a = tf.constant(alpha_w); nc = len(alpha_w)
    def loss(yt, yp):
        # Keras passes y_true as (batch, 1); flatten to (batch,) or one_hot broadcasts to garbage.
        yt = tf.reshape(tf.cast(yt, tf.int32), [-1])
        yp = tf.clip_by_value(yp, K.epsilon(), 1 - K.epsilon())
        pt = tf.reduce_sum(yp * tf.one_hot(yt, nc), axis=-1)
        return tf.reduce_mean(-tf.gather(a, yt) * tf.pow(1 - pt, gamma) * tf.math.log(pt))
    return loss

# ---- model (same architecture as the temporal CNN) ----
def build(nf, nc):
    inp = Input((nf, 1), name="input")
    x = inp
    for f, n in [(32, "1"), (64, "2"), (128, "3")]:
        x = layers.Conv1D(f, 3, padding="same", activation="relu", name=f"conv{n}")(x)
        x = layers.BatchNormalization(name=f"bn{n}")(x)
        x = layers.MaxPooling1D(2, name=f"pool{n}")(x)
    x = layers.Flatten(name="flatten")(x)
    x = layers.Dense(64, activation="relu", kernel_regularizer=tf.keras.regularizers.l2(1e-4), name="embedding")(x)
    x = layers.Dropout(0.4)(x)
    x = layers.Dense(32, activation="relu", kernel_regularizer=tf.keras.regularizers.l2(1e-4), name="dense2")(x)
    x = layers.Dropout(0.3)(x)
    out = layers.Dense(nc, activation="softmax", name="output")(x)
    return models.Model(inp, out, name="cnn_paper")

model = build(nfeat, n_classes)
model.compile(optimizer=tf.keras.optimizers.Adam(3e-4), loss=focal(alpha),
              metrics=["sparse_categorical_accuracy"])

best_path = os.path.join(paths.MODELS, "cnn_paper_best.keras")
cbs = [
    callbacks.EarlyStopping(monitor="val_sparse_categorical_accuracy", patience=8, restore_best_weights=True, mode="max"),
    callbacks.ReduceLROnPlateau(monitor="val_sparse_categorical_accuracy", factor=0.5, patience=3, min_lr=1e-6, mode="max"),
    callbacks.ModelCheckpoint(best_path, monitor="val_sparse_categorical_accuracy", save_best_only=True, mode="max"),
]
# NOTE: imbalance is handled by focal-loss alpha only. We deliberately do NOT also pass
# class_weight to fit() — double-weighting destabilised training (accuracy collapse in smoke).
hist = model.fit(X_tr, y_tr_e, validation_data=(X_val, y_val_e), epochs=EPOCHS, batch_size=256,
                 callbacks=cbs, verbose=2)

# ---- evaluate (headline = zero-day-only binary) ----
y_prob = model.predict(X_te, batch_size=1024, verbose=0)
p_attack = 1.0 - y_prob[:, benign_idx]
res = metrics.evaluate(y_te, p_attack, zero_day, fpr=0.01)
metrics.print_report(res)

# ---- save ----
model.save(os.path.join(paths.MODELS, "cnn_paper.keras"))
with open(os.path.join(paths.MODELS, "scaler_paper.pkl"), "wb") as f: pickle.dump(scaler, f)
with open(os.path.join(paths.MODELS, "label_encoder_paper.pkl"), "wb") as f: pickle.dump(le, f)
np.save(os.path.join(paths.PREDICTIONS, "y_prob_cnn_paper_test.npy"), p_attack)
with open(os.path.join(paths.METADATA, "cnn_paper_history.pkl"), "wb") as f: pickle.dump(hist.history, f)
emb = models.Model(model.input, model.get_layer("embedding").output)
for nm, arr in [("train", X_tr), ("val", X_val), ("test", X_te)]:
    np.save(os.path.join(paths.EMBEDDINGS, f"X_{nm}_cnn_paper_emb.npy"), emb.predict(arr, batch_size=1024, verbose=0))

if SUBSET == 0:
    tracking.log_run("cnn_paper", {"protocol": "paper", "transform": TFM, "seed": SEED, "epochs": EPOCHS},
                     metrics.flatten(res))
    print("\nlogged to runs.jsonl")
print("DONE (cnn_paper)")

import numpy as np
import pickle
import os
import tensorflow as tf
import tensorflow.keras.backend as K
from tensorflow.keras.models import load_model
from sklearn.metrics import (
    classification_report, confusion_matrix,
    roc_auc_score, average_precision_score,
    precision_recall_curve, roc_curve
)
from sklearn.utils.class_weight import compute_class_weight
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns

# =========================
# PATHS (see scripts/paths.py)
# =========================
import paths

# =========================
# FOCAL LOSS
# =========================
def categorical_focal_loss(alpha_weights, gamma=2.0):
    alpha_t = tf.constant(alpha_weights, dtype=tf.float32)
    n_cls   = len(alpha_weights)
    def loss(y_true, y_pred):
        y_true_int = tf.cast(y_true, tf.int32)
        y_pred     = tf.clip_by_value(y_pred, K.epsilon(), 1.0 - K.epsilon())
        pt         = tf.reduce_sum(y_pred * tf.one_hot(y_true_int, n_cls), axis=-1)
        alpha_s    = tf.gather(alpha_t, y_true_int)
        loss_val   = -alpha_s * tf.pow(1.0 - pt, gamma) * tf.math.log(pt)
        return tf.reduce_mean(loss_val)
    return loss

# =========================
# LOAD METADATA
# =========================
with open(os.path.join(paths.MODELS, "label_encoder.pkl"), "rb") as f:
    le = pickle.load(f)

class_names      = np.load(os.path.join(paths.METADATA, "class_names.npy"),      allow_pickle=True).tolist()
zero_day_classes = np.load(os.path.join(paths.METADATA, "zero_day_classes.npy"),  allow_pickle=True).tolist()
n_classes        = len(class_names)

print(f"Known train classes ({n_classes}): {class_names}")
print(f"Zero-day test classes: {zero_day_classes}")

# Reconstruct alpha_list
y_train   = np.load(os.path.join(paths.ARRAYS, "y_train.npy"))
classes   = np.unique(y_train)
weights   = compute_class_weight(class_weight='balanced', classes=classes, y=y_train)
cw        = dict(zip(classes.astype(int), weights))
alpha_arr = np.array([cw.get(i, 1.0) for i in range(n_classes)])
alpha_arr = alpha_arr / alpha_arr.mean()
alpha_list = alpha_arr.tolist()

# =========================
# LOAD MODEL + DATA
# =========================
model = load_model(
    os.path.join(paths.MODELS, "model_multiclass_best.keras"),
    custom_objects={"loss": categorical_focal_loss(alpha_list, gamma=2.0)}
)

X_test      = np.load(os.path.join(paths.ARRAYS, "X_test.npy"))
y_test_mc   = np.load(os.path.join(paths.ARRAYS, "y_test.npy"))      # multiclass (-1 = zero-day)
y_test_bin  = np.load(os.path.join(paths.ARRAYS, "y_test_bin.npy"))  # binary ground truth

# =========================
# PREDICT
# =========================
y_prob    = model.predict(X_test, batch_size=512, verbose=1)  # (N, n_classes)
y_pred_mc = np.argmax(y_prob, axis=1)

# Binary: P(attack) = 1 - P(BENIGN)
benign_idx    = class_names.index('BENIGN')
y_prob_attack = 1.0 - y_prob[:, benign_idx]
y_pred_bin    = (y_prob_attack > 0.5).astype(int)

# =========================
# REPORT 1 — BINARY ZERO-DAY DETECTION
# =========================
print("\n" + "="*60)
print("REPORT 1 — BINARY ZERO-DAY DETECTION (Benign vs Any Attack)")
print("="*60)
print(classification_report(
    y_test_bin, y_pred_bin,
    target_names=["Benign", "Attack"],
    digits=4, zero_division=0
))

cm_bin = confusion_matrix(y_test_bin, y_pred_bin)
tn, fp, fn, tp = cm_bin.ravel()
print(f"  TN={tn:,}  FP={fp:,}  FN={fn:,}  TP={tp:,}")
print(f"  False Positive Rate : {fp/(fp+tn):.4f}")
print(f"  False Negative Rate : {fn/(fn+tp):.4f}  (missed attacks)")

roc_auc = roc_auc_score(y_test_bin, y_prob_attack)
pr_auc  = average_precision_score(y_test_bin, y_prob_attack)
print(f"\n  ROC-AUC : {roc_auc:.4f}")
print(f"  PR-AUC  : {pr_auc:.4f}  *** RECORD THIS — LTN must beat it ***")

# =========================
# REPORT 2 — PER ZERO-DAY FAMILY
# =========================
print("\n" + "="*60)
print("REPORT 2 — PER ZERO-DAY ATTACK FAMILY RECALL")
print("(CNN predicts BENIGN or a known attack class for all of these)")
print("="*60)

y_test_str = np.load(os.path.join(paths.PROCESSED, "labels_test_multiclass.npy"), allow_pickle=True)

for attack in zero_day_classes:
    mask   = y_test_str == attack
    total  = mask.sum()
    if total == 0:
        continue
    detected_as_attack = (y_pred_bin[mask] == 1).sum()
    recall = detected_as_attack / total
    print(f"  {attack:<35} total={total:>6,}  "
          f"detected as attack={detected_as_attack:>6,}  "
          f"recall={recall:.4f}")

# =========================
# REPORT 3 — KNOWN CLASS PERFORMANCE (val-like check)
# =========================
print("\n" + "="*60)
print("REPORT 3 — KNOWN CLASS PERFORMANCE (test samples with known labels)")
print("="*60)
known_mask = y_test_mc != -1
if known_mask.sum() > 0:
    print(classification_report(
        y_test_mc[known_mask], y_pred_mc[known_mask],
        labels=list(range(n_classes)),
        target_names=class_names,
        digits=4, zero_division=0
    ))
else:
    print("  No known-class samples in test set (pure zero-day test).")

# =========================
# PLOTS
# =========================
with open(os.path.join(paths.METADATA, "history.pkl"), "rb") as f:
    hist = pickle.load(f)

fig = plt.figure(figsize=(18, 12))
gs  = gridspec.GridSpec(2, 3, figure=fig)

ax1 = fig.add_subplot(gs[0, 0])
ax1.plot(hist.get('accuracy',     []), label='Train Acc', color='steelblue')
ax1.plot(hist.get('val_accuracy', []), label='Val Acc',   color='orange', linestyle='--')
ax1.set_title("Accuracy over Epochs"); ax1.set_xlabel("Epoch"); ax1.legend(); ax1.grid(alpha=0.3)

ax2 = fig.add_subplot(gs[0, 1])
ax2.plot(hist.get('loss',     []), label='Train Loss', color='steelblue')
ax2.plot(hist.get('val_loss', []), label='Val Loss',   color='orange', linestyle='--')
ax2.set_title("Focal Loss over Epochs"); ax2.set_xlabel("Epoch"); ax2.legend(); ax2.grid(alpha=0.3)

ax3 = fig.add_subplot(gs[0, 2])
prec, rec, _ = precision_recall_curve(y_test_bin, y_prob_attack)
ax3.plot(rec, prec, color='darkorange', label=f'PR AUC={pr_auc:.4f}')
ax3.set_title("PR Curve — Binary Zero-Day Detection")
ax3.set_xlabel("Recall"); ax3.set_ylabel("Precision")
ax3.legend(); ax3.grid(alpha=0.3)

ax4 = fig.add_subplot(gs[1, 0])
sns.heatmap(cm_bin, annot=True, fmt=',', cmap='Blues', ax=ax4,
            xticklabels=["Benign","Attack"], yticklabels=["Benign","Attack"])
ax4.set_title("Binary Confusion Matrix"); ax4.set_xlabel("Predicted"); ax4.set_ylabel("True")

ax5 = fig.add_subplot(gs[1, 1])
zd_names, zd_recalls = [], []
for attack in zero_day_classes:
    mask  = y_test_str == attack
    total = mask.sum()
    if total == 0:
        continue
    recall = (y_pred_bin[mask] == 1).sum() / total
    zd_names.append(f"{attack}\n(n={total:,})")
    zd_recalls.append(recall)

colors = ['tomato' if r < 0.5 else 'steelblue' for r in zd_recalls]
ax5.barh(zd_names, zd_recalls, color=colors)
ax5.axvline(0.5, color='black', linestyle='--', alpha=0.5)
ax5.set_title("Zero-Day Family Binary Recall\n(red = CNN misses >50%)")
ax5.set_xlabel("Recall (detected as any attack)"); ax5.set_xlim(0, 1)

ax6 = fig.add_subplot(gs[1, 2])
is_benign    = y_test_bin == 0
is_known_atk = (y_test_bin == 1) & np.isin(y_test_str, class_names)
is_zeroday   = (y_test_bin == 1) & ~np.isin(y_test_str, class_names)

ax6.hist(y_prob_attack[is_benign],    bins=60, alpha=0.5, color='steelblue',
         label=f'Benign (n={is_benign.sum():,})',        density=True)
ax6.hist(y_prob_attack[is_known_atk], bins=60, alpha=0.5, color='orange',
         label=f'Known attack (n={is_known_atk.sum():,})', density=True)
ax6.hist(y_prob_attack[is_zeroday],   bins=60, alpha=0.5, color='tomato',
         label=f'Zero-day (n={is_zeroday.sum():,})',     density=True)
ax6.axvline(0.5, color='black', linestyle='--')
ax6.set_title("Score Distribution by Category")
ax6.set_xlabel("P(Attack)"); ax6.set_ylabel("Density"); ax6.legend()

plt.suptitle("CNN Zero-Day Evaluation — CICIDS\n"
             f"Binary PR-AUC={pr_auc:.4f} | LTN baseline to beat",
             fontsize=13, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(paths.FIGURES, "cnn_zeroday_eval.png"), dpi=150, bbox_inches='tight')
plt.show()
print("\nPlot saved to cnn_zeroday_eval.png")

# =========================
# SAVE for Decision Fusion
# =========================
np.save(os.path.join(paths.PREDICTIONS, "y_prob_test.npy"),     y_prob)
np.save(os.path.join(paths.PREDICTIONS, "y_prob_test_bin.npy"), y_prob_attack)
print("\nSaved y_prob_test.npy (softmax) and y_prob_test_bin.npy (P(attack)) for LTN fusion.")
print(f"\n{'='*60}")
print(f"CNN BASELINE SUMMARY")
print(f"{'='*60}")
print(f"  Binary PR-AUC  : {pr_auc:.4f}  (LTN must beat this)")
print(f"  Binary ROC-AUC : {roc_auc:.4f}")
print(f"  FNR on zero-day attacks: {fn/(fn+tp):.4f}  ({fn:,} missed)")
print(f"{'='*60}")
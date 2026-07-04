"""
novelty.py — Phase 1 free open-set / novelty scores from the trained paper CNN.

Zero-day detection is really "is this NONE of my known classes?" — so we add two
post-hoc, no-retraining OOD channels that reuse the CNN we already trust:

  * MSP        — 1 - max softmax probability (Hendrycks & Gimpel 2017 baseline)
  * Mahalanobis— min distance to per-class Gaussians in the 64-dim embedding space
                 (shared covariance), a strong OOD signal

Both evaluated via metrics.py (zero-day-only headline), saved as fusion channels.

Run (after cnn_paper.py):  python scripts/novelty.py
"""
import os
import pickle
import numpy as np
from tensorflow.keras.models import load_model

import paths, config, features, metrics, tracking

cfg = config.get()
PAPER = os.path.join(paths.PROCESSED, cfg["paths"]["paper_subdir"])
yte_mc = np.load(os.path.join(PAPER, "y_test_mc.npy"), allow_pickle=True)
ytr_mc = np.load(os.path.join(PAPER, "y_train_mc.npy"), allow_pickle=True)
zero_day = set(np.load(os.path.join(PAPER, "zero_day_classes.npy"), allow_pickle=True).tolist())

# ---- MSP: reload CNN, max softmax on test ----
print("Loading CNN + computing MSP...")
model = load_model(os.path.join(paths.MODELS, "cnn_paper_best.keras"), compile=False)
# re-derive the scaled (N,68,1) input from raw features + saved scaler + transform
scaler = pickle.load(open(os.path.join(paths.MODELS, "scaler_paper.pkl"), "rb"))
TFM = cfg["protocol"]["feature_transform"]
Xte_raw = np.load(os.path.join(PAPER, "X_test.npy"))
Xte_in = scaler.transform(features.transform(Xte_raw, TFM)).reshape(-1, Xte_raw.shape[1], 1)
prob = model.predict(Xte_in, batch_size=1024, verbose=0)
msp = 1.0 - prob.max(axis=1)          # high = novel

# ---- Mahalanobis in embedding space ----
print("Computing Mahalanobis (per-class Gaussians on embeddings)...")
E_tr = np.load(os.path.join(paths.EMBEDDINGS, "X_train_cnn_paper_emb.npy"))
E_te = np.load(os.path.join(paths.EMBEDDINGS, "X_test_cnn_paper_emb.npy"))
classes = np.unique(ytr_mc)
means = np.stack([E_tr[ytr_mc == c].mean(0) for c in classes])
# shared covariance (tied), regularised
cov = np.cov((E_tr - means[np.searchsorted(classes, ytr_mc)]).T) + 1e-6 * np.eye(E_tr.shape[1])
inv = np.linalg.inv(cov)
d = E_te[:, None, :] - means[None, :, :]                     # (N, C, d)
maha = np.einsum("ncd,de,nce->nc", d, inv, d).min(1)          # min distance to any class
maha = np.sqrt(np.clip(maha, 0, None))                        # high = novel

# ---- evaluate + save ----
for name, score in [("msp", msp), ("mahalanobis", maha)]:
    r = metrics.evaluate(yte_mc, score, zero_day, fpr=0.01)
    z = r["views"]["zeroday_only"]
    print(f"\n=== {name} ===  zeroday PR-AUC={z['pr_auc']:.4f}  ROC={z['roc_auc']:.4f}")
    tracking.log_run(name, {"protocol": "paper", "seed": cfg["seed"]}, metrics.flatten(r))
    np.save(os.path.join(paths.PREDICTIONS, f"y_prob_{name}_test.npy"), score.astype(np.float32))
print("\nDONE (novelty) — MSP + Mahalanobis saved as fusion channels")

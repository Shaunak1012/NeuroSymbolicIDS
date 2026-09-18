"""
novelty.py — Phase 1 free open-set / novelty scores from the trained paper CNN.

Zero-day detection is really "is this NONE of my known classes?" — so we add two
post-hoc, no-retraining OOD channels that reuse the CNN we already trust:

  * MSP        — 1 - max softmax probability (Hendrycks & Gimpel 2017 baseline)
  * Mahalanobis— min distance to per-class Gaussians in the 64-dim embedding space
                 (shared covariance), a strong OOD signal

Both evaluated via metrics.py (zero-day-only headline), saved as fusion channels.

Run (after cnn_paper.py):  python scripts/novelty.py

Multi-seed (added 2026-08-02): both channels are post-hoc functions of a trained
CNN, so they inherit that CNN's seed. Point them at a different seed's artifacts
with NOVELTY_SEED; outputs get an _s<seed> suffix and the seed-42 originals are
never touched.

    NOVELTY_SEED=43 python scripts/novelty.py
    NOVELTY_SEED=44 python scripts/novelty.py

WHY THIS MATTERS (docs/STATUS.md, 2026-08-02): the CNN-vs-autoencoder double
dissociation is established but unexplained. MSP and Mahalanobis are the
informative middle cases -- both are computed from an (A)-TRAINED model but use
(B)-STYLE scoring (softmax uncertainty / embedding distance rather than class
likelihood). If they pattern with the CNN, the dissociation is driven by what the
model was TRAINED on; if they pattern with the autoencoder, it is driven by how
the score is COMPUTED. Mahalanobis in particular shares the CNN's exact
representation, so if it beats the CNN on Bot then the Bot signal IS present in
the CNN's embedding and the failure is one of decision rule, not representation.
"""
import os
import pickle
import numpy as np
from tensorflow.keras.models import load_model

import paths, config, features, metrics, tracking

cfg = config.get()
_DEFAULT_SEED = cfg["seed"]
SEED = int(os.environ.get("NOVELTY_SEED", _DEFAULT_SEED))
SFX = "" if SEED == _DEFAULT_SEED else f"_s{SEED}"   # artifact suffix, matches cnn_paper.py
# NOVELTY_CNN (added 2026-09-18, itinerary 4.4) scores a named CNN run instead of
# cnn_paper[_s<seed>] -- e.g. NOVELTY_CNN=c4_log1p_s42 for the deterministic
# population. Outputs are tagged msp_<run> / mahalanobis_<run>; the default is
# unchanged. The pre-flag and deterministic populations are never pooled.
CNN_RUN = os.environ.get("NOVELTY_CNN", "")
CNN_TAG = CNN_RUN or f"cnn_paper{SFX}"
SCALER_SFX = f"_{CNN_RUN}" if CNN_RUN else SFX
OUT_SFX = f"_{CNN_RUN}" if CNN_RUN else SFX
print(f"CONFIG: seed={SEED} cnn={CNN_TAG} output_suffix='{OUT_SFX}'")
PAPER = os.path.join(paths.PROCESSED, cfg["paths"]["paper_subdir"])
yte_mc = np.load(os.path.join(PAPER, "y_test_mc.npy"), allow_pickle=True)
ytr_mc = np.load(os.path.join(PAPER, "y_train_mc.npy"), allow_pickle=True)
zero_day = set(np.load(os.path.join(PAPER, "zero_day_classes.npy"), allow_pickle=True).tolist())

# ---- MSP: reload CNN, max softmax on test ----
print("Loading CNN + computing MSP...")
model = load_model(os.path.join(paths.MODELS, f"{CNN_TAG}_best.keras"), compile=False)
# re-derive the scaled (N,68,1) input from raw features + saved scaler + transform
scaler = pickle.load(open(os.path.join(paths.MODELS, f"scaler_paper{SCALER_SFX}.pkl"), "rb"))
TFM = cfg["protocol"]["feature_transform"]
Xte_raw = np.load(os.path.join(PAPER, "X_test.npy"))
Xte_in = scaler.transform(features.transform(Xte_raw, TFM)).reshape(-1, Xte_raw.shape[1], 1)
prob = model.predict(Xte_in, batch_size=1024, verbose=0)
msp = 1.0 - prob.max(axis=1)          # high = novel

# ---- Mahalanobis in embedding space ----
print("Computing Mahalanobis (per-class Gaussians on embeddings)...")
E_tr = np.load(os.path.join(paths.EMBEDDINGS, f"X_train_{CNN_TAG}_emb.npy"))
E_te = np.load(os.path.join(paths.EMBEDDINGS, f"X_test_{CNN_TAG}_emb.npy"))
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
    tag = f"{name}{OUT_SFX}"
    r = metrics.evaluate(yte_mc, score, zero_day, fpr=0.01)
    z = r["views"]["zeroday_only"]
    print(f"\n=== {tag} ===  zeroday PR-AUC={z['pr_auc']:.4f}  ROC={z['roc_auc']:.4f}")
    metrics.print_report(r)
    tracking.log_run(tag, {"protocol": "paper", "seed": SEED, "cnn": CNN_TAG}, metrics.flatten(r))
    np.save(os.path.join(paths.PREDICTIONS, f"y_prob_{tag}_test.npy"), score.astype(np.float32))
print("\nDONE (novelty) — MSP + Mahalanobis saved as fusion channels")

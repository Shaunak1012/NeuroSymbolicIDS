"""
autoencoder_paper.py — canonical Phase 3, the anomaly pillar. Benign-only
reconstruction-error autoencoder on the paper split.

Why this exists (see docs/STATUS.md "THESIS REFRAMING", 2026-07-29)
---------------------------------------------------------------
Every Phase-2 symbolic intervention (LTN axioms, aux head, fitted fusion) shares
one structural cause of failure: each is fitted on data that by construction
contains no zero-day flows, so none can transfer to a class it was never shown.
That is the (A) "learn what attacks look like" family. The (B) "learn what
NORMAL looks like, flag deviation" family needs no attack labels at all and
reaches novel classes by construction — and the existing (B) evidence already
favours it on the family that matters: Mahalanobis scores 4.3x lift on Bot,
and IsolationForest (macro 0.0628 overall, dreadful) still TIES the CNN on Bot
(0.0571 vs 0.0591) despite never seeing a single labelled attack.

This autoencoder is the third (B)-family channel and the direct falsification
test of that reframing: if a benign-only AE ALSO lands at chance on Bot, the
(A)/(B) account is wrong and the STATUS reframing must be retracted in place.
It was also nearly skipped entirely by a phase-number collision (STATUS called
the Knowledge Graph "Phase 3"; canonical Phase 3 is this script, Phase 4 is the
KG) and is ranked Tier-1 "highest leverage" in target/enhancements.md because it
answers the standing reviewer objection "why not just an autoencoder?".

Design
------
A feedforward (Dense) autoencoder, not Conv1D — the CNN's convolutional
architecture treats feature *order* as a spatial signal to learn discriminative
filters; reconstruction has no such need, and a dense encoder/decoder is the
standard, simpler choice for tabular flow features. Trained ONLY on the log1p +
scaled BENIGN rows of the train split (no attack labels used anywhere, model
selection included). Scored by per-row reconstruction MSE at test time
(high = anomalous = attack-like). Evaluated exactly like every other channel via
metrics.py (zero-day-only binary as the headline), logged to runs.jsonl.

Smoke test:  AE_SUBSET=50000 AE_EPOCHS=3 python scripts/autoencoder_paper.py

Outputs:
  models/autoencoder_paper.keras   models/scaler_ae_paper.pkl
  outputs/predictions/y_prob_autoencoder_test.npy   (reconstruction MSE, high=novel)
  outputs/metadata/autoencoder_paper_history.pkl
"""
import os
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
import pickle
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models, callbacks, Input
from sklearn.preprocessing import StandardScaler

import paths, config, features, metrics, tracking
import determinism

cfg = config.get()
_DEFAULT_SEED = cfg["seed"]
SEED = int(os.environ.get("AE_SEED", _DEFAULT_SEED))
# Phase 7.5 Tier 2 #5 — seeding alone does not pin the result (SD 0.0222 measured
# on the CNN). Must run before any op is created. TF_DETERMINISM=0 opts out.
DET = determinism.enable(SEED, intra=int(os.environ.get("TF_THREADS", "16")),
                         inter=int(os.environ.get("TF_THREADS_INTER", "2")))
PAPER = os.path.join(paths.PROCESSED, cfg["paths"]["paper_subdir"])
TFM = cfg["protocol"]["feature_transform"]

EPOCHS = int(os.environ.get("AE_EPOCHS", "50"))
SUBSET = int(os.environ.get("AE_SUBSET", "0"))
TAG = os.environ.get("AE_TAG", "autoencoder_paper" if SEED == _DEFAULT_SEED else f"autoencoder_paper_s{SEED}")
print(f"CONFIG: seed={SEED} tag={TAG}")


def load(split):
    X = np.load(os.path.join(PAPER, f"X_{split}.npy"))
    yb = np.load(os.path.join(PAPER, f"y_{split}_bin.npy"))
    ymc = np.load(os.path.join(PAPER, f"y_{split}_mc.npy"), allow_pickle=True)
    return X, yb, ymc


Xtr, ytr, _ = load("train")
Xval, yval, _ = load("val")
Xte, _, yte_mc = load("test")
zero_day = set(np.load(os.path.join(PAPER, "zero_day_classes.npy"), allow_pickle=True).tolist())
print(f"train {Xtr.shape} | val {Xval.shape} | test {Xte.shape}")

if SUBSET > 0:
    print(f"[SMOKE] subset {SUBSET} rows, {EPOCHS} epochs")
    idx = np.random.RandomState(SEED).choice(len(Xtr), min(SUBSET, len(Xtr)), replace=False)
    Xtr, ytr = Xtr[idx], ytr[idx]

# ---- transform + scale (fit on ALL of train, matching baselines.py's convention
#      exactly, so this channel is directly comparable to IsolationForest) ----
Xtr = features.transform(Xtr, TFM); Xval = features.transform(Xval, TFM); Xte = features.transform(Xte, TFM)
scaler = StandardScaler().fit(Xtr)
Xtr, Xval, Xte = scaler.transform(Xtr), scaler.transform(Xval), scaler.transform(Xte)

# ---- BENIGN-ONLY subsets for both training and model selection. No attack
#      label is used anywhere past this point -- this is what makes it a
#      genuine (B)-family / zero-day-legitimate channel. ----
Xtr_benign = Xtr[ytr == 0]
Xval_benign = Xval[yval == 0]
print(f"benign-only: train {Xtr_benign.shape}  val {Xval_benign.shape}")

nfeat = Xtr.shape[1]

# ---- model: symmetric dense encoder/decoder, bottleneck << input width so the
#      network must actually compress rather than memorise. ----
def build(nf):
    inp = Input((nf,), name="input")
    x = layers.Dense(48, activation="relu", name="enc1")(inp)
    x = layers.Dense(32, activation="relu", name="enc2")(x)
    x = layers.Dense(16, activation="relu", name="bottleneck")(x)
    x = layers.Dense(32, activation="relu", name="dec1")(x)
    x = layers.Dense(48, activation="relu", name="dec2")(x)
    out = layers.Dense(nf, activation="linear", name="reconstruction")(x)
    return models.Model(inp, out, name="autoencoder_paper")


model = build(nfeat)
model.compile(optimizer=tf.keras.optimizers.Adam(1e-3), loss="mse")

best_path = os.path.join(paths.MODELS, f"{TAG}.keras")
cbs = [
    callbacks.EarlyStopping(monitor="val_loss", patience=8, restore_best_weights=True, mode="min"),
    callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=3, min_lr=1e-6, mode="min"),
    callbacks.ModelCheckpoint(best_path, monitor="val_loss", save_best_only=True, mode="min"),
]
hist = model.fit(Xtr_benign, Xtr_benign, validation_data=(Xval_benign, Xval_benign),
                 epochs=EPOCHS, batch_size=256, callbacks=cbs, verbose=2)

# ---- score: per-row reconstruction MSE on test (high = anomalous) ----
recon = model.predict(Xte, batch_size=1024, verbose=0)
score = np.mean((Xte - recon) ** 2, axis=1).astype(np.float32)

res = metrics.evaluate(yte_mc, score, zero_day, fpr=0.01)
metrics.print_report(res)

# ---- save ----
model.save(os.path.join(paths.MODELS, f"{TAG}.keras"))
with open(os.path.join(paths.MODELS, f"scaler_ae_paper{'' if TAG=='autoencoder_paper' else '_'+TAG.split('autoencoder_paper_',1)[-1]}.pkl"), "wb") as f:
    pickle.dump(scaler, f)
np.save(os.path.join(paths.predictions_dir(TAG), f"y_prob_{TAG}_test.npy"), score)
with open(os.path.join(paths.METADATA, f"{TAG}_history.pkl"), "wb") as f:
    pickle.dump(hist.history, f)

if SUBSET == 0:
    tracking.log_run(TAG, {"protocol": "paper", "transform": TFM, "seed": SEED,
                           "epochs": EPOCHS, "benign_only": True}, metrics.flatten(res))
    print(f"\nlogged {TAG} to runs.jsonl")
print(f"DONE ({TAG})")

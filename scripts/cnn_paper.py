"""
cnn_paper.py — Phase 1 neural pillar. Trains the 1D CNN on the PAPER-aligned split
(data/processed/paper/), with the log1p transform, and evaluates via metrics.py
(zero-day-only binary as the headline). Produces loadable Keras-2 models + embeddings.

Smoke test:  CNN_SUBSET=50000 CNN_EPOCHS=2 python scripts/cnn_paper.py

Multi-seed (added 2026-07-30, for STATUS "earlier-phase audit" C2 — the reference
baseline was n=1 while the LTN control it's compared against was n=3):
  CNN_SEED=43 python scripts/cnn_paper.py    # writes cnn_paper_s43.* — does NOT
  CNN_SEED=44 python scripts/cnn_paper.py    # touch the original seed-42 artifacts

Outputs (TAG defaults to "cnn_paper" at the config seed, "cnn_paper_s<seed>" otherwise):
  models/<TAG>_best.keras  models/scaler_paper<_suffix>.pkl  models/label_encoder_paper<_suffix>.pkl
  outputs/embeddings/X_{train,val,test}_<TAG>_emb.npy
  outputs/predictions/y_prob_<TAG>_test.npy   (P(attack))
  outputs/metadata/<TAG>_history.pkl
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
import determinism

cfg = config.get()
_DEFAULT_SEED = cfg["seed"]
SEED = int(os.environ.get("CNN_SEED", _DEFAULT_SEED))
# Phase 7.5 Tier 2 #5. Seeding alone does NOT pin the result: 6 runs of seed 42
# on an idle machine gave SD 0.0222 / CV 3.6%, because CPU thread scheduling
# changes float accumulation order. This must run before any op is created.
# TF_DETERMINISM=0 opts out for a throwaway exploratory run.
DET = determinism.enable(SEED, intra=int(os.environ.get("TF_THREADS", "16")),
                         inter=int(os.environ.get("TF_THREADS_INTER", "2")))
PAPER = os.path.join(paths.PROCESSED, cfg["paths"]["paper_subdir"])
# C4 (KNOWN_ISSUES): feature_transform was selected on the OVERALL BINARY metric
# ("0.980 vs 0.965"), i.e. the one inflated by train/test duplicate overlap and the
# one metrics.py forbids as an optimisation target. It has never been A/B'd on macro
# zero-day PR-AUC, the actual headline. FEATURE_TRANSFORM overrides the config default
# so the A/B runs WITHOUT mutating config.yaml mid-experiment -- editing the config
# would silently switch every other script's arm too, and there is no record in
# runs.jsonl of which arm a given historical run used beyond this `transform` param.
_TFM_DEFAULT = cfg["protocol"]["feature_transform"]
TFM = os.environ.get("FEATURE_TRANSFORM", _TFM_DEFAULT)

EPOCHS = int(os.environ.get("CNN_EPOCHS", "50"))
SUBSET = int(os.environ.get("CNN_SUBSET", "0"))

# TAG default preserves the original "cnn_paper" filenames exactly when SEED is the
# config default (42) -- so the existing reference model/embeddings are never at risk
# of being overwritten by a differently-seeded run. Other seeds get an _s<seed> suffix,
# matching the ltn_paper.py convention (ltn_ctrl_w0_s43, etc.).
# The transform suffix exists for the same reason the seed suffix does: a non-default
# arm must NEVER be able to overwrite the reference cnn_paper artifacts. Without it,
# FEATURE_TRANSFORM=raw at the default seed would silently clobber cnn_paper.keras,
# its embeddings and its fusion channel -- the reference every other script reads.
_TFM_SFX = "" if TFM == _TFM_DEFAULT else f"_{TFM}"
_DEFAULT_TAG = f"cnn_paper{_TFM_SFX}" if SEED == _DEFAULT_SEED else f"cnn_paper{_TFM_SFX}_s{SEED}"
TAG = os.environ.get("CNN_TAG", _DEFAULT_TAG)
print(f"CONFIG: seed={SEED} transform={TFM} tag={TAG}")

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

best_path = os.path.join(paths.MODELS, f"{TAG}_best.keras")
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

# ---- save (all paths keyed by TAG so a differently-seeded run never overwrites
#             the seed-42 reference model/embeddings/scaler/encoder) ----
model.save(os.path.join(paths.MODELS, f"{TAG}.keras"))
scaler_suffix = "" if TAG == "cnn_paper" else f"_{TAG.split('cnn_paper_', 1)[-1]}"
with open(os.path.join(paths.MODELS, f"scaler_paper{scaler_suffix}.pkl"), "wb") as f: pickle.dump(scaler, f)
with open(os.path.join(paths.MODELS, f"label_encoder_paper{scaler_suffix}.pkl"), "wb") as f: pickle.dump(le, f)
# predictions_dir() quarantines smoke runs into _smoke_archive/ so an undertrained
# array can never be picked up as a real fusion channel (see paths.py).
np.save(os.path.join(paths.predictions_dir(TAG), f"y_prob_{TAG}_test.npy"), p_attack)
with open(os.path.join(paths.METADATA, f"{TAG}_history.pkl"), "wb") as f: pickle.dump(hist.history, f)
emb = models.Model(model.input, model.get_layer("embedding").output)
for nm, arr in [("train", X_tr), ("val", X_val), ("test", X_te)]:
    np.save(os.path.join(paths.EMBEDDINGS, f"X_{nm}_{TAG}_emb.npy"), emb.predict(arr, batch_size=1024, verbose=0))

if SUBSET == 0:
    # Determinism state travels with the numbers: runs recorded before this flag
    # existed are a DIFFERENT population (pinning threads changes the reduction
    # order), so they must not be pooled with deterministic ones.
    tracking.log_run(TAG, {"protocol": "paper", "transform": TFM, "seed": SEED,
                           "epochs": EPOCHS, **{f"det_{k}": v for k, v in DET.items()}},
                     metrics.flatten(res))
    print(f"\nlogged {TAG} to runs.jsonl")
print(f"DONE ({TAG})")

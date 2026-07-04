"""
ltn_paper.py — Phase 2 symbolic pillar on the paper split. ONE configurable trainer
that serves (a) faithful base-paper reproduction, (b) our LTN v2, and (c) the
failure-anatomy grid.

Hybrid loss = CE + omega_eff * SAT, trained with a custom loop (SAT needs per-batch
behaviour weights + labels, which model.fit can't provide).

Config via env vars:
  LTN_LOSS       focal | ce            (default focal)
  LTN_AXIOMS     base | behaviour | both  (default both)
                   base      = Ax1 (benign->benign) + Ax2 (attack->not-benign)   [label anchors]
                   behaviour = Ax3 (LargePkt^HighEntropy->not-benign) + Ax4 (Burst->not-benign)
                               + Ax5 (ScanProbe->not-benign)  [now valid: PortScan is a KNOWN class]
  LTN_OMEGA      float                 (default 0.1)
  LTN_OMEGA_MODE fixed | ratio         (default ratio)
                   ratio = loss-ratio normalization: scale SAT so omega_eff*SAT ~= OMEGA * CE
                           (THE FIX for SAT domination that broke the temporal LTN)
  LTN_EPOCHS     int (default 40)   LTN_SUBSET int (default 0)   LTN_TAG str (run name)

Eval via metrics.py (zero-day-only binary headline). Logged to runs.jsonl.
"""
import os
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models, Input
import tensorflow.keras.backend as K
from sklearn.preprocessing import StandardScaler, LabelEncoder

import paths, config, features, behavior, metrics, tracking

cfg = config.get(); SEED = cfg["seed"]
tf.random.set_seed(SEED); np.random.seed(SEED)
PAPER = os.path.join(paths.PROCESSED, cfg["paths"]["paper_subdir"])
TFM = cfg["protocol"]["feature_transform"]

LOSS = os.environ.get("LTN_LOSS", "focal")
AXIOMS = os.environ.get("LTN_AXIOMS", "both")
OMEGA = float(os.environ.get("LTN_OMEGA", "0.1"))
OMEGA_MODE = os.environ.get("LTN_OMEGA_MODE", "ratio")
EPOCHS = int(os.environ.get("LTN_EPOCHS", "40"))
SUBSET = int(os.environ.get("LTN_SUBSET", "0"))
TAG = os.environ.get("LTN_TAG", f"ltn_{LOSS}_{AXIOMS}_w{OMEGA}_{OMEGA_MODE}")
print(f"CONFIG: loss={LOSS} axioms={AXIOMS} omega={OMEGA} mode={OMEGA_MODE} tag={TAG}")

# ---- load paper split ----
def load(s): return (np.load(os.path.join(PAPER, f"X_{s}.npy")),
                      np.load(os.path.join(PAPER, f"y_{s}_mc.npy"), allow_pickle=True))
Xtr_raw, ytr = load("train"); Xval_raw, yval = load("val"); Xte_raw, yte = load("test")
zero_day = set(np.load(os.path.join(PAPER, "zero_day_classes.npy"), allow_pickle=True).tolist())

# ---- behaviour weights (fresh thresholds on paper train; RAW features) ----
thr = behavior.compute_thresholds(Xtr_raw)
def beh_weights(Xraw):
    b = behavior.abstract_behaviours(Xraw, thr)
    w3 = (b["LargePackets"] * b["HighEntropy"]).astype(np.float32)  # Ax3
    w4 = b["BurstTraffic"].astype(np.float32)                        # Ax4
    w5 = b["ScanProbe"].astype(np.float32)                           # Ax5 (valid now)
    return np.stack([w3, w4, w5], axis=1)
W_tr = beh_weights(Xtr_raw)
print(f"behaviour weights mean: Ax3={W_tr[:,0].mean():.3f} Ax4={W_tr[:,1].mean():.3f} Ax5={W_tr[:,2].mean():.3f}")

# ---- transform + scale ----
sc = StandardScaler().fit(features.transform(Xtr_raw, TFM))
def prep(Xraw): return sc.transform(features.transform(Xraw, TFM)).reshape(-1, Xtr_raw.shape[1], 1).astype(np.float32)
Xtr, Xval, Xte = prep(Xtr_raw), prep(Xval_raw), prep(Xte_raw)

le = LabelEncoder().fit(ytr); n_classes = len(le.classes_)
benign_idx = list(le.classes_).index("BENIGN")
ytr_e, yval_e = le.transform(ytr), le.transform(yval)

if SUBSET > 0:
    i = np.random.RandomState(SEED).choice(len(Xtr), min(SUBSET, len(Xtr)), replace=False)
    Xtr, ytr_e, ytr, W_tr = Xtr[i], ytr_e[i], ytr[i], W_tr[i]
    print(f"[SMOKE] {len(Xtr)} rows, {EPOCHS} epochs")

# ---- losses ----
def focal_loss(yt, yp, gamma=2.0):
    yt = tf.reshape(tf.cast(yt, tf.int32), [-1]); yp = tf.clip_by_value(yp, 1e-7, 1 - 1e-7)
    pt = tf.reduce_sum(yp * tf.one_hot(yt, n_classes), axis=-1)
    return tf.reduce_mean(-tf.pow(1 - pt, gamma) * tf.math.log(pt))

def ce_loss(yt, yp):
    return tf.reduce_mean(tf.keras.losses.sparse_categorical_crossentropy(tf.reshape(yt, [-1]), yp))

ce_fn = focal_loss if LOSS == "focal" else ce_loss

def sat_loss(sm, y_str, w, p=2.0):
    sm = tf.clip_by_value(sm, 1e-7, 1 - 1e-7)
    pben = sm[:, benign_idx]; patk = 1.0 - pben
    def sat_masked(target, mask):   # soft-mean satisfaction of `target` weighted by mask
        m = tf.constant(mask, tf.float32); n = tf.maximum(tf.reduce_sum(m), 1.0)
        err = tf.pow(1.0 - target, p) * m
        return 1.0 - tf.pow(tf.clip_by_value(tf.reduce_sum(err) / n, 0.0, 1.0), 1.0 / p)
    sats = []
    if AXIOMS in ("base", "both"):
        sats += [sat_masked(pben, (y_str == "BENIGN").astype(np.float32)),
                 sat_masked(patk, (y_str != "BENIGN").astype(np.float32))]
    if AXIOMS in ("behaviour", "both"):
        sats += [sat_masked(patk, w[:, 0]), sat_masked(patk, w[:, 1]), sat_masked(patk, w[:, 2])]
    sat = tf.reduce_mean(tf.stack(sats))
    return tf.clip_by_value(1.0 - sat, 0.0, 1.0)

# ---- model ----
def build():
    inp = Input((Xtr.shape[1], 1), name="input"); x = inp
    for f, n in [(32, "1"), (64, "2"), (128, "3")]:
        x = layers.Conv1D(f, 3, padding="same", activation="relu", name=f"conv{n}")(x)
        x = layers.BatchNormalization(name=f"bn{n}")(x); x = layers.MaxPooling1D(2, name=f"pool{n}")(x)
    x = layers.Flatten(name="flatten")(x)
    x = layers.Dense(64, activation="relu", kernel_regularizer=tf.keras.regularizers.l2(1e-4), name="embedding")(x)
    x = layers.Dropout(0.4)(x); x = layers.Dense(32, activation="relu", name="dense2")(x); x = layers.Dropout(0.3)(x)
    return models.Model(inp, layers.Dense(n_classes, activation="softmax", name="output")(x), name="ltn_paper")

cnn = build()
opt = tf.keras.optimizers.Adam(3e-4, clipnorm=1.0)
BATCH = 256; n = len(Xtr); nb = int(np.ceil(n / BATCH))
best_va, best_ep, noimp = 0.0, 0, 0; best_w = None
print(f"\nTraining {TAG} ...")
for ep in range(1, EPOCHS + 1):
    perm = np.random.permutation(n)
    Xs, ye, ys, Ws = Xtr[perm], ytr_e[perm], ytr[perm], W_tr[perm]
    for b in range(nb):
        s, e = b * BATCH, min((b + 1) * BATCH, n)
        xb = tf.constant(Xs[s:e]); yb = tf.constant(ye[s:e], tf.float32)
        with tf.GradientTape() as tape:
            sm = cnn(xb, training=True); sm = tf.clip_by_value(sm, 1e-7, 1 - 1e-7)
            ce = ce_fn(yb, sm)
            sat = sat_loss(sm, ys[s:e], Ws[s:e])
            if OMEGA_MODE == "ratio":
                oeff = OMEGA * tf.stop_gradient(ce) / (tf.stop_gradient(sat) + 1e-7)
            else:
                oeff = OMEGA
            total = ce + oeff * sat
        if tf.math.is_nan(total): continue
        g = tape.gradient(total, cnn.trainable_variables)
        g, _ = tf.clip_by_global_norm([tf.where(tf.math.is_nan(x), tf.zeros_like(x), x) for x in g], 1.0)
        opt.apply_gradients(zip(g, cnn.trainable_variables))
    va = (np.argmax(cnn(tf.constant(Xval), training=False).numpy(), 1) == yval_e).mean()
    if va > best_va: best_va, best_ep, noimp, best_w = va, ep, 0, cnn.get_weights()
    else: noimp += 1
    if ep % 5 == 0 or ep == 1: print(f"  ep {ep:3d} val_acc={va:.4f} (best {best_va:.4f}@{best_ep}) ce={float(ce):.4f} sat={float(sat):.4f}")
    if noimp >= 8: print(f"  early stop @ {ep}"); break
if best_w: cnn.set_weights(best_w)

# ---- evaluate + save ----
prob = cnn.predict(Xte, batch_size=1024, verbose=0)
patk = 1.0 - prob[:, benign_idx]
res = metrics.evaluate(yte, patk, zero_day, fpr=0.01)
metrics.print_report(res)
np.save(os.path.join(paths.PREDICTIONS, f"y_prob_{TAG}_test.npy"), patk.astype(np.float32))
if SUBSET == 0:
    cnn.save(os.path.join(paths.MODELS, f"{TAG}.keras"))
    tracking.log_run(TAG, {"protocol": "paper", "loss": LOSS, "axioms": AXIOMS,
                           "omega": OMEGA, "omega_mode": OMEGA_MODE, "seed": SEED}, metrics.flatten(res))
    print(f"logged {TAG} to runs.jsonl")
print(f"DONE ({TAG})  best_val_acc={best_va:.4f}@{best_ep}")

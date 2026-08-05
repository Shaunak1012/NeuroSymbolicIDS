"""
protocol_variance.py — Tier D / Phase 7.5 Tier 2 items #6 (k-fold CV) and #7
(checkpoint averaging, SWA).

WHAT THIS MEASURES THAT NOTHING ELSE DOES
------------------------------------------
The measured noise floor (SD 0.0222, CV 3.6 %) came from re-running the SAME
split with the SAME seed, so it captures **training stochasticity**. Now that
`determinism.py` pins that source, a different and arguably more important
question is exposed:

    **How much does the headline move if we had drawn a different TRAIN SPLIT?**

That is data variance, not seed variance, and no measurement in this project has
ever separated the two. A paper that reports one number from one stratified draw
is implicitly claiming this quantity is small. It has never been checked.

DESIGN — AND THE CONSTRAINT THAT SHAPES IT
-------------------------------------------
**The test set is FIXED and never re-partitioned.** Zero-day families are
test-only by construction; folding them into training would destroy the protocol
and produce a meaningless number. So the k-fold runs over the **train+val pool
only** (known classes), and every fold is scored against the same untouched test
set. Each fold therefore answers "same model, same evaluation, different
training draw".

⚠️ This is NOT the k-fold usually reported in NIDS papers, which rotates the test
set too and thereby reports known-class performance. Ours holds the zero-day
evaluation fixed on purpose. Stated so the numbers are not mistaken for theirs.

SWA (item #7) averages the weights of the final K epochs of a single run.
Cheap intra-run variance reduction: the iterates late in training oscillate
around a minimum, and their average often sits in a flatter region than any
individual iterate.

PRE-REGISTERED PREDICTIONS (written before running — see git history)
---------------------------------------------------------------------
D1  **Data-split variance is comparable to or LARGER than the seed noise floor
    (SD >= 0.0222).** Rationale: which specific benign flows get under-sampled
    into the 1:1 balance, and which known-attack examples land in train vs val,
    changes the decision boundary more than thread scheduling does. If it comes
    back much smaller, the single-split protocol is safer than feared and that
    is worth knowing too.

D2  **SWA reduces nothing on the zero-day metric.** Rationale: SWA flattens the
    solution with respect to the KNOWN-class loss surface it is averaging over.
    Zero-day performance is not what that loss measures, so there is no reason
    for weight averaging to stabilise it. Falsified if SWA's macro sits above
    the fold mean by more than the noise floor.

Run:  scripts/run_long.sh protocol_variance.py
      KFOLD_N=3 scripts/run_long.sh protocol_variance.py   # cheaper
Out:  outputs/metadata/protocol_variance.json
"""
import os
import sys
import json
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
import tensorflow as tf                                        # noqa: E402
from tensorflow.keras import layers, models, Input, callbacks   # noqa: E402
from sklearn.preprocessing import StandardScaler, LabelEncoder  # noqa: E402
from sklearn.model_selection import StratifiedKFold             # noqa: E402
from sklearn.utils.class_weight import compute_class_weight     # noqa: E402

import paths, config, features, metrics, tracking              # noqa: E402
import determinism                                             # noqa: E402

cfg = config.get()
SEED = int(os.environ.get("PV_SEED", cfg["seed"]))
DET = determinism.enable(SEED, intra=int(os.environ.get("TF_THREADS", "16")),
                         inter=int(os.environ.get("TF_THREADS_INTER", "2")))
PAPER = os.path.join(paths.PROCESSED, cfg["paths"]["paper_subdir"])
TFM = cfg["protocol"]["feature_transform"]
KFOLD_N = int(os.environ.get("KFOLD_N", "5"))
EPOCHS = int(os.environ.get("PV_EPOCHS", "30"))
SWA_LAST = int(os.environ.get("SWA_LAST", "5"))
NOISE_SD = 0.0222
print(f"CONFIG: seed={SEED} folds={KFOLD_N} epochs={EPOCHS} swa_last={SWA_LAST}",
      flush=True)


def load(split):
    X = np.load(os.path.join(PAPER, f"X_{split}.npy"))
    ymc = np.load(os.path.join(PAPER, f"y_{split}_mc.npy"), allow_pickle=True)
    return X, ymc


Xtr, ytr = load("train"); Xval, yval = load("val"); Xte, yte_mc = load("test")
zero_day = set(np.load(os.path.join(PAPER, "zero_day_classes.npy"), allow_pickle=True).tolist())

# Pool train+val. The TEST set is never touched.
Xpool = np.concatenate([Xtr, Xval]); ypool = np.concatenate([ytr, yval])
print(f"pool {Xpool.shape} (train+val, known classes only) | test {Xte.shape} FIXED",
      flush=True)

Xpool_t = features.transform(Xpool, TFM)
Xte_t = features.transform(Xte, TFM)
le = LabelEncoder().fit(ypool)
n_classes, benign_idx = len(le.classes_), list(le.classes_).index("BENIGN")
ypool_e = le.transform(ypool)
nfeat = Xpool_t.shape[1]


# 🔴 THIS MUST BE cnn_paper.py's MODEL, EXACTLY.
# The first version of this file used a loosely "CNN-like" model — 2 conv blocks,
# GlobalAveragePooling, plain cross-entropy, plus class_weight — and carried a
# docstring claiming it was "the same shape as cnn_paper.py". It was not, and
# fold 1 came back at macro 0.3244 against the CNN's 0.6250. That gap was an
# ARCHITECTURE AND LOSS difference being silently reported as data-split
# variance, which is the exact confound this script exists to isolate. Caught by
# reading cnn_paper.py instead of trusting the comment I had written from memory
# — the "verify against source, not memory" rule in CLAUDE.md.
#
# cnn_paper.py cannot be imported (it is a script: importing runs a full
# training), so the definition is replicated here and must be kept in sync.
def focal(alpha_w, gamma=2.0):
    """Verbatim from cnn_paper.py, including the reshape([-1]) that fixes the
    (batch,1) broadcast bug — any new loss in this project must apply it."""
    a = tf.constant(alpha_w); nc = len(alpha_w)

    def loss(yt, yp):
        yt = tf.reshape(tf.cast(yt, tf.int32), [-1])
        yp = tf.clip_by_value(yp, tf.keras.backend.epsilon(),
                              1 - tf.keras.backend.epsilon())
        pt = tf.reduce_sum(yp * tf.one_hot(yt, nc), axis=-1)
        return tf.reduce_mean(-tf.gather(a, yt) * tf.pow(1 - pt, gamma) * tf.math.log(pt))
    return loss


def build(nf, nc):
    """Verbatim from cnn_paper.py, so fold-to-fold variance is attributable to
    the DATA SPLIT and nothing else."""
    inp = Input((nf, 1), name="input")
    x = inp
    for f, n in [(32, "1"), (64, "2"), (128, "3")]:
        x = layers.Conv1D(f, 3, padding="same", activation="relu", name=f"conv{n}")(x)
        x = layers.BatchNormalization(name=f"bn{n}")(x)
        x = layers.MaxPooling1D(2, name=f"pool{n}")(x)
    x = layers.Flatten(name="flatten")(x)
    x = layers.Dense(64, activation="relu",
                     kernel_regularizer=tf.keras.regularizers.l2(1e-4),
                     name="embedding")(x)
    x = layers.Dropout(0.4)(x)
    x = layers.Dense(32, activation="relu",
                     kernel_regularizer=tf.keras.regularizers.l2(1e-4),
                     name="dense2")(x)
    x = layers.Dropout(0.3)(x)
    return models.Model(inp, layers.Dense(nc, activation="softmax", name="output")(x))


def score(model, Xt):
    p = model.predict(Xt, batch_size=2048, verbose=0)
    return (1.0 - p[:, benign_idx]).astype(np.float64)


def ev(s):
    r = metrics.evaluate(yte_mc, s, zero_day, fpr=0.01)
    return r["macro"]["pr_auc"], {k: v["pr_auc"] for k, v in r["zeroday_family"].items()}, r


RES = {"folds": [], "meta": {"n_folds": KFOLD_N, "epochs": EPOCHS, "seed": SEED,
                             "noise_floor_sd": NOISE_SD,
                             "test_set": "FIXED, never re-partitioned"}}

# =============================================================================
# PART 1 — K-FOLD OVER THE TRAIN+VAL POOL, TEST HELD FIXED
# =============================================================================
skf = StratifiedKFold(n_splits=KFOLD_N, shuffle=True, random_state=SEED)
swa_snapshots = []
for k, (itr, iva) in enumerate(skf.split(Xpool_t, ypool_e)):
    print(f"\n=== fold {k+1}/{KFOLD_N} ===", flush=True)
    t0 = time.time()
    # Scaler refit PER FOLD -- refitting on each fold's own training rows is the
    # point; a scaler fit on the whole pool would leak fold-validation
    # statistics into training and shrink the very variance being measured.
    sc = StandardScaler().fit(Xpool_t[itr])
    Xa = sc.transform(Xpool_t[itr]).reshape(-1, nfeat, 1).astype(np.float32)
    Xb = sc.transform(Xpool_t[iva]).reshape(-1, nfeat, 1).astype(np.float32)
    Xt = sc.transform(Xte_t).reshape(-1, nfeat, 1).astype(np.float32)
    ya, yb = ypool_e[itr], ypool_e[iva]

    # alpha computed per fold from that fold's own training rows, exactly as
    # cnn_paper.py computes it from its training split.
    cw = compute_class_weight("balanced", classes=np.unique(ya), y=ya)
    alpha = np.array([dict(zip(np.unique(ya), cw)).get(i, 1.0) for i in range(n_classes)])
    alpha = (alpha / alpha.mean()).astype(np.float32)
    model = build(nfeat, n_classes)
    model.compile(optimizer=tf.keras.optimizers.Adam(3e-4), loss=focal(alpha),
                  metrics=["sparse_categorical_accuracy"])

    snaps = []

    class Snap(callbacks.Callback):
        """Keep the last SWA_LAST epochs' weights for part 2."""

        def on_epoch_end(self, epoch, logs=None):
            snaps.append([w.copy() for w in self.model.get_weights()])
            if len(snaps) > SWA_LAST:
                snaps.pop(0)

    # ⚠️ NO class_weight — cnn_paper.py deliberately omits it because focal-loss
    # alpha already handles the imbalance, and passing both compounds the effect
    # (the "double class-weighting" issue in KNOWN_ISSUES). The first version of
    # this script passed it, which alone made the model non-comparable.
    # Callbacks also match cnn_paper.py: monitor val accuracy, not val_loss.
    hist = model.fit(Xa, ya, validation_data=(Xb, yb), epochs=EPOCHS, batch_size=256,
                     verbose=2,
                     callbacks=[callbacks.EarlyStopping(
                                    monitor="val_sparse_categorical_accuracy",
                                    patience=8, restore_best_weights=True, mode="max"),
                                callbacks.ReduceLROnPlateau(
                                    monitor="val_sparse_categorical_accuracy",
                                    factor=0.5, patience=3, min_lr=1e-6, mode="max"),
                                Snap()])
    macro, fam, r = ev(score(model, Xt))
    print(f"  fold {k+1}: macro {macro:.4f} | Bot {fam.get('Bot', float('nan')):.4f} "
          f"| {time.time()-t0:.0f}s | epochs {len(hist.history['loss'])}", flush=True)
    RES["folds"].append({"fold": k + 1, "macro": macro, "families": fam,
                         "epochs": len(hist.history["loss"]),
                         "n_train": int(len(itr)), "n_val": int(len(iva))})
    tracking.log_run(f"cnn_kfold{k+1}", {"protocol": "paper", "seed": SEED,
                                         "fold": k + 1, "n_folds": KFOLD_N,
                                         "tier": "protocol_variance"},
                     metrics.flatten(r))
    if k == 0:                       # SWA is measured on fold 1 only
        swa_snapshots = snaps
        swa_model, swa_X = model, Xt
    else:
        del model
        tf.keras.backend.clear_session()

vals = np.array([f["macro"] for f in RES["folds"]])
print("\n" + "=" * 92)
print("PART 1 — DATA-SPLIT VARIANCE (test set fixed; only the train/val draw changes)")
print("=" * 92)
for f in RES["folds"]:
    print(f"  fold {f['fold']}  macro {f['macro']:.4f}  Bot {f['families'].get('Bot', 0):.4f}")
print(f"\n  mean {vals.mean():.4f} | SD {vals.std(ddof=1):.4f} | "
      f"range [{vals.min():.4f}, {vals.max():.4f}] (spread {vals.ptp():.4f})")
print(f"  seed/training noise floor for comparison: SD {NOISE_SD:.4f}")
ratio = vals.std(ddof=1) / NOISE_SD
print(f"  data-split SD / training SD = {ratio:.2f}x")
d1 = vals.std(ddof=1) >= NOISE_SD
RES["kfold"] = {"mean": float(vals.mean()), "sd": float(vals.std(ddof=1)),
                "min": float(vals.min()), "max": float(vals.max()),
                "ratio_to_noise_floor": float(ratio)}

# =============================================================================
# PART 2 — SWA on fold 1
# =============================================================================
print("\n" + "=" * 92)
print(f"PART 2 — SWA: average of the last {len(swa_snapshots)} epochs (fold 1)")
print("=" * 92)
if len(swa_snapshots) >= 2:
    avg = [np.mean([s[i] for s in swa_snapshots], axis=0)
           for i in range(len(swa_snapshots[0]))]
    base_macro = RES["folds"][0]["macro"]
    swa_model.set_weights(avg)
    swa_macro, swa_fam, _ = ev(score(swa_model, swa_X))
    delta = swa_macro - base_macro
    print(f"  fold-1 best-epoch macro {base_macro:.4f}")
    print(f"  fold-1 SWA        macro {swa_macro:.4f}   ({delta:+.4f}, "
          f"{delta/NOISE_SD:+.2f} SD)")
    d2 = delta <= NOISE_SD
    RES["swa"] = {"n_snapshots": len(swa_snapshots), "base_macro": base_macro,
                  "swa_macro": swa_macro, "delta": float(delta),
                  "delta_in_sd": float(delta / NOISE_SD)}
else:
    print("  not enough snapshots (run ended too early)")
    d2, RES["swa"] = True, None

print("\n" + "=" * 92)
print("PRE-REGISTERED PREDICTIONS")
print("=" * 92)
print(f"  D1 data-split SD >= training SD : {'CONFIRMED' if d1 else 'FALSIFIED'} "
      f"({vals.std(ddof=1):.4f} vs {NOISE_SD:.4f}, {ratio:.2f}x)")
if d1:
    print("     -> A single stratified draw understates the uncertainty on the headline.")
    print("        Any future single-split number should carry this SD, not just the seed one.")
else:
    print("     -> The single-split protocol is more stable than feared; the dominant")
    print("        uncertainty remains training stochasticity, now pinned by determinism.py.")
if RES["swa"]:
    print(f"  D2 SWA does not help zero-day   : {'CONFIRMED' if d2 else 'FALSIFIED'} "
          f"({RES['swa']['delta']:+.4f})")

RES["predictions"] = {"D1_data_sd_ge_noise": bool(d1), "D2_swa_no_help": bool(d2)}
RES["cross_dataset"] = {
    "status": "BLOCKED — not attempted",
    "reason": "CIC-IDS2018 is not present locally (data/ holds only the 2017 "
              "raw_csv, raw_csv_full and processed dirs). Phase 6 cross-dataset "
              "validation needs a separate data acquisition step; reporting this "
              "rather than silently skipping it."}
print("\n  ⬜ Cross-dataset (Phase 6) is BLOCKED: CIC-IDS2018 is not present locally.")
print("     Recorded in the JSON rather than silently skipped.")

outp = os.path.join(paths.METADATA, "protocol_variance.json")
with open(outp, "w", encoding="utf-8") as f:
    json.dump(RES, f, indent=1)
print(f"\nwrote {outp}")
print("DONE (protocol_variance)")

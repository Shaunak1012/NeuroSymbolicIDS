"""
deep_zoo.py — Tier B: the deep architectures the NIDS literature reports and this
project had never run. LSTM, GRU, CNN-LSTM and a Transformer encoder.

WHY IT IS LAST
--------------
Every model here needs a full training run, so this tier costs the most wall
clock and — on the evidence already collected — is the one predicted to teach us
least. It is run anyway because *"why didn't you try an LSTM?"* is a guaranteed
reviewer/examiner question and "we predicted it wouldn't help" is not an answer.

⚠️ A HONEST NOTE ON APPLYING SEQUENCE MODELS TO THIS DATA
---------------------------------------------------------
An LSTM over a **flow feature vector** is not a sequence model in the sense the
NIDS literature usually means. Each row is 68 independent engineered statistics
of one flow — Destination Port, Flow Duration, packet-length means — not 68
time-ordered observations. Running an LSTM across the feature axis treats an
arbitrary column ordering as a temporal ordering, which is exactly what
`check.py` exists to stop people doing casually.

**This is done deliberately and labelled**, because it is what papers reporting
"LSTM on CIC-IDS2017 flow features" actually do. The genuinely sequential
version would consume packet sequences or flow sequences per host, which this
project does not have (payload/PCAP is documented future work, and the KG is
where per-host temporal structure lives). **Do not write these up as evidence
that "sequence modelling doesn't help intrusion detection"** — they are evidence
about sequence layers applied to unordered tabular features.

The Transformer is not subject to that objection in the same way: self-attention
is permutation-equivariant, so treating the 68 features as an unordered set is
principled (that is what FT-Transformer/TabTransformer do for tabular data).

PRE-REGISTERED PREDICTIONS (written before running — see git history)
---------------------------------------------------------------------
B1  **None of them escapes the top tier upward.** All should land within, or
    below, ~0.0256 of the CNN's n=6 mean of 0.6250. Rationale: the task is
    saturated for closed-set supervised learners — CNN, LTN control, RF and MSP
    are already mutually indistinguishable, and a single depth-20 decision tree
    reaches 0.6049.

B2  **None of them detects Bot** (all at 1-2x chance, i.e. Bot PR-AUC well under
    0.10). Rationale: the Bot failure is representational and shared by every
    closed-set discriminative method measured so far. Architecture does not
    change which features carry gradient pressure.

B3  **The Transformer is the most likely to differ**, because attention over
    features is the only architecture here whose inductive bias actually matches
    unordered tabular data. If anything beats the CNN, it should be this.

Run:  scripts/run_long.sh deep_zoo.py
      DEEP_ARCH=lstm scripts/run_long.sh deep_zoo.py     # one architecture only
Out:  outputs/metadata/deep_zoo.json + runs.jsonl + per-model scores
"""
import os
import sys
import json
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
import tensorflow as tf                                       # noqa: E402
from tensorflow.keras import layers, models, Input, callbacks  # noqa: E402
from sklearn.preprocessing import StandardScaler, LabelEncoder  # noqa: E402
from sklearn.utils.class_weight import compute_class_weight   # noqa: E402

import paths, config, features, metrics, tracking             # noqa: E402
import determinism                                            # noqa: E402

cfg = config.get()
_DEFAULT_SEED = cfg["seed"]
SEED = int(os.environ.get("DEEP_SEED", _DEFAULT_SEED))
DET = determinism.enable(SEED, intra=int(os.environ.get("TF_THREADS", "16")),
                         inter=int(os.environ.get("TF_THREADS_INTER", "2")))
SUFFIX = "" if SEED == _DEFAULT_SEED else f"_s{SEED}"
PAPER = os.path.join(paths.PROCESSED, cfg["paths"]["paper_subdir"])
TFM = cfg["protocol"]["feature_transform"]
EPOCHS = int(os.environ.get("DEEP_EPOCHS", "30"))
ONLY = os.environ.get("DEEP_ARCH", "").strip().lower()
print(f"CONFIG: seed={SEED} epochs={EPOCHS} only={ONLY or 'all'}", flush=True)


def load(split):
    X = np.load(os.path.join(PAPER, f"X_{split}.npy"))
    ymc = np.load(os.path.join(PAPER, f"y_{split}_mc.npy"), allow_pickle=True)
    return X, ymc


Xtr, ytr = load("train"); Xval, yval = load("val"); Xte, yte_mc = load("test")
zero_day = set(np.load(os.path.join(PAPER, "zero_day_classes.npy"), allow_pickle=True).tolist())

Xtr = features.transform(Xtr, TFM); Xval = features.transform(Xval, TFM)
Xte = features.transform(Xte, TFM)
sc = StandardScaler().fit(Xtr)
Xtr, Xval, Xte = sc.transform(Xtr), sc.transform(Xval), sc.transform(Xte)

le = LabelEncoder().fit(ytr)
n_classes = len(le.classes_)
benign_idx = list(le.classes_).index("BENIGN")
ytr_e, yval_e = le.transform(ytr), le.transform(yval)
nfeat = Xtr.shape[1]
# (rows, timesteps=68, channels=1) -- same shape cnn_paper.py uses.
Xtr = Xtr.reshape(-1, nfeat, 1).astype(np.float32)
Xval = Xval.reshape(-1, nfeat, 1).astype(np.float32)
Xte = Xte.reshape(-1, nfeat, 1).astype(np.float32)
print(f"train {Xtr.shape} | val {Xval.shape} | test {Xte.shape} | {n_classes} classes",
      flush=True)

cw = compute_class_weight("balanced", classes=np.unique(ytr_e), y=ytr_e)
CW = {i: float(w) for i, w in enumerate(cw)}


def build_lstm(nf, nc):
    inp = Input((nf, 1))
    x = layers.LSTM(64, return_sequences=True)(inp)
    x = layers.LSTM(32)(x)
    x = layers.Dense(32, activation="relu", name="embedding")(x)
    return models.Model(inp, layers.Dense(nc, activation="softmax")(x), name="lstm")


def build_gru(nf, nc):
    inp = Input((nf, 1))
    x = layers.GRU(64, return_sequences=True)(inp)
    x = layers.GRU(32)(x)
    x = layers.Dense(32, activation="relu", name="embedding")(x)
    return models.Model(inp, layers.Dense(nc, activation="softmax")(x), name="gru")


def build_cnn_lstm(nf, nc):
    inp = Input((nf, 1))
    x = layers.Conv1D(64, 3, activation="relu", padding="same")(inp)
    x = layers.MaxPooling1D(2)(x)
    x = layers.Conv1D(64, 3, activation="relu", padding="same")(x)
    x = layers.LSTM(64)(x)
    x = layers.Dense(32, activation="relu", name="embedding")(x)
    return models.Model(inp, layers.Dense(nc, activation="softmax")(x), name="cnn_lstm")


def build_transformer(nf, nc, d=32, heads=4, blocks=2):
    """Feature-token self-attention, the FT-Transformer/TabTransformer shape.
    Permutation-equivariant over features, so no false temporal ordering is
    imposed -- unlike the recurrent models above."""
    inp = Input((nf, 1))
    x = layers.Dense(d)(inp)                       # per-feature token embedding
    for _ in range(blocks):
        h = layers.LayerNormalization(epsilon=1e-6)(x)
        h = layers.MultiHeadAttention(num_heads=heads, key_dim=d // heads)(h, h)
        x = layers.Add()([x, h])
        h = layers.LayerNormalization(epsilon=1e-6)(x)
        h = layers.Dense(d * 2, activation="relu")(h)
        h = layers.Dense(d)(h)
        x = layers.Add()([x, h])
    x = layers.GlobalAveragePooling1D()(x)
    x = layers.Dense(32, activation="relu", name="embedding")(x)
    return models.Model(inp, layers.Dense(nc, activation="softmax")(x), name="transformer")


ARCHS = {"lstm": build_lstm, "gru": build_gru,
         "cnn_lstm": build_cnn_lstm, "transformer": build_transformer}
if ONLY:
    ARCHS = {k: v for k, v in ARCHS.items() if k == ONLY}
    if not ARCHS:
        raise SystemExit(f"DEEP_ARCH={ONLY!r} is not one of {list(ARCHS)}")

RES = {}
BOT_CHANCE = 1956 / (1956 + 55237)
CNN_N6, THRESH = 0.6250, 0.0256

for name, builder in ARCHS.items():
    tag = f"deep_{name}{SUFFIX}"
    print(f"\n=== {tag} ===", flush=True)
    t0 = time.time()
    model = builder(nfeat, n_classes)
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-3),
                  loss="sparse_categorical_crossentropy",
                  metrics=["sparse_categorical_accuracy"])
    print(f"  params {model.count_params():,}", flush=True)
    hist = model.fit(Xtr, ytr_e, validation_data=(Xval, yval_e), epochs=EPOCHS,
                     batch_size=256, class_weight=CW, verbose=2,
                     callbacks=[callbacks.EarlyStopping(monitor="val_loss", patience=5,
                                                        restore_best_weights=True)])
    fit_s = time.time() - t0
    prob = model.predict(Xte, batch_size=2048, verbose=0)
    p_attack = 1.0 - prob[:, benign_idx]
    r = metrics.evaluate(yte_mc, p_attack.astype(np.float64), zero_day, fpr=0.01)
    macro = r["macro"]["pr_auc"]
    fam = {k: v["pr_auc"] for k, v in r["zeroday_family"].items()}
    dg = r["diagnostics"]
    print(f"  macro {macro:.4f} | Bot {fam.get('Bot', float('nan')):.4f} "
          f"| fit {fit_s/60:.1f}min | epochs {len(hist.history['loss'])} "
          f"| tie {dg['largest_tie_frac']:.3f}", flush=True)

    model.save(os.path.join(paths.MODELS, f"{tag}.keras"))
    np.save(os.path.join(paths.predictions_dir(tag), f"y_prob_{tag}_test.npy"),
            p_attack.astype(np.float64))
    tracking.log_run(tag, {"protocol": "paper", "transform": TFM, "seed": SEED,
                           "family": "A", "tier": "deep_zoo", "arch": name,
                           "epochs_run": len(hist.history["loss"]),
                           "params": int(model.count_params()),
                           **{f"det_{k}": v for k, v in DET.items()}},
                     metrics.flatten(r))
    RES[tag] = {"macro": macro, "families": fam, "fit_minutes": fit_s / 60,
                "params": int(model.count_params()),
                "epochs_run": len(hist.history["loss"]),
                "largest_tie_frac": dg["largest_tie_frac"],
                "overall_binary_pr_auc": r["views"]["all"]["pr_auc"]}
    del model
    tf.keras.backend.clear_session()

# ---- table + verdicts --------------------------------------------------------
print("\n" + "=" * 100)
print(f"TIER B — DEEP ARCHITECTURES (seed {SEED})")
print("=" * 100)
print(f"  {'model':22s} {'MACRO zd':>9s} {'Bot':>8s} {'lift':>7s} {'WebBF':>8s} "
      f"{'XSS':>8s} | {'FIELD bin':>10s} {'min':>6s}")
for tag, d in sorted(RES.items(), key=lambda kv: -kv[1]["macro"]):
    f = d["families"]
    bot = f.get("Bot", float("nan"))
    print(f"  {tag:22s} {d['macro']:>9.4f} {bot:>8.4f} {bot/BOT_CHANCE:>6.2f}x "
          f"{f.get('Web Attack Brute Force', float('nan')):>8.4f} "
          f"{f.get('Web Attack XSS', float('nan')):>8.4f} | "
          f"{d['overall_binary_pr_auc']:>10.4f} {d['fit_minutes']:>6.1f}")
print(f"\n  Reference: CNN 0.6250 [n=6] | LTN control 0.6110 | RandomForest 0.5985")
print(f"  Indistinguishable from the CNN if |gap| <= {THRESH}")

above = [t for t, d in RES.items() if d["macro"] - CNN_N6 > THRESH]
b1 = not above
best_bot = max(RES.items(), key=lambda kv: kv[1]["families"].get("Bot", 0)) if RES else None
b2 = best_bot and best_bot[1]["families"].get("Bot", 0) < 0.10
print("\n" + "=" * 100)
print("PRE-REGISTERED PREDICTIONS")
print("=" * 100)
print(f"  B1 none escapes the top tier upward : {'CONFIRMED' if b1 else 'FALSIFIED'}"
      f"{'' if b1 else '  -> ' + ', '.join(above)}")
if best_bot:
    print(f"  B2 none detects Bot                 : {'CONFIRMED' if b2 else 'FALSIFIED'} "
          f"(best {best_bot[0]} at {best_bot[1]['families'].get('Bot', 0):.4f})")
tr = RES.get(f"deep_transformer{SUFFIX}")
if tr and len(RES) > 1:
    others = max(d["macro"] for t, d in RES.items() if "transformer" not in t)
    print(f"  B3 transformer is the best of the tier: "
          f"{'CONFIRMED' if tr['macro'] > others else 'FALSIFIED'} "
          f"({tr['macro']:.4f} vs best other {others:.4f})")
print("\n  ⚠️  The recurrent models run over the FEATURE axis, not time — each row is 68")
print("     unordered engineered statistics, not 68 timesteps. This mirrors what published")
print("     'LSTM on CIC-IDS2017' work does, but these results are NOT evidence about")
print("     sequence modelling for intrusion detection. See the module docstring.")

RES["_predictions"] = {"B1_none_above_band": bool(b1), "B2_no_bot": bool(b2)}
RES["_meta"] = {"seed": SEED, "epochs_cap": EPOCHS, "cnn_n6_reference": CNN_N6,
                "threshold": THRESH,
                "caveat": "recurrent models applied across the feature axis, not time"}
outp = os.path.join(paths.METADATA, f"deep_zoo{SUFFIX}.json")
with open(outp, "w", encoding="utf-8") as f:
    json.dump(RES, f, indent=1)
print(f"\nwrote {outp}")
print("DONE (deep_zoo)")

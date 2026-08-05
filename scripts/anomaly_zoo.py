"""
anomaly_zoo.py — Tier C: the deep / classical anomaly detectors this project had
not run. All (B)-family: trained on BENIGN ONLY, so they are zero-day-legitimate
by construction.

WHY THIS TIER MATTERS MORE THAN THE OTHERS
-------------------------------------------
On every measurement this project has made, the channels that touch Bot are the
ones that model *normality* rather than a decision boundary: the autoencoder
(0.1314), Mahalanobis (0.1030) and above all the KG (0.3103). Meanwhile every
closed-set supervised learner sits at 1-2x chance on Bot with a cross-seed rank
correlation indistinguishable from noise. **So this is the only tier where the
existing evidence says a real Bot gain is possible.**

WHAT IS ADDED (all benign-only, matching autoencoder_paper.py's discipline:
no attack label is used in training OR model selection)
---------------------------------------------------------------------------
  * **VAE**        — variational autoencoder. Score = negative ELBO. Unlike the
                     plain AE it models a DISTRIBUTION over normal traffic, so
                     it can in principle flag "plausible reconstruction, but from
                     an implausible latent region" — which a plain AE cannot.
  * **Deep SVDD**  — learns a compact hypersphere around benign data in a learned
                     space; score = distance from centre. The canonical deep
                     one-class method. Implemented with the standard collapse
                     guards: no bias terms and no bounded activations, since
                     either lets the network map everything to the centre and
                     score a perfect (meaningless) zero.
  * **One-Class SVM** — `SGDOneClassSVM`, the linear-time approximation. The
                     exact kernel OC-SVM is O(n^2) and not runnable at 442k
                     benign rows.
  * **LOF**        — Local Outlier Factor in novelty mode. Density-ratio against
                     local neighbourhoods, the classical instance-based anomaly
                     detector.

⚠️ SCALE DEVIATIONS, STATED NOT HIDDEN
--------------------------------------
  * **LOF is fitted on a 50,000-row benign subsample** (of ~442k). LOF stores its
    training set and scores every query against local neighbourhoods; at full
    size this does not finish. Size fixed in advance, not tuned.
  * **One-Class SVM uses the SGD approximation**, not the exact kernel method.

PRE-REGISTERED PREDICTIONS (written before running — see git history)
---------------------------------------------------------------------
C1  **At least one of these beats the autoencoder's Bot 0.1314.** This is the
    tier where the evidence says it is possible. If ALL of them fail to, that is
    itself a strong result: it would mean the AE is not merely "a" benign-only
    method that works on Bot but close to the best that family offers on this
    representation, and the KG's 0.3103 comes from something other than
    benign-density modelling (its clustering + temporal structure).

C2  **All of them collapse on the web families** (macro well below 0.2),
    reproducing the AE's shape (macro 0.0970, Web BF 0.1048, XSS 0.0547). Web
    attacks are absorbed into a known attack class by supervised models; a
    benign-only model has no such mechanism and must flag them on distance
    alone, which the AE already showed is weak.

C3  **Deep SVDD is the collapse risk.** If its score variance is near zero, the
    network has mapped everything to the hypersphere centre — the known
    degenerate solution. The script checks for this explicitly rather than
    reporting a meaningless number.

Run:  scripts/run_long.sh anomaly_zoo.py
Out:  outputs/metadata/anomaly_zoo.json + runs.jsonl + per-model scores
"""
import os
import sys
import json
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
import tensorflow as tf                                    # noqa: E402
from tensorflow.keras import layers, models, Input, callbacks   # noqa: E402
from sklearn.preprocessing import StandardScaler           # noqa: E402
from sklearn.linear_model import SGDOneClassSVM            # noqa: E402
from sklearn.neighbors import LocalOutlierFactor           # noqa: E402

import paths, config, features, metrics, tracking          # noqa: E402
import determinism                                         # noqa: E402

cfg = config.get()
_DEFAULT_SEED = cfg["seed"]
SEED = int(os.environ.get("ANOM_SEED", _DEFAULT_SEED))
DET = determinism.enable(SEED, intra=int(os.environ.get("TF_THREADS", "16")),
                         inter=int(os.environ.get("TF_THREADS_INTER", "2")))
SUFFIX = "" if SEED == _DEFAULT_SEED else f"_s{SEED}"
PAPER = os.path.join(paths.PROCESSED, cfg["paths"]["paper_subdir"])
TFM = cfg["protocol"]["feature_transform"]
EPOCHS = int(os.environ.get("ANOM_EPOCHS", "50"))
LOF_SUBSAMPLE = 50_000
LATENT = 16
print(f"CONFIG: seed={SEED} suffix={SUFFIX or '(reference)'}", flush=True)


def load(split):
    X = np.load(os.path.join(PAPER, f"X_{split}.npy"))
    yb = np.load(os.path.join(PAPER, f"y_{split}_bin.npy"))
    ymc = np.load(os.path.join(PAPER, f"y_{split}_mc.npy"), allow_pickle=True)
    return X, yb, ymc


Xtr, ytr, _ = load("train")
Xval, yval, _ = load("val")
Xte, _, yte_mc = load("test")
zero_day = set(np.load(os.path.join(PAPER, "zero_day_classes.npy"), allow_pickle=True).tolist())

Xtr = features.transform(Xtr, TFM); Xval = features.transform(Xval, TFM)
Xte = features.transform(Xte, TFM)
sc = StandardScaler().fit(Xtr)
Xtr, Xval, Xte = sc.transform(Xtr), sc.transform(Xval), sc.transform(Xte)

# BENIGN ONLY, for training AND model selection. No attack label past this line.
Btr = Xtr[ytr == 0].astype(np.float32)
Bval = Xval[yval == 0].astype(np.float32)
Xte = Xte.astype(np.float32)
nfeat = Btr.shape[1]
print(f"benign-only train {Btr.shape} | val {Bval.shape} | test {Xte.shape}", flush=True)

RES, results = {}, {}
BOT_CHANCE = 1956 / (1956 + 55237)


def run(name, score_te, note="", extra=None):
    tag = f"{name}{SUFFIX}"
    s = np.asarray(score_te, float)
    r = metrics.evaluate(yte_mc, s, zero_day, fpr=0.01)
    results[tag] = r
    macro = r["macro"]["pr_auc"]
    fam = {k: v["pr_auc"] for k, v in r["zeroday_family"].items()}
    print(f"    {tag}: macro {macro:.4f} | Bot {fam.get('Bot', float('nan')):.4f} "
          f"({fam.get('Bot', 0)/BOT_CHANCE:.2f}x)", flush=True)
    params = {"protocol": "paper", "transform": TFM, "seed": SEED,
              "family": "B", "tier": "anomaly_zoo", "benign_only": True}
    if note:
        params["deviation"] = note
    tracking.log_run(tag, params, metrics.flatten(r))
    # float64: the saved array must reproduce the logged metric exactly. A
    # float32 cast collapses extreme scores into ties and moves PR-AUC (found
    # 2026-08-05 in baselines_classic.py, where it shifted GaussianNB's macro
    # from 0.1264 to 0.0597 on reload).
    np.save(os.path.join(paths.PREDICTIONS, f"y_prob_{tag}_test.npy"),
            np.asarray(s, np.float64))
    RES[tag] = {"macro": macro, "families": fam, "deviation": note or None,
                "score_std": float(s.std()), **(extra or {})}


# =============================================================================
# 1 — VARIATIONAL AUTOENCODER.  score = negative ELBO
# =============================================================================
print("\n=== VAE ===", flush=True)
t0 = time.time()


class VAE(models.Model):
    """Subclassed so the ELBO can be computed per-row at scoring time, which a
    functional model with an added KL loss cannot give back."""

    def __init__(self, nf, latent):
        super().__init__()
        self.enc = models.Sequential([Input((nf,)), layers.Dense(48, activation="relu"),
                                      layers.Dense(32, activation="relu"),
                                      layers.Dense(latent * 2)])
        self.dec = models.Sequential([Input((latent,)), layers.Dense(32, activation="relu"),
                                      layers.Dense(48, activation="relu"),
                                      layers.Dense(nf)])
        self.latent = latent

    def elbo(self, x):
        h = self.enc(x)
        mu, logvar = h[:, :self.latent], tf.clip_by_value(h[:, self.latent:], -8.0, 8.0)
        eps = tf.random.normal(tf.shape(mu))
        z = mu + tf.exp(0.5 * logvar) * eps
        xr = self.dec(z)
        rec = tf.reduce_sum(tf.square(x - xr), axis=1)
        kl = -0.5 * tf.reduce_sum(1 + logvar - tf.square(mu) - tf.exp(logvar), axis=1)
        return rec + kl

    def train_step(self, data):
        x = data[0] if isinstance(data, tuple) else data
        with tf.GradientTape() as tape:
            loss = tf.reduce_mean(self.elbo(x))
        g = tape.gradient(loss, self.trainable_variables)
        self.optimizer.apply_gradients(zip(g, self.trainable_variables))
        return {"loss": loss}

    def test_step(self, data):
        x = data[0] if isinstance(data, tuple) else data
        return {"loss": tf.reduce_mean(self.elbo(x))}


vae = VAE(nfeat, LATENT)
vae.compile(optimizer=tf.keras.optimizers.Adam(1e-3))
vae.fit(Btr, Btr, validation_data=(Bval, Bval), epochs=EPOCHS, batch_size=256,
        verbose=2,
        callbacks=[callbacks.EarlyStopping(monitor="val_loss", patience=5,
                                           restore_best_weights=True)])
sv = np.concatenate([vae.elbo(Xte[i:i + 4096]).numpy()
                     for i in range(0, len(Xte), 4096)])
print(f"  VAE fit {time.time()-t0:.0f}s", flush=True)
run("vae", sv)

# =============================================================================
# 2 — DEEP SVDD.  score = squared distance from the hypersphere centre
# =============================================================================
print("\n=== Deep SVDD ===", flush=True)
t0 = time.time()
# COLLAPSE GUARDS (C3): no bias terms and no bounded activations. With either,
# the network can map every input to the centre and drive the objective to zero
# — the known trivial solution, which looks like a perfect fit and detects
# nothing.
enc = models.Sequential([Input((nfeat,)),
                         layers.Dense(48, activation="relu", use_bias=False),
                         layers.Dense(32, activation="relu", use_bias=False),
                         layers.Dense(LATENT, use_bias=False)], name="svdd_enc")
c = tf.constant(enc.predict(Btr[:20000], batch_size=2048, verbose=0).mean(0))
# Standard fix: nudge near-zero centre coordinates away from 0, else they are a
# free direction the network can collapse along.
c = tf.where(tf.abs(c) < 1e-6, tf.fill(tf.shape(c), 1e-6), c)
opt = tf.keras.optimizers.Adam(1e-4)


@tf.function
def svdd_step(xb):
    with tf.GradientTape() as tape:
        loss = tf.reduce_mean(tf.reduce_sum(tf.square(enc(xb) - c), axis=1))
    g = tape.gradient(loss, enc.trainable_variables)
    opt.apply_gradients(zip(g, enc.trainable_variables))
    return loss


ds = tf.data.Dataset.from_tensor_slices(Btr).shuffle(65536, seed=SEED).batch(256)
for ep in range(min(EPOCHS, 20)):
    ls = [float(svdd_step(xb)) for xb in ds]
    if ep % 5 == 0 or ep == min(EPOCHS, 20) - 1:
        print(f"  epoch {ep:2d} loss {np.mean(ls):.6f}", flush=True)
zs = np.concatenate([np.square(enc.predict(Xte[i:i + 8192], batch_size=2048,
                                           verbose=0) - c.numpy()).sum(1)
                     for i in range(0, len(Xte), 8192)])
collapsed = bool(zs.std() < 1e-8)
print(f"  Deep SVDD fit {time.time()-t0:.0f}s | score std {zs.std():.3e} "
      f"| collapsed={collapsed}", flush=True)
if collapsed:
    print("  🔴 C3 TRIGGERED: hypersphere collapse — every input maps to the centre.")
    print("     The number below is meaningless; reported, not hidden.")
run("deep_svdd", zs, extra={"collapsed": collapsed})

# =============================================================================
# 3 — ONE-CLASS SVM (SGD approximation)
# =============================================================================
print("\n=== One-Class SVM (SGD) ===", flush=True)
t0 = time.time()
oc = SGDOneClassSVM(nu=0.05, random_state=SEED)
oc.fit(Btr)
print(f"  fit {time.time()-t0:.0f}s", flush=True)
run("ocsvm_sgd", -oc.decision_function(Xte),
    note="SGD linear approximation; exact kernel OC-SVM is O(n^2) at 442k benign rows")

# =============================================================================
# 4 — LOCAL OUTLIER FACTOR (novelty mode, subsampled)
# =============================================================================
print("\n=== LOF (novelty) ===", flush=True)
t0 = time.time()
rs = np.random.RandomState(SEED)
sub = rs.choice(len(Btr), min(LOF_SUBSAMPLE, len(Btr)), replace=False)
lof = LocalOutlierFactor(n_neighbors=20, novelty=True, n_jobs=-1)
lof.fit(Btr[sub])
print(f"  fit {time.time()-t0:.0f}s on {len(sub):,} benign rows", flush=True)
run("lof", -lof.decision_function(Xte),
    note=f"fitted on a {LOF_SUBSAMPLE:,}-row benign subsample of {len(Btr):,}; "
         f"LOF stores its training set and does not finish at full size")

# =============================================================================
# TABLE + VERDICTS
# =============================================================================
print("\n" + "=" * 96)
print(f"TIER C — BENIGN-ONLY ANOMALY DETECTORS (seed {SEED})")
print("=" * 96)
print(f"  {'model':18s} {'MACRO':>8s} {'Bot':>8s} {'Bot lift':>9s} {'WebBF':>8s} {'XSS':>8s}")
for tag, d in sorted(RES.items(), key=lambda kv: -kv[1]["families"].get("Bot", 0)):
    f = d["families"]
    bot = f.get("Bot", float("nan"))
    print(f"  {tag:18s} {d['macro']:>8.4f} {bot:>8.4f} {bot/BOT_CHANCE:>8.2f}x "
          f"{f.get('Web Attack Brute Force', float('nan')):>8.4f} "
          f"{f.get('Web Attack XSS', float('nan')):>8.4f}")
print("\n  Reference (B)-family: Autoencoder Bot 0.1314 (3.8x) macro 0.0970")
print("                        Mahalanobis Bot 0.1030 | IsolationForest Bot 0.0637")
print("                        KG causal   Bot 0.3103 (best channel measured)")

AE_BOT = 0.1314
best = max(RES.items(), key=lambda kv: kv[1]["families"].get("Bot", 0))
c1 = best[1]["families"].get("Bot", 0) > AE_BOT
c2 = all(d["macro"] < 0.20 for d in RES.values())
print("\n" + "=" * 96)
print("PRE-REGISTERED PREDICTIONS")
print("=" * 96)
print(f"  C1 something beats the AE on Bot : {'CONFIRMED' if c1 else 'FALSIFIED'}")
print(f"     best is {best[0]} at {best[1]['families'].get('Bot', 0):.4f} vs AE {AE_BOT}")
if not c1:
    print("     -> FALSIFIED is the informative outcome: the AE is close to the best this")
    print("        family offers on this representation, and the KG's 0.3103 therefore does")
    print("        NOT come from benign-density modelling — it comes from its clustering +")
    print("        temporal structure. That sharpens what the KG is actually contributing.")
print(f"  C2 all collapse on the web families : {'CONFIRMED' if c2 else 'FALSIFIED'} "
      f"(max macro {max(d['macro'] for d in RES.values()):.4f})")
svdd = RES.get(f"deep_svdd{SUFFIX}", {})
print(f"  C3 Deep SVDD collapse check       : "
      f"{'COLLAPSED (score void)' if svdd.get('collapsed') else 'no collapse'} "
      f"(score std {svdd.get('score_std', float('nan')):.3e})")

RES["_predictions"] = {"C1_beats_ae_on_bot": bool(c1), "C2_web_collapse": bool(c2),
                       "C3_svdd_collapsed": bool(svdd.get("collapsed", False))}
RES["_meta"] = {"seed": SEED, "lof_subsample": LOF_SUBSAMPLE, "latent": LATENT,
                "epochs": EPOCHS, "ae_bot_reference": AE_BOT}
outp = os.path.join(paths.METADATA, f"anomaly_zoo{SUFFIX}.json")
with open(outp, "w", encoding="utf-8") as f:
    json.dump(RES, f, indent=1)
print(f"\nwrote {outp}")
print("DONE (anomaly_zoo)")

"""
fitted_fusion.py — Phase 5's LAST open item: run the fitted fuser the spec asks
for, so "blocked by THE FUSION WALL" stops being an argument and becomes a
RESULT with a number.

WHY THIS EXISTS
---------------
`conference_roadmap.md` Phase 5 specifies *"interpretable logistic fusion over
all signals (legitimately trainable under the new split)."* The project has
never run it. What it has is `fusion_beaconlike.py` — a **two-channel special
case** (CNN log-odds + the BeaconLike behaviour) that returned coefficients
`[2.35, 0.02]`, and the paper outline currently generalises from that one
experiment to *"structurally impossible here."*

**Generalising a blocker from a special case is the same defect class this
project keeps retracting**, just pointed at a negative claim instead of a
positive one. Either the fitted fuser fails on the real channel set, in which
case the blocker is measured and citable, or it does not, in which case the
outline is wrong and must be corrected. Both outcomes are worth the run.

THE FUSION WALL, STATED PRECISELY
----------------------------------
The paper split puts all six zero-day families in **test only**. A fitted
combiner must be fitted on **validation**, which therefore contains **benign +
known attacks and no zero-day flows whatsoever**. So the combiner optimises
"separate benign from KNOWN attacks" and is then asked to rank a class it has
had no opportunity to weight for. Any channel whose value is *specifically* on
novel classes is invisible to the fitting objective.

WHICH CHANNELS, AND WHY THE KG IS NOT ONE OF THEM
--------------------------------------------------
Fittable here: **CNN** (1 - p(BENIGN)) and **autoencoder** (per-row
reconstruction MSE). Both score any array, so both produce validation scores.

🔴 **The KG is excluded, and the exclusion is itself a result.** `kg.py`'s
burstiness score is defined by streaming the **test** set into 20 windows —
there is no validation-side KG score at all, not as an oversight but by
construction. **So the one channel that demonstrably helps (+0.0527 macro,
3/3 seeds) is the one a fitted combiner structurally cannot weight.** That
sentence is the fusion wall in its sharpest form and it does not depend on any
number below.

PRE-REGISTERED PREDICTIONS (written and committed before the first run)
------------------------------------------------------------------------
F1  **The fitted fuser puts nearly all weight on the CNN and ~0 on the
    autoencoder.** On validation the CNN is near-perfect on known classes
    (99.8 % multiclass) and the AE adds nothing there, so the AE's coefficient
    should be small or negative. Same shape as `fusion_beaconlike.py`'s
    `[2.35, 0.02]`, but on the real anomaly channel rather than one behaviour.

F2  **The fitted fuser therefore lands at or near CNN-alone on macro zero-day,
    and LOSES to parameter-free equal-weight rank fusion of the SAME two
    channels.** Equal weights are the only way to retain the AE's contribution,
    and the fitting data cannot teach that weight.

F3  **The gap is concentrated on Bot** — the family the AE is comparatively good
    at (AE 0.1291 n=6 vs CNN ~0.03). Fitted-fusion Bot should sit near the
    CNN's; equal-weight rank fusion's should sit materially above it.

F4  **FALSIFIER, stated in advance:** if the fitted fuser matches or beats
    equal-weight rank fusion on macro zero-day, the fusion wall as written is
    wrong, `paper_outline.md` §5's "structurally impossible" row must be
    retracted, and Phase 5's blocker claim goes with it.

WHAT THIS RUN IS NOT
--------------------
Not a claim that no fitted combiner can ever work — only that one fitted on a
zero-day-free validation set, over the channels that can produce validation
scores, does not. LOCO (manufacture synthetic zero-day by holding out a known
class) remains the untried alternative and was deprioritised on separate
grounds: no known class in CIC-IDS2017 beacons, so the rotation is predictably
null for Bot.

Run:  scripts/run_long.sh fitted_fusion.py
Out:  outputs/metadata/fitted_fusion.json
"""
import os
import sys
import json
import pickle

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import paths                                      # noqa: E402
import config                                     # noqa: E402
import features                                   # noqa: E402
import metrics                                    # noqa: E402

cfg = config.get()
SEED = cfg["seed"]
TFM = cfg["protocol"]["feature_transform"]
P = paths.PAPER

import determinism                                # noqa: E402
determinism.enable(SEED)

import tensorflow as tf                           # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from scipy.stats import rankdata                  # noqa: E402

SEEDS = [42, 43, 44]
FAMS = ["Bot", "Web Attack Brute Force", "Web Attack XSS"]


def tag(base, s):
    return base if s == 42 else f"{base}_s{s}"


print("=" * 100)
print("PHASE 5 - THE FITTED FUSER  (the blocker, measured rather than argued)")
print("=" * 100)

# ------------------------------------------------------------------ data ----
Xtr_raw = np.load(os.path.join(P, "X_train.npy"))
Xva_raw = np.load(os.path.join(P, "X_val.npy"))
Xte_raw = np.load(os.path.join(P, "X_test.npy"))
yva_mc = np.load(os.path.join(P, "y_val_mc.npy"), allow_pickle=True)
yte_mc = np.load(os.path.join(P, "y_test_mc.npy"), allow_pickle=True)
zero_day = set(np.load(os.path.join(P, "zero_day_classes.npy"),
                       allow_pickle=True).tolist())

# Transform + scale exactly as cnn_paper.py AND autoencoder_paper.py do it:
# fit on ALL of train, after the configured transform. Both scripts share this
# convention deliberately (autoencoder_paper.py notes it is baselines.py's), so
# one scaler serves both channels here.
Xtr = features.transform(Xtr_raw, TFM)
Xva = features.transform(Xva_raw, TFM)
Xte = features.transform(Xte_raw, TFM)
scaler = StandardScaler().fit(Xtr)
Xva_s = scaler.transform(Xva).astype(np.float32)
Xte_s = scaler.transform(Xte).astype(np.float32)
nfeat = Xte_s.shape[1]

# THE WALL, ASSERTED IN CODE RATHER THAN ASSUMED: validation must contain no
# zero-day flow. If this ever fires, every "fitted on zero-day-free data" claim
# in the project is void and the run must stop.
zd_in_val = int(np.isin(yva_mc, list(zero_day)).sum())
assert zd_in_val == 0, f"validation contains {zd_in_val} zero-day flows -- the wall is not what we think"
print(f"val {Xva_s.shape} | test {Xte_s.shape} | zero-day flows in val: {zd_in_val}  (asserted)")

y_val_bin = (yva_mc != "BENIGN").astype(int)
print(f"fitting target on val: benign {int((y_val_bin == 0).sum()):,} vs "
      f"KNOWN attack {int(y_val_bin.sum()):,}  (no zero-day available, by construction)")


def score_cnn(s, X):
    """1 - p(BENIGN), matching cnn_paper.py's p_attack."""
    m = tf.keras.models.load_model(
        os.path.join(paths.MODELS, f"{tag('cnn_paper', s)}.keras"), compile=False)
    enc_path = os.path.join(paths.MODELS,
                            "label_encoder_paper.pkl" if s == 42
                            else f"label_encoder_paper_s{s}.pkl")
    with open(enc_path, "rb") as fh:
        ben = list(pickle.load(fh).classes_).index("BENIGN")
    p = m.predict(X.reshape(-1, nfeat, 1), batch_size=1024, verbose=0)
    return (1.0 - p[:, ben]).astype(np.float64)


def score_ae(s, X):
    """Per-row reconstruction MSE, matching autoencoder_paper.py."""
    m = tf.keras.models.load_model(
        os.path.join(paths.MODELS, f"{tag('autoencoder_paper', s)}.keras"), compile=False)
    rec = m.predict(X, batch_size=1024, verbose=0)
    return np.mean((X - rec) ** 2, axis=1).astype(np.float64)


def macro(scores):
    r = metrics.evaluate(yte_mc, scores, zero_day, fpr=0.01)
    fam = r["zeroday_family"]
    return ([r["macro"]["pr_auc"]] + [fam[f]["pr_auc"] for f in FAMS],
            r["diagnostics"]["achieved_fpr"])


OUT = {"seeds": SEEDS, "channels": ["cnn", "autoencoder"],
       "kg_excluded_reason": ("kg.py's burstiness score is defined over TEST windows; "
                              "there is no validation-side KG score by construction, so a "
                              "fitted combiner cannot weight the one channel that helps"),
       "n_zero_day_in_val": zd_in_val, "per_seed": {}}

rows = {"cnn": [], "autoencoder": [], "fitted": [], "rank_equal": []}
coefs = []

for s in SEEDS:
    print("\n" + "-" * 100)
    print(f"SEED {s}")
    print("-" * 100)
    cv, ct = score_cnn(s, Xva_s), score_cnn(s, Xte_s)
    av, at = score_ae(s, Xva_s), score_ae(s, Xte_s)

    # Standardise each channel on VALIDATION so the two coefficients are on a
    # comparable scale and F1 is readable. Fitting statistics come from val
    # only -- test is never touched by the fit.
    cs = StandardScaler().fit(np.c_[cv, av])
    Zv, Zt = cs.transform(np.c_[cv, av]), cs.transform(np.c_[ct, at])

    lr = LogisticRegression(max_iter=2000, random_state=s).fit(Zv, y_val_bin)
    w = lr.coef_[0]
    fitted_test = lr.decision_function(Zt)
    coefs.append(w.tolist())

    # The parameter-free comparator, exactly fusion_multi.py's operation over
    # the SAME two channels: per-channel rank, then equal-weight mean.
    n = len(ct)
    rank_eq = np.mean([rankdata(ct) / n, rankdata(at) / n], axis=0)

    per = {}
    for name, sc in (("cnn", ct), ("autoencoder", at),
                     ("fitted", fitted_test), ("rank_equal", rank_eq)):
        vals, afpr = macro(sc)
        rows[name].append(vals)
        per[name] = {"macro": vals[0], "bot": vals[1], "webbf": vals[2],
                     "xss": vals[3], "achieved_fpr": afpr}
    per["coefficients"] = {"cnn": float(w[0]), "autoencoder": float(w[1]),
                           "intercept": float(lr.intercept_[0]),
                           "ae_share_of_abs_weight": float(
                               abs(w[1]) / (abs(w[0]) + abs(w[1])))}
    OUT["per_seed"][str(s)] = per

    print(f"  coefficients (standardised): cnn {w[0]:+.4f}   autoencoder {w[1]:+.4f}"
          f"   -> AE holds {per['coefficients']['ae_share_of_abs_weight']:.1%} of |weight|")
    for name in ("cnn", "autoencoder", "fitted", "rank_equal"):
        p = per[name]
        print(f"  {name:12s} macro {p['macro']:.4f} | Bot {p['bot']:.4f} "
              f"WebBF {p['webbf']:.4f} XSS {p['xss']:.4f}")

# ------------------------------------------------------------- aggregate ----
print("\n" + "=" * 100)
print(f"MEAN OVER {len(SEEDS)} SEEDS")
print("=" * 100)
print(f"{'channel':14s} {'macro':>9s} {'range':>19s} {'Bot':>9s} {'WebBF':>9s} {'XSS':>9s}")
agg = {}
for name in ("cnn", "autoencoder", "fitted", "rank_equal"):
    a = np.array(rows[name])
    agg[name] = {"macro": float(a[:, 0].mean()),
                 "macro_min": float(a[:, 0].min()), "macro_max": float(a[:, 0].max()),
                 "bot": float(a[:, 1].mean()), "webbf": float(a[:, 2].mean()),
                 "xss": float(a[:, 3].mean())}
    m = agg[name]
    print(f"{name:14s} {m['macro']:>9.4f} [{m['macro_min']:.4f}, {m['macro_max']:.4f}] "
          f"{m['bot']:>9.4f} {m['webbf']:>9.4f} {m['xss']:>9.4f}")
OUT["mean_over_seeds"] = agg

# PAIRED per-seed deltas. The 0.0222 noise floor is the SD of an ABSOLUTE
# number; over shared seeds that common variance cancels, so the paired
# difference and its direction-consistency are the right criterion -- the
# lesson figure 4 taught on 2026-08-10.
d_fit_rank = np.array(rows["fitted"])[:, 0] - np.array(rows["rank_equal"])[:, 0]
d_fit_cnn = np.array(rows["fitted"])[:, 0] - np.array(rows["cnn"])[:, 0]
d_rank_cnn = np.array(rows["rank_equal"])[:, 0] - np.array(rows["cnn"])[:, 0]
OUT["paired_deltas"] = {
    "fitted_minus_rank_equal": {"per_seed": d_fit_rank.tolist(),
                                "mean": float(d_fit_rank.mean()),
                                "sd": float(d_fit_rank.std(ddof=1)),
                                "seeds_negative": int((d_fit_rank < 0).sum())},
    "fitted_minus_cnn": {"per_seed": d_fit_cnn.tolist(), "mean": float(d_fit_cnn.mean()),
                         "seeds_positive": int((d_fit_cnn > 0).sum())},
    "rank_equal_minus_cnn": {"per_seed": d_rank_cnn.tolist(), "mean": float(d_rank_cnn.mean()),
                             "seeds_positive": int((d_rank_cnn > 0).sum())},
}
print(f"\npaired  fitted - rank_equal : {d_fit_rank.mean():+.4f}  "
      f"per-seed {np.round(d_fit_rank, 4).tolist()}  ({int((d_fit_rank < 0).sum())}/3 negative)")
print(f"paired  fitted - cnn        : {d_fit_cnn.mean():+.4f}  "
      f"per-seed {np.round(d_fit_cnn, 4).tolist()}")
print(f"paired  rank_equal - cnn    : {d_rank_cnn.mean():+.4f}  "
      f"per-seed {np.round(d_rank_cnn, 4).tolist()}")

# ------------------------------------------------------------- verdicts ----
ae_share = float(np.mean([abs(c[1]) / (abs(c[0]) + abs(c[1])) for c in coefs]))
V = {
    "F1_fitted_ignores_the_anomaly_channel": {
        "mean_ae_share_of_abs_weight": ae_share, "threshold": 0.15,
        "coefficients_per_seed": coefs,
        "confirmed": bool(ae_share < 0.15)},
    "F2_fitted_loses_to_parameter_free": {
        "mean_delta": float(d_fit_rank.mean()),
        "seeds_negative": int((d_fit_rank < 0).sum()),
        "confirmed": bool(d_fit_rank.mean() < 0 and (d_fit_rank < 0).sum() == len(SEEDS))},
    "F3_gap_concentrated_on_bot": {
        "fitted_bot": agg["fitted"]["bot"], "rank_equal_bot": agg["rank_equal"]["bot"],
        "cnn_bot": agg["cnn"]["bot"],
        "confirmed": bool(agg["rank_equal"]["bot"] > agg["fitted"]["bot"])},
    "F4_falsifier_fitted_wins": {
        "triggered": bool(d_fit_rank.mean() >= 0),
        "note": ("if triggered, the fusion wall as written is wrong and "
                 "paper_outline.md 5's 'structurally impossible' row must be retracted")},
}
OUT["predictions"] = V
print("\n" + "=" * 100)
print("PRE-REGISTERED PREDICTIONS")
print("=" * 100)
for k, v in V.items():
    if k.startswith("F4"):
        print(f"  {'TRIGGERED' if v['triggered'] else 'not triggered':14s}  {k}")
    else:
        print(f"  {'CONFIRMED' if v['confirmed'] else 'FALSIFIED':14s}  {k}")
print(f"\n  autoencoder holds {ae_share:.1%} of the fitted combiner's absolute weight")

out_path = os.path.join(paths.METADATA, "fitted_fusion.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(OUT, f, indent=2)
print(f"\nwrote {out_path}")
print("DONE")

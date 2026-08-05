"""
operational.py — Phase 7.5 Tier 1: the metrics that decide whether automated
response is SAFE. All four Tier-1 items in one pass.

WHY THIS EXISTS
---------------
**PR-AUC is the wrong target for a response engine.** It summarises *ranking
quality across all thresholds*; a response engine acts at **one threshold**. What
decides whether automated response is safe is **precision at that operating
point** — a false positive means auto-blocking legitimate traffic.

A system can post macro 0.69 and still auto-block at 40 % precision, which is
operationally unusable, and **no metric currently in this project would warn
you.** Phase 7.5 gates Phase R for exactly this reason.

THE FOUR TIER-1 ITEMS (docs/STATUS.md -> "PHASE 7.5")
-----------------------------------------------------
1. **Ship the ensemble, not a single run.** The measured noise floor is SD 0.0222
   (CV 3.6 %) at fixed seed. You cannot deploy a model whose score swings 0.06
   between identical trainings. The ensemble is the *reproducible* baseline.
2. **Calibration** — isotonic/Platt fitted on KNOWN CLASSES ONLY, plus ECE and
   reliability curves. Without it `p = 0.9` does not mean 90 %, and every
   threshold is arbitrary.
3. **Precision @ alert budget** — *"at N alerts, what fraction are real?"* This
   predicts response accuracy; PR-AUC does not.
4. **Selective prediction / abstention** — precision-vs-coverage. The engine
   should NOT act when uncertain: find the band where precision is high enough to
   auto-act, defer the rest to a human.

CALIBRATION IS FITTED ON VALIDATION, WHICH IS ZERO-DAY-FREE BY CONSTRUCTION
---------------------------------------------------------------------------
The paper split puts all 6 zero-day families in test only. Fitting the calibrator
on VAL therefore uses **no zero-day information at all** — it is the strictest
legitimate choice, stricter than fitting on known-class test rows (which would at
least touch test benign). This mirrors the fusion wall's constraint rather than
evading it.

PRE-REGISTERED PREDICTIONS (written before the first run — see git history)
---------------------------------------------------------------------------
P1  The ensemble beats the MEAN single run but NOT the max single run, because
    0.6446 is the max of 11 draws from a noisy process, not a typical result.
    STATUS already reports 0.6356; this should reproduce it.

P2  Calibration fitted on known classes will be MUCH worse on zero-day flows than
    on known-class flows (higher ECE on the zero-day subset). Rationale: the
    closed-set transfer failure. A calibrator maps a score to a probability using
    the score->outcome relationship it saw; for a class the model has never seen,
    that relationship does not hold.

P3  Precision at a small alert budget will be high overall but the alerts will be
    almost entirely KNOWN attacks, with near-zero zero-day recall — because the
    CNN's Bot ranking is noise (cross-seed rho = -0.090) and 100 % of Bot flows
    are confidently classified BENIGN.

P4  **Abstention will NOT rescue zero-day.** This is the sharp one. Abstention
    keys on *confidence*, and the Bot failure analysis established that the CNN is
    confidently WRONG on Bot (100 % argmax BENIGN, mean p(BENIGN) = 0.9984).
    Confident-and-wrong is precisely the case a confidence-based abstention rule
    cannot catch. If zero-day precision improves materially as coverage drops,
    P4 is falsified and the Bot mechanism needs revisiting.

Run:  python scripts/operational.py
Out:  outputs/metadata/operational.json
      outputs/figures/operational.png
"""
import os
import sys
import json
import glob
import pickle

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                    # noqa: E402
import metrics                                  # noqa: E402
import features                                 # noqa: E402
import config                                   # noqa: E402

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                 # noqa: E402

cfg = config.get()
P, PR, MD = paths.PAPER, paths.PREDICTIONS, paths.METADATA
TFM = cfg["protocol"]["feature_transform"]

# Alert budgets to report. The test set is 114,658 flows drawn from a 5-day
# capture, so "per day" is not literal -- these are top-N budgets and are
# labelled as such.
BUDGETS = [50, 100, 250, 500, 1000, 2500, 5000, 10000, 25000, 50000]
COVERAGES = [1.00, 0.95, 0.90, 0.75, 0.50, 0.25, 0.10]
N_BINS = 15

y_te = np.load(os.path.join(P, "y_test_mc.npy"), allow_pickle=True)
zero_day = set(np.load(os.path.join(P, "zero_day_classes.npy"), allow_pickle=True).tolist())

is_benign = y_te == "BENIGN"
is_zd = np.isin(y_te, list(zero_day))
is_known_atk = ~is_benign & ~is_zd
y_bin = (~is_benign).astype(int)

print("=" * 100)
print("PHASE 7.5 TIER 1 — OPERATIONAL READINESS")
print("=" * 100)
print(f"test flows {len(y_te):,} | benign {is_benign.sum():,} | "
      f"known attacks {is_known_atk.sum():,} | zero-day {is_zd.sum():,} "
      f"({is_zd.mean():.2%})")

OUT = {"n_test": int(len(y_te)),
       "n_benign": int(is_benign.sum()),
       "n_known_attack": int(is_known_atk.sum()),
       "n_zero_day": int(is_zd.sum())}


# =============================================================================
# ITEM 1 — SHIP THE ENSEMBLE, NOT A SINGLE RUN
# =============================================================================
print("\n" + "=" * 100)
print("ITEM 1 — ENSEMBLE vs SINGLE RUN  (the noise floor is SD 0.0222; a single")
print("         run is not a deployable artifact)")
print("=" * 100)

# Every CNN run that saved a probability-scale test prediction. Deliberately the
# RAW p_attack files, not the _logodds ones: log-odds is a rank-preserving
# rescale used for PR-AUC hygiene, but averaging probabilities and averaging
# log-odds are different ensembles, and probability is what a deployed system
# would actually average.
#
# ⚠️ `cnn_auxhead_*` is EXCLUDED and the exclusion is load-bearing. It matches the
# `cnn_*` glob but is a DIFFERENT ARCHITECTURE (the auxiliary behaviour-prediction
# head, macro 0.5797), not another run of the same model. Ensembling it would
# silently answer a different question -- "does a heterogeneous ensemble help?" --
# while being reported as the reproducibility fix for a single architecture.
# Caught on first run: the glob returned 12 files, not the 11 STATUS reports.
EXCLUDE = ("auxhead",)
cnn_files = sorted(f for f in glob.glob(os.path.join(PR, "y_prob_cnn_*_test.npy"))
                   if "logodds" not in os.path.basename(f)
                   and not any(x in os.path.basename(f) for x in EXCLUDE))
print(f"found {len(cnn_files)} CNN runs with probability-scale predictions:")

singles, stack = {}, []
for f in cnn_files:
    name = os.path.basename(f).replace("y_prob_", "").replace("_test.npy", "")
    s = np.load(f)
    r = metrics.evaluate(y_te, s, zero_day, fpr=0.01)
    singles[name] = r["macro"]["pr_auc"]
    stack.append(s)
    print(f"  {name:22s} macro {r['macro']['pr_auc']:.4f}")

stack = np.vstack(stack)
vals = np.array(list(singles.values()))

# Two ensembles. Probability-mean is the obvious one; rank-mean is the
# scale-free variant that fusion_kg.py established works here.
ens_prob = stack.mean(axis=0)
ranks = np.vstack([np.argsort(np.argsort(s)) / (len(s) - 1) for s in stack])
ens_rank = ranks.mean(axis=0)

r_prob = metrics.evaluate(y_te, ens_prob, zero_day, fpr=0.01)
r_rank = metrics.evaluate(y_te, ens_rank, zero_day, fpr=0.01)
SD = 0.0222                                     # measured noise floor

print(f"\n  {'single-run mean':28s} {vals.mean():.4f}   (n={len(vals)}, SD {vals.std(ddof=1):.4f})")
print(f"  {'single-run MAX':28s} {vals.max():.4f}   <- the number usually quoted")
print(f"  {'single-run min':28s} {vals.min():.4f}")
print(f"  {'ENSEMBLE (prob-mean)':28s} {r_prob['macro']['pr_auc']:.4f}   "
      f"{(r_prob['macro']['pr_auc'] - vals.mean()) / SD:+.2f} SD vs mean single run")
print(f"  {'ENSEMBLE (rank-mean)':28s} {r_rank['macro']['pr_auc']:.4f}   "
      f"{(r_rank['macro']['pr_auc'] - vals.mean()) / SD:+.2f} SD vs mean single run")

beats_mean = r_prob["macro"]["pr_auc"] > vals.mean()
beats_max = r_prob["macro"]["pr_auc"] > vals.max()
print(f"\n  P1 (beats mean, not max): "
      f"{'CONFIRMED' if beats_mean and not beats_max else 'FALSIFIED'} "
      f"(beats mean={beats_mean}, beats max={beats_max})")
print("  The ensemble's real argument is not the +delta -- it is that it is"
      " REPRODUCIBLE.\n  A single run is a draw; the ensemble is an artifact.")

OUT["ensemble"] = {
    "n_runs": len(vals),
    "singles": {k: float(v) for k, v in singles.items()},
    "single_mean": float(vals.mean()), "single_sd": float(vals.std(ddof=1)),
    "single_max": float(vals.max()), "single_min": float(vals.min()),
    "ensemble_prob_mean": float(r_prob["macro"]["pr_auc"]),
    "ensemble_rank_mean": float(r_rank["macro"]["pr_auc"]),
    "p1_confirmed": bool(beats_mean and not beats_max),
}


# =============================================================================
# ITEM 2 — CALIBRATION, FITTED ON VALIDATION (ZERO-DAY-FREE BY CONSTRUCTION)
# =============================================================================
print("\n" + "=" * 100)
print("ITEM 2 — CALIBRATION  (fitted on VAL, which contains no zero-day by")
print("         construction, then measured separately on known vs zero-day)")
print("=" * 100)


def ece(y, p, n_bins=N_BINS):
    """Expected Calibration Error: |confidence - accuracy| weighted by bin size."""
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    idx = np.clip(np.digitize(p, edges[1:-1]), 0, n_bins - 1)
    tot, curve = 0.0, []
    for b in range(n_bins):
        m = idx == b
        if not m.any():
            curve.append((float(edges[b] + edges[b + 1]) / 2, None, 0))
            continue
        conf, acc = float(p[m].mean()), float(y[m].mean())
        tot += m.mean() * abs(conf - acc)
        curve.append((conf, acc, int(m.sum())))
    return float(tot), curve


# Regenerate val probabilities from the seed-42 reference model. Cheap
# (110,475 rows, CPU) and avoids storing another artifact.
print("regenerating validation probabilities from models/cnn_paper.keras ...")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
import tensorflow as tf                          # noqa: E402

X_val = features.transform(np.load(os.path.join(P, "X_val.npy")), TFM)
with open(os.path.join(paths.MODELS, "scaler_paper.pkl"), "rb") as f:
    scaler = pickle.load(f)
with open(os.path.join(paths.MODELS, "label_encoder_paper.pkl"), "rb") as f:
    le = pickle.load(f)
benign_idx = list(le.classes_).index("BENIGN")

X_val = scaler.transform(X_val).reshape(-1, X_val.shape[1], 1)
model = tf.keras.models.load_model(os.path.join(paths.MODELS, "cnn_paper.keras"),
                                   compile=False)
p_val = 1.0 - model.predict(X_val, batch_size=1024, verbose=0)[:, benign_idx]
y_val = np.load(os.path.join(P, "y_val_mc.npy"), allow_pickle=True)
y_val_bin = (y_val != "BENIGN").astype(int)
assert not np.isin(y_val, list(zero_day)).any(), "zero-day leaked into val!"
print(f"  val {len(p_val):,} flows, prevalence {y_val_bin.mean():.3f} — "
      f"confirmed zero-day-free")

p_test = np.load(os.path.join(PR, "y_prob_cnn_paper_test.npy"))

from sklearn.isotonic import IsotonicRegression          # noqa: E402
from sklearn.linear_model import LogisticRegression      # noqa: E402

iso = IsotonicRegression(out_of_bounds="clip").fit(p_val, y_val_bin)
eps = 1e-7
logit_val = np.log(np.clip(p_val, eps, 1 - eps) / (1 - np.clip(p_val, eps, 1 - eps)))
platt = LogisticRegression().fit(logit_val.reshape(-1, 1), y_val_bin)

logit_test = np.log(np.clip(p_test, eps, 1 - eps) / (1 - np.clip(p_test, eps, 1 - eps)))
cal = {
    "uncalibrated": p_test,
    "platt": platt.predict_proba(logit_test.reshape(-1, 1))[:, 1],
    "isotonic": iso.predict(p_test),
}

# Subsets. "known" = benign + known attacks (what the calibrator was fitted for);
# "zero-day" = benign + zero-day (what it was never shown).
subsets = {"all": np.ones(len(y_te), bool),
           "known-class": is_benign | is_known_atk,
           "zero-day": is_benign | is_zd}

print(f"\n  {'ECE (lower=better)':22s} {'all':>10s} {'known-class':>13s} {'zero-day':>10s}"
      f" {'zd/known':>10s}")
OUT["calibration"] = {"n_bins": N_BINS, "fitted_on": "validation (zero-day-free)",
                      "methods": {}}
curves = {}
for name, p in cal.items():
    row, e = {}, {}
    for sname, m in subsets.items():
        v, c = ece(y_bin[m], p[m])
        e[sname] = v
        if sname == "all":
            curves[name] = c
    ratio = e["zero-day"] / e["known-class"] if e["known-class"] > 0 else float("nan")
    print(f"  {name:22s} {e['all']:>10.4f} {e['known-class']:>13.4f} "
          f"{e['zero-day']:>10.4f} {ratio:>10.1f}x")
    OUT["calibration"]["methods"][name] = {"ece": e, "zd_over_known": float(ratio)}

best = min(cal, key=lambda k: OUT["calibration"]["methods"][k]["ece"]["known-class"])
worst_ratio = max(OUT["calibration"]["methods"][k]["zd_over_known"] for k in cal)
print(f"\n  best on known-class ECE: {best}")
print(f"  P2 (zero-day calibration much worse than known-class): "
      f"{'CONFIRMED' if worst_ratio > 2 else 'NOT CONFIRMED'} "
      f"(worst zd/known ratio {worst_ratio:.1f}x)")
OUT["calibration"]["p2_confirmed"] = bool(worst_ratio > 2)
OUT["calibration"]["best_known_class"] = best


# =============================================================================
# ITEM 3 — PRECISION @ ALERT BUDGET
# =============================================================================
print("\n" + "=" * 100)
print("ITEM 3 — PRECISION @ ALERT BUDGET  (the operational metric: at N alerts,")
print("         what fraction are real? PR-AUC does not answer this)")
print("=" * 100)

CHANNELS = {
    "CNN": p_test,
    "CNN ensemble": ens_prob,
    "CNN + KG fusion": None,       # filled below if present
    "KG (causal)": None,
}
for key, fn in [("CNN + KG fusion", "y_prob_fusion_cnn_kg_test.npy"),
                ("KG (causal)", "y_prob_kg_causal_test.npy")]:
    fp = os.path.join(PR, fn)
    CHANNELS[key] = np.load(fp) if os.path.exists(fp) else None
CHANNELS = {k: v for k, v in CHANNELS.items() if v is not None}

OUT["alert_budget"] = {}
for cname, s in CHANNELS.items():
    order = np.argsort(-s)
    print(f"\n  {cname}")
    print(f"    {'budget':>8s} {'precision':>10s} {'  of which':>12s} {'zero-day':>10s} "
          f"{'zd recall':>10s}")
    print(f"    {'(top-N)':>8s} {'(any attack)':>10s} {'known':>12s} {'in alerts':>10s} {'':>10s}")
    rows = []
    for n in BUDGETS:
        sel = order[:n]
        prec = float(y_bin[sel].mean())
        n_known = int(is_known_atk[sel].sum())
        n_zd = int(is_zd[sel].sum())
        zd_rec = n_zd / max(1, is_zd.sum())
        rows.append({"budget": n, "precision": prec, "n_known": n_known,
                     "n_zero_day": n_zd, "zero_day_recall": float(zd_rec)})
        print(f"    {n:>8,} {prec:>10.3f} {n_known:>12,} {n_zd:>10,} {zd_rec:>10.4f}")
    OUT["alert_budget"][cname] = rows

# How deep must an analyst go before zero-day flows start appearing at all? This
# is the number a SOC actually cares about, and no PR-AUC reports it.
print("\n  DEPTH REQUIRED FOR ZERO-DAY RECALL  (how far down the ranking before a")
print("  novel attack surfaces at all — the question an alert budget really asks)")
print(f"    {'channel':18s} {'@10% zd':>10s} {'@25% zd':>10s} {'@50% zd':>10s}"
      f"  {'(as % of the 114,658 test flows)':>10s}")
OUT["zero_day_depth"] = {}
for cname, s in CHANNELS.items():
    order = np.argsort(-s)
    zd_cum = np.cumsum(is_zd[order])
    need = {}
    for frac in (0.10, 0.25, 0.50):
        tgt = frac * is_zd.sum()
        hit = np.argmax(zd_cum >= tgt) + 1 if (zd_cum >= tgt).any() else None
        need[frac] = int(hit) if hit else None
    OUT["zero_day_depth"][cname] = {str(k): v for k, v in need.items()}
    fmt = lambda v: f"{v:,} ({v/len(y_te):.0%})" if v else "never"   # noqa: E731
    print(f"    {cname:18s} {fmt(need[0.10]):>10s} {fmt(need[0.25]):>10s} "
          f"{fmt(need[0.50]):>10s}")

# P3 checks the CNN specifically: high precision, but the alerts are known attacks.
cnn_rows = OUT["alert_budget"]["CNN"]
r100 = next(r for r in cnn_rows if r["budget"] == 100)
p3 = r100["precision"] > 0.9 and r100["zero_day_recall"] < 0.05
print(f"\n  P3 (high precision, but alerts are known attacks): "
      f"{'CONFIRMED' if p3 else 'NOT CONFIRMED'} — at 100 alerts the CNN is "
      f"{r100['precision']:.1%} precise, {r100['n_zero_day']} of them zero-day "
      f"({r100['zero_day_recall']:.2%} of all zero-day flows)")
OUT["alert_budget_p3_confirmed"] = bool(p3)


# =============================================================================
# ITEM 4 — SELECTIVE PREDICTION / ABSTENTION
# =============================================================================
print("\n" + "=" * 100)
print("ITEM 4 — SELECTIVE PREDICTION  (precision vs coverage: where can the engine")
print("         auto-act, and where must it defer to a human?)")
print("=" * 100)
print("  Confidence = |logit(p) - logit(threshold)|, i.e. the MARGIN from the")
print("  decision boundary. Abstain on the least confident tail; the operating")
print("  threshold is the 1%-FPR point on benign, as everywhere else.")

# 🔴 ISOTONIC WINS ECE BUT IS UNUSABLE AS AN OPERATING POINT, and this is an
# operational finding in its own right. Isotonic regression is a STEP function:
# it collapses the score into a small number of distinct values, so the 1%-FPR
# quantile lands inside a huge tie block and the threshold fires on everything
# tied with it. First run of this script did exactly that -- achieved FPR 0.70
# against a 0.01 target. Platt is a monotone CONTINUOUS transform of the raw
# score: it preserves the ranking exactly, has no ties, and therefore has a real
# operating point. **Calibrate with isotonic for reporting probabilities;
# threshold with Platt.** metrics.py already flags this failure mode for model
# scores (`largest_tie_frac`); it applies to calibrators too.
res = {k: len(np.unique(v)) for k, v in cal.items()}
print(f"\n  distinct score values: " +
      " | ".join(f"{k} {v:,}" for k, v in res.items()))
OUT["calibration"]["distinct_values"] = {k: int(v) for k, v in res.items()}
if res["isotonic"] < 0.01 * len(y_te):
    print(f"  -> isotonic has {res['isotonic']:,} distinct values on {len(y_te):,} "
          f"flows: TOO TIED for a threshold. Using platt for the operating point.")
thr_method = "platt" if res["platt"] > res["isotonic"] else best

p_cal = cal[thr_method]
thr = float(np.quantile(p_cal[is_benign], 0.99))
print(f"  operating point from '{thr_method}': thr={thr:.6f}, "
      f"achieved benign FPR {float((p_cal[is_benign] >= thr).mean()):.4f} "
      f"(target 0.0100)")

# ⚠️ CONFIDENCE IS THE MARGIN FROM THE DECISION THRESHOLD, NOT FROM 0.5.
# The first version used |p - 0.5|, which is wrong whenever the operating point
# is not 0.5 -- and here it is 0.000049 (the 1%-FPR point). Under |p - 0.5| the
# "most confident" flows are the most confidently BENIGN, so shrinking coverage
# threw away every attack and recall collapsed to 0.035 for reasons that had
# nothing to do with selective prediction. The margin is measured in log-odds so
# it is scaled sensibly across the range rather than crushed near p=0.
_lg = lambda v: np.log(np.clip(v, eps, 1 - eps) / (1 - np.clip(v, eps, 1 - eps)))  # noqa: E731
conf = np.abs(_lg(p_cal) - _lg(thr))
pred = (p_cal >= thr).astype(int)
order_conf = np.argsort(-conf)

print(f"\n  {'coverage':>9s} {'precision':>10s} {'recall':>9s} {'FPR':>8s} "
      f"{'benign kept':>12s} {'zd precision':>13s} {'zd recall':>10s}")
print("  (FPR is conditional on the COVERED set — at low coverage few benign flows")
print("   remain, so it saturates. Read it with the 'benign kept' denominator.)")
OUT["abstention"] = {"threshold": thr, "confidence": "|p-0.5|",
                     "calibration_for_threshold": thr_method,
                     "calibration_best_ece": best, "curve": []}
for c in COVERAGES:
    k = max(1, int(round(c * len(conf))))
    sel = order_conf[:k]
    fired = sel[pred[sel] == 1]
    prec = float(y_bin[fired].mean()) if len(fired) else float("nan")
    rec = float(y_bin[fired].sum() / max(1, y_bin.sum()))
    fpr_ = float(is_benign[fired].sum() / max(1, is_benign[sel].sum()))
    zd_prec = float(is_zd[fired].mean()) if len(fired) else float("nan")
    zd_rec = float(is_zd[fired].sum() / max(1, is_zd.sum()))
    n_ben = int(is_benign[sel].sum())
    OUT["abstention"]["curve"].append(
        {"coverage": c, "n_covered": int(k), "n_alerts": int(len(fired)),
         "n_benign_covered": n_ben, "precision": prec, "recall": rec, "fpr": fpr_,
         "zd_precision": zd_prec, "zd_recall": zd_rec})
    print(f"  {c:>9.0%} {prec:>10.3f} {rec:>9.3f} {fpr_:>8.4f} {n_ben:>12,} "
          f"{zd_prec:>13.4f} {zd_rec:>10.4f}")

curve = OUT["abstention"]["curve"]
full = curve[0]
# Test P4 against the BEST point on the curve, not the endpoint. Using the
# endpoint would pick whichever comparison flatters the prediction -- the exact
# error class this project has retracted five findings over.
#
# ⚠️ But only over NON-DEGENERATE coverages. Below ~50% coverage the covered set
# retains 2-125 benign flows out of 55,237, so precision there is computed on a
# denominator too small to mean anything (it is why FPR reads exactly 1.0000).
# Scoring P4 on those points would compare against noise in either direction.
MIN_BENIGN = 1000
usable = [r for r in curve if r["n_benign_covered"] >= MIN_BENIGN]
degenerate = [r["coverage"] for r in curve if r["n_benign_covered"] < MIN_BENIGN]
if degenerate:
    print(f"\n  excluded as degenerate (<{MIN_BENIGN:,} benign flows covered): "
          + ", ".join(f"{c:.0%}" for c in degenerate))
OUT["abstention"]["degenerate_coverages"] = degenerate
bestpt = max(usable, key=lambda r: (r["zd_precision"]
                                    if np.isfinite(r["zd_precision"]) else -1))
zd_gain = bestpt["zd_precision"] - full["zd_precision"]
p4 = zd_gain < 0.05
OUT["abstention"]["zd_precision_full"] = full["zd_precision"]
OUT["abstention"]["zd_precision_best"] = bestpt["zd_precision"]
OUT["abstention"]["zd_precision_best_coverage"] = bestpt["coverage"]
print(f"\n  P4 (abstention does NOT rescue zero-day): "
      f"{'CONFIRMED' if p4 else 'FALSIFIED'} — best zero-day precision anywhere on "
      f"the curve is {bestpt['zd_precision']:.4f} at {bestpt['coverage']:.0%} "
      f"coverage, vs {full['zd_precision']:.4f} at full coverage ({zd_gain:+.4f})")
if p4:
    print("  Mechanism: the CNN is CONFIDENTLY wrong on Bot (100% argmax BENIGN,")
    print("  mean p(BENIGN)=0.9984). A confidence-based rule cannot catch")
    print("  confident-and-wrong -- abstention removes uncertain flows, and Bot is")
    print("  not among them.")
OUT["abstention"]["p4_confirmed"] = bool(p4)

# find the coverage where precision clears common auto-action bars
for bar in (0.95, 0.99):
    ok = [r for r in curve if r["precision"] >= bar]
    best_cov = max((r["coverage"] for r in ok), default=None)
    OUT["abstention"][f"max_coverage_at_precision_{bar}"] = best_cov
    print(f"  max coverage with precision >= {bar:.0%}: "
          f"{'none' if best_cov is None else f'{best_cov:.0%}'}")


# =============================================================================
# FIGURE + PERSIST
# =============================================================================
fig, ax = plt.subplots(1, 3, figsize=(16, 4.6))

ax[0].plot([0, 1], [0, 1], "k--", lw=1, label="perfect")
for name in ("uncalibrated", "platt", "isotonic"):
    pts = [(c, a) for c, a, n in curves[name] if a is not None and n > 50]
    if pts:
        ax[0].plot(*zip(*pts), "o-", ms=4, label=name)
ax[0].set_xlabel("mean predicted p(attack)"), ax[0].set_ylabel("observed fraction")
ax[0].set_title("Reliability (all test flows)"), ax[0].legend(fontsize=8)

# Precision is pinned at ~1.00 for every channel at every budget, so plotting it
# hides the actual finding. What matters operationally is that zero-day recall
# stays at ZERO until the budget reaches ~10-25% of the entire test set.
for cname in CHANNELS:
    rows = OUT["alert_budget"][cname]
    ax[1].plot([r["budget"] for r in rows],
               [r["zero_day_recall"] for r in rows], "o-", ms=4, label=cname)
ax[1].set_xscale("log"), ax[1].set_xlabel("alert budget (top-N of 114,658 flows)")
ax[1].set_ylabel("zero-day recall"), ax[1].set_ylim(-0.02, 1.02)
ax[1].axvspan(50, 1000, color="0.85", zorder=0)
ax[1].text(200, 0.55, "realistic\nSOC budget", ha="center", fontsize=8, color="0.35")
ax[1].set_title("Zero-day recall @ alert budget\n(precision is ~1.00 throughout — "
                "the alerts are known attacks)", fontsize=9)
ax[1].legend(fontsize=8, loc="upper left")

ax[2].plot([r["coverage"] for r in curve], [r["precision"] for r in curve], "o-",
           ms=4, label="all attacks")
ax[2].plot([r["coverage"] for r in curve], [r["zd_precision"] for r in curve], "s-",
           ms=4, label="zero-day only")
ax[2].set_xlabel("coverage"), ax[2].set_ylabel("precision"), ax[2].set_ylim(0, 1.02)
ax[2].invert_xaxis()
ax[2].set_title("Selective prediction"), ax[2].legend(fontsize=8)

fig.suptitle("Phase 7.5 Tier 1 — operational readiness (CNN, paper split)", y=1.02)
fig.tight_layout()
figp = os.path.join(paths.FIGURES, "operational.png")
fig.savefig(figp, dpi=140, bbox_inches="tight")
print(f"\nwrote {figp}")

outp = os.path.join(MD, "operational.json")
with open(outp, "w", encoding="utf-8") as f:
    json.dump(OUT, f, indent=1)
print(f"wrote {outp}")

print("\n" + "=" * 100)
print("PRE-REGISTERED PREDICTIONS")
print("=" * 100)
for k, v in [("P1 ensemble beats mean not max", OUT["ensemble"]["p1_confirmed"]),
             ("P2 zero-day calibration far worse", OUT["calibration"]["p2_confirmed"]),
             ("P3 alerts are known attacks", OUT["alert_budget_p3_confirmed"]),
             ("P4 abstention does not rescue zero-day", OUT["abstention"]["p4_confirmed"])]:
    print(f"  {k:44s} {'CONFIRMED' if v else 'NOT CONFIRMED'}")

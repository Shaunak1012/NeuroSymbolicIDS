"""
ablation.py — Remaining Work #6: does each component earn its place?

CNN -> +LTN -> +KG -> full, at n=3 paired seeds (42/43/44), using the SAME
parameter-free equal-weight rank fusion `fusion_kg.py` established. Nothing is
fitted, so nothing here can be tuned on the test set.

WHY THE LADDER HAS FIVE RUNGS, NOT THREE
-----------------------------------------
"+LTN" is ambiguous in this project and the ambiguity is load-bearing:

  * **LTN control (`ltn_ctrl_w0`)** is the symbolic TRAINER with its axiom weight
    at zero -- a custom training loop, no symbolic content. At n=6 it is
    statistically INDISTINGUISHABLE from the CNN (+0.0140 against a ~0.0256
    threshold), which is what retracted C2.
  * **LTN Ax6 (`ltn_ax6_ratio_w1p0`)** is the actual symbolic pillar: behaviour-
    grounded axioms, `ratio` omega-mode (the only configuration that does not
    collapse on some seeds).

Reporting only one of them would answer a different question than the one asked.
"Does the symbolic pillar earn its place?" is about **axioms**; "does the
symbolic trainer earn its place?" is about the loop. Both rungs are run.

THE RIGHT REFERENCE FOR THESE DELTAS
------------------------------------
The measured noise floor is SD 0.0222 between identical re-trainings. But every
fused variant here is computed **from the same CNN run** as its baseline, so
run-to-run noise is shared by both sides and largely cancels. **The correct
reference is the PAIRED per-seed delta and its consistency across seeds, not the
between-run floor** -- exactly as STATUS records for the CNN+KG fusion entry.
Both are printed; the paired one is the one to cite.

PRE-REGISTERED PREDICTIONS (written before the first run -- see git history)
----------------------------------------------------------------------------
A1  +KG improves macro on 3/3 seeds, reproducing the established +0.0527. If it
    does not reproduce, something in the channel files has drifted.

A2  +LTN(control) changes macro by roughly NOTHING. Rationale: it is a closed-set
    supervised model trained on the same data as the CNN and statistically
    indistinguishable from it, so the two channels are near-redundant and an
    equal-weight rank mean of two correlated channels adds no information.

A3  +LTN(Ax6) does NOT help macro, and does not reliably help Bot either. The
    macro cost of axioms is one of the most robust findings in this project
    (non-overlapping ranges, n=3); the Bot benefit was retracted after
    multi-seeding.

A4  **The FULL system (CNN+LTN+KG) does NOT beat CNN+KG.** This is the sharp
    prediction and the point of the whole exercise. `fusion_multi.py` already
    showed that adding channels under equal weighting dilutes strong ones. If A4
    holds, the honest ablation conclusion is that **only the KG earns its place**
    as a fusion channel -- which is a negative result about the project's own
    architecture and must be reported as such.

Run:  python scripts/ablation.py
Out:  outputs/metadata/ablation.json
"""
import os
import sys
import json
import itertools

import numpy as np
from scipy.stats import rankdata
from sklearn.metrics import average_precision_score

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                    # noqa: E402
import metrics                                  # noqa: E402

P, PR, MD = paths.PAPER, paths.PREDICTIONS, paths.METADATA
SEEDS = [42, 43, 44]
SD = 0.0222                                     # measured noise floor
B = 2000                                        # bootstrap replicates
RNG_SEED = 7
FAMS = ["Bot", "Web Attack Brute Force", "Web Attack XSS"]

yte = np.load(os.path.join(P, "y_test_mc.npy"), allow_pickle=True)
zero_day = set(np.load(os.path.join(P, "zero_day_classes.npy"), allow_pickle=True).tolist())
n = len(yte)

# ---- the four component channels, one file per seed --------------------------
COMPONENTS = {
    "CNN": ["y_prob_cnn_paper_logodds_test.npy",
            "y_prob_cnn_paper_s43_logodds_test.npy",
            "y_prob_cnn_paper_s44_logodds_test.npy"],
    "LTN-ctrl": ["y_prob_ltn_ctrl_w0_logodds_test.npy",
                 "y_prob_ltn_ctrl_w0_s43_logodds_test.npy",
                 "y_prob_ltn_ctrl_w0_s44_logodds_test.npy"],
    "LTN-Ax6": ["y_prob_ltn_ax6_ratio_w1p0_s42_logodds_test.npy",
                "y_prob_ltn_ax6_ratio_w1p0_s43_logodds_test.npy",
                "y_prob_ltn_ax6_ratio_w1p0_s44_logodds_test.npy"],
    "KG": ["y_prob_kg_causal_test.npy",
           "y_prob_kg_s43_causal_test.npy",
           "y_prob_kg_s44_causal_test.npy"],
}

print("=" * 100)
print("ABLATION — CNN -> +LTN -> +KG -> full   (parameter-free rank fusion, n=3 paired seeds)")
print("=" * 100)

CH = {}
for name, files in COMPONENTS.items():
    arrs = []
    for f in files:
        p = os.path.join(PR, f)
        if not os.path.exists(p):
            raise SystemExit(f"missing channel file: {f}")
        arrs.append(np.load(p))
    CH[name] = arrs
    print(f"  loaded {name:10s} {len(arrs)} seeds")


def rk(s):
    """Rank-normalise to [0,1]. Same convention as fusion_kg.py."""
    return rankdata(s) / n


# Rank-normalise once per channel per seed -- ranks are invariant to the
# monotone log-odds rescale, so this is stable.
RK = {k: [rk(a) for a in v] for k, v in CH.items()}

# ---- the ladder --------------------------------------------------------------
# Each rung is an equal-weight rank mean of its components. Equal weight is the
# no-tuning default; any weighting chosen by looking at zero-day performance
# would be fitting on the test set (the fusion wall in another guise).
LADDER = [
    ("CNN",                       ["CNN"]),
    ("CNN + LTN-ctrl",            ["CNN", "LTN-ctrl"]),
    ("CNN + LTN-Ax6",             ["CNN", "LTN-Ax6"]),
    ("CNN + KG",                  ["CNN", "KG"]),
    ("CNN + LTN-Ax6 + KG (FULL)", ["CNN", "LTN-Ax6", "KG"]),
    ("CNN + LTN-ctrl + KG",       ["CNN", "LTN-ctrl", "KG"]),
]

is_benign = yte == "BENIGN"
ben_idx = np.flatnonzero(is_benign)
fam_idx = {f: np.flatnonzero(yte == f) for f in FAMS}


def fuse(parts, si):
    return np.mean([RK[p][si] for p in parts], axis=0)


def macro_fam(scores_by_seed, idx=None):
    """Mean-over-seeds macro + per-family PR-AUC. `idx` allows bootstrap resampling."""
    per_seed_macro, per_fam = [], {f: [] for f in FAMS}
    for s in scores_by_seed:
        vals = []
        for f in FAMS:
            bi, fi = (ben_idx, fam_idx[f]) if idx is None else idx[f]
            y = np.concatenate([np.zeros(len(bi), np.int8), np.ones(len(fi), np.int8)])
            v = average_precision_score(y, np.concatenate([s[bi], s[fi]]))
            vals.append(v)
            per_fam[f].append(v)
        per_seed_macro.append(float(np.mean(vals)))
    return per_seed_macro, {f: float(np.mean(v)) for f, v in per_fam.items()}


RES, fused_by_rung = {}, {}
print(f"\n{'rung':30s} {'macro (mean)':>13s} {'range':>18s} {'Bot':>8s} {'WebBF':>8s} {'XSS':>8s}")
print("-" * 100)
for label, parts in LADDER:
    fused = [fuse(parts, i) for i in range(len(SEEDS))]
    fused_by_rung[label] = fused
    per_seed, fam = macro_fam(fused)
    RES[label] = {"components": parts, "per_seed_macro": per_seed,
                  "macro_mean": float(np.mean(per_seed)),
                  "macro_min": float(np.min(per_seed)),
                  "macro_max": float(np.max(per_seed)),
                  "families": fam}
    print(f"{label:30s} {np.mean(per_seed):>13.4f} "
          f"[{np.min(per_seed):.4f}, {np.max(per_seed):.4f}] "
          f"{fam['Bot']:>8.4f} {fam['Web Attack Brute Force']:>8.4f} "
          f"{fam['Web Attack XSS']:>8.4f}")

# ---- paired per-seed deltas vs the CNN baseline -------------------------------
base = RES["CNN"]["per_seed_macro"]
print("\n" + "=" * 100)
print("PAIRED DELTAS vs CNN  (each rung shares the CNN run, so run-to-run noise")
print("cancels — this, not the between-run SD, is the correct reference)")
print("=" * 100)
print(f"{'rung':30s} {'s42':>9s} {'s43':>9s} {'s44':>9s} {'mean':>9s} "
      f"{'seeds up':>9s} {'(÷SD ctx)':>10s}")
print("-" * 100)
for label, _ in LADDER[1:]:
    d = [a - b for a, b in zip(RES[label]["per_seed_macro"], base)]
    up = sum(x > 0 for x in d)
    RES[label]["paired_delta_per_seed"] = d
    RES[label]["paired_delta_mean"] = float(np.mean(d))
    RES[label]["seeds_improved"] = int(up)
    print(f"{label:30s} {d[0]:>+9.4f} {d[1]:>+9.4f} {d[2]:>+9.4f} "
          f"{np.mean(d):>+9.4f} {up:>7d}/3 {np.mean(d)/SD:>+10.2f}")

# ---- paired bootstrap on the comparisons that decide the ablation -------------
print("\n" + "=" * 100)
print("PAIRED BOOTSTRAP over test flows (stratified, B=%d)" % B)
print("=" * 100)


# Every rung is evaluated on the SAME resampled draw, so all comparisons come out
# of one pass (common random numbers -- which is also the correct construction
# for paired comparisons, not just the fast one). The first version re-ran the
# bootstrap per comparison: 5 comparisons x 2 rungs x 2000 replicates = ~180,000
# PR-AUC computations at 5.4 ms each, i.e. well over half an hour. This is one
# pass of B x 6 rungs x 3 seeds x 3 families.
LABELS = [l for l, _ in LADDER]
rng = np.random.RandomState(RNG_SEED)
boot = np.empty((B, len(LABELS)))
print(f"  bootstrapping {B} replicates x {len(LABELS)} rungs "
      f"(~{B * len(LABELS) * 9 * 5.4e-3 / 60:.0f} min)...")
for i in range(B):
    b = rng.choice(ben_idx, size=len(ben_idx), replace=True)
    idx = {f: (b, rng.choice(fam_idx[f], size=len(fam_idx[f]), replace=True))
           for f in FAMS}
    for j, lab in enumerate(LABELS):
        per_seed, _ = macro_fam(fused_by_rung[lab], idx)
        boot[i, j] = np.mean(per_seed)
    if (i + 1) % 100 == 0:
        print(f"    replicate {i + 1}/{B}", flush=True)

col = {l: j for j, l in enumerate(LABELS)}


def boot_compare(la, lb):
    obs = RES[la]["macro_mean"] - RES[lb]["macro_mean"]
    diffs = boot[:, col[la]] - boot[:, col[lb]]
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    p = 2 * min((diffs <= 0).mean(), (diffs >= 0).mean())
    return {"a": la, "b": lb, "diff": float(obs), "ci95": [float(lo), float(hi)],
            "p": float(min(p, 1.0)), "significant": bool(lo > 0 or hi < 0)}


KEY = [("CNN + KG", "CNN"),                                   # does the KG earn it?
       ("CNN + LTN-ctrl", "CNN"),                             # does the trainer?
       ("CNN + LTN-Ax6", "CNN"),                              # do the axioms?
       ("CNN + LTN-Ax6 + KG (FULL)", "CNN + KG"),             # A4 — the sharp one
       ("CNN + LTN-Ax6 + KG (FULL)", "CNN")]                  # full vs baseline
RES["_bootstrap"] = []
for la, lb in KEY:
    r = boot_compare(la, lb)
    RES["_bootstrap"].append(r)
    verdict = "SIGNIFICANT" if r["significant"] else "n.s."
    print(f"  {la:30s} vs {lb:26s} {r['diff']:>+8.4f} "
          f"[{r['ci95'][0]:+.4f}, {r['ci95'][1]:+.4f}] p={r['p']:.4f}  {verdict}")

# ---- verdicts on the pre-registered predictions -------------------------------
print("\n" + "=" * 100)
print("PRE-REGISTERED PREDICTIONS")
print("=" * 100)
kg = RES["CNN + KG"]
ctrl = RES["CNN + LTN-ctrl"]
ax6 = RES["CNN + LTN-Ax6"]
full = RES["CNN + LTN-Ax6 + KG (FULL)"]

a1 = kg["seeds_improved"] == 3 and kg["paired_delta_mean"] > 0.03
a2 = abs(ctrl["paired_delta_mean"]) < 0.02
a3 = ax6["paired_delta_mean"] <= 0.02
a4 = full["macro_mean"] <= kg["macro_mean"]

for k, v, detail in [
    ("A1 +KG improves on 3/3 seeds", a1,
     f"{kg['seeds_improved']}/3 seeds, mean {kg['paired_delta_mean']:+.4f}"),
    ("A2 +LTN(control) changes ~nothing", a2,
     f"mean {ctrl['paired_delta_mean']:+.4f}"),
    ("A3 +LTN(Ax6) does not help macro", a3,
     f"mean {ax6['paired_delta_mean']:+.4f}"),
    ("A4 FULL does NOT beat CNN+KG", a4,
     f"full {full['macro_mean']:.4f} vs CNN+KG {kg['macro_mean']:.4f} "
     f"({full['macro_mean'] - kg['macro_mean']:+.4f})"),
]:
    print(f"  {k:36s} {'CONFIRMED' if v else 'FALSIFIED':10s} {detail}")

RES["_predictions"] = {"A1": bool(a1), "A2": bool(a2), "A3": bool(a3), "A4": bool(a4)}

# ---- the ablation's actual conclusion ----------------------------------------
best = max((l for l, _ in LADDER), key=lambda l: RES[l]["macro_mean"])
print("\n" + "=" * 100)
print("CONCLUSION")
print("=" * 100)
print(f"  best rung on macro: {best} ({RES[best]['macro_mean']:.4f})")
earners = [l for l, _ in LADDER[1:]
           if RES[l]["paired_delta_mean"] > 0 and RES[l]["seeds_improved"] == 3]
print(f"  rungs that improve on ALL 3 seeds: {', '.join(earners) if earners else 'none'}")
if not a4:
    print("  A4 FALSIFIED — the full system beats CNN+KG, so the symbolic pillar")
    print("  DOES add something on top of the graph. Revisit the fusion_multi")
    print("  'more channels dilute' conclusion; it may be channel-specific.")
else:
    print("  A4 CONFIRMED — adding the symbolic pillar on top of the KG does not")
    print("  help. On this evidence ONLY THE KG earns its place as a fusion")
    print("  channel. That is a negative result about this project's own")
    print("  architecture, and it is the honest ablation outcome.")

RES["_meta"] = {"seeds": SEEDS, "noise_floor_sd": SD, "bootstrap_B": B,
                "fusion": "equal-weight rank mean, nothing fitted",
                "reference": "paired per-seed delta (rungs share the CNN run)"}
outp = os.path.join(MD, "ablation.json")
with open(outp, "w", encoding="utf-8") as f:
    json.dump(RES, f, indent=1)
print(f"\nwrote {outp}")

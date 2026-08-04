"""
significance_seed.py — SEED-level significance, which n=3 made impossible.

WHY THIS EXISTS
---------------
Every significance result in this project so far (`significance.py`) is a paired
bootstrap over test FLOWS. That quantifies "would this hold on different traffic?"
It does **not** quantify "would this hold if we retrained?" — a different and, for
a claim about a *method*, arguably more important question.

Seed-level testing was impossible at n=3: the Wilcoxon signed-rank test with 3
paired samples has a **minimum achievable two-sided p of 0.25**, so no result
could reach p<0.05 regardless of effect size. This was flagged repeatedly in
STATUS and never fixable without more seeds.

At **n=6** the floor drops to **p = 2/2^6 = 0.031**, so seed-level significance
becomes achievable for the first time. `seed_sweep.sh` produced seeds 45-47 for
the CNN and autoencoder to make this possible.

⚠️ Even at n=6 the test is weak: it can only ever return p ∈ {0.031, 0.094, ...}.
A non-significant result at n=6 is NOT evidence of no effect — it is evidence the
test is underpowered. Both the p-value and the raw per-seed values are printed so
the reader can judge, and the sign test is reported alongside as a sanity check.

Run:  python scripts/significance_seed.py
Out:  outputs/metadata/significance_seed.json
"""
import os
import json
import glob
import numpy as np
from scipy.stats import wilcoxon
from sklearn.metrics import average_precision_score as AP

import paths

P, PR = paths.PAPER, paths.PREDICTIONS
yte = np.load(os.path.join(P, "y_test_mc.npy"), allow_pickle=True)
is_ben = yte == "BENIGN"
FAMS = ["Bot", "Web Attack Brute Force", "Web Attack XSS"]


def fam_pr(s, f):
    m = (yte == f) | is_ben
    return float(AP((yte[m] != "BENIGN").astype(int), s[m]))


def macro(s):
    return float(np.mean([fam_pr(s, f) for f in FAMS]))


def _find(pattern_fmt, seeds):
    """Resolve per-seed score files; seed 42 has no suffix by convention."""
    out = []
    for s in seeds:
        sfx = "" if s == 42 else f"_s{s}"
        p = os.path.join(PR, pattern_fmt.format(sfx=sfx))
        out.append(p if os.path.exists(p) else None)
    return out


SEEDS = [42, 43, 44, 45, 46, 47]
CHANNELS = {
    "cnn":         "y_prob_cnn_paper{sfx}_logodds_test.npy",
    "autoencoder": "y_prob_autoencoder_paper{sfx}_test.npy",
}
scores = {}
for name, pat in CHANNELS.items():
    files = _find(pat, SEEDS)
    have = [(s, f) for s, f in zip(SEEDS, files) if f]
    if len(have) < 4:
        print(f"  !! {name}: only {len(have)} seeds present — need >=6 for a seed-level test")
    scores[name] = {s: np.load(f) for s, f in have}
    print(f"  {name:12s} seeds present: {sorted(scores[name])}")

OUT = {"seeds_requested": SEEDS, "comparisons": []}


def seed_test(a, b, metric_fn, label):
    """Paired Wilcoxon over seeds. Both channels must share the same seed set."""
    common = sorted(set(scores[a]) & set(scores[b]))
    if len(common) < 6:
        print(f"\n  {label}: only {len(common)} shared seeds — SKIPPED "
              f"(n=6 needed for p<0.05 to be reachable)")
        return
    va = np.array([metric_fn(scores[a][s]) for s in common])
    vb = np.array([metric_fn(scores[b][s]) for s in common])
    d = va - vb
    try:
        stat, p = wilcoxon(va, vb)
    except ValueError:
        stat, p = float("nan"), float("nan")
    wins = int((d > 0).sum())
    sign_p = 2 * min(sum(1 for x in d if x > 0), sum(1 for x in d if x < 0)) / len(d) \
        if len(d) else float("nan")
    print(f"\n  {label}  (n={len(common)} seeds)")
    print(f"    {a}: {np.round(va, 4).tolist()}")
    print(f"    {b}: {np.round(vb, 4).tolist()}")
    print(f"    mean diff {d.mean():+.4f} | {a} wins {wins}/{len(d)} seeds | "
          f"Wilcoxon p={p:.4f} | floor at n={len(common)} is {2/2**len(common):.3f}")
    verdict = ("SIGNIFICANT at seed level" if p < 0.05 else
               "n.s. — but note the floor; at this n a null is weak evidence")
    print(f"    -> {verdict}")
    OUT["comparisons"].append({
        "a": a, "b": b, "metric": label, "n_seeds": len(common),
        "values_a": va.tolist(), "values_b": vb.tolist(),
        "mean_diff": float(d.mean()), "wilcoxon_p": float(p),
        "sign_test_p": float(sign_p), "wins": wins,
        "min_achievable_p": float(2 / 2 ** len(common)),
        "significant": bool(p < 0.05)})


print("\n" + "=" * 88)
print("SEED-LEVEL SIGNIFICANCE (paired Wilcoxon over training seeds)")
print("=" * 88)
seed_test("cnn", "autoencoder", macro, "macro zero-day PR-AUC")
seed_test("cnn", "autoencoder", lambda s: fam_pr(s, "Bot"), "Bot PR-AUC")
seed_test("cnn", "autoencoder", lambda s: fam_pr(s, "Web Attack Brute Force"), "Web BF PR-AUC")
seed_test("cnn", "autoencoder", lambda s: fam_pr(s, "Web Attack XSS"), "XSS PR-AUC")

print("\n" + "-" * 88)
print("⚠️ Even at n=6 the Wilcoxon floor is p=0.031, so this test can only ever")
print("   distinguish 'all seeds agree' from 'they do not'. A non-significant result")
print("   is evidence of LOW POWER, not of no effect. Per-seed values are printed")
print("   above so the reader can judge the effect size directly.")

with open(os.path.join(paths.METADATA, "significance_seed.json"), "w", encoding="utf-8") as f:
    json.dump(OUT, f, indent=1)
print(f"\nwrote {os.path.join(paths.METADATA, 'significance_seed.json')}")

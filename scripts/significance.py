"""
significance.py — paired significance tests on per-flow scores.

Why this exists
---------------
`conference_roadmap.md` Tier-S #2 ("statistical honesty as a weapon") requires a
paired bootstrap / Wilcoxon on per-flow scores before any head-to-head claim is
published. Two open items in STATUS.md need it:

  * **C2** — CNN (`cnn_paper`, n=3, macro 0.6399 [0.6353, 0.6446]) vs the LTN
    no-axiom control (n=3, 0.6194 [0.6029, 0.6505]). The CNN's ENTIRE range sits
    inside the control's, so "the neural baseline wins" was explicitly recorded as
    NOT ESTABLISHED pending this test.
  * **The double dissociation** — CNN vs autoencoder per family. Seed ranges do not
    overlap, which is suggestive but is not a test.

And one raised 2026-08-03 by putting the classical baselines on 3 seeds:

  * **RandomForest vs autoencoder on Bot.** RF (a supervised (A)-family method)
    came back at Bot 0.1311 mean — indistinguishable from the AE's 0.1314 — while
    also scoring macro 0.5995. That is a direct challenge to the "(B) methods own
    Bot" reading, so it needs a test rather than an eyeball.

Method
------
**Stratified paired bootstrap over test flows.** For each family view (benign + one
zero-day family) we resample the benign indices and the family indices SEPARATELY,
with replacement, preserving each group's count. Preserving counts holds the family's
chance PR-AUC fixed, so a shift in PR-AUC reflects a change in *ranking quality*
rather than a change in prevalence — without this, PR-AUC wobbles for reasons that
have nothing to do with the models.

Both channels are scored on the SAME resampled indices (that is what makes it
paired), so the difference cancels flow-sampling noise that is common to both.

Multi-seed channels are collapsed to their **mean macro over seeds** inside each
bootstrap replicate, i.e. the estimand is "mean-over-seeds macro zero-day PR-AUC".

⚠️ **What this test does and does not cover.** It quantifies uncertainty from *which
test flows we happened to draw*. It does NOT convert n=3 seeds into statistical
power over *training* randomness — with 3 paired seeds a Wilcoxon signed-rank test
cannot produce p < 0.25 no matter how large the effect, so it is reported for
completeness and explicitly marked underpowered. Seed-level and flow-level
uncertainty are different things and both are printed.

Run:  python scripts/significance.py
Writes: outputs/metadata/significance.json
"""
import os
import json
import itertools
import numpy as np
from sklearn.metrics import average_precision_score

import paths

RNG_SEED = 42
B = 2000                      # bootstrap replicates
FAMS = ["Bot", "Web Attack Brute Force", "Web Attack XSS"]

P = paths.PAPER
PRED = paths.PREDICTIONS

yte = np.load(os.path.join(P, "y_test_mc.npy"), allow_pickle=True)

# ---------------------------------------------------------------- channels ----
# Each channel -> list of per-seed score files. Log-odds scoring where available
# (PR-AUC is rank-based, but the saturated runs needed it; see KNOWN_ISSUES).
CHANNELS = {
    "cnn_paper":     ["y_prob_cnn_paper_logodds_test.npy",
                      "y_prob_cnn_paper_s43_logodds_test.npy",
                      "y_prob_cnn_paper_s44_logodds_test.npy"],
    "ltn_ctrl_w0":   ["y_prob_ltn_ctrl_w0_logodds_test.npy",
                      "y_prob_ltn_ctrl_w0_s43_logodds_test.npy",
                      "y_prob_ltn_ctrl_w0_s44_logodds_test.npy"],
    "autoencoder":   ["y_prob_autoencoder_paper_test.npy",
                      "y_prob_autoencoder_paper_s43_test.npy",
                      "y_prob_autoencoder_paper_s44_test.npy"],
    "random_forest": ["y_prob_random_forest_test.npy",
                      "y_prob_random_forest_s43_test.npy",
                      "y_prob_random_forest_s44_test.npy"],
    "mahalanobis":   ["y_prob_mahalanobis_test.npy",
                      "y_prob_mahalanobis_s43_test.npy",
                      "y_prob_mahalanobis_s44_test.npy"],
    "msp":           ["y_prob_msp_test.npy",
                      "y_prob_msp_s43_test.npy",
                      "y_prob_msp_s44_test.npy"],
    # deterministic: random_state has no stochastic component to control
    # (no subsampling configured), verified byte-identical across seeds 42/43/44.
    "xgboost":       ["y_prob_xgboost_test.npy"],
    # Phase 4 (added 2026-08-03). "causal" = online variant, scored using only
    # windows that had already arrived — the honest real-time number.
    "kg_causal":     ["y_prob_kg_causal_test.npy",
                      "y_prob_kg_s43_causal_test.npy",
                      "y_prob_kg_s44_causal_test.npy"],
    "kg":            ["y_prob_kg_test.npy",
                      "y_prob_kg_s43_test.npy",
                      "y_prob_kg_s44_test.npy"],
}

scores = {}
for name, files in CHANNELS.items():
    arrs = []
    for f in files:
        p = os.path.join(PRED, f)
        if not os.path.exists(p):
            print(f"  !! missing {f} — skipping channel {name}")
            arrs = None
            break
        arrs.append(np.load(p))
    if arrs:
        scores[name] = arrs
        print(f"  loaded {name:14s} n_seeds={len(arrs)}")

# ------------------------------------------------------------- index cache ----
is_benign = yte == "BENIGN"
ben_idx = np.flatnonzero(is_benign)
fam_idx = {f: np.flatnonzero(yte == f) for f in FAMS}
for f in FAMS:
    print(f"  {f:24s} n={len(fam_idx[f]):6d}  chance PR-AUC="
          f"{len(fam_idx[f])/(len(fam_idx[f])+len(ben_idx)):.4f}")


def macro_on(idx_by_fam, seed_arrs):
    """Mean-over-seeds macro PR-AUC given a resampled index set per family."""
    per_seed = []
    for s in seed_arrs:
        fams = []
        for f in FAMS:
            bi, fi = idx_by_fam[f]
            y = np.concatenate([np.zeros(len(bi), np.int8), np.ones(len(fi), np.int8)])
            sc = np.concatenate([s[bi], s[fi]])
            fams.append(average_precision_score(y, sc))
        per_seed.append(np.mean(fams))
    return float(np.mean(per_seed))


def family_on(idx_by_fam, seed_arrs, fam):
    per_seed = []
    for s in seed_arrs:
        bi, fi = idx_by_fam[fam]
        y = np.concatenate([np.zeros(len(bi), np.int8), np.ones(len(fi), np.int8)])
        sc = np.concatenate([s[bi], s[fi]])
        per_seed.append(average_precision_score(y, sc))
    return float(np.mean(per_seed))


def identity_idx():
    return {f: (ben_idx, fam_idx[f]) for f in FAMS}


def boot_idx(rng):
    """Stratified: resample benign and each family separately, preserving counts."""
    b = rng.choice(ben_idx, size=len(ben_idx), replace=True)
    return {f: (b, rng.choice(fam_idx[f], size=len(fam_idx[f]), replace=True))
            for f in FAMS}


def compare(a, b, metric="macro", fam=None):
    """Paired stratified bootstrap of (a - b). Returns dict with CI and p."""
    rng = np.random.RandomState(RNG_SEED)
    f_ = (lambda ix, s: macro_on(ix, s)) if metric == "macro" \
        else (lambda ix, s: family_on(ix, s, fam))
    ix0 = identity_idx()
    obs_a, obs_b = f_(ix0, scores[a]), f_(ix0, scores[b])
    diffs = np.empty(B)
    for i in range(B):
        ix = boot_idx(rng)
        diffs[i] = f_(ix, scores[a]) - f_(ix, scores[b])
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    # two-sided bootstrap p: fraction of replicates on the other side of 0, doubled
    p = 2 * min((diffs <= 0).mean(), (diffs >= 0).mean())
    return {"a": a, "b": b, "metric": metric if fam is None else fam,
            "obs_a": obs_a, "obs_b": obs_b, "obs_diff": obs_a - obs_b,
            "ci95_lo": float(lo), "ci95_hi": float(hi),
            "p_boot": float(min(p, 1.0)),
            "significant": bool(lo > 0 or hi < 0)}


RESULTS = {"config": {"B": B, "rng_seed": RNG_SEED,
                      "method": "stratified paired bootstrap over test flows; "
                                "benign and family resampled separately preserving counts; "
                                "multi-seed channels collapsed to mean-over-seeds inside each replicate"},
           "comparisons": []}

TESTS = [
    # (a, b, metric, fam, why)
    ("cnn_paper", "ltn_ctrl_w0", "macro", None,
     "C2 — is the neural baseline actually better than the no-axiom LTN control?"),
    ("cnn_paper", "autoencoder", "family", "Bot",
     "double dissociation — AE should WIN Bot (negative diff expected)"),
    ("cnn_paper", "autoencoder", "family", "Web Attack Brute Force",
     "double dissociation — CNN should win Web BF"),
    ("cnn_paper", "autoencoder", "family", "Web Attack XSS",
     "double dissociation — CNN should win XSS"),
    ("random_forest", "autoencoder", "family", "Bot",
     "NEW 2026-08-03 — does a supervised (A) method match the AE on Bot?"),
    ("random_forest", "cnn_paper", "family", "Bot",
     "NEW — RF vs CNN on Bot, both (A)-family"),
    ("random_forest", "autoencoder", "macro", None,
     "NEW — RF should dominate AE on macro"),
    ("cnn_paper", "xgboost", "macro", None,
     "retracted-claim check: 'on macro the CNN beats XGBoost'"),
    ("autoencoder", "mahalanobis", "family", "Bot",
     "is the AE really the better (B) Bot channel?"),
    ("kg_causal", "autoencoder", "family", "Bot",
     "PHASE 4 — does the KG beat the previous best Bot channel?"),
    ("kg_causal", "random_forest", "family", "Bot",
     "PHASE 4 — KG vs the other joint-best Bot channel"),
    ("kg_causal", "kg", "family", "Bot",
     "PHASE 4 — is the causal/online KG really better than the transductive one?"),
    ("cnn_paper", "kg_causal", "macro", None,
     "PHASE 4 — the CNN should still dominate on macro"),
]

print("\n" + "=" * 100)
print(f"PAIRED STRATIFIED BOOTSTRAP  (B={B} replicates, 95% CI on the paired difference)")
print("=" * 100)
for a, b, metric, fam, why in TESTS:
    if a not in scores or b not in scores:
        print(f"  skip {a} vs {b} (missing channel)")
        continue
    r = compare(a, b, metric, fam)
    r["why"] = why
    RESULTS["comparisons"].append(r)
    verdict = "SIGNIFICANT" if r["significant"] else "n.s."
    label = metric if fam is None else fam
    print(f"\n  {a} vs {b}   [{label}]")
    print(f"    {why}")
    print(f"    {a}={r['obs_a']:.4f}  {b}={r['obs_b']:.4f}  diff={r['obs_diff']:+.4f}")
    print(f"    95% CI [{r['ci95_lo']:+.4f}, {r['ci95_hi']:+.4f}]  p={r['p_boot']:.4f}  -> {verdict}")

# ------------------------------------------------- seed-level power caveat ----
print("\n" + "=" * 100)
print("SEED-LEVEL VARIANCE — reported separately, and it is UNDERPOWERED at n=3")
print("=" * 100)
seedwise = {}
for name, arrs in scores.items():
    per_seed = []
    ix0 = identity_idx()
    for s in arrs:
        per_seed.append(macro_on(ix0, [s]))
    seedwise[name] = per_seed
    rng_txt = f"[{min(per_seed):.4f}, {max(per_seed):.4f}]" if len(per_seed) > 1 else "(deterministic)"
    print(f"  {name:14s} n={len(per_seed)}  macro mean={np.mean(per_seed):.4f}  range {rng_txt}")
RESULTS["seedwise_macro"] = seedwise
RESULTS["seed_power_note"] = (
    "With 3 paired seeds the Wilcoxon signed-rank test has a minimum achievable "
    "two-sided p of 0.25, so no seed-level comparison in this project can reach "
    "p<0.05 regardless of effect size. The bootstrap above quantifies FLOW-sampling "
    "uncertainty only. To make a seed-level claim at alpha=0.05 you need n>=6 seeds.")
print("\n  " + RESULTS["seed_power_note"].replace(". ", ".\n  "))

out = os.path.join(paths.METADATA, "significance.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(RESULTS, f, indent=1)
print(f"\nwrote {out}")

"""
fusion_multi.py — parameter-free multi-channel rank fusion. The improvement path
that does NOT involve fitting on test.

THE CONSTRAINT THAT SHAPES THIS SCRIPT
--------------------------------------
Zero-day families are test-only by construction. So **any** hyperparameter tuned
by looking at zero-day performance — k, tau, the burst threshold, which channels
to include — is fitting on the test set. That is the fusion wall wearing a
different hat, and it rules out most of what would normally be called "improving
the score."

What remains legitimate is combination with **imposed** rather than **learned**
weights. `fusion_kg.py` established that this works (CNN+KG: 0.6399 -> 0.6926,
p<0.001) precisely because a rank-mean never has to *discover* that a
zero-day-specific channel is worth weighting.

This extends that to every channel we have built, with **pre-registered** subsets
so the choice among them is visible rather than fitted.

PRE-REGISTERED SUBSETS (fixed before running — see the git history of this file)
-------------------------------------------------------------------------------
  ALL        every channel, equal weight. No selection at all — the most honest
             single number, and the one to lead with if it wins.
  A_ONLY     the supervised/closed-set channels (CNN, XGB, RF, LTN control).
  B_ONLY     the benign-only / distance channels (AE, Mahalanobis, IsoForest).
  A_PLUS_B   one strongest of each family + the KG. Tests whether the diversity,
             rather than the count, is what helps.
  CNN_KG     the established 2-channel result, as the reference to beat.

⚠️ Reporting the best of five subsets is a selection effect. It is stated here and
in STATUS rather than hidden, and ALL five are reported, not just the winner.

Run:  python scripts/fusion_multi.py
"""
import os
import json
import numpy as np
from scipy.stats import rankdata

import paths, metrics, tracking

P, PR = paths.PAPER, paths.PREDICTIONS
yte = np.load(os.path.join(P, "y_test_mc.npy"), allow_pickle=True)
zero_day = set(np.load(os.path.join(P, "zero_day_classes.npy"), allow_pickle=True).tolist())
n = len(yte)

# channel -> per-seed score files (seed 42/43/44 where available)
CH = {
    "cnn":  ["y_prob_cnn_paper_logodds_test.npy", "y_prob_cnn_paper_s43_logodds_test.npy",
             "y_prob_cnn_paper_s44_logodds_test.npy"],
    "ltn":  ["y_prob_ltn_ctrl_w0_logodds_test.npy", "y_prob_ltn_ctrl_w0_s43_logodds_test.npy",
             "y_prob_ltn_ctrl_w0_s44_logodds_test.npy"],
    "xgb":  ["y_prob_xgboost_test.npy"] * 3,
    "rf":   ["y_prob_random_forest_test.npy", "y_prob_random_forest_s43_test.npy",
             "y_prob_random_forest_s44_test.npy"],
    "msp":  ["y_prob_msp_test.npy", "y_prob_msp_s43_test.npy", "y_prob_msp_s44_test.npy"],
    "maha": ["y_prob_mahalanobis_test.npy", "y_prob_mahalanobis_s43_test.npy",
             "y_prob_mahalanobis_s44_test.npy"],
    "ae":   ["y_prob_autoencoder_paper_test.npy", "y_prob_autoencoder_paper_s43_test.npy",
             "y_prob_autoencoder_paper_s44_test.npy"],
    "iso":  ["y_prob_isolation_forest_test.npy", "y_prob_isolation_forest_s43_test.npy",
             "y_prob_isolation_forest_s44_test.npy"],
    "kg":   ["y_prob_kg_causal_test.npy", "y_prob_kg_s43_causal_test.npy",
             "y_prob_kg_s44_causal_test.npy"],
}
SUBSETS = {
    "ALL (no selection)":      list(CH),
    "A_ONLY (supervised)":     ["cnn", "ltn", "xgb", "rf"],
    "B_ONLY (benign-only)":    ["ae", "maha", "iso"],
    "A_PLUS_B (+KG)":          ["cnn", "ae", "kg"],
    "CNN_KG (the reference)":  ["cnn", "kg"],
}

ranks = {}
for c, files in CH.items():
    ok = [f for f in files if os.path.exists(os.path.join(PR, f))]
    if len(ok) < 3:
        print(f"  !! {c}: only {len(ok)}/3 seed files — skipped")
        continue
    ranks[c] = [rankdata(np.load(os.path.join(PR, f))) / n for f in ok]
print(f"loaded {len(ranks)} channels x 3 seeds: {', '.join(ranks)}\n")

FAMS = ["Bot", "Web Attack Brute Force", "Web Attack XSS"]


def ev(seed_scores):
    """Mean over seeds of (macro, per-family)."""
    out = []
    for s in seed_scores:
        r = metrics.evaluate(yte, s, zero_day, fpr=0.01)
        fam = r["zeroday_family"]
        out.append([r["macro"]["pr_auc"]] + [fam[f]["pr_auc"] for f in FAMS])
    a = np.array(out)
    return a.mean(0), a[:, 0].min(), a[:, 0].max()


BASE = 0.6399  # CNN alone, n=3
print("=" * 96)
print("PARAMETER-FREE MULTI-CHANNEL RANK FUSION (equal weights — nothing is fitted)")
print("=" * 96)
print(f"{'subset':26s} {'macro':>8s} {'range':>17s} {'Δ vs CNN':>10s} | {'Bot':>7s} {'WebBF':>7s} {'XSS':>7s}")
print("-" * 96)
RES = {}
for name, chans in SUBSETS.items():
    use = [c for c in chans if c in ranks]
    if len(use) < 2:
        continue
    fused = [np.mean([ranks[c][i] for c in use], axis=0) for i in range(3)]
    m, lo, hi = ev(fused)
    RES[name] = {"channels": use, "macro": m[0], "macro_range": [lo, hi],
                 "bot": m[1], "webbf": m[2], "xss": m[3], "delta_vs_cnn": m[0] - BASE}
    star = " *" if m[0] > BASE else "  "
    print(f"{name:26s} {m[0]:>8.4f} [{lo:.4f}, {hi:.4f}] {m[0]-BASE:>+10.4f}{star}| "
          f"{m[1]:>7.4f} {m[2]:>7.4f} {m[3]:>7.4f}")
    tag = "fusion_" + name.split()[0].lower()
    tracking.log_run(tag, {"protocol": "paper", "rule": "rank_mean_equal",
                           "fitted": False, "channels": use, "n_seeds": 3},
                     {"macro_zd_pr_auc": float(m[0]), "fam_bot_pr_auc": float(m[1]),
                      "fam_web_attack_brute_force_pr_auc": float(m[2]),
                      "fam_web_attack_xss_pr_auc": float(m[3])})
print("-" * 96)
print(f"{'CNN alone (baseline)':26s} {BASE:>8.4f} [0.6353, 0.6446] {0.0:>+10.4f}  | "
      f"{0.0446:>7.4f} {0.9226:>7.4f} {0.9524:>7.4f}")

best = max(RES.items(), key=lambda kv: kv[1]["macro"])
print(f"\nBEST: {best[0]} -> macro {best[1]['macro']:.4f} ({best[1]['delta_vs_cnn']:+.4f} vs CNN alone)")
print("⚠️ Five subsets were pre-registered and all five are reported. Choosing the best")
print("   of five is a selection effect — state it; do not quote the winner alone.")

with open(os.path.join(paths.METADATA, "fusion_multi.json"), "w", encoding="utf-8") as f:
    json.dump({"baseline_cnn_macro": BASE, "subsets": RES}, f, indent=1)
print(f"\nwrote {os.path.join(paths.METADATA, 'fusion_multi.json')}")

"""
hostwindow_detect.py — does the host-window view REACH the zero-day families, and does
benign-calibrated min-p fusion beat the best single channel?

TWO QUESTIONS, KEPT SEPARATE
----------------------------
`hostwindow.py` asks whether the window view is outside the learned feature basis. Even
if it is, that says nothing about whether it DETECTS anything: the project has already
found knowledge that was novel and useless, and a mechanism (§4 of the paper) under
which a channel can be exogenous and still not separate a family. So this script asks
the two remaining questions separately, and reports them separately:

  Q1  Does a benign-only novelty model on the 8 window features reach Bot, Web Brute
      Force and XSS at all? Bot's signature is persistence, so if any channel in this
      project should reach Bot, it is this one.
  Q2  Does conformal min-p fusion over {known-attack GBM, benign autoencoder, window
      novelty} beat its own best channel on macro zero-day PR-AUC?

WHAT TO EXPECT FROM Q2, WRITTEN DOWN BEFORE RUNNING (pre-registration)
----------------------------------------------------------------------
Conformal calibration is a MONOTONE transform of each channel's scores, so it cannot
change any channel's own PR-AUC. Only the min-p combination can move the number. The
withdrawn fusion result is the reference case: across 11 CNN runs the online rank
fusion gained in 5, and in 0 of 6 deterministic runs. So the honest prediction is:

  P1  Calibration preserves each channel's ORDERING (Spearman rho = 1). It does not
      preserve PR-AUC exactly: a p-value takes at most n_calib+1 distinct values, and
      the ties that quantisation creates move average precision a little. That is a
      property of the transform, not an error -- but it has to be measured, not
      assumed, so the check is on rho and the tie fraction.
  P2  min-p fusion does NOT beat the best channel's macro zero-day PR-AUC by more than
      the noise floor (post-flag SD 0.0171; deltas below ~0.026 are not results).
  P3  What fusion DOES buy is a calibrated operating point: the achieved benign FPR at
      a requested p-threshold should match the request, which no single raw channel
      gives you. That is a reporting property, not a detection gain. NOTE that raw
      min-p is NOT calibrated: over k channels P(min p <= t) ~ 1-(1-t)^k, so a 1 %
      request fires at about k %. The fix is a second conformal step on the min-p
      statistic itself, which needs its own calibration half. Both are reported.

CALIBRATION SET, AND WHY IT IS NOT THE VALIDATION SPLIT
-------------------------------------------------------
No channel has stored validation scores (the pipeline saves test scores only), so
split-conformal calibration uses HALF OF THE BENIGN TEST FLOWS, drawn by a fixed seed,
and every metric is computed on the other half plus all attack flows. No attack label
is ever used for calibration. Consequence, stated because it matters: benign
prevalence in the evaluation half differs from the full test set, so the numbers here
are NOT comparable with the recorded 0.6299-style figures. Every channel is evaluated
on exactly the same subset, so the comparisons WITHIN this script are sound. The raw
full-set PR-AUC of each channel is also printed, and those are comparable.

Run:  python scripts/hostwindow_detect.py
Out:  outputs/metadata/hostwindow_detect.json
      outputs/predictions/y_prob_hostwin_s{42,43,44}_test.npy
"""
import os
import sys
import json

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                          # noqa: E402
import config                                         # noqa: E402
import metrics                                        # noqa: E402
import tracking                                       # noqa: E402

SEEDS = [42, 43, 44]
NOISE_SD = 0.0171          # post-flag seed SD (n=6), STATUS "NOISE FLOOR SETTLED"

# The deterministic population. Never pooled with pre-flag runs.
CHANNELS = {
    "gbm_known":  ["y_prob_random_forest_tuned_s%d_test.npy" % s for s in SEEDS],
    "ae_novelty": ["y_prob_ae_det_s%d_test.npy" % s for s in SEEDS],
    "cnn_ref":    ["y_prob_c4_log1p_s%d_test.npy" % s for s in SEEDS],
}


def load_labels():
    y = np.load(os.path.join(paths.PAPER, "y_test_mc.npy"), allow_pickle=True)
    return np.asarray(y).astype(str)


def window_channel(seed):
    """Benign-only novelty on the 8 window features: the diagram's host-window box.

    Fitted on BENIGN TRAINING rows only, exactly like the autoencoder pillar, so the
    channel never sees an attack label. Scores are +anomaly (higher = more novel).
    """
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler

    Wtr = np.load(os.path.join(paths.PAPER, "hostwin_train.npy"))
    Wte = np.load(os.path.join(paths.PAPER, "hostwin_test.npy"))
    ytr = np.asarray(np.load(os.path.join(paths.PAPER, "y_train_mc.npy"),
                             allow_pickle=True)).astype(str)
    benign = Wtr[ytr == "BENIGN"]
    rng = np.random.RandomState(seed)
    if len(benign) > 200000:
        benign = benign[rng.choice(len(benign), 200000, replace=False)]
    sc = StandardScaler().fit(benign)
    iso = IsolationForest(n_estimators=200, random_state=seed, n_jobs=-1)
    iso.fit(sc.transform(benign))
    return -iso.score_samples(sc.transform(Wte))       # higher = more anomalous


def conformal_p(cal_scores, scores):
    """Split-conformal p-value: fraction of benign calibration scores at least as
    extreme, with the standard +1 correction so p is valid (never 0)."""
    cal = np.sort(np.asarray(cal_scores))
    n = len(cal)
    ge = n - np.searchsorted(cal, scores, side="left")
    return (1.0 + ge) / (n + 1.0)


def main():
    cfg = config.get()
    zd = cfg["zero_day_classes"]
    y = load_labels()
    PR = paths.PREDICTIONS

    print("=" * 100)
    print("Q1 - DOES THE HOST-WINDOW VIEW REACH THE ZERO-DAY FAMILIES?")
    print("=" * 100)

    scores = {c: [] for c in CHANNELS}
    for c, files in CHANNELS.items():
        for f in files:
            p = os.path.join(PR, f)
            if not os.path.exists(p):
                sys.exit("missing channel file %s" % p)
            scores[c].append(np.load(p).astype(float))
    scores["window"] = []
    for s in SEEDS:
        w = window_channel(s)
        np.save(os.path.join(PR, "y_prob_hostwin_s%d_test.npy" % s), w)
        scores["window"].append(w)

    raw = {}
    for c, arrs in scores.items():
        per_seed = [metrics.evaluate(y, a, zd) for a in arrs]
        macro = [r["macro"]["pr_auc"] for r in per_seed]
        fam = {}
        for f in per_seed[0]["zeroday_family"]:
            if per_seed[0]["zeroday_family"][f]["underpowered"]:
                continue
            fam[f] = {"pr_auc": [r["zeroday_family"][f]["pr_auc"] for r in per_seed],
                      "chance": per_seed[0]["zeroday_family"][f]["chance_pr_auc"]}
        raw[c] = {"macro_per_seed": macro, "macro_mean": float(np.mean(macro)),
                  "family": fam}
        print("\n  %-11s macro zero-day PR-AUC %.4f  (seeds %s)"
              % (c, np.mean(macro), ", ".join("%.4f" % m for m in macro)))
        for f, d in fam.items():
            lift = np.mean(d["pr_auc"]) / d["chance"]
            print("      %-26s %.4f  (chance %.4f, lift %5.2fx)"
                  % (f, np.mean(d["pr_auc"]), d["chance"], lift))

    print("\n" + "=" * 100)
    print("Q2 - CONFORMAL MIN-P FUSION vs ITS BEST CHANNEL")
    print("=" * 100)

    fuse_in = ["gbm_known", "ae_novelty", "window"]
    rng = np.random.RandomState(cfg["seed"])
    is_benign = y == "BENIGN"
    bidx = np.flatnonzero(is_benign)
    half = rng.choice(bidx, len(bidx) // 2, replace=False)
    # Two calibration folds: the first builds each channel's p-values, the second
    # calibrates the fused min-p statistic. Using one fold for both would calibrate
    # the fusion on the same flows that defined it, which is the defect this whole
    # split-conformal construction exists to avoid.
    cal, cal2 = half[: len(half) // 2], half[len(half) // 2:]
    keep = np.ones(len(y), bool)
    keep[half] = False             # evaluation half: other benign + every attack flow
    print("calibration: %d benign (channels) + %d benign (fused statistic); "
          "evaluation: %d flows (%d benign)"
          % (len(cal), len(cal2), keep.sum(), (is_benign & keep).sum()))

    out = {"raw": raw, "fusion": {}, "predictions": {}}
    per_seed_fused, per_seed_best, checks = [], [], []
    for i, s in enumerate(SEEDS):
        ps = {}
        for c in fuse_in:
            sc = scores[c][i]
            ps[c] = conformal_p(sc[cal], sc)
        minp = np.min(np.vstack([ps[c] for c in fuse_in]), axis=0)
        # second conformal step: the p-value OF the min-p statistic, calibrated on
        # benign flows the fusion has not seen. This is what makes a requested FPR
        # mean what it says.
        minp_cal = conformal_p(-minp[cal2], -minp)
        ev_f = metrics.evaluate(y[keep], -minp[keep], zd)
        chan = {c: metrics.evaluate(y[keep], -ps[c][keep], zd)["macro"]["pr_auc"]
                for c in fuse_in}
        # P1: calibration is monotone, so a channel's PR-AUC must not move
        for c in fuse_in:
            # Monotonicity, checked exactly. Spearman is the WRONG instrument here: a
            # p-value takes at most n_cal+1 values, ties 98 % of rows, and tied ranks
            # drag rho to 0.91 even when the map is perfectly order-preserving. Sort by
            # score and assert p never rises.
            o = np.argsort(scores[c][i], kind="stable")
            viol = int((np.diff(ps[c][o]) > 1e-12).sum())
            ties = 1.0 - len(np.unique(ps[c][keep])) / float(keep.sum())
            checks.append({"channel": c, "monotonicity_violations": viol,
                           "tie_fraction": float(ties),
                           "raw_macro": float(metrics.evaluate(
                               y[keep], scores[c][i][keep], zd)["macro"]["pr_auc"]),
                           "calibrated_macro": float(chan[c])})
        best = max(chan, key=chan.get)
        per_seed_fused.append(ev_f["macro"]["pr_auc"])
        per_seed_best.append(chan[best])
        # P3: does a requested p-threshold deliver the benign FPR it promises?
        fpr = {str(t): float((minp[keep & is_benign] <= t).mean())
               for t in (0.01, 0.05)}
        fpr2 = {str(t): float((minp_cal[keep & is_benign] <= t).mean())
                for t in (0.01, 0.05)}
        out["fusion"]["seed_%d" % s] = {
            "fused_macro": ev_f["macro"]["pr_auc"], "channel_macro": chan,
            "best_channel": best, "achieved_benign_fpr": fpr,
            "achieved_benign_fpr_recalibrated": fpr2,
            "fused_family": {f: d["pr_auc"] for f, d in ev_f["zeroday_family"].items()
                             if not d["underpowered"]}}
        print("\n  seed %d: fused %.4f | best channel %s %.4f | delta %+.4f"
              % (s, ev_f["macro"]["pr_auc"], best, chan[best],
                 ev_f["macro"]["pr_auc"] - chan[best]))
        print("           raw min-p   : requested 0.01 -> %.4f ; 0.05 -> %.4f"
              % (fpr["0.01"], fpr["0.05"]))
        print("           recalibrated: requested 0.01 -> %.4f ; 0.05 -> %.4f"
              % (fpr2["0.01"], fpr2["0.05"]))

    d = np.array(per_seed_fused) - np.array(per_seed_best)
    print("\n" + "-" * 100)
    viol = sum(c["monotonicity_violations"] for c in checks)
    max_shift = max(abs(c["calibrated_macro"] - c["raw_macro"]) for c in checks)
    print("P1 ordering preserved: %d monotonicity violations %s"
          % (viol, "OK" if viol == 0 else "<- FAILED, calibration reorders scores"))
    print("   PR-AUC shift from tie quantisation alone: max %.4f (ties %.3f of rows)"
          % (max_shift, max(c["tie_fraction"] for c in checks)))
    print("   NOTE: that shift is the same order as the noise floor (%.4f), so a small"
          % NOISE_SD)
    print("   calibration set perturbs the headline metric as much as a re-run does.")
    print("P2 fusion - best channel: mean %+.4f (%s), %d of %d seeds positive"
          % (d.mean(), ", ".join("%+.4f" % x for x in d), (d > 0).sum(), len(d)))
    print("   |delta| / noise SD (%.4f) = %.2f  -> %s"
          % (NOISE_SD, abs(d.mean()) / NOISE_SD,
             "WITHIN NOISE, not a result" if abs(d.mean()) < 2 * NOISE_SD
             else "exceeds 2 SD, worth a paired test"))
    out["summary"] = {
        "fused_macro_per_seed": per_seed_fused,
        "best_channel_macro_per_seed": per_seed_best,
        "delta_mean": float(d.mean()), "delta_per_seed": [float(x) for x in d],
        "seeds_positive": int((d > 0).sum()),
        "channel_calibration_checks": checks,
        "monotonicity_violations": int(viol),
        "max_pr_auc_shift_from_ties": float(max_shift),
        "noise_sd": NOISE_SD, "within_noise": bool(abs(d.mean()) < 2 * NOISE_SD)}

    p = os.path.join(paths.METADATA, "hostwindow_detect.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("\nwrote %s" % p)
    tracking.log_run("hostwindow_fusion", {"channels": fuse_in, "rule": "conformal_min_p"},
                     {"macro_zd_pr_auc": float(np.mean(per_seed_fused)),
                      "best_channel_macro": float(np.mean(per_seed_best)),
                      "delta_vs_best": float(d.mean())})
    for s, m in zip(SEEDS, raw["window"]["macro_per_seed"]):
        tracking.log_run("hostwin_s%d" % s, {"model": "isolation_forest_windowview", "seed": s},
                         {"macro_zd_pr_auc": float(m)})


if __name__ == "__main__":
    main()

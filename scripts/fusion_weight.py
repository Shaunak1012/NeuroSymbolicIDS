"""
fusion_weight.py — can weighted / multi-resolution fusion beat 50-50 rank fusion?

THE DIAGNOSIS THIS COMES FROM
------------------------------
At a 1 % false-alarm rate, CNN + KG (k=800) flags 57.6 % of unknown flows. Bot is
**1,956 of the 4,183** unknown flows -- 47 % of the total -- and sits at 23.2 %
there while reaching **85.2 % at a 10 % FPR**. So the KG's Bot signal is strong
and is being DILUTED, not missed: equal-weight rank fusion averages it with a CNN
whose Bot ranking is noise (cross-seed rho = -0.090).

`fitted_fusion.py` already showed equal weights cannot express "this channel is
worth more than that one" -- equal-weight CNN+AE LOSES to the CNN alone by 0.0501
(4.34 sigma). Every KG fusion result to date has been fixed at 50-50 and that
weight has never been swept.

TWO ARMS
--------
  W.  Weight sweep:  w*rank(KG) + (1-w)*rank(CNN), w in [0, 1].
  M.  Multi-resolution: fuse KG at SEVERAL k at once. Different k capture
      different cluster granularity, so this is an ensemble over a HYPERPARAMETER,
      not over seeds -- which matters, because ensembling over seeds was measured
      and it DESTROYED the fusion (0.5414 vs 0.6930, 3.70 sigma), by averaging
      away the per-seed noise the KG was correcting. Averaging over k has no such
      mechanism, but the arm is reported either way.

🔴 SELECTION IS DONE ON HELD-OUT DATA, NOT ON THE REPORTING SPLIT
-----------------------------------------------------------------
Sweeping w over the split that reports the headline is exactly the tuning
artefact this project keeps catching. Test is split stratified in half with a
FIXED rng (9001, independent of any model seed): **w and the k-set are chosen on
half A and reported on half B.** The reported number is therefore never the
maximum of anything.

⚠️ WHAT THIS CANNOT FIX. Heartbleed (n=11) and Infiltration (n=36) are below the
power bar and no weighting rescues them. Bot's detectability rides substantially
on CIC-IDS2017's scripted attack window, which is a property of the capture, not
of the method. Weighting moves how much of an existing signal survives fusion --
it does not create signal.

Run:  python scripts/fusion_weight.py
Out:  outputs/metadata/fusion_weight.json
"""
import os
import sys
import json

import numpy as np
from scipy.stats import rankdata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                        # noqa: E402
import metrics                                      # noqa: E402

P, PR = paths.PAPER, paths.PREDICTIONS
SEEDS = [42, 43, 44]
WEIGHTS = [0.0, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0]
KSETS = {"k800": [800], "k400+800": [400, 800],
         "k200+400+800": [200, 400, 800], "k100+200+400+800": [100, 200, 400, 800]}
SPLIT_RNG = 9001


def L(n):
    p = os.path.join(PR, n)
    return np.load(p) if os.path.exists(p) else None


def rk(x):
    return rankdata(x) / len(x)


def kgf(k, s):
    if k == 200:
        return "y_prob_kg_test.npy" if s == 42 else "y_prob_kg_s%d_test.npy" % s
    return "y_prob_kg_k%d_s%d_test.npy" % (k, s)


def main():
    yte = np.load(os.path.join(P, "y_test_mc.npy"), allow_pickle=True)
    zd = set(np.load(os.path.join(P, "zero_day_classes.npy"), allow_pickle=True).tolist())
    ben = yte == "BENIGN"
    allzd = np.isin(yte, list(zd))

    cnn = {s: L("y_prob_cnn_paper_test.npy" if s == 42
                else "y_prob_cnn_paper_s%d_test.npy" % s) for s in SEEDS}
    kg = {k: {s: L(kgf(k, s)) for s in SEEDS} for k in (100, 200, 400, 800)}
    for k, d in kg.items():
        if any(v is None for v in d.values()):
            sys.exit("missing KG predictions for k=%d" % k)

    # stratified half-split; rng fixed and independent of any model seed
    rng = np.random.RandomState(SPLIT_RNG)
    a, b = [], []
    for c in np.unique(yte):
        ii = np.flatnonzero(yte == c)
        rng.shuffle(ii)
        h = len(ii) // 2
        a.append(ii[:h]); b.append(ii[h:])
    A, B = np.concatenate(a), np.concatenate(b)

    def macro(sc, idx):
        return metrics.evaluate(yte[idx], sc[idx], zd, fpr=0.01)["macro"]["pr_auc"]

    def recall_at(sc, idx, fpr=0.01):
        m_ben = ben[idx]; m_zd = allzd[idx]
        s = sc[idx]
        thr = np.quantile(s[m_ben], 1.0 - fpr)
        return float((s[m_zd] >= thr).mean())

    def build(w, ks, s):
        kgr = np.mean([rk(kg[k][s]) for k in ks], axis=0)
        return w * kgr + (1.0 - w) * rk(cnn[s])

    print("=" * 92)
    print("WEIGHTED / MULTI-RESOLUTION FUSION — selected on half A, reported on half B")
    print("=" * 92)

    grid = {}
    for name, ks in KSETS.items():
        for w in WEIGHTS:
            sc = [build(w, ks, s) for s in SEEDS]
            grid[(name, w)] = (np.array([macro(x, A) for x in sc]),
                               np.array([macro(x, B) for x in sc]),
                               np.array([recall_at(x, B) for x in sc]))

    print("\n%-20s %s" % ("k-set", "  ".join("w=%.1f" % w for w in WEIGHTS)))
    for name in KSETS:
        print("%-20s %s" % (name, "  ".join("%5.3f" % grid[(name, w)][0].mean()
                                            for w in WEIGHTS)))
    print("(half A — SELECTION ONLY, never reported)")

    best = max(grid, key=lambda kk: grid[kk][0].mean())
    bname, bw = best
    baseA, baseB, baseR = grid[("k800", 0.5)]
    selA, selB, selR = grid[best]

    print("\n" + "-" * 92)
    print("SELECTED on half A : k-set=%s  w=%.1f  (half-A macro %.4f)"
          % (bname, bw, selA.mean()))
    print("-" * 92)
    print("REPORTED on half B — never used for selection")
    print("  baseline  k800 @ w=0.5 : macro %.4f | unknown-flow recall @1%%FPR %.1f%%"
          % (baseB.mean(), 100 * baseR.mean()))
    print("  selected  %-14s: macro %.4f | unknown-flow recall @1%%FPR %.1f%%"
          % ("%s @ w=%.1f" % (bname, bw), selB.mean(), 100 * selR.mean()))
    d = selB - baseB
    sd = d.std(ddof=1)
    sig = abs(d.mean()) / sd if sd > 0 else float("inf")
    cons = bool((d > 0).all() or (d < 0).all())
    print("  paired delta %+.4f | %.2f sigma | %d/3 better | %s"
          % (d.mean(), sig, int((d > 0).sum()),
             "direction consistent" if cons else "DIRECTION INCONSISTENT"))
    if not cons or d.mean() <= 0:
        print("\n  => NOT AN IMPROVEMENT on held-out data. The half-A gain was selection.")

    out = {"split_rng": SPLIT_RNG, "weights": WEIGHTS, "ksets": KSETS,
           "selected": {"kset": bname, "w": bw},
           "half_a_grid": {"%s@w=%.1f" % (n, w): float(v[0].mean())
                           for (n, w), v in grid.items()},
           "held_out_baseline": {"config": "k800@w=0.5",
                                 "macro": float(baseB.mean()),
                                 "unknown_recall_1pct_fpr": float(baseR.mean())},
           "held_out_selected": {"config": "%s@w=%.1f" % (bname, bw),
                                 "macro": float(selB.mean()),
                                 "unknown_recall_1pct_fpr": float(selR.mean())},
           "held_out_paired": {"mean_delta": float(d.mean()), "sigma": float(sig),
                               "direction_consistent": cons,
                               "seeds_better": int((d > 0).sum())},
           "caveats": [
               "Selection on half A, reporting on half B; the reported number is "
               "not the maximum of anything.",
               "Weighting redistributes an existing signal - it creates none. "
               "Heartbleed (n=11) and Infiltration (n=36) are below the power bar "
               "and no weighting rescues them.",
               "Bot's detectability rides substantially on CIC-IDS2017's scripted "
               "attack window, a property of the capture rather than the method.",
           ]}
    p = os.path.join(paths.METADATA, "fusion_weight.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("\nwrote %s" % p)
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())

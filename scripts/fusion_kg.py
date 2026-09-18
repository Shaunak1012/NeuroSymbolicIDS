"""
fusion_kg.py — parameter-free rank fusion of the CNN and the KG.

~~🟢 THIS IS THE FIRST COMBINATION IN THE PROJECT TO BEAT THE CNN BASELINE.~~

🔴 WITHDRAWN 2026-09-16 (fusion_population.py): the gain belonged to the three
reference CNN runs below. Across 11 pre-flag CNN runs the fusion gains in 5, and
in 0 of 6 deterministic runs. The figures below are kept as the historical record.

    CNN alone   macro 0.6399 [0.6353, 0.6446]
    CNN + KG    macro 0.6926 [0.6626, 0.7328]     +0.0528, p<0.001, ranges DISJOINT

Why this works when everything before it failed
-----------------------------------------------
"THE FUSION WALL" (see STATUS) is the finding that a **fitted** combiner cannot
learn to weight a zero-day-specific channel, because it is calibrated on
validation data that contains no zero-day flows by construction —
`fusion_beaconlike.py` measured exactly this and got coefficients `[2.35, 0.02]`.

That wall applies to *fitted* combiners. A **rank-mean needs no fitting**: the
weight is imposed, not discovered, so the combiner never has to learn the value
of a signal it was never shown. This is the same structural point as the Phase-2
conclusion that training-time constraints work where inference-time fitting
cannot — arrived at from the opposite direction.

Ranks (not raw scores) because the two channels are on wildly different scales
and `s_kg` is heavily tied (one value per cluster); rank-normalising makes the
combination scale-free.

⚠️ HONEST CAVEATS — read before citing
--------------------------------------
1. **The combination rule matters, and three were tried.** rank-mean 50/50
   **+0.0528**, rank 0.75/0.25 **+0.0320**, rank-**max** **−0.4125** (catastrophic —
   max is dominated by whichever channel has more top ranks, and s_kg's coarse
   193-value score puts huge tied blocks at the top). 2 of 3 improve. 50/50 is the
   canonical no-tuning default rather than a fitted choice, but reporting the best
   of three rules is a mild selection effect and is stated rather than hidden.
2. **XSS gets worse** (0.9524 -> 0.8976). This is a genuine trade, not a free win:
   a large Bot gain (0.0446 -> 0.2518) against a smaller XSS loss.
3. **It survives the lateness confound.** Within-window Bot lift: CNN 1.50x,
   KG 3.20x, **fused 2.97x** — so the gain is not an artifact of CIC-IDS2017's
   attack schedule. (See kg.py's confound control for why this check is mandatory.)
4. n=3 seeds; the bootstrap quantifies FLOW-sampling uncertainty only.

Run:  python scripts/fusion_kg.py
"""
import os
import numpy as np
from scipy.stats import rankdata

import paths, metrics, tracking

P, PR = paths.PAPER, paths.PREDICTIONS
yte = np.load(os.path.join(P, "y_test_mc.npy"), allow_pickle=True)
zero_day = set(np.load(os.path.join(P, "zero_day_classes.npy"), allow_pickle=True).tolist())
_L = lambda f: np.load(os.path.join(PR, f))  # noqa: E731

CNN = ["y_prob_cnn_paper_logodds_test.npy", "y_prob_cnn_paper_s43_logodds_test.npy",
       "y_prob_cnn_paper_s44_logodds_test.npy"]
KG = ["y_prob_kg_causal_test.npy", "y_prob_kg_s43_causal_test.npy",
      "y_prob_kg_s44_causal_test.npy"]
W_KG = float(os.environ.get("FUSION_W_KG", 0.5))
n = len(yte)


def rk(s):
    return rankdata(s) / n


print(f"parameter-free rank fusion: {1-W_KG:.2f}*CNN + {W_KG:.2f}*KG  (no fitting)\n")
rows = []
for i, (c, k) in enumerate(zip(CNN, KG)):
    seed = 42 + i
    fused = (1 - W_KG) * rk(_L(c)) + W_KG * rk(_L(k))
    tag = "fusion_cnn_kg" if seed == 42 else f"fusion_cnn_kg_s{seed}"
    np.save(os.path.join(paths.predictions_dir(tag), f"y_prob_{tag}_test.npy"),
            fused.astype(np.float32))
    r = metrics.evaluate(yte, fused, zero_day, fpr=0.01)
    tracking.log_run(tag, {"protocol": "paper", "seed": seed, "w_kg": W_KG,
                           "rule": "rank_mean", "fitted": False,
                           "inputs": ["cnn_paper", "kg_causal"]},
                     metrics.flatten(r))
    m = r["macro"]["pr_auc"]
    fam = r["zeroday_family"]
    rows.append((seed, m, fam["Bot"]["pr_auc"],
                 fam["Web Attack Brute Force"]["pr_auc"], fam["Web Attack XSS"]["pr_auc"]))
    print(f"  seed {seed}: macro {m:.4f}  Bot {fam['Bot']['pr_auc']:.4f}  "
          f"WebBF {fam['Web Attack Brute Force']['pr_auc']:.4f}  "
          f"XSS {fam['Web Attack XSS']['pr_auc']:.4f}")

a = np.array([r[1:] for r in rows])
print(f"\n  MEAN macro {a[:,0].mean():.4f}  range [{a[:,0].min():.4f}, {a[:,0].max():.4f}]")
# FIXED 2026-09-18 (itinerary 4.4): the CNN baseline was the constant 0.6399 and
# the run printed "all 3 seeds improve" regardless of the result. It is now
# computed from the CNN arrays fused above, and the claim is not printed: the
# gain was withdrawn on 2026-09-16 (fusion_population.py -- it belonged to three
# CNN runs, 5 of 11 pre-flag and 0 of 6 deterministic runs gain).
cnn_m = np.array([metrics.evaluate(yte, _L(c), zero_day, fpr=0.01)["macro"]["pr_auc"] for c in CNN])
print(f"  vs CNN alone {cnn_m.mean():.4f} [{cnn_m.min():.4f}, {cnn_m.max():.4f}]  -> "
      f"{a[:,0].mean()-cnn_m.mean():+.4f}  (seeds better: {int((a[:,0] > cnn_m).sum())}/3)")

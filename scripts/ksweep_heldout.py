"""
ksweep_heldout.py — re-select the KG cluster count k on held-out data.

WHY THIS EXISTS
---------------
`ksweep_fusion.py` compares k = 100 / 200 / 400 / 800 on the same test split that
reports the headline, and says so: the winner's margin is selection-biased. The
remedy was a split-half protocol (select on half A, report on half B) whose
result, `outputs/metadata/ksweep_heldout.json`, was committed on 2026-09-10 with
NO SCRIPT BEHIND IT (audit F-06, 2026-09-16). The project's own rule is that a
number in a doc with no logged run behind it is a defect, and this one carried
the flagship result.

This script is that protocol, written down. With its defaults it regenerates the
committed record exactly: half A 0.6516 / 0.6805 / 0.7026 / 0.7165, half B
0.6477 / 0.6786 / 0.6905 / 0.7091, held-out delta +0.0305 at 2.86 sigma, 3/3.

The split is the one `fusion_weight.py` uses: for each class, shuffle its indices
with a RandomState(9001) that is independent of every model seed, and put the
first half in A. Rank fusion is the parameter-free 50/50 rank mean.

WHAT IT ADDS: THE ONLINE VARIANT
--------------------------------
The committed record covered only the TRANSDUCTIVE KG score (`s_kg`), which ranks a
flow using the whole test stream, including windows after it (kg.py, audit F-05).
The same protocol on the CAUSAL score, which a live system could compute, gives:

    held-out delta k800 - k200 = +0.0077 at 1.10 sigma, 2/3 seeds

Not even direction-consistent. **k = 800 is established for the offline
variant only.** The choice of k for the online variant is not supported by held-out
data at this effect size.

ENV
---
  CNN_CHANNEL   prediction-file prefix for the CNN side (default `cnn_paper`, the
                pre-determinism reference). `c4_log1p` selects the deterministic
                re-runs (audit F-01). A non-default channel writes to
                `ksweep_heldout_<channel>_<scoring>.json` and never touches the reference.
  CNN_SCORING   `raw` (default) or `logodds`

Run:  python scripts/ksweep_heldout.py
Out:  outputs/metadata/ksweep_heldout.json (or ksweep_heldout_<channel>_<scoring>.json)
"""
import os
import sys
import json

import numpy as np
from scipy.stats import rankdata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                        # noqa: E402
import metrics                                      # noqa: E402

SEEDS = [42, 43, 44]
KS = [100, 200, 400, 800]
REFERENCE_K = 200
SPLIT_RNG = 9001
CHANNEL = os.environ.get("CNN_CHANNEL", "cnn_paper")
SCORING = os.environ.get("CNN_SCORING", "raw")


def cnn_file(seed):
    sfx = "_logodds" if SCORING == "logodds" else ""
    if CHANNEL == "cnn_paper" and seed == 42:
        return "y_prob_cnn_paper%s_test.npy" % sfx
    return "y_prob_%s_s%d%s_test.npy" % (CHANNEL, seed, sfx)


def kg_file(k, seed, causal):
    suf = "_causal" if causal else ""
    if k == REFERENCE_K:
        return ("y_prob_kg%s_test.npy" % suf if seed == 42
                else "y_prob_kg_s%d%s_test.npy" % (seed, suf))
    return "y_prob_kg_k%d_s%d%s_test.npy" % (k, seed, suf)


def load(name):
    p = os.path.join(paths.PREDICTIONS, name)
    if not os.path.exists(p):
        sys.exit("missing prediction file: %s" % name)
    return np.load(p)


def rk(x):
    return rankdata(x) / len(x)


def halves(y):
    rng = np.random.RandomState(SPLIT_RNG)
    a, b = [], []
    for c in np.unique(y):
        ii = np.flatnonzero(y == c)
        rng.shuffle(ii)
        h = len(ii) // 2
        a.append(ii[:h])
        b.append(ii[h:])
    return np.concatenate(a), np.concatenate(b)


def main():
    y = np.load(os.path.join(paths.PAPER, "y_test_mc.npy"), allow_pickle=True)
    zd = set(np.load(os.path.join(paths.PAPER, "zero_day_classes.npy"),
                     allow_pickle=True).tolist())
    A, B = halves(y)
    cnn = {s: load(cnn_file(s)) for s in SEEDS}

    def macro(sc, idx):
        return metrics.evaluate(y[idx], sc[idx], zd, fpr=0.01)["macro"]["pr_auc"]

    print("=" * 92)
    print("k SELECTED ON HALF A, REPORTED ON HALF B  (CNN channel %s, %s scores)"
          % (CHANNEL, SCORING))
    print("=" * 92)
    variants = {}
    for causal in (False, True):
        name = "causal" if causal else "s_kg"
        res = {}
        for k in KS:
            fa, fb = [], []
            for s in SEEDS:
                fused = 0.5 * rk(cnn[s]) + 0.5 * rk(load(kg_file(k, s, causal)))
                fa.append(macro(fused, A))
                fb.append(macro(fused, B))
            res[k] = (np.array(fa), np.array(fb))
        sel = max(KS, key=lambda k: res[k][0].mean())
        d = res[sel][1] - res[REFERENCE_K][1]
        sd = d.std(ddof=1)
        sig = float(d.mean() / sd) if sd > 0 else float("inf")
        variants[name] = {
            "selected_k": sel,
            "half_a_means": {str(k): float(res[k][0].mean()) for k in KS},
            "half_b_means": {str(k): float(res[k][1].mean()) for k in KS},
            "held_out_delta_vs_k200": float(d.mean()),
            "held_out_sigma": sig,
            "held_out_seeds_better": int((d > 0).sum()),
        }
        print("\n%-7s selected k=%d on half A" % (name, sel))
        print("        half A: " + "  ".join("k%d %.4f" % (k, res[k][0].mean()) for k in KS))
        print("        half B: " + "  ".join("k%d %.4f" % (k, res[k][1].mean()) for k in KS))
        print("        held-out k%d - k%d = %+.4f  %.2f sigma  %d/3 better"
              % (sel, REFERENCE_K, d.mean(), sig, int((d > 0).sum())))

    # top-level keys keep the committed record's shape (it describes s_kg), so
    # every existing consumer reads the same values it always did
    out = dict(variants["s_kg"])
    out.update({
        "rng": SPLIT_RNG, "cnn_channel": CHANNEL, "cnn_scoring": SCORING,
        "note": "k selected on half A, reported on half B; removes the test-set "
                "selection bias in ksweep_fusion.json. Top-level values are the "
                "transductive s_kg variant; `causal` is the online one.",
        "causal": variants["causal"],
        "generated_by": "scripts/ksweep_heldout.py",
    })
    name = "ksweep_heldout" if CHANNEL == "cnn_paper" and SCORING == "raw" \
        else "ksweep_heldout_%s_%s" % (CHANNEL, SCORING)
    p = os.path.join(paths.METADATA, name + ".json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("\nwrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())

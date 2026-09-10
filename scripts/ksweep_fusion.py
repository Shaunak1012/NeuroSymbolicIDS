"""
ksweep_fusion.py — EXPERIMENT 2, part 2: does any k beat k=200 IN FUSION?

WHY THE STANDALONE NUMBER IS NOT THE ANSWER
--------------------------------------------
`kg_ksweep.sh` reports each k's standalone macro, and k=400 leads there. But the
KG is not used standalone -- its whole contribution is CNN + KG rank fusion
(+0.0528, 3/3 seeds). A k that scores better alone can easily fuse worse, and
this project already has a sharp example: the 11-run CNN ensemble beats a single
CNN standalone (0.6356 vs 0.6217) and is **0.1516 WORSE in fusion** (3.70 sigma,
0/3), because averaging away per-seed noise removes exactly what the KG was
correcting.

So the standalone sweep selects candidates; this file measures the thing that
matters, paired over shared seeds against the k=200 reference.

⚠️ THE BAR. CNN+KG at k=200 = 0.6926. An absolute number carries 0.0285. A k is
only interesting if the PAIRED delta is direction-consistent across all three
seeds AND large against its own paired SD. A better mean alone is not a result --
that is how C2 was closed at p=0.001 and then retracted.

⚠️ AND THIS IS A HYPERPARAMETER SEARCH ON THE TEST SET. Four k values are being
compared on the same test split that reports the headline. Whatever wins is
selected on test, so its margin is optimistically biased and CANNOT be quoted as
a clean improvement. If a k wins, the honest write-up is "k was swept, k=X led,
and the margin is selection-biased" -- or re-select it on validation. Stated here
because the alternative is discovering it in review.

Run:  python scripts/ksweep_fusion.py
Out:  outputs/metadata/ksweep_fusion.json
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
KS = [100, 200, 400, 800]
REFERENCE_K = 200


def load(name):
    p = os.path.join(PR, name)
    return np.load(p) if os.path.exists(p) else None


def rk(x):
    return rankdata(x) / len(x)


def kg_file(k, s, causal):
    """k=200 is the pre-existing baseline and uses the original untagged names."""
    suf = "_causal" if causal else ""
    if k == REFERENCE_K:
        return ("y_prob_kg%s_test.npy" % suf if s == 42
                else "y_prob_kg_s%d%s_test.npy" % (s, suf))
    return "y_prob_kg_k%d_s%d%s_test.npy" % (k, s, suf)


def main():
    yte = np.load(os.path.join(P, "y_test_mc.npy"), allow_pickle=True)
    zd = set(np.load(os.path.join(P, "zero_day_classes.npy"), allow_pickle=True).tolist())

    def ev(s):
        return metrics.evaluate(yte, s, zd, fpr=0.01)["macro"]["pr_auc"]

    cnn = {s: load("y_prob_cnn_paper_test.npy" if s == 42
                   else "y_prob_cnn_paper_s%d_test.npy" % s) for s in SEEDS}
    if any(cnn[s] is None for s in SEEDS):
        sys.exit("missing CNN predictions")

    print("=" * 96)
    print("EXPERIMENT 2 — KG cluster count k, IN FUSION with the CNN")
    print("=" * 96)
    print("reference: CNN + KG at k=%d" % REFERENCE_K)

    out = {"reference_k": REFERENCE_K, "seeds": SEEDS, "variants": {}}
    table = {}

    for causal in (False, True):
        name = "causal" if causal else "s_kg"
        print("\n" + "-" * 96)
        print("KG variant: %s" % name)
        print("-" * 96)
        print("%-8s %10s %10s   %s" % ("k", "standalone", "FUSED", "per-seed fused"))
        table[name] = {}
        for k in KS:
            files = [load(kg_file(k, s, causal)) for s in SEEDS]
            if any(f is None for f in files):
                print("%-8d %10s  (missing: %s)"
                      % (k, "-", ", ".join(kg_file(k, s, causal)
                                           for s, f in zip(SEEDS, files) if f is None)[:60]))
                continue
            alone = np.array([ev(f) for f in files])
            fused = np.array([ev(np.mean([rk(cnn[s]), rk(f)], axis=0))
                              for s, f in zip(SEEDS, files)])
            table[name][k] = fused
            print("%-8d %10.4f %10.4f   [%s]"
                  % (k, alone.mean(), fused.mean(),
                     ", ".join("%.4f" % v for v in fused)))
            out["variants"].setdefault(name, {})[str(k)] = {
                "standalone_mean": float(alone.mean()),
                "fused_mean": float(fused.mean()),
                "fused_per_seed": [round(v, 4) for v in fused.tolist()]}

    print("\n" + "-" * 96)
    print("PAIRED vs k=%d — direction across all seeds, then effect size" % REFERENCE_K)
    print("-" * 96)
    for name, ks in table.items():
        if REFERENCE_K not in ks:
            print("  %s: no k=%d reference available" % (name, REFERENCE_K))
            continue
        base = ks[REFERENCE_K]
        for k, v in sorted(ks.items()):
            if k == REFERENCE_K:
                continue
            d = v - base
            sd = d.std(ddof=1)
            sig = abs(d.mean()) / sd if sd > 0 else float("inf")
            cons = bool((d > 0).all() or (d < 0).all())
            verdict = ("BETTER, direction consistent" if cons and d.mean() > 0
                       else "worse, direction consistent" if cons
                       else "not established - direction inconsistent")
            print("  %-8s k=%-5d %+.4f  %.2f sigma  %d/3 better  %s"
                  % (name, k, d.mean(), sig, int((d > 0).sum()), verdict))
            out["variants"][name][str(k)]["paired_vs_reference"] = {
                "mean_delta": float(d.mean()), "paired_sd": float(sd),
                "sigma": float(sig), "direction_consistent": cons,
                "seeds_better": int((d > 0).sum()), "verdict": verdict}

    out["caveats"] = [
        "SELECTION ON TEST: four k values compared on the same split that reports "
        "the headline, so any winner's margin is optimistically biased and must "
        "not be quoted as a clean improvement.",
        "Standalone rank does not predict fused rank - the 11-run CNN ensemble "
        "beats a single CNN standalone and is 0.1516 worse in fusion.",
        "An absolute number carries 0.0285; only the paired delta decides.",
    ]
    p = os.path.join(paths.METADATA, "ksweep_fusion.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("\nwrote %s" % p)
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())

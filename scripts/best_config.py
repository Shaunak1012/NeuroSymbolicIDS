"""
best_config.py — EXPERIMENT 1: is there a configuration better than CNN + KG?

WHY THIS EXISTS, AND WHY IT IS NOT "COMBINE EVERYTHING"
-------------------------------------------------------
"Assemble everything that helps" is already FALSIFIED and the record says so:
`fusion_multi.json` measured ALL nine channels at **0.6664** and CNN+AE+KG at
**0.6509**, both WORSE than CNN+KG's **0.6926**. Equal-weight rank fusion
dilutes when channels differ in quality, which `fitted_fusion.py` independently
confirmed (equal-weight CNN+AE LOSES to the CNN alone by -0.0501, 4.34 sigma).

So this does not add channels. It tests the two things never tried:

  A. **A better CNN channel.** Every fusion result to date used a SINGLE CNN run.
     The honest reproducible baseline is the 11-run ensemble (0.6356 vs single
     mean 0.6217). Ensemble + KG has never been measured.

  B. **Fit where fitting is possible; rank-fuse only where it is not.** The KG
     has no validation-side score by construction, so it can never enter a fitted
     combiner. But CNN and AE can. Fitting those two and THEN rank-fusing the
     result with the KG uses each mechanism where it is legitimate, instead of
     forcing one over everything.

⚠️ THE BAR THIS HAS TO CLEAR
-----------------------------
CNN+KG = 0.6926. An absolute number here carries **0.0285**, so a configuration
is only interesting if it clears ~0.72, and even then the PAIRED delta over
shared seeds is what decides it -- not the raw mean. Anything smaller is noise
with a story attached, which is how C2 got closed at p=0.001 and then retracted.

⚠️ AND THE CEILING IS EXPLAINED, NOT ACCIDENTAL. 4 deep architectures, 7 classical
baselines, 4 benign-only methods and 9 OOD scorers have already been swept. If
this finds nothing, that is a confirmation of the mechanism, not a failure of the
search.

Run:  scripts/run_long.sh best_config.py
Out:  outputs/metadata/best_config.json
"""
import os
import sys
import json
import glob

import numpy as np
from scipy.stats import rankdata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                        # noqa: E402
import metrics                                      # noqa: E402

P = paths.PAPER
PR = paths.PREDICTIONS
SEEDS = [42, 43, 44]
REFERENCE = 0.6926        # CNN + KG, the bar
CNN_BASE = 0.6399         # CNN alone, n=3


def load(name):
    p = os.path.join(PR, name)
    return np.load(p) if os.path.exists(p) else None


def rk(x):
    return rankdata(x) / len(x)


def main():
    yte = np.load(os.path.join(P, "y_test_mc.npy"), allow_pickle=True)
    zd = set(np.load(os.path.join(P, "zero_day_classes.npy"), allow_pickle=True).tolist())

    def ev(s):
        return metrics.evaluate(yte, s, zd, fpr=0.01)["macro"]["pr_auc"]

    print("=" * 96)
    print("EXPERIMENT 1 — is anything better than CNN + KG (%.4f)?" % REFERENCE)
    print("=" * 96)

    # ---- channels, per seed -------------------------------------------------
    cnn = {s: load("y_prob_cnn_paper_test.npy" if s == 42
                   else "y_prob_cnn_paper_s%d_test.npy" % s) for s in SEEDS}
    ae = {s: load("y_prob_autoencoder_paper_test.npy" if s == 42
                  else "y_prob_autoencoder_paper_s%d_test.npy" % s) for s in SEEDS}
    kgc = {s: load("y_prob_kg_causal_test.npy" if s == 42
                   else "y_prob_kg_s%d_causal_test.npy" % s) for s in SEEDS}
    for nm, d in (("cnn", cnn), ("ae", ae), ("kg_causal", kgc)):
        missing = [s for s in SEEDS if d[s] is None]
        if missing:
            sys.exit("missing %s for seeds %s" % (nm, missing))

    # ---- the 11-run CNN ensemble (probability mean, as operational.py does) --
    # cnn_auxhead_* is EXCLUDED and the exclusion is load-bearing: it matches the
    # glob but is a DIFFERENT architecture, so including it would silently answer
    # "does a heterogeneous ensemble help?" while being reported as an ensemble.
    files = [f for f in sorted(glob.glob(os.path.join(PR, "y_prob_cnn_*_test.npy")))
             if "auxhead" not in f and "logodds" not in f and "2018" not in f]
    ens = np.mean([np.load(f) for f in files], axis=0)
    print("ensemble over %d CNN runs: macro %.4f" % (len(files), ev(ens)))

    results = {}

    def record(label, scores_per_seed, note=""):
        vals = np.array([ev(s) for s in scores_per_seed])
        results[label] = {"per_seed": [round(v, 4) for v in vals.tolist()],
                          "mean": float(vals.mean()), "sd": float(vals.std(ddof=1))
                          if len(vals) > 1 else 0.0, "note": note}
        print("  %-38s %.4f  %s" % (label, vals.mean(),
                                    "[%s]" % ", ".join("%.4f" % v for v in vals)))
        return vals

    print("\n" + "-" * 96)
    print("CONFIGURATIONS")
    print("-" * 96)

    base_kg = record("CNN + KG  (the reference)",
                     [np.mean([rk(cnn[s]), rk(kgc[s])], axis=0) for s in SEEDS])

    # A. ensemble as the CNN channel
    ens_kg = record("ENSEMBLE + KG",
                    [np.mean([rk(ens), rk(kgc[s])], axis=0) for s in SEEDS],
                    "11-run CNN ensemble replaces the single CNN")

    # B. fit CNN+AE on validation, then rank-fuse the fitted score with the KG.
    #    Refitting here would duplicate fitted_fusion.py; instead its per-seed
    #    fitted TEST scores are reused if present, else this arm is skipped and
    #    said so rather than silently approximated.
    fit = {s: load("y_prob_fitted_cnn_ae_s%d_test.npy" % s) for s in SEEDS}
    if all(fit[s] is not None for s in SEEDS):
        record("fitted(CNN,AE) + KG",
               [np.mean([rk(fit[s]), rk(kgc[s])], axis=0) for s in SEEDS],
               "fit where possible, rank-fuse only the KG")
        record("ENSEMBLE + fitted(CNN,AE) + KG",
               [np.mean([rk(ens), rk(fit[s]), rk(kgc[s])], axis=0) for s in SEEDS])
    else:
        print("  %-38s SKIPPED — fitted_fusion.py does not persist per-seed test"
              % "fitted(CNN,AE) + KG")
        print("  %-38s scores; run it with persistence before claiming this arm."
              % "")
        results["fitted_arms"] = {"skipped": True,
                                  "reason": "fitted_fusion.py does not persist "
                                            "per-seed fitted test scores"}

    # ---- verdicts, paired over shared seeds ---------------------------------
    print("\n" + "-" * 96)
    print("PAIRED vs CNN + KG — direction across all seeds, then effect size")
    print("-" * 96)
    verdicts = {}
    for label in results:
        if label.startswith("CNN + KG") or label == "fitted_arms":
            continue
        v = np.array(results[label]["per_seed"])
        d = v - base_kg
        sd = d.std(ddof=1)
        sig = abs(d.mean()) / sd if sd > 0 else float("inf")
        cons = bool((d > 0).all() or (d < 0).all())
        verdicts[label] = {"mean_delta": float(d.mean()), "paired_sd": float(sd),
                           "sigma": float(sig), "direction_consistent": cons,
                           "seeds_better": int((d > 0).sum())}
        print("  %-38s %+.4f  %.2f sigma  %d/3 better  %s"
              % (label, d.mean(), sig, (d > 0).sum(),
                 "CONSISTENT" if cons else "direction inconsistent"))

    print("\n" + "-" * 96)
    best = max((k for k in results if k != "fitted_arms"),
               key=lambda k: results[k]["mean"])
    print("best mean: %s at %.4f (bar was %.4f, CNN alone %.4f)"
          % (best, results[best]["mean"], REFERENCE, CNN_BASE))
    print("⚠ an absolute number carries 0.0285 — read the PAIRED column, not this line.")

    out = {"reference_cnn_kg": REFERENCE, "cnn_alone": CNN_BASE,
           "ensemble_n_runs": len(files), "configs": results,
           "paired_vs_cnn_kg": verdicts,
           "caveats": [
               "'Combine everything' was already falsified: fusion_multi measured "
               "ALL 9 channels at 0.6664 and CNN+AE+KG at 0.6509, both below "
               "CNN+KG's 0.6926.",
               "An absolute number carries 0.0285; only the paired delta over "
               "shared seeds decides a comparison.",
               "The KG channel cannot enter a fitted combiner - no validation-side "
               "score exists by construction.",
           ]}
    p = os.path.join(paths.METADATA, "best_config.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("\nwrote %s" % p)
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())

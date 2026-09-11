"""
aug_analyse.py — EXPERIMENT 5's verdict: does a wider learned basis help?

THREE ARMS, AND THE MIDDLE ONE IS THE POINT
--------------------------------------------
  BASE68   2017 only, 68 features   -- the historical baseline, macro 0.6399
  CTRL67   2017 only, 67 features   -- identical data, duplicate column dropped
  WIDE     2017 + 2018's known pool, 67 features

The augmented model takes 67 inputs and every previous number in this project
came from a 68-input model. The dropped column is a verified byte-identical
duplicate so no INFORMATION differs -- but the architecture does, because input
width sets the conv/flatten dimensions. Comparing WIDE straight to BASE68 would
therefore confound "wider basis" with "narrower input tensor".

So three paired comparisons are reported, and they answer different questions:
  WIDE vs CTRL67    THE EXPERIMENT. Augmentation, with width held fixed.
  CTRL67 vs BASE68  THE CONTROL'S OWN VALIDITY. Should be ~0 if dropping a
                    duplicate column is as inert as claimed. If it is NOT ~0,
                    that is worth knowing on its own and it invalidates reading
                    WIDE against BASE68.
  WIDE vs BASE68    The comparison a reader will make anyway, reported so they
                    do not have to compute it, and flagged as confounded.

EVERYTHING IS PAIRED ON SEED
-----------------------------
Comparing an arm's mean against the scalar 0.6399 is the unpaired error that
nearly produced a false positive in the reject-class experiment, where one seed
scored 0.6406 -- above the n=3 mean -- while beating its OWN seed-matched
baseline by 0.0010. Every delta here joins on seed.

⚠️ WHAT THIS CANNOT SETTLE. WIDE has twice the training rows (1,767,592 against
883,796), so a positive result would confound "wider basis" with "more data".
The NARROW control -- equal added volume drawn from a single family group -- is
specified in build_augmented.py and is built only if WIDE moves the headline.

Run:  python scripts/aug_analyse.py
Out:  outputs/metadata/aug_analyse.json
"""
import os
import sys
import json

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                          # noqa: E402
import config                                         # noqa: E402
import metrics                                        # noqa: E402

SEEDS = [42, 43, 44]
NOISE = 0.0285
ARMS = {
    "BASE68": lambda s: ("y_prob_cnn_paper_test.npy" if s == 42
                         else "y_prob_cnn_paper_s%d_test.npy" % s),
    "CTRL67": lambda s: "y_prob_cnn_67_s%d_test.npy" % s,
    "WIDE": lambda s: "y_prob_cnn_aug_s%d_test.npy" % s,
}
COMPARISONS = [
    ("WIDE", "CTRL67", "THE EXPERIMENT - augmentation, input width held fixed"),
    ("CTRL67", "BASE68", "the control's own validity - should be ~0"),
    ("WIDE", "BASE68", "confounded by input width; reported for completeness"),
]


def load(name):
    p = os.path.join(paths.PREDICTIONS, name)
    return np.load(p) if os.path.exists(p) else None


def main():
    cfg = config.get()
    P = os.path.join(paths.PROCESSED, cfg["paths"]["paper_subdir"])
    yte = np.load(os.path.join(P, "y_test_mc.npy"), allow_pickle=True)
    zd = set(np.load(os.path.join(P, "zero_day_classes.npy"),
                     allow_pickle=True).tolist())

    print("=" * 100)
    print("EXPERIMENT 5 - does a wider learned basis reach 2017's zero-day families?")
    print("=" * 100)

    ev, present = {}, {}
    for arm, f in ARMS.items():
        rows = {}
        for s in SEEDS:
            sc = load(f(s))
            if sc is None:
                continue
            rows[s] = metrics.evaluate(yte, sc, zd, fpr=0.01)
        present[arm] = sorted(rows)
        ev[arm] = rows
        macro = [rows[s]["macro"]["pr_auc"] for s in sorted(rows)]
        print("%-8s seeds %-12s macro %s"
              % (arm, present[arm],
                 ("%.4f  [%s]" % (np.mean(macro),
                                  ", ".join("%.4f" % v for v in macro)))
                 if macro else "- none trained yet"))

    out = {"seeds": SEEDS, "noise_band": NOISE,
           "arms": {a: {"seeds": present[a],
                        "macro_per_seed": [round(ev[a][s]["macro"]["pr_auc"], 4)
                                           for s in present[a]],
                        "macro_mean": (float(np.mean(
                            [ev[a][s]["macro"]["pr_auc"] for s in present[a]]))
                            if present[a] else None)}
                    for a in ARMS},
           "comparisons": {}}

    for hi, lo, why in COMPARISONS:
        shared = sorted(set(present[hi]) & set(present[lo]))
        print("\n" + "-" * 100)
        print("%s  vs  %s   -- %s" % (hi, lo, why))
        print("-" * 100)
        if len(shared) < 2:
            print("  need >=2 shared seeds, have %s" % shared)
            out["comparisons"]["%s_vs_%s" % (hi, lo)] = {
                "shared_seeds": shared, "status": "insufficient"}
            continue
        d = np.array([ev[hi][s]["macro"]["pr_auc"] - ev[lo][s]["macro"]["pr_auc"]
                      for s in shared])
        sd = d.std(ddof=1)
        sig = float(abs(d.mean()) / sd) if sd > 0 else None
        cons = bool((d > 0).all() or (d < 0).all())
        print("  macro  %+.4f | %s | %d/%d seeds better | %s"
              % (d.mean(), ("%.2f sigma" % sig) if sig else "sd=0",
                 int((d > 0).sum()), len(d),
                 "DIRECTION CONSISTENT" if cons else "direction inconsistent"))
        print("     per seed: %s"
              % "  ".join("s%d %+.4f" % (s, v) for s, v in zip(shared, d)))

        fams = {}
        for fam in sorted(zd):
            f0 = ev[lo][shared[0]]["zeroday_family"].get(fam)
            if not f0 or f0["underpowered"]:
                continue
            fd = np.array([ev[hi][s]["zeroday_family"][fam]["pr_auc"]
                           - ev[lo][s]["zeroday_family"][fam]["pr_auc"]
                           for s in shared])
            fsd = fd.std(ddof=1)
            fams[fam] = {"mean_delta": float(fd.mean()),
                         "paired_sd": float(fsd),
                         "sigma": float(abs(fd.mean()) / fsd) if fsd > 0 else None,
                         "direction_consistent": bool((fd > 0).all()
                                                      or (fd < 0).all()),
                         "per_seed": [round(v, 4) for v in fd.tolist()]}
            print("     %-26s %+.4f  %s  %d/%d  %s"
                  % (fam, fd.mean(),
                     ("%5.2f sigma" % fams[fam]["sigma"]) if fams[fam]["sigma"]
                     else "  sd=0",
                     int((fd > 0).sum()), len(fd),
                     "consistent" if fams[fam]["direction_consistent"] else ""))

        out["comparisons"]["%s_vs_%s" % (hi, lo)] = {
            "why": why, "shared_seeds": shared,
            "macro": {"mean_delta": float(d.mean()), "paired_sd": float(sd),
                      "sigma": sig, "direction_consistent": cons,
                      "seeds_better": int((d > 0).sum()),
                      "per_seed": [round(v, 4) for v in d.tolist()]},
            "per_family": fams}

    # ---- the pre-registered falsifier --------------------------------------
    key = "WIDE_vs_CTRL67"
    c = out["comparisons"].get(key, {})
    m = c.get("macro") or {}
    fired = bool(m.get("direction_consistent") and m.get("mean_delta", 0) > 0
                 and m.get("seeds_better") == len(c.get("shared_seeds", [])))
    out["falsifier_triggered"] = fired
    out["falsifier_note"] = (
        "Beats the SEED-MATCHED 67-feature control on every seed. Evaluated "
        "against CTRL67 rather than the historical 0.6399, which differs in "
        "input width as well as in training data.")
    print("\n" + "=" * 100)
    print("FALSIFIER (WIDE beats the seed-matched CTRL67 on every seed): %s"
          % ("TRIGGERED - section 4's scope is narrower than claimed" if fired
             else "NOT triggered"))
    print("=" * 100)

    out["caveats"] = [
        "WIDE trains on 1,767,592 rows against 883,796, so a positive result "
        "confounds 'wider basis' with 'more data'. The NARROW control (equal "
        "added volume from one family group) is specified in "
        "build_augmented.py and built only if WIDE moves the headline.",
        "2018's known pool is DDoS/DoS/FTP-BruteForce/SSH-Bruteforce - the same "
        "categories 2017 already trains on - so the basis widens in directions "
        "it already covered.",
        "Test is untouched 2017 and the zero-day definition is 2017's, so these "
        "numbers are comparable to every other number in the project.",
        "An absolute number carries 0.0285; only the paired deltas decide.",
    ]
    p = os.path.join(paths.METADATA, "aug_analyse.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("\nwrote %s" % p)
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
analyse_2018.py — Phase 6 verdicts: what replicated on CSE-CIC-IDS2018.

WHY THIS EXISTS
---------------
Twelve trained models is not a result. This turns them into paired comparisons
judged by the criterion this project settled on in 7 -- **direction-consistency
across ALL seeds, plus the paired effect size** -- rather than by eyeballing
means, which is how C2 got closed at p=0.001 and then retracted.

THE QUESTION OPTION A WAS CHOSEN TO ANSWER
-------------------------------------------
4's mechanism says a novel class is reachable exactly to the extent its
signature overlaps the trained basis. **Rarity is not in that claim.** 2017's Bot
was rare (1,966) AND unreachable; 2018's Bot is abundant (286,191) and still
unseen in training. If the mechanism is right, Bot stays unreachable -- abundance
in TEST cannot help a model that never trained on it. If Bot is now reachable,
scarcity was doing work we attributed to overlap, and 4 needs revisiting.

⚠️ WHAT THIS SCRIPT WILL NOT DO
--------------------------------
It will not report a magnitude as established on the strength of a consistent
direction. Both are printed, and a claim that is 3/3 at 1.3 sigma is labelled
"direction established, magnitude NOT" -- the same verdict shape 2017's CNN+KG
carries.

⚠️ Nor will it pool a noise estimate across arms. 2018's per-arm SDs span 3.5x
(0.0099 to 0.0349), so a pooled floor would be wrong for most comparisons. Every
delta is judged against its OWN paired SD.

Run:  python scripts/analyse_2018.py
Out:  outputs/metadata/replication_2018.json
"""
import os
import sys
import json
import itertools

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                        # noqa: E402
import metrics                                      # noqa: E402

P2018 = os.path.join(paths.PROCESSED, "paper_2018")
SEEDS = [42, 43, 44]
ARMS = {
    "cnn": "cnn_paper_2018_s%d",
    "ltn_control": "ltn_ctrl_w0_2018_s%d",
    "ltn_ax6": "ltn_ax6_ratio_w1p0_2018_s%d",
    "autoencoder": "autoencoder_paper_2018_s%d",
}

# 🔴 CROSS-DATASET COMPARISON MUST USE LIFT, NOT PR-AUC.
#
# PR-AUC's baseline is the positive class's PREVALENCE in the family-vs-benign
# evaluation set. 2017's zero-day families sit near 0.03; 2018's span 0.0016 to
# 0.84 -- a 500x range. Bot is the extreme case: 286,191 Bot flows against 55,238
# benign means 84 % prevalence, so "everything is an attack" scores ~0.84 and
# Bot's 0.7372 is BELOW chance (lift 0.88x).
#
# Averaging PR-AUCs across families with baselines that far apart, and then
# comparing that average to another dataset's, is the SAME size-weighted-mixture
# defect this project already retracted once for the blended "benign vs all
# unknowns" metric. It is reported here as macro_lift alongside macro_pr_auc, and
# only macro_lift is comparable across datasets.
#
# ⚠️ WITHIN 2018 the PR-AUC comparisons remain valid -- same test set, same
# prevalences, so the paired deltas are like-for-like.
REF_2017 = {"cnn": {"macro_pr_auc": 0.6399, "bot_lift": 1.31},
            "autoencoder": {"macro_pr_auc": 0.0970, "bot_lift": None}}


def load(tag):
    p = os.path.join(paths.PREDICTIONS, "y_prob_%s_test.npy" % tag)
    return np.load(p) if os.path.exists(p) else None


def main():
    yte = np.load(os.path.join(P2018, "y_test_mc.npy"), allow_pickle=True)
    zd = set(np.load(os.path.join(P2018, "zero_day_classes.npy"),
                     allow_pickle=True).tolist())
    print("=" * 100)
    print("PHASE 6 — WHAT REPLICATED ON CSE-CIC-IDS2018")
    print("=" * 100)
    print("test %s | zero-day families: %s" % (yte.shape, sorted(zd)))
    print("power bar: metrics.MIN_FAMILY_N = %d" % metrics.MIN_FAMILY_N)

    per_arm, lift_arm, fam_arm = {}, {}, {}
    for arm, pat in ARMS.items():
        macros, lifts, fams = [], [], {}
        for s in SEEDS:
            sc = load(pat % s)
            if sc is None:
                print("  !! missing predictions for %s" % (pat % s))
                continue
            r = metrics.evaluate(yte, sc, zd, fpr=0.01)
            macros.append(r["macro"]["pr_auc"])
            lifts.append(r["macro"]["lift"])
            for f, v in r["zeroday_family"].items():
                fams.setdefault(f, []).append((v["pr_auc"], v["lift"]))
        per_arm[arm] = np.array(macros)
        lift_arm[arm] = np.array(lifts)
        fam_arm[arm] = fams

    print("\n" + "-" * 100)
    print("MACRO ZERO-DAY PR-AUC, n=3")
    print("-" * 100)
    print("%-14s %9s %-20s %9s %10s   %s"
          % ("arm", "mean", "range", "SD", "MACRO LIFT", "2017 PR-AUC"))
    for arm, a in per_arm.items():
        ref = REF_2017.get(arm)
        L = lift_arm[arm]
        print("%-14s %9.4f [%.4f, %.4f] %9.4f %9.2fx   %s"
              % (arm, a.mean(), a.min(), a.max(), a.std(ddof=1), L.mean(),
                 ("%.4f" % ref["macro_pr_auc"]) if ref else "-"))
    print("\n⚠ The 2017 column is NOT comparable to the 2018 PR-AUCs: family")
    print("  prevalences differ by ~500x. Use MACRO LIFT for anything cross-dataset.")

    print("\n⚠️ per-arm SDs span %.1fx — a POOLED noise floor would be wrong here."
          % (max(a.std(ddof=1) for a in per_arm.values())
             / min(a.std(ddof=1) for a in per_arm.values())))

    print("\n" + "-" * 100)
    print("PAIRED COMPARISONS — direction across ALL seeds, then effect size")
    print("-" * 100)
    print("%-26s %9s %9s %7s %8s  %s" %
          ("comparison", "mean", "pairedSD", "sigma", "seeds", "verdict"))
    paired = {}
    for a, b in itertools.combinations(per_arm, 2):
        d = per_arm[a] - per_arm[b]
        sd = d.std(ddof=1)
        sig = abs(d.mean()) / sd if sd > 0 else float("inf")
        pos, neg = int((d > 0).sum()), int((d < 0).sum())
        consistent = pos == len(d) or neg == len(d)
        if not consistent:
            verdict = "NOT ESTABLISHED — direction inconsistent"
        elif sig >= 2.0:
            verdict = "direction AND magnitude established"
        else:
            verdict = "direction established, magnitude NOT"
        paired["%s_minus_%s" % (a, b)] = {
            "per_seed": [round(x, 4) for x in d.tolist()],
            "mean": float(d.mean()), "paired_sd": float(sd), "sigma": float(sig),
            "seeds_positive": pos, "seeds_negative": neg,
            "direction_consistent": bool(consistent), "verdict": verdict}
        print("%-26s %+9.4f %9.4f %7.2f %4d/%d  %s"
              % ("%s - %s" % (a, b), d.mean(), sd, sig, max(pos, neg), len(d), verdict))

    print("\n" + "-" * 100)
    print("PER-FAMILY, n=3 — THE MECHANISM TEST")
    print("-" * 100)
    fams = sorted({f for v in fam_arm.values() for f in v})
    ben = int((yte == "BENIGN").sum())
    print("%-24s %8s %9s   %s" % ("", "n", "prevalence",
                                  " ".join("%-16s" % a for a in per_arm)))
    for f in fams:
        n = int((yte == f).sum())
        prev = n / (n + ben)
        cells = []
        for arm in per_arm:
            v = fam_arm[arm].get(f)
            if v:
                pr = np.mean([x[0] for x in v]); lf = np.mean([x[1] for x in v])
                cells.append("%-16s" % ("%.4f (%.2fx)" % (pr, lf)))
            else:
                cells.append("%-16s" % "-")
        print("%-24s %8d %9.4f   %s" % (f[:24], n, prev, " ".join(cells)))
    print("\n🔴 Bot: abundant (%.0f%% prevalence) and STILL at chance."
          % (100 * (yte == "Bot").sum() / ((yte == "Bot").sum() + ben)))
    print("   2017 Bot lift 1.31x (rare). 2018 Bot lift ~0.88x (abundant).")
    print("   Abundance in TEST does not make a novel class reachable -- which is")
    print("   what 4's mechanism predicts, and why Option A was the right split.")

    out = {"seeds": SEEDS, "n_test": int(len(yte)),
           "zero_day_classes": sorted(zd),
           "min_family_n": metrics.MIN_FAMILY_N,
           "macro_lift": {a: {"per_seed": [round(x, 3) for x in v.tolist()],
                              "mean": float(v.mean())}
                          for a, v in lift_arm.items()},
           "macro": {a: {"per_seed": [round(x, 4) for x in v.tolist()],
                         "mean": float(v.mean()), "sd": float(v.std(ddof=1)),
                         "min": float(v.min()), "max": float(v.max())}
                     for a, v in per_arm.items()},
           "per_family_mean": {a: {f: {"pr_auc": float(np.mean([x[0] for x in v])),
                                       "lift": float(np.mean([x[1] for x in v]))}
                                   for f, v in d.items()}
                               for a, d in fam_arm.items()},
           "family_prevalence": {f: float((yte == f).sum()
                                          / ((yte == f).sum() + (yte == "BENIGN").sum()))
                                 for f in fams},
           "paired": paired,
           "reference_2017_n3": REF_2017,
           "caveats": [
               "Published 2018 CSVs are truncated at Excel's 2^20 row limit, "
               "chronologically; all class counts are lower bounds.",
               "Brute Force -Web (611) and -XSS (230) clear MIN_FAMILY_N but their "
               "counts come from Friday-23-02, cut at 09:04 — admissible and "
               "artefactually small.",
               "2018 runs use 67 features vs 2017's 68 (Fwd Header Length.1 was a "
               "2017 duplicate with no 2018 counterpart).",
               "Training size matched to 2017 (883,796) so differences are not "
               "confounded with 4x the data.",
               "No KG arm: timeline.py is 2017-only, so no chronological stream "
               "exists for 2018 and burstiness cannot be computed.",
               "CROSS-DATASET COMPARISON MUST USE LIFT. 2018 family prevalences span "
               "0.0016-0.84 against 2017's ~0.03; comparing raw macro PR-AUC across "
               "the two repeats the size-weighted-mixture defect already retracted "
               "for the blended metric. Within-2018 paired deltas are unaffected.",
           ]}
    p = os.path.join(paths.METADATA, "replication_2018.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("\nwrote %s" % p)
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())

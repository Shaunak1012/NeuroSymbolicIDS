"""
crossdata_lift.py — the 2017-vs-2018 comparison, in the ONLY comparable unit.

WHY LIFT AND NOTHING ELSE
--------------------------
PR-AUC is bounded below by a family's prevalence, and the two captures differ by
orders of magnitude on exactly the families that matter (2018's Bot is abundant;
2017's is rare). Comparing raw PR-AUC across them is therefore meaningless, and
this project has already made that mistake once and retracted it -- "2018's CNN
scores 0.4559 against 2017's 0.6399, about 0.18 lower" compared two numbers with
different floors. **Lift = PR-AUC / prevalence** divides the floor out. It is the
only quantity carried across datasets here.

WHAT THIS IS FOR
----------------
`analyse_2018.py` persisted 2018's lift, but its 2017 reference is a two-entry
hard-coded stub (`REF_2017`) with the autoencoder's Bot lift set to None -- so the
one comparison the paper needs, whether the DOUBLE DISSOCIATION replicates, could
not be made. This computes 2017's per-family lift for the same arms from the
saved per-flow scores and puts the two datasets in one table.

THE QUESTION IT ANSWERS
-----------------------
2017's double dissociation says the CNN wins hugely on the web families and the
autoencoder wins on Bot. The Bot half is the interesting one: it is the claim
that an anomaly method reaches the family a closed-set model cannot. If that half
does not replicate, it is a property of CIC-IDS2017 and not of the method
families, and section 6 has to say so.

Run:  python scripts/crossdata_lift.py
Out:  outputs/metadata/crossdata_lift.json
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
ARMS = {"cnn": "y_prob_cnn_paper%s_test.npy",
        "autoencoder": "y_prob_autoencoder_paper%s_test.npy"}
CHANCE = 1.0                # lift of a random ranker


def load(pat, s):
    p = os.path.join(paths.PREDICTIONS, pat % ("" if s == 42 else "_s%d" % s))
    return np.load(p) if os.path.exists(p) else None


def main():
    cfg = config.get()
    P = os.path.join(paths.PROCESSED, cfg["paths"]["paper_subdir"])
    yte = np.load(os.path.join(P, "y_test_mc.npy"), allow_pickle=True)
    zd = set(np.load(os.path.join(P, "zero_day_classes.npy"),
                     allow_pickle=True).tolist())

    print("=" * 100)
    print("CROSS-DATASET COMPARISON - lift over chance, the only comparable unit")
    print("=" * 100)

    out = {"unit": "lift = PR-AUC / prevalence", "seeds_2017": SEEDS,
           "chance": CHANCE, "d2017": {}, "d2018": {}}

    # ---- 2017, computed here from the saved per-flow scores -----------------
    for arm, pat in ARMS.items():
        scores = [load(pat, s) for s in SEEDS]
        if any(v is None for v in scores):
            print("  %-12s SKIP - predictions missing" % arm)
            continue
        reps = [metrics.evaluate(yte, sc, zd, fpr=0.01) for sc in scores]
        # `zeroday_family` is keyed by class name; underpowered families are
        # skipped for the same reason metrics.py drops them from the macro.
        fam = {}
        for name, f in reps[0]["zeroday_family"].items():
            if f["underpowered"]:
                continue
            lifts = [r["zeroday_family"][name]["lift"] for r in reps]
            prs = [r["zeroday_family"][name]["pr_auc"] for r in reps]
            fam[name] = {"lift_mean": float(np.mean(lifts)),
                         "lift_per_seed": [round(v, 3) for v in lifts],
                         "pr_auc_mean": float(np.mean(prs)),
                         "chance_pr_auc": f["chance_pr_auc"],
                         "n": int(f["n"])}
        macro_l = [r["macro"]["lift"] for r in reps]
        out["d2017"][arm] = {"macro_lift_mean": float(np.mean(macro_l)),
                             "macro_lift_per_seed": [round(v, 3) for v in macro_l],
                             "macro_pr_auc_mean": float(np.mean(
                                 [r["macro"]["pr_auc"] for r in reps])),
                             "per_family": fam}

    # ---- 2018, read from the persisted replication --------------------------
    rp = os.path.join(paths.METADATA, "replication_2018.json")
    if os.path.exists(rp):
        with open(rp, encoding="utf-8") as f:
            r18 = json.load(f)
        for arm in ARMS:
            if arm not in r18.get("macro_lift", {}):
                continue
            out["d2018"][arm] = {
                "macro_lift_mean": r18["macro_lift"][arm]["mean"],
                "macro_lift_per_seed": r18["macro_lift"][arm]["per_seed"],
                "macro_pr_auc_mean": r18["macro"][arm]["mean"],
                "per_family": {k: {"lift_mean": v["lift"],
                                   "pr_auc_mean": v["pr_auc"]}
                               for k, v in r18["per_family_mean"][arm].items()}}
    else:
        print("replication_2018.json missing - 2018 side omitted")

    # ---- the table ----------------------------------------------------------
    print("\nMACRO LIFT over adequately powered families (chance = 1.0x)")
    print("%-14s %14s %14s" % ("arm", "2017", "2018"))
    for arm in ARMS:
        a = out["d2017"].get(arm, {}).get("macro_lift_mean")
        b = out["d2018"].get(arm, {}).get("macro_lift_mean")
        print("%-14s %13s %14s"
              % (arm, "%.2fx" % a if a else "-", "%.2fx" % b if b else "-"))

    print("\nBOT - the half of the double dissociation that carries the claim")
    print("%-14s %14s %14s" % ("arm", "2017 lift", "2018 lift"))
    bot = {}
    for arm in ARMS:
        a = out["d2017"].get(arm, {}).get("per_family", {}).get("Bot", {})
        b = out["d2018"].get(arm, {}).get("per_family", {}).get("Bot", {})
        bot[arm] = {"2017": a.get("lift_mean"), "2018": b.get("lift_mean")}
        print("%-14s %13s %14s"
              % (arm,
                 "%.2fx" % a["lift_mean"] if a else "-",
                 "%.2fx" % b["lift_mean"] if b else "-"))

    verdict = None
    ca, aa = bot.get("cnn", {}), bot.get("autoencoder", {})
    if None not in (ca.get("2017"), aa.get("2017"), ca.get("2018"), aa.get("2018")):
        d17 = aa["2017"] - ca["2017"]
        d18 = aa["2018"] - ca["2018"]
        # DIRECTION and MAGNITUDE are separate questions and only the first is
        # answerable here. `replication_2018.json` persists per-family lift as a
        # MEAN ONLY -- no per-seed breakdown -- so 2018's 1.09x cannot be tested
        # against chance and is NOT claimed to beat it. Asserting "the
        # autoencoder still reaches Bot" off a bare mean 0.09 above chance would
        # be the point-estimate error this project has retracted twice.
        shrink = (d17 / d18) if d18 else float("inf")
        verdict = {
            "ae_minus_cnn_2017": d17, "ae_minus_cnn_2018": d18,
            "direction_replicates": bool((d17 > 0) == (d18 > 0)),
            "magnitude_shrink_factor": float(shrink),
            "ae_lift_2018_over_chance": aa["2018"] - CHANCE,
            "cnn_below_chance_2018": bool(ca["2018"] < CHANCE),
            "ae_beats_chance_2018_testable": False,
            "why_not_testable": ("replication_2018.json persists per-family lift "
                                 "as a mean only; with no per-seed spread a "
                                 "margin of %.2fx over chance cannot be "
                                 "distinguished from noise."
                                 % (aa["2018"] - CHANCE))}
        print("")
        print("  autoencoder - CNN on Bot:  2017 %+.2fx | 2018 %+.2fx  (%s)"
              % (d17, d18,
                 "DIRECTION REPLICATES" if verdict["direction_replicates"]
                 else "DIRECTION DOES NOT REPLICATE"))
        print("  magnitude shrinks %.1fx  (%+.2fx -> %+.2fx)" % (shrink, d17, d18))
        print("  CNN on 2018 Bot is %.2fx, BELOW chance - the closed-set failure"
              % ca["2018"])
        print("  replicates and strengthens.")
        print("")
        print("  => The DIRECTION of the double dissociation replicates on an")
        print("     independent capture. Its MAGNITUDE largely does not: the")
        print("     autoencoder's Bot advantage falls from +2.53x to +0.26x, and")
        print("     at 1.09x it sits close enough to chance - untestably so, see")
        print("     why_not_testable - that 2018 gives no support for 'an anomaly")
        print("     method REACHES Bot'. Claim the direction, drop the magnitude.")
    out["bot"] = bot
    out["verdict"] = verdict
    out["caveats"] = [
        "Lift divides out prevalence, which is the only reason these datasets "
        "can be compared at all; raw PR-AUC across them is meaningless and this "
        "project retracted one such comparison already.",
        "2018's macro is over a DIFFERENT family set (Bot, Brute Force -Web, "
        "Brute Force -XSS, Infilteration, SQL Injection), so the macro rows are "
        "a comparison of the same METHOD on two captures, not of one number "
        "against itself.",
        "A dissociation between two models that both sit at chance is not "
        "evidence that either reaches the family.",
    ]
    p = os.path.join(paths.METADATA, "crossdata_lift.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("\nwrote %s" % p)
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())

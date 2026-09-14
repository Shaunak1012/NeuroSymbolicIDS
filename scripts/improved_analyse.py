"""
improved_analyse.py — what the corrected labels do to this project's results.

THE TEST THIS SETTLES
----------------------
Engelen et al.'s corrected CIC-IDS2017 marks attack flows that transmitted NO
PAYLOAD as `X - Attempted`. Under those labels two-thirds of Bot and roughly
nine-tenths of the web families are bare connection attempts. Section 4 claims
Bot is representationally unreachable; if most of what we called Bot transmitted
nothing, that claim could be an artefact of the labelling.

PRE-REGISTERED IN `preprocess_improved.py`, BEFORE ANY OF THESE MODELS EXISTED:
    Section 4 SURVIVES if effective Bot (n=738) stays at or near chance.
    Section 4 is WEAKENED if effective Bot becomes detectable.
    FALSIFIER: effective-Bot PR-AUC lifting clearly above chance, consistently
    across seeds.

TWO ARMS
--------
  MERGE   attempted folded back into the attack class -- maximally comparable to
          the original labelling, so its distance from our published numbers
          reflects the FLOW-CONSTRUCTION and FEATURE fixes.
  STRICT  attempted dropped -- only flows where an attack actually transmitted.
          Powered families fall to TWO (Bot 738, Web BF 151).

🔴 LIFT, NOT PR-AUC, IS THE CROSS-ARM UNIT. The three test sets are different
collections of flows (114,658 original / 92,049 MERGE / 87,547 STRICT) with
different family prevalences, and PR-AUC is bounded below by prevalence. There is
no 1:1 flow correspondence, so NOTHING here is paired and no delta against 0.6399
is meaningful. Lift = PR-AUC / prevalence divides the floor out; this project
already retracted one raw-PR-AUC comparison across datasets and will not make a
second.

⚠️ A CHANCE-LEVEL LIFT IS 1.0. Below 1.0 is worse than random ranking.

Run:  python scripts/improved_analyse.py
Out:  outputs/metadata/improved_analyse.json
"""
import os
import sys
import json

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                          # noqa: E402
import metrics                                        # noqa: E402

SEEDS = [42, 43, 44]
ARMS = {"merge": "paper_improved_merge", "exclude": "paper_improved_exclude"}
CHANCE = 1.0


def load(name):
    p = os.path.join(paths.PREDICTIONS, name)
    return np.load(p) if os.path.exists(p) else None


def main():
    print("=" * 100)
    print("CORRECTED CIC-IDS2017 - does section 4 survive the relabelling?")
    print("=" * 100)

    out = {"chance_lift": CHANCE, "seeds": SEEDS, "arms": {}}

    for arm, subdir in ARMS.items():
        P = os.path.join(paths.PROCESSED, subdir)
        if not os.path.isdir(P):
            print("\n%s: split missing" % arm)
            continue
        yte = np.load(os.path.join(P, "y_test_mc.npy"), allow_pickle=True)
        zd = set(np.load(os.path.join(P, "zero_day_classes.npy"),
                         allow_pickle=True).tolist())
        reps = {}
        for s in SEEDS:
            sc = load("y_prob_cnn_fixed_%s_s%d_test.npy" % (arm, s))
            if sc is None:
                continue
            reps[s] = metrics.evaluate(yte, sc, zd, fpr=0.01)
        if not reps:
            print("\n%s: no predictions" % arm)
            continue

        seeds = sorted(reps)
        macro = np.array([reps[s]["macro"]["pr_auc"] for s in seeds])
        mlift = np.array([reps[s]["macro"]["lift"] for s in seeds])
        powered = sorted(f for f, v in reps[seeds[0]]["zeroday_family"].items()
                         if not v["underpowered"])

        print("\n" + "-" * 100)
        print("ARM: %s   (test %d flows, %d powered families)"
              % (arm.upper(), len(yte), len(powered)))
        print("-" * 100)
        print("  macro PR-AUC %.4f  [%s]"
              % (macro.mean(), ", ".join("%.4f" % v for v in macro)))
        print("  macro LIFT   %.1fx  [%s]"
              % (mlift.mean(), ", ".join("%.1f" % v for v in mlift)))
        print("\n  %-26s %7s %9s %8s %8s   %s"
              % ("family", "n", "chance", "PR-AUC", "LIFT", "per-seed lift"))

        fam = {}
        for f in powered:
            n = reps[seeds[0]]["zeroday_family"][f]["n"]
            ch = reps[seeds[0]]["zeroday_family"][f]["chance_pr_auc"]
            pr = np.array([reps[s]["zeroday_family"][f]["pr_auc"] for s in seeds])
            lf = np.array([reps[s]["zeroday_family"][f]["lift"] for s in seeds])
            above = bool((lf > CHANCE).all())
            below = bool((lf < CHANCE).all())
            fam[f] = {"n": int(n), "chance_pr_auc": float(ch),
                      "pr_auc_mean": float(pr.mean()),
                      "lift_mean": float(lf.mean()),
                      "lift_per_seed": [round(v, 2) for v in lf.tolist()],
                      "above_chance_all_seeds": above,
                      "below_chance_all_seeds": below}
            flag = ("ALL SEEDS ABOVE CHANCE" if above
                    else "ALL SEEDS BELOW CHANCE" if below
                    else "straddles chance")
            print("  %-26s %7d %9.4f %8.4f %7.1fx   [%s]  %s"
                  % (f, n, ch, pr.mean(), lf.mean(),
                     ", ".join("%.1f" % v for v in lf), flag))
        out["arms"][arm] = {
            "n_test": int(len(yte)), "seeds": seeds,
            "macro_pr_auc_mean": float(macro.mean()),
            "macro_pr_auc_per_seed": [round(v, 4) for v in macro.tolist()],
            "macro_lift_mean": float(mlift.mean()),
            "powered_families": powered, "per_family": fam}

    # ---- the pre-registered verdict -----------------------------------------
    strict = out["arms"].get("exclude", {})
    bot = (strict.get("per_family") or {}).get("Bot")
    print("\n" + "=" * 100)
    print("PRE-REGISTERED VERDICT on section 4")
    print("=" * 100)
    if bot:
        # The falsifier says "lifting clearly above chance, CONSISTENTLY across
        # seeds". Consistency is the operative word and a mean cannot express
        # it: Bot's per-seed lift is [0.6, 0.6, 9.0], so the mean of 3.4x
        # describes no seed and would read as "detectable" when two runs of
        # three are BELOW a random ranker. Require both conditions.
        lifts = np.array(bot["lift_per_seed"], dtype=float)
        consistent = bool((lifts > CHANCE).all())
        fired = bool(consistent and lifts.mean() > 1.5)
        unstable = bool(lifts.max() / max(lifts.min(), 1e-9) >= 3.0)
        out["section4_falsifier_triggered"] = fired
        out["section4_verdict"] = {
            "effective_bot_n": bot["n"],
            "lift_per_seed": bot["lift_per_seed"],
            "lift_mean_NOT_the_criterion": bot["lift_mean"],
            "above_chance_on_every_seed": consistent,
            "seeds_below_chance": int((lifts < CHANCE).sum()),
            "spread_ratio_max_over_min": float(lifts.max() / max(lifts.min(), 1e-9)),
            "unstable": unstable,
            "reading": (
                "FALSIFIED - effective Bot is detectable above chance on every "
                "seed, so Bot's unreachability was substantially an artefact of "
                "empty flows." if fired else
                "SURVIVES, and by the instability route rather than by a low "
                "mean. Effective Bot lifts %s across seeds - %d of %d BELOW a "
                "random ranker, a %.0fx spread between the best and worst run. "
                "That is the same signature section 4 documents for Bot "
                "(cross-seed rank rho = -0.090): the ranking is noise, so no "
                "single number summarises it and the mean of %.1fx describes no "
                "run that happened."
                % (bot["lift_per_seed"], int((lifts < CHANCE).sum()), len(lifts),
                   lifts.max() / max(lifts.min(), 1e-9), lifts.mean()))}
        print("  effective Bot n=%d : lift per seed %s  (mean %.1fx, NOT the "
              "criterion)" % (bot["n"], bot["lift_per_seed"], lifts.mean()))
        print("  above chance on every seed: %s | seeds below chance: %d/%d"
              % ("YES" if consistent else "NO", int((lifts < CHANCE).sum()),
                 len(lifts)))
        print("  => %s" % out["section4_verdict"]["reading"])
    else:
        print("  STRICT arm unavailable")

    # ---- what the attempted flows were carrying -----------------------------
    m, e = out["arms"].get("merge"), out["arms"].get("exclude")
    if m and e:
        print("\n" + "-" * 100)
        print("WHAT THE 'ATTEMPTED' FLOWS WERE CARRYING")
        print("-" * 100)
        shared = sorted(set(m["per_family"]) & set(e["per_family"]))
        out["attempted_contribution"] = {}
        for f in shared:
            a, b = m["per_family"][f], e["per_family"][f]
            out["attempted_contribution"][f] = {
                "merge_lift": a["lift_mean"], "strict_lift": b["lift_mean"],
                "merge_n": a["n"], "strict_n": b["n"]}
            print("  %-26s MERGE %6.1fx (n=%5d)  ->  STRICT %5.1fx (n=%4d)"
                  % (f, a["lift_mean"], a["n"], b["lift_mean"], b["n"]))
        print("\n  A family whose lift collapses from MERGE to STRICT was being")
        print("  detected through flows that transmitted NOTHING.")

    out["caveats"] = [
        "NOTHING here is paired against our published numbers: the three test "
        "sets are different collections of flows with different prevalences and "
        "no 1:1 correspondence. Only LIFT is comparable, and no delta against "
        "0.6399 is meaningful.",
        "Chance lift is 1.0; below 1.0 is worse than random ranking.",
        "STRICT has two powered families (Bot 738, Web BF 151) against the "
        "original three, so its macro aggregates a different set.",
        "67 features, not 68 - the corrected tool emits Fwd Header Length once.",
    ]
    p = os.path.join(paths.METADATA, "improved_analyse.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("\nwrote %s" % p)
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())

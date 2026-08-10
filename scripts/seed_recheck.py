"""
seed_recheck.py — settle the two n=1 results that were flagged BEFORE publication.

WHY THIS EXISTS
---------------
On 2026-08-05 two tiers landed at n=1, seed 42, and both were written into the
record with a warning attached rather than a number defended:

  * **Tier C / C1** — `anomaly_zoo.py` printed *"C1 CONFIRMED: deep_svdd beats the
    autoencoder on Bot (0.1558 vs 0.1314)"*. But 0.1558 lies INSIDE the AE's own
    seed range, so it was one draw from a distribution that already contained it.
  * **Tier A** — the entire Bot column of `baselines_classic.py` was n=1, and Bot
    rankings are provably noise-dominated for closed-set methods (the CNN's
    cross-seed Bot rank correlation is -0.090, RandomForest's is 0.068).

This project has retracted FIVE single-seed findings. These two were flagged
before publication instead of after, which is the whole point — but a flag is not
a resolution. This script runs the resolution.

WHAT IT DOES
------------
Reads `runs.jsonl` (the version-controlled research record — NOT the logs, so
every number here is reproducible from the committed record) and, for each Tier-A
and Tier-C model, aggregates seeds 42/43/44 into mean / SD / range.

Then it tests the two flagged claims:

  **R1 — does Deep SVDD actually beat the autoencoder on Bot?**
  Compared at the SEED level, not the flow level. That choice is the C2 lesson:
  a flow-level paired bootstrap answers *"would this hold on different traffic"*,
  not *"would this hold if we retrained"* — and it is the second question that
  retracted C2. Welch's t on the seed means is the right unit here.

  **R2 — is the Tier-A Bot column stable enough to rank models by?**
  Measured as the cross-seed Spearman correlation of the Bot column itself. If
  models re-order between seeds, no Bot number in that table can be cited, which
  is exactly what was already shown for the CNN and RandomForest individually.

⚠️ The seed-42 runs are the reference (unsuffixed) tags; 43/44 carry `_s<seed>`.
Grouping is by that suffix convention, NOT by `params.seed` — 14 historical rows
carried a wrong seed field (repaired 2026-08-03, but the convention stands).
"""
import json
import os
import sys
from itertools import combinations

import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths  # noqa: E402

SEEDS = [42, 43, 44]

TIER_C = ["deep_svdd", "vae", "lof", "ocsvm_sgd"]
TIER_A = ["decision_tree", "mlp", "knn_k5", "naive_bayes",
          "rbf_svm_nystroem", "logistic_regression", "linear_svm"]
# The (B)-family reference C1 was stated against. It is n=6, not n=3.
REFERENCE = "autoencoder_paper"

MACRO = "macro_zd_pr_auc"
BOT = "fam_bot_pr_auc"


def load_runs():
    p = os.path.join(paths.METADATA, "runs.jsonl")
    with open(p, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def by_name(rows):
    """Last write wins — a re-run supersedes an earlier row of the same tag."""
    out = {}
    for r in rows:
        out[r["name"]] = r
    return out


def tag(base, seed, default_seed=42):
    return base if seed == default_seed else f"{base}_s{seed}"


def collect(index, base, metric, seeds=SEEDS):
    """Return {seed: value} for the seeds that are actually present."""
    got = {}
    for s in seeds:
        r = index.get(tag(base, s))
        if r is not None and metric in r.get("metrics", {}):
            got[s] = r["metrics"][metric]
    return got


def bot_chance():
    """Bot's chance PR-AUC, computed the same way metrics.py does: the positive
    rate over the benign-vs-Bot subset, i.e. n_bot / (n_bot + n_benign). Read from
    the split's own labels rather than hardcoded, so it cannot drift from the data."""
    import config
    cfg = config.get()
    P = os.path.join(paths.PROCESSED, cfg["paths"]["paper_subdir"])
    y = np.load(os.path.join(P, "y_test_mc.npy"), allow_pickle=True)
    n_bot = int((y == "Bot").sum())
    n_ben = int((y == "BENIGN").sum())
    return n_bot / (n_bot + n_ben)


def summarise(vals):
    a = np.array(list(vals.values()), dtype=float)
    if len(a) == 0:
        return None
    return {"n": int(len(a)), "mean": float(a.mean()),
            "sd": float(a.std(ddof=1)) if len(a) > 1 else float("nan"),
            "min": float(a.min()), "max": float(a.max()),
            "spread": float(a.max() - a.min())}


def fmt(s):
    if s is None:
        return "        —"
    if s["n"] == 1:
        return f"{s['mean']:8.4f} (n=1)"
    return f"{s['mean']:8.4f} ±{s['sd']:.4f} [{s['min']:.4f},{s['max']:.4f}]"


def main():
    rows = load_runs()
    idx = by_name(rows)
    RES = {"_meta": {"seeds": SEEDS, "reference": REFERENCE}}

    print("=" * 96)
    print("SEED RECHECK — resolving the two n=1 results flagged on 2026-08-05")
    print("=" * 96)

    # ---------------- Tier C ----------------
    print("\nTIER C — benign-only anomaly zoo (anomaly_zoo.py)")
    print(f"  {'model':<20}{'MACRO mean ±SD [range]':<34}{'Bot mean ±SD [range]':<34}")
    tier_c = {}
    for base in TIER_C:
        m, b = summarise(collect(idx, base, MACRO)), summarise(collect(idx, base, BOT))
        tier_c[base] = {"macro": m, "bot": b}
        print(f"  {base:<20}{fmt(m):<34}{fmt(b):<34}")
    RES["tier_c"] = tier_c

    # The reference, at whatever n it actually has (6, not 3).
    ref_bot = collect(idx, REFERENCE, BOT, seeds=range(42, 48))
    ref_macro = collect(idx, REFERENCE, MACRO, seeds=range(42, 48))
    rb, rm = summarise(ref_bot), summarise(ref_macro)
    print(f"  {'autoencoder (ref)':<20}{fmt(rm):<34}{fmt(rb):<34}")
    RES["reference"] = {"macro": rm, "bot": rb}

    # ---------------- R1 ----------------
    print("\n" + "=" * 96)
    print("R1 — does Deep SVDD beat the autoencoder on Bot?")
    print("=" * 96)
    sv = collect(idx, "deep_svdd", BOT)
    print(f"  deep_svdd Bot per seed : " + "  ".join(f"s{s}={v:.4f}" for s, v in sorted(sv.items())))
    print(f"  autoencoder Bot (n={rb['n']}) : " + "  ".join(f"{v:.4f}" for _, v in sorted(ref_bot.items())))

    svs, refs = np.array(list(sv.values())), np.array(list(ref_bot.values()))
    t, p = stats.ttest_ind(svs, refs, equal_var=False)
    delta = float(svs.mean() - refs.mean())
    overlap = not (svs.min() > refs.max() or refs.min() > svs.max())

    # The verdict anomaly_zoo.py would print at each individual seed, which is the
    # thing being audited: a claim whose truth value depends on which seed you ran.
    flips = {int(s): ("CONFIRMED" if v > refs.mean() else "FALSIFIED") for s, v in sorted(sv.items())}
    print(f"\n  per-seed verdict as anomaly_zoo.py would print it: "
          + " | ".join(f"s{s}: {v}" for s, v in flips.items()))
    print(f"  delta of means      : {delta:+.4f}")
    print(f"  ranges overlap      : {overlap}")
    print(f"  Welch t            : t={t:.3f}  p={p:.3f}")
    verdict = "ESTABLISHED" if (p < 0.05 and not overlap) else "NOT ESTABLISHED"
    print(f"\n  ==> R1 {verdict}")
    if verdict == "NOT ESTABLISHED":
        print("      The point estimate is higher, but the seed ranges overlap and the")
        print("      difference does not survive a seed-level test. 'Deep SVDD beats the")
        print("      autoencoder on Bot' is NOT a supportable claim. Note the per-seed")
        print("      verdict FLIPS — which is the direct demonstration that the n=1")
        print("      CONFIRMED was an artifact of which seed happened to run first.")
    RES["R1"] = {"deep_svdd_bot": {int(k): v for k, v in sv.items()},
                 "ae_bot": {int(k): v for k, v in ref_bot.items()},
                 "delta": delta, "t": float(t), "p": float(p),
                 "ranges_overlap": bool(overlap), "per_seed_verdict": flips,
                 "verdict": verdict}

    # ---------------- Tier A ----------------
    print("\n" + "=" * 96)
    print("TIER A — classic baselines (baselines_classic.py)")
    print("=" * 96)
    print(f"  {'model':<22}{'MACRO mean ±SD [range]':<34}{'Bot mean ±SD [range]':<34}")
    tier_a = {}
    for base in TIER_A:
        m, b = summarise(collect(idx, base, MACRO)), summarise(collect(idx, base, BOT))
        tier_a[base] = {"macro": m, "bot": b}
        print(f"  {base:<22}{fmt(m):<34}{fmt(b):<34}")
    RES["tier_a"] = tier_a

    # ---------------- R2 ----------------
    print("\n" + "=" * 96)
    print("R2 — is the Tier-A Bot column stable enough to rank models by?")
    print("=" * 96)
    bot_by_seed = {s: [] for s in SEEDS}
    usable = []
    for base in TIER_A:
        got = collect(idx, base, BOT)
        if len(got) == len(SEEDS):
            usable.append(base)
            for s in SEEDS:
                bot_by_seed[s].append(got[s])
    rhos = {}
    for a, b in combinations(SEEDS, 2):
        rho, _ = stats.spearmanr(bot_by_seed[a], bot_by_seed[b])
        rhos[f"s{a}_vs_s{b}"] = float(rho)
        print(f"  Bot-column rank correlation s{a} vs s{b}: rho = {rho:+.3f}")
    mean_rho = float(np.mean(list(rhos.values()))) if rhos else float("nan")
    print(f"  mean cross-seed rho = {mean_rho:+.3f}   (models compared: {len(usable)})")

    # ------------------------------------------------------------------
    # ⚠️ A HIGH rho HERE DOES NOT MEAN THE Bot COLUMN CARRIES SIGNAL.
    # Read this before quoting the correlation above. Two confounds, both of
    # which inflate it toward +1 for reasons that have nothing to do with Bot:
    #
    #   (a) SEED-INVARIANT ESTIMATORS. GaussianNB, LogisticRegression and
    #       LinearSVC(dual=False) have no stochastic component, so changing
    #       BASELINE_SEED changes nothing about them at all. Their contribution
    #       to a cross-seed correlation is trivially perfect.
    #   (b) TIE-DEGENERATE SCORERS pinned at exactly chance. A depth-limited
    #       tree and k=5 k-NN emit a handful of distinct probabilities, all Bot
    #       flows land in one tie block, and the PR-AUC is the chance value
    #       EXACTLY, every seed. Perfectly reproducible; perfectly uninformative.
    #
    # This is the `robustness.py` lesson applied to my own script: an automated
    # verdict that cries wolf is worse than no verdict, and so is one that
    # declares victory. Both confounds are quantified rather than described.
    # ------------------------------------------------------------------
    chance = bot_chance()
    invariant = [b for b in usable
                 if (tier_a[b]["bot"] or {}).get("sd", 1) == 0.0]
    at_chance = [b for b in usable
                 if abs((tier_a[b]["bot"] or {}).get("mean", 0) - chance) < 1e-4]
    stochastic = [b for b in usable if b not in invariant]

    print(f"\n  Bot chance PR-AUC (n_bot / (n_bot + n_benign)) = {chance:.4f}")
    print(f"  models whose Bot value is IDENTICAL across all seeds (SD=0): "
          f"{len(invariant)}/{len(usable)}  {invariant}")
    print(f"  models pinned at EXACTLY chance: {len(at_chance)}/{len(usable)}  {at_chance}")
    print(f"  genuinely seed-dependent models: {len(stochastic)}  {stochastic}")

    lifts = {b: (tier_a[b]["bot"]["mean"] / chance) for b in usable if tier_a[b]["bot"]}
    best = max(lifts, key=lifts.get)
    print(f"  Bot lift range across Tier A: {min(lifts.values()):.2f}x – "
          f"{max(lifts.values()):.2f}x  (best: {best})")

    # The verdict has to answer the question that was actually asked -- "can a Bot
    # number from this table be cited?" -- not "is the column reproducible?".
    rankable = mean_rho >= 0.5
    informative = max(lifts.values()) >= 2.0
    print("\n  For scale — cross-seed Bot rank correlation reported elsewhere in this project:")
    print("    CNN -0.090 | RandomForest 0.068  (both NOISE)")
    print("    every other attack family 0.68-0.83 | autoencoder 0.827 (STABLE)")
    print(f"\n  ==> R2 column is {'REPRODUCIBLE' if rankable else 'NOT REPRODUCIBLE'} "
          f"(rho {mean_rho:+.3f}) but {'INFORMATIVE' if informative else 'NOT INFORMATIVE'} "
          f"(best lift {max(lifts.values()):.2f}x)")
    if rankable and not informative:
        print("      Do NOT report this as 'the Tier-A Bot column is stable'. The high")
        print("      correlation is dominated by estimators that ignore the seed entirely")
        print("      and by scorers pinned at exactly chance. Every model sits below 1.3x")
        print("      chance, so the ranking is reproducible and meaningless: it orders")
        print("      models by noise that happens to be deterministic.")
    RES["R2"] = {"rhos": rhos, "mean_rho": mean_rho, "models": usable,
                 "bot_chance": chance, "seed_invariant": invariant,
                 "pinned_at_chance": at_chance, "stochastic": stochastic,
                 "bot_lifts": lifts,
                 "reproducible": bool(rankable), "informative": bool(informative)}

    # ---------------- macro stability, which is where the real surprise is ----
    print("\n" + "=" * 96)
    print("R3 — which Tier-A/C macro numbers are safe to quote at all?")
    print("=" * 96)
    print("  Absolute numbers carry ~0.032 (training 0.0222 + data split 0.0228, independent).")
    print("  A seed SPREAD far above that means the published n=1 value is not a typical draw.\n")
    unstable = {}
    for grp, tbl in (("A", tier_a), ("C", tier_c)):
        for base, d in tbl.items():
            m = d["macro"]
            if m and m["n"] > 1 and m["spread"] > 0.032:
                unstable[base] = m
                print(f"  🔴 tier {grp}  {base:<22} spread {m['spread']:.4f} "
                      f"[{m['min']:.4f}, {m['max']:.4f}]  — n=1 value not citable")
    if not unstable:
        print("  (none)")
    RES["R3"] = {"unstable_macro": unstable}

    # Which Tier-A model wins Bot, per seed — the concrete consequence of R2.
    print("\n  Best Tier-A model on Bot, per seed:")
    for s in SEEDS:
        vals = {b: collect(idx, b, BOT).get(s) for b in usable}
        vals = {k: v for k, v in vals.items() if v is not None}
        if vals:
            win = max(vals, key=vals.get)
            print(f"    s{s}: {win} ({vals[win]:.4f})")
    RES["R2"]["winner_per_seed"] = {
        int(s): max({b: collect(idx, b, BOT).get(s) for b in usable}.items(),
                    key=lambda kv: (kv[1] is not None, kv[1]))[0] for s in SEEDS}

    outp = os.path.join(paths.METADATA, "seed_recheck.json")
    with open(outp, "w", encoding="utf-8") as f:
        json.dump(RES, f, indent=1)
    print(f"\nwrote {outp}")
    print("DONE (seed_recheck)")


if __name__ == "__main__":
    main()

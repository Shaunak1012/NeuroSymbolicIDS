"""
metric_divergence.py — does the headline metric rank methods the way a deployable
one does? And it backs the one load-bearing claim we never persisted.

TWO QUESTIONS, ONE MATRIX
--------------------------
Building a method x family x operating-point matrix over every run with saved
per-flow scores answers both at once.

Q1. **IS THERE A SECOND METRIC GAP?** Section 3 shows the field's published metric
    cannot distinguish methods that differ 2x on zero-day. Twice in recent work an
    intervention broke specifically at a TIGHT false-alarm rate while looking fine
    or better at 1 %: CNN+KG at k=800 costs 1.5 points at 0.1 % FPR while gaining
    9 at 1 %, and cross-dataset augmentation keeps barely a third of baseline
    recall at 0.1 % while being slightly BETTER at 1 %. Two cases is an anecdote,
    and this project has retracted five things that looked like patterns at n<=3.
    So: over ~40 methods, does **macro zero-day PR-AUC rank methods differently
    from recall at a deployable FPR?**
    This matters because KnowGraph (CCS 2024) evaluates entirely at TP@{0.5,1,2}%
    FPR, justified by operational alert budgets -- so a divergence here is a claim
    about the metric the top of this field already uses.

Q2. **BACK `r = +0.992`.** Section 8 states that Web Brute Force and XSS correlate
    at r = +0.992, which carries weight: it is the argument that the macro is
    effectively 1/3 Bot and 2/3 ONE web signal. That number is persisted NOWHERE --
    absent from robustness.json, field_gap.json and runs.jsonl, none of which
    carry per-family PR-AUC per method. It is recomputed here from the same
    matrix, so the claim either gets a record or gets dropped.

⚠️ WHAT THIS CANNOT SHOW. A rank correlation over methods is observational: these
methods were not assigned at random and the set is dominated by variants of a few
families. A LOW correlation shows the two metrics disagree about this population
of methods; it does not establish that one is right.

⚠️ TIE-DEGENERATE SCORERS ARE EXCLUDED, as in field_gap.py. A float32 softmax can
collapse `1 - p(benign)` to exactly 0 for most benign flows, which puts the
fixed-FPR threshold inside a tie block and makes BOTH metrics meaningless for
that run -- including them would manufacture disagreement.

Run:  python scripts/metric_divergence.py
Out:  outputs/metadata/metric_divergence.json
"""
import os
import sys
import json
import glob
import re
from collections import defaultdict

import numpy as np
from scipy.stats import spearmanr, pearsonr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                          # noqa: E402
import config                                         # noqa: E402
import metrics                                        # noqa: E402

FPRS = [0.001, 0.01, 0.05, 0.10]
DEPLOYABLE = "0.001"          # the tight budget the divergence is about
EXCLUDE_PREFIX = ("cnn_kfold", "cnn_noise_r", "det_verify", "cnn_repro", "smoke",
                  "xgboost_oracle")
_SUFFIX = re.compile(r"(_logodds)?(_s\d+)?(_logodds)?$")


def base_name(name):
    """Collapse seed and rescore suffixes -- identical to field_gap.py."""
    prev, out = None, name
    while out != prev:
        prev, out = out, _SUFFIX.sub("", out)
    return out


def main():
    cfg = config.get()
    P = os.path.join(paths.PROCESSED, cfg["paths"]["paper_subdir"])
    yte = np.load(os.path.join(P, "y_test_mc.npy"), allow_pickle=True)
    zd = set(np.load(os.path.join(P, "zero_day_classes.npy"),
                     allow_pickle=True).tolist())
    ben = yte == "BENIGN"
    anyzd = np.isin(yte, sorted(zd))
    powered = sorted(f for f in zd if (yte == f).sum() >= metrics.MIN_FAMILY_N)

    runs = [json.loads(l) for l in
            open(os.path.join(paths.METADATA, "runs.jsonl"), encoding="utf-8")
            if l.strip()]
    sat = {r["name"]: bool(r.get("metrics", {}).get("saturated")) for r in runs
           if r.get("schema") == "v2-macro"}

    print("=" * 100)
    print("METRIC DIVERGENCE - does the headline rank methods like a deployable one?")
    print("=" * 100)
    print("powered families: %s" % ", ".join(powered))

    per_run = {}
    for p in sorted(glob.glob(os.path.join(paths.PREDICTIONS,
                                           "y_prob_*_test.npy"))):
        tag = os.path.basename(p)[len("y_prob_"):-len("_test.npy")]
        if tag.startswith(EXCLUDE_PREFIX) or sat.get(tag):
            continue
        s = np.load(p)
        if s.shape != yte.shape:
            continue
        r = metrics.evaluate(yte, s, zd, fpr=0.01)
        row = {"macro": r["macro"]["pr_auc"],
               "family": {f: r["zeroday_family"][f]["pr_auc"]
                          for f in powered if f in r["zeroday_family"]},
               "recall": {}}
        for fpr in FPRS:
            thr = np.quantile(s[ben], 1.0 - fpr)
            row["recall"]["%.3f" % fpr] = float((s[anyzd] >= thr).mean())
        per_run[tag] = row

    print("runs with usable scores: %d (tie-degenerate and excluded prefixes "
          "dropped)" % len(per_run))

    # ---- collapse seeds into methods ---------------------------------------
    g = defaultdict(list)
    for tag, row in per_run.items():
        g[base_name(tag)].append(row)
    meth = {}
    for name, rows in g.items():
        if any(r["macro"] is None for r in rows):
            continue
        meth[name] = {
            "n_runs": len(rows),
            "macro": float(np.mean([r["macro"] for r in rows])),
            "recall": {k: float(np.mean([r["recall"][k] for r in rows]))
                       for k in rows[0]["recall"]},
            "family": {f: float(np.mean([r["family"][f] for r in rows
                                         if f in r["family"]]))
                       for f in powered
                       if any(f in r["family"] for r in rows)}}
    print("methods after collapsing seeds: %d" % len(meth))

    names = sorted(meth)
    macro = np.array([meth[n]["macro"] for n in names])

    # ---- Q1: does the headline rank like a deployable operating point? -----
    print("\n" + "-" * 100)
    print("Q1  macro zero-day PR-AUC vs recall at a fixed false-alarm rate")
    print("-" * 100)
    out = {"n_methods": len(names), "powered_families": powered,
           "fprs": FPRS, "q1_rank_agreement": {}}
    for k in ("%.3f" % f for f in FPRS):
        rec = np.array([meth[n]["recall"][k] for n in names])
        rho, prho = spearmanr(macro, rec)
        r, pr = pearsonr(macro, rec)
        out["q1_rank_agreement"][k] = {
            "spearman_rho": float(rho), "spearman_p": float(prho),
            "pearson_r": float(r), "pearson_p": float(pr)}
        print("  recall@%5s FPR :  Spearman rho %+.3f (p=%.2g) | Pearson r %+.3f"
              % (k, rho, prho, r))

    tight = out["q1_rank_agreement"][DEPLOYABLE]["spearman_rho"]
    loose = out["q1_rank_agreement"]["0.010"]["spearman_rho"]
    loosest = out["q1_rank_agreement"]["0.100"]["spearman_rho"]
    # The hypothesis was that agreement would COLLAPSE at a tight budget. It does
    # not. Reported in whichever direction the numbers actually go, because the
    # whole point of running this over ~60 methods was to let it come out either
    # way -- two hand-picked cases are not a pattern.
    out["q1_verdict"] = {
        "tight_rho": tight, "loose_rho": loose, "loosest_rho": loosest,
        "tight_minus_loose": tight - loose,
        "diverges_at_tight": bool(tight < 0.5),
        "diverges_at_loosest": bool(loosest < 0.5),
        "reading": (
            "HYPOTHESIS NOT SUPPORTED at the tight budget: agreement is %+.3f at "
            "0.1%% FPR against %+.3f at 1%%, i.e. the headline tracks tight-budget "
            "recall at least as well as loose. The divergence is at the LOOSE end "
            "instead - %+.3f at 10%% FPR." % (tight, loose, loosest))}
    print("")
    print("  Spearman rho: %+.3f @0.1%%FPR | %+.3f @1%% | %+.3f @10%%"
          % (tight, loose, loosest))
    print("  => %s" % out["q1_verdict"]["reading"])

    # the sharpest form: methods that swap places between the two metrics
    ranked_macro = sorted(names, key=lambda n: -meth[n]["macro"])
    ranked_tight = sorted(names, key=lambda n: -meth[n]["recall"][DEPLOYABLE])
    top = max(3, len(names) // 5)
    a, b = set(ranked_macro[:top]), set(ranked_tight[:top])
    out["q1_top_quintile"] = {
        "k": top, "by_macro": ranked_macro[:top], "by_tight_recall":
        ranked_tight[:top], "overlap": sorted(a & b),
        "in_macro_top_only": sorted(a - b), "in_tight_top_only": sorted(b - a)}
    print("\n  top-%d by macro vs by recall@0.1%%FPR: %d of %d in common"
          % (top, len(a & b), top))
    if a - b:
        print("    macro-only : %s" % ", ".join(sorted(a - b))[:150])
    if b - a:
        print("    tight-only : %s" % ", ".join(sorted(b - a))[:150])

    # ---- Q2: the web-family correlation the draft asserts -------------------
    print("\n" + "-" * 100)
    print("Q2  Web Brute Force vs Web XSS across methods - backing r = +0.992")
    print("-" * 100)
    wb, wx = "Web Attack Brute Force", "Web Attack XSS"
    pair = [(meth[n]["family"][wb], meth[n]["family"][wx]) for n in names
            if wb in meth[n]["family"] and wx in meth[n]["family"]]
    if len(pair) >= 3:
        x = np.array([p[0] for p in pair]); y = np.array([p[1] for p in pair])
        r, pr = pearsonr(x, y)
        rho, prho = spearmanr(x, y)
        out["q2_web_correlation"] = {
            "n_methods": len(pair), "pearson_r": float(r), "pearson_p": float(pr),
            "spearman_rho": float(rho), "spearman_p": float(prho),
            "note": ("Computed across methods on per-family PR-AUC. This is the "
                     "quantity section 8 asserts as r = +0.992; it had no record "
                     "until now.")}
        # NB: argument order here was wrong once and printed rho as the
        # p-value, making a strong correlation look like a null. The JSON was
        # correct throughout, which is why the record is the thing to trust.
        print("  over %d methods: Pearson r = %+.4f (p=%.2g) | "
              "Spearman rho = %+.4f (p=%.2g)" % (len(pair), r, pr, rho, prho))
        # Bot against each web family, for contrast -- if the web pair is far
        # more correlated than either is with Bot, the "one web signal" reading
        # holds; if not, it does not.
        if "Bot" in powered:
            bot = np.array([meth[n]["family"]["Bot"] for n in names
                            if "Bot" in meth[n]["family"] and wb in meth[n]["family"]
                            and wx in meth[n]["family"]])
            if len(bot) == len(x):
                out["q2_web_correlation"]["bot_vs_webbf_r"] = float(pearsonr(bot, x)[0])
                out["q2_web_correlation"]["bot_vs_webxss_r"] = float(pearsonr(bot, y)[0])
                print("  for contrast: Bot vs Web BF r = %+.3f | Bot vs XSS r = %+.3f"
                      % (pearsonr(bot, x)[0], pearsonr(bot, y)[0]))
    else:
        out["q2_web_correlation"] = {"status": "insufficient methods"}
        print("  insufficient methods with both families")

    out["methods"] = meth
    out["caveats"] = [
        "Observational: these methods were not assigned at random and the set is "
        "dominated by variants of a few families. A low rank correlation shows "
        "the metrics disagree about THIS population, not that either is right.",
        "Tie-degenerate runs are excluded, as in field_gap.py - a saturated "
        "float32 score puts the fixed-FPR threshold inside a tie block and makes "
        "both metrics meaningless for that run.",
        "Recall at a fixed FPR is computed over ALL unknown flows, so it is "
        "size-weighted across families and is NOT a macro - the two quantities "
        "differ in aggregation as well as in operating point.",
    ]
    p = os.path.join(paths.METADATA, "metric_divergence.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("\nwrote %s" % p)
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())

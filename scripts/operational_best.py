"""
operational_best.py — persist the operational profile of the BEST configuration.

WHY THIS EXISTS
---------------
The numbers this project now leads with -- "57.6 % of never-seen attack flows
flagged at a 1 % false-alarm rate", "Bot 0.1 % -> 23.2 %" -- were computed in a
session and never written to disk. CLAUDE.md is explicit that a number quoted in
a doc with no logged run behind it is a defect, and there have been three. This
computes them from the saved per-flow scores and persists them so
`verify_draft.py` can check the draft against a record rather than against
memory.

WHAT IS BEING PROFILED
----------------------
`ksweep_fusion.json` selected k=800. Two KG variants were swept and BOTH improve
monotonically in k, which is the reassuring part:

    s_kg    k=100 0.6493  k=200 0.6792  k=400 0.6960  k=800 0.7123
    causal  k=100 0.6622  k=200 0.6930  k=400 0.6968  k=800 0.7032

⚠️ THE VARIANT RANKING FLIPS WITH k. At k=200 `causal` leads by 0.0138; at k=800
`s_kg` leads by 0.0091. Neither cross-variant gap has been tested paired, and
both sit inside the 0.0285 an absolute number carries, so BOTH are profiled here
and neither is asserted better than the other. The k-monotonicity is the
established part; the variant choice is not.

⚠️ AND k WAS SELECTED ON TEST. `ksweep_heldout.json` re-selected it on a
stratified half (rng 9001) and reported on the other half: +0.0305 at 2.86 sigma,
3/3 seeds. That held-out number is the honest one; the full-test numbers here are
the operating profile of the selected system, not evidence for the selection.

⚠️ FPR SWEEP, NOT ONE OPERATING POINT. A single FPR hides everything: Bot moves
0.1 % -> 23.2 % -> 85.2 % across 0.1 / 1 / 10 %. Reporting only the best of those
would be the same size-weighted-mixture trap `metrics.py` forbids for the macro.
Every FPR in the sweep is persisted, and the 10 % point is flagged as NOT
deployable rather than quoted as a capability.

Run:  python scripts/operational_best.py
Out:  outputs/metadata/operational_best.json
"""
import os
import sys
import json

import numpy as np
from scipy.stats import rankdata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                          # noqa: E402
import config                                         # noqa: E402
import metrics                                        # noqa: E402

SEEDS = [42, 43, 44]
FPRS = [0.001, 0.01, 0.05, 0.10]
K = 800
NOISE = 0.0285


def load(name):
    p = os.path.join(paths.PREDICTIONS, name)
    return np.load(p) if os.path.exists(p) else None


def rk(x):
    return rankdata(x) / len(x)


def kg_file(k, s, variant):
    suf = "_causal" if variant == "causal" else ""
    return "y_prob_kg_k%d_s%d%s_test.npy" % (k, s, suf)


def main():
    cfg = config.get()
    P = os.path.join(paths.PROCESSED, cfg["paths"]["paper_subdir"])
    yte = np.load(os.path.join(P, "y_test_mc.npy"), allow_pickle=True)
    zd = sorted(np.load(os.path.join(P, "zero_day_classes.npy"),
                        allow_pickle=True).tolist())

    ben = yte == "BENIGN"
    anyzd = np.isin(yte, zd)
    fam_n = {f: int((yte == f).sum()) for f in zd}
    powered = [f for f in zd if fam_n[f] >= metrics.MIN_FAMILY_N]

    cnn = {s: load("y_prob_cnn_paper_test.npy" if s == 42
                   else "y_prob_cnn_paper_s%d_test.npy" % s) for s in SEEDS}
    if any(cnn[s] is None for s in SEEDS):
        sys.exit("missing CNN predictions")

    configs = {"CNN alone": {s: cnn[s] for s in SEEDS}}
    for variant in ("s_kg", "causal"):
        f = {s: load(kg_file(K, s, variant)) for s in SEEDS}
        if any(v is None for v in f.values()):
            print("skipping CNN+KG k=%d (%s) - predictions missing" % (K, variant))
            continue
        configs["CNN + KG k=%d (%s)" % (K, variant)] = {
            s: np.mean([rk(cnn[s]), rk(f[s])], axis=0) for s in SEEDS}

    print("=" * 100)
    print("OPERATIONAL PROFILE OF THE SELECTED SYSTEM")
    print("=" * 100)
    print("test flows %d | benign %d | zero-day %d over %d families (%d adequately powered)"
          % (len(yte), int(ben.sum()), int(anyzd.sum()), len(zd), len(powered)))
    print("underpowered, excluded from the macro: %s"
          % ", ".join("%s n=%d" % (f, fam_n[f]) for f in zd if f not in powered))

    def recall(sc, mask, fpr):
        """Recall over `mask` at a threshold set on BENIGN flows only."""
        thr = np.quantile(sc[ben], 1.0 - fpr)
        return float((sc[mask] >= thr).mean())

    out = {"k": K, "seeds": SEEDS, "fprs": FPRS, "noise_band": NOISE,
           "n_test": len(yte), "n_benign": int(ben.sum()),
           "n_zero_day": int(anyzd.sum()), "family_n": fam_n,
           "powered_families": powered, "configs": {}}

    for label, per_seed in configs.items():
        macro = np.array([metrics.evaluate(yte, per_seed[s], set(zd),
                                           fpr=0.01)["macro"]["pr_auc"]
                          for s in SEEDS])
        row = {"macro_pr_auc": {"per_seed": [round(v, 4) for v in macro.tolist()],
                                "mean": float(macro.mean()),
                                "sd": float(macro.std(ddof=1))},
               "recall_at_fpr": {}}
        print("\n" + "-" * 100)
        print("%s   macro %.4f  (per seed %s)"
              % (label, macro.mean(), ", ".join("%.4f" % v for v in macro)))
        print("-" * 100)
        print("%-28s %s" % ("recall @ FPR", "  ".join("%7.1f%%" % (100 * f)
                                                      for f in FPRS)))
        for nm, mask in ([("ALL unknown flows", anyzd)]
                         + [(f, yte == f) for f in powered]):
            vals = {}
            line = []
            for fpr in FPRS:
                v = np.array([recall(per_seed[s], mask, fpr) for s in SEEDS])
                vals["%.3f" % fpr] = {"mean": float(v.mean()),
                                      "sd": float(v.std(ddof=1)),
                                      "per_seed": [round(x, 4) for x in v.tolist()]}
                line.append("%7.1f%%" % (100 * v.mean()))
            row["recall_at_fpr"][nm] = vals
            print("%-28s %s" % (nm, "  ".join(line)))
        out["configs"][label] = row

    # the headline delta, paired over shared seeds -- the only comparable form
    base = np.array(out["configs"]["CNN alone"]["macro_pr_auc"]["per_seed"])
    for label in out["configs"]:
        if label == "CNN alone":
            continue
        v = np.array(out["configs"][label]["macro_pr_auc"]["per_seed"])
        d = v - base
        sd = d.std(ddof=1)
        out["configs"][label]["paired_vs_cnn"] = {
            "mean_delta": float(d.mean()), "paired_sd": float(sd),
            "sigma": float(abs(d.mean()) / sd) if sd > 0 else None,
            "seeds_better": int((d > 0).sum()),
            "direction_consistent": bool((d > 0).all() or (d < 0).all())}
        print("\n%s vs CNN alone: %+.4f, %d/3 seeds"
              % (label, d.mean(), int((d > 0).sum())))

    out["caveats"] = [
        "k was selected on test. ksweep_heldout.json re-selected it on a "
        "stratified half (rng 9001) and reported +0.0305 at 2.86 sigma on the "
        "other half - that is the honest number for the improvement; these are "
        "the operating profile of the selected system.",
        "The variant ranking flips with k (causal leads at k=200, s_kg at "
        "k=800). Neither cross-variant gap is tested paired and both sit inside "
        "the 0.0285 band, so neither variant is asserted better.",
        "Bot's detectability rides substantially on CIC-IDS2017's SCRIPTED "
        "attack windows; a real network with continuous low-rate C2 would not "
        "produce this signal.",
        "The 10 % FPR column is reported for shape only. It is NOT a deployable "
        "operating point - at 55,237 benign test flows it is ~5,500 false "
        "alerts.",
        "Web Brute Force and XSS score high by ABSORPTION into a known attack "
        "class, not by novel-class detection - see the standing caution.",
        "Heartbleed, Infiltration and SQL Injection are below MIN_FAMILY_N=100 "
        "and are excluded from the macro and from the per-family table.",
    ]
    p = os.path.join(paths.METADATA, "operational_best.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("\nwrote %s" % p)
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())

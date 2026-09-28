"""
exogeneity_residual.py — is "predictable from the features" the same as "adds no evidence"?

THE GAP THIS CLOSES
-------------------
The paper's §6 (and `exogenous_predicate.py`, `hostwindow.py`) decide exogeneity by
MARGINAL predictability: fit gradient boosting X -> W and call W "not exogenous" if R²
(or AUC) is high. §6 then says "a stronger predictor could only make the conclusion
stronger."

That inference is not valid as stated. Knowledge adds evidence through its RESIDUAL,
r = W - E[W | X]: the part of the predicate the features could not reproduce. An
average R² of 0.95 is a statement about all 114,658 test rows; it says nothing about
whether the unexplained 5 % is concentrated on the ~2 % of rows that are zero-day. A
Bot flow that LOOKS benign would get a benign-looking prediction Ŵ, and if its true
host behaviour is unusual the residual is large exactly there. Conversely a predicate
with low R² can carry no label information at all. Marginal R² is neither necessary
nor sufficient for the quantity that matters, which is conditional: does W say
anything about the zero-day label that X does not?

WHAT THIS MEASURES
------------------
For both views already built -- the STATIC host-role predicates (`exo_*.npy`) and the
causal HOST-WINDOW features (`hostwin_*.npy`) -- and for three seeds (the seed picks
the 200k training subsample and the boosting seed):

  U  univariate: ROC-AUC of |r| for each predicate, each powered zero-day family vs
     benign. Direction (magnitude) is fixed in advance, not chosen per result.
  M  multivariate: a benign-only IsolationForest on the residual vector, fitted on
     VALIDATION benign rows (never in the boosting subsample, so residuals there are
     out-of-sample, like test), scored on test -> macro zero-day PR-AUC and per-family
     lift through `metrics.evaluate`, exactly as every other channel is scored. The
     same model on the RAW view is the comparison.

No attack label is used to fit anything. Residuals on the training rows are never used
(they are in-sample for the booster).

PRE-REGISTERED PREDICTIONS (written before the first run)
---------------------------------------------------------
  R1  (the paper's §6 reading holds) For BOTH views, the residual channel's Bot lift is
      < 2x on every seed, AND no predicate's |r| reaches ROC-AUC >= 0.75 (the project's
      own exogeneity threshold) on any powered family on all 3 seeds.
  R2  (the alternative) Some view's residual channel reaches Bot lift >= 2x on 3/3
      seeds, OR some predicate's |r| reaches ROC-AUC >= 0.75 on a powered family on
      3/3 seeds. Then "predictable from the features" does not imply "adds no
      evidence", and §6's "a stronger predictor could only make the conclusion
      stronger" must be struck and replaced by the conditional statement.
  Expectation, stated so it can be wrong: R1 for the static view (each testbed host
  runs one scripted role, so residuals are small everywhere); genuinely uncertain for
  the window view, whose R² (0.51-0.87) leaves far more unexplained.

Run:  python scripts/exogeneity_residual.py
Out:  outputs/metadata/exogeneity_residual.json
"""
import os
import sys
import json

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                          # noqa: E402
import config                                         # noqa: E402
import features as featmod                            # noqa: E402
import metrics                                        # noqa: E402
import tracking                                       # noqa: E402

SEEDS = [42, 43, 44]
N_FIT = 200000              # same subsample size as the two exogeneity scripts
AUC_EXO = 0.75              # the project's exogeneity threshold for AUCs
LIFT_REACH = 2.0

VIEWS = {
    # name: (file stem, column names, which columns are binary)
    "static_host_role": ("exo", ["UnusualPortForHost", "ServesWebPort",
                                 "FanOutLog", "PairPersistenceLog"], {0, 1}),
    "host_window": ("hostwin", ["Flows60", "Dsts60", "Ports60", "Flows600",
                                "Dsts600", "Ports600", "PairFlows600",
                                "GapCV600"], set()),
}


def load_view(stem, n_cols):
    P = paths.PAPER
    out = {}
    for sp in ("train", "val", "test"):
        a = np.load(os.path.join(P, "%s_%s.npy" % (stem, sp))).astype(np.float64)
        out[sp] = a[:, :n_cols]     # exo_*.npy carries a 5th, degenerate UnknownHost
    return out


def residuals(X, W, binary, itr, seed):
    """Out-of-sample residuals on val and test for every column of the view."""
    from sklearn.ensemble import (HistGradientBoostingRegressor as HGBR,
                                  HistGradientBoostingClassifier as HGBC)
    R = {"val": np.zeros_like(W["val"]), "test": np.zeros_like(W["test"])}
    r2 = []
    for j in range(W["train"].shape[1]):
        y = W["train"][itr, j]
        if j in binary:
            m = HGBC(max_iter=120, random_state=seed).fit(X["train"][itr], y.astype(int))
            pred = {sp: m.predict_proba(X[sp])[:, 1] for sp in ("val", "test")}
        else:
            m = HGBR(max_iter=120, random_state=seed).fit(X["train"][itr], y)
            pred = {sp: m.predict(X[sp]) for sp in ("val", "test")}
        for sp in ("val", "test"):
            R[sp][:, j] = W[sp][:, j] - pred[sp]
        t = W["test"][:, j]
        r2.append(float(1.0 - np.var(R["test"][:, j]) / np.var(t)) if np.var(t) > 0
                  else float("nan"))
    return R, r2


def novelty(fit_rows, score_rows, seed):
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    sc = StandardScaler().fit(fit_rows)
    iso = IsolationForest(n_estimators=200, random_state=seed, n_jobs=-1)
    iso.fit(sc.transform(fit_rows))
    return -iso.score_samples(sc.transform(score_rows))


def main():
    from sklearn.metrics import roc_auc_score
    cfg = config.get()
    zd = cfg["zero_day_classes"]
    tfm = cfg["protocol"]["feature_transform"]
    P = paths.PAPER
    X = {sp: featmod.transform(np.load(os.path.join(P, "X_%s.npy" % sp)), tfm)
         for sp in ("train", "val", "test")}
    y = {sp: np.asarray(np.load(os.path.join(P, "y_%s_mc.npy" % sp),
                                allow_pickle=True)).astype(str)
         for sp in ("val", "test")}
    ben_val = y["val"] == "BENIGN"
    ben_te = y["test"] == "BENIGN"

    out = {"seeds": SEEDS, "thresholds": {"auc_exo": AUC_EXO, "lift_reach": LIFT_REACH},
           "views": {}}
    for vname, (stem, cols, binary) in VIEWS.items():
        print("=" * 100)
        print("VIEW %s  (%d predicates)" % (vname, len(cols)))
        print("=" * 100)
        W = load_view(stem, len(cols))
        per_seed = []
        for s in SEEDS:
            itr = np.random.RandomState(s).choice(len(X["train"]), N_FIT, replace=False)
            R, r2 = residuals(X, W, binary, itr, s)

            # U: univariate |r| AUC per predicate per powered family
            uni = {}
            for j, c in enumerate(cols):
                uni[c] = {}
                for fam in zd:
                    m = y["test"] == fam
                    if m.sum() < metrics.MIN_FAMILY_N:
                        continue
                    sub = ben_te | m
                    uni[c][fam] = float(roc_auc_score(
                        m[sub].astype(int), np.abs(R["test"][sub, j])))

            # M: benign-only novelty on residuals vs on the raw view
            chan = {}
            for tag, V in (("residual", R), ("raw", W)):
                sc = novelty(V["val"][ben_val], V["test"], s)
                ev = metrics.evaluate(y["test"], sc, zd)
                chan[tag] = {
                    "macro_pr_auc": ev["macro"]["pr_auc"],
                    "family": {f: {"pr_auc": d["pr_auc"], "lift": d["lift"],
                                   "roc_auc": d["roc_auc"]}
                               for f, d in ev["zeroday_family"].items()
                               if not d["underpowered"]}}
            per_seed.append({"seed": s, "r2_test": dict(zip(cols, r2)),
                             "univariate_abs_residual_auc": uni, "channel": chan})
            print("\n  seed %d   R2(test) %s" % (s, " ".join("%.3f" % v for v in r2)))
            for tag in ("raw", "residual"):
                c = chan[tag]
                print("    %-8s novelty macro %.4f | %s" % (
                    tag, c["macro_pr_auc"], " | ".join(
                        "%s lift %.2fx" % (f.replace("Web Attack ", ""), d["lift"])
                        for f, d in c["family"].items())))
            best = max(((c, f, a) for c, d in uni.items() for f, a in d.items()),
                       key=lambda t: t[2])
            print("    best univariate |r| AUC: %s on %s = %.3f" % best)

        # verdicts, pre-registered
        bot_lifts = [p["channel"]["residual"]["family"]["Bot"]["lift"] for p in per_seed]
        reach_bot = all(l >= LIFT_REACH for l in bot_lifts)
        uni_hits = []
        for c in cols:
            for fam in per_seed[0]["univariate_abs_residual_auc"][c]:
                a = [p["univariate_abs_residual_auc"][c][fam] for p in per_seed]
                if all(v >= AUC_EXO for v in a):
                    uni_hits.append({"predicate": c, "family": fam, "auc": a})
        verdict = "R2" if (reach_bot or uni_hits) else "R1"
        out["views"][vname] = {
            "predicates": cols, "per_seed": per_seed,
            "residual_bot_lift": bot_lifts, "residual_reaches_bot_3of3": reach_bot,
            "univariate_hits_3of3": uni_hits,
            "residual_macro_mean": float(np.mean(
                [p["channel"]["residual"]["macro_pr_auc"] for p in per_seed])),
            "raw_macro_mean": float(np.mean(
                [p["channel"]["raw"]["macro_pr_auc"] for p in per_seed])),
            "verdict": verdict}
        print("\n  VERDICT %s: residual Bot lift %s ; univariate hits (3/3 seeds) %d"
              % (verdict, ", ".join("%.2fx" % l for l in bot_lifts), len(uni_hits)))
        for h in uni_hits:
            print("     %s on %s: %s" % (h["predicate"], h["family"],
                                         ", ".join("%.3f" % v for v in h["auc"])))

    p = os.path.join(paths.METADATA, "exogeneity_residual.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("\nwrote %s" % p)
    for v, d in out["views"].items():
        tracking.log_run("exo_residual_%s" % v, {"seeds": SEEDS, "n_fit": N_FIT},
                         {"residual_macro_zd_pr_auc": d["residual_macro_mean"],
                          "raw_macro_zd_pr_auc": d["raw_macro_mean"],
                          "residual_bot_lift_mean": float(np.mean(d["residual_bot_lift"])),
                          "verdict_R2": d["verdict"] == "R2"})


if __name__ == "__main__":
    main()

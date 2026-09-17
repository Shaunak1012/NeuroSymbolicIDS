"""
baselines_tuned.py — the classical baselines, given the tuning budget the CNN gets.

WHY THIS EXISTS (audit F-12, 2026-09-17)
----------------------------------------
`baselines.py` trains XGBoost, RandomForest and IsolationForest with fixed
hyperparameters and never loads the validation split. The CNN trains for up to 50
epochs with early stopping, learning-rate annealing and checkpoint selection, all
on validation. Every "the CNN vs the baselines" statement in the project was
therefore tuning-mismatched. This script gives each baseline a small grid and
selects on the same zero-day-free validation split the CNN uses, with the same
kind of criterion (known-class validation performance, never test, never a
zero-day label).

  XGBoost          max_depth x learning_rate, up to 1000 trees, early stopping on
                   validation log-loss. No row/column subsampling, so -- like the
                   original -- it is seed-invariant: one run stands for all seeds.
  RandomForest     max_depth x max_features, 200 trees, selected on validation
                   PR-AUC (benign vs known attack); the selected setting is then
                   trained at seeds 42/43/44.
  IsolationForest  n_estimators x max_samples, fitted on benign training flows
                   only, selected on validation PR-AUC; seeds 42/43/44.

Selection never sees test data or a zero-day flow. Reported against the untuned
records (baselines.py) and the deterministic CNN (0.6299).

Run:  python scripts/baselines_tuned.py
Out:  outputs/metadata/baselines_tuned.json
"""
import os
import sys
import json
import time
import itertools

import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.metrics import average_precision_score
from xgboost import XGBClassifier

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                        # noqa: E402
import config                                       # noqa: E402
import features                                     # noqa: E402
import metrics                                      # noqa: E402
import tracking                                     # noqa: E402

cfg = config.get()
P = os.path.join(paths.PROCESSED, cfg["paths"]["paper_subdir"])
TFM = cfg["protocol"]["feature_transform"]
SEEDS = [42, 43, 44]
FAMS = ["Bot", "Web Attack Brute Force", "Web Attack XSS"]
GRID = {
    "xgboost": {"max_depth": [4, 6, 8, 10], "learning_rate": [0.05, 0.1, 0.3]},
    "random_forest": {"max_depth": [10, 20, 30], "max_features": ["sqrt", 0.3]},
    "isolation_forest": {"n_estimators": [100, 200, 400], "max_samples": [256, 4096, "auto"]},
}
UNTUNED = {"xgboost": ["xgboost"],
           "random_forest": ["random_forest", "random_forest_s43", "random_forest_s44"],
           "isolation_forest": ["isolation_forest", "isolation_forest_s43",
                                "isolation_forest_s44"]}


def load(split):
    X = np.load(os.path.join(P, "X_%s.npy" % split))
    return (X, np.load(os.path.join(P, "y_%s_bin.npy" % split)),
            np.load(os.path.join(P, "y_%s_mc.npy" % split), allow_pickle=True))


def main():
    Xtr, ytr, _ = load("train")
    Xva, yva, _ = load("val")
    Xte, _, yte = load("test")
    zd = set(np.load(os.path.join(P, "zero_day_classes.npy"), allow_pickle=True).tolist())
    Xtr, Xva, Xte = (features.transform(a, TFM) for a in (Xtr, Xva, Xte))
    sc = StandardScaler().fit(Xtr)
    Xtr, Xva, Xte = sc.transform(Xtr), sc.transform(Xva), sc.transform(Xte)
    ben_tr = Xtr[ytr == 0]

    def report(tag, score, params):
        r = metrics.evaluate(yte, score, zd, fpr=0.01)
        tracking.log_run(tag, {"protocol": "paper", "transform": TFM, "tuned_on": "val",
                               **params}, metrics.flatten(r))
        np.save(os.path.join(paths.PREDICTIONS, "y_prob_%s_test.npy" % tag),
                np.asarray(score, dtype=np.float32))
        return {"macro": r["macro"]["pr_auc"],
                "family": {f: r["zeroday_family"][f]["pr_auc"] for f in FAMS},
                "known_only_pr_auc": r["views"]["known_only"]["pr_auc"]}

    out = {"grid": {k: {kk: [str(x) for x in vv] for kk, vv in v.items()} for k, v in GRID.items()},
           "selection": "validation split only (no zero-day flows); test never used",
           "models": {}}

    # ---- XGBoost ------------------------------------------------------------
    t0, trials = time.time(), []
    for d, lr in itertools.product(*GRID["xgboost"].values()):
        m = XGBClassifier(n_estimators=1000, max_depth=d, learning_rate=lr, n_jobs=-1,
                          tree_method="hist", eval_metric="logloss",
                          early_stopping_rounds=30, random_state=42)
        m.fit(Xtr, ytr, eval_set=[(Xva, yva)], verbose=False)
        trials.append({"max_depth": d, "learning_rate": lr, "best_iteration": int(m.best_iteration),
                       "val_logloss": float(m.best_score), "model": m})
        print("xgb d=%-2s lr=%-4s trees=%4d val_logloss=%.5f" % (d, lr, m.best_iteration + 1,
                                                                m.best_score), flush=True)
    best = min(trials, key=lambda t: t["val_logloss"])
    params = {k: best[k] for k in ("max_depth", "learning_rate", "best_iteration")}
    res = report("xgboost_tuned", best["model"].predict_proba(Xte)[:, 1], params)
    out["models"]["xgboost"] = {"selected": params, "val_logloss": best["val_logloss"],
                                "trials": [{k: v for k, v in t.items() if k != "model"} for t in trials],
                                "runs": [res], "seconds": round(time.time() - t0)}

    # ---- RandomForest -------------------------------------------------------
    t0, trials = time.time(), []
    for d, mf in itertools.product(*GRID["random_forest"].values()):
        m = RandomForestClassifier(n_estimators=200, max_depth=d, max_features=mf,
                                   n_jobs=-1, random_state=42).fit(Xtr, ytr)
        v = float(average_precision_score(yva, m.predict_proba(Xva)[:, 1]))
        trials.append({"max_depth": d, "max_features": mf, "val_pr_auc": v})
        print("rf  d=%-4s mf=%-4s val_pr_auc=%.6f" % (d, mf, v), flush=True)
    best = max(trials, key=lambda t: t["val_pr_auc"])
    runs = []
    for s in SEEDS:
        m = RandomForestClassifier(n_estimators=200, max_depth=best["max_depth"],
                                   max_features=best["max_features"], n_jobs=-1,
                                   random_state=s).fit(Xtr, ytr)
        runs.append(report("random_forest_tuned_s%d" % s, m.predict_proba(Xte)[:, 1],
                           {"seed": s, "max_depth": str(best["max_depth"]),
                            "max_features": str(best["max_features"])}))
    out["models"]["random_forest"] = {"selected": {k: str(best[k]) for k in ("max_depth", "max_features")},
                                      "val_pr_auc": best["val_pr_auc"], "trials":
                                      [{k: str(v) if k != "val_pr_auc" else v for k, v in t.items()}
                                       for t in trials],
                                      "runs": runs, "seconds": round(time.time() - t0)}

    # ---- IsolationForest (benign-only) --------------------------------------
    t0, trials = time.time(), []
    for ne, ms in itertools.product(*GRID["isolation_forest"].values()):
        m = IsolationForest(n_estimators=ne, max_samples=ms, n_jobs=-1, random_state=42).fit(ben_tr)
        v = float(average_precision_score(yva, -m.score_samples(Xva)))
        trials.append({"n_estimators": ne, "max_samples": ms, "val_pr_auc": v})
        print("if  n=%-4s ms=%-5s val_pr_auc=%.6f" % (ne, ms, v), flush=True)
    best = max(trials, key=lambda t: t["val_pr_auc"])
    runs = []
    for s in SEEDS:
        m = IsolationForest(n_estimators=best["n_estimators"], max_samples=best["max_samples"],
                            n_jobs=-1, random_state=s).fit(ben_tr)
        runs.append(report("isolation_forest_tuned_s%d" % s, -m.score_samples(Xte),
                           {"seed": s, "n_estimators": best["n_estimators"],
                            "max_samples": str(best["max_samples"])}))
    out["models"]["isolation_forest"] = {"selected": {k: str(best[k]) for k in ("n_estimators", "max_samples")},
                                         "val_pr_auc": best["val_pr_auc"],
                                         "trials": [{k: str(v) if k != "val_pr_auc" else v
                                                     for k, v in t.items()} for t in trials],
                                         "runs": runs, "seconds": round(time.time() - t0)}

    # ---- compare with the untuned records and the deterministic CNN ---------
    recs = {r["name"]: r for r in tracking.load_runs()}
    det_cnn = [recs["c4_log1p_s%d" % s]["metrics"]["macro_zd_pr_auc"] for s in SEEDS]
    print("\n%-18s %10s %10s %10s | %s" % ("model", "untuned", "tuned", "delta", "tuned Bot / WebBF / XSS"))
    for name, v in out["models"].items():
        before = [recs[t]["metrics"]["macro_zd_pr_auc"] for t in UNTUNED[name] if t in recs]
        after = [r["macro"] for r in v["runs"]]
        v["untuned_macro_mean"] = float(np.mean(before))
        v["tuned_macro_mean"] = float(np.mean(after))
        v["tuned_minus_untuned"] = v["tuned_macro_mean"] - v["untuned_macro_mean"]
        v["tuned_minus_det_cnn"] = v["tuned_macro_mean"] - float(np.mean(det_cnn))
        fam = {f: float(np.mean([r["family"][f] for r in v["runs"]])) for f in FAMS}
        v["tuned_family_mean"] = fam
        print("%-18s %10.4f %10.4f %+10.4f | %.4f / %.4f / %.4f   (vs det CNN %+.4f)"
              % (name, v["untuned_macro_mean"], v["tuned_macro_mean"], v["tuned_minus_untuned"],
                 fam["Bot"], fam["Web Attack Brute Force"], fam["Web Attack XSS"],
                 v["tuned_minus_det_cnn"]))
    out["det_cnn_macro"] = det_cnn
    p = os.path.join(paths.METADATA, "baselines_tuned.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=str)
    print("wrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())

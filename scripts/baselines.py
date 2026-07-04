"""
baselines.py — Phase 1 classical + anomaly baselines on the paper split.

Reviewers always ask "why not XGBoost / Isolation Forest?" — this answers it with numbers.
All evaluated via metrics.py (zero-day-only binary as the headline), logged to runs.jsonl.

  * XGBoost      — supervised binary (benign vs known attack), the tabular SOTA
  * RandomForest — supervised binary
  * IsolationForest — UNSUPERVISED anomaly detector, fit on benign-only (zero-day-legitimate)

Run:  python scripts/baselines.py
"""
import os
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from xgboost import XGBClassifier

import paths, config, features, metrics, tracking

cfg = config.get()
SEED = cfg["seed"]
PAPER = os.path.join(paths.PROCESSED, cfg["paths"]["paper_subdir"])
TFM = cfg["protocol"]["feature_transform"]


def load(split):
    X = np.load(os.path.join(PAPER, f"X_{split}.npy"))
    yb = np.load(os.path.join(PAPER, f"y_{split}_bin.npy"))
    ymc = np.load(os.path.join(PAPER, f"y_{split}_mc.npy"), allow_pickle=True)
    return X, yb, ymc


Xtr, ytr, _ = load("train")
Xte, yte, yte_mc = load("test")
zero_day = set(np.load(os.path.join(PAPER, "zero_day_classes.npy"), allow_pickle=True).tolist())

# log1p transform + scale (fit on train)
Xtr = features.transform(Xtr, TFM); Xte = features.transform(Xte, TFM)
sc = StandardScaler().fit(Xtr); Xtr, Xte = sc.transform(Xtr), sc.transform(Xte)
print(f"train {Xtr.shape}  test {Xte.shape}")

results = {}

def run(name, score_te):
    r = metrics.evaluate(yte_mc, score_te, zero_day, fpr=0.01)
    results[name] = r
    z = r["views"]["zeroday_only"]; a = r["views"]["all"]
    print(f"\n=== {name} ===  zeroday PR-AUC={z['pr_auc']:.4f} ROC={z['roc_auc']:.4f} | all PR-AUC={a['pr_auc']:.4f}")
    tracking.log_run(name, {"protocol": "paper", "transform": TFM, "seed": SEED}, metrics.flatten(r))
    np.save(os.path.join(paths.PREDICTIONS, f"y_prob_{name}_test.npy"), score_te)
    return r

# --- XGBoost (supervised binary) ---
print("\nTraining XGBoost...")
xgb = XGBClassifier(n_estimators=300, max_depth=8, learning_rate=0.1, n_jobs=-1,
                    tree_method="hist", eval_metric="logloss", random_state=SEED)
xgb.fit(Xtr, ytr)
run("xgboost", xgb.predict_proba(Xte)[:, 1])

# --- Random Forest (supervised binary) ---
print("\nTraining RandomForest...")
rf = RandomForestClassifier(n_estimators=200, n_jobs=-1, random_state=SEED, max_depth=20)
rf.fit(Xtr, ytr)
run("random_forest", rf.predict_proba(Xte)[:, 1])

# --- Isolation Forest (UNSUPERVISED, benign-only) ---
print("\nTraining IsolationForest (benign-only)...")
Xtr_benign = Xtr[ytr == 0]
iso = IsolationForest(n_estimators=200, contamination="auto", n_jobs=-1, random_state=SEED)
iso.fit(Xtr_benign)
# higher score = more anomalous = more likely attack
run("isolation_forest", -iso.score_samples(Xte))

# --- headline comparison ---
print("\n" + "=" * 64)
print("PHASE-1 BASELINES — zero-day-only binary (headline):")
print(f"  {'model':16s} {'zd_PR-AUC':>10s} {'zd_ROC':>8s} {'all_PR-AUC':>11s}")
for name, r in results.items():
    z = r["views"]["zeroday_only"]; a = r["views"]["all"]
    print(f"  {name:16s} {z['pr_auc']:>10.4f} {z['roc_auc']:>8.4f} {a['pr_auc']:>11.4f}")
print("\nDONE (baselines) — scores saved for fusion; metrics logged to runs.jsonl")

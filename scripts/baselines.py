"""
baselines.py — Phase 1 classical + anomaly baselines on the paper split.

Reviewers always ask "why not XGBoost / Isolation Forest?" — this answers it with numbers.
All evaluated via metrics.py (zero-day-only binary as the headline), logged to runs.jsonl.

  * XGBoost      — supervised binary (benign vs known attack), the tabular SOTA
  * RandomForest — supervised binary
  * IsolationForest — UNSUPERVISED anomaly detector, fit on benign-only (zero-day-legitimate)

Run:  python scripts/baselines.py
Multi-seed: BASELINE_SEED=43 python scripts/baselines.py
  -> writes `<name>_s43` tags and `y_prob_<name>_s43_test.npy`, never touching the
     seed-42 reference artifacts (same convention as CNN_SEED / LTN_SEED / AE_SEED).

Seed support added 2026-08-03. Before that these three were n=1 AND predated the
2026-07-27 metrics.py rewrite, so their runs.jsonl entries carried only the blended
`zd_pr_auc` with no per-family or macro breakdown — which is why STATUS listed them
as "not citable for comparison" even though macro figures for xgboost (0.6372) and
isolation_forest (0.0628) were quoted in earlier tables with no logged provenance.
"""
import os
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from xgboost import XGBClassifier

import paths, config, features, metrics, tracking

cfg = config.get()
_DEFAULT_SEED = cfg["seed"]
SEED = int(os.environ.get("BASELINE_SEED", _DEFAULT_SEED))
SUFFIX = "" if SEED == _DEFAULT_SEED else f"_s{SEED}"
PAPER = os.path.join(paths.PROCESSED, cfg["paths"]["paper_subdir"])
TFM = cfg["protocol"]["feature_transform"]
print(f"CONFIG: seed={SEED} suffix={SUFFIX or '(reference)'}")


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
    tag = f"{name}{SUFFIX}"
    r = metrics.evaluate(yte_mc, score_te, zero_day, fpr=0.01)
    results[tag] = r
    z = r["views"]["zeroday_only"]; a = r["views"]["all"]
    macro = r.get("macro", {}).get("pr_auc")
    print(f"\n=== {tag} ===  MACRO(headline)={macro:.4f} "
          f"| blended zd PR-AUC={z['pr_auc']:.4f} ROC={z['roc_auc']:.4f} | all PR-AUC={a['pr_auc']:.4f}")
    tracking.log_run(tag, {"protocol": "paper", "transform": TFM, "seed": SEED}, metrics.flatten(r))
    np.save(os.path.join(paths.PREDICTIONS, f"y_prob_{tag}_test.npy"), score_te)
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
print(f"PHASE-1 BASELINES (seed {SEED}) — MACRO zero-day PR-AUC is the headline:")
print(f"  {'model':20s} {'MACRO':>8s} {'Bot':>8s} {'WebBF':>8s} {'XSS':>8s} {'blended':>8s}")
for name, r in results.items():
    z = r["views"]["zeroday_only"]
    m = r.get("macro", {}).get("pr_auc")
    fam = {k: v["pr_auc"] for k, v in r.get("zeroday_family", {}).items()}
    g = lambda k: f"{fam[k]:.4f}" if k in fam else "   --  "
    print(f"  {name:20s} {m:>8.4f} {g('Bot'):>8s} "
          f"{g('Web Attack Brute Force'):>8s} {g('Web Attack XSS'):>8s} {z['pr_auc']:>8.4f}")
print("\nDONE (baselines) — scores saved for fusion; metrics logged to runs.jsonl")

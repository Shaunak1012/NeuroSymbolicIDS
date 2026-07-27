"""
skyline_oracle.py — Phase-2(B) skyline/oracle experiment. No TensorFlow needed.

Question: is Bot (and the other zero-day families) genuinely undetectable in the
current 68-dim per-flow feature space, or is the near-chance PR-AUC merely a
zero-day *generalization* failure — never seeing the class at train time — rather
than an information-theoretic limit of the representation?

Method: stratified 50/50 split of EACH zero-day family's test flows into an
oracle-train half (added into the training set, true label revealed) and a
held-out eval half (kept fully out of training). Retrain XGBoost (identical
hyperparams to scripts/baselines.py) on train + oracle-train-half; evaluate ONLY
on benign(test) + oracle-eval-half, and compare per-family PR-AUC against the
original never-seen baseline on the SAME eval subset (apples-to-apples: same
rows, same threshold procedure — only the training exposure differs).

Interpretation:
  * oracle PR-AUC stays near chance -> the per-flow representation does not
    separate that family from benign REGARDLESS of supervision. An information-
    theoretic ceiling, not a training-signal problem. Motivates changing the unit
    of analysis (host/session-level features — see host_features.py), not the
    training method.
  * oracle PR-AUC jumps well above chance -> the information IS present in the
    68 features; the true zero-day setting (never trained on it) is the
    bottleneck, not the feature space. Motivates better zero-day transfer
    (domain adaptation, open-set recognition) instead.

Run: python scripts/skyline_oracle.py
"""
import os
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

import paths, config, features, metrics, tracking

cfg = config.get(); SEED = cfg["seed"]
PAPER = os.path.join(paths.PROCESSED, cfg["paths"]["paper_subdir"])
TFM = cfg["protocol"]["feature_transform"]


def load(split):
    X = np.load(os.path.join(PAPER, f"X_{split}.npy"))
    ymc = np.load(os.path.join(PAPER, f"y_{split}_mc.npy"), allow_pickle=True)
    return X, ymc


Xtr_raw, ytr_mc = load("train")
Xte_raw, yte_mc = load("test")
zero_day = sorted(set(np.load(os.path.join(PAPER, "zero_day_classes.npy"),
                              allow_pickle=True).tolist()))

# ---- split each zero-day family's test flows 50/50: oracle-train / held-out eval ----
oracle_train_idx = []
fam_counts = {}
for fam in zero_day:
    idx = np.where(yte_mc == fam)[0]
    tr_half, ev_half = train_test_split(idx, test_size=0.5, random_state=SEED)
    oracle_train_idx.extend(tr_half.tolist())
    fam_counts[fam] = (len(tr_half), len(ev_half))

oracle_train_idx = np.array(sorted(oracle_train_idx))
eval_mask = np.ones(len(yte_mc), dtype=bool)
eval_mask[oracle_train_idx] = False   # oracle-train rows are fully removed from eval

yte_mc_eval = yte_mc[eval_mask]
Xte_raw_eval = Xte_raw[eval_mask]

print("oracle-train additions (train half / held-out eval half):")
for fam in zero_day:
    tr_n, ev_n = fam_counts[fam]
    print(f"  {fam:28s} {tr_n:>5,} / {ev_n:>5,}")

# ---- baseline-on-same-eval-subset: slice the already-trained xgboost's saved scores ----
base_scores_full = np.load(os.path.join(paths.PREDICTIONS, "y_prob_xgboost_test.npy")).astype(np.float64)
base_scores_eval = base_scores_full[eval_mask]
print("\n" + "=" * 78)
print("BASELINE (never seen this class) — restricted to the same held-out eval rows:")
res_base = metrics.evaluate(yte_mc_eval, base_scores_eval, zero_day, fpr=0.01)
metrics.print_report(res_base)

# ---- build the oracle training set: original train + revealed zero-day halves ----
Xtr_aug_raw = np.vstack([Xtr_raw, Xte_raw[oracle_train_idx]])
ytr_aug_bin = np.concatenate([
    (ytr_mc != "BENIGN").astype(int),
    np.ones(len(oracle_train_idx), dtype=int),   # all revealed zero-day rows are attacks
])

Xtr_aug = features.transform(Xtr_aug_raw, TFM)
Xte_eval = features.transform(Xte_raw_eval, TFM)
sc = StandardScaler().fit(Xtr_aug)
Xtr_aug, Xte_eval = sc.transform(Xtr_aug), sc.transform(Xte_eval)
print(f"\ntrain (augmented) = {Xtr_aug.shape}, eval (held-out) = {Xte_eval.shape}")

print("\nTraining oracle XGBoost (identical hyperparams to baselines.py)...")
xgb = XGBClassifier(n_estimators=300, max_depth=8, learning_rate=0.1, n_jobs=-1,
                    tree_method="hist", eval_metric="logloss", random_state=SEED)
xgb.fit(Xtr_aug, ytr_aug_bin)
oracle_scores = xgb.predict_proba(Xte_eval)[:, 1]
np.save(os.path.join(paths.PREDICTIONS, "y_prob_xgboost_oracle_test.npy"), oracle_scores)

print("\n" + "=" * 78)
print("ORACLE (trained on revealed half) — same held-out eval rows:")
res_oracle = metrics.evaluate(yte_mc_eval, oracle_scores, zero_day, fpr=0.01)
metrics.print_report(res_oracle)
tracking.log_run("xgboost_oracle", {"protocol": "paper", "transform": TFM, "seed": SEED,
                                    "oracle_train_frac": 0.5}, metrics.flatten(res_oracle))

# ---- head-to-head ----
print("\n" + "=" * 78)
print("HEAD-TO-HEAD (same eval rows; only training exposure differs):")
print(f"{'family':28s} {'baseline PR':>11s} {'oracle PR':>10s} {'gain':>8s}  verdict")
fb, fo = res_base["zeroday_family"], res_oracle["zeroday_family"]
for fam in zero_day:
    b, o = fb[fam]["pr_auc"], fo[fam]["pr_auc"]
    gain = o - b
    verdict = "CEILING (info absent)" if o < 3 * fb[fam]["chance_pr_auc"] else "recoverable w/ supervision"
    print(f"{fam:28s} {b:>11.4f} {o:>10.4f} {gain:>+8.4f}  {verdict}")

mb, mo = res_base["macro"]["pr_auc"], res_oracle["macro"]["pr_auc"]
print(f"\n{'MACRO':28s} {mb:>11.4f} {mo:>10.4f} {mo-mb:>+8.4f}")
print("DONE (skyline_oracle)")

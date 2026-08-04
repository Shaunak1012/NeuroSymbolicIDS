"""
comparability.py — the table that makes this project comparable to the literature.

THE PROBLEM IT SOLVES
---------------------
Published CIC-IDS2017 work routinely reports **99%+**. We headline **macro
zero-day PR-AUC ~0.64**. That looks like we are far behind. We are not — the two
numbers measure different tasks, and the same models produce both:

    CNN   overall binary PR-AUC 0.9928   |   macro zero-day PR-AUC 0.6446
    XGB   overall binary PR-AUC 0.9936   |   macro zero-day PR-AUC 0.6372

Reviewers cannot be expected to notice that unprompted, so this script emits the
side-by-side explicitly. It is the opening argument of the write-up: *the same
model, the same run, two protocols, a 0.35 gap.*

THREE COLUMNS, AND WHY THE THIRD MATTERS
----------------------------------------
1. **Overall binary** — what the field reports. Benign vs all attacks, including
   the 8 attack families the model was TRAINED on.
2. **Overall binary, DEDUPLICATED** — the same, after removing test rows that are
   exact feature-vector duplicates of a training row. CIC-IDS2017 is
   duplicate-heavy and the paper split is stratified-random, so **17.0% of test
   rows have an exact twin in train** (PortScan 58.3%, SSH-Patator 48.6%). For
   those rows the task is lookup, not detection. This is issue C1, and the fix
   was specified but never run until now. Costs one evaluation pass, no retraining.
3. **Macro zero-day** — our headline. Six families never seen in training or
   validation, scored per-family and averaged over the adequately powered ones.

⚠️ The zero-day metric is UNAFFECTED by deduplication — all six zero-day families
measure 0.0% train overlap by construction, since they are test-only. So the
duplicate problem inflates exactly the number the field reports and leaves ours
alone. That asymmetry is the point.

Run:  python scripts/comparability.py
Out:  outputs/metadata/comparability.json
"""
import os
import json
import hashlib
import numpy as np

import paths, metrics

P, PR = paths.PAPER, paths.PREDICTIONS
yte = np.load(os.path.join(P, "y_test_mc.npy"), allow_pickle=True)
zero_day = set(np.load(os.path.join(P, "zero_day_classes.npy"), allow_pickle=True).tolist())

# ---- exact-duplicate detection (row hashing, C1's measurement) ---------------
print("hashing train/test feature vectors to find exact duplicates...")
Xtr = np.load(os.path.join(P, "X_train.npy"))
Xte = np.load(os.path.join(P, "X_test.npy"))


def _hashes(X):
    return {hashlib.blake2b(r.tobytes(), digest_size=16).digest() for r in X}, \
           [hashlib.blake2b(r.tobytes(), digest_size=16).digest() for r in X]


train_set, _ = _hashes(Xtr)
_, te_list = _hashes(Xte)
is_dup = np.array([h in train_set for h in te_list])
unique = ~is_dup
print(f"  {is_dup.sum():,}/{len(yte):,} test rows ({is_dup.mean():.1%}) are exact duplicates of a train row")
for c in sorted(set(yte.tolist())):
    m = yte == c
    if m.sum() >= 100:
        print(f"    {c:28s} {is_dup[m].mean():6.1%}")

CHANNELS = {
    "CNN (cnn_paper)":      "y_prob_cnn_paper_logodds_test.npy",
    "XGBoost":              "y_prob_xgboost_test.npy",
    "RandomForest":         "y_prob_random_forest_test.npy",
    "LTN control":          "y_prob_ltn_ctrl_w0_logodds_test.npy",
    "Mahalanobis":          "y_prob_mahalanobis_test.npy",
    "Autoencoder":          "y_prob_autoencoder_paper_test.npy",
    "IsolationForest":      "y_prob_isolation_forest_test.npy",
    "KG (causal)":          "y_prob_kg_causal_test.npy",
    "CNN + KG fusion":      "y_prob_fusion_cnn_kg_test.npy",
}

OUT = {"duplicate_rate_overall": float(is_dup.mean()),
       "n_test": int(len(yte)), "n_duplicated": int(is_dup.sum()), "channels": {}}

print("\n" + "=" * 100)
print("COMPARABILITY TABLE — the same models under the field's protocol and ours")
print("=" * 100)
print(f"{'channel':22s} {'overall binary':>15s} {'dedup':>9s} {'Δ':>8s} | {'MACRO ZERO-DAY':>16s}")
print(f"{'':22s} {'(what the field':>15s} {'(honest)':>9s} {'':>8s} | {'(ours)':>16s}")
print(f"{'':22s} {'reports)':>15s}")
print("-" * 100)
for name, f in CHANNELS.items():
    p = os.path.join(PR, f)
    if not os.path.exists(p):
        print(f"{name:22s}  (missing)")
        continue
    s = np.load(p)
    r_all = metrics.evaluate(yte, s, zero_day, fpr=0.01)
    r_ded = metrics.evaluate(yte[unique], s[unique], zero_day, fpr=0.01)
    a = r_all["views"]["all"]["pr_auc"]
    d = r_ded["views"]["all"]["pr_auc"]
    m = r_all["macro"]["pr_auc"]
    OUT["channels"][name] = {"overall_binary": a, "overall_binary_dedup": d,
                             "delta_from_dedup": d - a, "macro_zero_day": m}
    print(f"{name:22s} {a:>15.4f} {d:>9.4f} {d-a:>+8.4f} | {m:>16.4f}")

print("-" * 100)
best_all = max(OUT["channels"].items(), key=lambda kv: kv[1]["overall_binary"])
best_zd = max(OUT["channels"].items(), key=lambda kv: kv[1]["macro_zero_day"])
print(f"best on the FIELD's metric : {best_all[0]} @ {best_all[1]['overall_binary']:.4f}")
print(f"best on OUR metric         : {best_zd[0]} @ {best_zd[1]['macro_zero_day']:.4f}")
print(f"\nTHE GAP: {best_all[1]['overall_binary']:.4f} -> {best_all[1]['macro_zero_day']:.4f} "
      f"({best_all[1]['overall_binary']-best_all[1]['macro_zero_day']:.4f}) for the SAME model.")
print("That gap is the paper's opening argument: it is protocol, not capability.")

out = os.path.join(paths.METADATA, "comparability.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(OUT, f, indent=1)
print(f"\nwrote {out}")

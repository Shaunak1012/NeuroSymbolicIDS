"""
preprocess_paper.py — Paper-aligned split (Bizzarri et al.), Phase 0.

Reuses the already-processed 68-feature matrices (features_train/test.csv) and their
multiclass labels, then re-slices them into the PAPER protocol:

  * 9 known classes (BENIGN + 8 major attacks incl. PortScan/DDoS) -> stratified
    80/10/10 into train / val / test.
  * 6 rare zero-day classes -> appended to TEST only (never trained/validated).
  * BENIGN under-sampled to config `benign_ratio` : total known-attack count.

Outputs -> data/processed/paper/ :
  X_train.npy X_val.npy X_test.npy            (float32 feature matrices, 68 cols)
  y_train_mc.npy y_val_mc.npy y_test_mc.npy   (string multiclass labels)
  y_train_bin.npy y_val_bin.npy y_test_bin.npy(0/1)
  known_classes.npy  zero_day_classes.npy
  split_report.txt

The temporal protocol (data/processed/*.csv) is left untouched as the secondary
"hard-mode" benchmark.
"""
import os
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

import paths
import config

cfg = config.get()
SEED = cfg["seed"]
P = cfg["protocol"]
OUT = os.path.join(paths.PROCESSED, cfg["paths"]["paper_subdir"])
os.makedirs(OUT, exist_ok=True)
np.random.seed(SEED)


def _norm(lbl: str) -> str:
    """Normalise a raw label: strip the CIC-IDS encoding quirk (– shows as \\x96/�)."""
    return " ".join(lbl.replace("\x96", " ").replace("�", " ").split())


ZERO_DAY = set(cfg["zero_day_classes"])
KNOWN_ATK = set(cfg["known_attacks"])


def classify(lbl: str) -> str:
    n = _norm(lbl)
    if n == "BENIGN":
        return "benign"
    if n in ZERO_DAY:
        return "zero_day"
    if n in KNOWN_ATK:
        return "known"
    raise ValueError(f"Unclassified label: {lbl!r} (normalised {n!r})")


# ---- load pooled data (both temporal halves = all 5 days, already cleaned) ----
print("Loading pooled features + multiclass labels...")
X = np.vstack([
    pd.read_csv(os.path.join(paths.PROCESSED, "features_train.csv")).values,
    pd.read_csv(os.path.join(paths.PROCESSED, "features_test.csv")).values,
]).astype(np.float32)
y = np.concatenate([
    np.load(os.path.join(paths.PROCESSED, "labels_train_multiclass.npy"), allow_pickle=True),
    np.load(os.path.join(paths.PROCESSED, "labels_test_multiclass.npy"), allow_pickle=True),
])
y = np.array([_norm(s) for s in y])
print(f"  pooled: X={X.shape}  y={y.shape}")

kind = np.array([classify(s) for s in y])
is_benign, is_known, is_zd = kind == "benign", kind == "known", kind == "zero_day"
n_known_atk = int(is_known.sum())

# ---- under-sample benign to ratio : known-attack count ----
n_benign_keep = min(int(round(P["benign_ratio"] * n_known_atk)), int(is_benign.sum()))
benign_idx = np.where(is_benign)[0]
benign_keep = np.random.RandomState(SEED).choice(benign_idx, size=n_benign_keep, replace=False)
print(f"\nknown-attack flows: {n_known_atk:,} | benign kept: {n_benign_keep:,} "
      f"(of {is_benign.sum():,}, ratio {P['benign_ratio']})")

# ---- KNOWN pool = kept benign + all known attacks -> stratified 80/10/10 ----
known_pool = np.concatenate([benign_keep, np.where(is_known)[0]])
Xk, yk = X[known_pool], y[known_pool]
strat = yk  # stratify on multiclass to preserve rare known-attack ratios

X_tr, X_tmp, y_tr, y_tmp = train_test_split(
    Xk, yk, test_size=P["val_frac"] + P["test_frac"], random_state=SEED, stratify=strat)
rel = P["test_frac"] / (P["val_frac"] + P["test_frac"])
X_val, X_te_known, y_val, y_te_known = train_test_split(
    X_tmp, y_tmp, test_size=rel, random_state=SEED, stratify=y_tmp)

# ---- append zero-day to TEST only ----
X_zd, y_zd = X[is_zd], y[is_zd]
X_te = np.vstack([X_te_known, X_zd]).astype(np.float32)
y_te = np.concatenate([y_te_known, y_zd])

# ---- binary labels ----
def to_bin(arr): return (arr != "BENIGN").astype(np.int8)

# ---- save ----
np.save(os.path.join(OUT, "X_train.npy"), X_tr)
np.save(os.path.join(OUT, "X_val.npy"),   X_val)
np.save(os.path.join(OUT, "X_test.npy"),  X_te)
np.save(os.path.join(OUT, "y_train_mc.npy"), y_tr)
np.save(os.path.join(OUT, "y_val_mc.npy"),   y_val)
np.save(os.path.join(OUT, "y_test_mc.npy"),  y_te)
np.save(os.path.join(OUT, "y_train_bin.npy"), to_bin(y_tr))
np.save(os.path.join(OUT, "y_val_bin.npy"),   to_bin(y_val))
np.save(os.path.join(OUT, "y_test_bin.npy"),  to_bin(y_te))
np.save(os.path.join(OUT, "known_classes.npy"), np.array(sorted(set(y_tr))))
np.save(os.path.join(OUT, "zero_day_classes.npy"), np.array(sorted(ZERO_DAY)))

# ---- report + leakage assertions ----
lines = []
def log(s): print(s); lines.append(s)

log("\n" + "=" * 60)
log("PAPER-ALIGNED SPLIT REPORT")
log("=" * 60)
for name, arr in [("TRAIN", y_tr), ("VAL", y_val), ("TEST", y_te)]:
    u, c = np.unique(arr, return_counts=True)
    log(f"\n{name}  (n={len(arr):,}, attack ratio {to_bin(arr).mean():.4f})")
    for cls, cnt in sorted(zip(u, c), key=lambda t: -t[1]):
        tag = "  [ZERO-DAY]" if cls in ZERO_DAY else ""
        log(f"    {cls:32s} {cnt:>8,}{tag}")

# assertions: zero-day must NOT appear in train/val
zd_in_train = set(y_tr) & ZERO_DAY
zd_in_val = set(y_val) & ZERO_DAY
assert not zd_in_train, f"LEAK: zero-day in train: {zd_in_train}"
assert not zd_in_val, f"LEAK: zero-day in val: {zd_in_val}"
log(f"\n[OK] no zero-day leakage into train/val")
log(f"[OK] known classes: {len(set(y_tr))}  zero-day classes in test: {len(set(y_te) & ZERO_DAY)}")

with open(os.path.join(OUT, "split_report.txt"), "w") as f:
    f.write("\n".join(lines))
log(f"\nSaved -> {OUT}")

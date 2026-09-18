"""
preprocess_paper.py — Paper-INSPIRED split (after Bizzarri et al., ICCCN 2024), Phase 0.

Not a replication: the paper equalises every known attack class to 31,843, holds out
PortScan (we train on it) and trains on Infiltration (we hold it out), deletes duplicate
and payload-less records, and works on payload packets rather than flows. See the
protocol comment in config.yaml and BASEPAPER_COMPARISON.md (FD-01, FD-02).

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
# SPLIT_MODE / PAPER_SUBDIR (added 2026-09-17, audit F-02/F-03, decision D4).
#   random         the paper-inspired split every reported result uses (default;
#                  byte-identical to the code before these variables existed)
#   grouped        no Flow ID (5-tuple) on both sides of the boundary; every group
#                  that contains a zero-day flow is a test group
#   chronological  within each known class, the earliest 80 % of its flows train,
#                  the next 10 % validate, the latest 10 % test
#   balanced       (itinerary 5.4, FD-01, 2026-09-18) the random split, then train and
#                  val each cut down so every known attack class has as many flows as
#                  the SMALLEST one -- the base paper's rule (their 31,843 is the size of
#                  their smallest class, FTP-Patator) -- with benign at benign_ratio x
#                  the attack total. TEST IS THE CANONICAL TEST SET, unchanged.
#   subsampled     the matched control for `balanced`: train and val cut to exactly the
#                  same sizes, but with the natural class mix (stratified). Balanced vs
#                  subsampled isolates class balance; subsampled vs random isolates the
#                  smaller training set. Test unchanged.
# A variant MUST be written to its own PAPER_SUBDIR; writing one over the
# canonical split is refused below.
SPLIT_MODE = os.environ.get("SPLIT_MODE", "random")
SUBDIR = os.environ.get("PAPER_SUBDIR", cfg["paths"]["paper_subdir"])
if SPLIT_MODE not in ("random", "grouped", "chronological", "balanced", "subsampled"):
    raise SystemExit("unknown SPLIT_MODE %r" % SPLIT_MODE)
if SPLIT_MODE != "random" and SUBDIR == cfg["paths"]["paper_subdir"]:
    raise SystemExit("SPLIT_MODE=%s would overwrite the canonical split; set PAPER_SUBDIR"
                     % SPLIT_MODE)
OUT = os.path.join(paths.PROCESSED, SUBDIR)
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
print("Loading pooled features + multiclass labels + meta...")
X = np.vstack([
    pd.read_csv(os.path.join(paths.PROCESSED, "features_train.csv")).values,
    pd.read_csv(os.path.join(paths.PROCESSED, "features_test.csv")).values,
]).astype(np.float32)
y = np.concatenate([
    np.load(os.path.join(paths.PROCESSED, "labels_train_multiclass.npy"), allow_pickle=True),
    np.load(os.path.join(paths.PROCESSED, "labels_test_multiclass.npy"), allow_pickle=True),
])
y = np.array([_norm(s) for s in y])
# pooled meta (IP/port/timestamp), same row order as X — for RepeatedConnections + response replay
meta = pd.concat([
    pd.read_csv(os.path.join(paths.PROCESSED, "meta_train.csv")),
    pd.read_csv(os.path.join(paths.PROCESSED, "meta_test.csv")),
], ignore_index=True)
assert len(meta) == len(X), f"meta/X misalignment: {len(meta)} vs {len(X)}"
print(f"  pooled: X={X.shape}  y={y.shape}  meta={meta.shape}")

kind = np.array([classify(s) for s in y])
is_benign, is_known, is_zd = kind == "benign", kind == "known", kind == "zero_day"
n_known_atk = int(is_known.sum())

# ---- under-sample benign to ratio : known-attack count ----
n_benign_keep = min(int(round(P["benign_ratio"] * n_known_atk)), int(is_benign.sum()))
benign_idx = np.where(is_benign)[0]
benign_keep = np.random.RandomState(SEED).choice(benign_idx, size=n_benign_keep, replace=False)
print(f"\nknown-attack flows: {n_known_atk:,} | benign kept: {n_benign_keep:,} "
      f"(of {is_benign.sum():,}, ratio {P['benign_ratio']})")

# ---- split on INDICES so meta follows each row into train/val/test ----
known_pool = np.concatenate([benign_keep, np.where(is_known)[0]])
zd_idx = np.where(is_zd)[0]
SPLIT_NOTES = []
if SPLIT_MODE in ("random", "balanced", "subsampled"):
    tr_idx, tmp_idx = train_test_split(
        known_pool, test_size=P["val_frac"] + P["test_frac"], random_state=SEED,
        stratify=y[known_pool])
    rel = P["test_frac"] / (P["val_frac"] + P["test_frac"])
    val_idx, te_known_idx = train_test_split(
        tmp_idx, test_size=rel, random_state=SEED, stratify=y[tmp_idx])
    if SPLIT_MODE != "random":
        _rs = np.random.RandomState(SEED)

        def _balanced(idx, name):
            atk = sorted(c for c in set(y[idx].tolist()) if c != "BENIGN")
            n_min = min(int((y[idx] == c).sum()) for c in atk)
            keep = [_rs.choice(idx[y[idx] == c], n_min, replace=False) for c in atk]
            n_ben = min(int(round(P["benign_ratio"] * n_min * len(atk))),
                        int((y[idx] == "BENIGN").sum()))
            keep.append(_rs.choice(idx[y[idx] == "BENIGN"], n_ben, replace=False))
            SPLIT_NOTES.append("balanced %s: %d per known attack class (the smallest), "
                               "%d benign" % (name, n_min, n_ben))
            return idx[np.isin(idx, np.concatenate(keep))]

        def _subsampled(idx, n, name):
            keep, _ = train_test_split(idx, train_size=n, random_state=SEED, stratify=y[idx])
            SPLIT_NOTES.append("subsampled %s: %d flows, natural class mix" % (name, n))
            return idx[np.isin(idx, keep)]

        _btr, _bval = _balanced(tr_idx, "train"), _balanced(val_idx, "val")
        if SPLIT_MODE == "balanced":
            tr_idx, val_idx = _btr, _bval
        else:
            tr_idx = _subsampled(tr_idx, len(_btr), "train")
            val_idx = _subsampled(val_idx, len(_bval), "val")
        SPLIT_NOTES.append("test is the canonical test set, unchanged")
elif SPLIT_MODE == "grouped":
    # Group = Flow ID. Groups are fine-grained (no group holds more than 0.16 % of
    # any known class), so assigning whole groups at random keeps the class mix
    # close to stratified without a stratified-group solver.
    fid = meta["Flow ID"].astype(str).to_numpy()
    zd_groups = set(fid[zd_idx].tolist())
    forced = np.fromiter((f in zd_groups for f in fid[known_pool]), bool, len(known_pool))
    free = known_pool[~forced]
    ug, inv = np.unique(fid[free], return_inverse=True)
    u = np.random.RandomState(SEED).rand(len(ug))[inv]
    t, v = P["test_frac"], P["test_frac"] + P["val_frac"]
    tr_idx = free[u >= v]
    val_idx = free[(u >= t) & (u < v)]
    te_known_idx = np.concatenate([free[u < t], known_pool[forced]])
    SPLIT_NOTES.append("grouped by Flow ID; %d known/benign flows share a 5-tuple with a "
                       "zero-day flow and were sent to test" % int(forced.sum()))
    _tr = set(fid[tr_idx].tolist())
    assert not (_tr & set(fid[val_idx].tolist())), "LEAK: Flow ID shared train/val"
    assert not (_tr & set(fid[np.concatenate([te_known_idx, zd_idx])].tolist())), \
        "LEAK: Flow ID shared train/test"
    SPLIT_NOTES.append("[OK] no Flow ID appears in both train and val, or train and test")
else:  # chronological, within each known class
    import timeline
    ts_all = timeline.parse(meta["Timestamp"]).to_numpy()
    parts = {"train": [], "val": [], "test": []}
    for c in sorted(set(y[known_pool].tolist())):
        ii = known_pool[y[known_pool] == c]
        ii = ii[np.argsort(ts_all[ii], kind="stable")]
        a = int(round(len(ii) * (1 - P["val_frac"] - P["test_frac"])))
        b = int(round(len(ii) * (1 - P["test_frac"])))
        parts["train"].append(ii[:a]); parts["val"].append(ii[a:b]); parts["test"].append(ii[b:])
        SPLIT_NOTES.append("%-18s train <= %s | val %s .. %s | test >= %s"
                           % (c, ts_all[ii[a - 1]], ts_all[ii[a]], ts_all[ii[b - 1]],
                              ts_all[ii[b]]))
    tr_idx = np.concatenate(parts["train"])
    val_idx = np.concatenate(parts["val"])
    te_known_idx = np.concatenate(parts["test"])
te_idx = np.concatenate([te_known_idx, zd_idx])  # zero-day appended to TEST only

X_tr, y_tr = X[tr_idx], y[tr_idx]
X_val, y_val = X[val_idx], y[val_idx]
X_te, y_te = X[te_idx].astype(np.float32), y[te_idx]

# ---- binary labels ----
def to_bin(arr): return (arr != "BENIGN").astype(np.int8)

# ---- save features/labels/meta per split ----
np.save(os.path.join(OUT, "X_train.npy"), X_tr)
np.save(os.path.join(OUT, "X_val.npy"),   X_val)
np.save(os.path.join(OUT, "X_test.npy"),  X_te)
np.save(os.path.join(OUT, "y_train_mc.npy"), y_tr)
np.save(os.path.join(OUT, "y_val_mc.npy"),   y_val)
np.save(os.path.join(OUT, "y_test_mc.npy"),  y_te)
np.save(os.path.join(OUT, "y_train_bin.npy"), to_bin(y_tr))
np.save(os.path.join(OUT, "y_val_bin.npy"),   to_bin(y_val))
np.save(os.path.join(OUT, "y_test_bin.npy"),  to_bin(y_te))
meta.iloc[tr_idx].to_csv(os.path.join(OUT, "meta_train.csv"), index=False)
meta.iloc[val_idx].to_csv(os.path.join(OUT, "meta_val.csv"), index=False)
meta.iloc[te_idx].to_csv(os.path.join(OUT, "meta_test.csv"), index=False)
np.save(os.path.join(OUT, "known_classes.npy"), np.array(sorted(set(y_tr))))
np.save(os.path.join(OUT, "zero_day_classes.npy"), np.array(sorted(ZERO_DAY)))

# ---- CORRECTED timestamps as a typed artifact (added 2026-08-03) ----
# The raw `Timestamp` string in meta_*.csv is a TRAP: dates are D/M/YYYY (naive
# parsing scatters this 5-day capture across March/June/July) and the clock is
# 12-hour with no AM/PM (so 1 PM sorts before 9 AM). Emitting the corrected value
# as datetime64[s] here means downstream consumers get it right by default
# instead of having to know. See scripts/timeline.py.
import timeline
for _sp, _idx in (("train", tr_idx), ("val", val_idx), ("test", te_idx)):
    _ts = timeline.parse(meta.iloc[_idx]["Timestamp"])
    timeline.write_corrected(_sp, _ts, root=OUT)
print(f"wrote corrected timestamp_{{train,val,test}}.npy -> {OUT}")

# ---- report + leakage assertions ----
lines = []
def log(s): print(s); lines.append(s)

log("\n" + "=" * 60)
log("PAPER-ALIGNED SPLIT REPORT" + ("" if SPLIT_MODE == "random" else "  (SPLIT_MODE=%s)" % SPLIT_MODE))
for _n in SPLIT_NOTES:
    log(_n)
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

with open(os.path.join(OUT, "split_report.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
log(f"\nSaved -> {OUT}")

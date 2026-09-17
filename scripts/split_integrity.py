"""
split_integrity.py — measure what crosses the train/test boundary of the paper split.

WHY THIS EXISTS
---------------
The 2026-09-16 audit measured five properties of the paper-aligned split that no
record held, although the write-up and the audit both depend on them:

  F-10  exact feature-vector duplicates across train/test      (17.02 %)
  F-02  test flows whose 5-tuple (Flow ID) also occurs in train (54.88 %;
        100 % for four DoS families AND all three Web Attack zero-day families)
  F-03  test flows inside the training time range               (100 %)
  F-04  how much benign was removed before the split            (4.11x)
  F-15  whether the constant columns dropped in preprocess.py are constant on the
        paper TRAIN split alone (they were selected on the temporal train half)

`comparability.py` already measures F-10 and reports a deduplicated metric. The
others had no record at all. This script measures all five from the artefacts, per
class where it matters, and `tests/test_split_integrity.py` asserts the boundary
properties that must hold and pins the measured values so a regression is visible.

It reads data only; no model is loaded and nothing is trained.

Run:  python scripts/split_integrity.py
Out:  outputs/metadata/split_integrity.json
"""
import os
import sys
import json
import hashlib

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                        # noqa: E402
import config                                       # noqa: E402
import timeline                                     # noqa: E402


def _norm(s):
    return " ".join(str(s).replace("\x96", " ").replace("�", " ").split())


def main():
    # PAPER_SUBDIR measures a variant split (grouped / chronological, audit D4)
    # and writes split_integrity_<subdir>.json; unset, the canonical split.
    sub = os.environ.get("PAPER_SUBDIR", "")
    P = os.path.join(paths.PROCESSED, sub) if sub else paths.PAPER
    cfg = config.get()
    zero_day = set(cfg["zero_day_classes"])
    out = {}

    y = {s: np.load(os.path.join(P, "y_%s_mc.npy" % s), allow_pickle=True)
         for s in ("train", "val", "test")}
    X = {s: np.load(os.path.join(P, "X_%s.npy" % s)) for s in ("train", "val", "test")}

    # ---- label boundary -------------------------------------------------------
    out["zero_day_in_train"] = sorted(set(y["train"].tolist()) & zero_day)
    out["zero_day_in_val"] = sorted(set(y["val"].tolist()) & zero_day)
    out["n_features"] = int(X["train"].shape[1])
    out["sizes"] = {s: int(len(y[s])) for s in y}

    # ---- F-10: exact duplicates ----------------------------------------------
    def hashes(A):
        return [hashlib.blake2b(r.tobytes(), digest_size=16).digest() for r in A]
    h_tr = set(hashes(X["train"]))
    h_te = hashes(X["test"])
    dup = np.fromiter((h in h_tr for h in h_te), bool, len(h_te))
    out["duplicates"] = {
        "test_rows_duplicated_in_train": int(dup.sum()),
        "fraction": float(dup.mean()),
        "per_class": {c: float(dup[y["test"] == c].mean())
                      for c in sorted(set(y["test"].tolist()))},
    }

    # ---- F-02: grouped-split violation ---------------------------------------
    meta = {s: pd.read_csv(os.path.join(P, "meta_%s.csv" % s)) for s in ("train", "test")}
    fid_tr = set(meta["train"]["Flow ID"].astype(str))
    fid = np.fromiter((f in fid_tr for f in meta["test"]["Flow ID"].astype(str)),
                      bool, len(meta["test"]))
    sip_tr = set(meta["train"]["Source IP"].astype(str))
    sip = np.fromiter((s in sip_tr for s in meta["test"]["Source IP"].astype(str)),
                      bool, len(meta["test"]))
    out["group_overlap"] = {
        "flow_id_fraction": float(fid.mean()),
        "flow_id_per_class": {c: float(fid[y["test"] == c].mean())
                              for c in sorted(set(y["test"].tolist()))},
        "source_ip_fraction": float(sip.mean()),
    }

    # ---- F-03: temporal overlap (corrected timestamps only) -------------------
    ts_tr = timeline.load_timestamps("train", root=P)
    ts_te = timeline.load_timestamps("test", root=P)
    inside = (ts_te >= ts_tr.min()) & (ts_te <= ts_tr.max())
    out["temporal"] = {
        "train_start": str(ts_tr.min()), "train_end": str(ts_tr.max()),
        "test_start": str(ts_te.min()), "test_end": str(ts_te.max()),
        "test_inside_train_range": float(np.asarray(inside).mean()),
    }

    # ---- F-04: benign under-sampling ------------------------------------------
    pooled = np.concatenate([
        np.load(os.path.join(paths.PROCESSED, "labels_%s_multiclass.npy" % s), allow_pickle=True)
        for s in ("train", "test")])
    pooled = np.array([_norm(s) for s in pooled])
    n_benign_pool = int((pooled == "BENIGN").sum())
    n_benign_kept = int(sum((y[s] == "BENIGN").sum() for s in y))
    out["benign"] = {
        "pooled": n_benign_pool, "kept": n_benign_kept,
        "undersample_factor": n_benign_pool / n_benign_kept,
        "pooled_share": n_benign_pool / len(pooled),
        "test_share": float((y["test"] == "BENIGN").mean()),
    }

    # ---- F-15: were the dropped columns constant on paper train alone? --------
    dropped = [str(c) for c in np.load(os.path.join(paths.PROCESSED, "constant_cols_dropped.npy"),
                                        allow_pickle=True)]
    raw_cols = pd.read_csv(os.path.join(paths.PROCESSED, "features_train.csv"), nrows=0).columns
    # preprocess.py chose these on the TEMPORAL train half (Mon-Wed) only. The
    # audit assumed they were constant everywhere; measured, two are not.
    cc = {"dropped": dropped,
          "any_dropped_column_still_present": bool(set(dropped) & set(raw_cols)),
          "checked_on_full_capture": False}
    if os.path.isdir(paths.RAW_CSV_FULL):
        nonconst = {}
        for fn in sorted(os.listdir(paths.RAW_CSV_FULL)):
            fp = os.path.join(paths.RAW_CSV_FULL, fn)
            hdr = pd.read_csv(fp, nrows=0, encoding="latin-1").columns
            use = [h for h in hdr if h.strip() in set(dropped) | {"Label", "URG Flag Count"}]
            df = pd.read_csv(fp, usecols=use, encoding="latin-1", low_memory=False)
            df.columns = df.columns.str.strip()
            for c in dropped:
                v = pd.to_numeric(df[c], errors="coerce")
                m = v.notna() & (v != 0)
                if m.any():
                    e = nonconst.setdefault(c, {"rows": 0, "labels": {}, "files": [],
                                                "urg_flag_count_also_1": 0})
                    e["rows"] += int(m.sum())
                    e["files"].append(fn)
                    for lab, n in df.loc[m, "Label"].astype(str).str.strip().value_counts().items():
                        e["labels"][lab] = e["labels"].get(lab, 0) + int(n)
                    e["urg_flag_count_also_1"] += int(
                        (pd.to_numeric(df.loc[m, "URG Flag Count"], errors="coerce") == 1).sum())
        cc.update({"checked_on_full_capture": True, "non_constant_on_full_capture": nonconst})
    out["constant_columns"] = cc

    out["split_dir"] = os.path.relpath(P, paths.ROOT)
    p = os.path.join(paths.METADATA, "split_integrity%s.json" % ("_" + sub if sub else ""))
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)

    print("SPLIT INTEGRITY — paper split")
    print("  zero-day in train/val     : %s / %s" % (out["zero_day_in_train"] or "none",
                                                     out["zero_day_in_val"] or "none"))
    print("  exact duplicates (F-10)   : %.2f %% of test rows" % (100 * out["duplicates"]["fraction"]))
    print("  Flow-ID overlap  (F-02)   : %.2f %% of test rows" % (100 * out["group_overlap"]["flow_id_fraction"]))
    print("  Source-IP overlap         : %.2f %%" % (100 * out["group_overlap"]["source_ip_fraction"]))
    print("  test inside train window  : %.2f %% (F-03)" % (100 * out["temporal"]["test_inside_train_range"]))
    print("  benign under-sample       : %.2fx (F-04)" % out["benign"]["undersample_factor"])
    print("wrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())

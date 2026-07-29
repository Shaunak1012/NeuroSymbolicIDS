"""
preprocess.py — clean the CIC-IDS2017 GeneratedLabelledFlows (full variant) into the
numeric feature matrices + labels used by every downstream script, PLUS an aligned
IP/port/timestamp META side-table (enables RepeatedConnections + response replay).

Input : data/raw_csv_full/  (85-col CSVs WITH Flow ID / IPs / Ports / Protocol / Timestamp)
Split : temporal — Train = Mon+Tue+Wed, Test = Thu+Fri (secondary "hard-mode" benchmark;
        the paper protocol re-pools these in preprocess_paper.py).

Outputs -> data/processed/ :
  features_train.csv  features_test.csv            (68 numeric features, whitespace/constant-cleaned)
  labels_train.npy    labels_test.npy              (binary 0/1)
  labels_train_binary.npy labels_test_binary.npy   (== above, explicit)
  labels_train_multiclass.npy labels_test_multiclass.npy   (string labels)
  meta_train.csv      meta_test.csv                (Flow ID, Source/Dest IP+Port, Protocol, Timestamp)
  constant_cols_dropped.npy

The 68 numeric feature columns are identical to the ML-CVE variant (Destination Port kept as a
feature; the other 6 identifiers moved to meta). Behaviour indices in behavior.py stay valid.
"""
import os
import numpy as np
import pandas as pd

import paths

RAW = paths.RAW_CSV_FULL

TRAIN_FILES = ["Monday-WorkingHours.pcap_ISCX.csv",
               "Tuesday-WorkingHours.pcap_ISCX.csv",
               "Wednesday-workingHours.pcap_ISCX.csv"]
TEST_FILES = ["Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv",
              "Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv",
              "Friday-WorkingHours-Morning.pcap_ISCX.csv",
              "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv",
              "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv"]

# 7 identifier columns -> META. All but Destination Port are dropped from features.
META_COLS = ["Flow ID", "Source IP", "Source Port", "Destination IP",
             "Destination Port", "Protocol", "Timestamp"]
DROP_FROM_FEATURES = ["Flow ID", "Source IP", "Source Port", "Destination IP",
                      "Protocol", "Timestamp"]  # keep Destination Port as a feature


def load_day(fname):
    df = pd.read_csv(os.path.join(RAW, fname), low_memory=False, encoding="latin-1")
    df.columns = df.columns.str.strip()
    return df


def load_split(files, name):
    df = pd.concat([load_day(f) for f in files], ignore_index=True)
    print(f"  {name}: raw {df.shape}")
    return df


def clean(df, name):
    before = len(df)
    label_mc = df["Label"].astype(str).str.strip()
    meta = df[META_COLS].copy()
    feats = df.drop(columns=META_COLS + ["Label"])
    # coerce every feature column to numeric (handles "Infinity"/"NaN" strings), then drop bad rows
    feats = feats.apply(pd.to_numeric, errors="coerce")
    feats.replace([np.inf, -np.inf], np.nan, inplace=True)
    good = feats.notna().all(axis=1)
    feats, meta, label_mc = feats[good].reset_index(drop=True), meta[good].reset_index(drop=True), label_mc[good].reset_index(drop=True)
    print(f"  {name}: dropped {before - len(feats):,} inf/nan rows "
          f"({100*(before-len(feats))/before:.2f}%), {len(feats):,} remain")
    return feats, meta, label_mc


print("Loading full-variant CSVs (data/raw_csv_full)...")
train_df = load_split(TRAIN_FILES, "train")
test_df = load_split(TEST_FILES, "test")

Xtr, meta_tr, y_tr_mc = clean(train_df, "train")
Xte, meta_te, y_te_mc = clean(test_df, "test")

# keep Destination Port as feature 0 (drop only the other identifiers — already excluded from Xtr/Xte)
# (Xtr/Xte already exclude META_COLS incl. Destination Port; add Destination Port back as a feature)
Xtr.insert(0, "Destination Port", meta_tr["Destination Port"].astype(np.int64).values)
Xte.insert(0, "Destination Port", meta_te["Destination Port"].astype(np.int64).values)

# align columns, drop constants (computed on train)
common = [c for c in Xtr.columns if c in Xte.columns]
Xtr, Xte = Xtr[common], Xte[common]
nunique = Xtr.nunique()
const_cols = nunique[nunique <= 1].index.tolist()
print(f"\nDropping {len(const_cols)} constant columns: {const_cols}")
Xtr = Xtr.drop(columns=const_cols)
Xte = Xte.drop(columns=const_cols, errors="ignore")[Xtr.columns]

print(f"Final feature count: {Xtr.shape[1]}  | train {Xtr.shape[0]:,}  test {Xte.shape[0]:,}")

# labels
y_tr_bin = (y_tr_mc != "BENIGN").astype(int).values
y_te_bin = (y_te_mc != "BENIGN").astype(int).values

# save
Xtr.to_csv(os.path.join(paths.PROCESSED, "features_train.csv"), index=False)
Xte.to_csv(os.path.join(paths.PROCESSED, "features_test.csv"), index=False)
np.save(os.path.join(paths.PROCESSED, "labels_train.npy"), y_tr_bin)
np.save(os.path.join(paths.PROCESSED, "labels_test.npy"), y_te_bin)
np.save(os.path.join(paths.PROCESSED, "labels_train_binary.npy"), y_tr_bin)
np.save(os.path.join(paths.PROCESSED, "labels_test_binary.npy"), y_te_bin)
np.save(os.path.join(paths.PROCESSED, "labels_train_multiclass.npy"), y_tr_mc.values)
np.save(os.path.join(paths.PROCESSED, "labels_test_multiclass.npy"), y_te_mc.values)
meta_tr.to_csv(os.path.join(paths.PROCESSED, "meta_train.csv"), index=False)
meta_te.to_csv(os.path.join(paths.PROCESSED, "meta_test.csv"), index=False)
np.save(os.path.join(paths.PROCESSED, "constant_cols_dropped.npy"), np.array(const_cols))

print("\nDONE. Produced features_*.csv, labels_*, meta_*.csv (IP/port/timestamp), constant_cols_dropped.npy")
print(f"  train attack ratio {y_tr_bin.mean():.4f}  |  test attack ratio {y_te_bin.mean():.4f}")

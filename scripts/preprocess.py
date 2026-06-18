import pandas as pd
import numpy as np
import os
import paths

# =========================
# PATHS (see scripts/paths.py)
#   inputs  -> paths.RAW_CSV
#   outputs -> paths.PROCESSED
# =========================
DATA_PATH = paths.RAW_CSV

# =========================
# PART 1 — LOAD AND CLEAN
# =========================

print("Loading CSVs...")
mon  = pd.read_csv(os.path.join(DATA_PATH, "Monday-WorkingHours.pcap_ISCX.csv"))
tue  = pd.read_csv(os.path.join(DATA_PATH, "Tuesday-WorkingHours.pcap_ISCX.csv"))
wed  = pd.read_csv(os.path.join(DATA_PATH, "Wednesday-workingHours.pcap_ISCX.csv"))

thu1 = pd.read_csv(os.path.join(DATA_PATH, "Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv"))
thu2 = pd.read_csv(os.path.join(DATA_PATH, "Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv"))
fri1 = pd.read_csv(os.path.join(DATA_PATH, "Friday-WorkingHours-Morning.pcap_ISCX.csv"))
fri2 = pd.read_csv(os.path.join(DATA_PATH, "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv"))
fri3 = pd.read_csv(os.path.join(DATA_PATH, "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv"))

train_df = pd.concat([mon, tue, wed],               ignore_index=True)
test_df  = pd.concat([thu1, thu2, fri1, fri2, fri3], ignore_index=True)

# Strip whitespace from column names (CICIDS CSVs have leading spaces)
train_df.columns = train_df.columns.str.strip()
test_df.columns  = test_df.columns.str.strip()

print(f"Raw train shape : {train_df.shape}")
print(f"Raw test shape  : {test_df.shape}")

# =========================
# CLEAN — inf/nan only, NO deduplication
# =========================
def clean_df(df, name):
    before = len(df)
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.dropna(inplace=True)
    print(f"  {name}: dropped {before - len(df):,} rows with inf/nan "
          f"({100*(before-len(df))/before:.2f}%), {len(df):,} remain")
    return df.reset_index(drop=True)

train_df = clean_df(train_df, "train")
test_df  = clean_df(test_df,  "test")

# Save original string labels BEFORE binary encoding
# Needed for multiclass CNN and LTN axioms later
train_df['Label_multiclass'] = train_df['Label'].str.strip()
test_df['Label_multiclass']  = test_df['Label'].str.strip()

print("\nTrain attack type distribution:")
print(train_df['Label_multiclass'].value_counts())
print("\nTest attack type distribution (zero-day targets):")
print(test_df['Label_multiclass'].value_counts())

train_df.to_csv(os.path.join(paths.PROCESSED, "clean_train.csv"), index=False)
test_df.to_csv(os.path.join(paths.PROCESSED, "clean_test.csv"),   index=False)
print("\nPart 1 DONE — clean_train.csv and clean_test.csv saved")
print(f"Saved to: {os.path.join(paths.PROCESSED, 'clean_train.csv')}")


# =========================
# PART 2 — FEATURE ENGINEERING AND LABEL ENCODING
# =========================

train_df = pd.read_csv(os.path.join(paths.PROCESSED, "clean_train.csv"))
test_df  = pd.read_csv(os.path.join(paths.PROCESSED, "clean_test.csv"))

# DROP IDENTIFIER COLUMNS
drop_cols = ['Flow ID', 'Source IP', 'Destination IP', 'Timestamp']
train_df.drop(columns=[c for c in drop_cols if c in train_df.columns], inplace=True)
test_df.drop(columns=[c for c in drop_cols  if c in test_df.columns],  inplace=True)

# BINARY LABELS
train_df['Label'] = (train_df['Label'].str.strip() != 'BENIGN').astype(int)
test_df['Label']  = (test_df['Label'].str.strip()  != 'BENIGN').astype(int)

# SAVE MULTICLASS LABELS SEPARATELY before dropping the column
y_train_multiclass = train_df['Label_multiclass'].values
y_test_multiclass  = test_df['Label_multiclass'].values

np.save(os.path.join(paths.PROCESSED, "labels_train_multiclass.npy"), y_train_multiclass)
np.save(os.path.join(paths.PROCESSED, "labels_test_multiclass.npy"),  y_test_multiclass)

train_df.drop(columns=['Label_multiclass'], inplace=True)
test_df.drop(columns=['Label_multiclass'],  inplace=True)

# COLUMN ALIGNMENT
common_cols      = [c for c in train_df.columns if c in test_df.columns]
missing_in_test  = set(train_df.columns) - set(test_df.columns)
missing_in_train = set(test_df.columns)  - set(train_df.columns)

if missing_in_test:
    print(f"\nWARNING: {len(missing_in_test)} train columns missing from test: {missing_in_test}")
if missing_in_train:
    print(f"WARNING: {len(missing_in_train)} test columns missing from train: {missing_in_train}")

train_df = train_df[common_cols]
test_df  = test_df[common_cols]

# SPLIT FEATURES AND LABELS
X_train = train_df.drop('Label', axis=1)
y_train = train_df['Label'].values

X_test  = test_df.drop('Label', axis=1)
y_test  = test_df['Label'].values

print(f"\nAfter alignment:")
print(f"  X_train: {X_train.shape}  attack ratio: {y_train.mean():.4f}")
print(f"  X_test : {X_test.shape}   attack ratio: {y_test.mean():.4f}")

# REMOVE CONSTANT COLUMNS (computed on train only)
nunique       = X_train.nunique()
constant_cols = nunique[nunique <= 1].index.tolist()
print(f"\nDropping {len(constant_cols)} constant columns: {constant_cols}")

# Save the list so future inference and LTN pipelines apply the same drop
np.save(os.path.join(paths.PROCESSED, "constant_cols_dropped.npy"), np.array(constant_cols))

X_train.drop(columns=constant_cols, inplace=True)
X_test.drop(columns=constant_cols,  inplace=True, errors='ignore')

# FINAL ALIGNMENT
missing_after = set(X_train.columns) - set(X_test.columns)
if missing_after:
    raise ValueError(
        f"Columns in train missing from test after constant drop: {missing_after}\n"
        f"Test had these as constant but train did not. Add to drop_cols manually."
    )

X_test = X_test[X_train.columns]  

print(f"\nFinal feature count : {X_train.shape[1]}")
print(f"Final train samples : {X_train.shape[0]:,}")
print(f"Final test samples  : {X_test.shape[0]:,}")

# SAVE
X_train.to_csv(os.path.join(paths.PROCESSED, "features_train.csv"), index=False)
X_test.to_csv(os.path.join(paths.PROCESSED, "features_test.csv"),   index=False)

np.save(os.path.join(paths.PROCESSED, "labels_train.npy"), y_train)
np.save(os.path.join(paths.PROCESSED, "labels_test.npy"),  y_test)

print("\nPart 2 DONE")
print("\nFiles produced:")
print("  features_train.csv / features_test.csv       — features for CNN")
print("  labels_train.npy / labels_test.npy           — binary labels")
print("  labels_train_multiclass.npy                  — string labels for multiclass CNN + LTN")
print("  labels_test_multiclass.npy                   — string labels for multiclass CNN + LTN")
print("  constant_cols_dropped.npy                    — columns dropped at inference time")
# Pipeline Execution Guide

> ⚠️ **FROZEN (banner added 2026-07-29) — this is the legacy temporal-split run order.**
> The current pipeline is in [README.md → Quick Start](../README.md#quick-start) and
> [scripts_reference.md](scripts_reference.md). The four steps below still execute, but they
> produce the **superseded** temporal-split artifacts; no reported result uses them.
> The "Expected baseline: PR-AUC ~0.45–0.55" figure at Step 3 is a stale temporal-split
> estimate — current numbers are in [STATUS.md](STATUS.md) and [README](../README.md#key-results).

## Prerequisites

```bash
# Use the project venv (Python 3.11). Install pinned deps:
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Raw CSV files must be present in `data/raw_csv/` (not committed to git — files are large).

> **Output locations:** the filenames listed under each step below are written to organised subfolders, **not** the repo root — `data/processed/`, `models/`, `outputs/{arrays,embeddings,predictions,metadata,figures}/`. The exact mapping is defined in [`scripts/paths.py`](../scripts/paths.py); see [artifacts.md](artifacts.md#where-everything-lives). Run scripts with the venv interpreter from the project root.

## Step 1 — Preprocessing

```bash
python scripts/preprocess.py
```

**What it does:**
- Reads all 8 raw CSV files
- Strips whitespace from column names (CIC-IDS2017 quirk)
- Removes rows with `inf` or `NaN` values (duplicates are kept intentionally)
- Creates binary labels: BENIGN → 0, any attack → 1
- Creates multiclass labels: 9 training types → 0–8, zero-day types → −1
- Drops identifier columns (Flow ID, IPs, Timestamp)
- Drops zero-variance (constant) columns; saves dropped names to `constant_cols_dropped.npy`
- Aligns train/test column sets

**Outputs:**
```
clean_train.csv                  # ~1.67M rows, all columns including labels
clean_test.csv                   # ~1.16M rows
features_train.csv               # 70 numeric features only
features_test.csv
labels_train.npy                 # binary (0/1)
labels_test.npy
labels_train_binary.npy          # same as above, explicit copy
labels_test_binary.npy
labels_train_multiclass.npy      # string attack type names
labels_test_multiclass.npy
constant_cols_dropped.npy        # column names removed
```

## Step 2 — CNN Training

```bash
python scripts/cnn3.py
```

**What it does:**
- Loads `features_train.csv` and label arrays
- Fits `StandardScaler` on training data only
- Reshapes features → `(N, 70, 1)` for Conv1D
- Stratified 80/20 train/val split
- Trains 1D CNN with Focal Loss and class weights
- Extracts 64-dim embeddings from the `Dense(64)` layer for train, val, and test sets
- Saves best checkpoint via `ModelCheckpoint`

**Outputs:**
```
model_multiclass.keras           # final model
model_multiclass_best.keras      # best checkpoint (EarlyStopping)
scaler.pkl                       # StandardScaler (fit on train)
label_encoder.pkl                # LabelEncoder (9 training classes)
class_names.npy                  # array of 9 class name strings
zero_day_classes.npy             # array of zero-day class names
X_test.npy                       # scaled test features, shape (N_test, 70, 1)
X_train_emb.npy                  # 64-dim embeddings, shape (N_train, 64)
X_val_emb.npy                    # shape (N_val, 64)
X_test_emb.npy                   # shape (N_test, 64)
y_train.npy                      # multiclass labels, train
y_val.npy                        # multiclass labels, val
y_test.npy                       # multiclass labels, test (−1 = zero-day)
history.pkl                      # per-epoch loss/accuracy dict
```

## Step 3 — CNN Evaluation (Baseline)

```bash
python scripts/eval.py
```

**What it does:**
- Loads `model_multiclass_best.keras` and test data
- Runs inference to get 9-class softmax outputs
- Derives binary probability: `P(attack) = 1 − P(BENIGN)`
- Reports binary detection metrics: Precision, Recall, F1, FPR, FNR, PR-AUC, ROC-AUC
- Reports per-family recall on each zero-day attack type
- Reports known-class performance on test set
- Generates 6-subplot evaluation dashboard

**Outputs:**
```
y_prob_test.npy                  # (N_test, 9) softmax outputs
y_prob_test_bin.npy              # (N_test,) P(attack) scores
cnn_zeroday_eval.png             # 6-subplot visualisation
```

**Expected baseline:** PR-AUC ~0.45–0.55, zero-day recall ~5–15% per family.

## Step 4 — Neuro-Symbolic Training (Hybrid-LTN)

```bash
python scripts/ltn.py
```

**What it does:**
- Retrains CNN from scratch with **Hybrid Loss = Focal CE Loss + ω × SAT Loss**
- Computes behavioural thresholds from training data (via `behavior.py`)
- Applies 4 fuzzy logic axioms as soft constraints during each training step
- Uses adaptive ω weight that adjusts based on axiom satisfaction rate
- Evaluates on test set and compares against CNN baseline
- Generates 9-subplot dashboard comparing both approaches

**Outputs:**
```
ltn_model_best.keras             # best Hybrid-LTN checkpoint
ltn_model_final.keras            # model after all epochs
scaler_ltn.pkl                   # scaler for LTN pipeline
behaviour_thresholds.npy         # computed percentile thresholds
X_train_ltn_emb.npy             # embeddings from LTN model
X_val_ltn_emb.npy
X_test_ltn_emb.npy
y_prob_ltn_test.npy              # (N_test, 9) LTN softmax outputs
y_prob_ltn_bin.npy               # (N_test,) LTN P(attack) scores
ltn_history.pkl                  # per-epoch metrics incl. axiom satisfaction
ltn_eval.png                     # 9-subplot comparison dashboard
```

## Optional Utilities

```bash
# Visualise preprocessing impact (row counts, missing values, duplicates)
python scripts/visual.py

# Inspect feature names with indices (useful for verifying behavior.py groups)
python scripts/check.py
```

## Common Issues

| Issue | Likely Cause | Fix |
|-------|-------------|-----|
| `FileNotFoundError` on CSV files | `data/raw_csv/` not populated | Download CIC-IDS2017 dataset |
| `KeyError` on column names | Raw CSV has leading-space column names | Already handled in `preprocess.py` |
| OOM during training | Large batch size | Reduce `batch_size` in `cnn3.py` (inline, `=256`) |
| Mismatched feature counts | `constant_cols_dropped.npy` not saved | Re-run `preprocess.py` first |

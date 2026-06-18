# Scripts Reference

All scripts live in `scripts/`. Run them from the project root using the venv interpreter (`.venv\Scripts\python.exe`).

---

## `scripts/paths.py`

**Purpose**: Central definition of every filesystem location. All other scripts `import paths` and reference its constants, so artifacts land in a consistent tree instead of the repo root.

**Constants**: `RAW_CSV`, `PROCESSED`, `MODELS`, `ARRAYS`, `EMBEDDINGS`, `PREDICTIONS`, `METADATA`, `FIGURES` (+ `ROOT`). Output directories are created on import via `os.makedirs(..., exist_ok=True)`.

**To relocate any artifact**, edit `paths.py` only — never hardcode paths in the pipeline scripts.

> Import works because running `python scripts/<x>.py` puts `scripts/` on `sys.path`. Always run scripts from the project root.

---

## `scripts/preprocess.py`

**Purpose**: Load and clean raw CIC-IDS2017 CSVs, engineer features, and create label arrays.

**Depends on**: Raw CSV files in `data/raw_csv/`

**Key steps**:
1. Concatenate Monday–Wednesday CSVs → train set
2. Concatenate Thursday–Friday CSVs → test set
3. Strip leading/trailing whitespace from column names
4. Drop rows with `inf` or `NaN` values
5. Remove identifier columns: Flow ID, Source IP, Destination IP, Timestamp
6. Create binary labels (BENIGN=0, any attack=1)
7. Create multiclass labels (9 training types → 0–8, zero-day → −1)
8. Drop constant (zero-variance) columns; save names to `constant_cols_dropped.npy`
9. Align train/test column sets to the same 70 features
10. Save `clean_*.csv`, `features_*.csv`, all label `.npy` files

**Inputs**: `data/raw_csv/*.csv`  
**Outputs**: See [artifacts.md](artifacts.md) — CSV Data Files and Label Arrays sections

---

## `scripts/cnn3.py`

**Purpose**: Train the 1D CNN multiclass classifier and extract learned embeddings.

**Depends on**: `features_train.csv`, `features_test.csv`, `labels_train_multiclass.npy`, `labels_test_multiclass.npy`, `constant_cols_dropped.npy`

**Key steps**:
1. Load features and multiclass labels
2. Encode labels with `LabelEncoder` (9 classes; zero-day flows excluded from training)
3. Stratified 80/20 train/val split
4. Fit `StandardScaler` on train only, apply to val and test
5. Reshape → `(N, 70, 1)` for Conv1D
6. Build 1D CNN: Conv1D×3 → Flatten → Dense(64) → Dense(32) → Dense(9, softmax)
7. Train with Focal Loss, class weights, EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
8. Extract 64-dim embeddings from `Dense(64)` for train/val/test
9. Save models, scaler, encoder, embeddings, labels, history

**Inputs**: `features_train.csv`, `features_test.csv`, label arrays  
**Outputs**: `model_multiclass.keras`, `model_multiclass_best.keras`, `scaler.pkl`, `label_encoder.pkl`, `X_*_emb.npy`, `y_*.npy`, `history.pkl`, `class_names.npy`, `zero_day_classes.npy`, `X_test.npy`

---

## `scripts/eval.py`

**Purpose**: Evaluate the CNN baseline on zero-day detection.

**Depends on**: `model_multiclass_best.keras`, `X_test.npy`, `y_test_bin.npy`, `y_test.npy`, `zero_day_classes.npy`, `labels_test_multiclass.npy`, `history.pkl`

**Reports generated**:
1. **Binary detection** — Precision, Recall, F1, Accuracy, FPR, FNR, PR-AUC, ROC-AUC
2. **Per-family recall** — Recall for each zero-day attack type (Web Attacks, Infiltration, DDoS, PortScan)
3. **Known class performance** — Accuracy on flows from known (training) classes in the test set

**Visualisation** (`cnn_zeroday_eval.png`, 6 subplots):
- Training accuracy curve
- Training loss curve
- Precision-Recall curve with AUC
- Binary confusion matrix heatmap
- Zero-day family recall bar chart
- Score distribution (BENIGN vs attack vs zero-day)

**Inputs**: Model + test arrays  
**Outputs**: `y_prob_test.npy`, `y_prob_test_bin.npy`, `cnn_zeroday_eval.png`

---

## `scripts/behavior.py`

**Purpose**: Library module for symbolic behaviour extraction from raw feature arrays.

**Not run directly** — imported by `ltn.py`.

**Functions**:

| Function | Description |
|----------|-------------|
| `compute_thresholds(X_train)` | Compute percentile thresholds from training data |
| `load_thresholds(path)` | Load saved thresholds with fallback defaults |
| `extract_behaviour(X, thresholds)` | Convert `(N, 70, 1)` → list of N behaviour dicts |

**Atomic flags**: `high_traffic`, `large_packets`, `high_rate`, `high_variance`, `high_mean`, `bursty_iat`  
**Compound patterns**: `scan_pattern`, `exfil_pattern`, `covert_pattern`

See [neuro_symbolic.md](neuro_symbolic.md) for full details.

---

## `scripts/ltn.py`

**Purpose**: Train the Hybrid-LTN model (CNN + fuzzy logic axioms) and compare to CNN baseline.

**Depends on**: `features_train.csv`, `features_test.csv`, all label arrays, `behavior.py`

**Key steps**:
1. Load features and labels (same preprocessing as `cnn3.py`)
2. Fit scaler, split train/val
3. Compute behaviour thresholds → save `behaviour_thresholds.npy`
4. Build same 1D CNN architecture
5. Custom training loop (not `model.fit()`):
   - Each step: compute Focal CE Loss + SAT Loss (4 fuzzy axioms)
   - Adaptive ω updates each epoch based on axiom satisfaction
6. Save best checkpoint, evaluate on test set
7. Compare LTN vs CNN baseline metrics
8. Extract LTN embeddings
9. Generate 9-subplot evaluation dashboard → `ltn_eval.png`

**Inputs**: Same as `cnn3.py` + `behavior.py`  
**Outputs**: `ltn_model_best.keras`, `ltn_model_final.keras`, `scaler_ltn.pkl`, `behaviour_thresholds.npy`, `X_*_ltn_emb.npy`, `y_prob_ltn_*.npy`, `ltn_history.pkl`, `ltn_eval.png`

---

## `scripts/visual.py`

**Purpose**: Visualise the impact of preprocessing on data quality.

**Depends on**: Raw CSV files (reads them again directly)

**Outputs**: 3-panel bar chart (inline display, not saved to file):
- Row count: before vs after cleaning
- Missing values: before vs after
- Duplicate rows: before vs after

---

## `scripts/check.py`

**Purpose**: Print the first 30 feature column names with their indices.

**Depends on**: `features_train.csv`

**Usage**:
```bash
python scripts/check.py
```
Use this to verify that feature group index ranges in `behavior.py` match the actual column order after preprocessing (which can vary if `constant_cols_dropped.npy` changes).

---

## `utils/config.py` — REMOVED (2026-06-18)

This file was **deleted** as dead code. It was a leftover from an abandoned raw-PCAP/payload pipeline (`PAYLOAD_LEN=1500`, 3 classes, `data/raw_pcaps/`, attack time-windows) and was imported by nothing.

The active scripts (`preprocess.py`, `cnn3.py`, `eval.py`, `ltn.py`) have **no centralised config** — each defines paths and hyperparameters inline. If centralised config is wanted later, create a fresh module that the scripts actually import.

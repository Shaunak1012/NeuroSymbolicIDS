# Artifacts Catalog

This file catalogs every generated file, its shape/size, and what produced it.

> **Two artifact generations coexist on disk.** The **paper-split** artifacts (current — everything
> below the "Paper-split artifacts" heading) are what all reported results use. The **temporal-split**
> artifacts (legacy, the rest of this file) are from the superseded protocol and are kept only for the
> secondary hard-mode comparison. Filenames disambiguate them: paper-split models and predictions
> carry a run tag (`cnn_paper`, `ltn_ctrl_w0`, `ltn_ax6_ratio_w1p0_s43`, …), legacy ones do not
> (`model_multiclass.keras`, `y_prob_test.npy`).

## Paper-split artifacts (current)

### `data/processed/paper/` — the split itself (`paths.PAPER`)

| File | Shape | Produced by |
|---|---|---|
| `X_{train,val,test}.npy` | (883,796 / 110,475 / 114,658, **68**) float32 | `preprocess_paper.py` |
| `y_{train,val,test}_mc.npy` | (N,) string class labels | `preprocess_paper.py` |
| `y_{train,val,test}_bin.npy` | (N,) 0/1 | `preprocess_paper.py` |
| `meta_{train,val,test}.csv` | (N, 7) Flow ID / Source+Dest IP / Ports / Protocol / Timestamp | `preprocess_paper.py` |
| `known_classes.npy` | (9,) str | `preprocess_paper.py` |
| `zero_day_classes.npy` | (6,) str | `preprocess_paper.py` |
| `split_report.txt` | text | `preprocess_paper.py` |

> `meta_*.csv` is aligned **row-for-row** with the corresponding `X_*.npy`. This is what unblocks
> `RepeatedConnections`, source-level response replay, and any IP/time-aware Knowledge Graph work.

### Models (`models/`)

| Pattern | Produced by |
|---|---|
| `cnn_paper.keras`, `cnn_paper_best.keras` | `cnn_paper.py` |
| `scaler_paper.pkl`, `label_encoder_paper.pkl` | `cnn_paper.py` |
| `cnn_auxhead_l0.5.keras` | `cnn_auxhead_paper.py` |
| `ltn_ctrl_w0{,_s43,_s44}.keras` | `ltn_paper.py` — no-axiom control, 3 seeds |
| `ltn_anat_w{0p5,1p0,2p0}.keras` | `ltn_paper.py` — ω-sweep, old axioms |
| `ltn_ax6_w{0p5,1p0}{,_s43,_s44}.keras` | `ltn_paper.py` — Ax6, fixed ω, 3 seeds |
| `ltn_ax6_ratio_w1p0_s{42,43,44}.keras` | `ltn_paper.py` — Ax6, **ratio** ω-mode, 3 seeds |
| `ltn_repro.keras`, `ltn_v2.keras` | `ltn_paper.py` — reproduction + v2 variants |

### Embeddings (`outputs/embeddings/`)

| File | Shape | Model |
|---|---|---|
| `X_{train,val,test}_cnn_paper_emb.npy` | (N, 64) | `cnn_paper.py` |
| `X_{train,test}_cnn_auxhead_l0.5_emb.npy` | (N, 64) | `cnn_auxhead_paper.py` |

> ⚠️ The aux-head has **no `X_val_` embedding** — only train and test were saved. Any downstream
> stage that needs a validation embedding (e.g. fitting a fusion combiner or clustering calibration)
> must use the `cnn_paper` embeddings, which do have all three.

### Predictions / fusion channels (`outputs/predictions/`)

Naming: `y_prob_<run-tag>_test.npy` (P(attack)) and `y_prob_<run-tag>_logodds_test.npy`
(log-odds re-score from `rescore_logits.py`).

| Channel | Source |
|---|---|
| `y_prob_cnn_paper_test.npy` | `cnn_paper.py` — the reference |
| `y_prob_{xgboost,random_forest,isolation_forest}_test.npy` | `baselines.py` |
| `y_prob_{msp,mahalanobis}_test.npy` | `novelty.py` |
| `y_prob_ltn_*_test.npy` | `ltn_paper.py` (one per run/seed) |
| `y_prob_fusion_{cnn_beaconlike,cnn_allbehaviours}_test.npy` | `fusion_beaconlike.py` |
| `y_prob_xgboost_oracle_test.npy` | `skyline_oracle.py` |
| `y_prob_smoke_*_test.npy` | ⚠️ **smoke-test debris** — undertrained, not results. Safe to delete. |

> **Prefer the `_logodds_` variant where it exists.** Plain `y_prob_*` scores can be float32-saturated
> (`ltn_ctrl_w0`: 99.25% of benign flows at exactly 0.0), which corrupts rank-based metrics. See
> [scripts_reference.md](scripts_reference.md#scriptsrescore_logitspy).

### Metadata (`outputs/metadata/`)

| File | Contents |
|---|---|
| `runs.jsonl` | One JSON line per run — the self-assembling ablation table (`tracking.py`) |
| `behaviour_thresholds.npy` | Fuzzy ramp percentile pairs (`behavior.py`) |
| `cnn_paper_history.pkl` | Per-epoch training history (`cnn_paper.py`) |

> ⚠️ `runs.jsonl` contains entries from **two metrics schemas**. Records written before the
> 2026-07-27 `metrics.py` rewrite carry only `zd_pr_auc` (the blended, size-weighted number);
> later records carry per-family PR-AUC + macro. `random_forest` is one of the old-schema entries and
> has no macro score. Check for the per-family keys before comparing rows.

---

## Legacy temporal-split artifacts

> ⚠️ **Everything below this line is from the superseded temporal split.** Shapes reference the
> temporal row counts (train 1,666,532 / test 1,161,344) and "9 classes / 4 zero-day", which do not
> describe the current protocol. Retained for provenance.

## Where everything lives

Artifacts are organised into subfolders (locations defined in [`scripts/paths.py`](../scripts/paths.py)). The per-category tables below list filenames; use this map for the folder each lands in:

| Folder | `paths.py` const | Contents |
|--------|------------------|----------|
| `data/processed/` | `PROCESSED` | `clean_*.csv`, `features_*.csv`, `labels_*.npy`, `constant_cols_dropped.npy` |
| `models/` | `MODELS` | `*.keras` models, `scaler*.pkl`, `label_encoder.pkl` |
| `outputs/arrays/` | `ARRAYS` | `X_test*.npy`, `y_train/val/test*.npy` (model-ready tensors & label splits) |
| `outputs/embeddings/` | `EMBEDDINGS` | `X_*_emb.npy` (CNN + LTN 64-dim embeddings) |
| `outputs/predictions/` | `PREDICTIONS` | `y_prob_*.npy` (softmax + P(attack) scores) |
| `outputs/metadata/` | `METADATA` | `class_names.npy`, `zero_day_classes.npy`, `history.pkl`, `behaviour_thresholds.npy` |
| `outputs/figures/` | `FIGURES` | `*.png` evaluation plots (the only outputs tracked by git) |

> All folders except `outputs/figures/` are git-ignored. They are created automatically when any script imports `paths`.

## CSV Data Files

| File | Rows | Columns | Produced By |
|------|------|---------|-------------|
| `clean_train.csv` | 1,666,532 | ~80 | `preprocess.py` |
| `clean_test.csv` | 1,161,344 | ~80 | `preprocess.py` |
| `features_train.csv` | 1,666,532 | 70 | `preprocess.py` |
| `features_test.csv` | 1,161,344 | 70 | `preprocess.py` |

`clean_*.csv` includes all columns plus labels. `features_*.csv` contains numeric features only (no labels, no identifiers).

---

## Label Arrays (.npy)

| File | Shape | Values | Produced By |
|------|-------|--------|-------------|
| `labels_train.npy` | (1,666,532,) | 0 / 1 | `preprocess.py` |
| `labels_test.npy` | (1,161,344,) | 0 / 1 | `preprocess.py` |
| `labels_train_binary.npy` | (1,666,532,) | 0 / 1 | `preprocess.py` |
| `labels_test_binary.npy` | (1,161,344,) | 0 / 1 | `preprocess.py` |
| `labels_train_multiclass.npy` | (1,666,532,) | str (9 class names) | `preprocess.py` |
| `labels_test_multiclass.npy` | (1,161,344,) | str (9 + 4 zero-day names) | `preprocess.py` |
| `class_names.npy` | (9,) | str | `cnn3.py` |
| `zero_day_classes.npy` | (4,) | str | `cnn3.py` |
| `constant_cols_dropped.npy` | (K,) | str (column names) | `preprocess.py` |

> `labels_train.npy` and `labels_train_binary.npy` are equivalent; both are binary (0/1). The two copies exist for clarity when loading in different scripts.

---

## Training Label Arrays (.npy)

These are produced by `cnn3.py` after encoding and splitting:

| File | Shape | Values | Notes |
|------|-------|--------|-------|
| `y_train.npy` | (N_train,) | 0–8 (int) | Multiclass, train split |
| `y_val.npy` | (N_val,) | 0–8 (int) | Multiclass, val split |
| `y_test.npy` | (N_test,) | 0–8 or −1 | −1 = zero-day (unseen class) |
| `y_test_bin.npy` | (N_test,) | 0 / 1 | Binary ground truth for test |

---

## Feature Arrays (.npy)

| File | Shape | Size | Produced By |
|------|-------|------|-------------|
| `X_test.npy` | (N_test, 70, 1) | ~603 MB | `cnn3.py` |

`X_test.npy` contains scaled test features reshaped for CNN inference.

---

## Embedding Arrays (.npy)

64-dimensional representations from the `Dense(64)` hidden layer.

| File | Shape | Size | Model |
|------|-------|------|-------|
| `X_train_emb.npy` | (N_train, 64) | ~326 MB | CNN (cnn3.py) |
| `X_val_emb.npy` | (N_val, 64) | ~82 MB | CNN (cnn3.py) |
| `X_test_emb.npy` | (N_test, 64) | ~284 MB | CNN (cnn3.py) |
| `X_train_ltn_emb.npy` | (N_train, 64) | ~326 MB | Hybrid-LTN (ltn.py) |
| `X_val_ltn_emb.npy` | (N_val, 64) | ~82 MB | Hybrid-LTN (ltn.py) |
| `X_test_ltn_emb.npy` | (N_test, 64) | ~284 MB | Hybrid-LTN (ltn.py) |

---

## Prediction Arrays (.npy)

| File | Shape | Values | Produced By |
|------|-------|--------|-------------|
| `y_prob_test.npy` | (N_test, n_classes) | [0, 1] softmax | `eval.py` |
| `y_prob_test_bin.npy` | (N_test,) | [0, 1] | `eval.py` — `1 − P(BENIGN)` |
| `y_prob_ltn_test.npy` | (N_test, n_classes) | [0, 1] softmax | `ltn.py` |
| `y_prob_ltn_bin.npy` | (N_test,) | [0, 1] | `ltn.py` — `1 − P(BENIGN)` |

---

## Behaviour Artifacts (.npy)

| File | Type | Location | Produced By |
|------|------|----------|-------------|
| `behaviour_thresholds.npy` | dict (object array) | `outputs/metadata/` | `behavior.py` (`save_thresholds()`) |

> **Correction (2026-07-29): the previous note on this row was wrong and is retracted.** It read
> *"NOT generated by any current script … if the file exists it is a stale leftover … `load_thresholds()`
> always falls back to hardcoded defaults."* That was accurate before the 2026-06-18 rebuild but has
> been false ever since. `behavior.py` now exposes `compute_thresholds()` / `save_thresholds()`, running
> `python scripts/behavior.py` regenerates the file, and it is **present** at
> `outputs/metadata/behaviour_thresholds.npy` (verified 2026-07-29).
>
> Keys are percentile pairs for the 7 fuzzy behaviours (not the old boolean-flag names) — see
> [behaviour_abstraction_current.md](implementation/behaviour_abstraction_current.md).

### LTN extra outputs (also produced by `ltn.py`)

| File | Description |
|------|-------------|
| `X_test_ltn.npy` | Scaled, reshaped test features from the LTN pipeline |
| `y_test_ltn_bin.npy` | Binary ground-truth labels (LTN copy) |
| `y_test_ltn_mc.npy` | Multiclass labels (−1 = zero-day, LTN copy) |

---

## Model Files (.keras)

| File | Size | Produced By | Notes |
|------|------|-------------|-------|
| `model_multiclass.keras` | ~1.3 MB | `cnn3.py` | Final epoch |
| `model_multiclass_best.keras` | ~1.3 MB | `cnn3.py` | Best val loss (EarlyStopping) |
| `model_focal.keras` | ~735 KB | ⚠️ unknown — **not produced by any current script** | Likely a stale experiment artifact |
| `ltn_model_best.keras` | ~1.3 MB | `ltn.py` | Best Hybrid-LTN checkpoint |
| `ltn_model_final.keras` | ~1.3 MB | `ltn.py` | Final epoch of LTN training |

---

## Preprocessing Artifacts (.pkl)

| File | Type | Size | Produced By |
|------|------|------|-------------|
| `scaler.pkl` | `sklearn.StandardScaler` | ~2.1 KB | `cnn3.py` |
| `scaler_ltn.pkl` | `sklearn.StandardScaler` | ~2.1 KB | `ltn.py` |
| `label_encoder.pkl` | `sklearn.LabelEncoder` | ~752 B | `cnn3.py` |

`scaler.pkl` is fit on training features only and used for all CNN pipeline predictions. `scaler_ltn.pkl` is the equivalent for the LTN pipeline.

---

## Training History (.pkl)

| File | Keys | Produced By |
|------|------|-------------|
| `history.pkl` | `loss, val_loss, accuracy, val_accuracy` | `cnn3.py` |
| `ltn_history.pkl` | `loss, val_loss, accuracy, val_accuracy, ce_loss, sat_loss, ax1_sat, ax2_sat, ax3_sat, ax4_sat` | `ltn.py` |

---

## Visualisation Files (.png)

| File | Contents | Produced By |
|------|----------|-------------|
| `cnn_zeroday_eval.png` | 6-subplot: train/val accuracy, train/val loss, PR curve, confusion matrix, zero-day family recall, score distribution | `eval.py` |
| `ltn_eval.png` | 9-subplot: same as above plus axiom satisfaction curves and LTN vs CNN comparison | `ltn.py` |

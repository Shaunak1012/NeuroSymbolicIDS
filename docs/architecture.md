# System Architecture

> ⚠️ **FROZEN (banner added 2026-07-29) — describes the legacy temporal-split pipeline.**
> This document was written before the 2026-06-18 protocol reset and describes
> `preprocess.py → cnn3.py → eval.py → ltn.py` on the **temporal split** (train Mon–Wed /
> test Thu–Fri) as the system. That pipeline is superseded: all current results come from the
> **paper-aligned split** (`preprocess_paper.py → cnn_paper.py → ltn_paper.py`).
> Known inaccuracies below: feature count is **68**, not 70; the "4 fuzzy logic axioms" referred to
> in the `ltn.py` box are the pre-fix label-tautology set (current code has 6, Ax1–Ax6, configurable);
> PortScan/DDoS are **known** classes under the current protocol, not zero-day; and the flow
> `cnn3 → eval → ltn` is not how any current result was produced.
> **Current state → [STATUS.md](STATUS.md).**

## Overview

NeuroSymbolic-IDS is a two-stage detection pipeline:

1. **Neural stage** — a 1D CNN trained on known attack families produces a 64-dim embedding and a softmax score per class.
2. **Symbolic stage** — hand-crafted behavioral rules derived from network traffic features are injected as axiom constraints during CNN training (Hybrid-LTN) to improve generalisation to unseen attacks.

## Data Flow

```
Raw CIC-IDS2017 CSVs (8 files)
           │
           ▼
    preprocess.py
    ├── Strip whitespace, remove inf/NaN
    ├── Drop identifier columns (IP, port, Flow ID, Timestamp)
    ├── Remove zero-variance features
    └── Align train/test column sets
           │
           ▼
features_train.csv / features_test.csv   (70 numeric features)
labels_train_binary.npy / labels_test_binary.npy
labels_train_multiclass.npy / labels_test_multiclass.npy
           │
           ▼
    cnn3.py
    ├── StandardScaler (fit on train only)
    ├── Reshape → (N, 70, 1)
    ├── Train 1D CNN with Focal Loss + class weights
    └── Extract 64-dim embeddings from Dense(64) layer
           │
      ┌────┴────┐
      ▼         ▼
model_*.keras   X_*_emb.npy
y_prob_test.npy (9-class softmax)
           │
           ▼
    eval.py
    ├── Binary zero-day detection metrics (PR-AUC, ROC-AUC)
    ├── Per-family recall on unseen attack types
    └── 6-subplot visualisation → cnn_zeroday_eval.png
           │
           ▼
    ltn.py  (Hybrid-LTN)
    ├── Retrain CNN with: Focal CE Loss + ω × SAT Loss
    ├── 4 fuzzy logic axioms constrain training
    ├── Adaptive ω weight based on axiom satisfaction
    └── 9-subplot evaluation → ltn_eval.png
           │
           ▼
ltn_model_best.keras
y_prob_ltn_bin.npy  ← improved zero-day detection
```

## Component Roles

| Component | Role |
|-----------|------|
| `preprocess.py` | Data cleaning, feature engineering, label creation |
| `cnn3.py` | Neural representation learning, embedding extraction |
| `eval.py` | Baseline evaluation (CNN only, no symbolic rules) |
| `behavior.py` | Symbolic flag extraction library |
| `ltn.py` | Neuro-symbolic fusion (Hybrid-LTN training) |
| `visual.py` | Preprocessing impact visualisation |
| `check.py` | Feature inspection utility |
| `scripts/paths.py` | Centralised filesystem paths (all scripts import it) |

## Why 1D CNN?

Each flow is represented as a 1D sequence of 70 numeric features. Conv1D filters learn local patterns across adjacent features (e.g., packet length statistics clustered together), treating feature order as a spatial signal. This is more parameter-efficient than a fully-connected approach while still capturing local correlations.

## Why Neuro-Symbolic Fusion?

A CNN trained on known attacks has no mechanism to detect attack types it has never seen. Symbolic rules encode domain knowledge ("high-rate + high-variance traffic is suspicious") that generalises beyond training classes. The Hybrid-LTN approach injects these rules as soft constraints during training rather than as post-hoc overrides, allowing the network to internalise the symbolic knowledge.

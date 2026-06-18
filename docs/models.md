# Models

> **Accuracy note:** This file describes intended design. For the line-by-line verified state of the source, see [implementation/cnn_current.md](implementation/cnn_current.md) and [implementation/ltn_current.md](implementation/ltn_current.md). The LTN as currently coded has a conceptual flaw (axioms are label tautologies) — see that audit.
>
> The CNN architecture diagram below shows Dropout after BatchNorm/MaxPool for brevity; in the source (`cnn3.py`) Conv blocks are `Conv→BN→MaxPool` and the two Dropout layers (0.4, 0.3) sit after the Dense(64) and Dense(32) layers respectively.

## 1. CNN (Multiclass Classifier)

### Architecture

```
Input: (N, 70, 1)
  │
  ├─ Conv1D(32, kernel=3, padding='same') + BatchNorm + ReLU + MaxPool(2) + Dropout(0.4)
  │
  ├─ Conv1D(64, kernel=3, padding='same') + BatchNorm + ReLU + MaxPool(2) + Dropout(0.4)
  │
  ├─ Conv1D(128, kernel=3, padding='same') + BatchNorm + ReLU + MaxPool(2) + Dropout(0.4)
  │
  ├─ Flatten
  │
  ├─ Dense(64, ReLU) + L2(1e-4) + Dropout(0.3)   ← EMBEDDING LAYER
  │
  ├─ Dense(32, ReLU) + L2(1e-4)
  │
  └─ Dense(n_classes, Softmax)                     ← n_classes ≈ 8 (computed from data)
```

**Total parameters**: ~200k–300k

### Training Configuration

| Hyperparameter | Value |
|----------------|-------|
| Optimizer | Adam (lr = 3e-4) |
| Loss | Focal Loss with class weights |
| Batch size | 256 |
| Max epochs | 50 |
| Early stopping patience | 8 epochs |
| LR reduce patience | 4 epochs (factor 0.5) |
| Regularisation | L2(1e-4), Dropout(0.4 / 0.3) |
| Train/val split | 80/20 stratified |

### Focal Loss

```
FL(p_t) = −α (1 − p_t)^γ log(p_t)
```

- `γ = 2` (focusing parameter) — down-weights easy examples
- `α` = inverse class frequency weights — corrects for class imbalance
- Applied per-class in the multiclass setting

### Label Strategy

The CNN is trained on the **classes present in Monday–Wednesday data** (~8, computed dynamically — not hardcoded). Test flows belonging to zero-day attack families (Web Attacks, Infiltration, Bot, PortScan, DDoS) receive label `−1` in the multiclass arrays and are **excluded from CNN training**. This means:

- Zero-day recall of ~5–15% from the CNN alone is expected and intentional
- The symbolic stage (LTN) is responsible for improving this

### Saved Files

| File | Description |
|------|-------------|
| `model_multiclass.keras` | Final model after all training epochs |
| `model_multiclass_best.keras` | Best checkpoint restored by EarlyStopping |
| `model_focal.keras` | Alternative binary variant (experimental) |
| `history.pkl` | Dict: `loss, val_loss, accuracy, val_accuracy` per epoch |

---

## 2. Hybrid-LTN Model

The Hybrid-LTN model uses the **same CNN architecture** but is trained with a combined loss that incorporates symbolic knowledge via fuzzy logic axioms.

### Hybrid Loss

```
L_hybrid = L_focal + ω × L_SAT
```

- `L_focal` — standard Focal Cross-Entropy on labelled training data
- `L_SAT` — axiom Satisfiability Loss (measures rule violations)
- `ω` — adaptive weight, starts at 0.1, adapts every epoch based on axiom satisfaction rate

**Adaptive ω rule:**
- If mean axiom satisfaction < 0.5 → increase ω (push harder on rules)
- If mean axiom satisfaction > 0.8 → decrease ω (rules are satisfied, relax)
- Clamped to range [0.3, 1.0]

### Fuzzy Logic Operators

Product t-norm logic:
- **AND**: `p ∧ q = p × q`
- **OR**: `p ∨ q = p + q − p × q`
- **NOT**: `¬p = 1 − p`
- **Implication**: `p → q = 1 − p + p × q`
- **Aggregation**: ApME (Approximate Mean Existential) over batch

### Knowledge Axioms

| Axiom | Statement | Fuzzy Form |
|-------|-----------|-----------|
| Ax1 | All benign flows → classified as BENIGN | `∀x: is_benign(x) → P_BENIGN(x) > 0.5` |
| Ax2 | All attack flows → NOT classified as BENIGN | `∀x: is_attack(x) → P_BENIGN(x) < 0.5` |
| Ax3 | All DoS flows → classified as attack | `∀x: is_dos(x) → (1 − P_BENIGN(x)) > 0.5` |
| Ax4 | All Patator flows → classified as attack | `∀x: is_patator(x) → (1 − P_BENIGN(x)) > 0.5` |

SAT Loss per axiom = `1 − mean_satisfaction`, averaged across axioms.

### Training Details

Unlike `cnn3.py` (which uses `model.fit()`), the LTN uses a **custom training loop** to compute SAT Loss at each step with full control over gradient flow.

### Saved Files

| File | Description |
|------|-------------|
| `ltn_model_best.keras` | Best Hybrid-LTN checkpoint |
| `ltn_model_final.keras` | Final model after all epochs |
| `scaler_ltn.pkl` | StandardScaler fitted for LTN pipeline |
| `ltn_history.pkl` | Dict: `loss, val_loss, accuracy, val_accuracy, ce_loss, sat_loss, ax1_sat … ax4_sat` |

---

## Embedding Layer

Both CNN and LTN models expose a 64-dim embedding from the `Dense(64, ReLU)` layer (second-to-last hidden layer). These embeddings are extracted post-training and saved as `.npy` arrays. Uses:
- Downstream visualisation (t-SNE / UMAP)
- Knowledge graph construction
- Clustering / anomaly detection on zero-day samples
- Feature input to secondary classifiers

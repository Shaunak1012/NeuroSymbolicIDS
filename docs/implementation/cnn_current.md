# CNN — Current Implementation (Verified)

**File:** `scripts/cnn3.py`  
**Verdict:** ✅ Correct and sound. Minor notes below, none blocking.

This documents the CNN **exactly as implemented**, after reading the source line-by-line.

## What it does

1. Loads `features_train.csv` / `features_test.csv` and the multiclass string labels.
2. Computes `train_classes = sorted(set(y_train_str))` **dynamically** from the data (not hardcoded).
3. Fits a `LabelEncoder` on train classes only. Test flows whose label is not in the train set are encoded as **−1** (zero-day marker).
4. Also builds binary labels (`!= 'BENIGN'`).
5. Stratified 80/20 train/val split (`random_state=42`).
6. `StandardScaler` fit on the **train split only**, applied to val and test. ✅ No leakage.
7. Reshapes to `(N, n_features, 1)` for Conv1D.
8. Computes balanced class weights; normalises them into focal-loss `alpha`.
9. Trains the CNN with categorical focal loss (γ=2.0), Adam(3e-4), 50 epochs, batch 256.
10. Callbacks: EarlyStopping(`val_accuracy`, patience 8, restore best), ReduceLROnPlateau(patience 3), ModelCheckpoint(best).
11. Saves model, scaler, encoder, test arrays, history, and 64-dim embeddings for train/val/test.

## Architecture (as coded)

```
Input(n_features, 1)
Conv1D(32,3,'same',relu) → BN → MaxPool(2)
Conv1D(64,3,'same',relu) → BN → MaxPool(2)
Conv1D(128,3,'same',relu) → BN → MaxPool(2)
Flatten
Dense(64, relu, L2=1e-4)  [name="embedding"]
Dropout(0.4)
Dense(32, relu, L2=1e-4)
Dropout(0.3)
Dense(n_classes, softmax)  [name="output"]
```

> Note: Dropout(0.4) is applied **after** the embedding Dense layer, not before. The embedding extracted for downstream use is the pre-dropout activation (dropout is inactive at inference anyway).

## Label strategy (verified correct)

| Set | Encoding |
|-----|----------|
| Train | 0 … n_classes−1 (known classes only) |
| Test, known class | its train index |
| Test, unseen class | −1 (zero-day) |

The CNN is trained only on classes present in Mon–Wed. This makes ~0% recall on zero-day families the **honest, intended baseline**. ✅ This is the correct framing for the research question.

## Focal loss (verified correct)

```
pt       = sum(y_pred * one_hot(y_true))
alpha_s  = alpha[y_true]
loss     = -alpha_s * (1 - pt)^gamma * log(pt)
```
Predictions are clipped to `[eps, 1-eps]` before `log`. Standard, correct implementation.

## Minor notes (not bugs)

1. **`class_weight` applied on top of focal `alpha`.** Both `class_weight=class_weight_dict` in `model.fit()` *and* the focal-loss `alpha` weight rare classes. This double-weights imbalance. Not wrong, but the effect compounds — worth being aware of when tuning. Consider using one or the other.
2. ~~Binary split is recomputed (`y_train_b`, `y_val_b`) but never used downstream.~~ **Removed 2026-06-18** — the redundant second `train_test_split` block is gone.
3. **`model_focal.keras`** (seen in the repo) is **not produced by this script** — provenance unknown; likely from an earlier experiment. See [known issues](../../docs/KNOWN_ISSUES.md).
4. **Embedding name dependency.** Downstream extraction relies on the layer being named `"embedding"`. Keep this name stable.

## Outputs (verified)

`model_multiclass.keras`, `model_multiclass_best.keras`, `scaler.pkl`, `label_encoder.pkl`, `class_names.npy`, `zero_day_classes.npy`, `labels_train_binary.npy`, `labels_test_binary.npy`, `X_test.npy`, `y_test.npy` (−1=zero-day), `y_test_bin.npy`, `y_train.npy`, `y_val.npy`, `history.pkl`, `X_train_emb.npy`, `X_val_emb.npy`, `X_test_emb.npy`.

## Conclusion

The CNN is implemented correctly for its stated purpose. The only judgement call is the double class-weighting (note 1). No changes required for the pipeline to be valid.

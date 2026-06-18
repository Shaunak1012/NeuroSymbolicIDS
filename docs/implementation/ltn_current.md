# LTN — Current Implementation

**File:** `scripts/ltn.py`
**Verdict:** ✅ Re-grounded on behaviours (2026-06-18). The core flaw (label-tautology axioms) is fixed. Full-training results pending the first complete run.

This documents `ltn.py` **as it stands after the re-grounding**. For the prior broken state, see [CHANGELOG](../CHANGELOG.md).

## What it does

Trains a CNN (same architecture as `cnn3.py`) from scratch with a **custom loop** using:

```
Hybrid Loss = Focal CE Loss + ω · SAT Loss
```

where ω is adaptive (starts 0.1, range 0.3–1.0). The model is then evaluated against the CNN baseline (PR-AUC, ROC-AUC, per-family zero-day recall).

## The fix — axioms are now behaviour-grounded

Previously all four SAT axioms were built from ground-truth labels (restating the supervised objective → no transfer to zero-day). Now:

| Axiom | Statement | Source | Transfers to |
|-------|-----------|--------|--------------|
| Ax1 | benign(label) → P(benign) high | label (supervised anchor) | — |
| Ax2 | attack(label) → ¬benign | label (supervised anchor) | — |
| **Ax3** | **LargePackets(x) ∧ HighEntropy(x) → ¬benign(x)** | **behaviour** | **DDoS** (zero-day) |
| **Ax4** | **BurstTraffic(x) → ¬benign(x)** | **behaviour** | **DoS/flood** |

- **Ax1/Ax2** remain label-based — they are legitimate *supervised consistency anchors*, not the whole story.
- **Ax3/Ax4** are grounded in fuzzy behaviour confidences from `behavior.py` (computed on the RAW training split, before scaling). Each flow's contribution to the axiom is weighted by its behaviour confidence `b(x) ∈ [0,1]`; the aggregator uses a soft (behaviour-weighted) mean with soft count `Σ b(x)`.

### Why this transfers to zero-day
Ax3/Ax4 constrain the model's output **wherever the behaviour holds**, regardless of label. A zero-day DDoS flow shares the LargePackets∧HighEntropy behaviour with training attacks, so the constraint shapes the decision boundary to push it toward ¬benign — something label-only axioms could never do.

### Why ScanProbe / HighVolume are NOT LTN axioms
`ScanProbe` is benign-heavy on the *training* distribution (short DNS-like flows), so asserting `ScanProbe → attack` during training would cause false positives. Its zero-day PortScan value is reserved for the **Knowledge Graph** stage (adaptive memory at inference), not the training axioms. `HighVolume` is only weakly discriminative (1.3×) and was left out to keep 4 axioms.

## Behaviour wiring (in `ltn.py`)

```python
import behavior
_beh_thr   = behavior.load_thresholds()                    # outputs/metadata/
_beh_train = behavior.abstract_behaviours(X_train, _beh_thr)   # RAW, pre-scaling
b_ax3 = _beh_train["LargePackets"] * _beh_train["HighEntropy"] # fuzzy AND
b_ax4 = _beh_train["BurstTraffic"]
```
These arrays are shuffled in lockstep with the batches and passed to `compute_sat_loss(softmax, y_str, b_ax3_batch, b_ax4_batch, ...)`.

## Smoke-test hook

```bash
LTN_SUBSET=50000 LTN_EPOCHS=2 python scripts/ltn.py   # fast end-to-end check
```
Verified: pipeline runs end-to-end, no NaNs, behaviour axioms compute and are satisfied (Ax3≈0.90, Ax4≈0.78 even at 2 epochs). Smoke metrics are not meaningful (undertrained).

## Remaining smaller issues (unchanged from prior audit)

1. `fuzzy_and` / `fuzzy_not` / `fuzzy_forall` are still defined but unused (the SAT aggregation is inlined). Cosmetic.
2. `history['accuracy']` is a fixed 5000-row proxy, not full-train accuracy.
3. Axiom weighting `(2·Ax1 + 2·Ax2 + Ax3 + Ax4)/6` is hand-set (no ablation yet).
4. Separate `scaler_ltn.pkl` from the CNN's scaler — keep in mind for fusion.

## Results

> ⏳ **Pending the first full training run** (in progress). Fill in PR-AUC / ROC-AUC / per-family zero-day recall vs the CNN baseline (0.6689 PR-AUC) when complete. Recorded in [STATUS.md](../STATUS.md#last-measured-results).

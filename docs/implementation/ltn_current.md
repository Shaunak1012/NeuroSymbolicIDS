# LTN — Legacy Implementation (`scripts/ltn.py`, temporal split)

> 🔴 **SUPERSEDED (updated 2026-07-29). This documents the legacy temporal-split LTN, which ran,
> underperformed, and was replaced.** It is retained as the historical record of the re-grounding
> fix. **The current symbolic pillar is [`scripts/ltn_paper.py`](../../scripts/ltn_paper.py)** —
> paper split, 6 configurable axioms (Ax1–Ax6), `ratio` omega-mode by default.
> **Current axioms and results → [STATUS.md](../STATUS.md).**

**File:** `scripts/ltn.py`
**Verdict:** 🔴 Superseded. The core flaw it fixed (label-tautology axioms) *was* genuinely fixed,
but the resulting model **underperformed the CNN baseline** on the full run and the whole protocol
was then reset.

**Result of the "pending" run (completed 2026-06-18):** PR-AUC **0.4529 vs the CNN's 0.6689**
(−0.22). Early-stopped ~epoch 10; validation accuracy declined after epoch 2. Per-family:
PortScan 0.36→0.16, DDoS 0.67→0.64. **Root cause:** focal CE collapsed to ~0.0005 while the SAT
term stayed O(0.1), so SAT dominated the gradient roughly **40:1**. The base paper avoided this by
using balanced data + plain CE + ω=1, which keeps SAT gentle relative to a much larger CE.
This diagnosis is what motivated `ratio` omega-mode (loss-ratio normalization) in `ltn_paper.py`.

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

## Results — ✅ complete (2026-06-18), not pending

> The "⏳ pending the first full training run" note that stood here until 2026-07-29 was stale by
> more than a year of project time. The run finished the same day this doc was written.

| Metric | CNN baseline (temporal) | Hybrid-LTN (`ltn.py`) | Δ |
|---|---:|---:|---:|
| Binary PR-AUC (zero-day) | 0.6689 | **0.4529** | **−0.216** |
| PortScan per-family | 0.36 | 0.16 | −0.20 |
| DDoS per-family | 0.67 | 0.64 | −0.03 |

Early-stopped ~epoch 10; val accuracy peaked at epoch 2 then declined — the signature of the SAT
term overwhelming a collapsed focal CE (~40:1). Post-hoc fusion investigation on these outputs:
**leaky** logistic fusion (fit on zero-day-labelled test half) reached 0.78, but the honest
**label-free** parameter-free fusion scored **−0.16** — behaviours carry real signal, unsupervised
transfer to zero-day was the wall. Both figures predate the paper split and the corrected
per-family/macro metric; they are not comparable to current numbers.

Superseded by the protocol reset. See [STATUS.md](../STATUS.md) for what replaced it.

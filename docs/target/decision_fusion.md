# Decision Fusion

> **Status: not yet built.** This document is the design spec.

Decision Fusion is the late-fusion stage that combines three calibrated signals into a single benign/malicious decision plus a confidence. It must itself be **interpretable** — a black-box fusion network would undermine the system's explainability goal.

## The Three Input Signals

| Signal | Symbol | Source | Range | High value means |
|--------|--------|--------|-------|------------------|
| CNN Confidence | `s_cnn` | 1D CNN | [0, 1] | `1 − P(BENIGN)` — learned attack likelihood |
| LTN SAT Score | `s_ltn` | LTN axioms | [0, 1] | Axiom-derived attack evidence (e.g., violation of "is benign" for this flow) |
| KG Consistency | `s_kg` | Knowledge Graph | [0, 1] | Flow aligns with attack-associated / emerging memory |

All three must be **calibrated to a common [0, 1] scale** where higher = more likely malicious, before fusion. Use the validation split to calibrate (e.g., Platt scaling / isotonic regression on each raw signal).

## Phase 1 (default): Fixed Interpretable Weighting

A transparent weighted score:

```
S_fused = w_cnn · s_cnn + w_ltn · s_ltn + w_kg · s_kg
alert   = (S_fused ≥ τ)
```

- Weights `w_cnn + w_ltn + w_kg = 1`, set by hand from validation behaviour. A reasonable starting point: `w_cnn = 0.5, w_ltn = 0.25, w_kg = 0.25` (trust the neural signal most initially, lean on symbolic signals for the zero-day tail).
- Threshold `τ` tuned on the validation PR curve to hit a target FPR.
- **Fully auditable:** every alert decomposes into the exact contribution of each signal.

### Why start here
- Zero training, no risk of overfitting the fusion stage.
- Directly defendable in a capstone review.
- Establishes the baseline the learned fuser must beat.

## Phase 2 (upgrade): Logistic-Regression Meta-Classifier

Train a logistic regression on the three signals (classic stacking):

```
S_fused = σ(β0 + β_cnn·s_cnn + β_ltn·s_ltn + β_kg·s_kg)
```

- Trained on a **held-out validation split** (never the CNN/LTN training data — avoids leakage).
- Still interpretable: the coefficients `β` show each signal's learned importance, and odds ratios are reportable.
- Typically improves over fixed weights when signals have non-obvious relative reliability.

A shallow neural fuser is explicitly **not recommended** — the marginal accuracy gain isn't worth losing interpretability.

## Special Handling: Zero-Day / Emerging Flows

When `s_cnn` is low (CNN has never seen the attack) but `s_kg` is high (KG flags an emerging pattern), the fused score should still raise an alert. The fixed-weight scheme handles this naturally as long as `w_kg` is non-trivial; the learned fuser should be trained on data that includes zero-day examples in the validation split so it learns to trust `s_kg` in this regime.

This is the crux of the whole system: **the KG and LTN signals carry the cases the CNN alone misses.**

## Outputs

For each flow, Decision Fusion emits:

| Output | Use |
|--------|-----|
| `alert ∈ {benign, malicious}` | The decision |
| `S_fused ∈ [0, 1]` | Confidence |
| `(contribution_cnn, contribution_ltn, contribution_kg)` | Fed into the [Final Alert explanation](explainability.md) |

## Evaluation Hooks

To prove the fusion adds value, log metrics for each ablation:

| Configuration | Purpose |
|---------------|---------|
| CNN only (`s_cnn`) | Baseline (already produced by `eval.py`) |
| CNN + LTN | Isolate the logic contribution |
| CNN + KG | Isolate the memory contribution |
| Full fusion | The complete system |

Report PR-AUC and per-family zero-day recall for each. See the [gap analysis](roadmap_gap_analysis.md#ablation-plan).

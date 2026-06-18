# Explainability & Final Alert

> **Status: not yet built.** This document is the design spec.

Every alert the system emits carries **three complementary explanations**, one from each pillar. This is what makes the system "Explainable" rather than just accurate.

## The Final Alert Object

```
FinalAlert {
    verdict:        "benign" | "malicious"
    confidence:     float          # S_fused from Decision Fusion
    fusion_breakdown: {            # which pillar drove the decision
        cnn: float, ltn: float, kg: float
    }
    explanations: {
        neural:  NeuralExplanation
        logic:   LogicExplanation
        kg:      KGExplanation
    }
}
```

## 1. Neural Explanation — Feature Attribution

*"Which input features pushed the CNN toward this verdict?"*

- **Method:** gradient-based attribution (Integrated Gradients or SHAP) over the 70 flow features for this flow's CNN prediction.
- **Output:** ranked list of top-k features with signed contributions, e.g.:
  ```
  Flow Bytes/s        +0.41
  Packet Length Std   +0.22
  SYN Flag Count      +0.18
  ...
  ```
- **Library:** `tf-keras-vis` / `captum`-style integrated gradients, or `shap.DeepExplainer`.

## 2. Logic Explanation — Violated Axioms & SAT

*"Which symbolic rules did this flow satisfy or violate?"*

- **Method:** evaluate each LTN axiom's satisfaction for this flow and report the per-axiom SAT score.
- **Output:** e.g.:
  ```
  Ax2 (attack ⇒ not benign):  SATISFIED   (sat 0.93)
  Ax3 (DoS ⇒ attack):         VIOLATED    (sat 0.12)  ← contributed to alert
  ```
- Violated axioms with low SAT are the logical "reasons" for the verdict.

## 3. KG Explanation — Reasoning Path

*"What in the system's memory supports this verdict?"*

- **Method:** extract the weighted traversal from the flow's cluster to attack-associated / emerging nodes (see [knowledge_graph.md](knowledge_graph.md#kg-explanation-reasoning-path)).
- **Output:** a readable path, e.g.:
  ```
  Flow#1284 → Cluster#7 → {BurstTraffic, ProtocolAnomalies} → EMERGING (w=0.81, rising)
  ```

## Agreement vs. Disagreement (a feature, not a bug)

The three explanations don't always agree. **Disagreement is itself diagnostic** and should be surfaced, not hidden:

| Pattern | Interpretation |
|---------|---------------|
| All three flag malicious | High-confidence known attack |
| CNN low, LTN low, **KG high** | Likely **zero-day** — memory sees an emerging pattern the CNN never learned |
| CNN high, KG low | Possible CNN overfit / distribution shift — worth analyst review |
| LTN violated, CNN benign | Rule-vs-data conflict — flag for rule refinement |

Presenting the agreement structure turns the explanation layer into a triage aid, not just a justification.

## Presentation

For each alert, render a compact card:

```
┌─ ALERT  Flow#1284 ─ MALICIOUS (conf 0.78) ──────────────┐
│ Fusion:  CNN 0.31 │ LTN 0.66 │ KG 0.81                   │
│                                                          │
│ Neural:  ↑ Flow Bytes/s, ↑ Packet Length Std            │
│ Logic:   Ax3 VIOLATED (DoS⇒attack, sat 0.12)            │
│ KG:      Cluster#7 → EMERGING pattern (rising)          │
│                                                          │
│ ⚠ CNN unsure but KG+LTN agree → suspected ZERO-DAY      │
└──────────────────────────────────────────────────────────┘
```

## Build Notes

- Feature attribution is the most compute-heavy explanation; compute it lazily (only for flagged flows), not for every benign flow.
- All three explanations should be serialisable (JSON) so alerts can be logged and audited.

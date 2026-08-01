# Target Architecture

**Explainable & Adaptive Neuro-Symbolic Intrusion Detection System (CIC-IDS2017)**

This document describes the *full intended* system — it is a **target**, so being ahead of the
implementation is by design. Two corrections as of **2026-07-29**:

> ⚠️ **1. The behaviour vocabulary in the diagram is not the implemented one.** The diagram lists
> `HighEntropy` / `BurstTraffic` / `RepeatedConnections` / **`ProtocolAnomalies`**. `ProtocolAnomalies`
> was **built, measured, and dropped** — in CIC-IDS2017 the TCP flag-count columns are ~0 even for
> real scans, and the flag-based behaviour fired on 45% of benign traffic vs 0% of attacks. It was
> replaced by `ScanProbe` (short duration × tiny payload), which scores 0.955 on PortScan.
> The implemented set is 7 behaviours — see
> [behaviour_abstraction_current.md](../implementation/behaviour_abstraction_current.md).
>
> ⚠️ **2. "LTN reasoning ✅ implemented" is true but should not be read as "working".** It is built
> and measured; the measurement is that **it does not improve zero-day detection** — every axiom
> variant tried costs macro PR-AUC versus a no-axiom control, across 3 seeds. The pipeline diagram
> below shows LTN feeding Decision Fusion as a value-adding signal; that is the *hypothesis*, and it
> is currently unsupported. See [STATUS.md](../STATUS.md).

For what is currently implemented, see the [implemented docs](../architecture.md) and the [gap analysis](roadmap_gap_analysis.md).
Phase numbering is canonical in [conference_roadmap.md §1b](conference_roadmap.md).

## Vision

A network intrusion detector that is **explainable** (every alert comes with neural, logical, and graph-based justifications) and **adaptive** (a decaying knowledge graph remembers emerging patterns and influences future decisions), built to detect both known attacks and zero-day attacks.

## Full Pipeline

```
Raw PCAP Ingestion
        │
        ▼
X_train / y_train ─────────────────────────────────────────────┐
        │                                                       │
        ▼                                                       │
Preprocessing                                                   │
  • Packet Extraction                                           │
  • Payload Normalization (1500 bytes)                          │
  • Timestamp Labelling                                         │
  • Strict Zero-Day Split                                       │
        │                                                       │
        ▼                                                       │
Training Path: 1D CNN                                           │
  • Class Probabilities                                         │
  • Latent Embeddings (64-dim)                                  │
        │                                                       │
        ▼                                                       │
LTN Reasoning                                                   │
  • Core Hard Axioms                                            │
  • SAT Loss                                                    │
        │                                                       │
        ▼                                                       │
KG Reasoning ◄──────────────┐                                  │
        │                   │                                  │
        ▼                   │ (async symbolic path)            │
Knowledge Graph             │                                  │
(Adaptive Memory)           │                                  │
  • Packets, Behaviours,    │                                  │
    Clusters                │                                  │
  • Weighted Edges & Decay  │                                  │
  • Emerging Patterns       │                                  │
        │                   │                                  │
        │            Behaviour Abstraction                     │
        │              • HighEntropy                           │
        │              • BurstTraffic                          │
        │              • RepeatedConnections                   │
        │              • ProtocolAnomalies                     │
        │                   ▲                                  │
        ▼                   │                                  │
Decision Fusion ◄───────────┘         X_test / y_test ─────────┘
  • CNN Confidence                            │
  • LTN SAT Score                             │
  • KG Consistency                            │
        │                                     │
        ▼                                     ▼
Final Alert ◄─────────────────────────────────
  • Benign / Malicious
  • Neural Explanation (Feature Attribution)
  • Logic Explanation (Violated Axioms & SAT)
  • KG Explanation (Reasoning Path)
```

> **Note on input modality:** The diagram shows raw PCAP ingestion and payload normalization. The current and near-term implementation uses **CIC-IDS2017 flow-feature CSVs** (70 numeric statistics per flow) as an abstraction over packet extraction. The PCAP boxes represent the conceptual origin of the data; payload-level processing is a possible future extension. See [behaviour_abstraction.md](behaviour_abstraction.md) for the consequences of this choice.

## Three Pillars of the System

### 1. Neural (CNN)
Learns class probabilities and a 64-dim latent embedding from flow features. Provides the primary discriminative signal and feature-attribution explanations. **Status: implemented.**

### 2. Symbolic — Logic (LTN)
Hard axioms encoded as fuzzy-logic constraints, optimised jointly with the CNN via SAT loss. Provides logical guarantees and violated-axiom explanations. **Status: implemented (soft axioms; "hard" framing TBD).**

### 3. Symbolic — Memory (Knowledge Graph)
An adaptive graph of flows, behaviours, and embedding clusters with weighted, time-decaying edges. Detects *emerging patterns* not tied to any known attack class — the zero-day mechanism. Provides reasoning-path explanations. **Status: not yet built.** See [knowledge_graph.md](knowledge_graph.md).

## Decision Fusion

A late-fusion stage combines three calibrated signals into a final benign/malicious decision:

| Signal | Source | Meaning |
|--------|--------|---------|
| CNN Confidence | 1D CNN | `1 − P(BENIGN)` — learned attack likelihood |
| LTN SAT Score | LTN axioms | Degree of axiom satisfaction/violation for this flow |
| KG Consistency | Knowledge Graph | Whether the flow aligns with attack-associated or emerging memory patterns |

See [decision_fusion.md](decision_fusion.md) for the scoring scheme.

## Explainability

Every alert carries three complementary explanations. They can agree (high confidence) or disagree (a signal in itself — often a sign of a novel attack). See [explainability.md](explainability.md).

## Adaptivity & the Asynchronous Symbolic Path

The KG updates on a different cadence than per-flow neural inference. A flow's decision uses the *current* KG state, while the KG ingests that flow's behaviours and embeddings to update its memory for *future* decisions. This decoupling (the "Asynchronous Symbolic Path" in the diagram) keeps inference fast while letting the memory evolve. Consequence: KG consistency for any single flow may reflect a slightly stale graph — this is intentional.

## Component Status Summary

| Component | Status |
|-----------|--------|
| Preprocessing (flow features) | ✅ Implemented |
| 1D CNN + embeddings | ✅ Implemented |
| LTN reasoning (SAT loss, 4 axioms) | ✅ Implemented |
| Behaviour abstraction | ⚠️ Partial (different vocabulary — see gap analysis) |
| Knowledge Graph (adaptive memory) | ❌ Not built |
| KG reasoning | ❌ Not built |
| Decision Fusion | ❌ Not built |
| Explainability (3 explanations) | ❌ Not built |
| Final Alert assembly | ❌ Not built |

See [roadmap_gap_analysis.md](roadmap_gap_analysis.md) for the build plan.

# Target Architecture Docs

These documents describe the **full intended system** — the *Explainable & Adaptive Neuro-Symbolic IDS* — not just what is implemented today. For the current implemented state, see the [parent docs folder](../).

| Doc | Contents |
|-----|----------|
| [target_architecture.md](target_architecture.md) | Full system overview, pipeline diagram, three pillars, component status |
| [behaviour_abstraction.md](behaviour_abstraction.md) | The four target behaviours, derivability from flow features, target API |
| [knowledge_graph.md](knowledge_graph.md) | KG design — NetworkX schema, weighted edges + decay, emerging-pattern detection |
| [decision_fusion.md](decision_fusion.md) | Combining CNN / LTN / KG signals; fixed-weight then learned fusion |
| [explainability.md](explainability.md) | Three explanations (neural / logic / KG) and the Final Alert |
| [roadmap_gap_analysis.md](roadmap_gap_analysis.md) | Built vs. planned, key gaps, build phases, ablation plan |
| [enhancements.md](enhancements.md) | Captured enhancement ideas (backlog — not scheduled) |

## TL;DR

- **Input:** CIC-IDS2017 flow-feature CSVs (PCAP boxes in the diagram are conceptual).
- **Built:** preprocessing, 1D CNN + embeddings, LTN/SAT reasoning, partial behaviour abstraction.
- **Not built:** Knowledge Graph (adaptive memory), Decision Fusion, Explainability/Final Alert.
- **Recommended choices:** KG → NetworkX; Fusion → fixed interpretable weights first, logistic meta-classifier as upgrade.
- **Top gaps:** `RepeatedConnections` needs IP/port (currently dropped); `HighEntropy` only approximable from flow features; "hard" vs soft axioms to reconcile.

Start with [roadmap_gap_analysis.md](roadmap_gap_analysis.md) for the build plan.

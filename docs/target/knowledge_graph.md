# Knowledge Graph (Adaptive Memory)

> **Status: not yet built.** This document is the design spec.

The Knowledge Graph (KG) is the system's *adaptive memory*. It accumulates associations between observed flows, their abstracted behaviours, and clusters of CNN embeddings. Edges carry weights that **decay over time**, so stale associations fade and recently-reinforced ones dominate. The KG's primary job is to surface **emerging patterns** — recurring structures not tied to any known attack class — which is the system's zero-day signal.

## Recommended Implementation: NetworkX

**Why NetworkX:**
- Pure Python — drops straight into the existing numpy / scikit-learn / Keras stack with no extra infrastructure.
- Node and edge **attributes** store weights and `last_updated` timestamps natively.
- Built-in algorithms for the hard parts: community detection (Louvain via `python-louvain`), connected components, shortest paths (for KG explanation reasoning paths), and subgraph extraction.
- Easy to serialise (`pickle` / GraphML) for checkpointing the adaptive memory between runs.

**Migration path:** if graph size or persistence becomes a bottleneck, the same schema maps cleanly onto Neo4j (nodes → labelled nodes, edges → typed relationships, weights/timestamps → properties). Start with NetworkX.

## Graph Schema

### Node Types

| Node type | Represents | Lifetime |
|-----------|-----------|----------|
| `Flow` | An individual flow (or a sampled representative) | Ephemeral — decays fast, pruned when weight → 0 |
| `Behaviour` | An abstracted behaviour symbol (HighEntropy, BurstTraffic, …) | Persistent |
| `Cluster` | A cluster of CNN 64-dim embeddings (KMeans/DBSCAN over `X_*_emb.npy`) | Semi-persistent |
| `AttackType` | A known attack family + a special `EMERGING` placeholder | Persistent |

### Edge Types

| Edge | From → To | Weight semantics |
|------|-----------|------------------|
| `exhibits` | Flow → Behaviour | Strength/confidence the flow shows this behaviour |
| `belongs_to` | Flow → Cluster | `1 / (1 + dist_to_centroid)` |
| `characterized_by` | Cluster → Behaviour | Fraction of cluster's flows exhibiting the behaviour |
| `associated_with` | Cluster → AttackType | Fraction of cluster's labelled flows of that type |
| `co_occurs` | Behaviour ↔ Behaviour | Co-occurrence frequency across flows |

## Weighted Edges & Temporal Decay

Each edge stores `(weight, last_updated)`. On every update at time `t`:

```
Δt          = t − last_updated
w_decayed   = w * exp(−λ · Δt)        # forget the past
w_new       = w_decayed + reinforcement   # reinforce on observation
last_updated = t
```

- `λ` (decay rate) is a hyperparameter — larger λ = faster forgetting (more adaptive, noisier).
- `reinforcement` is typically the observation strength (e.g., behaviour confidence, or 1.0 for a hard observation).
- Edges whose weight falls below a prune threshold `ε` are removed; isolated `Flow` nodes are garbage-collected.

This gives the "Weighted Edges & Decay" property from the diagram: the graph is a **rolling, self-forgetting memory** rather than an ever-growing log.

## Emerging Pattern Detection

This is the core zero-day mechanism. An *emerging pattern* is a subgraph that is **growing in weight** but **not yet explained by a known attack type**.

Detection procedure (run periodically on the async symbolic path):

1. **Track growth.** Maintain a short history of each edge's weight; compute the growth rate (positive derivative over recent windows).
2. **Community detection.** Run Louvain on the `Cluster`–`Behaviour` subgraph to find tightly-knit groups.
3. **Flag candidates.** A community is an *emerging pattern* if it:
   - has **rising aggregate weight** (reinforced recently), AND
   - has **weak or no `associated_with` edges to known `AttackType` nodes** (unexplained), AND
   - co-occurs with behaviours considered suspicious (e.g., BurstTraffic + ProtocolAnomalies).
4. **Promote.** Link the community to the `EMERGING` AttackType node and raise its KG-consistency contribution. If later labelled, it can be promoted to a named AttackType.

## KG Consistency Score (used by Decision Fusion)

At inference, for a flow `x`:

1. Extract its behaviours and nearest `Cluster`.
2. Walk the KG from that cluster: aggregate the (decayed) weights of edges leading to attack-associated or `EMERGING` nodes vs. benign-associated nodes.
3. Normalise to a scalar `kg_consistency(x) ∈ [0, 1]`, where high = "the memory supports this being malicious / part of an emerging pattern."

This scalar is one of the three inputs to [Decision Fusion](decision_fusion.md).

## KG Explanation (Reasoning Path)

For the [Final Alert](explainability.md), the KG produces a human-readable path, e.g.:

```
Flow#1284 → belongs_to → Cluster#7
Cluster#7 → characterized_by → {BurstTraffic, ProtocolAnomalies}
Cluster#7 → associated_with → EMERGING (weight 0.81, rising)
⇒ Flagged as emerging/zero-day pattern.
```

Use `networkx.shortest_path` / weighted traversal to extract and render this path.

## Open Design Questions

- **Flow node granularity:** one node per flow is expensive at 1.1M test flows. Consider sampling, or only materialising flows that are anomalous / near cluster boundaries.
- **Decay schedule:** wall-clock time vs. logical time (flow count). Flow-count "time" is more reproducible for offline CIC-IDS2017 experiments.
- **Cluster maintenance:** static clusters (fit once on training embeddings) vs. incremental clustering as new embeddings arrive. Static is simpler for a first version.
- **`RepeatedConnections` dependency:** requires source/dest IPs, which current preprocessing drops. See [behaviour_abstraction.md](behaviour_abstraction.md) and the [gap analysis](roadmap_gap_analysis.md).

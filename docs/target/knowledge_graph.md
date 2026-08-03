# Knowledge Graph (Adaptive Memory)

> **Status: not yet built.** This document is the design spec. **Canonical Phase 4**
> (not "Phase 3" — see [conference_roadmap.md §1b](conference_roadmap.md)).

---

## 🚨 READ FIRST — MEASURED 2026-08-03. Two of this spec's decisions are now settled by data.

`scripts/kg_readiness.py` → `outputs/metadata/kg_readiness.json`. Predictions pre-registered.

### 🔴 1. The "unexplained cluster" mechanism DOES NOT WORK. Do not build it.

This spec flags an emerging pattern partly by **weak or no `associated_with` edges to a known
AttackType**. Measured honestly — cluster is "unexplained" if its **training** flows contain < τ
known-attack fraction (train labels only, which the KG legitimately has), scored against test:

| representation | τ=0.01 | τ=0.05 | τ=0.10 |
|---|---:|---:|---:|
| CNN embedding 64-d | 0.55× | 0.54× | 1.00× |
| AE bottleneck 16-d | 0.28× | 0.44× | 0.43× |
| Raw features 68-d | 0.93× | 0.90× | 0.90× |

*(lift over the base rate 0.0704; **> 1.0 = better than random**)*

**Best result anywhere: 1.00×, exactly chance. Everything else is below it** — a flow in an
"unexplained" cluster is *less* likely to be zero-day than a random flow. **118 of 200 clusters
contain zero known-attack training flows**, because benign traffic is diverse and is half the
training set, so the criterion flags ~59,000 of ~59,400 benign+zero-day test flows. Not a tuning
problem: lift ≤ 1.0 across 3 representations × 3 thresholds.

**Consequences:**
- ✅ **Contradiction #1 below is RESOLVED — empirically, in the roadmap's favour.** The KG is
  **corroboration + explainability, not a primary detector.** That is now a measurement.
- ⬜ **The other two emerging-pattern criteria are still untested** — **cluster growth rate** and
  **behaviour co-occurrence**. Any detection role must come from those, and they must be measured
  the same way *before* being built on.

### ✅ 2. Cluster on RAW FEATURES, not embeddings

| representation | Bot purity across seeds (k=200) | spread |
|---|---|---:|
| CNN embedding 64-d | 87.9 / 86.6 / **44.4** % | 43.4 pp |
| AE bottleneck 16-d | 82.0 / 74.1 / **29.9** % | **52.1 pp** |
| **Raw features 68-d** | **77.6 %** (80.6 % at k=400) | **no training lottery** |

Raw features are competitive with the CNN's *good* seeds, far above its worst, and carry no
training-seed lottery (residual k-means seed sensitivity ~2.6 pp).

> ⚠️ **The AE bottleneck was the recommended option until this was measured, and the reasoning was
> wrong.** It was chosen because the AE ranks Bot *reproducibly* (cross-seed ρ = 0.827 vs the CNN's
> −0.090). **Rank stability ≠ cluster stability**: the AE orders Bot flows consistently by
> reconstruction error, but its 16-d geometry still scatters them across seeds — measured spread
> 52.1 pp, the worst of all three.

### 🧩 3. Behaviour columns need care as `exhibits` edge weights

Use `behavior.active_behaviour_matrix()` / `active_behaviour_names()`, not the raw 7-column matrix:
- **`RepeatedConnections` is constant 0.0** — a dead edge type, and a divide-by-zero risk in any
  co-occurrence statistic. `active_*` drops it automatically.
- **`BeaconLike` is binary (0.0/1.0)**, not graded — bimodal as an edge weight. Check
  `behavior.BEHAVIOUR_KIND` before assuming a column is continuous.

---

## ⚠️ Phase-4 readiness review (2026-07-29) — items 2 and 3 still stand

> **Item 1 below is superseded by the measurement above** (same conclusion, now with evidence
> rather than argument). Kept in place per the retract-in-place convention.

This spec was written **before the protocol reset** and three of its assumptions no longer hold.
Resolve these before writing code; none is fatal, but each changes what gets built.

### 1. 🔴 Scope contradiction: is the KG a detector or not?

This document says the KG's *"primary job … is the system's zero-day signal."*
[conference_roadmap.md](conference_roadmap.md) Phase 4 says the opposite —
*"corroboration + reasoning paths (**not primary detector**)."*
**The roadmap is canonical and the more defensible position**, because the fusion path a "primary
detector" would need has already been measured to fail (see
[decision_fusion.md](decision_fusion.md#special-handling-zero-day--emerging-flows): a non-leaky
combiner cannot discover the value of a zero-day-specific signal; `fusion_beaconlike.py` returned
coefficients `[2.35, 0.02]` and zero macro change). **Build the KG for corroboration + explanation,
and evaluate it on its own terms** — not by whether it moves PR-AUC through a fitted fuser.

### 2. ⚠️ The zero-day target changed shape completely

The "emerging pattern" mechanism was designed when zero-day meant **PortScan (158,804 flows) +
DDoS (128,025)** — huge, dense, structurally distinctive families under the temporal split.
Under the paper split **both are known, trained-on classes.** Zero-day is now **4,183 flows total**
(1.7% of test) across 6 families, only **3 adequately powered**: Bot (1,956), Web Attack Brute Force
(1,507), Web Attack XSS (652). "Detect the large emerging cluster" is a materially harder problem
than the one this spec was written for.

### 3. ⚠️ "Temporal decay" has no clean time axis under this split

The paper split is a **stratified random 80/10/10 across all 5 capture days** — there is no time
arrow between train and test. The decay model (`w·exp(−λ·Δt)`) and the "rolling, self-forgetting
memory" framing assume one. Timestamps *do* exist (`meta_*.csv`), so ordering within a split is
possible, but train/val/test are interleaved in wall-clock time. **Pick one before building:**
(a) decay over flow-count in timestamp-sorted order *within test*; (b) drop decay for v1 and build a
static graph; (c) evaluate the adaptive/decay story on the **temporal** split as a secondary result,
where the time arrow is genuine. Note that "Adaptive" is in the project title — option (b) has a
write-up cost.

### 4. 🔴 Empirical pre-check — RETRACTED 2026-08-02, the substrate is CNN-seed-dependent

> **The "viable, better than expected" conclusion below is retracted.** It varied only the
> **clustering** seed on a **fixed seed-42 embedding**. Varying the **CNN seed** — the representation
> the KG is actually built on — gives Bot cluster purity **87.9% / 86.6% / 44.4%** at k=200
> (**43.4 pp spread**), versus 2.6 pp when only the clustering seed moves.
> **The instability is specific to Bot**: Web BF and XSS move only 0.7–2.5 pp. Seed 44 is
> independently confirmed bad — Mahalanobis Bot 0.0413 (1.2×, chance) on the same embedding — while
> its classification is unremarkable (macro 0.6396).
> **Decide the representation before writing `kg.py`** (ensemble across seeds · raw features ·
> the AE's benign-trained 16-d bottleneck · accept-and-publish the variance).
> Full analysis: [STATUS.md](../STATUS.md) → "PHASE-4 BLOCKER".

### ~~4. ✅ Empirical pre-check: the clustering substrate is viable — better than expected~~

Ran before committing to the phase: MiniBatchKMeans on 200k `cnn_paper` train embeddings, applied to
test, sweeping k ∈ {50,100,200,400,800} × 2 seeds. Measures, for each powered zero-day family, its
single best cluster — **purity** (what fraction of that cluster is the family) and **recall** (what
fraction of the family that one cluster captures).

| k | Bot | Web Attack BF | Web Attack XSS |
|---:|---|---|---|
| 50 | p=23–25% r=44–50% | p=38–62% r=75–89% | p=17–28% r=75–91% |
| 100 | p=75–81% r=34% | p=52–53% r=89% | p=24% r=92–93% |
| **200** | **p=88–91% r=34%** | p=62–66% r=90% | p=28–30% r=94% |
| 400 | p=82–90% r=34% | p=63–65% r=90% | p=28–29% r=94% |
| 800 | p=91–92% r=25–32% | p=66–67% r=90% | p=30% r=94% |

**Bot — the family that defeated every Phase-2 intervention — forms a ~90%-pure cluster at k≥200,
stable across both seeds.** Web BF reaches ~65% purity at 90% recall. XSS stays impure (~30%),
consistent with it sharing a region with Web BF.

**What this does and does not license:**
- ✅ `Cluster` nodes are a *meaningful* object here. There is real, seed-stable structure to hang a
  graph on. This was not obvious — it is the same 64-dim space in which Bot scores at chance (1.7×).
- ⚠️ **Recall caps at ~34% for Bot.** One cluster holds a third of Bot. The KG's realistic
  contribution is **precision-oriented** (high-confidence flagging of a subset), not recall.
- 🔴 **Purity here is measured with test labels — an oracle view, and therefore an upper bound.**
  A real KG must decide "this cluster is unexplained/emerging" from *unlabelled* structure. At k=50,
  **25 of 50 clusters were already >90% benign in training**, and 100% of Bot/Web-BF/Heartbleed/
  Infiltration flows landed in benign-dominated clusters. So the spec's criterion
  *"weak or no `associated_with` edges to known AttackType"* will flag these clusters — **but it will
  also flag a large number of ordinary benign clusters.** The **false-positive rate of "unexplained
  cluster" is the untested quantity**, and it is the thing that decides whether this works.
- **Therefore the discriminative work must come from criteria #1 (growth) and #3 (suspicious
  behaviour co-occurrence) in the detection procedure below — not from #2 (unexplained) alone.**
  Design the emerging-pattern rule accordingly, and measure its FPR first.

> **Provenance/caveats:** MiniBatchKMeans (not the KMeans/DBSCAN this spec suggests), 200k train
> subsample, 2 seeds, k not tuned by any criterion. **n=2 seeds — provisional, not confirmed.**
> Purity/recall are geometric measures, *not* detection metrics. Reproduce and extend before citing.

### 5. Minor, but will bite

- **`RepeatedConnections` is constant 0.0** and is column 6 of `behaviour_matrix`. It will create a
  `Behaviour` node with no meaningful edges. Filter it, or wire it up first — the IP/port side-tables
  now exist (`meta_*.csv`), so it is unblocked, just unwired.
- **`BeaconLike` is binary (0.0/1.0), not graded.** As an `exhibits` edge weight it produces a
  bimodal distribution, not a spread. Any weight-thresholding logic must account for that.
- **Use the `cnn_paper` embeddings, not the aux-head ones** — the aux-head has **no `X_val_`
  embedding** saved, and it underperformed the plain CNN (0.5744 vs 0.6446) anyway.
- **Scale is no longer a concern.** The spec worries about 1.1M flow nodes; the paper-split test set
  is **114,658** flows. Materialising every test flow as a node is tractable.

---

The Knowledge Graph (KG) is the system's *adaptive memory*. It accumulates associations between observed flows, their abstracted behaviours, and clusters of CNN embeddings. Edges carry weights that **decay over time**, so stale associations fade and recently-reinforced ones dominate. The KG's ~~primary~~ job is to surface **emerging patterns** — recurring structures not tied to any known attack class — which is ~~the system's zero-day signal~~ *a corroboration and explanation signal; see the scope note above*.

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

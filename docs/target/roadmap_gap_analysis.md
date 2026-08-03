# Roadmap & Gap Analysis

> ⚠️ **PARTIALLY SUPERSEDED (banner added 2026-07-29).**
>
> **The "Phase A–E" scheme below is retired.** It is one of three competing phase numberings that
> were in circulation; the **canonical scheme is Phase 0–7 + R** in
> [conference_roadmap.md §1b](conference_roadmap.md), which carries the full mapping table. Roughly:
> A→Phases 1–2, B→Phase 4 (KG), C→Phase 5 (fusion), D→Phase 4 (explainability), E→Phases 5+7.
> **Do not cite "Phase B" — say "Phase 4 (KG)".**
>
> **The "Built vs. Planned" table below is also out of date.** `behaviour abstraction` is no longer
> "⚠️ Partial" (rebuilt and validated 2026-06-18, 7 fuzzy behaviours); `LTN reasoning ✅ Built` is
> true but misleading — it was built, measured, and **found not to help** (every axiom variant costs
> macro PR-AUC). Gap #2 (`RepeatedConnections` needs IP/port) is **resolved at the data level** —
> the meta side-tables exist. **Current component status → [STATUS.md](../STATUS.md).**
>
> The **Ablation Plan** and **Risks** sections at the end remain useful and are not superseded.

What is built today vs. the [target architecture](target_architecture.md), and the plan to close the gap.

## Built vs. Planned

> 🔑 **This table was REMOVED on 2026-08-03 — deliberately, not lost.**
>
> **Component status now lives in exactly one place:
> [docs/STATUS.md](../STATUS.md) → "Component Status".**
>
> A parallel table here was one of four independent copies, and that duplication caused the same
> drift error in three consecutive sessions (this copy still said `behaviour abstraction ⚠️ Partial`
> and `LTN reasoning ✅ Built` long after both had changed, and described preprocessing as dropping
> IP/port, which stopped being true at the 2026-06-18 dataset upgrade). Restating status here is
> what kept rotting — so it is a pointer now.
>
> Phase **numbering** (a different thing) stays canonical in
> [conference_roadmap.md §1b](conference_roadmap.md).

## Key Gaps to Resolve (in priority order)

### 1. "Hard" vs. soft axioms
The diagram says *Core Hard Axioms*; `ltn.py` implements *soft* axioms via adaptive-ω SAT loss. Decide:
- Keep soft (current) and rename in the diagram, **or**
- Add genuinely hard constraints (e.g., post-inference overrides for axioms that must never be violated).
*Recommendation: keep soft for training, optionally add a thin hard-rule guard at inference for safety-critical axioms.*

### 2. `RepeatedConnections` needs IP/port (currently dropped)
`preprocess.py` removes Flow ID, IPs, and Timestamp as identifiers. `RepeatedConnections` (PortScan/Bot/brute-force signal) can't be computed without endpoint info.
- **Fix:** persist IP/port/timestamp to a side table (e.g., `meta_train.csv` / `meta_test.csv`) keyed to row index, without feeding them into the CNN. The KG and behaviour abstraction consume the side table.

### 3. `HighEntropy` is only approximate with flow features
True payload entropy needs packet bytes. Document the approximation (packet-length variance/spread) honestly, or scope `HighEntropy` out of v1.

### 4. Behaviour vocabulary mismatch
Refactor `behavior.py` to emit the four target behaviours as fuzzy [0,1] confidences (see [behaviour_abstraction.md](behaviour_abstraction.md#recommended-target-api)).

## Suggested Build Phases

### Phase A — Symbolic vocabulary & metadata
- Refactor `behavior.py` → fuzzy target behaviours.
- Add IP/port/timestamp side table in `preprocess.py` (unblocks `RepeatedConnections`).
- *Deliverable:* per-flow behaviour confidences for train/test.

### Phase B — Knowledge Graph (NetworkX)
- Cluster CNN embeddings (`X_*_emb.npy`) → `Cluster` nodes.
- Build graph schema; implement weighted edges + temporal decay.
- Implement emerging-pattern detection (growth tracking + Louvain).
- Implement `kg_consistency(x)` score + reasoning-path extraction.
- *Deliverable:* `kg.py` producing a per-flow KG consistency score + serialisable graph.

### Phase C — Decision Fusion
- Calibrate `s_cnn`, `s_ltn`, `s_kg` to common [0,1] on validation.
- Implement Phase-1 fixed-weight fusion; tune `τ`.
- *Deliverable:* `fusion.py` emitting verdict + confidence + breakdown.

### Phase D — Explainability & Final Alert
- Integrated-gradients/SHAP attribution (lazy, flagged flows only).
- Per-axiom SAT reporting.
- KG reasoning-path renderer.
- Assemble `FinalAlert` object + alert card.
- *Deliverable:* `explain.py` + end-to-end alert demo.

### Phase E — Evaluation & polish
- Run the full ablation (below).
- Phase-2 logistic meta-fuser if it beats fixed weights.
- Write up results.

## Ablation Plan

Prove each component earns its place. Report **PR-AUC** and **per-family zero-day recall** for each row:

| Configuration | What it isolates |
|---------------|------------------|
| CNN only | Baseline (from `eval.py`) |
| CNN + LTN | Logic contribution |
| CNN + KG | Memory contribution |
| CNN + LTN + KG (full fusion) | Complete system |

Expected story: full fusion should lift zero-day recall well above the CNN's ~5–15% baseline, with KG carrying most of the zero-day gain and LTN tightening known-class consistency.

## Risks

| Risk | Mitigation |
|------|-----------|
| KG emerging-pattern detection is hand-wavy under scrutiny | Pin down concrete metrics (weight growth rate, Louvain communities) now — done in spec. |
| 1.1M flow nodes blow up the graph | Sample / only materialise anomalous flows; use Cluster nodes as the main carriers. |
| Fusion overfits if trained on CNN's training data | Train meta-fuser only on a held-out split incl. zero-day examples. |
| `HighEntropy`/`RepeatedConnections` unsupported by data | Resolve in Phase A; scope out of v1 if needed. |

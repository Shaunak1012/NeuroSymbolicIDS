# Project Status (Living Document)

> **Update this file at the end of every working session.** It is the single source of truth for "where are we right now." Last updated: **2026-06-18**.

## ▶ RESUME HERE (next session)

**Major pivot decided (2026-06-18).** LTN full run finished and **underperformed** the baseline
(PR-AUC 0.45 vs CNN 0.67). Root cause diagnosed: focal CE collapsed to ~0.0005 so the SAT term
dominated ~40:1 (base paper used *balanced data + plain CE + ω=1*, keeping SAT gentle). We then
read the base paper (`basepaper.pdf`) and found our split is a *much harder, misaligned* protocol.
**Decision: protocol reset + rebuild per plan v1.2.** Full plan + conference agenda in
**[conference_roadmap.md](target/conference_roadmap.md)** — read that first.

**✅ Phase 0 DONE (2026-06-18).** Paper-aligned split built (`scripts/preprocess_paper.py` → `data/processed/paper/`): 9 known classes (BENIGN + 8 attacks incl. PortScan/DDoS) stratified 80/10/10 = train 883,796 / val 110,475 / test 114,658, balanced 50/50, 6 zero-day (Bot, Web×3, Infiltration, Heartbleed) in test only, leakage-verified. `config.yaml` + `scripts/config.py`/`features.py`/`tracking.py` scaffolding in place. **log1p A/B: signed-log1p wins (0.980 vs 0.965 PR-AUC) → adopted.** IP/timestamp side-table **not possible** (MachineLearningCVE variant has no IP/timestamp cols — documented). Corrected labels (Engelen): deferred, current labels first.

**⚠️ Key nuance:** on the paper split, overall binary PR-AUC is ~0.97 (PortScan/DDoS are now *known*). The **real challenge metric is binary on the zero-day-only subset** (Bot/Web/Infiltration/Heartbleed, ~4,183 test flows) — matching the paper's "6 unknown classes" metric. Track that separately everywhere.

**▶ Next action = Phase 1 (neural pillar + baselines):**
1. Retrain CNN in our venv on the paper split (fixes Keras-3 load issue; produces loadable models).
2. Add post-hoc novelty scores: Mahalanobis on embeddings + energy/max-logit.
3. Add classical baselines: XGBoost, Random Forest, Isolation Forest.
See [conference_roadmap.md](target/conference_roadmap.md) Phase 1.

**Key measured findings to carry forward:**
- Leaky fusion (fit on zero-day labels) hit 0.78 (+0.11) — behaviours carry real signal, but
  label-free fusion (parameter-free) was −0.16. The signal is real; unsupervised transfer is the wall.
- `model_multiclass_best.keras` was saved in **Keras 3** → won't load in our Keras-2.15 venv.
  Retrain in-venv is required anyway (Phase 1).

**Compute:** **CPU** (Ryzen 9 9950X3D). GPU (RTX 5080 / Blackwell) deferred. For long runs use
`python -u` so progress is live and completion is caught reliably (last run's notification was missed).

## Environment

✅ **Ready.** `.venv/` at repo root — Python 3.11.9, TF 2.15.1 (Keras 2), numpy 1.26.4, + networkx / python-louvain / shap. CPU mode (no GPU). Pinned in `requirements.txt`. Use `.venv\Scripts\python.exe`. See [CLAUDE.md](../CLAUDE.md#environment--venv).

## Repository layout

✅ **Reorganised (2026-06-18).** Artifacts no longer dump to repo root — they live under `data/processed/`, `models/`, and `outputs/{arrays,embeddings,predictions,metadata,figures}/`. All paths are centralised in [`scripts/paths.py`](../scripts/paths.py); every script imports it. Verified: all scripts compile, all 28 existing artifacts present at new locations. Layout documented in [README](../README.md#project-structure) and [artifacts.md](artifacts.md#where-everything-lives).

## Component Status

| Component | Status | File | Notes |
|-----------|--------|------|-------|
| Preprocessing | ✅ Working | `scripts/preprocess.py` | Flow features, binary + multiclass labels. Drops IPs/ports. |
| CNN (multiclass) | ✅ Verified correct | `scripts/cnn3.py` | See [cnn_current.md](implementation/cnn_current.md). Minor: double class-weighting. |
| CNN evaluation | ✅ Working | `scripts/eval.py` | Produces PR-AUC baseline + `cnn_zeroday_eval.png`. |
| Behaviour abstraction | ✅ Rebuilt & validated | `scripts/behavior.py` | Verified indices, vectorised, fuzzy [0,1], thresholds saved. PortScan/DDoS strongly covered. Not yet wired into LTN. See [doc](implementation/behaviour_abstraction_current.md). |
| LTN reasoning | 🔴 Ran, underperformed (0.45 vs 0.67) | `scripts/ltn.py` | Behaviour-grounded, but SAT dominated CE ~40:1. Becomes the **"failure anatomy" headline study** (Phase 2c), not a dead end. See [doc](implementation/ltn_current.md). |
| Knowledge Graph | ❌ Not built | — | Rescoped as memory + explainability corroboration. Spec: [knowledge_graph.md](target/knowledge_graph.md). |
| Decision Fusion | ❌ Not built | — | Now legitimately trainable under paper-aligned split. Spec: [decision_fusion.md](target/decision_fusion.md). |
| Explainability / Final Alert | ❌ Not built | — | + explanation-faithfulness measurement (Tier A). Spec: [explainability.md](target/explainability.md). |
| Anomaly pillar (autoencoder) | ❌ Not built | — | Phase 3 — benign-only reconstruction error. |
| Response engine (IPS) | ❌ Not built | — | Phase R (Shaunak solo, last). Temporal-replay containment. |

**Direction:** targeting top-tier publication — see [conference_roadmap.md](target/conference_roadmap.md) for plan v1.2 + the Tier-S/A/B "godly" agenda.

## Remaining Work ("what's left")

Ordered build queue. ✅ done · ▶ next · ⬜ pending.

| # | Item | Status | Notes |
|---|------|--------|-------|
| 0 | Behaviour abstraction rebuild | ✅ | Done 2026-06-18. Validated; thresholds saved. |
| 1 | **Re-ground LTN axioms on behaviours** | 🟡 Implemented; full run in progress | Ax3=LargePkt∧HighEntropy→¬benign, Ax4=BurstTraffic→¬benign. Smoke-tested OK. Awaiting full-run metrics. |
| 2 | Decide `RepeatedConnections` data path | ⬜ | IP/port side table from `preprocess.py`, or keep out of v1 (currently 0). Can be done alongside #1 or deferred. |
| 3 | Knowledge Graph (NetworkX) | ⬜ | Cluster embeddings → graph + decay + emerging-pattern detection. Spec: [knowledge_graph.md](target/knowledge_graph.md). |
| 4 | Decision Fusion | ⬜ | CNN + LTN + KG → verdict. Spec: [decision_fusion.md](target/decision_fusion.md). |
| 5 | Explainability / Final Alert | ⬜ | 3 explanations + alert. Spec: [explainability.md](target/explainability.md). |
| 6 | Ablation (CNN → +LTN → +KG → full) | ⬜ | Proves each component earns its place. |

Enhancement backlog (not scheduled): [enhancements.md](target/enhancements.md).

## Open Decisions

| Decision | Default chosen | Revisit? |
|----------|----------------|----------|
| KG backend | NetworkX | If scale demands, → Neo4j |
| Fusion mechanism | Fixed weights (Phase 1) → logistic (Phase 2) | After KG exists |
| Input modality | Flow-feature CSVs | PCAP/payload is future work |
| "Hard" vs soft axioms | Soft (SAT loss) + optional inference guard | During LTN rework |
| KG clustering | Static (fit once on train embeddings) | If drift observed |
| Decay "time" | Flow-count (reproducible) | — |
| Compute (CPU vs GPU) | **CPU** (Ryzen 9 9950X3D) | GPU (RTX 5080/Blackwell) deferred — needs WSL2 + CUDA 12.8 + newer TF + Keras 3 migration. Revisit if training volume grows (multi-seed/sweeps/cross-dataset). |

## Last Measured Results

> Fill in after running `eval.py` / `ltn.py`. (Not yet recorded in this doc.)

| Metric | CNN baseline | Hybrid-LTN |
|--------|-------------|------------|
| Binary PR-AUC | _TBD_ | _TBD_ |
| Binary ROC-AUC | _TBD_ | _TBD_ |
| FNR (missed attacks) | _TBD_ | _TBD_ |
| Zero-day recall (avg) | _TBD_ | _TBD_ |

## Session Log Pointer

Dated change history lives in [CHANGELOG.md](CHANGELOG.md). Bugs/risks live in [KNOWN_ISSUES.md](KNOWN_ISSUES.md).

# Project Status (Living Document)

> **Update this file at the end of every working session.** It is the single source of truth for "where are we right now." Last updated: **2026-06-18**.

## ▶ RESUME HERE (next session)

**Where we stopped:** LTN re-grounding is **implemented and smoke-tested**; the first **full training run is in progress** (background). When it finishes:
1. Read results from `outputs/ltn_run.log` (PR-AUC, ROC-AUC, per-family zero-day recall) and `outputs/figures/ltn_eval.png`.
2. Record them in "Last Measured Results" below and in [ltn_current.md](implementation/ltn_current.md).
3. **Interpret vs baseline (CNN PR-AUC 0.6689):** if the behaviour-grounded LTN improves zero-day recall (esp. DDoS via Ax3), that validates the approach. If not, tune ω / axiom weights or reconsider which behaviours to ground on.
4. Then proceed to the **Knowledge Graph** (item 3) — where ScanProbe's PortScan value gets realised.

**To re-run training:** `MPLBACKEND=Agg .venv\Scripts\python.exe scripts\ltn.py` (CPU, ~30–60 min). Smoke test: `LTN_SUBSET=50000 LTN_EPOCHS=2 ...`.

**Compute decision:** **CPU** (Ryzen 9 9950X3D). GPU (RTX 5080 / Blackwell) deferred — needs WSL2 + CUDA 12.8 + newer TF + Keras 3 migration. See Open Decisions.

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
| LTN reasoning | 🟡 Re-grounded; training run in progress | `scripts/ltn.py` | Ax3/Ax4 now behaviour-grounded (LargePkt∧HighEntropy, BurstTraffic). Smoke-tested OK. Full-run results pending. See [doc](implementation/ltn_current.md). |
| Knowledge Graph | ❌ Not built | — | Spec: [knowledge_graph.md](target/knowledge_graph.md). |
| Decision Fusion | ❌ Not built | — | Spec: [decision_fusion.md](target/decision_fusion.md). |
| Explainability / Final Alert | ❌ Not built | — | Spec: [explainability.md](target/explainability.md). |

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

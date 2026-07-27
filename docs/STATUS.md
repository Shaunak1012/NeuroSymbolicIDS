# Project Status (Living Document)

> **Update this file at the end of every working session.** It is the single source of truth for "where are we right now." Last updated: **2026-07-27**.

## ▶ RESUME HERE (next session)

**Major pivot decided (2026-06-18).** LTN full run finished and **underperformed** the baseline
(PR-AUC 0.45 vs CNN 0.67). Root cause diagnosed: focal CE collapsed to ~0.0005 so the SAT term
dominated ~40:1 (base paper used *balanced data + plain CE + ω=1*, keeping SAT gentle). We then
read the base paper (`basepaper.pdf`) and found our split is a *much harder, misaligned* protocol.
**Decision: protocol reset + rebuild per plan v1.2.** Full plan + conference agenda in
**[conference_roadmap.md](target/conference_roadmap.md)** — read that first.

**✅ Phase 0 DONE + dataset upgraded (2026-06-18).** Paper-aligned split (`preprocess_paper.py` → `data/processed/paper/`): 9 known classes stratified 80/10/10 = train 883,796 / val 110,475 / test 114,658, balanced 50/50, 6 zero-day in test only, leakage-verified. `config.yaml` + `config.py`/`features.py`/`tracking.py`/`metrics.py` scaffolding done. **log1p A/B: signed-log1p wins (0.980 vs 0.965) → adopted.**

**🔼 Switched to the FULL dataset variant (GeneratedLabelledFlows).** Replaced ML-CVE with the richer `data/raw_csv_full/` (has IP/port/timestamp). `preprocess.py` rewritten to extract a **meta side-table** (`meta_train/test.csv`) aligned by row; `preprocess_paper.py` carries meta through the split (`data/processed/paper/meta_{train,val,test}.csv`). **68 features + row counts identical to ML-CVE** (verified) — behaviour indices unchanged. IP/timestamp now available → `RepeatedConnections` + source-level response replay **unblocked** (PortScan test = 1 source IP → 998 dest ports, textbook). `config.yaml data.has_ip_timestamp: true`. Corrected labels (Engelen): still deferred.

**⚠️ Key nuance:** on the paper split, overall binary PR-AUC is ~0.97 (PortScan/DDoS are now *known*). The **real challenge metric is binary on the zero-day-only subset** (Bot/Web/Infiltration/Heartbleed, ~4,183 test flows) — matching the paper's "6 unknown classes" metric. Track that separately everywhere.

**✅ Phase 1 DONE (2026-06-18).** CNN retrained in-venv on paper split (loadable Keras-2 models). Caught+fixed a **focal-loss shape bug** (`(batch,1)` broadcast froze training) and a callback-monitor bug. Classical baselines + free novelty channels done. **6 fusion channels saved.**

**Phase 1 results — zero-day-only binary PR-AUC (headline):**
| Channel | zd PR-AUC | zd ROC |
|---------|-----------|--------|
| xgboost | **0.604** | 0.876 |
| cnn_paper | 0.599 | 0.855 |
| msp | 0.587 | 0.855 |
| mahalanobis | 0.583 | **0.883** |
| random_forest | 0.564 | 0.812 |
| isolation_forest | 0.153 | 0.766 |

Honest findings: XGBoost (tabular SOTA) ≈ CNN (pivot story to explanation/adaptivity/response); unsupervised anomaly (IsoForest 0.15) is far worse → motivates supervised neuro-symbolic. Per-family: CNN catches Web attacks (0.9+) but misses Bot (0.002)/Infiltration — the gap fusion/symbolic must close.

**🔄 Phase 2 IN PROGRESS (symbolic pillar).** `scripts/ltn_paper.py` (configurable: loss/axioms/omega/omega-mode, loss-ratio normalization = SAT-domination fix, ScanProbe axiom now valid) + `scripts/cnn_auxhead_paper.py` (aux behaviour head) written & smoke-tested (UNCOMMITTED).

**✅ CRITICAL open question RESOLVED (2026-07-27).** Ran the ω=0 control + a fixed-ω failure-anatomy sweep, all under the fairness-upgraded custom loop. Full fair-loop comparison (zero-day-only PR-AUC):

| Run | ω (mode) | zd PR-AUC | zd ROC |
|---|---|---|---|
| cnn_paper (reference, `model.fit`) | — | 0.599 | 0.855 |
| ltn_ctrl_w0 (no SAT, fair loop) | 0 fixed | 0.501 | 0.739 |
| ltn_repro (paper method: CE + base axioms) | 1.0 fixed | 0.485 | 0.738 |
| ltn_v2 (focal + both axioms, adaptive) | 0.1 ratio | 0.491 | 0.738 |
| **ltn_anat_w0p5** | 0.5 fixed | **0.520** | 0.765 |
| **ltn_anat_w1p0** | 1.0 fixed | **0.513** | 0.759 |
| ltn_anat_w2p0 | 2.0 fixed | 0.092 | 0.615 |
| cnn_auxhead_l0.5 (aux behaviour head, `model.fit`) | — | 0.497 | 0.727 |

**Interpretation:**
1. **Training-method confound confirmed as the dominant gap.** Even the ω=0 control (no symbolic loss at all, same custom loop) sits at 0.501 vs the CNN's 0.599 — a ~0.10 gap from the custom loop alone (no LR-reduction-on-plateau restore weights, no batch-norm running-stat nuances of `model.fit`, etc.). Everything below must be read *relative to 0.501*, not 0.599.
2. **Axioms genuinely help in a narrow band.** Fixed ω=0.5 (0.520) and ω=1.0 (0.513) both *beat* the ω=0 control — a real, non-trivial signal that the behaviour-grounded axioms (Ax3/4/5) carry useful information for zero-day detection, contradicting the pre-reset narrative that axioms only hurt.
3. **But there's a sharp phase transition.** ω=2.0 collapses to 0.092 — SAT overwhelms CE and wrecks classification (Web Attack recall ~0%), reproducing the original full-run failure mode. The safe zone is roughly ω∈[0.5, 1.0]; ω=2.0 is firmly past the cliff.
4. **The adaptive "ratio" omega-mode (v2) is leaving signal on the table.** It nets out at ω_eff≈0.1-equivalent (0.491), close to the *control*, not the sweet spot found by the fixed sweep (0.5–1.0). The loss-ratio normalization that fixed SAT-domination undershoots the useful axiom weight — worth recalibrating the ratio target if pursuing this loss-level path further.
5. **CE vs focal is a separate confound.** `ltn_repro` (CE + base axioms) is the *worst* fair-loop variant (0.485), even below the ω=0 control — suggesting plain CE is a poor fit for this class-imbalanced zero-day setting independent of the axiom question.
6. **Representation-level injection (aux-head) doesn't clearly help either.** `cnn_auxhead_l0.5` uses the *same* `model.fit` method as the CNN reference (no loop confound) yet still underperforms it (0.497 vs 0.599) — the behaviour-prediction auxiliary task alone isn't a free win, landing in the same ~0.49-0.52 band as the SAT variants.

**Phase-2 "three symbolic integration points" (per [conference_roadmap.md](target/conference_roadmap.md)):**

| Integration point | Method | Status | Best result (zd PR-AUC) |
|---|---|---|---|
| (1) Loss-level | Hybrid-LTN (SAT constraint), `scripts/ltn_paper.py` | ✅ Reproduced + anatomized | 0.520 (ω=0.5 fixed) |
| (2) Representation-level | Aux behaviour-prediction head, `scripts/cnn_auxhead_paper.py` | ✅ Measured | 0.497 |
| (3) Inference-level | Fusion (CNN + LTN + KG) | ❌ Not built — Phase 4 | — expected primary performance mechanism |

**Performance note (2026-07-27):** `ltn_paper.py`'s custom training loop was fully eager (~3,450 raw Python iterations/epoch) and left most CPU cores idle. Rewrote the train step under `@tf.function` (masks precomputed as numeric arrays instead of per-batch string comparison, since that's not graph-compatible) + explicit `intra_op=16`/`inter_op=2` thread config in both `ltn_paper.py` and `cnn_auxhead_paper.py`. Verified numerically equivalent (same ops, same math, just compiled) and faster per epoch on CPU. All results above are from the upgraded loop.

**▶ Next:** (1) commit Phase-2 work (P2-6); (2) decide whether to recalibrate the ratio-mode target given finding #4, or move on; (3) Phase 3 (autoencoder) on user's prompt. Note: failure-anatomy *balance* axis (vary benign_ratio) still TODO — follow-up candidate. **Focal-loss `reshape([-1])` fix** required in any new loss.

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
| LTN reasoning (paper-split) | 🟡 Anatomized — narrow band beats loop control, phase-transition found | `scripts/ltn_paper.py` | Fair-loop control 0.501; axioms beat it at ω=0.5–1.0 (best 0.520); collapses at ω=2.0 (0.092). Training-method confound (custom loop vs `model.fit`) accounts for most of the gap to CNN (0.599). See STATUS "RESUME HERE" for full table + interpretation. |
| LTN reasoning (legacy, temporal split) | 🔴 Superseded | `scripts/ltn.py` | Ran, underperformed (0.45 vs 0.67); SAT dominated CE ~40:1. Superseded by the paper-split protocol reset — see [doc](implementation/ltn_current.md). |
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

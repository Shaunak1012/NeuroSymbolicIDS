# Changelog (Living Document)

> Append a dated entry whenever something meaningful changes (code, data, decisions, results). Newest first. Keep entries short; link to detail docs.

## 2026-07-27 (measurement audit — retractions + corrected metrics)

- **Found a float32 softmax saturation defect invalidating 4 of 13 runs.** Scores were `1 - softmax[benign]`; for a confident model `p(benign)` rounds to exactly 1.0, so the score underflows to exactly 0.0 — on `ltn_ctrl_w0`, 99.25% of benign and 51.7% of zero-day flows. The 1%-FPR threshold therefore lands at 0.0 and flags everything (achieved FPR 1.000), producing the bogus "recall=1.0000 for every family" rows and an identical `zd_f1 = 0.1315` across three models (the algebraic predict-all constant at 7% prevalence). Saturated: `ltn_ctrl_w0`, `ltn_repro`, `ltn_v2`, `ltn_anat_w2p0` — i.e. every fair-loop run the control experiment depended on.
- **Found the blended headline metric is a size-weighted mixture** of families whose detectability differs ~30x, so it moves for reasons unrelated to detection quality — and it reorders the model ranking versus a per-family view.
- **Rewrote `metrics.py`:** headline is now per-family PR-AUC + macro-average over adequately powered families (n≥100), with `chance_pr_auc`/`lift` columns; blended demoted to secondary; Heartbleed (n=11), Infiltration (n=36), SQL Injection (n=21) excluded as underpowered instead of reported to 4 dp; added saturation diagnostics (`achieved_fpr`, `largest_tie_frac`) and a `to_logodds` helper.
- **RETRACTED "axioms help at ω=0.5–1.0"** (written earlier the same day). It rested on blended (0.520 > 0.501); on macro it reverses (0.5552 vs 0.5937), and per-family ω=0.5 is worse than the control on both families carrying signal.
- **RETRACTED "XGBoost ≈ CNN (tabular SOTA matches us)"** from Phase 1. On macro the CNN beats XGBoost (0.6446 vs 0.6372) — the tie was an artefact of family sizes. The "pivot the story to explanation/adaptivity" framing was motivated by a tie that isn't there.
- **RETRACTED "unsupervised anomaly is far worse → motivates supervised neuro-symbolic".** IsolationForest is far worse overall (macro 0.063) but scores **0.0571 on Bot — indistinguishable from the CNN's 0.0591**. 884K labelled training flows buy no Bot signal over an unsupervised outlier detector.
- **New central finding: Bot is at chance for every supervised method** (lift 1.0–1.8x); Mahalanobis (0.1467, 4.3x) is the sole exception and is a *distance* method — the open-set-recognition signature. Evidence that the per-flow representation does not contain the Bot signal: Bot is C2 beaconing, whose signature is periodicity *across* flows, destroyed by i.i.d. flow classification. Explains why every symbolic intervention moves the number by only ±0.02, and why Ax3/4/5 (thresholded functions of the same 68 input features) are tautological.
- Upheld: the ω=2.0 collapse, and the aux head underperforming the plain CNN (0.5744 vs 0.6446, same training method, neither saturated).
- Added `scripts/rescore_logits.py` (recompute scores as `logsumexp(attack_logits) − benign_logit` from saved models) and a missing `model.save` in `cnn_auxhead_paper.py`. **Both blocked**: TensorFlow stopped loading mid-session with `An Application Control policy has blocked this file` across rotating native DLLs; numpy/sklearn/scipy unaffected. Not worked around — machine security control.
- Revised plan: A (fix measurement) → B (skyline/oracle to establish the per-family ceiling) → C (host/session-level aggregation using the IP+timestamp from the dataset upgrade, with a falsifiable prediction that Bot rises above chance).

## 2026-07-27 (Phase 2 — symbolic pillar, fair-loop batch + training-loop speedup)

- **Resolved the training-method confound.** Ran the ω=0 control under the fairness-upgraded custom loop (best-by-val-loss, LR annealing) — it lands at zd PR-AUC 0.501, vs the CNN reference's 0.599. Confirms most of the LTN-vs-CNN gap is the custom loop itself, not the axioms. All LTN numbers must be read relative to 0.501, not 0.599.
- **Failure-anatomy ω-sweep (fixed omega, focal + both axioms):** ω=0.5 → 0.520 PR-AUC, ω=1.0 → 0.513 (both beat the control — axioms genuinely help in this band), ω=2.0 → 0.092 (sharp collapse, SAT overwhelms CE, reproduces the original full-run failure mode). Safe zone ≈ ω∈[0.5, 1.0].
- **Adaptive ratio-mode (`ltn_v2`) undershoots the sweet spot** — nets out at ω_eff≈0.1-equivalent (0.491), close to the control rather than the fixed-sweep optimum. Flagged as a recalibration candidate.
- **`ltn_repro` (CE + base axioms) is the worst fair-loop variant** (0.485, below the control) — isolates plain CE as a poor loss choice for this imbalance, independent of the axiom question.
- **Aux behaviour-prediction head measured** (`scripts/cnn_auxhead_paper.py`, representation-level integration point): 0.497 zd PR-AUC, using the same `model.fit` method as the CNN reference (no loop confound) — still underperforms it, landing in the same band as the SAT variants.
- **Assembled the Phase-2 "three symbolic integration points" table** (loss-level / representation-level / inference-level) per `conference_roadmap.md`. Inference-level (fusion) remains the expected primary performance mechanism — not yet built (Phase 4).
- **Training-loop performance fix:** `ltn_paper.py`'s custom loop ran fully eager (~3,450 raw Python iterations/epoch), starving the CPU's 16 cores behind Python dispatch overhead (~2.6 cores observed). Rewrote the train step under `@tf.function` — required precomputing benign/attack masks as numeric arrays instead of per-batch string comparison (not graph-compatible) — plus explicit `intra_op=16`/`inter_op=2` thread config in both `ltn_paper.py` and `cnn_auxhead_paper.py`. Smoke-tested equivalent, faster per epoch; all Phase-2 results above are from the upgraded loop.
- Full results in `outputs/metadata/runs.jsonl`. Updated STATUS.

## 2026-06-18 (Phase 1 — neural pillar + baselines)

- **Retrained the CNN in-venv on the paper split** (`scripts/cnn_paper.py`) — loadable Keras-2 models, log1p transform, `metrics.py` headline. Early-stopped epoch 25, val-acc 0.997.
- **Fixed a real focal-loss bug** (see KNOWN_ISSUES): Keras passes `y_true` as `(batch,1)`, so `one_hot` broadcast to a `(B,B,n)` garbage tensor → frozen val_loss / random accuracy. Confirmed by controlled race (focal as-is 0.50 vs fixed 0.996 val-acc). Fixed `reshape([-1])` in `cnn_paper.py` + legacy `cnn3.py`. Also fixed callback monitors (`val_sparse_categorical_accuracy`) that had silently disabled early-stopping/checkpointing.
- **Classical baselines** (`scripts/baselines.py`): XGBoost, RandomForest, IsolationForest. **Free novelty channels** (`scripts/novelty.py`): MSP + Mahalanobis.
- **Phase-1 zero-day-only PR-AUC:** xgboost 0.604 · cnn 0.599 · msp 0.587 · mahalanobis 0.583 · rf 0.564 · isolation_forest 0.153. Honest: XGBoost ≈ CNN (pivot to explanation/adaptivity/response); unsupervised anomaly far worse (motivates supervised NSAI). Per-family: CNN catches Web attacks (~0.9) but misses Bot (0.002)/Infiltration.
- 6 fusion channels saved to `outputs/predictions/`. Metrics logged to `runs.jsonl`. xgboost pinned.

## 2026-06-18 (dataset upgrade → full variant with IP/timestamp)

- **Switched from the ML-CVE variant to the full `GeneratedLabelledFlows`** (added `data/raw_csv_full/`, gitignored). Rewrote `scripts/preprocess.py` to ingest the 85-col CSVs, guard the `Infinity`-string quirk (`to_numeric coerce`), and extract a **meta side-table** (`meta_train/test.csv` — Flow ID, Source/Dest IP+Port, Protocol, Timestamp) aligned row-for-row through cleaning.
- **Verified feature parity:** identical 68 features, same 10 constant columns, exact same row counts (train 1,666,532 / test 1,161,344) as ML-CVE → behaviour indices unchanged (Destination Port at 0, etc.).
- **`preprocess_paper.py` now splits on indices** so meta follows each row into paper train/val/test (`data/processed/paper/meta_{train,val,test}.csv`), all aligned.
- **Result:** IP/timestamp available → `RepeatedConnections` + source-level response replay **unblocked**. PortScan test set = 15,881 flows from **1 source IP → 998 distinct dest ports** (canonical scan signature). `config.yaml`: `variant: GeneratedLabelledFlows`, `has_ip_timestamp: true`. Done at the zero-cost window (before any training on the paper split).

## 2026-06-18 (Phase 0 — protocol reset)

- **Built the paper-aligned split** (`scripts/preprocess_paper.py` → `data/processed/paper/`): pools all 5 days, 9 known classes (BENIGN + 8 attacks incl. PortScan/DDoS) stratified 80/10/10 (train 883,796 / val 110,475 / test 114,658), benign under-sampled 1:1 (balanced 50/50), 6 rare classes (Bot, Web×3, Infiltration, Heartbleed) appended to test only. Leakage asserted (no zero-day in train/val). Temporal split kept untouched as secondary hard-mode.
- **Config + scaffolding:** `config.yaml` (all protocol params) + `scripts/config.py`, `scripts/features.py` (shared transform), `scripts/tracking.py` (JSONL run logger). pyyaml pinned.
- **log1p A/B (Phase 0.3):** signed-log1p `sign(x)·log1p(|x|)` beat raw on the paper split (PR-AUC 0.980 vs 0.965) → adopted in config.
- **Data constraint found:** the CSVs are the **MachineLearningCVE** variant — no Flow ID/IP/Timestamp columns → IP-based `RepeatedConnections` and response-replay are limited (documented in config `has_ip_timestamp: false`).
- **Nuance recorded:** overall binary is easy (~0.97) under the paper split since PortScan/DDoS are known; the challenge metric is the **zero-day-only binary** (~4,183 test flows), matching the paper's "6 unknown" metric.

## 2026-06-18 (strategic pivot → conference roadmap)

- **LTN full run completed and underperformed** — PR-AUC 0.4529 vs CNN baseline 0.6689 (−0.22); early-stopped ~epoch 10, val accuracy declined after epoch 2. Root cause: focal CE collapsed to ~0.0005, SAT term dominated ~40:1. Per-family: PortScan 0.36→0.16, DDoS 0.67→0.64.
- **Fusion investigation (post-hoc, no retraining):** leaky logistic fusion (fit on zero-day-labelled test half) reached 0.78 (+0.11) — but the honest **label-free** parameter-free fusion was −0.16. Conclusion: behaviours carry real signal, but supervised transfer to zero-day is the wall. Also found `model_multiclass_best.keras` is **Keras 3** (won't load in our Keras-2.15 venv) → in-venv retrain required.
- **Read the base paper** (`basepaper.pdf`, Bizzarri et al., IEEE). Findings: it uses payload bytes (1500) not flow features; stratified 80/10/10 with **known attacks in test**; zero-day = rare classes only (keeps PortScan/DDoS in training); **balanced data + plain CE + ω=1** (why their SAT stays gentle and ours dominated). Their result: zero-day acc 48→60%. Our protocol was a much harder, misaligned exam.
- **Decided a strategic pivot** to a top-tier-publication plan: protocol reset (paper-aligned split) → retrain in-venv → reproduce paper → fix + extend → multi-pillar fusion → cross-dataset → response engine. Captured in **[conference_roadmap.md](target/conference_roadmap.md)** (plan v1.2 + Tier-S/A/B agenda). Headline thesis: *"when and why neuro-symbolic training fails under imbalance, and the inference-time fusion fix."* Response/IPS engine added as Shaunak's solo final phase. Updated STATUS, enhancements.

## 2026-06-18 (LTN re-grounded)

- **Re-grounded the LTN axioms on behaviours** (`scripts/ltn.py`), fixing the core flaw (label tautologies). Kept Ax1/Ax2 as supervised anchors; replaced Ax3 (was DoS-label) with **LargePackets∧HighEntropy → ¬benign** and Ax4 (was Patator-label) with **BurstTraffic → ¬benign**, weighted per-flow by fuzzy behaviour confidences from `behavior.py` (computed on raw features pre-scaling, shuffled in lockstep with batches). ScanProbe/HighVolume deliberately excluded from training axioms (ScanProbe benign-heavy in training → reserved for KG stage).
- **Added smoke-test hook** (`LTN_SUBSET` / `LTN_EPOCHS` env vars). Smoke test (50k×2) passed end-to-end: no NaNs, behaviour axioms compute & satisfy (Ax3≈0.90, Ax4≈0.78).
- **Launched first full training run** (background, CPU, headless `MPLBACKEND=Agg`, logging to `outputs/ltn_run.log`). Results pending. Baseline to beat: CNN PR-AUC 0.6689.
- Updated [ltn_current.md](implementation/ltn_current.md), STATUS.

## 2026-06-18 (session close)

- **Compute decision recorded:** training stays on **CPU** (Ryzen 9 9950X3D, 62 GB RAM — LTN run estimated ~30–60 min). GPU (RTX 5080) **deferred**: Blackwell needs WSL2 + CUDA 12.8 + newer TF + likely Keras 3 migration — poor ROI now, revisit if training volume grows. Logged in STATUS Open Decisions.
- **STATUS.md prepped for resume:** added a "▶ RESUME HERE" block (next action = re-ground LTN axioms on behaviours) and a "Remaining Work" queue (LTN → RepeatedConnections → KG → Fusion → Explainability → Ablation). No code changed this turn.

## 2026-06-18 (behaviour abstraction rebuilt)

- **Rebuilt `scripts/behavior.py`** from broken/dead to working+validated. Verified the real 68-column feature order via `check.py` (old indices were badly wrong — e.g. old `RATE_FEATURES=[5,6,7]` actually pointed at packet-length fields, old flags pointed at IAT). New module: vectorised, fuzzy `[0,1]` outputs, data-driven percentile thresholds saved to `outputs/metadata/behaviour_thresholds.npy`, built-in validation harness.
- **Two bugs caught by validation and fixed:** (1) flag-count `ProtocolAnomalies` fired 45% on benign / 0% on attacks (matched benign UDP), so the flag approach was **dropped** — flag-count columns are ~0 even for real scans in CIC-IDS2017; (2) replaced it with **`ScanProbe`** (short duration × tiny payload), which scores **0.955 on the zero-day PortScan** vs 0.244 benign.
- **Behaviours:** BurstTraffic, HighVolume, LargePackets, HighEntropy (approx), ScanProbe, RepeatedConnections (unavailable → 0). LargePackets/HighEntropy ~7–8× attack-discriminative; PortScan+DDoS (largest zero-day families) strongly covered. Web Attacks/Bot remain weakly covered (documented limitation).
- Updated [behaviour_abstraction_current.md](implementation/behaviour_abstraction_current.md), STATUS, KNOWN_ISSUES.
- **Next:** re-ground LTN axioms on these behaviours.

## 2026-06-18 (enhancements captured)

- **Captured an enhancement backlog** at [target/enhancements.md](target/enhancements.md) — anomaly-detection baseline, multi-seed variance, cross-dataset eval, active-learning loop, calibration/abstain, latency benchmark, config/orchestration/tests, dataset-label caveat. **Backlog only — nothing scheduled or started.**

## 2026-06-18 (reorg)

- **Repository reorganised to professional layout.** Moved all generated artifacts out of the repo root into `data/processed/`, `models/`, and `outputs/{arrays,embeddings,predictions,metadata,figures}/`. Added [`scripts/paths.py`](../scripts/paths.py) as the single source of path truth and rewired every script (`preprocess`, `cnn3`, `eval`, `ltn`, `behavior`, `check`, `visual`) to import it — no more hardcoded root paths. Verified: all scripts compile; all 28 existing artifacts present at new locations (eval can run without regeneration).
- **Artifact cleanup.** Deleted stale `model_focal.keras` + `behaviour_thresholds.npy`. LTN outputs never existed (script not yet run), so nothing to clear there. Kept valid preprocessing/CNN/eval artifacts (expensive to regenerate).
- **Archived** the original `PROJECT_DOCUMENTATION.md` → `docs/archive/` (superseded by the structured docs).
- **Rewrote `.gitignore`** to directory-based ignores matching the new layout (`outputs/figures/` intentionally tracked).
- Git check: only `.gitignore` + an old `preprocess_friday.py` were ever tracked; no large binaries committed.

## 2026-06-18 (later)

- **Dead code removed.** Deleted `utils/config.py` + `utils/` dir (stale, from abandoned payload pipeline, imported by nothing). Removed the unused `y_train_b`/`y_val_b` binary-split block in `cnn3.py`. **Kept** `behavior.py` and the `fuzzy_*` operators in `ltn.py` — both feed the upcoming behaviour/LTN rework. `model_focal.keras` (stale binary artifact) left in place but gitignored. Updated all doc references.
- **Environment set up.** Installed Python 3.11.9 (winget, user scope) and created `.venv` at repo root. Added pinned `requirements.txt` (Python 3.11 / TF 2.15.1 / Keras 2 / numpy 1.26.4 + KG libs networkx, python-louvain + explainability lib shap). Smoke test passed: all imports work, `tensorflow.keras` (Keras 2) OK, CPU mode (no GPU).
- **Rewrote `.gitignore`** to match the real artifact layout (root-level `*.npy`/`*.keras`/`*.pkl` + large generated CSVs + `.venv/`); the old one referenced the abandoned payload pipeline's paths.
- **Found `utils/config.py` is stale orphaned code** from the abandoned raw-PCAP/payload pipeline (PAYLOAD_LEN=1500, 3 classes). Not imported anywhere. Corrected `scripts_reference.md`; logged in KNOWN_ISSUES.

## 2026-06-18

- **Documentation overhaul.** Created `docs/` (implemented-state docs), `docs/target/` (target-architecture specs + gap analysis), `docs/implementation/` (line-by-line source audits), and dynamic tracking files (`STATUS.md`, `CHANGELOG.md`, `KNOWN_ISSUES.md`). Added root `CLAUDE.md` for session onboarding.
- **Source audit completed** for `cnn3.py`, `behavior.py`, `ltn.py`, `preprocess.py`, `eval.py`:
  - CNN verified ✅ correct (minor: double class-weighting).
  - `behavior.py` found ❌ orphaned/dead (never imported; thresholds never generated; feature indices misaligned). See [audit](implementation/behaviour_abstraction_current.md).
  - `ltn.py` found ⚠️ conceptually wrong (axioms are label tautologies, fuzzy operators unused, not wired to behaviour). See [audit](implementation/ltn_current.md).
- **Correction:** earlier draft docs wrongly listed **Bot** as a training class (index 8) with 9 train classes. Source confirms Bot is a **zero-day/test** class; training has ~8 classes. Fixed in `dataset.md`, `models.md`, `artifacts.md`.
- **Decisions recorded:** KG → NetworkX; Fusion → fixed-weights then logistic; input → flow-feature CSVs. See [STATUS.md](STATUS.md#open-decisions).

<!-- TEMPLATE for new entries:
## YYYY-MM-DD
- **<area>.** <what changed and why>. <link to detail>.
-->

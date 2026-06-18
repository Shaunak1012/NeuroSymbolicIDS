# Changelog (Living Document)

> Append a dated entry whenever something meaningful changes (code, data, decisions, results). Newest first. Keep entries short; link to detail docs.

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

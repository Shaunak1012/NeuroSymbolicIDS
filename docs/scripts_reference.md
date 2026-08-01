# Scripts Reference

All scripts live in `scripts/`. Run them **from the project root** using the venv interpreter
(`.venv\Scripts\python.exe`), which puts `scripts/` on `sys.path` so `import paths` works.

> Last verified against source: **2026-07-29** (22 scripts).

## Map

| Group | Scripts |
|---|---|
| **Infrastructure** | `paths` · `config` · `features` · `tracking` · `metrics` |
| **Current pipeline** (paper split) | `preprocess` → `preprocess_paper` → `cnn_paper` → `baselines` · `novelty` → `behavior` → `ltn_paper` · `cnn_auxhead_paper` |
| **Analysis / one-off** | `skyline_oracle` · `rescore_logits` · `fusion_beaconlike` |
| **Legacy** (temporal split, superseded) | `cnn3` · `eval` · `ltn` |
| **Utilities** | `dashboard_server` · `visual` · `check` |

---

# Infrastructure

## `scripts/paths.py`

**Purpose**: Central definition of every filesystem location. All other scripts `import paths`.

**Constants**: `ROOT`, `RAW_CSV_FULL` (current input), `RAW_CSV` (legacy ML-CVE, superseded),
`PROCESSED`, `PAPER` (= `data/processed/paper/`), `MODELS`, `ARRAYS`, `EMBEDDINGS`, `PREDICTIONS`,
`METADATA`, `FIGURES`. Output directories are created on import; raw-CSV dirs are inputs and are not.
Helper: `paths.p(dir, filename)`.

**To relocate any artifact**, edit `paths.py` only — never hardcode paths in pipeline scripts.

## `scripts/config.py`

**Purpose**: Loads the central [`config.yaml`](../config.yaml) (protocol params, class lists, seed).

```python
import config
cfg = config.get()          # cached dict
seed = cfg["seed"]
zd   = cfg["zero_day_classes"]
```

`config.yaml` is the single source of truth for: the seed, `protocol.{val_frac,test_frac,benign_ratio,feature_transform}`,
the 8 `known_attacks`, the 6 `zero_day_classes`, and `data.{variant,raw_dir,has_ip_timestamp,n_features}`.

## `scripts/features.py`

**Purpose**: The shared feature transform, so every model prepares data identically.

`signed_log1p(X)` = `sign(x)·log1p(|x|)` — a heavy-tail compressor that, unlike plain `log1p`,
handles the `-1` sentinels in `Init_Win_bytes_*`. Selected by a Phase-0.3 A/B (**0.980 vs 0.965**
PR-AUC on the paper split) and pinned via `config protocol.feature_transform: log1p`.

```python
import features, config
Xt = features.transform(X, config.get()["protocol"]["feature_transform"])
```

## `scripts/tracking.py`

**Purpose**: Lightweight experiment log — one JSON line per run, so the ablation table self-assembles.

```python
import tracking
tracking.log_run("cnn_paper", {"protocol": "paper", "seed": 42}, {"pr_auc": 0.97})
runs = tracking.load_runs()     # -> list[dict]
```

Writes `outputs/metadata/runs.jsonl`. Also consumed by `dashboard_server.py` for the run-history table.

## `scripts/metrics.py`

**Purpose**: The standard evaluation suite. **Every experiment reports the same views**, so the
easy overall number can never masquerade as the result.

**Headline** = per-family zero-day PR-AUC + the **macro-average over adequately powered families**.
The blended "benign vs all 6 unknowns" figure is reported as **secondary only** — it is a
size-weighted mixture of families whose detectability differs ~30×, so it moves for reasons
unrelated to detection quality, and it demonstrably reorders the model ranking.

| API | Purpose |
|---|---|
| `evaluate(y_mc, scores, zero_day_classes, fpr=0.01)` | Full report dict |
| `print_report(r)` | Human-readable console output |
| `flatten(r, prefix="")` | Flatten for `tracking.log_run` |
| `to_logodds(p_attack)` | Convert a saturated probability score to log-odds |
| `MIN_FAMILY_N = 100` | Families below this are excluded from macro + flagged `underpowered` |

**Two guards, both added because the failure was observed in real runs:**

- **`underpowered`** — Heartbleed (n=11), Infiltration (n=36) and SQL Injection (n=21) are excluded
  from the macro-average rather than reported to 4 dp, which would imply precision that does not exist.
- **`saturated`** — a float32 softmax collapses `1 − p(benign)` to exactly 0.0 for confident models,
  which lands the 1%-FPR threshold at 0.0, flags everything, and yields fake `recall=1.0` rows.
  Diagnostics `achieved_fpr` and `largest_tie_frac` detect it. Fix a saturated run with
  `rescore_logits.py`, not by reinterpreting the number.

---

# Current pipeline (paper-aligned split)

## `scripts/preprocess.py`

**Purpose**: Clean the raw CIC-IDS2017 CSVs into aligned feature matrices **plus an IP/timestamp
meta side-table**.

**Input**: `data/raw_csv_full/` (`paths.RAW_CSV_FULL`) — the **GeneratedLabelledFlows** variant,
85 columns, retaining Flow ID / Source+Destination IP / Ports / Protocol / Timestamp.

**Key steps**: strip whitespace from column names · guard the `Infinity`-string quirk via
`to_numeric(coerce)` · drop `inf`/`NaN` rows (duplicates deliberately kept) · extract the meta
side-table **aligned row-for-row through cleaning** · drop identifiers from the feature matrix ·
drop zero-variance columns · align train/test column sets → **68 features**.

**Outputs**: `clean_*.csv`, `features_*.csv`, `labels_*` arrays, `constant_cols_dropped.npy`,
`meta_train.csv` / `meta_test.csv`.

> Feature parity with the old ML-CVE variant was verified: identical 68 features, same 10 constant
> columns, exact same row counts (train 1,666,532 / test 1,161,344) — so behaviour feature indices
> were unchanged by the dataset upgrade.

## `scripts/preprocess_paper.py`

**Purpose**: Re-slice the cleaned matrices into the **paper-aligned protocol** (Bizzarri et al.).

- 9 known classes (BENIGN + 8 attacks **including PortScan and DDoS**) → stratified **80/10/10**
- 6 rare classes (Bot, Heartbleed, Infiltration, Web Attack ×3) → appended to **test only**
- BENIGN under-sampled to `config protocol.benign_ratio` (1.0 = balanced, paper-faithful)
- Splits on **indices**, so `meta_*.csv` follows each row into train/val/test
- Asserts no zero-day leakage into train/val

**Outputs** → `data/processed/paper/`: `X_{train,val,test}.npy` (68 cols), `y_*_mc.npy` (string
labels), `y_*_bin.npy`, `meta_{train,val,test}.csv`, `known_classes.npy`, `zero_day_classes.npy`,
`split_report.txt`.

**Sizes**: train 883,796 / val 110,475 / test 114,658; ~4,183 zero-day test flows.

## `scripts/cnn_paper.py`

**Purpose**: Phase-1 neural pillar — the 1D CNN on the paper split. **This is the reference baseline.**

Same architecture as `cnn3.py` (Conv1D 32/64/128 → Dense(64) `"embedding"` → Dense(32) → softmax),
plus the signed-log1p transform, the **fixed** focal loss, and `metrics.py` as the headline.
Produces loadable **Keras-2** models.

**Smoke test**: `CNN_SUBSET=50000 CNN_EPOCHS=2 python scripts/cnn_paper.py`

**Outputs**: `models/cnn_paper{,_best}.keras`, `models/scaler_paper.pkl`,
`models/label_encoder_paper.pkl`, `outputs/embeddings/X_{train,val,test}_cnn_paper_emb.npy`,
`outputs/predictions/y_prob_cnn_paper_test.npy`, `outputs/metadata/cnn_paper_history.pkl`.

**Result**: macro zero-day PR-AUC **0.6446** — the number every later stage is measured against.

## `scripts/baselines.py`

**Purpose**: Classical + anomaly baselines, so "why not XGBoost / Isolation Forest?" is answered
with numbers rather than assertion.

- **XGBoost** — supervised binary (benign vs known attack), the tabular SOTA → macro **0.6372**
- **RandomForest** — supervised binary → ⚠️ **blended 0.5643 only; never re-scored on the corrected
  macro metric.** Its `runs.jsonl` entry predates the 2026-07-27 `metrics.py` rewrite and carries no
  per-family breakdown, so it is absent from STATUS's corrected table. Re-run `baselines.py` to fill
  this gap before citing RF in any comparison. Tracked in [KNOWN_ISSUES.md](KNOWN_ISSUES.md).
- **IsolationForest** — **unsupervised**, fit on benign only (zero-day-legitimate) → macro **0.0628**
  (but Bot 0.0571, statistically indistinguishable from the CNN's 0.0591 — supervision buys nothing
  on the family that matters)

All evaluated via `metrics.py`, logged to `runs.jsonl`, saved as fusion channels. sklearn/xgboost
only — **no TensorFlow**, so these run even when TF is unavailable.

## `scripts/novelty.py`

**Purpose**: Free open-set / novelty channels from the already-trained CNN — post-hoc, no retraining.

- **MSP** — `1 − max softmax` (Hendrycks & Gimpel 2017 baseline) → macro 0.6123
- **Mahalanobis** — min distance to per-class Gaussians in the 64-dim embedding space, shared
  covariance. ⚠️ **n=3 corrected: macro 0.3777, Bot 0.1030 (3.0× chance, range 1.2–4.3×).** The
  widely-quoted "Bot 0.1467 / 4.3×" was **seed 42 only, the best of three** — retracted 2026-08-02.
  It is *not* the best Bot channel; the autoencoder is both higher (3.8×) and far more stable
  (spread 1.5× vs Mahalanobis's 3.6×). Still notable as a *distance* method on an attack-trained
  representation. **Multi-seed support: `NOVELTY_SEED=43 python scripts/novelty.py`.**

Run after `cnn_paper.py`.

## `scripts/behavior.py`

**Purpose**: Library — maps raw flow features into 7 named fuzzy behaviours. The shared symbolic
vocabulary for the LTN axioms and (next) the Knowledge Graph. **Not a pipeline stage**; imported.

Running it directly (`python scripts/behavior.py`) fits thresholds on `features_train.csv`, saves
`outputs/metadata/behaviour_thresholds.npy`, and prints the discriminativeness validation tables.

```python
import behavior
thr = behavior.compute_thresholds(X_train_raw)   # p50/p95 high ramps, p5/p40 low ramps
behavior.save_thresholds(thr)
beh  = behavior.abstract_behaviours(X_raw, thr)  # dict[name] -> (N,) in [0,1]
M    = behavior.behaviour_matrix(X_raw, thr)     # (N, 7); columns == BEHAVIOUR_NAMES
```

⚠️ **Pass RAW, unscaled features** — thresholds are percentiles of real units.
⚠️ **Select behaviours by name, never by slice** — see
[behaviour_abstraction_current.md](implementation/behaviour_abstraction_current.md) for the
ordering hazard that already caused one silent bug.

Full detail: [implementation/behaviour_abstraction_current.md](implementation/behaviour_abstraction_current.md).

## `scripts/ltn_paper.py`

**Purpose**: Phase-2 symbolic pillar. **One configurable trainer** serving (a) faithful base-paper
reproduction, (b) LTN v2, and (c) the failure-anatomy grid.

`Hybrid loss = CE + ω_eff · SAT`, via a custom training loop (SAT needs per-batch behaviour weights
and labels, which `model.fit` cannot supply). The train step is compiled under `@tf.function`, with
masks precomputed as numeric arrays (per-batch string comparison is not graph-compatible), plus
explicit `intra_op=16` / `inter_op=2` thread config.

**Configured entirely by environment variable:**

| Var | Values | Default | Meaning |
|---|---|---|---|
| `LTN_LOSS` | `focal` \| `ce` | `focal` | Classification loss |
| `LTN_AXIOMS` | `base` \| `behaviour` \| `both` | `both` | Which axiom set |
| `LTN_OMEGA` | float | `0.1` | SAT weight |
| `LTN_OMEGA_MODE` | `fixed` \| `ratio` | **`ratio`** | See below |

**Axioms**: Ax1 (benign→benign) + Ax2 (attack→¬benign) are label anchors [`base`];
Ax3 (LargePackets∧HighEntropy→¬benign), Ax4 (BurstTraffic→¬benign), Ax5 (ScanProbe→¬benign),
Ax6 (BeaconLike→¬benign) are behaviour-grounded [`behaviour`].

> **`LTN_OMEGA_MODE=ratio` is the default for a measured reason.** `fixed` mode makes the SAT weight
> independent of CE's actual magnitude, so whether SAT or CE dominates the early-training gradient is
> decided by random init — at ω=1.0 that collapsed **2 of 3 seeds** (macro 0.05, 0.04) while ω=2.0
> collapsed deterministically. `ratio` scales SAT to a fixed fraction of CE and eliminated the
> collapse across all 3 seeds at no measured cost. **Do not use `fixed` without a specific reason.**

**Outcome (Phase 2, concluded):** every axiom variant costs macro PR-AUC relative to the no-axiom
control (0.6194 mean, n=3), robust across seeds. See [STATUS.md](STATUS.md).

## `scripts/cnn_auxhead_paper.py`

**Purpose**: Phase-2(d) — **representation-level** symbolic injection, the alternative to a logic
constraint that fights the classification loss.

Adds a second head that *predicts* the fuzzy behaviours from the shared embedding:
`loss = focal(class) + λ · BCE(behaviour)`. A well-behaved auxiliary/multi-task objective — it shapes
the representation to be behaviour-aware without competing with classification, and was intended to
produce embeddings that directly benefit the Knowledge Graph.

**Config**: `AUX_LAMBDA` (0.5) · `AUX_EPOCHS` (50) · `AUX_SUBSET` (0 = full).

**Result**: macro **0.5744** vs the plain CNN's 0.6446 — same `model.fit` training method, neither
saturated, so this is a clean comparison. **The aux head does not help.** Bot lift was also not
reproducible across two runs at the same seed (1.0× then 0.8×).

---

# Analysis / one-off

## `scripts/skyline_oracle.py`

**Purpose**: Establish the **per-family ceiling** — is Bot genuinely undetectable in the 68-dim
per-flow space, or is near-chance PR-AUC merely a zero-day *generalization* failure?

**Method**: stratified 50/50 split of each zero-day family's test flows into an oracle-train half
(label revealed, added to training) and a **held-out** eval half. Retrain XGBoost with identical
hyperparameters to `baselines.py`; evaluate only on benign(test) + oracle-eval-half, compared against
the never-seen baseline **on the same rows** — apples-to-apples, only training exposure differs.

**Result**: Bot PR-AUC **0.0314 → 0.9764** (56× chance) with ~1,000 labelled examples; macro
0.5947 → 0.9899. **This falsified the "beaconing / cross-flow" hypothesis** — the information was
always present per-flow. Also used to isolate a Bot-vs-benign-only classifier's feature importances,
which is where `BeaconLike` came from.

No TensorFlow required.

## `scripts/rescore_logits.py`

**Purpose**: Recompute zero-day scores in **log-odds space** from saved models, correcting float32
softmax saturation.

Scores were `1 − softmax[benign]`; for a confident model `p(benign)` rounds to exactly 1.0 and the
score underflows to exactly 0.0 (measured: 99.25% of benign and 51.7% of zero-day flows on
`ltn_ctrl_w0`). Log-odds fixes this at the source by reading **pre-softmax logits**:

```
s = logsumexp(attack_logits) − benign_logit      # == log( P(attack) / P(benign) )
```

Extend the `TAGS` list to re-score additional runs. Writes `*_logodds_test.npy` alongside the
originals. Requires TensorFlow (model load).

> Diagnostic value: PR-AUC is rank-based, so log-odds only changes it when tie blocks were corrupting
> the ranking. `ltn_anat_w2p0` **stayed** at 0.0348 after rescoring — proving that collapse was a real
> weight degeneration, not a measurement artefact.

## `scripts/fusion_beaconlike.py`

**Purpose**: The **inference-level** integration point — the third of the three from
[conference_roadmap.md](target/conference_roadmap.md), and the only one that does not touch training.

Fits a small logistic combiner (CNN attack log-odds + BeaconLike raw score) on **known-class
validation data only**, then applies it blind to the zero-day test set. The paper split's val set
contains no zero-day flows by construction, so this **cannot leak** — unlike the earlier "leaky
fusion" already flagged as invalid.

**Result**: macro **0.6447** vs the CNN's 0.6446 alone — *nothing*. Fitted coefficients `[2.35, 0.02]`:
the combiner learned to ignore the symbolic channel.

> This is a **mechanistic finding, not a failed experiment.** A non-leaky calibration is fit on data
> that structurally cannot contain the class (Bot) that makes BeaconLike valuable, so it cannot
> discover that signal's worth. This is why loss-level injection is currently the only mechanism that
> can get a hand-specified zero-day signature into the model at all.

---

# Legacy (temporal split — superseded 2026-06-18)

> These still execute, but produce the **superseded** temporal-split artifacts. No reported result
> uses them. Retained for the secondary "hard mode" comparison. The temporal split trained on
> Mon–Wed and tested on Thu–Fri, which made PortScan and DDoS zero-day (98% of test attacks) — a much
> harder and *misaligned* protocol versus the base paper.

| Script | Purpose | Status |
|---|---|---|
| `cnn3.py` | 1D CNN on the temporal split; source of the `"embedding"` layer name convention | Superseded by `cnn_paper.py`. Focal-loss shape bug fixed here too. |
| `eval.py` | Baseline zero-day metrics + `cnn_zeroday_eval.png` (6 subplots) | Superseded by `metrics.py` |
| `ltn.py` | Behaviour-grounded Hybrid-LTN, adaptive ω | 🔴 Ran, **underperformed** (0.4529 vs 0.6689). Superseded by `ltn_paper.py`. See [implementation/ltn_current.md](implementation/ltn_current.md) |

---

# Utilities

## `scripts/dashboard_server.py`

**Purpose**: Live local ops console — a localhost-only (`127.0.0.1`) stdlib HTTP server that reads
**real** machine state on every poll: CPU/RAM (`psutil`), git branch + uncommitted count, running
training processes matched against known pipeline scripts, the tail of the most recently modified
`outputs/*.log`, and the full `runs.jsonl` history.

```bash
.venv/Scripts/python.exe scripts/dashboard_server.py --port 8787
```

This is what **"open preview"** means — see [DASHBOARD.md](DASHBOARD.md). Never network-exposed;
never published as an Artifact.

## `scripts/visual.py`

**Purpose**: Visualise preprocessing impact — row count, missing values, and duplicate rows before
vs after cleaning. 3-panel bar chart, displayed inline (not saved).

## `scripts/check.py`

**Purpose**: Print feature column names with their indices.

```bash
python scripts/check.py
```

⚠️ **Run this before editing any feature-index logic in `behavior.py`.** The original behaviour
module's indices were badly misaligned (`RATE_FEATURES=[5,6,7]` actually pointed at packet-length
fields), which is why it was rebuilt from scratch.

---

## Removed

**`utils/config.py`** — deleted 2026-06-18 as dead code. A leftover from an abandoned raw-PCAP /
payload pipeline (`PAYLOAD_LEN=1500`, 3 classes, `data/raw_pcaps/`, attack time-windows), imported by
nothing. It is the origin of the "1500 bytes" boxes in the architecture diagram. Centralised config
now lives in [`config.yaml`](../config.yaml) + `scripts/config.py`, which scripts actually import.

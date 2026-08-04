# Scripts Reference

All scripts live in `scripts/`. Run them **from the project root** using the venv interpreter
(`.venv\Scripts\python.exe`), which puts `scripts/` on `sys.path` so `import paths` works.

> Last verified against source: **2026-08-03** (35 Python scripts, plus run_long.sh).

## Map

| Group | Scripts |
|---|---|
| **Infrastructure** | `paths` · `config` · `features` · `tracking` · `metrics` |
| **Current pipeline** (paper split) | `preprocess` → `preprocess_paper` → `cnn_paper` → `baselines` · `novelty` → `behavior` → `ltn_paper` · `cnn_auxhead_paper` · **`autoencoder_paper`** |
| **Analysis / one-off** | `skyline_oracle` · `rescore_logits` · `fusion_beaconlike` · **`modality_analysis`** · **`kg_precheck`** · **`kg_readiness`** · **`audit_leakage`** · **`significance`** · **`bot_failure_analysis`** |
| **Maintenance** | **`repair_runs_log`** (one-shot `runs.jsonl` integrity repair) |
| **Phase-4 gates** | **`kg_precheck`** → **`kg_readiness`** → **`kg_criteria`** · **`timeline`** (timestamp utility) |
| **Legacy** (temporal split, superseded) | `cnn3` · `eval` · `ltn` |
| **Utilities** | `dashboard_server` · `visual` · `check` |

**Multi-seed convention.** Every trainable script takes a `<PREFIX>_SEED` env var and writes
`<name>_s<seed>` artifacts, leaving the config-default (seed 42) filenames untouched:
`CNN_SEED` · `LTN_SEED` · `AE_SEED` · `NOVELTY_SEED` · **`BASELINE_SEED`** (added 2026-08-03).
Given **four** retractions caused by single-seed results, **treat any n=1 number as provisional.**
⚠️ Note `xgboost` in `baselines.py` is **deterministic** — no subsampling is configured, so
`random_state` has nothing to randomise and multi-seeding it produces byte-identical output.

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

**Result** (n=3, seeds 42/43/44): macro zero-day PR-AUC **0.6399** [0.6353, 0.6446] — the reference
every later stage is measured against. ⚠️ The single figure **0.6446 is seed 42 only** and appears
throughout older entries; quote the n=3 mean and range instead. Multi-seed with
`CNN_SEED=43 python scripts/cnn_paper.py` (writes `cnn_paper_s43*`, never touches seed-42 artifacts).

## `scripts/baselines.py`

**Purpose**: Classical + anomaly baselines, so "why not XGBoost / Isolation Forest?" is answered
with numbers rather than assertion.

✅ **All three re-run at n=3 on the current metric schema, 2026-08-03** (`BASELINE_SEED=42/43/44`),
closing the long-standing "n=1 + old schema → not citable" gap.

- **XGBoost** — supervised binary (benign vs known attack), the tabular SOTA → macro **0.6372**.
  ⚠️ **Deterministic**: no subsampling is configured (`subsample`/`colsample_*` default to 1.0) and
  `tree_method="hist"` is deterministic, so `random_state` has nothing to randomise — seeds 42/43/44
  give **byte-identical** output. Treat as n=1 with verified reproducibility; its training variance
  is *unmeasured*, not zero.
- **RandomForest** — supervised binary → macro **0.5995** [0.5682, 0.6235], **Bot 0.1311**
  [0.0576, 0.1933]. 🔴 **This result falsified the strong form of the (A)/(B) thesis reframing**: RF
  is an (A)-family method yet **ties the autoencoder on Bot** (0.1314, paired bootstrap p=0.88)
  while beating it 0.50 on macro. ⚠️ Its Bot range is the widest in the project (3.4× spread) and
  its cross-seed Bot rank correlation is 0.068 — i.e. **noise**, same as the CNN. Never quote the
  mean without the range; do not write "RF solves Bot."
- **IsolationForest** — **unsupervised**, fit on benign only (zero-day-legitimate) → macro **0.0653**
  [0.0628, 0.0683], Bot 0.0637 (1.9×) — still roughly the CNN's Bot level despite never seeing a
  single attack.

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

## `scripts/autoencoder_paper.py`

**Purpose**: **Canonical Phase 3 — the anomaly pillar.** A benign-only reconstruction-error detector,
and the project's only (B)-family channel that is trained rather than derived.

Dense (not Conv1D) autoencoder, 68→48→32→16→32→48→68, trained **and model-selected on benign rows
only** — no attack label is used anywhere, including in early stopping, which is what makes it
zero-day-legitimate by construction. Scored by per-row reconstruction MSE (high = anomalous).
Scaler is fit on all of train, matching `baselines.py`'s convention so the channel is directly
comparable to IsolationForest.

**Config**: `AE_SEED` · `AE_EPOCHS` (50) · `AE_SUBSET` (0 = full) · `AE_TAG`.
**Smoke test**: `AE_SUBSET=50000 AE_EPOCHS=3 python scripts/autoencoder_paper.py`
**Multi-seed**: `AE_SEED=43 python scripts/autoencoder_paper.py` → `autoencoder_paper_s43*`.

**Result** (n=3): macro **0.0970** [0.0894, 0.1014] — far below the CNN — but **Bot 3.8×
[3.2–4.8], the most reliable Bot channel measured**, plus near-perfect recall on Heartbleed (1.0000)
and Infiltration (0.8611). It fails on web attacks (0.1048 / 0.0547 vs the CNN's 0.9226 / 0.9524).
CNN and AE seed ranges **do not overlap on any family** — a **double dissociation**. The mechanism is
unexplained: a proposed "modality analogue" account was pre-registered, tested, and falsified.

---

# Analysis / one-off

## `scripts/modality_analysis.py`

**Purpose**: Test the proposed "modality analogue" explanation for the CNN-vs-autoencoder double
dissociation — *does a zero-day family's similarity to some known class predict which method wins?*

All four predictions are written into the script **before** it runs, with three explicit guards
against circularity: every measurement is repeated in **raw feature space** (untrained by any model),
the **named** nearest known class is reported (a falsifiable prediction), and tests are **per-flow**
rather than across only 6 families. Measures tied-covariance Mahalanobis distances to known-class
centroids: `d_benign`, `d_attack`, and `margin = d_benign − d_attack`.

**Result: the account was largely falsified, and the guards are what caught it.** The named mechanism
was wrong (web attacks sit nearest **DoS Hulk**, not Patator); the direction was backwards (**Bot is
closer to benign than the web attacks are**); and the strongest supporting correlation (+0.933) was
**circular** — measured in the CNN's own embedding space, where it merely restates the CNN's
log-odds; in raw space it is −0.388. One prediction survived: the AE **is** a raw-space
distance-from-benign detector (`corr = +0.732`). Writes `outputs/metadata/modality_analysis.json`.

## `scripts/kg_precheck.py`

**Purpose**: **Phase-4 viability test — run before writing any KG code.** The KG spec treats a dense
cluster with weak links to known attack types as its zero-day mechanism; this asks whether zero-day
families actually form usable clusters in the representation the KG would be built on.

**Part 1** varies the **CNN seed** (the embedding itself); **Part 2** varies only the **clustering**
seed, for contrast. That distinction is the whole point — the original version varied only the
clustering seed and reported "stable across 2 seeds", which measured k-means stability, not the
stability of the representation.

**Result: this is the current Phase-4 blocker.** Bot cluster purity across CNN seeds is
**87.9% / 86.6% / 44.4%** at k=200 (43.4 pp spread) versus 2.6 pp when only the clustering seed
moves. The instability is **specific to Bot** — web families move 0.7–2.5 pp — and is independently
confirmed by Mahalanobis (seed 44 at chance) even though classification is flat across seeds.

**Writes** `outputs/metadata/kg_precheck.json` (added 2026-08-03 — before that it persisted
**nothing**, so the numbers blocking all of Phase 4 existed only as prose in STATUS.md). Re-run
2026-08-03: reproduces exactly.

⚠️ **Read alongside `bot_failure_analysis.py`**, which explains *why* this instability exists: the
CNN's Bot ranking is noise (cross-seed ρ = −0.090), so clustering it is clustering noise.

## `scripts/kg_readiness.py`

**Purpose**: the two measurements that **gate Phase 4**. Run after `kg_precheck.py`, before writing
any KG code. Four predictions pre-registered in the script.

**Part A — which representation should the KG cluster?**

| representation | Bot purity across seeds (k=200) | spread |
|---|---|---:|
| CNN embedding 64-d | 87.9 / 86.6 / 44.4 % | 43.4 pp |
| AE bottleneck 16-d | 82.0 / 74.1 / 29.9 % | **52.1 pp** |
| **Raw features 68-d** | **77.6 %** (80.6 % at k=400) | **no training lottery** |

✅ **Raw features win.** 🔴 **The AE bottleneck was the standing recommendation and was rejected by
this measurement** — its reproducible Bot *ranking* (ρ=0.827) did not transfer to cluster stability.
**Rank stability ≠ cluster stability.**

**Part B — does "unexplained cluster" discriminate anything?** 🚨 **No.** Lift over the base rate is
**≤ 1.00× across 3 representations × 3 thresholds** — at or below chance, i.e. anti-correlated.
118 of 200 clusters contain zero known-attack training flows, so the criterion flags ~59,000 of
~59,400 benign+zero-day test flows. **The KG's specified zero-day mechanism does not work**, which
resolves the spec's scope contradiction empirically: corroboration + explainability, not primary
detection. The spec's other two criteria (growth rate, behaviour co-occurrence) remain **untested**.

Part B deliberately uses **train labels only** for the criterion and test labels only for scoring —
an honest simulation of the real mechanism, unlike Part A's oracle-style purity upper bound.

**Writes** `outputs/metadata/kg_readiness.json`, and caches
`outputs/embeddings/X_{train,test}_ae_bottleneck{,_s43,_s44}.npy`.

## `scripts/timeline.py`

**Purpose**: correct CIC-IDS2017 timestamp reconstruction. ⚠️ **Use this for any temporal work —
never parse `meta_*.csv` timestamps directly.**

Naive `pd.to_datetime` is **silently wrong twice**: (1) dates are **D/M/YYYY**, so default parsing
turns "3/7/2017" into March 7 and scatters a 5-day capture across three months; (2) the clock is
**12-hour with no AM/PM** — observed hours are exactly {1..5, 8..12}, which map onto an 08:00–17:00
workday, so without correction 1 PM sorts *before* 9 AM and any ordering/growth/decay is meaningless.

The reconstruction is **validated against the published capture schedule**, not fitted: Web BF
Thu 09:15–10:00 · XSS Thu 10:15–10:35 · Bot Fri 09:34–12:59 · PortScan Fri 13:06–15:23 · DDoS
Fri 15:56–16:16. `parse()` raises rather than guessing if the date/hour pattern doesn't match.

**Severity is total, not subtle:** measured, **all 114,658 test rows change position** between naive
and corrected chronological order, and naive parsing additionally emits `NaT`.

`preprocess_paper.py` now emits `timestamp_{train,val,test}.npy` (datetime64[s]) so consumers get the
corrected value **by default**. `load_timestamps()` prefers that artifact and falls back to correct
parsing. `parse()` **raises rather than guessing** if the date/hour pattern is unexpected.

API: `load_timestamps(split)` → row-aligned `pd.Series` · `time_order(split)` → chronological index ·
`write_corrected(split)` · `selftest(split)` → validates against the published schedule, raises on
mismatch. Regenerate artifacts: `python scripts/timeline.py --backfill`.

## `scripts/kg_criteria.py`

**Purpose**: the **last Phase-4 gate** — do the KG's other two emerging-pattern criteria work, now
that "unexplained cluster" is measured dead? Three predictions pre-registered.

| criterion | result | status |
|---|---|---|
| **#1 Growth / burstiness** | **lift 5.94× [5.66, 6.11] (n=3), ~81 % recall** | ✅ **works — robust** |
| #2 Unexplained cluster *(from `kg_readiness`)* | ≤ 1.00× | 🔴 dead |
| #3 Behaviour co-occurrence | 2.81× at 1.5 % recall; cluster-level ≤ 1.35× | ⚠️ weak |
| #1 ∧ #3 | lift 1.73–11.57×, precision 0.12–0.81 | 🔴 not established |

🔴 **The conjunction's seed-42 result (11.57× lift, 81.4 % precision) is a single-seed artifact** —
the script's own multi-seed section demotes it. **Fifth such trap in this project, first one caught
before publication.** Do not cite it.

⚠️ **External-validity caveat:** growth works substantially because CIC-IDS2017's attacks are
scripted into fixed windows. A real network with continuous low-rate C2 would not produce it.

Both criteria are computed **without labels** — growth from cluster ids + timestamps, co-occurrence
calibrated on benign training flows only. Labels score the result, never define it.
**Writes** `outputs/metadata/kg_criteria.json`.

## `scripts/repair_runs_log.py`

**Purpose**: one-shot, auditable repair of `runs.jsonl`. **Dry-run by default**; `--apply` to write.

Fixes wrong seeds (re-derived from each tag's `_s<N>` suffix), removes **exact** duplicates, and
stamps every row with a schema version. Safe to run now — and deliberately *not* run before
2026-08-03 — because `runs.jsonl` is version-controlled, so git supplies the audit trail the
append-only rule was protecting.

⚠️ **Only exact duplicates are removed** (identical name, params *and* every metric). Eight
duplicated names are preserved because their content genuinely differs — six old/new metric-schema
pairs plus `ltn_repro` and `ltn_v2`, which are distinct training runs with identical configs. The
script asserts no run name disappears and refuses to write if one would.

## `scripts/significance.py`

**Purpose**: paired significance tests on per-flow scores — the `conference_roadmap` Tier-S #2
requirement, and the thing C2 was left waiting on.

**Method**: stratified **paired bootstrap** over test flows (B=2000). Benign and the family are
resampled *separately, preserving counts*, so the family's chance PR-AUC is held fixed and PR-AUC
moves only with ranking quality. Both channels are scored on the same resampled indices (that is
what makes it paired). Multi-seed channels collapse to their mean-over-seeds inside each replicate.

**Key verdicts (2026-08-03)**: CNN **does** beat the LTN control (+0.0204, p=0.001) despite
overlapping seed ranges · the CNN/AE double dissociation is significant on all three families
(p<0.0005) · **RandomForest ties the autoencoder on Bot (p=0.88)** · **"CNN beats XGBoost on macro"
is n.s. (p=0.80), reversing a 2026-07-27 retraction.**

⚠️ **Estimand caveat, and it matters**: this quantifies *flow*-sampling uncertainty, treating the 3
seeds as fixed. It does **not** convert n=3 into seed-level power — at n=3 the Wilcoxon signed-rank
floor is p=0.25, so no seed-level claim in this project can reach p<0.05. Needs n≥6.

**Writes** `outputs/metadata/significance.json`.

## `scripts/bot_failure_analysis.py`

**Purpose**: answer the project's last open research question — *why* does the CNN sit at chance on
Bot when the skyline oracle proved the signal is fully present in the 68 features?

**Four hypotheses were written into the script before it was run** (the pre-registration discipline
adopted after the modality-analogue failure). Verdicts: **H1 absorption CONFIRMED** · **H3 feature
neglect CONFIRMED** · **H2b rank instability CONFIRMED** · H2a boundary-adjacency REFUTED (Bot is
benign-*interior*, not boundary-adjacent) · H4 raw-overlap REFUTED as predicted.

**Answer — the failure is representational, not informational**: 100% of Bot flows are classified
BENIGN across all 3 seeds (mean p(BENIGN)=0.9984); the features separating Bot from benign have
**0/8 overlap** with those the known-class task needs; so the residual Bot ranking is **noise**
(cross-seed ρ = **−0.090** vs 0.68–0.83 for other families). The autoencoder ranks Bot *reproducibly*
(ρ=0.827) — which is what makes its bottleneck the data-backed choice for the Phase-4 KG.

Also measured: **web attacks transfer by absorption into `DoS slowloris`** (~90% modal class), i.e.
misclassification landing on the right side of the binary, not detection.

**Anti-circularity**: feature-space claims are measured in **raw** space, never in the CNN's own
embedding — the project was previously burned by a +0.933 correlation that became −0.388 in raw space.

**Writes** `outputs/metadata/bot_failure_analysis.json`. Requires TF (loads all 3 CNN seeds).

## `scripts/audit_leakage.py`

**Purpose**: Measure exact-duplicate overlap between the paper split's train and test sets, per class.
CIC-IDS2017 is duplicate-heavy, `preprocess.py` deliberately keeps duplicates, and the paper split is
**stratified random** — so identical feature vectors can land on both sides. A documented criticism of
this dataset (Engelen et al. 2021) that a reviewer will check.

**Result**: **19,513 / 114,658 test rows (17.0%)** have an exact feature-vector twin in train —
PortScan **58.3%**, SSH-Patator **48.6%**, DoS Hulk 25.3%, BENIGN 6.9%. **All six zero-day classes
measure 0.0%** (test-only by construction), so the macro zero-day headline is unaffected; what is
contaminated is the ~0.98 overall binary PR-AUC. Seed-independent — a property of the split.

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

# Scripts Reference

All scripts live in `scripts/`. Run them **from the project root** using the venv interpreter
(`.venv\Scripts\python.exe`), which puts `scripts/` on `sys.path` so `import paths` works.

> Last verified against source: **2026-08-10** (53 Python scripts, plus 8 shell launchers).

> 🔴 **Nine scripts were undocumented here until 2026-08-05** (32 covered, of the 41 then on
> disk) — the entire Phase-4 / fusion /
> explainability toolchain (`kg` · `kg_visualize` · `explain` · `fusion_kg` · `fusion_multi` ·
> `comparability` · `robustness` · `significance_seed` · `lint_conventions`) was missing while the
> header still claimed it was verified. The `script-count` lint **passed** throughout, because its
> regex `(\d+) scripts` required the number to sit directly against the word, and the phrasing here
> put a qualifier between them (*"…&#32;Python scripts"*), so the check never fired. Both were fixed:
> the regex now tolerates a qualifier, and a new **`undocumented-scripts`** check verifies
> *membership* rather than arithmetic — a count can be right while the file is still incomplete.

## Map

| Group | Scripts |
|---|---|
| **Infrastructure** | `paths` · `config` · `features` · `tracking` · `metrics` |
| **Current pipeline** (paper split) | `preprocess` → `preprocess_paper` → `cnn_paper` → `baselines` · `novelty` → `behavior` → `ltn_paper` · `cnn_auxhead_paper` · **`autoencoder_paper`** |
| **Analysis / one-off** | `skyline_oracle` · `rescore_logits` · `fusion_beaconlike` · **`modality_analysis`** · **`kg_precheck`** · **`kg_readiness`** · **`audit_leakage`** · **`significance`** · **`bot_failure_analysis`** · **`comparability`** · **`robustness`** |
| **Maintenance** | **`repair_runs_log`** (one-shot `runs.jsonl` integrity repair) · **`lint_conventions`** (run at the end of every session) |
| **Phase-4 gates** | **`kg_precheck`** → **`kg_readiness`** → **`kg_criteria`** · **`timeline`** (timestamp utility) |
| **Phase 4 — build** | **`kg`** → **`kg_visualize`** · **`explain`** |
| **Phase 5 — fusion + rigor** | **`fusion_kg`** · **`fusion_multi`** · `significance` · **`significance_seed`** |
| **Phase 7.5 — operational readiness** | **`operational`** (Tier 1, gates Phase R) · **`determinism`** (Tier 2 — imported by trainable scripts) · **`ablation`** |
| **Tier B — deep architectures** | **`deep_zoo`** (LSTM · GRU · CNN-LSTM · Transformer) |
| **Tier D — protocol variance** | **`protocol_variance`** (k-fold + SWA) |
| **Tier C — benign-only anomaly** | **`anomaly_zoo`** (VAE · Deep SVDD · OC-SVM · LOF) |
| **Tier A — classic baselines** | **`baselines_classic`** (DT · kNN · NB · LogReg · SVM · MLP) |
| **Open-set / OOD** | **`ood_scores`** (post-hoc battery on the CNN) · `novelty` (MSP, Mahalanobis) |
| **Literature comparability** | **`paper_metrics`** (base-paper Table II + the field's suite) · `comparability` |
| **Legacy** (temporal split, superseded) | `cnn3` · `eval` · `ltn` |
| **Utilities** | `dashboard_server` · `visual` · `check` |
| **Shell launchers** (not Python) | `run_long.sh` (**use this for any job >10–15 min**) · `seed_sweep.sh` · `noise_floor.sh` · `rigor_n6.sh` · `ltn_ctrl_sweep.sh` · `verify_determinism.sh` |

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

## `scripts/deep_zoo.py`

**Purpose**: **Tier B** — LSTM, GRU, CNN-LSTM and a Transformer encoder. Run last (each needs a full
training pass) and predicted to teach least, but closes the guaranteed *"why didn't you try an
LSTM?"* question with a measurement. `DEEP_ARCH=lstm` runs one architecture.

| model | MACRO zd | Bot | Web BF | XSS | FIELD binary | min |
|---|---:|---:|---:|---:|---:|---:|
| **deep_cnn_lstm** | **0.6219** | 0.0206 | 0.9079 | 0.9372 | 0.9854 | 25.4 |
| deep_lstm | 0.3633 | 0.0501 | 0.5875 | 0.4524 | 0.9914 | 94.3 |
| deep_gru | 0.3029 | 0.0626 | 0.5071 | 0.3390 | 0.9932 | 44.9 |
| **deep_transformer** | **0.1106** | 0.0609 | 0.1818 | 0.0892 | 0.9894 | 57.9 |

✅ **Only the convolutional front-end matters.** CNN-LSTM sits **0.0031** from the CNN
(indistinguishable); pure recurrence halves the score. Adding an LSTM on top of a conv stack neither
helps nor hurts; replacing the stack with recurrence is destructive.

**B1 CONFIRMED** (nothing escapes the top tier upward) · **B2 CONFIRMED** (nothing touches Bot; best
0.0626 vs the KG's 0.3103).

🔴 **B3 FALSIFIED — the tier's most confident prediction.** The Transformer was predicted to be
*best*, since self-attention is permutation-equivariant and is the only bias here matching unordered
tabular features. **It came last (0.1106).** ⚠️ Read as *"an untuned Transformer at a 30-epoch
budget"*, **not** "attention is unsuited to this task" — flat Adam 1e-3, d=32, 2 blocks, 4 heads, no
warmup, mean-pooled tokens. A negative result about one under-tuned configuration is not one about
the architecture class.

⚠️ **Two tier-wide caveats.** (1) The recurrent models run over the **feature axis, not time** — 68
unordered statistics, not 68 timesteps. This matches what published "LSTM on CIC-IDS2017" work does,
so it is the right comparison to report, but it is **not evidence about sequence modelling for
intrusion detection**. (2) **Budgets are not matched**: `deep_lstm` ran all 30 epochs without early
stopping (budget-limited) while `cnn_paper` gets 50; the others early-stopped.

📊 **The field's metric hides the entire tier**: FIELD binary spans 0.9854–0.9932, and the *worst*
zero-day model posts 0.9894 while `deep_gru` (macro 0.3029) posts the tier's *highest* at 0.9932.

## `scripts/protocol_variance.py`

**Purpose**: **Tier D** — Phase 7.5 Tier 2 #6 (k-fold CV) and #7 (SWA). Measures **data-split
variance**, which nothing else in this project separates from seed variance.

**Design constraint**: the **test set is fixed and never re-partitioned** — zero-day families are
test-only, so folding them into training destroys the protocol. The 5-fold runs over the
**train+val pool only**, every fold scored against the same untouched test set. ⚠️ This is *not* the
k-fold NIDS papers usually report, which rotates the test set and thereby measures known-class
performance.

| fold | 1 | 2 | 3 | 4 | 5 |
|---|---:|---:|---:|---:|---:|
| macro | 0.6218 | 0.6054 | 0.6384 | 0.6284 | **0.5802** |

**mean 0.6148 · SD 0.0228 · spread 0.0582**

🔴 **Data-split SD (0.0228) and training SD (0.0222) are the SAME SIZE — 1.03×.** D1 technically
confirms, but **do not report it as "data variance is larger"**; it is a dead heat, and the finding
is that a *second* unmeasured uncertainty source exists at the same magnitude as the one that
retracted C2. Comparisons on a shared split still cancel it (threshold ~0.0256 stands); **an absolute
number carries √(0.0228² + 0.0222²) ≈ 0.032.** Fold 5 (0.5802) falls **below the CNN's entire n=6
range**.

✅ **D2 — SWA does nothing** (0.6218 → 0.6217). It flattens the solution w.r.t. the *known-class* loss
it averages over, which is not what zero-day performance measures.

⬜ **Cross-dataset (Phase 6) BLOCKED** — CIC-IDS2018 is not present locally. Recorded in the JSON
rather than silently skipped.

⚠️ **The model is `cnn_paper.py`'s replicated VERBATIM** (3 conv+BN blocks, Flatten, L2 dense, focal
loss with the `reshape([-1])` fix, **no `class_weight`**), and must be kept in sync — `cnn_paper.py`
cannot be imported because importing it runs a training. The first version used a loosely CNN-like
model and reported **0.3244**, an architecture-and-loss gap masquerading as data variance.

## `scripts/anomaly_zoo.py`

**Purpose**: **Tier C** — VAE, Deep SVDD, One-Class SVM (SGD) and LOF, all trained on **benign only**,
so zero-day-legitimate by construction. This is the tier the evidence said could move Bot, since the
channels that touch Bot all model normality rather than a decision boundary.

| model | MACRO | Bot | lift | Web BF | XSS |
|---|---:|---:|---:|---:|---:|
| **deep_svdd** | 0.1393 | **0.1558** | **4.56×** | 0.1656 | 0.0964 |
| **lof** | **0.3368** | 0.0380 | 1.11× | **0.5592** | **0.4131** |
| vae | 0.0444 | 0.0742 | 2.17× | 0.0422 | 0.0169 |
| ocsvm_sgd | 0.0275 | 0.0213 | 0.62× | 0.0422 | 0.0191 |

🔴 **C1 reads CONFIRMED in the output — do not cite it that way.** Deep SVDD's Bot **0.1558 sits
inside the autoencoder's own n=3 range [0.1078, 0.1647]**, so at n=1 it is not an established
improvement. ~~**Multi-seed with `ANOM_SEED=43/44` first.**~~

> ✅ **RESOLVED 2026-08-10 — multi-seeded, and C1 does NOT survive** (`seed_recheck.py`).
> Deep SVDD Bot across seeds: **0.1558 (s42) · 0.1275 (s43) · 0.1950 (s44)** — mean 0.1594 ±0.0339
> against the autoencoder's **0.1291 ±0.0199 (n=6)**. Delta **+0.0304**, ranges **overlap**,
> Welch **t=1.43, p=0.256** → **NOT ESTABLISHED.**
> 🔴 **The verdict the script prints flips with the seed: CONFIRMED / FALSIFIED / CONFIRMED.**
> That is the cleanest demonstration in this project that an n=1 pre-registered verdict is a
> coin-flip, not a result. The flag written here on 2026-08-05 was correct.
> ⚠️ **Deep SVDD's macro is also unstable** — 0.1393 / 0.0743 / 0.1320, spread **0.0650**, twice
> the ~0.032 an absolute number already carries. The published 0.1393 is the top of its range.

🔴 **C2 FALSIFIED, and that is the real finding.** LOF reaches macro **0.3368** (Web BF 0.5592, XSS
0.4131) — a benign-only method that does *not* collapse on web attacks, landing where **Mahalanobis**
does (0.3777). Both are density/distance methods; the AE scores by reconstruction. **So
"benign-only ⇒ collapses on web attacks" is a property of reconstruction-error scoring, not of the
(B) family.** A real correction to how this project has described that family.

✅ **C3 — Deep SVDD did not collapse** (score SD 3.20×10⁻²). Guarded with no bias terms and no
bounded activations, and checked explicitly rather than assumed.

⚠️ **Deviations**: LOF fitted on a 50,000-row benign subsample (of ~442k — it stores its training set
and does not finish at full size); One-Class SVM uses the SGD linear approximation (exact kernel
OC-SVM is O(n²)).

## `scripts/baselines_classic.py`

**Purpose**: **Tier A** — the classic baselines every NIDS comparison table carries and this project
had never run: **Decision Tree, k-NN, Naive Bayes, Logistic Regression, linear SVM, RBF-SVM
(Nystroem), MLP**. Same protocol as `baselines.py`. `BASELINE_SEED` supported.

| model | MACRO zd | Bot | Web BF | XSS | **FIELD binary** | ties |
|---|---:|---:|---:|---:|---:|---:|
| decision_tree | 0.6049 | 0.0342 | 0.8467 | 0.9339 | 0.9807 | **0.501 ⚠️** |
| mlp | **0.5360** | 0.0219 | 0.8237 | 0.7622 | 0.9854 | 0.020 |
| knn (k=5) | 0.4270 | 0.0342 | 0.6786 | 0.5682 | 0.9804 | **0.498 ⚠️** |
| naive_bayes | 0.1264 | 0.0415 | 0.2067 | 0.1310 | 0.8468 | 0.331 ⚠️ |
| rbf_svm (Nystroem) | 0.0870 | 0.0197 | 0.1671 | 0.0743 | 0.9821 | 0.001 |
| logistic_regression | 0.0380 | 0.0234 | 0.0630 | 0.0275 | **0.9769** | 0.008 |
| linear_svm | 0.0374 | 0.0312 | 0.0570 | 0.0241 | 0.9802 | 0.008 |

🔴 **The two columns tell opposite stories, and that is the point.** On the field's binary metric all
seven score **0.977–0.985** against the CNN's 0.9928; on macro zero-day they span **0.0374 → 0.6049**.
Logistic regression looks 98 % as good as the CNN on the published metric and is **17× worse** on
zero-day.

⚠️ **The two that look competitive are score-degenerate.** `decision_tree` is nominally
indistinguishable from the CNN (gap 0.0201 < 0.0256) but **50.1 % of test rows share one score**;
k-NN is 49.8 % tied. **PR-AUC over a half-tied ranking is not comparable to a continuous scorer's.**
The best *valid* result is the **MLP at 0.5360**, which is genuinely below the CNN.

**Predictions**: T1 ✅ · T2 ✅ · **T3 🔴 FALSIFIED** — k-NN was predicted to be the best Tier-A method
on Bot (the only instance-based one, operating on the same raw-feature substrate as the KG); it was
not (0.0342 vs naive_bayes 0.0415).

⚠️ **Deviations**: k-NN on a stratified 50,000-row subsample; RBF-SVM via Nystroem(300) + linear SGD
(exact kernel SVM is O(n²), not runnable at 883k rows). Both printed in the output and stored in
`runs.jsonl` params.

> 🔴 **MULTI-SEEDED 2026-08-10 (`seed_recheck.py`) — the table above is seed 42 only, and two rows
> are not citable.**
>
> | model | s42 (published) | s43 | s44 | spread |
> |---|---:|---:|---:|---:|
> | **knn (k=5)** | **0.4270** | 0.4037 | **0.0440** | **0.3830** |
> | **mlp** | **0.5360** | 0.4686 | 0.4849 | **0.0673** |
> | decision_tree | 0.6049 | 0.6064 | 0.6100 | 0.0051 |
> | naive_bayes / logistic_regression / linear_svm | — | *identical* | *identical* | **0.0000** |
>
> 🔴 **k-NN's macro collapses 10× at seed 44** (0.4270 → 0.0440; Web BF 0.6786 → 0.0805, XSS
> 0.5682 → 0.0173). **The only thing the seed changes for k-NN is which 50,000 rows it memorises** —
> the deviation noted above as "stated not hidden" turns out to dominate the result. **The published
> 0.4270 is the top of a range spanning an order of magnitude.**
>
> ⚠️ **The MLP was called "the best *valid* Tier-A result" at 0.5360. Its 3-seed mean is 0.4965**,
> which widens the gap to the CNN rather than narrowing it — the conclusion survives, the number does
> not. **For all three unstable models seed 42 happened to be the highest draw** (p≈0.04 under a
> uniform null, but these three were *selected* for being unstable, so read it as an observation, not
> an established bias).
>
> ✅ **T2 CONFIRMED at n=3, and T3's falsification holds** — `naive_bayes` wins Bot at all three seeds
> (0.0415, constant). But see `seed_recheck.py` below: **that ranking is reproducible and
> meaningless.**

⚠️ **Scores are saved float64.** The first version cast to float32, which collapsed GaussianNB's
underflowing probabilities into ties and moved its reloaded macro **0.1264 → 0.0597** — the saved
array no longer reproduced the logged metric. Same float32-precision class as the 2026-07-27
saturation bug.

## `scripts/seed_recheck.py`

**Purpose**: Settle the two **n=1 results that were flagged before publication** on 2026-08-05
(Tier C's C1, and Tier A's whole Bot column). Reads `runs.jsonl` — the version-controlled record, not
the logs — so every number it prints is reproducible from the committed repo. No training, no
scoring; pure aggregation. Writes `outputs/metadata/seed_recheck.json`.

**Why the comparison is at the SEED level, not the flow level.** A flow-level paired bootstrap
answers *"would this hold on different traffic"*; the question here is *"would this hold if we
retrained"*. Getting that backwards is what retracted C2.

**R1 — Deep SVDD vs the autoencoder on Bot: 🔴 NOT ESTABLISHED.** +0.0304 of means, ranges overlap,
Welch t=1.43 **p=0.256**. The per-seed verdict **flips CONFIRMED / FALSIFIED / CONFIRMED**.

**R2 — the Tier-A Bot column: REPRODUCIBLE (ρ = +0.770) but NOT INFORMATIVE.** This is the result
that needed the most care, because the headline correlation is *misleading in the optimistic
direction*:

- **5 of 7 models have Bot SD exactly 0.0000** — GaussianNB, LogisticRegression and
  LinearSVC(dual=False) have **no stochastic component at all**, so `BASELINE_SEED` changes nothing
  about them. Their contribution to a cross-seed correlation is trivially perfect.
- **2 of 7 are pinned at exactly the chance value 0.0342** (decision tree, k-NN) because their tied
  score blocks swallow every Bot flow. Perfectly reproducible, perfectly uninformative.
- **Bot lift across the whole tier is 0.64×–1.21×.**

So the ranking is stable *and* meaningless — it orders models by noise that happens to be
deterministic. ⚠️ **This is a partial correction to how the issue was originally framed.**
KNOWN_ISSUES predicted the column would be *noise-dominated* like the CNN's (ρ = −0.090); it is the
opposite, ρ = +0.770. **The conclusion — do not cite a Bot number from Tier A — is unchanged, but the
reason is not the predicted one.** The verdict logic reports reproducibility and informativeness
**separately** for exactly this reason; collapsing them to one boolean is what would have produced a
false "stable" headline (the `robustness.py` lesson applied to a new script).

**R3 — which macro numbers are safe to quote**: flags any model whose seed spread exceeds the
**~0.032** an absolute number already carries (√(0.0228² + 0.0222²), data split + training). Three
fail: **knn_k5 (0.3830)**, **deep_svdd (0.0650)**, **mlp (0.0673)**.

```bash
python scripts/seed_recheck.py
```

## `scripts/noise_postdet.py` + `scripts/noise_postdet.sh`

**Purpose**: Decompose the project's uncertainty into its actual sources. The ~0.0256
"indistinguishable" threshold — which retracted C2 and demotes every within-tier comparison — rests on
the noise floor **SD 0.0222**, and that floor was measured as **six runs of seed 42 with determinism
OFF**. It is therefore *thread-scheduling nondeterminism at a fixed seed*, and the project has been
using it as a proxy for *seed-to-seed variance*. `determinism.enable()` separates them for the first
time.

| population | varies | measures |
|---|---|---|
| **A** pre-flag, seed FIXED (n=6) | run order | nondeterminism only |
| **B** pre-flag, seed VARIES (n=6) | seed + run order | both |
| **C** post-flag, seed VARIES (n=6) | seed only | **seed alone** |

⚠️ **Population A was identified by verification, not assumption** — the six runs
(`cnn_paper_logodds`, `cnn_noise_r1–r4`, `cnn_repro_s42`) reproduce the documented **SD 0.0222 and
spread 0.0622 exactly**.

**Only 3 trainings are needed** (`noise_postdet.sh 45|46|47`): seeds 42/43/44 post-flag already exist
as C4's log1p arm, which is `cnn_paper.py` verbatim at the config-default transform — verified by
`c4_log1p_s42` == `det_verify_a` to twelve decimals.

**Pre-registered predictions** (committed before seeds 45–47 finished — see git history): **P1**
post-flag seed SD < 0.010 · **P2** the withdrawn "session effect" will not reproduce · **P3**
√(A² + C²) ≈ B.

🔴 **This cannot reopen C2, and the script says so in its own output.** C2's +0.0204 is **pre-flag on
both sides**; applying a post-flag threshold to pre-flag numbers is the mixing error that
manufactured the 2026-08-03 "C2 collapse". Reopening it requires a post-flag LTN-control sweep.
⚠️ **The data-split SD (0.0228) is unaffected** — determinism tightened *comparisons on a shared
split*, and did nothing for the uncertainty on a single quoted number.

## `scripts/field_gap.py`

**Purpose**: The **write-up's opening argument**, computed once over **every method the project has
measured (n=40)** instead of separately in four tier sections. Reads `runs.jsonl`; no training.
Writes `outputs/metadata/field_gap.json` and `outputs/figures/field_gap.png`.

**Excluded, and why**: replicates of `cnn_paper`'s model (`cnn_kfold*`, `cnn_noise_r*`,
`det_verify_*`, `cnn_repro_*`) would over-weight one method in a cross-method correlation.
**`xgboost_oracle` is excluded on separate grounds** — it trains on ~1,000 zero-day labels, so it is
an upper bound, not a method runnable under this protocol, and as a single extreme high-high point
(FIELD 1.0000 / MACRO 0.9899) it inflates any correlation containing it. Tie-degenerate scorers are
**flagged, not dropped**; the correlation is reported both ways.

### 🔴 Two strong forms of the argument are REFUTED here — do not write either

| tempting claim | verdict |
|---|---|
| "the published metric carries **no information** about zero-day detection" | 🔴 **FALSE** — Spearman ρ = **+0.568** (p=0.0001); still +0.41 restricted to the field's own ≥0.98 regime. It is a real, if weak, proxy. |
| "its whole spread is **below its own noise**" | 🔴 **FALSE** — the field metric is *precise*: median run-to-run SD **0.0020**, an order of magnitude below its spread. |

### ✅ What the data does support — a RESOLUTION failure, which is enough

**67 of 204 method pairs (33 %) are indistinguishable on the metric the literature publishes
(< 0.0058 apart, ≈2 SD of a difference) while differing ≥2× on macro zero-day PR-AUC.**

Worst case: **`deep_cnn_lstm` vs `ltn_anat_w2p0` — 0.0028 apart on the published metric, 18× apart on
zero-day.** Also `fusion_cnn_kg` vs `deep_transformer`: **0.0006 apart, 6× apart**.

**The published number ranks methods roughly right and cannot resolve the differences that decide
whether a novel attack is caught** — and the field reports it to 3 decimals with no error bar, which
presents that as precision.

```bash
python scripts/field_gap.py
```

## `scripts/c4_transform_ab.sh`

**Purpose**: Runs the **log1p-vs-raw feature-transform A/B on macro zero-day PR-AUC** — the C4 issue.
`config.yaml` justifies `feature_transform: log1p` with *"0.980 vs 0.965 PR-AUC"*, which is the
**overall binary** metric: inflated by the 17 % train/test duplicate overlap, and the one `metrics.py`
forbids as an optimisation target. 3 seeds per arm, 50 epochs, determinism on.

Uses explicit `c4_<arm>_s<seed>` tags. **`cnn_paper.py`'s default tag for seed 43 is `cnn_paper_s43`,
which already exists from the pre-determinism-flag era** — reusing it would put two populations under
one run name, the defect that cost three wrong-model rows on 2026-08-05.

Driven by the `FEATURE_TRANSFORM` env override added to `cnn_paper.py`, rather than by editing
`config.yaml`, so the arms stay isolated: a config edit would silently switch every other script's arm
too. The tag carries a transform suffix for the same reason it already carries a seed suffix —
without it, `FEATURE_TRANSFORM=raw` at the default seed would overwrite `cnn_paper.keras` and its
fusion channel.

```bash
scripts/c4_transform_ab.sh raw      # -> outputs/c4_raw.log
scripts/c4_transform_ab.sh log1p    # -> outputs/c4_log1p.log
```

## `scripts/ood_scores.py`

**Purpose**: The open-set / OOD scoring functions this project had **not** tried — **max-logit**,
**energy** (Liu et al. 2020, T ∈ {1,10,100,1000}), **entropy**, **ODIN** (Liang et al. 2018,
temperature + input perturbation), **logit margin** — all **post-hoc on the trained CNN, no
retraining**. Closes the most predictable reviewer question for a zero-day paper, which until now
had the honest answer *"we tried two."*

⚠️ **Nothing is tuned.** ODIN's ε and the temperatures are normally selected on held-out OOD data;
here that would be fitting the test set (the fusion wall again), so literature defaults are used and
**every value is reported, not the best one.**

| scorer | macro | Bot | Bot lift | Web BF | XSS |
|---|---:|---:|---:|---:|---:|
| CNN p(attack) *(ref)* | **0.6399** | 0.0448 | 1.31× | **0.9226** | **0.9524** |
| logit margin | 0.5929 | 0.0488 | 1.43× | 0.8763 | 0.8536 |
| MSP *(ref)* | 0.5884 | 0.0448 | 1.31× | 0.8719 | 0.8485 |
| max-logit | 0.5702 | 0.0332 | 0.97× | 0.8595 | 0.8179 |
| **energy T=1000** | **0.0326** | **0.0783** | **2.29×** | 0.0135 | 0.0059 |

**O1 (no scorer materially beats MSP on Bot) — CONFIRMED by a 2 % margin.** Threshold fixed at 0.08
in advance; best came in at **0.0783**. Reported as borderline, not as a clean pass.

**What disqualifies the winner is the cost, not the margin**: `energy_T1000` buys Bot by destroying
known-class discrimination (macro **0.0326**), and is still below **every** (B)-family channel
already measured (AE 0.1314 · RF 0.1311 · Mahalanobis 0.1030 · KG 0.3103). Consistent across
T=10/100/1000, so real — just useless.

✅ **The "representational, not informational" account now covers the whole standard battery.**

**Writes** `outputs/metadata/ood_scores.json` + `y_prob_ood_<name>_test.npy` per scorer (so any of
them can be fused or compared like any other channel), and logs each to `runs.jsonl`.

## `scripts/paper_metrics.py`

**Purpose**: **Our runs in the base paper's metric set (Accuracy + F1, five test-set views) and in
the wider literature's (accuracy/precision/recall/F1/FAR/ROC-AUC/PR-AUC).** This project headlines
macro zero-day PR-AUC because `metrics.py` enforces it — but that is not what anyone we are compared
against reports, and until 2026-08-05 **not one of the base paper's numbers had ever been computed
for our models.**

**Base paper Table II (50 epochs, Adamax) with our column added:**

| Test set | Hybrid-LTN | 1D CNN | **CNN (ours, n=3)** | LTN ctrl | LTN +Ax6 | LTN repro |
|---|---:|---:|---:|---:|---:|---:|
| Multi-class, 9 known | 81.08 % | 80.99 % | **99.81 %** | 99.87 % | 99.87 % | 99.86 % |
| Binary, 9 known | 99.57 % | 99.42 % | **99.84 %** | 99.89 % | 99.89 % | 99.89 % |
| Multi-class, 15 classes | 67.52 % | 67.45 % | **96.17 %** | 96.22 % | 96.23 % | 96.22 % |
| Binary, 15 classes | 93.03 % | 90.88 % | **97.95 %** | 97.90 % | 97.97 % | 97.97 % |
| **Binary, 6 unknown** | **60.47 %** | **48.34 %** | **47.85 %** | 45.37 % | 47.18 % | 47.24 % |

**Two results, and they point opposite ways:**

1. ✅ **We beat the base paper by 18–29 pp on all four known-class views** (multi-class 15: 96.17 %
   vs 67.52 %). ⚠️ That is a **modality** advantage, not a method one — 68 engineered flow features
   are far more separable than raw payload bytes. Do not claim it as an algorithmic win.
2. 🔴 **We reproduce their 1D CNN's zero-day number almost exactly (47.85 % vs 48.34 %) and CANNOT
   reproduce the Hybrid-LTN's +12 pp symbolic gain.** Our closest reproduction of their model
   (`ltn_repro` = plain CE + Ax1/Ax2 label anchors) scores **47.24 %** — no gain over our own CNN.
   **This is the project's central finding, expressed for the first time on the base paper's own
   metric.**

### 🔴 Two defects in the base paper's zero-day metric, both verified here

**(a) It has no false-positive term.** View 5 contains **only attack rows**, so precision ≡ 1,
accuracy *is* recall, and `F1 = 2A/(1+A)` exactly. The script reproduces every published F1 from the
matching accuracy to <0.02 pp. So their *"accuracy 48→60 %, F1 65→75 %"* headline is **one result
reported twice**, and **a model that flags every flow as an attack scores 100 % on both** while
running a 100 % false alarm rate. Our own float32 saturation bug did exactly that in 2026-07-27 and
was caught **only** because our metric has a benign side.

**(b) It is a size-weighted mixture** — the same defect `metrics.py` was rewritten to remove.
Per-family detection at their argmax rule (our CNN):

| family | n | our share | their share | detected |
|---|---:|---:|---:|---:|
| **Bot** | 1,956 | **46.8 %** | 8.0 % | **0.0 %** |
| Web Attack Brute Force | 1,507 | 36.0 % | 36.8 % | 89.9 % |
| Web Attack XSS | 652 | 15.6 % | 10.5 % | 96.9 % |
| **Heartbleed** | 11 | 0.3 % | **42.2 %** | 0.0 % |
| Infiltration | 36 | 0.9 % | — (known to them) | 0.0 % |

Holding the model fixed and only changing the mix moves the headline **48.32 % → 44.38 %**. Their
set is Heartbleed+WebBF-dominated (79 %); ours is **Bot**-dominated, the one family our CNN provably
cannot reach. **A single zero-day accuracy number is not comparable across papers unless the family
mix matches** — composition explains ~4 pp of the gap, so the missing ~12 pp symbolic gain is *not*
explained away by it.

### The field's suite (overall binary, all 15 classes) — comparable to published 99 %+ claims

| channel | accuracy | precision | recall | F1 | FAR | ROC-AUC | PR-AUC |
|---|---:|---:|---:|---:|---:|---:|---:|
| **CNN (ours)** | **97.95 %** | 99.71 % | 96.32 % | **97.98 %** | 0.31 % | 98.32 % | 99.00 % |
| LTN control | 97.90 % | 99.82 % | 96.13 % | 97.94 % | 0.19 % | 98.15 % | 98.24 % |
| LTN +Ax6 | 97.97 % | 99.82 % | 96.26 % | 98.01 % | 0.19 % | 98.16 % | 98.24 % |

⚠️ **These are in the literature's range and are NOT a better result than our 0.64 macro zero-day
PR-AUC — they are an easier question asked of the same models.** Report both, and say which is which.

⚠️ **Three documented deviations make this a comparison in FORM, not head-to-head**: modality
(payload bytes vs flow features), zero-day membership (**they hold out PortScan and train on
Infiltration; we do the reverse** — 5 of 6 overlap), and class sizes (their Heartbleed is 13,486
payload packets; flow data has 11).

**Writes** `outputs/metadata/paper_metrics.json`.

## `scripts/comparability.py`

**Purpose**: **The table that makes this project comparable to the literature.** Published
CIC-IDS2017 work routinely reports **99 %+**; we headline **~0.64**. That looks like we are far
behind. We are not — the two numbers measure different tasks, and **the same models produce both.**

| channel | overall binary *(what the field reports)* | dedup *(honest)* | **macro zero-day** *(ours)* |
|---|---:|---:|---:|
| XGBoost | **0.9936** | 0.9901 | 0.6372 |
| CNN | **0.9928** | 0.9884 | 0.6446 |
| LTN control | 0.9921 | 0.9874 | 0.6049 |
| **CNN + KG fusion** | 0.9893 | 0.9896 | **0.7328** |

**The same model goes 0.9936 → 0.6372 — a 0.3564 gap — purely by changing protocol.** That is the
write-up's opening argument, and reviewers cannot be expected to notice it unprompted.

**The third column closes audit item C1.** 17.0 % of test rows are exact feature-vector duplicates
of a training row (PortScan 58.3 %, SSH-Patator 48.6 %); for those rows the task is lookup, not
detection. **No de-duplication is performed** — that would change the protocol and break base-paper
comparability. Both variants are reported instead, which is what C1 proposed. Costs one evaluation
pass, no retraining. **The asymmetry is the finding: all six zero-day families measure 0.0 % overlap**,
so duplication inflates *the field's* metric and leaves *ours* untouched.

**Constants**: `CHANNELS`, `OUT` · helper `_hashes`.

## `scripts/robustness.py`

**Purpose**: Closes audit item **C3**, and tests the fusion wall **constructively**.

**Part 1 — C3: the macro metric counts one signal twice.** `fam_web_attack_brute_force_pr_auc` and
`fam_web_attack_xss_pr_auc` correlate at **r = +0.992** (same Thursday-morning campaign, same tool,
same target), so `macro = mean(Bot, WebBF, XSS)` is really **⅓ Bot + ⅔ one web signal**, weighted by
an artifact of how many web sub-labels CIC-IDS2017 happens to define. The regrouped alternative
`mean(Bot, mean(WebBF, XSS))` weights the two *phenomena* equally instead of the two *labels*.
**Verdict: absolute values shift ~0.11–0.15 but every meaningful ordering is preserved** — the
macro-cost conclusions are robust to the label-granularity artifact.

**Part 2 — does known-class weighting beat equal weighting?** The obvious fix to `fusion_multi.py`'s
"weak channels dilute strong ones" is to weight by quality, and the only **legitimate** way here is
on **known-class validation performance**, which uses no zero-day information. **The fusion wall
predicts this will hurt, and it does: Bot −0.0176** — it down-weights the KG precisely for being
good at a family it never trained on. A constructive confirmation of the wall rather than another
null result.

⚠️ **A false verdict was caught and fixed in this script**: a 1.3×10⁻⁵ tie was being printed as
*"conclusions NOT robust"*. **An automated verdict that cries wolf is worse than none.**

**Functions**: `fam_pr`, `macro_std`, `macro_regrouped`, `_swaps`.

# Phase 4 — Knowledge Graph + explainability

## `scripts/kg.py`

**Purpose**: **Phase 4 — the adaptive Knowledge Graph.** 215 nodes (200 Cluster + 6 Behaviour +
9 AttackType), 1,183 edges. Memory is initialised from TRAIN, then TEST is **streamed in true
chronological order** with exponential edge decay (τ=3 windows) — the "adaptive" half of the
project title. n=3 seeds.

⚠️ **Every design decision here was forced by measurement, not by the original spec.** Read
[STATUS.md](STATUS.md) → "LAST PHASE-4 GATE CLOSED" before changing any of them:

| Decision | Value | Why not the alternative |
|---|---|---|
| Representation | **raw features** | CNN embeddings swing Bot purity 87.9/86.6/**44.4** % across seeds; the AE bottleneck is worse still (52.1 pp) — **rank stability ≠ cluster stability** |
| Scope | **corroboration + explanation** | the spec's "unexplained cluster" detector measures lift **≤ 1.00×**, at or below chance |
| Emerging rule | **growth/burstiness only** | co-occurrence is weak (2.81× at 1.5 % recall); "unexplained" is dead |
| Decay | **kept (adaptive)** | time = flow-count position in true chronological order, via `timeline.py` |
| Behaviours | **`active_behaviour_matrix()`** | `RepeatedConnections` is constant zero; `BeaconLike` is binary |

**Constants**: `SEED`, `K` (clusters), `N_WINDOWS`, `TAU` (decay), `BURST_THR`, `TAG`, `BEH`.

**Results**: `s_kg` **causal / online** (past only) — macro **0.2488** [0.2446, 0.2523], Bot
**0.3103** [0.2970, 0.3210], **the best Bot channel measured in this project**. The transductive
(whole-stream) variant is worse (Bot 0.2457), so **the deployable version is the stronger one**.
The CNN still dominates macro by 0.39 — the KG is not a general detector, exactly as scoped.

🔴 **The lateness control is permanent in this script and must be quoted with any KG number.** The
causal score rises with arrival position and CIC-IDS2017 schedules attacks late, so *"later ⇒ more
suspicious"* had to be ruled out. A **trivial lateness-only baseline scores Bot 0.1575** — beating
the previous best channel (autoencoder, 0.1314). The KG's advantage **survives** (within-window
3.2× vs the AE's 1.9× and the CNN's 1.5×; the control collapses to exactly 1.0×, confirming the
test is sound), but the headline 9.4× is roughly *schedule × cluster signal*. **Quote 0.3103 global
and 3.2× within-window together.**

⚠️ `s_kg` takes only **193 distinct values** (one per cluster), so PR-AUC is valid but
**recall@1%FPR is degenerate — do not cite it.**

**Writes** `models/kg.gpickle`, KG channel predictions, and its metrics to `runs.jsonl`.

## `scripts/kg_visualize.py`

**Purpose**: Obsidian-style interactive view of the graph built by `kg.py`. Emits a
**self-contained** HTML file — no CDN, no external assets, everything inline — with a force-directed
layout: dark canvas, nodes sized by degree and coloured by type, hover-to-highlight-neighbourhood,
drag, zoom, pan.

**Why hand-rolled rather than d3**: the published-artifact CSP blocks every external host, so a CDN
import would silently fail. At ~215 nodes an O(n²) repulsion step is cheaper than the download.

**Reads** `models/kg.gpickle` · **Writes** `outputs/figures/kg_graph.html` (215 nodes, 931 edges).

```bash
python scripts/kg_visualize.py
```

## `scripts/explain.py`

**Purpose**: **The explainability half of canonical Phase 4**, plus the **Tier-A faithfulness
measurement** the roadmap asks for and almost nobody in this field runs. `kg.py` delivered the KG
and one of the three explanations; this delivers the other two, assembles the Final Alert, and
measures whether the neural explanation is actually faithful to the model.

**The three explanations** (per [explainability.md](target/explainability.md)):

1. **Neural** — **Integrated Gradients**, implemented directly against `tf.GradientTape`, baseline =
   the training mean (so attributions read as *deviation from typical traffic*). Chosen over SHAP's
   DeepExplainer because IG carries an exactness check — the **completeness axiom**, verified in
   `ig_completeness()`: `sum(attributions) ≈ f(x) − f(baseline)`, |error| 0.0001–0.042 — and avoids
   SHAP's brittle Keras-2 Conv1D path.
2. **Logic** — per-axiom SAT for the flow. ⚠️ **Only Ax3–Ax6 appear, deliberately.** Ax1/Ax2 are
   *label anchors*: they condition on the ground-truth class, which does not exist at inference, so
   reporting them as explanations would be circular. This is why 4 of 6 axioms are shown.
3. **KG** — reasoning path from `kg.py` (cluster → behaviours → known attacks, plus whether the
   cluster is currently emerging).

**Faithfulness (Tier A)** — ERASER-style deletion metrics, each against a **random-feature control**
(without which the numbers mean nothing), n=1,500 flows:

| top-k | comprehensiveness (IG) | random control | **ratio** |
|---|---:|---:|---:|
| 3 | +0.2908 | +0.0141 | **20.67×** |
| 5 | +0.3810 | +0.0311 | **12.26×** |
| 10 | +0.4536 | +0.1089 | **4.16×** |

⚠️ **Sufficiency is the weaker half and is reported as such**: IG beats random (0.442–0.460 vs
0.513–0.515) but the absolute gap stays ~0.44, so the top-k *alone* do not reproduce the decision.
Honest reading: **the explanation reliably finds features the model depends on; the decision is
distributed across more than 10 features.**

**Functions**: `attack_score`, `integrated_gradients`, `ig_completeness`, `logic_explanation`.
**Constants**: `N_ALERTS`, `N_FAITH`, `IG_STEPS`, `BASELINE`, `AXIOMS`.

🔬 **Its most informative output is not a score.** On Bot flow #114062 the CNN says benign
(p_attack=0.0021), **Ax6 BeaconLike fires 1.00 → VIOLATED**, and the KG flags the cluster as
emerging and beacon-dominated. Both non-neural pillars dissent from the CNN, on exactly the family
the CNN is independently proven to get wrong. **No single-pillar system produces that.**

# Phase 5 — fusion + rigor

## `scripts/fusion_kg.py`

**Purpose**: **Parameter-free rank fusion of the CNN and the KG — the first combination in this
project to beat the CNN baseline.**

| | macro | Bot | Web BF | XSS |
|---|---|---|---|---|
| CNN alone | 0.6399 [0.6353, 0.6446] | 0.0446 | 0.9226 | **0.9524** |
| **CNN + KG (rank-mean)** | **0.6926 [0.6626, 0.7328]** | **0.2518** | **0.9283** | 0.8976 |

+0.0528, paired bootstrap **p<0.001**, 95 % CI [+0.0468, +0.0594], all 3 seeds improve, seed ranges
**disjoint**, and it survives the lateness control.

**Why it works when every fitted fusion failed**: THE FUSION WALL applies to *fitted* combiners,
which must be calibrated on validation data containing no zero-day by construction —
`fusion_beaconlike.py` measured exactly that and returned `[2.35, 0.02]`. **A rank-mean needs no
fitting: the weight is imposed, not discovered**, so the combiner never has to learn the value of a
signal it was never shown. Ranks rather than raw scores because the channels are on wildly different
scales and `s_kg` is heavily tied.

⚠️ **Caveats that must travel with the number**: (1) **three combination rules were tried and the
best is reported** — rank-mean 50/50 **+0.0528**, rank 0.75/0.25 **+0.0320**, rank-**max**
**−0.4125** (catastrophic; max is dominated by whichever channel has more top ranks, and `s_kg`'s
193-value score puts huge tied blocks there). 50/50 is the canonical no-tuning default, but this is
a mild selection effect and is stated, not hidden. (2) **XSS gets worse** (0.9524 → 0.8976) — a real
trade. (3) It is a channel combination, **not** the full Phase-5 Decision Fusion. (4) Per the noise
floor, **direction is established (3/3 seeds); magnitude is not (0.027–0.088).**

## `scripts/fusion_multi.py`

**Purpose**: Parameter-free multi-channel rank fusion over **five pre-registered subsets** — the
improvement path that does not involve fitting on test.

**The constraint that shapes it**: zero-day families are test-only by construction, so **any**
hyperparameter tuned by looking at zero-day performance (k, τ, burst threshold, which channels to
include) is fitting on the test set. What remains legitimate is combination with **imposed** rather
than learned weights.

| subset | macro | Δ vs CNN | Bot |
|---|---:|---:|---:|
| **CNN + KG (2 channels)** | **0.6926** | **+0.0527** | 0.2518 |
| ALL 9 channels | 0.6664 | +0.0265 | 0.1510 |
| A_ONLY (supervised) | 0.6600 | +0.0201 | 0.0730 |
| A+B+KG (3 channels) | 0.6509 | +0.0110 | 0.3147 |
| B_ONLY (benign-only) | 0.1180 | **−0.5219** | 0.0975 |

🔴 **More channels made it worse.** Under equal weighting IsolationForest (macro 0.0653) gets the
same vote as the CNN. The 2-channel pairing wins because CNN and KG are **complementary in a
specific way** — the KG rescues Bot while the CNN holds the web attacks — **not** because more
evidence is better. **What survives as robust: 4 of 5 subsets beat the CNN baseline.**

⚠️ All five subsets were pre-registered and **all five are reported**. Quoting only the winner would
be a selection effect.

## `scripts/significance_seed.py`

**Purpose**: **Seed-level** significance — "would this hold if we retrained?" — which n=3 made
arithmetically impossible. `significance.py` bootstraps over test **flows** ("would this hold on
different traffic?"); this is the different, and for a claim about a *method* arguably more
important, question.

**Why it could not exist before**: the Wilcoxon signed-rank test with 3 paired samples has a
**minimum achievable two-sided p of 0.25**, so no n=3 result could reach p<0.05 regardless of effect
size. At **n=6** the floor drops to **p = 2/2⁶ = 0.031**.

⚠️ **Even at n=6 the test is weak** — it can only return p ∈ {0.031, 0.094, …}. **A non-significant
result at n=6 is not evidence of no effect; it is evidence the test is underpowered.** Both the
p-value and the raw per-seed values are printed, and a sign test is reported alongside.

**Functions**: `fam_pr`, `macro`, `seed_test` · **Writes** `outputs/metadata/significance_seed.json`.

# Phase 7.5 — operational readiness

## `scripts/operational.py`

**Purpose**: **All four Tier-1 items that gate Phase R**, in one pass. Exists because **PR-AUC is
the wrong target for a response engine**: it summarises ranking across *all* thresholds while the
engine acts at **one**. A system can post macro 0.69 and still auto-block at 40 % precision, and no
other metric in this project would warn you.

**Four pre-registered predictions, all CONFIRMED.**

**1 — Ship the ensemble, not a single run.** 11 CNN runs, probability-mean:

| | macro |
|---|---:|
| single-run mean (n=11) | 0.6217 |
| single-run **max** | **0.6446** ← the number usually quoted |
| single-run min | 0.5825 |
| **ENSEMBLE** | **0.6356** |

Beats the mean, **not** the max — because 0.6446 is the top of 11 draws, not a typical result. **The
ensemble's argument is not the delta, it is that it is reproducible.** ⚠️ `cnn_auxhead_*` is
**excluded and the exclusion is load-bearing** — it matches the `cnn_*` glob but is a *different
architecture*, so including it would silently answer "does a heterogeneous ensemble help?" while
being reported as a reproducibility fix. Caught on first run (12 files, not the 11 STATUS reports).

**2 — Calibration**, fitted on **validation**, which is zero-day-free by construction (asserted in
code), then measured *separately* on known-class and zero-day subsets:

| method | ECE all | ECE known-class | ECE zero-day | **zd ÷ known** |
|---|---:|---:|---:|---:|
| uncalibrated | 0.0260 | 0.0084 | 0.0381 | 4.5× |
| Platt | 0.0196 | 0.0006 | 0.0387 | 62× |
| isotonic | **0.0192** | **0.0001** | 0.0387 | **287×** |

🔴 **Calibration works beautifully on known classes and does nothing for zero-day.** Isotonic reaches
ECE 0.0001 on known classes while its zero-day ECE is unchanged at 0.0387 — **287× worse.** A
calibrator learns a score→outcome mapping; for a class the model has never seen, that mapping does
not hold. **The better the calibration, the wider the gap** — which is the fusion wall in yet another
guise.

🔴 **Isotonic wins ECE but is UNUSABLE as an operating point**, and this is an operational finding in
its own right: it is a step function with **74 distinct values** over 114,658 flows, so the 1%-FPR
quantile lands inside a tie block. The first run of this script thresholded on it and achieved
**FPR 0.70 against a 0.01 target.** Platt is a monotone *continuous* transform (59,920 distinct
values), preserves the ranking exactly, and hits the target FPR at 0.0100. **Calibrate with isotonic
for reporting; threshold with Platt.**

**3 — Precision @ alert budget.** Precision is **~1.000 at every budget for every channel** — and
that is the problem, because **the alerts are entirely known attacks**:

| budget | CNN precision | zero-day in alerts | zd recall |
|---:|---:|---:|---:|
| 100 | 1.000 | **0** | 0.0000 |
| 1,000 | 1.000 | **0** | 0.0000 |
| 10,000 | 1.000 | 3 | 0.0007 |
| 25,000 | 1.000 | 1,913 | 0.4573 |

**Depth required before a novel attack surfaces at all** (as % of the 114,658 test flows):

| channel | @10 % zd | @25 % zd | @50 % zd |
|---|---:|---:|---:|
| CNN | 13,170 (11 %) | 14,301 (12 %) | 59,355 (**52 %**) |
| CNN ensemble | 29,911 (26 %) | 31,533 (28 %) | 60,043 (52 %) |
| **CNN + KG fusion** | 16,556 (14 %) | 23,899 (21 %) | **36,661 (32 %)** |
| **KG (causal)** | 14,992 (13 %) | 28,701 (25 %) | **33,063 (29 %)** |

**At any deployable alert budget you see only known attacks.** Reaching half the zero-day flows means
reviewing a third to a half of all traffic. **The KG and the fusion cut that depth by ~20 pp**, which
is the clearest operational statement of what the KG buys — better than any PR-AUC delta.

**4 — Selective prediction / abstention.** Confidence = **margin from the decision threshold**,
`|logit(p) − logit(thr)|`. ⚠️ The first version used `|p − 0.5|`, which is wrong when the operating
point is 0.000049 — it ranks *confidently benign* flows as most confident and collapsed recall to
0.035 for reasons unrelated to selective prediction.

| coverage | precision | recall | benign kept | **zd precision** |
|---:|---:|---:|---:|---:|
| 100 % | 0.990 | 0.964 | 55,237 | **0.0350** |
| 95 % | 0.996 | 0.963 | 49,766 | **0.0350** |
| 90 % | 0.996 | 0.963 | 44,035 | **0.0350** |
| 75 % | 0.996 | 0.963 | 26,839 | **0.0350** |

🔴 **Abstention does not rescue zero-day — zero-day precision does not move at all (+0.0000).**
Predicted in advance from the Bot failure analysis: the CNN is **confidently wrong** on Bot (100 %
argmax BENIGN, mean p(BENIGN)=0.9984), and **confidence-based abstention cannot catch
confident-and-wrong.** Coverages ≤50 % are excluded as degenerate — they retain 2–125 benign flows
out of 55,237, which is why their FPR column reads exactly 1.0000.

**Writes** `outputs/metadata/operational.json`, `outputs/figures/operational.png`.

```bash
python scripts/operational.py
```

## `scripts/ablation.py`

**Purpose**: **Remaining Work #6 — does each component earn its place?** CNN → +LTN → +KG → full, at
n=3 paired seeds, using the same parameter-free equal-weight rank fusion `fusion_kg.py` established.
Nothing is fitted, so nothing here can be tuned on the test set.

**Five rungs, not three, because "+LTN" is ambiguous and the ambiguity is load-bearing**: the LTN
**control** is the symbolic *trainer* with axiom weight zero (statistically indistinguishable from
the CNN at n=6), while **Ax6** is the actual symbolic *pillar* (behaviour-grounded axioms, `ratio`
omega-mode). *"Do the axioms earn their place?"* and *"does the training loop?"* are different
questions; both are run.

| rung | macro (mean) | range | Bot | Web BF | XSS |
|---|---:|---|---:|---:|---:|
| CNN | 0.6399 | [0.6353, 0.6446] | 0.0446 | 0.9226 | **0.9524** |
| CNN + LTN-ctrl | 0.6433 | [0.6338, 0.6497] | 0.0594 | 0.9195 | 0.9511 |
| CNN + LTN-Ax6 | 0.6394 | [0.6319, 0.6498] | 0.0495 | 0.9187 | 0.9501 |
| **CNN + KG** | **0.6926** | [0.6626, 0.7328] | **0.2518** | **0.9283** | 0.8976 |
| CNN + LTN-Ax6 + KG (FULL) | 0.6708 | [0.6394, 0.7114] | 0.2043 | 0.9277 | 0.8806 |
| CNN + LTN-ctrl + KG | 0.6887 | [0.6559, 0.7133] | 0.2302 | 0.9276 | 0.9085 |

**Paired deltas vs CNN** (each rung shares the CNN run, so run-to-run noise cancels — **this, not the
between-run SD, is the correct reference**):

| rung | mean Δ | seeds improved |
|---|---:|---:|
| CNN + LTN-ctrl | +0.0035 | 2/3 |
| CNN + LTN-Ax6 | **−0.0004** | **1/3** |
| **CNN + KG** | **+0.0528** | **3/3** |
| CNN + LTN-Ax6 + KG (FULL) | +0.0310 | 3/3 |

**Paired bootstrap over test flows** (B=2000, common random numbers):

| comparison | diff | 95 % CI | p |
|---|---:|---|---:|
| CNN + KG vs CNN | **+0.0528** | [+0.0466, +0.0592] | <0.0001 |
| CNN + LTN-ctrl vs CNN | +0.0035 | [+0.0017, +0.0061] | <0.0001 |
| CNN + LTN-Ax6 vs CNN | −0.0004 | [−0.0021, +0.0018] | 0.59 (n.s.) |
| **FULL vs CNN + KG** | **−0.0218** | [−0.0288, −0.0149] | **<0.0001** |

⚠️ **`CNN + LTN-ctrl vs CNN` is "significant" at p<0.0001 and must NOT be reported as an
improvement.** The gap is **+0.0035 — 0.16 SD** of the measured noise floor, and it improves on only
**2 of 3 seeds.** This is precisely the C2 trap: *a flow-level paired bootstrap cannot rescue a delta
below the pipeline's own reproducibility.* The bootstrap quantifies "would this hold on different
traffic", not "would this hold if we retrained". **Applying the project's own rule to its own new
result: this is noise.**

🔴 **The conclusion is negative, and it is about this project's own architecture: only the KG earns
its place.** Adding the symbolic pillar on top of the KG is **significantly harmful** (−0.0218,
p<0.0001) — not merely unhelpful. The symbolic pillar adds nothing on its own (−0.0004, improving on 1 of 3 seeds) and
**actively hurts when stacked on the KG** — the full system scores **0.6708 vs CNN+KG's 0.6926**, and
dilutes the KG's Bot signal from 0.2518 to 0.2043. Consistent with `fusion_multi.py`'s independent
finding that equal-weight fusion is about **complementarity, not quantity**.

✅ **Two independent reproductions validate the implementation**: this script recomputes macro from
raw score arrays and lands on **0.6399** for the CNN and **0.6926** for CNN+KG — exactly the figures
`metrics.py` and `fusion_kg.py` report.

**Writes** `outputs/metadata/ablation.json`. ⚠️ The bootstrap is one pass of B × 6 rungs using
**common random numbers** (correct for paired comparisons, and ~5× cheaper than per-comparison
resampling — the first version needed ~180,000 PR-AUC computations and had to be killed).
**Run it through `run_long.sh`** — it takes ~10 min.

## `scripts/determinism.py`

**Purpose**: **Phase 7.5 Tier 2 #5 — make training reproducible at fixed seed.** Imported by every
trainable script and called immediately after `import tensorflow`, before any op runs.

**The defect it addresses**: six runs of **seed 42, identical code, idle machine** gave **SD 0.0222,
range 0.0621, CV 3.6 %**. A fixed seed did *not* pin the result. That noise floor **retracted C2**,
made every published n=3 range an artefact, and showed the headline `cnn_paper = 0.6446` is the
**max of 11 runs**. Root cause: **no determinism flags were set anywhere in this project.** Seeding
controls the *pseudo-random* sources (init, shuffling, dropout); it does nothing about *thread
scheduling*, and float addition is not associative.

**What `enable(seed, intra=16, inter=2)` sets**: `PYTHONHASHSEED` · `TF_DETERMINISTIC_OPS` ·
`TF_CUDNN_DETERMINISTIC` (no-op on CPU, set so a future GPU move inherits it) ·
`tf.keras.utils.set_random_seed` · `tf.config.experimental.enable_op_determinism()` · **pinned
intra/inter-op thread counts**.

**Why pinned rather than `threads=1`.** One thread is the only setting reproducible *across machines
with different core counts*, but it is drastically slower and this project has one machine. Pinning
to a fixed count should give same-machine reproducibility at full speed — **and because that is an
empirical claim, it is tested rather than assumed** (`verify_determinism.sh`).

⚠️ **Determinism does NOT make old and new runs comparable.** Pinning threads changes the reduction
order, so a deterministic seed-42 run will not reproduce any of the 11 historical seed-42 values —
it defines a **new fixed point**. Runs before and after this flag are different populations; do not
pool them. Same trap as the session/environment effect in KNOWN_ISSUES. The applied state is returned
and logged into `runs.jsonl` as `det_*` fields so it travels with the numbers.

⚠️ **Must be called before any op runs** — TF snapshots the threadpool config on first use and raises
afterwards. `enable()` detects that rejection and prints a loud warning rather than silently
producing a non-deterministic run. `TF_DETERMINISM=0` opts out for throwaway exploration.

## `scripts/verify_determinism.sh`

**Purpose**: Tests the claim above instead of asserting it. Trains **seed 42 twice** with identical
settings and compares the saved probability arrays for **byte-level identity** — the only unambiguous
pass, since "close" is exactly what we already had at SD 0.0222.

```bash
scripts/verify_determinism.sh            # fast: 50k rows, 2 epochs
FULL=1 scripts/verify_determinism.sh     # full training, both runs (slow)
```

Runs use tags containing `smoke`, so `paths.predictions_dir()` quarantines the undertrained arrays
into `_smoke_archive/` and `CNN_SUBSET` suppresses `runs.jsonl` logging — **this cannot pollute the
fusion-channel namespace or the research record.** On failure it prints `max|diff|` and tells you to
fall back to `TF_THREADS=1`.

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

## `scripts/lint_conventions.py`

**Purpose**: **Mechanical enforcement of this repo's conventions. Run it at the end of every
session** — it is non-negotiable #6 in [CLAUDE.md](../CLAUDE.md).

```bash
python scripts/lint_conventions.py            # report
python scripts/lint_conventions.py --strict   # exit 1 on any FAIL (for CI)
```

**Why it exists**: on 2026-08-03 the same latent bug (`open()` with no explicit encoding → cp1252 on
Windows) was found and fixed **three separate times in one session** — `config.py`, `tracking.py`,
`dashboard_server.py` — because each was treated as an incident rather than an instance of a *class*.
Separately, the heartbeat-monitor rule lapsed on **six** long-running jobs. Conventions written as
prose depend on someone remembering them at exactly the right moment; this fails loudly instead.
**Each check names the incident that motivated it**, so nobody has to re-derive why.

**Checks**: `open()`-without-encoding · timestamp-bypass (naive `to_datetime` without `timeline`) ·
smoke-namespace · single-component-table · **script-count** · **undocumented-scripts** ·
hardcoded-paths · `runs.jsonl` integrity · launcher-suppresses-log-growth · gitignored-research-record.

⚠️ **A cautionary note about this script itself.** On 2026-08-05 the `script-count` check was found
to have been **passing on a wrong count for two sessions**: its regex `(\d+) scripts` required the
number to sit directly against the word, but the docs put a qualifier between them
(*"…&#32;Python scripts"*), so the check never fired — 9 undocumented scripts slid through while the
lint reported ALL CHECKS PASS. **A mechanical check that cannot fire is worse than no check — it
buys false confidence.** Fixed by tolerating a qualifier (while staying on one line and rejecting
`scripts/` so command lines are not counted as prose) and by adding `undocumented-scripts`, which
verifies *membership* rather than arithmetic.

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

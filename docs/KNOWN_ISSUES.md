# Known Issues (Living Document)

> Track bugs, design flaws, and risks here. Mark `[OPEN]` / `[FIXED]` / `[WONTFIX]`. Reference from commits when resolved.
>
> **Restructured 2026-07-29.** The file previously had duplicated `## High` and `## Medium` headings
> (two interleaved halves), and carried five `[OPEN]` issues that had already been fixed — including
> "no dependency manifest" when `requirements.txt` has been pinned since 2026-06-18. It was also
> missing the entire 2026-07-27 measurement-defect class, which lived only in STATUS/CHANGELOG.
> Severity now reflects impact on **current** work; issues scoped to superseded code are marked as such.

## Legend

| Tag | Meaning |
|---|---|
| `[OPEN]` | Live — affects current work |
| `[FIXED]` | Resolved, kept for the record |
| `[SUPERSEDED]` | Real when written, but scoped to code that is no longer used |
| `[WONTFIX]` | Accepted limitation, deliberately not fixed |

---

## Critical — measurement integrity

These are the highest-severity class in this project: they do not crash, they produce **numbers that
look fine and are wrong**. All three were caught only by auditing distributions rather than reading
summary metrics.

### [FIXED 2026-07-27] float32 softmax saturation silently faked perfect recall
Scores were computed as `patk = 1 − softmax[benign]` in float32. For a confident model `p(benign)`
rounds to exactly 1.0, so `patk` underflows to **exactly 0.0**. On `ltn_ctrl_w0`, **99.25% of benign
and 51.7% of zero-day flows** sat at exactly 0.0. The 1%-FPR threshold therefore landed at 0.0,
flagged everything (achieved FPR = 1.000), and produced `recall=1.0000` rows for every family — an
artefact, not detection. `zd_f1` collapsed to `0.13153…`, the algebraic predict-all-positive constant
at 7% prevalence, **identical across three different models** — the tell that should have been caught
sooner. **4 of 13 runs affected**, including all three fair-loop runs the control experiment depended on.
**Fix:** `metrics.py` now reports `diagnostics.saturated` plus `achieved_fpr` / `largest_tie_frac`;
`scripts/rescore_logits.py` re-scores from pre-softmax logits as `logsumexp(attack) − benign_logit`.

### [FIXED 2026-07-27] The headline metric was a size-weighted mixture
"Benign vs all 6 unknowns" averaged families whose detectability differs by ~30×, so it moved for
reasons unrelated to detection quality — and it **reordered the model ranking** versus a per-family
view (this is what produced the retracted "XGBoost ≈ CNN" claim). **Fix:** `metrics.py` headline is
now per-family PR-AUC + macro over families with n ≥ `MIN_FAMILY_N` (100); the blend is secondary.
Heartbleed (n=11), Infiltration (n=36) and SQL Injection (n=21) are excluded as underpowered rather
than reported to 4 decimal places.

### [CLOSED 2026-08-03] 17% of test rows are exact duplicates of training rows

> ✅ **CLOSED — the proposed fix was implemented exactly as written** (`scripts/comparability.py`):
> report both the as-is and a unique-flows-only variant, no de-duplication, protocol unchanged, one
> evaluation pass, no retraining. **Deduplication costs the supervised channels 0.0035–0.0049**
> (XGBoost 0.9936 → 0.9901, CNN 0.9928 → 0.9884, LTN control 0.9921 → 0.9874). The **asymmetry is
> the finding**: all six zero-day families measure **0.0 % overlap**, so duplication inflates *the
> field's* headline metric and leaves *ours* untouched. That is now the write-up's opening argument
> rather than a liability. *(Tagged `[OPEN]` here until 2026-08-05 — a doc-drift lapse; the work
> landed 2026-08-03.)* Original issue below, kept as written.
CIC-IDS2017 is duplicate-heavy and `preprocess.py` deliberately keeps duplicates; the paper split is
**stratified random**, so identical feature vectors land in both train and test. Measured by hashing
every row: **19,513 / 114,658 test rows (17.0%)** have an exact feature-vector twin in train.
Per class: PortScan **58.3%**, SSH-Patator **48.6%**, FTP-Patator 29.6%, DoS Hulk 25.3%, BENIGN 6.9%.
Train is 13.5% internally duplicated, test 7.0%.

**✅ Zero-day metrics are unaffected — all 6 zero-day classes measure 0.0%**, because they are
test-only by construction and cannot overlap train. **🔴 The contaminated figure is the ~0.98 overall
binary PR-AUC**, where PortScan at 58% overlap is substantially a lookup rather than detection.
Documented in the literature (Engelen et al. 2021), so a dataset-familiar reviewer will find it.
**Fix (proposed, NOT implemented):** do not de-duplicate — that changes the protocol and breaks
base-paper comparability. Report both the as-is and a unique-flows-only variant, stating the
duplicate rate. One evaluation pass, no retraining. See [STATUS.md](STATUS.md) → "Earlier-phase audit".

### [RESOLVED 2026-08-02] 🔴 → 🟡 The reference baseline was single-seed while its comparators were not
`cnn_paper` (macro **0.6446**) was **n=1, seed 42** while the LTN control it was compared against was
n=3 (range 0.6029–0.6505, containing 0.6446) — the same error class that produced the Ax6 Bot-lift
retraction. **Ran seeds 43 and 44** (`CNN_SEED=43/44 python scripts/cnn_paper.py`, using new
multi-seed support that never touches the seed-42 reference artifacts — verified by hash), then
log-odds rescored both for a clean comparison.

**Result: `cnn_paper` n=3, mean 0.6399, range 0.6353–0.6446. The LTN control's n=3 range
(0.6029–0.6505) fully contains the CNN's range.** So the original concern was well-founded — this is
**not resolved to "CNN confirmed,"** it is resolved to **"no clean winner at n=3; a proper
significance test (paired bootstrap / Wilcoxon on per-flow scores, per conference_roadmap Tier-S #2)
is required before either baseline can be cited as beating the other."** That test is not yet run —
new open item. Full numbers and interpretation in [STATUS.md](STATUS.md) → "EARLIER-PHASE AUDIT" C2.

xgboost, random_forest, isolation_forest, msp, mahalanobis remain n=1 — not addressed this pass.

### [CLOSED 2026-08-03] The macro metric counts one signal twice

> ✅ **CLOSED — the regrouped macro is now reported as a robustness row** (`scripts/robustness.py`),
> which is what this issue proposed. Regrouping to `mean(Bot, mean(WebBF, XSS))` shifts absolute
> values by ~0.11–0.15 but **preserves every meaningful ordering**, so the macro-cost conclusions are
> robust to the label-granularity artifact. ⚠️ **A false verdict was caught and fixed in the script
> itself**: a 1.3×10⁻⁵ tie was being printed as *"conclusions NOT robust"*. An automated verdict that
> cries wolf is worse than none. *(Tagged `[OPEN]` here until 2026-08-05 — a doc-drift lapse; the
> work landed 2026-08-03.)* Original issue below, kept as written.
`fam_web_attack_brute_force_pr_auc` and `fam_web_attack_xss_pr_auc` correlate at **r = +0.992** across
60 runs — same Thursday-morning campaign, same tool. `macro = mean(Bot, WebBF, XSS)` is therefore
⅓ Bot + ⅔ *one* web signal, weighted by an artifact of CIC-IDS2017's labelling granularity.
**Tested and refuted:** regrouping to `mean(Bot, mean(WebBF, XSS))` **preserved the run ordering
exactly** (cnn_paper 0.4982 > control 0.4824 > Ax6-ratio 0.4596 > Ax6-fixed 0.3977), so the
macro-cost finding is robust. But absolute values shift ~0.15.
**Fix (proposed, NOT implemented):** report the regrouped macro as a robustness row.

### [OPEN 2026-07-29] The feature transform was selected on the contaminated metric
`config.yaml` pins `feature_transform: log1p` citing *"0.980 vs 0.965 PR-AUC"* — that is the
**overall binary** metric, i.e. the one inflated by the duplicate leakage above and the one
`metrics.py` explicitly forbids as an optimisation target. The transform was never A/B'd against
macro zero-day PR-AUC, the actual headline.
**Fix (proposed, NOT implemented):** re-run the A/B on the headline metric (2 trainings). log1p may
still win; the issue is that the current justification cites the wrong number.

### [FIXED 2026-08-02] `rescore_logits.py` recorded the wrong seed on every multi-seed entry
Every `_logodds` entry was written with `seed: 42` regardless of which seed's model was actually being
rescored — wrong on 8 pre-existing rows (`ltn_ctrl_w0_s43_logodds`, `ltn_ax6_*_s43/s44_logodds`,
`ltn_ax6_ratio_w1p0_s43/s44_logodds`). **Caught live** while rescoring the two new C2 seeds: the fix
was needed to avoid writing 2 more wrong entries on top of the existing 8. **Fix:** seed is now parsed
from the tag's `_s<N>` suffix (`tag_seed()`), falling back to the config default only for unsuffixed
tags. Verified: `cnn_paper_s43_logodds` / `cnn_paper_s44_logodds` now correctly show `seed: 43` /
`seed: 44`. Cross-checked that STATUS's already-published LTN-control range (0.6029–0.6505) was
itself unaffected — it must have been read by run name, not the buggy field, when first computed.

**Still open — deliberately not touched:** the pre-existing rows still carry the wrong seed value in
`runs.jsonl`. Not corrected in place, because `runs.jsonl` is an append-only research log and
silently rewriting past entries would violate the project's own retract-in-place convention.
Any code reading `runs.jsonl` for those rows **must group by run name (tag), not by `params.seed`**,
until/unless a deliberate, logged correction pass is run.

> ✅ **REPAIRED 2026-08-03 — `scripts/repair_runs_log.py`.** Both defects are now fixed in the data,
> not merely described. **Why it became safe to do:** the append-only rule above existed to prevent
> untraceable edits — but `runs.jsonl` is now **version-controlled**, so `git diff` / `git revert`
> provide exactly the audit trail the rule was protecting, and better.
>
> | | originally said | **actually measured** | after repair |
> |---|---|---|---|
> | rows with the wrong seed | "8 rows" | **14 rows** (8 tags; 6 present twice, 2 once) | **0** |
> | exact-duplicate rows | "several duplicated 3×" | **26 rows** | **0** |
> | rows missing a schema version | (not tracked) | 97 of 97 | **0** — all stamped `v1-blended` (15) or `v2-macro` (56) |
> | total rows | 97 | | **71** |
>
> ⚠️ **Two counting corrections, including one of my own:**
> - The original "8" counted distinct *tags*, not rows — a repair guided by it would have fixed
>   roughly half and left the rest wrong.
> - An intermediate audit note in this file said **16 rows**; that was **also wrong** — it matched on
>   `'_s4' in name and seed==42`, which wrongly includes `ltn_ax6_ratio_w1p0_s42{,_logodds}`, whose
>   seed *is* correctly 42. The true figure is **14**, derived by comparing each row's seed against
>   its own `_s<N>` suffix. Corrected here rather than silently.
>
> 🔒 **What the repair deliberately did NOT touch.** Only **exact** duplicates were removed (identical
> in name, params *and* every metric). **8 duplicated names were preserved** because their content
> genuinely differs and collapsing them would have destroyed research data:
> `xgboost` · `msp` · `mahalanobis` · `random_forest` · `isolation_forest` · `cnn_auxhead_l0.5`
> (each an old-schema/new-schema pair from the 2026-07-27 metrics rewrite), plus `ltn_repro`
> (0.4401 vs 0.4853) and `ltn_v2` (0.4908 vs 0.4912) — **distinct training runs with identical
> configs.** The script asserts no run name disappears entirely, and refuses to write if one would.
>
> ✅ **Verified: every published figure reproduces unchanged after the repair** — CNN 0.6399/0.0446,
> LTN control 0.6194/0.0712, AE 0.0970/0.1314, Mahalanobis 0.3777/0.1030, MSP 0.5884/0.0448,
> RandomForest 0.5995/0.1311. A metadata repair that moved a result would have been a bug.
> Report: `outputs/metadata/runs_repair_report.json`.

**Also still open:** several entries remain duplicated 3× from repeated full re-runs of
`rescore_logits.py` (e.g. `cnn_paper_logodds` appears 3 times) — the code fix above does not dedupe
existing rows, and the 2026-08-02 rescore was deliberately scoped to only the 2 new tags specifically
to avoid adding a 4th copy of the other 17 (see the note now in `rescore_logits.py` itself: don't run
the full `TAGS` list just to add one new tag — temporarily scope `TAGS`, run, restore).

**✅ Mitigated 2026-08-03:** `runs.jsonl` is now **version-controlled** (it was gitignored, so the
entire research record had no history or backup — see the new issue below). A bad write is now
detectable and revertible via git, which is the practical protection the append-only rule needs.

### [FIXED 2026-08-03] 🔴 The entire research record was gitignored
`.gitignore` excluded `outputs/metadata/` wholesale, which included **`runs.jsonl` — the append-only
log backing every number in STATUS.md.** So the research record had **no version history, no backup,
and no way to detect a corrupting write**, even while this very file described it as an append-only
log whose past entries must never be silently rewritten. There was nothing enforcing or preserving
that. A `git clean` or a bad append would have silently destroyed the provenance of every published
result; the docs' own instruction to "regenerate with `rescore_logits.py`" is not a real recovery
path, since that needs TF plus the gitignored models and the 600 MB arrays.
**Fix:** `outputs/metadata/` is now tracked (101 KB total — `runs.jsonl`, thresholds, the analysis
JSONs, per-run history pickles). Also now tracked: the paper split's **protocol definition**
(`split_report.txt`, `known_classes.npy`, `zero_day_classes.npy`, ~3 KB) which is the provenance for
which classes are known vs zero-day. Large artifacts remain ignored.

### [FIXED 2026-08-03] `kg_precheck.py` persisted nothing, so the Phase-4 blocker was prose-only
The numbers **blocking all of Phase 4** — Bot cluster purity 87.9 / 86.6 / **44.4** % across CNN
seeds — existed only as text in STATUS.md and CHANGELOG.md. The script contained no `json.dump`,
no `np.save`, no `log_run`. They were unverifiable without a full re-run, and inconsistent with how
every other measurement in this project is recorded.
**Fix:** writes `outputs/metadata/kg_precheck.json`. Re-run 2026-08-03 — **numbers reproduce
exactly** (k=200 spread 43.4 pp, k=400 spread 28.3 pp; Web BF 2.5 pp, XSS 1.6 pp). The stale
"stable across seeds" claim in its docstring was also retracted in place.

### [FIXED 2026-08-03] Legacy temporal artifacts shared filenames with the current protocol's
`outputs/metadata/{class_names,zero_day_classes}.npy` were written by the superseded temporal-split
pipeline (`cnn3.py`/`ltn.py`) under the **same basenames** the paper split uses in
`data/processed/paper/`, with **incompatible contents**: the temporal `zero_day_classes.npy` lists
**DDoS and PortScan as zero-day** (both are KNOWN, trained-on classes now) and omits Heartbleed;
`class_names.npy` has 8 classes vs the paper split's 9. Names also carry mojibake
(`Web Attack ? Brute Force`).
**Not an active bug** — all 11 current-pipeline scripts correctly read the `paper/` copy; only
legacy `eval.py` read the metadata one. But re-running `cnn3.py`/`ltn.py` would have silently
overwritten it, and any *future* script reaching for the obvious-looking
`paths.METADATA/zero_day_classes.npy` would have scored against DDoS/PortScan as if unseen.
**Fix:** added `paths.METADATA_LEGACY` (`outputs/metadata/_legacy_temporal/`), moved the four legacy
artifacts there with a README explaining the collision, and repointed `cnn3.py`/`ltn.py`/`eval.py`.
**Moved, not deleted**, per the project rule.

### [FIXED 2026-08-03] `config.py` read `config.yaml` with the platform default encoding
`open(_PATH, "r")` uses cp1252 on Windows, so a single non-ASCII character anywhere in `config.yaml`
raised `UnicodeDecodeError` and broke every script that imports `config`. Hit while annotating the
`feature_transform` entry. **Fix:** explicit `encoding="utf-8"`.

### [FIXED 2026-08-03] `runs.jsonl` mixed two incompatible metric schemas
Records written before the 2026-07-27 `metrics.py` rewrite carried only `zd_pr_auc` (the blended
number); later records carry per-family + macro. Nothing in the file marked which was which, so a
naive read compared incomparable numbers. **`random_forest`, `xgboost` and `isolation_forest` had
never been re-scored on the corrected metric** — yet STATUS's corrected table and the Phase-3 table
both *quoted* macro figures for xgboost (0.6372) and isolation_forest (0.0628) that had **no logged
provenance anywhere**.
**Fix:** `baselines.py` gained `BASELINE_SEED` support and was re-run on seeds 42/43/44. All three
now carry per-family + macro on the current schema, at n=3.
**This was not cosmetic — it overturned a thesis-level claim.** RandomForest came back at Bot
**0.1311** [0.0576, 0.1933], statistically tied with the autoencoder (p=0.88) while beating it 0.50
on macro, which falsifies the strong form of the (A)/(B) reframing. See
[STATUS.md](STATUS.md) → "THE (A)/(B) FRAMING IS FALSIFIED IN ITS STRONG FORM".
**✅ Closed 2026-08-03:** `tracking.log_run` now writes a `schema` field (`v2-macro`), and
`load_runs(schema=...)` filters on it. All 71 existing rows were stamped retroactively by
`repair_runs_log.py`. Two further defects in the same file were found and fixed while doing it:
**every `stamp` was empty** (it defaulted to `""` and no caller ever passed one, so 97 rows had no
time information at all), and **the log was opened without an explicit encoding** — cp1252 on
Windows, the same bug class that broke `config.py`, which would corrupt or crash on any non-ASCII
class name (CIC-IDS2017 labels contain them).

### [FIXED 2026-08-03] 🔴 `meta_*.csv` timestamps are silently wrong under naive parsing
Found while building the KG's temporal-decay axis. `pd.to_datetime(meta["Timestamp"])` looks like it
works and is wrong **twice**:

1. **Dates are D/M/YYYY, not M/D/YYYY.** CIC-IDS2017 was captured Mon 3 – Fri 7 July 2017. Default
   parsing turns `"3/7/2017"` into **March 7** and `"6/7/2017"` into **June 7**, scattering a
   five-day capture across four months. The tell: every naively-parsed date has `day == 7` while the
   month varies — impossible for a 5-day capture.
2. **The clock is 12-hour with no AM/PM marker.** Observed hours are exactly {1,2,3,4,5, 8,9,10,11,12}
   — no 0, no 6, no 7, nothing above 12 — which maps one-to-one onto an **08:00–17:00 workday**
   ({8..12} AM, {1..5} PM) with no collisions. Uncorrected, **1 PM sorts before 9 AM**.

**Severity: total, not subtle.** Measured directly — **all 114,658 test rows change position**
between naive and corrected chronological order, and naive parsing additionally produces `NaT`.
Any ordering, growth rate, decay curve or time-window analysis built on the raw column is
meaningless. This would have silently wrecked the "adaptive" story that was committed to the same day.

**Fix:** `scripts/timeline.py` — corrects both defects, and **`preprocess_paper.py` now emits
`timestamp_{train,val,test}.npy` (datetime64[s]) as a typed artifact**, so consumers get the right
value by default rather than having to know the trap exists. `timeline.load_timestamps()` prefers
the artifact and falls back to (correct) parsing. `timeline.parse()` **raises rather than guessing**
if the date/hour pattern doesn't match the expected capture window.

**Validated against external ground truth, not fitted** — `timeline.selftest()` asserts every family
lands in its published window and is wired to fail loudly on any future data change:

| family | reconstructed | published schedule |
|---|---|---|
| Web Attack Brute Force | Thu 06 Jul 09:15–10:00 | Thu morning ✅ |
| Web Attack XSS | Thu 06 Jul 10:15–10:35 | Thu morning ✅ |
| Bot | Fri 07 Jul 09:34–12:59 | Fri morning ✅ |
| PortScan | Fri 07 Jul 13:06–15:23 | Fri afternoon ✅ |
| DDoS | Fri 07 Jul 15:56–16:16 | Fri afternoon ✅ |

Artifacts are gitignored (≈9 MB, regenerable in seconds):
```bash
.venv/Scripts/python.exe scripts/timeline.py --backfill
```

⚠️ **Consequence that outlives the bug:** because the attacks are *scripted into fixed windows*, any
growth-rate or decay result is partly measuring CIC-IDS2017's experimental design rather than the
attacks. Must be stated in the write-up — see STATUS → "LAST PHASE-4 GATE CLOSED".

### [FIXED 2026-08-03] Smoke-test artifacts were written into the real fusion-channel namespace
`*_SUBSET` runs train on a tiny slice for two epochs purely to prove the code path executes, but
wrote `y_prob_<tag>_test.npy` into `outputs/predictions/` alongside genuine channels, where an
undertrained array could plausibly be picked up as one. Five were archived by hand on 2026-08-02,
but the code would recreate them on the next smoke run — so the issue was left open.
**Fix:** `paths.predictions_dir(tag)` routes any tag containing "smoke" to
`outputs/predictions/_smoke_archive/` automatically; `cnn_paper.py` and `ltn_paper.py` use it.
The separation is now structural rather than a recurring cleanup chore.

---

## High

### [OPEN 2026-07-29] 🔑 Inference-time fusion cannot learn to weight a zero-day signal
**The structural wall, and the proposed way through it.** A fitted combiner must be calibrated on
validation data, which under this protocol contains **no zero-day flows by construction**. So it
cannot discover that a zero-day-specific channel is worth weighting. Measured, not feared:
`fusion_beaconlike.py` returned coefficients `[2.35, 0.02]` and zero macro change (0.6447 vs 0.6446).
**This also blocks the Knowledge Graph's intended contribution path** — `s_kg` feeds Decision Fusion
the same way and should be expected to hit the same wall.
`decision_fusion.md`'s own prescribed remedy ("train the fuser on a val split that includes zero-day
examples") is **impossible here** and is struck through in that document.

**Proposed fix — Leave-One-Class-Out (LOCO):** manufacture synthetic zero-day from *known* classes.
Hide one known attack class from CNN training entirely, retrain, and that class becomes a genuine
novel class in validation. Fit the combiner on that; rotate over the 8 known attack classes. Does not
leak — the 6 real zero-day families are never touched.

> 🔴 **REFUTED for `BeaconLike` (2026-07-29), before any compute was spent.** Measured how BeaconLike
> actually fires per class:
>
> | Known class | BeaconLike fires |
> |---|---:|
> | **PortScan** | **97.6%** |
> | DoS Hulk · DDoS · GoldenEye · FTP-Patator · SSH-Patator · slowloris · Slowhttptest | **0.0%** |
> | BENIGN | 22.7% |
>
> Every known attack except PortScan targets a well-known port (80/21/22), so BeaconLike is silent on
> them. **The rotation is therefore predictably null:** 7 of 8 folds hold out a class where the signal
> fires 0% → the combiner learns it is worthless; the 1 PortScan fold shows 97.6% → learns it is
> valuable **for the wrong reason** (port *scanning*, not C2 *beaconing* on 8080). Pooled, this
> reproduces `[2.35, ~0]`.
>
> **The originally-recommended "cheap probe: hold out PortScan first" was the worst possible choice**
> — the single fold guaranteed to yield a false positive.
>
> **The deeper result, which is more publishable than the fix would have been:** you cannot
> manufacture a synthetic zero-day that exercises BeaconLike in a Bot-like way, because **no known
> class in CIC-IDS2017 beacons.** LOCO is not broken — the known-class pool does not span the
> behavioural modalities of the unknown classes. So the fusion failure is not fixable by protocol alone.

**Revised proposal (NOT implemented):** apply LOCO to **modality-general** channels, not
class-specific axioms. Mahalanobis/MSP respond to *any* structurally novel class, so all 8 folds
exercise them. (⚠️ The "Mahalanobis has the best Bot lift, 4.3×" premise originally written here is
**retracted** — that was seed 42, best of 3; n=3 mean is 3.0×, range 1.2–4.3×, and the autoencoder is
both higher at 3.8× and far more stable. The argument for using a *modality-general* channel rather
than a class-specific axiom still stands.) Size-match the folds to
the zero-day regime by holding out the **rare** known classes (Slowhttptest 550, slowloris 580,
SSH-Patator 589), not the large distinctive ones.
- **Free probe, no training:** fit the Mahalanobis class-conditional Gaussians on 8 of 9 known classes
  instead of 9; class *k* becomes novel to the distance model without retraining the CNN. Optimistic
  (the embedding still saw class *k*) but it establishes whether the regime is learnable at all.
- Full version: 8 retrains.

⚠️ **Priority note:** per the thesis reframing in [STATUS.md](STATUS.md), all LOCO work is an attempt
to repair an **(A)-family** method (learn-what-attacks-look-like). The evidence favours **(B)-family**
methods (learn-what-normal-looks-like). **Run the Phase-3 autoencoder first.**

**Complementary alternative (proposed, NOT implemented) — conformal / benign-only calibration:**
calibrate each channel as a p-value against the **benign** distribution only, combine via Fisher's
method. Needs **no attack labels at all**, so the zero-day gap never arises; ~no training cost.
Weaker if channels are correlated, but an independent second shot.

### [RESOLVED 2026-08-03] 🔴 → ✅ PHASE-4 BLOCKER — resolved by measuring alternatives, not by fixing the CNN
The blocker below stands as measured. It is resolved by **not clustering a learned representation
at all**: `kg_readiness.py` measured cluster purity for all candidate representations and
**raw features win** — Bot purity 77.6 % (k=200) / 80.6 % (k=400), competitive with the CNN's good
seeds, far above its worst (44.4 %), with **no training-seed lottery** (residual k-means seed
sensitivity ~2.6 pp).

🔴 **The AE bottleneck — which STATUS recommended earlier the same day — was measured and REJECTED**:
Bot-purity spread **52.1 pp**, the *worst* of all options. The recommendation had reasoned from the
AE's reproducible Bot *ranking* (ρ=0.827). **Rank stability ≠ cluster stability.**

⚠️ **A larger finding came out of the same run: the KG's specified detection mechanism does not
work at all** — "unexplained cluster" scores lift ≤ 1.00× (at or below chance) across every
representation and threshold. See [STATUS.md](STATUS.md) → "PHASE-4 READINESS MEASURED".

**Original blocker, kept for the record:**

### [OPEN 2026-08-02] 🔴 PHASE-4 BLOCKER — the CNN embedding's open-set geometry is a seed lottery
The KG is specified to cluster `cnn_paper` embeddings. Bot cluster purity across **CNN seeds**
42/43/44 at k=200 is **87.9% / 86.6% / 44.4% — a 43.4 pp spread**; at k=400, 82.2% / 91.1% / 62.7%.
Varying only the *clustering* seed on a fixed embedding moves it 2.6 pp, so **clustering is stable
and the embedding is not.** The instability is **specific to Bot** — Web BF and XSS move 0.7–2.5 pp.
Independently confirmed: seed 44 is worst on both cluster purity and Mahalanobis Bot PR-AUC (0.0413,
1.2× ≈ chance), while its *classification* is unremarkable (macro 0.6396 vs 0.6446/0.6353).
**Equally good classifiers produce embeddings that do or do not isolate Bot.**

Consequence: the KG would cluster *stably* on the families the CNN already handles (web attacks,
0.92–0.95) and *unstably* on the one family where a memory/novelty mechanism would earn its place.
**Fix (proposed, NOT implemented — a design decision, not a bug fix):** choose the representation
before writing `kg.py` — (a) ensemble across CNN seeds / require a cluster to reproduce before
promoting it to a node; (b) cluster raw features (no training, no lottery); (c) cluster the
autoencoder's benign-trained 16-d bottleneck (the AE was the most *stable* Bot channel, spread 1.5×);
(d) accept and publish the variance. Full analysis: [STATUS.md](STATUS.md) → "PHASE-4 BLOCKER".

### [FIXED 2026-08-03] 🔁 Component status was duplicated across 4+ files — a recurring source of drift
**This was a process defect, and it caused the same error THREE times in three sessions.**

> ✅ **FIXED 2026-08-03, as the proposed plan below specified.** `docs/STATUS.md` →
> "Component Status" is now the **single source of truth**, carrying a banner saying so.
> `CLAUDE.md`'s table was replaced by a one-line "you are here" pointer; the end-of-session
> checklist now names the exact three living docs; `roadmap_gap_analysis.md` and
> `target_architecture.md` point at STATUS instead of restating it.
>
> 🔴 **The third occurrence, found by the audit that triggered this fix, is the reason the naive
> version of the plan would have made things worse:** STATUS's own Component Status table — the one
> nominated as canonical — was itself **the stalest table in the repo.** It still described the
> autoencoder as `n=1 / macro 0.1000 / Bot 3.6× / 0.0000 recall on web attacks` (all four superseded
> the previous day, 400 lines above it in the same file), cited "PortScan/DDoS strongly covered"
> (a claim this file explicitly forbids), said the behaviours were "not yet wired into LTN" (wired
> since 2026-07-27), and had **no rows at all** for `cnn_paper.py` / `baselines.py` / `novelty.py`,
> pointing instead at the superseded `cnn3.py` and `eval.py`. **Collapsing to a single source
> without first correcting it would have propagated all of that.** The table was rewritten before
> being promoted. Verify only one table exists:
> ```bash
> grep -rln "^| Component | Status" --include=*.md . | grep -v .venv
> ```

**Original issue, kept for the record:**

Component/phase status is written out independently in at least four places:
`CLAUDE.md` ("Current state" table) · `docs/STATUS.md` ("Component Status" + "Remaining Work" +
"Open Decisions") · `docs/target/roadmap_gap_analysis.md` ("Built vs. Planned") ·
`docs/target/target_architecture.md` ("Component Status Summary"), plus the phase table in
`docs/target/conference_roadmap.md §1b`.

**Observed failures, both the same shape — update one table, miss the parallel one:**
1. **2026-07-29** — the reference-tier audit found `roadmap_gap_analysis` and `target_architecture`
   still listing behaviour abstraction as "⚠️ Partial" and the LTN as plainly "✅ Built", long after
   both had changed. That audit is what created most of this file.
2. **2026-08-02** — after Phase 3 was built, run and multi-seeded, `STATUS.md`'s component table was
   updated but **`CLAUDE.md`'s still said "Anomaly pillar: ❌ Not built — decision needed first."**
   `CLAUDE.md` is auto-loaded into every session, so it was the single worst place to leave stale.
   Caught only by an explicit post-merge audit, not by the normal workflow.

**Why it recurs:** the end-of-session checklist in `CLAUDE.md` says "flip component statuses" without
naming *which files*, so it is satisfied by updating whichever table the author is looking at.

**Fix (proposed, NOT implemented — do this before Phase 4 status starts changing):**
- Make **`docs/STATUS.md` → "Component Status" the single source of truth.** It is already the most
  detailed and the most reliably updated.
- Replace the tables in `CLAUDE.md`, `roadmap_gap_analysis.md` and `target_architecture.md` with a
  one-line pointer to it. `CLAUDE.md` may keep a *minimal* "you are here" line (current phase +
  what's blocking) since it is the onboarding file — but not a full component table that can rot.
- Keep `conference_roadmap.md §1b` as the canonical **phase-numbering** table (a different thing from
  component status) and cross-link the two explicitly.
- Add a line to `CLAUDE.md`'s end-of-session checklist naming exactly which file to update.
- Cheap verification afterwards: `grep -rn "Not built\|✅ Built\|⬜" --include=*.md .` should return
  hits from **one** file, not four.

### [OPEN] Behaviour validation tables were measured on the superseded temporal split
`behavior.py`'s built-in validation, and the coverage table in
[behaviour_abstraction_current.md](implementation/behaviour_abstraction_current.md), report PortScan
(0.955) and DDoS (0.62) as **zero-day** coverage. Under the paper split **both are known, trained-on
classes**, so the behaviours' strongest coverage contributes nothing to the zero-day metric. The
families that remain zero-day are exactly the ones the table shows as weak/partial.
**Fix:** regenerate the validation tables against `data/processed/paper/`. Until then, do not cite
"PortScan/DDoS are strongly covered" as evidence for the symbolic approach.

### [OPEN] `HighEntropy` is not true entropy
Named honestly in code and docs, but it is packet-length **standard deviation**, not Shannon entropy
of the payload — flow features contain no payload bytes. Any axiom or explanation phrased as
"high entropy ⇒ encryption/obfuscation" is overclaiming. Either keep the approximation and always
qualify it, or rename to `PacketSizeVariance`.

### [MITIGATED 2026-08-03] `RepeatedConnections` / `BeaconLike` reach consumers unguarded
Both issues below are real and unchanged, but the *downstream* risk they posed to Phase 4 is now
handled explicitly rather than by a doc note. `behavior.py` gained (additively — the frozen
7-column `behaviour_matrix()` and `BEHAVIOUR_NAMES` are untouched, so every Phase-2 LTN result
remains valid):

- **`BEHAVIOUR_KIND`** — declares each behaviour as `graded` / `binary` / `constant`, so a consumer
  can check rather than assume continuity.
- **`active_behaviour_names()` / `active_behaviour_indices()` / `active_behaviour_matrix()`** — drop
  constant columns automatically. If the IP/port side-table is ever wired in, flipping
  `REPEATED_CONNECTIONS_AVAILABLE` re-includes the column with no consumer change.

`knowledge_graph.md` now instructs the KG to use `active_behaviour_matrix()`.

### [OPEN] `BeaconLike` is binary, not fuzzy
It returns exactly 0.0 or 1.0 (`~np.isin(dst_port, WELL_KNOWN_PORTS)`), unlike the other six graded
behaviours. Deliberate — port number is not ordinal, and a magnitude ramp was tried and dropped for
being anti-correlated with Bot (ROC 0.3995). But consequences must be respected downstream: it
contributes a hard 0/1 to product-t-norm conjunctions, and as a KG `exhibits` edge weight it will
give a bimodal distribution rather than a spread. Relevant to Phase 4.

### [WONTFIX-for-now] `RepeatedConnections` returns constant zero
`REPEATED_CONNECTIONS_AVAILABLE = False`; the behaviour is always 0.0.
⚠️ **The historical blocker is resolved** — the IP/port/timestamp side-tables
(`data/processed/paper/meta_{train,val,test}.csv`) now exist, aligned row-for-row, since the
2026-06-18 dataset upgrade. The behaviour is **unblocked but unwired**, which is a deprioritization
decision, not a data constraint. No longer motivated as a Bot fix (the oracle result located Bot's
signature in per-flow features); may still help Infiltration / lateral movement.
**A constant-zero column is silently carried through `behaviour_matrix` (column 6) and into any
consumer that does not filter it** — including, prospectively, the KG.

---

## Medium

### [OPEN 2026-08-03] 🔴 SEEDS ARE NOT COMPARABLE ACROSS SESSIONS — a session/environment effect
**The most consequential methodological finding of the session, and it invalidates a comparison
this project has been making since Phase 1.**

Extending the CNN from n=3 to n=6 produced macro values that declined **perfectly monotonically with
seed number** (ρ = **−1.000** for XSS, −0.943 for macro). Seed *number* has no causal meaning, so a
perfect correlation with **run order** points at something drifting across the sweep, not at seed
randomness. Probability of a perfect ordering by chance at n=6 is 2/720 ≈ **0.3 %**.

**Confirmed by an independent channel.** The LTN control, retrained the same day, dropped the same way:

| channel | seeds 42–44 *(earlier sessions)* | seeds 45–47 *(today)* | Δ |
|---|---:|---:|---:|
| CNN | 0.6398 | 0.6101 | **−0.0298** |
| LTN control | 0.6194 | 0.5784 *(n=1 so far)* | **−0.0410** |

Two unrelated architectures shifting the same direction by a similar amount is a **session effect**,
not seed variance.

**Most likely cause:** TensorFlow on CPU is not bit-deterministic even with a fixed seed — thread
scheduling changes float accumulation order. Concurrent analysis work (KG runs, significance tests,
rescoring — at one point a rescore ran *while* a training job was in flight) raised CPU contention
steadily across the sweep, which reproduces exactly this pattern.

#### 🔴 What it invalidated, including a claim made hours earlier in the same session

1. **"n=3 understated seed variance by 4–5×" — CONFOUNDED.** Part of the widened n=6 range is session
   effect, not seed randomness. Do not cite that figure.
2. **"C2 must be reopened" — WITHDRAWN.** That alarm came from comparing a *depressed* CNN (n=6, half
   trained today) against a *non-depressed* control (n=3, all trained earlier):

   | C2 gap computed... | value |
   |---|---:|
   | earlier-session only | **+0.0204** |
   | today-session only | **+0.0317** *(provisional)* |
   | **mixed — the error** | **+0.0055** |

   **Mixing sessions manufactured the collapse.** Within-session the CNN's advantage is preserved or
   larger. The original C2 conclusion stands.
3. **Unaffected: the CNN/AE double dissociation.** Both channels are measured on the *same* seeds, and
   the gaps are 0.5–0.86 — a common −0.03 shift cannot touch it. It survives at n=6, 6/6 seeds per
   family.

#### The protocol change this forces

**Compare within session, never pooled across sessions.** Any multi-seed comparison must use seeds
trained in the same environment, or explicitly model the session as a blocking factor. Pooling seeds
from different sessions silently compares models trained under different conditions.

⚠️ **Every n=3 range published in this project predates this finding** and was computed from seeds
trained in one or two sessions. Those ranges are probably *too narrow* (they miss cross-session
variance) while the n=6 ranges are *too wide* (they conflate it with seed variance). Neither is a
clean estimate of seed variance alone.

**The clean test, not yet run:** retrain seed 42 on an idle machine. If it reproduces 0.6446, seeds
are fine and the environment is the whole story; if it returns ~0.60, the effect is environmental and
the magnitude is measured directly.

> **Process note.** The confound was flagged *one message after* the C2 collapse had already been
> reported as a headline finding. The project's own rule — *"a point-estimate gap is not a result"* —
> was applied rigorously to old claims and not to a new one of my own. That asymmetry is the failure
> mode worth remembering here, more than the confound itself.

### [FIXED 2026-08-03] Heartbeat monitors produced TWO false alarms — both from launcher design
The heartbeat rule (CLAUDE.md non-negotiable #2) watches **log growth**. Twice in one session the
monitor cried wolf, and **both times the fault was the launcher, not the job**:

1. **"STALLED" on a job that had already finished.** `run_long.sh`'s liveness check kept matching
   after exit, so log-growth stopping was read as a hang rather than completion.
   **Fix:** check the process explicitly before declaring a stall; report completion otherwise.
2. **"STALLED" on a training run that was working perfectly.** `seed_sweep.sh` piped each run
   through `| tail -5`. **`tail` buffers until EOF**, so nothing reached the log for the whole
   ~20-minute run. Diagnosed by evidence rather than the alert: the process had **7,381 s of CPU**,
   a 1.6 GB working set, and had just written `cnn_paper_s45_best.keras`.
   **Fix:** launchers must not pipe long jobs through `tail`/`head`, and
   `lint_conventions.py` now **fails** on that pattern (plus `grep` without `--line-buffered`).

**The transferable lesson, now encoded:** *a heartbeat rule is only as good as the launcher
preserving the signal it depends on.* The rule was strengthened earlier the same day and then a
launcher written hours later silently broke its precondition. A false alarm is not harmless — the
next reader discounts the real ones.

### [OPEN 2026-08-01] `ps aux` liveness checks are flaky on Windows Git-Bash — false "process died" reads
While heartbeat-monitoring the C2 seed sweep (`cnn_paper.py` background training), a `ps aux | grep -c
"[c]nn_paper.py"` liveness check reported `proc_alive=0` and the monitor declared the process dead at
epoch 2 — no traceback, no error, log simply stopped growing for one poll tick. Checked immediately
after: the process was still running (`ps -ef` showed it, PID matched the launch), and the log resumed
growing within 15 seconds, training completed epochs 3, 4, 5 normally. **The process never died — the
`ps` enumeration missed it for a single poll under MSYS2/Git-Bash's WINPID-mapped process listing**,
plausibly during a Windows I/O syscall (checkpoint save) that briefly makes the process invisible to
that particular `ps` invocation.
**Fix (applied):** treat **log-growth staleness** (no new bytes for N consecutive polls) as the
authoritative dead/hung signal, not a single `ps` miss. `ps` output can still be logged as an advisory
data point but must not trigger an early exit on its own. Require sustained staleness (this session
used 12 ticks × 90s = 18 min) before declaring failure, matching how genuinely stuck runs actually
behave (they stop writing to the log, they don't intermittently vanish from `ps`).

### [OPEN] PowerShell `*>>` batch logs are mixed-encoding
When a PowerShell script redirects a Python subprocess's output with `*>> $log`, the resulting file
mixes **UTF-8** (Python's own stdout, passed through) with **UTF-16LE** (PowerShell's `Add-Content`
header lines), interleaved with no marker. Naive single-encoding reads (`iconv -f UTF-16LE`, plain
`Get-Content`) either garble the UTF-8 portions into CJK-looking mojibake or silently truncate.
Cost real time **3 separate times** in the 2026-07-27 session.
**Workaround:** locate section markers by searching raw bytes for both `text.encode('utf-8')` and
`text.encode('utf-16-le')`, then decode each segment with whichever codec matched.
**Real fix:** don't mix `Add-Content` with `*>>` redirection in the same file — emit batch headers
from the Python side (`print`) so the whole log is one encoding.

### [OPEN] Double class-weighting in `cnn3.py` / `cnn_paper.py`
Both `class_weight=` in `fit()` **and** the focal-loss `alpha` weight imbalance, compounding the
effect. Not incorrect, but the effect multiplies — pick one when tuning.
Detail: [cnn_current.md](implementation/cnn_current.md).

### [FIXED 2026-08-02] Smoke-test artifacts polluted `outputs/predictions/`
Five undertrained outputs from `LTN_SUBSET`/`CNN_SUBSET` smoke runs
(`y_prob_smoke{,_perf,_ax6,_seed43,_test}_test.npy`) sat in the same directory and the same
`y_prob_*_test.npy` namespace as real fusion channels, where one could plausibly be picked up as a
channel. **Fix:** moved to `outputs/predictions/_smoke_archive/` with a README explaining what they
are. **Moved, not deleted** — per the project rule that artifacts are not destroyed, even worthless
ones. 62 real channels remain in the namespace, none of them smoke.
**Still open (minor):** the smoke path in `ltn_paper.py`/`cnn_paper.py` will recreate them in
`outputs/predictions/` on the next `*_SUBSET` run — a proper fix would write smoke output to the
archive subdirectory directly.

### [OPEN] TensorFlow can be blocked by Windows Smart App Control
`import tensorflow` fails with `ImportError: DLL load failed … An Application Control policy has
blocked this file`, on a **different native DLL each attempt**. Root cause (diagnosed 2026-07-27):
Smart App Control (`VerifiedAndReputablePolicyState=1` in
`HKLM\SYSTEM\CurrentControlSet\Control\CI\Policy`) rejecting TF's unsigned compiled wheels. Not a
code or environment fault. numpy/sklearn/scipy/xgboost are unaffected — `baselines.py` and
`skyline_oracle.py` still run. **Resolution:** user disables Smart App Control in Windows Security
(reversible without reinstall on build ≥ 26200.8116). **Diagnose via** Event Viewer → Applications
and Services Logs → Microsoft → Windows → CodeIntegrity → Operational.

---

## Low

### [OPEN] `history['accuracy']` is a 5,000-sample proxy in `ltn.py` / `ltn_paper.py`
The train-accuracy curve is computed on a fixed, unshuffled slice rather than the full train set.
Affects plots only, not model selection (which uses `val_loss`).

---

## Resolved

### [FIXED 2026-07-27] ω=1.0 collapsed on 2 of 3 seeds
`LTN_OMEGA_MODE=fixed` made the SAT weight independent of CE's actual magnitude, so whether SAT or CE
dominated the early-training gradient was decided by random initialization. When SAT won that window
the model never learned to classify, and best-by-val-loss early stopping locked it in by ~epoch 10
(best epoch 1–2, macro 0.052 / 0.037). ω=2.0 was the same dynamic with zero margin (100% reproducible).
**Fix:** `LTN_OMEGA_MODE=ratio` scales SAT to a fixed fraction of CE. Re-ran the same 3 seeds —
**zero collapses**, tight macro range 0.58–0.61. `ratio` is now the code default.

### [FIXED 2026-06-18] Focal-loss shape bug silently broke `model.fit()` training
`tf.one_hot(y_true, n)` where Keras passes `y_true` as `(batch, 1)` — the one-hot then broadcast into
a `(batch, batch, n)` garbage tensor, freezing val_loss and pinning accuracy near-random. Confirmed by
a controlled race (plain CE → 0.996 val-acc; focal as-is → stuck at 0.50; focal fixed → 0.996).
**Fix:** flatten `y_true` to `[-1]` before one-hot, in both `cnn_paper.py` and `cnn3.py`. The LTN
custom loop was unaffected (it passes `(batch,)` directly). **Any new loss function must apply the
same `reshape([-1])`.** Also fixed alongside: callback monitors (`val_sparse_categorical_accuracy`)
that had silently disabled early-stopping and checkpointing.

> ⚠️ **Open caveat on a published baseline number — do not lose this when writing up.**
> The **old temporal CNN baseline (0.6689 PR-AUC) may itself have been hampered by this bug**, since
> it was trained with the broken focal loss. That baseline is the denominator in the headline legacy
> comparison *"LTN 0.4529 vs CNN 0.6689"* — if the CNN was handicapped, the LTN's deficit against a
> clean baseline would be **larger**, not smaller. The temporal CNN has **never been retrained with
> the fixed loss**, so this remains unquantified. Either retrain it before citing that comparison, or
> state the caveat explicitly in the write-up. (The LTN custom loop was unaffected, so the *direction*
> of the comparison is not in doubt — only its magnitude.)

### [FIXED 2026-06-18] Behaviour abstraction was dead code
`scripts/behavior.py` had misaligned feature indices (`RATE_FEATURES=[5,6,7]` actually pointed at
packet-length fields), was never imported, and never generated thresholds. **Rebuilt:** verified
indices via `check.py`, vectorised, fuzzy `[0,1]` outputs, data-driven thresholds saved to
`outputs/metadata/behaviour_thresholds.npy`, with a built-in validation harness. Two bugs were caught
*by* that validation: flag-count `ProtocolAnomalies` fired 45% on benign / 0% on attacks (dropped),
replaced by `ScanProbe`. Detail:
[behaviour_abstraction_current.md](implementation/behaviour_abstraction_current.md).

### [FIXED 2026-06-18] `utils/config.py` was stale orphaned code
Belonged to an abandoned raw-PCAP/payload pipeline (`PAYLOAD_LEN=1500`, 3 classes, time windows);
imported by nothing. **Deleted** along with the `utils/` directory. Origin of the diagram's
"1500 bytes" boxes. Replaced by `config.yaml` + `scripts/config.py`.

### [FIXED 2026-06-18] No dependency manifest
`requirements.txt` now pins every dependency exactly (TF 2.15.1 / numpy 1.26.4 / scikit-learn 1.4.2 /
xgboost 3.2.0 / networkx 3.2.1 / python-louvain 0.16 / shap 0.45.1 / pyyaml 6.0.3 / psutil 6.1.0).

⚠️ **Partial — the Python version is still not machine-enforced.** `requirements.txt` documents
"Target: Python 3.11" in a comment, but there is **no `.python-version` or `pyproject.toml`
`requires-python`**, so nothing prevents creating the venv on a wrong interpreter. TF 2.15 supports
only Python 3.9–3.11; on 3.12+ the install fails confusingly. Low priority (the venv exists and
works), but the original issue is not fully closed.

### [FIXED 2026-06-18] `.gitignore` did not match real artifact locations
**What was wrong:** the old `.gitignore` only ignored `data/raw_pcaps/`, `data/processed/*.npy` and
`data/processed/chunks*/` — paths belonging to the **abandoned payload pipeline**, which never
existed on disk. Meanwhile the real pipeline wrote large artifacts to the **repo root**
(`X_test.npy` ~600 MB, `X_*_emb.npy` ~300 MB each, `*.keras`, `*.pkl`, `clean_*.csv`,
`features_*.csv`, `*.png`) — **none of which were ignored.** Risk was committing hundreds of MB of
binaries.
**Fix:** rewritten to directory-based ignores matching the reorganised layout; `outputs/figures/` is
intentionally tracked. Git history was checked — only `.gitignore` and an old `preprocess_friday.py`
had ever been tracked, so **no large binaries were ever actually committed.**

### [FIXED 2026-06-18] Unused binary split vars in `cnn3.py`
`y_train_b` / `y_val_b` computed but not used downstream. Removed.

### [FIXED 2026-07-29] `preprocess.py` hardcoded its input path
Line 27 read `os.path.join(paths.ROOT, "data", "raw_csv_full")`, bypassing `paths.py` — while
`paths.RAW_CSV` still pointed at the abandoned `data/raw_csv`. Violated the project's own rule that
all locations come from `paths.py`. **Fix:** added `paths.RAW_CSV_FULL` (current) and `paths.PAPER`,
kept `paths.RAW_CSV` marked legacy, and pointed `preprocess.py` at the constant.

---

## Superseded (real when written; scoped to code no longer in use)

### [SUPERSEDED] LTN axioms are label tautologies
`scripts/ltn.py`'s original axioms used only ground-truth labels, restating the supervised target, so
they could not help zero-day detection. **Fixed 2026-06-18** by re-grounding Ax3/Ax4 on behaviour
predicates — and `ltn.py` itself was then superseded by `ltn_paper.py`, whose axiom set is
Ax1/Ax2 (label anchors, legitimate consistency constraints) + Ax3–Ax6 (behaviour-grounded).
The current concern is the opposite one: the behaviour-grounded axioms are *not* tautological but
still **cost macro PR-AUC**. See [STATUS.md](STATUS.md).

### [SUPERSEDED] Dead fuzzy operators in `ltn.py`
`fuzzy_and`, `fuzzy_not`, `fuzzy_forall` defined but never used (SAT aggregation was inlined).
Cosmetic, and scoped to the superseded legacy script.

### [SUPERSEDED] Adaptive ω ignores Ax3/Ax4
ω adaptation in the legacy `ltn.py` used only `mean(ax1_sat, ax2_sat)`. `ltn_paper.py` uses
`LTN_OMEGA_MODE` (`fixed` | `ratio`) instead, so this specific defect no longer exists.

### [FIXED 2026-06-18] `model_focal.keras` provenance unknown
A stale experiment artifact not produced by any script. **Deleted** during the artifact cleanup.

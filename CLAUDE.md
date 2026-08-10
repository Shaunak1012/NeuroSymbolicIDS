# CLAUDE.md — Session Onboarding Guide

> This file is auto-loaded at the start of every Claude Code session. It tells you (Claude) and any collaborator how to get oriented fast, what state the project is in, and how to work in this repo. **Keep it current.**

---

## 🚨 NON-NEGOTIABLES — read these eight lines first, every session

Everything below this block is context. **This block is rules.** Every one of them
exists because it was *already broken at least once* — the incident is named so
nobody re-litigates it. They lapse during long tool-heavy stretches, which is
exactly when they matter, so re-read this block after every merged PR.

| # | Rule | Broken when |
|---|---|---|
| 1 | **End every response with `→ Next model:`** — including one-line acknowledgements | 2026-07-27: silently stopped mid-session during tool-heavy turns |
| 2 | **Long job ⇒ `scripts/run_long.sh`**, never a bare background launch. Completion notifications are *not* monitoring — they don't cover stalls | 2026-08-03: lapsed on **six** jobs in one session |
| 3 | **Multi-seed BEFORE writing a number down.** n=1 is provisional, always | **Five** retractions; only the fifth was caught pre-publication |
| 4 | **Retract in place** — strike through, keep the reasoning, never silently delete or rewrite | The living docs' credibility depends entirely on this |
| 5 | **Branch → PR → local `--no-ff` merge.** Never commit straight to `main` | 2026-08-02: 20 commits merged with no PR ever opened |
| 6 | **Run `python scripts/lint_conventions.py` before ending a session** | The same cp1252 bug was fixed **3×** as separate incidents before being linted |
| 7 | **Component status lives ONLY in `docs/STATUS.md`** | Same drift error in 3 consecutive sessions |
| 8 | **Timestamps go through `scripts/timeline.py`** — never parse `meta_*.csv` directly | Naive parsing reorders **all 114,658** test rows |

> **Why a rule lapses here, so you can catch it in yourself:** each of these has a
> *plausible-but-wrong substitute* sitting next to it — the harness notifies on
> completion (feels like monitoring), a point estimate looks like a result, one
> updated table feels like updating the docs. When something feels already handled,
> check *which* rule you actually satisfied.

---

## What this project is

**NeuroSymbolic-IDS** — an *Explainable & Adaptive Neuro-Symbolic Intrusion Detection System* for the CIC-IDS2017 dataset. Goal: detect both known and **zero-day** network attacks by combining:
1. a **1D CNN** (learned features + class probabilities),
2. **symbolic logic** (LTN-style fuzzy axioms grounded in network behaviour),
3. an **adaptive Knowledge Graph** (memory of emerging patterns),
fused into an explainable benign/malicious alert.

Input is **CIC-IDS2017 flow-feature CSVs** (**68** numeric features/flow — not 70; several frozen docs still say 70 and are banner-marked). The "Raw PCAP" boxes in the architecture diagram are conceptual; payload-level processing is future work.

**Reality check on the goal above:** as of Phase 2, the symbolic pillar does **not** beat the neural baseline — every symbolic injection point tried (loss-level, representation-level, inference-level) costs macro zero-day PR-AUC or changes nothing. The project's current contribution is the *anatomy of why*, and as of 2026-08-03 that anatomy has a **mechanism**: a closed-set discriminative model learns only the features that separate the classes it is trained on, so a novel class is reachable exactly to the extent its signature overlaps that basis — and *unreachable and unstable* otherwise (Bot: 0/8 feature overlap, cross-seed rank ρ = −0.090). Don't write or reason as though the fusion story is established.

## ⚡ First thing every session

1. Read **[docs/STATUS.md](docs/STATUS.md)** — current component status, priorities, open decisions, last results.
2. Skim **[docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md)** — what's broken and why.
3. Check recent **[docs/CHANGELOG.md](docs/CHANGELOG.md)** entries.
4. **State it back, briefly, before starting work** — one line naming the current phase and what's blocking or next (per STATUS's "RESUME HERE"). This is a forcing function, not a formality: reading the files silently doesn't confirm the state actually landed. If the one-liner doesn't match what STATUS.md says, that's a sign it wasn't really absorbed — reread before proceeding.
Then proceed with the task.

## ⚡ Last thing every session

Update the **living documents** so the next session starts clean. These are the *only* three files
that record project state — nothing else needs touching:
- **[docs/STATUS.md](docs/STATUS.md)** — flip statuses in **"Component Status"** (the single source
  of truth), update **"Remaining Work"**, **"Open Decisions"** and **"Last Measured Results."**
- **[docs/CHANGELOG.md](docs/CHANGELOG.md)** — add a dated entry for what changed (newest first).
- **[docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md)** — open new issues, mark fixed ones.

If a *result* changed, it must also be reproducible from `outputs/metadata/runs.jsonl` (now
version-controlled) — a number quoted in a doc with no logged run behind it is a defect, and there
have been three.

**Then run the lint** (non-negotiable #6). It mechanically checks the conventions that have
actually lapsed, and names the incident behind each one:

```bash
python scripts/lint_conventions.py
```

✅ **Component status now has ONE home (fixed 2026-08-03).** Change it in
**[docs/STATUS.md](docs/STATUS.md) → "Component Status"** and nowhere else. This file,
`docs/target/roadmap_gap_analysis.md` and `docs/target/target_architecture.md` used to carry
parallel tables; they now point at STATUS instead. Phase *numbering* (a different thing) stays
canonical in [conference_roadmap.md §1b](docs/target/conference_roadmap.md).

> **Why this rule exists.** The duplication caused the same drift error three times — 2026-07-29
> (target docs stale), 2026-08-02 (this file claimed Phase 3 was "not built" after it had been built,
> run and multi-seeded), and 2026-08-03 (STATUS's *own* table still said the autoencoder was n=1 with
> "0.0000 recall on web attacks", both superseded the previous day). The checklist said "flip
> component statuses" without naming files, so it was satisfied by updating whichever table you
> happened to be looking at. Verify there is still only one table:

```bash
grep -rln "^| Component | Status" --include=*.md . | grep -v .venv
```

## Current state (one-line pointer — full table in STATUS.md)

**Phases 0–4 done. Phase 5 (Decision Fusion) is 🟡 PARTIALLY ENTERED. Phases 6–7, 7.5 and R not
started.**

> 🔴 **This block said "Phase 4 … awaits sign-off. Not started" until 2026-08-05 — while Phase 4 had
> been built, multi-seeded AND completed with explainability two sessions earlier.** Fourth
> occurrence of the component-status drift defect, in the one file auto-loaded into every session.
> It survived because the 2026-08-04 session updated STATUS/KNOWN_ISSUES but not this pointer.
> **If you change phase state, change it here too** — this line is the first thing the next session
> reads.

Three established results: **(1)** a **double dissociation** between the CNN (`cnn_paper.py`) and the
autoencoder (`autoencoder_paper.py`) — 3.9–40 SD of the measured noise floor, the only comparative
claim in the project with that margin, though it is a dissociation between *two models*, **not** two
method families; **(2)** the CNN's Bot failure is **representational** — 100% of Bot flows are
classified BENIGN, Bot's discriminative features have 0/8 overlap with the known-class task's, and
the resulting Bot ranking is **noise** (cross-seed ρ = −0.090); **(3)** **training is not
reproducible at fixed seed** (SD 0.0222 — see the noise floor below), which retracted C2 and demotes
every within-tier comparison this project spent months on.

👉 **Component-by-component status: [docs/STATUS.md](docs/STATUS.md) → "Component Status".**
Do not restate it here — that is exactly what kept rotting.

**Next action (resume here — as of end of 2026-08-05):**
1. **Multi-seed two n=1 results that currently read as findings**: `ANOM_SEED=43/44 anomaly_zoo.py`
   (Deep SVDD's Bot sits *inside* the AE's own n=3 range) and `BASELINE_SEED=43/44
   baselines_classic.py` (the whole Tier-A Bot column). Cheap; five single-seed retractions precede this.
2. **C4** — the feature transform is still justified by the contaminated overall-binary metric.
3. **Decide the write-up spine** — the field-metric gap now has *three* independent demonstrations.

**Done as of 2026-08-05:** Phase 4 complete · Phase 5 partial (significance, parameter-free fusion,
n=6; calibration/latency/fitted-fusion outstanding) · **Phase 7.5 Tiers 1 AND 2 complete** ·
**the ablation** (only the KG earns its place) · **the base paper's metric set computed for the first
time** · **method tiers A/B/C/D** (11 new methods). Phase 6 cross-dataset is **blocked** — no
CIC-IDS2018 locally.

⚙️ **DETERMINISM IS NOW ON** (`scripts/determinism.py`, intra=16/inter=2 — byte-identical across two
full 50-epoch runs). **The SD 0.0222 floor applies to PRE-flag runs only, and pre/post-flag runs are
different populations — do not pool them.** Separately, **data-split SD (0.0228) ≈ training SD
(0.0222)**: shared-split comparisons cancel it, but **an absolute number carries ≈0.032**.

### 🔴🔴 THE NOISE FLOOR — read before citing ANY number in this project

**Training is not reproducible at fixed seed.** Six runs of seed 42, identical code, idle machine:
**SD 0.0222 · range 0.0621 · CV 3.6 %**. No TF determinism flags are set, so thread scheduling
changes float accumulation between runs.

**Express every delta as a multiple of this SD. That ratio, not the raw number, decides survival.**

| claim | delta | ÷ SD | verdict |
|---|---:|---:|---|
| Double dissociation (XSS / Web BF) | +0.90 / +0.82 | 40 / 37 | ✅ established |
| Double dissociation (Bot) | +0.0868 | 3.9 | ✅ established |
| CNN+KG fusion | +0.0527 | *paired* | ✅ direction (3/3 seeds); magnitude 0.027–0.088 |
| **C2: CNN vs LTN control** | +0.0204 | **0.9** | 🔴 **RETRACTED — within noise** |

🔴 **C2 is retracted on controlled grounds.** It was closed in the CNN's favour with a paired
bootstrap (p=0.001) earlier the same day. The gap is **smaller than re-running one model twice**.
**A flow-level significance test cannot rescue a delta below the pipeline's own reproducibility** —
the most important methodological lesson in this project.

⚠️ **`cnn_paper = 0.6446` is the MAX of 11 runs, not a typical result** (mean 0.6217). The honest
reproducible baseline is the **ensemble, 0.6356**.

⚠️ **Every n=3 range in the docs is an artefact.** The CNN's "tight" 0.0093 spread is **0.4 SD** —
less than half a single re-run's noise. Never cite an n=3 range as evidence of stability.

🧭 **Three claims were asserted and withdrawn in one session** ("n=3 understated variance", "session
effect", "C2 must be reopened") — all competing explanations for this one unmeasured quantity. Four
training runs settled what hours of observational comparison could not. **Measure variance before
explaining it.**

### What changed on 2026-08-03 (read this before citing anything older)

A full audit + remediation session. It was scoped as bookkeeping, but the re-runs it required
**overturned two documented claims and answered the last open research question.**

🔬 **"Why does the CNN fail on Bot?" is ANSWERED** (`scripts/bot_failure_analysis.py`, 4 hypotheses
pre-registered before running). The failure is **representational, not informational**:
- **100% of Bot flows are classified BENIGN** (all 3 seeds, mean p(BENIGN)=0.9984) — Bot is not
  ambiguous to the CNN, it is confidently asserted benign.
- The features separating Bot from benign have **0/8 overlap** with those the known-class task needs.
- So the CNN's Bot ranking is **noise**: cross-seed Spearman **ρ = −0.090**, vs 0.68–0.83 for every
  other family. RandomForest is the same (0.068); **the autoencoder is not (0.827).**
- **One cause, four symptoms** — this explains the Phase-4 purity lottery, the Mahalanobis Bot
  spread, and RF's Bot swing simultaneously. Not an information limit (oracle PR-AUC 0.9988).

🔴 **The (A)/(B) thesis reframing is FALSIFIED in its strong form.** **RandomForest — a supervised
(A)-family method — ties the autoencoder on Bot** (0.1311 vs 0.1314, paired bootstrap p=0.88) while
beating it 0.50 on macro. "(B) methods are needed to reach Bot" is **dead**, and so is "no channel
sits at both ends of the frontier" (RF does). ⚠️ **The CNN-vs-AE double dissociation survives and is
now statistically significant — but it is a dissociation between two MODELS, not two FAMILIES.**
Do not write it up as an (A)-vs-(B) result.

✅ **Significance tests are RUN** (`scripts/significance.py`). **C2 closes in the CNN's favour** —
it does beat the LTN control (+0.0204, p=0.001) despite overlapping seed ranges, because the paired
test cancels flow-noise common to both. ⚠️ **Flow-level uncertainty only**: at n=3 the Wilcoxon
floor is p=0.25, so **no seed-level claim in this project can reach p<0.05** — that needs n≥6 seeds.

🔴 **A RETRACTION WAS REVERSED: "on macro the CNN beats XGBoost" is n.s. (p=0.80).** The 2026-07-27
retraction of *"XGBoost ≈ CNN"* compared two point estimates with no test. The original claim was
right. Lesson, symmetric to the earlier ones: **a point-estimate gap is not a result in either
direction.**

### Standing cautions (still current)

🔴 **Do NOT repeat the "modality analogue" mechanism** (that web attacks transfer because they
resemble FTP/SSH-Patator) — falsified by `modality_analysis.py`. ✅ **The replacement IS measured**:
the CNN assigns ~90% of Web BF/XSS flows to **`DoS slowloris`**, a known *attack* class, so their
0.92–0.95 PR-AUC is **absorption into a known attack, not zero-day detection.** (Note this differs
from raw-space nearest-neighbour, which is DoS Hulk — classifier behaviour ≠ raw proximity; cite
which measurement you mean.)

🟡 **Earlier-phase audit (2026-07-29):** C2 🔴 **retracted** (the gap is 0.9 SD — see the noise floor)
· C5 ✅ addressed (counts corrected, record now version-controlled) · **C1 ✅ closed 2026-08-03**
(`comparability.py` reports the dedup variant; supervised channels lose 0.0035–0.0049, all six
zero-day families measure 0.0 % overlap) · **C3 ✅ closed 2026-08-03** (`robustness.py`; the regrouped
macro shifts values ~0.11–0.15 but preserves every ordering) · **C4 still open** — annotated in
`config.yaml` but not fixed; the log1p A/B still cites the contaminated metric.

✅ **PHASE 4 IS COMPLETE (2026-08-03) — KG built, multi-seeded, explainability + faithfulness
delivered.** `kg.py` · `kg_visualize.py` · `explain.py`.

It was **fully specified by measurement**, not by the original spec:
- **Representation: RAW FEATURES.** Bot purity 77.6 % (k=200) / 80.6 % (k=400), no training-seed
  lottery. 🔴 The AE bottleneck was recommended, then measured and **rejected** (52.1 pp spread,
  worst of all options) — **rank stability ≠ cluster stability.**
- **Scope: CORROBORATION + EXPLAINABILITY, not primary detection.** The spec's "unexplained
  cluster" criterion scores **lift ≤ 1.00× — at or below chance.** The scope contradiction with
  `conference_roadmap.md` is resolved empirically; the roadmap was right.
- **Emerging-pattern rule: GROWTH RATE ONLY.** Of the spec's three criteria, only cluster
  growth/burstiness survives: **lift 5.94× [5.66, 6.11] (n=3), ~81 % recall.** "Unexplained" is
  dead; behaviour co-occurrence is weak (2.81× at 1.5 % recall, cluster-level ≤ 1.35×) and worth
  keeping only as an *explanation* attribute.
- **Decay: KEPT (adaptive).** Decision logged 2026-08-03 — time = flow-count position in true
  chronological order.

⚠️ **Two caveats that must reach the write-up.**
① **Growth works substantially because CIC-IDS2017's attacks are scripted into fixed windows**
(Bot Fri 09:34–12:59, Web BF Thu 09:15–10:00, XSS Thu 10:15–10:35). A real network with continuous
low-rate C2 would not produce this signal — and Bot's real signature is persistence, not bursts.
② **"Temporal burstiness of a raw-feature cluster" does not need a knowledge graph.** The KG's
justification must rest on explanation/corroboration, not on this detection number. A reviewer will
say this; say it first.

🔴 **Do NOT cite "the conjunction gives 81 % precision."** That was clustering-seed 42 only; n=3
gives lift 1.73–11.57× and precision 0.122–0.814. **Fifth single-seed trap in this project, and the
first caught before publication** — multi-seed *before* writing, always.

⏱️ **Use `timeline.py` for ANY temporal work — never parse `meta_*.csv` timestamps directly.**
Two silent defects: dates are **D/M/YYYY** (naive parsing scatters the 5-day capture across
March/June/July) and the clock is **12-hour with no AM/PM** (so 1 PM sorts before 9 AM).
`timeline.parse()` corrects both and validates against the published capture schedule.

🧩 **Use `behavior.active_behaviour_matrix()`** in any KG code, not the raw 7-column matrix:
`RepeatedConnections` is constant 0.0 (dead edge type / divide-by-zero risk) and `BeaconLike` is
binary, so bimodal as an edge weight. Check `behavior.BEHAVIOUR_KIND` before assuming continuity.

**Recommended order:** ~~C2~~ ✅ → ~~Phase 3 AE~~ ✅ → ~~modality test~~ ✅ → ~~multi-seed AE~~ ✅ →
~~train-vs-score decomposition~~ ✅ → ~~KG substrate re-check~~ ✅ → ~~significance test~~ ✅ →
~~baselines on current schema~~ ✅ → ~~why the CNN fails on Bot~~ ✅ → ~~KG representation purity~~ ✅
(raw features win) → ~~"unexplained cluster" FP rate~~ ✅ (mechanism dead) → ~~KG's other two
emerging-pattern criteria~~ ✅ (growth works, co-occurrence weak) → ~~temporal-decay time axis~~ ✅
(kept adaptive) → ~~C1/C3 reporting variants~~ ✅ (both closed) → ~~build the KG~~ ✅ →
~~explainability + faithfulness~~ ✅ → ~~noise floor + n=6 everywhere~~ ✅ (C2 retracted) →
**next: (a) Phase 7.5 Tier 1 — ensemble, calibration/ECE, precision@alert-budget, abstention;
(b) the CNN→+LTN→+KG ablation; (c) TF determinism flags, which attack the 3.6 % CV at source;
then C4.** LOCO/fusion-repair stays deprioritized; the per-flow "router" idea rested on the
falsified modality mechanism.

**Phase numbering is canonical in [conference_roadmap.md §1b](docs/target/conference_roadmap.md)** — three competing schemes were in circulation; don't invent a fourth. Full history, retractions, and decisions in [STATUS.md](docs/STATUS.md). Training stays on **CPU** (GPU/Blackwell deferred — see STATUS Open Decisions).

## Environment / venv

A working virtualenv lives at **`.venv/`** (Python 3.11.9, TensorFlow 2.15.1 / Keras 2, CPU mode). Dependencies are pinned in `requirements.txt`.

```powershell
# Activate (PowerShell)
.\.venv\Scripts\Activate.ps1
# Or call the interpreter directly without activating:
.\.venv\Scripts\python.exe scripts\preprocess.py
```

- System Python is **not** on PATH (only a Store stub); always use the venv interpreter at `.venv\Scripts\python.exe`.
- Recreate if needed: `& "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe" -m venv .venv` then `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`.
- GPU: none — native Windows TF is CPU-only. Training the full 1.6M-row set will be slow; expect long epochs.

## How to run the pipeline

Run from the project root, in order, **using the venv interpreter**. Each step consumes the previous step's artifacts (organised under `data/processed/`, `models/`, `outputs/` — see `scripts/paths.py`).

**Current pipeline (paper-aligned split — this is what all reported results use):**

```bash
python scripts/preprocess.py        # 1. clean raw_csv_full → 68 features + meta_*.csv side-table
python scripts/preprocess_paper.py  # 2. paper split → data/processed/paper/
python scripts/cnn_paper.py         # 3. neural pillar → cnn_paper*.keras, embeddings, channel
python scripts/baselines.py         # 4. XGBoost / RandomForest / IsolationForest
python scripts/novelty.py           # 5. MSP + Mahalanobis (post-hoc, no retraining)
python scripts/ltn_paper.py         # 6. symbolic pillar (configured by LTN_* env vars)
python scripts/autoencoder_paper.py # 7. anomaly pillar — benign-only autoencoder (Phase 3)
python scripts/significance.py      # 8. paired bootstrap over per-flow scores (no training)
```

Multi-seed anything trainable via `CNN_SEED` / `LTN_SEED` / `AE_SEED` / `NOVELTY_SEED` /
`BASELINE_SEED` — each writes
`<name>_s<seed>` artifacts and never touches the seed-42 originals. **Treat any n=1 number as
provisional**; three findings have already been retracted as single-seed artifacts.

**Legacy temporal-split pipeline** (`preprocess.py → cnn3.py → eval.py → ltn.py`) still runs but is **superseded** — it produced the 0.4529-vs-0.6689 LTN underperformance and was replaced by the protocol reset. Kept only as a secondary "hard mode" result. Don't use it for new work.

Utilities: `python scripts/check.py` (print real feature column order — **use before touching behaviour indices**), `python scripts/behavior.py` (regenerate thresholds + validation tables), `python scripts/visual.py` (preprocessing impact).

**All 51 Python scripts are documented in [docs/scripts_reference.md](docs/scripts_reference.md)** — read it before assuming what a script does. Dependencies are pinned in `requirements.txt`. There are also **7 shell launchers** (`run_long.sh`, `seed_sweep.sh`, `noise_floor.sh`, `rigor_n6.sh`, `ltn_ctrl_sweep.sh`, `verify_determinism.sh`, `c4_transform_ab.sh`) — long jobs go through `run_long.sh` per non-negotiable #2.

## Repo layout

```
NeuroSymbolicIDS/
├── CLAUDE.md                  ← you are here
├── README.md                  ← human entry point
├── requirements.txt           ← pinned dependencies
├── .venv/                     ← Python 3.11 virtualenv (not committed)
│
├── config.yaml                ← protocol/experiment config (seed, splits, class lists)
│
├── scripts/                   ← 51 Python scripts + 7 shell launchers — see docs/scripts_reference.md
│   ├── paths.py               ←   central path config — ALL I/O locations
│   ├── config, features, tracking, metrics        ← infrastructure
│   ├── preprocess, preprocess_paper, cnn_paper,   ← CURRENT pipeline
│   │   baselines, novelty, behavior, ltn_paper,
│   │   cnn_auxhead_paper, autoencoder_paper
│   ├── kg, kg_visualize, explain                  ← PHASE 4 (KG + explainability)
│   ├── fusion_kg, fusion_multi, significance,     ← PHASE 5 (fusion + rigor)
│   │   significance_seed
│   ├── skyline_oracle, rescore_logits,            ← analysis / one-off
│   │   fusion_beaconlike, modality_analysis,
│   │   kg_precheck, kg_readiness, kg_criteria,
│   │   bot_failure_analysis, comparability,
│   │   robustness, timeline, audit_leakage
│   ├── cnn3, eval, ltn                            ← LEGACY (superseded)
│   └── dashboard_server, visual, check,           ← utilities
│       lint_conventions, repair_runs_log
│
├── data/
│   ├── raw_csv_full/          ← CIC-IDS2017 GeneratedLabelledFlows (not committed)
│   ├── raw_csv/               ← legacy ML-CVE variant (superseded)
│   └── processed/
│       └── paper/             ← the paper split + meta_*.csv (IP/port/timestamp)
├── models/                    ← *.keras + scaler/encoder *.pkl
├── outputs/
│   ├── arrays/                ← X_test.npy, y_train/val/test
│   ├── embeddings/            ← X_*_emb.npy
│   ├── predictions/           ← y_prob_*.npy
│   ├── metadata/              ← class_names, history.pkl, thresholds
│   └── figures/               ← *.png (tracked)
│
└── docs/
    ├── *.md                   ← implemented-state reference (architecture, dataset, models, …)
    ├── implementation/        ← line-by-line source AUDITS (current truth, incl. bugs)
    ├── target/                ← TARGET architecture specs + roadmap/gap analysis
    ├── archive/               ← superseded original docs
    ├── STATUS.md              ← 🔴 living: where we are
    ├── CHANGELOG.md           ← 🔴 living: dated history
    ├── KNOWN_ISSUES.md        ← 🔴 living: bugs & risks
    └── DASHBOARD.md           ← 🔴 living: "open preview" convention (see below)
```

**Artifact locations are defined once in [`scripts/paths.py`](scripts/paths.py)** (`PROCESSED`, `MODELS`, `ARRAYS`, `EMBEDDINGS`, `PREDICTIONS`, `METADATA`, `FIGURES`). Every script imports it. To change where something is written, edit `paths.py` — don't hardcode paths in scripts.

Documentation map:
- **What's true now (incl. bugs):** [docs/implementation/](docs/implementation/)
- **What we're building toward:** [docs/target/](docs/target/) — start with [roadmap_gap_analysis.md](docs/target/roadmap_gap_analysis.md)
- **Reference (pipeline, dataset, artifacts):** [docs/](docs/)

## Key facts to not get wrong

- **The split is the paper-aligned one** (`config.yaml`, `preprocess_paper.py`): 9 known classes stratified 80/10/10, benign under-sampled 1:1. Train 883,796 / val 110,475 / test 114,658. *The temporal split (Mon–Wed / Thu–Fri) is the superseded secondary protocol.*
- **Zero-day classes are the 6 rare families** (test only, never trained): **Bot**, Heartbleed, Infiltration, Web Attack Brute Force / XSS / Sql Injection. Bot is **not** a training class — this exact fact was once documented wrong from a summary; verify against `config.yaml`.
- **⚠️ PortScan and DDoS are KNOWN, trained-on classes** under the current protocol. Any claim of the form "the behaviours strongly cover PortScan/DDoS, so the symbolic approach works" is measuring the temporal split and does not transfer.
- **68 features**, not 70. Verify with `check.py`.
- **Only 3 zero-day families are adequately powered** (Bot n=1,956, Web Brute Force, Web XSS). Heartbleed (n=11), Infiltration (n=36) and SQL Injection (n=21) are excluded from the macro metric — never report them to 4 decimal places.
- **The headline metric is macro zero-day PR-AUC**, not the blended "benign vs all unknowns" number — the blend is a size-weighted mixture that reorders the ranking. `metrics.py` enforces this.
- **⏱️ NEVER parse `meta_*.csv` `Timestamp` directly — use `scripts/timeline.py`.** The raw string is wrong twice: dates are **D/M/YYYY** (naive parsing scatters the 5-day capture across four months) and the clock is **12-hour with no AM/PM** (1 PM sorts before 9 AM). Measured: **all 114,658 test rows change position** between naive and corrected order, and naive parsing emits `NaT`. Corrected values are persisted as `data/processed/paper/timestamp_{train,val,test}.npy`; regenerate with `python scripts/timeline.py --backfill`. `timeline.selftest()` validates against the published capture schedule and raises on mismatch.
- Test flows of unseen classes are encoded as **−1** (zero-day marker).
- The embedding layer is named **`"embedding"`** — downstream extraction depends on this name.
- CNN ~chance recall on zero-day is **intended** — it's the honest baseline the symbolic stages must beat. As of Phase 2, **nothing has beaten it.**

## Working conventions

- **Verify against source, not memory or summaries.** A prior exploration summary already introduced an error (Bot misclassified). Read the actual `.py` file before claiming what it does.
- **Run `check.py` before editing any feature-index logic** in `behavior.py`.
- Artifacts are large (`X_test.npy` ~600 MB); they live under `data/processed/`, `models/`, `outputs/` and are git-ignored (except `outputs/figures/`). Don't commit big binaries.
- Keep the embedding layer name (`"embedding"`) and the saved-artifact filenames stable — many scripts reference them by name.
- All path locations come from `scripts/paths.py`; scripts `import paths` (works because `scripts/` is on `sys.path` when you run `python scripts/<x>.py`).
- When you change behaviour/LTN, update [STATUS.md](docs/STATUS.md) and [CHANGELOG.md](docs/CHANGELOG.md).
- **"Open preview" means the LIVE local ops console, always.** When the user says "open preview" (or equivalent), start it via `preview_start` with `name: "phase2-dashboard"` (config in `.claude/launch.json`, runs `scripts/dashboard_server.py`) — not the static published Artifact, which is a separate, sharable-but-frozen snapshot. Full detail (what's live, what each file is for, when to update which one) in [DASHBOARD.md](docs/DASHBOARD.md).
- **A finding from one run/seed is provisional, not fact — say so.** Confirmed failure mode (2026-07-27): three separate claims (a scoring-saturation artifact, a "beaconing" hypothesis, an axiom's Bot-detection benefit) were written up as settled before multi-seeding or independent verification, and all three had to be retracted. Write single-run results as "n=1, unverified" in STATUS/CHANGELOG, not as confirmed — the retraction is cheap to prevent and expensive to discover later.
- **Retract in place — never silently rewrite.** When a documented finding turns out wrong, strike it through / mark it `RETRACTED` with the reasoning kept, rather than deleting or quietly correcting it. STATUS.md's 2026-07-27 entries are the reference example: every reversal is visible, dated, and explains what changed the picture. This is what makes the living docs trustworthy as a research record, not just a status board.
- **Background jobs expected to run >10–15 min get a heartbeat monitor** (process-alive + log-growth at minimum), not fire-and-forget — this is what made the 2026-07-27 multi-hour training batches trustworthy instead of a black box. See that session's transcript for the pattern (`Monitor` tool watching `Win32_Process` + log file size).
- **Known pitfall: PowerShell `*>>` redirect of a Python subprocess produces a mixed-encoding log file** — part UTF-8 (Python's own stdout), part UTF-16LE (PowerShell's own `Add-Content` lines), interleaved in the same file. Naive `iconv`/`Get-Content` reads garble or truncate. Fix: locate markers by raw byte offset (search both UTF-8 and UTF-16LE encodings of the string), then decode each segment with the codec that matches. Hit 3 times in the 2026-07-27 session before this was written down — don't rediscover it.
- **Known pitfall: `ps aux` on Windows Git-Bash can give a false "process died" reading for one poll tick**, even while the process is running normally (2026-08-01, heartbeat-monitoring `cnn_paper.py`: `ps` missed it at epoch 2, training resumed and completed fine seconds later). Don't gate a heartbeat monitor's failure decision on a single `ps` miss — use **log-growth staleness over several consecutive polls** as the authoritative dead/hung signal; `ps` is advisory only.

## Git & commit conventions (MANDATORY — see [CONTRIBUTING.md](CONTRIBUTING.md))

Full rules in [CONTRIBUTING.md](CONTRIBUTING.md). The non-negotiables:

- **Identity:** every commit is authored AND committed as `Shaunak1012 <195268122+Shaunak1012@users.noreply.github.com>` (set locally in this repo).
- **No assistant attribution — ever.** Do NOT add `Co-Authored-By:` trailers or any mention of "Claude" / "Anthropic" / "Generated with …" in commit messages or PR bodies. All work is attributed solely to Shaunak1012.
- **Conventional Commits:** `type(scope): description` (`feat`/`fix`/`docs`/`chore`/`refactor`/`test`/…). One logical change per commit — never an "add everything" dump.
- **Branch + PR workflow:** feature work goes on `feat|fix|docs|chore/<topic>` branches → `gh pr create` → **merge LOCALLY** with `git merge --no-ff` then `git push origin main` (do NOT use the GitHub button / `gh pr merge` — it authors the merge commit as "Shaunak", not "Shaunak1012"). Never commit feature work straight to `main`. Full steps in [CONTRIBUTING.md](CONTRIBUTING.md).
- **Don't commit** gitignored artifacts or smoke-test/placeholder figures — only finalised `outputs/figures/*.png`.

## Model-selection convention (user efficiency preference)

**End every response with a one-line `→ Next model:` recommendation** for the upcoming step, so the user doesn't overspend on Opus for routine work. Rough guide:
- **Opus** — hard reasoning: design decisions, debugging, result interpretation/thesis framing, research, anything ambiguous or high-stakes.
- **Sonnet** — routine implementation: writing/running scripts, assembling tables, commits, doc updates, launching batches.
- **Haiku** — trivial: status checks, "is the background run done?", simple lookups.

The user switches models per step based on this. Keep the recommendation honest — don't default to Opus.

**Non-negotiable: this line does not lapse.** Confirmed failure mode (2026-07-27 session): the line quietly stopped appearing partway through a long session — specifically during stretches of many consecutive tool-call-heavy turns (background-job heartbeat monitoring, git housekeeping) where the response was mostly tool output and the trailing recommendation got dropped. Include `→ Next model: ...` on **every** response with user-visible text, including one-line heartbeat acknowledgements and routine status updates — not just on responses that "feel like" a natural decision point. If a run of near-identical short updates makes the line feel redundant, that repetition is fine; silently dropping it is the failure being guarded against here.

## Environment

Windows 11, PowerShell primary shell. GitHub CLI (`gh`) v2.94 installed, authenticated as `Shaunak1012`. Git repo on branch `main`, remote `origin → github.com/Shaunak1012/NeuroSymbolicIDS`.

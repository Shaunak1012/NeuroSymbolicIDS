# CLAUDE.md — Session Onboarding Guide

> This file is auto-loaded at the start of every Claude Code session. It tells you (Claude) and any collaborator how to get oriented fast, what state the project is in, and how to work in this repo. **Keep it current.**

## What this project is

**NeuroSymbolic-IDS** — an *Explainable & Adaptive Neuro-Symbolic Intrusion Detection System* for the CIC-IDS2017 dataset. Goal: detect both known and **zero-day** network attacks by combining:
1. a **1D CNN** (learned features + class probabilities),
2. **symbolic logic** (LTN-style fuzzy axioms grounded in network behaviour),
3. an **adaptive Knowledge Graph** (memory of emerging patterns),
fused into an explainable benign/malicious alert.

Input is **CIC-IDS2017 flow-feature CSVs** (**68** numeric features/flow — not 70; several frozen docs still say 70 and are banner-marked). The "Raw PCAP" boxes in the architecture diagram are conceptual; payload-level processing is future work.

**Reality check on the goal above:** as of Phase 2, the symbolic pillar does **not** beat the neural baseline — every symbolic injection point tried (loss-level, representation-level, inference-level) costs macro zero-day PR-AUC or changes nothing. The project's current contribution is the *anatomy of why*. Don't write or reason as though the fusion story is established.

## ⚡ First thing every session

1. Read **[docs/STATUS.md](docs/STATUS.md)** — current component status, priorities, open decisions, last results.
2. Skim **[docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md)** — what's broken and why.
3. Check recent **[docs/CHANGELOG.md](docs/CHANGELOG.md)** entries.
4. **State it back, briefly, before starting work** — one line naming the current phase and what's blocking or next (per STATUS's "RESUME HERE"). This is a forcing function, not a formality: reading the files silently doesn't confirm the state actually landed. If the one-liner doesn't match what STATUS.md says, that's a sign it wasn't really absorbed — reread before proceeding.
Then proceed with the task.

## ⚡ Last thing every session

Update the **living documents** so the next session starts clean:
- **STATUS.md** — flip component statuses, update priorities & "Last Measured Results."
- **CHANGELOG.md** — add a dated entry for what changed (newest first).
- **KNOWN_ISSUES.md** — open new issues, mark fixed ones.

⚠️ **Component status is currently duplicated across 4+ files, and updating one while missing another
has caused the same drift error twice** (2026-07-29 and 2026-08-02 — the second left this very file
claiming Phase 3 was "not built" after it had been built, run and multi-seeded). **Until that is
fixed, changing any component's status means updating ALL of:** `docs/STATUS.md` (Component Status ·
Remaining Work · Open Decisions) · **this file's "Current state" table** · `docs/target/roadmap_gap_analysis.md` ·
`docs/target/target_architecture.md`. Verify with:

```bash
grep -rn "Not built\|✅ Built\|⬜" --include=*.md . | grep -v .venv
```

**The real fix — collapse these to a single source — is a tracked issue in
[KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md) with a concrete plan. Worth doing before Phase 4 starts
changing statuses.**

## Current state (snapshot — authoritative version in STATUS.md)

| Component | Status |
|-----------|--------|
| Preprocessing (+ IP/timestamp meta side-table) | ✅ Working |
| Paper-aligned split | ✅ Working |
| CNN + embeddings | ✅ Verified correct — **n=3**, macro zd PR-AUC **0.6399** [0.6353, 0.6446] |
| Classical baselines | ⚠️ Working but **n=1 and old metrics schema** (XGBoost, RF, IsoForest) — no per-family/macro recorded, **not citable for comparison**; re-run `baselines.py` |
| Novelty channels (MSP, Mahalanobis) | ✅ **n=3** — MSP macro 0.5884, Mahalanobis 0.3777. ⚠️ "Mahalanobis 4.3× on Bot" is **retracted** (seed 42 only); n=3 mean is **3.0×**, seed 44 at chance |
| Behaviour abstraction | ✅ Rebuilt & validated — **7 behaviours incl. `BeaconLike`**. ⚠️ Validation tables were measured on the *temporal* split, where PortScan/DDoS were zero-day; they are **known classes** now, so "PortScan/DDoS strongly covered" is not evidence for the current protocol |
| LTN reasoning (paper-split) | 🟡 Anatomized, multi-seeded — macro cost confirmed, Bot benefit retracted; `ratio` omega-mode fix confirmed stable |
| Anomaly pillar (autoencoder) — canonical **Phase 3** | ✅ **BUILT & RUN 2026-08-02, n=3** — `scripts/autoencoder_paper.py`. macro 0.0970, **best Bot channel measured (3.8×)**, fails on web attacks → **double dissociation** vs the CNN |
| Knowledge Graph — canonical **Phase 4** | ❌ Not built — 🔴 **BLOCKED on a representation decision** (CNN embedding geometry is a seed lottery; see STATUS "PHASE-4 BLOCKER") |
| Decision Fusion — Phase 5 | ❌ Not built — ⚠️ a *fitted* combiner is structurally blocked (see "THE FUSION WALL") |
| Explainability | ❌ Not built |

**Next action (resume here):** Phase 2 (symbolic/LTN pillar) is concluded for now — every axiom variant tried (Ax3–Ax6) costs macro PR-AUC relative to the no-axiom control, robust across 3 seeds; the targeted Ax6 (BeaconLike) axiom's apparent Bot-detection benefit did not survive multi-seed validation and is retracted.

🟡 **Read the "EARLIER-PHASE AUDIT" section near the top of [STATUS.md](docs/STATUS.md) before doing anything else.** A retrospective audit on 2026-07-29 found **5 open concerns**. **C2 is now RESOLVED (2026-08-02)** — `cnn_paper` is n=3 (mean 0.6399, range 0.6353–0.6446) and its full range sits inside the LTN control's range (0.6029–0.6505, also n=3); "the neural baseline wins" is not currently supportable without a proper significance test (not yet run). **C1, C3, C4, C5 remain findings-only — no fixes implemented, they await the user's go-ahead. Do not implement them unprompted.**

✅ **Phase 3 (benign-only autoencoder) is BUILT AND RUN (2026-08-02)** — and the interpretation I first wrote for it was **tested the same day and largely falsified.** Read the **red box at the top of "🧪 PHASE 3 RESULTS"** in STATUS before citing anything from this phase.

Short version of what is actually established (all n=3): the AE is a **raw-space distance-from-benign detector** (`corr = +0.732`), and it is **the most reliable Bot channel measured** — mean **3.8×** [3.2–4.8] vs Mahalanobis **3.0×** [1.2–4.3] and the CNN's **1.3×** [0.7–1.7]. It is excellent on Heartbleed (103×) / Infiltration (145×), which are the **underpowered** families `metrics.py` excludes. Note the "0.0000 recall on web attacks" split I first reported was a **threshold artifact**, not a categorical difference — on lift the AE is 3.8×/3.9×/4.7× across Bot/WebBF/XSS.

🔴 **Do NOT repeat the "modality analogue" mechanism** (that web attacks transfer because they resemble FTP/SSH-Patator). `scripts/modality_analysis.py` falsified it: their nearest known attack is **DoS Hulk**, and **Bot sits closer to benign (7.28) than the web attacks do (8.84)** — the opposite of the claim. The supporting +0.933 correlation was **circular** (measured in the CNN's own embedding space, where it just restates the CNN's log-odds; in raw space it is −0.388). (A)/(B) complementarity survives as an *empirical pattern*; the *explanation* is open.

✅ **AE multi-seeded (n=3) — the (A)/(B) complementarity is now ESTABLISHED as a double dissociation.** CNN vs AE ranges **do not overlap on any family**: AE wins Bot **2.9×** (0.1314 vs 0.0446), CNN wins Web BF **8.8×** and XSS **17.4×**. First cleanly multi-seeded comparative result in the project — the pattern the falsified modality account was invented to explain is itself **real**; only the explanation died. Caveat: both are weak on Bot in absolute terms (3.8× vs 1.3× chance), so this is a robust *relative* difference, not a solved problem.

🔴 **PHASE-4 BLOCKER (2026-08-02) — read before writing any KG code.** The pre-check's "Bot forms a ~90%-pure cluster, stable across seeds" is **retracted**: it varied only the *clustering* seed on a *fixed* seed-42 embedding. Varying the **CNN seed** gives Bot purity **87.9% / 86.6% / 44.4%** (43.4 pp spread) while Web BF/XSS stay stable (0.7–2.5 pp). **The CNN's embedding geometry w.r.t. Bot is a seed lottery**, independently confirmed by Mahalanobis (seed 44: 1.2×, chance) — even though classification is flat across seeds (macro spread 0.009). So the KG would cluster *stably* on the families the CNN already handles, and *unstably* on the one family where it would matter. **Decide the representation first** (ensemble seeds · raw features · the AE's benign-trained 16-d bottleneck · accept-and-publish the variance). See STATUS "PHASE-4 BLOCKER".

**Recommended order:** ~~C2~~ ✅ → ~~Phase 3 AE~~ ✅ → ~~modality test~~ ✅ (falsified) → ~~multi-seed AE~~ ✅ (dissociation established) → ~~train-vs-score decomposition~~ ✅ (retracted "Mahalanobis 4.3×") → ~~re-check KG substrate across CNN seeds~~ ✅ (found the blocker) → **next: (a) decide the KG representation question above; (b) why is the CNN specifically so bad on Bot** — the oracle result (0.0314 → 0.9764 with ~1,000 labels) proves the information *is* in the features, so it's an unexplained transfer failure; **(c)** C1/C3 reporting variants (no training) → C4 → C5. **LOCO/fusion-repair stays deprioritized**, and the per-flow "router" idea rested on the falsified modality mechanism — not motivated as-is.

🧭 **Read the "THESIS REFRAMING" section at the top of [STATUS.md](docs/STATUS.md).** Argued 2026-07-29 from existing evidence (no new runs): every Phase-2 null shares **one** structural cause — a mechanism fitted on data that lacks zero-day cannot transfer to zero-day. That covers the LTN axioms, the aux head, the fitted fusion, *and* the KG's planned `s_kg` path. The split is **(A)** learn-what-attacks-look-like (needs attack examples, cannot reach novel classes) vs **(B)** learn-what-normal-looks-like (needs only benign, reaches novel classes by construction). The project invested in (A); the Bot evidence favours (B). ⚠️ **The "Mahalanobis 4.3×" figure originally cited here is RETRACTED — that was seed 42, the best of 3; n=3 mean is 3.0× (range 1.2–4.3×).** Corrected n=3 Bot lifts: **AE 3.8×** [3.2–4.8] · Mahalanobis 3.0× [1.2–4.3] · CNN 1.3× [0.7–1.7] · MSP 1.3×. **This reframing was subsequently TESTED (2026-08-02): the (A)/(B) complementarity is confirmed as a double dissociation, but the *modality-analogue mechanism* proposed for it was falsified.** See the boxes at the top of STATUS.

⚠️ **Phase 3 (benign-only autoencoder, ~1h) is now the load-bearing next experiment, not a checkbox.** It is a pure (B) method and the direct test of the reframing. It was never actually decided — it was about to be skipped by a phase-number collision (STATUS used "Phase 3" for the KG while the canonical roadmap uses Phase 3 = autoencoder, Phase 4 = KG). **Very likely run it before the KG (canonical Phase 4).**

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
```

Multi-seed anything trainable via `CNN_SEED` / `LTN_SEED` / `AE_SEED` / `NOVELTY_SEED` — each writes
`<name>_s<seed>` artifacts and never touches the seed-42 originals. **Treat any n=1 number as
provisional**; three findings have already been retracted as single-seed artifacts.

**Legacy temporal-split pipeline** (`preprocess.py → cnn3.py → eval.py → ltn.py`) still runs but is **superseded** — it produced the 0.4529-vs-0.6689 LTN underperformance and was replaced by the protocol reset. Kept only as a secondary "hard mode" result. Don't use it for new work.

Utilities: `python scripts/check.py` (print real feature column order — **use before touching behaviour indices**), `python scripts/behavior.py` (regenerate thresholds + validation tables), `python scripts/visual.py` (preprocessing impact).

**All 22 scripts are documented in [docs/scripts_reference.md](docs/scripts_reference.md)** — read it before assuming what a script does. Dependencies are pinned in `requirements.txt`.

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
├── scripts/                   ← 26 scripts — see docs/scripts_reference.md
│   ├── paths.py               ←   central path config — ALL I/O locations
│   ├── config, features, tracking, metrics        ← infrastructure
│   ├── preprocess, preprocess_paper, cnn_paper,   ← CURRENT pipeline
│   │   baselines, novelty, behavior, ltn_paper,
│   │   cnn_auxhead_paper, autoencoder_paper
│   ├── skyline_oracle, rescore_logits,            ← analysis / one-off
│   │   fusion_beaconlike, modality_analysis,
│   │   kg_precheck, audit_leakage
│   ├── cnn3, eval, ltn                            ← LEGACY (superseded)
│   └── dashboard_server, visual, check            ← utilities
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

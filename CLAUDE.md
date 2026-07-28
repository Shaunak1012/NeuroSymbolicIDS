# CLAUDE.md — Session Onboarding Guide

> This file is auto-loaded at the start of every Claude Code session. It tells you (Claude) and any collaborator how to get oriented fast, what state the project is in, and how to work in this repo. **Keep it current.**

## What this project is

**NeuroSymbolic-IDS** — an *Explainable & Adaptive Neuro-Symbolic Intrusion Detection System* for the CIC-IDS2017 dataset. Goal: detect both known and **zero-day** network attacks by combining:
1. a **1D CNN** (learned features + class probabilities),
2. **symbolic logic** (LTN-style fuzzy axioms grounded in network behaviour),
3. an **adaptive Knowledge Graph** (memory of emerging patterns),
fused into an explainable benign/malicious alert.

Input is **CIC-IDS2017 flow-feature CSVs** (70 numeric features/flow). The "Raw PCAP" boxes in the architecture diagram are conceptual; payload-level processing is future work.

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

## Current state (snapshot — authoritative version in STATUS.md)

| Component | Status |
|-----------|--------|
| Preprocessing | ✅ Working |
| CNN + embeddings | ✅ Verified correct |
| CNN evaluation | ✅ Working |
| Behaviour abstraction | ✅ Rebuilt & validated (PortScan/DDoS covered) |
| LTN reasoning (paper-split) | 🟡 Anatomized, multi-seeded — macro cost confirmed, Bot benefit retracted; `ratio` omega-mode fix confirmed stable |
| Knowledge Graph | ❌ Not built — **next** |
| Decision Fusion | ❌ Not built |
| Explainability | ❌ Not built |

**Next action (resume here):** Phase 2 (symbolic/LTN pillar) is concluded for now — every axiom variant tried (Ax3–Ax6) costs macro PR-AUC relative to the no-axiom control, robust across 3 seeds; the targeted Ax6 (BeaconLike) axiom's apparent Bot-detection benefit did not survive multi-seed validation and is retracted. Next real work is **Phase 3: Knowledge Graph** (item #3 in STATUS's Remaining Work table). Full history, retractions, and decisions in [STATUS.md](docs/STATUS.md). Training stays on **CPU** (GPU/Blackwell deferred — see STATUS Open Decisions).

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

```bash
python scripts/preprocess.py   # 1. clean CSVs → features_*.csv, labels_*.npy
python scripts/cnn3.py         # 2. train CNN → model_*.keras, X_*_emb.npy, history.pkl
python scripts/eval.py         # 3. baseline metrics → y_prob_test*.npy, cnn_zeroday_eval.png
python scripts/ltn.py          # 4. hybrid-LTN → ltn_model_*.keras, ltn_eval.png
```

Utilities: `python scripts/check.py` (print real feature column order — **use before touching behaviour indices**), `python scripts/visual.py` (preprocessing impact).

Dependencies: `numpy pandas scikit-learn tensorflow matplotlib seaborn`.

## Repo layout

```
NeuroSymbolicIDS/
├── CLAUDE.md                  ← you are here
├── README.md                  ← human entry point
├── requirements.txt           ← pinned dependencies
├── .venv/                     ← Python 3.11 virtualenv (not committed)
│
├── scripts/                   ← pipeline code
│   ├── paths.py               ←   central path config — ALL I/O locations
│   └── preprocess, cnn3, eval, behavior, ltn, visual, check
│
├── data/
│   ├── raw_csv/               ← CIC-IDS2017 input CSVs (not committed)
│   └── processed/             ← clean_*, features_*, labels_*
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

- **Train/test split is temporal.** Train = Mon+Tue+Wed; Test = Thu+Fri.
- **Zero-day classes** (test only, never trained): Web Attacks, Infiltration, **Bot**, PortScan, DDoS. Bot is **not** a training class.
- **Train classes** (~8): BENIGN, FTP-Patator, SSH-Patator, DoS Hulk/GoldenEye/slowloris/Slowhttptest, Heartbleed. `n_classes` is computed dynamically from the data — don't hardcode.
- Test flows of unseen classes are encoded as **−1** (zero-day marker).
- The embedding layer is named **`"embedding"`** — downstream extraction depends on this name.
- CNN ~0% recall on zero-day is **intended** — it's the honest baseline the symbolic stages must beat.

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

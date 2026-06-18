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
| LTN reasoning | ⚠️ Runs but axioms are label tautologies — **next: re-ground on behaviours** |
| Knowledge Graph | ❌ Not built |
| Decision Fusion | ❌ Not built |
| Explainability | ❌ Not built |

**Next action (resume here):** re-ground the LTN axioms on `behavior.py` (wire it into `ltn.py`, replace label-tautology axioms with behaviour→class rules), then run the ~30–60 min CPU training. Full remaining-work list and decisions in [STATUS.md](docs/STATUS.md). Training stays on **CPU** (GPU/Blackwell deferred — see STATUS Open Decisions).

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
    └── KNOWN_ISSUES.md        ← 🔴 living: bugs & risks
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

## Git & commit conventions (MANDATORY — see [CONTRIBUTING.md](CONTRIBUTING.md))

Full rules in [CONTRIBUTING.md](CONTRIBUTING.md). The non-negotiables:

- **Identity:** every commit is authored AND committed as `Shaunak1012 <195268122+Shaunak1012@users.noreply.github.com>` (set locally in this repo).
- **No assistant attribution — ever.** Do NOT add `Co-Authored-By:` trailers or any mention of "Claude" / "Anthropic" / "Generated with …" in commit messages or PR bodies. All work is attributed solely to Shaunak1012.
- **Conventional Commits:** `type(scope): description` (`feat`/`fix`/`docs`/`chore`/`refactor`/`test`/…). One logical change per commit — never an "add everything" dump.
- **Branch + PR workflow:** feature work goes on `feat|fix|docs|chore/<topic>` branches → `gh pr create` → `gh pr merge --merge --delete-branch` → sync `main`. Never commit feature work straight to `main`.
- **Don't commit** gitignored artifacts or smoke-test/placeholder figures — only finalised `outputs/figures/*.png`.

## Environment

Windows 11, PowerShell primary shell. GitHub CLI (`gh`) v2.94 installed, authenticated as `Shaunak1012`. Git repo on branch `main`, remote `origin → github.com/Shaunak1012/NeuroSymbolicIDS`.

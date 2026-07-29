# NeuroSymbolic-IDS

A hybrid intrusion detection system that combines a 1D Convolutional Neural Network with symbolic rule-based reasoning (Logic Tensor Networks) to detect zero-day network attacks.

Trained on the [CIC-IDS2017](https://www.unb.ca/cic/datasets/ids-2017.html) dataset. The CNN learns
from known attack families; the symbolic pillar is an attempt to extend coverage to unseen
(zero-day) attack types.

> **Honest framing.** "Symbolic rules extend coverage to zero-day attacks" is the *hypothesis under
> test*, not a demonstrated result. As of Phase 2 it does **not** hold on this dataset: every
> symbolic injection point tried (loss-level, representation-level, inference-level) either costs
> macro zero-day PR-AUC or changes nothing. The project's contribution is currently the *anatomy of
> why* — see [Key Results](#key-results) and [docs/STATUS.md](docs/STATUS.md).

## Quick Start

Use the venv interpreter (`.venv\Scripts\python.exe`) from the project root. This is the
**current (paper-aligned) pipeline** — the protocol all reported results use:

```bash
# 1. Clean raw CSVs -> 68 features + IP/timestamp meta side-table
python scripts/preprocess.py

# 2. Re-slice into the paper-aligned split (stratified 80/10/10, 6 zero-day classes test-only)
python scripts/preprocess_paper.py

# 3. Train the CNN on the paper split -> models, embeddings, fusion channel
python scripts/cnn_paper.py

# 4. Classical + anomaly baselines (XGBoost / RandomForest / IsolationForest)
python scripts/baselines.py

# 5. Free open-set novelty channels (MSP + Mahalanobis) from the trained CNN
python scripts/novelty.py

# 6. Symbolic pillar — configurable hybrid CE + omega*SAT trainer
python scripts/ltn_paper.py
```

<details>
<summary><strong>Legacy temporal-split pipeline</strong> (superseded 2026-06-18 — kept as secondary "hard mode")</summary>

```bash
python scripts/preprocess.py   # then:
python scripts/cnn3.py
python scripts/eval.py
python scripts/ltn.py          # underperformed (0.45 vs 0.67 PR-AUC); see STATUS
```

The temporal split (train Mon–Wed / test Thu–Fri) made PortScan and DDoS zero-day, which turned out
to be a much harder and *misaligned* protocol versus the base paper. It is retained for a secondary
robustness result, not as the main track. Docs describing it are banner-marked as frozen.
</details>

## Documentation

> **Read the living docs first.** The reference docs below are a mix of current and frozen;
> every frozen one carries a dated banner at the top saying so. When a reference doc and
> [STATUS.md](docs/STATUS.md) disagree, **STATUS wins** — it is the only file guaranteed current.

### Living / dynamic docs (updated every session) — start here

| File | Contents |
|------|----------|
| [docs/STATUS.md](docs/STATUS.md) | 🔴 Current state, results, retractions, what's next |
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | 🔴 Dated history of changes |
| [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md) | 🔴 Bug & risk tracker |
| [docs/DASHBOARD.md](docs/DASHBOARD.md) | 🔴 Live ops console + the "open preview" convention |
| [CLAUDE.md](CLAUDE.md) | Session onboarding guide (read first each session) |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Git identity, commit conventions, branch/PR workflow (mandatory) |

### Reference docs

| File | Contents | Currency |
|------|----------|----------|
| [docs/scripts_reference.md](docs/scripts_reference.md) | Per-script purpose, inputs, and outputs | ✅ current |
| [docs/artifacts.md](docs/artifacts.md) | Catalog of all saved files (.npy, .keras, .pkl, .csv) | ✅ current |
| [docs/architecture.md](docs/architecture.md) | System design, data flow diagram | ⚠️ frozen (temporal split) |
| [docs/dataset.md](docs/dataset.md) | CIC-IDS2017 dataset, classes, split strategy | ⚠️ frozen (temporal split) |
| [docs/pipeline.md](docs/pipeline.md) | Step-by-step pipeline execution guide | ⚠️ frozen (temporal split) |
| [docs/models.md](docs/models.md) | CNN architecture, LTN hybrid loss, hyperparameters | ⚠️ frozen (pre-fix axioms) |
| [docs/neuro_symbolic.md](docs/neuro_symbolic.md) | Symbolic behaviour extraction and fuzzy logic axioms | ⚠️ frozen (pre-rebuild) |

### Implementation audits (line-by-line source verification)

| File | Contents | Currency |
|------|----------|----------|
| [docs/implementation/cnn_current.md](docs/implementation/cnn_current.md) | CNN — ✅ verified correct, minor notes | ✅ current |
| [docs/implementation/behaviour_abstraction_current.md](docs/implementation/behaviour_abstraction_current.md) | Behaviour module — ✅ rebuilt & validated, 7 behaviours | ✅ current |
| [docs/implementation/ltn_current.md](docs/implementation/ltn_current.md) | Legacy `ltn.py` — 🔴 ran, underperformed, superseded | ⚠️ historical |

### Target architecture (what we're building toward)

The [docs/target/](docs/target/) folder describes the full *Explainable & Adaptive Neuro-Symbolic IDS* — including the Knowledge Graph, Decision Fusion, and explainability layers not yet built. Start with the [gap analysis](docs/target/roadmap_gap_analysis.md) for built-vs-planned and the build plan.

| File | Contents |
|------|----------|
| [docs/target/target_architecture.md](docs/target/target_architecture.md) | Full system overview and pipeline |
| [docs/target/knowledge_graph.md](docs/target/knowledge_graph.md) | Adaptive-memory KG design (NetworkX) |
| [docs/target/decision_fusion.md](docs/target/decision_fusion.md) | Combining CNN / LTN / KG signals |
| [docs/target/explainability.md](docs/target/explainability.md) | Three explanations + Final Alert |
| [docs/target/behaviour_abstraction.md](docs/target/behaviour_abstraction.md) | Target behaviours and feature derivability |
| [docs/target/roadmap_gap_analysis.md](docs/target/roadmap_gap_analysis.md) | Built vs. planned, phases, ablation plan |

## Project Structure

```
NeuroSymbolicIDS/
├── README.md                  # This file
├── CLAUDE.md                  # Session onboarding guide
├── requirements.txt           # Pinned deps (Python 3.11 / TF 2.15)
├── .gitignore
│
├── config.yaml                # central experiment/protocol config
│
├── scripts/                   # see docs/scripts_reference.md for all 22
│   ├── paths.py               #   ← central path config (all I/O locations)
│   ├── config.py              #   ← loads config.yaml
│   ├── features.py            #   ← shared signed-log1p transform
│   ├── tracking.py            #   ← appends runs.jsonl
│   ├── metrics.py             #   ← the standard eval suite (per-family + macro)
│   │
│   ├── preprocess.py          # CURRENT pipeline ──────────────
│   ├── preprocess_paper.py    #   paper-aligned split
│   ├── cnn_paper.py           #   neural pillar
│   ├── baselines.py           #   XGBoost / RF / IsolationForest
│   ├── novelty.py             #   MSP + Mahalanobis
│   ├── behavior.py            #   7 fuzzy behaviours
│   ├── ltn_paper.py           #   symbolic pillar (configurable)
│   ├── cnn_auxhead_paper.py   #   representation-level injection
│   │
│   ├── skyline_oracle.py      # analysis ──────────────────────
│   ├── rescore_logits.py      #   log-odds re-scoring
│   ├── fusion_beaconlike.py   #   inference-level fusion
│   │
│   ├── cnn3.py                # LEGACY temporal split ─────────
│   ├── eval.py                #   (superseded, kept for the
│   ├── ltn.py                 #    secondary hard-mode result)
│   │
│   ├── dashboard_server.py    # live local ops console
│   ├── visual.py
│   └── check.py
│
├── data/
│   ├── raw_csv_full/          # CIC-IDS2017 GeneratedLabelledFlows (gitignored)
│   └── processed/
│       └── paper/             # the paper-aligned split + meta side-tables
│
├── models/                    # *.keras + scaler/encoder *.pkl (gitignored)
│
├── outputs/
│   ├── arrays/                # X_test.npy, y_train/val/test splits (gitignored)
│   ├── embeddings/            # X_*_emb.npy (gitignored)
│   ├── predictions/           # y_prob_*.npy (gitignored)
│   ├── metadata/              # class_names, history.pkl, thresholds (gitignored)
│   └── figures/               # *.png eval plots (tracked)
│
├── docs/                      # Documentation (see below)
└── .venv/                     # Python 3.11 virtualenv (gitignored)
```

> **Paths are centralised in [`scripts/paths.py`](scripts/paths.py).** Every script imports it, so artifacts always land in the right subfolder instead of the repo root. Output directories are created automatically on first run.

## Key Results

> Measured on the **paper-aligned split** (`data/processed/paper/`), which is the protocol all
> current results use. Headline metric is **macro zero-day PR-AUC** — the mean over adequately
> powered unseen families (Bot, Web Brute Force, Web XSS; n≥100). Underpowered families
> (Heartbleed n=11, Infiltration n=36, SQL Injection n=21) are excluded rather than reported to
> false precision. Full tables, provenance, and retractions in [docs/STATUS.md](docs/STATUS.md).

| Channel | macro zero-day PR-AUC | Bot PR-AUC | Bot lift vs chance |
|---------|----------------------:|-----------:|-------------------:|
| CNN (`cnn_paper.py`) | **0.6446** | 0.0591 | 1.7× |
| XGBoost | 0.6372 | 0.0608 | 1.8× |
| LTN, no axioms (control, n=3 seeds) | 0.6194 | — | 2.07× (range 1.5–2.9×) |
| Mahalanobis (open-set distance) | 0.4585 | **0.1467** | **4.3×** |
| Isolation Forest | 0.0628 | 0.0571 | 1.7× |

**What the symbolic pillar actually showed (Phase 2, concluded):**

- **Symbolic axioms do *not* currently improve on the neural baseline.** Every axiom variant tried
  (Ax3–Ax6) costs macro PR-AUC relative to the no-axiom control, and this holds across 3 seeds with
  non-overlapping ranges. An earlier claim that a targeted Bot axiom "roughly doubles Bot lift" was
  **retracted** after multi-seeding — it compared the control's worst seed against the axiom's best.
- **Inference-time fusion of a zero-day-specific symbolic signal is structurally impossible here.**
  A non-leaky combiner must be fit on validation data, which by construction contains no zero-day
  flows — so it cannot discover the value of a signal that is only useful on the class it never sees.
  Fitted coefficients came back `[2.35, 0.02]`: the combiner learned to ignore the symbolic channel.
- **Bot's signal is present in the 68 per-flow features.** An oracle test (reveal ~1,000 labelled Bot
  flows to XGBoost, held-out eval) lifts Bot PR-AUC from 0.031 to **0.976**. The near-chance
  never-seen score is a zero-day *transfer* failure of the closed-set classifier, not an
  information-theoretic limit.
- **Behaviours:** 7 named fuzzy behaviours in `behavior.py` (`BurstTraffic`, `HighVolume`,
  `LargePackets`, `HighEntropy`, `ScanProbe`, `BeaconLike`, `RepeatedConnections`). The last is
  always 0.0 pending wiring to the IP/port side table.

**Status:** Phases 0–2 complete. Knowledge Graph, Decision Fusion, and Explainability are not built.

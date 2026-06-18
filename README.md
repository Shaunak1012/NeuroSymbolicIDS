# NeuroSymbolic-IDS

A hybrid intrusion detection system that combines a 1D Convolutional Neural Network with symbolic rule-based reasoning (Logic Tensor Networks) to detect zero-day network attacks.

Trained on the [CIC-IDS2017](https://www.unb.ca/cic/datasets/ids-2017.html) dataset. The CNN learns from known attack families; symbolic rules extend coverage to unseen (zero-day) attack types at inference time.

## Quick Start

```bash
# 1. Preprocess raw CSVs
python scripts/preprocess.py

# 2. Train CNN and extract embeddings
python scripts/cnn3.py

# 3. Evaluate CNN baseline (zero-day recall, PR-AUC)
python scripts/eval.py

# 4. Train Hybrid-LTN model (neuro-symbolic fusion)
python scripts/ltn.py
```

## Documentation

### Implemented (current state)

| File | Contents |
|------|----------|
| [docs/architecture.md](docs/architecture.md) | System design, data flow diagram |
| [docs/dataset.md](docs/dataset.md) | CIC-IDS2017 dataset, classes, split strategy |
| [docs/pipeline.md](docs/pipeline.md) | Step-by-step pipeline execution guide |
| [docs/models.md](docs/models.md) | CNN architecture, LTN hybrid loss, hyperparameters |
| [docs/neuro_symbolic.md](docs/neuro_symbolic.md) | Symbolic behaviour extraction and fuzzy logic axioms |
| [docs/artifacts.md](docs/artifacts.md) | Catalog of all saved files (.npy, .keras, .pkl, .csv) |
| [docs/scripts_reference.md](docs/scripts_reference.md) | Per-script purpose, inputs, and outputs |

### Implementation audits (verified current state, incl. bugs)

| File | Contents |
|------|----------|
| [docs/implementation/cnn_current.md](docs/implementation/cnn_current.md) | CNN — verified correct, minor notes |
| [docs/implementation/behaviour_abstraction_current.md](docs/implementation/behaviour_abstraction_current.md) | Behaviour module — ❌ orphaned/dead code |
| [docs/implementation/ltn_current.md](docs/implementation/ltn_current.md) | LTN — ⚠️ axioms are label tautologies |

### Living / dynamic docs (updated every session)

| File | Contents |
|------|----------|
| [docs/STATUS.md](docs/STATUS.md) | Current component status, priorities, decisions, results |
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | Dated history of changes |
| [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md) | Bug & risk tracker |
| [CLAUDE.md](CLAUDE.md) | Session onboarding guide (read first each session) |

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
├── scripts/                   # Pipeline code (run in order)
│   ├── paths.py               #   ← central path config (all I/O locations)
│   ├── preprocess.py
│   ├── cnn3.py
│   ├── eval.py
│   ├── behavior.py
│   ├── ltn.py
│   ├── visual.py
│   └── check.py
│
├── data/
│   ├── raw_csv/               # CIC-IDS2017 input CSVs (gitignored)
│   └── processed/             # clean_*, features_*, labels_* (gitignored)
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

- **CNN baseline**: ~5–15% recall on zero-day attacks, PR-AUC ~0.45–0.55
- **Hybrid-LTN**: Improves zero-day recall via symbolic axioms applied during training
- **Symbolic flags**: 6 atomic behaviour flags + 3 compound patterns (scan, exfiltration, covert)

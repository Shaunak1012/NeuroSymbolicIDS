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

# 7. Anomaly pillar — benign-only autoencoder (Phase 3)
python scripts/autoencoder_paper.py
```

> **Multi-seed anything trainable** with `CNN_SEED` / `LTN_SEED` / `AE_SEED` / `NOVELTY_SEED`. Each
> writes `<name>_s<seed>` artifacts and leaves the seed-42 originals untouched. Three findings in
> this project have been retracted as single-seed artifacts — **treat any n=1 number as provisional.**

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

All figures below are **mean over 3 seeds (42/43/44), log-odds scored**, with the seed range given —
single-seed numbers have repeatedly proven unsafe in this project (three retractions to date).

| Channel | family | macro zero-day PR-AUC | Bot PR-AUC | Bot lift | Web BF | XSS |
|---------|:---:|----------------------:|-----------:|---------:|-------:|------:|
| **CNN** (`cnn_paper.py`) | A | **0.6399** [0.6353, 0.6446] | 0.0446 [0.0241, 0.0591] | 1.3× | **0.9226** | **0.9524** |
| XGBoost † | A | 0.6372 *(deterministic)* | 0.0608 | 1.8× | 0.9484 | 0.9023 |
| LTN, no axioms (control) | A | 0.6194 [0.6029, 0.6505] | 0.0712 [0.0528, 0.0985] | 2.1× | 0.8889 | 0.8982 |
| **RandomForest** | A | 0.5995 [0.5682, 0.6235] | **0.1311** [0.0576, 0.1933] | **3.8×** | 0.8686 | 0.7987 |
| MSP (softmax novelty) | A/B | 0.5884 [0.5694, 0.6123] | 0.0448 [0.0245, 0.0591] | 1.3× | 0.8719 | 0.8485 |
| Mahalanobis (embedding distance) | B | 0.3777 [0.3363, 0.4585] | 0.1030 [0.0413, 0.1467] | 3.0× | 0.5840 | 0.4462 |
| **Autoencoder** (`autoencoder_paper.py`) | B | 0.0970 [0.0894, 0.1014] | **0.1314** [0.1078, 0.1647] | **3.8×** | 0.1048 | 0.0547 |
| IsolationForest | B | 0.0653 [0.0628, 0.0683] | 0.0637 [0.0571, 0.0732] | 1.9× | 0.0862 | 0.0459 |

*(A) = trained on known attacks · (B) = trained on benign only.*
† XGBoost is **deterministic** under `random_state` here (no subsampling configured), so seeds
42/43/44 are byte-identical — n=1 with verified reproducibility, not a variance estimate.

**Result 1 — a double dissociation between the CNN and the autoencoder.** Their seed ranges do not
overlap on any family and a paired bootstrap confirms it (p<0.0005 each): the AE wins Bot **2.9×**,
the CNN wins Web Brute Force **8.8×** and XSS **17.4×**. Each wins decisively where the other fails.

> ⚠️ **This is a dissociation between two *models*, not two *method families*.** An earlier framing —
> "the problem is structurally (B), so benign-only methods are needed to reach Bot" — was
> **falsified on 2026-08-03**: RandomForest, a supervised (A)-family method, **ties the autoencoder
> on Bot** (0.1311 vs 0.1314, p=0.88) while beating it by 0.50 on macro. You do not need a (B)
> method to reach Bot.

**Result 2 — why the CNN fails on Bot (answered 2026-08-03).** The failure is **representational,
not informational**, and three measurements compose into the mechanism:

- **100% of Bot flows are classified BENIGN** by the CNN (all 3 seeds, mean p(BENIGN)=0.9984). Bot
  is not ambiguous to the model — it is confidently asserted benign.
- **The features that separate Bot from benign have 0/8 overlap** with the features the known-class
  task needs. A discriminative model learns only what separates the classes it is shown, so there is
  no pressure to represent Bot's signature.
- **Consequently the CNN's Bot ranking is noise**: cross-seed Spearman ρ = **−0.090**, against
  0.68–0.83 for every other family. The autoencoder, by contrast, ranks Bot *reproducibly*
  (ρ = 0.827).

This single cause explains four previously separate symptoms — the CNN's Bot score, the Knowledge
Graph's cluster-purity lottery, Mahalanobis's Bot spread, and RandomForest's Bot swing. It is *not*
an information limit: given labels, Bot is separable at oracle PR-AUC **0.9988**.

**Result 3 — web attacks are not being "detected".** The CNN assigns ~90% of Web Brute Force and
XSS flows to **`DoS slowloris`**, a known *attack* class. Their 0.92–0.95 PR-AUC is misclassification
landing on the correct side of the benign/attack binary — transfer by absorption, not zero-day
detection.

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

**What the anomaly pillar showed (Phase 3, concluded):**

- **A benign-only autoencoder is the most reliable Bot channel measured** — 3.8× chance
  [3.2–4.8], versus Mahalanobis 3.0× [1.2–4.3] and the CNN's 1.3× [0.7–1.7]. It uses **no attack
  labels at all**, in training or model selection, so it is zero-day-legitimate by construction.
- **It is near-perfect on the structurally extreme rare families** — Heartbleed 1.0000 recall,
  Infiltration 0.8611 — but both are underpowered (n=11, n=36) and excluded from the macro.
- **It fails on web attacks** (0.1048 / 0.0547 vs the CNN's 0.9226 / 0.9524), which is what makes
  the dissociation a dissociation rather than a ranking.
- **Changing the scoring rule alone does not help.** MSP — novelty-style scoring on the CNN's own
  softmax — lands at Bot 0.0448 vs the CNN's 0.0446. The dissociation is driven by *what a model
  trains on*, not by how its score is computed, and forms a monotonic frontier across
  (A-train/A-score) → (A/B) → (A/B) → (B/B).

**Reproducibility note.** Every comparative claim above is n=3 seeds with ranges reported. Three
findings have been **retracted** after multi-seeding exposed them as single-seed artifacts (a
symbolic axiom's Bot benefit, "Mahalanobis 4.3× on Bot", and a Knowledge-Graph clustering-stability
result). Retractions are preserved in place with their reasoning in
[docs/STATUS.md](docs/STATUS.md) and [docs/CHANGELOG.md](docs/CHANGELOG.md) rather than deleted.

**Status:** Phases 0–3 complete (protocol reset · neural pillar + baselines · symbolic pillar ·
anomaly pillar). Phase 4 (Knowledge Graph) is **blocked on a representation decision** — see
[docs/STATUS.md](docs/STATUS.md) → "PHASE-4 BLOCKER". Decision Fusion and Explainability are not built.

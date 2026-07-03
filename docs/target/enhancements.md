# Enhancement Backlog (Captured Ideas)

> **➡️ Most of these are now folded into the [conference_roadmap.md](conference_roadmap.md) (plan v1.2 + "godly" agenda).** This file remains the raw idea list; the roadmap is the scheduled, prioritized version. Post-LTN-failure status noted per item below.
>
> Quick status: #1 autoencoder → **Phase 3** · #2 multi-seed → **Phase 5 (now with significance tests)** · #3 cross-dataset → **Phase 6** · #4 HITL → demo · #5 calibration/abstain → **Phase 5** · #6 latency → **Phase 5** · #7–9 hygiene → **Phase 0 (tracking/config mandatory now)** · Engelen labels → **Phase 0 decision**. New conference-tier items (failure-anatomy study, significance testing, classical baselines, explanation-faithfulness, adversarial probe, response engine) live in the roadmap.

## Tier 1 — high value, strengthens the core thesis

### 1. Unsupervised anomaly-detection baseline ⭐ highest leverage
Zero-day detection is fundamentally an anomaly-detection problem, so reviewers will ask "why not just an autoencoder / Isolation Forest / one-class SVM?" Add one (autoencoder reconstruction error trained on benign-only is the natural fit) as a comparison column in the ablation. If neuro-symbolic beats it → headline result; if not → learned early. Without this, the thesis has an unanswered baseline.

### 2. Multi-seed runs with variance
Everything is currently `seed=42`, single run. A research claim needs **mean ± std over 3–5 seeds** — a 2% PR-AUC gain could otherwise be noise. Cheap, big credibility payoff.

### 3. Cross-dataset generalization
Train on CIC-IDS2017, test on a different dataset (CIC-IDS2018, UNSW-NB15, or NSL-KDD). Gold-standard evidence that detection is behaviour-based, not dataset-artifact-based. Directly stress-tests the "symbolic rules generalize" claim. Strong differentiator.

## Tier 2 — completes the "explainable & adaptive" story

### 4. Human-in-the-loop / active-learning loop
The KG detects emerging patterns with no known label. Close the loop: surface emerging clusters → analyst labels → promote to a known class → optionally retrain. Makes "Adaptive" in the title real; compelling narrative.

### 5. Score calibration + "abstain" option
Calibrated scores (reliability diagrams) are needed for fusion anyway. On top: when all three signals are uncertain, abstain and flag for human review instead of forcing a verdict. Uncertainty-aware IDS is a clean contribution.

### 6. Latency / throughput measurement
IDS is real-time. One benchmark — "X flows/sec on CPU, KG adds Y ms" — answers the deployability question for almost no effort.

## Tier 3 — engineering hygiene (de-risks the multi-stage build)

### 7. Real config + one orchestration script
No config exists (stale `utils/config.py` was deleted). Add a `config.yaml` for hyperparameters + a single `run_all.py` / Makefile to run the pipeline end to end.

### 8. Tiny test suite
Unit tests for behaviour extraction and the fuzzy-logic operators, plus a synthetic-data smoke test of the full pipeline. Catches silent breakage across the 5 stages.

### 9. Experiment tracking
TensorBoard (TF already installed) or MLflow instead of `print` + pickle. Optional; makes the ablation table self-generating.

## Data caveat to note in the write-up
CIC-IDS2017 has documented labeling errors; a corrected version exists (Engelen et al., 2021). Worth a sentence in the report, or switching to the corrected labels — dataset-familiar reviewers will notice.

## Suggested priority if/when pulled in
- **Must-haves** (low effort, defend the core claim): #1, #2, #6
- **Standout differentiators** (if time allows): #3, #4
- **Fold in while building** (not retrofitted): #7, #8, #9

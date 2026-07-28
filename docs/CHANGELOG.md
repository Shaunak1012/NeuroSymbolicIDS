# Changelog (Living Document)

> Append a dated entry whenever something meaningful changes (code, data, decisions, results). Newest first. Keep entries short; link to detail docs.

## 2026-07-27 (multi-seed results — the Ax6 headline finding is retracted)

- **Ran 2 additional seeds (43, 44) for `ltn_ctrl_w0`, `ltn_ax6_w0p5`, `ltn_ax6_w1p0`** (n=3 each with seed 42) and log-odds re-scored all 6 new models. This was flagged as necessary before shipping any comparative claim as far back as the aux-head reproducibility gap earlier the same day — it caught a real overclaim within hours of that warning being written.
- **RETRACTED: "Ax6 roughly doubles Bot's lift."** With n=3 seeds, the control's mean Bot lift (2.07x, range 1.5–2.9x) is *higher* than either Ax6 variant's (1.87x / 1.70x, both narrower ranges). The original single-seed comparison (1.5x control vs 2.2x Ax6) pitted the control's worst seed against Ax6's best seed — pure seed luck, not a real effect. Flagged as retracted at every place this session claimed it: the integration-points table, the B2 write-up, and the log-odds re-score entry.
- **What survives, and is now stronger than the single-seed version:** Ax6 robustly costs macro PR-AUC — zero overlap between the control's range (0.60–0.65) and either Ax6 config's, across all 3 seeds. That part of the finding is *more* solid than it looked on n=1, not less.
- **New finding: ω=1.0 is not the "safe zone" it appeared to be.** 2 of 3 new seeds collapsed catastrophically (macro 0.052, 0.037; both early-stopped by epoch 10) — the same failure mode as `ltn_anat_w2p0`'s deterministic ω=2.0 collapse, just triggered stochastically near ω=1.0 rather than always. Seed 42's 0.5316 was the lucky outcome, not representative. ω=0.5 is comparatively more stable (0/3 seeds collapsed) but still consistently below the control on macro.
- **Bot lift is highly seed-sensitive even with zero axioms** — the control alone swings from 1.5x to 2.9x across seeds. Any single-seed claim about Bot detection at this scale (n=1,956 test flows) needs multiple seeds to mean anything.
- Net: the fusion finding and the macro-cost finding both survive this correction; the specific "Ax6 helps Bot" claim does not. If Ax6 is pursued further, the priority is understanding why ω=1.0 collapses 2/3 of the time before drawing more conclusions from single runs at that setting.

## 2026-07-27 (inference-level fusion — the third integration point tested, and why it fails)

- **Checked whether Ax6 generalizes to zero-day families it wasn't designed from** (Heartbleed n=11, Infiltration n=36, SQL Injection n=21) using data already on disk from the earlier Ax6 runs. Mixed and noisy: Heartbleed and Infiltration move in the right direction (0.5x→2.9x, 0.8x→1.4x lift), SQL Injection moves the wrong way (369x→256x) — but at these sample sizes any of these could flip from one or two predictions changing. The only statistically meaningful signal remains Bot up / Web attacks down. Flagging this explicitly: Ax6 was designed by looking directly at Bot's labels (the feature-importance scan in `skyline_oracle.py`), so "Ax6 helps Bot" is a weaker zero-day-generalization claim than it might read as — it's closer to "hand-built rule works on the class it was built for" than evidence of transferable symbolic knowledge.
- **Built and ran `scripts/fusion_beaconlike.py`** — the third of the "three symbolic integration points" from `conference_roadmap.md`, and the one never attempted before this session. Fits a small logistic combiner (CNN's attack log-odds + BeaconLike's raw score) on validation data only — the paper split's val set contains no zero-day flows by construction, so this cannot leak into the zero-day evaluation, unlike the "leaky fusion" already flagged as invalid in earlier entries.
- **Result: fusion changes nothing.** Macro 0.6447 vs the CNN's 0.6446 alone; Bot lift 1.7x, identical to baseline. Fitted coefficients came back `[2.35, 0.02]` — the combiner learned to essentially ignore BeaconLike.
- **This is a real, mechanistic finding, not a failed experiment.** The fusion weights are fit on validation data, which cannot contain the pattern (Bot) that makes BeaconLike valuable — a non-leaky calibration structurally cannot discover the worth of a zero-day-specific signal. This explains why loss-level injection (Ax6) is currently the *only* mechanism, of the three tested, that gets a hand-specified zero-day signature into the model at all: it imposes the constraint directly rather than requiring the data to reveal its value. Reframes the macro cost Ax6 pays from "a flaw to fix with fusion" to "the price of the only lever available" — at least for this signal.

## 2026-07-27 (log-odds re-score — resolves the deferred CE finding, strengthens the control)

- **Retrained `cnn_auxhead_l0.5`** (needed the `model.save` added earlier) and ran `scripts/rescore_logits.py` across all 10 saved models now that TF is unblocked.
- **Corrects the 3 genuinely-saturated runs.** `ltn_ctrl_w0` moves from 0.5937/~1.0x Bot lift to a clean **0.6049/1.5x**; `ltn_repro` and `ltn_v2` similarly move up. The Ax6-vs-same-ω comparison from the previous entry is untouched — neither `ltn_anat_*` nor `ltn_ax6_*` was ever saturated, so "Ax6 roughly doubles Bot lift" still holds exactly.
- **Resolves the deferred CE-vs-focal question: false alarm.** `ltn_repro` (CE + base axioms) was flagged as the worst fair-loop variant based on its saturated blended score. Cleanly measured it's mid-pack (macro 0.5751), between the control and the old fixed-ω axiom variants — plain CE isn't demonstrably a poor loss choice here.
- **The clean control is stronger than previously measured**, which raises the bar the axioms have to clear: even with zero axioms, the custom loop already gets 1.5x lift on Bot. Ax6's honest accounting against the *best* baseline is +0.7–1.1x Bot lift for a ~0.07–0.09 macro cost — a real, worthwhile, but not free trade, not a wash against a weak control as it looked before this correction.
- **`ltn_anat_w2p0`'s collapse is confirmed genuine, not a saturation artefact** — PR-AUC is rank-based and threshold-independent, so it only moves under log-odds rescoring when tie blocks were corrupting the ranking (true for the other 3). It stays at 0.0348 here, meaning the ω=2.0 model's weights actually degenerated rather than merely underflowing its output scores.
- **The aux-head retrain didn't reproduce its own Bot number** — 0.8x lift this run vs ~1.0x the first time, same seed and config. Most plausible explanation is ordinary single-seed noise (TF training isn't bit-deterministic across runs even with a fixed seed), which is itself a concrete argument for the still-outstanding multi-seed work before any comparative claim ships.

## 2026-07-27 (Ax6 trained — prediction confirmed, with a real tradeoff)

- **TensorFlow unblocked.** Root cause was Windows Smart App Control (`VerifiedAndReputablePolicyState=1` in `HKLM\SYSTEM\CurrentControlSet\Control\CI\Policy`), rejecting TF's unsigned compiled wheels under its "Enterprise signing level" requirement. User turned it off via Windows Security; reversible without reinstall on this build (25H2, build 26200.8875, past the 26200.8116 cutoff). Not a code or environment problem.
- **Ran `ltn_ax6_w0p5` and `ltn_ax6_w1p0`** — identical configs to the earlier `ltn_anat_w0p5`/`w1p0` runs, with Ax6 (`BeaconLike`) now live in the axiom set. **B2's prediction is confirmed: Bot lift roughly doubles at both ω values** (1.1x → 2.2x at ω=0.5; 1.1x → 1.8x at ω=1.0). The axiom-injection mechanism was never the bottleneck — the old axioms simply targeted the wrong signature.
- **The gain isn't free.** At ω=0.5, Bot's improvement came with Web Brute Force and Web XSS PR-AUC dropping (0.833→0.779, 0.796→0.696), pulling macro down (0.5552→0.5169). At ω=1.0 the tradeoff is milder — Bot still improves while macro is roughly flat. `sat_loss` weights all active axioms uniformly regardless of how many flows each targets, so satisfying one family's constraint pulls slack from the shared decision boundary that the other axioms also depend on.
- **Neither Ax6 variant beats the plain CNN's macro (0.6446).** The neural baseline still wins in aggregate; this is the first symbolic intervention with a measured, targeted effect on the family that was actually stuck, at a real but non-catastrophic cost elsewhere — a genuinely different, more nuanced Phase-2 headline than either "axioms don't help" or "axioms are free."

## 2026-07-27 (targeted Bot axiom — built and validated, training blocked)

- **Designed a first-pass Bot axiom from a median-only glance and got it wrong.** `Bwd Packet Length Mean` looked like a clean separator (benign median 77, Bot median 6), but the full distribution shows Bot's values cluster exactly at the percentile boundary used for the fuzzy ramp — the resulting signal was net anti-correlated with Bot (ROC 0.3995, worse than random). Caught by validating standalone against real labels before spending a training run on it, not by inspection.
- **Replaced with what the full distribution actually supports:** destination-port membership against a small, externally-defined list of well-known service ports (`behavior.WELL_KNOWN_PORTS`) — not data-fitted, not a magnitude ramp (port number isn't ordinal; a magnitude ramp was tried and also failed for the same median-lies reason). Standalone: ROC 0.887, PR-AUC 0.135 on Bot-vs-benign alone (chance 0.034, ~4x lift) — comparable to Mahalanobis.
- **Added `BeaconLike` to `behavior.py`** (vectorized via `np.isin`, not a per-row Python loop), wired into `ltn_paper.py` as **Ax6** (behaviour weight matrix and `sat_loss` now carry 4 columns instead of 3). Fixed `cnn_auxhead_paper.py`'s `BEH` list, which used `BEHAVIOUR_NAMES[:5]` to drop the constant-zero `RepeatedConnections` entry — inserting `BeaconLike` before it in the list would have silently excluded the new behaviour too; now filters by name.
- **Blocked on the same TensorFlow issue** — re-checked before this write-up, still failing on a 5th distinct native DLL. The axiom is built and standalone-validated; its effect on the trained LTN (the actual test of B2's prediction) is not yet measured.

## 2026-07-27 (skyline/oracle — beaconing hypothesis falsified)

- **Ran the skyline/oracle experiment** (`scripts/skyline_oracle.py`, sklearn/xgboost only, unaffected by the TF block): revealed a random 50% of each zero-day family's test flows to XGBoost training (held-out other 50% for eval, no leakage), same hyperparams as `baselines.py`. Bot PR-AUC rose from 0.0314 (never-seen) to **0.9764** (56x chance) with ~1,000 labelled examples. Every family recovers similarly (macro 0.5947 → 0.9899).
- **This falsifies the "Bot's signal is absent from the per-flow representation" claim written into STATUS/CHANGELOG earlier the same day.** That was an untested domain-knowledge hypothesis (Bot = C2 beaconing = a cross-flow phenomenon) presented as a finding without verifying it against the labels. The oracle result shows the information was always in the 68 per-flow features; the near-chance never-seen score is a **zero-day transfer failure of the closed-set classifier**, not an information-theoretic limit.
- **Isolated a Bot-vs-benign-only classifier's feature importances** to find the actual signature: `Bwd Packet Length Mean` 77→6 (near-empty backward payload), `Destination Port` 80→8080, `Init_Win_bytes_forward` 116→8192 — a clean, mundane, single-flow pattern. None of the existing axioms (Ax3 LargePackets∧HighEntropy, Ax4 BurstTraffic, Ax5 ScanProbe) touch it; they're volume/scan-shaped, tuned for DoS/PortScan.
- **Reframes the Phase-2 thesis:** not "symbolic injection is capped by the representation" but "the current axiom set targets the wrong signature for the family that matters." Next step is a targeted axiom test (B2 in STATUS), not host/session-level feature aggregation (C) — deprioritized, no longer well-motivated for Bot specifically (may still help Infiltration/lateral-movement).

## 2026-07-27 (measurement audit — retractions + corrected metrics)

- **Found a float32 softmax saturation defect invalidating 4 of 13 runs.** Scores were `1 - softmax[benign]`; for a confident model `p(benign)` rounds to exactly 1.0, so the score underflows to exactly 0.0 — on `ltn_ctrl_w0`, 99.25% of benign and 51.7% of zero-day flows. The 1%-FPR threshold therefore lands at 0.0 and flags everything (achieved FPR 1.000), producing the bogus "recall=1.0000 for every family" rows and an identical `zd_f1 = 0.1315` across three models (the algebraic predict-all constant at 7% prevalence). Saturated: `ltn_ctrl_w0`, `ltn_repro`, `ltn_v2`, `ltn_anat_w2p0` — i.e. every fair-loop run the control experiment depended on.
- **Found the blended headline metric is a size-weighted mixture** of families whose detectability differs ~30x, so it moves for reasons unrelated to detection quality — and it reorders the model ranking versus a per-family view.
- **Rewrote `metrics.py`:** headline is now per-family PR-AUC + macro-average over adequately powered families (n≥100), with `chance_pr_auc`/`lift` columns; blended demoted to secondary; Heartbleed (n=11), Infiltration (n=36), SQL Injection (n=21) excluded as underpowered instead of reported to 4 dp; added saturation diagnostics (`achieved_fpr`, `largest_tie_frac`) and a `to_logodds` helper.
- **RETRACTED "axioms help at ω=0.5–1.0"** (written earlier the same day). It rested on blended (0.520 > 0.501); on macro it reverses (0.5552 vs 0.5937), and per-family ω=0.5 is worse than the control on both families carrying signal.
- **RETRACTED "XGBoost ≈ CNN (tabular SOTA matches us)"** from Phase 1. On macro the CNN beats XGBoost (0.6446 vs 0.6372) — the tie was an artefact of family sizes. The "pivot the story to explanation/adaptivity" framing was motivated by a tie that isn't there.
- **RETRACTED "unsupervised anomaly is far worse → motivates supervised neuro-symbolic".** IsolationForest is far worse overall (macro 0.063) but scores **0.0571 on Bot — indistinguishable from the CNN's 0.0591**. 884K labelled training flows buy no Bot signal over an unsupervised outlier detector.
- **New central finding: Bot is at chance for every supervised method** (lift 1.0–1.8x); Mahalanobis (0.1467, 4.3x) is the sole exception and is a *distance* method — the open-set-recognition signature. Evidence that the per-flow representation does not contain the Bot signal: Bot is C2 beaconing, whose signature is periodicity *across* flows, destroyed by i.i.d. flow classification. Explains why every symbolic intervention moves the number by only ±0.02, and why Ax3/4/5 (thresholded functions of the same 68 input features) are tautological.
- Upheld: the ω=2.0 collapse, and the aux head underperforming the plain CNN (0.5744 vs 0.6446, same training method, neither saturated).
- Added `scripts/rescore_logits.py` (recompute scores as `logsumexp(attack_logits) − benign_logit` from saved models) and a missing `model.save` in `cnn_auxhead_paper.py`. **Both blocked**: TensorFlow stopped loading mid-session with `An Application Control policy has blocked this file` across rotating native DLLs; numpy/sklearn/scipy unaffected. Not worked around — machine security control.
- Revised plan: A (fix measurement) → B (skyline/oracle to establish the per-family ceiling) → C (host/session-level aggregation using the IP+timestamp from the dataset upgrade, with a falsifiable prediction that Bot rises above chance).

## 2026-07-27 (Phase 2 — symbolic pillar, fair-loop batch + training-loop speedup)

- **Resolved the training-method confound.** Ran the ω=0 control under the fairness-upgraded custom loop (best-by-val-loss, LR annealing) — it lands at zd PR-AUC 0.501, vs the CNN reference's 0.599. Confirms most of the LTN-vs-CNN gap is the custom loop itself, not the axioms. All LTN numbers must be read relative to 0.501, not 0.599.
- **Failure-anatomy ω-sweep (fixed omega, focal + both axioms):** ω=0.5 → 0.520 PR-AUC, ω=1.0 → 0.513 (both beat the control — axioms genuinely help in this band), ω=2.0 → 0.092 (sharp collapse, SAT overwhelms CE, reproduces the original full-run failure mode). Safe zone ≈ ω∈[0.5, 1.0].
- **Adaptive ratio-mode (`ltn_v2`) undershoots the sweet spot** — nets out at ω_eff≈0.1-equivalent (0.491), close to the control rather than the fixed-sweep optimum. Flagged as a recalibration candidate.
- **`ltn_repro` (CE + base axioms) is the worst fair-loop variant** (0.485, below the control) — isolates plain CE as a poor loss choice for this imbalance, independent of the axiom question.
- **Aux behaviour-prediction head measured** (`scripts/cnn_auxhead_paper.py`, representation-level integration point): 0.497 zd PR-AUC, using the same `model.fit` method as the CNN reference (no loop confound) — still underperforms it, landing in the same band as the SAT variants.
- **Assembled the Phase-2 "three symbolic integration points" table** (loss-level / representation-level / inference-level) per `conference_roadmap.md`. Inference-level (fusion) remains the expected primary performance mechanism — not yet built (Phase 4).
- **Training-loop performance fix:** `ltn_paper.py`'s custom loop ran fully eager (~3,450 raw Python iterations/epoch), starving the CPU's 16 cores behind Python dispatch overhead (~2.6 cores observed). Rewrote the train step under `@tf.function` — required precomputing benign/attack masks as numeric arrays instead of per-batch string comparison (not graph-compatible) — plus explicit `intra_op=16`/`inter_op=2` thread config in both `ltn_paper.py` and `cnn_auxhead_paper.py`. Smoke-tested equivalent, faster per epoch; all Phase-2 results above are from the upgraded loop.
- Full results in `outputs/metadata/runs.jsonl`. Updated STATUS.

## 2026-06-18 (Phase 1 — neural pillar + baselines)

- **Retrained the CNN in-venv on the paper split** (`scripts/cnn_paper.py`) — loadable Keras-2 models, log1p transform, `metrics.py` headline. Early-stopped epoch 25, val-acc 0.997.
- **Fixed a real focal-loss bug** (see KNOWN_ISSUES): Keras passes `y_true` as `(batch,1)`, so `one_hot` broadcast to a `(B,B,n)` garbage tensor → frozen val_loss / random accuracy. Confirmed by controlled race (focal as-is 0.50 vs fixed 0.996 val-acc). Fixed `reshape([-1])` in `cnn_paper.py` + legacy `cnn3.py`. Also fixed callback monitors (`val_sparse_categorical_accuracy`) that had silently disabled early-stopping/checkpointing.
- **Classical baselines** (`scripts/baselines.py`): XGBoost, RandomForest, IsolationForest. **Free novelty channels** (`scripts/novelty.py`): MSP + Mahalanobis.
- **Phase-1 zero-day-only PR-AUC:** xgboost 0.604 · cnn 0.599 · msp 0.587 · mahalanobis 0.583 · rf 0.564 · isolation_forest 0.153. Honest: XGBoost ≈ CNN (pivot to explanation/adaptivity/response); unsupervised anomaly far worse (motivates supervised NSAI). Per-family: CNN catches Web attacks (~0.9) but misses Bot (0.002)/Infiltration.
- 6 fusion channels saved to `outputs/predictions/`. Metrics logged to `runs.jsonl`. xgboost pinned.

## 2026-06-18 (dataset upgrade → full variant with IP/timestamp)

- **Switched from the ML-CVE variant to the full `GeneratedLabelledFlows`** (added `data/raw_csv_full/`, gitignored). Rewrote `scripts/preprocess.py` to ingest the 85-col CSVs, guard the `Infinity`-string quirk (`to_numeric coerce`), and extract a **meta side-table** (`meta_train/test.csv` — Flow ID, Source/Dest IP+Port, Protocol, Timestamp) aligned row-for-row through cleaning.
- **Verified feature parity:** identical 68 features, same 10 constant columns, exact same row counts (train 1,666,532 / test 1,161,344) as ML-CVE → behaviour indices unchanged (Destination Port at 0, etc.).
- **`preprocess_paper.py` now splits on indices** so meta follows each row into paper train/val/test (`data/processed/paper/meta_{train,val,test}.csv`), all aligned.
- **Result:** IP/timestamp available → `RepeatedConnections` + source-level response replay **unblocked**. PortScan test set = 15,881 flows from **1 source IP → 998 distinct dest ports** (canonical scan signature). `config.yaml`: `variant: GeneratedLabelledFlows`, `has_ip_timestamp: true`. Done at the zero-cost window (before any training on the paper split).

## 2026-06-18 (Phase 0 — protocol reset)

- **Built the paper-aligned split** (`scripts/preprocess_paper.py` → `data/processed/paper/`): pools all 5 days, 9 known classes (BENIGN + 8 attacks incl. PortScan/DDoS) stratified 80/10/10 (train 883,796 / val 110,475 / test 114,658), benign under-sampled 1:1 (balanced 50/50), 6 rare classes (Bot, Web×3, Infiltration, Heartbleed) appended to test only. Leakage asserted (no zero-day in train/val). Temporal split kept untouched as secondary hard-mode.
- **Config + scaffolding:** `config.yaml` (all protocol params) + `scripts/config.py`, `scripts/features.py` (shared transform), `scripts/tracking.py` (JSONL run logger). pyyaml pinned.
- **log1p A/B (Phase 0.3):** signed-log1p `sign(x)·log1p(|x|)` beat raw on the paper split (PR-AUC 0.980 vs 0.965) → adopted in config.
- **Data constraint found:** the CSVs are the **MachineLearningCVE** variant — no Flow ID/IP/Timestamp columns → IP-based `RepeatedConnections` and response-replay are limited (documented in config `has_ip_timestamp: false`).
- **Nuance recorded:** overall binary is easy (~0.97) under the paper split since PortScan/DDoS are known; the challenge metric is the **zero-day-only binary** (~4,183 test flows), matching the paper's "6 unknown" metric.

## 2026-06-18 (strategic pivot → conference roadmap)

- **LTN full run completed and underperformed** — PR-AUC 0.4529 vs CNN baseline 0.6689 (−0.22); early-stopped ~epoch 10, val accuracy declined after epoch 2. Root cause: focal CE collapsed to ~0.0005, SAT term dominated ~40:1. Per-family: PortScan 0.36→0.16, DDoS 0.67→0.64.
- **Fusion investigation (post-hoc, no retraining):** leaky logistic fusion (fit on zero-day-labelled test half) reached 0.78 (+0.11) — but the honest **label-free** parameter-free fusion was −0.16. Conclusion: behaviours carry real signal, but supervised transfer to zero-day is the wall. Also found `model_multiclass_best.keras` is **Keras 3** (won't load in our Keras-2.15 venv) → in-venv retrain required.
- **Read the base paper** (`basepaper.pdf`, Bizzarri et al., IEEE). Findings: it uses payload bytes (1500) not flow features; stratified 80/10/10 with **known attacks in test**; zero-day = rare classes only (keeps PortScan/DDoS in training); **balanced data + plain CE + ω=1** (why their SAT stays gentle and ours dominated). Their result: zero-day acc 48→60%. Our protocol was a much harder, misaligned exam.
- **Decided a strategic pivot** to a top-tier-publication plan: protocol reset (paper-aligned split) → retrain in-venv → reproduce paper → fix + extend → multi-pillar fusion → cross-dataset → response engine. Captured in **[conference_roadmap.md](target/conference_roadmap.md)** (plan v1.2 + Tier-S/A/B agenda). Headline thesis: *"when and why neuro-symbolic training fails under imbalance, and the inference-time fusion fix."* Response/IPS engine added as Shaunak's solo final phase. Updated STATUS, enhancements.

## 2026-06-18 (LTN re-grounded)

- **Re-grounded the LTN axioms on behaviours** (`scripts/ltn.py`), fixing the core flaw (label tautologies). Kept Ax1/Ax2 as supervised anchors; replaced Ax3 (was DoS-label) with **LargePackets∧HighEntropy → ¬benign** and Ax4 (was Patator-label) with **BurstTraffic → ¬benign**, weighted per-flow by fuzzy behaviour confidences from `behavior.py` (computed on raw features pre-scaling, shuffled in lockstep with batches). ScanProbe/HighVolume deliberately excluded from training axioms (ScanProbe benign-heavy in training → reserved for KG stage).
- **Added smoke-test hook** (`LTN_SUBSET` / `LTN_EPOCHS` env vars). Smoke test (50k×2) passed end-to-end: no NaNs, behaviour axioms compute & satisfy (Ax3≈0.90, Ax4≈0.78).
- **Launched first full training run** (background, CPU, headless `MPLBACKEND=Agg`, logging to `outputs/ltn_run.log`). Results pending. Baseline to beat: CNN PR-AUC 0.6689.
- Updated [ltn_current.md](implementation/ltn_current.md), STATUS.

## 2026-06-18 (session close)

- **Compute decision recorded:** training stays on **CPU** (Ryzen 9 9950X3D, 62 GB RAM — LTN run estimated ~30–60 min). GPU (RTX 5080) **deferred**: Blackwell needs WSL2 + CUDA 12.8 + newer TF + likely Keras 3 migration — poor ROI now, revisit if training volume grows. Logged in STATUS Open Decisions.
- **STATUS.md prepped for resume:** added a "▶ RESUME HERE" block (next action = re-ground LTN axioms on behaviours) and a "Remaining Work" queue (LTN → RepeatedConnections → KG → Fusion → Explainability → Ablation). No code changed this turn.

## 2026-06-18 (behaviour abstraction rebuilt)

- **Rebuilt `scripts/behavior.py`** from broken/dead to working+validated. Verified the real 68-column feature order via `check.py` (old indices were badly wrong — e.g. old `RATE_FEATURES=[5,6,7]` actually pointed at packet-length fields, old flags pointed at IAT). New module: vectorised, fuzzy `[0,1]` outputs, data-driven percentile thresholds saved to `outputs/metadata/behaviour_thresholds.npy`, built-in validation harness.
- **Two bugs caught by validation and fixed:** (1) flag-count `ProtocolAnomalies` fired 45% on benign / 0% on attacks (matched benign UDP), so the flag approach was **dropped** — flag-count columns are ~0 even for real scans in CIC-IDS2017; (2) replaced it with **`ScanProbe`** (short duration × tiny payload), which scores **0.955 on the zero-day PortScan** vs 0.244 benign.
- **Behaviours:** BurstTraffic, HighVolume, LargePackets, HighEntropy (approx), ScanProbe, RepeatedConnections (unavailable → 0). LargePackets/HighEntropy ~7–8× attack-discriminative; PortScan+DDoS (largest zero-day families) strongly covered. Web Attacks/Bot remain weakly covered (documented limitation).
- Updated [behaviour_abstraction_current.md](implementation/behaviour_abstraction_current.md), STATUS, KNOWN_ISSUES.
- **Next:** re-ground LTN axioms on these behaviours.

## 2026-06-18 (enhancements captured)

- **Captured an enhancement backlog** at [target/enhancements.md](target/enhancements.md) — anomaly-detection baseline, multi-seed variance, cross-dataset eval, active-learning loop, calibration/abstain, latency benchmark, config/orchestration/tests, dataset-label caveat. **Backlog only — nothing scheduled or started.**

## 2026-06-18 (reorg)

- **Repository reorganised to professional layout.** Moved all generated artifacts out of the repo root into `data/processed/`, `models/`, and `outputs/{arrays,embeddings,predictions,metadata,figures}/`. Added [`scripts/paths.py`](../scripts/paths.py) as the single source of path truth and rewired every script (`preprocess`, `cnn3`, `eval`, `ltn`, `behavior`, `check`, `visual`) to import it — no more hardcoded root paths. Verified: all scripts compile; all 28 existing artifacts present at new locations (eval can run without regeneration).
- **Artifact cleanup.** Deleted stale `model_focal.keras` + `behaviour_thresholds.npy`. LTN outputs never existed (script not yet run), so nothing to clear there. Kept valid preprocessing/CNN/eval artifacts (expensive to regenerate).
- **Archived** the original `PROJECT_DOCUMENTATION.md` → `docs/archive/` (superseded by the structured docs).
- **Rewrote `.gitignore`** to directory-based ignores matching the new layout (`outputs/figures/` intentionally tracked).
- Git check: only `.gitignore` + an old `preprocess_friday.py` were ever tracked; no large binaries committed.

## 2026-06-18 (later)

- **Dead code removed.** Deleted `utils/config.py` + `utils/` dir (stale, from abandoned payload pipeline, imported by nothing). Removed the unused `y_train_b`/`y_val_b` binary-split block in `cnn3.py`. **Kept** `behavior.py` and the `fuzzy_*` operators in `ltn.py` — both feed the upcoming behaviour/LTN rework. `model_focal.keras` (stale binary artifact) left in place but gitignored. Updated all doc references.
- **Environment set up.** Installed Python 3.11.9 (winget, user scope) and created `.venv` at repo root. Added pinned `requirements.txt` (Python 3.11 / TF 2.15.1 / Keras 2 / numpy 1.26.4 + KG libs networkx, python-louvain + explainability lib shap). Smoke test passed: all imports work, `tensorflow.keras` (Keras 2) OK, CPU mode (no GPU).
- **Rewrote `.gitignore`** to match the real artifact layout (root-level `*.npy`/`*.keras`/`*.pkl` + large generated CSVs + `.venv/`); the old one referenced the abandoned payload pipeline's paths.
- **Found `utils/config.py` is stale orphaned code** from the abandoned raw-PCAP/payload pipeline (PAYLOAD_LEN=1500, 3 classes). Not imported anywhere. Corrected `scripts_reference.md`; logged in KNOWN_ISSUES.

## 2026-06-18

- **Documentation overhaul.** Created `docs/` (implemented-state docs), `docs/target/` (target-architecture specs + gap analysis), `docs/implementation/` (line-by-line source audits), and dynamic tracking files (`STATUS.md`, `CHANGELOG.md`, `KNOWN_ISSUES.md`). Added root `CLAUDE.md` for session onboarding.
- **Source audit completed** for `cnn3.py`, `behavior.py`, `ltn.py`, `preprocess.py`, `eval.py`:
  - CNN verified ✅ correct (minor: double class-weighting).
  - `behavior.py` found ❌ orphaned/dead (never imported; thresholds never generated; feature indices misaligned). See [audit](implementation/behaviour_abstraction_current.md).
  - `ltn.py` found ⚠️ conceptually wrong (axioms are label tautologies, fuzzy operators unused, not wired to behaviour). See [audit](implementation/ltn_current.md).
- **Correction:** earlier draft docs wrongly listed **Bot** as a training class (index 8) with 9 train classes. Source confirms Bot is a **zero-day/test** class; training has ~8 classes. Fixed in `dataset.md`, `models.md`, `artifacts.md`.
- **Decisions recorded:** KG → NetworkX; Fusion → fixed-weights then logistic; input → flow-feature CSVs. See [STATUS.md](STATUS.md#open-decisions).

<!-- TEMPLATE for new entries:
## YYYY-MM-DD
- **<area>.** <what changed and why>. <link to detail>.
-->

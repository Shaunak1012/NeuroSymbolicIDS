# Project Status (Living Document)

> **Update this file at the end of every working session.** It is the single source of truth for "where are we right now." Last updated: **2026-07-27**.

## ▶ RESUME HERE (next session)

**Major pivot decided (2026-06-18).** LTN full run finished and **underperformed** the baseline
(PR-AUC 0.45 vs CNN 0.67). Root cause diagnosed: focal CE collapsed to ~0.0005 so the SAT term
dominated ~40:1 (base paper used *balanced data + plain CE + ω=1*, keeping SAT gentle). We then
read the base paper (`basepaper.pdf`) and found our split is a *much harder, misaligned* protocol.
**Decision: protocol reset + rebuild per plan v1.2.** Full plan + conference agenda in
**[conference_roadmap.md](target/conference_roadmap.md)** — read that first.

**✅ Phase 0 DONE + dataset upgraded (2026-06-18).** Paper-aligned split (`preprocess_paper.py` → `data/processed/paper/`): 9 known classes stratified 80/10/10 = train 883,796 / val 110,475 / test 114,658, balanced 50/50, 6 zero-day in test only, leakage-verified. `config.yaml` + `config.py`/`features.py`/`tracking.py`/`metrics.py` scaffolding done. **log1p A/B: signed-log1p wins (0.980 vs 0.965) → adopted.**

**🔼 Switched to the FULL dataset variant (GeneratedLabelledFlows).** Replaced ML-CVE with the richer `data/raw_csv_full/` (has IP/port/timestamp). `preprocess.py` rewritten to extract a **meta side-table** (`meta_train/test.csv`) aligned by row; `preprocess_paper.py` carries meta through the split (`data/processed/paper/meta_{train,val,test}.csv`). **68 features + row counts identical to ML-CVE** (verified) — behaviour indices unchanged. IP/timestamp now available → `RepeatedConnections` + source-level response replay **unblocked** (PortScan test = 1 source IP → 998 dest ports, textbook). `config.yaml data.has_ip_timestamp: true`. Corrected labels (Engelen): still deferred.

**⚠️ Key nuance:** on the paper split, overall binary PR-AUC is ~0.97 (PortScan/DDoS are now *known*). The **real challenge metric is binary on the zero-day-only subset** (Bot/Web/Infiltration/Heartbleed, ~4,183 test flows) — matching the paper's "6 unknown classes" metric. Track that separately everywhere.

**✅ Phase 1 DONE (2026-06-18).** CNN retrained in-venv on paper split (loadable Keras-2 models). Caught+fixed a **focal-loss shape bug** (`(batch,1)` broadcast froze training) and a callback-monitor bug. Classical baselines + free novelty channels done. **6 fusion channels saved.**

**Phase 1 results — ⚠️ SUPERSEDED 2026-07-27, see the corrected table below.** These are
the *blended* zero-day PR-AUC, which the audit showed is a size-weighted mixture and
reorders the ranking. Kept for provenance only:
| Channel | zd PR-AUC (blended, superseded) | zd ROC |
|---------|-----------|--------|
| xgboost | 0.604 | 0.876 |
| cnn_paper | 0.599 | 0.855 |
| msp | 0.587 | 0.855 |
| mahalanobis | 0.583 | **0.883** |
| random_forest | 0.564 | 0.812 |
| isolation_forest | 0.153 | 0.766 |

**🔴 RETRACTED: "XGBoost (tabular SOTA) ≈ CNN".** On the corrected macro metric the CNN
*beats* XGBoost (0.6446 vs 0.6372) — the tie was an artefact of family sizes in the blend.
The "pivot the story to explanation/adaptivity/response" framing was motivated by a tie
that isn't there and should be revisited. **Also retracted: "unsupervised anomaly is far
worse → motivates supervised neuro-symbolic".** IsoForest is far worse *overall* (macro
0.063) but scores 0.0571 on Bot — indistinguishable from the CNN's 0.0591. On the family
that actually matters, supervision buys nothing. Upheld: CNN catches Web attacks (~0.92–0.96)
and misses Bot/Infiltration.

**🔄 Phase 2 IN PROGRESS (symbolic pillar).** `scripts/ltn_paper.py` (configurable: loss/axioms/omega/omega-mode, loss-ratio normalization = SAT-domination fix, ScanProbe axiom now valid) + `scripts/cnn_auxhead_paper.py` (aux behaviour head) written & smoke-tested (UNCOMMITTED).

**🔴 MEASUREMENT DEFECT FOUND (2026-07-27) — earlier Phase-2 conclusions RETRACTED.**
An audit of the actual score distributions found two defects that invalidate the
comparison this batch was run to settle. Do not cite the ω-sweep conclusions written
earlier today; the corrected picture is below.

**Defect 1 — float32 softmax saturation.** Scores were `patk = 1 - softmax[benign]`.
For a confident model `p(benign)` rounds to exactly 1.0, so `patk` underflows to
exactly 0.0: on `ltn_ctrl_w0`, **99.25% of benign and 51.7% of zero-day flows sit at
exactly 0.0**. The 1%-FPR threshold therefore lands at 0.0, flags everything
(achieved FPR = 1.000), and produces the "recall=1.0000 for every family" rows —
an artefact, not detection. `zd_f1 = 0.13153467603729385` is the algebraic
predict-all-positive constant at 7% prevalence, identical across three different
models. **4 of 13 runs are saturated: `ltn_ctrl_w0`, `ltn_repro`, `ltn_v2`,
`ltn_anat_w2p0`** — i.e. all three fair-loop runs the control experiment depended on.
`metrics.py` now detects and flags this (`diagnostics.saturated`).

**Defect 2 — the blended headline is a size-weighted mixture.** "Benign vs all 6
unknowns" averages families whose detectability differs by ~30x, so it moves for
reasons unrelated to detection quality. `metrics.py` now reports **per-family PR-AUC
+ macro-average over powered families (n≥100)** as the headline; the blend is
secondary. Heartbleed (n=11), Infiltration (n=36) and SQL Injection (n=21) are
excluded as underpowered rather than reported to 4 dp.

**Corrected table** (macro = mean PR-AUC over Bot / Web-BF / Web-XSS; `lift` = PR-AUC ÷ chance):

| Run | sat? | **macro** | Bot | Bot lift | Web BF | XSS | blended (old headline) |
|---|---|---|---|---|---|---|---|
| cnn_paper | no | **0.6446** | 0.0591 | 1.7x | 0.9194 | 0.9554 | 0.599 |
| xgboost | no | 0.6372 | 0.0608 | 1.8x | 0.9484 | 0.9023 | 0.604 |
| msp | no | 0.6123 | 0.0591 | 1.7x | 0.8864 | 0.8913 | 0.587 |
| ltn_ctrl_w0 | **YES** | (0.5937) | 0.0342 | 1.0x | 0.8609 | 0.8861 | 0.501 |
| cnn_auxhead_l0.5 | no | 0.5744 | 0.0339 | 1.0x | 0.8505 | 0.8386 | 0.497 |
| ltn_anat_w0p5 | no | 0.5552 | 0.0367 | 1.1x | 0.8326 | 0.7962 | 0.520 |
| ltn_anat_w1p0 | no | 0.5241 | 0.0369 | 1.1x | 0.8105 | 0.7250 | 0.513 |
| mahalanobis | no | 0.4585 | **0.1467** | **4.3x** | 0.6830 | 0.5457 | 0.583 |
| isolation_forest | no | 0.0628 | 0.0571 | 1.7x | 0.0861 | 0.0451 | 0.153 |
| ltn_anat_w2p0 | YES | (0.0348) | 0.0344 | 1.0x | 0.0477 | 0.0223 | 0.092 |

Bracketed values are computed on saturated (tied) scores and are **not trustworthy** —
they need the log-odds re-score (`scripts/rescore_logits.py`, blocked, see below).

**Corrected interpretation:**
1. **RETRACTED — "axioms help at ω=0.5–1.0".** That rested on blended (0.520 > 0.501).
   On macro it *reverses*: ω=0.5 scores 0.5552 vs the control's 0.5937, and per-family
   ω=0.5 is worse than the control on both families that carry signal (Web BF 0.833 vs
   0.861; XSS 0.796 vs 0.886). The claim does not survive; n=1 seed and a saturation
   confound on the control make it unsafe in either direction.
2. **RETRACTED — "XGBoost ≈ CNN, tabular SOTA matches us".** On macro the CNN *beats*
   XGBoost (0.6446 vs 0.6372); the blended ordering was an artefact of family sizes.
   The Phase-1 "pivot the story to explanation/adaptivity" framing needs revisiting —
   it was motivated by a tie that isn't there.
3. **UPHELD — the ω=2.0 collapse.** 0.0348 macro, every family at chance. Real under
   any metric; the phase transition stands.
4. **UPHELD — the aux head does not help.** `cnn_auxhead_l0.5` (0.5744) vs `cnn_paper`
   (0.6446), same `model.fit` training method, neither saturated → clean comparison.
5. **RETRACTED same-day — "Bot's signal is absent from the per-flow representation
   (beaconing thesis)".** This was a hypothesis stated as a finding, and the skyline
   oracle test (`scripts/skyline_oracle.py`, 2026-07-27) falsifies it directly: revealing
   only ~1,000 labelled Bot flows to XGBoost (held-out eval, no leakage) lifts Bot PR-AUC
   from 0.0314 (never-seen) to **0.9764** — 56x chance, near-ceiling. A Bot-vs-benign-only
   classifier finds a clean, mundane, **single-flow** signature: `Bwd Packet Length Mean`
   77→**6** (near-empty backward payload), `Destination Port` 80→**8080**,
   `Init_Win_bytes_forward` 116→**8192**. Bot's low never-seen PR-AUC is a **zero-day
   transfer failure of the closed-set classifier**, not an information-theoretic limit —
   the information was always in the 68 features. Do not repeat the beaconing/cross-flow
   framing without new evidence; it was an untested domain intuition, not a measurement.
6. **CORRECTED — why the symbolic axioms don't move Bot.** Not "information absent from
   the representation" (see #5). Ax3 (LargePackets∧HighEntropy), Ax4 (BurstTraffic), Ax5
   (ScanProbe) are volume/scan-shaped — tuned for DoS/PortScan — and none of them touch
   Bot's actual signature. **Ax6 built and standalone-validated (2026-07-27, see B2
   below):** the initial 2-signal design (small backward payload ∧ high port-number) was
   built from a median-only glance and turned out **backwards on the full distribution** —
   Bot's `Bwd Packet Length Mean` clusters exactly at the percentile boundary (ROC 0.40,
   anti-correlated). What actually works, after checking full distributions: destination
   port **set membership** against a small fixed list of well-known service ports (not a
   magnitude ramp — port number isn't ordinal) reaches **ROC 0.887, PR-AUC 0.135 alone**
   (chance 0.034, ~4x lift) — comparable to Mahalanobis. Wired into `ltn_paper.py` as Ax6
   (`BeaconLike` in `behavior.py`); **training blocked on the same TF issue**, so the
   effect on the trained model is not yet measured. Mahalanobis's edge on Bot (4.3x, vs
   1.0–1.8x for closed-set classifiers) is still real and still an open-set-recognition
   signature — a closed-set softmax has no probability mass reserved for "structurally
   novel," which is the actual mechanism, not missing information.
7. **Deferred — CE vs focal.** `ltn_repro` (CE + base axioms) looked worst on blended
   (0.485), but it is one of the saturated runs; the comparison is unsafe until re-scored.

**Phase-2 "three symbolic integration points" (per [conference_roadmap.md](target/conference_roadmap.md))
— ALL THREE NOW TESTED (2026-07-27):**

⚠️ **The row-1 Ax6 numbers below are single-seed (seed 42) and were RETRACTED later the
same day** — see "🔴 MULTI-SEED RESULTS" further down. With n=3 seeds, Ax6's mean Bot
lift (1.7–1.9x) is *lower* than the control's (2.07x); only the macro cost survives as a
robust finding. Table kept as originally measured for the record; do not cite the Bot-lift
column for Ax6 without reading the retraction below.

| Integration point | Method | Status | Macro zd PR-AUC | Bot lift |
|---|---|---|---|---|
| (0) Neural baseline | `scripts/cnn_paper.py` | ✅ reference | **0.6446** | 1.7x |
| (1) Loss-level, no targeted axiom | `ltn_ctrl_w0` / `ltn_anat_w0p5` | ✅ measured, clean | 0.6049 / 0.5552 | 1.5x / 1.1x |
| (1) Loss-level, targeted (Ax6) | `ltn_ax6_w0p5` / `ltn_ax6_w1p0` | ⚠️ seed 42 only, see retraction | 0.5169 / 0.5316 | ~~2.2x / 1.8x~~ |
| (2) Representation-level | Aux behaviour-prediction head | ✅ measured | 0.5814 | 0.8–1.0x (seed-noisy) |
| (3) Inference-level | `scripts/fusion_beaconlike.py` — logistic fusion of CNN logit + BeaconLike, calibrated on known-class val only | ✅ measured | 0.6447 | 1.7x — **no change from baseline** |

**Only loss-level injection with a targeted axiom (Ax6) moves Bot at all** *(single-seed
claim — see multi-seed retraction below; treat this paragraph as superseded)*. Inference-level
fusion — the mechanism the original roadmap expected to be primary — measurably does
**nothing**: fitted coefficients came back `[2.35, 0.02]` (base model logit, BeaconLike),
i.e. the calibration learned to ignore the symbolic signal almost entirely.

**Why, precisely — and this is the real finding, not just a null result.** The fusion
combiner is fit on validation data, which by construction contains **no Bot flows**
(zero-day is test-only in this protocol). BeaconLike is a signal specifically *about* the
one class the fitting data can never contain. A non-leaky calibration cannot discover the
value of a zero-day-specific signal — nothing in the distribution it's fit on makes that
signal look useful. This is a structural limit of inference-time fusion for this class of
axiom, not a tuning failure. It explains, mechanistically, why loss-level injection is not
just *one option among three* but currently the **only** mechanism that can get a
hand-specified zero-day signature into the model at all: training-time constraints don't
need the value of the signal to be *discoverable* from labelled data the way a fitted
combiner does — they impose it directly. The macro cost Ax6 pays (finding above) isn't a
flaw to route around with fusion; on this evidence, it looks like the price of the only
lever available.

Reframes the Phase-2 thesis once more: not "symbolic injection is capped by the
representation" (oracle result, #5, already ruled this out), and not merely "the old
axioms targeted the wrong signature" (Ax6 already confirmed this) — but **"only
training-time constraint injection can deliver a hand-specified zero-day signal at all;
inference-time fusion cannot discover what it was never shown."** Whether that generalizes
beyond this one signal/dataset is untested — a different axiom correlated with *known*
classes too (unlike BeaconLike, which is Bot-specific) might fuse successfully; that's a
distinct, open question, not addressed here.

**Performance note (2026-07-27):** `ltn_paper.py`'s custom training loop was fully eager (~3,450 raw Python iterations/epoch) and left most CPU cores idle. Rewrote the train step under `@tf.function` (masks precomputed as numeric arrays instead of per-batch string comparison, since that's not graph-compatible) + explicit `intra_op=16`/`inter_op=2` thread config in both `ltn_paper.py` and `cnn_auxhead_paper.py`. Verified numerically equivalent (same ops, same math, just compiled) and faster per epoch on CPU.

**🔴 BLOCKER (2026-07-27): TensorFlow will not load.** Mid-session, `import tensorflow`
began failing with `ImportError: DLL load failed ... An Application Control policy has
blocked this file` — a different native DLL each attempt (`_pywrap_py_exception_registry`,
`flags_pybind`, `_pywrap_determinism`), so the policy is blocking TF's binaries broadly.
Python 3.11.9, numpy, sklearn and scipy all import fine; only TF is affected, in both
PowerShell and Git Bash. TF ran normally earlier the same session, so a Windows
Application Control / Smart App Control policy refresh landed mid-session. **Diagnose via
Event Viewer → Applications and Services Logs → Microsoft → Windows → CodeIntegrity →
Operational.** Not worked around — it is a machine security control and the user's call.
Blocks anything needing model load/train (TF-based): the log-odds re-score, multi-seed
neural runs. Does **not** block sklearn/xgboost (unaffected — confirmed by running B below).

**✅ B. Skyline/oracle — RUN (2026-07-27, `scripts/skyline_oracle.py`).** Revealed ~1,000
labelled Bot flows to XGBoost (held-out eval, no leakage): Bot PR-AUC 0.0314 → **0.9764**
(56x chance). **Falsifies the beaconing/cross-flow hypothesis** — see finding #5/#6 above.
Bot's signal is fully present per-flow; the failure is zero-day transfer, not missing
information. This changes the next step from "build cross-flow features" (C, now
deprioritized — no longer well-motivated) to a cheaper, more targeted fix:

**🟡 B2: targeted Bot axiom — BUILT + standalone-validated, training BLOCKED (2026-07-27).**

Isolated a Bot-vs-benign-only XGBoost's feature importances (no TF needed). First-pass
design from a median-only glance (`Bwd Packet Length Mean` 77→6, `Destination Port`
80→8080) was **wrong**: checking the *full* distribution, not just the median, showed
Bot's backward-payload values cluster exactly at the percentile boundary used for the
ramp, making the signal net **anti-correlated with Bot** (ROC 0.3995 — worse than
random). Diagnosed, dropped, and replaced with what the full-distribution check actually
supports: destination-port **set membership** against a small fixed list of well-known
service ports (`behavior.WELL_KNOWN_PORTS` — external domain knowledge, not
data-fitted; a magnitude ramp on the raw port number was tried and also failed, for the
same "median lies" reason). Standalone (`metrics`-style check, no LTN):

| Signal | Bot ROC | Bot PR-AUC | vs chance |
|---|---|---|---|
| magnitude ramp (dropped) | 0.400 | 0.034 | ~1.0x (anti-correlated) |
| **well-known-port membership (kept)** | **0.887** | **0.135** | **~4.0x** |

Comparable to Mahalanobis's 4.3x — a real, non-tautological signal. Added as
`BeaconLike` in `behavior.py`, wired into `ltn_paper.py` as **Ax6**
(`W_tr`/`sat_loss` now carry 4 behaviour columns instead of 3), and
`cnn_auxhead_paper.py`'s `BEH` list fixed to be robust to `BEHAVIOUR_NAMES` order
(`[:5]` would have silently dropped the new entry given its list position).

**✅ B2 RESOLVED (2026-07-27).** TF unblocked (root cause: Windows Smart App Control,
`VerifiedAndReputablePolicyState=1` — blocking TF's unsigned wheels; user turned it off,
reversible on this build per Microsoft, no reinstall needed). Ran `ltn_ax6_w0p5` and
`ltn_ax6_w1p0` — same configs as the earlier `ltn_anat_*` runs, Ax6 now live:

| Run | macro | Bot PR-AUC | Bot lift |
|---|---|---|---|
| cnn_paper (reference) | 0.6446 | 0.0591 | 1.7x |
| ltn_anat_w0p5 (no Ax6) | 0.5552 | 0.0367 | 1.1x |
| **ltn_ax6_w0p5 (+Ax6)** | 0.5169 | **0.0762** | **2.2x** |
| ltn_anat_w1p0 (no Ax6) | 0.5241 | 0.0369 | 1.1x |
| **ltn_ax6_w1p0 (+Ax6)** | 0.5316 | **0.0632** | **1.8x** |

**🔴 RETRACTED same day, after multi-seeding (see the "MULTI-SEED RESULTS" section
below) — this was single-seed luck, not a real effect. Do not cite "Ax6 doubles Bot
lift."** Kept below for the record, with the correction directly beneath it.

~~**Prediction confirmed: Ax6 roughly doubles Bot's lift at both ω values.** The
axiom-injection mechanism is not the bottleneck — Ax3/4/5 failed to move Bot because
they targeted the wrong signature, not because loss-level injection structurally cannot
help. This is the strongest evidence yet for the reframed Phase-2 thesis (finding #6).~~

**Not free, and this is the more interesting part.** At ω=0.5, Bot's gain came with Web
Brute Force and Web XSS *dropping* (0.779/0.696 vs 0.833/0.796 without Ax6) — macro fell
0.5552→0.5169. At ω=1.0 the tradeoff is milder: Bot still improves (1.8x) while macro is
roughly flat (0.5241→0.5316). `sat_loss` averages all active axiom satisfactions
uniformly regardless of how many flows each one actually targets — pushing on one
family's signature pulls slack from the shared decision boundary. **Neither variant beats
the plain CNN's 0.6446 macro** — the neural baseline still wins in aggregate; Ax6 is the
first symbolic intervention that measurably moves the specific family that was stuck,
at a real (not catastrophic) cost elsewhere.

**✅ Step A CLOSED (2026-07-27) — log-odds re-score run.** `scripts/rescore_logits.py`
(TF unblocked) re-scored all 10 saved models. Corrects the 3 genuinely-saturated
control-family runs; the Ax6 comparison above is untouched (neither side was ever
saturated):

| Run | macro (log-odds) | Bot lift | change |
|---|---|---|---|
| ltn_ctrl_w0 (no axioms) | **0.6049** | **1.5x** | was 0.5937 / ~1.0x — corrected **up** |
| ltn_repro (CE+base) | **0.5751** | 1.1x | was flagged "worst variant" from a saturated blend — **not true** |
| ltn_v2 (focal+both, adaptive) | **0.5727** | 1.0x | corrected up |
| ltn_anat_w2p0 (ω=2.0) | 0.0348 | 1.0x | **still flagged saturated after the fix — the collapse is real**, not a measurement artefact |

**Two real corrections, not just cleanup:**
1. **Finding #7 (deferred CE-vs-focal) is resolved: false alarm.** `ltn_repro` looked
   worst under the saturated blended score; cleanly scored it's mid-pack (0.5751),
   between the control and the old-axiom fixed-ω variants. Plain CE is not a
   demonstrably poor loss choice here.
2. **The clean control is stronger than previously measured, which raises the bar Ax6
   has to clear.** Without any axioms, the custom loop already gets 1.5x lift on Bot
   (not ~1.0x/chance) and 0.6049 macro (not 0.5937). *(True as far as it goes on seed 42
   — but this whole "vs control" comparison turned out to need seeds, not just clean
   scoring, to be trustworthy. See "🔴 MULTI-SEED RESULTS" further down: with n=3 the
   control's own Bot lift ranges 1.5–2.9x, and the "roughly doubles" claim below does
   not survive.)*

`ltn_anat_w2p0` staying saturated even in log-odds space is itself informative: PR-AUC
is rank-based and threshold-independent, so log-odds only changes it when massive tie
blocks were corrupting the ranking (true for ctrl_w0/repro/v2). Here it doesn't move,
meaning the ω=2.0 model didn't just underflow its scores — its weights genuinely
collapsed. The phase-transition finding is confirmed, not an artefact.

`cnn_auxhead_l0.5` was retrained (needed `model.save`, added earlier) — fresh run's Bot
lift came in at 0.8x (below chance), vs ~1.0x the first time round. Same seed, same
config; the gap is most plausibly ordinary single-seed noise (TF isn't perfectly
deterministic across runs even with a fixed seed), which is itself the strongest
argument yet for the still-outstanding multi-seed work.

## 🔴 MULTI-SEED RESULTS (2026-07-27) — the Ax6 "prediction confirmed" claim does not survive

Ran 2 additional seeds (43, 44) for `ltn_ctrl_w0`, `ltn_ax6_w0p5`, `ltn_ax6_w1p0` — n=3
each with the original seed 42 — and log-odds re-scored all 6 new models
(`scripts/rescore_logits.py`, extended `TAGS`). This is exactly what the
"still-outstanding multi-seed work" warning above was for, and it caught a real
overclaim from earlier the same day.

**Bot lift, n=3 per config:**

| Config | seed42 | s43 | s44 | mean | range |
|---|---|---|---|---|---|
| ltn_ctrl_w0 (no axioms) | 1.5x | 1.8x | **2.9x** | **2.07x** | 1.5–2.9x |
| ltn_ax6_w0p5 | 2.2x | 1.9x | 1.5x | 1.87x | 1.5–2.2x |
| ltn_ax6_w1p0 | 1.8x | 1.8x | 1.5x | 1.70x | 1.5–1.8x |

**Macro, n=3 per config:**

| Config | seed42 | s43 | s44 | mean | range |
|---|---|---|---|---|---|
| ltn_ctrl_w0 | 0.6049 | 0.6029 | 0.6505 | **0.6194** | 0.603–0.651 (tight) |
| ltn_ax6_w0p5 | 0.5169 | 0.5601 | 0.4501 | 0.5090 | 0.450–0.560 |
| ltn_ax6_w1p0 | 0.5316 | **0.0520** | **0.0366** | **0.2067** | catastrophic, 2/3 seeds |

**🔴 RETRACTED: "Ax6 roughly doubles Bot's lift."** The control's mean Bot lift (2.07x)
is *higher* than either Ax6 variant's (1.87x, 1.70x), with heavily overlapping ranges.
The original comparison (1.5x control vs 2.2x Ax6, both seed 42) pitted the control's
worst seed against Ax6's best seed. That's exactly the single-seed trap the "still
outstanding multi-seed work" note two sections up predicted — the trap it was written
to catch is the one that caught this finding, hours after it was written.

**What survives, and is now *stronger* than the single-seed version:**
1. **Ax6 robustly costs macro.** No overlap at all between the control's range
   (0.60–0.65) and either Ax6 config's — this holds across all 3 seeds, not a fluke.
2. **ω=1.0 is not the "milder tradeoff" it looked like on n=1 — it's the riskier one.**
   2 of 3 seeds collapse catastrophically (macro 0.05, 0.04; both early-stopped by
   epoch 10) while the control never does. Seed 42's 0.5316 was the lucky outcome, not
   the norm — the same failure mode as `ltn_anat_w2p0`'s ω=2.0 collapse, just triggered
   stochastically at ω=1.0 rather than deterministically. ω=0.5 is comparatively more
   stable (0/3 seeds collapse) but still consistently below control on macro.
3. **Bot lift itself is highly seed-sensitive even with zero axioms** — the control
   alone swings from 1.5x to 2.9x on random initialization. Any single-seed claim about
   Bot detection on this dataset (n=1,956, but apparently still noisy at this scale)
   needs seeds to mean anything.

**Net effect on the Phase-2 thesis:** the fusion finding (inference-level fusion
structurally can't discover a zero-day-specific signal) and the macro-cost finding
(loss-level injection consistently trades macro for *something*) both survive. What
does **not** survive is the specific claim that Ax6 delivers a targeted, reliable
Bot-detection improvement — on this evidence it delivers a real, robust macro cost and
an unreliable, noise-level Bot effect that a plain unweighted control can match or beat
on any given seed. If Ax6 is pursued further, the next step is understanding *why*
ω=1.0 collapses 2/3 of the time (likely the same runaway SAT-dominance dynamic as
ω=2.0, just probabilistic near the boundary) before drawing any more conclusions from
it.

C (host/session-level features) is not abandoned — RepeatedConnections/fan-out may still
help Infiltration or lateral-movement detection specifically — but it is no longer
motivated as a Bot fix, and B2 no longer provides positive evidence either way.

**Focal-loss `reshape([-1])` fix** required in any new loss. Failure-anatomy *balance* axis
(vary benign_ratio) still TODO.

**Key measured findings to carry forward:**
- Leaky fusion (fit on zero-day labels) hit 0.78 (+0.11) — behaviours carry real signal, but
  label-free fusion (parameter-free) was −0.16. The signal is real; unsupervised transfer is the wall.
- `model_multiclass_best.keras` was saved in **Keras 3** → won't load in our Keras-2.15 venv.
  Retrain in-venv is required anyway (Phase 1).

**Compute:** **CPU** (Ryzen 9 9950X3D). GPU (RTX 5080 / Blackwell) deferred. For long runs use
`python -u` so progress is live and completion is caught reliably (last run's notification was missed).

## Environment

✅ **Ready.** `.venv/` at repo root — Python 3.11.9, TF 2.15.1 (Keras 2), numpy 1.26.4, + networkx / python-louvain / shap. CPU mode (no GPU). Pinned in `requirements.txt`. Use `.venv\Scripts\python.exe`. See [CLAUDE.md](../CLAUDE.md#environment--venv).

## Repository layout

✅ **Reorganised (2026-06-18).** Artifacts no longer dump to repo root — they live under `data/processed/`, `models/`, and `outputs/{arrays,embeddings,predictions,metadata,figures}/`. All paths are centralised in [`scripts/paths.py`](../scripts/paths.py); every script imports it. Verified: all scripts compile, all 28 existing artifacts present at new locations. Layout documented in [README](../README.md#project-structure) and [artifacts.md](artifacts.md#where-everything-lives).

## Component Status

| Component | Status | File | Notes |
|-----------|--------|------|-------|
| Preprocessing | ✅ Working | `scripts/preprocess.py` | Flow features, binary + multiclass labels. Drops IPs/ports. |
| CNN (multiclass) | ✅ Verified correct | `scripts/cnn3.py` | See [cnn_current.md](implementation/cnn_current.md). Minor: double class-weighting. |
| CNN evaluation | ✅ Working | `scripts/eval.py` | Produces PR-AUC baseline + `cnn_zeroday_eval.png`. |
| Behaviour abstraction | ✅ Rebuilt & validated | `scripts/behavior.py` | Verified indices, vectorised, fuzzy [0,1], thresholds saved. PortScan/DDoS strongly covered. Not yet wired into LTN. See [doc](implementation/behaviour_abstraction_current.md). |
| LTN reasoning (paper-split) | 🟡 Anatomized, multi-seeded — macro cost confirmed, Bot benefit retracted | `scripts/ltn_paper.py` | Clean (log-odds) control macro 0.6049 (n=1) / 0.6194 (n=3 mean); every axiom variant tried (old Ax3-5, targeted Ax6) costs macro relative to control, robust across seeds. ω=2.0 always collapses; ω=1.0 collapses 2/3 seeds — not the "safe zone" it looked like on n=1. Ax6's apparent Bot-lift improvement did not survive multi-seeding (control's own Bot lift ranges 1.5–2.9x). See STATUS "RESUME HERE" → "🔴 MULTI-SEED RESULTS" for the full table + retraction. |
| LTN reasoning (legacy, temporal split) | 🔴 Superseded | `scripts/ltn.py` | Ran, underperformed (0.45 vs 0.67); SAT dominated CE ~40:1. Superseded by the paper-split protocol reset — see [doc](implementation/ltn_current.md). |
| Knowledge Graph | ❌ Not built | — | Rescoped as memory + explainability corroboration. Spec: [knowledge_graph.md](target/knowledge_graph.md). |
| Decision Fusion | ❌ Not built | — | Now legitimately trainable under paper-aligned split. Spec: [decision_fusion.md](target/decision_fusion.md). |
| Explainability / Final Alert | ❌ Not built | — | + explanation-faithfulness measurement (Tier A). Spec: [explainability.md](target/explainability.md). |
| Anomaly pillar (autoencoder) | ❌ Not built | — | Phase 3 — benign-only reconstruction error. |
| Response engine (IPS) | ❌ Not built | — | Phase R (Shaunak solo, last). Temporal-replay containment. |

**Direction:** targeting top-tier publication — see [conference_roadmap.md](target/conference_roadmap.md) for plan v1.2 + the Tier-S/A/B "godly" agenda.

## Remaining Work ("what's left")

Ordered build queue. ✅ done · ▶ next · ⬜ pending.

| # | Item | Status | Notes |
|---|------|--------|-------|
| 0 | Behaviour abstraction rebuild | ✅ | Done 2026-06-18. Validated; thresholds saved. |
| 1 | **Re-ground LTN axioms on behaviours** | 🟡 Implemented; full run in progress | Ax3=LargePkt∧HighEntropy→¬benign, Ax4=BurstTraffic→¬benign. Smoke-tested OK. Awaiting full-run metrics. |
| 2 | Decide `RepeatedConnections` data path | ⬜ | IP/port side table from `preprocess.py`, or keep out of v1 (currently 0). Can be done alongside #1 or deferred. |
| 3 | Knowledge Graph (NetworkX) | ⬜ | Cluster embeddings → graph + decay + emerging-pattern detection. Spec: [knowledge_graph.md](target/knowledge_graph.md). |
| 4 | Decision Fusion | ⬜ | CNN + LTN + KG → verdict. Spec: [decision_fusion.md](target/decision_fusion.md). |
| 5 | Explainability / Final Alert | ⬜ | 3 explanations + alert. Spec: [explainability.md](target/explainability.md). |
| 6 | Ablation (CNN → +LTN → +KG → full) | ⬜ | Proves each component earns its place. |

Enhancement backlog (not scheduled): [enhancements.md](target/enhancements.md).

## Open Decisions

| Decision | Default chosen | Revisit? |
|----------|----------------|----------|
| KG backend | NetworkX | If scale demands, → Neo4j |
| Fusion mechanism | Fixed weights (Phase 1) → logistic (Phase 2) | After KG exists |
| Input modality | Flow-feature CSVs | PCAP/payload is future work |
| "Hard" vs soft axioms | Soft (SAT loss) + optional inference guard | During LTN rework |
| KG clustering | Static (fit once on train embeddings) | If drift observed |
| Decay "time" | Flow-count (reproducible) | — |
| Compute (CPU vs GPU) | **CPU** (Ryzen 9 9950X3D) | GPU (RTX 5080/Blackwell) deferred — needs WSL2 + CUDA 12.8 + newer TF + Keras 3 migration. Revisit if training volume grows (multi-seed/sweeps/cross-dataset). |

## Last Measured Results

> Fill in after running `eval.py` / `ltn.py`. (Not yet recorded in this doc.)

| Metric | CNN baseline | Hybrid-LTN |
|--------|-------------|------------|
| Binary PR-AUC | _TBD_ | _TBD_ |
| Binary ROC-AUC | _TBD_ | _TBD_ |
| FNR (missed attacks) | _TBD_ | _TBD_ |
| Zero-day recall (avg) | _TBD_ | _TBD_ |

## Session Log Pointer

Dated change history lives in [CHANGELOG.md](CHANGELOG.md). Bugs/risks live in [KNOWN_ISSUES.md](KNOWN_ISSUES.md).

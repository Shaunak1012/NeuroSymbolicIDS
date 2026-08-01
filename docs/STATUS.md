# Project Status (Living Document)

> **Update this file at the end of every working session.** It is the single source of truth for "where are we right now." Last updated: **2026-08-02**.

## ▶ RESUME HERE (next session)

**2026-08-02 session: C2 resolved, Phase 3 RUN — and it reframed the architecture.**

1. **C2 closed.** `cnn_paper` is now n=3 (seeds 42/43/44, log-odds) — mean 0.6399, range
   0.6353–0.6446, and **the CNN's entire range sits inside the LTN control's range** (0.6029–0.6505,
   also n=3). "The neural baseline wins" is **not supportable at this n** without a significance
   test (paired bootstrap / Wilcoxon — flagged, not yet run). Also fixed a real bug found en route:
   `rescore_logits.py` stamped every multi-seed rescore with the wrong seed.
2. **🧪 Phase 3 (benign-only autoencoder) RUN — see "PHASE 3 RESULTS" below.** The headline is not
   the macro (0.1000, far below the CNN). It is the **shape** of the result: the AE catches
   Heartbleed at **1.0000 recall** and Infiltration at **0.8611**, gets the 2nd-best Bot number ever
   measured (**3.6×**), and scores **exactly 0.0000 recall on every web attack.**
3. **I then proposed a "modality analogue" explanation for that split — and tested it the same day
   with `scripts/modality_analysis.py`. It was largely FALSIFIED.** Predictions were written into
   the script before running. The named mechanism (Web attacks transfer because they resemble
   FTP/SSH-Patator) is wrong — their nearest known attack is **DoS Hulk**, not a Patator class. And
   **Bot turns out to sit *closer* to benign (7.28) than the web attacks do (8.84)**, so "Bot is a
   structural outlier the AE catches" is backwards. Worse, my "categorical split" came from reading
   **recall@1%FPR instead of lift**: on lift the AE is comparably weak across *all* powered families
   (Bot 3.6×, Web BF 4.4×, XSS 5.3×). **See the red box in "PHASE 3 RESULTS" below for the full
   correction.**
4. **Then multi-seeded the AE (n=3) — and the complementarity came back ESTABLISHED.** CNN vs AE
   ranges **do not overlap on any family**: AE wins Bot **2.9×** (0.1314 vs 0.0446), CNN wins
   Web BF **8.8×** and XSS **17.4×**. That is a **double dissociation** — the first cleanly
   multi-seeded comparative result in the project, and a stronger claim than "one method is better."
   **The pattern is real; only the explanation was wrong.**

**Where this leaves the project:** a robust, reproducible functional specialisation between (A) and
(B) methods, with **no established mechanism** — the modality account was falsified, and the
per-flow "router" idea rested on it, so that is no longer motivated as-is. Open questions, in order
of value: **(a) why is the CNN specifically so bad on Bot** (the oracle result — 0.0314 → 0.9764
with ~1,000 labels — proves the information *is* in the features, so this is a transfer failure with
no explanation); **(b)** whether the double dissociation can be exploited at all given the fusion
wall; **(c)** whether Mahalanobis (n=1, Bot 0.1467) behaves like the AE under multi-seeding, which
would strengthen "(B)-family" from two data points to a genuine family claim.

**2026-07-29 session: git housekeeping + live ops dashboard (tooling, not research).** No new Phase-2 findings — this session closed out process debt and built dev tooling. Summary (full detail in [CHANGELOG.md](CHANGELOG.md)):
- Codified session-discipline learnings into `CLAUDE.md` as non-negotiables (model-selection-per-step recommendation that must not lapse, "state phase back" onboarding step, provisional-claim discipline, retract-in-place documentation, heartbeat-monitor rule for long background jobs) — PRs #14–#17.
- Built `scripts/dashboard_server.py`, a localhost-only live ops console (CPU/RAM, git state, running training processes, log tail, `runs.jsonl` history) — PR #18. "Open preview" now means this, not the static published-Artifact snapshot; see [DASHBOARD.md](DASHBOARD.md).
- **Phase 2 (symbolic/LTN) is unchanged and concluded for now** — see the multi-seed retraction and ratio-mode-fix sections below, both still current. **Next research action is the Knowledge Graph** (Remaining Work #3 below), not further LTN axiom work; every axiom variant tried costs macro PR-AUC with no confirmed zero-day benefit.

> ⚠️ **Phase-number correction (2026-07-29).** This line previously read *"Phase 3 — Knowledge
> Graph."* That was a **numbering collision**: the canonical scheme
> ([conference_roadmap.md §1b](target/conference_roadmap.md)) has **Phase 3 = anomaly pillar
> (benign-only autoencoder)** and **Phase 4 = Knowledge Graph** — which is also what this document's
> own Component Status table and a comment in `cnn_auxhead_paper.py` already said. The KG is
> **Phase 4**.
>
> **This was not cosmetic: it was about to skip Phase 3 entirely.** The autoencoder is ~1 hour of
> work and is ranked Tier-1 "⭐ highest leverage" in [enhancements.md](target/enhancements.md)
> specifically because it closes the "why not just an autoencoder?" reviewer objection. **Decide it
> before starting the KG** — see [Open Decisions](#open-decisions).

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
on any given seed.

**✅ ω=1.0 collapse mechanism DIAGNOSED (2026-07-27), free — read existing logs, no new
training.** Decoded the per-epoch trajectories for all 3 ω=1.0 seeds (mixed
PowerShell/Python encoding in the log files; extract via raw byte offsets + UTF-16LE
decode if repeating this):

| Seed | best epoch | best val_loss | **best val_acc** | outcome |
|---|---|---|---|---|
| 42 | @3 | 0.0361 | **99.64%** | worked (macro 0.5316) |
| 43 | @2 | 0.0349 | 92.80% | collapsed (macro 0.0520) |
| 44 | @1 | 0.0323 | 96.19% | collapsed (macro 0.0366) |

**In both collapsed seeds, the model's best epoch is 1–2 — it essentially never improves
beyond its random-init starting point**, and best-by-val-loss early stopping (chosen to
mirror the CNN's `model.fit` for a fair comparison) locks that in within ~10 epochs. The
working seed kept genuinely improving through epoch 3 and reached near-perfect known-class
validation accuracy before stopping. SAT values themselves look similar across all three
runs (~0.17–0.26) — this is *not* the same visible catastrophe as ω=2.0.

**Mechanism:** `LTN_OMEGA_MODE=fixed` means the SAT term's weight doesn't adapt to how
large CE actually is (unlike "ratio" mode). Early in training, whether CE or SAT
dominates the gradient in that window depends on random initialization. If SAT happens
to dominate during the first couple of epochs, the model gets pulled toward satisfying
axioms at the expense of ever learning to classify — and once that happens, early
stopping locks it in before it can recover. **ω=1.0 sits right on the edge of this
cliff — which side a given run lands on is essentially a coin flip on seed, not a stable
operating point.** ω=0.5 has enough margin to avoid it (0/3 seeds); ω=2.0 has none (the
single-seed sweep's 100%-reproducible collapse makes sense as the same dynamic with zero
margin, not a different failure mode).

**✅ FIX CONFIRMED (2026-07-27).** Re-ran the exact same 3 seeds (42, 43, 44) at
ω=1.0 with `LTN_OMEGA_MODE=ratio` instead of `fixed` — the two seeds that collapsed
under fixed mode (43, 44) are the direct test.

| Seed | macro (log-odds) | Bot lift | fixed-mode outcome |
|---|---|---|---|
| 42 | 0.6051 | 3.2x | worked either way (0.5316) |
| 43 | 0.5796 | 0.9x | **was 0.0520 catastrophic** |
| 44 | 0.5914 | 1.3x | **was 0.0366 catastrophic** |
| **mean** | **0.5920** | 1.8x | (fixed-mode mean: 0.2067) |

**Zero collapses across all 3 seeds — the fix works exactly as diagnosed.** Tight macro
range (0.58–0.61), both previously-catastrophic seeds now land comfortably in the working
range. This is also, incidentally, **the best Ax6 configuration found all session on
macro** (mean 0.5920, beating fixed ω=0.5's mean of 0.5090) — though still below the
clean no-axiom control's mean (0.6194; ratio ω=1.0's own range 0.58–0.61 doesn't overlap
it either, so the macro cost is real, just smaller and now free of catastrophic risk).

**Does not resolve the earlier retraction.** Bot lift stays noisy (0.9–3.2x, mean 1.8x)
and does not clearly exceed the control's own mean (2.07x) — consistent with the
"multi-seed results" retraction above. **The fix solves the stability problem
(ω=1.0 is now a genuinely safe operating point), not the "does Ax6 reliably help Bot"
question — that remains unresolved/likely negative.** If loss-level injection is pursued
further, `ratio` mode is now the clearly preferred choice over `fixed` for any ω, since
it removes a real failure mode at essentially no measured cost.

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

## 🧭 THESIS REFRAMING (2026-07-29) — the Phase-2 nulls share one structural cause

> **This is a reinterpretation of existing measurements, not a new experiment.** No new runs were
> made. Every number cited below was already in this document; what is new is the account of *why*
> they all point the same way. Recorded as analysis — the discriminating experiment (Phase 3) has
> **not** been run.

**The question that prompted it:** if validation contains no zero-day flows by construction, is the
whole training premise flawed — the model can never know what a zero-day looks like?

**Answer: the protocol is sound; the *method family* is misallocated.**

### What is NOT flawed

The absence of zero-day from train/val **is the definition of the problem**, not a defect in it. Put
Bot in validation and it is no longer zero-day — it is a held-out known class, and the resulting
number is meaningless. Every open-set recognition protocol has this property. The CNN's chance-level
Bot recall is *correct and intended* — the honest baseline. **Do not "fix" this by changing the split.**

### What IS flawed — and it is one thing, not five

The buried assumption is that **a mechanism which must be *fitted on data* can transfer to classes
absent from that data.** It cannot. That assumption underlies every Phase-2 intervention:

| Intervention | Result | Fitted on data lacking zero-day? |
|---|---|---|
| LTN axioms, loss-level (Ax3–Ax6) | costs macro, all variants, n=3 | yes |
| Aux behaviour head, representation-level | 0.5744 vs 0.6446 | yes |
| Logistic fusion, inference-level | `[2.35, 0.02]`, no change | yes |
| *(proposed)* KG `s_kg` → Decision Fusion | not built | yes — **same wall** |

**These were not five independent tuning failures. They are one structural fact encountered five
times.** That is the Phase-2 finding, now derived rather than merely observed.

### The distinction that rescues the project

- **(A) Learn what attacks look like, then match.** Requires attack examples. *Cannot* reach a novel
  class, by construction. → CNN, LTN axioms, aux head, fitted fusion.
- **(B) Learn what *normal* looks like, flag deviation.** Requires only benign/known data. Reaches
  novel classes *by construction*. → Mahalanobis, MSP, IsolationForest, **autoencoder**.

**The project has been investing in (A) on a problem that is structurally (B). The existing evidence
already says so** — on Bot, the family that matters:

| Method | Family | Bot lift |
|---|---|---:|
| **Mahalanobis** (distance from known-class Gaussians) | **B** | ~~4.3×~~ → **3.0× mean, n=3** (see retraction below) |
| XGBoost | A | 1.8× |
| CNN (`cnn_paper`) | A | 1.7× |
| **IsolationForest** — *never sees a single attack* | **B** | 1.7× |
| every LTN axiom variant | A | ~1–2×, seed-noisy |

The best Bot channel measured is a (B) method. IsolationForest — unsupervised, macro 0.063, dreadful
overall — **ties the CNN on Bot despite 884K labelled training flows.** That observation has been in
this document since 2026-07-27 under "supervision buys nothing on the family that matters"; its
significance was not drawn out until now.

### Why this does not mean Bot is undetectable

The skyline oracle settles it: revealing ~1,000 labelled Bot flows lifts Bot PR-AUC **0.0314 →
0.9764**. The information is fully present in the 68 features. This was never an information-theoretic
limit — it is a **transfer** limit specific to fitted, closed-set methods. (B) methods do not have it.

### Consequences

1. **🔴 The Phase-3 autoencoder is promoted from "answer a reviewer objection" to a load-bearing
   experiment.** It is a pure (B) method — the one family with demonstrated traction on Bot — costs
   ~1h, and was nearly deleted by a phase-number collision. It is now the **discriminating test of
   the reframed thesis**, and should very likely run before the KG.
2. **The KG's value proposition needs re-examination in this light.** As specified it feeds a fitted
   fusion stage (an (A)-shaped consumer). Its *clustering/distance* aspect is (B)-shaped and may be
   the part worth keeping — consistent with the Phase-4 readiness review below.
3. **LOCO / fusion-repair work drops down the priority list** — it is an attempt to repair (A). See
   the refutation in [KNOWN_ISSUES.md](KNOWN_ISSUES.md): BeaconLike fires on **97.6% of PortScan and
   0.0% of every other known attack**, so a leave-one-class-out rotation is predictably null for it.

### Proposed thesis statement (not yet adopted — for discussion)

> *Closed-set supervised learning cannot transfer to novel classes regardless of where symbolic
> knowledge is injected — loss-level, representation-level and inference-level all fail, for one
> shared structural reason. Open-set/distance methods reach the same families without labels. We show
> when, why, and by how much.*

This is consistent with [conference_roadmap.md](target/conference_roadmap.md) Tier-S #1
("failure-anatomy study as science") — it sharpens that plan rather than replacing it.

~~**⚠️ Status of this reframing: argued from existing evidence, NOT yet tested.** The autoencoder is
the experiment that could falsify it — if a benign-only AE also lands at chance on Bot, the (A)/(B)
split is not the right account and this section should be retracted in place.~~

> ✅ **TESTED 2026-08-02 (Phase 3). The stated falsification condition was NOT met — the reframing
> survives on Bot, but is TOO STRONG as written and is refined below.**
>
> The benign-only autoencoder scored **Bot PR-AUC 0.1217 (3.6× chance)** — *not* chance, and the
> second-best Bot result ever measured here, behind only Mahalanobis (4.3×). Both top-2 Bot channels
> are (B)-family. That part of the account holds.
>
> **But the AE's macro is 0.1000 vs the CNN's 0.6399 — it collapses on Web attacks** (Web BF 0.1168,
> XSS 0.0615, both at **0.0000 recall** @1% FPR, vs the CNN's 0.9194/0.9554). So "the project is
> investing in (A) on a structurally (B) problem" is **not right as a blanket claim.** Neither family
> dominates; they are **complementary, and which one wins is family-dependent.**
>
> **See "🧪 PHASE 3 RESULTS" below for the refined account** — the governing variable is not (A) vs (B)
> but **whether the unseen class shares a behavioural modality with some known class.**

## 🧪 PHASE 3 RESULTS (2026-08-02) — benign-only autoencoder. ✅ BUILT & RUN.

`scripts/autoencoder_paper.py`. Dense 68→48→32→16→32→48→68, trained **and model-selected using zero
attack labels** (benign-only train + benign-only val), scored by per-row reconstruction MSE.
Converged cleanly (50 epochs, val_loss 0.0039, exit 0). **n=1 (seed 42) — provisional, not
multi-seeded.** Given C2's finding that seed variance is large enough to swallow a 0.02 macro gap,
**do not treat any small difference below as established** without repeat seeds.

| channel | family | macro | Bot | Bot lift | Web BF | XSS |
|---|---|---:|---:|---:|---:|---:|
| CNN `cnn_paper` | A | **0.6446** | 0.0591 | 1.7× | **0.9194** | **0.9554** |
| XGBoost | A | 0.6372 | 0.0608 | 1.8× | 0.9484 | 0.9023 |
| MSP *(B-scoring on an A-model)* | A/B | 0.6123 | 0.0591 | 1.7× | 0.8864 | 0.8913 |
| LTN control w0 | A | 0.6049 | 0.0528 | 1.5× | 0.8749 | 0.8869 |
| Mahalanobis | B | 0.4585 | ~~0.1467~~ | ~~4.3×~~ | 0.6830 | 0.5457 |
| *(Mahalanobis, corrected n=3)* | B | *0.3777* | *0.1030* | *3.0×* | *0.5840* | *0.4462* |
| **Autoencoder (new)** | **B** | **0.1000** | **0.1217** | **3.6×** | 0.1168 | 0.0615 |
| IsolationForest | B | 0.0628 | 0.0571 | 1.7× | 0.0861 | 0.0451 |

**Recall @1% FPR is the decisive column, and it is unusually clean:**

| family | n | AE recall @1% FPR |
|---|---:|---:|
| Heartbleed | 11 | **1.0000** |
| Infiltration | 36 | **0.8611** |
| Bot | 1,956 | 0.0082 |
| Web Attack Brute Force | 1,507 | **0.0000** |
| Web Attack XSS | 652 | **0.0000** |
| Web Attack Sql Injection | 21 | **0.0000** |

(Heartbleed/Infiltration/SQLi are underpowered — direction is informative, magnitudes are not.)

### 🔬 TRAIN-vs-SCORE DECOMPOSITION (n=3 each, 2026-08-02) — and a retraction of "Mahalanobis 4.3×"

> Recomputed MSP and Mahalanobis from **all three CNN seeds** (free — both are post-hoc functions of
> a trained CNN, no retraining). Seed-42 outputs reproduced **byte-identically**, confirming both are
> deterministic. This decomposes the dissociation: is it driven by what a model is **trained on**, or
> by how its score is **computed**?

| channel | train | score | macro | Bot (mean [range]) | lift | Web BF | XSS |
|---|---|---|---:|---|---:|---:|---:|
| CNN softmax | A | A | **0.6399** | 0.0446 [0.024, 0.059] | 1.3× | **0.9226** | **0.9524** |
| MSP | A | **B** | 0.5884 | 0.0448 [0.024, 0.059] | 1.3× | 0.8719 | 0.8485 |
| Mahalanobis | A | **B** | 0.3777 | 0.1030 [0.041, **0.147**] | 3.0× | 0.5840 | 0.4462 |
| Autoencoder | **B** | **B** | 0.0970 | **0.1314** [0.108, 0.165] | **3.8×** | 0.1048 | 0.0547 |

**Finding 1 — changing the scoring function alone buys nothing.** MSP is (B)-style novelty scoring on
the CNN's own softmax, and it lands at **Bot 0.0448 vs the CNN's 0.0446 — indistinguishable.** So the
Bot failure is *not* "the CNN has the signal but the argmax throws it away."

**Finding 2 — there is a monotonic trade-off frontier, not a binary split.** Moving A/A → A/B → A/B →
B/B, Bot rises (0.0446 → 0.0448 → 0.1030 → 0.1314) while Web BF (0.9226 → 0.8719 → 0.5840 → 0.1048)
and XSS (0.9524 → 0.8485 → 0.4462 → 0.0547) fall — **monotonically, on all three families.** No
channel sits at both ends. The dissociation is a *frontier*, and it is governed mainly by **what the
model is trained on**, with the representation/decision rule modulating position along it.

**🔴 Finding 3 — RETRACTED: "Mahalanobis gets 4.3× on Bot, the best Bot channel."** That figure is
**seed 42 only, and it is the best of three seeds:**

| seed | Mahalanobis Bot PR-AUC | lift |
|---|---:|---:|
| 42 | 0.1467 | **4.3×** ← the number quoted throughout the docs |
| 43 | 0.1210 | 3.5× |
| 44 | 0.0413 | **1.2× — essentially chance** |
| **mean** | **0.1030** | **3.0×** |

Best-to-worst seed spread is **3.6×**. This number has been load-bearing — cited in the thesis
reframing, README, and CLAUDE.md as the headline evidence that (B)-family methods work on Bot.
**It should now be quoted as 3.0× mean (range 1.2–4.3×, n=3), not 4.3×.** Same single-seed trap as
the Ax6 retraction and C2; third occurrence in this project.

**Finding 4 — the autoencoder is the better *and far more stable* (B) channel.**
AE Bot 3.8× [3.2–4.8], spread **1.5×** · Mahalanobis 3.0× [1.2–4.3], spread **3.6×**.
(Their ranges do overlap, so "AE > Mahalanobis" is not established — but "AE is more reliable" is.)

**⚠️ Finding 5 — the CNN's classification is seed-stable while its embedding's open-set geometry is
NOT.** Across the *same three seeds*, CNN macro barely moves (0.6353–0.6446, spread 0.009) while
Mahalanobis-on-its-embedding swings **3.6×** on Bot. Equally good classifiers produce embeddings of
wildly differing usefulness for novelty detection.
**This is a direct warning for Phase 4:** the KG is specified to cluster these embeddings, and the
Phase-4 pre-check's "Bot forms a ~90%-pure cluster, stable across 2 seeds" measured **clustering
stability on a fixed (seed-42) embedding** — *not* stability of the embedding across CNN seeds.
Those are different claims, and this result suggests the second may not hold. **Re-run that
pre-check across CNN seeds before building on it.**

### ✅ AE MULTI-SEEDED (n=3, 2026-08-02) — the complementarity is now ESTABLISHED as a double dissociation

> Ran AE seeds 43 and 44 (`AE_SEED=43/44`, seed-42 artifacts untouched). **This is the first
> cleanly-established, multi-seeded comparative result in the project** — every prior head-to-head was
> either single-seed or had overlapping ranges (cf. C2, where CNN-vs-LTN-control *did* overlap and so
> established nothing).

**CNN (A) vs Autoencoder (B), n=3 each, per family — ranges do NOT overlap on any of them:**

| family | CNN (A) mean [range] | AE (B) mean [range] | winner | ratio |
|---|---|---|---|---|
| **Bot** | 0.0446 [0.0241, 0.0591] · 1.3× | **0.1314** [0.1078, 0.1647] · 3.8× | **AE (B)** | **2.9×** |
| Web Attack Brute Force | **0.9226** [0.9194, 0.9288] · 34.7× | 0.1048 [0.0928, 0.1168] · 3.9× | **CNN (A)** | **8.8×** |
| Web Attack XSS | **0.9524** [0.9485, 0.9554] · 81.4× | 0.0547 [0.0468, 0.0615] · 4.7× | **CNN (A)** | **17.4×** |
| macro | **0.6399** [0.6353, 0.6446] | 0.0970 [0.0894, 0.1014] | **CNN (A)** | 6.6× |

AE underpowered families (n=11/36 — direction only): Infiltration **121.8× mean lift**,
Heartbleed **125.3× mean lift**, both far above anything the CNN achieves on them (1.4×, 0.5×).

**This is a double dissociation, and that is a stronger claim than "one method is better."** Each
method wins *decisively* on families where the other fails, with seed ranges that do not touch. It
rules out the boring explanations — not noise (n=3, no overlap), not "the AE is simply weaker"
(it beats the CNN 2.9× on Bot), not "the CNN is simply better" (it loses 2.9× on Bot while winning
8.8–17.4× on web attacks). **The (A)/(B) complementarity is real.**

**What remains unexplained is WHY** — the modality-analogue mechanism proposed for it was tested and
falsified the same day (red box immediately below). So the current honest position is: *a robust,
reproducible functional specialisation with no established mechanism.* That is a legitimate and
publishable state, and notably it is **exactly the kind of result the fusion wall makes hard to
exploit** — the two channels provably cover different families, but no fitted combiner can learn to
route between them (`fusion_beaconlike.py` → `[2.35, 0.02]`).

⚠️ Both methods remain **weak in absolute terms on Bot** (0.13 and 0.045, chance 0.034). "AE wins on
Bot" means 3.8× chance vs 1.3× chance — a robust *relative* difference, not a solved problem.

### 🔴 THE MECHANISM PROPOSED FOR THE ABOVE WAS TESTED AND LARGELY FALSIFIED — read this box too

> **Tested 2026-08-02 by `scripts/modality_analysis.py`, with all four predictions written into the
> script before it was run. Result: the specific mechanism is wrong and the "categorical split"
> framing over-read a threshold statistic.** Kept below unedited as the record; corrections here.
>
> **① The named mechanism is FALSIFIED.** I claimed Web Brute Force transfers because it resembles
> **FTP/SSH-Patator** (shared "repeated authentication attempts" modality). It does not. In raw
> feature space the nearest known attack to Web BF is **DoS Hulk (80%)** and to XSS **DoS Hulk (96%)**
> — not a Patator class. DoS Hulk is an HTTP flood, so any shared modality is *"HTTP traffic to a web
> server on port 80,"* **not** brute-force authentication. The story was plausible and wrong.
>
> **② "Bot is structurally anomalous, web attacks are structurally normal" is BACKWARDS.**
> Median Mahalanobis distance from the benign manifold in raw space:
> **Bot 7.28** · Web BF 8.86 · XSS 8.84 · BENIGN(reference) 6.10 · Infiltration 23.25 · Heartbleed 34.25.
> **Bot sits closer to benign than the web attacks do.** So "the AE catches Bot because Bot is a
> structural outlier" cannot be the mechanism — Bot is not an outlier.
>
> **③ The "categorical split" was an artifact of reading recall@1%FPR instead of lift.** On lift, the
> AE is **comparably weak on all three powered families — Bot 3.6×, Web BF 4.4×, XSS 5.3×** — and web
> attacks are actually *higher* than Bot. The dramatic-looking "0.0000 recall on web attacks vs Bot"
> compares two numbers that are both effectively zero (Bot's recall was 0.0082 = 16 of 1,956 flows).
> **There is no categorical split in the AE's behaviour across powered families.**
> The AE's genuinely striking numbers are on **Heartbleed (103×) and Infiltration (145×)** — which are
> exactly the underpowered families (n=11, n=36) that `metrics.py` excludes from the macro on purpose.
>
> **④ The one prediction that held, once measured correctly: the AE *is* a raw-space
> distance-from-benign detector.** `corr(d_benign_raw, AE reconstruction error) = +0.732` across
> zero-day flows. (My first pass measured this in *embedding* space and got +0.069 — a design error
> on my part, since the AE reconstructs raw features; the geometrically matched test confirms the
> mechanism.)
>
> **⑤ The strongest-looking evidence for the account was circular and is discarded.**
> `corr(margin, CNN−AE advantage)` = **+0.933 in CNN embedding space** but **−0.388 in raw space**
> — opposite sign. The embedding-space figure is near-tautological: `margin` there correlates
> **+0.863** with the CNN's own attack log-odds, i.e. it largely restates the CNN's decision rather
> than predicting it. **In the unbiased space the account is not supported.**
>
> **What actually survives:** the AE is a legitimately distinct channel (raw distance-from-benign),
> it is the best Bot channel after Mahalanobis (3.6× vs 4.3×) though both are weak in absolute terms,
> and it is excellent on structurally extreme rare classes. **Why the AE beats the CNN on Bot is not
> "the AE is good at Bot" — it is that the CNN is unusually bad at Bot (1.7×).** Two weak methods.
>
> **Net:** the (A)/(B) complementarity observation stands as an empirical pattern; the *modality
> analogue* explanation for it does **not** currently have support, and should not be written into
> any paper draft as a mechanism. Full numbers: `outputs/metadata/modality_analysis.json`.

### ~~The refined account — modality analogue, not (A) vs (B)~~ (superseded by the box above)

The autoencoder catches **Heartbleed and Infiltration almost perfectly** and misses **every web
attack entirely**. That is not a performance gradient, it is a categorical split, and it has a
mechanical explanation:

- **Web attacks are structurally normal.** They are HTTP requests to port 80. In the 68 flow
  features they look like ordinary web browsing — what makes them malicious is *payload content*,
  which this feature set does not contain. A benign-trained autoencoder reconstructs them perfectly,
  so reconstruction error carries no signal. **0.0000 recall is the honest, expected result.**
- **The CNN nonetheless scores 0.92–0.96 on them** — despite never training on them — because
  **Web Brute Force resembles FTP-Patator and SSH-Patator, which ARE known training classes.**
  Same behavioural modality (repeated authentication attempts). The CNN is not solving zero-day
  detection here; it is doing **within-modality transfer** from a known class.
- **Bot has no such analogue.** Independently established: `BeaconLike` (destination port ∉
  well-known set) fires on **97.6% of PortScan and 0.0% of every other known attack** — i.e. no
  known class beacons. With nothing to transfer from, every (A) method sits at 1.5–1.8×, and the
  distance/reconstruction methods win (Mahalanobis 4.3×, AE 3.6×).

**So the governing variable is not the method family. It is whether the unseen class shares a
behavioural modality with some known class:**

| | shares modality with a known class | no known-class analogue |
|---|---|---|
| **examples** | Web BF/XSS (≈ Patator brute-force) | Bot, Infiltration, Heartbleed |
| **(A) supervised/closed-set** | ✅ **wins** (0.92–0.96) | ❌ chance (1.5–1.8×) |
| **(B) distance/reconstruction** | ❌ fails (0.06–0.12) | ✅ **wins** (3.6–4.3×) |

This **supersedes the blanket "(B) is the right family" claim** in the reframing above, explains
every Phase-2 null, and is *predictive* rather than descriptive — it says which method to use when.

### Why this makes the fusion wall the central problem, not a side issue

The two families are **complementary, not competing** — each covers exactly what the other misses.
A correct system routes per-flow by modality. But **the router cannot be fitted**, for precisely the
reason documented in "THE FUSION WALL" below: any fitted combiner is calibrated on validation data
that contains no zero-day flows, so it can never learn "trust the distance channel when this flow
has no known-class analogue." Measured, not hypothesised: `fusion_beaconlike.py` → `[2.35, 0.02]`.

**This also gives the Knowledge Graph its first genuinely well-motivated job.** "Is this flow in a
region of embedding space with no known-class analogue?" is exactly a **clustering / density
question answerable without labels** — and the Phase-4 pre-check already found the structure exists
(Bot forms a ~90%-pure cluster at k≥200, stable across seeds). That is a *routing* signal, not a
detection signal, and routing is what this architecture actually needs.

**Status: promising and mechanically coherent, but n=1 and the modality account is an
interpretation, not a measured quantity.** The concrete next test is to **measure** modality
similarity between each zero-day family and the known classes (e.g. embedding-space distance to
nearest known-class centroid) and check it predicts which family wins. That would convert the story
from a plausible narrative into a falsifiable law.

## 🟡 EARLIER-PHASE AUDIT (2026-07-29) — 5 open concerns; C2 RESOLVED 2026-08-02, C1/C3/C4/C5 still open

> **C2 is done** (2 CNN seeds run + rescored, see below) — resolved to "no clean winner at n=3,
> needs a significance test," not to "CNN confirmed." **C1, C3, C4, C5 remain findings-only,
> awaiting go-ahead** — nothing on those four has been actioned.
> Retrospective audit of Phases 0–2 opened 2026-07-29. Ordered by severity.

### C1 — 17% of test rows are exact duplicates of training rows

CIC-IDS2017 is duplicate-heavy (`preprocess.py` deliberately keeps duplicates) and the paper split is
**stratified random**, so identical feature vectors land on both sides. Measured by hashing every row:

| Class | test rows that are exact copies of a train row |
|---|---:|
| PortScan | **58.3%** |
| SSH-Patator | **48.6%** |
| FTP-Patator | 29.6% |
| DoS Hulk | 25.3% |
| BENIGN | 6.9% |
| **all 6 zero-day classes** | **0.0%** |

Train is 13.5% internally duplicated, test 7.0%; 11,848 distinct vectors appear in both.

**✅ The headline zero-day metric is SAFE** — zero-day classes are test-only by construction, so they
cannot overlap train. **🔴 What is contaminated is the ~0.98 "overall binary PR-AUC"**: PortScan at
58% overlap is substantially a lookup, not detection. Known in the literature (Engelen et al. 2021).

**Proposed fix (not implemented):** do **not** de-duplicate — that changes the protocol and breaks
comparability with the base paper. Instead **report both**: overall PR-AUC as-is plus a
"unique-flows-only" variant, and state the duplicate rate explicitly. One evaluation pass, no
retraining. Converts a reviewer vulnerability into a rigor point.

### C2 — ✅ RESOLVED 2026-08-02 — the baseline is now n=3, matching the LTN control

> **Findings only when opened this morning; ran the 2 seeds and closed it out same day.** Both new
> seeds trained clean (exit code 0, no crashes — see the false "process died" heartbeat note in
> KNOWN_ISSUES, which was a monitoring artifact, not a training failure). Multi-seed support was
> added to `cnn_paper.py` first (`CNN_SEED`/`CNN_TAG` env vars, mirroring `ltn_paper.py`'s existing
> convention) so the run would **never touch the seed-42 reference artifacts** — verified by hash
> before and after: all 9 reference files (model, scaler, encoder, embeddings, history) byte-identical.

**Ran seeds 43 and 44**, then log-odds-rescored both (`rescore_logits.py`) for a clean
apples-to-apples comparison against the seed-42 reference, which is itself a log-odds number.
While doing this, found and fixed the exact bug flagged as C5 below: `rescore_logits.py` stamped
every rescored entry with the config-default seed (42) regardless of which seed's model was
actually being rescored — silently wrong on 8 pre-existing rows, and would have been wrong on these
2 new ones too. Fixed to parse the seed from the tag's `_s<N>` suffix. **Re-running the fix surfaced
that STATUS's already-published LTN-control range (0.6029–0.6505) was itself correct** — it must
have been read by run name rather than the buggy field — but the bug was live and uncaught until now.

**Result — CNN (`cnn_paper`), n=3, log-odds:**

| seed | macro zd PR-AUC |
|---|---:|
| 42 | 0.6446 |
| 43 | 0.6353 |
| 44 | 0.6396 |
| **mean** | **0.6399** |
| **range** | **0.6353 – 0.6446** |

**Compared to the LTN control (`ltn_ctrl_w0`), n=3, log-odds: mean 0.6194, range 0.6029–0.6505.**

**🔴 The CNN's entire 3-seed range sits inside the LTN control's range.** This is stronger evidence
for the original concern than the preliminary single-point check — not one number falling in an
interval, but two full 3-seed distributions overlapping almost completely (CNN's range is a strict
subset of the LTN control's).

**What this does and does not establish:**
- The point-estimate means still favour the CNN (0.6399 vs 0.6194, Δ=0.0205).
- **But at n=3 each, with this much overlap, "the neural baseline wins" is not a supportable claim
  without a proper significance test.** The LTN control's own seed-to-seed spread (0.048) is larger
  than the gap between the two means. This is exactly the class of claim
  [conference_roadmap.md](target/conference_roadmap.md) Tier-S #2 ("statistical honesty as a weapon
  — paired bootstrap / Wilcoxon on per-flow scores") already flags as required before shipping.
- **What DOES survive:** the axiom variants' macro cost relative to the control is far larger than
  this seed noise (Ax6 fixed ω=0.5 mean 0.5091, ratio ω=1.0 mean 0.5920 — both well outside either
  range above), so that finding is unaffected. What is now unsupported is specifically the framing
  "CNN beats every LTN variant including the plain control" — the control-vs-CNN comparison needs a
  real test, not eyeballed means.

**Next step (not yet done): a proper paired significance test** (bootstrap or Wilcoxon on per-flow
scores, matching Tier-S #2) is the correct way to close this, rather than more seeds alone. Not
scheduled — flag for the next research session.

### C3 — The macro metric counts one signal twice

`fam_web_attack_brute_force_pr_auc` and `fam_web_attack_xss_pr_auc` correlate at **r = +0.992**
across 60 runs (same Thursday-morning campaign, same tool, same target). So
`macro = mean(Bot, WebBF, XSS)` is really ⅓ Bot + ⅔ *one* web signal — the weighting is an artifact
of how many web sub-labels CIC-IDS2017 happens to define.

**Hypothesis tested and REFUTED:** predicted this biased the metric against Bot-targeted
interventions (Ax6 helps Bot, hurts web). Regrouping to `mean(Bot, mean(WebBF, XSS))` **preserved
the ordering exactly**:

| config | macro as reported | macro regrouped |
|---|---:|---:|
| cnn_paper (n=1) | 0.6446 | 0.4982 |
| LTN control w0 (n=3) | 0.6194 | 0.4824 |
| Ax6 ratio ω=1.0 (n=3) | 0.5920 | 0.4596 |
| Ax6 fixed ω=0.5 (n=3) | 0.5091 | 0.3977 |

**The macro-cost finding is robust to this** — a genuine strengthening. But absolute values shift by
~0.15, so the *number* is label-granularity-dependent.
**Proposed fix (not implemented):** report regrouped macro as a robustness row.

### C4 — The feature transform was selected on the contaminated metric

`config.yaml` pins `feature_transform: log1p` citing *"signed-log1p beat raw 0.980 vs 0.965 PR-AUC."*
That **0.980 is the overall binary metric** — the one inflated by C1's duplicate leakage, and the one
`metrics.py` explicitly says "can never masquerade as the result." The transform was **never A/B'd on
macro zero-day PR-AUC**, the actual headline.
**Proposed fix (not implemented):** re-run the A/B on the headline metric (2 trainings). log1p may
well still win — but the current justification cites the wrong number.

### C5 — Two metadata defects in `runs.jsonl`

1. `rescore_logits.py` writes `seed: 42` for **every** `_logodds` entry, including the s43/s44 models
   — the seed field is wrong on 8 rows.
2. Several entries are duplicated 3× from repeated rescoring runs (`cnn_paper_logodds` appears 3×).
   Naive aggregation double-counts.

**Proposed fix (not implemented):** propagate the source model's seed; dedupe on write.

---

## 🔑 THE FUSION WALL — LOCO refuted for BeaconLike; deprioritized per the reframing above

**The problem.** A fitted combiner cannot learn to weight a zero-day-specific signal, because the
validation set contains no zero-day flows *by construction*. `fusion_beaconlike.py` returned
coefficients `[2.35, 0.02]` — it learned to ignore the symbolic channel. This blocks the KG's
intended contribution path too (see the Phase-4 readiness section below).

**Leave-One-Class-Out (LOCO) was proposed as a fix, then refuted for `BeaconLike` before any
compute was spent (2026-07-29) — see the full table in
[KNOWN_ISSUES.md](KNOWN_ISSUES.md#high).** BeaconLike fires on **97.6% of PortScan and 0.0% of every
other known attack** (every other known attack targets a well-known port). A rotation is therefore
predictably null: 7 of 8 folds teach the combiner the channel is worthless, and the PortScan fold
teaches it the channel is valuable *for the wrong reason* (scanning, not C2 beaconing). **The
originally-recommended "cheap probe: hold out PortScan first" was the single fold guaranteed to
produce a false positive** — do not run it.

**The deeper result:** no known class in CIC-IDS2017 beacons, so a synthetic zero-day exercising
BeaconLike in a Bot-like way cannot be constructed from this known-class pool. LOCO itself is not
broken — it just needs a **modality-general** channel (Mahalanobis/MSP, which respond to any
structurally novel class), not a class-specific axiom. Revised proposal, still not implemented:
free Mahalanobis-8-of-9-classes probe (no retraining) → if promising, real LOCO on novelty channels,
folds size-matched to the zero-day regime (rare known classes, not PortScan).

**Complementary alternative — conformal / benign-only calibration.** Calibrate each channel as a
p-value against the **benign** distribution only, then combine via Fisher's method (or Simes —
BeaconLike is a function of `Destination Port`, a CNN input feature, so channels are not independent
and Fisher's assumption doesn't hold cleanly). Requires **no attack labels at all**. ~No training cost.

⚠️ **Priority note (per the THESIS REFRAMING above): all LOCO/fusion-repair work targets an
(A)-family method** (learn-what-attacks-look-like). **The evidence favours (B)-family methods**
(learn-what-normal-looks-like) — Mahalanobis 4.3×, IsolationForest 1.7× while never seeing an attack.
**Run the Phase-3 autoencoder before returning to this.**

**Recommended order:** ~~C2~~ **✅ done** (see above) → **Phase 3 autoencoder** (tests the reframing
directly) → re-decide the KG's role → C1 + C3 reporting variants (no training) → C4 → C5 →
Mahalanobis-LOCO probe if the autoencoder result still motivates fusion repair.

## 🟢 PHASE-4 (Knowledge Graph) READINESS — audited 2026-07-29

Full review, with tables and caveats, at the top of
[target/knowledge_graph.md](target/knowledge_graph.md). Summary:

**Green — inputs verified present and aligned:**
`X_{train,val,test}_cnn_paper_emb.npy` (883,796 / 110,475 / 114,658 × 64, all three splits) ·
`meta_{train,val,test}.csv` with IP/port/timestamp, row-aligned · `networkx` 3.2.1 and
`python-louvain` 0.16 installed and importable · test set is 114,658 flows, so the spec's
"1.1M nodes will blow up" risk no longer applies.

**Green — empirical pre-check, better than predicted (n=2 seeds, provisional):**
Clustering `cnn_paper` train embeddings and applying to test, **Bot forms a ~90%-pure cluster at
k≥200, stable across seeds**, capturing ~34% of Bot. This is the family that defeated every Phase-2
intervention, and it *does* have seed-stable geometric structure in the embedding space. Web Attack
Brute Force reaches ~65% purity at 90% recall. Not a detection result — a viability result.

**🔴 Three assumptions in the KG spec no longer hold — decide before coding:**
1. **Scope contradiction.** `knowledge_graph.md` calls the KG the *"primary zero-day signal"*;
   `conference_roadmap.md` Phase 4 says *"corroboration + reasoning paths, not primary detector."*
   The roadmap is canonical and better supported — see #2.
2. **The fusion path for a "primary detector" is already measured to fail.** A non-leaky combiner
   must be fit on validation data, which under this protocol **cannot contain zero-day flows by
   construction**. `fusion_beaconlike.py` ran exactly this and got coefficients `[2.35, 0.02]` —
   the combiner ignored the symbolic channel; macro unchanged (0.6447 vs 0.6446).
   **`s_kg` should be expected to hit the identical wall.** `decision_fusion.md`'s own prescribed
   remedy ("train the fuser on a val split that includes zero-day examples") is **impossible here**
   and is now struck through in that document with the three real options.
3. **"Temporal decay" has no clean time axis.** The paper split is stratified-random across all 5
   days; there is no train→test time arrow. Options: decay over flow-count in timestamp-sorted order
   within test · drop decay for v1 · or run the adaptive story on the temporal split as a secondary
   result. "Adaptive" is in the project title, so option 2 has a write-up cost.

**🔴 The single most important untested quantity:** the spec flags an "emerging pattern" partly by
*"weak or no `associated_with` edges to known AttackType"*. But **25 of 50 clusters were already
>90% benign in training**, and 100% of Bot / Web-BF / Infiltration / Heartbleed test flows landed in
benign-dominated clusters. So that criterion will fire on the zero-day families **and on a large
number of ordinary benign clusters**. **Measure the false-positive rate of "unexplained cluster"
first** — the discriminative work has to come from the growth-rate and behaviour-co-occurrence
criteria, not from "unexplained" alone. Build that measurement before building the graph.

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
| Anomaly pillar (autoencoder) | ✅ **Built & run 2026-08-02** | `scripts/autoencoder_paper.py` | Canonical Phase 3. Benign-only reconstruction error, zero attack labels used. macro 0.1000, **Bot 3.6× (2nd best measured)**, but **0.0000 recall on all web attacks**. Produced the modality-analogue refinement — see "PHASE 3 RESULTS". n=1, not multi-seeded. |
| Response engine (IPS) | ❌ Not built | — | Phase R (Shaunak solo, last). Temporal-replay containment. |

**Direction:** targeting top-tier publication — see [conference_roadmap.md](target/conference_roadmap.md) for plan v1.2 + the Tier-S/A/B "godly" agenda.

## Remaining Work ("what's left")

Ordered build queue. ✅ done · ▶ next · ⬜ pending.

| # | Item | Status | Notes |
|---|------|--------|-------|
| 0 | Behaviour abstraction rebuild | ✅ | Done 2026-06-18. Validated; thresholds saved. |
| 1 | **Re-ground LTN axioms on behaviours** | ✅ Concluded (not "done" in the sense of shipping a win — see multi-seed retraction below) | Ax3–Ax6 all implemented, smoke-tested, multi-seeded. Every variant costs macro PR-AUC vs. the no-axiom control; targeted Ax6 (BeaconLike)'s apparent Bot-lift benefit did not survive multi-seeding. `ratio` omega-mode confirmed as the safe default if this line is revisited. Not pursuing further axiom variants for now. |
| 2 | Decide `RepeatedConnections` data path | ⬜ deprioritized | **Unblocked, not blocked** — `meta_{train,val,test}.csv` now carry IP/port/timestamp aligned row-for-row. No longer motivated as a Bot fix (B2/fusion findings above); may still help Infiltration/lateral-movement. Wiring it is a choice, not a data problem. |
| 2b | **Anomaly pillar — benign-only autoencoder (canonical Phase 3)** | ✅ **DONE 2026-08-02** | Ran. Closes the "why not an autoencoder?" objection with a number, and produced the modality-analogue refinement that reframes the whole architecture. Was nearly skipped by a phase-number collision. **Follow-up (not scheduled): multi-seed it (n=1 today), and measure modality similarity to test the refined account.** |
| 3 | **Knowledge Graph (NetworkX) — canonical Phase 4** | ⬜ **next build** | Cluster embeddings → graph + decay + emerging-pattern detection. Spec: [knowledge_graph.md](target/knowledge_graph.md). ⚠️ **Read the "Phase-4 readiness review" at the top of that spec before starting** — 3 of its original assumptions no longer hold, and there are 2 design decisions to make first. |
| 4 | Decision Fusion — canonical Phase 5 | ⬜ | CNN + LTN + KG → verdict. Spec: [decision_fusion.md](target/decision_fusion.md). |
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
| **Run the Phase-3 autoencoder before the KG?** | ⬜ **UNDECIDED — raised 2026-07-29** | Was never actually decided; it was skipped by a phase-number collision. ~1h. Evidence cuts both ways: IsolationForest is dreadful overall (macro 0.0628) but ties the CNN on Bot (0.0571 vs 0.0591), so an AE's result is genuinely unpredictable. Recommendation: **run it** — cheap, and it closes a named reviewer objection. |
| **Omega mode for any future LTN work** | **`ratio`** (already the code default) | Settled 2026-07-27: `fixed` collapses 2/3 seeds at ω=1.0, deterministically at ω=2.0; `ratio` eliminated the collapse at no measured cost. Do not use `fixed` without a stated reason. |

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

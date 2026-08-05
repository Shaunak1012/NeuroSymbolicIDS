# Project Status (Living Document)

> **Update this file at the end of every working session.** It is the single source of truth for "where are we right now." Last updated: **2026-08-05**.

## ▶ RESUME HERE (next session)

## 📊 BASE-PAPER + LITERATURE METRICS (2026-08-05) — `scripts/paper_metrics.py`

**Until today not one of the base paper's numbers had ever been computed for our models.** The
project headlines macro zero-day PR-AUC because `metrics.py` enforces it; the capstone also has to be
readable next to Bizzarri et al. (Accuracy + F1, five views) and next to the field's 99 %+ claims.
Both metric systems are now produced from the same runs.

### Base paper Table II (50 epochs, Adamax), our column added

| Test set | Hybrid-LTN | 1D CNN | **CNN (ours, n=3)** | LTN ctrl | LTN +Ax6 | LTN repro |
|---|---:|---:|---:|---:|---:|---:|
| Multi-class, 9 known | 81.08 % | 80.99 % | **99.81 %** | 99.87 % | 99.87 % | 99.86 % |
| Binary, 9 known | 99.57 % | 99.42 % | **99.84 %** | 99.89 % | 99.89 % | 99.89 % |
| Multi-class, 15 classes | 67.52 % | 67.45 % | **96.17 %** | 96.22 % | 96.23 % | 96.22 % |
| Binary, 15 classes | 93.03 % | 90.88 % | **97.95 %** | 97.90 % | 97.97 % | 97.97 % |
| **Binary, 6 unknown** | **60.47 %** | **48.34 %** | **47.85 %** | 45.37 % | 47.18 % | 47.24 % |

**Two results, pointing opposite ways:**

1. ✅ **We beat the base paper by 18–29 pp on all four known-class views.** ⚠️ **This is a MODALITY
   advantage, not a method one** — 68 engineered flow features are far more separable than raw
   payload bytes. Do not write it up as an algorithmic win.
2. 🔴 **We reproduce their 1D CNN's zero-day number almost exactly (47.85 % vs 48.34 %) and CANNOT
   reproduce the Hybrid-LTN's +12 pp symbolic gain.** Our closest reproduction of their model
   (`ltn_repro`, plain CE + Ax1/Ax2 label anchors) scores **47.24 %** — no gain over our own CNN.
   **This is the project's central finding stated for the first time on the base paper's own
   metric**, and it is the strongest form of it: not "our variants cost macro PR-AUC" but "*their*
   reported improvement does not appear."

### 🔴 Two defects in the base paper's zero-day metric, both verified arithmetically

**(a) No false-positive term.** View 5 contains **only attack rows** → precision ≡ 1, accuracy *is*
recall, and **`F1 = 2A/(1+A)` exactly** — reproducing every published F1 from its accuracy to
<0.02 pp. So *"accuracy 48→60 %, F1 65→75 %"* is **one result reported twice**, and **a model that
flags everything scores 100 % on both** while running a 100 % false alarm rate. Our own float32
saturation bug did exactly that (2026-07-27) and was caught **only** because our metric has a benign
side.

**(b) A size-weighted mixture** — the defect `metrics.py` was rewritten to remove:

| family | n | our share | their share | our CNN detects |
|---|---:|---:|---:|---:|
| **Bot** | 1,956 | **46.8 %** | 8.0 % | **0.0 %** |
| Web Attack Brute Force | 1,507 | 36.0 % | 36.8 % | 89.9 % |
| Web Attack XSS | 652 | 15.6 % | 10.5 % | 96.9 % |
| **Heartbleed** | 11 | 0.3 % | **42.2 %** | 0.0 % |

Holding the model fixed and changing only the mix moves the headline **48.32 % → 44.38 %**.
**Composition explains ~4 pp — so the missing ~12 pp symbolic gain is NOT explained away by it.**

### The field's suite (overall binary) — comparable to published 99 %+ claims

| channel | accuracy | precision | recall | F1 | FAR | ROC-AUC | PR-AUC |
|---|---:|---:|---:|---:|---:|---:|---:|
| **CNN (ours)** | **97.95 %** | 99.71 % | 96.32 % | **97.98 %** | **0.31 %** | 98.32 % | 99.00 % |
| LTN control | 97.90 % | 99.82 % | 96.13 % | 97.94 % | 0.19 % | 98.15 % | 98.24 % |
| LTN +Ax6 | 97.97 % | 99.82 % | 96.26 % | 98.01 % | 0.19 % | 98.16 % | 98.24 % |

⚠️ **In the literature's range, and NOT a better result than our 0.64 macro zero-day PR-AUC** — an
easier question asked of the same models. **Report both, and say which is which.**

⚠️ **Comparison in FORM, not head-to-head.** Three documented deviations: **modality** (payload bytes
vs flow features) · **zero-day membership differs by a swap** — they hold out **PortScan** and train
on **Infiltration**, we do the reverse (5 of 6 overlap) · **class sizes** (their Heartbleed is 13,486
payload packets; flow data has 11).

## 🔴 ABLATION (2026-08-05) — `scripts/ablation.py`. ONLY THE KG EARNS ITS PLACE.

Remaining Work #6, n=3 paired seeds, parameter-free equal-weight rank fusion (nothing fitted).
Five rungs, because *"+LTN"* is ambiguous: the **control** is the symbolic trainer with axiom weight
zero, **Ax6** is the actual symbolic pillar. Both are run.

| rung | macro | range | Bot | Web BF | XSS | Δ vs CNN | seeds up |
|---|---:|---|---:|---:|---:|---:|---:|
| CNN | 0.6399 | [0.6353, 0.6446] | 0.0446 | 0.9226 | **0.9524** | — | — |
| CNN + LTN-ctrl | 0.6433 | [0.6338, 0.6497] | 0.0594 | 0.9195 | 0.9511 | +0.0035 | 2/3 |
| CNN + LTN-Ax6 | 0.6394 | [0.6319, 0.6498] | 0.0495 | 0.9187 | 0.9501 | **−0.0004** | **1/3** |
| **CNN + KG** | **0.6926** | [0.6626, 0.7328] | **0.2518** | **0.9283** | 0.8976 | **+0.0528** | **3/3** |
| CNN + LTN-Ax6 + KG (**FULL**) | 0.6708 | [0.6394, 0.7114] | 0.2043 | 0.9277 | 0.8806 | +0.0310 | 3/3 |
| CNN + LTN-ctrl + KG | 0.6887 | [0.6559, 0.7133] | 0.2302 | 0.9276 | 0.9085 | +0.0489 | 3/3 |

**Paired bootstrap** (B=2000): CNN+KG vs CNN **+0.0528** [+0.0466, +0.0592] p<0.0001 ·
**FULL vs CNN+KG −0.0218** [−0.0288, −0.0149] **p<0.0001** · CNN+LTN-Ax6 vs CNN −0.0004 **n.s.**

### The conclusion, and it is negative about our own architecture

**Only the KG earns its place.** The symbolic pillar adds nothing alone (−0.0004, n.s., improving on
1 of 3 seeds) and **significantly HURTS when stacked on the KG** (0.6926 → 0.6708, p<0.0001),
diluting the KG's Bot signal from **0.2518 → 0.2043**. Consistent with `fusion_multi.py`'s
independent finding that equal-weight fusion rewards **complementarity, not quantity**.

> ⚠️ **A trap inside our own new result, caught by applying our own rule.** `CNN + LTN-ctrl vs CNN`
> comes back **p<0.0001** — and must **NOT** be reported as an improvement. The gap is **+0.0035 =
> 0.16 SD** of the noise floor, improving on **2 of 3 seeds**. This is exactly C2: *a flow-level
> paired bootstrap cannot rescue a delta below the pipeline's own reproducibility.* It answers
> "would this hold on different traffic", not "would this hold if we retrained". **This is noise.**

✅ **Two independent reproductions validate the implementation** — recomputing macro from raw score
arrays gives **0.6399** (CNN) and **0.6926** (CNN+KG), exactly matching `metrics.py` and
`fusion_kg.py`.

## ✅ PHASE 7.5 TIER 1 COMPLETE (2026-08-05) — `scripts/operational.py`. All 4 predictions confirmed.

**PR-AUC is the wrong target for a response engine**, and Tier 1 measures what is. Four predictions
pre-registered before running; **all four CONFIRMED**.

### 1 — The ensemble is the deployable baseline

| | macro |
|---|---:|
| single-run mean (n=11) | 0.6217 |
| single-run **max** | **0.6446** ← the number usually quoted |
| single-run min | 0.5825 |
| **ENSEMBLE (probability-mean)** | **0.6356** |

Reproduces STATUS's previously-quoted 0.6356 exactly. Beats the mean, **not** the max — as predicted,
because 0.6446 is the top of 11 draws. **The ensemble's argument is not the delta; it is that it is
reproducible.** ⚠️ `cnn_auxhead` was caught contaminating the glob on the first run — it matches
`cnn_*` but is a *different architecture*, and including it would have silently answered "does a
heterogeneous ensemble help?" while being reported as a reproducibility fix.

### 2 — 🔴 Calibration works on known classes and does NOTHING for zero-day

Fitted on **validation** (zero-day-free by construction — asserted in code), measured separately:

| method | ECE all | ECE known-class | ECE zero-day | **zd ÷ known** |
|---|---:|---:|---:|---:|
| uncalibrated | 0.0260 | 0.0084 | 0.0381 | 4.5× |
| Platt | 0.0196 | 0.0006 | 0.0387 | 62× |
| isotonic | **0.0192** | **0.0001** | 0.0387 | **287×** |

**Isotonic reaches ECE 0.0001 on known classes while zero-day ECE does not move at all.** A
calibrator learns a score→outcome mapping, and for a class the model has never seen that mapping does
not hold. **The better the calibration, the wider the gap** — the fusion wall in another guise, and a
direct operational consequence: **`p = 0.9` means 90 % for known attacks and nothing for novel ones.**

🔴 **Isotonic wins ECE but is unusable as an operating point** — a step function with **74 distinct
values** over 114,658 flows, so the 1 %-FPR quantile lands inside a tie block. The first run
thresholded on it and achieved **FPR 0.70 against a 0.01 target.** Platt is monotone and continuous
(59,920 values) and hits 0.0100 exactly. **Calibrate with isotonic for reporting; threshold with
Platt.** `metrics.py` already flags this failure mode for model scores; it applies to calibrators too.

### 3 — 🔴 At any deployable alert budget, you see ONLY known attacks

Precision is **~1.000 at every budget for every channel** — and that is the problem:

| budget | CNN precision | zero-day in alerts | zd recall |
|---:|---:|---:|---:|
| 100 | 1.000 | **0** | 0.0000 |
| 1,000 | 1.000 | **0** | 0.0000 |
| 10,000 | 1.000 | 3 | 0.0007 |
| 25,000 | 1.000 | 1,913 | 0.4573 |

**Depth required before novel attacks surface** (as % of the 114,658 test flows):

| channel | @10 % zd | @25 % zd | @50 % zd |
|---|---:|---:|---:|
| CNN | 13,170 (11 %) | 14,301 (12 %) | 59,355 (**52 %**) |
| CNN ensemble | 29,911 (26 %) | 31,533 (28 %) | 60,043 (52 %) |
| **CNN + KG fusion** | 16,556 (14 %) | 23,899 (21 %) | **36,661 (32 %)** |
| **KG (causal)** | 14,992 (13 %) | 28,701 (25 %) | **33,063 (29 %)** |

**Reaching half the zero-day flows means reviewing a third to a half of all traffic.** The KG and the
fusion **cut that depth by ~20 pp** — the clearest operational statement of what the KG buys, and
more meaningful than any PR-AUC delta. **A 100 %-precise alert stream that contains zero novel
attacks is exactly the failure Phase 7.5 exists to expose, and PR-AUC 0.64 does not show it.**

### 4 — 🔴 Abstention does not rescue zero-day. At all.

Confidence = margin from the decision threshold, `|logit(p) − logit(thr)|`.

| coverage | precision | recall | benign kept | **zd precision** |
|---:|---:|---:|---:|---:|
| 100 % | 0.990 | 0.964 | 55,237 | **0.0350** |
| 95 % | 0.996 | 0.963 | 49,766 | **0.0350** |
| 90 % | 0.996 | 0.963 | 44,035 | **0.0350** |
| 75 % | 0.996 | 0.963 | 26,839 | **0.0350** |

**Zero-day precision does not move (+0.0000) across every non-degenerate coverage.** This was
predicted in advance from the Bot failure analysis: the CNN is **confidently wrong** on Bot (100 %
argmax BENIGN, mean p(BENIGN)=0.9984), and **a confidence-based rule cannot catch
confident-and-wrong.** Coverages ≤50 % are excluded as degenerate (2–125 benign flows retained out of
55,237 — which is why their FPR reads exactly 1.0000).

⚠️ **Two methodological errors were caught and fixed inside this script**, both of which would have
produced publishable-looking nonsense: thresholding on a tie-degenerate isotonic score (FPR 0.70 vs
0.01 target), and defining confidence as `|p − 0.5|` when the operating point is 0.000049 — which
ranks *confidently benign* flows as most confident and collapsed recall to 0.035 for reasons
unrelated to selective prediction. **Both were visible only because the achieved FPR was printed
next to its target.**

### What Tier 1 means for Phase R

**Automated response is safe on what this system fires on** (precision ~0.99 at the 1 %-FPR operating
point, ≥0.95 at every coverage) **and useless for novel attacks at any budget a SOC would run.** The
honest deployment story is: auto-act on known attacks, and treat zero-day as a *depth* problem the KG
improves but does not solve. Tier 2 (determinism, k-fold, SWA) is next.

### 📍 CURRENT — 2026-08-05

**Phases 0–4 COMPLETE. Phase 5 partially entered. Next: Phase 7.5 Tier 1 · the ablation · TF
determinism flags.**

| Phase | State |
|---|---|
| 0–3 (split, CNN, LTN, autoencoder) | ✅ done |
| **4 — Knowledge Graph + explainability** | ✅ **COMPLETE** — `kg.py`, `kg_visualize.py`, `explain.py`; faithfulness measured |
| **5 — Decision Fusion + rigor** | 🟡 **PARTIAL** — ✅ significance · ✅ parameter-free rank fusion · ✅ n=6 on all 7 channels. ❌ calibration · ❌ latency · ❌ the *fitted* fuser (blocked by THE FUSION WALL) |
| 6, 7 | ⬜ not started |
| **7.5 — operational readiness** | 🟡 **Tier 1 ✅ DONE 2026-08-05** (`operational.py`, 4/4 predictions confirmed); Tier 2 in progress. **Gates Phase R** |
| R — response engine | ⬜ not started |

**The three things in flight, in order:** (a) **Phase 7.5 Tier 1** — ship the ensemble, calibration
+ ECE, precision @ alert budget, abstention curve; (b) **the ablation** CNN → +LTN → +KG → full
(Remaining Work #6); (c) **TF determinism flags**, which attack the 3.6 % CV at source.

> 🔴 **Read [THE NOISE FLOOR](#-the-noise-floor--measured-2026-08-03-and-it-retracts-a-headline-result)
> before citing any number below.** SD **0.0222** at fixed seed. C2 is **retracted** on those grounds
> — the CNN and the LTN control are **indistinguishable** at n=6 (+0.0140 against a ~0.0256
> threshold). The double dissociation survives at **3.9–40 SD**.

> ⚠️ **Documentation-debt note (closed 2026-08-05).** The 2026-08-04 session updated this file,
> `CLAUDE.md` and `KNOWN_ISSUES.md` but **never wrote a CHANGELOG entry**, and left `CLAUDE.md`
> asserting Phase 4 had not started — two sessions after it was completed. Eight drift items were
> found and closed on 2026-08-05; see that CHANGELOG entry. The lint's `script-count` check had
> **passed on a wrong count** because its regex `(\d+) scripts` never matched the actual phrasing,
> *"40 Python scripts"*. **A mechanical check that cannot fire is worse than no check** — it buys
> false confidence. Regex widened.

---

**2026-08-03 session: pre-Phase-4 remediation — and it produced three research results, not just fixes.**

The session was scoped as "fix every discrepancy before Phase 4," then extended to "make Phase 4
ready to start without starting it." Both produced research results.

> 🚨 **MOST IMPORTANT SINGLE FINDING OF THE SESSION — read before touching Phase 4.**
> **The Knowledge Graph's specified zero-day mechanism does not work.** "Unexplained cluster"
> (weak/no `associated_with` edges to a known AttackType) scores **lift ≤ 1.00× — at or below
> chance — across 3 representations × 3 thresholds.** It is anti-correlated, not merely weak.
> This kills the KG as a *primary detector* and empirically resolves the spec's scope
> contradiction in the roadmap's favour: **corroboration + explainability only.**
> Also: **cluster raw features, not embeddings** — and note that this document's *own* AE-bottleneck
> recommendation, made earlier the same day, was measured and **rejected** (52.1 pp spread, worst
> of all options). See [PHASE-4 READINESS MEASURED](#-phase-4-readiness-measured-2026-08-03--the-kgs-specified-zero-day-mechanism-does-not-work).

**Read these three boxes next:**

1. 🔬 **"Why does the CNN fail on Bot?" is ANSWERED** — see
   [WHY THE CNN FAILS ON BOT](#-why-the-cnn-fails-on-bot--answered-2026-08-03). All four
   pre-registered predictions resolved. The mechanism is **representational, not
   informational**: 100% of Bot flows are confidently classified as BENIGN, the features that
   separate Bot from benign have **0/8 overlap** with the features the known-class task needs, and
   consequently the CNN's Bot ranking is **noise** (cross-seed rank correlation **−0.090**, vs
   0.68–0.83 for every other family). **This also decides the Phase-4 representation question** —
   see Open Decisions.
2. ✅ **Significance tests are RUN** (`scripts/significance.py`) — C2 is properly closed and the
   double dissociation is now statistically established (p<0.0005 on all three families). **But one
   earlier *retraction* is itself reversed: "CNN beats XGBoost on macro" is n.s. (p=0.80), so the
   original "XGBoost ≈ CNN" claim was right and retracting it was premature.**
3. 🔴 **The (A)/(B) thesis reframing is FALSIFIED IN ITS STRONG FORM.** Putting the classical
   baselines on 3 seeds (a bookkeeping fix) showed **RandomForest — a supervised (A)-family method —
   ties the autoencoder on Bot** (0.1311 vs 0.1314, p=0.88) **while beating it by 0.50 on macro.**
   "(B) methods are needed to reach Bot" does not survive. See
   [the (A)/(B) falsification](#-the-ab-framing-is-falsified-in-its-strong-form-2026-08-03).

---

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

~~**Recall @1% FPR is the decisive column, and it is unusually clean:**~~

> 🔴 **RETRACTED (marked in place 2026-08-03; the substance was already falsified 2026-08-02).**
> Recall @1% FPR is **not** the decisive column and reading it as one is exactly the error that
> manufactured the false "categorical split" — see finding ③ in the red box below. On **lift**, the
> AE is comparably weak across all three powered families (Bot 3.6×, Web BF 4.4×, XSS 5.3×). The
> table below is kept as measured; interpret it as a threshold statistic, not as detection quality.

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
question answerable without labels** — and the Phase-4 pre-check found the structure exists
(Bot forms a ~90%-pure cluster at k≥200). ⚠️ **That structure was later shown to be CNN-seed-dependent
(87.9% / 86.6% / 44.4% across seeds — see "PHASE-4 BLOCKER"), so it is not a dependable foundation
as-is.** The routing idea also rested on the modality mechanism, which was falsified. Both caveats
apply; treat this paragraph as a hypothesis with two known problems, not a plan.

**Status: promising and mechanically coherent, but n=1 and the modality account is an
interpretation, not a measured quantity.** The concrete next test is to **measure** modality
similarity between each zero-day family and the known classes (e.g. embedding-space distance to
nearest known-class centroid) and check it predicts which family wins. That would convert the story
from a plausible narrative into a falsifiable law.

## 🟡 EARLIER-PHASE AUDIT (2026-07-29) — 5 concerns; only C4 remains open

> 📍 **Final disposition (updated 2026-08-05).** **C1 ✅ closed** 2026-08-03 (`comparability.py` runs
> the dedup variant: supervised channels lose 0.0035–0.0049, all six zero-day families measure 0.0 %
> overlap) · **C2 🔴 RETRACTED** 2026-08-03 — it was "resolved in the CNN's favour" at p=0.001 and
> then retracted on controlled grounds, because the +0.0204 gap is **0.9 SD** of the measured noise
> floor · **C3 ✅ closed** 2026-08-03 (`robustness.py`: regrouping shifts values ~0.11–0.15 but
> preserves every ordering) · **C5 ✅ closed** 2026-08-03 (`repair_runs_log.py`) · **C4 ⬜ still
> open** — the feature transform is still justified by the contaminated overall-binary metric.
> The section below is the original audit, kept as written.

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
(learn-what-normal-looks-like) — ~~Mahalanobis 4.3×~~, IsolationForest 1.7× while never seeing an attack.
~~**Run the Phase-3 autoencoder before returning to this.**~~

> 🔴 **Two corrections, marked in place 2026-08-03.**
> ① **"Mahalanobis 4.3×" is RETRACTED** — seed 42 only, best of 3; n=3 mean is **3.0×**
> (range 1.2–4.3×). This sentence was missed when the retraction was applied elsewhere;
> KNOWN_ISSUES's parallel copy *was* corrected on 2026-08-02.
> ② **Phase 3 is DONE** (built, run, multi-seeded 2026-08-02) — this directive pointed at
> completed work. ③ The premise itself is now weaker: **RandomForest, an (A)-family method,
> scores Bot 3.8× (n=3)** — matching the autoencoder. "(B) methods own Bot" does not survive
> as a family-level claim; see "🔴 THE (A)/(B) FRAMING IS FALSIFIED IN ITS STRONG FORM".

~~**Recommended order:** C2 **✅ done** (see above) → **Phase 3 autoencoder** (tests the reframing
directly) → re-decide the KG's role → C1 + C3 reporting variants (no training) → C4 → C5 →
Mahalanobis-LOCO probe if the autoencoder result still motivates fusion repair.~~

> ✅ **Superseded 2026-08-03 — everything up to "re-decide the KG's role" is done.** Current order:
> ~~C2~~ ✅ → ~~Phase 3 AE~~ ✅ → ~~multi-seed AE~~ ✅ → ~~significance test~~ ✅ (run 2026-08-03,
> `scripts/significance.py`) → ~~C5 / runs.jsonl integrity~~ ✅ → ~~baselines on the current
> schema~~ ✅ (n=3; surfaced the RandomForest-Bot result) → **next: decide the KG representation
> (Phase 4)** → C1 + C3 reporting variants (no training) → C4.

## 🔴 PHASE-4 BLOCKER (2026-08-02) — the KG's clustering premise does not survive CNN reseeding

> **The "Bot forms a ~90%-pure cluster, stable across 2 seeds" result below (2026-07-29) was
> measuring the wrong thing, and I flagged it, re-ran it, and it broke.** The original test varied
> only the **clustering** seed on a **fixed seed-42 embedding**. It never varied the CNN seed — i.e.
> it measured k-means stability, not stability of the *representation the KG would be built on*.

**Re-run varying the CNN seed (clustering seed held at 42), `scripts/kg_precheck.py` Part 1:**

| k | family | purity across CNN seeds 42/43/44 | spread |
|---|---|---|---:|
| 200 | **Bot** | **87.9% · 86.6% · 44.4%** | **43.4 pp** |
| 200 | Web Attack Brute Force | 62.4% · 64.9% · 64.8% | 2.5 pp |
| 200 | Web Attack XSS | 28.1% · 29.4% · 27.8% | 1.6 pp |
| 400 | **Bot** | **82.2% · 91.1% · 62.7%** | **28.3 pp** |
| 400 | Web Attack Brute Force | 65.2% · 67.0% · 65.5% | 1.7 pp |
| 400 | Web Attack XSS | 29.4% · 30.1% · 29.5% | 0.7 pp |

For contrast, varying only the **clustering** seed on a fixed embedding (the original test, Part 2)
gives Bot purity 87.9% vs 90.5% at k=200 — **spread 2.6 pp.** So clustering is stable; **the
embedding is not.**

**Three things make this serious rather than merely noisy:**

1. **The instability is specific to Bot.** Web BF and XSS purity are rock-stable across CNN seeds
   (0.7–2.5 pp). So this is not "clustering is generally seed-sensitive" — it is
   **"the CNN's embedding geometry *with respect to Bot* is a seed lottery."**
2. **Two independent measures agree, and agree on which seed is bad.** Seed 44 is worst on *both*
   cluster purity (44.4%) and Mahalanobis Bot PR-AUC (0.0413, 1.2× — chance), while its
   classification is completely unremarkable:

   | seed | CNN macro | CNN Bot | Mahalanobis Bot | KG Bot purity (k=200) |
   |---|---:|---:|---:|---:|
   | 42 | 0.6446 | 0.0591 | 0.1467 | 87.9% |
   | 43 | 0.6353 | 0.0241 | 0.1210 | 86.6% |
   | 44 | 0.6396 | 0.0507 | **0.0413** | **44.4%** |

   **Classification is flat (macro spread 0.009); open-set geometry is not.** A CNN can be equally
   good at its training task and produce an embedding that does or does not isolate Bot.
3. **The KG's value proposition inverts.** It clusters *stably* on web attacks — which the CNN
   already handles at 0.92–0.95, so clustering adds nothing there — and *unstably* on Bot, the one
   family where a memory/novelty mechanism would actually earn its place.

**Implication for Phase 4 as specified:** a KG built on one CNN's embeddings inherits that seed's
lottery ticket. On seed 42 the pre-check looks like a green light; on seed 44 the same procedure
yields a 44%-pure blob. **Do not build on a single embedding.**

**Options (none implemented, none decided):**
- **Ensemble across CNN seeds** — cluster a concatenation/average of several seeds' embeddings, or
  require a cluster to reproduce across seeds before promoting it to a KG node. Most faithful to the
  spec, costs n× embeddings (already have 3).
- **Cluster raw features instead** — no training, so no seed lottery at all. Loses the learned
  representation, but the Phase-3 modality work showed raw-space distance is a real signal
  (`corr = +0.732` with AE error).
- **Cluster the autoencoder's 16-d bottleneck** — benign-only-trained, and the AE proved the most
  *stable* Bot channel (spread 1.5× vs Mahalanobis's 3.6×). Untested for clustering; plausible.
- **Accept and report the variance** — build on one seed but publish the seed-sensitivity as a
  finding rather than hiding it. Cheapest, and honest.

**This does not kill Phase 4** — it kills "clustering CNN embeddings is a solid foundation" as an
unexamined assumption. Decide the representation question before writing `kg.py`.

## 🟢 PHASE-4 (Knowledge Graph) READINESS — audited 2026-07-29 (⚠️ point 4 superseded by the blocker above)

Full review, with tables and caveats, at the top of
[target/knowledge_graph.md](target/knowledge_graph.md). Summary:

**Green — inputs verified present and aligned:**
`X_{train,val,test}_cnn_paper_emb.npy` (883,796 / 110,475 / 114,658 × 64, all three splits) ·
`meta_{train,val,test}.csv` with IP/port/timestamp, row-aligned · `networkx` 3.2.1 and
`python-louvain` 0.16 installed and importable · test set is 114,658 flows, so the spec's
"1.1M nodes will blow up" risk no longer applies.

~~**Green — empirical pre-check, better than predicted (n=2 seeds, provisional):**
Clustering `cnn_paper` train embeddings and applying to test, **Bot forms a ~90%-pure cluster at
k≥200, stable across seeds**, capturing ~34% of Bot. This is the family that defeated every Phase-2
intervention, and it *does* have seed-stable geometric structure in the embedding space. Web Attack
Brute Force reaches ~65% purity at 90% recall. Not a detection result — a viability result.~~

> 🔴 **RETRACTED 2026-08-02 — "stable across seeds" was measuring the wrong variable.** The two seeds
> varied were **clustering** seeds on a **fixed seed-42 embedding**; the CNN seed was never varied.
> Re-running across CNN seeds gives Bot purity **87.9% / 86.6% / 44.4%** at k=200 — a **43.4 pp
> spread**, versus 2.6 pp when only the clustering seed moves. The ~90% figure is seed-42's lottery
> ticket. Web BF/XSS purity *is* stable across CNN seeds (0.7–2.5 pp), so the instability is specific
> to Bot. **See "PHASE-4 BLOCKER" above.**

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

## ✅ C3 CLOSED + a fusion-wall test (2026-08-03) — `scripts/robustness.py`

### C3: the macro conclusions ARE robust to the label-granularity artifact

Web BF and XSS correlate at **r = +0.992** (same Thursday campaign, same tool), so
`macro = mean(Bot, WebBF, XSS)` is really **⅓ Bot + ⅔ one web signal**. The regrouped
alternative `mean(Bot, mean(WebBF, XSS))` weights *phenomena* instead of *labels*:

| channel | macro (reported) | macro regrouped | Δ |
|---|---:|---:|---:|
| **CNN + KG fusion** | **0.6926** | **0.5824** | −0.1102 |
| CNN | 0.6399 | 0.4910 | −0.1489 |
| RandomForest | 0.5995 | 0.4824 | −0.1171 |
| LTN control | 0.6194 | 0.4824 | −0.1371 |
| KG (causal) | 0.2488 | 0.2642 | +0.0154 |
| Autoencoder | 0.0970 | 0.1056 | +0.0086 |

✅ **Meaningful ordering preserved.** Absolute values shift ~0.11–0.15, but every conclusion holds —
fusion > CNN > the rest, KG > AE.

> ⚠️ **A caught false alarm worth recording.** The first version flagged *"ORDERING CHANGES —
> conclusions NOT robust"*. Investigating: LTN control and RandomForest differ by **1.3 × 10⁻⁵**
> under regrouping — an exact tie the sort broke arbitrarily, not a reversal. The script now ignores
> swaps between channels it ties to within 0.005. **An automated verdict that cries wolf is worse
> than no verdict**, because the next reader will discount the real ones.

### The fusion wall: tested constructively, and it holds where it claims to

`fusion_multi.py` showed weak channels dilute strong ones under equal weighting. The obvious fix —
weight by quality — is only legitimate if the weights use **no zero-day information**, so they were
computed from **known-class PR-AUC**. Prediction registered before running: *this will hurt.*

| | macro | Bot |
|---|---:|---:|
| equal weighting | 0.7089 | **0.3125** |
| known-class weighted | 0.7116 | 0.2949 |
| Δ | **+0.0027** | **−0.0176** |

**The wall holds on the family it is about.** Known-class weighting **hurts Bot by 0.0176** — it
down-weights the KG (known-class PR-AUC 0.9099) precisely because the KG's value lies on a family it
was never trained on. The trivial macro gain (+0.0027) comes from the web attacks, which *are* well
served by known-class-skilled channels.

> ⚠️ **A second inverted verdict, also caught.** The script first judged on **macro** alone and
> printed *"PREDICTION REFUTED"* — while Bot had moved exactly as predicted. **Wrong metric, wrong
> conclusion.** The wall is a claim about zero-day-specific channels, so Bot is the diagnostic.
> Fixed in the script, not just the write-up.
>
> ⚠️ **Power caveat:** known-class PR-AUC **saturates** (0.9998–1.0000 for CNN/LTN/RF; spread 0.0900
> overall), so it barely differentiates the supervised channels. This test is **underpowered by
> construction** — do not over-read the macro number in either direction.

## 🟢 PHASE 4 COMPLETE (2026-08-03) — explainability delivered, and it is FAITHFUL

`scripts/explain.py`. All three explanations, Final Alert assembly, and the Tier-A
faithfulness measurement the roadmap asks for and almost nobody in this field runs.

### The neural explanation is measurably faithful, not decorative

ERASER-style deletion metrics, each against a **random-feature control** (without which the numbers
mean nothing), n=1,500 flows, Integrated Gradients with the training mean as baseline:

| top-k | comprehensiveness (IG) | (random control) | **ratio** | sufficiency gap IG / random |
|---|---:|---:|---:|---:|
| 3 | +0.2908 | +0.0141 | **20.67×** | 0.4603 / 0.5153 |
| 5 | +0.3810 | +0.0311 | **12.26×** | 0.4444 / 0.5141 |
| 10 | +0.4536 | +0.1089 | **4.16×** | 0.4421 / 0.5131 |

**Masking the 3 features IG points at drops the attack score 20.7× more than masking 3 random
features.** The attribution is identifying what the model actually uses.

⚠️ **Sufficiency is the weaker half and is reported as such**: IG beats random (0.442–0.460 vs
0.513–0.515) but the absolute gap stays ~0.44, so the top-k *alone* do **not** reproduce the
decision. Honest reading: **the explanation reliably finds features the model depends on
(comprehensiveness), but the decision is distributed across more than 10 features (sufficiency).**

✅ **Correctness check:** IG's completeness axiom holds — `sum(attributions) ≈ f(x) − f(baseline)`,
|error| 0.0001–0.042.

### 🔬 The qualitative result: the three pillars visibly disagree on Bot

The single most informative output of the whole system, and it required all three pillars:

```
flow #114062 — true=Bot [ZERO-DAY] -> verdict=benign (p_attack=0.0021)
  NEURAL : PSH Flag Count=+0.0107, Fwd Packet Length Max=-0.0068  (nothing decisive)
  LOGIC  : Ax6 BeaconLike fires 1.00 -> VIOLATED
  KG     : Cluster:163 burst=15.84x EMERGING | exhibits BeaconLike 0.841
                                             | known: BENIGN 99.9%
```

**The neural pillar says benign. The symbolic pillar says beacon ⇒ attack, VIOLATED. The KG says
this cluster is emerging and beacon-dominated.** Both non-neural pillars dissent from the CNN — on
exactly the family we independently proved the CNN gets wrong (100% classified BENIGN, 0/8 feature
overlap, cross-seed rank ρ = −0.090).

This is the *"agreement vs disagreement is a feature, not a bug"* case the explainability spec
anticipated, and **no single-pillar system can produce it.** It is the clearest argument in the
project for the neuro-symbolic architecture — not that it beats the CNN's macro score, but that it
**tells you when the CNN is wrong and why.**

### What was built vs. deliberately omitted

✅ Neural (Integrated Gradients) · ✅ Logic (per-axiom SAT) · ✅ KG (reasoning path) ·
✅ Final Alert assembly · ✅ Faithfulness measurement.

⚠️ **Only 4 of 6 axioms appear in the logic explanation, deliberately.** Ax1/Ax2 are *label
anchors* — they condition on the ground-truth class, which does not exist at inference. Reporting
them as explanations would be circular. Only the behaviour-grounded Ax3–Ax6 are usable.

⚠️ **IG rather than SHAP**: implemented directly against `tf.GradientTape`, so it carries an exact
correctness check (completeness) and avoids SHAP's brittle Keras-2 Conv1D path.

## 📊 COMPARABILITY + THE LIMITS OF FUSION (2026-08-03)

### We are not behind the literature — we report a harder metric

`scripts/comparability.py`. Published CIC-IDS2017 work reports **99%+**; we headline **~0.64**.
Same models, same runs, two protocols:

| channel | overall binary *(what the field reports)* | dedup *(honest)* | **macro zero-day** *(ours)* |
|---|---:|---:|---:|
| XGBoost | **0.9936** | 0.9901 | 0.6372 |
| CNN | **0.9928** | 0.9884 | 0.6446 |
| LTN control | 0.9921 | 0.9874 | 0.6049 |
| **CNN + KG fusion** | 0.9893 | 0.9896 | **0.7328** |

**The same model goes 0.9936 → 0.6372 — a 0.3564 gap — purely by changing protocol.** That is the
write-up's opening argument: *the field's numbers measure an easier task, and here is the same code
producing both.*

**Deduplication (issue C1, finally run):** 17.0 % of test rows are exact feature-vector duplicates of
a train row (PortScan 58.3 %, SSH-Patator 48.6 %). Removing them costs the supervised channels
0.0035–0.0049 — small, but the asymmetry is the point: **all six zero-day families measure 0.0 %
overlap**, so duplication inflates *the field's* metric and leaves *ours* untouched.

### 🔴 More channels do NOT help — a clean negative result

`scripts/fusion_multi.py`, five **pre-registered** subsets, equal-weight rank fusion, nothing fitted:

| subset | macro | Δ vs CNN | Bot | Web BF | XSS |
|---|---:|---:|---:|---:|---:|
| **CNN + KG (2 channels)** | **0.6926** | **+0.0527** | 0.2518 | 0.9283 | 0.8976 |
| ALL 9 channels | 0.6664 | +0.0265 | 0.1510 | 0.9302 | 0.9179 |
| A_ONLY (supervised) | 0.6600 | +0.0201 | 0.0730 | 0.9475 | 0.9596 |
| A+B+KG (3 channels) | 0.6509 | +0.0110 | 0.3147 | 0.8807 | 0.7572 |
| B_ONLY (benign-only) | 0.1180 | **−0.5219** | 0.0975 | 0.1642 | 0.0922 |
| *CNN alone* | *0.6399* | — | *0.0446* | *0.9226* | *0.9524* |

**Adding channels made it worse.** Under equal weighting IsolationForest (macro 0.0653) gets the
same vote as the CNN (0.6399), so weak channels dilute strong ones. The **2-channel** pairing wins
because CNN and KG are *complementary in a specific way* — the KG rescues Bot (0.0446 → 0.2518)
while the CNN holds the web attacks — not because more evidence is better.

**What survives as robust:** **4 of 5 subsets beat the CNN baseline.** Parameter-free fusion helps
reliably; the *amount* depends on picking complementary channels, not many.

⚠️ Five subsets were pre-registered and **all five are reported**. Quoting only the winner would be
a selection effect.

### Why we cannot simply "tune for a better score"

Zero-day families are **test-only by construction**, so any knob tuned on zero-day performance —
`k`, `tau`, burst threshold, channel subset — is fitting on the test set. That is the fusion wall in
another guise, and it is why every improvement here is **parameter-free by necessity, not by taste.**

**Still-legitimate levers, untested:** weighting channels by *known-class* validation performance
(uses no zero-day information — though the fusion wall predicts it will *down*-weight the KG and
hurt, which makes it a clean test); conformal / benign-only p-value calibration combined via
Fisher/Simes (proposed in KNOWN_ISSUES, needs no attack labels at all); and n≥6 seeds.

## 🔴 n=6 EVERYWHERE (2026-08-03) — the top tier is INDISTINGUISHABLE

All 7 channels now at n=6, with **consistent log-odds scoring** for the TF channels.

| channel | n=6 mean | range |
|---|---:|---|
| **CNN** | **0.6250** | [0.5966, 0.6446] |
| **LTN control** | **0.6110** | [0.5824, 0.6505] |
| RandomForest | 0.5985 | [0.5682, 0.6235] |
| MSP | 0.5761 | [0.5053, 0.6289] |
| Mahalanobis | 0.3948 | [0.2295, 0.5782] |
| Autoencoder | 0.1083 | [0.0894, 0.1346] |
| IsolationForest | 0.0681 | [0.0628, 0.0750] |

**Distinguishable only if the gap exceeds ~0.0256** (2·SE·√2 at n=6, SD 0.0222):

| comparison | gap | verdict |
|---|---:|---|
| CNN vs MSP | +0.0489 | ✅ distinguishable |
| LTN control vs MSP | +0.0349 | ✅ distinguishable |
| CNN vs RandomForest | +0.0265 | ✅ marginally |
| **CNN vs LTN control** | **+0.0140** | 🔴 **INDISTINGUISHABLE** |
| RandomForest vs LTN control | −0.0125 | 🔴 indistinguishable |

### 🔴 The symbolic control MATCHES the neural baseline

Not "the CNN wins narrowly" — **they cannot be told apart at achievable precision.** This is C2's
third and cleanest refutation.

⚠️ **And the gap SHRANK when a scoring inconsistency was fixed.** LTN control seeds 45–47 were
initially scored **raw** while 42–44 were **log-odds** — mixed scoring *within one channel*, which
penalises the LTN (it was saturated, so log-odds runs ~0.015–0.03 higher). Rescoring moved it
**0.5977 → 0.6110** and cut the CNN's apparent lead from +0.0273 to +0.0140. So the original C2 gap
was **partly a scoring artefact**, independent of the noise floor.

**What this does NOT overturn:** *"every axiom variant costs macro relative to the no-axiom control"*
— those gaps are 0.05–0.13, well above threshold. Phase 2's conclusion is unaffected and arguably
sharper: adding axioms hurts, but the axiom-free symbolic trainer matches the CNN.

**Three tiers, not a ranking:** supervised/closed-set (~0.58–0.63: CNN, LTN control, RF, MSP —
mutually indistinguishable) · distance (~0.39: Mahalanobis, range 0.35 wide — unstable) ·
benign-only (~0.07–0.11: AE, IsoForest). **The double dissociation lives ACROSS tiers**, which is why
it survives everything; the within-tier comparisons this project spent months on were always below
the noise.

## 🔴🔴 THE NOISE FLOOR — measured 2026-08-03, and it retracts a headline result

> **Read this before citing ANY number in this document.** It is the single most consequential
> measurement in the project, and it invalidates a claim that had already passed a significance test.

### Training is not reproducible at fixed seed

Six runs of **seed 42, identical code, idle machine**: 0.6446 · 0.6295 · 0.6366 · 0.6124 · 0.5825 ·
0.6280.

**mean 0.6223 · SD 0.0222 · range 0.0621 · CV 3.6 %**

TensorFlow on CPU is not bit-deterministic and **no determinism flags are set** in this project, so
thread scheduling changes float accumulation order between runs. A fixed seed does **not** pin the
result here.

### 🔴 C2 IS RETRACTED — on controlled grounds

*"The neural baseline beats the LTN control"* was closed in the CNN's favour earlier the same day
with a paired bootstrap, **p = 0.001**. Against the measured floor:

| | value |
|---|---:|
| C2 gap | +0.0204 |
| noise SD | 0.0222 |
| **ratio** | **0.9 SD** |

**The gap is smaller than re-running one model twice.** The bootstrap was arithmetically correct and
epistemically empty: it treated each run's score as exact when re-running moves it by up to 0.062.
**A paired significance test over per-flow scores cannot rescue a delta smaller than the pipeline's
own reproducibility.** This is the project's most important methodological lesson.

### 🔴 Every n=3 range in this document is an artefact

The CNN's macro range was repeatedly described as *"tight (spread 0.0093)"*. That spread is **0.4 SD**
— **less than half the noise of a single re-run.** Those ranges never measured seed variance; they
measured too few draws from a noisy process. **Do not cite any n=3 range as evidence of stability.**

### ⚠️ `cnn_paper = 0.6446` is the MAX of 11 runs, not a typical result

The headline CNN number is the top of an 11-run distribution (mean 0.6217). The honest, reproducible
baseline is the **ensemble: 0.6356**. This correction matters more than it looks — 0.6446 is the
number that would otherwise have gone into the paper as "the CNN's score".

### What survives, and why it always did

| claim | delta | ÷ SD | verdict |
|---|---:|---:|---|
| Double dissociation (XSS) | +0.8977 | **40.4** | ✅ **ESTABLISHED** |
| Double dissociation (Web BF) | +0.8178 | **36.8** | ✅ **ESTABLISHED** |
| Double dissociation (Bot) | +0.0868 | **3.9** | ✅ **ESTABLISHED** |
| CNN+KG fusion | +0.0527 | *paired* | ✅ **direction** (3/3 seeds positive); magnitude 0.027–0.088 |
| **C2: CNN vs LTN control** | +0.0204 | **0.9** | 🔴 **RETRACTED — within noise** |

The double dissociation strengthened under every test today while C2 collapsed under each one. That
was never about rigour applied — it was **effect size relative to a floor nobody had measured.**

> ⚠️ **On the fusion entry.** Judging it against the *between-run* floor (2.4 SD) is the wrong
> reference: the fused score is computed **from the same CNN run**, so run-to-run noise is shared by
> both sides and largely cancels. The right reference is the paired delta, which is positive on 3/3
> seeds but varies 0.027–0.088. **Direction established, magnitude not.**

### Three withdrawn claims, one underlying fact

Over the course of the session I asserted and then withdrew: *"n=3 understated seed variance 4–5×"*,
*"there is a session effect"*, and *"C2 must be reopened"*. All three were competing explanations for
**one unmeasured quantity**. Four training runs settled what hours of observational comparison could
not. A monotonic decline that looked like drift (ρ = −1.0 across three consecutive runs) **broke at
run 4** — it was coincidence, as its 1-in-6 probability predicted.

**The lesson: measure the variance before explaining it.**

## 🟡 THE SCORE IMPROVED (2026-08-03) — first combination to beat the CNN baseline

> ⚠️ **Amended 2026-08-03 (same day).** Direction holds (positive on 3/3 seeds) but the magnitude is
> uncertain (0.027–0.088), and the `0.6399` baseline it is quoted against is itself the mean of an
> n=3 sample from a process with SD 0.0222. See "THE NOISE FLOOR" above.

`scripts/fusion_kg.py`. **Parameter-free rank fusion of CNN + KG.**

| | macro | Bot | Web BF | XSS |
|---|---|---|---|---|
| CNN alone (the baseline) | 0.6399 [0.6353, 0.6446] | 0.0446 | 0.9226 | **0.9524** |
| **CNN + KG (rank-mean)** | **0.6926 [0.6626, 0.7328]** | **0.2518** | **0.9283** | 0.8976 |
| | **+0.0528** | **5.6×** | +0.0057 | −0.0548 |

**Verified on all three of this project's own bars:**
- **All 3 seeds improve** (+0.0881 / +0.0273 / +0.0428); fused range **disjoint** from the CNN's
- **Paired bootstrap +0.0528, 95% CI [+0.0468, +0.0594], p<0.001**
- **Survives the lateness control** — within-window Bot lift: CNN 1.50× · KG 3.20× · **fused 2.97×**

### Why this works when every previous fusion failed

**THE FUSION WALL applies to *fitted* combiners.** A fitted fuser is calibrated on validation data
containing no zero-day by construction, so it cannot *discover* that a zero-day-specific channel is
worth weighting — `fusion_beaconlike.py` measured exactly that and returned `[2.35, 0.02]`.

**A rank-mean needs no fitting: the weight is imposed, not discovered.** The combiner never has to
learn the value of a signal it was never shown. This is the same structural point as the Phase-2
conclusion that *training-time* constraints succeed where *inference-time* fitting cannot — reached
from the opposite direction, and it is the first constructive use of that insight.

### ⚠️ Caveats that must travel with the number

1. **Three combination rules were tried and the best is reported.** rank-mean 50/50 **+0.0528** ·
   rank 0.75/0.25 **+0.0320** · rank-**max** **−0.4125** (catastrophic; max is dominated by whichever
   channel has more top ranks, and `s_kg`'s coarse 193-value score puts huge tied blocks there).
   2 of 3 improve, and 50/50 is the canonical no-tuning default rather than a fitted choice — but
   this is a mild selection effect and is stated, not hidden.
2. **XSS gets worse** (0.9524 → 0.8976). A real trade, not a free win.
3. This is a **channel combination**, not the full Phase-5 Decision Fusion.
4. n=3; the bootstrap covers flow-sampling uncertainty only.

## 🟢 PHASE 4 BUILT (2026-08-03) — `scripts/kg.py`. Best Bot channel measured, with a caveat that halves it.

Adaptive KG over **raw-feature clusters** (215 nodes: 200 Cluster + 6 Behaviour + 9 AttackType;
1,183 edges). Memory initialised from TRAIN, then TEST **streamed in true chronological order** with
exponential edge decay (τ=3 windows) — the "adaptive" half of the project title. n=3 seeds.

### Two scores, and the causal one is better

| | macro | Bot | Bot lift |
|---|---|---|---|
| `s_kg` transductive (whole stream) | 0.1991 [0.1825, 0.2090] | 0.2457 [0.2377, 0.2583] | 7.2× |
| **`s_kg` causal / online (past only)** | **0.2488 [0.2446, 0.2523]** | **0.3103 [0.2970, 0.3210]** | **9.1×** |

**All four Phase-4 comparisons are significant** (paired bootstrap, B=2000):

| comparison | diff | 95% CI | p |
|---|---:|---|---:|
| KG causal vs **Autoencoder** (Bot) | **+0.1789** | [+0.1686, +0.1886] | <0.0005 |
| KG causal vs **RandomForest** (Bot) | **+0.1792** | [+0.1711, +0.1881] | <0.0005 |
| KG causal vs KG transductive (Bot) | +0.0646 | [+0.0598, +0.0692] | <0.0005 |
| **CNN vs KG causal (macro)** | **+0.3910** | [+0.3778, +0.4031] | <0.0005 |

So: **the KG is the best Bot channel ever measured here** (0.3103 vs the previous best 0.1314), and
**the online variant is significantly better than the batch one** — a good result for a real IDS,
since the deployable version is the stronger one. **The CNN still dominates macro by 0.39**, exactly
as scoped: the KG is not a general detector.

### 🔴 THE CONFOUND CONTROL — run it before quoting any of the above

The causal score rises with arrival position, and CIC-IDS2017 schedules attacks **late**. So
"later ⇒ more suspicious" could explain everything. Measured, and now a permanent part of `kg.py`:

| channel | Bot global | lift | **Bot within-window** | **lift** |
|---|---:|---:|---:|---:|
| **s_kg causal** | 0.3210 | 9.4× | **0.9134** | **3.2×** |
| s_kg transductive | 0.2583 | 7.6× | 0.9052 | 3.2× |
| Autoencoder | 0.1217 | 3.6× | 0.5368 | 1.9× |
| RandomForest | 0.0576 | 1.7× | 0.4217 | 1.5× |
| CNN | 0.0591 | 1.7× | 0.4267 | 1.5× |
| **lateness ONLY (control)** | **0.1575** | **4.6×** | 0.2853 | **1.0×** ✓ |

*Within-window = score family-vs-benign inside each time window separately, so lateness is held
constant. The control collapsing to exactly 1.0× confirms the test is sound.*

**Three things follow, and all three must reach the write-up:**

1. 🔴 **A trivial "later in the week" baseline scores Bot 0.1575 — beating the autoencoder (0.1314),
   the previous best channel.** That is a finding *about the dataset*: a meaningful share of
   apparent zero-day detection on CIC-IDS2017 is recoverable from the capture schedule alone.
   Anyone reporting temporal zero-day results here owes this control.
2. ✅ **The KG's advantage survives the control.** Within-window it still leads every channel —
   3.2× vs the AE's 1.9× and the CNN's 1.5×. The signal is real, not schedule artifact.
3. ⚠️ **But the headline 9.4× is roughly "schedule × cluster signal."** Quote **0.3103 global and
   3.2× within-window together**; the global figure alone overstates the method.

Also precise: **causal ≈ transductive within-window** (0.9134 vs 0.9052). The causal variant's
significant global edge comes almost entirely from better exploiting *when*, not from better
identifying *which* — worth stating plainly rather than implying a representational gain.

### What the KG actually delivers

Reasoning paths, which is the job the roadmap scoped it for:

```
Cluster:41 -[exhibits]-> [BeaconLike 93%, HighVolume 7%]
           -[associated_with]-> [DoS slowloris 100%]
           | EMERGING - activity concentrated in time (burstiness 20.0x uniform)
```

⚠️ Note the top-burstiness clusters are mostly **known** attacks and benign, not zero-day — the
zero-day ones sit lower. And `s_kg` takes only **193 distinct values** (one per cluster), so PR-AUC
is valid but **recall@1%FPR is degenerate — do not cite it.**

🎨 `scripts/kg_visualize.py` emits `outputs/figures/kg_graph.html` — a self-contained Obsidian-style
force-directed view (215 nodes, 931 edges, no CDN).

## ✅ LAST PHASE-4 GATE CLOSED (2026-08-03) — 1 of 3 emerging-pattern criteria works

`scripts/kg_criteria.py` → `outputs/metadata/kg_criteria.json`. Three predictions pre-registered.
With "unexplained cluster" already dead, this measured the spec's other two criteria — the only
remaining route to any KG detection role. **All three criteria are now measured. The gate is closed.**

Setup follows the decisions already taken: **raw features** (representation), **flow-count position
in true chronological order** (the adaptive time axis, kept per the 2026-08-03 decision), k=200.
Both criteria are computed **without labels** — growth from cluster ids + timestamps only,
co-occurrence calibrated on **benign training flows only**. Labels score the result, never define it.

### Verdict

| criterion | result | status |
|---|---|---|
| **#1 Growth / burstiness** | **lift 5.94× [5.66, 6.11] (n=3), recall ~0.81** | ✅ **WORKS — robust** |
| #2 Unexplained cluster | lift ≤ 1.00× (at or below chance) | 🔴 **DEAD** |
| #3 Behaviour co-occurrence | flow-level 2.81× at **1.5 % recall**; cluster-level ≤ 1.35× | ⚠️ **WEAK** |
| #1 ∧ #3 conjunction | lift 1.73–11.57×, precision 0.12–0.81 | 🔴 **NOT established** |

**✅ Criterion #1 (growth) is the one that works, and it is genuinely robust.** Burstiness ≥ 8
(peak-window share ÷ uniform share, 20 equal-flow-count windows) gives **lift 5.94× mean across 3
clustering seeds, range [5.66, 6.11]** — a tight range — at **~81 % recall** of all zero-day flows
and ~42 % precision against a 7.04 % base rate. At the looser burstiness ≥ 4 threshold it captures
**98.9 %** of zero-day flows at 3.27× lift.

> 🔴 **THE CONJUNCTION RESULT WAS A SINGLE-SEED ARTIFACT — CAUGHT BEFORE PUBLICATION.**
> On clustering seed 42, `burst ≥ 8 ∧ rarity ≥ p90` gave **lift 11.57× at 81.4 % precision** — the
> most striking number of the session, and it was about to be written up as the KG's headline.
> Multi-seeding first (the discipline this project adopted after four retractions) gives
> **11.57× / 2.37× / 1.73×** and precision **0.814 / 0.167 / 0.122**. A **6.7× lift spread.**
> **Do not cite "81 % precision."** This is the fifth single-seed trap in this project and the first
> one caught *before* it entered the documentation rather than after.

**⚠️ Criterion #3 (co-occurrence) is weak and also structurally coarse.** Only **24 of 64** possible
behaviour patterns occur in benign training data, so the rarity statistic is nearly discrete — the
p90/p95/p99 thresholds collapse onto the *same* value (9.6 bits) and flag identical flow sets. At
cluster level it is at or below chance (0.00× / 0.37× / 1.35×). Prediction Q2 confirmed. Root cause
is visible in the inputs: the five graded behaviours are DoS/scan-shaped (`BurstTraffic`,
`HighVolume`, `LargePackets`, `HighEntropy`, `ScanProbe`) and Bot/web attacks are none of those.

### 🔴 The external-validity caveat, which is not optional

**Growth works substantially because CIC-IDS2017's attacks are scripted into fixed windows.**
Reconstructed capture schedule (`timeline.py`): Web Brute Force **Thu 09:15–10:00**, XSS **Thu
10:15–10:35**, Bot **Fri 09:34–12:59** — against benign traffic spanning Mon 08:56 → Fri 17:02. Of
course a 20-minute attack burst is bursty. **A real network with continuous low-rate C2 beaconing
would not produce this signal**, and Bot is exactly the family whose real-world signature is
*persistence*, not bursts. This must be stated in any write-up: it is a property of the dataset's
experimental design as much as of the method. Q1 was pre-registered as *"will work, largely for the
wrong reason"* — confirmed on both halves.

### What this means for Phase 4 — the last gate is CLOSED

**The KG can proceed, with its detection contribution reduced to one mechanism: cluster growth
rate.** Combined with the earlier findings, Phase 4 is now fully specified by measurement:

- **Representation:** raw features (not embeddings — the AE bottleneck was rejected).
- **Scope:** corroboration + explainability (the "primary detector" path is measured dead).
- **Emerging-pattern rule:** growth/burstiness **only**. Drop "unexplained" (chance). Drop
  co-occurrence as a *detector* — it may still be worth keeping as an **explanation** attribute,
  which costs nothing and is the KG's actual job.
- **Decay:** kept (adaptive), flow-count over true chronological order.

> 🧭 **One honest observation to carry into the write-up.** "Temporal burstiness of a raw-feature
> cluster" **does not require a knowledge graph** — it is a much simpler mechanism than the spec's
> graph-with-decaying-edges. The KG's justification therefore has to rest on **explanation and
> corroboration** (reasoning paths, attributing a flow to a remembered pattern), not on this
> detection number. A reviewer will make this point; better to make it first.

## 🚨 PHASE-4 READINESS MEASURED (2026-08-03) — the KG's specified zero-day mechanism DOES NOT WORK

`scripts/kg_readiness.py` → `outputs/metadata/kg_readiness.json`. Four predictions pre-registered
before running. **Two decisive results, one of which falsifies the recommendation this document
made earlier the same day.**

### 🔴 PART B — "unexplained cluster" is WORSE THAN RANDOM. The mechanism is dead as specified.

STATUS has called this *"the single most important untested quantity"* since 2026-07-29. It is now
tested. The KG spec flags an emerging pattern partly by **weak or no `associated_with` edges to a
known AttackType**. Operationalised honestly — a cluster is "unexplained" if its **training** flows
contain < τ known-attack fraction (train labels only, which the KG legitimately has), then scored
against test labels:

| representation | τ=0.01 | τ=0.05 | τ=0.10 |
|---|---:|---:|---:|
| CNN embedding 64-d | **0.55×** | **0.54×** | **1.00×** |
| AE bottleneck 16-d | **0.28×** | **0.44×** | **0.43×** |
| Raw features 68-d | **0.93×** | **0.90×** | **0.90×** |

*(lift over the base rate of 0.0704 = 4,183 zero-day vs 55,237 benign test flows)*

**The best lift achieved by any representation at any threshold is 1.00× — i.e. exactly chance.
Everything else is BELOW 1.0, meaning a flow in an "unexplained" cluster is *less* likely to be
zero-day than a randomly chosen flow.** The criterion is not weak; it is **anti-correlated**.

The reason is structural and was visible in the pre-check: **118 of 200 clusters contain zero
known-attack training flows.** Benign traffic is diverse and makes up half the training set, so
"no known-attack anchor" describes most of the space. The criterion flags 48,000–59,000 of ~59,400
benign+zero-day test flows — it flags nearly everything.

**This is not a tuning problem.** Lift ≤ 1.0 across 3 representations × 3 thresholds. Prediction P4
(*"lift < 3× would kill the mechanism"*) is confirmed far more strongly than expected.

**What it means for Phase 4** — and this is constructive, not fatal:
1. 🔴 **The KG cannot be a primary zero-day detector via "unexplained cluster."** Do not build that.
2. ✅ **It empirically resolves the spec's scope contradiction.** `knowledge_graph.md` calls the KG
   the *"primary zero-day signal"*; `conference_roadmap.md §Phase 4` says *"corroboration +
   reasoning paths, not primary detector."* **The roadmap was right.** That is now a measurement,
   not a preference.
3. ⬜ **The spec's other two emerging-pattern criteria are still untested** — cluster **growth
   rate** and **behaviour co-occurrence**. If the KG is to retain any detection role it has to come
   from those, and they should be measured the same way *before* being built on.

### 🔴 PART A — and my own representation recommendation was WRONG

| representation | Bot purity across seeds (k=200) | spread | k=400 spread |
|---|---|---:|---:|
| CNN embedding 64-d | 87.9 / 86.6 / **44.4** % | **43.4 pp** | 28.3 pp |
| **AE bottleneck 16-d** | 82.0 / 74.1 / **29.9** % | **52.1 pp** | **44.3 pp** |
| **Raw features 68-d** | **77.6 %** (k=200) · 80.6 % (k=400) | **no training lottery** | — |

> 🔴 **PREDICTION P1 FALSIFIED — and it was the basis of this document's own recommendation.**
> Earlier on 2026-08-03, Open Decisions recorded *"(c) the AE's benign-trained 16-d bottleneck is
> now the data-backed lean"*, reasoning that the AE ranks Bot **reproducibly** (cross-seed Spearman
> ρ = 0.827, vs the CNN's −0.090). **That reasoning does not transfer.** Measured, the AE bottleneck
> is the *least* stable representation for clustering — **52.1 pp** Bot-purity spread, worse than
> the CNN's 43.4 pp.
>
> **The lesson: rank stability ≠ cluster stability.** The AE orders Bot flows consistently by
> reconstruction error, but the *geometry* of its 16-d bottleneck still varies enough across seeds
> to scatter Bot across different clusters. Those are different properties and I conflated them.
> This is precisely why the measurement had to be run instead of argued — the recommendation was
> confident, cheap to test, and wrong.

**✅ Raw features (option b) is the data-backed choice.** Bot purity 77.6 % (k=200) / 80.6 % (k=400)
— competitive with the CNN's *good* seeds, far above its worst (44.4 %), above the AE's mean, and
with **no training-seed lottery at all**, since no model is trained.
⚠️ **Precisely stated:** raw features remove the *training* lottery, not all variance — k-means has
its own seed, worth ~2.6 pp per `kg_precheck.py` Part 2. That is an order of magnitude below the
28–52 pp training lottery, not zero.

**A pattern worth noting:** Bot-purity instability appears in **every learned representation** (CNN
and AE alike) while Web BF / XSS purity stays stable in both (0.7–2.5 pp for the CNN; 53.4/53.4/54.4 %
for the AE). Consistent with the Bot failure analysis — Bot's signature is not what either training
objective is organised around, so where Bot lands is left to initialisation.

## 🔬 WHY THE CNN FAILS ON BOT — ANSWERED (2026-08-03)

`scripts/bot_failure_analysis.py`. **Four hypotheses were written into the script before it was
run** (the pre-registration discipline that caught the modality-analogue error). Artifact:
`outputs/metadata/bot_failure_analysis.json`.

This was the project's last open research question: the skyline oracle proved the Bot signal is
fully present in the 68 features (PR-AUC 0.0314 → **0.9764** when ~1,000 labels are revealed), yet
every closed-set method sits near chance. **That gap now has a measured mechanism.**

### The three measurements that compose into the answer

**① Bot is not "missed" — it is confidently absorbed into BENIGN. (H1: CONFIRMED, more strongly
than predicted.)**

| test family | argmax = BENIGN | mean p(BENIGN) | modal predicted class |
|---|---:|---:|---|
| **Bot** | **100.0 %** | **0.9984** | **BENIGN (100.0%)** |
| Web Attack Brute Force | 10.1 % | 0.1046 | **DoS slowloris (89.8%)** |
| Web Attack XSS | 3.1 % | 0.0413 | **DoS slowloris (92.9%)** |
| BENIGN *(reference)* | 99.7 % | 0.9955 | BENIGN (99.7%) |

Identical across all three CNN seeds (Bot 100.0 % / 100.0 % / 100.0 %). **The CNN does not find Bot
ambiguous — it asserts benign.** *(The mean-p comparison to real benign is affected by benign's
0.3% misclassified tail; the robust statement is the 100% argmax, which is seed-invariant.)*

**This also supplies the transfer mechanism the falsified "modality analogue" story was reaching
for — now measured rather than assumed.** Web attacks transfer *not* because the CNN detects them,
but because it misclassifies them into **DoS slowloris**, a known *attack* class — which still
lands on the correct side of the benign/attack binary. Their 0.92–0.95 PR-AUC is **absorption into
a known attack**, not zero-day detection. Bot has no such absorber and falls into benign.
⚠️ Note this is a *different* answer from `modality_analysis.py`'s raw-space nearest known attack
(**DoS Hulk**): what the classifier actually does ≠ raw-space proximity. Both are HTTP/DoS-shaped,
so a loose "shared HTTP modality" reading survives, but do not claim the specific class without
citing which measurement.

**② The features that separate Bot from benign are orthogonal to the ones the task teaches.
(H3: CONFIRMED — predicted ≤2/8 overlap, measured 0/8.)**

| | top-8 features |
|---|---|
| What the **known-class task** needs (benign vs known attack, fit on train) | Bwd Packet Length Min · Total Fwd Packets · Average Packet Size · Bwd Packet Length Std · Bwd Header Length · PSH Flag Count · Fwd Packet Length Max · Init_Win_bytes_backward |
| What **separates Bot from benign** (oracle, held-out eval) | Bwd IAT Min · Bwd Packet Length Mean · Bwd Packet Length Max · Fwd Header Length · Destination Port · min_seg_size_forward · Init_Win_bytes_forward · Total Backward Packets |
| **overlap** | **0 of 8** *(Web BF for contrast: 1 of 8)* |

A discriminative model only learns what separates the classes it is shown. Bot's signature is
**orthogonal to that feature set**, so there is no gradient pressure to represent it.

**③ Therefore the CNN's residual Bot score is NOISE, not a weak signal. (H2b: CONFIRMED — and this
is the sharpest number in the study.)**

Spearman rank correlation *between CNN seeds*, computed within each family — "do independently
trained models agree on which flows are most suspicious?"

| channel | **Bot** | Web Attack BF | Web Attack XSS | BENIGN (ref) |
|---|---:|---:|---:|---:|
| CNN `cnn_paper` | **−0.090** | 0.678 | 0.830 | 0.696 |
| RandomForest | **0.068** | 0.803 | 0.757 | 0.653 |
| **Autoencoder** | **0.827** | 0.941 | 0.912 | 0.971 |

**Both supervised models rank Bot flows essentially at random with respect to each other** (ρ ≈ 0,
one slightly negative) while ranking every other family consistently. **The autoencoder does not
have this problem.** Any statistic computed on a noise ranking is a lottery — which is exactly and
independently what the Phase-4 blocker (cluster purity 87.9/86.6/**44.4**%), the Mahalanobis Bot
spread (1.2–4.3×) and RandomForest's Bot swing (0.0576/0.1933/0.1423) all are. **One cause, four
symptoms.**

### Two hypotheses refuted, which matters for what NOT to try

- **H4 — "Bot is intrinsically harder / overlaps benign in raw space." REFUTED as predicted.** Given
  labels, Bot is as separable as the web attacks: oracle PR-AUC **0.9988** (ROC 0.9999) vs Web BF
  0.9999 / XSS 0.9984. There is nothing intrinsically hard about Bot.
- **H2(a) — "Bot sits near the decision boundary." REFUTED as stated.** Bot is not boundary-adjacent,
  it is **benign-interior**: only 9.6 % of Bot flows score below the benign *median*, and its
  AUC-vs-benign is 0.7115 (vs 0.9908 / 0.9982 for the web attacks). So a *little* signal survives —
  enough for AUC 0.71, nowhere near enough for PR-AUC at 3.4 % prevalence. **Threshold tuning cannot
  fix this**; the ordering itself is unreliable (see ③).

### What this establishes

> **The CNN's Bot failure is representational, not informational.** A closed-set discriminative model
> learns only the features that separate the classes in its training set. Bot's discriminative
> features are disjoint from that set (0/8), so Bot is projected into the benign region and asserted
> benign with 100% argmax agreement across seeds. The residual score carries no reproducible
> ordering (ρ = −0.09). **This is a general prediction about closed-set zero-day detection, not a
> fact about Bot** — it says a novel class is detectable by an (A)-family model exactly to the
> extent that its signature overlaps the known-class discriminative basis, and is *undetectable and
> unstable* otherwise. That is falsifiable on other datasets and is the strongest claim this project
> currently has.

**⚠️ Scope limits, stated plainly.** n=3 seeds, one dataset, one architecture. The feature-importance
comparison uses XGBoost as a proxy for "what the task needs" — the CNN's own attributions were not
measured (SHAP is installed and this is the obvious follow-up). "0/8 overlap" is a top-8 cut; the
full importance-vector correlation was not computed.

## 🔴 THE (A)/(B) FRAMING IS FALSIFIED IN ITS STRONG FORM (2026-08-03)

> Found while fixing a **bookkeeping** defect — the classical baselines were n=1 and on the
> pre-2026-07-27 metric schema. Putting them on 3 seeds and the current schema produced a result
> that contradicts a load-bearing part of the thesis reframing.

**RandomForest, n=3 (new):**

| channel | family | macro | Bot | Bot lift | Web BF | XSS |
|---|:---:|---:|---:|---:|---:|---:|
| **RandomForest** | **A** | **0.5995** [0.5682, 0.6235] | **0.1311** [0.0576, 0.1933] | **3.8×** | 0.8686 | 0.7987 |
| Autoencoder | B | 0.0970 | 0.1314 | 3.8× | 0.1048 | 0.0547 |
| CNN | A | 0.6399 | 0.0446 | 1.3× | 0.9226 | 0.9524 |

**Paired bootstrap verdicts** (`significance.py`):
- **RF vs AE on Bot: diff −0.0003, 95% CI [−0.0070, +0.0060], p = 0.88 → a statistical tie**, and a
  tight one.
- RF vs AE on macro: **+0.5025**, p < 0.0005 → RF dominates.
- RF vs CNN on Bot: **+0.0865**, p < 0.0005 → RF beats the CNN on Bot by 2.9×.

**What breaks:**

1. 🔴 **"The project invested in (A) on a problem that is structurally (B)" — does not survive.**
   RandomForest is squarely (A): supervised, trained on benign vs known attacks, never sees a Bot
   flow. It reaches the best (B) method's Bot performance **and** keeps 0.60 macro. You do not need
   a (B) method to reach Bot.
2. 🔴 **"There is a monotonic trade-off frontier — no channel sits at both ends" (Finding 2 of the
   train-vs-score decomposition) — FALSIFIED.** RF sits at both ends: AE-level on Bot, near-CNN-level
   on web attacks. The frontier was an artifact of only having sampled four channels.
3. ⚠️ **The double dissociation (CNN vs AE) survives and is now *significant*** — but it is a
   dissociation between **two particular models**, not between two **method families**. Do not
   write it up as an (A)-vs-(B) result.

**What survives:** the *observation* that benign-only training reaches Bot without labels is intact
and still interesting (the AE gets there with zero attack supervision, and — per the Bot analysis
above — with a **stable** ranking, ρ=0.827, which neither supervised model achieves). The claim that
it is *necessary* is dead.

**Why RF succeeds where the CNN fails — consistent with the Bot analysis.** RF is an axis-aligned
ensemble over raw features; it can split on `Destination Port` / `Init_Win_bytes_forward` for known
classes and those splits incidentally isolate Bot. The CNN compresses to a 64-d embedding optimised
*only* for known-class separation, discarding what it doesn't need. ⚠️ **This is a plausible account
consistent with the evidence, not a measured mechanism** — RF's own Bot ranking is *also* unstable
across seeds (ρ=0.068), so it is not reliably solving Bot either; its higher mean comes with a
0.0576–0.1933 spread. **Do not write "RF solves Bot."**

## ✅ SIGNIFICANCE TESTS RUN (2026-08-03) — C2 closed, one retraction reversed

`scripts/significance.py` → `outputs/metadata/significance.json`. Stratified **paired bootstrap over
test flows** (B=2000; benign and family resampled separately preserving counts, so the family's
chance PR-AUC is held fixed and PR-AUC moves only with ranking quality). Multi-seed channels are
collapsed to their mean-over-seeds inside each replicate.

| comparison | metric | diff | 95% CI | p | verdict |
|---|---|---:|---|---:|---|
| **CNN vs LTN control** | macro | **+0.0204** | [+0.0082, +0.0331] | **0.001** | ✅ **SIGNIFICANT** |
| CNN vs Autoencoder | Bot | −0.0868 | [−0.0940, −0.0800] | <0.0005 | ✅ AE wins |
| CNN vs Autoencoder | Web BF | +0.8178 | [+0.8017, +0.8330] | <0.0005 | ✅ CNN wins |
| CNN vs Autoencoder | XSS | +0.8977 | [+0.8734, +0.9192] | <0.0005 | ✅ CNN wins |
| RandomForest vs Autoencoder | Bot | −0.0003 | [−0.0070, +0.0060] | 0.88 | ⬜ **tie** |
| RandomForest vs CNN | Bot | +0.0865 | [+0.0807, +0.0926] | <0.0005 | ✅ RF wins |
| RandomForest vs Autoencoder | macro | +0.5025 | [+0.4841, +0.5222] | <0.0005 | ✅ RF wins |
| **CNN vs XGBoost** | macro | +0.0027 | [−0.0161, +0.0217] | **0.80** | ⬜ **n.s.** |
| Autoencoder vs Mahalanobis | Bot | +0.0284 | [+0.0227, +0.0339] | <0.0005 | ✅ AE wins |

*(p is floored at 1/B; "<0.0005" means no bootstrap replicate crossed zero.)*

**① C2 is properly closed — and it resolves in the CNN's favour after all.** The overlapping n=3
seed ranges (CNN [0.6353, 0.6446] inside control [0.6029, 0.6505]) suggested no winner. The
**paired** test cancels flow-sampling noise common to both channels and finds the CNN's +0.0204
advantage robust (p=0.001). **⚠️ Estimand caveat, and it matters:** this tests whether the
*seed-mean* differs, treating these 3 seeds as fixed, and quantifies *flow*-sampling uncertainty
only. It does **not** establish that a *fresh* CNN seed would beat a *fresh* control seed. At n=3
the Wilcoxon signed-rank floor is p=0.25, so **no seed-level claim in this project can reach
p<0.05 — that needs n≥6 seeds.** Both uncertainties are reported; do not conflate them.

**② The double dissociation is now statistically established**, not merely non-overlapping ranges.
Its *interpretation* changes though — see the (A)/(B) falsification above.

**③ 🔴 A RETRACTION IS REVERSED: "on macro the CNN beats XGBoost" is NOT supported (p=0.80).**
On 2026-07-27 the claim *"XGBoost (tabular SOTA) ≈ CNN"* was **retracted** on the grounds that the
corrected macro metric showed the CNN winning 0.6446 vs 0.6372. That retraction compared two point
estimates with no test. The paired bootstrap puts the difference at +0.0027 with a CI spanning zero.
**The original "XGBoost ≈ CNN" claim was correct; retracting it was premature.** Consequence: the
Phase-1 note that *"the 'pivot the story to explanation/adaptivity/response' framing was motivated
by a tie that isn't there and should be revisited"* is **withdrawn — the tie is there.**
This is the project's first retraction-of-a-retraction, and the lesson is symmetric to the earlier
ones: *a point-estimate gap is not a result in either direction.*

## Component Status

> 🔑 **THIS TABLE IS THE SINGLE SOURCE OF TRUTH for component status** (established 2026-08-03).
> `CLAUDE.md`, `target/roadmap_gap_analysis.md` and `target/target_architecture.md` now point here
> instead of maintaining parallel tables. Phase *numbering* (a different thing) is canonical in
> [conference_roadmap.md §1b](target/conference_roadmap.md).
>
> ⚠️ **This table was itself the stalest thing in the repo when audited on 2026-08-03** — it still
> described the autoencoder as `n=1 / macro 0.1000 / Bot 3.6× / 0.0000 recall on web attacks` after
> all four had been superseded *the previous day, 400 lines above it in this same file*; it cited
> "PortScan/DDoS strongly covered" (a claim KNOWN_ISSUES explicitly forbids); it said the behaviours
> were "not yet wired into LTN" (they had been since 2026-07-27); and it had **no rows at all** for
> `cnn_paper.py`, `baselines.py` or `novelty.py`, pointing instead at the superseded `cnn3.py`/`eval.py`.
> Rewritten below. **If you change a component's status, change it HERE.**

**Current pipeline (paper-aligned split) — this is what all reported results use:**

| Component | Status | File | Notes |
|-----------|--------|------|-------|
| Preprocessing | ✅ Working | `scripts/preprocess.py` | 68 flow features + binary/multiclass labels. **Keeps** IP/port/timestamp in a row-aligned `meta_*.csv` side-table (since the 2026-06-18 dataset upgrade) — the old "drops IPs/ports" note was wrong. |
| Paper-aligned split | ✅ Working | `scripts/preprocess_paper.py` | 9 known classes stratified 80/10/10, benign under-sampled 1:1. Train 883,796 / val 110,475 / test 114,658. Leakage-verified. |
| **CNN + embeddings (neural pillar)** | ✅ **Verified correct — n=3** | `scripts/cnn_paper.py` | **macro 0.6399 [0.6353, 0.6446]**, log-odds scored. Multi-seed via `CNN_SEED`. Named `"embedding"` layer feeds novelty + KG. Minor: double class-weighting ([cnn_current.md](implementation/cnn_current.md)). |
| Classical baselines | ✅ **n=3 (2026-08-03)** | `scripts/baselines.py` | XGBoost / RandomForest / IsolationForest. Multi-seed via `BASELINE_SEED`. Previously n=1 **and** on the pre-2026-07-27 metric schema (no macro logged) — both fixed; see "Last Measured Results". |
| Novelty channels | ✅ **n=3** | `scripts/novelty.py` | MSP macro 0.5884, Mahalanobis 0.3777. Post-hoc on a trained CNN, no retraining. ⚠️ "Mahalanobis 4.3× on Bot" is **retracted** (seed 42 only); n=3 mean **3.0×**, seed 44 at chance. |
| Behaviour abstraction | ✅ Rebuilt & validated | `scripts/behavior.py` | Verified indices, vectorised, fuzzy [0,1], thresholds saved. **7 behaviours** incl. `BeaconLike`. ⚠️ **Wired into LTN as Ax3–Ax6 since 2026-07-27.** ⚠️ Its validation tables were measured on the *temporal* split where PortScan/DDoS were zero-day — under the current protocol both are **known**, so "PortScan/DDoS strongly covered" is **not** evidence for the symbolic approach. `RepeatedConnections` is constant 0.0 (unblocked but unwired). See [doc](implementation/behaviour_abstraction_current.md). |
| Metrics / tracking infra | ✅ Working | `scripts/metrics.py`, `tracking.py` | Headline = **macro** zero-day PR-AUC over powered families (n≥100); detects float32 saturation; appends to `runs.jsonl` (now version-controlled, see KNOWN_ISSUES). |
| LTN reasoning (paper-split) | 🟡 Anatomized, multi-seeded — macro cost confirmed, Bot benefit retracted | `scripts/ltn_paper.py` | Clean (log-odds) control macro 0.6049 (n=1) / 0.6194 (n=3 mean); every axiom variant tried (old Ax3-5, targeted Ax6) costs macro relative to control, robust across seeds. ω=2.0 always collapses; ω=1.0 collapses 2/3 seeds — not the "safe zone" it looked like on n=1. Ax6's apparent Bot-lift improvement did not survive multi-seeding (control's own Bot lift ranges 1.5–2.9x). See STATUS "RESUME HERE" → "🔴 MULTI-SEED RESULTS" for the full table + retraction. |
| **Anomaly pillar (autoencoder)** — canonical **Phase 3** | ✅ **Built, run & multi-seeded 2026-08-02 — n=3** | `scripts/autoencoder_paper.py` | Benign-only reconstruction error; **zero attack labels used in training *or* model selection**, so it is zero-day-legitimate by construction. **macro 0.0970 [0.0894, 0.1014]** · **Bot 0.1314 (3.8×) — the best Bot channel measured** · loses on web attacks (0.1048 / 0.0547). Establishes the **double dissociation** vs the CNN. Multi-seed via `AE_SEED`. ⚠️ Its first-day interpretation (a "modality analogue" mechanism) was **falsified the same day**; the *pattern* is real, the *explanation* is open — see "PHASE 3 RESULTS". |
| **Knowledge Graph** — canonical **Phase 4** | 🟢 **BUILT & multi-seeded 2026-08-03** | `scripts/kg.py` | 215 nodes / 1,183 edges on **raw-feature** clusters (CNN embeddings and the AE bottleneck were both measured and rejected). Adaptive decay over true chronological order. **s_kg causal: macro 0.2488, Bot 0.3103 — best Bot channel measured.** Scope is corroboration + explanation: the spec's "unexplained cluster" detector is measured dead (≤1.00×). ⚠️ Mandatory lateness control lives in the script — a trivial "later in the week" baseline scores Bot 0.1575. Viz: `kg_visualize.py`. |
| Decision Fusion — Phase 5 | ❌ Not built | — | ⚠️ A **fitted** combiner is structurally blocked — validation contains no zero-day by construction, so it cannot learn to weight a zero-day-specific channel (`fusion_beaconlike.py` → `[2.35, 0.02]`). See "THE FUSION WALL". Spec: [decision_fusion.md](target/decision_fusion.md). |
| Explainability / Final Alert | ✅ **BUILT 2026-08-03 — 3 of 3 + faithfulness** | `scripts/explain.py` (+ KG paths in `scripts/kg.py`) | ✅ **Neural explanation** — Integrated Gradients against `tf.GradientTape`, with the completeness axiom verified as a correctness check (\|error\| 0.0001–0.042). ✅ **Logic explanation** — per-axiom SAT; only Ax3–Ax6 are reported, because Ax1/Ax2 are label anchors and would be circular at inference. ✅ **KG explanation** — reasoning paths. ✅ **Final Alert assembly.** ✅ **Faithfulness (Tier A)** — ERASER deletion metrics vs a random-feature control: masking IG's top-3 drops the attack score **20.67×** more than 3 random features. ⚠️ Sufficiency is the weaker half and is reported as such (0.442–0.460 vs random 0.513–0.515) — the decision is distributed across more than 10 features. Spec: [explainability.md](target/explainability.md). |
| Response engine (IPS) | ❌ Not built | — | Phase R (Shaunak solo, last). Temporal-replay containment. |

**Legacy (temporal-split) pipeline — superseded 2026-06-18, retained as a secondary "hard mode" result:**

| Component | Status | File | Notes |
|-----------|--------|------|-------|
| CNN (multiclass, temporal) | 🔴 Superseded | `scripts/cnn3.py` | The 0.6689 PR-AUC baseline. ⚠️ Trained with the **broken focal loss** and never retrained — see the open caveat in [KNOWN_ISSUES.md](KNOWN_ISSUES.md). |
| CNN evaluation (temporal) | 🔴 Superseded | `scripts/eval.py` | Produces `cnn_zeroday_eval.png`. Reads `outputs/metadata/_legacy_temporal/`. |
| LTN reasoning (temporal) | 🔴 Superseded | `scripts/ltn.py` | Ran, underperformed (0.45 vs 0.67); SAT dominated CE ~40:1. Superseded by the protocol reset — see [doc](implementation/ltn_current.md). |

**Direction:** targeting top-tier publication — see [conference_roadmap.md](target/conference_roadmap.md) for plan v1.2 + the Tier-S/A/B "godly" agenda.

## Remaining Work ("what's left")

Ordered build queue. ✅ done · ▶ next · ⬜ pending.

| # | Item | Status | Notes |
|---|------|--------|-------|
| 0 | Behaviour abstraction rebuild | ✅ | Done 2026-06-18. Validated; thresholds saved. |
| 1 | **Re-ground LTN axioms on behaviours** | ✅ Concluded (not "done" in the sense of shipping a win — see multi-seed retraction below) | Ax3–Ax6 all implemented, smoke-tested, multi-seeded. Every variant costs macro PR-AUC vs. the no-axiom control; targeted Ax6 (BeaconLike)'s apparent Bot-lift benefit did not survive multi-seeding. `ratio` omega-mode confirmed as the safe default if this line is revisited. Not pursuing further axiom variants for now. |
| 2 | Decide `RepeatedConnections` data path | ⬜ deprioritized | **Unblocked, not blocked** — `meta_{train,val,test}.csv` now carry IP/port/timestamp aligned row-for-row. No longer motivated as a Bot fix (B2/fusion findings above); may still help Infiltration/lateral-movement. Wiring it is a choice, not a data problem. |
| 2b | **Anomaly pillar — benign-only autoencoder (canonical Phase 3)** | ✅ **DONE 2026-08-02** | Ran. Closes the "why not an autoencoder?" objection with a number, and produced the modality-analogue refinement that reframes the whole architecture. Was nearly skipped by a phase-number collision. **Follow-up (not scheduled): multi-seed it (n=1 today), and measure modality similarity to test the refined account.** |
| 2c | **Pre-Phase-4 remediation + significance + Bot analysis** | ✅ **DONE 2026-08-03** | All audit discrepancies fixed (research record version-controlled, component status collapsed to one table, `kg_precheck` now persists, baselines on n=3 + current schema, legacy artifact collision resolved). Plus three research outputs: **significance tests run** (C2 closed; one retraction reversed), **the (A)/(B) strong form falsified** by RandomForest, and **the CNN's Bot failure explained**. |
| 3 | **Knowledge Graph (NetworkX) — canonical Phase 4** | ✅ **BUILT & multi-seeded 2026-08-03** (the KG half of Phase 4; explainability half is item 5) | **Prerequisites now measured** (`kg_readiness.py`). ✅ Representation decided on evidence: **raw features** (Bot purity 77.6/80.6 %, no training lottery) — *not* the AE bottleneck, whose 52.1 pp spread was the worst of all options. 🔴 **Scope forced by measurement: corroboration + explainability, NOT primary detection** — the "unexplained cluster" criterion scores **lift ≤ 1.00× (at or below chance)** across every representation and threshold, so that mechanism is dead. ✅ **Last gate CLOSED 2026-08-03**: all three emerging-pattern criteria measured — **growth works** (lift 5.94x [5.66, 6.11], n=3, ~81% recall), unexplained is dead, co-occurrence is weak. ✅ Decay decided: **keep it adaptive**, flow-count over true chronological order. Spec: [knowledge_graph.md](target/knowledge_graph.md). |
| 4 | Decision Fusion — canonical Phase 5 | 🟡 **PARTIALLY DONE — entered without being scheduled** | ⚠️ **Scope note (2026-08-03):** Phase 5 is *"Fusion + rigor (seeds, significance, calibration, latency)"*, and parts of it were done while answering other questions rather than as a planned phase start. **Done:** `significance.py` (paired bootstrap) · `fusion_kg.py` + `fusion_multi.py` (parameter-free rank fusion, **+0.0527 macro, p<0.001** — the first result to beat the CNN baseline; direction established on 3/3 seeds, **magnitude uncertain 0.027–0.088**) · **n≥6 seeds ✅ DONE 2026-08-04** (`rigor_n6.sh`, all 7 channels — and it showed the top tier is mutually **indistinguishable**). **NOT done:** the *fitted* Decision Fusion the spec actually describes (blocked by THE FUSION WALL) · calibration · latency. Spec: [decision_fusion.md](target/decision_fusion.md). |
| 5 | **Explainability / Final Alert — the REST of canonical Phase 4** | ✅ **DONE 2026-08-03 — 3 of 3 + faithfulness** (`explain.py`) | ✅ Neural (Integrated Gradients, completeness-checked) · ✅ Logic (per-axiom SAT, Ax3–Ax6 only — Ax1/Ax2 are label anchors and would be circular) · ✅ KG reasoning paths · ✅ Final Alert assembly · ✅ Tier-A faithfulness (IG top-3 masking is **20.67×** a random-feature control; sufficiency reported as the weaker half). **Phase 4 is therefore complete.** Its most informative output is not a score: on a Bot flow the CNN calls benign, **both other pillars dissent** — no single-pillar system produces that. Spec: [explainability.md](target/explainability.md). |
| 6 | Ablation (CNN → +LTN → +KG → full) | ✅ **DONE 2026-08-05** (`ablation.py`) | 🔴 **Result is negative: only the KG earns its place.** The symbolic pillar adds nothing alone (−0.0004, n.s.) and **significantly hurts stacked on the KG** (0.6926 → 0.6708, p<0.0001). See the ablation section. |
| 7 | **Phase 7.5 — OPERATIONAL READINESS (intermission, after the paper)** | 🟡 **TIER 1 DONE 2026-08-05** — `operational.py`, all 4 predictions confirmed. **GATES PHASE R** | See the dedicated section below. Four Tier-1 items that decide whether automated response is *safe*, plus three noise-reduction items. **PR-AUC is the wrong target for a response engine** — it summarises ranking across all thresholds, while the engine acts at ONE. |

Enhancement backlog (not scheduled): [enhancements.md](target/enhancements.md).

## 🧭 PHASE 7.5 — OPERATIONAL READINESS (intermission, planned 2026-08-03)

**Sits between Phase 7 (paper) and Phase R (response engine), and gates Phase R.** Not started.

### Why this phase exists

**PR-AUC is the wrong target for a response engine.** It summarises *ranking quality across all
thresholds*; a response engine acts at **one threshold**. What decides whether automated response is
safe is **precision at that operating point** — a false positive means auto-blocking legitimate
traffic. A system can post macro 0.69 and still auto-block at 40 % precision, which is operationally
unusable, and **no metric currently in this project would warn you.**

Three capabilities that determine response accuracy are entirely absent today.

### Tier 1 — gates Phase R (mostly evaluation code, low compute)

| # | Item | Why it matters for response |
|---|---|---|
| 1 | **Ship the ensemble, not a single run** | Measured noise floor is **SD 0.0222, CV 3.6 %** at fixed seed. You cannot deploy a model whose score swings 0.06 between identical trainings. Ensembling 11 existing runs gives **0.6356** (+0.0138 over the mean single run) and, more importantly, is **reproducible**. ⚠️ It does *not* beat the best single run (0.6446) — because **0.6446 is the max of 11 runs, not a typical result.** The honest deployable baseline is the ensemble. |
| 2 | **Calibration** — isotonic/Platt fitted on **known classes only** (no zero-day leakage), plus **ECE** and reliability curves | Without it, `p = 0.9` does not mean 90 % and every threshold is arbitrary. |
| 3 | **Precision @ alert budget** | The operational metric: *"at 100 alerts/day, what fraction are real?"* This predicts response accuracy; PR-AUC does not. |
| 4 | **Selective prediction / abstention** — precision-vs-coverage curve | The engine should **not act** when uncertain. Find the confidence band where precision is high enough to auto-act, defer the rest to a human. |

### Tier 2 — reduce noise at source

| # | Item | Note |
|---|---|---|
| 5 | **TF determinism flags** (`enable_op_determinism()`, fixed `intra_op`/`inter_op`) | ✅ **BUILT 2026-08-05** — `scripts/determinism.py`, wired into `cnn_paper`/`ltn_paper`/`autoencoder_paper`. Pins `PYTHONHASHSEED`, op-determinism and **fixed** thread counts (intra=16/inter=2 — fixed, not minimal). ⚠️ **Whether pinned multi-threading is enough is an empirical claim, so it is tested, not assumed**: `verify_determinism.sh` trains seed 42 twice and requires **byte-identical** output. ⚠️ **Determinism does not make old and new runs comparable** — pinning threads changes the reduction order, defining a *new* fixed point; do not pool across the flag. |
| 6 | **k-fold CV** instead of a single stratified split | Better variance estimates; uses all the data. |
| 7 | **Checkpoint averaging (SWA)** | Cheap intra-run variance reduction. |

### Tier 3 — deferred

Cross-dataset validation (Phase 6 proper) · architecture search. Larger effort, lower
value-per-hour than Tier 1 for the response use case.

### The standard every future claim must meet

**Measured noise floor: SD 0.0222 / range 0.0621** over 6 identical seed-42 runs. Express every
delta as a **multiple of it** — that ratio, not the raw number, decides whether a claim survives:

| claim | delta | SD | verdict |
|---|---:|---:|---|
| Double dissociation (XSS / WebBF) | +0.90 / +0.82 | 40 / 37 | ✅ established |
| Double dissociation (Bot) | +0.0868 | 3.9 | ✅ established |
| CNN+KG fusion | +0.0527 | *(paired — 3/3 seeds positive)* | ✅ direction; magnitude uncertain |
| C2: CNN vs LTN control | +0.0204 | 0.9 | 🔴 within noise |

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
| ~~Run the Phase-3 autoencoder before the KG?~~ | ✅ **DECIDED & DONE 2026-08-02** | Ran it (n=3). Verdict: worth it. It answered the reviewer objection *and* produced the double-dissociation result, retracted "Mahalanobis 4.3×", and exposed the Phase-4 blocker. The prediction that its result was "genuinely unpredictable" held — it beat the CNN on Bot and lost 6.6× on macro. |
| 🔴 **Which representation should the KG cluster?** | ✅ **MEASURED 2026-08-03 → recommend (b) RAW FEATURES.** Awaiting sign-off. | **Clustering purity is now measured for all options** (`kg_readiness.py`), and it **overturned the lean recorded here earlier the same day.** (a) ensemble CNN seeds — ❌ futile: the CNN's Bot ranking is noise (ρ=−0.090); averaging noise creates no signal. (b) **raw features — ✅ RECOMMENDED**: Bot purity **77.6 % (k=200) / 80.6 % (k=400)**, competitive with the CNN's good seeds and far above its worst (44.4 %), with **no training lottery** (residual k-means seed sensitivity ~2.6 pp). (c) AE bottleneck — 🔴 **WAS the lean, now REJECTED**: measured Bot-purity spread **52.1 pp**, the *worst* of all options, because **rank stability ≠ cluster stability** — the AE orders Bot flows consistently (ρ=0.827) but its 16-d geometry still scatters them across seeds. (d) accept-and-publish — unnecessary now that (b) exists. |
| 🔴 **Is the KG a primary detector or corroboration?** | ✅ **RESOLVED EMPIRICALLY 2026-08-03 → corroboration.** | The spec contradiction (`knowledge_graph.md` "primary zero-day signal" vs `conference_roadmap.md` "corroboration, not primary detector") is settled by measurement, not preference: the "unexplained cluster" criterion scores **lift ≤ 1.00× — at or below chance — across 3 representations × 3 thresholds.** The primary-detector path is dead. **The roadmap was right.** |
| ~~**Do the KG's other two emerging-pattern criteria work?**~~ | ✅ **MEASURED 2026-08-03 — 1 of 3 works. Gate closed.** | `kg_criteria.py`. **Growth/burstiness WORKS and is robust**: lift **5.94×** [5.66, 6.11] n=3, ~81 % recall. **Co-occurrence is WEAK**: 2.81× at 1.5 % recall, cluster-level ≤ 1.35 ×, and structurally coarse (only 24/64 patterns observed, so percentile thresholds degenerate). **The conjunction is NOT established** — seed-42 gave 11.57×/81 % precision but n=3 is 1.73–11.57× / 0.12–0.81; caught before publication. ⚠️ Growth substantially measures CIC-IDS2017's scripted attack windows — mandatory caveat. **Emerging-pattern rule = growth only.** |
| **KG "temporal decay" time axis** | ✅ **DECIDED 2026-08-03 (user) — KEEP IT ADAPTIVE.** | The paper split is stratified-random across all 5 days, so there is no train→test time arrow — but `meta_{train,val,test}.csv` carry **real CIC-IDS2017 timestamps**, row-aligned. **Decision: keep the adaptive/decay mechanism**, with time defined as **flow-count position in timestamp-sorted order within test** (already the standing default in this table: *"Decay 'time': Flow-count (reproducible)"*). Dropping decay was rejected — **"Adaptive" is in the project title** and removing it carries a write-up cost. ⚠️ **Caveat to state in any write-up:** CIC-IDS2017's attacks are *scripted into fixed windows*, so temporal concentration is partly an artifact of the capture schedule, not purely an intrinsic property of the attacks. Report it as such. |
| ~~**Run a significance test before citing CNN vs LTN control?**~~ | ✅ **DONE 2026-08-03** | `scripts/significance.py`. Verdict: **the CNN does beat the control** (+0.0204, p=0.001, paired bootstrap over flows). ⚠️ Flow-level only — seed-level significance needs n≥6 and is *not* achievable at n=3 (Wilcoxon floor p=0.25). Also reversed the "CNN beats XGBoost" retraction (p=0.80, n.s.). |
| **Multi-seed the remaining n=1 channels?** | ⬜ **NEW — raised 2026-08-03** | Now that `BASELINE_SEED` exists and multi-seeding overturned a thesis claim once, the remaining single-seed artifacts are a known risk. XGBoost is deterministic (no action possible without changing its config). Candidates: the LTN axiom variants at n=3 are done; `cnn_auxhead`, `fusion_*` are still n=1. Low cost, and this project has retracted **four** single-seed findings. |
| **Omega mode for any future LTN work** | **`ratio`** (already the code default) | Settled 2026-07-27: `fixed` collapses 2/3 seeds at ω=1.0, deterministically at ω=2.0; `ratio` eliminated the collapse at no measured cost. Do not use `fixed` without a stated reason. |

## Last Measured Results

> 🔴 **NOISE-FLOOR CAVEAT (2026-08-03).** Every figure below is an n=3 mean from a process with
> **SD 0.0222** at fixed seed. Ranges in brackets are **too narrow** — they are 3 draws, not a
> stability estimate. Treat any two channels within **~0.045 (2 SD)** of each other as
> **indistinguishable**. See "THE NOISE FLOOR".
>
> 📍 **SUPERSEDED FOR MACRO BY THE n=6 TABLE (2026-08-04).** All 7 channels were subsequently taken
> to **n=6** with consistent log-odds scoring — see
> [n=6 EVERYWHERE](#-n6-everywhere-2026-08-03--the-top-tier-is-indistinguishable). **Cite the n=6
> macro figures, not the n=3 ones below.** The table here is kept for its per-family breakdown
> (Bot / Web BF / XSS), which was not recomputed at n=6. The headline change: **CNN 0.6399 → 0.6250**
> and **LTN control 0.6194 → 0.6110**, a gap of **+0.0140 against a ~0.0256 distinguishability
> threshold** — i.e. the two are **indistinguishable**, which is what retracted C2.
>
> **Canonical results table — last updated 2026-08-02.** Supersedes the `_TBD_` placeholder that
> stood here from project start (it referenced the legacy `eval.py`/`ltn.py` pipeline, superseded
> 2026-06-18). All figures are **mean over seeds 42/43/44, log-odds scored**, on the paper-aligned
> split, with seed range in brackets. Headline metric is **macro zero-day PR-AUC** over the three
> adequately powered families (Bot n=1,956 · Web BF n=1,507 · Web XSS n=652).
> Regenerate with: `python scripts/rescore_logits.py` then read `outputs/metadata/runs.jsonl`.

| Channel | family | n | macro zd PR-AUC | Bot | Bot lift | Web BF | XSS |
|---|:---:|:---:|---|---|---:|---:|---:|
| **CNN** `cnn_paper` | A | 3 | **0.6399** [0.6353, 0.6446] | 0.0446 [0.0241, 0.0591] | 1.3× | **0.9226** | **0.9524** |
| XGBoost | A | 1† | 0.6372 *(deterministic)* | 0.0608 | 1.8× | 0.9484 | 0.9023 |
| LTN control `ltn_ctrl_w0` | A | 3 | 0.6194 [0.6029, 0.6505] | 0.0712 [0.0528, 0.0985] | 2.1× | 0.8889 | 0.8982 |
| **RandomForest** | A | 3 | 0.5995 [0.5682, 0.6235] | **0.1311** [0.0576, 0.1933] | **3.8×** | 0.8686 | 0.7987 |
| MSP | A/B | 3 | 0.5884 [0.5694, 0.6123] | 0.0448 [0.0245, 0.0591] | 1.3× | 0.8719 | 0.8485 |
| Mahalanobis | B | 3 | 0.3777 [0.3363, 0.4585] | 0.1030 [0.0413, 0.1467] | 3.0× | 0.5840 | 0.4462 |
| **Autoencoder** `autoencoder_paper` | B | 3 | 0.0970 [0.0894, 0.1014] | **0.1314** [0.1078, 0.1647] | **3.8×** | 0.1048 | 0.0547 |
| IsolationForest | B | 3 | 0.0653 [0.0628, 0.0683] | 0.0637 [0.0571, 0.0732] | 1.9× | 0.0862 | 0.0459 |

*(A) trained on known attacks · (B) trained on benign only.*

† **XGBoost is deterministic here, so n=3 would be meaningless.** Seeds 42/43/44 produce
**byte-identical** score arrays: no subsampling is configured (`subsample`/`colsample_*` default to
1.0) and `tree_method="hist"` is deterministic, so `random_state` has no stochastic component to
control. Treat this as **n=1 with verified reproducibility**, *not* as a 3-seed estimate — its
training-time variance is **unmeasured**, not zero. To measure it you would need to enable
subsampling or bootstrap the training data.

> ✅ **All baselines were re-run on 3 seeds and the current metric schema on 2026-08-03**
> (`BASELINE_SEED=42/43/44 python scripts/baselines.py`), closing the long-standing "n=1 and old
> schema → not citable" gap. Doing so **overturned a thesis-level claim** — RandomForest's Bot score
> ties the autoencoder's. See "🔴 THE (A)/(B) FRAMING IS FALSIFIED IN ITS STRONG FORM".
> ⚠️ **RandomForest's Bot range [0.0576, 0.1933] is the widest in the table** — a 3.4× spread, and
> its cross-seed Bot rank correlation is 0.068 (noise). Quote the mean only with the range.

**Established comparative findings:**

| claim | status | evidence |
|---|---|---|
| **The CNN's Bot failure is representational, not informational** | ✅ **established 2026-08-03** | 100% argmax=BENIGN (all 3 seeds) · 0/8 feature overlap with the known-class task · cross-seed Bot rank ρ = **−0.090** vs 0.68–0.83 elsewhere · oracle PR-AUC 0.9988 rules out an information limit |
| Web attacks transfer by **absorption into DoS slowloris**, not by detection | ✅ established 2026-08-03 | 89.8% / 92.9% modal-class assignment, stable across 3 seeds |
| CNN vs Autoencoder is a **double dissociation** | ✅ **established + significant** | paired bootstrap: Bot −0.0868, Web BF +0.8178, XSS +0.8977, all p<0.0005 |
| Every LTN axiom variant costs macro vs the no-axiom control | ✅ established | non-overlapping ranges, n=3 |
| ~~"The neural baseline beats the LTN control"~~ | 🔴 **RETRACTED 2026-08-03 (controlled)** | The +0.0204 gap is **0.9 SD** of the measured noise floor (SD 0.0222) — smaller than re-running one model twice. The p=0.001 bootstrap treated each run's score as exact; re-running moves it up to 0.062. **A flow-level test cannot rescue a delta below the pipeline's own reproducibility.** |
| "**Only (B) methods reach Bot**" / "the problem is structurally (B)" | 🔴 **RETRACTED 2026-08-03** | RandomForest (A-family) ties the AE on Bot: 0.1311 vs 0.1314, p=0.88 — while beating it 0.50 on macro |
| "Monotonic frontier — no channel sits at both ends" | 🔴 **RETRACTED 2026-08-03** | RF sits at both ends (Bot 0.1311 *and* Web BF 0.8686) |
| "On macro the CNN beats XGBoost" | 🔴 **RETRACTION REVERSED** | +0.0027, CI [−0.0161, +0.0217], p=0.80 → n.s. The original *"XGBoost ≈ CNN"* claim stands; retracting it in 2026-07-27 was premature |
| "Ax6 roughly doubles Bot lift" | 🔴 **retracted** | single-seed artifact; control's own mean lift is higher |
| **Training is not reproducible at fixed seed** | ✅ **established 2026-08-03** | 6 runs of seed 42, identical code: SD **0.0222**, range **0.0621**, CV 3.6%. No TF determinism flags are set. |
| "cnn_paper = 0.6446" as the CNN's score | ⚠️ **misleading** | it is the **max of 11 runs** (mean 0.6217). Honest reproducible baseline = **ensemble 0.6356**. |
| Every n=3 range quoted in this document | ⚠️ **artefact** | the "tight" 0.0093 CNN spread is **0.4 SD** — less than half a single re-run's noise. |
| "Mahalanobis 4.3× — best Bot channel" | 🔴 **retracted** | seed 42 only; n=3 mean is 3.0×, seed 44 at chance |
| "Bot forms a stable ~90%-pure cluster" | 🔴 **retracted** | varied clustering seed, not CNN seed; 87.9/86.6/**44.4**% across CNN seeds |
| KG cluster **growth rate** detects zero-day | ✅ **established 2026-08-03** | lift **5.94x** [5.66, 6.11] n=3 clustering seeds, ~81% recall. ⚠️ substantially measures CIC-IDS2017's scripted attack windows |
| KG "unexplained cluster" detects zero-day | 🔴 **refuted 2026-08-03** | lift <= 1.00x (at or below chance) across 3 representations x 3 thresholds |
| KG behaviour **co-occurrence** detects zero-day | 🔴 **refuted 2026-08-03** | flow-level 2.81x at 1.5% recall; cluster-level <= 1.35x; only 24/64 patterns observed so thresholds degenerate |
| "growth AND co-occurrence gives 81% precision" | 🔴 **NOT established — caught pre-publication** | seed-42 artifact; n=3 lift range [1.73, 11.57], precision [0.122, 0.814] |
| "The AE is a better Bot channel than Mahalanobis" | ✅ **established 2026-08-03** | +0.0284, CI [+0.0227, +0.0339], p<0.0005 (previously "ranges overlap, not established") |

## Session Log Pointer

Dated change history lives in [CHANGELOG.md](CHANGELOG.md). Bugs/risks live in [KNOWN_ISSUES.md](KNOWN_ISSUES.md).

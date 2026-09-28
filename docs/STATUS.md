# Project Status (Living Document)

> **Update this file at the end of every working session.** It is the single source of truth for "where are we right now." Last updated: **2026-09-28**.

## ▶ RESUME HERE (next session)

> **Restructured 2026-09-28.** Every dated session section (2026-06-18 → 2026-09-28, 3,699 lines) now
> lives verbatim in [archive/STATUS_history_to_2026-09-28.md](archive/STATUS_history_to_2026-09-28.md).
> This file keeps **state only**: this section, then the canonical tables. When a session ends, replace
> this section's body with the new state and move the old body to the archive — do not let history
> accumulate above the tables again. Section names cited from scripts ("THE FUSION WALL", "PHASE 3
> RESULTS", …) resolve in the archive.

**Where the project is.** Phases 0–4 done · Phase 5 done except the fitted fuser · Phase 7.5 Tiers 1–2
done · Phase 7 (paper) drafted and built in three versions · Phase 6 (2018) partially run · Phase R not
started. Nothing in the architecture beats the deterministic CNN baseline (0.6299); the paper is the
exogeneity-precondition negative result. **ICC 2027 deadline: 2 Oct 2026.**

### 2026-09-28 — what changed

1. **Host-window view built and measured** (another session, PR #93): 0 of 8 window features pass the
   marginal exogeneity threshold (R² 0.51–0.87 without `Destination Port`), the window channel reaches
   Bot at 1.42×, and conformal min-p fusion loses to its best channel by −0.0745 on 3 of 3 seeds.
   A second conformal step does deliver a requested FPR (1 % → 0.96–1.12 %).
2. **The marginal exogeneity test was the wrong instrument** (`exogeneity_residual.py`, pre-registered,
   **R2 on both views**). Knowledge adds evidence through its residual W − E[W|X]; the residual reaches
   Bot at 3.6–6.0× (host-role) and 4.9–7.4× (window, against 1.3–1.5× raw).
3. **Its signal is identity and X, not host behaviour** (`exogeneity_residual_controls.py`, pre-registered,
   **K0 on 3 of 3 seeds**). Every external attack shares NAT address 172.16.0.1, so the host-role
   residual is an attacker-identity proxy. Same host, same time (1,255 Bot vs 2,075 benign): residual AUC
   0.672 / 0.785 / 0.700 vs **X-only 0.931 / 0.936 / 0.946**; the residual's Bot lift comes from the C2
   server (701 flows, AUC 0.96–0.97). Secondary, not pre-registered: the CNN scores 0.709 / 0.277 /
   0.223 on that same comparison.
4. **Low-data axiom test** (`ltn_lowdata.py`, pre-registered L1/L2): **L1 — the axioms do not help when data is scarce either.** On the
   70,384-flow `paper_subsampled` split (12.6× smaller, canonical test set), paired deltas +0.0143 /
   −0.0861 / −0.0796, mean −0.0505, 1 of 3 seeds positive. The control's seed SD at this size is 0.0560,
   so the magnitude is uncertain; the direction shows no benefit. Secondary, not pre-registered: the
   axioms hold 0.2399–0.2424 on every seed (SD 0.0013) — a strong regulariser, at a level below the
   control's mean.
5. **Paper corrected.** §6 now rests on the conditional test; "a stronger predictor could only make the
   conclusion stronger" is struck in the master draft and guarded by `verify_draft.py`. §3 gains the
   data-processing-inequality framing [19]; Flood et al. [18] added. ICC cut still 6 of 6 pages (two
   paragraphs whose content survives elsewhere were dropped). All three LaTeX builds regenerated.
6. **Latent bug fixed:** `rescore_logits.py` ignored `PAPER_SUBDIR` (scaler always fitted on the
   canonical split). No recorded result used that path.
7. **Documentation debt paid:** `CLAUDE.md` 520 → ~345 lines (history archived, four stale claims
   struck), `AGENTS.md` is a pointer, this file restructured, roadmap spine marked superseded, two new
   lint checks (`onboarding-stale-claims`, `onboarding-single-source`).

### Next

1. **D6 names only** — confirm author names, order and affiliation (ICC is not blind; D7 answered:
   6 pages hard). Then build with `md_to_latex.py --ieee docs/target/ieee/paper_ieee_short.md --pages 6
   --authors --compile`, register every co-author on EDAS exactly as in the PDF, submit by 2 Oct.
2. ~~Read both IEEE PDFs end to end as a reviewer~~ ✅ done 2026-09-28 for the ICC PDF: four defects
   fixed ("Section Section", a §8 opener promising a dropped paragraph, a reference without its arXiv
   id, a doubled "and").
3. If the work continues past ICC: an exogenous-knowledge experiment needs a capture that ships an asset
   inventory or topology — CIC-IDS2017 cannot supply one, now shown by a sound test.

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
| Paper-aligned split | ✅ Working — ⚠️ **not grouped, not chronological (2026-09-16)**; ✅ variants measured 2026-09-17 | `scripts/preprocess_paper.py`, `scripts/split_variants.py` | **D4 (2026-09-17):** grouped split costs the CNN **0.071** (0.5589; web families), chronological 0.028 but halves the AE (0.0455); double dissociation keeps its direction everywhere. `SPLIT_MODE=grouped` / `chronological` build `paper_grouped` / `paper_chrono` (random stays byte-identical). ⚠️ `split_integrity.json`: **54.88 %** of test flows share a 5-tuple with train (100 % for all Web Attack zero-day families), **100 %** of test lies inside the train time range, benign removed **4.11×**, 17.02 % exact duplicates. "Paper-inspired", not a replication of Bizzarri's balancing. 9 known classes stratified 80/10/10, benign under-sampled 1:1. Train 883,796 / val 110,475 / test 114,658. Leakage-verified. |
| **CNN + embeddings (neural pillar)** | ✅ **Verified correct — re-based 2026-09-16** | `scripts/cnn_paper.py` | **Deterministic: macro 0.6299** (0.6298 / 0.6269 / 0.6330, `c4_log1p_s42-44`). ~~**macro 0.6399 [0.6353, 0.6446]**~~ is the pre-flag population and must not be pooled with it, log-odds scored. Multi-seed via `CNN_SEED`. Named `"embedding"` layer feeds novelty + KG. Minor: double class-weighting ([cnn_current.md](implementation/cnn_current.md)). |
| Classical baselines | ✅ **n=3 (2026-08-03)**; ✅ **tuned on validation 2026-09-17** | `scripts/baselines.py`, `scripts/baselines_tuned.py` | **Tuned (F-12):** XGBoost 0.6180, RandomForest **0.6407** (≈ det CNN 0.6299; Bot 0.2196), IsolationForest 0.0564. XGBoost / RandomForest / IsolationForest. Multi-seed via `BASELINE_SEED`. Previously n=1 **and** on the pre-2026-07-27 metric schema (no macro logged) — both fixed; see "Last Measured Results". |
| Novelty channels | ✅ **n=3**, both populations | `scripts/novelty.py`, `scripts/ood_scores.py` | **2026-09-18 (4.4):** on the deterministic CNN (`NOVELTY_CNN=c4_log1p_s*`) MSP **0.5865**, Mahalanobis **0.4127**; Mahalanobis Bot lift still spreads 1.9–4.3× across seeds. **2026-09-17:** the OOD battery re-run on the deterministic CNN (`OOD_POPULATION=det`): best Bot scorer 0.0576 (< 0.08 pre-set). ~~Mahalanobis not yet re-derived on it.~~ MSP macro 0.5884, Mahalanobis 0.3777. Post-hoc on a trained CNN, no retraining. ⚠️ "Mahalanobis 4.3× on Bot" is **retracted** (seed 42 only); n=3 mean **3.0×**, seed 44 at chance. |
| Behaviour abstraction | ✅ Rebuilt & validated | `scripts/behavior.py` | Verified indices, vectorised, fuzzy [0,1], thresholds saved. **7 behaviours** incl. `BeaconLike` — 🔴 **oracle-informed (2026-09-16, F-08): selected on Bot (zero-day) labels; fires on 99.95 % of Bot because the capture's C2 uses 8080.** ⚠️ **Wired into LTN as Ax3–Ax6 since 2026-07-27.** ⚠️ Its validation tables were measured on the *temporal* split where PortScan/DDoS were zero-day — under the current protocol both are **known**, so "PortScan/DDoS strongly covered" is **not** evidence for the symbolic approach. `RepeatedConnections` is constant 0.0 (unblocked but unwired). See [doc](implementation/behaviour_abstraction_current.md). |
| Metrics / tracking infra | ✅ Working | `scripts/metrics.py`, `tracking.py` | Headline = **macro** zero-day PR-AUC over powered families (n≥100); detects float32 saturation; appends to `runs.jsonl` (now version-controlled, see KNOWN_ISSUES). **2026-09-16:** `evaluate(thr=...)` accepts a validation-derived threshold (F-07; on the CNN it moves achieved test FPR to 1.06 %), and every run records `scoring`. |
| **Tests** | ✅ **NEW 2026-09-16 — 37 tests (2026-09-17)** | `tests/` | `python -m unittest discover -s tests -v`. Leakage-boundary invariants, pinned split defects, the `metrics.evaluate` contract, the records the paper cites, and `verify_draft.py` in both modes. The project had none before. |
| LTN reasoning (paper-split) | 🟡 Anatomized, multi-seeded — macro cost confirmed, Bot benefit retracted | `scripts/ltn_paper.py` | Clean (log-odds) control macro 0.6049 (n=1) / 0.6194 (n=3 mean); every axiom variant tried (old Ax3-5, targeted Ax6) costs macro relative to control, robust across seeds. ω=2.0 always collapses; ω=1.0 collapses 2/3 seeds — not the "safe zone" it looked like on n=1. Ax6's apparent Bot-lift improvement did not survive multi-seeding (control's own Bot lift ranges 1.5–2.9x). See "🔴 MULTI-SEED RESULTS" in the [archive](archive/STATUS_history_to_2026-09-28.md) for the full table + retraction. **2026-09-28, low data (`ltn_lowdata.py`, L1):** on the 12.6× smaller `paper_subsampled` split the axioms still do not help (paired +0.0143 / −0.0861 / −0.0796); they cut seed SD to 0.0013 but hold the score below the control's mean. Fix alongside: `ltn_paper.py` and `rescore_logits.py` now log/honour `PAPER_SUBDIR`. |
| **Anomaly pillar (autoencoder)** — canonical **Phase 3** | ✅ **Built, run & multi-seeded 2026-08-02 — n=3**; deterministic n=3 2026-09-17 | `scripts/autoencoder_paper.py` | **Deterministic (`ae_det_s42-44`): macro 0.0985, Bot 0.1338** — the pre-flag figures below are a different population. Benign-only reconstruction error; **zero attack labels used in training *or* model selection**, so it is zero-day-legitimate by construction. **macro 0.0970 [0.0894, 0.1014]** · **Bot 0.1314 (3.8×) — the best Bot channel measured** · loses on web attacks (0.1048 / 0.0547). Establishes the **double dissociation** vs the CNN. Multi-seed via `AE_SEED`. ⚠️ Its first-day interpretation (a "modality analogue" mechanism) was **falsified the same day**; the *pattern* is real, the *explanation* is open — see "PHASE 3 RESULTS". |
| **Knowledge Graph** — canonical **Phase 4** | 🟢 **BUILT & multi-seeded 2026-08-03** — 🔴 **fusion gain withdrawn 2026-09-16** | `scripts/kg.py` (class in `kg_graph.py`) | 🔴 **As a fusion partner its gain belongs to three CNN runs (`fusion_population.py`); its standalone and explanation results stand.** 215 nodes / 1,183 edges on **raw-feature** clusters (CNN embeddings and the AE bottleneck were both measured and rejected). Adaptive decay over true chronological order. **s_kg causal: macro 0.2488, Bot 0.3103 — best Bot channel measured.** Scope is corroboration + explanation: the spec's "unexplained cluster" detector is measured dead (≤1.00×). ⚠️ Mandatory lateness control lives in the script — a trivial "later in the week" baseline scores Bot 0.1575. Viz: `kg_visualize.py`. |
| Decision Fusion — Phase 5 | 🟡 Partial — ~~parameter-free CNN+KG fusion beats the CNN~~ **withdrawn 2026-09-16** | `fusion_kg.py`, `fitted_fusion.py` | The fitted CNN+AE combiner (+0.0103, 0.80σ) is measured on the same three reference CNN runs and is **not re-tested**. ⚠️ A **fitted** combiner is structurally blocked — validation contains no zero-day by construction, so it cannot learn to weight a zero-day-specific channel (`fusion_beaconlike.py` → `[2.35, 0.02]`). See "THE FUSION WALL". Spec: [decision_fusion.md](target/decision_fusion.md). |
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
| 4 | Decision Fusion — canonical Phase 5 | 🟡 **PARTIALLY DONE — entered without being scheduled** | ⚠️ **Scope note (2026-08-03):** Phase 5 is *"Fusion + rigor (seeds, significance, calibration, latency)"*, and parts of it were done while answering other questions rather than as a planned phase start. **Done:** `significance.py` (paired bootstrap) · `fusion_kg.py` + `fusion_multi.py` (parameter-free rank fusion, ~~**+0.0527 macro, p<0.001** — the first result to beat the CNN baseline; direction established on 3/3 seeds, **magnitude uncertain 0.027–0.088**~~ 🔴 **withdrawn 2026-09-16**: three reference CNN runs; 5 of 11 pre-flag, 0 of 6 deterministic — `fusion_population.py`; *struck 2026-09-28, this row had not been updated*) · **n≥6 seeds ✅ DONE 2026-08-04** (`rigor_n6.sh`, all 7 channels — and it showed the top tier is mutually **indistinguishable**). **Also done:** ✅ **calibration** — delivered 2026-08-05 by `operational.py` (Tier-1 item 2); this row said "NOT done" for a month, see the drift note above. ⚠️ scalar ECE per subset is persisted, per-bin reliability curves are not. ✅ **latency** — 2026-09-05, `latency.py`. **STILL NOT done:** the *fitted* Decision Fusion the spec actually describes (blocked by THE FUSION WALL — the deliverable is to write the blocker as a result). Spec: [decision_fusion.md](target/decision_fusion.md). |
| 5 | **Explainability / Final Alert — the REST of canonical Phase 4** | ✅ **DONE 2026-08-03 — 3 of 3 + faithfulness** (`explain.py`) | ✅ Neural (Integrated Gradients, completeness-checked) · ✅ Logic (per-axiom SAT, Ax3–Ax6 only — Ax1/Ax2 are label anchors and would be circular) · ✅ KG reasoning paths · ✅ Final Alert assembly · ✅ Tier-A faithfulness (IG top-3 masking is **20.67×** a random-feature control; sufficiency reported as the weaker half). **Phase 4 is therefore complete.** Its most informative output is not a score: on a Bot flow the CNN calls benign, **both other pillars dissent** — no single-pillar system produces that. Spec: [explainability.md](target/explainability.md). |
| 6 | Ablation (CNN → +LTN → +KG → full) | ✅ **DONE 2026-08-05** (`ablation.py`) — 🔴 **KG rung withdrawn 2026-09-16** | 🔴 **Result is negative: ~~only the KG earns its place~~ nothing earns its place** — the KG rung's gain belongs to the three reference CNN runs (`fusion_population.py`). The symbolic pillar adds nothing alone (−0.0004, n.s.) and ~~**significantly hurts stacked on the KG** (0.6926 → 0.6708, p<0.0001)~~ *(withdrawn 2026-09-17 — built on the withdrawn three-run fusion; the matched comparison is: worse than the no-axiom trainer in all 17 pairings, `ablation_population.py`)*. See the ablation section (archive). |
| 8 | **Method comparison tiers A/B/C/D** | ✅ **DONE 2026-08-05** | `baselines_classic` (7 classic) · `anomaly_zoo` (4 benign-only) · `deep_zoo` (4 deep) · `protocol_variance` (k-fold + SWA) · `ood_scores` (open-set battery). **Nothing rescued Bot** (best 0.0626 vs the KG's 0.3103). **Only the conv front-end matters** among deep architectures. ⬜ **Follow-up: multi-seed Deep SVDD and the Tier-A Bot column — both n=1.** |
| 7 | **Phase 7.5 — OPERATIONAL READINESS (intermission, after the paper)** | ✅ **TIER 1 + TIER 2 DONE 2026-08-05** — `operational.py`, all 4 predictions confirmed. **GATES PHASE R** | See the dedicated section below. Four Tier-1 items that decide whether automated response is *safe*, plus three noise-reduction items. **PR-AUC is the wrong target for a response engine** — it summarises ranking across all thresholds, while the engine acts at ONE. |

| 9 | **Audit remediation (2026-09-16)** | ~~🟡 **Stages 1–3 done, Stage 4 mostly done, Stages 5–8 partly**~~ ✅ **COMPLETE 2026-09-18** (row not updated until 2026-09-28; the notes below are the 2026-09-16 plan) | Branch `fix/audit-remediation`, **not pushed**. Plan: `REMEDIATION_ITINERARY.md`. **Waiting:** `audit_rebase.sh` (CL-02 control + seed-42 byte-identity). **Blocked on the author:** D1, D3, D4, D5 and the §6 reframe. **Not done:** 5.1/5.2 grouped and chronological splits (D4), 6.1 tuning-matched baselines, 6.4 evasion experiment (optional), 6.5 view 5 on the X-Attempted variant, 7.4 end-to-end `run_all.py --run`, 8.1 notebook (D3). **Stale records to regenerate** when the CPU is free: `significance.json` (Holm now in code). |

Enhancement backlog (not scheduled): [enhancements.md](target/enhancements.md).

## 🧭 PHASE 7.5 — OPERATIONAL READINESS (intermission, planned 2026-08-03)

**Sits between Phase 7 (paper) and Phase R (response engine), and gates Phase R.** ~~Not started.~~ ✅ **Tiers 1 and 2 done 2026-08-05** (`operational.py`); Tier 3 deferred. *(Corrected 2026-09-28.)*

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
| 🔴 **D1 — benign under-sampling (audit F-04)** | ~~⬜ OPEN 2026-09-16~~ ✅ **DECIDED 2026-09-17: keep 1:1, report both** (0.6299 at 1:1; 0.5845 at the capture's own proportion) | It is deliberate and matches Bizzarri; its unstated effect is that every absolute PR-AUC is measured at a 4.11× inflated attack base rate (det CNN 0.6299 → **0.5845** at capture prevalence). Recommendation: keep the split and report both columns. |
| 🔴 **D3 — the notebook** | ~~⬜ OPEN 2026-09-16~~ ✅ **DECIDED 2026-09-18: not the deliverable** — kept private and gitignored | `Capstone_final (4) (1).ipynb` (untracked) is a second pipeline whose zero-day set is the **base paper's** (PortScan held out, Infiltration trained). Is it the capstone deliverable? If yes: track + re-execute; if not: archive with a banner. |
| 🔴 **D4 — grouped and chronological splits (audit F-02/F-03)** | ~~⬜ OPEN 2026-09-16~~ ✅ **RUN 2026-09-17** — grouped −0.071, chronological halves the AE, the dissociation holds | 54.88 % 5-tuple overlap, 100 % temporal overlap. ~2 days CPU to measure. Recommendation: run them, at least as a measured limitation. |
| 🔴 **D5 — push the audit branches?** | ~~⬜ OPEN~~ ✅ **DECIDED 2026-09-18: five sequential PRs** (#83–#87), each merged locally `--no-ff` | `docs/paper-revision` and `fix/audit-remediation` are local only; the repository is public. |
| 🔴 **Reframe the paper after the fusion withdrawal?** | ~~⬜ OPEN 2026-09-16~~ ✅ **DONE 2026-09-17** ("go ahead with it"): the paper is framed around the precondition, with no positive fusion claim | The paper's one positive result is gone. Option A: reframe §6 and the contribution list around "nothing beats the neural baseline, and here is why" (the thesis predicts it). Option B: look for a fusion that is stable across CNN runs (e.g. fuse with an ensemble or with calibrated scores rather than whole-set ranks) — but the 11-run ensemble already fused *worse*. Recommendation: A. |
| 🔴 **D6 — author list and blind review for the IEEE versions** | 🟡 **HALF ANSWERED 2026-09-28: ICC 2027 is NOT blind** — the PDF's author list and title must exactly match the EDAS registration (icc2027.ieee-icc.org/submission-guidelines), so the anonymous build is non-compliant for submission. **Still open: confirm names, order and affiliation.** The named build (`--authors`) is 6 of 6 pages. | The PDFs build anonymous by default; `md_to_latex.py --ieee ... --authors` fills the block from `AUTHORS`, taken from the weekly report (four PES University students; guide not listed). Confirm names, order, affiliation and whether ICC 2027 review is blind before any camera-ready build. |
| ~~🔴 **D7 — ICC 2027 page limit**~~ | ✅ **ANSWERED 2026-09-28 (official guidelines):** initial submission **6 printed pages, 10-pt, hard** (longer is rejected without review); only an *accepted* paper may add pages 7–8 at US$100 each. Deadline **2 Oct 2026** (EDAS, CISS symposium). Our build: 6 of 6 including references. | Built to 6 pages including references (the usual ICC limit). Confirm from the ICC 2027 author kit, including whether a paid extra page is allowed; the 7-page full version is ready if so. |
| ~~D2 — was `BeaconLike` chosen before or after the Bot measurement?~~ | ✅ **ANSWERED 2026-09-16** | After — commit 8c9e40f designed it on Bot and validated it against Bot labels. Relabelled oracle-informed in code and paper. |
| KG backend | NetworkX | If scale demands, → Neo4j |
| Fusion mechanism | Fixed weights (Phase 1) → logistic (Phase 2) | After KG exists |
| 🔴 **Input modality — add payload / raw PCAP?** | ✅ **DECIDED 2026-09-05 — NO. Flow-feature CSVs stand; payload is out of scope, not deferred-and-desirable.** | **Settled by a measurement already in the record.** The H4 oracle probe (`bot_failure_analysis.py`, `outputs/metadata/bot_failure_analysis.json`) separates every adequately-powered zero-day family from benign **using the 68 flow features alone** — **Bot 0.9988 · Web BF 0.9999 · XSS 0.9984** PR-AUC. There is no missing information for payload to supply, so the Bot gap (oracle 0.9988 → CNN 0.0321, chance 0.0342) is **100 % a closed-set-supervision gap and 0 % a modality gap**. ⚠️ **The mechanism is basis-agnostic**: H3 shows Bot's oracle top-8 has **0/8 overlap** with the known-class task's (Web BF 1/8), and a closed-set model on payload bytes would select payload features separating the same nine classes — **relocating the failure, not removing it**. Corroborated by the base paper, which **is** the payload version: Bizzarri et al. use 1500 payload bytes and we beat them ~~18–29 pp on all four known-class views~~ **+18.8 / +0.4 / +28.7 / +7.1 pp on the four known-class views** *(corrected 2026-09-16, CL-01)* while their 1D CNN's zero-day number matches ours (**48.34 % vs 47.85 %** — ⚠️ *qualified 2026-09-16, FD-02: measured on differently filtered populations. They delete payload-less records, which is structurally Engelen's `X - Attempted` filter that collapses our Web BF from 0.8861 to 0.0072. This corroboration is weaker than it reads; the H4 oracle argument above stands on its own*) — payload costs known-class performance and buys nothing on zero-day. **Where payload would genuinely help is the wrong place**: it would replace the web families' *absorption* (~90 % assigned to `DoS slowloris`) with real detection — an honesty gain, not a metric one, since Web BF/XSS already score 0.91–0.95 and **all the headroom is in Bot, where payload adds no information**. Costs if ever revisited: ~48 GB of PCAP not held locally, packet→flow alignment through the one field with two documented defects (D/M/YYYY, 12-hour no AM/PM), a new header/User-Agent leakage surface `audit_leakage.py` does not cover, plaintext-2017 ecological validity, and a **forked record** — the noise floor, ablation, double dissociation and field-metric gap are all defined on the 68-feature basis. **Revisit only** for basis-independence of the mechanism (does 0-overlap → ρ≈0 reproduce on payload bytes?), which is a separate paper, not a Phase-5 task. |
| "Hard" vs soft axioms | Soft (SAT loss) + optional inference guard | During LTN rework |
| KG clustering | Static (fit once on train embeddings) | If drift observed |
| Decay "time" | Flow-count (reproducible) | — |
| Compute (CPU vs GPU) | **CPU** (Ryzen 9 9950X3D) | GPU (RTX 5080/Blackwell) deferred — needs WSL2 + CUDA 12.8 + newer TF + Keras 3 migration. Revisit if training volume grows (multi-seed/sweeps/cross-dataset). |
| ~~Run the Phase-3 autoencoder before the KG?~~ | ✅ **DECIDED & DONE 2026-08-02** | Ran it (n=3). Verdict: worth it. It answered the reviewer objection *and* produced the double-dissociation result, retracted "Mahalanobis 4.3×", and exposed the Phase-4 blocker. The prediction that its result was "genuinely unpredictable" held — it beat the CNN on Bot and lost 6.6× on macro. |
| 🔴 **Which representation should the KG cluster?** | ✅ **MEASURED 2026-08-03 → recommend (b) RAW FEATURES.** Awaiting sign-off. | **Clustering purity is now measured for all options** (`kg_readiness.py`), and it **overturned the lean recorded here earlier the same day.** (a) ensemble CNN seeds — ❌ futile: ~~the CNN's Bot ranking is noise (ρ=−0.090); averaging noise creates no signal~~ *(reason retracted 2026-09-17 — Bot's median cross-run ρ is +0.55 / +0.59; the decision for raw features stands on the purity numbers alone)*. (b) **raw features — ✅ RECOMMENDED**: Bot purity **77.6 % (k=200) / 80.6 % (k=400)**, competitive with the CNN's good seeds and far above its worst (44.4 %), with **no training lottery** (residual k-means seed sensitivity ~2.6 pp). (c) AE bottleneck — 🔴 **WAS the lean, now REJECTED**: measured Bot-purity spread **52.1 pp**, the *worst* of all options, because **rank stability ≠ cluster stability** — the AE orders Bot flows consistently (ρ=0.827) but its 16-d geometry still scatters them across seeds. (d) accept-and-publish — unnecessary now that (b) exists. |
| 🔴 **Is the KG a primary detector or corroboration?** | ✅ **RESOLVED EMPIRICALLY 2026-08-03 → corroboration.** | The spec contradiction (`knowledge_graph.md` "primary zero-day signal" vs `conference_roadmap.md` "corroboration, not primary detector") is settled by measurement, not preference: the "unexplained cluster" criterion scores **lift ≤ 1.00× — at or below chance — across 3 representations × 3 thresholds.** The primary-detector path is dead. **The roadmap was right.** |
| ~~**Do the KG's other two emerging-pattern criteria work?**~~ | ✅ **MEASURED 2026-08-03 — 1 of 3 works. Gate closed.** | `kg_criteria.py`. **Growth/burstiness WORKS and is robust**: lift **5.94×** [5.66, 6.11] n=3, ~81 % recall. **Co-occurrence is WEAK**: 2.81× at 1.5 % recall, cluster-level ≤ 1.35 ×, and structurally coarse (only 24/64 patterns observed, so percentile thresholds degenerate). **The conjunction is NOT established** — seed-42 gave 11.57×/81 % precision but n=3 is 1.73–11.57× / 0.12–0.81; caught before publication. ⚠️ Growth substantially measures CIC-IDS2017's scripted attack windows — mandatory caveat. **Emerging-pattern rule = growth only.** |
| **KG "temporal decay" time axis** | ✅ **DECIDED 2026-08-03 (user) — KEEP IT ADAPTIVE.** | The paper split is stratified-random across all 5 days, so there is no train→test time arrow — but `meta_{train,val,test}.csv` carry **real CIC-IDS2017 timestamps**, row-aligned. **Decision: keep the adaptive/decay mechanism**, with time defined as **flow-count position in timestamp-sorted order within test** (already the standing default in this table: *"Decay 'time': Flow-count (reproducible)"*). Dropping decay was rejected — **"Adaptive" is in the project title** and removing it carries a write-up cost. ⚠️ **Caveat to state in any write-up:** CIC-IDS2017's attacks are *scripted into fixed windows*, so temporal concentration is partly an artifact of the capture schedule, not purely an intrinsic property of the attacks. Report it as such. |
| ~~**Run a significance test before citing CNN vs LTN control?**~~ | ✅ **DONE 2026-08-03** | `scripts/significance.py`. Verdict: **the CNN does beat the control** (+0.0204, p=0.001, paired bootstrap over flows). ⚠️ Flow-level only — seed-level significance needs n≥6 and is *not* achievable at n=3 (Wilcoxon floor p=0.25). Also reversed the "CNN beats XGBoost" retraction (p=0.80, n.s.). |
| **Multi-seed the remaining n=1 channels?** | ⬜ **NEW — raised 2026-08-03** | Now that `BASELINE_SEED` exists and multi-seeding overturned a thesis claim once, the remaining single-seed artifacts are a known risk. XGBoost is deterministic (no action possible without changing its config). Candidates: the LTN axiom variants at n=3 are done; `cnn_auxhead`, `fusion_*` are still n=1. Low cost, and this project has retracted **four** single-seed findings. |
| **Omega mode for any future LTN work** | **`ratio`** (already the code default) | Settled 2026-07-27: `fixed` collapses 2/3 seeds at ω=1.0, deterministically at ω=2.0; `ratio` eliminated the collapse at no measured cost. Do not use `fixed` without a stated reason. |

## Last Measured Results

> ✅ **2026-09-28 — exogeneity tested conditionally, and low-data axioms.** All pre-registered, three seeds.
>
> | test | verdict | numbers |
> |---|---|---|
> | residual reaches zero-day? (`exogeneity_residual.py`) | **R2**, both views | host-role residual macro 0.3773–0.4656 (raw 0.2315–0.2888), Bot 3.6–6.0×; window residual 0.1792–0.2666 (raw 0.0742–0.0839), Bot 4.9–7.4× (raw 1.3–1.5×) |
> | is it behaviour? (`exogeneity_residual_controls.py`) | **K0**, 3/3 | same host + time: residual AUC 0.672 / 0.785 / 0.700 vs X-only 0.931 / 0.936 / 0.946; C2 server 0.96–0.97; CNN 0.709 / 0.277 / 0.223 (secondary) |
> | axioms with scarce data? (`ltn_lowdata.py`) | **L1** | paired +0.0143 / −0.0861 / −0.0796, mean −0.0505; axioms 0.2399–0.2424, control 0.2273–0.3285 |

> 🔴 **RE-BASED 2026-09-16 (audit F-01) — read this before any number below.** The figures below come
> from the **pre-determinism** CNN population. On the deterministic population
> (`rebase_deterministic.json`, `operational_best_c4_log1p.json`, `fusion_population.json`):
>
> | quantity | pre-flag (below) | deterministic |
> |---|---:|---:|
> | CNN macro zero-day PR-AUC | 0.6399 | **0.6299** |
> | CNN + KG k=800, online | 0.7032 (+0.0633) | **0.5030 (−0.1269, 0/3)** |
> | CNN + KG k=800, transductive | 0.7123 (+0.0724) | 0.6639 (+0.0340, 3/3; 4/6 across 6 runs) |
> | recall of unknown flows @1 % FPR, CNN / online fusion | 48.3 % / 54.6 % | **48.2 % / 46.5 %** |
> | CNN macro at capture-faithful benign prevalence | — | **0.5845** |
> | achieved test FPR with a validation-fixed 1 % threshold (CNN) | 1.00 % by construction | **1.06 %** |
>
> And across **all 11** pre-flag CNN runs, the online fusion gains in only **5**; the three reference
> runs that every number below used are the ones that gain.

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

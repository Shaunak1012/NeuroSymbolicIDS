# Changelog (Living Document)

> Append a dated entry whenever something meaningful changes (code, data, decisions, results). Newest first. Keep entries short; link to detail docs.

## 2026-08-02 (post-merge audit — found and recorded a recurring process defect)

- **Audited what `origin/main` actually serves rather than trusting the merge, and found real drift.**
  Four documents still described pre-Phase-3 state. Most seriously, **`CLAUDE.md`'s component table
  still read "Anomaly pillar: ❌ Not built — decision needed first"** after Phase 3 had been built,
  run and multi-seeded — and `CLAUDE.md` is the file auto-loaded into every session, so it was the
  worst possible place for it. `STATUS.md`'s table had been updated; this one was missed.
  Also: STATUS Open Decisions still asked "run the autoencoder?" (done), Remaining Work called the KG
  an unblocked "next build" (it is blocked), and `scripts_reference.md` documented 22 of 26 scripts.
- **Root-caused it as a process defect and tracked it, rather than just patching the symptom.**
  Component status is written out independently in 4+ files, and the end-of-session checklist said
  "flip component statuses" without naming which ones — so it is satisfied by updating whichever
  table happens to be in front of you. **The same failure has now occurred twice in two sessions**
  (2026-07-29 caught it in the target docs; 2026-08-02 in `CLAUDE.md`).
- **Recorded the fix as an actionable issue:** make STATUS's Component Status the single source of
  truth and reduce the others to pointers, keep `conference_roadmap §1b` as the canonical *phase
  numbering* table, name the exact files in the checklist, and verify with a one-line grep that
  should hit one file rather than four. **Not implemented** — flagged to be done before Phase 4
  starts changing statuses. Interim mitigation added to `CLAUDE.md`: the checklist now names all
  four files explicitly and includes the verification command.

## 2026-08-02 (Phase 3 closed out — canonical results table, docs squared, branch merged)

Housekeeping pass to leave the repository in a clean state before Phase 4 begins in a new session.

- **Established a single canonical results table** (STATUS → "Last Measured Results") and made every
  other document quote it. It replaces a `_TBD_` placeholder that had stood since project start and
  still referenced the superseded `eval.py`/`ltn.py` pipeline. All figures are **n=3 mean with seed
  range**; channels that are n=1 or predate the metrics rewrite (`xgboost`, `random_forest`,
  `isolation_forest`) are explicitly listed as **not citable for comparison** rather than quoted.
- **Added an "established vs retracted" ledger** to the same section, so the status of every
  comparative claim is visible in one place: 2 established, 1 explicitly *not* established
  (CNN vs LTN control — needs a significance test), 3 retracted.
- **Refreshed README** with the Phase-3 results, the double-dissociation finding, and a
  reproducibility note stating plainly that three findings have been retracted after multi-seeding.
  Removed the stale "Mahalanobis 4.3×" row.
- **Marked Phase 3 complete** in `conference_roadmap.md` (both the canonical phase table and the
  build-plan row, with actual vs estimated effort) and in `enhancements.md` item #1, whose stated
  purpose — answer *"why not just an autoencoder?"* — is now discharged with a number.
- **Moved smoke-test artifacts out of the fusion-channel namespace** into
  `outputs/predictions/_smoke_archive/` with an explanatory README. Moved, **not deleted**, per the
  project rule that artifacts are never destroyed. 62 real channels remain, none of them smoke.
- **Tracked the Phase-4 blocker in KNOWN_ISSUES**, which had only been recorded in STATUS — the same
  living-docs drift that made the 2026-07-29 reference-tier audit necessary in the first place.

## 2026-08-02 (Phase-4 blocker — the KG's clustering premise breaks under CNN reseeding)

- **Acted on the warning raised by the train-vs-score decomposition and it broke the pre-check.**
  Extended `scripts/kg_precheck.py` to vary the **CNN seed** (the embedding itself), not just the
  clustering seed, and re-ran.
- **🔴 RETRACTED: "Bot forms a ~90%-pure cluster, stable across 2 seeds."** The two seeds originally
  varied were **clustering** seeds on a **fixed seed-42 embedding** — that measured k-means
  stability, never the stability of the representation the KG would actually be built on.

  | k | family | purity across CNN seeds 42/43/44 | spread |
  |---|---|---|---:|
  | 200 | **Bot** | **87.9% · 86.6% · 44.4%** | **43.4 pp** |
  | 200 | Web BF | 62.4% · 64.9% · 64.8% | 2.5 pp |
  | 200 | XSS | 28.1% · 29.4% · 27.8% | 1.6 pp |
  | 400 | **Bot** | **82.2% · 91.1% · 62.7%** | **28.3 pp** |

  Varying only the *clustering* seed on a fixed embedding gives Bot 87.9% vs 90.5% — spread 2.6 pp.
  **Clustering is stable; the embedding is not.**
- **The instability is specific to Bot.** Web BF and XSS purity move 0.7–2.5 pp across CNN seeds. So
  this is not general seed-sensitivity — the CNN's embedding geometry *with respect to Bot* is a
  seed lottery.
- **Two independent measures agree on which seed is bad.** Seed 44 is worst on both cluster purity
  (44.4%) and Mahalanobis Bot PR-AUC (0.0413, 1.2× ≈ chance), while its classification is
  unremarkable (macro 0.6396 vs 0.6446/0.6353). **Classification is flat across seeds; open-set
  geometry is not.**
- **The KG's value proposition inverts:** it clusters *stably* on web attacks — which the CNN already
  handles at 0.92–0.95, so clustering adds nothing — and *unstably* on Bot, the one family where a
  memory/novelty mechanism would earn its place.
- **Does not kill Phase 4**; kills "clustering CNN embeddings is a solid foundation" as an unexamined
  assumption. Four options recorded (ensemble across seeds · cluster raw features · cluster the AE's
  16-d benign-trained bottleneck · accept and publish the variance). **None implemented, none
  decided** — the representation question should be settled before `kg.py` is written.

## 2026-08-02 (train-vs-score decomposition — and "Mahalanobis 4.3×" is retracted)

- **Added `NOVELTY_SEED` to `novelty.py`** and recomputed MSP + Mahalanobis from all three CNN seeds.
  Free — both are post-hoc functions of a trained CNN, no retraining. Seed-42 outputs reproduced
  **byte-identically**, confirming determinism and leaving the original record intact.
- **Purpose: decompose the double dissociation.** MSP and Mahalanobis are the informative middle
  cases — both computed from an **(A)-trained** model but using **(B)-style** scoring. If they
  pattern with the CNN, the dissociation is driven by *what the model is trained on*; if with the
  autoencoder, by *how the score is computed*.

  | channel | train | score | macro | Bot mean [range] | lift | Web BF | XSS |
  |---|---|---|---:|---|---:|---:|---:|
  | CNN softmax | A | A | 0.6399 | 0.0446 [0.024, 0.059] | 1.3× | 0.9226 | 0.9524 |
  | MSP | A | B | 0.5884 | 0.0448 [0.024, 0.059] | 1.3× | 0.8719 | 0.8485 |
  | Mahalanobis | A | B | 0.3777 | 0.1030 [0.041, 0.147] | 3.0× | 0.5840 | 0.4462 |
  | Autoencoder | B | B | 0.0970 | 0.1314 [0.108, 0.165] | 3.8× | 0.1048 | 0.0547 |

- **Changing the scoring function alone buys nothing.** MSP lands at Bot 0.0448 vs the CNN's 0.0446 —
  indistinguishable. So the Bot failure is *not* "the signal is there but argmax discards it."
- **The dissociation is a monotonic frontier, not a binary split.** Moving A/A → A/B → A/B → B/B, Bot
  rises (0.045 → 0.045 → 0.103 → 0.131) while Web BF and XSS fall monotonically. No channel is at
  both ends. Position on the frontier is governed mainly by **what the model trains on**.
- **🔴 RETRACTED: "Mahalanobis gets 4.3× on Bot, the best Bot channel."** Seed 42 = 0.1467 (4.3×),
  seed 43 = 0.1210 (3.5×), **seed 44 = 0.0413 (1.2×, essentially chance)**. Mean **3.0×**, best-to-worst
  spread **3.6×**. The 4.3× figure was the best of three seeds and has been load-bearing — quoted in
  the thesis reframing, README, CLAUDE.md and KNOWN_ISSUES as the headline evidence that (B) methods
  work on Bot. **Third single-seed overclaim in this project** (after Ax6 and C2). Corrected at every
  forward-looking citation; dated historical entries left intact per retract-in-place.
- **The autoencoder is the better and far more stable (B) channel:** 3.8× [3.2–4.8], spread 1.5×,
  versus Mahalanobis 3.0× [1.2–4.3], spread 3.6×. (Ranges overlap, so "AE > Mahalanobis" is not
  established — but "AE is more reliable" is.)
- **⚠️ New Phase-4 warning: the CNN's classification is seed-stable while its embedding's open-set
  geometry is not.** Across the same three seeds CNN macro moves 0.009 (0.6353–0.6446) while
  Mahalanobis-on-its-embedding swings **3.6×** on Bot. The KG is specified to cluster these
  embeddings, and the Phase-4 pre-check's "Bot forms a ~90%-pure cluster, stable across 2 seeds"
  measured **clustering stability on a fixed seed-42 embedding**, *not* stability of the embedding
  across CNN seeds. Different claims — **re-run that pre-check across CNN seeds before building on it.**

## 2026-08-02 (AE multi-seeded — the (A)/(B) complementarity is established as a double dissociation)

- **Ran autoencoder seeds 43 and 44** (`AE_SEED`, seed-42 artifacts untouched, both exit 0).
  AE n=3: macro mean **0.0970** [0.0894, 0.1014] · Bot mean **0.1314** [0.1078, 0.1647].
- **🎯 CNN vs AE ranges do not overlap on ANY family at n=3 each** — the first cleanly-established
  multi-seeded comparative result in this project. (Contrast C2, where CNN-vs-LTN-control *did*
  overlap and therefore established nothing.)

  | family | CNN (A) mean [range] | AE (B) mean [range] | winner | ratio |
  |---|---|---|---|---|
  | Bot | 0.0446 [0.0241, 0.0591] | **0.1314** [0.1078, 0.1647] | **AE** | **2.9×** |
  | Web BF | **0.9226** [0.9194, 0.9288] | 0.1048 [0.0928, 0.1168] | **CNN** | **8.8×** |
  | XSS | **0.9524** [0.9485, 0.9554] | 0.0547 [0.0468, 0.0615] | **CNN** | **17.4×** |
  | macro | **0.6399** | 0.0970 | **CNN** | 6.6× |

- **This is a double dissociation, which is a stronger claim than "method X is better."** Each method
  wins decisively where the other fails, with non-touching seed ranges — ruling out noise, "the AE is
  just weaker" (it beats the CNN 2.9× on Bot), and "the CNN is just better" (it loses on Bot while
  winning 8.8–17.4× on web attacks). **The complementarity that the falsified modality account was
  invented to explain is itself real** — the pattern survived; only the explanation died.
- **Honest scope:** both methods remain weak in absolute terms on Bot (0.13 vs 0.045, chance 0.034),
  so "AE wins on Bot" means 3.8× chance vs 1.3× chance — a robust relative difference, not a solved
  problem. And the mechanism is now **openly unknown**, which is where it should stay until measured.
- Also notable and unexplained: on the underpowered families the AE reaches **121.8×** (Infiltration)
  and **125.3×** (Heartbleed) mean lift, versus the CNN's 1.4× and 0.5×. Direction only (n=36, n=11).

## 2026-08-02 (modality test — falsifies the same-day Phase-3 interpretation)

- **Built and ran `scripts/modality_analysis.py`** to test the "modality analogue" account proposed
  hours earlier. **All four predictions were written into the script before it was run**, and the
  design deliberately guarded against circularity three ways: repeat every measurement in **raw
  feature space** (untrained by any model), report **which** known class is nearest (a named,
  falsifiable prediction), and test **per-flow** rather than across only 6 families.
- **🔴 The account was largely falsified — and the guards are what caught it.**
  - **Named mechanism wrong.** Web Brute Force / XSS do **not** sit nearest FTP/SSH-Patator (the
    claimed shared "brute-force authentication" modality). Their nearest known attack in raw space is
    **DoS Hulk — 80% and 96% respectively.** DoS Hulk is an HTTP flood, so any shared modality is
    "HTTP traffic on port 80", not brute force.
  - **Direction backwards.** Median raw distance from the benign manifold: **Bot 7.28**, Web BF 8.86,
    XSS 8.84, BENIGN 6.10, Infiltration 23.25, Heartbleed 34.25. **Bot is closer to benign than the
    web attacks are** — so "the AE catches Bot because Bot is structurally anomalous" cannot hold.
  - **The "categorical split" was a threshold artifact.** It came from recall@1%FPR (Bot 0.0082 vs
    web 0.0000 — both effectively zero). On **lift**, the AE is comparably weak across all powered
    families: **Bot 3.6×, Web BF 4.4×, XSS 5.3×** — web attacks are *higher* than Bot. The AE's
    genuinely large numbers (Heartbleed 103×, Infiltration 145×) are on the two families
    `metrics.py` excludes as underpowered (n=11, n=36).
  - **The best-looking evidence was circular.** `corr(margin, CNN−AE advantage)` = **+0.933 in CNN
    embedding space** but **−0.388 in raw space**. The embedding figure is near-tautological —
    `margin` correlates **+0.863** with the CNN's own log-odds there, restating its decision rather
    than predicting it. Discarded.
- **One prediction held, after correcting my own test design.** The AE *is* a raw-space
  distance-from-benign detector: `corr(d_benign_raw, AE error) = +0.732` on zero-day flows. My first
  pass measured this in embedding space (+0.069) — wrong geometry, since the AE reconstructs raw
  features. Both numbers recorded.
- **Net effect on the thesis:** (A)/(B) complementarity survives as an *empirical pattern*; the
  modality-analogue *explanation* for it does not, and must not go into a paper draft as a mechanism.
  The fusion/router proposal rested on that mechanism and is accordingly no longer motivated as-is.
  The open question is now sharper and more honest: **why is the CNN specifically so bad on Bot**,
  given the oracle result proves the information is present in the features?
- Corrected the Phase-3 interpretation **in place** in STATUS (red box above the original text, which
  is preserved unedited) rather than rewriting it, per the project's retract-in-place convention.
  Full numbers: `outputs/metadata/modality_analysis.json`.

## 2026-08-02 (Phase 3 RUN — the autoencoder result refines the thesis rather than confirming it)

- **Ran `scripts/autoencoder_paper.py` (canonical Phase 3).** Converged cleanly, 50 epochs, exit 0,
  zero attack labels used in training *or* model selection. **n=1 (seed 42) — provisional.**
- **The stated falsification condition was NOT met, so the 2026-07-29 reframing survives on Bot** —
  but it was **too strong as written and is now refined in place, not retracted.** The AE scored
  **Bot PR-AUC 0.1217 (3.6× chance)**, the second-best Bot result ever measured here (behind only
  Mahalanobis at 4.3×). Both top-2 Bot channels are (B)-family, as predicted.
- **But the AE collapses on web attacks**: macro **0.1000** vs the CNN's 0.6399, with **exactly
  0.0000 recall** on Web Brute Force, XSS *and* SQL Injection at 1% FPR — while catching
  **Heartbleed at 1.0000 recall** and **Infiltration at 0.8611**. That is a categorical split, not a
  performance gradient, and it refutes "the project is investing in (A) on a structurally (B)
  problem" as a blanket claim.
- **The refined account — modality analogue, not method family.** Web attacks are *structurally
  normal*: HTTP to port 80, indistinguishable from ordinary browsing in the 68 flow features (what
  makes them malicious is payload content, which this feature set lacks), so a benign-trained
  autoencoder reconstructs them perfectly and 0.0000 recall is the honest expected result. The CNN
  nonetheless scores 0.92–0.96 on them **not** by solving zero-day detection but by
  **within-modality transfer** — Web Brute Force resembles FTP-Patator/SSH-Patator, which *are*
  training classes. Bot has no such analogue (independently established: `BeaconLike` fires on 97.6%
  of PortScan and **0.0% of every other known attack** — no known class beacons), so every
  supervised method sits at 1.5–1.8× and only distance/reconstruction methods win.
  **Governing variable: does the unseen class share a behavioural modality with some known class?**
  Yes → (A) wins. No → (B) wins. Neither family dominates; they are complementary.
- **This makes the fusion wall the central architectural problem rather than a side issue.** Each
  family covers exactly what the other misses, so the system needs a per-flow **router** — and the
  router is precisely what cannot be *fitted*, since any combiner is calibrated on validation data
  containing no zero-day flows (`fusion_beaconlike.py` → `[2.35, 0.02]`).
- **It also gives the Knowledge Graph its first well-motivated job.** "Is this flow in a region with
  no known-class analogue?" is a clustering/density question answerable **without labels**, and the
  Phase-4 pre-check already showed the structure exists (Bot forms a ~90%-pure cluster at k≥200,
  stable across seeds). That is a *routing* signal, not a detection signal.
- **Flagged as interpretation, not measurement.** The modality account explains every prior null and
  is predictive, but has not been measured. Concrete next test: compute each zero-day family's
  embedding distance to the nearest known-class centroid and check it predicts which family wins.

## 2026-08-02 (C2 resolved — CNN baseline is n=3, overlaps the LTN control; Phase 3 built)

- **Added multi-seed support to `cnn_paper.py`** (`CNN_SEED`/`CNN_TAG` env vars, mirroring
  `ltn_paper.py`'s existing `LTN_SEED`/`LTN_TAG` convention). TAG defaults to the original
  `cnn_paper` filenames unchanged at the config seed (42), and to `cnn_paper_s<seed>` otherwise, so a
  differently-seeded run can never overwrite the reference model/scaler/encoder/embeddings. Verified
  by hash before and after: all 9 reference artifacts byte-identical post-run.
- **Ran seeds 43 and 44** in the background with a heartbeat monitor. One false alarm during
  monitoring — see the separate entry below — training itself completed cleanly both times (exit
  code 0). Seed 43: macro 0.6355 (raw) / 0.6353 (log-odds). Seed 44: macro 0.6396 / 0.6396.
- **Found and fixed a real bug in `rescore_logits.py` while rescoring the new seeds**: every
  `_logodds` entry was stamped with the config-default seed (42) regardless of which seed's model was
  actually rescored — wrong on 8 pre-existing rows. Fixed to parse the seed from the tag's `_s<N>`
  suffix. The 8 already-wrong historical rows were deliberately left as-is (append-only log,
  retract-in-place convention) — anything reading them must group by run name, not `params.seed`.
  Cross-checked that STATUS's already-published LTN-control range was unaffected by this bug (it must
  have been read by name originally).
- **C2 resolved: `cnn_paper` is now n=3 (log-odds), mean 0.6399, range 0.6353–0.6446 — and this
  range sits entirely inside the LTN control's n=3 range (0.6029–0.6505).** Stronger evidence for the
  original concern than the single-point check that opened it: not one number falling in an interval,
  but two full 3-seed distributions overlapping almost completely. **Resolved to "no clean winner at
  this n, needs a proper significance test" — not to "CNN confirmed."** The axiom-cost finding
  (Ax6 variants well outside both ranges) is unaffected and survives as the one comparison this data
  can actually support.
- **Built `scripts/autoencoder_paper.py` — canonical Phase 3.** Benign-only, dense encoder/decoder
  (68→48→32→16→32→48→68), trained and model-selected using zero attack labels, scored by
  reconstruction MSE. This is the direct falsification test of the 2026-07-29 thesis reframing: if it
  also lands at chance on Bot, that reframing is wrong and must be retracted in place. Not yet run.
- **Found and documented a Windows Git-Bash monitoring pitfall**: a `ps aux`-based liveness check
  reported the seed-43 training process dead at epoch 2 — no error, no traceback, training had
  actually continued normally and completed minutes later. `ps` enumeration under MSYS2's
  WINPID-mapped process listing can miss a live process for a single poll tick. Fixed the live
  monitor (and recorded the convention) to require sustained **log-growth staleness** across several
  consecutive polls before declaring a job dead or hung; a single `ps` miss is now advisory only.

## 2026-07-29 (thesis reframing — the Phase-2 nulls share one structural cause)

> **Reinterpretation of existing measurements. No new runs. Phase 3 has NOT started** — verified: no
> autoencoder script, no AE model, no AE entry in `runs.jsonl`. Everything this session was
> pre-Phase-3 (documentation, readiness analysis, retrospective audit).

- **Refuted the LOCO fusion fix proposed earlier the same day — before spending any compute on it.**
  Measured how `BeaconLike` actually fires per class: **PortScan 97.6%, every other known attack
  0.0%, BENIGN 22.7%** (each non-PortScan known attack targets a well-known port, so the signal is
  silent on them). A leave-one-class-out rotation is therefore **predictably null**: 7 of 8 folds
  teach the combiner the channel is worthless, and the 1 PortScan fold teaches it the channel is
  valuable *for the wrong reason* (port scanning, not C2 beaconing on 8080). The specifically
  recommended "cheap probe: hold out PortScan first" was **the worst available choice** — the one
  fold guaranteed to produce a false positive and validate an approach that would then fail.
- **The refutation is a better result than the fix would have been:** you cannot manufacture a
  synthetic zero-day that exercises BeaconLike in a Bot-like way, because **no known class in
  CIC-IDS2017 beacons.** LOCO is not broken — the known-class pool does not span the behavioural
  modalities of the unknown classes, so the fusion failure is not repairable by protocol alone.
- **Reframed the Phase-2 nulls as one structural fact rather than five failures.** Prompted by the
  question "if val contains no zero-day by construction, is the training premise flawed?" The
  protocol is **sound** — absence of zero-day from train/val is the *definition* of the problem, and
  putting Bot in validation would make the metric meaningless. What is flawed is the buried
  assumption that **a mechanism fitted on data can transfer to classes absent from that data**. That
  assumption underlies the LTN axioms, the aux head, the fitted fusion, *and* the KG's planned
  `s_kg` path — which is why all four fail identically.
- **Named the split that follows: (A) learn-what-attacks-look-like** (needs attack examples, cannot
  reach novel classes) **vs (B) learn-what-normal-looks-like** (needs only benign, reaches novel
  classes by construction). The project invested in (A) on a structurally (B) problem. **The existing
  Bot evidence already said so:** Mahalanobis **4.3×**, IsolationForest **1.7× while never seeing a
  single attack**, versus the CNN's 1.7× and every LTN variant's noisy 1–2×. The IsolationForest
  observation has been in STATUS since 2026-07-27; its significance was not drawn out until now.
  The oracle result (0.0314 → **0.9764** with ~1,000 labels) confirms this is a *transfer* limit of
  closed-set methods, not an information-theoretic one.
- **Consequence: the Phase-3 autoencoder is promoted from reviewer-objection checkbox to the
  load-bearing next experiment.** It is a pure (B) method, ~1h, and the direct falsification test of
  the reframing — if a benign-only AE also lands at chance on Bot, the (A)/(B) account is wrong and
  the reframing must be retracted in place. LOCO/fusion-repair work is deprioritized accordingly.
- **Proposed thesis statement (not yet adopted):** *"Closed-set supervised learning cannot transfer to
  novel classes regardless of where symbolic knowledge is injected — loss-, representation- and
  inference-level all fail for one shared structural reason. Open-set/distance methods reach the same
  families without labels."* Consistent with conference_roadmap Tier-S #1; sharpens it, not replaces it.

## 2026-07-29 (earlier-phase audit — 5 open concerns + a proposed fix for the fusion wall)

> **Findings only. No fixes implemented — all await go-ahead.** Full detail in
> [STATUS.md](STATUS.md) → "Earlier-phase audit"; tracked individually in
> [KNOWN_ISSUES.md](KNOWN_ISSUES.md).

- **Verified no records were lost in the same-day documentation rewrite.** Audited every deleted line
  across 24 files: all 23 dated CHANGELOG headers preserved (+1 new), every retracted claim preserved
  **verbatim inside `~~strikethrough~~`** with its retraction box. Two genuine losses were found and
  restored: the caveat that the **temporal CNN baseline (0.6689) may itself have been hampered by the
  focal-loss bug** (research-relevant — it is the denominator in "LTN 0.4529 vs CNN 0.6689", and a
  clean baseline would make the LTN deficit *larger*; never retrained, still unquantified), and the
  concrete `.gitignore` failure detail. Process note: both losses came from full-file `Write`
  rewrites — avoid that on record-bearing files.
- **🔴 Found 17% duplicate leakage between train and test.** CIC-IDS2017 is duplicate-heavy and the
  paper split is stratified random, so 19,513 / 114,658 test rows have an exact feature-vector twin
  in train — PortScan **58.3%**, SSH-Patator **48.6%**, DoS Hulk 25.3%, BENIGN 6.9%. **All 6 zero-day
  classes measure 0.0%**, so the headline macro zero-day metric is safe; what is contaminated is the
  ~0.98 overall binary PR-AUC. Proposed: report a unique-flows-only variant alongside, rather than
  de-duplicating (which would break base-paper comparability).
- **🔴 Found the reference baseline is single-seed while its comparators are not.** `cnn_paper`
  (0.6446) is n=1; the LTN control is n=3 and spans **0.6029–0.6505** — an interval that *contains*
  0.6446. STATUS's claim "neither variant beats the plain CNN, the neural baseline still wins in
  aggregate" therefore compares a point estimate against a distribution — the same error class that
  produced the Ax6 retraction. Two more CNN seeds would confirm or overturn it.
- **Tested and REFUTED a hypothesis of my own.** Web Brute Force and Web XSS correlate at
  **r = +0.992** across 60 runs, so the macro counts one web signal twice (⅓ Bot, ⅔ web). Predicted
  this biased the metric against Bot-targeted interventions like Ax6. Regrouping to
  `mean(Bot, mean(WebBF, XSS))` **preserved the ordering exactly** (0.4982 > 0.4824 > 0.4596 >
  0.3977) — the macro-cost finding is robust, and now more so. Absolute values shift ~0.15.
- **Found the feature transform was selected on the contaminated metric.** `log1p` is pinned citing
  "0.980 vs 0.965", which is the overall binary number — inflated by the duplicate leakage above and
  explicitly forbidden by `metrics.py` as an optimisation target. Never A/B'd on macro zero-day PR-AUC.
- **Found two `runs.jsonl` metadata defects:** `rescore_logits.py` stamps `seed: 42` on every
  `_logodds` row including s43/s44-derived ones (wrong on 8 rows), and repeated rescoring runs left
  triplicate entries.
- **🔑 Proposed a fix for the fusion wall — Leave-One-Class-Out.** The wall: a fitted combiner cannot
  learn to weight a zero-day-specific signal because validation contains no zero-day flows by
  construction (`[2.35, 0.02]`), and the KG feeds fusion the same way. The fix: **manufacture
  synthetic zero-day from known classes** — hide one known attack class from CNN training, retrain,
  and that class becomes a genuine novel class in validation; fit the combiner there and rotate over
  the 8 known classes. Gives the combiner the missing *regime* ("CNN confused by novelty + what the
  symbolic channel said"), which transfers, unlike a class-specific fact. Does not leak — the 6 real
  zero-day families are never touched. Cheap probe: hold out PortScan only, **1 retrain**; if the
  BeaconLike coefficient moves off 0.02 the approach is alive. Complementary alternative: conformal
  benign-only p-value calibration (Fisher combination), which needs no attack labels at all.
  This would upgrade the result from a dead end to *"inference-time fusion fails naively, and here is
  the protocol that repairs it."*

## 2026-07-29 (documentation audit — reference tier reconciled with reality before Phase 4)

Full read-through of all 27 project `.md` files. The **living tier** (STATUS / CHANGELOG /
KNOWN_ISSUES / DASHBOARD / CLAUDE / CONTRIBUTING) was found current and honest; the **reference
tier** (`docs/*.md`, `docs/implementation/`, `docs/target/`) was frozen at 2026-06-18 and in several
places asserted the *opposite* of confirmed findings. Nothing marked which tier a reader was in.

- **Two substantive findings, not just doc rot:**
  1. **A phase-number collision was about to skip a whole phase.** STATUS called the Knowledge Graph
     "Phase 3" while the canonical roadmap — *and STATUS's own component table, and a comment in
     `cnn_auxhead_paper.py`* — used Phase 3 = **anomaly pillar (benign-only autoencoder)** and
     Phase 4 = KG. The number was reused, not reassigned. The autoencoder (~1h, ranked Tier-1
     "highest leverage", closes the "why not just an autoencoder?" reviewer objection) was on track
     to be silently dropped. Canonical numbering table added to
     [conference_roadmap.md §1b](target/conference_roadmap.md); the autoencoder is now an explicit
     **Open Decision** in STATUS rather than a default.
  2. **`preprocess.py` hardcoded its input path**, bypassing `paths.py` — which still pointed
     `RAW_CSV` at the abandoned `data/raw_csv`. Added `paths.RAW_CSV_FULL` and `paths.PAPER`, marked
     `RAW_CSV` legacy, and pointed the script at the constant. All 22 scripts compile; paths verified.
- **Corrected content that was actively wrong:** README's "Key Results" advertised the **retracted**
  claim that the LTN improves zero-day recall; `artifacts.md` stated `behaviour_thresholds.npy` is
  "NOT generated by any current script" (false since the 2026-06-18 rebuild — the file is on disk);
  `ltn_current.md` still said results were "⏳ pending" for a run that finished, underperformed
  (0.4529 vs 0.6689) and was superseded; `neuro_symbolic.md`'s warning banner described two bugs that
  had been fixed a year of project time earlier.
- **Documented what existed but wasn't written down:** `scripts_reference.md` covered 7 of 22 scripts
  — rewritten to cover all, grouped current / analysis / legacy. `BeaconLike` (the 7th behaviour, the
  Ax6 signal) was absent from the behaviour audit, along with two properties that have already caused
  bugs: `BEHAVIOUR_NAMES` ordering is load-bearing (a `[:5]` slice would have silently dropped it),
  and it is the only **binary**, non-graded behaviour — which matters for fuzzy conjunctions and for
  KG edge weights.
- **Rebuilt KNOWN_ISSUES.md**: fixed duplicated `## High`/`## Medium` headings (the file was two
  interleaved halves), closed 5 stale `[OPEN]` issues, added a `[SUPERSEDED]` tier, and added the
  entire missing 2026-07-27 measurement-defect class (float32 saturation, size-weighted headline,
  ω-collapse, Smart App Control) which previously lived only in STATUS/CHANGELOG. New issues logged:
  `runs.jsonl` mixes two metric schemas (**`random_forest` has never been re-scored on the corrected
  macro metric**), behaviour validation tables are temporal-split, smoke-test artifacts pollute
  `outputs/predictions/`.
- **Applied retract-in-place markers to CHANGELOG**, which had been violating the project's own
  convention: three entries still asserted the Ax6 Bot-lift claim and the beaconing thesis as
  settled. STATUS struck them through; CHANGELOG did not. Newest-first ordering is not sufficient —
  someone citing an entry reads it in place.
- **Banners** added to every frozen reference doc naming what specifically is stale in each and
  pointing at STATUS, plus a superseded banner on the archive doc (which still lists Bot as a
  training class — the exact error CLAUDE.md names as a confirmed failure mode).
- **Phase-4 (KG) readiness audit** — inputs verified against disk, not assumed: embeddings exist for
  all three splits (883,796 / 110,475 / 114,658 × 64), `meta_*.csv` are row-aligned and carry
  IP/port/timestamp, `networkx` + `python-louvain` import cleanly. Split sizes, the 9 known / 6
  zero-day class lists, and every per-family count quoted in the docs were re-derived from the arrays
  rather than copied from STATUS (all matched: 4,183 zero-day test flows, Bot n=1,956).
- **Ran a falsification pre-check on the KG's core assumption** (that zero-day flows cluster
  separately in the CNN embedding space — the space where Bot scores at chance). MiniBatchKMeans,
  k ∈ {50…800} × 2 seeds. **The prediction was half wrong, in the useful direction:** zero-day flows
  do land 100% in benign-dominated clusters, *but they concentrate rather than smear* — **Bot forms a
  ~90%-pure cluster at k≥200, stable across both seeds**, capturing ~34% of Bot. Real structure
  exists to hang a graph on. Recorded with its caveats (n=2 seeds, oracle purity measured with test
  labels = upper bound, geometric not detection metric).
- **Three assumptions in `knowledge_graph.md` were found no longer to hold**, and are now documented
  at the top of that spec as a readiness review: (1) it calls the KG the "primary zero-day signal"
  while `conference_roadmap.md` says "not primary detector" — an unresolved scope contradiction;
  (2) the fusion path a primary detector needs is **already measured to fail** — a non-leaky combiner
  cannot be fit on a val set that by construction contains no zero-day flows, exactly as
  `fusion_beaconlike.py` demonstrated (`[2.35, 0.02]`, zero macro change) — so
  `decision_fusion.md`'s prescribed remedy is impossible and has been struck through with the three
  real options; (3) "temporal decay" has no time axis under a stratified-random split.
- **Identified the single most important untested quantity for Phase 4:** 25 of 50 clusters are
  already >90% benign in training, so the spec's "unexplained by known AttackType ⇒ emerging"
  criterion will fire on ordinary benign clusters as well as on zero-day ones. Its false-positive
  rate is unmeasured and decides whether the mechanism works — measure it before building the graph.

## 2026-07-29 (live local ops dashboard — "open preview" now means real-time, not a static snapshot)

- **Built `scripts/dashboard_server.py`**: a localhost-only (127.0.0.1, not network-exposed) Python HTTP server, stdlib `http.server` + `psutil`. Polls real machine state every 4s — CPU/RAM, git branch + uncommitted-file count, running training processes (matched against known pipeline scripts, reporting PID/CPU/mem/elapsed), the tail of whichever `outputs/*.log` file changed most recently (decoded leniently to survive the mixed UTF-8/UTF-16LE issue below), and the full `runs.jsonl` run history.
- **The Reconnect button reflects genuine connectivity**, not a decorative re-render: if a poll fails, the LIVE badge flips to a red "stalled" state and the button forces an immediate retry.
- Added `.claude/launch.json` (`preview_start` config: `"phase2-dashboard"`) and `docs/DASHBOARD.md` documenting the convention, file responsibilities, and when to update the live server vs. the static Artifact.
- **Superseded the earlier static-Artifact-only dashboard** (a published claude.ai Artifact, `phase2_console.html`) built and validated (colorblind-safe palette via `validate_palette.js`) the same day as the housekeeping below — that snapshot still exists for sharing outside a session, but "open preview" no longer means it.
- Added `psutil==6.1.0` to `requirements.txt`, marked dashboard-only (not part of the ML pipeline). PR #18.

## 2026-07-29 (session-discipline non-negotiables codified into CLAUDE.md — git housekeeping)

- Merged PRs #14–#17 from the previous session's work: a **model-selection convention** (recommend Opus/Sonnet/Haiku per step so the user doesn't overspend on Opus for routine work; explicitly marked as must-not-lapse after it silently stopped appearing mid-session once), a **"state phase back"** onboarding step (forces confirming STATUS.md's state actually landed, not just got read), and four new **working-convention non-negotiables**: provisional-claim discipline (a finding from one run/seed is "n=1, unverified," not fact — directly motivated by the Ax6 Bot-lift retraction below), retract-in-place documentation (strike through, don't silently rewrite — STATUS's 2026-07-27 entries are the reference example), a heartbeat-monitor requirement for any background job expected to run >10–15 min, and the PowerShell mixed-encoding pitfall (now also in [KNOWN_ISSUES.md](KNOWN_ISSUES.md)).
- These are process fixes, not research results — no component status changed.

## 2026-07-27 (ratio-mode fix confirmed — collapse eliminated, Bot question still unresolved)

- **Tested the fix suggested by the collapse diagnosis:** re-ran seeds 42, 43, 44 at ω=1.0 with `LTN_OMEGA_MODE=ratio` instead of `fixed`. Seeds 43 and 44 are the direct test — both collapsed catastrophically under fixed mode (macro 0.0520, 0.0366).
- **Zero collapses across all 3 seeds.** Log-odds macro: 0.6051 / 0.5796 / 0.5914 (mean 0.5920), a tight range with both previously-catastrophic seeds landing comfortably in the working range. Confirms the diagnosed mechanism precisely — adapting the SAT weight to the actual CE magnitude removes the coin-flip dynamic entirely.
- **Also, incidentally, the best Ax6 macro found all session** (mean 0.5920, beats fixed ω=0.5's mean of 0.5090) — though still below the clean no-axiom control's mean (0.6194); the macro cost is real, just smaller and now free of catastrophic risk.
- **Does not resolve the earlier Bot-lift retraction.** Bot lift stays noisy under ratio mode too (0.9x/3.2x/1.3x, mean 1.8x) and doesn't clearly exceed the control's own mean (2.07x) — consistent with the multi-seed retraction from earlier the same day. The fix solves stability, not whether Ax6 reliably helps Bot detection; that remains open, and the evidence so far leans negative. `ratio` mode is now the clearly preferred choice over `fixed` for any future loss-level injection work, since it removes a real failure mode at no measured cost.

## 2026-07-27 (ω=1.0 collapse mechanism diagnosed — free, from existing logs)

- **Diagnosed why `ltn_ax6_w1p0` collapses in 2 of 3 seeds**, using only logs already on disk — no new training. Had to work around a mixed PowerShell/Python encoding issue in the batch logs (header lines UTF-16LE, python's own stdout UTF-8, interleaved in the same file); resolved by locating markers at the raw byte level and decoding each segment with the right codec.
- **The pattern:** in both collapsed seeds, the model's best epoch is 1–2 — it never meaningfully improves beyond random initialization (best val_acc 92.8% / 96.2%), and best-by-val-loss early stopping locks that in within ~10 epochs. The seed that worked kept improving through epoch 3 and reached 99.6% val accuracy. SAT values look similar across all three runs (~0.17–0.26) — visually this doesn't look like the same catastrophe as ω=2.0, but the underlying cause is the same.
- **Mechanism:** `LTN_OMEGA_MODE=fixed` means the SAT weight doesn't adapt to how large CE actually is. Whether SAT or CE dominates the gradient during the first couple of epochs depends on random initialization; if SAT wins that window, the model gets pulled toward satisfying axioms over learning to classify, and early stopping locks in the result before it can recover. ω=1.0 sits right at the edge where this can go either way depending on seed; ω=0.5 has enough margin to avoid it every time (0/3 seeds); ω=2.0 has none (100% reproducible on n=1, now understood as the same dynamic with zero margin rather than a separate failure mode).
- **Suggested fix, untested:** `ratio` omega-mode (already implemented, adapts SAT weight to the actual CE/SAT ratio) or a warmup schedule should remove the coin-flip dynamic, since the failure is specifically "fixed weight doesn't match the actual early-training ratio." Next concrete experiment if this line of investigation continues.

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
- **Corrects the 3 genuinely-saturated runs.** `ltn_ctrl_w0` moves from 0.5937/~1.0x Bot lift to a clean **0.6049/1.5x**; `ltn_repro` and `ltn_v2` similarly move up. ~~The Ax6-vs-same-ω comparison from the previous entry is untouched — neither `ltn_anat_*` nor `ltn_ax6_*` was ever saturated, so "Ax6 roughly doubles Bot lift" still holds exactly.~~
  > 🔴 **RETRACTED later the same day (marked in place 2026-07-29).** The struck sentence is wrong in
  > its *conclusion*, not its premise: it is true that neither side was saturated, so log-odds
  > rescoring didn't disturb the comparison. But the comparison was **single-seed**, and with n=3 the
  > control's mean Bot lift (2.07x) exceeds both Ax6 variants' (1.87x, 1.70x). "Still holds exactly"
  > was reasoning about the wrong threat — it checked for a measurement artefact and concluded
  > robustness, when the actual problem was seed variance. See the multi-seed entry above.
- **Resolves the deferred CE-vs-focal question: false alarm.** `ltn_repro` (CE + base axioms) was flagged as the worst fair-loop variant based on its saturated blended score. Cleanly measured it's mid-pack (macro 0.5751), between the control and the old fixed-ω axiom variants — plain CE isn't demonstrably a poor loss choice here.
- **The clean control is stronger than previously measured**, which raises the bar the axioms have to clear: even with zero axioms, the custom loop already gets 1.5x lift on Bot. Ax6's honest accounting against the *best* baseline is +0.7–1.1x Bot lift for a ~0.07–0.09 macro cost — a real, worthwhile, but not free trade, not a wash against a weak control as it looked before this correction.
- **`ltn_anat_w2p0`'s collapse is confirmed genuine, not a saturation artefact** — PR-AUC is rank-based and threshold-independent, so it only moves under log-odds rescoring when tie blocks were corrupting the ranking (true for the other 3). It stays at 0.0348 here, meaning the ω=2.0 model's weights actually degenerated rather than merely underflowing its output scores.
- **The aux-head retrain didn't reproduce its own Bot number** — 0.8x lift this run vs ~1.0x the first time, same seed and config. Most plausible explanation is ordinary single-seed noise (TF training isn't bit-deterministic across runs even with a fixed seed), which is itself a concrete argument for the still-outstanding multi-seed work before any comparative claim ships.

## 2026-07-27 (Ax6 trained — ~~prediction confirmed~~ 🔴 **RETRACTED**, with a real tradeoff)

> 🔴 **This entry's headline did not survive multi-seeding** (marked in place 2026-07-29). The
> "prediction confirmed" framing rests on **seed 42 only**. What survives from this entry: the
> *tradeoff* (Ax6 costs macro PR-AUC) — which multi-seeding made **stronger**, not weaker — and the
> observation that neither variant beats the plain CNN. What does not survive: that Ax6 helps Bot.

- **TensorFlow unblocked.** Root cause was Windows Smart App Control (`VerifiedAndReputablePolicyState=1` in `HKLM\SYSTEM\CurrentControlSet\Control\CI\Policy`), rejecting TF's unsigned compiled wheels under its "Enterprise signing level" requirement. User turned it off via Windows Security; reversible without reinstall on this build (25H2, build 26200.8875, past the 26200.8116 cutoff). Not a code or environment problem.
- **Ran `ltn_ax6_w0p5` and `ltn_ax6_w1p0`** — identical configs to the earlier `ltn_anat_w0p5`/`w1p0` runs, with Ax6 (`BeaconLike`) now live in the axiom set. ~~**B2's prediction is confirmed: Bot lift roughly doubles at both ω values** (1.1x → 2.2x at ω=0.5; 1.1x → 1.8x at ω=1.0). The axiom-injection mechanism was never the bottleneck — the old axioms simply targeted the wrong signature.~~
  > 🔴 **RETRACTED (marked in place 2026-07-29).** Single seed. With n=3 the no-axiom control's own
  > Bot lift ranges **1.5–2.9× (mean 2.07×)** — *above* both Ax6 variants (1.87×, 1.70×). The
  > comparison quoted here pitted the control's worst seed (1.5×) against Ax6's best (2.2×). The
  > underlying claim "the axiom-injection mechanism was never the bottleneck" is therefore
  > **unsupported** — no mechanism has yet been shown to reliably move Bot.
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
- **New central finding: Bot is at chance for every supervised method** (lift 1.0–1.8x); Mahalanobis (0.1467, 4.3x) is the sole exception and is a *distance* method — the open-set-recognition signature. ~~Evidence that the per-flow representation does not contain the Bot signal: Bot is C2 beaconing, whose signature is periodicity *across* flows, destroyed by i.i.d. flow classification. Explains why every symbolic intervention moves the number by only ±0.02, and why Ax3/4/5 (thresholded functions of the same 68 input features) are tautological.~~
  > 🔴 **RETRACTED the same day (marked in place 2026-07-29).** The first sentence stands — Bot *is*
  > at chance for supervised methods, and Mahalanobis *is* the exception. The struck explanation does
  > not: the skyline oracle (`scripts/skyline_oracle.py`) lifted Bot PR-AUC from 0.0314 to **0.9764**
  > with ~1,000 labelled examples, proving the signal **was always present per-flow**. The beaconing/
  > cross-flow story was an untested domain intuition written up as a finding. The correct reading is
  > a **zero-day transfer failure of the closed-set classifier**, not an information-theoretic limit —
  > and consequently Ax3/4/5 are not "tautological", they simply target the wrong signature
  > (volume/scan-shaped, tuned for DoS/PortScan, untouched by Bot's actual pattern).
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

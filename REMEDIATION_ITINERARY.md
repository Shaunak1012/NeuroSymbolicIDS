# Remediation Itinerary

**Consolidates:** [AUDIT_REPORT.md](AUDIT_REPORT.md) (F-01 … F-25) and
[BASEPAPER_COMPARISON.md](BASEPAPER_COMPARISON.md) (CL-01/02, BP-01 … BP-08, FD-01 … FD-05).
**40 findings, all carried.** §11 is a coverage map — every finding ID appears in exactly one item.

**Opened:** 2026-09-16. **Status:** ~~nothing started~~ **worked the same day** on branch `fix/audit-remediation` — see §13 and the checklist in §12.
**Repo state at audit:** branch `docs/paper-revision`, HEAD `2406bc3`.

> **How to work this.** Stages run in order; items inside a stage are independent unless a
> `depends on` column says otherwise. Every item says whether it **changes a published number**.
> Stages 1–3 change none. Stage 4 changes nearly all of them. Stage 5 is gated separately because it
> changes the protocol, not just the numbers.
>
> **Per the audit prompt's Phase-2 rules:** one logical fix per commit with the finding ID in the
> message; record the baseline before any item that moves a metric; never edit a number in a doc
> without the code change that produced it; a fix that *improves* a metric deserves more suspicion
> than one that lowers it.

---

## 0. Decisions needed before work starts

Five blocking questions. Items that depend on them are marked. Nothing in Stages 1–3 is blocked.

| # | Decision | Why it blocks | Recommendation |
|---|---|---|---|
| **D1** | **F-04** — the 1:1 benign under-sampling is deliberate (`config.yaml:17`, "paper-faithful"). Keep the protocol and add a prevalence-faithful column, or change the split? | Determines whether item 4.8 (cheap, additive) or 5.3 (full re-split, invalidates all 221 stored prediction arrays) | **Keep + add the column.** The protocol choice is defensible as a replication; only its undocumented 4.11× effect is the defect |
| **D2** | **F-08** — was `BeaconLike` chosen *before* the Bot measurement and merely validated against it, or did the measurement drive the choice? `behavior.py:32-40` reads as the latter but that is an inference from a comment | Determines item 6.3: re-derive (days, may weaken the symbolic arms further) vs relabel (an hour) | Answer from memory/session history if possible; if unknowable, **relabel as oracle-informed** and exclude from transfer claims |
| **D3** | **F-13/F-14** — is `Capstone_final (4) (1).ipynb` the capstone deliverable, or superseded? | Determines item 8.1: track + re-execute, vs archive with a banner | Note it is **not** simply wrong: its zero-day set (PortScan in, Infiltration out) is the **base paper's Table I set**. On that axis it is the faithful one |
| **D4** | **F-02/F-03** — approve the grouped-split and temporal-split re-runs? | Stage 5 is ~2 days of compute and will lower the known-class numbers materially | **Approve at least the measurement**, even if the result stays a limitation rather than the headline. A reviewer will ask |
| **D5** | Repository visibility (already open in `STATUS.md`) — the repo is public and pushing this branch puts the paper text on GitHub, where a similarity checker would match it | Gates whether Stage 1/2 doc edits get pushed or held local | Author's call; unchanged by this audit |

---

## Stage 1 — Corrections with no compute

**Changes published numbers: no** (item 1.1 corrects a *claim about* numbers, not a number).
**Total effort: ~2 hours.** Do this first: five of these are wrong on the page right now, and two are
in the submission text.

| # | Finding | Action | Files | Effort |
|---|---|---|---|---|
| **1.1** | **CL-01** | Replace *"we beat the base paper by 18–29 pp on all four known-class views"* with the per-view deltas **+18.82 / +0.42 / +28.72 / +7.07**. Suggested wording is in BASEPAPER_COMPARISON §4 | `STATUS.md:1137`, `STATUS.md:3415`, `CHANGELOG.md:850`, `CHANGELOG.md:1291`, `scripts_reference.md:1038`, **`paper_draft.md:269`**, `paper_draft.md:838`, **`paper_supplementary.md:132`**, **`paper_supplementary.md:647`**, `paper_outline.md:187` | 30 min |
| **1.2** | **F-18** | "70 features" → 68, or add the frozen-doc banner CLAUDE.md says these carry | `docs/architecture.md:34,83`, `docs/dataset.md:86`, `docs/pipeline.md:41`, `docs/target/target_architecture.md:85` | 15 min |
| **1.3** | **FD-01** (wording half) | "paper-aligned split (Bizzarri et al.)" → "paper-**inspired**"; state that their per-class equalisation to 31,843 is **not** reproduced | `config.yaml:8`, `scripts/preprocess_paper.py:2` | 15 min |
| **1.4** | **BP-04** | Annotate the transcribed Table II F1 cell: their 1D CNN "Binary 15" F1 is printed identical to its accuracy (90.88 %); recomputed from their Fig. 3(e) it is ~92.3 % | `scripts/paper_metrics.py:102` | 5 min |
| **1.5** | **FD-02** (qualifier half) | Qualify the "47.85 % vs 48.34 %" agreement: the two figures are computed on **differently filtered populations** — they delete duplicates and payload-less records, we keep both | `STATUS.md:3415` (the input-modality decision cell, where it is load-bearing), drafts | 20 min |
| **1.6** | **F-23** | `git rm --cached outputs/.check.pid` (tracked despite the `outputs/*.pid` rule) | — | 2 min |
| **1.7** | **F-21** | Escape `e.path` before interpolating KG explanation strings into HTML | `scripts/dashboard_server.py:491-492` | 10 min |
| **1.8** | **F-19** | `PYTHONHASHSEED` is set after interpreter start, where it has no effect. Set it in the launcher and re-exec, or drop it from the documented control list | `scripts/determinism.py:69`, `scripts/run_long.sh` | 15 min |
| **1.9** | **F-20** | Record which score array each quoted 4-dp number came from. The `_logodds_` twins differ in the 4th decimal (s43: 0.6355 vs 0.6353; Bot 0.0245 vs 0.0241) | `scripts/tracking.py` (add a `scoring` param), STATUS conventions | 20 min |

**Gate:** re-run `python scripts/lint_conventions.py` and `python scripts/verify_draft.py`. Both must
stay at ALL PASS / 0 mismatched.

---

## Stage 2 — Write-up work, no compute

**Changes published numbers: no.** **Total effort: ~5 hours.** This is where the audit's analytical
value lands. Item 2.1 is the single highest-value piece of writing in the whole itinerary.

| # | Finding | Action | Effort |
|---|---|---|---|
| **2.1** | **BP-01** | Make the **threshold-shift** argument the primary base-paper criticism. Their gain by view is **+0.09 / +0.15 / +0.07 / +2.15 / +12.13 pp** — all of it in the one view with no benign rows — and their own Fig. 3 shows false positives rising **380 → 452** while false negatives fall 536 → 227. They report no threshold-free metric, so nothing in the paper separates "better model" from "different operating point". Keep `F1 = 2A/(1+A)` as the *second* criticism (it is about redundancy; this one is about validity) | 1 h |
| **2.2** | **BP-02** | Add the packets-per-flow table and the consequence: **42.2 % of their zero-day headline is Heartbleed**, 13,486 payload packets from **11 flows that share one 5-tuple inside 20 minutes — effectively one connection** (~~effective n ≈ 11, one host pair, split at packet level~~ — corrected: zero-day classes are test-only in their protocol, so never split). Heartbleed + Web BF = **79.0 %** of their zero-day set. Note the mirror: PortScan is held out but their payload filter reduces it to **830 rows, 2.6 %** | 1 h |
| **2.3** | **BP-03, BP-05, BP-06, BP-07** | Add to related work: their confusion matrices imply a known-class test set of ~~159,540 = 35.1 %~~ **159,160 = 35.0 %** of Table I, not the stated 10 % (verified three ways) · text says "**five** attack classes" where Table I lists six · **n = 1, no seeds**, with 0.07–0.15 pp differences reported as results — cross-reference our own noise floor (SD 0.0222, C2 retracted at 0.9 SD) · Fig. 2's "63 filters" | 1 h |
| **2.4** | **BP-08** | Raise as an **open question**, not a finding: a CNN over 1500 raw payload bytes on 2017-era plaintext traffic can key on protocol strings and attack-tool User-Agents; no leakage control is reported. We cannot confirm it without payload data we do not hold | 20 min |
| **2.5** | **FD-03** | Add an architecture row to the deviation table: pooling 1×4/8/16 vs 2/2/2 (forced by input width), Dense(N×5)→Dense(N) vs Dense(64)→Dropout→Dense(32)→Dropout→Dense(N), batch 128 vs 256, no dropout/L2 in theirs | 15 min |
| **2.6** | **FD-05** | State the packet↔flow unit change as a general rule: **no count in their Table I is comparable to any count in `split_report.txt`** | 10 min |
| **2.7** | **F-17** | Limitations: one test split has been the reporting surface for **239 logged runs over ~5 months**. The split-half protocol (`fusion_weight.py`) covers two experiments | 20 min |
| **2.8** | **F-16** | Limitations: **no adversarial-evasion evaluation exists**. `ood_scores.py`'s ODIN perturbation is an OOD-scoring technique, not a threat model. A flow-feature IDS is trivially evadable by padding and rate shaping. (Running one is item 6.4) | 20 min |
| **2.9** | **F-10** | Lead the field-gap argument with the **deduplicated** binary figure (0.9884) and footnote the raw 0.9928. The argument survives dedup; the number a reviewer will challenge is the one on the page | 20 min |

---

## Stage 3 — Code changes, written but not yet run against the record

**Changes published numbers: no** (nothing is executed against the reporting split until Stage 4).
**Total effort: ~1.5 days.** These are the guards that stop Stages 4–5 from regressing.

| # | Finding | Action | Effort | Depends on |
|---|---|---|---|---|
| **3.1** | **CL-01** guard | Add a `verify_draft.py` check that recomputes the four base-paper deltas from `paper_metrics.json` and fails on a mismatch. The current checker could not catch CL-01 because it was a derived range, with the base-paper side on the UNBACKED list | 20 min | 1.1 |
| **3.2** | **F-06** | Write `scripts/ksweep_heldout.py` implementing the split-half protocol that `ksweep_heldout.json` records but no code produces. Reuse `fusion_weight.py:100-140`. ~~My independent re-derivation gives **+0.0346 at 2.38σ** (s_kg) against the recorded +0.0305 at 2.86σ — expect the regenerated σ to be lower~~ *Done 2026-09-16: with `fusion_weight.py`'s split the record regenerates **identically**; the online variant gives +0.0077 at 1.10σ, 2/3* | 1 h | — |
| **3.3** | **F-09** (first tranche) | `tests/` with the leakage-boundary assertions, so Stage 5's protocol work is guarded: `test_no_zero_day_in_train_val`, `test_scaler_fitted_on_train_only`, `test_cross_split_exact_duplicates` (assert the **measured** 17.02 % so a regression is visible), `test_flow_id_group_overlap` (assert 54.88 %), `test_feature_count_is_68`, `test_behaviour_indices_match_check_py`, `test_threshold_not_derived_from_test` | 1 day | — |
| **3.4** | **F-15** | Move constant-column selection inside the paper split, or assert the 10 columns are constant on train alone. Practical effect is nil (all ten are all-zero across the capture) but the boundary is crossed | 30 min | 3.3 |
| **3.5** | **F-07** (code half) | `metrics.evaluate` accepts an optional `thr`; callers pass a threshold derived from **validation** benign scores. Report the *achieved* test FPR as a measurement rather than pinning it at 1.00 % | 1 h | — |
| **3.6** | **F-05** (code half) | Make the **causal** KG variant the default everywhere `operational_best.py` and the k-sweep read `s_kg`. `fusion_kg.py:56` already does this correctly | 30 min | — |
| **3.7** | **F-04** (column half) | Add a prevalence-faithful reporting column: thin the positive class by the measured **4.11×** benign under-sample factor, 200 bootstrap draws. Method validated in AUDIT_REPORT §3 F-04 | 1 h | D1 |

---

## Stage 4 — THE RE-BASE

**Changes published numbers: YES — nearly all of them.** **Compute: ~8–12 h.**
**This is the gate the paper cannot go out without.**

Wall-clock estimates from consecutive `runs.jsonl` stamps: **CNN ≈ 15–35 min/run** (determinism adds
overhead — budget 30–45), **LTN ≈ 30–47 min/run** (budget 45–60).

| # | Finding | Action | Compute | Depends on |
|---|---|---|---|---|
| **4.1** | — | **Record the baseline artifact first.** Snapshot every current headline into a dated JSON so the before/after table required by Phase-2 rule 2 is mechanical, not reconstructed | 10 min | — |
| **4.2** | **F-01** | Re-run `cnn_paper.py` at seeds 42/43/44 with determinism on. Expected: **0.6299**, down from the quoted 0.6399. Then mark every pre-flag run in `runs.jsonl` as `det_deterministic: false` (currently `None`) so the two populations can never be pooled | 3 × 30–45 min | 4.1 |
| **4.3** | **CL-02 + FD-04** | **The missing control.** Run `LTN_LOSS=ce LTN_AXIOMS=base LTN_OMEGA=0 LTN_OMEGA_MODE=fixed` — no such configuration has ever been run, so "their +12 pp gain does not appear" is currently confounded with the loss function. Run **3 seeds on both arms** (`ltn_repro` is also n=1 and pre-determinism). State the delta as `ltn_repro − ltn_repro_ctrl_ce_w0` on view 5 | 6 × 45–60 min | 4.1 |
| **4.4** | **F-01** (downstream) | Re-derive every post-hoc channel from the new predictions, in order: `novelty.py` → `kg.py` → `fusion_kg.py` → `ksweep_fusion.py` → `significance.py` → `ablation.py` → `operational.py` → `operational_best.py` → `paper_metrics.py` → `field_gap.py` → `paper_figures.py`. No retraining. Update the hard-coded `0.6399` at `fusion_kg.py:6,89` | ~2 h | 4.2 |
| **4.5** | **F-05** | Re-run `operational_best.py` with the causal KG as default. Expected: best macro **0.7123 → 0.7032**, recall @1 % FPR **57.6 % → 54.6 %**. Present the transductive figure only as a labelled offline upper bound, as `kg.py:243-247` already frames it | 20 min | 3.6, 4.4 |
| **4.6** | **F-07** | Re-score every channel with validation-derived thresholds. Achieved test FPR will no longer be exactly 1.00 % — that is the point | 1 h | 3.5, 4.4 |
| **4.7** | **F-06** | Run the new `ksweep_heldout.py`; replace the hand-made JSON with its output; quote whatever it produces | 30 min | 3.2, 4.4 |
| **4.8** | **F-04** | Publish the prevalence-faithful column. Expected: macro **0.6446 → ~0.6015**, Bot **0.0591 → ~0.0152**. Note the direction: Bot's correction *strengthens* the unreachability claim | 30 min | 3.7, 4.4 |
| **4.9** | **F-25** | Load `{TAG}.keras` and `{TAG}_best.keras` and compare weights. If identical, keep one and delete the other path; if not, find out why | 20 min | 4.2 |
| **4.10** | **F-10, FD-01, FD-02** | Publish the **deduplicated** and **composition-neutral** columns — both already computed in this audit (dedup moves the four known-class views by ≤0.71 pp; balanced accuracy moves the multi-class gap +18.82 → +18.79 pp). They defend the modality attribution and cost nothing | 30 min | 4.4 |
| **4.11** | — | Re-run `lint_conventions.py` and `verify_draft.py`; update **STATUS.md**, **CHANGELOG.md**, **KNOWN_ISSUES.md**; confirm every number has a `runs.jsonl` row behind it | 1 h | all of Stage 4 |

> **Before/after table is a deliverable of this stage, not an afterthought.** Every metric that moved,
> old value, new value, and the item that moved it.

---

## Stage 5 — Protocol variants *(gated on D4)*

**Changes published numbers: YES, and changes the protocol.** **Compute: ~2 days.**
Per Phase-2 rule 4, each item needs its justification written into the report **together with the
delta it caused**.

| # | Finding | Action | Expected impact | Compute |
|---|---|---|---|---|
| **5.1** | **F-02** | Grouped split keyed on `Flow ID` (or `(Source IP, Destination IP)`) via `GroupShuffleSplit`, reported alongside the current one. **54.88 %** of test flows currently share a 5-tuple with a training flow — 100 % for four DoS families and all three Web Attack zero-day families | Known-class numbers fall **materially**; web-attack zero-day expected to fall. Magnitude unknown — this *is* the experiment | ~1 day |
| **5.2** | **F-03** | Report the headline under the temporal protocol (`preprocess.py`, Mon–Wed / Thu–Fri) alongside the paper-aligned one; relabel the latter an i.i.d. benchmark, not a deployment estimate. Currently **100 %** of test flows fall inside the train time range | Known to be much worse (the 0.4529-vs-0.6689 result). That is the honest result, not a problem | ~0.5 day |
| **5.3** | **F-04** (full) *(only if D1 says change the split)* | Undersample benign for train/val only; give test all remaining benign | Invalidates all 221 stored prediction arrays → full re-score. **Prefer item 4.8** | ~1 day |
| **5.4** | **FD-01** (full) | Add `protocol.balance: per_class` as a second arm reproducing their equalisation to 31,843/class | Fidelity, not correctness — item 4.10 already shows composition does **not** explain our advantage | ~0.5 day |

**⚠️ Watch for:** stratification fights grouping. Some families are one or two groups and may become
unsplittable. Report that rather than forcing it.

---

## Stage 6 — Modelling, statistics, symbolic

**Changes published numbers: yes, locally.** **Effort: ~2 days + compute.**

| # | Finding | Action | Note | Depends on |
|---|---|---|---|---|
| **6.1** | **F-12** | Give XGBoost/RF/IsolationForest the same validation budget the CNN gets (early stopping on val for XGBoost, a small grid for RF). Currently they get fixed hyperparameters and never load the val split | Most likely outcome: XGBoost ties or beats the CNN more clearly — already the project's stated position. Context: a depth-12 tree hits **0.9978 PR-AUC** on the known-class task | 4.2 |
| **6.2** | **F-11** | Holm–Bonferroni within each pre-registered family in `significance.py`; report exploratory comparisons as exploratory; add adjusted p to `significance.json`. 13 tests at α=0.05 → family-wise error ≈ 0.49 under the global null | Some current "SIGNIFICANT" verdicts will become n.s. | 4.4 |
| **6.3** | **F-08** | Per **D2**: re-derive `BeaconLike` using only train-visible classes and re-run the LTN/KG arms, **or** relabel it oracle-informed and exclude it from transfer claims. It fires on **99.95 %** of Bot vs 22.65 % of benign purely because this capture's C2 sits on 8080, which is excluded from the "well-known" set while 8443 is included. `behavior.py:144` currently asserts "NOT data-fitted" | Re-derivation may weaken the symbolic arms further — which is itself a finding | D2 |
| **6.4** | **F-16** (optional) | A basic evasion experiment on the zero-day families: packet padding, rate shaping, IAT jitter. Otherwise item 2.8 stands as the limitation | — | — |
| **6.5** | **FD-02** (optional) | Recompute view 5 on the `X - Attempted`-excluded variant — the closest analogue of the base paper's filtered population. `preprocess_improved.py` already produces it | Directly tests whether the 47.85/48.34 agreement survives population-matching | 4.4 |

---

## Stage 7 — Reproducibility and engineering

**Changes published numbers: no.** **Effort: ~2 days + one long run.**

| # | Finding | Action |
|---|---|---|
| **7.1** | **F-09** (full) | Extend `tests/` beyond the Stage-3 leakage tranche: feature construction, split integrity, metric definitions, the `timeline.py` D/M/YYYY + 12-hour corrections. Note what exists today: **0 test files across 77 scripts / 18,010 lines**; `lint_conventions.py` lints conventions and `verify_draft.py` checks reporting consistency — neither asserts anything about the data path |
| **7.2** | **F-24** | `pip freeze > requirements.lock.txt`; plan the TensorFlow upgrade (2.15.1 is end-of-life, Windows-CPU-only); reconcile the venv packages absent from `requirements.txt` (`numba`, `llvmlite`, `cryptography`) |
| **7.3** | **F-22** | Replace `exec(compile(ast.Module(...)))` at `latency.py:228` — move `KnowledgeGraph` into an importable module |
| **7.4** | — | The first genuine **end-to-end** `python scripts/run_all.py --run`, so the claim can stop being "checked end to end and never executed end to end in one pass" (CLAUDE.md). ~10–20 h CPU |

---

## Stage 8 — Hygiene

| # | Finding | Action | Depends on |
|---|---|---|---|
| **8.1** | **F-13, F-14** | Per **D3**. If the notebook is the deliverable: track it, re-execute top to bottom so `execution_count` stops being `null` on all 22 code cells, and add a header stating which protocol it implements. If superseded: `docs/archive/` with a banner. Either way, record that its "Heartbleed 0 → 100 % recall" rests on **n=11** at a **10.2 %** system FPR, and that its zero-day set is the base paper's rather than `config.yaml`'s | D3 |
| **8.2** | — | Residual doc tidy; confirm the single-component-status-table invariant still holds (`grep -rln "^| Component | Status"`) | Stage 4 |

---

## 9. Consolidated expected impact on the headline numbers

Everything that moves, and why. ~~**Directions of every comparative conclusion survive; magnitudes do not.**~~ **Wrong — the CNN + KG fusion direction reversed (§13).**

| number | today | after | moved by |
|---|---:|---:|---|
| CNN baseline, macro zero-day PR-AUC | 0.6399 | **0.6299** | 4.2 (determinism re-base) |
| CNN seed-42 reference | 0.6446 | **0.6298** | 4.2 |
| Best config, macro | 0.7123 | **0.7032** | 4.5 (causal KG) |
| Recall of unknown flows @1 % FPR | 57.6 % | **54.6 %** | 4.5 |
| k=800 held-out delta / σ | +0.0305 / 2.86σ | **~+0.035 / ~2.4σ** | 4.7 (regenerated) |
| Macro at capture-faithful prevalence | — | **~0.6015** (new column) | 4.8 |
| Bot at capture-faithful prevalence | — | **~0.0152** (new column) | 4.8 |
| Achieved test FPR at the 1 % operating point | exactly 1.00 % | **measured, not pinned** | 4.6 |
| Base-paper delta, known-class views | "18–29 pp" | **+18.82 / +0.42 / +28.72 / +7.07** | 1.1 |
| "their +12 pp gain does not appear" | asserted | **tested, or withdrawn** | 4.3 |
| Known-class numbers under a grouped split | — | **expected to fall materially** | 5.1 (gated) |

---

## 10. Deliberately not in this itinerary

* **History rewriting for secrets.** None needed — a full scan of all 259 commits found **zero** keys,
  tokens, private keys, credential files, captures, or internal addresses.
* **Retracting the double dissociation, the Bot mechanism, or the field-metric gap.** All three
  reproduce from the stored artefacts (AUDIT_REPORT §5, rows 9–13). Stage 4 re-bases their magnitudes;
  it does not threaten them.
* **Abandoning the paper-aligned split.** D1 recommends keeping it. The defect is the undocumented
  4.11× prevalence effect, not the choice.
* **Adopting payload modality.** `STATUS.md:3415` decided against it on independent evidence (the H4
  oracle probe). Item 1.5 only qualifies *one* of that decision's supporting arguments; the decision
  itself is untouched.
* **A frozen holdout.** Structurally the right fix for F-17, and too late for this project. Item 2.7
  states the exposure instead.

---

## 11. Coverage map — all 40 findings

| Finding | Item | | Finding | Item |
|---|---|---|---|---|
| F-01 | 4.2, 4.4 | | F-21 | 1.7 |
| F-02 | 5.1 | | F-22 | 7.3 |
| F-03 | 5.2 | | F-23 | 1.6 |
| F-04 | 3.7 → 4.8 *(5.3 if D1 flips)* | | F-24 | 7.2 |
| F-05 | 3.6 → 4.5 | | F-25 | 4.9 |
| F-06 | 3.2 → 4.7 | | CL-01 | 1.1 *(guard 3.1)* |
| F-07 | 3.5 → 4.6 | | CL-02 | 4.3 |
| F-08 | 6.3 *(D2)* | | BP-01 | 2.1 |
| F-09 | 3.3 → 7.1 | | BP-02 | 2.2 |
| F-10 | 2.9, 4.10 | | BP-03 | 2.3 |
| F-11 | 6.2 | | BP-04 | 1.4 |
| F-12 | 6.1 | | BP-05 | 2.3 |
| F-13 | 8.1 *(D3)* | | BP-06 | 2.3 |
| F-14 | 8.1 *(D3)* | | BP-07 | 2.3 |
| F-15 | 3.4 | | BP-08 | 2.4 |
| F-16 | 2.8 → 6.4 | | FD-01 | 1.3 → 4.10 *(5.4 full)* |
| F-17 | 2.7 | | FD-02 | 1.5 → 6.5 |
| F-18 | 1.2 | | FD-03 | 2.5 |
| F-19 | 1.8 | | FD-04 | 4.3 |
| F-20 | 1.9 | | FD-05 | 2.6 |

**40 findings · 40 placed · 0 dropped.**

---

## 12. Tracking

```
STATUS 2026-09-17                 [x] done   [~] partial / running   [ ] not started   [-] not needed

STAGE 0  decisions      [x] D1  [x] D2  [ ] D3  [x] D4  [ ] D5
STAGE 1  no compute     [x] 1.1 [x] 1.2 [x] 1.3 [x] 1.4 [x] 1.5 [x] 1.6 [x] 1.7 [x] 1.8 [x] 1.9
STAGE 2  write-up       [x] 2.1 [x] 2.2 [x] 2.3 [x] 2.4 [x] 2.5 [x] 2.6 [x] 2.7 [x] 2.8 [x] 2.9
STAGE 3  code           [x] 3.1 [x] 3.2 [x] 3.3 [x] 3.4 [x] 3.5 [x] 3.6 [x] 3.7
STAGE 4  RE-BASE        [x] 4.1 [x] 4.2 [x] 4.3 [~] 4.4 [x] 4.5 [x] 4.6 [x] 4.7 [x] 4.8 [x] 4.9
                        [x] 4.10 [x] 4.11
STAGE 5  protocol (D4)  [x] 5.1 [x] 5.2 [-] 5.3 [ ] 5.4
STAGE 6  modelling      [x] 6.1 [x] 6.2 [x] 6.3 [ ] 6.4 [ ] 6.5
STAGE 7  engineering    [x] 7.1 [x] 7.2 [x] 7.3 [~] 7.4
STAGE 8  hygiene        [ ] 8.1 [x] 8.2
```

**Minimum set before the paper is shared with anyone:** 1.1, 1.3, 1.5, 2.1, 2.2, 3.1, 4.2, 4.3, 4.4,
4.5, 4.11. Everything else can follow.

**Long jobs go through `scripts/run_long.sh`** with a heartbeat monitor (non-negotiable #2).
**Multi-seed before writing any number down** (non-negotiable #3). **Retract in place**
(non-negotiable #4). **Branch → PR → local `--no-ff` merge** (non-negotiable #5).

---

*Read-only planning document. Companion to [AUDIT_REPORT.md](AUDIT_REPORT.md) and
[BASEPAPER_COMPARISON.md](BASEPAPER_COMPARISON.md). No other repository file was created or modified.*

---

## 13. Progress, 2026-09-16

**Done:** Stages 1–3 in full; Stage 4 except the training-dependent items; 6.2 (code), 6.3, 7.1–7.3,
8.2. 30 tests; `verify_draft.py` 207 verified / 0 mismatched; lint passes; the paper compiles.

**Partial or running.**
* 4.2 — the deterministic CNN population (`c4_log1p_s42-44`) already existed and is used; the seed-42
  byte-identity re-check (`cnn_det_verify_s42`) is running in `audit_rebase.sh` lane A.
* 4.3 — CL-02's matched control and the 3-seed deterministic `ltn_repro` are running (both lanes).
* 4.4 — re-derived on the deterministic CNN: fusion, operating profile, held-out k, base-paper views.
  **Not** re-derived: novelty (MSP / Mahalanobis), significance, ablation, field_gap, figures.
* 4.10 — deduplicated values are in the paper; the composition-neutral accuracy (99.78 %) is in
  `config.yaml` and BASEPAPER_COMPARISON but has no record of its own.
* 6.2 — Holm is in `significance.py`; the record has not been regenerated (CPU kept for training).
  Previewed: no verdict changes.

**What Stage 4 found that the itinerary did not predict.** §9 expected the re-base to move magnitudes
only. It reversed a direction. The online CNN + KG fusion is −0.1269 against the deterministic CNN, and
`fusion_population.py` showed why: across 11 pre-flag CNN runs the fusion gains in 5, the three
reference runs are the ones that gain, and the gain tracks where each run ranks XSS among all test
flows (Spearman +0.95). The result is withdrawn in STATUS, KNOWN_ISSUES and the paper.

**Corrections to this audit's own statements**, all made in place: F-06's figures do regenerate (the
audit had used a different split); F-15's ten columns are not all constant; BP-03 is 159,160 rows
(35.0 %); BP-04 is three cells, not one; BP-02's Heartbleed is one connection and is never split; F-18
overstated how many docs lacked a banner; F-13's notebook uses the base paper's zero-day set; F-01 and
§9 said directions survive.

**Not done, and why.** D1, D3, D4, D5 and the paper reframe need the author. 5.x waits on D4. 6.1
(tuning-matched baselines) and 7.4 (end-to-end run) were deferred to keep the CPU for the training
lanes. 6.4 and 6.5 are optional. 8.1 waits on D3.

**Update, 16:04 UTC.** `audit_rebase.sh` finished. 4.2: the seed-42 re-run is byte-identical to
`c4_log1p_s42`. 4.3 / CL-02: against a matched control the base paper's SAT term changes zero-day
accuracy by +0.55 pp (+0.60 / −0.84 / +1.89; not direction-consistent) where they report +12.13, and
macro by −0.0090 (1/3); the paper now says so. 4.10: balanced known-class accuracy is recorded
(deterministic CNN 99.73 %). 6.2: `significance.json` regenerated with Holm, no verdict changes.
4.4 stays partial: novelty, ablation, field_gap and the figures still use the pre-flag CNN.

---

## 14. Progress, 2026-09-17

**Decisions.** The author approved D1 (keep the 1:1 split, report both), D4 (run the variants) and the
reframe. D3 and D5 remain the author's.

**Done.**
* 4.8 / D1 — the paper states the base rate and the capture-faithful figures, and what crosses the split
  boundary (`verify_draft.py` checks both). 5.3 is therefore not needed.
* 6.1 — `baselines_tuned.py`: tuned RandomForest 0.6407 ≈ det CNN 0.6299; tuned XGBoost 0.6180; tuned
  IsolationForest 0.0564.
* 4.4 (part) — OOD battery re-run on the deterministic CNN (best Bot 0.0576 < 0.08).

**Not predicted by the itinerary.** 6.1 overturned part of the paper's mechanism: the tuned forest ranks
Bot consistently (+0.923). `bot_mechanism_recheck.py` then widened the CNN's Bot-ranking figure from
three runs to all 17: median +0.55 / +0.59, not −0.090. Retracted in the paper, STATUS, KNOWN_ISSUES
and CLAUDE.md; absorption and the 0/8 overlap stand. Separately, four analysis scripts
(`operational.py`, `best_config.py`, `field_gap.py`, `metric_divergence.py`) chose their populations from
whatever was on disk and would no longer have reproduced their records; all pinned, all byte-identical.

**Running.**
* 5.1 / 5.2 — `paper_grouped` and `paper_chrono`, CNN + AE at seeds 42–44. ⚠️ 5.2 is implemented as a
  **within-class chronological** split (earliest 80 % of each known class trains), not the legacy
  Mon–Wed / Thu–Fri protocol: that protocol changes which families are zero-day, so it would not be
  comparable with the headline. The grouped split had to move 42,500 known/benign flows that share a
  5-tuple with a zero-day flow into test.
* 7.4 — `run_all.py --run --keep-going` in a sandbox. Preprocess, split, timeline and the seed-42 CNN
  reproduce the canonical artifacts byte for byte from the raw CSVs.

**Update, 14:50 UTC.** 5.1 / 5.2 done: grouped CNN 0.5589 (−0.071), chronological CNN 0.6019 and
autoencoder 0.0455 (halved); double dissociation direction-consistent everywhere (`split_variants.json`,
paper Appendix A). The pre-registered forest test E4 failed (overlap is now an account of the CNN, not
a law). `run_all.py` was reworked after its first execution (26 stages, runs / needs / external) and a
second full execution started in `outputs/sandbox_e2e2`.

**Not done.** 4.4: Mahalanobis on the deterministic CNN. 5.4, 6.4, 6.5 (optional). 8.1 waits on D3.
7.4 until the second sandbox run finishes.

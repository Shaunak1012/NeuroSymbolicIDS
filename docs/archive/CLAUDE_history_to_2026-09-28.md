# CLAUDE.md history — the "Current state" block as of 2026-09-28 (archived verbatim)

> **Archived 2026-09-28, not deleted.** This was lines 106–352 of `CLAUDE.md`: every "next action",
> noise-floor table and standing caution accumulated since 2026-06-18. It is kept verbatim as the
> research record. It was moved because `CLAUDE.md` is auto-loaded into every session and this block
> had become the main source of drift — it contradicted itself and STATUS in at least four places.
> Those four are **struck through in place below** (non-negotiable #4), each with its correction:
>
> 1. "What this project is" (still in `CLAUDE.md`, rewritten there) cited ρ = −0.090 and "unreachable
>    and unstable" as the mechanism — retracted 2026-09-17 (`bot_mechanism_recheck.py`).
> 2. The noise-floor table listed CNN+KG fusion as "✅ direction (3/3 seeds)" — withdrawn 2026-09-16
>    (`fusion_population.py`: gains in 5 of 11 pre-flag runs, 0 of 6 deterministic).
> 3. "C4 still open" — C4 was closed 2026-08-10 (log1p wins by +0.4693, `c4_transform_ab.sh`).
> 4. "Recommended order … next: (a) Phase 7.5 Tier 1" — every item in it was done by 2026-09-05.
>
> **For the current state read `CLAUDE.md` → "Current state" and `docs/STATUS.md`.**

---
## Current state (one-line pointer — full table in STATUS.md)

**Phases 0–4 done. Phase 5 (Decision Fusion) is 🟡 PARTIALLY ENTERED. Phases 6–7, 7.5 and R not
started.**

> 🔴 **This block said "Phase 4 … awaits sign-off. Not started" until 2026-08-05 — while Phase 4 had
> been built, multi-seeded AND completed with explainability two sessions earlier.** Fourth
> occurrence of the component-status drift defect, in the one file auto-loaded into every session.
> It survived because the 2026-08-04 session updated STATUS/KNOWN_ISSUES but not this pointer.
> **If you change phase state, change it here too** — this line is the first thing the next session
> reads.

Three established results: **(1)** a **double dissociation** between the CNN (`cnn_paper.py`) and the
autoencoder (`autoencoder_paper.py`) — 3.9–40 SD of the measured noise floor, the only comparative
claim in the project with that margin, though it is a dissociation between *two models*, **not** two
method families *(2026-09-17: its direction holds on every seed of the grouped and chronological
splits too)*; **(2)** the CNN's Bot failure is **representational** — 100% of Bot flows are
classified BENIGN (all **17** CNN runs), Bot's discriminative features have 0/8 overlap with the
known-class task's~~, and the resulting Bot ranking is **noise** (cross-seed ρ = −0.090)~~ *(retracted
2026-09-17: over all CNN run pairs Bot's median ρ is +0.55/+0.59 — least consistent family, not noise;
−0.090 was the three reference runs. `bot_mechanism_recheck.py`)*; **(3)** **training is not
reproducible at fixed seed** (SD 0.0222 — see the noise floor below), which retracted C2 and demotes
every within-tier comparison this project spent months on.

🔴 **Withdrawn 2026-09-16: the CNN + KG fusion gain** — the project's only positive result. It was
measured with the same three CNN runs; across 11 CNN runs of that configuration the online fusion
gains in 5, and in 0 of 6 deterministic runs (`fusion_population.py`). **Nothing in the architecture
has been shown to beat the neural baseline.** The CNN baseline itself is re-based **0.6399 → 0.6299**
(deterministic population, `rebase_deterministic.py`); never pool the two populations.

👉 **Component-by-component status: [docs/STATUS.md](../STATUS.md) → "Component Status".**
Do not restate it here — that is exactly what kept rotting.

**Next action (resume here — as of 2026-09-17):** read STATUS → "REMEDIATION, DAY 2" and
`REMEDIATION_ITINERARY.md` §14. Branch `fix/audit-remediation` (not pushed).
1. ~~**Collect the D4 split variants**~~ ✅ done 2026-09-17 (grouped −0.071; chronological halves the
   AE; dissociation direction holds everywhere — STATUS).
2. ~~**Collect the second sandbox run**~~ ✅ done 2026-09-18: 20/26 stages, 6.5 h, **72 artifacts
   byte-identical, 0 different** (`repro_compare.py`; records in `outputs/metadata/run_all_sandbox2/`).
   Only the declared-external stages are incomplete.
3. ~~Author decisions **D3** and **D5**~~ ✅ 2026-09-18: D3 = the notebook is **not** the deliverable
   (kept private, gitignored); D5 = push as five sequential PRs, each merged locally `--no-ff`.
   ~~whether the tuned forest's features overlap Bot's~~ answered (E4 failed).
4. **Next, and ask the author before starting each:** ~~itinerary 5.4 (base-paper class balancing)~~
   ✅ done 2026-09-18 (balanced 0.4699 vs size-matched 0.2118 vs ours 0.6299 — STATUS), ~~6.4 (evasion
   experiment)~~ ✅ done 2026-09-18 (jitter evades the CNN, −0.068; every perturbation *raises* the AE and
   forest — STATUS), ~~6.5 (view 5 on the relabelled data)~~ ✅ done 2026-09-18 (**0.69 %** — "we
   reproduce their CNN" withdrawn), ~~**then** 4.4 (Mahalanobis on the deterministic CNN)~~ ✅ done
   2026-09-18 — **the remediation itinerary is complete.**
5. **IEEE versions (2026-09-19):** `build_ieee_md.py` + `md_to_latex.py --ieee` — full 7/9 pages, ICC 2027
   6/6 pages (deadline 2 Oct 2026), both subset-verified. **Open: D6 (authors, blind?) and D7 (ICC page
   limit)** — STATUS → Open Decisions. Never hand-edit the `.tex`; change the markdown and regenerate.

~~**Next action (resume here — as of end of 2026-09-16):**~~ *(superseded 2026-09-17)* read STATUS → "AUDIT + REMEDIATION" and
`REMEDIATION_ITINERARY.md`. Work is on branch `fix/audit-remediation` (not pushed).
1. ~~Collect `audit_rebase.sh`~~ ✅ **done 2026-09-16**: seed-42 CNN byte-identical; CL-02 answered —
   the base paper's SAT term moves zero-day accuracy **+0.55 pp** (not direction-consistent) against a
   matched control, where they report +12.13. The paper says so.
2. **Author decisions D1, D3, D4, D5** and how to reframe the paper without its positive result.
3. Remaining itinerary items: 6.1 tuning-matched baselines, 5.1/5.2 split variants (if D4), 7.4 the
   first real end-to-end `run_all.py --run`, re-run `significance.py` (Holm now in code).

~~**Next action (resume here — as of end of 2026-08-10):**~~ *(superseded 2026-09-16; kept for the record)*
1. **Write.** Spine decided: **field-metric gap leads, mechanism is the body**, double dissociation
   demoted to support. ⚠️ Write the **resolution** claim (67/204 method pairs indistinguishable on the
   published metric while ≥2× apart on zero-day), **not** the *information* claim — ρ=+0.568 refutes
   the strong form, and `field_gap.py` hard-codes that refutation.
2. **Phase 5's remaining three** — calibration, latency, the fitted fuser (blocked by the fusion wall).
3. **Optional, only if C2 matters to the write-up:** re-run the LTN control **post-flag** at n=6.
   C2's +0.0204 is pre-flag on both sides, so it can only be reopened *within* the post-flag
   population. 🔴 **The threshold is 0.0256 and did NOT move** — see the noise floor below.

🔴 **NOISE FLOOR SETTLED 2026-08-10 — the threshold did NOT move.** Post-flag **seed** variance is
**SD 0.0171 (n=6)**, statistically indistinguishable from the 0.0222 nondeterminism floor
(F(5,5)=1.69, **p=0.58**). The earlier "seed variance is ~7× smaller" reading came from two **n=3**
SD estimates that agreed with each other and were both wrong — **n=3 is enough for a MEAN and nowhere
near enough for a VARIANCE** (seed 45 returned 0.5882 and moved the SD 5×). ✅ Separately, the
**"session effect" is dead**: ρ vs seed number goes **−0.943 → −0.086** with determinism on, so it
tracked *run order*, not seed, and **post-flag seeds are comparable across sessions**.
⚠️ **Data-split SD 0.0228 untouched — an absolute number carries 0.0285.**

**Done 2026-08-10:** both flagged n=1 results settled (**C1 is dead** — the verdict flips seed by
seed) · **C4 closed** (log1p wins by **+0.4693**, t=163) · spine decided *and its strong forms
refuted* · **the last 2026-07-29 audit item is now closed**.

**Done as of 2026-08-05:** Phase 4 complete · Phase 5 partial (significance, parameter-free fusion,
n=6; calibration/latency/fitted-fusion outstanding) · **Phase 7.5 Tiers 1 AND 2 complete** ·
**the ablation** (only the KG earns its place) · **the base paper's metric set computed for the first
time** · **method tiers A/B/C/D** (11 new methods). Phase 6 cross-dataset is **blocked** — no
CIC-IDS2018 locally.

⚙️ **DETERMINISM IS NOW ON** (`scripts/determinism.py`, intra=16/inter=2 — byte-identical across two
full 50-epoch runs). **The SD 0.0222 floor applies to PRE-flag runs only, and pre/post-flag runs are
different populations — do not pool them.** Separately, **data-split SD (0.0228) ≈ training SD
(0.0222)**: shared-split comparisons cancel it, but **an absolute number carries ≈0.032**.

### 🔴🔴 THE NOISE FLOOR — read before citing ANY number in this project

**Training is not reproducible at fixed seed.** Six runs of seed 42, identical code, idle machine:
**SD 0.0222 · range 0.0621 · CV 3.6 %**. No TF determinism flags are set, so thread scheduling
changes float accumulation between runs.

**Express every delta as a multiple of this SD. That ratio, not the raw number, decides survival.**

| claim | delta | ÷ SD | verdict |
|---|---:|---:|---|
| Double dissociation (XSS / Web BF) | +0.90 / +0.82 | 40 / 37 | ✅ established |
| Double dissociation (Bot) | +0.0868 | 3.9 | ✅ established |
| ~~CNN+KG fusion~~ | ~~+0.0527~~ | ~~*paired*~~ | ~~✅ direction (3/3 seeds); magnitude 0.027–0.088~~ 🔴 **withdrawn 2026-09-16** — three reference runs; 5 of 11 pre-flag, 0 of 6 deterministic (`fusion_population.py`) |
| **C2: CNN vs LTN control** | +0.0204 | **0.9** | 🔴 **RETRACTED — within noise** |

🔴 **C2 is retracted on controlled grounds.** It was closed in the CNN's favour with a paired
bootstrap (p=0.001) earlier the same day. The gap is **smaller than re-running one model twice**.
**A flow-level significance test cannot rescue a delta below the pipeline's own reproducibility** —
the most important methodological lesson in this project.

⚠️ **`cnn_paper = 0.6446` is the MAX of 11 runs, not a typical result** (mean 0.6217). The honest
reproducible baseline is the **ensemble, 0.6356**.

⚠️ **Every n=3 range in the docs is an artefact.** The CNN's "tight" 0.0093 spread is **0.4 SD** —
less than half a single re-run's noise. Never cite an n=3 range as evidence of stability.

🧭 **Three claims were asserted and withdrawn in one session** ("n=3 understated variance", "session
effect", "C2 must be reopened") — all competing explanations for this one unmeasured quantity. Four
training runs settled what hours of observational comparison could not. **Measure variance before
explaining it.**

### What changed on 2026-08-03 (read this before citing anything older)

A full audit + remediation session. It was scoped as bookkeeping, but the re-runs it required
**overturned two documented claims and answered the last open research question.**

🔬 **"Why does the CNN fail on Bot?" is ANSWERED** (`scripts/bot_failure_analysis.py`, 4 hypotheses
pre-registered before running). The failure is **representational, not informational**:
- **100% of Bot flows are classified BENIGN** (all 3 seeds, mean p(BENIGN)=0.9984) — Bot is not
  ambiguous to the CNN, it is confidently asserted benign.
- The features separating Bot from benign have **0/8 overlap** with those the known-class task needs.
- ~~So the CNN's Bot ranking is **noise**: cross-seed Spearman **ρ = −0.090**, vs 0.68–0.83 for every
  other family. RandomForest is the same (0.068); **the autoencoder is not (0.827).**~~
  🔴 **Retracted 2026-09-17** (`bot_mechanism_recheck.py`): over all pairs of the 6 deterministic /
  11 pre-flag CNN runs, Bot's median ρ is **+0.55 / +0.59** (pairs −0.54 to +0.92) — the least
  consistent family, not noise. RF's 0.068 is its default `max_features="sqrt"`; tuned on validation
  (`baselines_tuned.py`, `max_features=0.3`) it gives **+0.923** and Bot PR-AUC **0.2196** (6.4×
  chance). Sixth "three runs looked decisive" trap; the absorption (17/17 runs) stands.
  🔴 **And the overlap account failed its first direct test (E4, pre-registered, 2026-09-17):** the tuned
  forest reaches Bot while weighting Bot's features *less* (0.19 vs 0.21). "0/8 overlap" is one XGBoost
  proxy's ranking (both forests: 2/8). Write overlap as an account of the **CNN**, never as a law.
- ~~**One cause, four symptoms** — this explains the Phase-4 purity lottery, the Mahalanobis Bot
  spread, and RF's Bot swing simultaneously.~~ RF's swing is a configuration effect, so only the CNN's
  failure is a measured symptom. Not an information limit (oracle PR-AUC 0.9988).

🔴 **The (A)/(B) thesis reframing is FALSIFIED in its strong form.** **RandomForest — a supervised
(A)-family method — ties the autoencoder on Bot** (0.1311 vs 0.1314, paired bootstrap p=0.88) while
beating it 0.50 on macro. "(B) methods are needed to reach Bot" is **dead**, and so is "no channel
sits at both ends of the frontier" (RF does). ⚠️ **The CNN-vs-AE double dissociation survives and is
now statistically significant — but it is a dissociation between two MODELS, not two FAMILIES.**
Do not write it up as an (A)-vs-(B) result.

✅ **Significance tests are RUN** (`scripts/significance.py`). **C2 closes in the CNN's favour** —
it does beat the LTN control (+0.0204, p=0.001) despite overlapping seed ranges, because the paired
test cancels flow-noise common to both. ⚠️ **Flow-level uncertainty only**: at n=3 the Wilcoxon
floor is p=0.25, so **no seed-level claim in this project can reach p<0.05** — that needs n≥6 seeds.

🔴 **A RETRACTION WAS REVERSED: "on macro the CNN beats XGBoost" is n.s. (p=0.80).** The 2026-07-27
retraction of *"XGBoost ≈ CNN"* compared two point estimates with no test. The original claim was
right. Lesson, symmetric to the earlier ones: **a point-estimate gap is not a result in either
direction.**

### Standing cautions (still current)

🔴 **Do NOT re-propose the "host-window view" as a second channel — it was built and measured
(2026-09-28, `hostwindow.py`).** All eight window features (flows / distinct destinations /
distinct ports over 60 s and 600 s, pair persistence, arrival regularity) are predictable from the
68 flow features at **R² 0.511–0.867 without `Destination Port`**, so **0 of 8 are exogenous** —
the same premise failure as the static host-role predicates, on a different quantity. The channel
also does not reach Bot (lift **1.42×**, n=3), and conformal **min-p fusion loses to its own best
channel by −0.0745 on 3 of 3 seeds** (4.35× the noise floor). ✅ What survives: windowing is
genuinely *less* derivable than a static host profile (0.51–0.87 vs 0.91–0.95), and a **second**
conformal step on the fused statistic does deliver a requested FPR (1 % → 0.96–1.12 %, where raw
min-p gives 2.8 %). See STATUS → "THE PROPOSED 'IMPROVED' ARCHITECTURE, TESTED".

🔴 **Do NOT repeat the "modality analogue" mechanism** (that web attacks transfer because they
resemble FTP/SSH-Patator) — falsified by `modality_analysis.py`. ✅ **The replacement IS measured**:
the CNN assigns ~90% of Web BF/XSS flows to **`DoS slowloris`**, a known *attack* class, so their
0.92–0.95 PR-AUC is **absorption into a known attack, not zero-day detection.** (Note this differs
from raw-space nearest-neighbour, which is DoS Hulk — classifier behaviour ≠ raw proximity; cite
which measurement you mean.)

🟡 **Earlier-phase audit (2026-07-29):** C2 🔴 **retracted** (the gap is 0.9 SD — see the noise floor)
· C5 ✅ addressed (counts corrected, record now version-controlled) · **C1 ✅ closed 2026-08-03**
(`comparability.py` reports the dedup variant; supervised channels lose 0.0035–0.0049, all six
zero-day families measure 0.0 % overlap) · **C3 ✅ closed 2026-08-03** (`robustness.py`; the regrouped
macro shifts values ~0.11–0.15 but preserves every ordering) · ~~**C4 still open** — annotated in
`config.yaml` but not fixed; the log1p A/B still cites the contaminated metric.~~ ✅ **C4 closed
2026-08-10** (log1p wins by +0.4693, t=163; `c4_transform_ab.sh`).

✅ **PHASE 4 IS COMPLETE (2026-08-03) — KG built, multi-seeded, explainability + faithfulness
delivered.** `kg.py` · `kg_visualize.py` · `explain.py`.

It was **fully specified by measurement**, not by the original spec:
- **Representation: RAW FEATURES.** Bot purity 77.6 % (k=200) / 80.6 % (k=400), no training-seed
  lottery. 🔴 The AE bottleneck was recommended, then measured and **rejected** (52.1 pp spread,
  worst of all options) — **rank stability ≠ cluster stability.**
- **Scope: CORROBORATION + EXPLAINABILITY, not primary detection.** The spec's "unexplained
  cluster" criterion scores **lift ≤ 1.00× — at or below chance.** The scope contradiction with
  `conference_roadmap.md` is resolved empirically; the roadmap was right.
- **Emerging-pattern rule: GROWTH RATE ONLY.** Of the spec's three criteria, only cluster
  growth/burstiness survives: **lift 5.94× [5.66, 6.11] (n=3), ~81 % recall.** "Unexplained" is
  dead; behaviour co-occurrence is weak (2.81× at 1.5 % recall, cluster-level ≤ 1.35×) and worth
  keeping only as an *explanation* attribute.
- **Decay: KEPT (adaptive).** Decision logged 2026-08-03 — time = flow-count position in true
  chronological order.

⚠️ **Two caveats that must reach the write-up.**
① **Growth works substantially because CIC-IDS2017's attacks are scripted into fixed windows**
(Bot Fri 09:34–12:59, Web BF Thu 09:15–10:00, XSS Thu 10:15–10:35). A real network with continuous
low-rate C2 would not produce this signal — and Bot's real signature is persistence, not bursts.
② **"Temporal burstiness of a raw-feature cluster" does not need a knowledge graph.** The KG's
justification must rest on explanation/corroboration, not on this detection number. A reviewer will
say this; say it first.

🔴 **Do NOT cite "the conjunction gives 81 % precision."** That was clustering-seed 42 only; n=3
gives lift 1.73–11.57× and precision 0.122–0.814. **Fifth single-seed trap in this project, and the
first caught before publication** — multi-seed *before* writing, always.

⏱️ **Use `timeline.py` for ANY temporal work — never parse `meta_*.csv` timestamps directly.**
Two silent defects: dates are **D/M/YYYY** (naive parsing scatters the 5-day capture across
March/June/July) and the clock is **12-hour with no AM/PM** (so 1 PM sorts before 9 AM).
`timeline.parse()` corrects both and validates against the published capture schedule.

🧩 **Use `behavior.active_behaviour_matrix()`** in any KG code, not the raw 7-column matrix:
`RepeatedConnections` is constant 0.0 (dead edge type / divide-by-zero risk) and `BeaconLike` is
binary, so bimodal as an edge weight. Check `behavior.BEHAVIOUR_KIND` before assuming continuity.

**Recommended order:** ~~C2~~ ✅ → ~~Phase 3 AE~~ ✅ → ~~modality test~~ ✅ → ~~multi-seed AE~~ ✅ →
~~train-vs-score decomposition~~ ✅ → ~~KG substrate re-check~~ ✅ → ~~significance test~~ ✅ →
~~baselines on current schema~~ ✅ → ~~why the CNN fails on Bot~~ ✅ → ~~KG representation purity~~ ✅
(raw features win) → ~~"unexplained cluster" FP rate~~ ✅ (mechanism dead) → ~~KG's other two
emerging-pattern criteria~~ ✅ (growth works, co-occurrence weak) → ~~temporal-decay time axis~~ ✅
(kept adaptive) → ~~C1/C3 reporting variants~~ ✅ (both closed) → ~~build the KG~~ ✅ →
~~explainability + faithfulness~~ ✅ → ~~noise floor + n=6 everywhere~~ ✅ (C2 retracted) →
~~**next: (a) Phase 7.5 Tier 1 — ensemble, calibration/ECE, precision@alert-budget, abstention;
(b) the CNN→+LTN→+KG ablation; (c) TF determinism flags, which attack the 3.6 % CV at source;
then C4.**~~ *(all four done by 2026-09-05 — stale as of archiving)* LOCO/fusion-repair stays deprioritized; the per-flow "router" idea rested on the
falsified modality mechanism.

**Phase numbering is canonical in [conference_roadmap.md §1b](../target/conference_roadmap.md)** — three competing schemes were in circulation; don't invent a fourth. Full history, retractions, and decisions in [STATUS.md](../STATUS.md). Training stays on **CPU** (GPU/Blackwell deferred — see STATUS Open Decisions).


---

## Appendix — the original "Reality check" line from "What this project is" (struck 2026-09-28)

~~**Reality check on the goal above:** as of Phase 2, the symbolic pillar does **not** beat the neural baseline — every symbolic injection point tried (loss-level, representation-level, inference-level) costs macro zero-day PR-AUC or changes nothing. The project's current contribution is the *anatomy of why*, and as of 2026-08-03 that anatomy has a **mechanism**: a closed-set discriminative model learns only the features that separate the classes it is trained on, so a novel class is reachable exactly to the extent its signature overlaps that basis — and *unreachable and unstable* otherwise (Bot: 0/8 feature overlap, cross-seed rank ρ = −0.090). Don't write or reason as though the fusion story is established.~~

*Retracted 2026-09-17 (`bot_mechanism_recheck.py`): over all CNN run pairs Bot's median ρ is +0.55 / +0.59; −0.090 was three runs. "Reachable exactly to the extent its signature overlaps" was also weakened by the failed E4 test.*

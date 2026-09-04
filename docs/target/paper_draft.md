# DRAFT — What the CIC-IDS2017 Literature Cannot Measure, and Why the Thing It Cannot Measure Is Hard

> **Status: FIRST PROSE DRAFT (2026-09-05).** Drafted *from* [paper_outline.md](paper_outline.md),
> not independently of it — every number here traces to that file's second column and every caveat
> to its third. **If a claim appears here without its caveat, that is a defect in this draft, not a
> simplification.**
>
> **Format:** Markdown, deliberately. No venue template is chosen yet (NeSy / MILCOM-adjacent per
> [conference_roadmap.md §4](conference_roadmap.md)), and committing to LaTeX before the venue is
> chosen buys nothing. **Section numbering matches the outline** so the two stay diffable.
>
> ⚠️ **Not yet drafted:** related work, and the reproducibility-artifact section. Figures are built
> (`paper_figures.py`, `field_gap.py`) and referenced by number.

---

## Abstract

Published intrusion-detection results on CIC-IDS2017 cluster above 99 % on the metric the field
reports, and are routinely used to claim capability against novel attacks. We show that this metric
**cannot resolve that capability**: across 40 methods evaluated identically, **67 of 204 method pairs
(33 %) are statistically indistinguishable on the published metric while differing by a factor of two
or more in macro zero-day PR-AUC**, the worst pair sitting 0.0028 apart on the former and **18×**
apart on the latter. The metric is not noisy and not uninformative — its run-to-run standard
deviation is 0.0020 and it correlates with zero-day performance at ρ = +0.568 — it is simply too
coarse, in the regime the field reports in, to separate methods on the axis the claims are about.

Underneath that measurement failure we identify a mechanism. A closed-set discriminative model learns
only the features that separate the classes it was trained on, so a novel class is reachable exactly
to the extent its signature overlaps that basis. For the Bot family this overlap is empty: **0 of 8**
discriminative features are shared with the known-class task, **100 %** of Bot flows are classified
BENIGN at mean p(BENIGN) = 0.9984, and the resulting ranking is **noise** (cross-seed Spearman
ρ = −0.090, against 0.68–0.83 for every other family). The information is present — an oracle with
Bot labels reaches PR-AUC 0.9988 from the same 68 flow features — so this is a limit of closed-set
supervision, not of the feature modality.

We then show what does not remove it: four deep architectures, seven classical baselines, four
benign-only anomaly methods, a nine-scorer out-of-distribution battery, calibration, abstention, and
**our own symbolic pillar**, which contributes −0.0004 (n.s.) alone and *significantly harms* the
system when stacked on the knowledge graph. We report one partial success (a knowledge-graph channel,
+0.0528 macro, direction established on 3/3 seeds and magnitude only bounded to 0.027–0.088) and one
retraction of our own negative claim. Throughout, we report a measured reproducibility floor
(SD 0.0222) and express every delta as a multiple of it; doing so retracted one of our own headline
results.

---

## §1 Introduction — a resolution failure

The CIC-IDS2017 literature reports accuracy, F1 and AUC above 99 % with enough regularity that the
numbers have stopped discriminating. That would be unremarkable if those numbers were used only to
claim what they measure — separating benign traffic from attack families the model was trained on.
They are not. They are routinely offered as evidence of capability against *novel* attacks, which is
the capability that matters operationally and the one the metric is least able to speak to.

We make that gap quantitative. Evaluating 40 methods under one protocol and scoring each on both the
published metric (overall binary detection across all fifteen classes) and on **macro zero-day
PR-AUC** over held-out attack families, we find:

- **67 of 204 comparable method pairs (33 %) are indistinguishable on the published metric while
  differing ≥2× on zero-day capability.** "Indistinguishable" means a difference below **0.0058**,
  which is two standard deviations of a *difference* derived from a measured median run-to-run
  SD of **0.0020**. We state the band rather than the count alone, because the count is meaningless
  without it.
- The extreme case, `deep_cnn_lstm` versus `ltn_anat_w2p0`, sits **0.0028 apart on the published
  metric and 18× apart on zero-day**. We give the extreme only alongside the distribution above; on
  its own it would be cherry-picking.
- Restricting to the field's own reporting regime — the 25 methods scoring ≥0.98, which is where
  published work lives — those methods sit **within 0.014 of one another and span 20×** on zero-day.
  The ≥0.98 cut is chosen *because it is the field's regime*, not because it separates the data.

**Two stronger versions of this claim are false and we do not make them.** The published metric is
not uninformative about zero-day performance: Spearman ρ = **+0.568** (p = 0.0001) across the 40
methods, and **+0.41** even within the ≥0.98 regime. Nor is its spread within its own noise: it is a
*precise* measurement, with a median run-to-run SD of 0.0020, roughly ten times below its spread
across methods. The metric is precise, weakly informative, and **too coarse in the regime that
matters** — which is a narrower and more useful statement than either strong form, and it is the one
our data support. Both refutations are hard-coded into the output of the script that produces the
figure, so the strong forms cannot be reintroduced by accident.

**Contributions.**

1. A resolution failure, demonstrated across 40 methods on a single axis (§3, Fig. 1).
2. A mechanism for why zero-day detection is hard rather than merely unmeasured, with four
   independent symptoms traced to one cause (§4).
3. A negative result that is expensive to obtain: four categories of method, a standard OOD battery,
   two post-hoc remedies and our own symbolic architecture all fail in the same way (§5).
4. One partial success and its honest bound (§6), and a measurement-discipline section that retracts
   two of our own claims (§7).

---

## §2 Protocol and metric

**Data and split.** CIC-IDS2017 flow features, **68 numeric features per flow**. Nine attack families
plus benign are treated as *known* and split 80/10/10 stratified, with benign under-sampled to 1:1:
**883,796 train / 110,475 validation / 114,658 test**. Six rare families — Bot, Heartbleed,
Infiltration, and Web Attack Brute Force / XSS / SQL Injection — appear **only in test** and are never
trained on. Note that PortScan and DDoS are *known, trained-on* classes under this protocol; claims
resting on their detection do not transfer to the zero-day setting.

**Headline metric.** **Macro zero-day PR-AUC**, averaged over the three adequately powered unseen
families: **Bot (n = 1,956), Web Attack Brute Force (n = 1,507), Web Attack XSS (n = 652)**.
Heartbleed (n = 11), Infiltration (n = 36) and SQL Injection (n = 21) are **excluded as underpowered**
and are never reported to four decimal places.

We do not headline the blended "benign versus all unknowns" figure. It is a **size-weighted mixture
that reorders the ranking**, and we know this because it produced a claim of ours — "XGBoost ≈ CNN" —
that we retracted on the strength of the mixture and later had to *un*-retract when a paired test
showed the original claim was right (p = 0.80, n.s.). We cite that episode as evidence for the metric
choice, and it is our own error.

**Duplicate rows, and why the asymmetry is the finding.** 17.0 % of test rows are exact
feature-vector duplicates of training rows. De-duplicating costs the supervised channels
0.0035–0.0049 on the published metric. It costs the zero-day metric **nothing**, because all six
zero-day families measure **0.0 % overlap** with training. Duplication therefore inflates *the
field's* metric and leaves *ours* untouched — this is a property of the comparison, not a flaw in our
numbers.

**Feature transform.** We use `log1p`, justified **on the headline metric**: 0.6299 ± 0.0031 against
0.1606 ± 0.0039 for raw features, over three seeds per arm (Welch t = 163). We note plainly that our
*original* justification for this choice cited the contaminated overall-binary metric, and that the
A/B was re-run on the correct metric. The conclusion was right and its justification was wrong; those
are separate facts, and the re-run was necessary regardless of which way it came out.

---

## §3 The gap, demonstrated four independent ways

**(a) One model, two protocols.** Holding the model fixed and changing only the evaluation protocol
moves XGBoost from **0.9936 to 0.6372** and our CNN from **0.9928 to 0.6446** — a gap of **0.3564**
produced by nothing but the question asked. This is the paper's opening argument and a reader cannot
be expected to notice it unprompted.

**(b) Seven classical baselines.** All seven land in **0.977–0.985** on the published metric, against
the CNN's 0.9928 — the field's regime. On zero-day they span **0.0374 to 0.6049, a factor of 16**.
Logistic regression is **98 % as good as the CNN on the published metric and 17× worse on zero-day.**
⚠️ Two members of this tier are **score-degenerate**: `decision_tree` and `knn` place 50.1 % and
49.8 % of all flows in a single tie block, so their PR-AUC is not comparable to a continuous scorer's.
The best *valid* Tier-A result is the MLP at a three-seed mean of **0.4965** — not the n = 1 figure of
0.5360 that a single run reported. **k-NN is not citable at all**: its macro spans 0.0440–0.4270
across seeds, because the only thing the seed changes is which 50,000 rows it memorises.

**(c) Four deep architectures.** Published metric **0.9854–0.9932**. The relationship with zero-day
capability is not merely weak here, it is **inverted**: the tier's *worst* zero-day model
(Transformer, macro 0.1106) posts 0.9894, while `deep_gru` (macro 0.3029) posts the tier's **highest**
published score, 0.9932. ⚠️ Three caveats travel with this tier. The recurrent models run over the
**feature axis, not time** — the 68 statistics are unordered — which matches published practice and
is therefore the right comparison, but is **not evidence about sequence modelling**. Budgets are
unmatched (the LSTM hit its 30-epoch cap). The Transformer result is **one under-tuned
configuration**, not a claim about attention.

**(d) The base paper's own metric set.** Evaluated on Bizzarri et al.'s five views, we exceed their
reported figures by 18–29 pp on all four known-class views and **reproduce their 1D CNN's zero-day
accuracy almost exactly — 47.85 % against 48.34 %.** What we cannot reproduce is their Hybrid-LTN's
**+12 pp symbolic gain**: our closest reproduction of their model scores **47.24 %**, no better than
our own CNN. ⚠️ This is a comparison in **form, not head-to-head** — different modality (flow features
versus payload bytes), zero-day membership differing by a swap (they hold out PortScan and train
Infiltration; we do the reverse), and different class sizes. Holding the model fixed and changing only
the family mix moves their headline from 48.32 % to 44.38 %, so **composition explains roughly 4 pp of
the missing 12** — it is not explained away, but we say what is controlled.

### §3b Two defects in that zero-day metric, verified arithmetically

**It has no false-positive term.** Their zero-day view contains only attack rows, so precision ≡ 1,
accuracy *is* recall, and F1 = 2A/(1+A) exactly — we reproduce every published F1 from its matching
accuracy to within 0.02 pp. The headline "accuracy 48 → 60 %, F1 65 → 75 %" is therefore **one result
reported twice**, and **a model that flags every flow scores 100 % on both**. We know this failure
mode is reachable because a float32 saturation bug in our own pipeline did exactly that, and was
caught only because our metric has a benign side. **It is also a size-weighted mixture**, the same
defect described in §2.

---

## §4 The mechanism — why a closed-set model cannot reach a novel class

This is the body of the paper. The gap in §3 is not merely unmeasured; it is hard, and we can say
why.

**The synthesis.** A closed-set discriminative model learns only those features that separate the
classes present in its training objective. A novel class is therefore reachable exactly to the extent
that its signature overlaps that learned basis — and where the overlap is empty, the model's output on
that class is not merely poor but **unstable**, because nothing in the objective constrains it.

We establish this on Bot, where the overlap is empty:

- **100 % of Bot flows are classified BENIGN**, mean p(BENIGN) = **0.9984**, on all three seeds. Bot
  is not ambiguous to the model; it is **confidently asserted benign**. This is what kills every
  confidence-based remedy in §5 before it is tried.
- The eight features that separate Bot from benign have **0 of 8 overlap** with the eight the
  known-class task selects. (Eight is the comparison-set size; for Web Brute Force the overlap is 1
  of 8.)
- Consequently the model's Bot ranking is **noise**: cross-seed Spearman **ρ = −0.090**, against
  0.68–0.83 for every other family. RandomForest behaves identically (ρ = 0.068); **the autoencoder
  does not (ρ = 0.827)**. The property therefore belongs to *closed-set discriminative learning*, not
  to neural networks.
- **The information is present.** An oracle given Bot labels reaches PR-AUC **0.9988** from the same
  68 flow features (Web BF 0.9999, XSS 0.9984). ⚠️ The oracle trains on zero-day labels; it is an
  **upper bound, not a method**, and it is excluded from every method comparison in this paper. Its
  role is to establish that the barrier is supervision, not information — and, in passing, that it is
  not modality either: there is no missing information for packet payloads to supply.

**One cause, four symptoms.** This single mechanism accounts for four otherwise unrelated
observations: the clustering-purity lottery we encountered building the knowledge graph, the spread
in Mahalanobis Bot scores, RandomForest's Bot swing across seeds, and the CNN's own failure. We
regard the unification, rather than any individual measurement, as the contribution.

**No standard out-of-distribution score rescues it.** We ran nine scorers — MSP, max-logit, energy at
four temperatures, entropy, ODIN at two settings, and margin — against a falsification threshold of
0.08 macro-Bot **fixed in advance**. The best reaches **0.0783**. ⚠️ We say plainly that this *passed
by two per cent* and do not round it to a clean pass; a threshold set slightly lower would have
flipped the verdict. The one scorer that buys Bot anything (`energy_T1000`, 2.29× chance) does so by
**destroying known-class discrimination**, collapsing macro to 0.0326.

---

## §5 What does not fix it

This section is the expensive part of the paper to obtain, and it is deliberately about our own
architecture as much as anyone else's.

| attempted fix | result |
|---|---|
| **More architecture** (LSTM, GRU, CNN-LSTM, Transformer) | Nothing escapes the top tier upward and nothing touches Bot (best 0.0626, against the knowledge graph's 0.3103). CNN-LSTM lands **0.0031** from the plain CNN, so the **convolutional front-end is doing the work**; pure recurrence halves the score. |
| **More classical baselines** | 16× spread, none competitive (§3b caveats apply). |
| **Benign-only anomaly methods** (VAE, Deep SVDD, OC-SVM, LOF) | **LOF reaches macro 0.3360 ± 0.0135 and does *not* collapse on web attacks** — a correction to our own earlier framing, which attributed that collapse to the benign-only *family* when it is a property of **reconstruction-error scoring**. |
| **The symbolic pillar itself** | **−0.0004 (n.s.)** alone, and it **significantly harms** the system stacked on the knowledge graph (0.6926 → 0.6708, **p < 0.0001**), diluting Bot from 0.2518 to 0.2043. |
| **Calibration** | Isotonic regression reaches ECE **0.0001** on known classes while **zero-day ECE does not move** (0.0387) — a **287×** gap. **The better the calibration, the wider the gap.** |
| **Abstention** | Zero-day precision **does not move (+0.0000)** at any non-degenerate coverage. |
| **A fitted fuser over the channel that actually helps** | **Structurally impossible.** The knowledge-graph channel's score is defined by streaming the *test* set into windows, so it has **no validation-side score at all** — the channel with the largest measured gain cannot enter a combiner fitted on held-out data under any protocol. |

Three of these deserve their consequence stated rather than left implicit.

**The symbolic pillar is a negative result about our own system, and we lead with it rather than
burying it.** We built it, we measured it, and it does not earn its place. Both the loss-level and
representation-level integration points cost macro PR-AUC; the inference-level one is null alone and
harmful in combination.

**Calibration's failure is diagnostic, not incidental.** A calibrator learns a score-to-outcome
mapping from data in which the outcome was observed. For a class the model has never seen, that
mapping does not hold — so the *better* the calibrator fits the known classes, the more confidently
wrong it is on novel ones. The operational consequence is blunt: **p = 0.9 means 90 % for known
attacks and nothing at all for novel ones.** ⚠️ A practical note: isotonic wins on ECE but is
**unusable as an operating point** — 74 distinct values over 114,658 flows, so the 1 %-FPR quantile
lands inside a tie block and the achieved FPR was 0.70 against a 0.01 target. Calibrate with isotonic
for reporting; threshold with Platt.

**Abstention's failure was predicted in advance from §4 and is the mechanism's sharpest consequence.**
Abstention keys on confidence. §4 established that the model is **confidently wrong** on Bot. A
confidence-based rule cannot catch confident-and-wrong, and it does not: zero-day precision is
unchanged to four decimal places across every non-degenerate coverage.

**The scope of the fitted-fuser claim, because we got it wrong once.** The wall applies to channels
whose value is **zero-day-specific**. It does *not* apply to a channel that also carries value on the
known classes the combiner is fitted on. §6 reports a fitted combiner that works, and §7 reports how
we came to state the impossibility too broadly.

---

## §6 What partially works, stated without overclaiming

**The knowledge-graph channel: +0.0528 macro** [+0.0466, +0.0592], p < 0.0001, **3/3 seeds**, lifting
Bot from 0.0446 to 0.2518. This is the only component of our architecture that earns its place.
⚠️ **Its direction is established and its magnitude is not**: against the paired difference's own
standard deviation the effect is 1.7σ, spanning **0.027–0.088**. We report the direction as
established and the magnitude as a range.

**The operational statement is better than the PR-AUC one.** Reaching half of the zero-day flows
requires reviewing **52 %** of all traffic with the CNN, and **29–32 %** with the knowledge graph or
the fusion. That 20-point reduction in review depth is the clearest operational statement of what the
knowledge graph buys, and it is more meaningful than any PR-AUC delta. 🔑 The accompanying finding is
worse news and more important: **at any deployable alert budget you see only known attacks** —
precision is ~1.000 at every budget, with **zero zero-day flows in the top 1,000**. A 100 %-precise
alert stream containing no novel attacks is exactly the failure a headline PR-AUC of 0.64 does not
show.

**A fitted combiner over the CNN and the autoencoder does work** — macro **0.6502 against the CNN's
0.6399** (+0.0103, 3/3 seeds), and **+0.0604 over equal-weight rank fusion of the same two channels**
(3/3 seeds, 2.5σ). It assigns the anomaly channel **17.9 % of absolute weight, positive on every
seed**; it does not learn to ignore it. Fitted on validation, which contains **zero zero-day flows by
construction** — asserted in code rather than assumed — and applied blind to test, achieving an FPR of
0.0100 exactly on all three seeds. ⚠️ **+0.0103 is 0.80σ: direction established, magnitude not.** The
honest sentence is *"a fitted combiner is possible and marginally positive"*, never *"fitted fusion
works"*, and it does not replace the knowledge-graph result.

⚠️ **Parameter-free fusion is not universally the safe choice, and we say so next to our own
parameter-free result.** Equal-weight rank fusion of the CNN and autoencoder **loses to the CNN alone
by −0.0501** (3/3 seeds, 4.34σ). Equal weights cannot express "this channel is worth a sixth of that
one", so they help with a comparable partner and harm with a weak one. **Our +0.0528 is a result about
the knowledge graph, not about equal weighting.**

**The emerging-pattern rule works on growth rate**: lift **5.94×** [5.66, 6.11] over three seeds, at
roughly 81 % recall. ⚠️ Two caveats must travel with it. First, growth works substantially *because
CIC-IDS2017's attacks are scripted into fixed windows* — a real network carrying continuous low-rate
command-and-control would not produce this signal, and Bot's real-world signature is persistence
rather than burstiness. Second, **temporal burstiness of a raw-feature cluster does not require a
knowledge graph**; a reviewer will say this, so we say it first. The knowledge graph's justification
rests on explanation and corroboration, not on this detection number.

🔴 **Two claims we explicitly do not make.** That "the conjunction of criteria gives 81 % precision" —
that was clustering-seed 42 alone, and three seeds give lift 1.73–11.57× and precision 0.122–0.814.
And that the knowledge graph's specified "unexplained cluster" mechanism detects zero-day attacks — it
scores lift ≤ 1.00×, at or below chance, across three representations and three thresholds. The
specified mechanism is dead; the scope is corroboration and explainability.

### The double dissociation — a supporting result, not the lead

The CNN and the autoencoder dissociate on every family, non-overlapping across seeds: XSS **+0.90
(40 SD)**, Web Brute Force **+0.82 (37 SD)**, Bot **+0.0868 (3.9 SD)**, p < 0.0005.

⚠️ **It is a dissociation between two models, not two method families.** RandomForest — a supervised
method — **ties the autoencoder on Bot** (0.1311 versus 0.1314, p = 0.88) while beating it by 0.50 on
macro. We do not write this up as a supervised-versus-unsupervised result; that stronger form is
falsified by our own data.

⚠️ **The web-attack half is not zero-day detection.** The CNN assigns **~90 % of Web Brute Force and
XSS flows to `DoS slowloris`**, a known *attack* class, so their 0.92–0.95 PR-AUC is **absorption into
a known attack**, not detection of a novel one. An earlier explanation of ours — that web attacks
transfer because they resemble the FTP/SSH brute-force families — was tested and **falsified**, and we
do not repeat it.

### Cost is not the objection

The full detection path runs at **7.95 µs per flow (125,762 flows/s)** on one CPU, scoring the entire
test set in 0.91 s; the knowledge graph adds **0.58 µs per flow, +9.2 % over the CNN**. ⚠️ But
**explanation costs 1,898× detection** — Integrated Gradients is 11.95 ms per flow, 84 flows/s.
Explaining every test flow takes 23 minutes; explaining 100 alerts takes **1.19 s**. The rule this
implies — **explain alerts, not flows** — composes with the alert-budget finding above rather than
conflicting with it. We state it explicitly because an "explainable IDS" claim that implies per-flow
explanation is wrong by four orders of magnitude. ⚠️ Throughput figures are meaningless without their
batch size (batch 1 gives 256 flows/s, batch 8192 gives 158,919 — a 620× spread), and upstream
flow-feature extraction is **not** measured here and may dominate a real deployment.

---

## §7 Measurement discipline — a section, not a footnote

We measured the reproducibility of our own pipeline before interpreting any delta, and we recommend
the practice on the strength of what it cost us.

| source of variance | SD | evidence |
|---|---:|---|
| Nondeterminism (fixed seed, determinism off) | **0.0222** | n = 6 |
| Seed variance (determinism on) | **0.0171** | n = 6 |
| Data-split variance (5-fold, model and test fixed) | **0.0228** | 5-fold |
| ⇒ uncertainty on an **absolute** number | **0.0285** | √(0.0228² + 0.0171²) |
| ⇒ threshold for a **shared-split comparison** | **0.0256** | 2·SE·√2 at n = 6 |

**Seed variance and nondeterminism are statistically indistinguishable** (F(5,5) = 1.69, p = 0.58).
Determinism flags are enabled and verified byte-identical across sessions five days apart; pre- and
post-flag runs are different populations and are never pooled.

Five lessons, each of which cost us something:

🔴 **A flow-level significance test cannot rescue a delta below the pipeline's own reproducibility.**
We closed a comparison in our own favour with a paired bootstrap at p = 0.001, then measured the noise
floor and found the gap (+0.0204) was **0.9 SD** — smaller than re-running one model twice. **The
claim is retracted.** This is the single most transferable methodological result in the paper, and it
retracts our own headline.

🔴 **n = 3 is enough for a mean and nowhere near enough for a variance.** Two independent n = 3 SD
estimates **agreed closely with each other and were both wrong by a factor of five**; a fourth seed
moved one of them 5×. Agreement between under-powered estimates reads as corroboration and is not.
**Sample-size adequacy depends on the statistic, not the count.**

🔑 **A paired comparison must be judged against the paired difference's own SD, not the
absolute-number floor.** The 0.0222 floor is run-to-run variance of a single channel; over shared
seeds that common variance **cancels**. We caught this while building a figure whose first version
applied the unpaired floor to paired deltas and rendered a 16.3σ, 3/3-seed effect as noise. ⚠️ That
error ran in the *safe* direction — it would have discarded a real result — but it is the same class
of mistake as the ones that manufacture false positives. **The correct criterion is
direction-consistency across all seeds plus the paired effect size**, and the two can disagree: our
knowledge-graph result is certain in direction (3/3) and uncertain in magnitude (1.7σ).

🔴 **A negative claim needs the same evidentiary standard as a positive one, and ours did not get
it.** We wrote that a fitted fuser was "structurally impossible here" on the strength of **one
two-channel special case**. Running it on the real channel set falsified all three of its predictions
and triggered a falsifier we had written down in advance. **Every safeguard in this project was
pointed at over-claiming a positive result; this was an over-claimed *blocker*, and nothing was
watching that direction.** The surviving claim (§5, last row) is narrower and still sufficient — but
it had to be measured to be found.

⚠️ **A single best run is not a result.** Our best CNN figure, 0.6446, is the **maximum of eleven
runs**; the mean is 0.6217. The honest reproducible baseline is the eleven-run ensemble at **0.6356**,
which beats the mean and *not* the maximum — because the maximum was never a typical result.

---

## §8 Limitations

1. **Single dataset.** Cross-dataset validation on CIC-IDS2018 is **blocked** — the data is not
   available to us — rather than skipped. This is the weakest point in the paper and we state it
   plainly rather than framing it as future work.
2. **Three adequately powered zero-day families, not six.** And Web Brute Force and XSS correlate at
   **r = +0.992** (same capture window, same tool), so the macro average is effectively ⅓ Bot and ⅔
   *one* web signal. Regrouping shifts values by 0.11–0.15 but **preserves every ordering** we report.
3. **Flow features, not payload bytes** — a deviation from the base paper's modality, and our 18–29 pp
   advantage on known-class views is a **modality** advantage rather than an algorithmic one. But we
   answer the "why not payload?" question rather than conceding it: the oracle probe separates every
   powered family from benign **in the flow-feature basis alone** (Bot 0.9988, Web BF 0.9999,
   XSS 0.9984), so the Bot gap is a closed-set-supervision gap and not a modality gap — and §4's
   mechanism would **relocate** to a payload basis rather than dissolve, since a closed-set model on
   payload bytes would select the payload features that separate the same nine classes. The honest
   cost of that choice: payload would replace the web families' *absorption* into `DoS slowloris` with
   genuine detection, which is an honesty gain this paper does not get to claim.
4. **Scripted attack windows** inflate any growth or temporal result (§6).
5. **Behaviour predicates are approximations.** What we call `HighEntropy` is packet-length **standard
   deviation**, not Shannon entropy of the payload, so any "entropy implies encryption" reading would
   be overclaiming. One predicate is constant and another is binary rather than graded.
6. **Our fusion result is transductive.** Rank fusion normalises each channel by its rank *within the
   scored set*, so a flow's fused score depends on the rest of the test set. This is not label
   leakage and not a scoring error — it is ordinary practice for a rank-based metric — but a streaming
   deployment could not compute it without a frozen reference distribution, which is a different
   estimator. **We have not measured that variant** and make no claim about its direction.
7. **No adversarial evaluation.** Named as future work rather than implied.

---

## §9 Conclusion

The metric the CIC-IDS2017 literature publishes is precise, weakly informative about zero-day
capability, and **too coarse in its own reporting regime to separate methods on that axis** — a third
of method pairs are indistinguishable on it while differing twofold or more on the capability the
numbers are used to claim. Underneath that, a closed-set discriminative model cannot reach a novel
class whose signature does not overlap the basis it was trained on, and when the overlap is empty the
model is not merely inaccurate but **unstable**: its ranking of that class is noise. We showed this
with a mechanism, traced four independent symptoms to it, and demonstrated that neither more
architecture, nor classical baselines, nor benign-only anomaly detection, nor a standard OOD battery,
nor calibration, nor abstention, nor our own symbolic pillar removes it.

What partially works — a knowledge-graph corroboration channel, and a fitted combiner over
complementary channels — works marginally and we have bounded both honestly. We regard the diagnosis,
the mechanism, and the cost of the negative result as the contribution, and we have reported the
reproducibility floor that makes those claims checkable, including where it forced us to retract our
own.

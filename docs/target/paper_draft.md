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
> ✅ **All eleven sections are drafted, all thirteen references verified, and one adversarial review
> pass applied (2026-09-09).** Figures are built (`paper_figures.py`, `field_gap.py`) and referenced
> by number.

---

## Abstract

Published intrusion-detection results on CIC-IDS2017 cluster above 99 % on the metric the field
reports, and are routinely used to claim capability against novel attacks. We show that this metric
**cannot resolve that capability**: across 31 methods evaluated identically, **37 of 169 method pairs
(22 %) are statistically indistinguishable on the published metric while differing by a factor of two
or more in macro zero-day PR-AUC**, the worst pair sitting 0.0052 apart on the former and **16.6×**
apart on the latter. The metric is not noisy and not uninformative — its run-to-run standard
deviation is 0.0021 and it correlates with zero-day performance at ρ = +0.582 — it is simply too
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
+0.0528 macro, direction established on 3/3 seeds and magnitude only bounded to 0.027–0.088) and
**two retractions of our own claims — one positive, one negative**. Throughout, we report a measured
reproducibility floor
(SD 0.0222) and express every delta as a multiple of it; doing so retracted one of our own headline
results.

---

## §1 Introduction — a resolution failure

The CIC-IDS2017 literature reports accuracy, F1 and AUC above 99 % with enough regularity that the
numbers have stopped discriminating. That would be unremarkable if those numbers were used only to
claim what they measure — separating benign traffic from attack families the model was trained on.
They are not. They are routinely offered as evidence of capability against *novel* attacks, which is
the capability that matters operationally and the one the metric is least able to speak to.

We make that gap quantitative. ⚠️ **The 40 methods are ours, and that matters for how the claim
should be read.** They are not 40 published systems re-run; they are 40 models we trained under one
protocol — classical baselines, deep architectures, benign-only anomaly detectors, neuro-symbolic
variants and fusions — precisely so that every one is scored identically on both axes, which
published numbers never are. **The step from "these 40" to "the literature" is therefore an
argument, not a measurement**, and it rests on two things we can check: the 40 span the algorithm
families the field publishes, and **they land inside the field's own reported band** (0.977–0.993 on
the published metric). Scoring each on that metric and on **macro zero-day PR-AUC** over held-out
families, we find:

- **37 of 169 comparable method pairs (22 %) are indistinguishable on the published metric while
  differing ≥2× on zero-day capability.** "Indistinguishable" means a difference below **0.0060**,
  two standard deviations of a *difference* derived from a measured median run-to-run SD of
  **0.0021**. We state the band rather than the count alone, because the count is meaningless
  without it.
- The extreme case, `deep_cnn_lstm` versus `linear_svm`, sits **0.0052 apart on the published metric
  and 16.6× apart on zero-day**. We give the extreme only alongside the distribution above; on its
  own it would be cherry-picking.
- Restricting to the field's own reporting regime — the 22 methods scoring ≥0.98, which is where
  published work lives — those methods sit **within 0.0144 of one another and span 18.5×** on
  zero-day. The ≥0.98 cut is chosen *because it is the field's regime*, not because it separates the
  data.

🔴 **These figures exclude 11 tie-degenerate scorers, and the exclusion is not optional.** Of the 42
methods we evaluated, eleven — `decision_tree`, `knn_k5`, `naive_bayes`, four LTN variants and the
four knowledge-graph channels — place roughly half of all flows in a **single tie block**. §3b
explains why that makes their PR-AUC incomparable to a continuous scorer's, and a "≥2× apart on
macro" test is precisely a comparison of PR-AUCs. Including them gives **75 of 249 pairs (30 %)** and
a headline extreme of 17.9×; both are inflated by the same artefact the paper elsewhere warns about,
so we report the excluded population and give the inclusive figures here rather than quietly
choosing the larger one. **The claim survives the exclusion — 22 % and 16.6× — and the rank
correlation barely moves (+0.589 → +0.582).**

**Two stronger versions of this claim are false and we do not make them.** The published metric is
not uninformative about zero-day performance: Spearman ρ = **+0.582** (p = 0.0006) over the
non-degenerate methods, **+0.589** over all 42, and it stays positive within the ≥0.98 regime. Nor is
its spread within its own noise: it is a *precise* measurement, with a median run-to-run SD of
0.0021, roughly ten times below its spread across methods. The metric is precise, weakly informative, and **too coarse in the regime that
matters** — which is a narrower and more useful statement than either strong form, and it is the one
our data support. Both refutations are hard-coded into the output of the script that produces the
figure, so the strong forms cannot be reintroduced by accident.

**Contributions.**

1. A resolution failure, demonstrated across 42 methods scored on a single axis (§3, Fig. 1).
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
produced by nothing but the question asked.

**(b) Seven classical baselines.** All seven land in **0.977–0.985** on the published metric, against
the CNN's 0.9928 — the field's regime. On zero-day they span **0.0374 to 0.6049, a factor of 16**.
Logistic regression is **98 % as good as the CNN on the published metric and 17× worse on zero-day.**
⚠️ Two members of this tier are **score-degenerate**: `decision_tree` and `knn` place 50.1 % and
49.8 % of all flows in a single tie block, so their PR-AUC is not comparable to a continuous scorer's.
**This is the same property that removes eleven methods from §1's headline** — it is a general
exclusion criterion in this paper, not a Tier-A footnote, and `field_gap.py` reports both populations
so the effect of applying it is visible rather than assumed.
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

The gap in §3 is not merely unmeasured; it is hard, and we can say why.

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
  ⚠️ **This is a stability statistic computed over three seeds, and §7 warns that n = 3 is far too
  few to estimate a dispersion.** We rely on it here for one reason, which we state rather than
  assume: the quantity is not marginal. Bot sits at ρ ≈ 0 while every other family sits at 0.68–0.83
  — a categorical separation, not a difference of degree — and it reproduces across two unrelated
  model families while the autoencoder, on the same three seeds, returns 0.827. **A three-seed
  estimate cannot tell us that Bot's ρ is −0.090 rather than −0.02 or +0.05; it is entirely adequate
  to tell us it is not 0.7.** Only the second claim is load-bearing.
- **The information is present.** An oracle given Bot labels reaches PR-AUC **0.9988** from the same
  68 flow features (Web BF 0.9999, XSS 0.9984). ⚠️ The oracle trains on zero-day labels; it is an
  **upper bound, not a method**, and it is excluded from every method comparison in this paper. Its
  role is to establish that the barrier is supervision, not information — and, in passing, that it is
  not modality either: there is no missing information for packet payloads to supply.

**One cause, four symptoms — and we separate what is measured from what is inferred.** The
mechanism accounts for four otherwise unrelated observations: the clustering-purity lottery we hit
building the knowledge graph, the spread in Mahalanobis Bot scores, RandomForest's Bot swing across
seeds, and the CNN's own failure. ⚠️ **Two of those links are measured and two are argued.**
RandomForest's instability is measured on the same axis as the CNN's (ρ = 0.068 against 0.827 for the
autoencoder), and the CNN's is the direct observation. The purity lottery and the Mahalanobis spread
are **independently observed phenomena that the mechanism explains**; we did not run a manipulation
that isolates the mechanism as their cause. We regard the unification as the contribution, and we
label it as an explanatory claim rather than a fifth measurement.

🔑 **The mechanism replicates on an independent capture, with the confound removed.** A standing
objection to §4 is that Bot is simply *rare* in CIC-IDS2017 (n = 1,956), so its failure might be a
sample-size artefact rather than a representational one. **CSE-CIC-IDS2018 supplies the control: Bot
there is abundant — and the CNN scores it at 0.83× chance, BELOW a random ranker**, against 1.31× on
2017. Infilteration behaves the same way (0.96×). Meanwhile the same model reaches **20.1×** on
Brute Force -Web and **47.3×** on Brute Force -XSS in that capture. Abundance does not buy
reachability, and scarcity was never the explanation: **reachability tracks overlap with the learned
basis**, which is what §4 claims. ⚠️ The 2018 arm is matched to 2017's training size (883,796 flows)
so nothing here is confounded with four times the data.

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
| **A fitted fuser over the channel that actually helps** — ⚠️ **scope: this row is about the knowledge-graph channel only; a fitted combiner over other channels *does* work, see §6** | **Structurally impossible for this channel.** The knowledge-graph score is defined by streaming the *test* set into windows, so it has **no validation-side score at all** — the channel with the largest measured gain cannot enter a combiner fitted on held-out data under any protocol. |

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

**The knowledge-graph channel is the only component of our architecture that earns its place**, and
its size depends on one hyper-parameter we had never swept. At the cluster count used throughout our
earlier experiments (k = 200) it is **+0.0528 macro** [+0.0466, +0.0592], p < 0.0001, **3/3 seeds**,
lifting Bot from 0.0446 to 0.2518. Sweeping k shows the fused macro is **monotone** in it, in both
knowledge-graph variants and at every step, 3/3 seeds:

| k | 100 | 200 | 400 | 800 |
|---|---:|---:|---:|---:|
| fused macro (`s_kg`) | 0.6493 | 0.6792 | 0.6960 | **0.7123** |
| fused macro (`causal`) | 0.6622 | 0.6930 | 0.6968 | **0.7032** |

At **k = 800 the fusion reaches macro 0.7123 against the CNN's 0.6399, +0.0724 on 3/3 seeds.**

⚠️ **That +0.0724 is selected on test and we do not report it as the improvement.** We re-selected
k on a stratified half of the test set with an rng fixed independently of any model seed, and report
on the half never used for selection: **+0.0305 at 2.86σ, 3/3 seeds.** That is the honest number.
The same protocol is what caught a companion result — a weighted-fusion variant worth +0.007 on the
selection half is **−0.0008 and direction-inconsistent** on the reporting half, and without the split
it would have shipped as a gain.

⚠️ **Direction established, magnitude not.** Against the paired difference's own standard deviation
the k = 200 effect is 1.7σ, spanning **0.027–0.088**. We report direction as established and
magnitude as a range throughout.

⚠️ **We do not claim `s_kg` is the better variant.** The two variants' ranking **flips with k** —
`causal` leads at k = 200, `s_kg` at k = 800 — neither cross-variant gap is tested paired, and both
sit inside the 0.0285 that an absolute number in our pipeline carries. The **monotonicity in k** is
the established finding; the variant choice is not.

**A single operating point hides the shape of the result, so we sweep the false-alarm rate.**
Recall of flows from families the model has never seen, three seeds, threshold set on benign flows
alone:

| recall of unknown flows @ FPR | 0.1 % | 1 % | 5 % | 10 % |
|---|---:|---:|---:|---:|
| CNN alone | **47.3 %** | 48.3 % | 54.2 % | 60.4 % |
| CNN + KG (k = 800) | **45.8 %** | **57.6 %** | 72.1 % | 91.6 % |
|  of which **Bot** | **0.0 %** | 23.2 % | 46.6 % | 85.2 % |
|   (CNN alone, Bot) | 0.0 % | 0.1 % | 9.5 % | 19.9 % |

🔴 **At the tightest budget the knowledge graph COSTS 1.5 points, and Bot is 0.0 % for both
models.** The gain is real but it begins around a 1 % false-alarm rate; **no configuration we built
reaches Bot at a tight alert budget.** We report this because quoting only the 1 % column — which is
the column that flatters us — would conceal it, and because it is the same error as reporting a
size-weighted blend in place of a macro. ⚠️ The 10 % column is reported for shape only: on 55,237
benign test flows it is roughly **5,500 false alerts**, and is not a deployable operating point.

**The review-depth statement is better than the PR-AUC one.** Reaching half of the zero-day flows
requires reviewing **52 %** of all traffic with the CNN, and **29–32 %** with the knowledge graph or
the fusion. That 20-point reduction in review depth is the clearest operational statement of what the
knowledge graph buys, and it is more meaningful than any PR-AUC delta. ⚠️ **It inherits the
scripted-window caveat below**: the knowledge-graph channel's advantage rests on temporal
concentration that this capture's attack schedule creates, so the depth reduction should be read as
an upper bound on what a real network would give. 🔑 The accompanying finding is
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

### The double dissociation — a supporting result, and what replication does to it

The CNN and the autoencoder dissociate on every family, non-overlapping across seeds: XSS **+0.90
(40 SD)**, Web Brute Force **+0.82 (37 SD)**, Bot **+0.0868 (3.9 SD)**, p < 0.0005.

🔑 **We replicated it on CSE-CIC-IDS2018, and the two halves come apart.** Only **lift**
(PR-AUC ÷ prevalence) is comparable across captures — raw PR-AUC is bounded below by prevalence and
the two datasets differ by orders of magnitude on exactly the families in question. We report lift
and nothing else, having made the raw-PR-AUC comparison ourselves first and withdrawn it.

| Bot, lift over chance | CIC-IDS2017 | CSE-CIC-IDS2018 |
|---|---:|---:|
| CNN | 1.31× | **0.83×** |
| autoencoder | 3.84× | 1.09× |
| **autoencoder − CNN** | **+2.53×** | **+0.26×** |

**The direction replicates on an independent capture; the magnitude does not.** The autoencoder's
Bot advantage shrinks by a factor of **9.7**, and at 1.09× it sits close enough to chance that 2018
lends no support to the reading *"an anomaly method reaches Bot."* ⚠️ We cannot even test whether
1.09× beats chance: our 2018 record persists per-family lift as a mean with no per-seed spread, so a
margin of 0.09× is not distinguishable from noise. **We therefore claim the direction and drop the
magnitude**, and we treat the 2017 magnitude as a property of that capture.

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

1. **~~Single dataset.~~ ✅ RESOLVED — and the retraction chain is worth keeping visible.** We first
   wrote that cross-dataset validation on CIC-IDS2018 was ~~*blocked* because the data was
   unavailable~~. That was **wrong** — CSE-CIC-IDS2018 is on the AWS Registry of Open Data and
   downloads without an account (`aws s3 sync s3://cse-cic-ids2018/ <dir> --no-sign-request`), under
   a licence permitting redistribution with citation. We then wrote that the honest limitation was
   ~~that we did not do it~~. **We have now done it**: four method arms × three seeds, training size
   matched to 2017's 883,796 flows, reported in §4 and §6. The mechanism replicates with the
   rarity confound removed, and the double dissociation replicates in direction but not magnitude.
   ⚠️ **What remains limited:** two captures from the *same producer* under related methodology is
   not evidence of generality across network environments, and **7 of the 10 published 2018 flow CSVs
   are Excel-truncated at 2²⁰ rows, chronologically** — a defect in the distributed artefact that we
   detected and worked around, and that anyone reusing those files should know about.
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

## §9 Related work

**The dataset, and what is already known to be wrong with it.** CIC-IDS2017 was released by
Sharafaldin et al. [1] and has become one of the most reported-on benchmarks in the field. Engelen
et al. [2] audited it and found defects in traffic generation, flow construction, feature extraction
and labelling, releasing corrected processing; a follow-up quantified how much detection performance
those errors move [3]. Goldschmidt and Chudá [4] survey 89 NIDS datasets and argue that data quality
and reporting practice, rather than data scarcity alone, now limit the field.

**Our claim is adjacent to theirs and not the same one.** That line of work asks whether the *labels
and flows* are correct. We take the data as given and ask what the *metric computed on it* can
resolve. The two are complementary, and one of our results sits precisely at the join: 17 % of test
rows are exact duplicates of training rows, which inflates the published metric — but **all six
zero-day families measure 0.0 % overlap**, so the contamination is asymmetric and leaves the
zero-day metric untouched. A data-quality critique would flag the duplication; only a
metric-resolution analysis shows that it matters for one number and not the other.

**Methodological critiques of machine learning in security.** Sommer and Paxson [5] argued that
intrusion detection is unusually hostile to machine learning, in large part because the interesting
events lie *outside the closed world* the model was trained on; the argument received a
Test-of-Time award and remains the reference statement of the problem. Arp et al. [6] catalogue ten
recurring pitfalls across 30 top-tier security papers and give recommendations for avoiding them.

**We are downstream of both, and we try to supply what they ask for.** Sommer and Paxson's claim is
qualitative — machine learning struggles with novelty. §4 supplies a **mechanism** for one instance
of it (empty overlap between the novel class's discriminative features and the trained basis) and
shows the failure is not merely inaccuracy but **instability**: the model's ranking of that class is
noise, cross-seed ρ = −0.090. §1 supplies the **quantitative** counterpart — 33 % of method pairs are
indistinguishable on the published metric while differing ≥2× on the capability at issue. Against
Arp et al., §7 attempts what their recommendations imply and few papers actually do: measure the
pipeline's own reproducibility floor, express every delta as a multiple of it, and **report the
claims of ours that the floor retracted**.

**Neuro-symbolic intrusion detection.** Logic Tensor Networks [7] provide the fuzzy-logic-to-loss
machinery this line of work builds on. Bizzarri et al. [8] apply it to NIDS: a 1D CNN trained with a
hybrid cross-entropy plus satisfiability loss, reporting improved unknown-attack accuracy over a
vanilla CNN on CIC-IDS2017. That paper is our starting point, and a recent survey by the same group
[9] places it in a fast-growing literature.

🔴 **We reproduce their CNN and cannot reproduce their symbolic gain.** On their own metric our
figures are 47.85 % against their 48.34 % for the 1D CNN — close agreement — while our nearest
reproduction of their hybrid model scores 47.24 %, no better than our own CNN (§3d). We report this
as a comparison **in form, not head-to-head**: the modality differs (flow features versus payload
bytes), the zero-day membership differs by a swap, and the class sizes differ, with composition
accounting for roughly 4 of the missing 12 points. We also identify two arithmetic defects in the
metric that gain is reported on (§3b). **And our own symbolic pillar fares no better** — it is null
alone and significantly harmful in combination (§5), which is a negative result about our
architecture, not only about theirs.

**Open-set recognition and out-of-distribution scoring.** Treating unseen attack families as an
open-set problem has a long history in this domain [10], and the general OOD literature supplies
post-hoc scorers that need no retraining: maximum softmax probability [11], temperature-scaled and
input-perturbed variants [12], and energy-based scores [13]. §4 evaluates nine such scorers against a
falsification threshold fixed in advance. **None rescues the hard family**, and the one that moves it
at all does so by destroying known-class discrimination. We report that as a bounded negative result
about post-hoc scoring on this problem, not as a claim about OOD detection in general.

### References

> ✅ **Citation-verification status: all thirteen references were confirmed against a primary or
> authoritative source (publisher page, arXiv record, DOI, or — for [8] — the PDF held in this
> repository).** The bibliographic pass was completed 2026-09-09.
>
> 🔴 **It caught a real error, which is why the pass was not skipped.** Reference [10] was drafted as
> *"E. M. Rudd et al."* from memory; the first author is **Steve Cruz**, and Rudd is third. An
> unchecked citation gets the same treatment here as an unchecked number, and this is what that
> policy bought.

1. I. Sharafaldin, A. H. Lashkari, A. A. Ghorbani. *Toward Generating a New Intrusion Detection
   Dataset and Intrusion Traffic Characterization.* ICISSP 2018, pp. 108–116.
2. G. Engelen, V. Rimmer, W. Joosen. *Troubleshooting an Intrusion Detection Dataset: the CICIDS2017
   Case Study.* IEEE Security and Privacy Workshops (SPW), 2021.
3. M. Lanvin, P.-F. Gimenez, Y. Han, F. Majorczyk, L. Mé, É. Totel. *Errors in the CICIDS2017
   Dataset and the Significant Differences in Detection Performances It Makes.* CRiSIS 2022, Lecture
   Notes in Computer Science vol. 13857, Springer, 2023. doi:10.1007/978-3-031-31108-6_2
4. P. Goldschmidt, D. Chudá. *Network Intrusion Datasets: A Survey, Limitations, and
   Recommendations.* Computers & Security, vol. 156, 2025, art. 104510.
5. R. Sommer, V. Paxson. *Outside the Closed World: On Using Machine Learning for Network Intrusion
   Detection.* IEEE Symposium on Security and Privacy, 2010, pp. 305–316.
6. D. Arp, E. Quiring, F. Pendlebury, A. Warnecke, F. Pierazzi, C. Wressnegger, L. Cavallaro,
   K. Rieck. *Dos and Don'ts of Machine Learning in Computer Security.* USENIX Security Symposium,
   2022, pp. 3971–3988.
7. S. Badreddine, A. d'Avila Garcez, L. Serafini, M. Spranger. *Logic Tensor Networks.* Artificial
   Intelligence, vol. 303, 2022, art. 103649. doi:10.1016/j.artint.2021.103649
8. A. Bizzarri, B. Jalaian, F. Riguzzi, N. D. Bastian. *A Neuro-Symbolic Artificial Intelligence
   Network Intrusion Detection System.* ICCCN 2024.
9. A. Bizzarri, C. Yu, B. Jalaian, F. Riguzzi, N. D. Bastian. *Neurosymbolic AI for Network
   Intrusion Detection Systems: A Survey.* Journal of Information Security and Applications,
   vol. 94, 2025, art. 104205.
10. S. Cruz, C. Coleman, E. M. Rudd, T. E. Boult. *Open Set Intrusion Recognition for Fine-Grained
    Attack Categorization.* IEEE International Symposium on Technologies for Homeland Security (HST),
    2017.
11. D. Hendrycks, K. Gimpel. *A Baseline for Detecting Misclassified and Out-of-Distribution Examples
    in Neural Networks.* ICLR 2017.
12. S. Liang, Y. Li, R. Srikant. *Enhancing the Reliability of Out-of-Distribution Image Detection in
    Neural Networks.* ICLR 2018.
13. W. Liu, X. Wang, J. D. Owens, Y. Li. *Energy-Based Out-of-Distribution Detection.* Advances in
    Neural Information Processing Systems (NeurIPS), vol. 33, 2020.

---

## §10 Reproducibility

**What is released.** All 58 analysis and pipeline scripts, the protocol configuration
(`config.yaml`), pinned dependencies, the 9 figures, the 70 metadata files that every number in this
paper is drawn from, and the **append-only research record** — 190 logged runs with their seeds,
parameters and results. The code is MIT-licensed.

**What is not, and why.** The **CIC-IDS2017 dataset is not redistributed**; it carries its own usage
terms and is obtained from its publisher. **Trained model weights are not released either** — they
are large, per-seed, and regenerable, and the determinism guarantee below makes regeneration the
better path than download.

**Environment.** Python 3.11.9, TensorFlow 2.15.1 (Keras 2), CPU only, dependencies pinned to exact
versions. All results in this paper were produced on one 32-core AMD workstation; no GPU is used or
required.

**Determinism.** Deterministic operations are enabled and thread counts are **pinned** rather than
left to the core-count default, because op-level determinism alone does not fix reduction order.
This was verified rather than assumed: two full 50-epoch runs of the same seed produce **byte-
identical** output, and a third run five days later in a different session reproduced the same figure
to twelve decimal places. §7 reports what that cost — 2–7 % throughput, and nothing measurable
elsewhere.

⚠️ **The determinism guarantee is forward-looking only.** Results computed **before** the flags
landed came from a process with a run-to-run SD of 0.0222 and are **not** reproducible at fixed seed.
Pre- and post-flag runs are different populations and we never pool them. A reader re-running the
pipeline today should reproduce the post-flag figures and should **not** expect to reproduce the
pre-flag ones exactly; where a number in this paper is pre-flag, §7's floor is the honest error bar.

**One entry point.** `run_all.py` declares the 19 pipeline stages in order together with the
artifacts each writes. Its **default mode verifies rather than executes** — it reports which stage
outputs are present on disk — and `--run` executes the sequence, with `--from <stage>` to resume.
Making a full CPU retrain the default behaviour of something called `run_all` would be a foot-gun.

⚠️ **An honest limit we do not smooth over: the stage sequence has been *checked* end to end and has
never been *executed* end to end in one pass.** Every stage has run individually, most of them dozens
of times, but *"each stage works"* and *"the sequence works from a clean checkout"* are different
claims and only the first is evidenced. `--run` is offered as a convenience, not as a validated
reproduction path.

**Two mechanical checks ship with the artifact**, both of which exist because the corresponding
mistake was actually made here:

- `lint_conventions.py` enforces the conventions that have lapsed in this project, **naming the
  incident behind each one** — an encoding bug fixed three times as separate incidents, a timestamp
  parser that silently reordered every test row, a script count that disagreed with disk.
- `verify_draft.py` checks **every quantitative claim in this paper against the metadata files that
  produced it**: it pulls each value from its source JSON, formats it as the paper should state it,
  and asserts the string is present. Current state: **52 verified, 0 mismatched.** It exists because
  the first draft misquoted a throughput figure and that was caught by accident rather than by any
  check. ⚠️ It verifies **transcription, not interpretation** — it cannot tell you a caveat is
  missing or a claim overreaches its evidence.

**Six claims in this paper have no machine-readable record** and are flagged as such by that checker:
the split sizes, the zero-day family counts, the base paper's published figures, the per-method
figures in Tiers A and B, the double-dissociation standard-deviation multiples, and the Web Brute
Force / XSS correlation. We list them rather than hiding them; that set is what a reader must check
by hand, and a checker that silently skips what it cannot verify is worse than no checker.

---

## §11 Conclusion

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

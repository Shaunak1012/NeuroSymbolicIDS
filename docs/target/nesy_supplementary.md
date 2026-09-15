# Supplementary Material — Knowledge the Network Already Has

*Anonymous submission. Supplementary material is not counted toward the page limit.*

> **Build note — not part of the submission.** Revised from the corresponding sections of
> [paper_draft.md](paper_draft.md). `verify_draft.py` checks this file together with
> [nesy_body.md](nesy_body.md), so every recorded number must still appear in one of the two. The
> build script strips this block on conversion to the PMLR template.

| appendix | master-draft source |
|---|---|
| A — Protocol and metric | Appendix A Protocol and metric |
| B — The metric-resolution gap | #The metric failure + Appendix B |
| C — The mechanism, extended | Appendix C The mechanism |
| D — What does not fix it, and what partially works | Appendix D |
| E — Measurement practice and the Arp et al. audit | Appendix E |
| F — Limitations, extended | Appendix F |
| G — Related work, extended | Appendix G |
| H — Reproducibility | Appendix H |

---

## Appendix A — Protocol and metric

**Data and split.** We use the CIC-IDS2017 flow features, 68 numeric features per flow. Nine attack
families and benign traffic are treated as known and split 80/10/10 with stratification, with benign
traffic under-sampled to 1:1. This gives 883,796 training, 110,475 validation and 114,658 test flows. Six
rare families (Bot, Heartbleed, Infiltration, and Web Attack Brute Force, XSS and SQL Injection) appear
only in the test set and are never used in training. PortScan and DDoS are known classes under this
protocol, so any result that depends on detecting them says nothing about the zero-day setting.

**Main metric.** We report macro zero-day PR-AUC, averaged over the three unseen families with enough
samples: Bot (n = 1,956), Web Attack Brute Force (n = 1,507) and Web Attack XSS (n = 652). Heartbleed
(n = 11), Infiltration (n = 36) and SQL Injection (n = 21) are too small. We leave them out of the
average and never report them to four decimal places.

We do not use the blended "benign versus all unknowns" score as a main result. It weights families by
size, and this changes the ranking of methods. We learned this from our own mistake. Based on the
blended score we withdrew an earlier claim that XGBoost and the CNN perform about the same, and a paired
test later showed that the original claim had been correct (p = 0.80, n.s.).

**Duplicate rows.** 17.0 % of test rows are exact feature-vector duplicates of training rows. Removing
them lowers the supervised models' scores on the commonly published metric by 0.0035–0.0049. It has no
effect on the zero-day metric, since all six zero-day families have 0.0 % overlap with the training set.
Duplication therefore inflates the metric most papers report and leaves ours unchanged. This is a
difference between the two metrics rather than a problem with our numbers.

**Feature transform.** We apply `log1p` to the features. On the main metric this gives 0.6299 ± 0.0031,
against 0.1606 ± 0.0039 with raw features, over three seeds per setting (Welch t = 163). Our original
reason for the choice relied on the contaminated overall binary metric, so we repeated the comparison on
the correct metric. The choice turned out to be right, but the first justification for it was not, and
the repeat was needed either way.

---

## Appendix B — The metric-resolution gap

### Motivation

Accuracy, F1 and AUC above 99 % are reported on CIC-IDS2017 so often that these numbers no longer
distinguish between methods. That would matter less if they were only used for what they measure, which
is separating benign traffic from attack families seen in training. In practice they are often presented
as evidence that a system can detect new attacks, which is the capability that matters most in operation
and the one these metrics say least about.

We try to put a number on this gap. The 40 methods in the analysis are models we trained ourselves under
one protocol: classical baselines, deep architectures, benign-only anomaly detectors, neuro-symbolic
variants and fusions. We did this so that every method is scored in the same way on both metrics, which
is never the case for numbers collected from different papers. Extending the conclusion from these 40
models to the published literature is therefore an argument and not a measurement. It rests on two
things we can check: the models cover the algorithm families that appear in the literature, and their
scores on the published metric (0.977–0.993) fall inside the range that papers report.

### Main findings

Scoring every method on the published metric and on macro zero-day PR-AUC gives the following.

- 37 of 169 comparable method pairs (22 %) cannot be distinguished on the published metric but differ by
  a factor of two or more on zero-day performance. We treat two scores as indistinguishable when they
  differ by less than 0.0060, which is two standard deviations of a difference, based on a measured
  median run-to-run SD of 0.0021. The threshold is stated because the count means little without it.
- The most extreme pair, a CNN-LSTM and a linear SVM, is 0.0052 apart on the published metric and 16.6×
  apart on zero-day PR-AUC. We give this example only together with the distribution above, since on its
  own it would be a selective choice.
- If we restrict attention to the 22 methods that score at least 0.98, which is the range in which
  published results usually fall, those methods lie within 0.0144 of each other and span a factor of
  18.5 on zero-day PR-AUC. The 0.98 cut-off was chosen because it matches reporting practice, not
  because it happens to separate the data.

**Excluded scorers.** These figures leave out 11 of the 42 methods we evaluated: a decision tree, k-NN
(k = 5), naive Bayes, four LTN variants and the four knowledge-graph channels. Each of them assigns
roughly half of all flows the same score. PR-AUC computed over such a large tie block is not comparable
with PR-AUC from a continuous scorer (see part (b) below), and the "two times apart" test is a
comparison of PR-AUC values. With these methods included the figures become 75 of 249 pairs (30 %) and an
extreme ratio of 17.9×. Both are inflated by the tie artefact, so we report the smaller figures in the
paper and give the larger ones here. The conclusion is the same either way (22 % and 16.6×), and the rank
correlation hardly changes (+0.589 → +0.582).

**Two stronger claims that our data do not support.** First, the published metric is not unrelated to
zero-day performance. The Spearman correlation is ρ = +0.582 (p = 0.0006) over the non-degenerate
methods and +0.589 over all 42, and it remains positive among the methods scoring at least 0.98. Second,
the spread in the published metric is not just noise. Its median run-to-run SD of 0.0021 is about ten
times smaller than its spread across methods. What the data do support is that the metric is precise and
weakly informative, but too coarse in the range where results are reported. The analysis code prints
both of these checks with every run, so the stronger claims are not reintroduced by mistake.

### Four independent views of the gap

**(a) One model, two protocols.** If the model is held fixed and only the evaluation protocol changes,
XGBoost goes from 0.9936 to 0.6372 and our CNN from 0.9928 to 0.6446. The difference of 0.3564 comes
entirely from the question being asked.

**(b) Seven classical baselines.** All seven score 0.977–0.985 on the published metric, compared with
0.9928 for the CNN, which is the range reported in the literature. Their zero-day scores run from 0.0374
to 0.6049, a factor of 16. Logistic regression reaches 98 % of the CNN's published-metric score while
being 17× worse on zero-day detection. Two of these baselines produce degenerate scores: the decision
tree and k-NN put 50.1 % and 49.8 % of all flows into a single tie block, so their PR-AUC cannot be
compared with that of a continuous scorer. This is the same criterion that removes eleven methods from
the main figures above, and we apply it throughout the paper while reporting both populations. The best
valid classical result is the MLP, with a three-seed mean of 0.4965 (a single run had given 0.5360). The
k-NN result cannot be cited at all. Its macro score ranges from 0.0440 to 0.4270 across seeds, because
the seed only changes which 50,000 training rows it stores.

**(c) Four deep architectures.** These score 0.9854–0.9932 on the published metric. Here the relationship
with zero-day performance is reversed. The Transformer has the lowest zero-day score in the group (macro
0.1106) but scores 0.9894, while the GRU (macro 0.3029) has the highest published-metric score, 0.9932.
Three caveats apply. The recurrent models run over the feature dimension rather than over time, since the
68 statistics have no order. This follows common practice and so is the right comparison, but it says
nothing about sequence modelling. Training budgets were not matched (the LSTM reached its limit of 30
epochs). The Transformer result comes from a single configuration with little tuning and is not a
statement about attention models in general.

**(d) The base paper's metrics.** On the five views used by Bizzarri et al. [8], our scores exceed their
reported figures by 18–29 percentage points on all four known-class views. On zero-day accuracy we
reproduce their 1D CNN closely, with 47.85 % against 48.34 %. We cannot reproduce the +12 percentage
point gain they report for their hybrid LTN model. Our closest reproduction of that model scores
47.24 %, which is no better than our CNN. The comparison is approximate rather than direct. The input
modality differs (flow features instead of payload bytes), the zero-day sets differ by one swap (they
hold out PortScan and train on Infiltration, and we do the reverse), and the class sizes differ. Keeping
the model fixed and changing only the family mix moves their headline from 48.32 % to 44.38 %, so the
composition of the zero-day set accounts for roughly 4 of the 12 missing points.

### Two defects in the base paper's zero-day metric

**No false-positive term.** Their zero-day view contains only attack rows. Precision is therefore always
1, accuracy equals recall, and F1 = 2A/(1+A). Using this formula we recover every published F1 value from
the corresponding accuracy to within 0.02 percentage points. The reported improvement from accuracy
48 → 60 % and F1 65 → 75 % is thus a single result stated twice, and a model that flags every flow as an
attack would score 100 % on both. This is not a hypothetical case: a float32 saturation bug in our own
pipeline once produced exactly that behaviour, and we noticed it only because our metric includes benign
traffic.

**Size weighting.** The metric also mixes families in proportion to their size, which is the problem
described in Appendix A.

---

## Appendix C — The mechanism, extended

### Why a closed-set model cannot reach a novel class

Appendix B shows that zero-day ability is poorly measured. This appendix argues that it is also hard to
achieve, and explains why.

A closed-set discriminative model learns the features that separate the classes in its training
objective. A novel class can then be reached only to the extent that its signature overlaps this learned
basis. When there is no overlap, the model's output on that class is not only poor but unstable, because
nothing in the objective constrains it. Bot is such a case.

- On all three seeds, 100 % of Bot flows are classified as BENIGN, with a mean p(BENIGN) of 0.9984. The
  model is confident that Bot traffic is benign, which is why the confidence-based remedies in Appendix D
  cannot work.
- The eight features that best separate Bot from benign traffic share 0 of 8 with the eight features
  selected by the known-class task. (We compare sets of eight; for Web Brute Force the overlap is 1 of 8.)
- The step from no overlap (unreachable) to one shared feature (reachable) is where the corrected labels
  hurt our argument, and we describe the damage here. Web Brute Force appeared reachable because its
  PR-AUC was 0.92–0.95. With labels that exclude attack flows carrying no payload, this falls to 0.0072
  (2.1× chance). The ordering remains, since Web Brute Force is above chance on every seed and Bot is
  not, but the size of the effect is mostly gone. The unreachable direction is well supported. The
  reachable direction now amounts to a consistent sign over two families. Appendix E has the details.
- The model's ranking of Bot flows is therefore close to random. The Spearman correlation between seeds is
  ρ = −0.090, against 0.68–0.83 for every other family. A random forest behaves the same way
  (ρ = 0.068), while the autoencoder does not (ρ = 0.827). The instability belongs to closed-set
  discriminative learning and not to neural networks specifically.
- This is a stability statistic over three seeds, and Appendix E notes that three seeds are far too few
  to estimate a dispersion. We still use it because the difference is large. Bot sits near ρ = 0 while
  every other family sits between 0.68 and 0.83, the pattern appears in two unrelated model families, and
  the autoencoder gives 0.827 on the same three seeds. Three seeds cannot tell us whether Bot's value is
  −0.090, −0.02 or +0.05, but they are enough to show that it is not 0.7, and the argument only needs the
  latter.
- The information needed to detect Bot is present. An oracle trained with Bot labels reaches a PR-AUC of
  0.9988 from the same 68 flow features (Web Brute Force 0.9999, XSS 0.9984). The oracle uses zero-day
  labels, so it is an upper bound and not a method, and we exclude it from every method comparison. It
  shows that the barrier is the lack of supervision rather than missing information. It also shows that
  input modality is not the barrier, because there is no missing information for packet payloads to
  provide.

**One cause for four observations.** The mechanism accounts for four observations that otherwise seem
unrelated: the variability in cluster purity we met when building the knowledge graph, the spread of
Mahalanobis scores on Bot, the random forest's changing Bot results across seeds, and the CNN's own
failure. Two of these links are measured and two are argued. The random forest's instability is measured
on the same statistic as the CNN's (ρ = 0.068, against 0.827 for the autoencoder), and the CNN's failure
is observed directly. The purity variability and the Mahalanobis spread are separate observations that the
mechanism would explain, but we did not run an intervention that isolates the mechanism as their cause. We
present the connection as an explanation, not as a further measurement.

**Replication on an independent capture.** One could object that Bot is simply rare in CIC-IDS2017
(n = 1,956) and that its failure is a sample-size effect. CSE-CIC-IDS2018 allows this to be checked,
because Bot is plentiful there. The CNN nevertheless scores Bot at 0.83× chance on that capture, worse
than a random ranker, compared with 1.31× on 2017. Infilteration (the 2018 label) behaves similarly
(0.96×). On the same capture the model reaches 20.1× on Brute Force -Web and 47.3× on Brute Force -XSS.
More samples do not make Bot reachable, and rarity was not the explanation. Reachability follows overlap
with the learned basis. The 2018 experiment uses the same training size as 2017 (883,796 flows), so it is
not confounded by having four times as much data.

**Out-of-distribution scores.** We evaluated nine post-hoc scorers: maximum softmax probability,
max-logit, energy at four temperatures, entropy, ODIN at two settings, and the margin between the top two
classes. The falsification threshold, fixed before running them, was 0.08 macro PR-AUC on Bot. The best
scorer reaches 0.0783. This is only about two per cent below the threshold, and a slightly lower threshold
would have given the opposite verdict. The only scorer that improves Bot at all (energy with T = 1000,
2.29× chance) does so by destroying known-class discrimination, and its macro score falls to 0.0326.

---

## Appendix D — What does not fix it, and what partially works

### What does not fix it

This part of the study took the most effort, and much of it concerns our own architecture.

| attempted fix | result |
|---|---|
| More architectures (LSTM, GRU, CNN-LSTM, Transformer) | None moves above the top group and none improves Bot (best 0.0626, against 0.3103 for the knowledge graph). The CNN-LSTM is within 0.0031 of the plain CNN, so the convolutional front end does most of the work; pure recurrence halves the score. |
| More classical baselines | A 16× spread and nothing competitive (caveats in Appendix B). |
| Benign-only anomaly detectors (VAE, Deep SVDD, OC-SVM, LOF) | LOF reaches a macro score of 0.3360 ± 0.0135 and does not collapse on web attacks. We had earlier attributed that collapse to benign-only methods in general; it is actually a property of reconstruction-error scoring. |
| The symbolic component | −0.0004 (n.s.) on its own; combined with the knowledge graph it significantly lowers performance (0.6926 → 0.6708, p < 0.0001) and reduces Bot from 0.2518 to 0.2043. |
| Calibration | Isotonic regression reaches an ECE of 0.0001 on known classes, while zero-day ECE stays at 0.0387, a 287× gap. Better calibration on known classes widens the gap. |
| Abstention | Zero-day precision does not change (+0.0000) at any non-degenerate coverage. |
| Training on a second dataset (known classes of CSE-CIC-IDS2018, doubling the training set) | Harmful: −0.1461 macro against a seed-matched control, better on 0/3 seeds, consistent in direction. The damage comes from new false positives, not lost detections (see below). |
| An explicit reject class (merging known classes into `UNKNOWN`) | No net effect. Merging three known families into one `UNKNOWN` class (9 → 7 classes) changes the main score by −0.0030 against the seed-matched CNN, better on 1/3 seeds. The reject class does not reach Bot (+0.068 above chance, with the sign changing across seeds), but which families it does reach depends on what is merged into it (see below). |
| A fitted fuser that includes the knowledge-graph channel | Not possible for this channel. The knowledge-graph score is computed by streaming the test set into windows, so no validation-set score exists, and the channel cannot enter a combiner fitted on held-out data. This applies to the knowledge-graph channel only; a fitted combiner over other channels does work (see "What partially works"). |

Several of these results need more explanation.

**The symbolic component.** This is a negative result about our own system. Both the loss-level and the
representation-level versions lowered macro PR-AUC. The inference-level version had no effect alone and
was harmful in combination.

**Calibration.** A calibrator learns a mapping from scores to outcomes using data in which the outcome was
observed. That mapping does not carry over to a class the model has never seen, so a calibrator that fits
the known classes more closely is more confidently wrong on the new ones. In practical terms, a score of
p = 0.9 means a 90 % chance for a known attack and says nothing about a new one. Isotonic regression gives
the best ECE but is not usable for setting an operating point. It produces only 74 distinct values over
114,658 flows, so the 1 % false-positive quantile falls inside a tie block and the achieved false-positive
rate was 0.70 against a target of 0.01. We therefore use isotonic calibration for reporting and Platt
scaling for thresholds.

**Abstention.** We predicted this failure in advance from Appendix C. Abstention is based on confidence,
and the model is confidently wrong on Bot. A rule based on confidence cannot catch errors made with high
confidence, and indeed zero-day precision is unchanged to four decimal places at every non-degenerate
coverage.

**A second dataset.** Adding data from another capture is common advice for improving generalisation, so
we tested it carefully. The known classes of the 2018 capture were added to the training and validation
sets, and the test set remained the untouched 2017 test set. BENIGN was merged across the two captures so
that "comes from 2018" could not act as a shortcut for "is an attack", and the 2018 attack names were
kept as separate classes. There is no leak, because the 2018 split already withholds Bot, the web
families, Infilteration and SQL Injection, which is exactly the 2017 zero-day set.

| comparison | macro Δ | σ | seeds better | |
|---|---:|---:|---:|---|
| augmented vs seed-matched control | −0.1461 | 1.80 | 0/3 | consistent direction |
| control vs the 68-feature baseline | −0.0091 | 0.78 | 1/3 | inconsistent, so no effect, as required |

The control is needed because the augmented model has 67 inputs. The 68th feature of the 2017 data is a
duplicate column (identical across all 883,796 training rows), and the input width changes the size of
the flattened layer. We built a 2017-only model with 67 features before any augmented result existed, and
it has no effect. The −0.1461 is therefore due to the augmentation and not to the architecture.

The drop comes from new false positives rather than lost detections. Our first explanation was wrong. We
expected dilution: that nine new attack classes specific to the 2018 capture would split the class
probability mass that the web families depend on. In fact the web families stay 89–92 % concentrated in
one class; only the class changes (from `DoS slowloris` to `DoS Slowhttptest`, another 2017 class). The
change is on the benign side. The number of benign flows scoring above the median Web Brute Force flow
rises from 2 to 242, and 81 % of these false positives are assigned to `SSH-Patator`, the 2017 family that
is reinforced by the 2018 `SSH-Bruteforce` class (36,054 flows). Adding a related attack family from
another capture sharpens that decision region until it fires with confidence on benign traffic from the
original capture. Only 13.8 % of these flows are assigned to a 2018 class, so the model is not simply
matching 2018 signatures. A change of feature scaling is also ruled out: the median scale ratio is 0.979,
and the two strongly distorted features are not among Bot's discriminative features on any seed.

PR-AUC and the operating curve also disagree here:

| recall of unknown flows @ FPR | 0.1 % | 1 % | 5 % | 10 % |
|---|---:|---:|---:|---:|
| baseline | 47.3 % | 48.3 % | 54.2 % | 60.4 % |
| augmented | 16.2 % | 49.1 % | 50.1 % | 50.9 % |

At a 1 % false-alarm rate the augmented model is slightly better. At 0.1 % it keeps only about a third of
the baseline's recall. A reader given only the macro score would think the model had been ruined, and a
reader given only the 1 % column would think nothing had changed. We report both because neither is
accurate alone.

We saw twice that an intervention failed specifically at the 0.1 % operating point, and wondered whether
the tightest alert budget is where these methods generally break down. When we tested this across 57
methods with saved per-flow scores, it did not hold. Macro zero-day PR-AUC and recall at a fixed
false-alarm rate agree more closely at a tight budget than at a loose one:

| Spearman ρ (macro vs recall) | @0.1 % FPR | @1 % | @5 % | @10 % |
|---|---:|---:|---:|---:|
| | +0.849 | +0.817 | +0.812 | +0.425 |

The two earlier cases are real and are still reported individually, but they are not examples of a
general rule. Two observations are not enough to establish a pattern, and we record the negative test
rather than the initial hunch. The sweep instead shows disagreement at the loose end (ρ = +0.425 at 10 %
FPR), the opposite of what we expected, and some reordering at the top. Of the 11 best methods by macro
score, only 6 are also among the top 11 by recall at 0.1 % FPR, and post-hoc OOD scorers (entropy,
max-logit, MSP, ODIN) rank higher on the operational metric than their macro scores suggest.

**The reject class.** Every other method in this study detects novelty without being trained to do so. An
explicit reject class is the obvious answer to that objection, so we built one. We recorded in advance our
prediction that it would fail, and ran two versions that differ only in which classes are merged into
`UNKNOWN`. HETERO merges `DDoS`, `FTP-Patator` and `PortScan` (a flood, a brute-force attack and a scan);
HOMOG merges three DoS variants. The table gives the mean percentile rank of each family under
`p(UNKNOWN)`, over three seeds per version, as a distance from chance:

| version | Bot | Web Brute Force | Web XSS |
|---|---:|---:|---:|
| HETERO | +0.068, sign changes across seeds | +0.200 | +0.219 |
| HOMOG | −0.206 (3/3 consistent) | +0.259 | +0.271 |
| paired by seed, HETERO − HOMOG | +0.274, 2.57σ, 3/3 | −0.059, 3.58σ, 3/3 | −0.052, 12.35σ, 3/3 |

The two versions form a double dissociation that holds on every seed for every family. The homogeneous
DoS merge gives a reject class that ranks Bot below chance (−0.206) while reaching the web families best,
and the heterogeneous merge reverses both. Appendix C predicts this direction. The CNN assigns the web
families to `DoS slowloris`, so merging the DoS classes into `UNKNOWN` carries the web families along. A
reject class is therefore not a neutral "none of the above" category. What it reaches depends on the
features of the classes merged into it, which is the closed-set mechanism appearing in the open-set
setting.

The upper limit of this effect for Bot is chance. The most heterogeneous merge we can build from the known
classes gives +0.068, with the sign changing between seeds. This is the same instability as the CNN's own
Bot ranking (cross-seed ρ = −0.090), so Bot's ranking is unstable whichever model produces it. Changing
the label space can steer which new families a reject class reaches, but it does not make an unreachable
family reachable.

**An earlier version of this experiment did nothing.** Holding out a single family and renaming it
`UNKNOWN` leaves nine classes and the same partition of the training data. A softmax objective does not
depend on class names, so that run was the baseline with its output units reordered, and `p(UNKNOWN)` was
simply `p(DDoS)`. It placed the held-out family at the 94.4th percentile and Bot at the 29th, below
benign. A reject class requires fewer classes, not a renamed class. Appendix E describes why a full
training run did not expose the error: the sweep's main metric added the reject probability back into
the attack probability, so the broken experiment produced a believable score close to the baseline.

### Endogenous and exogenous knowledge

§3 and §6 of the main paper give the core argument. Two details are added here. The axiom of Grov et al.
[14] almost doubles XSS precision (0.088 → 0.213) with recall unchanged, and it depends on an asset
inventory. KnowGraph [15] also uses auxiliary models trained on different objectives in addition to
relational structure.

On our side, the exogeneity test in §6 did not go on to injection experiments, because injecting a
predicate the model can already compute would report feature engineering as a symbolic result. The
"exogenous" thresholds (AUC < 0.75 or R² < 0.5) are conventions. A predicate with R² = 0.90 still leaves
some variance that could in principle carry signal, and a stronger predictor could recover more, which
would only strengthen the conclusion.

**Scope of the fitted-fuser result.** The obstacle described in the table applies to channels whose value
is specific to zero-day detection. It does not apply to a channel that is also useful on the known classes
the combiner is fitted on. The next subsection reports a fitted combiner that works, and Appendix E
explains how we first stated the obstacle too broadly.

### What partially works

**The knowledge-graph channel.** This is the only part of our architecture that improves results, and the
size of the improvement depends on a hyper-parameter we had not initially swept. At the cluster count used
in our earlier experiments (k = 200) it adds +0.0528 macro [+0.0466, +0.0592] (p < 0.0001, 3/3 seeds) and
raises Bot from 0.0446 to 0.2518. Sweeping k shows that the fused macro score increases with k in both
knowledge-graph variants and at every step, on 3/3 seeds:

| k | 100 | 200 | 400 | 800 |
|---|---:|---:|---:|---:|
| fused macro (`s_kg`) | 0.6493 | 0.6792 | 0.6960 | 0.7123 |
| fused macro (`causal`) | 0.6622 | 0.6930 | 0.6968 | 0.7032 |

At k = 800 the fusion reaches 0.7123 against 0.6399 for the CNN, a gain of +0.0724 on 3/3 seeds.

The +0.0724 figure was selected on the test set, so we do not report it as the improvement. We selected k
again on a stratified half of the test set, using a random generator fixed independently of all model
seeds, and evaluated on the other half, which was not used for selection. The result is +0.0305 at
2.86σ on 3/3 seeds, and this is the figure we report. The same split caught a related result: a weighted
fusion that gained +0.007 on the selection half gives −0.0008, inconsistent in direction, on the
evaluation half. Without the split it would have been reported as a gain.

The direction of the knowledge-graph effect is established but its size is not. Measured against the
standard deviation of the paired difference, the k = 200 effect is 1.7σ, with a range of 0.027–0.088. We
therefore report its direction as established and its size as a range.

We do not claim that `s_kg` is the better variant. The ranking of the two variants changes with k
(`causal` is ahead at k = 200 and `s_kg` at k = 800), neither gap has been tested with a paired
comparison, and both are within the 0.0285 uncertainty carried by an absolute number in our pipeline. The
increase with k is established; the choice of variant is not.

**Operating points.** A single operating point hides the shape of the result, so we vary the false-alarm
rate. The table shows recall on flows from families the model has never seen, over three seeds, with the
threshold set on benign flows only:

| recall of unknown flows @ FPR | 0.1 % | 1 % | 5 % | 10 % |
|---|---:|---:|---:|---:|
| CNN alone | 47.3 % | 48.3 % | 54.2 % | 60.4 % |
| CNN + KG (k = 800) | 45.8 % | 57.6 % | 72.1 % | 91.6 % |
| CNN + KG, Bot only | 0.0 % | 23.2 % | 46.6 % | 85.2 % |
| CNN alone, Bot only | 0.0 % | 0.1 % | 9.5 % | 19.9 % |

At the tightest budget the knowledge graph costs 1.5 points, and Bot recall is 0.0 % for both models. The
gain starts at around a 1 % false-alarm rate, and no configuration we built detects Bot at a tight alert
budget. Reporting only the 1 % column would hide this. The 10 % column shows the shape of the curve only.
On 55,237 benign test flows it would mean roughly 5,500 false alerts, which is not a usable operating
point.

**Review depth.** To find half of the zero-day flows, an analyst would have to review 52 % of all traffic
ranked by the CNN, but only 29–32 % when ranked by the knowledge graph or the fusion. This reduction of
about 20 points is the clearest practical statement of what the knowledge graph adds, and it is easier to
interpret than a PR-AUC difference. It is subject to the scripted-window caveat below: the knowledge
graph's advantage relies on the temporal concentration created by this capture's attack schedule, so the
reduction is an upper bound on what a real network would show. There is also a less encouraging result.
At any alert budget small enough to deploy, only known attacks appear. Precision is about 1.000 at every
budget, and none of the top 1,000 flows is a zero-day flow. An alert stream that is fully precise but
contains no new attacks is exactly the failure that a headline PR-AUC of 0.64 does not reveal.

**A fitted combiner of the CNN and the autoencoder.** This combination does work, reaching a macro score
of 0.6502 against 0.6399 for the CNN (+0.0103, 3/3 seeds), and +0.0604 over equal-weight rank fusion of
the same two channels (3/3 seeds, 2.5σ). It gives the anomaly channel 17.9 % of the absolute weight, with
a positive weight on every seed, so it does not simply learn to ignore that channel. The combiner is
fitted on the validation set, which contains no zero-day flows by construction (this is checked in the
code), and applied unchanged to the test set, where it achieves a false-positive rate of exactly 0.0100 on
all three seeds. The +0.0103 gain is 0.80σ, so again the direction is established and the size is not.
The accurate summary is that a fitted combiner is possible and slightly positive. It does not replace the
knowledge-graph result.

**Parameter-free fusion is not always safe.** Equal-weight rank fusion of the CNN and the autoencoder
performs worse than the CNN alone, by −0.0501 (3/3 seeds, 4.34σ). Equal weights cannot express that one
channel is worth about a sixth of another, so they help when the partner channel is comparable and hurt
when it is weak. Our +0.0528 is a result about the knowledge graph, not about equal weighting.

**The emerging-pattern rule.** Scoring clusters by growth rate gives a lift of 5.94× [5.66, 6.11] over
three seeds at roughly 81 % recall. Two caveats apply. First, growth works largely because the attacks in
CIC-IDS2017 were scripted into fixed time windows. A real network with continuous low-rate command-and-
control traffic would not produce this signal, and in practice Bot is characterised by persistence rather
than bursts. Second, detecting bursts in a raw-feature cluster does not require a knowledge graph. The
case for the knowledge graph has to rest on explanation and corroboration, not on this detection figure.

**Claims we do not make.** We do not claim that combining the criteria gives 81 % precision. That figure
came from a single clustering seed (42); over three seeds the lift is 1.73–11.57× and the precision
0.122–0.814. We also do not claim that the originally specified "unexplained cluster" mechanism detects
zero-day attacks. It achieves a lift of at most 1.00×, at or below chance, across three representations
and three thresholds. That mechanism does not work, and the knowledge graph's role is limited to
corroboration and explanation.

### The double dissociation and its replication

The CNN and the autoencoder dissociate on every family, with no overlap across seeds: XSS +0.90 (40 SD),
Web Brute Force +0.82 (37 SD) and Bot +0.0868 (3.9 SD), p < 0.0005.

When we repeated this on CSE-CIC-IDS2018, the two halves of the result behaved differently. Only lift
(PR-AUC ÷ prevalence) can be compared across captures, because PR-AUC is bounded below by prevalence and
the two datasets differ by orders of magnitude in prevalence on the families concerned. We first made the
comparison in raw PR-AUC and withdrew it, and we report lift only.

| Bot, lift over chance | CIC-IDS2017 | CSE-CIC-IDS2018 |
|---|---:|---:|
| CNN | 1.31× | 0.83× |
| autoencoder | 3.84× | 1.09× |
| autoencoder − CNN | +2.53× | +0.26× |

The direction replicates on the independent capture, but the size does not. The autoencoder's advantage
on Bot shrinks by a factor of 9.7, and at 1.09× it is close enough to chance that the 2018 data do not
support the statement that an anomaly method reaches Bot. We cannot test whether 1.09× is above chance,
because our 2018 records store per-family lift as a mean without per-seed values, so a margin of 0.09× is
indistinguishable from noise. We therefore claim the direction only and treat the 2017 magnitude as
specific to that capture.

The dissociation is between two models, not between two families of methods. A random forest, which is
supervised, ties with the autoencoder on Bot (0.1311 against 0.1314, p = 0.88) while beating it by 0.50
on the macro score. The broader supervised-versus-unsupervised claim is contradicted by our own data, and
we do not make it.

The web-attack half of the result is not zero-day detection. The CNN assigns about 90 % of Web Brute
Force and XSS flows to `DoS slowloris`, a known attack class, so their PR-AUC of 0.92–0.95 reflects
absorption into a known attack rather than detection of a new one. An earlier explanation of ours, that
web attacks transfer because they resemble the FTP and SSH brute-force families, was tested and found to
be wrong.

### Cost

The full detection path takes 7.95 µs per flow (125,762 flows/s) on one CPU and scores the entire test
set in 0.91 s. The knowledge graph adds 0.58 µs per flow, which is +9.2 % over the CNN. Explanation is far
more expensive, at 1,898× the cost of detection: Integrated Gradients takes 11.95 ms per flow, or 84
flows/s. Explaining every test flow would take 23 minutes, whereas explaining 100 alerts takes 1.19 s. In
practice this means explaining alerts rather than all flows, which fits with the alert-budget results
above. A claim of an "explainable IDS" that implies explaining every flow would be off by four orders of
magnitude. Throughput figures also depend heavily on batch size (batch 1 gives 256 flows/s and batch 8192
gives 158,919, a 620× spread), and we did not measure upstream flow-feature extraction, which may dominate
in a real deployment.

---

## Appendix E — Measurement practice and the Arp et al. audit

### Reproducibility of the pipeline

We measured the reproducibility of our own pipeline before interpreting any difference between methods.

| source of variance | SD | evidence |
|---|---:|---|
| Nondeterminism (fixed seed, determinism off) | 0.0222 | n = 6 |
| Seed variance (determinism on) | 0.0171 | n = 6 |
| Data-split variance (5-fold, model and test fixed) | 0.0228 | 5-fold |
| Uncertainty on an absolute number | 0.0285 | √(0.0228² + 0.0171²) |
| Threshold for a comparison on a shared split | 0.0256 | 2·SE·√2 at n = 6 |

Seed variance and nondeterminism cannot be distinguished statistically (F(5,5) = 1.69, p = 0.58).
Determinism flags are enabled, and runs were checked to be byte-identical across sessions five days
apart. Runs from before and after the flags were introduced are treated as different populations and are
never pooled.

### Auditing this work against Arp et al.

Arp et al. [6] describe ten common pitfalls in machine learning for security. In the papers they surveyed,
sampling bias occurred in 90 % and data snooping in 73 %, and every paper had at least three of the
pitfalls. We checked this work against their list.

| | pitfall | status in this work |
|---|---|---|
| P1 | Sampling bias | Partly addressed. We use two captures, but both come from the same producer with related methods (Appendix F). |
| P2 | Label inaccuracy | Found late, and it matters (see below). |
| P3 | Data snooping | Selection is done on a held-out half with a random generator fixed independently of model seeds. This caught a +0.007 result that is −0.0008 on the evaluation half. Remaining issue: the cluster count was first swept on test, which we state where we report it. |
| P4 | Spurious correlations | Covered by Appendix C and the absorption analysis. The web families' 0.92–0.95 reflects absorption into a known attack class rather than detection, and one of our earlier explanations was tested and withdrawn. |
| P5 | Biased parameter selection | The noise floor was measured before any difference was interpreted, and every comparison is paired on seed. |
| P6 | Inappropriate baseline | Four deep architectures, seven classical models, four benign-only models and nine post-hoc OOD scorers, each compared with a seed-matched baseline rather than a pooled mean. |
| P7 | Inappropriate performance measures | This is a central topic of the work (Appendix B). |
| P8 | Base rate fallacy | PR-AUC rather than ROC, prevalence and lift reported, families below 100 flows excluded from the macro average, and cross-dataset comparisons made only in lift because prevalence differs by orders of magnitude. |
| P9 | Lab-only evaluation | Not addressed. Throughput is measured (7.95 µs/flow), but nothing has been deployed. |
| P10 | Inappropriate threat model | Not addressed. There is no adversarial evaluation; we list it as future work. |

**Label inaccuracy (P2).** Engelen et al. [2] reprocessed CIC-IDS2017 with a corrected version of
CICFlowMeter and relabelled it. More than 20 % of traces were reconstructed or relabelled, and a new
`X - Attempted` class was introduced for attack flows that carried no payload. Under these labels our
three main zero-day families become:

| family | as published | effective | attempted |
|---|---:|---:|---:|
| Bot | 1,966 | 738 | 1,470 |
| Web Attack Brute Force | 1,507 | 151 | 1,214 |
| Web Attack XSS | 652 | 27 | 652 |

About two-thirds of Bot flows and about nine-tenths of the web-attack flows are bare connection attempts,
and Web XSS drops below our threshold of 100 flows. This is a real threat to Appendix C. If most of what
we called Bot transmitted nothing, part of its unreachability might come from labelling rather than from
the model. It also gives a better explanation of our absorption result: if nine in ten web-attack flows
transmitted nothing, they really are bare connection attempts, which is also what a slow-connection DoS
attack looks like. We rebuilt the split on the corrected data under two readings registered in advance,
and trained three seeds on each. We found this problem by comparing our dataset with the literature, not
through our own checks.

**Results on the corrected labels.** Lift (PR-AUC ÷ prevalence) is the only measure that can be compared
across these settings. The test sets contain different flows with different prevalences and there is no
one-to-one correspondence, so nothing here is paired against 0.6399. Chance lift is 1.0.

| family | attempted folded in | attempted excluded | n (excluded) |
|---|---:|---:|---:|
| Web Attack Brute Force | 29.4× | 2.1× | 151 |
| Web Attack XSS | 61.5× | *unmeasurable* | 27 |
| Bot | 7.1× | see below | 738 |

Web Brute Force falls from 29.4× chance to 2.1× once flows that transmitted nothing are removed (PR-AUC
0.8861 → 0.0072), and XSS falls below the size threshold altogether. We already knew that the web
families' 0.92–0.95 reflected absorption into a known attack class. It now appears that much of it was
detection of bare connection attempts. A flow in which the attacker sent no payload looks very different
from normal traffic, and that difference is what was being scored.

The falsification criterion we had set for Appendix C did not trigger, and the way it failed to trigger
is informative. The criterion was an effective-Bot lift clearly above chance and consistent across seeds.
The three seeds give 0.57, 0.64 and 8.99. Two of the three runs are below a random ranker, and the best
and worst differ by a factor of 16. The mean of 3.4× does not describe any actual run. This instability is
the same pattern Appendix C reports for Bot (cross-seed rank ρ = −0.090): the ranking is essentially
random, so Bot's unreachability comes from the model and not from the empty flows.

This has an uncomfortable consequence for the paper. Appendix B argues that the published metric cannot
measure zero-day detection. The corrected labels show that on two of three families the metric we propose
was itself measuring a labelling convention, namely whether the dataset counts a failed connection attempt
as an attack. A better metric on a mislabelled benchmark still gives the wrong measurement, and we would
not have noticed without checking the dataset against the published corrections.

### Lessons from our own errors

**A flow-level significance test cannot rescue a difference smaller than the pipeline's reproducibility.**
We had settled a comparison in our favour with a paired bootstrap (p = 0.001). After measuring the noise
floor, we found that the gap (+0.0204) was 0.9 SD, smaller than the difference between two runs of the
same model. We withdrew the claim. Of all our methodological findings, this is probably the one most
useful to other researchers.

**Three seeds are enough for a mean but not for a variance.** Two separate three-seed SD estimates agreed
closely with each other and were both wrong by a factor of five; adding a fourth seed changed one of them
5×. Agreement between two under-powered estimates looks like confirmation but is not. Whether a sample is
large enough depends on the statistic being estimated.

**A paired comparison must be judged against the SD of the paired difference, not the floor for absolute
numbers.** The 0.0222 floor is the run-to-run variance of a single channel, and when two channels share
seeds most of that variance cancels. We noticed this while making a figure whose first version applied the
unpaired floor to paired differences and displayed a 16.3σ effect, consistent on 3/3 seeds, as noise.
That mistake would have discarded a real result rather than created a false one, but it is the same kind
of error as those that do create false positives. The right criterion combines a consistent direction on
all seeds with the paired effect size, and the two can disagree. Our knowledge-graph result is certain in
direction (3/3) but uncertain in size (1.7σ).

**Negative claims need the same standard of evidence as positive ones.** We had written that a fitted fuser
was structurally impossible in our setting, based on a single two-channel special case. Running it on the
full channel set contradicted all three predictions of that claim and triggered a falsification criterion
we had written down beforehand. All of our safeguards had been designed to catch overstated positive
results; this was an overstated obstacle, and nothing was checking in that direction. The claim that
survives (last row of the first table in Appendix D) is narrower but still sufficient, and it had to be
measured before we could state it.

**A single best run is not a result.** Our best CNN score, 0.6446, is the maximum over eleven runs, whose
mean is 0.6217. The reproducible baseline is the eleven-run ensemble at 0.6356, which is above the mean
but below the maximum, as expected given that the maximum was never a typical run.

---

## Appendix F — Limitations, extended

1. **Cross-dataset validation.** We replicate on CSE-CIC-IDS2018, which is openly available from the AWS
   Registry of Open Data without an account (`aws s3 sync s3://cse-cic-ids2018/ <dir> --no-sign-request`)
   under a licence that allows redistribution with citation. We ran four method settings with three seeds
   each, matching the 2017 training size of 883,796 flows (Appendices C and D). The mechanism replicates
   once rarity is controlled for, and the double dissociation replicates in direction but not in size.
   The remaining limitation is that two captures from the same producer, using related methods, do not
   show that the results hold in other network environments. In addition, 7 of the 10 published 2018 flow
   CSV files are truncated at 2²⁰ rows in chronological order, apparently by Excel. We detected and worked
   around this, and anyone reusing these files should be aware of it.
2. **Three sufficiently large zero-day families, not six.** Moreover, Web Brute Force and XSS are strongly
   correlated across 57 methods (r = +0.9906; Spearman ρ = +0.9822, p < 1e-40), since they come from the
   same capture window and the same tool. The macro average is therefore in effect ⅓ Bot and ⅔ a single
   web signal. Bot correlates with neither (r = −0.216 against Web Brute Force and −0.265 against XSS), so
   the macro average combines one strong signal and one weak one that move in opposite directions.
   Regrouping the families changes the values by 0.11–0.15 but leaves every ordering we report unchanged.
3. **Flow features rather than payload bytes.** This departs from the base paper's input modality, and our
   advantage of 18–29 percentage points on the known-class views is a modality advantage rather than an
   algorithmic one. The oracle probe, however, separates every sufficiently large family from benign
   traffic using flow features alone (Bot 0.9988, Web Brute Force 0.9999, XSS 0.9984). The Bot gap is
   therefore a gap in closed-set supervision rather than in modality. The mechanism of Appendix C would
   move to a payload representation rather than disappear, since a closed-set model on payload bytes
   would select the payload features that separate the same nine classes. Using payloads would, however,
   likely replace the web families' absorption into `DoS slowloris` with real detection, which this study
   cannot claim.
4. **Scripted attack windows** inflate any growth-based or temporal result (Appendix D).
5. **Behaviour predicates are approximations.** The predicate we call `HighEntropy` is the standard
   deviation of packet length, not the Shannon entropy of the payload, so reading it as an indicator of
   encryption would be unjustified. One predicate is constant and another is binary rather than graded.
6. **The fusion result is transductive.** Rank fusion normalises each channel by rank within the scored
   set, so a flow's fused score depends on the rest of the test set. This is neither label leakage nor a
   scoring error, and it is normal for a rank-based metric, but a streaming deployment could not compute
   it without a fixed reference distribution, which would be a different estimator. We have not measured
   that variant and make no claim about how it would perform.
7. **No adversarial evaluation**, which we leave to future work.

---

## Appendix G — Related work, extended

**The dataset and its known problems.** CIC-IDS2017 was released by Sharafaldin et al. [1] and is among the
most widely used intrusion detection benchmarks. Engelen et al. [2] examined it, found errors at
most stages of its construction from the generated traffic through to the final labels, and released a
corrected version. A follow-up study measured how much these errors change detection results [3]. Goldschmidt
and Chudá [4] review 89 network intrusion datasets and argue that data quality and reporting practice, and
not only the amount of data, now limit progress.

Our question is related to theirs but different. That line of work asks whether the labels and flows are
correct. We take the data as given and ask what a metric computed on it can resolve. The two approaches
complement each other, and one of our results lies between them. 17 % of test rows are exact duplicates of
training rows, which inflates the published metric, but all six zero-day families have 0.0 % overlap, so
the zero-day metric is unaffected. A data-quality review would flag the duplication; only an analysis of
metric resolution shows that it affects one number and not the other.

**Critiques of machine learning in security.** Sommer and Paxson [5] argued that intrusion detection is a
particularly hard setting for machine learning, largely because the events of interest fall outside the
closed world the model was trained on. Arp et al. [6] identify ten recurring pitfalls in 30 papers from
top security venues and give recommendations for avoiding them.

Our work builds on both. Sommer and Paxson's argument is qualitative. Appendix C offers a mechanism for one
instance of it (no overlap between a new class's discriminative features and the trained basis) and shows
that the failure takes the form of instability as well as inaccuracy, with a cross-seed ρ of −0.090 for
Bot. Appendix B gives a quantitative counterpart: 22 % of comparable method pairs (37 of 169) cannot be
distinguished on the published metric while differing by a factor of two or more on the capability in
question. Following Arp et al., Appendix E measures the pipeline's reproducibility, expresses differences
relative to it, and lists the claims of ours that it led us to withdraw.

**Neuro-symbolic intrusion detection.** Logic Tensor Networks [7] provide the fuzzy-logic loss on which this
line of work builds. Bizzarri et al. [8] apply it to intrusion detection with a 1D CNN trained on a
combined cross-entropy and satisfiability loss, and report better accuracy on unknown attacks than a
standard CNN on CIC-IDS2017. That paper was our starting point, and a later survey by the same group [9]
situates it in a growing literature.

We reproduced their CNN but not their symbolic gain. On their metric we obtain 47.85 % against their
48.34 % for the 1D CNN, while our closest reproduction of their hybrid model scores 47.24 %, no better than
our CNN (Appendix B). The comparison is approximate: the modality differs (flow features instead of payload
bytes), the zero-day sets differ by one swap, and class sizes differ, with composition explaining roughly
4 of the 12 missing points. Appendix B also describes two arithmetic problems in the metric on which the
gain is reported. Our own symbolic component did no better, having no effect alone and a harmful effect in
combination (Appendix D).

The systems that do report gains [14]–[16] are discussed in §1 and §3 of the main paper. The axiom of Grov
et al. [14] raises XSS precision from 0.088 to 0.213 with unchanged recall, and KnowGraph [15] raises the
true-positive rate from 0.0 % to 35.5 % at a 0.5 % false-positive rate. In each case the knowledge comes
from outside the feature vector. Our attempt in §6 to build such knowledge from CIC-IDS2017 produced
host-role predicates that the flow features predict with AUC 0.990–0.994 and R² 0.89–0.95. We do not
intend this as a criticism of [14]–[16], whose knowledge is exogenous. Our point is that this property
determines whether the result holds, that it is usually left implicit, and that without it a knowledge
result cannot be told apart from a feature-engineering result.

**Open-set recognition and out-of-distribution scoring.** Treating unseen attack families as an open-set
problem has a long history in this area [10], and the general OOD literature offers post-hoc scorers that
need no retraining: maximum softmax probability [11], temperature scaling with input perturbation [12] and
energy-based scores [13]. Appendix C evaluates nine such scorers against a threshold fixed in advance.
None of them helps on Bot, and the one that changes Bot at all does so by destroying known-class
discrimination. We see this as a limited negative result about post-hoc scoring for this problem, not a
general statement about OOD detection.

---

## Appendix H — Reproducibility

**Released material.** All analysis and pipeline scripts, the protocol configuration, pinned dependencies,
the figures, the metadata files from which every number in the paper is taken, and the append-only
experiment log, which records every run with its seed, parameters and results. The code is released under
the MIT licence.

**Material not released.** The CIC-IDS2017 dataset is not redistributed, since it has its own terms of use
and is available from its publisher. Trained model weights are also not released. They are large, exist
per seed, and can be regenerated, and the determinism guarantee below makes regeneration the better option.

**Environment.** Python 3.11.9 and TensorFlow 2.15.1 (Keras 2) on CPU, with all dependencies pinned to
exact versions. All results were produced on a single 32-core AMD workstation; no GPU was used or is
required.

**Determinism.** Deterministic operations are enabled, and thread counts are fixed rather than left to
depend on the number of cores, because op-level determinism alone does not fix the order of reductions.
We checked this. Two full 50-epoch runs with the same seed produced byte-identical output, and a third run
five days later in a different session reproduced the same score to twelve decimal places. The cost was a
2–7 % loss in throughput and no other measurable effect.

The determinism guarantee only applies from the point the flags were introduced. Earlier results came from
a process with a run-to-run SD of 0.0222 and cannot be reproduced exactly at a fixed seed. We treat runs
from before and after this change as different populations and do not pool them. Someone re-running the
pipeline today should be able to reproduce the later results but not the earlier ones exactly; for those,
the noise floor in Appendix E is the appropriate error bar.

**Entry point.** A single driver script lists the 19 pipeline stages in order, together with the files each
stage writes. By default it only checks which outputs are present on disk. A flag runs the stages, and a
further option resumes from a given stage. We chose checking as the default because a full CPU retrain is
too expensive to trigger by accident.

The stage sequence has been checked end to end but never run end to end in a single pass. Every stage has
been run on its own, most of them many times, but "each stage works" and "the whole sequence works from a
clean checkout" are different claims, and only the first is supported. The run option is provided for
convenience and is not a validated reproduction path.

**Automated checks.** Two checks are included, each added after the corresponding mistake had actually
occurred:

- A linter enforces project conventions that were broken in the past, and names the incident behind each
  rule, for example an encoding bug that was fixed three separate times, a timestamp parser that silently
  reordered every test row, and a script count that did not match the files on disk.
- A claim checker compares every quantitative claim in the paper with the metadata files that produced it.
  It reads each value from its source file, formats it as the paper should state it, checks that the
  string appears in the text, and fails on values known to be out of date. At the time of writing every
  checked claim passes and none is mismatched. We added it after an early draft misquoted a throughput
  figure and the error was found by chance. It checks transcription, not interpretation, so it cannot
  detect a missing caveat or a claim that goes beyond its evidence.

Four claims in the paper have no machine-readable record, and the checker reports them as such: the split
sizes, the base paper's published figures, the per-method figures for the classical and deep baselines,
and the standard-deviation multiples of the double dissociation. We list them so that readers know which
numbers must be checked by hand.

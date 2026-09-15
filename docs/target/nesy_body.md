# Knowledge the Network Already Has: An Exogeneity Precondition for Neuro-Symbolic Intrusion Detection

*Anonymous submission — NeSy full paper (≤ 10 pages excluding references and supplementary material)*

> **Build note — not part of the submission.** Derived from [paper_draft.md](paper_draft.md), which
> remains the full verified research record. Every quantity here is checked by `verify_draft.py`
> against `outputs/metadata/*.json`, over this file and [nesy_supplementary.md](nesy_supplementary.md)
> together, and every decimal in this file must appear verbatim in the master draft. Delete this
> block before conversion to the PMLR template.

---

## Abstract

When does injecting symbolic knowledge into a neural model help? For intrusion detection we give a
precise answer, a mechanism for it, and a benchmark on which the question cannot be tested.
**The neuro-symbolic intrusion detectors that report gains share an unstated property: the knowledge
they inject is information the network cannot compute from its input** — an asset inventory, a
relational graph, an external attack taxonomy. Our own symbolic pillar did the opposite. Its Logic
Tensor Network axioms are deterministic functions of the flow features the network already reads,
and it was null alone (−0.0004, n.s.) and significantly harmful when stacked (0.6926 → 0.6708,
p < 0.0001). We propose that **symbolic knowledge helps exactly to the extent it lies outside the
model's learned feature basis**, and show that the same property explains a second failure: a
closed-set learner reaches a novel attack family only insofar as its signature overlaps that basis.
For Bot the overlap is empty (**0 of 8** discriminative features shared), every flow is classified
benign, and the model's ranking of it is noise (cross-seed ρ = **−0.090**). This survives five attempts
to break it, including a capture where Bot is abundant and corrected labels. We then try to satisfy
the precondition on CIC-IDS2017 and cannot: host-role knowledge built from metadata the network never
sees is still predicted from its features at AUC **0.990–0.994**. **Exogenous knowledge cannot be
manufactured by aggregating the same data**, so a benchmark with no external knowledge artefact
cannot support the experiment its neuro-symbolic results depend on.

---

## 1 Introduction

Neuro-symbolic learning promises that domain knowledge, stated as logic, can supply what data alone
does not. Intrusion detection is an attractive test: attacks absent from training are exactly where a
data-driven detector is weakest, and exactly where knowledge of how networks and attacks behave ought
to help.

We built a neuro-symbolic intrusion detector to test that promise, and it failed. Its Logic Tensor
Network axioms — over behaviours such as burst traffic, packet-size variance and beacon-like
periodicity — contributed **−0.0004** macro zero-day PR-AUC alone (not significant) and **harmed**
the system significantly when stacked on a knowledge-graph channel (0.6926 → 0.6708, p < 0.0001).
This paper is about why, and the answer turns out to be general.

**The published systems that report gains share a property ours lacked.** Grov et al. [14] add a
single axiom — *flows not communicating with web servers cannot be web attacks* — and roughly double
web-attack precision. KnowGraph [15] reasons over relational structure between entities and lifts
true positives from **0.0 % to 35.5 %** at a 0.5 % false-positive rate, where the neural baseline
detects nothing. Kalutharage et al. [16] align alerts to an external attack taxonomy. In each case
**the knowledge is information the network cannot compute from its own input**. Every one of our
behaviour predicates, by contrast, is a deterministic function of the flow features the network
already reads. Ours supplied an inductive bias; theirs supplied evidence.

We state this as a precondition — **symbolic knowledge helps a neural detector to the extent it lies
outside the model's learned feature basis** — and make three contributions around it.

1. **One principle, two consequences (§3–§4).** The same property governs *novel attack families*: a
   closed-set learner reaches a family it never saw only insofar as that family's signature overlaps
   the features it learned. Symbolic knowledge inside the basis adds nothing; a novel class outside
   it cannot be reached.
2. **A durability test (§5).** The unreachability survives five attempts to break it: a capture where
   the family is abundant rather than rare, corrected labels, an explicitly trained reject class,
   cross-dataset augmentation, and a broad architecture and out-of-distribution sweep.
3. **A negative evaluability result (§6).** Built from metadata the network never sees, host-role
   knowledge is still recovered from its features. A benchmark with no external knowledge artefact
   cannot support the experiment published neuro-symbolic gains rest on.

![Figure 1](../../outputs/figures/nesy_fig1_thesis.png)

**Figure 1.** *One principle, two consequences.* Both panels draw the same learned feature basis —
the features a closed-set objective selects. **(a)** Symbolic knowledge can help only from outside
that basis: our Logic Tensor Network axioms are functions of the flow features and add no evidence,
whereas the knowledge behind published gains [14–16] is not computable from the input. **(b)** An
unseen attack family is reachable only insofar as it overlaps the basis: Web Brute Force shares 1 of
8 discriminative features and is reached only weakly once label artefacts are removed (§7); Bot
shares none and is unreachable. Inside and outside map to opposite outcomes in the two panels.

⚠️ **Two measurement failures bound the magnitudes (§7), and we demonstrate both on our own system.**
The metric the field reports cannot resolve zero-day capability, and on corrected labels two of our
three headline zero-day families were measuring whether the dataset counts an unsuccessful connection
attempt as an attack. They limit what we can claim quantitatively; they do not move the mechanism.

---

## 2 Setting and measurement

**Data.** CIC-IDS2017 [1] flow features, **68 numeric features per flow**. Nine attack families plus
benign are *known* and split 80/10/10 stratified, benign under-sampled to 1:1: **883,796 train /
110,475 validation / 114,658 test**. Six rare families — Bot, Heartbleed, Infiltration, and Web Attack
Brute Force / XSS / SQL Injection — appear **only in test**.

**Metric.** Macro zero-day PR-AUC over the three adequately powered unseen families: **Bot
(n = 1,956), Web Attack Brute Force (n = 1,507), Web Attack XSS (n = 652)**. Heartbleed (n = 11),
Infiltration (n = 36) and SQL Injection (n = 21) are excluded as underpowered. Where test sets differ
in prevalence — across datasets or labellings — we compare only **lift** (PR-AUC ÷ prevalence), since
PR-AUC is bounded below by prevalence; chance lift is 1.0.

**Reproducibility floor.** Training is not bit-reproducible at a fixed seed without determinism flags,
so we measured the floor before interpreting any delta: nondeterminism SD **0.0222**, seed SD
**0.0171** (determinism on, n = 6), data-split SD **0.0228**, giving **0.0285** of uncertainty on an
absolute number. **Every comparison is paired on seed**, and a delta is reported as established only
when its direction is consistent across seeds; magnitudes are given as ranges. This floor retracted
one of our own headline claims, a gap of 0.9 SD that a paired bootstrap had called significant at
p = 0.001 (supplementary §E).

---

## 3 A symbolic pillar that could not help

**The architecture.** A 1D CNN over the flow features, a Logic Tensor Network [7] layer grounding
fuzzy axioms in network behaviours, and a knowledge-graph channel scoring cluster growth over time.
The axioms (Ax3–Ax6) constrain the network's attack output by behaviour predicates — large packets
with high packet-size variance, burst traffic, scan-like probing, beacon-like periodicity.

**The result.** Across every injection point we tried — loss-level, representation-level and
inference-level — the symbolic pillar costs macro zero-day PR-AUC or changes nothing. Alone it
contributes **−0.0004 (n.s.)**; stacked on the knowledge graph it **significantly harms** the system
(0.6926 → 0.6708, **p < 0.0001**), diluting Bot from 0.2518 to 0.2043. An axiom that briefly appeared
to help Bot did not survive multi-seeding. This is not a tuning failure: it is consistent in sign
across every configuration.

**What the successful systems share.** The contrast with published gains is the diagnostic:

| system | knowledge injected | computable from the flow features? |
|---|---|---|
| Grov et al. [14] | *non-web-server flows cannot be web attacks* | **no** — requires an asset inventory |
| KnowGraph [15] | logic over entity-relational structure | **no** — requires a relational graph |
| Kalutharage et al. [16] | technique mapping to an attack taxonomy | **no** — requires an external taxonomy |
| **ours** | behaviour predicates (Ax3–Ax6) | **yes** — each is a function of the input |

All seven of our behaviour predicates are deterministic functions of features the network consumes:
`HighEntropy` is packet-length standard deviation, not Shannon entropy; `BeaconLike` is a function of
destination port. A predicate the network can already compute cannot tell it anything; it can only
reshape the hypothesis space, which is regularisation. **The injected knowledge was endogenous.**

**The precondition.** We therefore propose: *symbolic knowledge helps a neural detector to the extent
that it lies outside the model's learned feature basis.* The next section shows the same property
governs a second, apparently unrelated failure.

---

## 4 One principle, two consequences

A closed-set discriminative model learns only the features that separate the classes in its training
objective. It follows that a class it never saw is reachable **exactly to the extent its signature
overlaps that learned basis** — the same statement as §3's precondition, with a novel class in place
of an injected predicate. Where the overlap is empty, the model's output on that class is not merely
poor but **unstable**, because nothing in the objective constrains it.

We establish this on Bot, where the overlap is empty:

- **100 % of Bot flows are classified BENIGN**, mean p(BENIGN) = **0.9984**, on all three seeds. Bot
  is not ambiguous to the model; it is confidently asserted benign, which defeats every
  confidence-based remedy before it is tried.
- The eight features separating Bot from benign share **0 of 8** with the eight the known-class task
  selects.
- The model's Bot ranking is therefore **noise** (Figure 2): cross-seed Spearman **ρ = −0.090**,
  against 0.68–0.83 for every other family. RandomForest behaves identically (ρ = 0.068); **the autoencoder
  does not (ρ = 0.827)**, so the property belongs to closed-set discriminative learning rather than to
  neural networks. ⚠️ Three seeds cannot distinguish −0.090 from −0.02; they are ample to show it is
  not 0.7, and only that is load-bearing.
- **The information is present.** An oracle given Bot labels reaches PR-AUC **0.9988** from the same
  features. The oracle trains on zero-day labels and is an upper bound, not a method; it shows the
  barrier is supervision, not information or modality.

![Figure 2](../../outputs/figures/nesy_fig2_mechanism.png)

**Figure 2.** *Bot's ranking is noise for closed-set learners.* Agreement between each model's
rankings of test flows across three training seeds (Spearman ρ), per unseen family. For Bot the two
closed-set discriminative learners do not agree with themselves (1D CNN −0.090, random forest
+0.068); the benign-only autoencoder does (+0.827), so the instability belongs to closed-set
discriminative learning rather than to neural networks. The zero line marks no agreement; no
threshold is drawn, because none is measured. Three seeds cannot distinguish −0.090 from −0.02, but
they suffice to show it is not 0.7.

**The two consequences side by side.** Knowledge *inside* the basis — our axioms — adds no evidence.
A novel class *outside* the basis — Bot — cannot be reached. Both follow from what a closed-set
objective does and does not constrain. ⚠️ **The reachable direction is weaker than the unreachable
one** (§7): the evidence that overlapping families *are* reached rested on web-attack scores that
corrected labels largely remove. The **ordering** survives; the magnitudes do not.

---

## 5 Durability: five attempts to break it

A mechanism asserted once is a hypothesis. We pre-registered a falsifier for each of the following
before running it.

| attempt | what it controls for | result for Bot |
|---|---|---|
| **Independent capture**, CSE-CIC-IDS2018, training size matched | that Bot is merely *rare* | Bot is **abundant** and scores **0.83×** chance — below a random ranker |
| **Corrected labels** [2], attack flows with no payload excluded | a labelling artefact | effective Bot (n = 738) lifts **0.57 / 0.64 / 8.99** — two of three seeds below chance |
| **Explicit reject class**, three known families merged into `UNKNOWN` | that the model was never *asked* to reject | ceiling is chance: **+0.068** with the sign flipping between seeds |
| **Cross-dataset augmentation**, 2018's known pool added | that the basis was too narrow | **−0.1461** macro against a seed-matched control, 0/3 seeds better |
| **Sweep**: 4 deep architectures, 7 classical, 4 benign-only, 9 OOD scorers | method choice | none reaches Bot; the best OOD scorer reaches 0.0783 against a pre-set 0.08 threshold |

**The corrected-label result is the most demanding, and how it fails to falsify matters.** The
criterion was lift above chance *consistently across seeds*. A mean of 3.4× would read as detection;
it describes no run that happened. The spread is itself §4's instability signature.

**The reject class yields the most informative positive.** Two merges differing only in *what* was
merged into `UNKNOWN` produce a **double dissociation**, direction-consistent on every seed for every
family: a homogeneous merge of three DoS variants anti-ranks Bot (−0.206) while reaching the web
families best, and a heterogeneous merge reverses both (Bot contrast **+0.274, 2.57σ, 3/3**). A reject
class is therefore not a generic "none of the above": **its reach is set by the feature basis of what
is merged into it** — §4's mechanism observed in the open-set case, with chance as its ceiling for Bot.

**Augmentation fails for a reason that is itself instructive.** Adding a related attack family from
another capture sharpened one decision region until it mis-fired on the original capture's benign
traffic: benign flows outscoring the Web Brute Force median rose from **2 to 242**, 81 % of them
assigned to `SSH-Patator`. A wider basis in directions already covered imports false positives rather
than reach.

---

## 6 Evaluability: the benchmark cannot supply exogenous knowledge

If §3's precondition is right, the constructive move is to inject knowledge from outside the basis.
We attempted this on CIC-IDS2017 and the attempt failed at the premise — which is the result.

**Construction.** Source and destination IP addresses are *not* among the features, and no single
flow's vector expresses a property of a host across many flows. We therefore built host-role
predicates from flow metadata: whether a destination normally serves a port, whether a flow's port is
unusual for its host, a source's fan-out, and pair persistence. Profiles are built from **training
flows only**, so the construction is inductive rather than transductive. Attacker identity is
**deliberately excluded**: the testbed documents the attacker subnet, and conditioning on it would be
label leakage dressed as domain knowledge.

**The premise test.** A predicate is exogenous only if the network could not already compute it. We
fitted gradient-boosted models to predict each predicate *from the flow features*:

| predicate | all features | without `Destination Port` |
|---|---:|---:|
| Unusual port for host | AUC 0.990 | 0.988 |
| Host serves a web port | AUC 0.994 | 0.992 |
| Source fan-out | R² 0.949 | 0.898 |
| Pair persistence | R² 0.914 | 0.886 |

**None is exogenous.** The ablation is what makes this a finding rather than an artefact: dropping the
one port feature barely moves the numbers, so the flow's own port is not giving the answer away — the
remaining features determine host role and cross-flow structure by themselves. In a testbed where each
host plays one scripted role, a flow's characteristics nearly identify its host, and therefore that
host's aggregate properties.

**The generalisable claim.** *Exogenous knowledge cannot be manufactured by aggregating the same
data.* Grov et al.'s axiom works because an asset inventory is an artefact from **outside** the
capture; ours was inferred **from** it, and anything inferable from the capture is largely inferable
from its features. CIC-IDS2017 ships no inventory, topology or threat intelligence, so **the
neuro-symbolic approach as the literature practises it cannot be evaluated on this benchmark.** We did
not run the injection arms: measuring a predicate the model can already compute would report feature
engineering as a symbolic result. ⚠️ The thresholds (AUC < 0.75, R² < 0.5) are conventions, and a
predicate at R² = 0.90 leaves residual variance; a stronger predictor would only strengthen the
conclusion.

---

## 7 What limits the magnitudes

Two measurement failures bound how far any number here should be trusted. We report both because the
second one retracts two of our own headline families.

**Label semantics.** Engelen et al. [2] re-ran CIC-IDS2017 through a corrected flow meter and
introduced an `X – Attempted` label for attack flows that transmitted **no payload**. Two-thirds of Bot
and roughly nine-tenths of the web families are such flows. Retraining on the corrected release:

| family | attempted folded in | attempted excluded | n (excluded) |
|---|---:|---:|---:|
| Web Attack Brute Force | **29.4×** | **2.1×** | 151 |
| Web Attack XSS | 61.5× | *unmeasurable* | 27 |

**Web Brute Force falls from PR-AUC 0.8861 to 0.0072** once flows that transmitted nothing are
removed. Its apparent reachability was substantially detection of bare connection attempts, which are
trivially unlike normal traffic. **A better metric on a mislabelled benchmark is still the wrong
measurement.** This is why §4's reachable direction is weak; it does not touch the unreachable one,
which §5 tested on exactly these labels.

**Metric resolution.** The metric the field publishes cannot resolve the capability it is used to
claim. Across 31 methods evaluated identically, **37 of 169 method pairs (22 %)** are statistically
indistinguishable on it while differing by a factor of two or more in macro zero-day PR-AUC; the
worst pair is **0.0052** apart on the former and **16.6×** apart on the latter. The metric is neither
noisy nor uninformative (ρ = +0.582 against zero-day performance) — it is too coarse where the field
reports. Full analysis in supplementary §B.

**The one component that helps.** A knowledge-graph channel scoring cluster growth over time improves
macro zero-day PR-AUC; its cluster count was selected on test, so the honest improvement is the
held-out one, **+0.0305 at 2.86σ** on a half never used for selection. ⚠️ Its signal rides
substantially on CIC-IDS2017's scripted attack windows, and temporal burstiness of a raw-feature
cluster does not require a knowledge graph; we do not claim it as evidence for the neuro-symbolic
approach (supplementary §D).

---

## 8 Related work

**Neuro-symbolic intrusion detection.** Logic Tensor Networks [7] supply the fuzzy-logic-to-loss
machinery. Bizzarri et al. [8] apply it to CIC-IDS2017 with a hybrid cross-entropy and satisfiability
loss and report improved unknown-attack accuracy; that paper is our starting point, and a survey by
the same group [9] places it in a growing literature. **We reproduce its CNN and cannot reproduce its
symbolic gain**: on its own metric we obtain 47.85 % against its 48.34 % for the CNN, while our nearest
reproduction of the hybrid scores 47.24 %. The comparison is in form rather than head-to-head — the
modality and zero-day membership differ. The gains in [14]–[16] are, by our reading, gains from
**exogenous** knowledge; we make that property explicit, test it, and show a widely used benchmark
cannot satisfy it. This is not a criticism of those works, whose knowledge genuinely is exogenous: the
point is that the property is load-bearing and usually left implicit, so a reader cannot distinguish a
knowledge result from a feature-engineering result without it. A survey [17] notes that most
neuro-symbolic cybersecurity evaluations are limited by evaluation gaps.

**The benchmark.** CIC-IDS2017 [1] is widely reported on. Engelen et al. [2] documented defects in
flow construction and labelling and released corrected processing; a follow-up quantified the effect
on detection [3], and a survey of 89 intrusion datasets argues data quality now limits the field [4].
We add a consequence for the zero-day question specifically, and a second property the benchmark
lacks: any external knowledge artefact.

**Closed worlds and security machine learning.** Sommer and Paxson [5] argued that intrusion detection
is hostile to machine learning because the interesting events lie outside the closed world. §4
supplies a mechanism for one instance and shows the failure is instability, not only inaccuracy.
Arp et al. [6] catalogue ten pitfalls in security machine learning; we audit this work against all ten
in supplementary §E, and two — lab-only evaluation and threat model — we do not address.

**Open-set recognition and OOD scoring.** Treating unseen attacks as an open-set problem has a long
history [10]; post-hoc scorers need no retraining [11]–[13]. None rescues Bot (§5).

---

## 9 Limitations and conclusion

**Limitations.** Two captures from the same producer under related methodology are not evidence of
generality across network environments. Only two zero-day families are adequately powered under
corrected labels. Flow features, not payload bytes, are used throughout, though the oracle shows the
barrier is not modality. Our exogeneity thresholds are conventions. We do not evaluate adversarially,
and nothing is deployed.

**Conclusion.** Symbolic knowledge helps a neural intrusion detector to the extent that it lies
outside the model's learned feature basis. The same property makes a novel attack family with no
overlap unreachable, and that unreachability survived every attempt we made to break it. The
neuro-symbolic systems that report gains inject genuinely exogenous knowledge; ours did not, and on
CIC-IDS2017 we could not construct any, because knowledge aggregated from a capture is recoverable
from that capture's features. **Before reporting a neuro-symbolic gain, establish that the knowledge
injected is not already in the input — and recognise that a benchmark may make that impossible.**

*Code, per-run records and trained models will be released upon acceptance.*

---

## References

1. I. Sharafaldin, A. H. Lashkari, A. A. Ghorbani. *Toward Generating a New Intrusion Detection
   Dataset and Intrusion Traffic Characterization.* ICISSP 2018, pp. 108–116.
2. G. Engelen, V. Rimmer, W. Joosen. *Troubleshooting an Intrusion Detection Dataset: the CICIDS2017
   Case Study.* IEEE Security and Privacy Workshops (SPW), 2021.
3. M. Lanvin, P.-F. Gimenez, Y. Han, F. Majorczyk, L. Mé, É. Totel. *Errors in the CICIDS2017
   Dataset and the Significant Differences in Detection Performances It Makes.* CRiSIS 2022, LNCS
   vol. 13857, Springer, 2023.
4. P. Goldschmidt, D. Chudá. *Network Intrusion Datasets: A Survey, Limitations, and
   Recommendations.* Computers & Security, vol. 156, 2025.
5. R. Sommer, V. Paxson. *Outside the Closed World: On Using Machine Learning for Network Intrusion
   Detection.* IEEE S&P 2010, pp. 305–316.
6. D. Arp et al. *Dos and Don'ts of Machine Learning in Computer Security.* USENIX Security 2022.
7. S. Badreddine, A. d'Avila Garcez, L. Serafini, M. Spranger. *Logic Tensor Networks.* Artificial
   Intelligence, vol. 303, 2022.
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
13. W. Liu, X. Wang, J. D. Owens, Y. Li. *Energy-Based Out-of-Distribution Detection.* NeurIPS 2020.
14. M. W. Eckhoff et al. *Experimenting with Neurosymbolic Artificial Intelligence for Defending
    Against Cyber Attacks.* Neurosymbolic Artificial Intelligence, 2025.
15. Z. Zhou et al. *KnowGraph: Knowledge-Enabled Anomaly Detection via Logical Reasoning on Graph
    Data.* ACM CCS 2024.
16. C. I. Kalutharage et al. — **⚠️ unverified; cited via [17]; check or drop before submission.**
17. *Neuro-Symbolic AI for Cybersecurity: State of the Art, Challenges, and Opportunities.*
    arXiv:2509.06921, 2025.

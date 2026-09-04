# Paper Outline — claim → evidence → the caveat that travels with it

> **Purpose.** The spine was decided 2026-08-10 (`conference_roadmap.md §0b`). This file turns it
> into a section-by-section plan in which **every claim carries the number, the script that produced
> it, and the limit that must be stated alongside it.** Prose gets drafted *from* this file, not
> independently of it.
>
> **Why the third column exists.** This project's recurring failure is not wrong numbers — it is
> *right numbers written without their limits* (five single-seed retractions, a size-weighted metric,
> a "same as X" comment that wasn't). A claim whose caveat is missing here will lose its caveat in
> the paper. **If the third column is empty, the claim is not ready to write.**
>
> 🔴 **Claims marked DO-NOT-WRITE are refuted forms that are tempting to state.** They are listed
> deliberately, because each one was either believed at some point in this project or is the obvious
> stronger version of a claim we can support.

---

## Status of the evidence base

| | |
|---|---|
| Methods measured on both metrics | **40** (`field_gap.py`) |
| Multi-seeded channels | CNN n=11 pre-flag / n=6 post-flag · AE n=6 · baselines n=6 · tiers A/C n=3 |
| Significance machinery | paired bootstrap over per-flow scores (`significance.py`), seed-level Welch/Wilcoxon |
| Reproducibility | determinism ON, byte-identical, verified across sessions 5 days apart |
| Research record | `runs.jsonl`, version-controlled, append-only, 190+ rows |

---

## §1 Introduction — the resolution failure

**Opening move:** the field reports ~99 % on CIC-IDS2017 and that number cannot tell its own methods
apart on the capability it is used to claim.

| claim | evidence | caveat that MUST travel with it |
|---|---|---|
| The published metric cannot resolve zero-day capability: **67 of 204 method pairs (33 %) are indistinguishable on it while ≥2× apart on macro zero-day** | `field_gap.py`, 40 methods | Threshold for "indistinguishable" is **< 0.0058** = 2 SD of a difference, from a measured median run-to-run **SD 0.0020**. State the band, not just the count. |
| Worst case: **0.0028 apart on the published metric, 18× apart on zero-day** (`deep_cnn_lstm` vs `ltn_anat_w2p0`) | `field_gap.json` | Cherry-picking the extreme is fair only if the distribution is also given (the 33 % figure). Give both. |
| Inside the field's own ≥0.98 regime, **25 methods sit within 0.014 of each other and span 20×** on zero-day | `field_gap.png` | The ≥0.98 cut is *the field's own reporting regime*, chosen for that reason — say so, or it looks like a fitted threshold. |
| 🔴 **DO-NOT-WRITE:** "the published metric carries no information about zero-day detection" | — | **FALSE.** ρ = **+0.568** (p=0.0001); **+0.41** even restricted to ≥0.98. It is a weak proxy, not uninformative. |
| 🔴 **DO-NOT-WRITE:** "its spread is below its own noise" | — | **FALSE.** The metric is *precise*: median run-to-run SD 0.0020, ~10× below its spread. |

---

## §2 Protocol and metric

| claim | evidence | caveat |
|---|---|---|
| Headline is **macro zero-day PR-AUC** over the 3 adequately-powered unseen families | `metrics.py` enforces it | Heartbleed (n=11), Infiltration (n=36), SQL Injection (n=21) are **excluded as underpowered** — never report them to 4 dp. |
| The blended "benign vs all unknowns" number is a **size-weighted mixture that reorders the ranking** | 2026-07-27 audit; it produced the retracted "XGBoost ≈ CNN" | This is *our own* retracted claim. Use it as evidence of the defect, and say it was ours. |
| **17 % of test rows are exact duplicates of training rows**; dedup costs supervised channels 0.0035–0.0049 | `comparability.py` | 🔑 **The asymmetry is the finding:** all six zero-day families measure **0.0 % overlap**, so duplication inflates *the field's* metric and leaves *ours* untouched. Do not present it as a flaw in our numbers. |
| The transform (`log1p`) is justified **on the headline metric**: 0.6299 ± 0.0031 vs raw 0.1606 ± 0.0039 | `c4_transform_ab.sh`, n=3/arm | Say plainly that the *original* justification cited the contaminated overall-binary metric and was re-run. Right answer, wrong reason, now fixed. |

---

## §3 The gap, demonstrated four independent ways

| demonstration | numbers | caveat |
|---|---|---|
| **One model, two protocols** (`comparability.py`) | as above | — |
| **Tier A, 7 classic baselines** | field **0.977–0.985** vs CNN 0.9928; macro **0.0374 → 0.6049 (16×)**. Logistic regression is **98 % as good** on the published metric and **17× worse** on zero-day | ⚠️ `decision_tree` and `knn` are **score-degenerate** (50.1 % / 49.8 % single tie block) — their PR-AUC is not comparable to a continuous scorer's. **Best valid Tier-A result is the MLP, 3-seed mean 0.4965** (not the n=1 0.5360). 🔴 **k-NN is not citable at all** — macro spans 0.0440–0.4270 across seeds. |
| **Tier B, 4 deep architectures** | field **0.9854–0.9932**; the *worst* zero-day model (Transformer, 0.1106) posts 0.9894, and `deep_gru` (macro 0.3029) posts the tier's **highest** field score, 0.9932 — **inverted** | ⚠️ Recurrent models run over the **feature axis, not time** (68 unordered statistics). Matches published practice, so it is the right comparison, but it is **not evidence about sequence modelling**. Budgets unmatched (LSTM hit the 30-epoch cap). The Transformer result is **one under-tuned configuration**, not a claim about attention. |
| **The base paper's own metric set** | We reproduce their 1D CNN's zero-day number almost exactly (**47.85 % vs 48.34 %**) and **cannot reproduce the Hybrid-LTN's +12 pp gain** (`ltn_repro` 47.24 %) | ⚠️ Comparison in **form, not head-to-head**: different modality (flow features vs payload bytes), zero-day membership differs by a swap (they hold out PortScan, train Infiltration; we do the reverse), class sizes differ. **Composition explains only ~4 pp of the missing 12 pp** — so it is not explained away, but say what is controlled. |

### §3b Two defects in the base paper's zero-day metric, verified arithmetically

1. **No false-positive term.** View 5 contains only attack rows → precision ≡ 1, accuracy *is* recall,
   and **F1 = 2A/(1+A) exactly** — reproduces every published F1 from its accuracy to <0.02 pp. So
   *"accuracy 48→60 %, F1 65→75 %"* is **one result reported twice**, and **a model that flags
   everything scores 100 % on both.**
   🔑 **Our own float32 saturation bug did exactly that (2026-07-27) and was caught only because our
   metric has a benign side.** Say this — it converts a critique into a demonstrated failure mode.
2. **A size-weighted mixture.** Holding the model fixed and changing only the family mix moves the
   headline **48.32 % → 44.38 %**.

---

## §4 The mechanism — why a closed-set model cannot reach a novel class

**The body of the paper.** The gap is not merely unmeasured; it is hard, and we can say why.

| claim | evidence | caveat |
|---|---|---|
| **100 % of Bot flows are classified BENIGN**, mean p(BENIGN) = **0.9984**, all 3 seeds | `bot_failure_analysis.py` | Bot is **confidently asserted benign**, not ambiguous — this is what kills confidence-based remedies. |
| Bot's discriminative features have **0/8 overlap** with the known-class task's | same | 8 features is the comparison set size; state it. |
| Consequently the CNN's Bot ranking is **noise: cross-seed ρ = −0.090** vs 0.68–0.83 for every other family | same | RandomForest is the same (0.068); **the autoencoder is not (0.827)** — so this is a property of closed-set discriminative learning, not of neural nets. |
| **The information is present**: oracle PR-AUC **0.9988** with ~1,000 Bot labels | `skyline_oracle.py` | The oracle **trains on zero-day labels** — it is an upper bound, not a method. Exclude it from any method comparison (as `field_gap.py` does). |
| **No standard OOD score rescues it.** 9 scorers (MSP, max-logit, energy×4, entropy, ODIN×2, margin); best Bot **0.0783** against a falsification threshold **fixed at 0.08 in advance** | `ood_scores.py`, n=3 | ⚠️ **Say it passed by 2 %, do not round it to a clean pass** — a threshold set slightly lower would have flipped it. `energy_T1000` buys Bot 2.29× chance by **destroying** known-class discrimination (macro 0.0326). |

**The synthesis to state explicitly:** a closed-set discriminative model learns only the features that
separate the classes it was trained on, so a novel class is reachable exactly to the extent its
signature overlaps that basis — and **unreachable and unstable** otherwise. **One cause, four
symptoms**: the Phase-4 purity lottery, the Mahalanobis Bot spread, RF's Bot swing, and the CNN's own
failure.

---

## §5 What does not fix it — and this is the expensive part to obtain

| attempted fix | result | caveat |
|---|---|---|
| **More architecture** (Tier B: LSTM, GRU, CNN-LSTM, Transformer) | Nothing escapes the top tier upward; nothing touches Bot (best 0.0626 vs the KG's 0.3103) | CNN-LSTM lands **0.0031** from the CNN — so **the convolutional front-end is doing the work**; pure recurrence halves the score. Cleaner than "LSTMs are bad here". |
| **More classical baselines** (Tier A) | 16× spread, none competitive | see §3 degeneracy caveats |
| **Benign-only anomaly methods** (Tier C: VAE, Deep SVDD, OC-SVM, LOF) | **LOF macro 0.3360 ± 0.0135** does *not* collapse on web attacks | ✅ **A real correction to our own framing**: "benign-only ⇒ collapses on web attacks" is a property of **reconstruction-error scoring**, not of the (B) family. 🔴 **Deep SVDD "beats the AE on Bot" is NOT established** — verdict flips by seed, p=0.256. |
| **The symbolic pillar itself** | **−0.0004 (n.s.)** alone; **significantly HURTS** on top of the KG (0.6926 → 0.6708, **p<0.0001**), diluting Bot 0.2518 → 0.2043 | 🔑 This is a **negative result about our own architecture** — lead with it rather than burying it. |
| **A fitted fuser** | Structurally impossible here: validation contains **no zero-day by construction**, so a combiner cannot learn to weight a zero-day channel. Measured: coefficients `[2.35, 0.02]`, zero macro change | LOCO (manufacture synthetic zero-day from known classes) was **refuted before compute was spent**: no known class in CIC-IDS2017 beacons, so the rotation is predictably null. |
| **Calibration** | Isotonic reaches ECE **0.0001** on known classes while **zero-day ECE does not move** (0.0387) | **The better the calibration, the wider the gap** (287×). Operational consequence: `p=0.9` means 90 % for known attacks and **nothing** for novel ones. ⚠️ Isotonic is unusable as an operating point (74 distinct values → threshold lands in a tie block, FPR 0.70 vs 0.01 target). **Calibrate with isotonic, threshold with Platt.** |
| **Abstention** | Zero-day precision **does not move (+0.0000)** at any non-degenerate coverage | Predicted in advance from the mechanism: **a confidence rule cannot catch confident-and-wrong.** |

---

## §6 What partially works, stated without overclaiming

| claim | evidence | caveat |
|---|---|---|
| **CNN + KG: +0.0528** [+0.0466, +0.0592], p<0.0001, 3/3 seeds, Bot 0.0446 → 0.2518 | `ablation.py`, `fusion_kg.py` | Only the KG earns its place. |
| **The operational statement is better than the PR-AUC one**: reaching 50 % of zero-day flows needs reviewing **52 %** of all traffic with the CNN, **29–32 %** with the KG/fusion | `operational.py` | 🔑 **At any deployable alert budget you see ONLY known attacks** — precision ~1.000 at every budget, **0 zero-day flows in the top 1,000**. This is the honest deployment story and PR-AUC 0.64 does not show it. |
| KG emerging-pattern rule works on **growth rate**: lift **5.94× [5.66, 6.11]**, ~81 % recall | `kg_criteria.py`, n=3 | ⚠️ **Two caveats that must reach the write-up.** ① Growth works substantially because CIC-IDS2017's attacks are **scripted into fixed windows** — a real network with continuous low-rate C2 would not produce this signal, and Bot's real signature is persistence, not bursts. ② **"Temporal burstiness of a raw-feature cluster" does not need a knowledge graph** — a reviewer will say this, so say it first. The KG's justification rests on explanation/corroboration. |
| 🔴 **DO-NOT-WRITE:** "the conjunction gives 81 % precision" | — | Clustering-seed 42 only. n=3 gives lift 1.73–11.57× and precision 0.122–0.814. |
| 🔴 **DO-NOT-WRITE:** the KG's specified "unexplained cluster" mechanism detects zero-day | — | **Lift ≤ 1.00× — at or below chance**, across 3 representations × 3 thresholds. The spec's mechanism is dead; scope is corroboration + explainability. |

### The double dissociation — supporting result, not the lead

**CNN vs autoencoder, non-overlapping across seeds on every family**: XSS **+0.90 (40 SD)**,
Web BF **+0.82 (37 SD)**, Bot **+0.0868 (3.9 SD)**, p<0.0005.

⚠️ **It is a dissociation between two MODELS, not two method families.** RandomForest — a supervised
(A)-family method — **ties the autoencoder on Bot** (0.1311 vs 0.1314, p=0.88) while beating it 0.50
on macro. **Do not write it up as an (A)-vs-(B) result**; that strong form is falsified.

⚠️ **The web-attack half is not zero-day detection.** The CNN assigns **~90 % of Web BF/XSS flows to
`DoS slowloris`**, a known *attack* class — so their 0.92–0.95 PR-AUC is **absorption into a known
attack**. 🔴 The earlier "modality analogue" explanation (web attacks resemble FTP/SSH-Patator) is
**falsified**; do not repeat it.

---

## §7 Measurement discipline — a section, not a footnote

**Argument:** the resolution failure in §1 is a *measurement* claim, so our own measurement standards
have to be visibly higher than the field's. This section is the credibility of §1.

| quantity | value | source |
|---|---|---|
| Nondeterminism (fixed seed, determinism OFF) | **SD 0.0222** | `noise_floor.sh`, n=6 |
| **Seed variance** (determinism ON) | **SD 0.0171** | `noise_postdet.py`, n=6 |
| Data-split variance (5-fold, model + test fixed) | **SD 0.0228** | `protocol_variance.py` |
| ⇒ uncertainty on an **absolute** number | **0.0285** | √(0.0228² + 0.0171²) |
| ⇒ threshold for a **shared-split comparison** | **0.0256** | 2·SE·√2 at n=6 |

**Points to make:**
- **Seed variance and nondeterminism are statistically indistinguishable** (F(5,5)=1.69, **p=0.58**).
- **Determinism is ON and verified byte-identical across sessions 5 days apart.** Pre/post-flag runs
  are **different populations and are never pooled.**
- 🔴 **C2 is retracted**: the CNN-vs-LTN-control gap (+0.0204) is **below the pipeline's own
  reproducibility**. **A flow-level significance test cannot rescue a delta below that** — the single
  most transferable methodological lesson here, and it retracts *our own* headline.
- 🔴 **n=3 is enough for a MEAN and nowhere near enough for a VARIANCE.** Two n=3 SD estimates agreed
  with each other and were both wrong by 5×. **Sample-size adequacy depends on the statistic.**
- 🔑 **A paired comparison must be judged against the PAIRED difference's own SD, not the
  absolute-number floor.** The 0.0222 floor is run-to-run variance of a single channel; over shared
  seeds that common variance **cancels**, exactly as the data-split SD cancels on a shared split.
  **Caught while building fig. 4**, whose first version applied the unpaired floor to paired deltas
  and rendered `FULL vs CNN+KG` (−0.0218, **16.3σ paired**, 3/3 seeds) as *noise*. ⚠️ **The error ran
  in the safe direction — it would have discarded a real result** — but it is the same class of
  mistake as the ones that manufactured false positives here.
  **The right criterion is direction-consistency across all seeds plus the paired effect size**, and
  the two can disagree: **CNN+KG's direction is certain (3/3) while its magnitude is not** (1.7σ,
  spanning 0.027–0.088). Report the direction as established and the magnitude as a range.
- ⚠️ `cnn_paper = 0.6446` is the **max of 11 runs**, not a typical result (mean 0.6217). The honest
  reproducible baseline is the **ensemble, 0.6356**.

---

## §8 Limitations (write these before a reviewer does)

1. **Single dataset.** Cross-dataset (CIC-IDS2018) is **blocked**, not skipped — not available locally.
   This is the weakest point in the paper; state it plainly.
2. **Three powered zero-day families**, not six. Bot / Web BF / XSS. And **Web BF and XSS correlate at
   r = +0.992** (same Thursday campaign, same tool), so macro is ⅓ Bot + ⅔ *one* web signal.
   Robustness row: regrouping shifts values ~0.11–0.15 but **preserves every ordering**.
3. **Flow features, not payload** — a deviation from the base paper's modality. Our 18–29 pp advantage
   on known-class views is a **modality** advantage, **not** an algorithmic one. Say so.
   ✅ **But answer the "why not payload?" question rather than conceding it** (decided 2026-09-05,
   STATUS → Open Decisions → *Input modality*): the H4 oracle probe separates every powered family
   from benign **in the flow-feature basis alone** — **Bot 0.9988 · Web BF 0.9999 · XSS 0.9984**
   PR-AUC — so the Bot gap is a **closed-set-supervision gap, not a modality gap**, and §4's
   mechanism (0/8 feature overlap → ρ ≈ 0 ranking) would **relocate** to a payload basis rather than
   dissolve. Corroborated by the base paper itself, the payload version: its 1D CNN's zero-day number
   matches ours (**48.34 % vs 47.85 %**). ⚠️ **State the honest cost too** — payload would replace the
   web families' *absorption* into `DoS slowloris` with genuine detection, which is an honesty gain
   this paper does not get to claim.
4. **Scripted attack windows** inflate any growth/temporal result (§6).
5. **Behaviour predicates are approximations**: `HighEntropy` is packet-length **standard deviation**,
   not Shannon entropy — any "entropy ⇒ encryption" phrasing is overclaiming.
   `RepeatedConnections` is constant 0; `BeaconLike` is binary.
6. **No adversarial evaluation.** Named as future work rather than implied.

---

## Figures

**All five are built and regenerable from the record** — `field_gap.py` for #1, `paper_figures.py`
for #2–5. **None of them retrains anything**: every value is read from `outputs/metadata/*.json`, the
same artifacts backing the claims above, so a figure and the text cannot silently diverge.

**Each figure carries its own caveat on its face**, because a figure lifted into a talk loses its
surrounding paragraph.

| # | figure | file | the caveat printed on it |
|---|---|---|---|
| 1 | Field metric vs macro zero-day, 40 methods, ≥0.98 band marked | `field_gap.png` | *"ρ = +0.57: a weak proxy, NOT uninformative"* |
| 2 | Bot confidently BENIGN + cross-seed ranking is noise | `fig2_bot_mechanism.png` | 0/8 feature overlap vs oracle PR-AUC 0.9988; web families absorbed into **DoS slowloris**, not benign |
| 3 | Alert budget: 0 zero-day in the top 1,000; depth curve | `fig3_alert_budget.png` | *"the failure macro PR-AUC 0.64 does not show"* |
| 4 | Ablation rungs, paired CIs, σ + seed-consistency per rung | `fig4_ablation.png` | grey = direction not consistent; the 0.0222 floor **cancels** in a paired comparison |
| 5 | Variance decomposition + the session effect vanishing | `fig5_variance.png` | determinism removed a **confound**, not the uncertainty; absolute numbers still carry 0.0285 |

---

## Open before submission

1. **Phase 5's remaining three** — calibration writeup ✅ done, **latency ❌**, **fitted fuser ❌**
   (blocked by the fusion wall — write the blocker as a result).
2. **Cross-dataset** — blocked on data.
3. **Optional:** post-flag LTN-control sweep at n=6, the only route to reopening C2.
4. **Figures 2–5.**

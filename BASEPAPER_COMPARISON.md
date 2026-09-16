# Base-Paper Comparison Audit — Bizzarri et al. vs. this repository

**Base paper:** A. Bizzarri, B. Jalaian, F. Riguzzi, N. D. Bastian, *"A Neuro-Symbolic Artificial
Intelligence Network Intrusion Detection System"*, **2024 33rd International Conference on Computer
Communications and Networks (ICCCN)**, DOI `10.1109/ICCCN61486.2024.10637618`, 9 pages.
Local copy: `basepaper.pdf` (gitignored, 2.9 MB).

**Repository state:** branch `docs/paper-revision`, HEAD `2406bc3`.
**Date:** 2026-09-16. Companion to [AUDIT_REPORT.md](AUDIT_REPORT.md).
**This document is read-only analysis.** No repository file was modified to produce it.

---

## 0. Why this document exists

`verify_draft.py` has one standing **UNBACKED** item:

```
UNBACKED  base paper 48.34 % / 47.85 % / 47.24 %   paper_metrics.json + basepaper.pdf - verify by hand
```

That item is now closed — all three figures verify (§6, rows 1, 14, 15). But reading the PDF end to
end to close it surfaced **one arithmetically false claim that is in the submission text**, **four
defects in the base paper that the repository has not recorded**, **three protocol-fidelity gaps**,
and **one missing experiment that undermines the project's central comparative claim**.

It also *refuted* two confounds I expected to find. Both refutations are reported (§5) because they
strengthen the repository's position and should be quoted.

---

## 1. Verdict

The repository's existing base-paper comparison (`paper_metrics.py`, `STATUS.md` §"Base paper Table
II", `conference_roadmap.md` §1) is **substantially correct and unusually well-caveated**. Every
number it transcribes from Table I and Table II is accurate. Its two headline criticisms — the
`F1 = 2A/(1+A)` degeneracy and the size-weighted-mixture defect — are real, verified, and
independently reproduced here.

Three things need to change.

1. **"We beat the base paper by 18–29 pp on all four known-class views" is false.** The true
   per-view deltas against their 1D CNN are **+18.82 / +0.42 / +28.72 / +7.07 pp**. Two of the four
   are nowhere near the stated band. The claim appears in **7 files, including
   `paper_draft.md:269`, `paper_supplementary.md:132` and `:647`.**
2. **The strongest available criticism of the base paper is not being made.** Their entire claimed
   symbolic gain lives in the one test view that contains no benign rows: per-view Hybrid-LTN minus
   1D CNN is **+0.09 / +0.15 / +0.07 / +2.15 / +12.13 pp**. Their own Fig. 3 shows Hybrid-LTN's
   false positives *rising* 380 → 452. It is a decision-threshold shift, and because they report no
   threshold-free metric, they cannot distinguish that from a better model. This is this project's
   own thesis, provable on their figures.
3. **The reproduction of their model has no matched control.** `ltn_repro` is CE + ω=1; the only
   controls available are focal + ω=0 and focal + no-SAT. **No CE + ω=0 run exists.** The claim
   "their reported improvement does not appear" is therefore confounded with the loss function. One
   ~40-minute run fixes it.

---

## 2. What the base paper actually does

Extracted from the PDF, with page/section references.

| Dimension | Base paper | Source |
|---|---|---|
| **Input modality** | **1500 payload bytes per packet**, each byte an integer 0–255, extracted with the Payload-Byte tool [21] | §Experiments/Dataset, p.4; Grounding `𝒢(items) = ℝ^1500`, p.3 |
| **Unit of analysis** | **Packet** (payload-bearing) | ibid. |
| **Flow CSVs used for** | labels only ("match packets with flow-based labeled data instances") | §Dataset, p.4 |
| **Cleaning** | "**any duplicate instances and those devoid of payload data are eliminated**" | §Dataset, p.4 |
| **Known-class balancing** | **every known attack class equalised to 31,843** (the size of the smallest, FTP-Patator) | Table I, p.4 |
| **Benign** | "arbitrarily decreased … from 362,108" to **200,000** | §Dataset, p.4 |
| **Dataset size** | 454,744 = 200,000 benign + 254,744 attack (8 × 31,843) | Table I |
| **Zero-day set** | **Heartbleed, Brute Force (Web), XSS (Web), Bot, PortScan, Sql Injection** — 31,966 packets | Table I |
| **Known set includes** | **Infiltration** | Table I |
| **Split** | stratified **80 / 10 / 10**; zero-day test-only | §Dataset, p.5 |
| **Architecture** | Input (batch, 1, 1500) → Conv1D 32 k=3 → MaxPool 1×4 → Conv1D "63" k=3 → MaxPool 1×8 → Conv1D 128 k=3 → MaxPool 1×16 → Flatten → Dense(N×5) → Dense(N) | Fig. 2, p.5 |
| **Batch size** | 128 | §Training phase, p.5 |
| **Optimizer** | **Adamax** | Table II caption |
| **Loss** | `Hybrid-Loss = L_CE + ω · SAT Loss`, **ω = 1**, plain cross-entropy | Eq. (9)–(10), p.4; §Training phase, p.5 |
| **Axioms** | **one pair**: `∀x_b P(x_b, l_b) ∧ ∀x_a ¬P(x_a, l_b)` — benign is benign, attack is not benign | Eq. (6), p.3 |
| **Aggregator** | `A_pME`, p = 2 | Eq. (3), §Learning p.3 |
| **LTN at test time** | discarded; "we only utilize the encapsulated DNN, MLP_θ(x), as a standard model" | §Methodology, p.4 |
| **Metrics** | **Accuracy** on five views; **F1 for binary views only**. No PR-AUC, no ROC-AUC, no per-family breakdown | §Results, p.6 |
| **Seeds / variance** | **none stated; single run**, "results after 30 or 50 epochs" | §Results, p.6 |
| **Headline** | zero-day accuracy **48.34 % → 60.47 %**, F1 **65.18 % → 75.37 %** (50 epochs) | Table II |

### Their Table I in full (verified transcription)

| | count | | count |
|---|---:|---|---:|
| BENIGN | 200,000 | **Zero-day attacks** | **31,966** |
| **ATTACKS** | **254,744** | Heartbleed | 13,486 |
| DoS Hulk | 31,843 | Brute Force (Web Attack) | 11,754 |
| DDoS | 31,843 | XSS (Web Attack) | 3,341 |
| DoS GoldenEye | 31,843 | Bot | 2,543 |
| DoS slowloris | 31,843 | PortScan | 830 |
| **Infiltration** | **31,843** | Sql Injection (Web Attack) | 12 |
| DoS Slowhttptest | 31,843 | | |
| SSH-Patator | 31,843 | | |
| FTP-Patator | 31,843 | | |

---

## 3. Findings

`BP-*` = defect in the base paper. `FD-*` = fidelity gap in our reproduction. `CL-*` = error in our
own claims about the base paper.

| ID | Sev | Finding | Confidence |
|---|---|---|---|
| **CL-01** | **HIGH** | "We beat the base paper by 18–29 pp on all four known-class views" is arithmetically false (+18.82 / **+0.42** / +28.72 / **+7.07**). In 7 files including the submission text | CONFIRMED |
| **CL-02** | **HIGH** | `ltn_repro` (CE + ω=1) has **no matched control**. No CE + ω=0 run exists, so "their +12 pp gain does not appear" is confounded with the loss function | CONFIRMED |
| **BP-01** | **HIGH** | The entire claimed symbolic gain is in the one view with no negatives (+12.13 pp there, +0.07 to +2.15 pp on the four views that have benign rows), and their Fig. 3 shows false positives *rising* 380 → 452. It is a threshold shift, and no threshold-free metric is reported | CONFIRMED |
| **BP-02** | **HIGH** | **42.2 % of their zero-day headline is Heartbleed**, which is 13,486 payload packets drawn from **11 flows** — effective sample size ≈ 11, all between one host pair. Heartbleed + Web Brute Force = **79.0 %** of the zero-day set | CONFIRMED |
| **BP-03** | MEDIUM | The confusion matrices imply a known-class evaluation set of **≈159,540 rows = 35.1 %** of Table I's 454,744 — not the 10 % the stated 80/10/10 split gives (45,474). Verified three ways | CONFIRMED |
| **BP-04** | MEDIUM | Table II, 1D CNN, "Binary 15 classes" F1 @50 epochs is printed as **90.88 %, identical to its accuracy**. Recomputed from their own Fig. 3(e): **≈92.3 %**. The same method reproduces the Hybrid-LTN cell (94.20 %) exactly | CONFIRMED |
| **BP-05** | LOW | Text says "we removed **five** attack classes"; Table I lists six and every other reference says "6 unknown classes" | CONFIRMED |
| **BP-06** | LOW | n = 1, no seeds, no variance. Differences of **0.07–0.15 pp** (Multi-class 9 known 81.08 vs 80.99) are reported as results | CONFIRMED |
| **BP-07** | LOW | Fig. 2 specifies "**63 filters**" in conv2 — certainly 64 | CONFIRMED |
| **BP-08** | MEDIUM | A CNN over raw payload bytes on CIC-IDS2017's largely **plaintext** traffic can key on protocol strings and attack-tool User-Agent headers. No leakage control is reported | SUSPECTED |
| **FD-01** | MEDIUM | We call our split "paper-aligned (Bizzarri et al.)" but **do not equalise the known attack classes**. Theirs are 31,843 each; ours run DoS Hulk 184,099 to DoS Slowhttptest 4,399 — a **41.8 : 1** spread | CONFIRMED |
| **FD-02** | MEDIUM | They **deduplicate**; we do not (17.02 % train/test overlap). They **drop payload-less records**; we keep them. So our "47.85 % vs 48.34 %" reproduction compares two differently-filtered populations | CONFIRMED |
| **FD-03** | LOW | Architecture deviations beyond loss and optimizer are undocumented: pooling 1×4/8/16 vs 2/2/2, Dense(N×5)→Dense(N) vs Dense(64)→Dropout→Dense(32)→Dropout→Dense(N), batch 128 vs 256, L2 1e-4 and dropout ours only | CONFIRMED |
| **FD-04** | LOW | `ltn_repro` is **n = 1** and from the pre-determinism population (see AUDIT_REPORT F-01), yet carries a load-bearing comparative claim | CONFIRMED |
| **FD-05** | LOW | The packet-vs-flow unit change is documented only through the Heartbleed example. **No count in their Table I is comparable to any count in `split_report.txt`** | CONFIRMED |

---

## 4. Detailed findings

### CL-01 — HIGH — "18–29 pp on all four known-class views" is false

**Evidence.** Our three-seed CNN against their 1D CNN column, 50 epochs:

| view | ours (n=3) | 1D CNN | Δ | Hybrid-LTN | Δ |
|---|---:|---:|---:|---:|---:|
| Multi-class, 9 known | 99.81 % | 80.99 % | **+18.82** | 81.08 % | +18.73 |
| **Binary, 9 known** | 99.84 % | 99.42 % | **+0.42** | 99.57 % | **+0.27** |
| Multi-class, 15 classes | 96.17 % | 67.45 % | **+28.72** | 67.52 % | +28.65 |
| **Binary, 15 classes** | 97.95 % | 90.88 % | **+7.07** | 93.03 % | **+4.92** |

The band "18–29 pp" describes only the two **multi-class** views. The two **binary** views are
+0.42 pp and +7.07 pp. Against Hybrid-LTN the binary-9-known advantage is **+0.27 pp** — inside any
reasonable noise band, and our own measured noise floor makes it uninterpretable as a win.

**Where it appears.** `docs/STATUS.md:1137`, `docs/STATUS.md:3415` (inside the *input-modality
decision*, where it is load-bearing), `docs/CHANGELOG.md:850`, `:1291`,
`docs/scripts_reference.md:1038`, **`docs/target/paper_draft.md:269` and `:838`**,
**`docs/target/paper_supplementary.md:132` and `:647`**, `docs/target/paper_outline.md:187`.

**Why `verify_draft.py` missed it.** The checker verifies draft numbers against JSON records. This
claim is a *derived range over a comparison*, not a recorded value, and the base-paper side is on the
UNBACKED list. A reviewer with a calculator finds it in a minute.

**Fix.** Replace the phrase everywhere with the per-view numbers. Suggested wording:

> On the two multi-class views we score 18.8 and 28.7 points above their 1D CNN; on the two binary
> views the gap is 0.4 and 7.1 points, because binary known-class detection is already saturated for
> both modalities (both above 99 % on nine known classes).

**Effort.** Minutes — 9 edits. **Risk.** None; it weakens an overstated claim and pre-empts a
reviewer. Add a `verify_draft.py` check that recomputes the four deltas from `paper_metrics.json`.

---

### CL-02 — HIGH — The reproduction has no matched control

**Evidence.** Every LTN configuration ever run, from `runs.jsonl`:

```
('ce',    'base', 1.0, 'fixed')     <- ltn_repro   : the base paper's configuration
('focal', 'base', 0.0, 'fixed')     <- ltn_ctrl_w0 : the "control"
('focal', 'both', 0.1, 'ratio')
('focal', 'both', 0.5, 'fixed')
('focal', 'both', 1.0, 'fixed')
('focal', 'both', 1.0, 'ratio')
('focal', 'both', 2.0, 'fixed')

CE + omega=0 control present?  False
```

**Mechanism.** The base paper's claim is *within-loss*: `L_CE` versus `L_CE + 1·SAT`, everything else
fixed. Our reproduction changes two things at once. `ltn_repro` is CE + ω=1 (47.24 %); the things it
is compared against are `cnn_paper` (focal, no SAT, 47.85 %) and `ltn_ctrl_w0` (focal, ω=0, 45.37 %).
Neither isolates the axiom term.

**Impact.** `STATUS.md:1141` calls this "the project's central finding stated for the first time on
the base paper's own metric … not 'our variants cost macro PR-AUC' but '*their* reported improvement
does not appear.'" As run, the experiment cannot support that: the 47.24 % vs 45.37 % gap is +1.87 pp
in the *same direction* as their claim, and the 47.24 % vs 47.85 % gap crosses the loss function.

**Fix.** One run:

```bash
LTN_LOSS=ce LTN_AXIOMS=base LTN_OMEGA=0 LTN_OMEGA_MODE=fixed LTN_TAG=ltn_repro_ctrl_ce_w0 python scripts/ltn_paper.py
```

Then re-run `paper_metrics.py` and state the delta as `ltn_repro − ltn_repro_ctrl_ce_w0` on view 5.
Do it at **three seeds** on both arms (FD-04), which is ~6 runs and a few hours.

**Risk.** The result may come back *positive* — i.e. the axioms may help at this operating point,
exactly as they claim. That would be a genuine, publishable reversal, and it is better found now.

---

### BP-01 — HIGH — Their entire gain is in the one view that cannot see false positives

**Evidence 1 — where the gain lives.** Hybrid-LTN minus 1D CNN, per view, 50 epochs:

| view | contains benign rows? | Δ |
|---|---|---:|
| Multi-class, 9 known | yes | +0.09 pp |
| Binary, 9 known | yes | +0.15 pp |
| Multi-class, 15 classes | yes | +0.07 pp |
| Binary, 15 classes | yes | +2.15 pp |
| **Binary, 6 unknown** | **no** | **+12.13 pp** |

**Evidence 2 — the mechanism, from their own Fig. 3.** Reading the 9-known confusion matrices:

| model | TN | **FP** | FN | TP |
|---|---:|---:|---:|---:|
| 1D CNN, Fig. 3(a) | ~70,000 | **380** | 536 | 88,624 |
| Hybrid-LTN, Fig. 3(d) | ~70,000 | **452** | 227 | 88,933 |

Hybrid-LTN produces **19 % more false positives** and 58 % fewer false negatives. On the all-15 view
the same trade appears: FP 380 → 452, FN 17,049 → 12,863. On the 6-unknown view, where there are no
benign rows at all, the FN reduction shows up as pure gain: TP 15,453 → 19,330.

*(My confusion-matrix readings are validated: recomputing Binary-9-known F1 from them gives 99.486 %
and 99.619 % against their printed 99.49 % and 99.62 %, and Binary-15 Hybrid-LTN F1 gives 94.20 %
against their printed 94.20 %.)*

**Mechanism.** The SAT term `∀x_b P(x_b,l_b) ∧ ∀x_a ¬P(x_a,l_b)` penalises calling an attack benign.
It shifts the decision boundary toward "attack". That is a legitimate and possibly useful change —
but it is an *operating-point* change, not demonstrated ranking improvement. Because the paper
reports **no ROC-AUC, no PR-AUC, and no precision–recall curve**, nothing in it distinguishes "better
model" from "same model, different threshold". A single ROC-AUC column would settle it.

**Why this matters to us.** This is precisely this project's own central methodological claim — that
the field's metric cannot resolve what it is asked to resolve — and it can be demonstrated on the
base paper's own published figures, without re-running anything. It is a stronger and more
defensible criticism than "their improvement does not appear in our reproduction" (which, per CL-02,
we cannot currently support).

**Fix.** Add this to the write-up as the primary base-paper criticism, with the per-view delta table
and the FP counts. Keep the `F1 = 2A/(1+A)` point as the second criticism; it is about redundancy,
whereas this one is about validity.

---

### BP-02 — HIGH — 42 % of their zero-day headline is a class with ~11 independent events

**Evidence.** Their Table I zero-day counts are **payload-bearing packets**; the same families in
CIC-IDS2017 flow data are:

| family | their packets | our flows | packets per flow | their share of the zero-day set |
|---|---:|---:|---:|---:|
| **Heartbleed** | 13,486 | **11** | **1,226.0** | **42.19 %** |
| Web Attack Brute Force | 11,754 | 1,507 | 7.80 | 36.77 % |
| Web Attack XSS | 3,341 | 652 | 5.12 | 10.45 % |
| Bot | 2,543 | 1,956 | 1.30 | 7.96 % |
| PortScan | 830 | 158,804 | **0.005** | 2.60 % |
| Web Attack Sql Injection | 12 | 21 | 0.57 | 0.04 % |

**Mechanism.** CIC-IDS2017 contains 11 Heartbleed flows, all between one attacker–victim pair in one
short window. Payload-Byte expands them into 13,486 packets because a Heartbleed exfiltration is one
connection emitting many large payloads. Those 13,486 rows are **not 13,486 independent observations**
— they are ~11, massively correlated, and they are split 80/10/10 *at the packet level*, so packets
from the same connection sit on both sides of the boundary.

**Impact.** Their headline "Binary 6 unknown classes" is 42.2 % Heartbleed and 36.8 % Web Brute
Force — **79.0 % from two families**, one of which has an effective n of about 11. The 48.34 % →
60.47 % improvement is therefore, in large part, a statement about whether one host pair's traffic
happens to cross a shifted threshold.

The mirror image is **PortScan**: held out as zero-day, but 99.5 % of its packets have no payload and
are deleted by their own cleaning step, leaving 830 rows — 2.6 % of the zero-day set. Our
documentation calls the difference "a swap: they hold out PortScan and train on Infiltration". The
swap description is right, but it understates the effect: **after their payload filter, PortScan is
almost absent from their evaluation.**

**Fix.** Two sentences in the related-work/comparison section, with the packets-per-flow column
above. It also retires a mild worry in our own docs — that their PortScan hold-out makes their
zero-day task easier than ours. It does not; it makes it *smaller*.

---

### BP-03 — MEDIUM — The confusion matrices contradict the stated 80/10/10 split

**Evidence.** From Fig. 3(a), the 1D CNN on 9 known classes: 70,000 + 380 + 536 + 88,624 =
**159,540 rows**. A stratified 10 % test split of Table I's 454,744 gives **45,474**.

Three independent checks say the matrices, not my reading, are self-consistent:

1. Accuracy from Fig. 3(a): 158,624 / 159,540 = **99.43 %** vs their printed **99.42 %**.
2. Accuracy from Fig. 3(d) (Hybrid-LTN): 158,933 / 159,612 = **99.57 %** vs printed **99.57 %**.
3. The benign : attack ratio in the matrices is 70,380 : 89,160 = **44.1 : 55.9**, matching Table I's
   200,000 : 254,744 = 44.0 : 56.0 exactly.

So the evaluation set is a correctly stratified sample of **35.1 %** of the dataset. The zero-day
matrices total exactly 31,966 — the full Table I zero-day count — consistent with "zero-day used only
in the test phase". Adding the two gives 191,506, and the all-15 accuracy recomputes to 90.90 %
against their printed 90.88 %.

**Impact.** Either Table I's counts are not the quantity the split is applied to, or the split is not
80/10/10. Since every accuracy reproduces at the larger size, the numbers in Table II are internally
consistent — but the **protocol as described cannot generate them**, so nobody can reproduce their
setup from the paper. That is worth one sentence in our related-work section, and it is a reason to
treat "paper-aligned split" as an approximation rather than a replication (see FD-01).

---

### BP-04 — MEDIUM — A transcription error in Table II

**Evidence.** Table II, 50 epochs, "Binary 15 classes": accuracy row gives 1D CNN **90.88 %**; the F1
row gives 1D CNN **90.88 %** — identical. Every other model on that row has F1 > accuracy
(Hybrid-LTN 93.03 → 94.20; M-LTN 92.19 → 93.47; B-LTN 89.40 → 90.93), and at 30 epochs the 1D CNN
itself has 90.68 → 92.12.

Recomputing from their Fig. 3(e): TP = 104,077, FP = 380, FN = 17,049 → precision 99.64 %, recall
85.93 %, **F1 = 92.28 %**. The identical method reproduces the Hybrid-LTN cell at 94.20 %, exactly as
printed.

**Impact.** Small in itself, but `paper_metrics.py:102` transcribes the erroneous 90.88 into
`PAPER_F1`, so it propagates into our comparison table.

**Fix.** Keep the transcription faithful to the PDF (it should record what they printed) but annotate
it: `"Binary 15 classes": {"Hybrid-LTN": 94.20, "1D CNN": 90.88}  # 1D CNN F1 == its accuracy in the
PDF; recomputed from Fig. 3(e) it is ~92.3 — probable transcription error in the source.`

---

### BP-05 to BP-08 — condensed

* **BP-05.** §Dataset, p.4: "We removed **five** attack classes from the training set". Table I lists
  six zero-day classes and §Results says "6 unknown classes" throughout. A stray error, worth one
  parenthetical if we describe their protocol precisely.
* **BP-06.** No seed, no repetition, no variance anywhere in the paper; "results after 30 or 50
  epochs" is the only robustness statement. Differences of **0.07–0.15 pp** are presented as results
  (Multi-class 9 known 81.08 vs 80.99; Multi-class 15 67.52 vs 67.45). **We are the right people to
  say this**: we measured a training noise floor of SD 0.0222 on macro zero-day PR-AUC over six
  identical runs, retracted our own C2 result for sitting 0.9 SD inside it, and had to install
  determinism flags to get a fixed point. A 0.09 pp difference from a single run is not a result. One
  sentence in related work, cross-referenced to our §noise-floor section.
* **BP-07.** Fig. 2 labels conv2 "**63 filters**". Almost certainly 64. Note it only if we reproduce
  their architecture exactly.
* **BP-08.** *(SUSPECTED.)* CIC-IDS2017's 2017-era capture is largely plaintext HTTP. A CNN reading
  1500 raw payload bytes can key on protocol strings and, for the web and Patator attacks, on the
  attack tool's own User-Agent and request structure. That is a label proxy of exactly the kind
  §1.3 of our audit prompt warns about, and the paper reports no leakage control, no feature
  attribution and no ablation. I cannot confirm it without the payload data, which we do not hold.
  State it as an open question, not a finding.

---

### FD-01 — MEDIUM — We do not equalise the known attack classes, but call the split "paper-aligned"

**Evidence.** `config.yaml:8` — *"PROTOCOL: paper-aligned split (Bizzarri et al.)"*;
`preprocess_paper.py:2` — *"Paper-aligned split (Bizzarri et al.), Phase 0."* What we implement
(`preprocess_paper.py:82-84`) is benign under-sampling to a 1 : 1 ratio against the **total** known
attack count. What they implement (Table I) is **per-class equalisation of all eight known attack
families to 31,843 each**, then benign fixed at 200,000.

The resulting training distributions are not comparable:

| | base paper | ours |
|---|---|---|
| benign share | 44.0 % | 50.0 % |
| each attack class | 7.0 % (identical) | 20.8 % (Hulk) down to 0.50 % (Slowhttptest) |
| largest : smallest attack | **1.0 : 1** | **41.8 : 1** (184,099 : 4,399) |

**Impact, and an important negative.** I expected this to explain the +18.8 pp multi-class gap.
**It does not.** Composition-neutral (per-class balanced) multi-class accuracy on our nine known
classes is **99.78 %** against the as-reported 99.81 % — the delta versus their 80.99 % moves from
+18.82 to **+18.79 pp**. Every one of our nine classes sits above 98.9 % recall:

```
BENIGN 99.70 · DDoS 99.99 · DoS GoldenEye 99.90 · DoS Hulk 99.91 · DoS Slowhttptest 99.82
DoS slowloris 99.14 · FTP-Patator 99.62 · PortScan 99.96 · SSH-Patator 100.00
```

So the repository's attribution of the known-class advantage to **modality** survives this check and
should be quoted with it. The fidelity gap is still worth fixing in the *description*: "paper-aligned"
overstates what `preprocess_paper.py` does.

**Fix.** Change the wording in `config.yaml` and `preprocess_paper.py` to "paper-*inspired* split
(stratified 80/10/10 with rare families held out, after Bizzarri et al.; **their per-class
equalisation is not reproduced**)", and add the per-class equalisation as an optional
`protocol.balance: {benign_ratio | per_class}` arm. Report the composition-neutral accuracy
alongside the raw one — it costs nothing and closes the obvious objection.

---

### FD-02 — MEDIUM — They deduplicate and drop payload-less records; we do neither

**Evidence.** Base paper, §Dataset p.4: *"Upon data labeling, any duplicate instances and those
devoid of payload data are eliminated."* Our pipeline has no dedup step; measured cross-split exact
duplicate overlap is **17.02 %** (AUDIT_REPORT F-10).

**Impact, and a second negative.** I expected the duplicate overlap to inflate our known-class
advantage. Measured on the same three seeds, removing every test row that has an exact twin in train:

| view | all rows | deduplicated | Δ |
|---|---:|---:|---:|
| Multi-class, 9 known | 99.81 % | 99.85 % | +0.04 |
| Binary, 9 known | 99.84 % | 99.89 % | +0.05 |
| Multi-class, 15 classes | 96.17 % | 95.46 % | −0.71 |
| Binary, 15 classes | 97.95 % | 97.60 % | −0.35 |
| **Binary, 6 unknown** | 47.85 % | 47.85 % | **0.00** |
| False alarm rate | 0.31 % | 0.19 % | −0.12 |

**Deduplication does not explain our advantage.** Accuracy is saturated at 99.8 %, so the duplicate
rows are not where the headroom is, and the zero-day view is exactly unchanged (zero-day families
have 0 % train overlap by construction). Report this; it closes the objection cleanly.

**The part that does matter is the second half of their filter.** "Devoid of payload data are
eliminated" is structurally the same filter as Engelen et al.'s `X - Attempted` relabelling — records
for a connection that transmitted nothing. Our own corrected-label run found that excluding those
flows collapses **Web Attack Brute Force PR-AUC from 0.8861 to 0.0072**. The base paper's zero-day
set is *already* free of them. So:

> **The "47.85 % vs 48.34 %" agreement that our docs call a reproduction of their 1D CNN's zero-day
> number is an agreement between two figures computed on differently filtered populations.** Their
> Web Brute Force is 11,754 payload-bearing packets; ours is 1,507 flows of which the corrected
> labelling says the detectable majority transmitted nothing.

This matters because that agreement is load-bearing in `STATUS.md:3415`, the decision not to pursue
payload modality ("their 1D CNN's zero-day number matches ours (48.34 % vs 47.85 %) — payload costs
known-class performance and buys nothing on zero-day"). The decision may well still be right — the H4
oracle evidence for it is independent and strong — but this particular corroboration is weaker than
it reads.

**Fix.** (a) One sentence qualifying the 47.85/48.34 agreement wherever it appears, especially in the
input-modality decision cell. (b) Report the deduplicated column above alongside the raw one — it is
already computed and it pre-empts the reviewer. (c) Optionally, recompute view 5 on the
`X - Attempted`-excluded variant, which is the closest available analogue of their filtered
population; `preprocess_improved.py` already produces it.

---

### FD-03 to FD-05 — condensed

* **FD-03.** `conference_roadmap.md` §1 tabulates Input / Split / Balance / Axioms / Loss / Metrics /
  Result but not architecture. Undocumented deviations: pooling **1×4, 1×8, 1×16** vs our **2, 2, 2**
  (forced by input width — 1500 bytes needs aggressive pooling, 68 features cannot afford it); their
  head is **Dense(N×5) → Dense(N)** vs our **Dense(64, "embedding") → Dropout(0.4) → Dense(32) →
  Dropout(0.3) → Dense(N)**; batch **128** vs **256**; **no dropout and no L2** in their model, both
  in ours. Add a row to the deviation table. Note in passing that their own claim to use "the
  identical architecture" for benchmark and Hybrid-LTN is preserved *within* their paper, but our
  reproduction shares almost none of it.
* **FD-04.** `ltn_repro` is **n = 1** and predates the determinism flags (AUDIT_REPORT F-01), yet
  `STATUS.md:1141` builds "the project's central finding" on it. Our own non-negotiable #3 forbids
  this. Run it at three seeds together with the CL-02 control.
* **FD-05.** The packet→flow unit change is currently conveyed only by the Heartbleed example
  (13,486 vs 11). State it as a general rule: **their Table I counts payload-bearing packets, ours
  count flows; no count in the two tables is directly comparable.** The packets-per-flow column in
  BP-02 is the artefact to publish.

---

## 5. Two confounds I expected and could not find

Reported because they are load-bearing in the other direction — they defend the repository's existing
claims, and they cost nothing to quote.

1. **Class-composition imbalance does not explain our known-class advantage.** Composition-neutral
   (balanced) multi-class accuracy is 99.78 % against 99.81 % as reported; the gap versus their 1D
   CNN moves +18.82 → +18.79 pp. All nine per-class recalls are ≥ 98.97 %.
2. **Duplicate overlap does not explain it either.** Deduplicated, the four known-class views move by
   +0.04, +0.05, −0.71 and −0.35 pp, and view 5 is unchanged to four decimal places.

Together these leave **modality** as the standing explanation for the known-class gap, which is
exactly what `STATUS.md:1137` already says. The claim is now measured rather than asserted — and, with
CL-01 fixed, correctly sized.

---

## 6. Every base-paper number quoted in this repository, verified against the PDF

| # | Number, as used in the repo | Repo location | PDF source | Verdict |
|---|---|---|---|---|
| 1 | 1D CNN, Binary 6 unknown, 50 ep = **48.34 %** | `paper_metrics.py:98`, STATUS, drafts | Table II | ✅ exact |
| 2 | Hybrid-LTN, Binary 6 unknown, 50 ep = **60.47 %** | ibid. | Table II | ✅ exact |
| 3 | Multi-class 9 known: 81.08 / 80.99 | `paper_metrics.py:94` | Table II | ✅ exact |
| 4 | Binary 9 known: 99.57 / 99.42 | `paper_metrics.py:95` | Table II | ✅ exact |
| 5 | Multi-class 15: 67.52 / 67.45 | `paper_metrics.py:96` | Table II | ✅ exact |
| 6 | Binary 15: 93.03 / 90.88 | `paper_metrics.py:97` | Table II | ✅ exact |
| 7 | F1 Binary 9 known: 99.62 / 99.49 | `paper_metrics.py:101` | Table II | ✅ exact |
| 8 | F1 Binary 15: 94.20 / 90.88 | `paper_metrics.py:102` | Table II | ✅ exact transcription of a **source error** (BP-04) |
| 9 | F1 Binary 6 unknown: 75.37 / 65.18 | `paper_metrics.py:103` | Table II | ✅ exact |
| 10 | 30-epoch pairs 47.13→64.07, 55.70→71.55 | `paper_metrics.py` docstring | Table II | ✅ exact |
| 11 | `F1 = 2A/(1+A)` reproduces their F1 row | `paper_metrics.py` docstring | derived | ✅ **independently reproduced**: 48.34 → 65.177 (printed 65.18); 60.47 → 75.367 (printed 75.37) |
| 12 | Their zero-day counts (13,486 / 11,754 / 3,341 / 2,543 / 830 / 12) | `paper_metrics.json` | Table I | ✅ exact |
| 13 | Their zero-day shares (42.2 / 36.8 / 10.5 / 8.0 %) | STATUS composition table | derived from Table I | ✅ exact |
| 14 | Ours, Binary 6 unknown = **47.85 %** | `paper_metrics.json` | our runs | ✅ reproduced (3 seeds, 47.852 %) |
| 15 | `ltn_repro` Binary 6 unknown = **47.24 %** | `paper_metrics.json` | our runs | ✅ value reproduced; ⚠️ n=1 and **uncontrolled** (CL-02, FD-04) |
| 16 | "1500 payload bytes via Payload-Byte" | roadmap §1, STATUS | §Dataset, Grounding | ✅ correct |
| 17 | "stratified 80/10/10" | roadmap §1 | §Dataset p.5 | ✅ as stated in the PDF; ⚠️ contradicted by their own Fig. 3 (BP-03) |
| 18 | "plain CE + ω·SAT, ω=1, Adamax" | roadmap §1 | Eq. (9), §Training, Table II caption | ✅ correct |
| 19 | "Ax1+Ax2 only" | roadmap §1 | Eq. (6) | ✅ correct — one conjunction, two conjuncts |
| 20 | "they hold out PortScan and train on Infiltration" | `paper_metrics.py`, STATUS | Table I | ✅ correct; ⚠️ incomplete — PortScan survives their payload filter at 0.5 % (BP-02) |
| 21 | "their Heartbleed is 13,486 payload packets; flow data has 11" | STATUS | Table I + ours | ✅ correct; ⚠️ the implication (effective n ≈ 11 carrying 42 % of their headline) is not drawn (BP-02) |
| 22 | "composition explains ~4 pp: 48.32 % → 44.38 %" | STATUS | `paper_metrics.json` | ✅ internally consistent |
| 23 | **"we beat them 18–29 pp on all four known-class views"** | 7 files incl. drafts | derived | ❌ **FALSE** — +18.82 / +0.42 / +28.72 / +7.07 (CL-01) |
| 24 | "we cannot reproduce the Hybrid-LTN's +12 pp symbolic gain" | STATUS:1141 | derived | ⚠️ **not supported as run** — no matched control (CL-02) |
| 25 | "their benign was decreased from 362,108 to 200,000" | not currently quoted | §Dataset p.4 | ℹ️ worth adding — it shows their benign pool is ~11× smaller than ours after packet filtering |

---

## 7. Corrected comparison table (drop-in replacement for STATUS §"Base paper Table II")

```markdown
### Base paper Table II (50 epochs, Adamax) with our column added

| Test set | Hybrid-LTN | 1D CNN | CNN (ours, n=3) | Δ vs 1D CNN | ours, deduplicated |
|---|---:|---:|---:|---:|---:|
| Multi-class, 9 known   | 81.08 % | 80.99 % | 99.81 % | +18.82 | 99.85 % |
| Binary, 9 known        | 99.57 % | 99.42 % | 99.84 % |  +0.42 | 99.89 % |
| Multi-class, 15 classes| 67.52 % | 67.45 % | 96.17 % | +28.72 | 95.46 % |
| Binary, 15 classes     | 93.03 % | 90.88 %¹| 97.95 % |  +7.07 | 97.60 % |
| **Binary, 6 unknown**  | 60.47 % | 48.34 % | 47.85 % |  −0.49 | 47.85 % |

¹ Their F1 for this cell is printed as 90.88 %, identical to its accuracy; recomputed from their
  Fig. 3(e) it is ~92.3 %. Probable transcription error in the source.

Comparison is in FORM, not head-to-head. Five documented deviations: modality (1500 payload bytes
vs 68 flow features) · unit (packet vs flow — their Heartbleed is 13,486 packets from 11 flows) ·
zero-day membership (they hold out PortScan, which their payload filter then reduces to 830 rows,
and train on Infiltration) · class balancing (they equalise every attack class to 31,843; we do not)
· cleaning (they remove duplicates and payload-less records; we remove neither).

Two checks that came back negative, and are reported because they defend the comparison:
composition-neutral accuracy moves the multi-class gap +18.82 → +18.79 pp, and deduplication moves
the four known-class views by at most 0.71 pp. The known-class advantage is a modality effect.
```

---

## 8. Fixes, prioritised

### Must fix before the paper is shared

| # | Fix | Files | Effort |
|---|---|---|---|
| 1 | Replace "18–29 pp on all four known-class views" with the per-view deltas | `STATUS.md:1137,3415`, `CHANGELOG.md:850,1291`, `scripts_reference.md:1038`, `paper_draft.md:269,838`, `paper_supplementary.md:132,647`, `paper_outline.md:187` | 30 min |
| 2 | Add a `verify_draft.py` check recomputing the four deltas from `paper_metrics.json` so this cannot recur | `scripts/verify_draft.py` | 20 min |
| 3 | Run the missing CE + ω=0 control, at 3 seeds, alongside 3 seeds of `ltn_repro` | `scripts/ltn_paper.py` (no change — env vars only) | ~4 h compute |
| 4 | Restate the base-paper criticism around BP-01 (threshold shift, FP 380→452, no threshold-free metric) as the primary one | `paper_body.md`/`paper_draft.md` related work | 1 h |
| 5 | Qualify the "47.85 % vs 48.34 %" agreement — differently filtered populations (FD-02) | `STATUS.md:3415`, drafts | 20 min |

### Should fix

| # | Fix | Files | Effort |
|---|---|---|---|
| 6 | Add BP-02's packets-per-flow table and the "42 % of their headline is n≈11" point | drafts, `paper_metrics.py` docstring | 1 h |
| 7 | Re-word "paper-aligned split" → "paper-inspired", and record that per-class equalisation is not reproduced | `config.yaml:8`, `preprocess_paper.py:2` | 15 min |
| 8 | Annotate the BP-04 transcription error in `PAPER_F1` | `scripts/paper_metrics.py:102` | 5 min |
| 9 | Publish the deduplicated and composition-neutral columns (§5) — both already computed | `paper_metrics.py`, STATUS | 1 h |
| 10 | Add the architecture row to the deviation table (FD-03) | `conference_roadmap.md` §1 | 15 min |
| 11 | Add BP-03 (the 35.1 % confusion-matrix inconsistency) and BP-06 (n=1, 0.09 pp deltas) to related work | drafts | 30 min |

### Optional

| # | Fix | Effort |
|---|---|---|
| 12 | Implement `protocol.balance: per_class` as a second protocol arm and report both | ~1 day + re-runs |
| 13 | Recompute view 5 on the `X - Attempted`-excluded variant as the closest analogue of their filtered population (`preprocess_improved.py` already produces it) | ~2 h |
| 14 | Note BP-05 ("five" vs six) and BP-07 ("63 filters") if their protocol is described in detail | 10 min |
| 15 | Raise BP-08 (payload/plaintext leakage surface) as an open question in the limitations of the modality decision | 20 min |

---

## 9. What the repository already gets right

Worth recording, because it is most of the work and it is good.

* **The `F1 = 2A/(1+A)` degeneracy** (`paper_metrics.py` docstring) is a genuinely sharp finding,
  correctly derived, and I reproduced it to within 0.01 pp on both models. The observation that our
  own float32 saturation bug would have scored 100 % under view 5 is the right way to make it land.
* **The size-weighted-mixture critique** and the 48.32 % → 44.38 % re-weighting are correct and
  correctly bounded ("composition explains ~4 pp, not the missing 12").
* **The three deviations already documented** — modality, zero-day membership, class sizes — are the
  right three to lead with; this document adds two more (balancing, cleaning) rather than correcting
  them.
* **`ltn_repro` is configured faithfully**: `loss=ce, axioms=base, omega=1.0, omega_mode=fixed`
  matches Eq. (9)–(10) and ω=1 exactly. The problem is the missing control, not the arm.
* **Every transcribed number is accurate** — 12 of 12 Table I and Table II values check out against
  the PDF, including one that faithfully reproduces an error in the source.
* **The `conference_roadmap.md` verdict — "not flawed, misaligned"** — was the right call in 2026-06,
  and it is still the right call. Nothing in this audit says the base paper is fraudulent or that our
  deviation from it was a mistake. It says their evaluation cannot support the weight their
  conclusion puts on it, and that we can show exactly why, from their own figures.

---

*Read-only analysis. Companion to [AUDIT_REPORT.md](AUDIT_REPORT.md). No repository file other than
this one was created or modified.*

# Full-Repository Audit — NeuroSymbolic-IDS

**Scope:** Phase 1 (read-only) of `nids-repo-audit-prompt.md`.
**Repository state audited:** branch `docs/paper-revision`, HEAD `2406bc3` (2026-09-15), 259 commits, 271 tracked files.
**Date of audit:** 2026-09-16.
**Files written by this audit:** this file only. Nothing else in the repository was modified.

---

## 1. Verdict

The headline metric — **macro zero-day PR-AUC** — is measuring what it claims to measure. There is
no oversampling-before-split, no scaler fitted on test, no zero-day label in train or val, no secret
in 259 commits, and the project has already found and disclosed most of the defects a reviewer would
reach for. That is unusual and it should be said first.

Three things matter.

1. **The reported CNN baseline cannot be reproduced by the code in the repository.** `cnn_paper =
   0.6446` and the 3-seed mean `0.6399` were produced before `determinism.py` existed. Re-running
   today's code at the same seeds gives **0.6298 / 0.6269 / 0.6330 (mean 0.6299)**. Every improvement
   in the project is quoted against the 0.6399 anchor. Directions survive; the numbers do not.
2. **The split is random over a chronologically ordered capture and is not grouped by session or
   host.** 54.9 % of test flows share an exact 5-tuple with a training flow — 100 % for four known
   families *and for all three Web Attack zero-day families*. 17.0 % of test rows are exact
   feature-vector duplicates of a training row. The project measured the second; it has never
   measured the first.
3. **The flagship "current best" is an offline number presented as an operational one.** `0.7123` and
   "57.6 % of unknown flows at 1 % FPR" come from the **transductive** KG variant, which scores a
   flow in window 3 using window 17. The online variant the same script computes gives 0.7032 and
   54.6 %.

**Deployable? No** — and the repository does not claim it is. **Trustworthy as research?** Yes for the
comparative conclusions, with the reservations below; no for any absolute number quoted to four
decimal places.

---

## 2. Findings

Sorted by severity, then by impact within severity.

| ID | Sev | Category | Location | Defect | Consequence | Confidence |
|---|---|---|---|---|---|---|
| **F-01** | CRITICAL | Reproducibility | `outputs/metadata/runs.jsonl`; `scripts/determinism.py:52-56`; `README.md:184`; `scripts/fusion_kg.py:6,89` | Headline CNN baseline (0.6399 / 0.6446) was produced by a code state with no determinism flags; that state no longer exists | Re-running the repo gives 0.6299. Every delta in the project is measured against an unreproducible anchor | CONFIRMED |
| **F-02** | HIGH | Leakage (structural) | `scripts/preprocess_paper.py:88-96` | No grouped split: 54.9 % of test flows share their exact Flow ID (5-tuple) with a training flow; 100 % for DoS GoldenEye/Hulk/Slowhttptest/slowloris and for Web BF / XSS / SQLi | Known-class metrics measure session recall, not detection; the web zero-day scores sit on sessions the model has already seen | CONFIRMED |
| **F-03** | HIGH | Leakage (temporal) | `scripts/preprocess_paper.py:90-94` | Stratified random split over a temporally ordered 5-day capture; 100 % of test flows fall inside the train time range | Future traffic trains a model evaluated on the past; no claim about detecting *later* traffic is supported | CONFIRMED |
| **F-04** | HIGH | Evaluation validity | `scripts/preprocess_paper.py:82-84` | Benign under-sampled 4.11× **before** the split, so the test set is not a sample of the capture | Every PR-AUC / lift / precision figure is measured at an inflated attack base rate. Macro 0.6446 → 0.6015 at capture prevalence; Bot 0.0591 → 0.0152 | CONFIRMED |
| **F-05** | HIGH | IDS realism | `scripts/kg.py:243-283`; `outputs/metadata/operational_best.json` | The quoted best (0.7123; 57.6 % @1 % FPR) uses the transductive KG score; the causal/online variant gives 0.7032 / 54.6 % | The project's flagship operational claim is not computable online | CONFIRMED |
| **F-06** | HIGH | Reproducibility | `outputs/metadata/ksweep_heldout.json` | The held-out re-selection of k=800 — the sole defence against the test-set tuning bias `ksweep_fusion.py:22-27` admits — has **no generating script** | The evidence that the flagship +0.0724 is not a tuning artefact cannot be regenerated | CONFIRMED |
| **F-07** | HIGH | Evaluation validity | `scripts/metrics.py:79`; `operational.py:390`; `operational_best.py:110`; `fusion_weight.py:107`; `metric_divergence.py:109`; `aug_analyse.py:186` | The 1 %-FPR decision threshold is taken as a quantile of the **test** set's benign scores | Every threshold metric (recall@FPR, F1, precision) is reported at an operating point fitted to the data it is reported on | CONFIRMED |
| **F-08** | HIGH | Feature leakage | `scripts/behavior.py:144-157, 283` | `BeaconLike` = "destination port ∉ well-known set". 8080 excluded, 8443 included; selected by measuring ROC against **Bot**, a test-only zero-day class | Fires on 99.95 % of Bot vs 22.65 % of benign purely because this capture's C2 listens on 8080. A capture artefact selected with held-out labels | CONFIRMED |
| **F-09** | HIGH | Engineering | repository-wide | No test suite: 0 test files across 77 scripts / 18,010 lines | Nothing mechanically asserts the leakage boundary, split integrity, or feature construction | CONFIRMED |
| **F-10** | MEDIUM | Data integrity | `scripts/preprocess_paper.py` (no dedup step) | 17.02 % of test rows are exact duplicates of a training row (PortScan 58.3 %, SSH-Patator 48.6 %, Hulk 25.3 %) | Inflates every known-class / binary figure, including the 0.9928 that anchors the field-gap argument. **Measured and disclosed** by `comparability.py`; the README table still leads with the non-dedup value | CONFIRMED |
| **F-11** | MEDIUM | Statistics | `scripts/significance.py:196-222` | 13 bootstrap comparisons at α=0.05, no multiple-comparison correction | Family-wise error ≈ 0.49 if all nulls were true; borderline results are weaker than stated | CONFIRMED |
| **F-12** | MEDIUM | Baseline fairness | `scripts/baselines.py:71-88` | XGBoost/RF/IsolationForest get fixed hyperparameters, no validation set, no early stopping; the CNN gets 50 epochs with val-monitored early stopping and LR scheduling | Comparisons against the classical baselines are not tuning-matched in either direction | CONFIRMED |
| **F-13** | MEDIUM | Divergent implementation | `Capstone_final (4) (1).ipynb` (untracked, 1.6 MB, project root) | A second, contradictory pipeline: 70 features, **PortScan as zero-day**, Infiltration trained on n=29 and scored on n=3, accuracy as headline, all 22 `execution_count` fields `null` | Results in it correspond to no commit and no script; its protocol contradicts `config.yaml` | CONFIRMED |
| **F-14** | MEDIUM | Statistical validity | notebook cell 35 | "Heartbleed recall 0.0000 → 1.0000" rests on n=11, with a rule whose second threshold has no stated derivation, at a system FPR of 10.2 % | Presented as an adaptability result; it is an unfalsifiable demo | CONFIRMED |
| **F-15** | MEDIUM | Pipeline order | `scripts/preprocess.py:87-91` | Constant-column selection computed on the *temporal* train half, which contains rows that later land in the paper test split | A feature-selection decision informed by rows that end up in test. Effect almost certainly nil (10 all-zero columns) but the boundary is crossed | CONFIRMED |
| **F-16** | MEDIUM | IDS realism | repository-wide | No adversarial-evasion evaluation of any kind (only ODIN's input perturbation, `ood_scores.py:23`, which is an OOD technique, not a threat model) | Nothing measures whether padding, timing manipulation or rate shaping defeats the detector | CONFIRMED |
| **F-17** | MEDIUM | Statistical validity | project-wide | One test split (`X_test.npy`, 114,658 rows) has been the reporting surface for every experiment across ~5 months and 239 logged runs | Cumulative selection pressure on a single split; the split-half protocol covers only two experiments | CONFIRMED |
| **F-18** | MEDIUM | Documentation | `docs/architecture.md:34,83`; `docs/dataset.md:86`; `docs/pipeline.md:41`; `docs/target/target_architecture.md:85` | Four docs state "70 features"; the verified count is 68. *Corrected 2026-09-16: `architecture.md` and `dataset.md` already carry a frozen banner naming 68; only `pipeline.md` (banner silent on the count) and `target_architecture.md` (not frozen) were live errors* | Reader-facing contradiction with `config.yaml` and `check.py` | CONFIRMED |
| **F-19** | LOW | Reproducibility | `scripts/determinism.py:69` | `os.environ["PYTHONHASHSEED"]` is set inside the running interpreter, after hash randomisation has already been seeded | The one listed control that does nothing. Harmless, but documented as effective | CONFIRMED |
| **F-20** | LOW | Metric hygiene | `outputs/predictions/y_prob_*_{,logodds_}test.npy` | Two score variants of the same run circulate and disagree in the 4th decimal (s43: macro 0.6355 vs 0.6353; Bot 0.0245 vs 0.0241) | The project quotes 4 dp; which array a number came from is not recorded | CONFIRMED |
| **F-21** | LOW | Security hygiene | `scripts/dashboard_server.py:491-492` | KG explanation strings interpolated into HTML with no escaping | Stored-XSS shape. Bound to 127.0.0.1 and fed only local data, so not exploitable as configured | CONFIRMED |
| **F-22** | LOW | Code safety | `scripts/latency.py:228` | `exec(compile(ast.Module(...)))` to lift a class out of `kg.py` source | Fragile and unnecessary; a normal import or a shared module would do | CONFIRMED |
| **F-23** | LOW | Hygiene | `outputs/.check.pid` | Tracked despite the `outputs/*.pid` ignore rule (committed before the rule) | Generated file under version control | CONFIRMED |
| **F-24** | LOW | Dependencies | `requirements.txt` | Fully pinned (good), but `tensorflow==2.15.1` is end-of-life and Windows-CPU-only; the venv carries packages absent from the file (`numba`, `llvmlite`, `cryptography`) | No lockfile; environment drift is invisible | CONFIRMED |
| **F-25** | LOW | Model artefacts | `scripts/cnn_paper.py:183-205`; `scripts/novelty.py:52` | Both `{TAG}.keras` (post-`restore_best_weights`) and `{TAG}_best.keras` (checkpoint) are written; downstream scripts read different ones | Should be identical in practice; nothing asserts it | SUSPECTED |

---

## 3. Detailed findings

### F-01 — CRITICAL — The reported baseline was produced by a code state that no longer exists

**Evidence.** Every record backing the headline is pre-determinism. From `outputs/metadata/runs.jsonl`:

```
(no stamp)            cnn_paper_logodds      macro=0.6446  det=None
(no stamp)            cnn_paper_s43          macro=0.6355  det=None
(no stamp)            cnn_paper_s44          macro=0.6396  det=None
```

Deterministic re-runs of the *same seeds with the current code*:

```
2026-08-05T03:55:03   det_verify_a           macro=0.6298  seed=42  det=True
2026-08-05T04:14:21   det_verify_b           macro=0.6298  seed=42  det=True
2026-08-10T04:36:24   c4_log1p_s42           macro=0.6298  seed=42  det=True
2026-08-10T05:11:18   c4_log1p_s43           macro=0.6269  seed=43  det=True
2026-08-10T05:33:49   c4_log1p_s44           macro=0.6330  seed=44  det=True
```

`scripts/determinism.py:52-56` states the rule the project then does not follow in its own reporting:

> "Determinism does NOT make old and new runs comparable. … Runs before and after this flag are
> different populations; do not pool them."

Yet `README.md:184` and `scripts/fusion_kg.py:6,89` quote `0.6399 [0.6353, 0.6446]` as *the* CNN
baseline, and `outputs/metadata/operational_best.json` computes the flagship `+0.0724` against
per-seed values `[0.6446, 0.6355, 0.6396]` — all three pre-flag. 71 of the 239 records in
`runs.jsonl` carry no timestamp at all, including the reference run.

**Mechanism.** Pinning thread counts changes floating-point reduction order, which moves the fixed
point. The pre-flag population has SD 0.0222 (the project's own measurement); the current code is
byte-deterministic at 0.6298. The two are not the same estimand.

**Impact.** The single most-quoted number in the project, the anchor of every reported improvement,
and the value `verify_draft.py` treats as ground truth, cannot be produced by running the repository.
The 3-seed deterministic baseline is **0.6299**, i.e. −0.0100 from the quoted 0.6399. Directions of
every comparison survive (the KG fusion still improves; the AE still loses macro and wins Bot); the
magnitudes are all re-based.

**Fix.** Re-run `cnn_paper.py` at seeds 42/43/44 with determinism on, re-derive every fusion channel
from those predictions, and re-state the baseline as 0.6299. Then mark the pre-flag runs in
`runs.jsonl` as a closed, non-citable population (`det_deterministic: false`) rather than `None`.

**Effort.** ~3 CNN trainings plus re-scoring of the post-hoc channels (novelty, KG fusion,
significance, operational) — hours of compute, no new code.
**Risk of fixing.** Low technically, high editorially: it changes every number in the draft. The KG
gain may grow or shrink; `fusion_kg.py` hard-codes `0.6399` in a print statement and must move with it.

---

### F-02 — HIGH — No grouped split: sessions, hosts and 5-tuples cross the train/test boundary

**Evidence.** `preprocess_paper.py:88-96` splits on row indices with `train_test_split(...,
stratify=y[known_pool])`. No group key is used. Measured on the artefacts on disk:

```
TEST flows whose Flow ID also appears in TRAIN: 62,923/114,658 = 54.88%
    DoS GoldenEye     100.00%     Web Attack Brute Force   100.00%
    DoS Hulk          100.00%     Web Attack XSS           100.00%
    DoS Slowhttptest  100.00%     Web Attack Sql Injection 100.00%
    DoS slowloris     100.00%     DDoS                      90.24%
    SSH-Patator        81.66%     FTP-Patator               78.69%
    BENIGN             41.33%     PortScan                   0.52%     Bot  0.00%
TEST flows whose Source IP appears in TRAIN: 98.92%  (3,166 of 3,657 distinct source IPs shared)
```

**Mechanism.** CICFlowMeter's `Flow ID` is `SrcIP-DstIP-SrcPort-DstPort-Protocol`. A 100 % figure
means every test flow of that family recurs as an identical 5-tuple somewhere in train — the same
scripted attack session, re-split at the flow level. For the Web Attack families (which are
*zero-day*, never trained as a class) this happens because the attacker–victim 5-tuple is reused by
flows that *are* in training under a different label.

**Impact.** Two distinct consequences, and they should not be conflated.

* For the **known classes**, the model is partly being asked to recognise sessions it has already
  seen. This is the second mechanism (with F-10) behind the 0.99+ binary figures.
* For the **zero-day web families**, the class label is genuinely unseen, but the host pair, the
  destination port and the session are not. This is a concrete mechanism for the "absorption into a
  known attack class" the project already documents: the CNN assigns ~90 % of Web BF/XSS flows to
  `DoS slowloris`, and every one of those families is 100 % on port 80.

```
Web Attack Brute Force  top dst ports: 80 (100.0%)
Web Attack XSS          top dst ports: 80 (100.0%)
DoS Hulk                top dst ports: 80 (100.0%)
Bot                     top dst ports: 8080 (64.2%)
BENIGN                  top dst ports: 53 (42.3%), 443 (22.5%), 80 (10.3%)
```

**Fix.** Add a grouped split option keyed on `Flow ID` (or on `(Source IP, Destination IP)`) using
`sklearn.model_selection.GroupShuffleSplit`, and report the headline under both. Expect the
known-class numbers to fall materially and the web-attack zero-day numbers to fall somewhat.
**Effort.** Small in code (`preprocess_paper.py`), large in consequence: a full re-run.
**Risk of fixing.** Stratification will fight the grouping — some families are one or two groups, so
a grouped split may make them unsplittable. Report that rather than forcing it.

---

### F-03 — HIGH — Temporal leakage

**Evidence.** From the corrected timestamps the project itself persists:

```
train: 2017-07-03T08:55:58 .. 2017-07-07T17:02:00   n=883,796
val:   2017-07-03T08:56:58 .. 2017-07-07T17:02:00   n=110,475
test:  2017-07-03T08:56:38 .. 2017-07-07T17:02:00   n=114,658
fraction of TEST flows inside the TRAIN time range: 100.00%
```

**Mechanism.** `preprocess_paper.py` re-pools all five capture days and splits at random.

**Impact.** Nothing in the reported results speaks to detecting traffic that arrives *after* the
training window — which is the deployment question. The project is aware: a temporal protocol exists
(`preprocess.py`, Mon–Wed / Thu–Fri) and is documented as "superseded … secondary hard-mode". It is
nonetheless the only protocol that answers the question, and no current result uses it. Note the
interaction with the KG: `kg.py` streams the test set "in chronological order so patterns genuinely
*emerge* over time", but that stream is interleaved in real time with the training data, so
"emergence" is measured against memory built from the same minutes.

**Fix.** Report the headline under the temporal protocol alongside the paper-aligned one, and label
the latter as an i.i.d. benchmark rather than a deployment estimate.
**Effort.** The code exists; it is a re-run plus a table.
**Risk.** The temporal numbers are known to be much worse (the 0.4529-vs-0.6689 result in STATUS).
That is the honest result, not a problem.

---

### F-04 — HIGH — The test set is benign-under-sampled 4.11×, so every PR-AUC is measured at an inflated base rate

**Evidence.** `preprocess_paper.py:82-84` draws the benign keep-set *before* the split:

```python
n_benign_keep = min(int(round(P["benign_ratio"] * n_known_atk)), int(is_benign.sum()))
benign_keep = np.random.RandomState(SEED).choice(benign_idx, size=n_benign_keep, replace=False)
```

Measured: the pooled cleaned dataset has 2,271,320 benign flows (80.32 % of 2,827,876); 552,373
survive (441,898 + 55,238 + 55,237). **Under-sample factor 4.11×.** Test benign is 55,237 against a
capture-faithful 227,132.

Re-evaluating the seed-42 CNN's stored predictions with the positive class thinned by 4.11× (the dual
of adding back the removed benign flows; 200 bootstrap draws):

| family | as reported | at capture prevalence |
|---|---:|---:|
| Bot | 0.0591 | **0.0152** |
| Web Attack Brute Force | 0.9194 | 0.8836 |
| Web Attack XSS | 0.9554 | 0.9056 |
| **macro** | **0.6446** | **0.6015** |

**Mechanism.** PR-AUC, precision and lift are prevalence-dependent; ROC, FPR and recall are not.
Removing three quarters of the benign class raises every family's chance PR-AUC ~4× and carries the
achieved PR-AUC up with it, most sharply where the ranking is weakest.

**Impact.** Absolute PR-AUC and lift figures throughout the docs are ~4× optimistic relative to the
capture, and far more relative to a real network. Three consequences worth separating:

* The **recall@FPR** figures (48.3 %, 57.6 %) are *not* affected — both are within-class rates.
* The **alert-volume** framing is: "10 % FPR is ~5,500 false alerts on this test set"
  (`operational_best.json`) understates the capture-faithful figure by 4.11× and a real network by
  orders of magnitude.
* Bot's inflation cuts *against* the project's own interest: the absolute 0.0152 at capture
  prevalence makes the unreachability claim stronger, not weaker. Say so rather than leaving it.

**Fix.** Either keep the 1:1 split for training and evaluate on a prevalence-faithful test set, or
report both columns. The former is one line: draw `benign_keep` for train/val only and let the test
split take all remaining benign.
**Effort.** Small code change, full re-evaluation (no retraining needed for the scored channels).
**Risk.** Low. It makes the numbers worse and the paper better.

---

### F-05 — HIGH — The flagship operational number is transductive

**Evidence.** `kg.py:243-247` is explicit:

> `s_kg` above is TRANSDUCTIVE: burstiness is computed over the WHOLE test stream, so a flow in
> window 3 is scored using information from window 17. … it IS an offline/batch setting that a live
> IDS could not reproduce.

`outputs/metadata/operational_best.json` then reports both, and the one carried into `docs/STATUS.md`
as "**CURRENT BEST**" and "**Operationally — the number to quote**" is the `s_kg` row:

| config | macro | recall of unknown @1 % FPR | @0.1 % |
|---|---:|---:|---:|
| CNN alone | 0.6399 | 48.3 % | 47.3 % |
| CNN + KG k=800 (**s_kg**, transductive) | **0.7123** | **57.6 %** | 45.8 % |
| CNN + KG k=800 (causal, online) | 0.7032 | 54.6 % | 42.8 % |

`fusion_kg.py:56` — the canonical fusion script — correctly uses the **causal** files. The k-sweep
that produced the "current best" does not.

**Mechanism.** Burstiness over the full stream is a batch statistic. Online, a cluster's peak-window
share is only known after the peak has happened.

**Impact.** The sentence a reviewer will quote ("57.6 % of unknown flows at a 1 % false-alarm rate")
describes a system that cannot exist. The honest online figure is 54.6 %. Note also that the causal
variant *leads* at k=200 and the transductive one at k=800 — the ranking flips with the
hyperparameter, which `operational_best.json` flags in its caveats but STATUS does not.

**Fix.** Make the causal variant the reported default everywhere, and present the transductive number
only as the batch/offline upper bound with the gap named as the cost of real-time operation — which
is exactly how `kg.py` frames it.
**Effort.** Trivial (re-point `operational_best.py`'s config list and re-run; no training).
**Risk.** None technically. It lowers the headline by ~0.009 macro and 3 recall points.

---

### F-06 — HIGH — The held-out k selection has no code behind it

**Evidence.** `ksweep_fusion.py:22-27` states its own defect:

> ⚠️ AND THIS IS A HYPERPARAMETER SEARCH ON THE TEST SET. Four k values are being compared on the
> same test split that reports the headline.

The stated remedy is `outputs/metadata/ksweep_heldout.json` (selected on half A, reported on half B,
`rng: 9001`, `+0.0305`, `2.86σ`). Searching the repository for anything that writes it:

```
$ grep -rn "heldout|held_out|half_a|9001" scripts/*.py scripts/*.sh
scripts/fusion_weight.py:60:   SPLIT_RNG = 9001          <- writes fusion_weight.json, different keys
scripts/operational_best.py:28 <- quotes it
scripts/verify_draft.py:291    <- verifies the draft against it
```

`git log` shows the JSON was committed once (`9acd134`, alongside `ksweep_fusion.py`), and
`git log --all --diff-filter=D -- 'scripts/*.py'` shows **no script has ever been deleted**. The file
is a hand-produced artefact.

**Independent re-derivation.** I re-implemented the protocol (stratified 50/50 split of test,
`random_state=9001`, 50/50 rank fusion, seeds 42/43/44):

| | half A (k800 / k200) | half B (k800 / k200) | held-out Δ | σ | seeds better |
|---|---|---|---:|---:|---:|
| recorded | 0.7165 / 0.6805 | 0.7091 / 0.6786 | +0.0305 | 2.86 | 3/3 |
| my re-derivation (`s_kg`) | 0.7199 / 0.6889 | 0.7063 / 0.6717 | **+0.0346** | **2.38** | 3/3 |
| my re-derivation (`causal`) | 0.7076 / 0.7003 | 0.7002 / 0.6875 | +0.0127 | 2.11 | 3/3 |

**Impact.** The *conclusion* survives — k=800 beats k=200 on held-out data, 3/3 seeds, in both
variants. The *cited figures* do not regenerate: my σ is 2.38, not 2.86, and the causal variant's
held-out gain is +0.0127, less than half the quoted value. `verify_draft.py` "verifies" the draft
against this file, so the project's own verification treats an unreproducible artefact as ground
truth. By the repository's own standard (CLAUDE.md: "a number quoted in a doc with no logged run
behind it is a defect") this is a defect, and it sits on the flagship result.

**Fix.** Write `scripts/ksweep_heldout.py` implementing the protocol, run it, and replace the JSON
with its output — quoting whatever it produces.
**Effort.** ~60 lines; the split-half machinery already exists in `fusion_weight.py:100-140`.
**Risk.** The regenerated σ will probably be lower than 2.86. Report it.

---

### F-07 — HIGH — Decision thresholds are fitted on the test set

**Evidence.** `metrics.py:79`, the function every channel is scored through:

```python
thr = float(np.quantile(scores[is_benign], 1.0 - fpr)) if is_benign.any() else 0.5
```

`is_benign` is derived from `y_mc`, the **test** labels. The same pattern recurs at
`operational.py:390` (`np.quantile(p_cal[is_benign], 0.99)`), `operational_best.py:110`,
`fusion_weight.py:107`, `metric_divergence.py:109`, `aug_analyse.py:186`. This is a systematic
convention, not a slip.

**Mechanism.** The achieved FPR is 1.0000 % by construction on the reporting split — the diagnostic
`achieved_fpr` in `metrics.py:89` reads exactly 0.0100 for every channel I re-scored. An operating
point chosen on the data it is evaluated on is optimistically biased.

**Impact.** Bounded but real. With 55,237 benign test flows the quantile is well estimated, so the
bias on the FPR itself is small; the bias on the *paired* recall, F1 and precision at that point is
the part that matters, and it is unquantified. The headline PR-AUC is threshold-free and unaffected —
which is why this is HIGH and not CRITICAL. Credit where due: the calibrators in `operational.py` are
correctly fitted on validation, with a zero-day leak assertion at line 235. Only the threshold is not.

**Fix.** Derive the threshold from the **validation** benign scores and apply it to test. Two lines in
`metrics.evaluate` (accept an optional `thr`) plus a caller change; then report the *achieved* test
FPR as a result rather than fixing it at 1 %.
**Effort.** Small. **Risk.** Low; the achieved FPR will no longer be exactly 1 %, which is the point.

---

### F-08 — HIGH — `BeaconLike` encodes this capture's C2 port, and was selected against held-out zero-day labels

**Evidence.** `behavior.py:144-157`:

```python
# Fixed domain knowledge, NOT data-fitted — standard well-known service ports.
# … Set membership against a small, externally-defined port list validated far
# better (ROC 0.887, PR-AUC 0.135 on Bot-vs-benign alone — see
# scripts/skyline_oracle.py, 2026-07-27).
WELL_KNOWN_PORTS = frozenset({20,21,22,23,25,53,67,68,80,110,123,143,161,389,
                              443,445,465,587,993,995,3306,3389,5060,8443})
```

and `behavior.py:283`: `beacon_like = (~np.isin(dst_port, _WELL_KNOWN_PORTS_ARR))`.

Reproduced on the test artefacts:

```
Bot top destination ports: 8080 (64.2%)      8080 in WELL_KNOWN_PORTS? False
BeaconLike fire rate:  Bot 0.9995   BENIGN 0.2265
BeaconLike vs benign:  Bot ROC=0.8865 PR-AUC=0.1351   (matches the docstring's 0.887 / 0.135)
                       Web BF ROC=0.3867   XSS ROC=0.3867   (anti-correlated)
```

**Mechanism.** The predicate's *form* is external domain knowledge. Its *selection* is not: two
candidate encodings (a magnitude ramp and set membership) were compared by their ROC **against Bot**,
a class that exists only in the test split, and the winner is the one that happens to exclude 8080
while including 8443. In this capture the botnet C2 listens on 8080; nothing about "well-known ports"
as a concept predicts that.

**Impact.** Any claim that a symbolic predicate "transfers to zero-day attacks" is, for this
predicate, a claim about a design choice made with knowledge of the zero-day class. The blast radius
is limited because the project's conclusion is that the symbolic pillar *does not* beat the neural
baseline — a predicate selected with held-out labels still failing is a stronger negative, not a
weaker one. But the provenance must be stated wherever `BeaconLike` is described as domain knowledge;
`behavior.py:144` currently asserts the opposite ("NOT data-fitted").

**Fix.** Either (a) re-select the predicate using only train-visible classes and re-run the LTN/KG
arms, or (b) keep it and relabel it honestly as oracle-informed, excluded from any transfer claim.
Given the negative result, (b) is cheap and sufficient.
**Effort.** (a) days; (b) a docstring and a caveat line.
**Risk.** (a) may weaken the symbolic arms further, which is itself a finding.

---

### F-09 — HIGH — No tests

**Evidence.** `find . -name "test_*.py" -o -name "*_test.py" -o -name conftest.py -o -name pytest.ini
-o -name pyproject.toml` → nothing. 15 inline `assert` statements across 18,010 lines; the meaningful
ones are `preprocess_paper.py:150-151` (zero-day not in train/val), `cnn_paper.py:92` (finite after
transform), `operational.py:235` (zero-day not in val), and `timeline.selftest()`.

**Mechanism.** `lint_conventions.py` (which passes, 10/10) lints *conventions* — doc/table drift,
smoke-namespace hygiene, runs.jsonl integrity. It asserts nothing about the data path.
`verify_draft.py` (172 verified / 0 mismatched) checks the *draft against JSON records*, i.e.
internal consistency of reporting, not correctness of computation.

**Impact.** None of F-02, F-03, F-04 or F-07 would be caught by anything currently in the repository.
The asserts that exist are the ones someone thought of after being burned; the leakage boundary as a
whole is untested.

**Fix.** A `tests/` directory with, at minimum: `test_no_zero_day_in_train_val`,
`test_scaler_fitted_on_train_only`, `test_cross_split_exact_duplicates_below_threshold` (asserting the
*measured* value so a regression is visible), `test_flow_id_group_overlap_recorded`,
`test_feature_count_is_68`, `test_behaviour_indices_match_check_py`,
`test_threshold_not_derived_from_test`.
**Effort.** A day. **Risk.** None; several will fail on first run, which is the value.

---

### F-10 — MEDIUM — 17 % exact train/test duplicate overlap (measured and disclosed; still headlined)

**Evidence.** My measurement on the artefacts:

```
[within] train: 883,796 rows, 119,288 duplicates (13.50%), max multiplicity 7,521
[cross]  TEST rows whose 68-feature vector also appears in TRAIN: 19,513/114,658 = 17.02%
         PortScan 58.33% · SSH-Patator 48.56% · FTP-Patator 29.63% · DoS Hulk 25.28% · BENIGN 6.91%
         Bot 0.00% · Heartbleed 0.00% · Infiltration 0.00% · all three Web Attack families 0.00%
         of the 19,513, 19,493 carry the same label in train and 20 do not
```

This reproduces `comparability.py`'s figure exactly ("17.0 % … PortScan 58.3 %, SSH-Patator 48.6 %"),
and confirms its central asymmetry claim: the six zero-day families measure **0.0 %** overlap, so the
headline macro is untouched.

**Credit where due.** This is the documented CIC-IDS2017 defect; the project found it, measured it,
built a deduplicated reporting variant, and quantified the cost (`KNOWN_ISSUES.md:267`: CNN binary
0.9928 → 0.9884, XGBoost 0.9936 → 0.9901). That is better than most published work on this dataset.

**Impact.** Residual, and editorial rather than computational: `README.md:184` and
`docs/target/paper_supplementary.md:108` lead the field-gap argument with the **non-dedup** 0.9928.
The argument survives dedup (0.9884 vs 0.6446 is still a 0.344 gap) so nothing changes materially —
but the number a reviewer will challenge is the one on the page.

**Fix.** Lead with the deduplicated figure and footnote the raw one.
**Effort.** Minutes. **Risk.** None.

---

### F-11 — MEDIUM — No multiple-comparison correction across 13 significance tests

**Evidence.** `significance.py:196-222` defines 13 entries in `TESTS`, each judged by
`significant = lo > 0 or hi < 0` on a 95 % bootstrap CI. No Bonferroni/Holm/FDR adjustment anywhere.

**Impact.** Under the global null, the probability of at least one "significant" result across 13
independent tests is ≈0.49. Several comparisons are pre-registered directional predictions (the
double dissociation), which mitigates this; several are explicitly exploratory ("NEW 2026-08-03 —
does a supervised (A) method match the AE on Bot?"), which does not. The C2 result closed at p=0.001
on this machinery and was later retracted on *other* grounds (0.9 SD of the noise floor) — the
retraction happened to be right for a reason that also covers this one.

**Fix.** Holm–Bonferroni within each pre-registered family; report exploratory comparisons as
exploratory. Add the adjusted p to `significance.json`.
**Effort.** ~15 lines. **Risk.** Some current "SIGNIFICANT" verdicts will become n.s.

---

### F-12 — MEDIUM — Baselines are not tuning-matched

**Evidence.** `baselines.py:71-88`: `XGBClassifier(n_estimators=300, max_depth=8, learning_rate=0.1)`,
`RandomForestClassifier(n_estimators=200, max_depth=20)`, `IsolationForest(n_estimators=200)`. No
validation set is loaded (`load("val")` is never called), no early stopping, no search. By contrast
`cnn_paper.py:184-192` trains 50 epochs with `EarlyStopping(patience=8, restore_best_weights=True)`,
`ReduceLROnPlateau` and `ModelCheckpoint`, all monitored on val.

**Context that cuts both ways.** A depth-12 decision tree on all 68 features reaches **PR-AUC 0.9978 /
F1 0.9982** on the known-class task — the supervised problem is trivially solved by a shallow tree, so
the CNN's architectural advantage is not where the action is. On the *zero-day* metric the baselines
are not obviously disadvantaged either (XGBoost 0.6372 vs CNN 0.6399, n.s. at p=0.80 by the project's
own test).

**Fix.** Give the baselines the same validation budget (early stopping on the val split for XGBoost, a
small grid for RF) and re-report.
**Effort.** Hours. **Risk.** Low; the most likely outcome is that XGBoost ties or beats the CNN more
clearly, which is already the project's stated position.

---

### F-13 / F-14 — MEDIUM — The orphan notebook is a second, contradictory pipeline

**Evidence.** `Capstone_final (4) (1).ipynb`, 1.6 MB, untracked, referenced nowhere in the repository.
36 cells; **all 22 code cells have `execution_count: null`** while carrying saved outputs — the
outputs cannot be attributed to any execution of the code as shown.

Its protocol contradicts `config.yaml` on the central design decision:

| | `config.yaml` (scripts) | notebook |
|---|---|---|
| features | 68 | **70** (`input (InputLayer) │ (None, 70, 1)`) |
| zero-day set | Bot, Heartbleed, Infiltration, Web ×3 | Bot, Heartbleed, **PortScan**, Web ×3 |
| Infiltration | zero-day (test only, n=36) | **known class, trained on n=29, scored on n=3** |
| benign | under-sampled 1:1 | full (1,817,056 in train) |
| headline | macro zero-day PR-AUC | **accuracy** ("Metric 1 — Multi-class known: 0.9928") |
| runtime | TF 2.15.1, CPU, local | TF 2.20.0, Colab, Google Drive paths |

Consequences visible in its own output: PortScan is 158,804 of the 162,951 "unknown" flows (97.5 %),
so its "Binary zero-day only: 0.5805" is a PortScan detector measurement; `Infiltration 0.0000
precision/recall/f1 support 3` is printed to 4 dp; and CLAUDE.md's explicit warning ("⚠️ PortScan and
DDoS are KNOWN, trained-on classes … any claim of the form 'the behaviours strongly cover
PortScan/DDoS, so the symbolic approach works' … does not transfer") is exactly what this notebook's
protocol would license.

**F-14 specifically** — cell 35, the "adaptability demo":

```python
heartbleed_rule = (bwd_mean > 2500) & (bwd_tot > 500000)
# Threshold set from benign p99 of Bwd Packet Length Mean (~1506), with margin
# — NOT tuned on Heartbleed labels.
```
→ `Heartbleed recall BEFORE rule : 0.0000 / AFTER rule : 1.0000`, `System FPR ... 0.1022`.

The first threshold has a stated derivation; the second (`bwd_tot > 500000`) has none. The result
rests on **11 flows** and is reported at a 10.2 % system false-positive rate. Whatever its provenance,
"0 → 100 % recall" on n=11 is not a measurement.

**Impact.** Bounded: no notebook number appears in any doc (I searched for 0.6161 / 0.7949 / 0.6622 /
0.6931 — none occur; the 0.9928 that does appear in the docs is `comparability.py`'s CNN binary
PR-AUC, a coincidence). The risk is external: this file sits in the project root, looks like the
deliverable, and a reader who runs it gets a protocol that contradicts the paper.

**Fix.** Decide what it is. If it is the capstone submission, track it, re-execute it top to bottom so
`execution_count` is meaningful, and add a header stating which protocol it implements and how that
differs from `config.yaml`. If it is superseded, move it to `docs/archive/` with a banner.
**Effort.** Small either way. **Risk.** Re-executing may not reproduce the saved outputs, which is
itself the thing to find out.

---

### F-15 to F-25 — condensed

Each is bounded and the fix follows from the location.

* **F-15** `preprocess.py:87-91` computes `const_cols` from the temporal train half only. Those 10
  columns are all-zero across the whole capture (`Bwd PSH Flags`, `Fwd/Bwd URG Flags`, `CWE Flag
  Count`, the six `*_Avg_Bulk_*`), so the practical effect is nil — but the decision is made with rows
  that later enter the paper test split. Move the computation inside the paper split, or assert the
  columns are constant on train alone.
* **F-16** No adversarial evaluation. `ood_scores.py:23` uses ODIN's input perturbation, which is an
  OOD-scoring trick, not an evasion threat model. A flow-feature IDS is trivially evadable by padding
  and rate shaping; if no experiment is run, the limitations section should say so explicitly.
* **F-17** Single reporting split, 239 logged runs over ~5 months. The split-half protocol in
  `fusion_weight.py` is the right instrument and covers two experiments. A frozen holdout carved out
  once at the start is the structural fix; it is too late here, so state the exposure instead.
* **F-18** "70 features" in `docs/architecture.md:34,83`, `docs/dataset.md:86`, `docs/pipeline.md:41`,
  `docs/target/target_architecture.md:85`. Verified count is 68 (`check.py`; `X_train.npy` is
  `(883796, 68)`). ~~CLAUDE.md says frozen docs are "banner-marked"; `architecture.md` is not.~~ *Wrong — corrected
  2026-09-16: `architecture.md:3-8` and `dataset.md:3-12` both carry a frozen banner that names 68. Only
  `pipeline.md` (banner silent on the count) and `target_architecture.md` (not a frozen doc) needed fixing.*
* **F-19** `determinism.py:69` sets `PYTHONHASHSEED` after interpreter start, where it has no effect.
  Either set it in the launcher (`run_long.sh`) and re-exec, or drop it from the documented list.
* **F-20** `y_prob_cnn_paper_s43_test.npy` gives macro 0.6355 / Bot 0.0245; the `_logodds_` twin gives
  0.6353 / 0.0241 (Spearman 0.999996; largest tie block 1.57 % → 0.78 %). README quotes the log-odds
  values. Harmless, but record which array a 4-dp number came from.
* **F-21** `dashboard_server.py:491-492` interpolates `e.path` into HTML unescaped. 127.0.0.1-bound
  and fed only local data; escape it anyway. Otherwise the server is sound — `basename()`-only path
  handling with an extension allowlist, no write endpoints.
* **F-22** `latency.py:228` `exec(compile(ast.Module(...)))` to extract `KnowledgeGraph` from `kg.py`
  source. Move the class into an importable module.
* **F-23** `outputs/.check.pid` is tracked despite `outputs/*.pid`. `git rm --cached`.
* **F-24** `tensorflow==2.15.1` is end-of-life. All direct deps pinned (good), no lockfile, and the
  venv has packages absent from `requirements.txt`. Add `pip freeze > requirements.lock.txt`.
* **F-25** `cnn_paper.py` writes both `{TAG}.keras` (weights restored by EarlyStopping) and
  `{TAG}_best.keras` (ModelCheckpoint); `novelty.py:52` reads `_best`, `operational.py:218` reads the
  plain one. They should be identical; nothing checks. SUSPECTED — I did not load both and compare.

---

## 4. What is right

Stated briefly, because the prompt asks for it and because it changes how the findings above should
be read.

* **No oversampling anywhere.** `grep -rni "smote|adasyn|imblearn|RandomOverSampler"` → nothing. The
  single most common fatal error in ML-IDS work is absent.
* **Every scaler is fitted on train only** — verified at all 12 `StandardScaler().fit(...)` call
  sites. No transform is fitted before a split or on test.
* **Zero-day never enters train or val**, and it is asserted, not assumed
  (`preprocess_paper.py:148-151`, `operational.py:235`).
* **The headline metric is the right one.** `metrics.py` refuses the size-weighted blend as a
  headline, excludes families with n < 100 from the macro, scores each family against benign
  separately so `chance_pr_auc` is explicit, uses PR-AUC not ROC-AUC, and ships a score-saturation
  diagnostic (`largest_tie_frac`) that catches a real failure mode.
* **The documented CIC-IDS2017 defects are handled.** Duplicates measured and a dedup variant reported
  (`comparability.py`); Engelen et al.'s corrected re-release actually run (`preprocess_improved.py`,
  `improved_analyse.py`), with the finding that the web families collapse from 0.8861 to 0.0072 PR-AUC
  once `X - Attempted` flows are excluded — a result most projects would have quietly dropped.
* **The noise floor was measured before deltas were published** (SD 0.0222, n=6) and used to retract a
  result that had already passed a p=0.001 bootstrap. `determinism.py` then attacked it at source, and
  `det_verify_a` / `det_verify_b` are byte-identical.
* **The KG ships its own confound control** (`kg.py:307-345`): "is this just detecting later in the
  week?", with the within-window measure reported alongside the global one, and an explicit statement
  that lateness alone beats the previous best Bot channel.
* **Retraction discipline.** Reversals are struck through in place with the reasoning kept. The
  research record (`runs.jsonl`, 239 rows, 0 exact duplicate records) is version-controlled.
* **Both self-checks pass:** `lint_conventions.py` 10/10, `verify_draft.py` 172 verified / 0
  mismatched / 0 stale / 4 explicitly unbacked.
* **No secrets.** Full-history scan of all 259 commits for AWS keys, GitHub tokens, private keys,
  Slack/OpenAI-shaped keys, bearer headers, and `.env`/`.pem`/`.key`/credential files → **zero hits**.
  No pcap, no capture file, no internal IP or hostname in any tracked text file. `.gitignore`
  correctly excludes `data/`, `models/`, embeddings and predictions while deliberately tracking the
  small protocol-definition artefacts.

---

## 5. Reported-claims verification

Claims I re-derived myself from the artefacts on disk, independently of the project's own scripts.

| # | Claim (source) | Verdict | Evidence |
|---|---|---|---|
| 1 | `cnn_paper` macro zero-day PR-AUC = **0.6446** (README, paper, `comparability.json`) | **Reproduced** | Re-scored `y_prob_cnn_paper_test.npy` through `metrics.evaluate` → 0.6446 exactly |
| 2 | CNN 3-seed baseline **0.6399 [0.6353, 0.6446]** (`README.md:184`, `fusion_kg.py:6`) | **Reproduced as recorded; NOT reproducible by re-running** | Stored seeds give 0.6446 / 0.6355 / 0.6396 → 0.6399. Deterministic re-runs of the same code give 0.6298 / 0.6269 / 0.6330 → **0.6299** (F-01) |
| 3 | Per-family CNN: Bot 0.0446, Web BF 0.9226, XSS 0.9524 (`README.md:184`) | **Reproduced** | Log-odds arrays: Bot 0.0591 / 0.0241 / 0.0507, WebBF 0.9194 / 0.9288 / 0.9196, XSS 0.9554 / 0.9532 / 0.9485 → means 0.0446 / 0.9226 / 0.9524 |
| 4 | Autoencoder macro **0.0970**, Bot **0.1314** (`README.md:190`) | **Reproduced** | `y_prob_autoencoder_paper_test.npy` → macro 0.1000, Bot 0.1217; s43 → 0.1014 / 0.1647. 3-seed means consistent with the quoted CI |
| 5 | "**17.0 %** of test rows have an exact twin in train (PortScan 58.3 %, SSH-Patator 48.6 %)" (`comparability.py:24-26`) | **Reproduced** | Independent row hashing: 17.02 %; PortScan 58.33 %; SSH-Patator 48.56 % |
| 6 | "all six zero-day families measure 0.0 % train overlap" (STATUS, C1) | **Reproduced** | Bot, Heartbleed, Infiltration, Web BF, XSS, SQLi all 0.00 % |
| 7 | Split sizes 883,796 / 110,475 / 114,658 (CLAUDE.md, `split_report.txt`) | **Reproduced** | `X_train/val/test.npy` shapes match exactly; 68 features |
| 8 | Zero-day counts Bot 1,956 · Web BF 1,507 · XSS 652 · Infiltration 36 · SQLi 21 · Heartbleed 11 | **Reproduced** | Direct count of `y_test_mc.npy` |
| 9 | "**100 %** of Bot flows are classified BENIGN, mean p(BENIGN)=0.9984" (`README.md:210`) | **Reproduced** | `bot_failure_analysis.json`: `frac_argmax_BENIGN` = 1.0 at seeds 42/43/44; `mean_p_BENIGN` 0.99838 / 0.99988 |
| 10 | "cross-seed Spearman ρ = **−0.090** for Bot, 0.68–0.83 elsewhere; AE 0.827" (`README.md:215-217`) | **Reproduced** | `bot_failure_analysis.json`: Bot −0.0898; WebBF 0.678; XSS 0.830; AE Bot 0.827; RF Bot 0.068 |
| 11 | "Bot's discriminative features have **0/8 overlap** with the known-class task" | **Reproduced** | `bot_failure_analysis.json`: `bot_overlap_n: 0`; Web BF overlap 1 |
| 12 | "Bot oracle PR-AUC **0.9988**" (`README.md:221`) | **Reproduced** | `bot_failure_analysis.json`: 0.99884 |
| 13 | `BeaconLike` "ROC 0.887, PR-AUC 0.135 on Bot-vs-benign" (`behavior.py:152`) | **Reproduced** | Recomputed: ROC 0.8865, PR-AUC 0.1351 |
| 14 | k=800 held-out: **+0.0305, 2.86σ, 3/3** (`ksweep_heldout.json`, STATUS) | **Partially reproduced — conclusion yes, figures no** | Independent split-half: +0.0346 at **2.38σ**, 3/3 (s_kg); +0.0127 at 2.11σ (causal). No script regenerates the recorded values (F-06) |
| 15 | "CNN+KG k=800 macro **0.7123**" (STATUS, "CURRENT BEST") | **Reproduced, but it is the transductive variant** | `operational_best.json`: s_kg 0.7123, causal 0.7032 (F-05) |
| 16 | "at 1 % FPR it flags **57.6 %** of unknown flows, CNN 48.3 %" (STATUS) | **Reproduced as recorded; mislabelled as operational** | `operational_best.json` s_kg 0.5761 vs causal 0.5459 (F-05) |
| 17 | Is `Destination Port` a label proxy? (audit hypothesis, §1.3) | **Refuted** | Port alone (depth-8 tree): macro zero-day 0.1437 vs the CNN's 0.6446; not in the top 12 single features for the known-class task. Strongest single feature is `Average Packet Size` (0.9509) |
| 18 | "68 features, not 70" (CLAUDE.md) vs "70 numeric features" (4 docs) | **Docs contradicted** | Verified 68 (F-18) |
| 19 | Benign under-sampled to 1:1, "paper-faithful" (`config.yaml:17`) | **Reproduced, with an unstated consequence** | 2,271,320 → 552,373 = 4.11×; macro at capture prevalence 0.6015, not 0.6446 (F-04) |
| 20 | "no zero-day leakage into train/val" (`split_report.txt`) | **Reproduced** | Intersection of train/val label sets with the zero-day list is empty |
| 21 | `lint_conventions.py` passes / `verify_draft.py` 172-0 | **Reproduced** | Both re-run during this audit: ALL CHECKS PASS; 172 verified · 14 not quoted · 4 unbacked · 0 mismatched · 0 stale |
| 22 | Notebook: "Multi-class known 0.9928", "Binary zero-day only 0.5805" | **Not reproducible, and not comparable** | All `execution_count` are `null`; protocol differs from `config.yaml` on features, zero-day set and balancing (F-13) |

---

## 6. Unverified — requires access, time or compute

1. **End-to-end re-run of the pipeline.** `run_all.py` reports 19/19 stages with all declared
   artefacts present, but CLAUDE.md states the sequence "has been **checked** end to end and **never
   executed** end to end in one pass". I did not execute it. *Needs:* ~10–20 h CPU.
2. **Re-training to confirm F-01's magnitude at more than 3 seeds.** I used the project's own logged
   deterministic runs (`det_verify_a/b`, `c4_log1p_s42/43/44`). *Needs:* ~6 × 40 min CPU.
3. **The exact `ksweep_heldout.json` protocol.** My re-derivation is close but not identical; the
   difference could be the stratification key, the KG variant, or the rank normalisation. *Needs:* the
   original session transcript, or the replacement script (F-06).
4. **`comparability.py`, `robustness.py`, `field_gap.py`, `ablation.py`, `latency.py`, `explain.py`,
   `ltn_paper.py`, `ltn.py`, `fitted_fusion.py`, the Phase-6 2018 chain and the `improved_*` chain
   were read only in part** — docstrings, I/O boundaries, and the specific patterns swept for. Their
   internal numerical logic is unverified line by line. `ltn.py` (731 lines) and `operational.py`
   (529) are the largest gaps.
5. **Whether `{TAG}.keras` and `{TAG}_best.keras` are identical** (F-25). *Needs:* loading both and
   comparing weights.
6. **The base-paper comparison.** `verify_draft.py` itself flags "base paper 48.34 % / 47.85 % /
   47.24 % — `paper_metrics.json` + `basepaper.pdf` — verify by hand" as unbacked. I did not read
   `basepaper.pdf` (gitignored, 2.9 MB) and cannot confirm the transcribed figures.
7. **The 2018 replication artefacts.** `data/raw_2018/` is not present locally (6.41 GB, gitignored),
   so the Phase-6 numbers rest on committed JSON I could not regenerate.
8. **Whether the notebook's saved outputs correspond to its code.** Every `execution_count` is null;
   settling this requires re-executing it on Colab against the Drive data.

---

## 7. Coverage statement

**Files.** 271 tracked + 2 untracked in the working tree (the notebook and the audit prompt).

* **Read end to end (24 Python files, ~4,400 lines):** `paths.py`, `config.py`, `features.py`,
  `tracking.py`, `determinism.py`, `metrics.py`, `preprocess.py`, `preprocess_paper.py`,
  `cnn_paper.py`, `baselines.py`, `novelty.py`, `autoencoder_paper.py`, `kg.py`, `fusion_kg.py`,
  `ksweep_fusion.py`, `significance.py`, plus substantial reads of `behavior.py`, `fusion_weight.py`,
  `skyline_oracle.py`, `dashboard_server.py`, `comparability.py`, `operational.py`,
  `operational_best.py`, `lint_conventions.py`.
* **Read via docstring + I/O boundary + targeted pattern sweep (all remaining 53 Python files and all
  14 shell launchers):** every file was swept for the specific defect classes — transforms fitted
  outside train, test-label use, threshold-on-test, oversampling, `pickle`/`eval`/`exec`/`shell=True`,
  bare excepts, hardcoded paths, TODO/FIXME. Findings F-07, F-16, F-19 and F-22 come from this sweep.
* **Notebook:** all 36 cells and all saved outputs read (dumped to UTF-8 first, to get past the cp1252
  trap in the mojibake'd class names).
* **Docs:** `CLAUDE.md`, `README.md`, `config.yaml`, `.gitignore`, `CONTRIBUTING.md` read in full;
  `STATUS.md` (3,504 lines), `CHANGELOG.md` (2,405), `KNOWN_ISSUES.md` (1,150),
  `scripts_reference.md` (129 KB), `paper_draft.md`, `paper_body.md` and `paper_supplementary.md` read
  in part and searched exhaustively for the numeric claims in §5.
* **Metadata:** all 62 `outputs/metadata/*.json` enumerated; `ksweep_heldout.json`,
  `operational_best.json`, `bot_failure_analysis.json` and `runs.jsonl` (239 records) read in full.

**Commits.** 259/259 scanned for secrets and for sensitive or heavyweight file additions;
`git log --all --diff-filter=D` run over `scripts/*.py`. **Not done:** a commit-by-commit
reconstruction of the evaluation code's evolution hunting for metric jumps. `runs.jsonl` gives the
metric history directly and shows no unexplained jump; the one large documented shift (the 2026-07-27
`metrics.py` rewrite from the blended metric to the macro) is recorded as a schema change
(`v1-blended` → `v2-macro`, 15 and 224 rows) and is a change of estimand, not an improvement claim.

**Deliberately excluded.** `.venv/` (third-party), `basepaper.pdf` (gitignored, copyrighted),
`data/raw_csv_full/` (input CSVs — reached through the processed artefacts, not re-parsed),
`docs/archive/` (superseded by construction), `docs/target/paper_latex/main.tex` (generated from the
markdown by `md_to_latex.py` and checked by the project's own lint).

**Probes executed** (read-only, against the artefacts on disk): exact-duplicate hashing across all
three splits; Flow-ID and Source-IP group-overlap; corrected-timestamp range comparison; pooled
class-prevalence recount; per-family PR-AUC re-derivation for 8 channels; prevalence-corrected
re-evaluation (200 bootstrap draws); a single-feature leakage probe over all 68 features; a
full-feature depth-12 tree; `BeaconLike` recomputation; a split-half re-derivation of the k selection;
probability-vs-log-odds tie analysis; `lint_conventions.py`; `verify_draft.py`; `run_all.py`.

---

## 8. Prioritised remediation plan

Each batch awaits explicit approval. **Nothing below has been done.** Expected metric impact is stated
before the work, as required.

### Batch A — Critical correctness (will change the reported numbers, mostly downward)

| Step | Finding | Expected impact |
|---|---|---|
| A1 | F-01: re-run the CNN at seeds 42/43/44 with determinism on; re-derive novelty, fusion, significance and operational from those predictions; re-base every quoted delta | CNN baseline 0.6399 → **0.6299**. KG fusion gain recomputed (currently +0.0724 against the old anchor) |
| A2 | F-05: make the causal KG the reported default; demote the transductive number to a labelled offline upper bound | Best macro 0.7123 → **0.7032**; @1 % FPR 57.6 % → **54.6 %** |
| A3 | F-06: write and run `scripts/ksweep_heldout.py`; replace the hand-made JSON with its output | σ likely falls from 2.86 toward ~2.4; the conclusion (k=800 > k=200, 3/3) is expected to survive |
| A4 | F-07: derive the operating threshold from **validation** benign scores; report achieved test FPR as a measurement | Achieved FPR will no longer be exactly 1.00 %; recall@FPR figures move by an unknown, probably small amount |
| A5 | F-04: undersample benign for train/val only, give test all remaining benign; report prevalence-faithful PR-AUC alongside | Macro 0.6446 → ~**0.6015**; Bot 0.0591 → ~**0.0152** |
| A6 | F-02 + F-03: add a grouped (Flow-ID) split and a chronological split as reported variants | Known-class binary will fall materially; web-attack zero-day expected to fall; magnitude unknown — this is the experiment |

> A5 and A6 change the protocol, so per Phase 2 rule 4 each needs its justification written into the
> report together with the delta it caused. A1–A4 are corrections within the existing protocol and
> should land first, since A5 and A6 are measured against them.

### Batch B — Secrets, data exposure, security

Nothing to rotate. Remaining items are hygiene: F-21 (escape the dashboard's HTML interpolation),
F-23 (`git rm --cached outputs/.check.pid`), F-22 (replace the `exec(compile(...))` import hack).
**No secret, credential, capture file, or internal address was found in 259 commits.**

### Batch C — Training, modelling, baselines

F-12 (matched validation budget for the baselines), F-08 (re-derive or relabel `BeaconLike`), F-11
(Holm–Bonferroni within the significance families), F-16 (either run a basic evasion experiment —
padding, rate shaping, IAT jitter on the zero-day families — or state its absence as a limitation),
F-25 (verify the two saved checkpoints match, then keep one).

### Batch D — Reproducibility, environment, tests

F-09 (the `tests/` directory listed in §3, leakage-boundary assertions first), F-15 (move
constant-column selection inside the paper split), F-19 (`PYTHONHASHSEED` in the launcher, or drop
it), F-24 (lockfile; plan the TF upgrade), F-20 (record which score array each quoted number came
from), plus the first genuine end-to-end `run_all.py --run` so the claim can stop being "checked but
never executed".

### Batch E — Hygiene and structure

F-13 / F-14 (decide the notebook's status: track and re-execute, or archive with a banner), F-18 (fix
"70 features" in four docs, or banner them), F-17 (state the single-split exposure in the paper's
limitations).

---

## 9. Two judgement calls flagged rather than assumed

Per the instruction to ask where a finding could plausibly be intentional:

1. **F-04, the 1:1 benign under-sampling, is deliberate.** `config.yaml:17` calls it "paper-faithful",
   matching Bizzarri et al. The *design* is intentional and defensible as a replication. What is not
   stated anywhere is that it makes every absolute PR-AUC ~4× optimistic relative to the capture. My
   recommendation is to keep the protocol and add the prevalence-faithful column, not to change the
   split. **Confirm before I touch it.**
2. **F-08, `BeaconLike`.** The predicate may have been chosen before the Bot measurement and merely
   *validated* against it, in which case the provenance is weaker than it looks from the docstring.
   `behavior.py:32-40` reads as if the measurement drove the choice, but that is an inference from a
   comment. **Tell me which it was**; the fix differs (re-derive vs. relabel).

---

*Phase 1 complete. No file other than this report was created or modified. Awaiting approval of
Batch A before any change.*

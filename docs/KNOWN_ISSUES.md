# Known Issues (Living Document)

> Track bugs, design flaws, and risks here. Mark `[OPEN]` / `[FIXED]` / `[WONTFIX]`. Reference from commits when resolved.
>
> **Restructured 2026-07-29.** The file previously had duplicated `## High` and `## Medium` headings
> (two interleaved halves), and carried five `[OPEN]` issues that had already been fixed — including
> "no dependency manifest" when `requirements.txt` has been pinned since 2026-06-18. It was also
> missing the entire 2026-07-27 measurement-defect class, which lived only in STATUS/CHANGELOG.
> Severity now reflects impact on **current** work; issues scoped to superseded code are marked as such.

## Legend

| Tag | Meaning |
|---|---|
| `[OPEN]` | Live — affects current work |
| `[FIXED]` | Resolved, kept for the record |
| `[SUPERSEDED]` | Real when written, but scoped to code that is no longer used |
| `[WONTFIX]` | Accepted limitation, deliberately not fixed |

---

## Critical — measurement integrity

These are the highest-severity class in this project: they do not crash, they produce **numbers that
look fine and are wrong**. All three were caught only by auditing distributions rather than reading
summary metrics.

### [FIXED 2026-07-27] float32 softmax saturation silently faked perfect recall
Scores were computed as `patk = 1 − softmax[benign]` in float32. For a confident model `p(benign)`
rounds to exactly 1.0, so `patk` underflows to **exactly 0.0**. On `ltn_ctrl_w0`, **99.25% of benign
and 51.7% of zero-day flows** sat at exactly 0.0. The 1%-FPR threshold therefore landed at 0.0,
flagged everything (achieved FPR = 1.000), and produced `recall=1.0000` rows for every family — an
artefact, not detection. `zd_f1` collapsed to `0.13153…`, the algebraic predict-all-positive constant
at 7% prevalence, **identical across three different models** — the tell that should have been caught
sooner. **4 of 13 runs affected**, including all three fair-loop runs the control experiment depended on.
**Fix:** `metrics.py` now reports `diagnostics.saturated` plus `achieved_fpr` / `largest_tie_frac`;
`scripts/rescore_logits.py` re-scores from pre-softmax logits as `logsumexp(attack) − benign_logit`.

### [FIXED 2026-07-27] The headline metric was a size-weighted mixture
"Benign vs all 6 unknowns" averaged families whose detectability differs by ~30×, so it moved for
reasons unrelated to detection quality — and it **reordered the model ranking** versus a per-family
view (this is what produced the retracted "XGBoost ≈ CNN" claim). **Fix:** `metrics.py` headline is
now per-family PR-AUC + macro over families with n ≥ `MIN_FAMILY_N` (100); the blend is secondary.
Heartbleed (n=11), Infiltration (n=36) and SQL Injection (n=21) are excluded as underpowered rather
than reported to 4 decimal places.

### [OPEN] `runs.jsonl` mixes two incompatible metric schemas
Records written before the 2026-07-27 `metrics.py` rewrite carry only `zd_pr_auc` (the blended
number); later records carry per-family + macro. Nothing in the file marks which is which, so a naive
read of the run history compares incomparable numbers. **Concretely: `random_forest` has never been
re-scored on the corrected metric** and is therefore absent from STATUS's corrected table.
**Fix:** re-run `baselines.py` to refresh RF, and add a schema-version field to `tracking.log_run`.

---

## High

### [OPEN] Behaviour validation tables were measured on the superseded temporal split
`behavior.py`'s built-in validation, and the coverage table in
[behaviour_abstraction_current.md](implementation/behaviour_abstraction_current.md), report PortScan
(0.955) and DDoS (0.62) as **zero-day** coverage. Under the paper split **both are known, trained-on
classes**, so the behaviours' strongest coverage contributes nothing to the zero-day metric. The
families that remain zero-day are exactly the ones the table shows as weak/partial.
**Fix:** regenerate the validation tables against `data/processed/paper/`. Until then, do not cite
"PortScan/DDoS are strongly covered" as evidence for the symbolic approach.

### [OPEN] `HighEntropy` is not true entropy
Named honestly in code and docs, but it is packet-length **standard deviation**, not Shannon entropy
of the payload — flow features contain no payload bytes. Any axiom or explanation phrased as
"high entropy ⇒ encryption/obfuscation" is overclaiming. Either keep the approximation and always
qualify it, or rename to `PacketSizeVariance`.

### [OPEN] `BeaconLike` is binary, not fuzzy
It returns exactly 0.0 or 1.0 (`~np.isin(dst_port, WELL_KNOWN_PORTS)`), unlike the other six graded
behaviours. Deliberate — port number is not ordinal, and a magnitude ramp was tried and dropped for
being anti-correlated with Bot (ROC 0.3995). But consequences must be respected downstream: it
contributes a hard 0/1 to product-t-norm conjunctions, and as a KG `exhibits` edge weight it will
give a bimodal distribution rather than a spread. Relevant to Phase 4.

### [WONTFIX-for-now] `RepeatedConnections` returns constant zero
`REPEATED_CONNECTIONS_AVAILABLE = False`; the behaviour is always 0.0.
⚠️ **The historical blocker is resolved** — the IP/port/timestamp side-tables
(`data/processed/paper/meta_{train,val,test}.csv`) now exist, aligned row-for-row, since the
2026-06-18 dataset upgrade. The behaviour is **unblocked but unwired**, which is a deprioritization
decision, not a data constraint. No longer motivated as a Bot fix (the oracle result located Bot's
signature in per-flow features); may still help Infiltration / lateral movement.
**A constant-zero column is silently carried through `behaviour_matrix` (column 6) and into any
consumer that does not filter it** — including, prospectively, the KG.

---

## Medium

### [OPEN] PowerShell `*>>` batch logs are mixed-encoding
When a PowerShell script redirects a Python subprocess's output with `*>> $log`, the resulting file
mixes **UTF-8** (Python's own stdout, passed through) with **UTF-16LE** (PowerShell's `Add-Content`
header lines), interleaved with no marker. Naive single-encoding reads (`iconv -f UTF-16LE`, plain
`Get-Content`) either garble the UTF-8 portions into CJK-looking mojibake or silently truncate.
Cost real time **3 separate times** in the 2026-07-27 session.
**Workaround:** locate section markers by searching raw bytes for both `text.encode('utf-8')` and
`text.encode('utf-16-le')`, then decode each segment with whichever codec matched.
**Real fix:** don't mix `Add-Content` with `*>>` redirection in the same file — emit batch headers
from the Python side (`print`) so the whole log is one encoding.

### [OPEN] Double class-weighting in `cnn3.py` / `cnn_paper.py`
Both `class_weight=` in `fit()` **and** the focal-loss `alpha` weight imbalance, compounding the
effect. Not incorrect, but the effect multiplies — pick one when tuning.
Detail: [cnn_current.md](implementation/cnn_current.md).

### [OPEN] Smoke-test artifacts pollute `outputs/predictions/`
`y_prob_smoke_test.npy`, `y_prob_smoke_perf_test.npy`, `y_prob_smoke_ax6_test.npy`,
`y_prob_smoke_seed43_test.npy`, `y_prob_smoke_test_test.npy` are undertrained debris from
`LTN_SUBSET`/`CNN_SUBSET` smoke runs, sitting in the same directory and naming space as real fusion
channels. Risk: one gets picked up as a channel. Safe to delete; better, write smoke output to a
`smoke/` subdirectory.

### [OPEN] TensorFlow can be blocked by Windows Smart App Control
`import tensorflow` fails with `ImportError: DLL load failed … An Application Control policy has
blocked this file`, on a **different native DLL each attempt**. Root cause (diagnosed 2026-07-27):
Smart App Control (`VerifiedAndReputablePolicyState=1` in
`HKLM\SYSTEM\CurrentControlSet\Control\CI\Policy`) rejecting TF's unsigned compiled wheels. Not a
code or environment fault. numpy/sklearn/scipy/xgboost are unaffected — `baselines.py` and
`skyline_oracle.py` still run. **Resolution:** user disables Smart App Control in Windows Security
(reversible without reinstall on build ≥ 26200.8116). **Diagnose via** Event Viewer → Applications
and Services Logs → Microsoft → Windows → CodeIntegrity → Operational.

---

## Low

### [OPEN] `history['accuracy']` is a 5,000-sample proxy in `ltn.py` / `ltn_paper.py`
The train-accuracy curve is computed on a fixed, unshuffled slice rather than the full train set.
Affects plots only, not model selection (which uses `val_loss`).

---

## Resolved

### [FIXED 2026-07-27] ω=1.0 collapsed on 2 of 3 seeds
`LTN_OMEGA_MODE=fixed` made the SAT weight independent of CE's actual magnitude, so whether SAT or CE
dominated the early-training gradient was decided by random initialization. When SAT won that window
the model never learned to classify, and best-by-val-loss early stopping locked it in by ~epoch 10
(best epoch 1–2, macro 0.052 / 0.037). ω=2.0 was the same dynamic with zero margin (100% reproducible).
**Fix:** `LTN_OMEGA_MODE=ratio` scales SAT to a fixed fraction of CE. Re-ran the same 3 seeds —
**zero collapses**, tight macro range 0.58–0.61. `ratio` is now the code default.

### [FIXED 2026-06-18] Focal-loss shape bug silently broke `model.fit()` training
`tf.one_hot(y_true, n)` where Keras passes `y_true` as `(batch, 1)` — the one-hot then broadcast into
a `(batch, batch, n)` garbage tensor, freezing val_loss and pinning accuracy near-random. Confirmed by
a controlled race (plain CE → 0.996 val-acc; focal as-is → stuck at 0.50; focal fixed → 0.996).
**Fix:** flatten `y_true` to `[-1]` before one-hot, in both `cnn_paper.py` and `cnn3.py`. The LTN
custom loop was unaffected (it passes `(batch,)` directly). **Any new loss function must apply the
same `reshape([-1])`.** Also fixed alongside: callback monitors (`val_sparse_categorical_accuracy`)
that had silently disabled early-stopping and checkpointing.

### [FIXED 2026-06-18] Behaviour abstraction was dead code
`scripts/behavior.py` had misaligned feature indices (`RATE_FEATURES=[5,6,7]` actually pointed at
packet-length fields), was never imported, and never generated thresholds. **Rebuilt:** verified
indices via `check.py`, vectorised, fuzzy `[0,1]` outputs, data-driven thresholds saved to
`outputs/metadata/behaviour_thresholds.npy`, with a built-in validation harness. Two bugs were caught
*by* that validation: flag-count `ProtocolAnomalies` fired 45% on benign / 0% on attacks (dropped),
replaced by `ScanProbe`. Detail:
[behaviour_abstraction_current.md](implementation/behaviour_abstraction_current.md).

### [FIXED 2026-06-18] `utils/config.py` was stale orphaned code
Belonged to an abandoned raw-PCAP/payload pipeline (`PAYLOAD_LEN=1500`, 3 classes, time windows);
imported by nothing. **Deleted** along with the `utils/` directory. Origin of the diagram's
"1500 bytes" boxes. Replaced by `config.yaml` + `scripts/config.py`.

### [FIXED 2026-06-18] No dependency manifest
`requirements.txt` now pins every dependency exactly (TF 2.15.1 / numpy 1.26.4 / scikit-learn 1.4.2 /
xgboost 3.2.0 / networkx 3.2.1 / python-louvain 0.16 / shap 0.45.1 / pyyaml 6.0.3 / psutil 6.1.0).

⚠️ **Partial — the Python version is still not machine-enforced.** `requirements.txt` documents
"Target: Python 3.11" in a comment, but there is **no `.python-version` or `pyproject.toml`
`requires-python`**, so nothing prevents creating the venv on a wrong interpreter. TF 2.15 supports
only Python 3.9–3.11; on 3.12+ the install fails confusingly. Low priority (the venv exists and
works), but the original issue is not fully closed.

### [FIXED 2026-06-18] `.gitignore` did not match real artifact locations
Rewritten to directory-based ignores matching the reorganised layout; `outputs/figures/` is
intentionally tracked. Verified no large binaries were ever committed.

### [FIXED 2026-06-18] Unused binary split vars in `cnn3.py`
`y_train_b` / `y_val_b` computed but not used downstream. Removed.

### [FIXED 2026-07-29] `preprocess.py` hardcoded its input path
Line 27 read `os.path.join(paths.ROOT, "data", "raw_csv_full")`, bypassing `paths.py` — while
`paths.RAW_CSV` still pointed at the abandoned `data/raw_csv`. Violated the project's own rule that
all locations come from `paths.py`. **Fix:** added `paths.RAW_CSV_FULL` (current) and `paths.PAPER`,
kept `paths.RAW_CSV` marked legacy, and pointed `preprocess.py` at the constant.

---

## Superseded (real when written; scoped to code no longer in use)

### [SUPERSEDED] LTN axioms are label tautologies
`scripts/ltn.py`'s original axioms used only ground-truth labels, restating the supervised target, so
they could not help zero-day detection. **Fixed 2026-06-18** by re-grounding Ax3/Ax4 on behaviour
predicates — and `ltn.py` itself was then superseded by `ltn_paper.py`, whose axiom set is
Ax1/Ax2 (label anchors, legitimate consistency constraints) + Ax3–Ax6 (behaviour-grounded).
The current concern is the opposite one: the behaviour-grounded axioms are *not* tautological but
still **cost macro PR-AUC**. See [STATUS.md](STATUS.md).

### [SUPERSEDED] Dead fuzzy operators in `ltn.py`
`fuzzy_and`, `fuzzy_not`, `fuzzy_forall` defined but never used (SAT aggregation was inlined).
Cosmetic, and scoped to the superseded legacy script.

### [SUPERSEDED] Adaptive ω ignores Ax3/Ax4
ω adaptation in the legacy `ltn.py` used only `mean(ax1_sat, ax2_sat)`. `ltn_paper.py` uses
`LTN_OMEGA_MODE` (`fixed` | `ratio`) instead, so this specific defect no longer exists.

### [FIXED 2026-06-18] `model_focal.keras` provenance unknown
A stale experiment artifact not produced by any script. **Deleted** during the artifact cleanup.

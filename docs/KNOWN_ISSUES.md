# Known Issues (Living Document)

> Track bugs, design flaws, and risks here. Mark `[OPEN]` / `[FIXED]` / `[WONTFIX]`. Reference from commits when resolved.

## Critical (block the neuro-symbolic goal)

### [OPEN] LTN axioms are label tautologies
`scripts/ltn.py` axioms use only ground-truth labels, restating the supervised target. They add no independent knowledge and **cannot help zero-day detection**. Fix: re-ground axioms in behaviour predicates (behaviour → class). Detail: [ltn_current.md](implementation/ltn_current.md).

### [FIXED 2026-06-18] Behaviour abstraction was dead code
`scripts/behavior.py` had misaligned feature indices, was never imported, and never generated thresholds. **Rebuilt**: verified indices (via `check.py`), vectorised, fuzzy `[0,1]` outputs, data-driven thresholds saved to `outputs/metadata/behaviour_thresholds.npy`, with a built-in validation harness. Behaviours validated discriminative; PortScan/DDoS (largest zero-day families) strongly covered. Still pending: **wire into the LTN** (next step). Detail: [behaviour_abstraction_current.md](implementation/behaviour_abstraction_current.md).

## High

### [OPEN] `RepeatedConnections` behaviour has no data source
Requires source/dest IP+port, which `preprocess.py` drops as identifiers. Fix options: (a) persist IP/port/timestamp to a side table keyed by row index; (b) scope behaviour out of v1. Detail: [behaviour_abstraction.md](target/behaviour_abstraction.md#derivability-from-flow-features-important).

### [OPEN] `HighEntropy` not truly derivable from flow features
No payload bytes available; only approximable via packet-length variance. Decide whether to approximate (and label it honestly) or defer.

## Medium

### [OPEN] Dead fuzzy operators in `ltn.py`
`fuzzy_and`, `fuzzy_not`, `fuzzy_forall` defined but never used. Either use them in real axioms or remove to avoid implying functionality that isn't there.

### [OPEN] Double class-weighting in `cnn3.py`
Both `class_weight=` in `fit()` and focal-loss `alpha` weight imbalance, compounding the effect. Pick one. Not incorrect, but worth tuning. Detail: [cnn_current.md](implementation/cnn_current.md).

### [OPEN] Adaptive ω ignores Ax3/Ax4
ω adaptation in `ltn.py` uses only `mean(ax1_sat, ax2_sat)`.

## High

### [OPEN] No dependency manifest / no Python version pin
There is no `requirements.txt`, `environment.yml`, or `.python-version`. Reproducing the env is guesswork, and TensorFlow on Windows is version-sensitive. Fix: add a pinned `requirements.txt` + document the Python/TF versions. (Being addressed during venv setup.)

### [OPEN] `.gitignore` does not match real artifact locations
Current `.gitignore` only ignores `data/raw_pcaps/`, `data/processed/*.npy`, `data/processed/chunks*/` — paths from the **abandoned payload pipeline** that don't exist. The real pipeline writes large artifacts to the **repo root** (`X_test.npy` ~600 MB, `X_*_emb.npy` ~300 MB, `*.keras`, `*.pkl`, `clean_*.csv`, `features_*.csv`, `*.png`) — none are ignored. Risk: committing hundreds of MB of binaries. Fix: rewrite `.gitignore` for the actual layout.

## Medium

### [FIXED 2026-06-18] `utils/config.py` was stale orphaned code
Belonged to an abandoned raw-PCAP/payload pipeline (`PAYLOAD_LEN=1500`, 3 classes, time windows); imported by nothing. **Deleted** along with the `utils/` directory. (Origin of the diagram's "1500 bytes" boxes.)

## Low

### [OPEN] `model_focal.keras` provenance unknown
Present in repo but not produced by any current script. Likely a stale experiment artifact. Confirm and delete, or document its source.

### [OPEN] `history['accuracy']` is a 5000-sample proxy in `ltn.py`
Train-accuracy curve is computed on a fixed unshuffled slice, not the full train set.

### [FIXED 2026-06-18] Unused binary split vars in `cnn3.py`
`y_train_b` / `y_val_b` computed but not used downstream. **Removed** (the redundant second `train_test_split` block).

# Behaviour Abstraction — Current Implementation

**File:** `scripts/behavior.py`
**Verdict:** ✅ Rebuilt and validated (2026-06-18). Was previously dead code; now a working, verified module.

This documents `behavior.py` **as it stands today** after the rebuild. For the history of what was wrong before, see [CHANGELOG](../CHANGELOG.md) and [KNOWN_ISSUES](../KNOWN_ISSUES.md).

## What it does

Maps raw CIC-IDS2017 flow features into named, human-meaningful **behaviours**, each a fuzzy confidence in `[0, 1]`. These are the shared symbolic vocabulary for the LTN axioms and the Knowledge Graph.

- **Operates on RAW (unscaled) features** — the values in `features_*.csv` before StandardScaler — so thresholds are interpretable. (Do **not** pass scaled data.)
- **Fully vectorised** numpy — runs on 1.66M flows in seconds (the old per-row loop was unusable).
- **Data-driven thresholds** computed on training data via percentiles, saved to `outputs/metadata/behaviour_thresholds.npy`.
- **Fuzzy `[0,1]` outputs** — plug directly into product fuzzy logic and weighted KG edges.
- **Verified feature indices** against the 68-column post-preprocessing order (`scripts/check.py`).

## The behaviours

| Behaviour | Signal | Type | Target attacks |
|-----------|--------|------|----------------|
| `BurstTraffic` | Flow Packets/s | high-ramp | DoS / flood |
| `HighVolume` | Total fwd+bwd packets | high-ramp | volumetric / Infiltration |
| `LargePackets` | Packet Length Mean | high-ramp | DDoS / exfil |
| `HighEntropy` | Packet Length Std *(approx — NOT Shannon entropy)* | high-ramp | DDoS / payload anomalies |
| `ScanProbe` | short Flow Duration **AND** tiny payload (fuzzy-AND) | low-ramps | PortScan / probes |
| `RepeatedConnections` | — | **unavailable** (→ 0.0) | needs IP/port side table |

Fuzzy ramps: `_ramp_high` (0 below `lo`=p50, 1 above `hi`=p95) and `_ramp_low` (1 at/below `lo`=p5, 0 at/above `hi`=p40). `ScanProbe = ramp_low(duration) × ramp_low(payload)`.

## Validation (built into `python scripts/behavior.py`)

**Discriminativeness on training data** (mean confidence, attack ÷ benign ratio):

| Behaviour | benign | attack | ratio |
|-----------|-------:|-------:|------:|
| BurstTraffic | 0.075 | 0.163 | 2.18 |
| HighVolume | 0.137 | 0.180 | 1.31 |
| LargePackets | 0.079 | 0.580 | **7.38** |
| HighEntropy | 0.074 | 0.583 | **7.85** |
| ScanProbe | 0.214 | 0.282 | 1.32¹ |
| RepeatedConnections | 0 | 0 | n/a |

¹ ScanProbe's training ratio understates it — it targets the *zero-day* PortScan in the test set.

**Coverage of zero-day classes (test set):**

| Class | n | Caught by | Conf |
|-------|--:|-----------|-----:|
| PortScan | 158,804 | ScanProbe | **0.955** |
| DDoS | 128,025 | LargePackets/HighEntropy | **0.62** |
| Infiltration | 36 | HighVolume | **0.79** |
| Bot | 1,956 | ScanProbe | 0.35 (partial) |
| Web Attacks | ~2,200 | — | weak (limitation) |

The two largest zero-day families (PortScan + DDoS) are strongly covered by behaviours that transfer from training — the core requirement for the neuro-symbolic approach.

## Known limitations (honest)

1. **`RepeatedConnections` is unavailable** — needs source/dest IP+port, which preprocessing drops. Module exposes `REPEATED_CONNECTIONS_AVAILABLE = False` and returns zeros. Fix path: IP/port side table from `preprocess.py`. Tracked in [KNOWN_ISSUES](../KNOWN_ISSUES.md).
2. **`HighEntropy` is an approximation** — packet-length variance, not true Shannon payload entropy (no payload bytes in flow features). Named honestly.
3. **Web Attacks and Bot remain weakly covered** — small, stealthy, low-volume; the current behaviour set does not separate them well. Documented, not hidden.
4. **Flag-count behaviours were tried and dropped** — in CIC-IDS2017 the flag-count columns are ~0 even for real scans, so they carry no signal. Flow structure (ScanProbe) replaced them.

## API

```python
import behavior
thr = behavior.compute_thresholds(X_train_raw)        # fit percentiles
behavior.save_thresholds(thr)                         # -> outputs/metadata/
beh = behavior.abstract_behaviours(X_raw, thr)        # dict[name] -> (N,) in [0,1]
M   = behavior.behaviour_matrix(X_raw, thr)           # (N, 6) array
```

`behavior.BEHAVIOUR_NAMES` lists the six keys in fixed order. Run `python scripts/behavior.py` to (re)generate thresholds and print the validation tables above.

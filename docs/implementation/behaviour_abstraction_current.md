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

**There are 7 behaviours, in this exact order** (`behavior.BEHAVIOUR_NAMES`):

| # | Behaviour | Signal | Type | Target attacks |
|---|-----------|--------|------|----------------|
| 0 | `BurstTraffic` | Flow Packets/s | high-ramp | DoS / flood |
| 1 | `HighVolume` | Total fwd+bwd packets | high-ramp | volumetric / Infiltration |
| 2 | `LargePackets` | Packet Length Mean | high-ramp | DDoS / exfil |
| 3 | `HighEntropy` | Packet Length Std *(approx — NOT Shannon entropy)* | high-ramp | DDoS / payload anomalies |
| 4 | `ScanProbe` | short Flow Duration **AND** tiny payload (fuzzy-AND) | low-ramps | PortScan / probes |
| 5 | **`BeaconLike`** | Destination Port **∉** `WELL_KNOWN_PORTS` | **binary set-membership** | **Bot / C2** |
| 6 | `RepeatedConnections` | — | **unavailable** (→ 0.0) | needs IP/port side table |

Fuzzy ramps: `_ramp_high` (0 below `lo`=p50, 1 above `hi`=p95) and `_ramp_low` (1 at/below `lo`=p5, 0 at/above `hi`=p40). `ScanProbe = ramp_low(duration) × ramp_low(payload)`.

### ⚠️ Two properties of this list that have already caused bugs

**1. `BEHAVIOUR_NAMES` order is load-bearing — never index it positionally.**
`BeaconLike` was inserted at position **5**, *before* the constant-zero `RepeatedConnections`.
`cnn_auxhead_paper.py` previously selected behaviours with `BEHAVIOUR_NAMES[:5]` (a slice intended
to drop the unavailable trailing entry) — which would have silently excluded the new behaviour
instead. It now filters **by name**. Any new consumer must do the same. Adding a behaviour also
widens `ltn_paper.py`'s `W_tr` / `sat_loss` behaviour matrix (3 → 4 columns when Ax6 landed).

**2. `BeaconLike` is the only behaviour that is not graded.** It returns exactly `0.0` or `1.0`
(`~np.isin(dst_port, WELL_KNOWN_PORTS)`), not a ramp. This is deliberate — destination-port
*magnitude* is not ordinal, and a percentile ramp on the raw port number was built, measured, and
**dropped** for being anti-correlated with Bot (ROC 0.3995, worse than random). Consequences to
respect downstream: it contributes a hard 0/1 to product-t-norm conjunctions, and as a Knowledge
Graph `exhibits` edge weight it will produce a bimodal weight distribution rather than a spread.

### `BeaconLike` provenance and standalone validation

Derived by isolating a **Bot-vs-benign-only** XGBoost's feature importances (`scripts/skyline_oracle.py`,
2026-07-27), then checking full distributions rather than medians. `WELL_KNOWN_PORTS` is a fixed
list of 24 standard service ports (20, 21, 22, 23, 25, 53, 80, 443, 445, 3389, …) — **external
domain knowledge, not fitted to this dataset.**

| Candidate signal | Bot ROC | Bot PR-AUC | vs chance (0.034) |
|---|---:|---:|---:|
| port-magnitude ramp — **dropped** | 0.400 | 0.034 | ~1.0× (anti-correlated) |
| **well-known-port membership — kept** | **0.887** | **0.135** | **~4.0×** |

Comparable to Mahalanobis's 4.3× on Bot — a real, non-tautological signal *standalone*.

> 🔴 **But it does not help the trained model.** Wired into `ltn_paper.py` as **Ax6**, it was
> initially reported to "roughly double Bot lift" — **that claim is RETRACTED.** Across 3 seeds the
> no-axiom control's mean Bot lift (2.07×) is *higher* than either Ax6 variant's (1.87×, 1.70×), and
> Ax6 robustly *costs* macro PR-AUC. Inference-level fusion of the same signal
> (`fusion_beaconlike.py`) changed nothing — coefficients `[2.35, 0.02]`. Full detail and reasoning
> in [STATUS.md](../STATUS.md). Treat `BeaconLike` as a validated *standalone* signal that has so
> far resisted every attempt to transfer its value into a trained model.

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

**Coverage of zero-day classes (test set) — ⚠️ measured on the TEMPORAL split (2026-06-18):**

| Class | n | Caught by | Conf | Still zero-day today? |
|-------|--:|-----------|-----:|---|
| PortScan | 158,804 | ScanProbe | **0.955** | ❌ **no — now a KNOWN class** |
| DDoS | 128,025 | LargePackets/HighEntropy | **0.62** | ❌ **no — now a KNOWN class** |
| Infiltration | 36 | HighVolume | **0.79** | ✅ yes (but underpowered, n=36) |
| Bot | 1,956 | ScanProbe | 0.35 (partial) | ✅ yes — the family that matters |
| Web Attacks | ~2,200 | — | weak (limitation) | ✅ yes |

> 🔴 **The conclusion originally drawn from this table no longer holds.** It read: *"The two largest
> zero-day families (PortScan + DDoS) are strongly covered by behaviours that transfer from training
> — the core requirement for the neuro-symbolic approach."* Under the **paper-aligned split adopted
> the same day**, PortScan and DDoS are **known, trained-on classes**. The behaviours' strongest
> coverage therefore lands entirely on classes the CNN already handles, and contributes nothing to
> the zero-day metric.
>
> The zero-day set is now Bot / Web×3 / Infiltration / Heartbleed (~4,183 test flows), of which only
> **three are adequately powered** (Bot n=1,956, Web Brute Force, Web XSS). On exactly those, this
> table shows the behaviour set is *weak-to-partial* — which is the honest reading, and is consistent
> with every Phase-2 result: the axioms are volume/scan-shaped and target families that are no longer
> the test. `BeaconLike` was built specifically to close this gap and, standalone, does
> (4× lift on Bot) — but has not transferred into a trained model. See [STATUS.md](../STATUS.md).
>
> **This table should be regenerated on the paper split** before it is cited again. Tracked in
> [KNOWN_ISSUES.md](../KNOWN_ISSUES.md).

## Known limitations (honest)

1. **`RepeatedConnections` is unavailable in code** — module exposes
   `REPEATED_CONNECTIONS_AVAILABLE = False` and returns zeros.
   ⚠️ **The stated blocker is out of date:** the IP/port side table *now exists*
   (`data/processed/paper/meta_{train,val,test}.csv`, carrying Flow ID / Source IP / Source Port /
   Destination IP / Destination Port / Protocol / Timestamp, aligned row-for-row — added with the
   2026-06-18 dataset upgrade to `GeneratedLabelledFlows`, `config.yaml has_ip_timestamp: true`).
   The behaviour is therefore **unblocked but unwired** — a deliberate deprioritization, not a data
   constraint. It is no longer motivated as a Bot fix (the oracle result located Bot's signature in
   per-flow features), but remains plausible for Infiltration / lateral movement.
   Tracked in [KNOWN_ISSUES](../KNOWN_ISSUES.md).
2. **`HighEntropy` is an approximation** — packet-length variance, not true Shannon payload entropy (no payload bytes in flow features). Named honestly.
3. **Web Attacks and Bot remain weakly covered** — small, stealthy, low-volume; the current behaviour set does not separate them well. Documented, not hidden.
4. **Flag-count behaviours were tried and dropped** — in CIC-IDS2017 the flag-count columns are ~0 even for real scans, so they carry no signal. Flow structure (ScanProbe) replaced them.

## API

```python
import behavior
thr = behavior.compute_thresholds(X_train_raw)        # fit percentiles (p50/p95 high, p5/p40 low)
behavior.save_thresholds(thr)                         # -> outputs/metadata/behaviour_thresholds.npy
beh = behavior.abstract_behaviours(X_raw, thr)        # dict[name] -> (N,) in [0,1]
M   = behavior.behaviour_matrix(X_raw, thr)           # (N, 7) array, column order = BEHAVIOUR_NAMES
```

`behavior.BEHAVIOUR_NAMES` lists the **seven** keys in fixed order — select by name, never by slice
(see the ordering hazard above). Accepts `(N, 68)` or `(N, 68, 1)`. **Pass RAW, unscaled features**;
thresholds are interpretable percentiles of real units, so scaled input silently produces garbage.
`load_thresholds()` falls back to neutral `(0.0, 1.0)` ramps **with a printed warning** if the
threshold file is missing — check for that warning rather than assuming defaults are sane.

Run `python scripts/behavior.py` to (re)generate thresholds and print the validation tables above.

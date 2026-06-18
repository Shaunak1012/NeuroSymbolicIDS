# Behaviour Abstraction

> **Status: partial.** A behaviour-extraction module exists (`scripts/behavior.py`) but uses a *different vocabulary* than the target diagram, and some target behaviours are not derivable from the current feature set. This document specifies the target and the gap.

Behaviour Abstraction is the shared symbolic vocabulary of the system. It maps raw numeric features into named, human-meaningful behaviours that feed **both** the LTN axioms and the Knowledge Graph. It is the bridge between the neural/numeric world and the symbolic world.

## Target Behaviours (from the diagram)

| Behaviour | Intuition | Typical attacks |
|-----------|-----------|-----------------|
| `HighEntropy` | Payload/feature randomness is unusually high | Encrypted C2, exfiltration, obfuscation |
| `BurstTraffic` | Short, intense bursts of packets/bytes | DoS, DDoS, flooding |
| `RepeatedConnections` | Same endpoints/ports contacted repeatedly | PortScan, brute force (Patator), Bot beaconing |
| `ProtocolAnomalies` | Unusual flag combinations / protocol misuse | Scans, malformed-packet attacks, Heartbleed |

## Derivability from Flow Features (Important)

The project uses **CIC-IDS2017 flow-feature CSVs**, not raw payloads. This constrains which target behaviours can actually be computed:

| Behaviour | Derivable from flow features? | How / Caveat |
|-----------|------------------------------|--------------|
| `BurstTraffic` | ✅ Yes | Flow rates (bytes/s, packets/s), flow duration, IAT std. Directly available. |
| `ProtocolAnomalies` | ⚠️ Partial | TCP flag counts (SYN/FIN/RST/PSH) capture *some* anomalies (e.g., NULL/XMAS-like flag patterns), but not full protocol-state violations. |
| `HighEntropy` | ⚠️ Approximate only | True payload entropy needs packet bytes, which flow features lack. Approximate via packet-length variance / distribution spread — **not** real Shannon entropy. Document this honestly. |
| `RepeatedConnections` | ❌ Not from `features_*.csv` | Requires source/dest **IP and port**, which preprocessing currently **drops**. Must either (a) retain IPs from `clean_*.csv` and aggregate cross-flow, or (b) let the KG track endpoint repetition. |

> **Action item:** to support `RepeatedConnections`, preprocessing must preserve IP/port columns (currently dropped as identifiers) in a side table, or the KG must compute repetition from flow metadata. Tracked in the [gap analysis](roadmap_gap_analysis.md).

## Mapping to the Existing `behavior.py`

The current implementation extracts these flags (percentile-threshold based):

| Current flag | Maps to target behaviour |
|--------------|--------------------------|
| `high_rate` + `bursty_iat` | → `BurstTraffic` |
| `high_variance` (+ packet-length spread) | → `HighEntropy` (approximation) |
| `high_traffic`, `large_packets`, `high_mean` | supporting signals (no direct 1:1 target) |
| compound `scan_pattern` (high_traffic ∧ high_rate ∧ high_variance) | → partial `RepeatedConnections` / scan signal |
| compound `exfil_pattern`, `covert_pattern` | supporting attack-pattern signals |

See the implemented detail in [../neuro_symbolic.md](../neuro_symbolic.md).

## Recommended Target API

Refactor `behavior.py` so abstraction returns the **four named target behaviours** (plus optional supporting flags), each as a confidence in [0, 1] rather than a hard boolean — fuzzy values integrate better with both LTN and KG edge weights:

```python
def abstract_behaviours(X, thresholds, meta=None) -> list[dict]:
    """
    Returns one dict per flow:
      {
        "BurstTraffic":        0.0–1.0,
        "HighEntropy":         0.0–1.0,   # approximate (see caveat)
        "ProtocolAnomalies":   0.0–1.0,   # partial
        "RepeatedConnections": 0.0–1.0,   # requires `meta` with IP/port
      }
    `meta` carries endpoint info for RepeatedConnections when available.
    """
```

Fuzzy (continuous) outputs let:
- the **LTN** use them in product-logic axioms directly,
- the **KG** use them as `exhibits` edge weights.

## How Behaviours Flow Downstream

```
Flow features ──> abstract_behaviours() ──> {behaviour: confidence}
                                              │
                          ┌───────────────────┴───────────────────┐
                          ▼                                        ▼
                  LTN axiom inputs                        KG `exhibits` edges
              (constrain CNN training)              (build/reinforce adaptive memory)
```

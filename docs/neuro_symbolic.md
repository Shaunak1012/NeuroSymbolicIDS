# Neuro-Symbolic Approach

> ⚠️ **FROZEN (banner replaced 2026-07-29). The previous banner on this file was itself stale** —
> it warned that `behavior.py` was orphaned dead code and that the LTN axioms were label
> tautologies. **Both were fixed on 2026-06-18** and the warning was left standing for over a year
> of project time. It is preserved in git history; it is not the current state.
>
> What *is* true: **the vocabulary in this document no longer exists in code.** The flags described
> below (`high_traffic`, `large_packets`, `high_rate`, `high_variance`, `high_mean`, `bursty_iat`)
> and the compound patterns (`scan_pattern`, `exfil_pattern`, `covert_pattern`) were **deleted** in
> the 2026-06-18 rebuild. They were replaced by 7 named, fuzzy `[0,1]` behaviours:
> `BurstTraffic`, `HighVolume`, `LargePackets`, `HighEntropy`, `ScanProbe`, `BeaconLike`,
> `RepeatedConnections`. The feature-group index table below is also wrong — the old indices were
> measured to be badly misaligned (`RATE_FEATURES=[5,6,7]` actually pointed at packet-length
> fields) and that is precisely why the module was rebuilt.
>
> The **fuzzy-logic semantics section (product t-norm) is still accurate** and remains the
> operator set used by `ltn_paper.py`.
>
> **Current behaviour module → [implementation/behaviour_abstraction_current.md](implementation/behaviour_abstraction_current.md).
> Current axioms and results → [STATUS.md](STATUS.md).**

## Motivation

A CNN trained on known attack families (DoS, Patator, Heartbleed) will fail to generalise to unseen attack types at test time (Web Attacks, Infiltration, Bot, PortScan, DDoS). This is the zero-day problem. The intended remedy is to inject **symbolic domain knowledge** — rules about how attacks behave at the network level — into the CNN so that detection transfers to unseen attacks. (See banner above: this is the goal, not yet the implemented reality.)

## Behaviour Extraction (`scripts/behavior.py`)

### Feature Groups

The 70 preprocessed features are divided into semantic groups by index:

| Group | Indices (approx.) | Description |
|-------|-------------------|-------------|
| `TRAFFIC_FEATURES` | 1–4 | Packet counts, byte totals |
| `RATE_FEATURES` | 5–7 | Bytes/sec, packets/sec, flow duration |
| `PACKET_LEN_FEATURES` | 10–14 | Min, max, mean, std, variance of packet lengths |
| `IAT_FEATURES` | 15–18 | Inter-arrival time statistics (burstiness) |
| `FLAG_FEATURES` | 20–23 | TCP flag counts (SYN, FIN, RST, PSH) |

> These indices are approximate — use `scripts/check.py` to verify exact positions after preprocessing.

### Threshold Computation

Thresholds are computed from the **training data** (not hardcoded constants) using percentiles:

| Threshold | Percentile | Meaning |
|-----------|-----------|---------|
| `high_traffic` | 75th of traffic mean | Unusually high packet/byte volume |
| `large_packets` | 65th of packet length mean | Above-average payload size |
| `high_rate` | 70th of rate max | High throughput or duration |
| `high_variance` | 80th of row std | Inconsistent feature values across flow |
| `high_mean` | 60th of row mean | Generally elevated feature magnitudes |
| `bursty_iat` | 75th of IAT std | Irregular packet timing |

Thresholds are saved to `behaviour_thresholds.npy` (used by `ltn.py` at training time).

### Atomic Behaviour Flags

Each network flow is mapped to a dict of boolean flags:

| Flag | Condition |
|------|-----------|
| `high_traffic` | mean(TRAFFIC_FEATURES) > threshold |
| `large_packets` | mean(PACKET_LEN_FEATURES) > threshold |
| `high_rate` | max(RATE_FEATURES) > threshold |
| `high_variance` | std(all features) > threshold |
| `high_mean` | mean(all features) > threshold |
| `bursty_iat` | std(IAT_FEATURES) > threshold |

### Compound Patterns

| Pattern | Definition | Intended Target |
|---------|-----------|----------------|
| `scan_pattern` | `high_traffic AND high_rate AND high_variance` | PortScan, DDoS |
| `exfil_pattern` | `large_packets AND high_rate` | Data exfiltration, Infiltration |
| `covert_pattern` | `high_variance AND NOT high_mean` | Stealthy/low-and-slow attacks |

## Logic Tensor Networks (LTN)

### What is LTN?

Logic Tensor Networks embed first-order logic into a differentiable framework. Logical formulae are translated into loss functions using **fuzzy logic** (real-valued truth values in [0, 1]). This allows symbolic rules to be optimised jointly with the neural network via gradient descent.

### Fuzzy Logic Semantics (Product T-norm)

| Operation | Formula |
|-----------|---------|
| AND (t-norm) | `A ∧ B = A × B` |
| OR (t-conorm) | `A ∨ B = A + B − A × B` |
| NOT | `¬A = 1 − A` |
| Implication | `A → B = 1 − A + A × B` |
| Universal (∀) | `ApME = 1 − mean(¬satisfaction)` |

### The Four Axioms

These axioms encode what should always be true for a correct IDS:

**Ax1 — Benign flows stay benign:**
```
∀x ∈ BENIGN_BATCH: P_BENIGN(x) is high
SAT = mean(P_BENIGN[benign_mask])
```

**Ax2 — Attack flows are not benign:**
```
∀x ∈ ATTACK_BATCH: 1 − P_BENIGN(x) is high
SAT = mean(1 − P_BENIGN[attack_mask])
```

**Ax3 — DoS flows are attacks:**
```
∀x ∈ DoS_BATCH: P_ATTACK(x) > 0.5
SAT = mean(1 − P_BENIGN[dos_mask])
```

**Ax4 — Patator flows are attacks:**
```
∀x ∈ PATATOR_BATCH: P_ATTACK(x) > 0.5
SAT = mean(1 − P_BENIGN[patator_mask])
```

### SAT Loss

```
L_SAT = mean([1 − sat_ax1, 1 − sat_ax2, 1 − sat_ax3, 1 − sat_ax4])
```

When axioms are fully satisfied, `L_SAT → 0`.

### Hybrid Loss

```
L_total = L_focal_CE + ω × L_SAT
```

The adaptive weight `ω` starts at 0.1 and is updated each epoch:
- Mean axiom satisfaction < 0.5 → ω increases (prioritise rules)
- Mean axiom satisfaction > 0.8 → ω decreases (rules satisfied, relax)
- `ω ∈ [0.3, 1.0]`

## Why Not Post-hoc Rules?

An alternative approach is to train the CNN first, then override its predictions with symbolic rules at inference time. This is simpler but has drawbacks:
- The CNN's internal representations are never influenced by the rules
- Rules can contradict the CNN score, causing inconsistent behaviour
- The embedding layer doesn't learn to represent symbolic concepts

The Hybrid-LTN approach **internalises** the symbolic knowledge during training, so the learned representations themselves become more rule-consistent.

# Dataset: CIC-IDS2017

> ⚠️ **FROZEN (banner added 2026-07-29) — documents the legacy temporal split only.**
> The **current protocol is the paper-aligned split** defined in [`config.yaml`](../config.yaml)
> and built by `scripts/preprocess_paper.py`: 9 known classes (BENIGN + 8 attacks **including
> PortScan and DDoS**) stratified 80/10/10, benign under-sampled to 1:1, and **6 rare classes**
> (Bot, Heartbleed, Infiltration, Web Attack ×3) held out as zero-day in test only.
> Under that protocol the zero-day table below is wrong — PortScan and DDoS are *trained on*.
>
> Also outdated here: the data source is now `data/raw_csv_full/` (the **GeneratedLabelledFlows**
> variant, which retains Flow ID / IP / Port / Timestamp), not `data/raw_csv/` (MachineLearningCVE);
> and the feature count is **68**, not ~70. Row counts and the 8-file listing remain accurate.
> **Current state → [STATUS.md](STATUS.md).**

**Source**: Canadian Institute for Cybersecurity  
**URL**: https://www.unb.ca/cic/datasets/ids-2017.html  
**Format**: 8 CSV files, one per capture day/session  
**Local path**: `data/raw_csv/`

## Raw Files

| File | Day | Contents |
|------|-----|----------|
| `Monday-WorkingHours.pcap_ISCX.csv` | Monday | Benign traffic only |
| `Tuesday-WorkingHours.pcap_ISCX.csv` | Tuesday | FTP-Patator, SSH-Patator |
| `Wednesday-workingHours.pcap_ISCX.csv` | Wednesday | DoS Hulk, DoS Slowhttptest, DoS Slowloris, DoS GoldenEye, Heartbleed |
| `Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv` | Thursday AM | Web Attacks (XSS, SQLi, Brute Force) |
| `Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv` | Thursday PM | Infiltration |
| `Friday-WorkingHours-Morning.pcap_ISCX.csv` | Friday AM | Bot (Mirai) |
| `Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv` | Friday PM | PortScan |
| `Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv` | Friday PM | DDoS |

## Train / Test Split Strategy

The split is **temporal**, not random — this reflects real-world deployment where a model is trained on historical data and tested on future traffic.

| Split | Days Used | Rows |
|-------|-----------|------|
| **Train** | Monday + Tuesday + Wednesday | 1,666,532 |
| **Test** | Thursday + Friday | 1,161,344 |

> Note: Thursday and Friday contain attack types never seen during training (Web Attacks, Infiltration, **Bot**, DDoS, PortScan). These are the **zero-day** classes.

## Attack Classes

> **Important:** `n_classes` is computed **dynamically** in code (`train_classes = sorted(set(y_train_str))`) — never hardcode it. The list below reflects the standard CIC-IDS2017 Mon–Wed content (~8 classes including BENIGN). Verify against your actual data with the printout in `cnn3.py`.

### Training Classes (~8, label-encoded 0…n−1)

| Label | Day |
|-------|-----|
| BENIGN | All days (Mon–Wed) |
| FTP-Patator | Tuesday |
| SSH-Patator | Tuesday |
| DoS Hulk | Wednesday |
| DoS GoldenEye | Wednesday |
| DoS slowloris | Wednesday |
| DoS Slowhttptest | Wednesday |
| Heartbleed | Wednesday |

### Zero-Day Classes (test set only, label = −1 in multiclass arrays)

| Label | Day |
|-------|-----|
| Web Attack – Brute Force | Thursday AM |
| Web Attack – XSS | Thursday AM |
| Web Attack – Sql Injection | Thursday AM |
| Infiltration | Thursday PM |
| **Bot** | Friday AM |
| PortScan | Friday PM |
| DDoS | Friday PM |

> **Correction note:** Bot is a **zero-day/test** class (Friday Morning is in the test split) — it is **not** a training class. Earlier documentation incorrectly listed it as training class index 8.

## Features

- **Raw columns**: ~79–80 per file (including label/identifiers)
- **After preprocessing**: ~70 numeric features (data-dependent — identifiers and zero-variance columns removed; exact count printed by `preprocess.py`)
- **Removed columns**: Flow ID, Source IP, Destination IP, Timestamp (when present), plus any zero-variance columns (saved to `constant_cols_dropped.npy`)
- **Feature types**: Packet counts, byte totals, flow duration, inter-arrival times, TCP flag counts, packet length statistics, flow rates

## Class Imbalance

BENIGN traffic dominates (~70–80% of samples). Attacks are rare, and within attacks some families (e.g., Heartbleed) have very few samples. This is handled via:
- **Focal Loss** during CNN training (focuses on hard/rare examples)
- **Class weights** computed from training label frequencies
- **Stratified train/val split** to preserve class ratios

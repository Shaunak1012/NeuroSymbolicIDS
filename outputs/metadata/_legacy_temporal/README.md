# Legacy temporal-split metadata (archived 2026-08-03)

These four artifacts belong to the **superseded temporal-split pipeline**
(`cnn3.py` → `eval.py` → `ltn.py`, train Mon–Wed / test Thu–Fri). They were
archived here because two of them **share filenames with the current paper-split
protocol's artifacts while carrying incompatible contents**.

**Moved, not deleted** — per the project rule that artifacts are never destroyed,
and because the legacy pipeline is deliberately retained as a secondary
"hard mode" robustness result.

| File | Written by | Why it is dangerous in the shared namespace |
|---|---|---|
| `zero_day_classes.npy` | `cnn3.py`, `ltn.py` | Lists **DDoS** and **PortScan** as zero-day. Under the current paper-aligned protocol both are **known, trained-on classes**. It also omits **Heartbleed**, which *is* zero-day now. Names additionally carry mojibake (`Web Attack ? Brute Force`) from the raw CSV encoding. |
| `class_names.npy` | `cnn3.py`, `ltn.py` | 8 classes including Heartbleed, missing DDoS/PortScan. The paper split has **9** known classes (BENIGN + 8 attacks). |
| `history.pkl` | `cnn3.py` | Training curve for the superseded temporal CNN. |
| `ltn_history.pkl` | `ltn.py` | Training curve for the superseded temporal LTN. |

## The collision that was fixed

Before this move, `outputs/metadata/zero_day_classes.npy` (temporal) and
`data/processed/paper/zero_day_classes.npy` (paper) had the **same basename** and
different contents. Every current-pipeline script correctly reads the `paper/`
copy — the audit on 2026-08-03 traced all 11 readers and found **no active bug** —
but:

- re-running `cnn3.py` or `ltn.py` would silently overwrite `outputs/metadata/`
  with wrong-protocol class lists, and
- any *future* script reading `paths.METADATA/zero_day_classes.npy` (the obvious,
  natural-looking path) would get the temporal answer and score against
  DDoS/PortScan as if they were unseen.

`paths.METADATA_LEGACY` now points here, and `cnn3.py` / `ltn.py` / `eval.py` were
updated to use it, so the two protocols can no longer collide.

## Caveat on the numbers these produced

The temporal CNN baseline (**0.6689 PR-AUC**) was trained with the focal-loss shape
bug fixed on 2026-06-18, and **has never been retrained**. See KNOWN_ISSUES.md
→ "Focal-loss shape bug" for the open caveat before citing the legacy
*"LTN 0.4529 vs CNN 0.6689"* comparison.

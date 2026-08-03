"""
timeline.py — correct CIC-IDS2017 timestamp reconstruction.

⚠️ READ THIS BEFORE USING `meta_*.csv` TIMESTAMPS FOR ANYTHING TEMPORAL.

The raw `Timestamp` column looks parseable and is not. Naive
`pd.to_datetime(col)` produces **silently wrong** values in two independent ways,
and both were found on 2026-08-03 while building the KG's temporal-decay axis:

**1. The date is D/M/YYYY, not M/D/YYYY.** CIC-IDS2017 was captured Monday
   3 July – Friday 7 July 2017. Default (`dayfirst=False`) parsing turns
   "3/7/2017" into **March 7** and "6/7/2017" into **June 7**, scattering a
   five-day capture across three months. The tell: every parsed date has
   `day == 7` while the month varies — impossible for a 5-day capture.

**2. The clock is 12-hour with no AM/PM marker.** Observed hours are exactly
   {1,2,3,4,5, 8,9,10,11,12} — no 0, no 6, no 7, nothing above 12. That set maps
   one-to-one onto an **08:00–17:00 workday** with no collisions: {8..12} are AM,
   {1..5} are PM. Without this correction, 1 PM sorts *before* 9 AM and any
   ordering, growth rate or decay computed from it is meaningless.

**This reconstruction is validated against the published capture schedule, not
fitted to our labels.** After correction, every attack family lands exactly where
CIC-IDS2017's documentation says it should:

    Web Brute Force   Thu 06 Jul  09:15 – 10:00
    Web XSS           Thu 06 Jul  10:15 – 10:35
    Bot               Fri 07 Jul  09:34 – 12:59
    PortScan          Fri 07 Jul  13:06 – 15:23
    DDoS              Fri 07 Jul  15:56 – 16:16
    BENIGN            Mon 03 Jul  08:56 – Fri 07 Jul 17:02

⚠️ **Consequence for the "adaptive" story (decision logged 2026-08-03):** attacks
in this dataset are **scripted into fixed windows**. Temporal concentration is
therefore partly an artifact of the capture schedule rather than an intrinsic
property of the attacks. Any growth-rate / decay result must say so explicitly —
it is a property of CIC-IDS2017 as much as of the method.

Usage:
    import timeline
    ts = timeline.load_timestamps("test")        # pd.Series[datetime64], row-aligned
    order = timeline.time_order("test")          # int index sorting rows by time
"""
import os
import numpy as np
import pandas as pd

import paths

_CAPTURE_DAYS = {3, 4, 5, 6, 7}   # 3-7 July 2017
_CAPTURE_MONTH = 7


def parse(raw):
    """Parse a raw CIC-IDS2017 Timestamp series into true datetimes."""
    t = pd.to_datetime(raw, dayfirst=True, format="mixed", errors="coerce")
    if t.isna().any():
        raise ValueError(f"{int(t.isna().sum())} timestamps failed to parse")

    days, months = set(t.dt.day.unique()), set(t.dt.month.unique())
    if not days <= _CAPTURE_DAYS or months != {_CAPTURE_MONTH}:
        raise ValueError(
            f"unexpected capture dates: days={sorted(days)} months={sorted(months)}; "
            "expected 3-7 July 2017. Check the dayfirst assumption before trusting this.")

    hours = set(t.dt.hour.unique())
    if hours & {0, 6, 7} or max(hours) > 12:
        raise ValueError(
            f"hour set {sorted(hours)} is not the expected 12-hour pattern "
            "{1..5, 8..12}; the AM/PM reconstruction below would be unsafe.")

    # {1..5} -> PM. {8..12} stay as-is (8-11 AM, 12 noon).
    t = t + pd.to_timedelta(np.where(t.dt.hour.to_numpy() <= 5, 12, 0), unit="h")
    return t


def load_timestamps(split):
    """Row-aligned timestamps for a paper split ('train' | 'val' | 'test')."""
    meta = pd.read_csv(os.path.join(paths.PAPER, f"meta_{split}.csv"),
                       usecols=["Timestamp"])
    return parse(meta["Timestamp"])


def time_order(split):
    """Indices that sort this split's rows into true chronological order."""
    return np.argsort(load_timestamps(split).to_numpy(), kind="stable")

"""
preprocess_2018.py — CSE-CIC-IDS2018 -> the paper-aligned split, Phase 6.

Mirrors `preprocess.py` + `preprocess_paper.py` so the 2018 replication runs the
same protocol on the same feature basis. Where it deviates, it is because 2018
forced the deviation, and each one is called out below rather than absorbed.

FOUR THINGS 2018 DOES DIFFERENTLY, ALL MEASURED NOT ASSUMED
------------------------------------------------------------
1. **Two schemas.** Nine files have 80 columns; `Thuesday-20-02-2018` has 84 --
   the same 80 plus `Flow ID`/`Src IP`/`Src Port`/`Dst IP`. Those four wide
   string columns are the entire reason that file is 3.9 GB against ~340 MB.
   Dropped on load, after which every day is schema-identical.
2. **Renamed features.** CICFlowMeter-V3 abbreviated nearly every column.
   `schema_map_2018.json` (from `schema_2018.py`) carries the 2017->2018 map and
   is *read*, not duplicated here, so the two cannot drift.
3. **67 features, not 68.** 2017's CICFlowMeter emitted `Fwd Header Length`
   twice and this project carried the duplicate as its 68th feature. 2018 emits
   it once. **Any cross-dataset claim must state this**, because the two feature
   matrices are not the same width.
4. **Repeated header rows mid-file** -- the literal string `Label` appears as a
   label value. Dropped, and the count is reported rather than silently absorbed.

🔴 THE TRUNCATION CAVEAT TRAVELS WITH EVERY NUMBER THIS SCRIPT PRODUCES.
`audit_2018.py` establishes that the published CSVs are cut at Excel's 2^20 row
limit, chronologically, so class counts here are **lower bounds** and families
scheduled late in a capture day are under-represented by an unknown amount. This
script does not correct that -- it cannot, without the PCAP -- it only refuses to
let the numbers be read as complete.

CLASS NAMES ARE KEPT AS 2018'S OWN, DELIBERATELY
-------------------------------------------------
It is tempting to rewrite `DoS attacks-Hulk` to 2017's `DoS Hulk` and treat the
two as one class. This script does **not**: canonical labels stay 2018's, and
`EQUIVALENT_2017` below is annotation for the write-up only. Forcing the names
together would manufacture a correspondence the data does not establish -- 2018's
DDoS is three different tools, 2018's `FTP-BruteForce` is not 2017's
`FTP-Patator` run, and collapsing them would hide that in a rename table.

🔴 NO TIMESTAMPS ARE WRITTEN, AND THAT IS THE POINT.
2018 carries the **same** defect this project documents for 2017: a 12-hour
clock with no AM/PM (`audit_2018.py` shows a file whose last stamp reads 02:08
after a first of 08:47). Non-negotiable #8 says temporal work goes through
`timeline.py` -- but `timeline.py` validates against the **2017** capture
schedule and does not support 2018.

Storing the raw strings anyway would leave a loaded gun in
`data/processed/paper_2018/`: the next person sorts by them and silently
reorders the capture, which is exactly the 2017 defect that moved all 114,658
test rows. So this script **drops the column**. The 4-architecture replication
does not need it; only the KG does, and extending `timeline.py` to 2018 is the
prerequisite for that. Filed in KNOWN_ISSUES.

Run:  scripts/run_long.sh preprocess_2018.py
Out:  data/processed/paper_2018/  +  outputs/metadata/preprocess_2018.json
"""
import os
import sys
import json
import glob

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                        # noqa: E402
import config                                       # noqa: E402

cfg = config.get()
SEED = cfg["seed"]
P = cfg["protocol"]
OUT = os.path.join(paths.PROCESSED, "paper_2018")

IDENT_COLS = ["Flow ID", "Src IP", "Src Port", "Dst IP"]   # only in the 84-col file
NON_FEATURE = ["Protocol", "Timestamp", "Label"]           # Dst Port IS kept as a feature

# Annotation for the write-up. NOT applied to the data -- see the docstring.
EQUIVALENT_2017 = {
    "Bot": "Bot",
    "DoS attacks-Hulk": "DoS Hulk",
    "DoS attacks-SlowHTTPTest": "DoS Slowhttptest",
    "DoS attacks-GoldenEye": "DoS GoldenEye",
    "DoS attacks-Slowloris": "DoS slowloris",
    "DDoS attacks-LOIC-HTTP": "DDoS (different tool)",
    "DDOS attack-HOIC": "DDoS (different tool)",
    "DDOS attack-LOIC-UDP": "DDoS (different tool)",
    "FTP-BruteForce": "FTP-Patator (different tool)",
    "SSH-Bruteforce": "SSH-Patator (different tool)",
    "Brute Force -Web": "Web Attack Brute Force",
    "Brute Force -XSS": "Web Attack XSS",
    "SQL Injection": "Web Attack Sql Injection",
    "Infilteration": "Infiltration",
}


def feature_map():
    """2017 name -> 2018 name, read from schema_2018.py's output."""
    p = os.path.join(paths.METADATA, "schema_map_2018.json")
    if not os.path.exists(p):
        sys.exit("missing %s -- run scripts/schema_2018.py first" % p)
    with open(p, encoding="utf-8") as f:
        m = json.load(f)
    if m["unmapped_error"]:
        sys.exit("schema map is incomplete: %s" % m["unmapped_error"])
    return {k: v for k, v in m["map"].items() if v}, m["intentionally_unmapped"]


def load_all(fwd_map):
    """Load every daily CSV, normalise both schemas, rename to 2017 names."""
    want_2018 = list(fwd_map.values())
    frames, stats = [], []
    for path in sorted(glob.glob(os.path.join(paths.RAW_2018, "*.csv"))):
        name = os.path.basename(path)
        df = pd.read_csv(path, low_memory=False, encoding="latin-1")
        df.columns = df.columns.str.strip()
        n_raw = len(df)
        wide = [c for c in IDENT_COLS if c in df.columns]
        if wide:
            df = df.drop(columns=wide)
        # repeated header rows: the literal string "Label" as a label value
        hdr = (df["Label"].astype(str).str.strip() == "Label")
        n_hdr = int(hdr.sum())
        if n_hdr:
            df = df[~hdr]
        missing = [c for c in want_2018 if c not in df.columns]
        if missing:
            sys.exit("%s is missing mapped columns: %s" % (name, missing[:6]))
        # Timestamp deliberately NOT selected -- see the docstring. 2018 has the
        # 12-hour-no-AM/PM defect and timeline.py is 2017-only, so carrying the
        # raw strings forward would invite the naive sort that reordered every
        # test row in 2017.
        keep = df[want_2018 + ["Label"]].copy()
        keep.columns = list(fwd_map.keys()) + ["Label"]
        frames.append(keep)
        stats.append({"file": name, "rows_raw": n_raw, "identifier_cols_dropped": wide,
                      "header_rows_dropped": n_hdr, "rows_kept": int(len(keep))})
        print("  %-50s %9d rows  (hdr rows %d, ident cols %d)"
              % (name[:50], len(keep), n_hdr, len(wide)))
    return pd.concat(frames, ignore_index=True), stats


def main():
    os.makedirs(OUT, exist_ok=True)
    fwd_map, unmapped = feature_map()
    print("=" * 100)
    print("CSE-CIC-IDS2018 -> paper-aligned split")
    print("=" * 100)
    print("features: %d mapped, %d intentionally dropped %s"
          % (len(fwd_map), len(unmapped), unmapped))
    print("-" * 100)

    df, file_stats = load_all(fwd_map)
    print("-" * 100)
    print("combined: %s" % (df.shape,))

    y_raw = df["Label"].astype(str).str.strip()
    feats = df.drop(columns=["Label"])

    before = len(feats)
    feats = feats.apply(pd.to_numeric, errors="coerce")
    feats.replace([np.inf, -np.inf], np.nan, inplace=True)
    good = feats.notna().all(axis=1)
    feats = feats[good].reset_index(drop=True)
    y_raw = y_raw[good].reset_index(drop=True)
    n_bad = before - len(feats)
    print("dropped {:,} inf/nan rows ({:.2f} %), {:,} remain".format(
        n_bad, 100.0 * n_bad / before, len(feats)))

    # BENIGN spelled as 2018 spells it, normalised to the pipeline's convention
    y = y_raw.replace({"Benign": "BENIGN", "benign": "BENIGN"}).values

    counts = {k: int(v) for k, v in pd.Series(y).value_counts().items()}
    print("\nCLASS COUNTS (lower bounds -- see the truncation caveat)")
    for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
        eq = EQUIVALENT_2017.get(k, "")
        print("  %-32s %10d   %s" % (k, v, ("~ 2017 " + eq) if eq else ""))

    # constant columns, computed on the whole 2018 set
    nun = feats.nunique()
    const = nun[nun <= 1].index.tolist()
    if const:
        print("\ndropping %d constant columns: %s" % (len(const), const))
        feats = feats.drop(columns=const)
    print("final feature count: %d" % feats.shape[1])

    meta = {"n_rows": int(len(feats)), "n_features": int(feats.shape[1]),
            "feature_names": list(feats.columns),
            "features_intentionally_unmapped": unmapped,
            "class_counts_lower_bound": counts,
            "equivalent_2017_annotation": EQUIVALENT_2017,
            "constant_columns_dropped": const,
            "per_file": file_stats,
            "timestamps_written": False,
            "timestamps_reason": ("2018 has the 12-hour-no-AM/PM defect and timeline.py is "
                                  "2017-only; storing unparsed strings would invite the naive "
                                  "sort that reordered all 114,658 test rows in 2017"),
            "truncation_caveat": ("published CSVs are cut at Excel's 2^20 row limit, "
                                  "chronologically; all class counts are lower bounds "
                                  "(see outputs/metadata/ids2018_audit.json)"),
            "split_written": False}

    zd = cfg.get("zero_day_classes_2018")
    if not zd:
        print("\n" + "!" * 100)
        print("NO `zero_day_classes_2018` IN config.yaml -- FEATURES WRITTEN, SPLIT NOT BUILT.")
        print("The zero-day family choice is a research decision and is deliberately not")
        print("defaulted here: 2018's Bot has ~286k flows against 1,956 in 2017, so mirroring")
        print("the 2017 split would NOT reproduce the 2017 regime. Choose against the counts")
        print("above, add the key to config.yaml, and re-run.")
        print("!" * 100)
    else:
        zd = set(zd)
        is_zd = np.isin(y, list(zd))
        is_ben = y == "BENIGN"
        is_known = ~is_zd & ~is_ben
        n_known = int(is_known.sum())
        n_keep = min(int(round(P["benign_ratio"] * n_known)), int(is_ben.sum()))
        rng = np.random.RandomState(SEED)
        ben_keep = rng.choice(np.where(is_ben)[0], n_keep, replace=False)
        pool = np.concatenate([ben_keep, np.where(is_known)[0]])
        tr, tmp = train_test_split(pool, test_size=P["val_frac"] + P["test_frac"],
                                   random_state=SEED, stratify=y[pool])
        rel = P["test_frac"] / (P["val_frac"] + P["test_frac"])
        va, te_known = train_test_split(tmp, test_size=rel, random_state=SEED,
                                        stratify=y[tmp])
        te = np.concatenate([te_known, np.where(is_zd)[0]])
        X = feats.to_numpy(dtype=np.float32)
        for nm, idx in (("train", tr), ("val", va), ("test", te)):
            np.save(os.path.join(OUT, "X_%s.npy" % nm), X[idx])
            np.save(os.path.join(OUT, "y_%s_mc.npy" % nm), y[idx])
            print("  %-6s %8d rows" % (nm, len(idx)))
        np.save(os.path.join(OUT, "zero_day_classes.npy"), np.array(sorted(zd)))
        np.save(os.path.join(OUT, "known_classes.npy"), np.array(sorted(set(y[tr]))))
        meta.update({"split_written": True, "zero_day_classes": sorted(zd),
                     "n_train": len(tr), "n_val": len(va), "n_test": len(te)})

    p = os.path.join(paths.METADATA, "preprocess_2018.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print("\nwrote %s" % p)
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())

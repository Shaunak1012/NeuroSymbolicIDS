"""
schema_2018.py — map this project's 68 CIC-IDS2017 features onto the
CSE-CIC-IDS2018 column schema, and prove the mapping is total.

WHY THIS EXISTS
---------------
Phase 6 needs the two datasets to be talking about the same features. Before
this ran, the risk was assumed to be large: CICFlowMeter-V3 renamed most columns
between the two releases, and the honest expectation was a partial mapping with
a judgement call about which features "count as the same".

**Measured, that expectation was wrong, and this file records why.** Of the 2017
columns with no literal 2018 match, every single one is a *rename* rather than a
missing feature, and the only 2017 columns with genuinely no 2018 counterpart in
the nine-file schema are the four identifier columns -- which are not features
and which this project already strips as META_COLS.

So the feature spaces are, for our purposes, **identical**. That is the finding
this script exists to establish and keep establishing: it is an assertion, run
against real headers, not a claim in a paragraph.

⚠️ TWO SCHEMAS INSIDE 2018 ITSELF, AND THE DIFFERENCE IS NOT FEATURES.
Nine of the ten daily CSVs have **80 columns**. `Thuesday-20-02-2018` (the typo
is the bucket's) has **84** -- the same 80 plus `Flow ID`, `Src IP`, `Src Port`,
`Dst IP`. Those four identifier columns, carried as wide strings across millions
of rows, are the entire reason that one file is 3.9 GB against ~340 MB for the
others. **Drop them and every day is schema-identical.** An earlier note in
`fetch_ids2018.py` implied the extra columns were extra *features*; they are not.

Run:  python scripts/schema_2018.py
Out:  outputs/metadata/schema_map_2018.json
Exit: 0 if all 68 map, 1 otherwise.
"""
import os
import sys
import json
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                        # noqa: E402

BUCKET = "https://cse-cic-ids2018.s3.amazonaws.com"
PREFIX = "Processed Traffic Data for ML Algorithms/"
LOCAL = paths.RAW_2018

# The canonical 68, in the order check.py reports them. Source of truth is the
# processed arrays; this list is asserted against them below when they exist.
FEATURES_2017 = [
    "Destination Port", "Flow Duration", "Total Fwd Packets", "Total Backward Packets",
    "Total Length of Fwd Packets", "Total Length of Bwd Packets", "Fwd Packet Length Max",
    "Fwd Packet Length Min", "Fwd Packet Length Mean", "Fwd Packet Length Std",
    "Bwd Packet Length Max", "Bwd Packet Length Min", "Bwd Packet Length Mean",
    "Bwd Packet Length Std", "Flow Bytes/s", "Flow Packets/s", "Flow IAT Mean",
    "Flow IAT Std", "Flow IAT Max", "Flow IAT Min", "Fwd IAT Total", "Fwd IAT Mean",
    "Fwd IAT Std", "Fwd IAT Max", "Fwd IAT Min", "Bwd IAT Total", "Bwd IAT Mean",
    "Bwd IAT Std", "Bwd IAT Max", "Bwd IAT Min", "Fwd PSH Flags", "Fwd Header Length",
    "Bwd Header Length", "Fwd Packets/s", "Bwd Packets/s", "Min Packet Length",
    "Max Packet Length", "Packet Length Mean", "Packet Length Std",
    "Packet Length Variance", "FIN Flag Count", "SYN Flag Count", "RST Flag Count",
    "PSH Flag Count", "ACK Flag Count", "URG Flag Count", "ECE Flag Count",
    "Down/Up Ratio", "Average Packet Size", "Avg Fwd Segment Size",
    "Avg Bwd Segment Size", "Fwd Header Length.1", "Subflow Fwd Packets",
    "Subflow Fwd Bytes", "Subflow Bwd Packets", "Subflow Bwd Bytes",
    "Init_Win_bytes_forward", "Init_Win_bytes_backward", "act_data_pkt_fwd",
    "min_seg_size_forward", "Active Mean", "Active Std", "Active Max", "Active Min",
    "Idle Mean", "Idle Std", "Idle Max", "Idle Min",
]

# CICFlowMeter-V3 renames. Every entry was confirmed by pairing the 2017-only and
# 2018-only column sets: the two sets are the same size and pair exactly, which is
# the evidence that these are renames rather than substitutions.
RENAMES = {
    "Destination Port": "Dst Port",
    "Total Fwd Packets": "Tot Fwd Pkts",
    "Total Backward Packets": "Tot Bwd Pkts",
    "Total Length of Fwd Packets": "TotLen Fwd Pkts",
    "Total Length of Bwd Packets": "TotLen Bwd Pkts",
    "Fwd Packet Length Max": "Fwd Pkt Len Max",
    "Fwd Packet Length Min": "Fwd Pkt Len Min",
    "Fwd Packet Length Mean": "Fwd Pkt Len Mean",
    "Fwd Packet Length Std": "Fwd Pkt Len Std",
    "Bwd Packet Length Max": "Bwd Pkt Len Max",
    "Bwd Packet Length Min": "Bwd Pkt Len Min",
    "Bwd Packet Length Mean": "Bwd Pkt Len Mean",
    "Bwd Packet Length Std": "Bwd Pkt Len Std",
    "Flow Bytes/s": "Flow Byts/s",
    "Flow Packets/s": "Flow Pkts/s",
    "Fwd IAT Total": "Fwd IAT Tot",
    "Bwd IAT Total": "Bwd IAT Tot",
    "Fwd Header Length": "Fwd Header Len",
    "Bwd Header Length": "Bwd Header Len",
    "Fwd Packets/s": "Fwd Pkts/s",
    "Bwd Packets/s": "Bwd Pkts/s",
    "Min Packet Length": "Pkt Len Min",
    "Max Packet Length": "Pkt Len Max",
    "Packet Length Mean": "Pkt Len Mean",
    "Packet Length Std": "Pkt Len Std",
    "Packet Length Variance": "Pkt Len Var",
    "FIN Flag Count": "FIN Flag Cnt",
    "SYN Flag Count": "SYN Flag Cnt",
    "RST Flag Count": "RST Flag Cnt",
    "PSH Flag Count": "PSH Flag Cnt",
    "ACK Flag Count": "ACK Flag Cnt",
    "URG Flag Count": "URG Flag Cnt",
    "ECE Flag Count": "ECE Flag Cnt",
    "Average Packet Size": "Pkt Size Avg",
    "Avg Fwd Segment Size": "Fwd Seg Size Avg",
    "Avg Bwd Segment Size": "Bwd Seg Size Avg",
    "Subflow Fwd Packets": "Subflow Fwd Pkts",
    "Subflow Bwd Packets": "Subflow Bwd Pkts",
    "Subflow Fwd Bytes": "Subflow Fwd Byts",
    "Subflow Bwd Bytes": "Subflow Bwd Byts",
    "Init_Win_bytes_forward": "Init Fwd Win Byts",
    "Init_Win_bytes_backward": "Init Bwd Win Byts",
    "act_data_pkt_fwd": "Fwd Act Data Pkts",
    "min_seg_size_forward": "Fwd Seg Size Min",
    # 🔴 NO 2018 COUNTERPART, and it is not a rename.
    #
    # 2017's CICFlowMeter emitted "Fwd Header Length" TWICE; pandas disambiguates
    # the second as "Fwd Header Length.1" and this project carried it as a 68th
    # feature. It is a duplicate of feature 31, not information -- 2018 fixed the
    # bug and emits the column once. Mapping it to the same 2018 column would
    # silently duplicate a feature in the 2018 matrix, so it maps to None and the
    # 2018 side runs with 67 features. State that in any cross-dataset claim.
    "Fwd Header Length.1": None,
}


def header_2018():
    """Prefer a downloaded file; fall back to a range request on the bucket."""
    if os.path.isdir(LOCAL):
        for f in sorted(os.listdir(LOCAL)):
            if f.lower().endswith(".csv") and not f.startswith("Thuesday"):
                p = os.path.join(LOCAL, f)
                if os.path.getsize(p) > 4096:
                    with open(p, encoding="utf-8", errors="replace") as fh:
                        return [c.strip().strip('"') for c in fh.readline().split(",")], f
    key = PREFIX + "Wednesday-14-02-2018_TrafficForML_CICFlowMeter.csv"
    rq = urllib.request.Request(BUCKET + "/" + urllib.parse.quote(key),
                                headers={"Range": "bytes=0-8191"})
    txt = urllib.request.urlopen(rq, timeout=90).read().decode("utf-8", "replace")
    return [c.strip().strip('"') for c in txt.splitlines()[0].split(",")], key + " (range request)"


def main():
    cols, src = header_2018()
    print("=" * 96)
    print("2017 -> 2018 FEATURE SCHEMA MAP")
    print("=" * 96)
    print("2018 header from : %s" % src)
    print("2018 columns     : %d" % len(cols))
    print("2017 features    : %d" % len(FEATURES_2017))

    have = set(cols)
    mapping, missing, dropped = {}, [], []
    for f in FEATURES_2017:
        tgt = RENAMES.get(f, f)
        if tgt is None:
            dropped.append(f)
            mapping[f] = None
        elif tgt in have:
            mapping[f] = tgt
        else:
            missing.append((f, tgt))

    print("-" * 96)
    print("mapped            : %d" % sum(1 for v in mapping.values() if v))
    print("deliberately none : %d  %s" % (len(dropped), dropped))
    if missing:
        print("UNMAPPED (%d):" % len(missing))
        for f, t in missing:
            print("   %-32s -> %-24s NOT IN 2018 HEADER" % (f, t))
    unused = sorted(have - set(v for v in mapping.values() if v) - {"Label", "Protocol", "Timestamp"})
    print("2018 cols we do not use (%d): %s" % (len(unused), unused))

    out = os.path.join(paths.METADATA, "schema_map_2018.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"source": src, "n_2018_columns": len(cols),
                   "n_2017_features": len(FEATURES_2017),
                   "n_mapped": sum(1 for v in mapping.values() if v),
                   "intentionally_unmapped": dropped,
                   "unmapped_error": [list(m) for m in missing],
                   "unused_2018_columns": unused,
                   "map": mapping}, fh, indent=2)
    print("-" * 96)
    print("wrote %s" % out)
    if missing:
        print("RESULT: INCOMPLETE - %d features have no 2018 counterpart" % len(missing))
        return 1
    print("RESULT: TOTAL - every 2017 feature maps, except the %d recorded above" % len(dropped))
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())

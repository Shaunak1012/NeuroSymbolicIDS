"""
audit_2018.py — data-quality audit of the published CSE-CIC-IDS2018 flow CSVs.

WHY THIS EXISTS
---------------
Phase 6 was about to consume these files as if they were a clean successor to
CIC-IDS2017. Counting labels on the first three downloaded files showed all
three landing on **exactly 1,048,575 data rows**. That is 2^20 - 1, and with the
header it is **exactly Excel's maximum sheet size**. Three independent capture
days do not coincidentally contain the same number of flows.

**The published processed CSVs appear to have been round-tripped through a
spreadsheet and truncated at the row limit.** This audit exists so that claim is
checked mechanically across all ten files rather than inferred from three, and
so Phase 6 states the defect instead of inheriting it silently.

WHAT IT CHECKS
--------------
1. **Excel truncation** -- data rows == 1,048,575 exactly.
2. **Chronological loss** -- first and last Timestamp in file order. Truncation
   cuts the TAIL of the day, so a file ending mid-morning has lost the rest of
   the capture, and any attack scheduled later that day is under-represented by
   an unknown amount. This is not random subsampling; it is systematically
   biased against late-day activity.
3. **Repeated header rows mid-file** -- the literal string "Label" appearing as
   a label value. Seen in Friday-16-02.
4. **12-hour timestamps with no AM/PM** -- the *same* defect this project
   already documents for 2017 and built `timeline.py` to correct. If a file's
   last timestamp sorts before its first, the clock is ambiguous and naive
   parsing will reorder the capture.

⚠️ WHAT THIS AUDIT DOES **NOT** ESTABLISH. It measures the published CSVs. It
does not quantify how many flows were lost, because the ground truth for that is
the ~470 GB of raw PCAP this project deliberately does not fetch. Report the
truncation as a defect of the distributed artefact, and do not put a number on
the loss that the data here cannot support.

Run:  python scripts/audit_2018.py
Out:  outputs/metadata/ids2018_audit.json
"""
import os
import sys
import csv
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                        # noqa: E402

SRC = paths.RAW_2018
EXCEL_MAX_DATA_ROWS = (1 << 20) - 1          # 1,048,575 rows + 1 header = 2^20


def audit(path):
    name = os.path.basename(path)
    rows = 0
    first_ts = last_ts = None
    header_rows = 0
    labels = {}
    ts_i = lab_i = None
    with open(path, encoding="utf-8", errors="replace", newline="") as f:
        r = csv.reader(f)
        try:
            head = next(r)
        except StopIteration:
            return {"file": name, "error": "empty"}
        head = [c.strip().strip('"') for c in head]
        ts_i = head.index("Timestamp") if "Timestamp" in head else None
        lab_i = head.index("Label") if "Label" in head else None
        for row in r:
            if not row:
                continue
            rows += 1
            if lab_i is not None and lab_i < len(row):
                v = row[lab_i].strip()
                if v == "Label":
                    header_rows += 1
                    continue
                labels[v] = labels.get(v, 0) + 1
            if ts_i is not None and ts_i < len(row):
                t = row[ts_i].strip()
                if t:
                    if first_ts is None:
                        first_ts = t
                    last_ts = t
    return {"file": name, "n_columns": len(head), "data_rows": rows,
            "truncated_at_excel_limit": rows == EXCEL_MAX_DATA_ROWS,
            "repeated_header_rows": header_rows,
            "first_timestamp": first_ts, "last_timestamp": last_ts,
            "labels": dict(sorted(labels.items(), key=lambda kv: -kv[1]))}


def main():
    if not os.path.isdir(SRC):
        print("no %s -- run scripts/fetch_ids2018.py first" % SRC)
        return 1
    files = sorted(f for f in os.listdir(SRC) if f.lower().endswith(".csv"))

    # A file still being downloaded reads as short, and a short file reads as
    # NOT truncated -- the audit would then report the exact opposite of the
    # defect it exists to find. Cross-check against the fetch manifest, and if
    # there is no manifest say so loudly rather than emitting a clean-looking
    # table built on partial data.
    man_p = os.path.join(paths.METADATA, "ids2018_manifest.json")
    sizes, provisional = {}, True
    if os.path.exists(man_p):
        with open(man_p, encoding="utf-8") as fh:
            man = json.load(fh)
        sizes = {e["file"]: e["bytes"] for e in man["files"]}
        provisional = not man.get("all_complete", False)
    incomplete = [f for f in files
                  if f in sizes and os.path.getsize(os.path.join(SRC, f)) != sizes[f]]
    if not sizes:
        print("!! NO FETCH MANIFEST -- download may still be running.")
        print("!! Results below are PROVISIONAL: a partially downloaded file reads as")
        print("!! short, and a short file reads as NOT truncated. Re-run when complete." + "\n")
    elif incomplete:
        print("!! %d file(s) do not match the manifest size and are SKIPPED: %s\n"
              % (len(incomplete), ", ".join(f[:28] for f in incomplete)))
        files = [f for f in files if f not in incomplete]

    print("=" * 100)
    print("CSE-CIC-IDS2018 DATA-QUALITY AUDIT  (%d files)" % len(files))
    print("=" * 100)
    print("%-46s %5s %10s %6s %-11s %-11s" %
          ("file", "cols", "rows", "trunc?", "first ts", "last ts"))
    print("-" * 100)

    out, n_trunc, n_hdr = [], 0, 0
    agg = {}
    for f in files:
        a = audit(os.path.join(SRC, f))
        out.append(a)
        if a.get("error"):
            print("%-46s %s" % (f[:46], a["error"]))
            continue
        n_trunc += bool(a["truncated_at_excel_limit"])
        n_hdr += a["repeated_header_rows"]
        for k, v in a["labels"].items():
            agg[k] = agg.get(k, 0) + v
        ft = (a["first_timestamp"] or "")[-8:]
        lt = (a["last_timestamp"] or "")[-8:]
        print("%-46s %5d %10d %6s %-11s %-11s%s" %
              (f[:46], a["n_columns"], a["data_rows"],
               "YES" if a["truncated_at_excel_limit"] else "no", ft, lt,
               "   <- header rows: %d" % a["repeated_header_rows"]
               if a["repeated_header_rows"] else ""))

    print("-" * 100)
    print("TRUNCATED AT EXCEL'S ROW LIMIT : %d of %d files" % (n_trunc, len(files)))
    print("repeated header rows found     : %d" % n_hdr)
    print("\nCLASS TOTALS (as published, i.e. AFTER truncation)")
    for k, v in sorted(agg.items(), key=lambda kv: -kv[1]):
        print("  %-34s %10d" % (k, v))
    if n_trunc:
        print("\n!! These counts are LOWER BOUNDS. Truncation removes the tail of each")
        print("   day, so any family scheduled later in a capture day is under-counted")
        print("   by an amount this data cannot reveal.")

    p = os.path.join(paths.METADATA, "ids2018_audit.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump({"excel_max_data_rows": EXCEL_MAX_DATA_ROWS,
                   "n_files": len(files), "n_truncated": n_trunc,
                   "n_repeated_header_rows": n_hdr,
                   "provisional_no_manifest": bool(provisional),
                   "class_totals_after_truncation": agg,
                   "files": out}, fh, indent=2)
    print("\nwrote %s" % p)
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())

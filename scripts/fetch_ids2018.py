"""
fetch_ids2018.py — download the CSE-CIC-IDS2018 processed flow CSVs (Phase 6).

WHY THIS EXISTS, AND WHY IT IS A SCRIPT RATHER THAN A SHELL ONE-LINER
----------------------------------------------------------------------
Phase 6 was recorded as "blocked - the data is not available to us" from the
roadmap onward, and that was **wrong**: the bucket is on the AWS Registry of
Open Data, is publicly listable over plain HTTPS, and needs no AWS account and
no AWS CLI. The claim survived unchallenged because it was a sentence rather
than a number, so nothing in this repo's checking machinery was ever pointed at
it (see CHANGELOG 2026-09-09b).

This script exists so the correction is **executable**: running it is the proof
that the data is obtainable, and the manifest below records exactly what was
fetched and how big it was.

WHAT IT DOWNLOADS
-----------------
Only `Processed Traffic Data for ML Algorithms/` -- 10 CICFlowMeter CSVs,
**6.41 GB**. The raw PCAP side of the bucket is ~470 GB and is deliberately NOT
fetched: this project's Input-modality decision (STATUS -> Open Decisions) rules
payload out of scope, and nothing in Phase 6 needs packets.

⚠️ ONE FILE IS NOT LIKE THE OTHERS. `Thuesday-20-02-2018` (the typo is in the
bucket, not here) is **3.9 GB against ~340 MB for every other day** because it
carries extra columns that the other nine do not. Whatever consumes these CSVs
must not assume a uniform schema across days -- the 2017 pipeline's assumption
that every daily file shares a header does not hold for 2018.

Resumable: a file whose local size already matches the bucket's Content-Length
is skipped, so a killed run can be relaunched without refetching.

Run:  scripts/run_long.sh fetch_ids2018.py
Out:  data/raw_2018/*.csv  +  outputs/metadata/ids2018_manifest.json
"""
import os
import sys
import json
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                        # noqa: E402

BUCKET = "https://cse-cic-ids2018.s3.amazonaws.com"
PREFIX = "Processed Traffic Data for ML Algorithms/"
DEST = paths.RAW_2018
NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"
CHUNK = 1 << 20


def listing():
    """Enumerate the processed CSVs straight off the public bucket."""
    url = BUCKET + "/?list-type=2&prefix=" + urllib.parse.quote(PREFIX)
    with urllib.request.urlopen(url, timeout=120) as r:
        root = ET.fromstring(r.read())
    out = []
    for c in root.findall(NS + "Contents"):
        key = c.find(NS + "Key").text
        size = int(c.find(NS + "Size").text)
        if key.lower().endswith(".csv") and size > 0:
            out.append((key, size))
    return sorted(out)


def fetch(key, size):
    name = os.path.basename(key)
    dst = os.path.join(DEST, name)
    if os.path.exists(dst) and os.path.getsize(dst) == size:
        print("  [skip] %-58s %8.1f MB already complete" % (name, size / 1048576))
        return dst, True
    url = BUCKET + "/" + urllib.parse.quote(key)
    t0 = time.time()
    got = 0
    with urllib.request.urlopen(url, timeout=300) as r, open(dst, "wb") as f:
        while True:
            b = r.read(CHUNK)
            if not b:
                break
            f.write(b)
            got += len(b)
            if got % (64 << 20) < CHUNK:
                print("       %-55s %6.0f / %6.0f MB"
                      % (name, got / 1048576, size / 1048576), flush=True)
    dt = time.time() - t0
    ok = os.path.getsize(dst) == size
    print("  [%s] %-58s %8.1f MB in %5.0fs (%.1f MB/s)"
          % ("ok" if ok else "SIZE MISMATCH", name, got / 1048576, dt,
             got / 1048576 / max(dt, 1e-9)))
    return dst, ok


def main():
    os.makedirs(DEST, exist_ok=True)
    print("=" * 96)
    print("CSE-CIC-IDS2018 - processed flow CSVs")
    print("=" * 96)
    files = listing()
    total = sum(s for _, s in files)
    print("%d CSVs, %.2f GB, -> %s" % (len(files), total / 1073741824, DEST))
    print("no AWS account and no AWS CLI required; bucket is public over HTTPS")
    print("-" * 96)

    man, allok = [], True
    for key, size in files:
        dst, ok = fetch(key, size)
        allok &= ok
        man.append({"key": key, "file": os.path.basename(dst),
                    "bytes": size, "complete": bool(ok)})

    out = os.path.join(paths.METADATA, "ids2018_manifest.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"bucket": BUCKET, "prefix": PREFIX, "dest": DEST,
                   "n_files": len(files), "total_bytes": total,
                   "all_complete": bool(allok), "files": man}, f, indent=2)
    print("-" * 96)
    print("wrote %s" % out)
    print("DONE" if allok else "DONE WITH ERRORS - some files incomplete")
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())

"""
preprocess_improved.py — rebuild the paper split on Engelen et al.'s CORRECTED CIC-IDS2017.

WHY THIS EXISTS, AND WHY IT IS A THREAT TO OUR CENTRAL FINDING
---------------------------------------------------------------
Engelen et al. (WTMC 2021) re-ran CIC-IDS2017 through a fixed CICFlowMeter and
relabelled it. Their fixes are not cosmetic: TCP termination now requires a
mutual FIN exchange, RST is handled, flow direction no longer flips after a
close, and several features (Idle Time, Bulk, Down/Up ratio, flow-length) are
recomputed. More than 20 % of traces are reconstructed or relabelled.

The part that lands on THIS project is the new `X - Attempted` class: attack
flows that transmitted NO PAYLOAD. Under the corrected labels our three
adequately powered zero-day families become

    family                    original    effective    attempted
    Bot                          1,966          738        1,470
    Web Attack Brute Force       1,507          151        1,214
    Web Attack XSS                 652           27          652

so roughly nine in ten web-attack flows, and two in three Bot flows, are bare
connection attempts. **Web XSS falls to 27 flows, below MIN_FAMILY_N=100, and
would leave the macro entirely.**

This bears directly on section 4, whose central claim is that Bot is
representationally unreachable. If most of what we called Bot is empty
connection attempts, part of that unreachability could be an artefact of the
labelling rather than a property of the model. That has to be measured, and it
can go against us.

🔬 IT ALSO OFFERS A DEEPER EXPLANATION OF OUR OWN ABSORPTION FINDING. We measured
that ~90 % of Web BF/XSS flows are classified `DoS slowloris`. If ~90 % of those
flows transmitted no payload, then they ARE essentially bare connection
attempts -- which is exactly what a slow-connection attack looks like. The
absorption may be a labelling consequence rather than a model quirk.

🔴 PRE-REGISTERED DESIGN DECISION, made before any model is trained
--------------------------------------------------------------------
"Attempted" flows are attack ATTEMPTS that transmitted nothing. Three readings
are defensible and the choice changes the answer, so BOTH informative arms are
built and the third is rejected with a reason:

  MERGED   (`ATTEMPTED=merge`)   `X - Attempted` -> `X`.
           Maximal comparability with the ORIGINAL labelling, so the difference
           against our existing results isolates the FLOW-CONSTRUCTION and
           FEATURE fixes from the labelling fix.
  STRICT   (`ATTEMPTED=exclude`) attempted flows dropped entirely.
           Evaluates only flows where an attack actually transmitted. This is
           the scientifically cleaner question and the harsher test.
  ❌ REJECTED: relabelling attempted flows BENIGN. They are not benign traffic,
     they are failed attacks; calling them benign would manufacture false
     positives and flatter any detector that ignores them.

🔴 PRE-REGISTERED PREDICTION
-----------------------------
Under STRICT, Web XSS (n=27) drops below the power bar and the macro is computed
over TWO families, so the headline is not comparable to 0.6399 and must not be
quoted against it -- only the per-family numbers transfer.
**Section 4 survives if effective Bot (n=738) remains at or near chance.** It is
weakened if effective Bot becomes detectable, because that would mean Bot's
unreachability was substantially an artefact of empty flows.
**Falsifier for section 4: effective-Bot PR-AUC lifting clearly above chance,
consistently across seeds.**

⚠️ 67 FEATURES, NOT 68. Like CIC-IDS2018, the corrected tool emits
`Fwd Header Length` once, so the duplicate 68th feature is absent. Compare
against the `paper_67` control arm, not the 68-feature baseline.

Run:  ATTEMPTED=merge   python scripts/preprocess_improved.py
      ATTEMPTED=exclude python scripts/preprocess_improved.py
Out:  data/processed/paper_improved_<arm>/ + outputs/metadata/preprocess_improved_<arm>.json
"""
import os
import sys
import json
import glob

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                          # noqa: E402
import config                                         # noqa: E402

SRC = paths.IMPROVED_2017
ARM = os.environ.get("ATTEMPTED", "merge").lower()
if ARM not in ("merge", "exclude"):
    sys.exit("ATTEMPTED must be 'merge' or 'exclude', got %r" % ARM)
OUT = os.path.join(paths.PROCESSED, "paper_improved_%s" % ARM)

ATTEMPTED_SUFFIX = " - Attempted"
# corrected-label -> this project's label. Only the web families differ, by the
# separator; everything else already matches and is asserted below.
LABEL_FIX = {
    "Web Attack - Brute Force": "Web Attack Brute Force",
    "Web Attack - XSS": "Web Attack XSS",
    "Web Attack - Sql Injection": "Web Attack Sql Injection",
}
# the ten columns automatic normalisation cannot match, all unambiguous
MANUAL = {
    "Destination Port": "Dst Port",
    "Min Packet Length": "Packet Length Min",
    "Max Packet Length": "Packet Length Max",
    "Avg Fwd Segment Size": "Fwd Segment Size Avg",
    "Avg Bwd Segment Size": "Bwd Segment Size Avg",
    "Init_Win_bytes_forward": "FWD Init Win Bytes",
    "Init_Win_bytes_backward": "Bwd Init Win Bytes",
    "act_data_pkt_fwd": "Fwd Act Data Pkts",
    "min_seg_size_forward": "Fwd Seg Size Min",
    # duplicate column; the fixed tool emits it once, exactly as 2018 does
    "Fwd Header Length.1": None,
}
META_COLS = ["Flow ID", "Src IP", "Src Port", "Dst IP", "Dst Port", "Protocol",
             "Timestamp"]


def our_features():
    """The 68 feature names, read from the cleaned CSV header check.py uses."""
    hdr = pd.read_csv(os.path.join(paths.PROCESSED, "features_train.csv"), nrows=0)
    return [c.strip() for c in hdr.columns]


def norm(s):
    import re
    s = re.sub(r"[^a-z0-9]", "", s.lower())
    for a, b in (("packets", "pkt"), ("packet", "pkt"), ("bytes", "byt"),
                 ("byts", "byt"), ("total", "tot"), ("backward", "bwd"),
                 ("forward", "fwd"), ("length", "len"), ("segment", "seg"),
                 ("average", "avg")):
        s = s.replace(a, b)
    return s


def build_map(new_cols):
    ni = {norm(c): c for c in new_cols}
    fwd, unmapped = {}, []
    for c in our_features():
        if c in MANUAL:
            if MANUAL[c] is None:
                unmapped.append(c)
                continue
            if MANUAL[c] not in new_cols:
                sys.exit("manual mapping %r -> %r missing from the corrected CSVs"
                         % (c, MANUAL[c]))
            fwd[c] = MANUAL[c]
            continue
        k = norm(c)
        if k in ni:
            fwd[c] = ni[k]
        else:
            sys.exit("no mapping for 2017 feature %r" % c)
    return fwd, unmapped


def main():
    cfg = config.get()
    P = cfg["protocol"]
    SEED = cfg["seed"]
    ZERO_DAY = set(cfg["zero_day_classes"])
    KNOWN_ATK = set(cfg["known_attacks"])

    files = sorted(glob.glob(os.path.join(SRC, "*.csv")))
    if not files:
        sys.exit("no corrected CSVs in %s" % SRC)

    print("=" * 96)
    print("CORRECTED CIC-IDS2017 (Engelen et al.) - arm: %s" % ARM.upper())
    print("=" * 96)

    hdr = [c.strip() for c in pd.read_csv(files[0], nrows=0).columns]
    fwd, unmapped = build_map(hdr)
    print("features: %d mapped, %d intentionally unmapped %s"
          % (len(fwd), len(unmapped), unmapped))

    frames, metas, stats = [], [], []
    for f in files:
        d = pd.read_csv(f, low_memory=False)
        d.columns = d.columns.str.strip()
        n_raw = len(d)
        lab = d["Label"].astype(str).str.strip()
        keep = d[list(fwd.values())].copy()
        keep.columns = list(fwd.keys())
        meta = d[[c for c in META_COLS if c in d.columns]].copy()
        keep["Label"] = lab.values
        frames.append(keep)
        metas.append(meta)
        stats.append({"file": os.path.basename(f), "rows": n_raw})
        print("  %-30s %8d rows" % (os.path.basename(f)[:30], n_raw))

    df = pd.concat(frames, ignore_index=True)
    meta_all = pd.concat(metas, ignore_index=True)
    del frames, metas

    # ---- the Attempted arm --------------------------------------------------
    lab = df["Label"]
    att = lab.str.endswith(ATTEMPTED_SUFFIX)
    n_att = int(att.sum())
    if ARM == "merge":
        df["Label"] = lab.str.replace(ATTEMPTED_SUFFIX, "", regex=False)
        print("\n[MERGE] %d attempted flows folded into their attack class" % n_att)
    else:
        df = df[~att].reset_index(drop=True)
        meta_all = meta_all[~att.values].reset_index(drop=True)
        print("\n[EXCLUDE] %d attempted flows dropped" % n_att)

    df["Label"] = df["Label"].replace(LABEL_FIX)
    seen = set(df["Label"].unique())
    expected = {"BENIGN"} | KNOWN_ATK | ZERO_DAY
    unknown = seen - expected
    if unknown:
        sys.exit("unrecognised labels after normalisation: %s" % sorted(unknown))

    # ---- clean, exactly as preprocess.py does -------------------------------
    y = df.pop("Label").values
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    ok = df.notna().all(axis=1).values
    dropped = int((~ok).sum())
    df = df[ok].reset_index(drop=True)
    y = y[ok]
    meta_all = meta_all[ok].reset_index(drop=True)
    print("dropped %d inf/nan rows" % dropped)

    const = [c for c in df.columns if df[c].nunique() <= 1]
    if const:
        print("dropping %d constant columns: %s" % (len(const), const))
        df = df.drop(columns=const)
    X = df.to_numpy(dtype=np.float32)
    print("feature matrix: %s" % (X.shape,))

    # ---- the paper split, same protocol and seed ----------------------------
    kind = np.where(y == "BENIGN", "benign",
                    np.where(np.isin(y, list(ZERO_DAY)), "zero_day", "known"))
    is_ben, is_known, is_zd = kind == "benign", kind == "known", kind == "zero_day"
    n_known_atk = int(is_known.sum())
    n_keep = min(int(round(P["benign_ratio"] * n_known_atk)), int(is_ben.sum()))
    ben_keep = np.random.RandomState(SEED).choice(
        np.flatnonzero(is_ben), size=n_keep, replace=False)
    print("\nknown-attack flows %d | benign kept %d (of %d)"
          % (n_known_atk, n_keep, int(is_ben.sum())))

    pool = np.concatenate([ben_keep, np.flatnonzero(is_known)])
    tr, tmp = train_test_split(pool, test_size=P["val_frac"] + P["test_frac"],
                               random_state=SEED, stratify=y[pool])
    rel = P["test_frac"] / (P["val_frac"] + P["test_frac"])
    va, te_k = train_test_split(tmp, test_size=rel, random_state=SEED,
                                stratify=y[tmp])
    te = np.concatenate([te_k, np.flatnonzero(is_zd)])

    os.makedirs(OUT, exist_ok=True)
    for nm, idx in (("train", tr), ("val", va), ("test", te)):
        np.save(os.path.join(OUT, "X_%s.npy" % nm), X[idx])
        np.save(os.path.join(OUT, "y_%s_mc.npy" % nm), y[idx].astype(object))
        np.save(os.path.join(OUT, "y_%s_bin.npy" % nm),
                (y[idx] != "BENIGN").astype(int))
        # meta travels with the split -- the exogenous-axiom experiment needs
        # Src/Dst IP, which are NOT among the 67 features.
        meta_all.iloc[idx].to_csv(os.path.join(OUT, "meta_%s.csv" % nm),
                                  index=False)
        print("%-6s %s" % (nm, X[idx].shape))
    np.save(os.path.join(OUT, "known_classes.npy"),
            np.array(sorted(set(y[tr].tolist())), dtype=object))
    np.save(os.path.join(OUT, "zero_day_classes.npy"),
            np.array(sorted(ZERO_DAY), dtype=object))

    import collections
    fam = collections.Counter(y[te].tolist())
    print("\nTEST zero-day families (power bar = 100):")
    for f in sorted(ZERO_DAY):
        n = fam.get(f, 0)
        print("  %-30s %6d %s" % (f, n, "" if n >= 100 else "<- UNDERPOWERED"))

    rec = {"arm": ARM, "source": "Engelen et al. WTMC 2021 corrected CIC-IDS2017",
           "n_features": int(X.shape[1]), "unmapped_features": unmapped,
           "constant_columns_dropped": const, "attempted_flows": n_att,
           "inf_nan_rows_dropped": dropped, "per_file": stats,
           "split": {"train": int(len(tr)), "val": int(len(va)),
                     "test": int(len(te))},
           "test_family_counts": {k: int(v) for k, v in fam.items()},
           "powered_families": sorted(f for f in ZERO_DAY if fam.get(f, 0) >= 100),
           "caveats": [
               "67 features, not 68 - the fixed tool emits Fwd Header Length "
               "once. Compare against the paper_67 control, not the 68-feature "
               "baseline.",
               "Under STRICT the macro is over a DIFFERENT family set, so its "
               "value is not comparable to 0.6399; only per-family numbers "
               "transfer.",
               "Flow construction and several feature calculations changed, so "
               "this is not a relabelling of our flows - the flows themselves "
               "differ and no 1:1 correspondence exists.",
           ]}
    p = os.path.join(paths.METADATA, "preprocess_improved_%s.json" % ARM)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=2)
    print("\nwrote %s" % p)
    print("wrote %s" % OUT)
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())

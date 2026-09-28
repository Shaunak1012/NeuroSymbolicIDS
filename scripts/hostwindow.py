"""
hostwindow.py — a HOST-WINDOW view, and the exogeneity test that decides whether it is real.

WHY THIS EXISTS
---------------
`exogenous_predicate.py` tested host-ROLE knowledge (does this host serve this port,
how many destinations does this source contact, how persistent is this pair) and the
premise failed: gradient boosting predicts every one of those predicates from the 68
flow features at AUC 0.990/0.994 and R2 0.949/0.914, and nearly as well with
`Destination Port` removed. In a testbed where each host runs one scripted role, a
flow's characteristics nearly identify its host, and with it the host's aggregates.

Those predicates were computed over the WHOLE capture per host -- a static role
profile. The proposed architecture asks a different question: what has this source
done in the last 60 and 600 SECONDS. That is not the same quantity. A static role
("this host is a web server") is a property the flow's own features can encode; a
short-horizon burst or a persistent trickle is a property of the arrival process,
which no single flow's feature vector contains. Bot's real signature is persistence,
so a 600 s window is where it should appear if it appears anywhere.

The premise can fail here exactly as it failed there, and this script is built to
find that out BEFORE anything is injected or fused. That is the whole point:

  low R2 / AUC near 0.5  = genuinely outside the learned feature basis
  high                   = we re-derived a feature, and any downstream gain would be
                           feature engineering wearing a logical costume

TWO PROPERTIES THIS BUILD HAS TO HAVE, AND WHY
----------------------------------------------
1. CAUSAL. Every window aggregate uses flows that arrived STRICTLY BEFORE the flow
   being described. Aggregating over the whole capture would be transductive -- a
   test flow's score would depend on flows that had not happened yet -- which is the
   defect already disclosed for rank fusion in the paper's section 8, and the one
   `kg.py` handles by streaming windows in true chronological order.
2. COMPUTED ON THE FULL CAPTURE, NOT ON THE SPLIT. The paper split under-samples
   benign traffic 4.11-fold, so counting a host's flows inside the split would
   measure the sampling, not the host. The stream is therefore built from
   `data/processed/meta_{train,test}.csv` (every flow of the 5-day capture) and the
   paper-split rows read their values out of it by (source, time). Using training
   flows that precede a test flow is not leakage: it is what a deployed sensor sees.

TIMESTAMPS GO THROUGH `timeline.py` (non-negotiable #8). The raw strings are wrong
twice -- D/M/YYYY dates and a 12-hour clock with no AM/PM -- and naive parsing
reorders all 114,658 test rows, which would silently destroy every window here.

Run:  python scripts/hostwindow.py              # build + exogeneity test
      python scripts/hostwindow.py --build      # build the view only
      python scripts/hostwindow.py --exo        # exogeneity test only (view must exist)
Out:  data/processed/paper/hostwin_{train,val,test}.npy
      outputs/metadata/hostwindow.json
"""
import os
import sys
import json
from collections import Counter

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                          # noqa: E402
import config                                         # noqa: E402
import features as featmod                            # noqa: E402
import timeline                                       # noqa: E402
import tracking                                       # noqa: E402

WINDOWS = (60, 600)            # seconds
MIN_GAPS_FOR_CV = 3            # fewer arrivals than this cannot describe regularity

# Eight features. The log1p counts are heavy-tailed (a DoS source contributes tens of
# thousands of flows a minute); `PairFlows600` is persistence to one destination, and
# `GapCV600` is how regular the arrivals are -- the beaconing shape, at the 1-second
# resolution the capture actually has.
NAMES = ["Flows60", "Dsts60", "Ports60",
         "Flows600", "Dsts600", "Ports600",
         "PairFlows600", "GapCV600"]


def full_capture_stream():
    """Every flow of the capture, in true chronological order."""
    frames = []
    for half in ("train", "test"):
        p = os.path.join(paths.PROCESSED, "meta_%s.csv" % half)
        if not os.path.exists(p):
            sys.exit("missing %s -- run preprocess.py first" % p)
        d = pd.read_csv(p, low_memory=False,
                        usecols=["Source IP", "Destination IP",
                                 "Destination Port", "Timestamp"])
        d.columns = [c.strip() for c in d.columns]
        frames.append(d)
        print("  %-6s %9d flows" % (half, len(d)))
    d = pd.concat(frames, ignore_index=True)
    t = timeline.parse(d["Timestamp"])          # non-negotiable #8
    d = d.drop(columns=["Timestamp"])
    d["ts"] = (t.values.astype("datetime64[s]").astype(np.int64))
    d = d.sort_values("ts", kind="stable").reset_index(drop=True)
    print("  total  %9d flows, %s -> %s"
          % (len(d), t.min(), t.max()))
    return d


def per_source_windows(stream):
    """Causal window aggregates at EVERY flow of the capture, grouped by source.

    Returns {source: (ts_array, feature_matrix)} where row i of the matrix describes
    the window ENDING AT, AND EXCLUDING, event i -- so it is exactly what was
    knowable when event i arrived.
    """
    src = stream["Source IP"].astype(str).values
    dst = stream["Destination IP"].astype(str).values
    port = stream["Destination Port"].fillna(-1).astype(np.int64).values
    ts = stream["ts"].values

    order = np.argsort(src, kind="stable")      # group by source, time order kept
    out = {}
    i = 0
    while i < len(order):
        j = i
        s = src[order[i]]
        while j < len(order) and src[order[j]] == s:
            j += 1
        idx = order[i:j]
        out[s] = _one_source(ts[idx], dst[idx], port[idx])
        i = j
    return out


def _one_source(ts, dst, port):
    """Two-pointer sweep over one source's arrivals: O(m) per window, not O(m*w)."""
    m = len(ts)
    feat = np.zeros((m, len(NAMES)), dtype=np.float32)
    state = []
    for w in WINDOWS:
        state.append({"start": 0, "dsts": Counter(), "ports": Counter(),
                      "gap_sum": 0.0, "gap_sqsum": 0.0, "n_gaps": 0, "w": w})
    for i in range(m):
        for k, st in enumerate(state):
            # admit event i-1 (everything strictly before i is in scope now)
            if i > 0:
                st["dsts"][dst[i - 1]] += 1
                st["ports"][port[i - 1]] += 1
                if i > 1:
                    g = float(ts[i - 1] - ts[i - 2])
                    st["gap_sum"] += g
                    st["gap_sqsum"] += g * g
                    st["n_gaps"] += 1
            # evict everything older than the window, anchored at ts[i]
            lo = ts[i] - st["w"]
            while st["start"] < i and ts[st["start"]] < lo:
                d0, p0 = dst[st["start"]], port[st["start"]]
                st["dsts"][d0] -= 1
                if st["dsts"][d0] == 0:
                    del st["dsts"][d0]
                st["ports"][p0] -= 1
                if st["ports"][p0] == 0:
                    del st["ports"][p0]
                if st["start"] > 0 and st["n_gaps"] > 0:
                    g = float(ts[st["start"]] - ts[st["start"] - 1])
                    st["gap_sum"] -= g
                    st["gap_sqsum"] -= g * g
                    st["n_gaps"] -= 1
                st["start"] += 1
            n = i - st["start"]
            base = 0 if k == 0 else 3
            feat[i, base + 0] = np.log1p(n)
            feat[i, base + 1] = np.log1p(len(st["dsts"]))
            feat[i, base + 2] = np.log1p(len(st["ports"]))
            if k == 1:      # the 600 s window carries persistence and regularity
                feat[i, 6] = np.log1p(st["dsts"].get(dst[i], 0))
                ng = st["n_gaps"]
                if ng >= MIN_GAPS_FOR_CV:
                    mean = st["gap_sum"] / ng
                    var = max(st["gap_sqsum"] / ng - mean * mean, 0.0)
                    feat[i, 7] = float(np.sqrt(var) / mean) if mean > 0 else 0.0
    return ts, feat


def query(per_source, meta_src, stamps):
    """Read each paper-split row's window values out of the full-capture stream.

    The row IS one of those flows, so `searchsorted(..., 'left')` lands on the first
    arrival of that source at that second, whose precomputed window covers exactly
    [t - w, t). Rows whose (source, second) is not in the stream are reported, not
    silently defaulted.
    """
    n = len(meta_src)
    out = np.zeros((n, len(NAMES)), dtype=np.float32)
    miss = 0
    for r in range(n):
        got = per_source.get(meta_src[r])
        if got is None:
            miss += 1
            continue
        ts_s, feat = got
        k = int(np.searchsorted(ts_s, stamps[r], side="left"))
        if k >= len(ts_s) or ts_s[k] != stamps[r]:
            miss += 1
            continue
        out[r] = feat[k]
    return out, miss


def build():
    P = paths.PAPER
    print("=" * 100)
    print("BUILDING THE HOST-WINDOW VIEW (causal, full capture, %s s)" % (WINDOWS,))
    print("=" * 100)
    stream = full_capture_stream()
    print("\nsweeping per source ...")
    per_source = per_source_windows(stream)
    print("  %d distinct sources" % len(per_source))

    report = {}
    for split in ("train", "val", "test"):
        meta = pd.read_csv(os.path.join(P, "meta_%s.csv" % split),
                           low_memory=False, usecols=["Source IP"])
        meta.columns = [c.strip() for c in meta.columns]
        stamps = np.load(os.path.join(P, "timestamp_%s.npy" % split),
                         allow_pickle=True)
        stamps = pd.to_datetime(pd.Series(stamps)).values.astype(
            "datetime64[s]").astype(np.int64)
        X, miss = query(per_source, meta["Source IP"].astype(str).values, stamps)
        np.save(os.path.join(P, "hostwin_%s.npy" % split), X)
        rate = 1.0 - miss / float(len(X))
        report[split] = {"n": int(len(X)), "matched": float(rate),
                         "mean": {NAMES[j]: float(X[:, j].mean())
                                  for j in range(len(NAMES))}}
        print("  %-5s %7d rows, matched %.4f" % (split, len(X), rate))
        if rate < 0.99:
            sys.exit("only %.3f of %s rows matched the capture stream -- stop and "
                     "check the join before trusting these features" % (rate, split))
    return report


def exogeneity():
    """The premise test. Same estimator, ablation and thresholds as
    exogenous_predicate.py, so the two tables can be read side by side."""
    from sklearn.ensemble import HistGradientBoostingRegressor as HGBR
    from sklearn.metrics import r2_score

    cfg = config.get()
    P = paths.PAPER
    tfm = cfg["protocol"]["feature_transform"]
    Xtr = featmod.transform(np.load(os.path.join(P, "X_train.npy")), tfm)
    Xte = featmod.transform(np.load(os.path.join(P, "X_test.npy")), tfm)
    Wtr = np.load(os.path.join(P, "hostwin_train.npy"))
    Wte = np.load(os.path.join(P, "hostwin_test.npy"))

    rng = np.random.RandomState(cfg["seed"])
    itr = rng.choice(len(Xtr), min(200000, len(Xtr)), replace=False)
    cols_nodp = [c for c in range(Xtr.shape[1]) if c != 0]      # 0 = Destination Port

    print("\n" + "=" * 100)
    print("EXOGENEITY - can the 68 flow features already predict the window view?")
    print("=" * 100)
    print("low R2 = genuinely outside the basis; high = re-derived from the features")
    print("(the static host-role predicates scored R2 0.949 / 0.914 and failed this)\n")

    res = {}
    for j, name in enumerate(NAMES):
        ytr, yte = Wtr[itr, j], Wte[:, j]
        if np.unique(ytr).size < 2 or np.unique(yte).size < 2:
            res[name] = {"status": "degenerate"}
            print("  %-14s degenerate (constant)" % name)
            continue
        row = {}
        for tag, cols in (("all_features", None), ("no_dest_port", cols_nodp)):
            A = Xtr[itr] if cols is None else Xtr[itr][:, cols]
            B = Xte if cols is None else Xte[:, cols]
            m = HGBR(max_iter=120, random_state=cfg["seed"]).fit(A, ytr)
            row[tag] = float(r2_score(yte, m.predict(B)))
        row["exogenous"] = bool(row["no_dest_port"] < 0.5)
        res[name] = row
        print("  %-14s R2 all %6.3f | without Dst Port %6.3f   %s"
              % (name, row["all_features"], row["no_dest_port"],
                 "EXOGENOUS" if row["exogenous"] else "<- already in the features"))

    n_exo = sum(1 for v in res.values() if v.get("exogenous"))
    print("\n  %d of %d window features are outside the feature basis" % (n_exo, len(res)))
    if n_exo == 0:
        print("  => THE PREMISE FAILS AGAIN. The window view is a function of the "
              "flow features, so fusing it would be feature engineering, not a "
              "second view. Do not build the rest.")
    else:
        print("  => %d feature(s) survive. Next question, and it is a separate one: "
              "do they REACH the zero-day families (hostwindow_detect.py)?" % n_exo)
    return res


if __name__ == "__main__":
    do_build = "--exo" not in sys.argv
    do_exo = "--build" not in sys.argv
    out = {"windows": list(WINDOWS), "names": NAMES}
    if do_build:
        out["view"] = build()
    if do_exo:
        out["exogeneity"] = exogeneity()
    p = os.path.join(paths.METADATA, "hostwindow.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("\nwrote %s" % p)
    if "exogeneity" in out:
        ok = {k: v for k, v in out["exogeneity"].items() if "no_dest_port" in v}
        tracking.log_run("hostwindow", {"windows": list(WINDOWS)},
                         {"n_exogenous": sum(1 for v in ok.values() if v["exogenous"]),
                          "min_r2_no_dport": min(v["no_dest_port"] for v in ok.values()),
                          "max_r2_no_dport": max(v["no_dest_port"] for v in ok.values())})

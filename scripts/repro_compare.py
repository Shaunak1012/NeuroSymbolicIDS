"""
repro_compare.py — does a from-scratch run reproduce the canonical artifacts?

WHY THIS EXISTS (audit item 7.4, 2026-09-17)
--------------------------------------------
`run_all.py --run` with NSIDS_WORKDIR rebuilds the pipeline into a sandbox from the
raw CSVs. "It reproduces the canonical results" is then a claim about files, and
it was first checked by hand with `cmp`. This script makes the check a record.

For every artifact the sandbox wrote, it finds the canonical file that SHOULD be
identical, if there is one, and compares them:

  * processed data and the split             same relative path
  * the seed-s CNN (cnn_paper[_s43|_s44])   the deterministic run c4_log1p_s<s>
    -- predictions, embeddings, history      (same code, same seed; the canonical
                                             cnn_paper* files are PRE-flag and are
                                             a different population by construction)
  * the seed-s autoencoder                   the deterministic run ae_det_s<s>
  * classical baselines, KG, tuned baselines same name (deterministic given seed)
  * CNN log-odds                             c4_log1p_s<s>_logodds

Everything else (novelty and LTN scores, which the canonical tree holds only for
pre-flag models; derived JSON records) is listed as `no_counterpart` rather than
compared, because a difference there says nothing about reproducibility.
Pickled histories are compared by content, arrays byte-for-byte, and a byte
mismatch in a .npy is followed by a numeric comparison so a float-level
difference is reported as such.

Run:  python scripts/repro_compare.py outputs/sandbox_e2e2
Out:  outputs/metadata/repro_compare_<sandbox name>.json
"""
import os
import sys
import json
import pickle
import hashlib

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                        # noqa: E402

SEEDS = (42, 43, 44)


def sfx(s):
    return "" if s == 42 else "_s%d" % s


def rename(name):
    """Canonical counterpart of a sandbox file name, or None."""
    for s in SEEDS:
        for a, b in ((f"cnn_paper{sfx(s)}", f"c4_log1p_s{s}"),
                     (f"autoencoder_paper{sfx(s)}", f"ae_det_s{s}")):
            for pat in ("y_prob_%s_test.npy", "y_prob_%s_logodds_test.npy",
                        "X_train_%s_emb.npy", "X_val_%s_emb.npy", "X_test_%s_emb.npy",
                        "%s_history.pkl"):
                if name == pat % a:
                    return pat % b
    same = ["y_prob_%s%s_test.npy" % (m, sfx(s)) for s in SEEDS
            for m in ("xgboost", "random_forest", "isolation_forest", "kg")]
    same += ["y_prob_kg%s_causal_test.npy" % sfx(s) for s in SEEDS]
    same += ["y_prob_xgboost_tuned_test.npy"]
    same += ["y_prob_%s_tuned_s%d_test.npy" % (m, s) for s in SEEDS
             for m in ("random_forest", "isolation_forest")]
    same += ["behaviour_thresholds.npy"]
    return name if name in same else None


def digest(p):
    h = hashlib.blake2b(digest_size=16)
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


def compare(a, b):
    if digest(a) == digest(b):
        return "identical", None
    if a.endswith(".pkl"):
        with open(a, "rb") as f:
            x = pickle.load(f)
        with open(b, "rb") as f:
            y = pickle.load(f)
        return ("identical_content" if x == y else "different"), None
    if a.endswith(".npy"):
        x, y = np.load(a, allow_pickle=True), np.load(b, allow_pickle=True)
        if x.dtype == object or y.dtype == object:
            # behaviour_thresholds.npy is a pickled dict of (low, high) tuples
            xo, yo = x.item() if x.shape == () else None, y.item() if y.shape == () else None
            if isinstance(xo, dict) and isinstance(yo, dict) and xo.keys() == yo.keys():
                xv = np.array([v for k in sorted(xo) for v in np.ravel(xo[k])], dtype=np.float64)
                yv = np.array([v for k in sorted(yo) for v in np.ravel(yo[k])], dtype=np.float64)
                rel = float(np.max(np.abs(xv - yv) / np.maximum(1.0, np.abs(yv))))
                return ("float_level" if rel < 1e-9 else "different"), "max rel diff %.3g" % rel
            return "different", "object array"
        if x.shape != y.shape:
            return "different", "shape %s vs %s" % (x.shape, y.shape)
        d = float(np.max(np.abs(x.astype(np.float64) - y.astype(np.float64))))
        return ("float_level" if d < 1e-9 * max(1.0, float(np.max(np.abs(y)))) else "different"), \
            "max abs diff %.3g" % d
    return "different", None


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: repro_compare.py <sandbox dir>")
    sb = os.path.abspath(sys.argv[1])
    root = os.path.abspath(paths.ROOT)
    groups = [(os.path.join(sb, "data", "processed"), paths.PROCESSED, True),
              (os.path.join(sb, "outputs", "predictions"), paths.PREDICTIONS, False),
              (os.path.join(sb, "outputs", "embeddings"), paths.EMBEDDINGS, False),
              (os.path.join(sb, "outputs", "metadata"), paths.METADATA, False)]
    rows, summary = [], {}
    for sdir, cdir, same_path in groups:
        for dp, _, files in os.walk(sdir):
            if "_smoke_archive" in dp or "_legacy_temporal" in dp:
                continue
            for fn in sorted(files):
                a = os.path.join(dp, fn)
                rel = os.path.relpath(a, sdir)
                target = rel if same_path else rename(fn)
                if target is None:
                    verdict, note, b = "no_counterpart", None, None
                else:
                    b = os.path.join(cdir, os.path.dirname(rel) if same_path else "",
                                     os.path.basename(target))
                    if not os.path.exists(b):
                        verdict, note = "canonical_missing", None
                    else:
                        verdict, note = compare(a, b)
                rows.append({"sandbox": os.path.relpath(a, sb).replace(os.sep, "/"),
                             "canonical": os.path.relpath(b, root).replace(os.sep, "/") if b else None,
                             "verdict": verdict, "note": note})
                summary[verdict] = summary.get(verdict, 0) + 1
    print("%-62s %-18s %s" % ("sandbox file", "verdict", "canonical / note"))
    for r in rows:
        if r["verdict"] != "no_counterpart":
            print("%-62s %-18s %s%s" % (r["sandbox"][-62:], r["verdict"], r["canonical"] or "",
                                       ("  (" + r["note"] + ")") if r["note"] else ""))
    print("summary:", summary)
    out = {"sandbox": os.path.relpath(sb, root).replace(os.sep, "/"), "summary": summary, "files": rows}
    p = os.path.join(paths.METADATA, "repro_compare_%s.json" % os.path.basename(sb.rstrip("/\\")))
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print("wrote %s" % p)
    bad = summary.get("different", 0)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

"""
Standard evaluation suite — every experiment reports the same views so the ablation
table is consistent and the *easy* overall number can never masquerade as the result.

Primary metric = PR-AUC (data is imbalanced; accuracy is misleading).

HEADLINE = **per-family** zero-day PR-AUC + the macro-average over adequately
powered families. The blended "benign vs all 6 unknowns" number is reported as a
SECONDARY view only: it is a size-weighted mixture of families with wildly
different detectability (measured 2026-07-27: Web attacks ~0.93, Bot ~chance), so
it moves for reasons that have nothing to do with detection quality and must not
be used as an optimisation target on its own.

Two guards exist because both failure modes were observed in real runs:
  * `underpowered` — families with n < MIN_FAMILY_N (Heartbleed n=11, Infiltration
    n=36, SQL Injection n=21) are excluded from the macro-average and flagged.
    Reporting them to 4 dp implies a precision that does not exist.
  * `saturated` — a float32 softmax can collapse `1 - p(benign)` to exactly 0 for
    ~99% of benign flows, which makes the fixed-FPR threshold degenerate (it lands
    inside a tie block, flags everything, and yields the algebraic "predict-all"
    F1 rather than a model property). `achieved_fpr` and `score_resolution` expose
    this; prefer log-odds scores (see `to_logodds`) over raw probabilities.

    import metrics
    r = metrics.evaluate(y_mc, scores, zero_day_classes, fpr=0.01)
    metrics.print_report(r)
"""
import numpy as np
from sklearn.metrics import (average_precision_score, roc_auc_score,
                             f1_score, precision_score, recall_score)

# Families with fewer than this many test flows are statistically underpowered:
# excluded from the macro-average, reported with a warning.
MIN_FAMILY_N = 100


def to_logodds(p_attack, eps=1e-12):
    """Convert an attack probability to log-odds.

    A float32 softmax saturates: `1 - p(benign)` underflows to exactly 0.0 for the
    bulk of benign flows, destroying the ranking resolution that PR-AUC and the
    fixed-FPR threshold both depend on. Log-odds preserves separation across many
    orders of magnitude. Use this on any score derived from a softmax before
    passing it to `evaluate`.
    """
    p = np.clip(np.asarray(p_attack, dtype=np.float64), eps, 1.0 - eps)
    return np.log(p) - np.log1p(-p)


def _binary(y_mc, scores, mask, thr):
    """Binary metrics on the subset selected by `mask`, at decision threshold `thr`."""
    yb = (y_mc[mask] != "BENIGN").astype(int)
    s = scores[mask]
    if yb.min() == yb.max():                      # only one class present
        return {"n": int(mask.sum()), "prevalence": float(yb.mean()),
                "pr_auc": None, "roc_auc": None, "f1": None}
    pred = (s >= thr).astype(int)
    return {
        "n": int(mask.sum()),
        "prevalence": float(yb.mean()),
        "pr_auc": float(average_precision_score(yb, s)),
        "roc_auc": float(roc_auc_score(yb, s)),
        "f1": float(f1_score(yb, pred, zero_division=0)),
        "precision": float(precision_score(yb, pred, zero_division=0)),
        "recall": float(recall_score(yb, pred, zero_division=0)),
    }


def evaluate(y_mc, scores, zero_day_classes, fpr=0.01):
    """Full suite. Returns a nested dict of views + per-family zero-day breakdown."""
    y_mc = np.asarray(y_mc)
    scores = np.asarray(scores, dtype=float)
    zd = set(zero_day_classes)
    is_benign = y_mc == "BENIGN"
    is_zd = np.isin(y_mc, list(zd))
    is_known = ~is_benign & ~is_zd

    # operating threshold set on benign to hit the target FPR
    thr = float(np.quantile(scores[is_benign], 1.0 - fpr)) if is_benign.any() else 0.5

    out = {"fpr_target": fpr, "threshold": thr, "views": {}}
    out["views"]["known_only"]   = _binary(y_mc, scores, is_benign | is_known, thr)
    out["views"]["all"]          = _binary(y_mc, scores, np.ones(len(y_mc), bool), thr)
    out["views"]["zeroday_only"] = _binary(y_mc, scores, is_benign | is_zd, thr)  # SECONDARY

    # ---- score-health diagnostics -------------------------------------------------
    # If the threshold lands inside a tie block, `achieved_fpr` overshoots the target
    # and every metric at that operating point is an artefact, not a measurement.
    achieved = float((scores[is_benign] >= thr).mean()) if is_benign.any() else float("nan")
    _, counts = np.unique(scores, return_counts=True)
    out["diagnostics"] = {
        "achieved_fpr": achieved,
        "score_resolution": float(len(counts) / len(scores)),   # 1.0 = all distinct
        "largest_tie_frac": float(counts.max() / len(scores)),
        "saturated": bool(achieved > 2 * fpr or counts.max() / len(scores) > 0.5),
    }

    # ---- per-family zero-day detection (HEADLINE) ---------------------------------
    # Each family is scored against the benign set alone, so `prevalence` is that
    # family's chance PR-AUC and `lift` says how far above chance the model is.
    fam = {}
    for c in sorted(zd):
        m = y_mc == c
        if not m.any():
            continue
        sub = is_benign | m
        yb = (y_mc[sub] != "BENIGN").astype(int)
        s = scores[sub]
        chance = float(yb.mean())
        pr = float(average_precision_score(yb, s))
        fam[c] = {
            "n": int(m.sum()),
            "chance_pr_auc": chance,
            "pr_auc": pr,
            "lift": float(pr / chance) if chance > 0 else float("nan"),
            "roc_auc": float(roc_auc_score(yb, s)),
            "recall": float((scores[m] >= thr).mean()),
            "underpowered": bool(m.sum() < MIN_FAMILY_N),
        }
    out["zeroday_family"] = fam
    # backwards-compatible alias — older callers read this key
    out["zeroday_family_recall"] = {c: {"n": f["n"], "recall": f["recall"]}
                                    for c, f in fam.items()}

    powered = [f for f in fam.values() if not f["underpowered"]]
    out["macro"] = {
        "n_families": len(powered),
        "pr_auc": float(np.mean([f["pr_auc"] for f in powered])) if powered else None,
        "lift": float(np.mean([f["lift"] for f in powered])) if powered else None,
        "excluded": sorted(c for c, f in fam.items() if f["underpowered"]),
    }
    return out


def flatten(r, prefix=""):
    """Flat dict for tracking.log_run — headline metrics first."""
    z = r["views"]["zeroday_only"]; a = r["views"]["all"]; m = r.get("macro", {})
    d = {
        f"{prefix}macro_zd_pr_auc": m.get("pr_auc"),      # HEADLINE
        f"{prefix}macro_zd_lift": m.get("lift"),
        f"{prefix}zd_pr_auc": z["pr_auc"],                # secondary (size-weighted blend)
        f"{prefix}zd_roc_auc": z["roc_auc"], f"{prefix}zd_f1": z["f1"],
        f"{prefix}all_pr_auc": a["pr_auc"],
        f"{prefix}saturated": r.get("diagnostics", {}).get("saturated"),
    }
    for c, f in r.get("zeroday_family", {}).items():
        key = c.lower().replace(" ", "_")
        d[f"{prefix}fam_{key}_pr_auc"] = f["pr_auc"]
    return d


def print_report(r):
    d = r.get("diagnostics", {})
    if d.get("saturated"):
        print(f"\n  !! SCORE SATURATION — achieved FPR {d['achieved_fpr']:.3f} vs target "
              f"{r['fpr_target']:.3f}; largest tie block {d['largest_tie_frac']:.1%} of rows.")
        print("     Threshold metrics below are artefacts. Re-score in log-odds "
              "(metrics.to_logodds) before comparing models.")

    m = r.get("macro", {})
    if m.get("pr_auc") is not None:
        print(f"\n  HEADLINE  macro zero-day PR-AUC = {m['pr_auc']:.4f} "
              f"({m['lift']:.1f}x chance, {m['n_families']} powered families)")
        if m["excluded"]:
            print(f"            excluded as underpowered (n<{MIN_FAMILY_N}): "
                  f"{', '.join(m['excluded'])}")

    print(f"\n  per-family zero-day detection @ {r['fpr_target']:.0%} FPR "
          f"(thr={r['threshold']:.4g}):")
    print(f"    {'family':30s} {'n':>6s} {'PR-AUC':>8s} {'chance':>8s} {'lift':>6s} {'recall':>7s}")
    for c, f in r.get("zeroday_family", {}).items():
        note = "  <- underpowered" if f["underpowered"] else ""
        print(f"    {c:30s} {f['n']:>6,} {f['pr_auc']:>8.4f} {f['chance_pr_auc']:>8.4f} "
              f"{f['lift']:>6.1f} {f['recall']:>7.4f}{note}")

    print(f"\n  {'view (secondary)':16s} {'n':>9s} {'prev':>6s} {'PR-AUC':>8s} {'ROC':>7s} {'F1':>7s}")
    for name, v in r["views"].items():
        pr = f"{v['pr_auc']:.4f}" if v['pr_auc'] is not None else "  n/a"
        roc = f"{v['roc_auc']:.4f}" if v['roc_auc'] is not None else "  n/a"
        f1 = f"{v['f1']:.4f}" if v['f1'] is not None else "  n/a"
        print(f"  {name:14s} {v['n']:>9,} {v['prevalence']:>6.3f} {pr:>8} {roc:>7} {f1:>7}")

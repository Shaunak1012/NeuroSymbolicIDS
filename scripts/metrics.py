"""
Standard evaluation suite — every experiment reports the same views so the ablation
table is consistent and the *easy* overall number can never masquerade as the result.

Primary metric = PR-AUC (data is imbalanced; accuracy is misleading).
HEADLINE view  = zero-day-only binary (benign vs the 6 rare classes) — matches the
                 base paper's "6 unknown classes" metric.

    import metrics
    r = metrics.evaluate(y_mc, scores, zero_day_classes, fpr=0.01)
    metrics.print_report(r)
"""
import numpy as np
from sklearn.metrics import (average_precision_score, roc_auc_score,
                             f1_score, precision_score, recall_score)


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
    """Full suite. Returns a nested dict of views + per-family zero-day recall."""
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
    out["views"]["zeroday_only"] = _binary(y_mc, scores, is_benign | is_zd, thr)  # HEADLINE

    # per-family zero-day recall at the fixed-FPR threshold
    fam = {}
    for c in sorted(zd):
        m = y_mc == c
        if m.any():
            fam[c] = {"n": int(m.sum()), "recall": float((scores[m] >= thr).mean())}
    out["zeroday_family_recall"] = fam
    return out


def flatten(r, prefix=""):
    """Flat dict for tracking.log_run — headline metrics only."""
    z = r["views"]["zeroday_only"]; a = r["views"]["all"]
    return {
        f"{prefix}zd_pr_auc": z["pr_auc"], f"{prefix}zd_roc_auc": z["roc_auc"],
        f"{prefix}zd_f1": z["f1"], f"{prefix}all_pr_auc": a["pr_auc"],
    }


def print_report(r):
    print(f"\n{'view':16s} {'n':>9s} {'prev':>6s} {'PR-AUC':>8s} {'ROC':>7s} {'F1':>7s}")
    for name, v in r["views"].items():
        tag = "  <- HEADLINE" if name == "zeroday_only" else ""
        pr = f"{v['pr_auc']:.4f}" if v['pr_auc'] is not None else "  n/a"
        roc = f"{v['roc_auc']:.4f}" if v['roc_auc'] is not None else "  n/a"
        f1 = f"{v['f1']:.4f}" if v['f1'] is not None else "  n/a"
        print(f"  {name:14s} {v['n']:>9,} {v['prevalence']:>6.3f} {pr:>8} {roc:>7} {f1:>7}{tag}")
    print(f"\n  per-family zero-day recall @ {r['fpr_target']:.0%} FPR (thr={r['threshold']:.4f}):")
    for c, f in r["zeroday_family_recall"].items():
        note = "  (tiny n — noisy)" if f["n"] < 100 else ""
        print(f"    {c:30s} n={f['n']:>6,}  recall={f['recall']:.4f}{note}")

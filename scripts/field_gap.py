"""
field_gap.py — the write-up's opening argument, computed once over every method
this project has measured.

WHY THIS EXISTS
---------------
The write-up spine (decided 2026-08-10) leads with the protocol gap: **the metric
the CIC-IDS2017 literature publishes cannot see zero-day detection at all.** That
argument currently exists as four separate demonstrations in four places —
`comparability.py` on 1 model, Tier A on 7, Tier B on 4, and the base paper's own
metric set. Nobody has ever put them on one axis.

This script does, and it computes the number the argument actually turns on:

    **the rank correlation between the field's metric and ours, across methods.**

If that correlation is high, the field's metric is a noisy proxy for zero-day
detection and the critique is merely about precision. If it is near zero or
negative, the published metric carries **no information** about the capability it
is used to claim — which is a categorically stronger statement, and the one the
scattered evidence has been hinting at.

  * FIELD binary  = `all_pr_auc`, benign vs ALL attacks **including the 8 families
                    the model trained on**. This is the ~99 % number the field
                    reports.
  * MACRO zero-day = `macro_zd_pr_auc`, mean PR-AUC over the 3 adequately-powered
                    families the model has **never seen**. This project's headline.

WHAT IS EXCLUDED, AND WHY (stated, not silent)
----------------------------------------------
Runs that are **replicates of one method rather than distinct methods** would
over-weight that method in a cross-method correlation: `cnn_kfold*` (data-split
folds), `cnn_noise_r*` (noise-floor replicates), `det_verify_*` (determinism
replicates), `cnn_repro_*` (a reproduction check). All are `cnn_paper`'s model.
Seeds of the same method ARE kept and averaged.

⚠️ **Tie-degenerate scorers are FLAGGED, NOT DROPPED.** A depth-limited tree and
k=5 k-NN emit a handful of distinct probabilities, so their PR-AUC is computed
over a half-tied ranking and is not strictly comparable to a continuous scorer's.
Dropping them would be a defensible choice made by the person who knows which
direction it moves the answer, so the correlation is reported BOTH ways instead.
"""
import json
import os
import re
import sys
from collections import defaultdict

import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths  # noqa: E402

FIELD = "all_pr_auc"
MACRO = "macro_zd_pr_auc"

# Replicates of cnn_paper's model, not distinct methods. See docstring.
# `xgboost_oracle` is excluded on different grounds: it is TRAINED ON ZERO-DAY
# LABELS (~1,000 of them), so it is an upper bound on what the features permit,
# not a method runnable under this protocol. It sits at FIELD 1.0000 / MACRO
# 0.9899 -- a single extreme high-high point that inflates any correlation it is
# included in, which is exactly why it must not be.
EXCLUDE_PREFIX = ("cnn_kfold", "cnn_noise_r", "det_verify", "cnn_repro", "smoke",
                  "xgboost_oracle")

_SUFFIX = re.compile(r"(_logodds)?(_s\d+)?(_logodds)?$")


def base_name(name):
    """Collapse seed and rescore suffixes so seeds of one method group together."""
    prev = None
    out = name
    while out != prev:
        prev = out
        out = _SUFFIX.sub("", out)
    return out


def field_noise(rows):
    """Median run-to-run SD of the FIELD metric, over methods with >=3 seeds.

    This is what makes the resolution claim quantitative rather than rhetorical:
    without it, "these two methods are indistinguishable" is an assertion. Median
    rather than mean because a few benign-only scorers (LOF, MSP, Mahalanobis)
    have order-of-magnitude larger seed variance and would drag a mean upward,
    making the field's metric look worse than it is.
    """
    g = defaultdict(list)
    for r in rows:
        if r.get("schema") != "v2-macro":
            continue
        v = r.get("metrics", {}).get(FIELD)
        if v is None or r["name"].startswith(EXCLUDE_PREFIX):
            continue
        g[base_name(r["name"])].append(float(v))
    sds = [float(np.std(v, ddof=1)) for v in g.values() if len(v) >= 3]
    return float(np.median(sds)) if sds else float("nan")


def main():
    p = os.path.join(paths.METADATA, "runs.jsonl")
    rows = [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]

    groups = defaultdict(lambda: {"field": [], "macro": [], "sat": False, "n": 0})
    skipped = 0
    for r in rows:
        if r.get("schema") != "v2-macro":
            continue
        m = r.get("metrics", {})
        if m.get(FIELD) is None or m.get(MACRO) is None:
            continue
        name = r["name"]
        if name.startswith(EXCLUDE_PREFIX):
            skipped += 1
            continue
        g = groups[base_name(name)]
        g["field"].append(float(m[FIELD]))
        g["macro"].append(float(m[MACRO]))
        g["n"] += 1
        if m.get("saturated"):
            g["sat"] = True

    table = []
    for name, g in groups.items():
        table.append({
            "method": name,
            "field": float(np.mean(g["field"])),
            "macro": float(np.mean(g["macro"])),
            "n_runs": g["n"],
            "tie_degenerate": bool(g["sat"]),
        })
    table.sort(key=lambda d: -d["macro"])

    print("=" * 92)
    print("THE FIELD-METRIC GAP — every method this project has measured, on one axis")
    print("=" * 92)
    print(f"  (excluded {skipped} rows that are replicates of cnn_paper's model, "
          f"not distinct methods)\n")
    print(f"  {'method':<28}{'FIELD binary':>14}{'MACRO zero-day':>16}{'runs':>6}  flag")
    for d in table:
        flag = "TIE-DEGENERATE" if d["tie_degenerate"] else ""
        print(f"  {d['method']:<28}{d['field']:>14.4f}{d['macro']:>16.4f}"
              f"{d['n_runs']:>6}  {flag}")

    f = np.array([d["field"] for d in table])
    mm = np.array([d["macro"] for d in table])

    print("\n" + "=" * 92)
    print("THE ARGUMENT, AS NUMBERS")
    print("=" * 92)
    print(f"  methods compared                : {len(table)}")
    print(f"  FIELD binary  range             : {f.min():.4f} – {f.max():.4f}  "
          f"(spread {f.max()-f.min():.4f})")
    print(f"  MACRO zero-day range            : {mm.min():.4f} – {mm.max():.4f}  "
          f"(spread {mm.max()-mm.min():.4f}, {mm.max()/max(mm.min(),1e-9):.0f}x)")

    rho, prho = stats.spearmanr(f, mm)
    r, pr = stats.pearsonr(f, mm)
    print(f"\n  Spearman rank corr FIELD vs MACRO : rho = {rho:+.3f}  (p = {prho:.3f})")
    print(f"  Pearson  corr                     : r   = {r:+.3f}  (p = {pr:.3f})")

    keep = [d for d in table if not d["tie_degenerate"]]
    if len(keep) > 2:
        fk = np.array([d["field"] for d in keep])
        mk = np.array([d["macro"] for d in keep])
        rho2, p2 = stats.spearmanr(fk, mk)
        print(f"  ...excluding tie-degenerate scorers ({len(table)-len(keep)} dropped): "
              f"rho = {rho2:+.3f}  (p = {p2:.3f}, n = {len(keep)})")
    else:
        rho2, p2 = float("nan"), float("nan")

    # ------------------------------------------------------------------
    # 🔴 THE STRONG FORM OF THIS ARGUMENT DOES NOT SURVIVE — read before quoting.
    #
    # The tempting claim is "the field's metric carries NO information about
    # zero-day detection". It is FALSE and the numbers above say so: rho stays
    # +0.4 to +0.6 and significant, including when restricted to the field's own
    # ~99% reporting regime. The published metric IS a real, if weak, proxy.
    #
    # A second tempting claim also fails: "the metric's whole spread is below its
    # own noise". The field metric is PRECISE — median run-to-run SD across
    # multi-seed methods is ~0.002, an order of magnitude below its spread.
    #
    # What the data DOES support is a resolution claim, and it is strong enough:
    # the metric compresses an enormous range of zero-day capability into a
    # scale so fine that method pairs separated by LESS THAN THEIR OWN MEASUREMENT
    # NOISE differ by multiples on the task that matters. That is a discrimination
    # failure, not an information failure -- a different and defensible claim.
    # ------------------------------------------------------------------
    print("\n" + "-" * 92)
    print("  DISCRIMINATION TEST — can the field's metric tell these methods apart?")
    print("-" * 92)
    noise = field_noise(rows)
    band = 2 * noise * np.sqrt(2)      # ~2 SD on a difference of two measurements
    print(f"  median run-to-run SD of the FIELD metric (multi-seed methods) : {noise:.4f}")
    print(f"  => two methods are INDISTINGUISHABLE on it if they differ by  < {band:.4f}")

    pairs, bad = 0, []
    for i in range(len(table)):
        for j in range(i + 1, len(table)):
            a, b = table[i], table[j]
            if abs(a["field"] - b["field"]) < band:
                pairs += 1
                lo = min(a["macro"], b["macro"])
                if lo > 1e-6 and max(a["macro"], b["macro"]) / lo >= 2.0:
                    bad.append((a, b, max(a["macro"], b["macro"]) / lo))
    frac = len(bad) / pairs if pairs else float("nan")
    bad.sort(key=lambda t: -t[2])
    print(f"  method pairs indistinguishable on the FIELD metric            : {pairs}")
    print(f"  ...of those, pairs differing >=2x on MACRO zero-day           : "
          f"{len(bad)}  ({frac:.0%})")
    if bad:
        w = bad[0]
        print(f"  worst case: {w[0]['method']} vs {w[1]['method']} — "
              f"{abs(w[0]['field']-w[1]['field']):.4f} apart on the published metric, "
              f"{w[2]:.0f}x apart on zero-day")
    RES_DISC = {"field_noise_sd": float(noise), "indistinguishable_band": float(band),
                "pairs_indistinguishable": pairs, "pairs_2x_apart_on_macro": len(bad),
                "fraction": float(frac)}

    # The single most quotable line: methods that are indistinguishable on the
    # field's metric but an order of magnitude apart on ours.
    print("\n  The gap made concrete — methods within 0.01 FIELD binary of each other:")
    shown = 0
    for i in range(len(table)):
        for j in range(i + 1, len(table)):
            a, b = table[i], table[j]
            if abs(a["field"] - b["field"]) <= 0.01 and b["macro"] > 1e-6:
                ratio = a["macro"] / b["macro"]
                if ratio >= 5 and shown < 6:
                    print(f"    {a['method']:<24} FIELD {a['field']:.4f}  MACRO {a['macro']:.4f}")
                    print(f"    {b['method']:<24} FIELD {b['field']:.4f}  MACRO {b['macro']:.4f}"
                          f"   -> {ratio:.0f}x apart on zero-day, "
                          f"{abs(a['field']-b['field']):.4f} apart on the published metric\n")
                    shown += 1

    print("\n" + "=" * 92)
    print("  THE CLAIM THIS SUPPORTS, STATED AT THE STRENGTH THE DATA ALLOWS")
    print("=" * 92)
    print(f"  🔴 NOT supported: 'the published metric carries no information about")
    print(f"     zero-day detection'. rho = {rho:+.3f} (p = {prho:.4f}) — it is a real,")
    print( "     if weak, proxy. Do not write the strong form.")
    print( "  🔴 NOT supported: 'its spread is below its own noise'. The field metric")
    print(f"     is precise (SD ~{noise:.4f}); its spread is ~10x that.")
    print( "\n  ✅ SUPPORTED — a RESOLUTION failure, which is enough:")
    print(f"     {len(bad)} of {pairs} method pairs ({frac:.0%}) are indistinguishable on the")
    print( "     metric the literature publishes while differing >=2x on zero-day")
    print( "     detection. The published number ranks methods roughly right and")
    print( "     cannot resolve the differences that decide whether a novel attack")
    print( "     is caught. Reporting it to 3 decimals with no error bar, as the")
    print( "     field does, presents that as precision.")

    RES = {"methods": table, "n_methods": len(table),
           "field_range": [float(f.min()), float(f.max())],
           "macro_range": [float(mm.min()), float(mm.max())],
           "spearman": {"rho": float(rho), "p": float(prho)},
           "pearson": {"r": float(r), "p": float(pr)},
           "spearman_excl_tie_degenerate": {"rho": float(rho2), "p": float(p2)},
           "discrimination": RES_DISC,
           "strong_form_supported": False,
           "excluded_replicate_rows": skipped}
    outp = os.path.join(paths.METADATA, "field_gap.json")
    with open(outp, "w", encoding="utf-8") as fh:
        json.dump(RES, fh, indent=1)
    print(f"\nwrote {outp}")

    _figure(table)
    print("DONE (field_gap)")


def _figure(table):
    """Scatter: the vertical collapse IS the argument."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:                                    # pragma: no cover
        print(f"  (figure skipped: {e})")
        return

    fig, ax = plt.subplots(figsize=(9.5, 6))

    # The argument is about the regime the literature actually publishes in, so
    # mark it rather than letting the eye average over anomaly scorers that never
    # claim 99% in the first place.
    CLUB = 0.98
    ax.axvspan(CLUB, 1.005, color="#3182ce", alpha=0.07, zorder=0)
    inside = [d for d in table if d["field"] >= CLUB]
    if inside:
        lo = min(d["macro"] for d in inside)
        hi = max(d["macro"] for d in inside)
        ax.annotate("", xy=(1.001, hi), xytext=(1.001, lo),
                    arrowprops=dict(arrowstyle="<->", color="#c53030", lw=1.6))
        ax.text(1.006, (lo + hi) / 2, f"{hi/max(lo,1e-9):.0f}×\nspread",
                fontsize=8.5, color="#c53030", va="center", ha="left", weight="bold")

    for d in table:
        deg = d["tie_degenerate"]
        ax.scatter(d["field"], d["macro"], s=64,
                   facecolor="none" if deg else "#2b6cb0",
                   edgecolor="#a0aec0" if deg else "#2b6cb0",
                   marker="s" if deg else "o", zorder=3)

    ax.set_xlabel("FIELD binary PR-AUC  (benign vs all attacks, INCLUDING trained families)\n"
                  "— the metric published CIC-IDS2017 work reports", fontsize=9)
    ax.set_ylabel("MACRO zero-day PR-AUC\n(3 powered families never seen in training)", fontsize=9)
    ax.set_title(f"Inside the field's own reporting regime (shaded, FIELD ≥ {CLUB}), "
                 f"{len(inside)} methods\nsit within {max(d['field'] for d in inside)-min(d['field'] for d in inside):.3f} "
                 f"of each other — and span {hi/max(lo,1e-9):.0f}× on zero-day detection",
                 fontsize=11)
    ax.set_xlim(right=1.05)
    ax.grid(alpha=0.25, zorder=0)
    ax.text(0.02, 0.02,
            "open squares = tie-degenerate scorers (flagged, not dropped)\n"
            "rank correlation across all 40 methods is rho = +0.57: a weak proxy, NOT uninformative",
            transform=ax.transAxes, fontsize=8, color="#718096")
    fig.tight_layout()
    outp = os.path.join(paths.FIGURES, "field_gap.png")
    fig.savefig(outp, dpi=150)
    print(f"  wrote {outp}")


if __name__ == "__main__":
    main()

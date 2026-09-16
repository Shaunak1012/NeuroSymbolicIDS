"""
basepaper_audit.py — the base paper's own figures, transcribed once and checked
against each other, so every number our write-up says about it has a record.

WHY THIS EXISTS
---------------
`paper_metrics.py` transcribes the base paper's Table II and puts our models in its
metric set. That covers what WE score. It does not cover the claims we make ABOUT
the base paper — and on 2026-09-16 an audit (BASEPAPER_COMPARISON.md) found that
the most important of those claims live in its Table I and Fig. 3, which no script
had ever transcribed:

  * where its symbolic gain comes from (BP-01),
  * how much of its zero-day headline one 11-flow family carries (BP-02),
  * what test-set size its confusion matrices imply (BP-03),
  * which Table II cell does not match its own confusion matrix (BP-04).

A number in a doc with no record behind it is a defect (CLAUDE.md). This is the
record. It loads no model and reads only our label arrays, so it is fast and
deterministic.

TRANSCRIPTION
-------------
Bizzarri et al., ICCCN 2024, DOI 10.1109/ICCCN61486.2024.10637618 (`basepaper.pdf`,
9 pages), read in full on 2026-09-16.

  Table I   — class counts after their under-sampling (payload-PACKET units)
  Table II  — accuracy and F1, 50 epochs (Adamax)
  Fig. 3    — twelve binary confusion matrices, 50 epochs

Fig. 3 prints two TN cells and some TP/FN cells in scientific notation ("7e+04",
"1e+05", "2e+04"). They are NOT needed: M-LTN and B-LTN print TN and FP exactly,
and both sum to 70,000, so the benign count is exact; every attack total is exact
from the matrices that print both cells. The rounded cells are then DERIVED.

VALIDATION vs FINDINGS. The transcription is validated by the eight binary
known-class and all-class accuracy cells: all eight reproduce Table II from the
counts, and the all-class ones use every count including the zero-day split.
Any OTHER printed cell that disagrees with the counts is then a finding about the
paper, not a transcription error. Three do (measured 2026-09-16):

  1D CNN  Binary 15 F1        printed 90.88, counts give 92.27 -- the accuracy
                              cell agrees with the counts, so the F1 cell is wrong
                              (it is a copy of the accuracy value)
  M-LTN   Binary 6 accuracy   printed 56.06, counts give 56.02 -- its F1 cell
                              (71.80) agrees with the counts, so the accuracy is wrong
  B-LTN   Binary 6 accuracy   printed 39.40, counts give 39.48 -- its F1 cell
                              (56.61) agrees with the counts exactly

The headline pair (1D CNN 48.34, Hybrid-LTN 60.47) reproduces exactly.

Run:  python scripts/basepaper_audit.py
Out:  outputs/metadata/basepaper_audit.json
"""
import os
import sys
import json

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                        # noqa: E402

# ---------------------------------------------------------------- Table I ----
TABLE_I_KNOWN = {"BENIGN": 200_000, "DoS Hulk": 31_843, "DDoS": 31_843,
                 "DoS GoldenEye": 31_843, "DoS slowloris": 31_843,
                 "Infiltration": 31_843, "DoS Slowhttptest": 31_843,
                 "SSH-Patator": 31_843, "FTP-Patator": 31_843}
TABLE_I_ZERO_DAY = {"Heartbleed": 13_486, "Web Attack Brute Force": 11_754,
                    "Web Attack XSS": 3_341, "Bot": 2_543, "PortScan": 830,
                    "Web Attack Sql Injection": 12}
BENIGN_BEFORE_REDUCTION = 362_108          # "arbitrarily decreased ... from 362,108"
STATED_SPLIT = (0.80, 0.10, 0.10)

# --------------------------------------------------------------- Table II ----
MODELS = ["1D CNN", "M-LTN", "B-LTN", "Hybrid-LTN"]
ACC_50 = {
    "Multi-class 9 known classes": {"Hybrid-LTN": 81.08, "1D CNN": 80.99, "M-LTN": 80.41, "B-LTN": None},
    "Binary 9 known classes":      {"Hybrid-LTN": 99.57, "1D CNN": 99.42, "M-LTN": 99.46, "B-LTN": 99.42},
    "Multi-class 15 classes":      {"Hybrid-LTN": 67.52, "1D CNN": 67.45, "M-LTN": 66.96, "B-LTN": None},
    "Binary 15 classes":           {"Hybrid-LTN": 93.03, "1D CNN": 90.88, "M-LTN": 92.19, "B-LTN": 89.40},
    "Binary 6 unknown classes":    {"Hybrid-LTN": 60.47, "1D CNN": 48.34, "M-LTN": 56.06, "B-LTN": 39.40},
}
F1_50 = {
    "Binary 9 known classes":   {"Hybrid-LTN": 99.62, "1D CNN": 99.49, "M-LTN": 99.52, "B-LTN": 99.49},
    "Binary 15 classes":        {"Hybrid-LTN": 94.20, "1D CNN": 90.88, "M-LTN": 93.47, "B-LTN": 90.93},
    "Binary 6 unknown classes": {"Hybrid-LTN": 75.37, "1D CNN": 65.18, "M-LTN": 71.80, "B-LTN": 56.61},
}
VIEW_HAS_BENIGN = {"Multi-class 9 known classes": True, "Binary 9 known classes": True,
                   "Multi-class 15 classes": True, "Binary 15 classes": True,
                   "Binary 6 unknown classes": False}

# ----------------------------------------------------------------- Fig. 3 ----
# Only the exactly printed cells. 9 known: (TN, FP, FN, TP). 6 unknown: (FN, TP),
# its benign row is printed as 0 / 0.
FIG3_KNOWN = {"1D CNN": (None, 380, 536, 88_624), "M-LTN": (69_364, 636, 224, 88_936),
              "B-LTN": (69_307, 693, 224, 88_936), "Hybrid-LTN": (None, 452, 227, 88_933)}
FIG3_UNKNOWN = {"1D CNN": (16_513, 15_453), "M-LTN": (14_060, 17_906),
                "B-LTN": (19_345, 12_621), "Hybrid-LTN": (12_636, 19_330)}


def f1(tp, fp, fn):
    p, r = tp / (tp + fp), tp / (tp + fn)
    return 100 * 2 * p * r / (p + r)


def main():
    out = {"source": "Bizzarri et al., ICCCN 2024, DOI 10.1109/ICCCN61486.2024.10637618",
           "transcribed": "2026-09-16"}
    bad = []

    # ---- the confusion matrices, completed from their exact cells ----------
    benign = {m: FIG3_KNOWN[m][0] + FIG3_KNOWN[m][1] for m in ("M-LTN", "B-LTN")}
    assert len(set(benign.values())) == 1, benign
    N_BEN = benign["M-LTN"]
    known_atk = {m: FIG3_KNOWN[m][2] + FIG3_KNOWN[m][3] for m in MODELS}
    assert len(set(known_atk.values())) == 1, known_atk
    N_KATK = known_atk["1D CNN"]
    N_ZD = sum(FIG3_UNKNOWN["1D CNN"])
    assert all(sum(v) == N_ZD for v in FIG3_UNKNOWN.values())
    assert N_ZD == sum(TABLE_I_ZERO_DAY.values()), "Fig. 3 zero-day total != Table I"

    cm = {}
    for m in MODELS:
        tn_p, fp, fn_k, tp_k = FIG3_KNOWN[m]
        fn_u, tp_u = FIG3_UNKNOWN[m]
        cm[m] = {"TN": N_BEN - fp, "FP": fp, "FN_known": fn_k, "TP_known": tp_k,
                 "FN_unknown": fn_u, "TP_unknown": tp_u,
                 "FN_all": fn_k + fn_u, "TP_all": tp_k + tp_u}
        if tn_p is not None:
            assert tn_p == N_BEN - fp

    # ---- every derived binary accuracy must reproduce Table II --------------
    recomputed = {}
    for m in MODELS:
        c = cm[m]
        n9, n15 = N_BEN + N_KATK, N_BEN + N_KATK + N_ZD
        acc = {"Binary 9 known classes": 100 * (c["TN"] + c["TP_known"]) / n9,
               "Binary 15 classes": 100 * (c["TN"] + c["TP_all"]) / n15,
               "Binary 6 unknown classes": 100 * c["TP_unknown"] / N_ZD}
        f1s = {"Binary 9 known classes": f1(c["TP_known"], c["FP"], c["FN_known"]),
               "Binary 15 classes": f1(c["TP_all"], c["FP"], c["FN_all"]),
               "Binary 6 unknown classes": f1(c["TP_unknown"], 0, c["FN_unknown"])}
        recomputed[m] = {"accuracy": acc, "f1": f1s}
        # VALIDATION: the known-class and all-class accuracy cells.
        for v in ("Binary 9 known classes", "Binary 15 classes"):
            if abs(round(acc[v], 2) - ACC_50[v][m]) > 0.011:
                bad.append(("accuracy", m, v, ACC_50[v][m], round(acc[v], 2)))
    out["confusion_matrices"] = cm
    out["recomputed_from_fig3"] = recomputed
    out["transcription_validated"] = not bad

    # FINDINGS: every other printed cell that disagrees with the counts. For each,
    # record whether the model's OTHER printed metric on that view agrees with the
    # counts -- that is what says which of the two printed cells is the wrong one.
    table_ii_inconsistent = []
    for m in MODELS:
        for metric, printed_tab in (("accuracy", ACC_50), ("f1", F1_50)):
            for v, val in recomputed[m][metric].items():
                if metric == "accuracy" and v != "Binary 6 unknown classes":
                    continue                    # already validated above
                printed = printed_tab[v][m]
                if abs(round(val, 2) - printed) <= 0.011:
                    continue
                other = "f1" if metric == "accuracy" else "accuracy"
                other_tab = F1_50 if other == "f1" else ACC_50
                other_ok = abs(round(recomputed[m][other][v], 2) - other_tab[v][m]) <= 0.011
                table_ii_inconsistent.append({
                    "model": m, "view": v, "metric": metric, "printed": printed,
                    "from_fig3": round(val, 2),
                    "other_metric_agrees_with_fig3": bool(other_ok)})
    out["table_ii_inconsistent"] = table_ii_inconsistent
    out["headline_pair_reproduces"] = all(
        abs(round(recomputed[m]["accuracy"]["Binary 6 unknown classes"], 2)
            - ACC_50["Binary 6 unknown classes"][m]) <= 0.011 for m in ("1D CNN", "Hybrid-LTN"))

    # ---- BP-03: the evaluation set is not the stated 10 % ------------------
    total = sum(TABLE_I_KNOWN.values())
    n_known_test = N_BEN + N_KATK
    out["test_size"] = {
        "table_i_total": total,
        "stated_split": STATED_SPLIT,
        "expected_known_test_at_10pct": round(total * STATED_SPLIT[2]),
        "implied_known_test_from_fig3": n_known_test,
        "implied_fraction": n_known_test / total,
        "benign_fraction": N_BEN / TABLE_I_KNOWN["BENIGN"],
        "attack_fraction": N_KATK / (total - TABLE_I_KNOWN["BENIGN"]),
        "zero_day_used_in_full": N_ZD == sum(TABLE_I_ZERO_DAY.values()),
    }

    # ---- BP-01: where the symbolic gain lives ------------------------------
    deltas = {v: round(ACC_50[v]["Hybrid-LTN"] - ACC_50[v]["1D CNN"], 2) for v in ACC_50}
    out["hybrid_minus_cnn"] = {
        "per_view": deltas,
        "view_has_benign_rows": VIEW_HAS_BENIGN,
        "max_gain_on_views_with_benign": max(d for v, d in deltas.items() if VIEW_HAS_BENIGN[v]),
        "gain_on_view_without_benign": deltas["Binary 6 unknown classes"],
        "fp_cnn": cm["1D CNN"]["FP"], "fp_hybrid": cm["Hybrid-LTN"]["FP"],
        "fp_change_pct": 100 * (cm["Hybrid-LTN"]["FP"] / cm["1D CNN"]["FP"] - 1),
        "fn_known_cnn": cm["1D CNN"]["FN_known"], "fn_known_hybrid": cm["Hybrid-LTN"]["FN_known"],
        "fn_known_change_pct": 100 * (cm["Hybrid-LTN"]["FN_known"] / cm["1D CNN"]["FN_known"] - 1),
        "tp_unknown_cnn": cm["1D CNN"]["TP_unknown"],
        "tp_unknown_hybrid": cm["Hybrid-LTN"]["TP_unknown"],
        "threshold_free_metric_reported": False,
    }

    # ---- BP-02: the zero-day set, in their units and ours ------------------
    P = paths.PAPER
    y_te = np.load(os.path.join(P, "y_test_mc.npy"), allow_pickle=True)
    flows = {c: int((y_te == c).sum()) for c in TABLE_I_ZERO_DAY if c != "PortScan"}
    # PortScan is a KNOWN class for us, so count it over the whole cleaned capture.
    pooled = np.concatenate([
        np.load(os.path.join(paths.PROCESSED, f"labels_{s}_multiclass.npy"), allow_pickle=True)
        for s in ("train", "test")])
    flows["PortScan"] = int(sum(1 for s in pooled if str(s).strip() == "PortScan"))
    comp = {}
    for c, n in TABLE_I_ZERO_DAY.items():
        comp[c] = {"their_packets": n, "our_flows": flows[c],
                   "packets_per_flow": n / flows[c] if flows[c] else None,
                   "their_share": n / N_ZD}
    # How many INDEPENDENT events is Heartbleed? Count distinct 5-tuples and the
    # time span of its flows (corrected timestamps -- never parse meta directly).
    import pandas as pd
    import timeline
    meta = pd.read_csv(os.path.join(P, "meta_test.csv"))
    hb = y_te == "Heartbleed"
    five = meta.loc[hb, ["Source IP", "Source Port", "Destination IP",
                         "Destination Port", "Protocol"]].drop_duplicates()
    ts = timeline.load_timestamps("test")[hb]
    comp["Heartbleed"]["distinct_5tuples"] = int(len(five))
    comp["Heartbleed"]["distinct_host_pairs"] = int(
        meta.loc[hb, ["Source IP", "Destination IP"]].drop_duplicates().shape[0])
    comp["Heartbleed"]["span_minutes"] = float((ts.max() - ts.min()).total_seconds() / 60)
    top2 = sorted(comp, key=lambda k: -comp[k]["their_share"])[:2]
    out["zero_day_composition"] = {
        "families": comp,
        "top_two": top2,
        "top_two_share": sum(comp[c]["their_share"] for c in top2),
        "heartbleed_share": comp["Heartbleed"]["their_share"],
        "heartbleed_flows": comp["Heartbleed"]["our_flows"],
        "portscan_survival": TABLE_I_ZERO_DAY["PortScan"] / flows["PortScan"],
    }

    # ---- report ------------------------------------------------------------
    print("=" * 92)
    print("BASE PAPER — its own figures, checked against each other")
    print("=" * 92)
    print(f"Fig. 3 benign rows {N_BEN:,} · known-attack rows {N_KATK:,} · zero-day {N_ZD:,}")
    print("\nTable II binary accuracies recomputed from Fig. 3:")
    for m in MODELS:
        print("  %-11s " % m + "  ".join("%s %.2f (printed %.2f)" % (v.split()[1], recomputed[m]["accuracy"][v], ACC_50[v][m])
                                        for v in recomputed[m]["accuracy"]))
    print("  -> transcription %s (8 known/all-class accuracy cells)"
          % ("VALIDATED" if not bad else "FAILED: %s" % bad))
    print("  -> headline pair (1D CNN, Hybrid-LTN view 5) reproduces: %s"
          % out["headline_pair_reproduces"])
    print("\nBP-04  Table II cells that disagree with the paper's own Fig. 3:")
    for x in table_ii_inconsistent:
        print("  %-10s %-26s %-8s printed %6.2f  Fig.3 gives %6.2f  (its %s cell agrees with Fig.3: %s)"
              % (x["model"], x["view"], x["metric"], x["printed"], x["from_fig3"],
                 "f1" if x["metric"] == "accuracy" else "accuracy", x["other_metric_agrees_with_fig3"]))
    t = out["test_size"]
    print(f"\nBP-03  known-class test set: {t['implied_known_test_from_fig3']:,} rows = "
          f"{t['implied_fraction']:.1%} of Table I ({t['table_i_total']:,}); a 10 % split gives "
          f"{t['expected_known_test_at_10pct']:,}")
    h = out["hybrid_minus_cnn"]
    print("\nBP-01  Hybrid-LTN minus 1D CNN: " + " / ".join("%+.2f" % d for d in h["per_view"].values()))
    print(f"       false positives {h['fp_cnn']} -> {h['fp_hybrid']} ({h['fp_change_pct']:+.0f} %), "
          f"known false negatives {h['fn_known_cnn']} -> {h['fn_known_hybrid']} ({h['fn_known_change_pct']:+.0f} %)")
    z = out["zero_day_composition"]
    hbc = comp["Heartbleed"]
    print(f"\nBP-02  Heartbleed = {z['heartbleed_share']:.1%} of their zero-day set, from "
          f"{z['heartbleed_flows']} flows = {hbc['distinct_5tuples']} distinct 5-tuple(s), "
          f"{hbc['distinct_host_pairs']} host pair(s), {hbc['span_minutes']:.0f} min; top two ({', '.join(z['top_two'])}) = {z['top_two_share']:.1%}; "
          f"PortScan survives their payload filter at {z['portscan_survival']:.2%}")

    path = os.path.join(paths.METADATA, "basepaper_audit.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(f"\nwrote {path}")
    if bad:
        print("TRANSCRIPTION CHECK FAILED")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

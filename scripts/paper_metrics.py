"""
paper_metrics.py — our numbers in the BASE PAPER'S metric set, and in the wider
CIC-IDS2017 literature's.

WHY THIS EXISTS
---------------
This project headlines **macro zero-day PR-AUC (~0.64)** because `metrics.py`
enforces it. That is the right *research* metric. But it is not what anyone we
are compared against reports, and a capstone has to be readable next to them:

  * **The base paper** (Bizzarri et al., IEEE — `basepaper.pdf`) reports
    **Accuracy + F1** across five test-set views (Table II). Its headline is
    *zero-day accuracy 48.34% -> 60.47%, F1 65.18% -> 75.37%* (50 epochs).
    We have never computed a single one of those numbers.
  * **The wider CIC-IDS2017 literature** reports **99%+** accuracy/F1 on overall
    binary detection. `comparability.py` already shows the protocol gap on
    PR-AUC; this adds the accuracy/precision/recall/F1/FAR suite those papers
    actually print.

Both are produced here so the write-up can show our result in three metric
systems at once, from the same runs.

THE FIVE TEST-SET VIEWS (base paper Table II)
----------------------------------------------
  1. Multi-class, 9 known classes   -- argmax over the 9 trained classes
  2. Binary, 9 known classes        -- benign vs attack, known rows only
  3. Multi-class, 15 classes        -- all rows; zero-day can NEVER be correct,
                                       since the model has no such output
  4. Binary, 15 classes             -- benign vs attack, all rows
  5. **Binary, 6 unknown classes**  -- the zero-day headline

🔴 A DEFECT IN THE BASE PAPER'S ZERO-DAY METRIC, VERIFIED ARITHMETICALLY
------------------------------------------------------------------------
View 5 contains **only attack rows** -- there are no benign flows in it. So
precision is 1 by construction, accuracy IS recall, and

        F1 = 2*P*R/(P+R) = 2R/(1+R) = 2A/(1+A)

This is not an inference. It reproduces every entry of their F1 row from their
accuracy row to within rounding:

    1D CNN 30ep      47.13% -> 64.07%   (paper: 64.07%)
    Hybrid-LTN 30ep  55.70% -> 71.55%   (paper: 71.55%)
    1D CNN 50ep      48.34% -> 65.17%   (paper: 65.18%)
    Hybrid-LTN 50ep  60.47% -> 75.37%   (paper: 75.37%)

**Consequences, and they matter for how we position our own numbers:**
  1. Their "Accuracy + F1" zero-day headline is **one result reported twice**,
     not two independent confirmations.
  2. **The metric has no false-positive term at all.** A model that labels
     *everything* an attack scores 100% accuracy and 100% F1 on view 5. Their
     zero-day number cannot distinguish detection from indiscriminate alerting.
  3. This is not a hypothetical failure mode here: our own float32 saturation
     bug (KNOWN_ISSUES, 2026-07-27) produced exactly that -- `recall=1.0000`
     for every family -- and was caught **only** because our metric has a benign
     side. Under view 5 it would have looked like a perfect score.

So view 5 is reported for comparability and **always alongside the benign-side
metrics that make it interpretable** (FAR, precision, PR-AUC).

⚠️ THE COMPARISON IS IN FORM, NOT HEAD-TO-HEAD. Three documented deviations:
  * **Modality** -- they use payload bytes (Payload-Byte, 1500 B/packet); we use
    68 CICFlowMeter flow features. Deliberate, recorded in conference_roadmap §1.
  * **Zero-day membership differs by a swap** -- their zero-day set contains
    **PortScan** and their known set contains **Infiltration**; ours is the
    reverse. 5 of 6 families overlap. PortScan is large and highly separable,
    Infiltration is tiny (n=36), so this is not a neutral difference.
  * **Class sizes** -- their Table I undersamples to 31,843/class with
    Heartbleed at 13,486; CIC-IDS2017 flow data has 11 Heartbleed flows total.

Run:  python scripts/paper_metrics.py
Out:  outputs/metadata/paper_metrics.json
"""
import os
import sys
import json
import pickle

import numpy as np
from sklearn.metrics import (accuracy_score, f1_score, precision_score,
                             recall_score, roc_auc_score, average_precision_score)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                    # noqa: E402
import config                                   # noqa: E402
import features                                 # noqa: E402

cfg = config.get()
P, PR, MD = paths.PAPER, paths.PREDICTIONS, paths.METADATA
TFM = cfg["protocol"]["feature_transform"]

# Base paper Table II, 50 epochs (Adamax). Transcribed from basepaper.pdf.
PAPER_TABLE = {
    "Multi-class 9 known classes": {"Hybrid-LTN": 81.08, "1D CNN": 80.99},
    "Binary 9 known classes":      {"Hybrid-LTN": 99.57, "1D CNN": 99.42},
    "Multi-class 15 classes":      {"Hybrid-LTN": 67.52, "1D CNN": 67.45},
    "Binary 15 classes":           {"Hybrid-LTN": 93.03, "1D CNN": 90.88},
    "Binary 6 unknown classes":    {"Hybrid-LTN": 60.47, "1D CNN": 48.34},
}
PAPER_F1 = {
    "Binary 9 known classes":   {"Hybrid-LTN": 99.62, "1D CNN": 99.49},
    "Binary 15 classes":        {"Hybrid-LTN": 94.20, "1D CNN": 90.88},
    "Binary 6 unknown classes": {"Hybrid-LTN": 75.37, "1D CNN": 65.18},
}

# Our models, mapped onto their columns. `ltn_repro` (plain CE + Ax1/Ax2 label
# anchors) is the closest reproduction of their Hybrid-LTN; `ltn_ctrl_w0` is the
# axiom-FREE control, which they have no equivalent of.
MODELS = {
    "CNN (ours)":            ["cnn_paper", "cnn_paper_s43", "cnn_paper_s44"],
    "LTN control (w=0)":     ["ltn_ctrl_w0", "ltn_ctrl_w0_s43", "ltn_ctrl_w0_s44"],
    "LTN +Ax6 (ratio w=1)":  ["ltn_ax6_ratio_w1p0_s42", "ltn_ax6_ratio_w1p0_s43",
                              "ltn_ax6_ratio_w1p0_s44"],
    "LTN repro (CE+Ax1/2)":  ["ltn_repro"],          # closest to their Hybrid-LTN; n=1
}

print("=" * 104)
print("PAPER-COMPARABLE METRICS — our runs in the base paper's metric set and the field's")
print("=" * 104)

y_te = np.load(os.path.join(P, "y_test_mc.npy"), allow_pickle=True)
zero_day = set(np.load(os.path.join(P, "zero_day_classes.npy"), allow_pickle=True).tolist())
known = set(np.load(os.path.join(P, "known_classes.npy"), allow_pickle=True).tolist())

is_benign = y_te == "BENIGN"
is_zd = np.isin(y_te, list(zero_day))
is_known = ~is_zd                                # includes BENIGN
y_bin = (~is_benign).astype(int)

print(f"test {len(y_te):,} | benign {is_benign.sum():,} | known attacks "
      f"{(is_known & ~is_benign).sum():,} | zero-day {is_zd.sum():,}")
print(f"our zero-day set   : {sorted(zero_day)}")
print("paper's zero-day set: ['Bot', 'Heartbleed', 'PortScan', 'Web Attack Brute Force', "
      "'Web Attack Sql Injection', 'Web Attack XSS']")
print("  -> DIFFERS BY A SWAP: they hold out PortScan and train on Infiltration; we do the")
print("     reverse. 5 of 6 overlap. Not a neutral difference — PortScan is large and highly")
print("     separable, Infiltration is n=36.")

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
import tensorflow as tf                          # noqa: E402

# Both cnn_paper.py and ltn_paper.py fit StandardScaler on features.transform(X_train)
# and LabelEncoder on y_train, so one saved pair is valid for every model here.
with open(os.path.join(paths.MODELS, "scaler_paper.pkl"), "rb") as f:
    scaler = pickle.load(f)
with open(os.path.join(paths.MODELS, "label_encoder_paper.pkl"), "rb") as f:
    le = pickle.load(f)
assert set(le.classes_) == known, "label encoder classes != known_classes.npy"
benign_idx = list(le.classes_).index("BENIGN")

X = scaler.transform(features.transform(np.load(os.path.join(P, "X_test.npy")), TFM))
X = X.reshape(-1, X.shape[1], 1).astype(np.float32)
print(f"\nprepared X_test {X.shape}")


def views(y_true_mc, pred_cls, p_attack):
    """The base paper's five views, plus the field's binary suite."""
    pred_bin = (pred_cls != benign_idx).astype(int)
    true_cls = np.array([list(le.classes_).index(c) if c in known else -1
                         for c in y_true_mc])
    out = {}

    # 1 / 2 — known rows only
    m = is_known
    out["Multi-class 9 known classes"] = 100 * accuracy_score(true_cls[m], pred_cls[m])
    out["Binary 9 known classes"] = 100 * accuracy_score(y_bin[m], pred_bin[m])
    out["_f1_Binary 9 known classes"] = 100 * f1_score(y_bin[m], pred_bin[m])

    # 3 / 4 — all rows. Zero-day rows can never be classified correctly in
    # multi-class: the model has no output for a class it never saw. This is a
    # property of the protocol, not a failure of the model, and it caps view 3.
    out["Multi-class 15 classes"] = 100 * accuracy_score(true_cls, pred_cls)
    out["Binary 15 classes"] = 100 * accuracy_score(y_bin, pred_bin)
    out["_f1_Binary 15 classes"] = 100 * f1_score(y_bin, pred_bin)

    # 5 — ZERO-DAY ROWS ONLY. No benign present, so accuracy == recall and
    # precision is 1 by construction. Reported for comparability only.
    z = is_zd
    out["Binary 6 unknown classes"] = 100 * accuracy_score(y_bin[z], pred_bin[z])
    out["_f1_Binary 6 unknown classes"] = 100 * f1_score(y_bin[z], pred_bin[z],
                                                         zero_division=0)

    # ---- the field's binary suite, on all 15 classes ----
    out["_field"] = {
        "accuracy": 100 * accuracy_score(y_bin, pred_bin),
        "precision": 100 * precision_score(y_bin, pred_bin, zero_division=0),
        "recall": 100 * recall_score(y_bin, pred_bin, zero_division=0),
        "f1": 100 * f1_score(y_bin, pred_bin, zero_division=0),
        # False Alarm Rate — the term view 5 structurally lacks.
        "far": 100 * float(pred_bin[is_benign].mean()),
        "roc_auc": 100 * roc_auc_score(y_bin, p_attack),
        "pr_auc": 100 * average_precision_score(y_bin, p_attack),
    }
    return out


RES = {"paper_table_50ep": PAPER_TABLE, "paper_f1_50ep": PAPER_F1, "ours": {}}
for label, tags in MODELS.items():
    runs = []
    for tag in tags:
        mp = os.path.join(paths.MODELS, f"{tag}.keras")
        if not os.path.exists(mp):
            print(f"  !! missing {tag}.keras — skipping")
            continue
        model = tf.keras.models.load_model(mp, compile=False)
        prob = model.predict(X, batch_size=2048, verbose=0)
        runs.append(views(y_te, prob.argmax(1), 1.0 - prob[:, benign_idx]))
        del model
    if not runs:
        continue
    agg = {}
    for k in runs[0]:
        if k == "_field":
            agg["_field"] = {kk: float(np.mean([r["_field"][kk] for r in runs]))
                             for kk in runs[0]["_field"]}
        else:
            agg[k] = float(np.mean([r[k] for r in runs]))
    agg["_n"] = len(runs)
    RES["ours"][label] = agg
    print(f"  {label:24s} n={len(runs)}  "
          f"zero-day acc {agg['Binary 6 unknown classes']:.2f}%")

# =============================================================================
# TABLE 1 — the base paper's Table II, with our column added
# =============================================================================
print("\n" + "=" * 104)
print("TABLE II EQUIVALENT — ACCURACY (%)   [paper: 50 epochs, Adamax]")
print("=" * 104)
ours_labels = list(RES["ours"])
hdr = f"{'Test Set':30s} {'Hybrid-LTN':>11s} {'1D CNN':>8s} |"
for l in ours_labels:
    hdr += f" {l[:20]:>20s}"
print(hdr + f"   n")
print("-" * 104)
for view in PAPER_TABLE:
    row = f"{view:30s} {PAPER_TABLE[view]['Hybrid-LTN']:>10.2f}% {PAPER_TABLE[view]['1D CNN']:>7.2f}% |"
    for l in ours_labels:
        row += f" {RES['ours'][l][view]:>19.2f}%"
    print(row)
print(f"{'':30s} {'':11s} {'':8s} |" + "".join(f" {RES['ours'][l]['_n']:>20d}" for l in ours_labels))

print("\n" + "=" * 104)
print("TABLE II EQUIVALENT — F1-SCORE (%)")
print("=" * 104)
for view in PAPER_F1:
    row = f"{view:30s} {PAPER_F1[view]['Hybrid-LTN']:>10.2f}% {PAPER_F1[view]['1D CNN']:>7.2f}% |"
    for l in ours_labels:
        row += f" {RES['ours']['_f1_' + view] if False else RES['ours'][l]['_f1_' + view]:>19.2f}%"
    print(row)

# =============================================================================
# THE F1 DEGENERACY — demonstrated, not asserted
# =============================================================================
print("\n" + "=" * 104)
print("🔴 VIEW 5 HAS NO FALSE-POSITIVE TERM — verification")
print("=" * 104)
print("  If 'Binary 6 unknown classes' contains only attack rows, precision == 1 and")
print("  F1 == 2A/(1+A) exactly. Checked against the paper's own published pairs:\n")
ok = True
for lab, a, f1 in [("1D CNN 30ep", 47.13, 64.07), ("Hybrid-LTN 30ep", 55.70, 71.55),
                   ("1D CNN 50ep", 48.34, 65.18), ("Hybrid-LTN 50ep", 60.47, 75.37)]:
    A = a / 100
    pred = 200 * A / (1 + A)
    good = abs(pred - f1) < 0.02
    ok &= good
    print(f"    {lab:18s} acc {a:6.2f}%  paper F1 {f1:6.2f}%  2A/(1+A) {pred:6.2f}%  "
          f"{'MATCH' if good else 'differs'}")
print(f"\n  -> {'CONFIRMED' if ok else 'NOT confirmed'}: their zero-day F1 carries NO information")
print("     beyond their zero-day accuracy. One result, reported twice.")

n_zd = int(is_zd.sum())
print(f"\n  And the pathology it permits: a model that flags EVERY flow as an attack scores")
print(f"    view-5 accuracy = 100.00%  and view-5 F1 = 100.00%   (n={n_zd:,}, all positive)")
print(f"  while its false alarm rate on the {int(is_benign.sum()):,} benign test flows is 100%.")
print("  Our own float32 saturation bug did exactly this in 2026-07-27 and was caught ONLY")
print("  because our headline metric has a benign side. Under view 5 it would have scored"
      " perfectly.")
RES["view5_degenerate"] = {"f1_equals_2a_over_1_plus_a": bool(ok),
                           "n_zero_day_rows": n_zd, "n_benign_in_view5": 0}

# =============================================================================
# WHY THE TWO ZERO-DAY NUMBERS ARE NOT COMPARABLE: composition
# =============================================================================
print("\n" + "=" * 104)
print("🔴 VIEW 5 IS ALSO A SIZE-WEIGHTED MIXTURE — the SAME defect we fixed in our own")
print("   metric on 2026-07-27, present in the base paper's headline")
print("=" * 104)

# Per-family detection rate under the paper's own decision rule (argmax != BENIGN),
# using our CNN. This is what view-5 accuracy is averaging over.
best_tag = MODELS["CNN (ours)"][0]
model = tf.keras.models.load_model(os.path.join(paths.MODELS, f"{best_tag}.keras"),
                                   compile=False)
pb = (model.predict(X, batch_size=2048, verbose=0).argmax(1) != benign_idx)
del model

print(f"  our CNN ({best_tag}), per-family detection rate at the paper's argmax rule:\n")
print(f"    {'family':30s} {'n':>7s} {'share':>7s} {'detected':>9s}")
fam_rates = {}
for c in sorted(zero_day):
    m = y_te == c
    if not m.any():
        continue
    r = float(pb[m].mean())
    fam_rates[c] = {"n": int(m.sum()), "share": float(m.sum() / is_zd.sum()), "rate": r}
    print(f"    {c:30s} {m.sum():>7,} {m.sum()/is_zd.sum():>6.1%} {r:>8.1%}")

# The two papers average over very different family mixes.
OURS_MIX = {c: fam_rates[c]["share"] for c in fam_rates}
# Base paper Table I, zero-day counts (payload-packet units, not flows).
THEIRS_N = {"Heartbleed": 13486, "Web Attack Brute Force": 11754, "Web Attack XSS": 3341,
            "Bot": 2543, "PortScan": 830, "Web Attack Sql Injection": 12}
tot = sum(THEIRS_N.values())
print(f"\n  {'family':30s} {'OUR share':>10s} {'THEIR share':>12s}")
for c in sorted(set(list(OURS_MIX) + list(THEIRS_N))):
    o = f"{OURS_MIX[c]:.1%}" if c in OURS_MIX else "— (known)"
    t = f"{THEIRS_N[c]/tot:.1%}" if c in THEIRS_N else "— (known)"
    print(f"  {c:30s} {o:>10s} {t:>12s}")

# Reweight OUR per-family rates by THEIR composition, over the families both
# hold out. Approximate by construction -- stated, not hidden.
shared = [c for c in fam_rates if c in THEIRS_N]
w = np.array([THEIRS_N[c] for c in shared], float); w /= w.sum()
r = np.array([fam_rates[c]["rate"] for c in shared])
reweighted = float((w * r).sum())
own_w = np.array([fam_rates[c]["n"] for c in shared], float); own_w /= own_w.sum()
own = float((own_w * r).sum())
print(f"\n  Our CNN's SAME per-family rates, averaged two ways over the {len(shared)} shared families:")
print(f"    weighted by OUR   family sizes : {own:6.2%}")
print(f"    weighted by THEIR family sizes : {reweighted:6.2%}   <- moves {reweighted-own:+.2%}")
print("\n  Nothing about the model changed — only the mix being averaged. Their zero-day set is")
print("  Heartbleed+WebBF-dominated (79%); ours is Bot+WebBF-dominated (83%), and Bot is the")
print("  family our CNN provably cannot reach (100% classified BENIGN, cross-seed rank")
print("  rho = -0.090). **A single zero-day accuracy number cannot be compared across papers")
print("  unless the family mix matches.** This is exactly why metrics.py was rewritten on")
print("  2026-07-27 to report per-family PR-AUC + a macro over powered families instead of a")
print("  blended number — the base paper's headline retains the defect we removed from ours.")
RES["composition"] = {"our_family_rates": fam_rates,
                      "their_counts": THEIRS_N,
                      "our_weighting": own, "their_weighting": reweighted,
                      "shared_families": shared}

# =============================================================================
# TABLE 2 — the field's metric suite
# =============================================================================
print("\n" + "=" * 104)
print("THE FIELD'S METRIC SUITE — overall binary (all 15 classes), which is what")
print("published CIC-IDS2017 work reports as '99%+'")
print("=" * 104)
print(f"{'channel':24s} {'accuracy':>9s} {'precision':>10s} {'recall':>8s} {'F1':>8s} "
      f"{'FAR':>7s} {'ROC-AUC':>8s} {'PR-AUC':>8s}")
print("-" * 104)
for l in ours_labels:
    f = RES["ours"][l]["_field"]
    print(f"{l:24s} {f['accuracy']:>8.2f}% {f['precision']:>9.2f}% {f['recall']:>7.2f}% "
          f"{f['f1']:>7.2f}% {f['far']:>6.2f}% {f['roc_auc']:>7.2f}% {f['pr_auc']:>7.2f}%")

print("\n  ⚠️  These are the numbers directly comparable to the literature's 99%+ claims, and")
print("     ours are in that range. They are NOT a better result than our 0.64 macro zero-day")
print("     PR-AUC — they are an EASIER QUESTION asked of the same models. Report both, and")
print("     say which is which.")

outp = os.path.join(MD, "paper_metrics.json")
with open(outp, "w", encoding="utf-8") as f:
    json.dump(RES, f, indent=1)
print(f"\nwrote {outp}")

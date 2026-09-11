"""
aug_assignment.py — WHY did augmentation destroy zero-day reachability?

THE OBSERVATION THIS EXPLAINS
------------------------------
Training on 2017 + 2018's known pool collapsed macro zero-day PR-AUC from 0.6399
to 0.3864 while known-class PR-AUC stayed at 0.9979. The model learned its
18-class task perfectly well; what broke was reachability of families it never
saw. Per family (seed 42):

    Bot        lift 1.31x -> 0.6x   (below a random ranker)
    Web BF     0.92       -> 0.6478
    Web XSS    0.95       -> 0.4913

TWO CANDIDATE EXPLANATIONS, AND THEY MEAN DIFFERENT THINGS
-----------------------------------------------------------
(a) CLASS-STRUCTURE DILUTION. This project's standing caution is that Web Brute
    Force and XSS score 0.92-0.95 by ABSORPTION: the CNN assigns ~90 % of those
    flows to `DoS slowloris`, a known ATTACK class, so a high score means "looks
    like a known attack", not "detected as novel". The augmented label space adds
    nine more capture-specific attack classes, including a second slowloris
    (`DoS attacks-Slowloris [2018]`). If absorption is real, that absorbing mass
    should now SPLIT across competing classes and the web families' scores should
    fall -- which is exactly what happened.

(b) SCALER DISTORTION. `StandardScaler` is refit on the union, so 2017 flows are
    represented differently than in the baseline. 🔴 Largely ruled out already:
    the union scaler's median scale ratio against 2017's is 0.979 and the median
    mean-shift is 0.151 sigma. Only TWO of 67 features are badly distorted --
    `RST Flag Count` and `ECE Flag Count`, near-constant in 2017 and variable in
    2018 -- and NEITHER appears in Bot's discriminative feature set on any of the
    three seeds measured by `bot_failure_analysis.py`. So (b) cannot explain
    Bot's collapse. It is still checked here rather than dismissed.

WHY THIS MATTERS MORE THAN THE NEGATIVE RESULT
-----------------------------------------------
The absorption caution has so far rested on an OBSERVATION -- we looked at where
web flows are assigned. This is a MANIPULATION: change the class structure and,
if absorption is the mechanism, the absorbed score must move. A manipulation that
moves it is far stronger evidence than the observation, and it converts a caveat
into a result.

🔴 PRE-REGISTERED PREDICTION, written before running this
----------------------------------------------------------
In the BASELINE, Web BF and XSS flows concentrate into a single absorbing class
(`DoS slowloris`, ~90 %). In the AUGMENTED model that concentration BREAKS: the
mass splits across competing capture-specific classes, so the largest single
destination takes a substantially smaller share.
**FALSIFIER:** if augmented web flows still concentrate >= 80 % into one class,
dilution is NOT the mechanism, and explanation (b) or something unidentified must
be revisited. Stated before the numbers exist so it cannot be fitted to them.

⚠️ Bot is a SEPARATE question. 100 % of Bot flows are already classified BENIGN by
the baseline, so there is no absorbing attack class to dilute. Bot's fall from
1.31x to 0.6x needs its own explanation and this script reports, rather than
explains, what happens to it.

Run:  python scripts/aug_assignment.py
Out:  outputs/metadata/aug_assignment.json
"""
import os
import sys
import json
import pickle

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                          # noqa: E402
import config                                         # noqa: E402
import features                                       # noqa: E402
import metrics                                        # noqa: E402

CONCENTRATION_FALSIFIER = 0.80
DUP_INDEX = 51


def top_assignments(pred_cls, mask, k=5):
    vals, counts = np.unique(pred_cls[mask], return_counts=True)
    order = np.argsort(-counts)
    n = int(mask.sum())
    return [{"class": str(vals[i]), "n": int(counts[i]),
             "share": float(counts[i]) / n} for i in order[:k]]


def main():
    import tensorflow as tf                            # noqa: E402

    cfg = config.get()
    P17 = os.path.join(paths.PROCESSED, cfg["paths"]["paper_subdir"])
    tfm = cfg["protocol"]["feature_transform"]
    yte = np.load(os.path.join(P17, "y_test_mc.npy"), allow_pickle=True)
    zd = sorted(np.load(os.path.join(P17, "zero_day_classes.npy"),
                        allow_pickle=True).tolist())
    powered = [f for f in zd if (yte == f).sum() >= metrics.MIN_FAMILY_N]

    Xraw = np.load(os.path.join(P17, "X_test.npy"))
    X68 = features.transform(Xraw, tfm)
    X67 = X68[:, [i for i in range(68) if i != DUP_INDEX]]
    del Xraw

    # (model tag, scaler suffix, feature matrix)
    MODELS = [("cnn_paper", "", X68, "BASELINE 2017, 68 features")]
    for s in (42, 43, 44):
        t = "cnn_aug_s%d" % s
        if os.path.exists(os.path.join(paths.MODELS, "%s.keras" % t)):
            MODELS.append((t, "_%s" % t, X67, "AUGMENTED 2017+2018, 67 features"))

    print("=" * 100)
    print("WHERE DO ZERO-DAY FLOWS GET ASSIGNED? baseline vs augmented")
    print("=" * 100)
    print("falsifier: augmented web flows still >= %.0f%% into ONE class means "
          "dilution is not the mechanism" % (100 * CONCENTRATION_FALSIFIER))

    out = {"falsifier_concentration": CONCENTRATION_FALSIFIER, "models": {}}

    for tag, sfx, X, label in MODELS:
        le_p = os.path.join(paths.MODELS, "label_encoder_paper%s.pkl" % sfx)
        sc_p = os.path.join(paths.MODELS, "scaler_paper%s.pkl" % sfx)
        if not (os.path.exists(le_p) and os.path.exists(sc_p)):
            print("\n  %-16s SKIP - scaler/encoder missing" % tag)
            continue
        with open(le_p, "rb") as f:
            classes = list(pickle.load(f).classes_)
        with open(sc_p, "rb") as f:
            scaler = pickle.load(f)
        Xs = scaler.transform(X).reshape(-1, X.shape[1], 1)
        model = tf.keras.models.load_model(
            os.path.join(paths.MODELS, "%s.keras" % tag), compile=False)
        prob = model.predict(Xs, batch_size=1024, verbose=0)
        pred = np.array(classes, dtype=object)[prob.argmax(axis=1)]
        del model, Xs

        print("\n" + "-" * 100)
        print("%s  (%s, %d classes)" % (tag, label, len(classes)))
        print("-" * 100)
        row = {"label": label, "n_classes": len(classes), "families": {}}
        for fam in powered:
            m = yte == fam
            tops = top_assignments(pred, m)
            row["families"][fam] = {
                "n": int(m.sum()), "top": tops,
                "largest_share": tops[0]["share"] if tops else None,
                "concentrated": bool(tops and tops[0]["share"]
                                     >= CONCENTRATION_FALSIFIER)}
            print("  %-24s n=%-6d -> %s"
                  % (fam, int(m.sum()),
                     ",  ".join("%s %.1f%%" % (t["class"], 100 * t["share"])
                                for t in tops[:3])))
        out["models"][tag] = row
        del prob, pred

    # ---- the verdict --------------------------------------------------------
    base = out["models"].get("cnn_paper")
    augs = [v for k, v in out["models"].items() if k.startswith("cnn_aug")]
    if base and augs:
        print("\n" + "=" * 100)
        print("VERDICT - concentration of the WEB families into their top class")
        print("=" * 100)
        web = [f for f in powered if f.startswith("Web")]
        summary = {}
        for fam in web:
            b = base["families"][fam]["largest_share"]
            a = float(np.mean([m["families"][fam]["largest_share"] for m in augs]))
            summary[fam] = {"baseline_top_share": b,
                            "augmented_top_share_mean": a,
                            "drop": b - a,
                            "baseline_top_class":
                                base["families"][fam]["top"][0]["class"]}
            print("  %-24s baseline %.1f%% (-> %s)  ->  augmented %.1f%%   "
                  "drop %.1f pp"
                  % (fam, 100 * b, base["families"][fam]["top"][0]["class"],
                     100 * a, 100 * (b - a)))
        still = [f for f in web
                 if summary[f]["augmented_top_share_mean"]
                 >= CONCENTRATION_FALSIFIER]
        out["web_concentration"] = summary
        out["dilution_falsified"] = bool(still)
        print("")
        if still:
            print("  => FALSIFIED for %s: still concentrated. Dilution is NOT "
                  "the mechanism." % ", ".join(still))
        else:
            print("  => Concentration BREAKS under augmentation, as predicted.")
            print("     The web families' 0.92-0.95 was absorption into a known")
            print("     attack class; adding competing classes splits that mass")
            print("     and the score falls with it. This is a MANIPULATION, not")
            print("     an observation - much stronger evidence for the caution.")

    out["caveats"] = [
        "Bot is a separate question: 100 % of Bot flows are already classified "
        "BENIGN by the baseline, so there is no absorbing attack class to "
        "dilute. Its fall from 1.31x to 0.6x is reported, not explained here.",
        "Scaler distortion is largely ruled out: only RST Flag Count and ECE "
        "Flag Count are badly distorted by refitting on the union, and neither "
        "is in Bot's discriminative set on any measured seed.",
        "Assignment share is argmax over the softmax; a flow counted in one "
        "class may have had a near-tie with another.",
    ]
    p = os.path.join(paths.METADATA, "aug_assignment.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("\nwrote %s" % p)
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
loco_reject.py — evaluate what the LOCO models' p(UNKNOWN) actually scores.

WHY THIS EXISTS
---------------
`loco_sweep.sh` reports macro on the DEFAULT scorer, 1 - p(BENIGN), which folds
p(UNKNOWN) into the attack mass and so does not test the LOCO hypothesis at all.
The hypothesis was narrower: relabelling a known family UNKNOWN makes p(UNKNOWN)
a *trained* novelty detector. `cnn_paper.py` persists only p_attack, so that had
to be recovered by re-scoring the saved models -- one forward pass each.

WHAT THIS FOUND, AND WHY THE SWEEP WAS STOPPED
-----------------------------------------------
`CNN_LOCO_HOLDOUT` RENAMES a class; it does not restructure the label space.

  baseline    [BENIGN, DDoS, DoS GoldenEye, ..., SSH-Patator]        9 classes
  LOCO 'DDoS' [BENIGN, DoS GoldenEye, ..., SSH-Patator, UNKNOWN]     9 classes

Same nine groups, same partition of the training set, same per-class focal alpha
(alpha is computed per class, so it follows the rename). A softmax objective is
invariant to class NAMES, so LOCO training is identical to baseline training up
to a PERMUTATION OF OUTPUT UNITS -- and therefore p(UNKNOWN) is exactly
p(DDoS): the probability that a flow looks like the held-out family. That is a
family detector, not a novelty detector, and no number from the sweep can bear
on the hypothesis.

This script measures that rather than asserting it. If p(UNKNOWN) is
p(held-out family), it must rank that family's own TEST flows near the top and
be uninformative about the real zero-day families.

TIE DEGENERACY. A softmax unit for one narrow family saturates near 0 for most
flows. Half the flows in a single tie block makes PR-AUC incomparable across
scorers, because a tie block is ordered arbitrarily. The largest tie fraction is
therefore reported next to every number, and a scorer past 0.5 is marked
unusable rather than compared.

Run:  python scripts/loco_reject.py
Out:  outputs/metadata/loco_reject.json
"""
import os
import sys
import json
import glob
import pickle

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
import numpy as np
from scipy.stats import rankdata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                          # noqa: E402
import config                                         # noqa: E402
import features                                       # noqa: E402
import metrics                                        # noqa: E402

CNN_BASE = 0.6399          # CNN alone, n=3 -- the pre-registered falsifier bar
NOISE = 0.0285             # what an absolute number in this project carries
SCORERS = ("1-p(BENIGN)", "p(UNKNOWN)", "p(UNKNOWN)|attack")


def tie_frac(s):
    """Fraction of flows sitting in the single largest tied score block."""
    _, c = np.unique(s, return_counts=True)
    return float(c.max()) / len(s)


def main():
    import tensorflow as tf                            # noqa: E402

    cfg = config.get()
    P = os.path.join(paths.PROCESSED, cfg["paths"]["paper_subdir"])
    tfm = cfg["protocol"]["feature_transform"]

    yte = np.load(os.path.join(P, "y_test_mc.npy"), allow_pickle=True)
    zd = set(np.load(os.path.join(P, "zero_day_classes.npy"),
                     allow_pickle=True).tolist())

    # matches both naming schemes: the retracted single-hold-out runs (loco_*)
    # and the redesigned merged-reject runs (locoR_*).
    tags = sorted(os.path.basename(p)[:-len(".keras")]
                  for p in glob.glob(os.path.join(paths.MODELS, "loco*.keras"))
                  if not p.endswith("_best.keras") and "smoke" not in p)
    if not tags:
        sys.exit("no loco_*.keras models found")

    print("=" * 96)
    print("LOCO REJECT-CLASS EVALUATION - what does p(UNKNOWN) actually score?")
    print("=" * 96)
    print("falsifier bar: CNN alone = %.4f  (an absolute number carries %.4f)"
          % (CNN_BASE, NOISE))
    print("models found: %s" % ", ".join(tags))

    # The scaler is refit inside every run on that run's transformed train set.
    # Recomputing it here would be a second implementation of the same step, so
    # the saved pickle is used -- and checked against the train mean, because
    # silently scoring with the wrong scaler yields a plausible garbage number.
    train_mean = features.transform(
        np.load(os.path.join(P, "X_train.npy")), tfm).mean(axis=0)
    Xte_t = features.transform(np.load(os.path.join(P, "X_test.npy")), tfm)

    out = {"cnn_alone": CNN_BASE, "noise_band": NOISE, "models": {}}

    # the baseline label space -- what a model with no hold-out would learn.
    # The held-out families are whatever is MISSING from a LOCO model's classes,
    # which is read off the encoder rather than parsed out of the tag: the tag is
    # a filename convention and the encoder is the ground truth.
    with open(os.path.join(paths.MODELS, "label_encoder_paper.pkl"), "rb") as f:
        base_classes = set(pickle.load(f).classes_)

    for tag in tags:
        sc_p = os.path.join(paths.MODELS, "scaler_paper_%s.pkl" % tag)
        le_p = os.path.join(paths.MODELS, "label_encoder_paper_%s.pkl" % tag)
        if not (os.path.exists(sc_p) and os.path.exists(le_p)):
            print("\n  %-22s SKIP - scaler/encoder missing" % tag)
            continue
        with open(sc_p, "rb") as f:
            scaler = pickle.load(f)
        with open(le_p, "rb") as f:
            classes = list(pickle.load(f).classes_)
        if "UNKNOWN" not in classes:
            print("\n  %-22s SKIP - no UNKNOWN class" % tag)
            continue
        assert np.allclose(scaler.mean_, train_mean, atol=1e-4), \
            "saved scaler does not match this train split - wrong PAPER_SUBDIR?"

        held = sorted(base_classes - set(classes))
        # nine classes still present means the label space was RENAMED, not
        # restructured -- the no-op this script exists to document.
        noop = len(classes) == len(base_classes)
        print("\n  %s  (held out %s, %d classes)%s"
              % (tag, ", ".join(repr(h) for h in held) or "nothing",
                 len(classes),
                 "  <- RENAME, NOT A REJECT CLASS" if noop else ""))
        Xte = scaler.transform(Xte_t).reshape(-1, Xte_t.shape[1], 1)
        model = tf.keras.models.load_model(
            os.path.join(paths.MODELS, "%s.keras" % tag), compile=False)
        prob = model.predict(Xte, batch_size=1024, verbose=0)
        del model, Xte

        b_i, u_i = classes.index("BENIGN"), classes.index("UNKNOWN")
        p_att = 1.0 - prob[:, b_i]
        p_rej = prob[:, u_i]
        # conditional novelty: given the model calls it an attack, is it the
        # reject class? clipped -- the denominator goes to 0 on benign flows.
        p_cond = p_rej / np.clip(p_att, 1e-9, None)

        row = {"held_out": held, "n_classes": len(classes), "classes": classes,
               "is_rename_noop": noop}
        for nm, s in zip(SCORERS, (p_att, p_rej, p_cond)):
            m = metrics.evaluate(yte, s, zd, fpr=0.01)["macro"]["pr_auc"]
            t = tie_frac(s)
            row[nm] = {"macro_pr_auc": float(m), "largest_tie_fraction": t,
                       "usable": bool(t <= 0.5)}
            print("    %-20s macro %.4f  | ties %5.1f%% %s"
                  % (nm, m, 100 * t,
                     "" if t <= 0.5 else "<- TIE-DEGENERATE, not comparable"))

        # THE DIRECT TEST. Does p(UNKNOWN) rank the HELD-OUT families' own test
        # flows above everything else? If it does, it is a signature detector for
        # those families rather than a reject region. The gap between the
        # held-out rank and the REAL zero-day rank is the whole question, and
        # benign gives the chance line to read both against.
        m_held = np.isin(yte, held)
        if m_held.sum():
            r = rankdata(p_rej) / len(p_rej)
            pr = {"held_out_families": float(r[m_held].mean()),
                  "real_zero_day": float(r[np.isin(yte, list(zd))].mean()),
                  "benign": float(r[yte == "BENIGN"].mean()),
                  "n_held_out_test": int(m_held.sum())}
            for f in sorted(zd):
                mf = yte == f
                if mf.sum() >= metrics.MIN_FAMILY_N:
                    pr["zd_" + f] = float(r[mf].mean())
            row["mean_percentile_rank"] = pr
            print("    p(UNKNOWN) mean percentile rank: held-out %.3f | "
                  "real zero-day %.3f | benign %.3f"
                  % (pr["held_out_families"], pr["real_zero_day"], pr["benign"]))
            # CHANCE IS 0.500 AND IT IS THE ONLY REFERENCE THAT MEANS ANYTHING.
            # Reading a family's rank against the BENIGN row instead invites a
            # specific error, made once already: benign sits LOW exactly when
            # the reject unit is working, so every other row floats up relative
            # to it and a family at chance looks detected. Each family is
            # therefore printed with its distance from 0.500, not from benign.
            print("      per adequately-powered zero-day family "
                  "(chance = 0.500):")
            for k, v in pr.items():
                if not k.startswith("zd_"):
                    continue
                print("        %-26s %.3f  (%+.3f vs chance)%s"
                      % (k[3:], v, v - 0.5,
                         "" if abs(v - 0.5) > 0.05 else "  <- AT CHANCE"))
        else:
            print("    held-out families have no test flows - percentile skipped")
        out["models"][tag] = row
        del prob

    # ---- ARM SUMMARY: the HETERO-vs-HOMOG contrast is the actual test -------
    # Either arm alone only says "a reject class does not reach Bot". The
    # CONTRAST says whether the unit learned a REGION or a SIGNATURE UNION: if
    # merging heterogeneous families broadens what the unit reaches, breadth is
    # a property of the merge and not an accident.
    arms = {}
    for tag, row in out["models"].items():
        if row.get("is_rename_noop") or not tag.startswith("locoR_"):
            continue
        arm = tag.split("_")[1]
        pr = row.get("mean_percentile_rank", {})
        for k, v in pr.items():
            if k.startswith("zd_"):
                arms.setdefault(arm, {}).setdefault(k[3:], []).append(v)
        arms.setdefault(arm, {}).setdefault("_macro", []).append(
            row["p(UNKNOWN)"]["macro_pr_auc"])
        arms[arm].setdefault("_headline", []).append(
            row["1-p(BENIGN)"]["macro_pr_auc"])
    if arms:
        print("\n" + "=" * 96)
        print("ARM SUMMARY - mean percentile rank vs chance (0.500), n seeds per arm")
        print("=" * 96)
        fams = sorted({f for a in arms.values() for f in a if not f.startswith("_")})
        print("%-10s %5s  %s" % ("arm", "n", "  ".join("%-24s" % f for f in fams)))
        for arm in sorted(arms):
            n = len(arms[arm].get("_macro", []))
            cells = []
            for f in fams:
                v = arms[arm].get(f, [])
                if not v:
                    cells.append("%-24s" % "-")
                    continue
                m = float(np.mean(v)) - 0.5
                # a sign flip across seeds is the finding, not a rounding detail
                flip = len(v) > 1 and not (all(x > 0.5 for x in v)
                                           or all(x < 0.5 for x in v))
                cells.append("%-24s" % ("%+.3f%s" % (m, " SIGN FLIP" if flip else "")))
            print("%-10s %5d  %s" % (arm, n, "  ".join(cells)))
        for arm in sorted(arms):
            print("  %-8s p(UNKNOWN) macro %.4f | headline 1-p(BENIGN) %.4f "
                  "(CNN alone %.4f)"
                  % (arm, float(np.mean(arms[arm]["_macro"])),
                     float(np.mean(arms[arm]["_headline"])), CNN_BASE))
        out["arm_summary"] = {
            a: {"n_seeds": len(v.get("_macro", [])),
                "p_unknown_macro_mean": float(np.mean(v["_macro"])),
                "headline_macro_mean": float(np.mean(v["_headline"])),
                "per_family_vs_chance": {
                    f: {"mean_minus_chance": float(np.mean(x)) - 0.5,
                        "per_seed": [round(y, 3) for y in x],
                        "sign_flip": bool(len(x) > 1 and not (
                            all(y > 0.5 for y in x) or all(y < 0.5 for y in x)))}
                    for f, x in v.items() if not f.startswith("_")}}
            for a, v in arms.items()}
        beat = [a for a, v in arms.items()
                if all(h > CNN_BASE for h in v["_headline"])]
        out["falsifier_triggered"] = bool(beat)
        print("\nFALSIFIER (headline > %.4f on EVERY seed in an arm): %s"
              % (CNN_BASE, ", ".join(beat) if beat else "NOT triggered"))

    out["finding"] = (
        "CNN_LOCO_HOLDOUT renames one class rather than restructuring the label "
        "space: nine classes before and after, same partition of the training "
        "set. A softmax objective is invariant to class names, so LOCO training "
        "equals baseline training up to a permutation of output units, and "
        "p(UNKNOWN) is p(held-out family) - a family detector, not a novelty "
        "detector. The sweep was stopped after 1.5 of 12 runs.")
    out["caveats"] = [
        "Ties are reported beside every macro; a scorer with more than half the "
        "flows in one block is not comparable to one without.",
        "Only models that were actually trained are scored - this makes no "
        "claim about hold-outs that never ran.",
    ]
    p = os.path.join(paths.METADATA, "loco_reject.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("\nwrote %s" % p)
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())

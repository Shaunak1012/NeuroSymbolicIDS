"""
build_augmented.py — EXPERIMENT 5: widen the learned basis with 2018's known classes.

THE HYPOTHESIS, AND WHY IT IS PRINCIPLED RATHER THAN "MORE DATA"
----------------------------------------------------------------
Section 4 says a novel class is reachable exactly to the extent its signature
overlaps the basis a closed-set model learned -- the features that separate the
classes it was TRAINED on. That makes "train on a wider set of known attack
families" the one intervention aimed at the mechanism itself rather than at its
symptoms. Every other thing swept (4 deep architectures, 7 classical baselines,
4 benign-only methods, 9 OOD scorers, 2 reject-class designs) leaves the basis
untouched and tries to squeeze more out of it.

WHAT THIS BUILDS
----------------
data/processed/paper_aug/ -- the 2017 paper split with 2018's known pool added to
TRAIN and VAL, and the TEST SET LEFT EXACTLY AS 2017's. The question is whether
2017's six zero-day families become more reachable, so 2017's test set and
2017's zero-day definition are the fixed measuring stick.

Then:  PAPER_SUBDIR=paper_aug CNN_TAG=cnn_aug_s42 python scripts/cnn_paper.py

FOUR DESIGN DECISIONS, EACH WITH A REASON THAT CAN BE CHECKED
-------------------------------------------------------------
1. **67 features, not 68.** 2017's 68th feature is `Fwd Header Length.1`, a
   DUPLICATE column that CICFlowMeter emitted twice and this project carried.
   Verified byte-identical to `Fwd Header Length` across all 883,796 training
   rows, so dropping it loses nothing. 2018's 67 columns are then 2017's
   remaining 67 in IDENTICAL ORDER, with no constant columns dropped on either
   side -- checked here, not assumed.

2. **BENIGN is MERGED across captures; attack names stay DISTINCT.**
   Merging benign is load-bearing, not cosmetic: if 2018 contributed only attack
   flows, then "came from 2018" would perfectly predict "is an attack", and the
   model could satisfy the objective by learning capture artefacts (a different
   network, a different CICFlowMeter build) instead of attack structure. Having
   2018 contribute BOTH benign and attack flows blocks that shortcut.
   Attack names stay distinct because `DoS attacks-Hulk` is not a rerun of
   `DoS Hulk` -- collapsing them would assert an equivalence nobody measured.

3. **No leak, and it is asserted rather than trusted.** 2018's own split already
   holds out Bot, Brute Force -Web, Brute Force -XSS, Infilteration and SQL
   Injection -- which is precisely the set that is zero-day in 2017. So the trap
   ("training on raw 2018 leaks five of 2017's six zero-day families") applies to
   the raw CSVs and NOT to this split. That is checked below and the build dies
   if it ever stops being true.

4. **TEST IS UNTOUCHED 2017.** No 2018 flow enters test, and the zero-day
   definition stays 2017's, so every number remains comparable to every other
   number in this project.

PRE-REGISTERED PREDICTION, written before the first run
--------------------------------------------------------
🔴 **This fails on Bot.** 2018's known pool is DDoS / DoS / FTP-BruteForce /
SSH-Bruteforce -- the same attack CATEGORIES 2017 already trains on. The basis
widens in directions it already covered, and Bot's discriminative features have
0/8 overlap with that task. Expect Bot unchanged and at most small movement on
the web families.
**Falsifier:** macro zero-day PR-AUC beating the CNN PAIRED against the
seed-matched baseline on 3/3 seeds. (Paired, because comparing to the n=3 mean
0.6399 is the unpaired error that nearly produced a false positive in the LOCO
experiment.)

⚠️ THE CONTROL, SPECIFIED NOW SO IT CANNOT BE CHOSEN AFTER SEEING THE RESULT.
This arm confounds "wider basis" with "twice the data". If and only if WIDE moves
the headline, a NARROW arm follows: the same NUMBER of added 2018 flows drawn
from a single family group (the three DDoS variants), so volume is held constant
and only basis width differs -- the same HETERO/HOMOG logic that made the
reject-class experiment interpretable. A null result needs no such control, which
is why it is not built yet.

Run:  python scripts/build_augmented.py
Out:  data/processed/paper_aug/ + outputs/metadata/build_augmented.json
"""
import os
import sys
import json

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                          # noqa: E402
import config                                         # noqa: E402

DUP_FEATURE = "Fwd Header Length.1"
OUT_SUBDIR = "paper_aug"
CTRL_SUBDIR = "paper_67"


def main():
    cfg = config.get()
    P17 = os.path.join(paths.PROCESSED, cfg["paths"]["paper_subdir"])
    P18 = os.path.join(paths.PROCESSED, "paper_2018")
    OUT = os.path.join(paths.PROCESSED, OUT_SUBDIR)
    for p in (P17, P18):
        if not os.path.isdir(p):
            sys.exit("missing %s" % p)
    os.makedirs(OUT, exist_ok=True)

    print("=" * 96)
    print("EXPERIMENT 5 - augmented training set (2017 + 2018's known pool)")
    print("=" * 96)

    # ---- 1. locate the duplicate column and prove it is a duplicate ---------
    meta18 = os.path.join(paths.METADATA, "preprocess_2018.json")
    with open(meta18, encoding="utf-8") as f:
        names18 = json.load(f)["feature_names"]
    names17 = list(np.load(os.path.join(P17, "feature_names.npy"),
                           allow_pickle=True)) \
        if os.path.exists(os.path.join(P17, "feature_names.npy")) else None
    if names17 is None:
        # the 2017 split does not persist names; recover them the way check.py
        # does, from the cleaned CSV header, so this never drifts from reality
        import pandas as pd
        hdr = pd.read_csv(os.path.join(paths.PROCESSED, "features_train.csv"),
                          nrows=0)
        names17 = [c.strip() for c in hdr.columns]
    if len(names17) != 68:
        sys.exit("expected 68 2017 features, found %d" % len(names17))
    dup_i = names17.index(DUP_FEATURE)
    keep17 = [i for i in range(68) if i != dup_i]
    if [names17[i] for i in keep17] != names18:
        sys.exit("feature order mismatch between 2017 (minus the duplicate) "
                 "and 2018 - refusing to build a silently misaligned set")
    print("features: 2017 68 -> drop %r at index %d -> 67, order matches 2018"
          % (DUP_FEATURE, dup_i))

    # ---- 2. the leak check, asserted -----------------------------------------
    zd17 = set(np.load(os.path.join(P17, "zero_day_classes.npy"),
                       allow_pickle=True).tolist())
    for split in ("train", "val"):
        y = np.load(os.path.join(P18, "y_%s_mc.npy" % split), allow_pickle=True)
        leak = sorted(set(y.tolist()) & zd17)
        if leak:
            sys.exit("LEAK: 2018 %s contains 2017 zero-day families %s"
                     % (split, leak))
    print("leak check: 2018 train/val contain none of 2017's zero-day families")
    print("  (2017 zero-day: %s)" % ", ".join(sorted(zd17)))

    # ---- 3. build ------------------------------------------------------------
    rec = {"features": {"n": 67, "dropped_from_2017": DUP_FEATURE,
                        "dropped_index": dup_i},
           "zero_day_classes": sorted(zd17), "splits": {}}

    for split in ("train", "val"):
        X17 = np.load(os.path.join(P17, "X_%s.npy" % split))[:, keep17]
        y17 = np.load(os.path.join(P17, "y_%s_mc.npy" % split), allow_pickle=True)
        X18 = np.load(os.path.join(P18, "X_%s.npy" % split))
        y18 = np.load(os.path.join(P18, "y_%s_mc.npy" % split), allow_pickle=True)
        if X17.shape[1] != X18.shape[1]:
            sys.exit("width mismatch %d vs %d" % (X17.shape[1], X18.shape[1]))

        # 2018 attack classes get a capture suffix; BENIGN does NOT -- see the
        # docstring. Without the suffix `DoS attacks-Hulk` and `DoS Hulk` would
        # stay distinct anyway (different strings), but the suffix makes the
        # provenance of every label legible in a confusion matrix.
        y18t = np.array(["BENIGN" if v == "BENIGN" else "%s [2018]" % v
                         for v in y18], dtype=object)

        X = np.concatenate([X17, X18], axis=0)
        y = np.concatenate([y17, y18t], axis=0)
        np.save(os.path.join(OUT, "X_%s.npy" % split), X)
        np.save(os.path.join(OUT, "y_%s_mc.npy" % split), y)
        n_ben = int((y == "BENIGN").sum())
        rec["splits"][split] = {"n_2017": int(len(y17)), "n_2018": int(len(y18t)),
                                "n_total": int(len(y)), "n_classes":
                                int(len(set(y.tolist()))),
                                "benign_fraction": n_ben / len(y)}
        print("%-6s 2017 %s + 2018 %s = %s rows, %d classes, benign %.1f%%"
              % (split, format(len(y17), ","), format(len(y18t), ","),
                 format(len(y), ","), len(set(y.tolist())),
                 100.0 * n_ben / len(y)))
        del X, y, X17, X18

    # ---- 4. test is UNTOUCHED 2017, minus the duplicate column ---------------
    Xte = np.load(os.path.join(P17, "X_test.npy"))[:, keep17]
    yte = np.load(os.path.join(P17, "y_test_mc.npy"), allow_pickle=True)
    np.save(os.path.join(OUT, "X_test.npy"), Xte)
    np.save(os.path.join(OUT, "y_test_mc.npy"), yte)
    np.save(os.path.join(OUT, "zero_day_classes.npy"),
            np.array(sorted(zd17), dtype=object))
    ytr = np.load(os.path.join(OUT, "y_train_mc.npy"), allow_pickle=True)
    np.save(os.path.join(OUT, "known_classes.npy"),
            np.array(sorted(set(ytr.tolist())), dtype=object))
    rec["splits"]["test"] = {"n_total": int(len(yte)), "source": "2017 only",
                             "note": "no 2018 flow enters test; the zero-day "
                                     "definition stays 2017's"}
    print("test   2017 only, %d rows - unchanged measuring stick" % len(yte))

    print("\ntraining classes (%d):" % len(set(ytr.tolist())))
    import collections
    for k, v in sorted(collections.Counter(ytr.tolist()).items(),
                       key=lambda kv: -kv[1]):
        print("   %-34s %8d" % (k, v))

    # ---- 5. THE FEATURE-COUNT CONTROL ---------------------------------------
    # The augmented model takes 67 inputs; every existing baseline takes 68. The
    # dropped column carries no information (byte-identical duplicate), but the
    # architecture is not identical -- 67 vs 68 changes the conv/flatten
    # dimensions. Without a 2017-ONLY 67-feature arm, any difference could be
    # attributed to that rather than to the wider basis. Built here, before any
    # result exists, so the control cannot be chosen after seeing the outcome.
    CTRL = os.path.join(paths.PROCESSED, CTRL_SUBDIR)
    os.makedirs(CTRL, exist_ok=True)
    for split in ("train", "val", "test"):
        np.save(os.path.join(CTRL, "X_%s.npy" % split),
                np.load(os.path.join(P17, "X_%s.npy" % split))[:, keep17])
        np.save(os.path.join(CTRL, "y_%s_mc.npy" % split),
                np.load(os.path.join(P17, "y_%s_mc.npy" % split),
                        allow_pickle=True))
    for f in ("zero_day_classes.npy", "known_classes.npy"):
        src = os.path.join(P17, f)
        if os.path.exists(src):
            np.save(os.path.join(CTRL, f),
                    np.load(src, allow_pickle=True))
    rec["control"] = {"subdir": CTRL_SUBDIR, "source": "2017 only, 67 features",
                      "why": ("isolates the augmentation from the 67-vs-68 "
                              "input-width change; the dropped column is a "
                              "verified duplicate but the architecture is not "
                              "identical")}
    print("\ncontrol: wrote %s (2017 only, 67 features)" % CTRL)

    rec["caveats"] = [
        "This arm confounds 'wider basis' with 'twice the data'. The NARROW "
        "control (equal added volume from a single family group) is specified "
        "in the docstring and is built only if WIDE moves the headline.",
        "2018's known pool is DDoS/DoS/FTP-BruteForce/SSH-Bruteforce - the same "
        "categories 2017 already trains on - so the basis widens in directions "
        "it already covered.",
        "2018 class counts are lower bounds: 7 of 10 published CSVs are "
        "Excel-truncated at 2^20 rows, chronologically.",
        "The falsifier is evaluated PAIRED against the seed-matched baseline, "
        "not against the n=3 mean 0.6399.",
        "The paired baseline is the 67-FEATURE 2017-only control (paper_67), "
        "not the historical 68-feature cnn_paper: the augmented model has a "
        "different input width and therefore a different flatten dimension.",
    ]
    p = os.path.join(paths.METADATA, "build_augmented.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=2)
    print("\nwrote %s" % p)
    print("wrote %s" % OUT)
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())

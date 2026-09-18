"""
split_variants.py — how much do the reported results depend on the split? (audit D4)

WHY THIS EXISTS
---------------
Every reported result uses a stratified random split of a chronologically ordered
capture, with no grouping (audit F-02, F-03). `preprocess_paper.py` now also builds

  paper_grouped   no Flow ID (5-tuple) on both sides of the boundary
  paper_chrono    within each known class, train precedes val precedes test

and `split_variants.sh` / `ae_seeds.sh` train the CNN and the benign-only
autoencoder on each at seeds 42/43/44, deterministic. This script compares them
with the canonical split's deterministic runs (CNN `c4_log1p_s*`, AE `ae_det_s*`).

What it reports, per split:
  * known-class detection (benign vs the nine trained classes), raw and with test
    rows that duplicate a training row removed -- the number the literature quotes
  * macro zero-day PR-AUC and the three powered families, for both models
  * the double dissociation (CNN minus AE per family, paired by seed)
  * what crosses the boundary (from split_integrity*.json)

⚠️ The zero-day flows are the same in every split (they are always test-only), but
the BENIGN test flows are not. In the chronological split every benign test flow is
from Friday afternoon, so a zero-day PR-AUC there is measured against a different
benign population, not only a different model.

Run:  python scripts/split_variants.py
Out:  outputs/metadata/split_variants.json
"""
import os
import sys
import json
import pickle
import hashlib
from collections import Counter

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                        # noqa: E402
import metrics                                      # noqa: E402

SEEDS = [42, 43, 44]
FAMS = ["Bot", "Web Attack Brute Force", "Web Attack XSS"]
SPLITS = {
    "random": {"subdir": "paper", "cnn": "c4_log1p_s%d", "ae": "ae_det_s%d",
               "integrity": "split_integrity"},
    "grouped": {"subdir": "paper_grouped", "cnn": "cnn_grouped_s%d", "ae": "ae_grouped_s%d",
                "integrity": "split_integrity_paper_grouped"},
    "chronological": {"subdir": "paper_chrono", "cnn": "cnn_chrono_s%d", "ae": "ae_chrono_s%d",
                      "integrity": "split_integrity_paper_chrono"},
    # Itinerary 5.4 (FD-01, 2026-09-18): the base paper's class balancing, and its
    # size-matched control. Both keep the canonical TEST set, so every metric here
    # is directly comparable with `random` and pairs by seed.
    "balanced": {"subdir": "paper_balanced", "cnn": "cnn_balanced_s%d", "ae": "ae_balanced_s%d",
                 "integrity": "split_integrity_paper_balanced"},
    "subsampled": {"subdir": "paper_subsampled", "cnn": "cnn_subsampled_s%d",
                   "ae": "ae_subsampled_s%d", "integrity": "split_integrity_paper_subsampled"},
    # Itinerary 6.5 (FD-02, 2026-09-18): the corrected-label release with the
    # "Attempted" flows excluded -- the closest analogue of the base paper's
    # payload-filtered population. CNN runs trained on it on 2026-09-13
    # (deterministic); no autoencoder on this variant.
    "improved_exclude": {"subdir": "paper_improved_exclude", "cnn": "cnn_fixed_exclude_s%d",
                         "ae": "ae_fixed_exclude_s%d", "integrity": "split_integrity_paper_improved_exclude"},
}
# random vs grouped vs chronological are different SPLITS (different test sets);
# balanced and subsampled change only TRAINING (same test set as random).
PROTOCOL_SPLITS = ("random", "grouped", "chronological")


def pred(tag):
    p = os.path.join(paths.PREDICTIONS, "y_prob_%s_test.npy" % tag)
    return np.load(p) if os.path.exists(p) else None


def load_json(name):
    p = os.path.join(paths.METADATA, name + ".json")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def absorption(tag, P, y):
    """Where the CNN's argmax sends each zero-day family (bot_failure_analysis H1)."""
    import tensorflow as tf
    import config
    import features
    sfx_ = tag.split("cnn_paper_", 1)[-1]
    with open(os.path.join(paths.MODELS, "scaler_paper_%s.pkl" % sfx_), "rb") as f:
        sc = pickle.load(f)
    with open(os.path.join(paths.MODELS, "label_encoder_paper_%s.pkl" % sfx_), "rb") as f:
        classes = list(pickle.load(f).classes_)
    tfm = config.get()["protocol"]["feature_transform"]
    X = sc.transform(features.transform(np.load(os.path.join(P, "X_test.npy")), tfm))
    m = tf.keras.models.load_model(os.path.join(paths.MODELS, tag + ".keras"), compile=False)
    am = m.predict(X.reshape(-1, X.shape[1], 1).astype(np.float32), batch_size=4096, verbose=0).argmax(1)
    out = {}
    for fam in FAMS:
        c = Counter(classes[i] for i in am[y == fam])
        top, n = c.most_common(1)[0]
        out[fam] = {"modal_class": top, "modal_frac": n / float((y == fam).sum()),
                    "frac_BENIGN": c.get("BENIGN", 0) / float((y == fam).sum())}
    # The base paper's views (Table II), from this run's own scaler and model.
    # View 5 has no benign rows, so it is reported with the false-alarm rate.
    pred = np.array(classes, dtype=object)[am]
    known = np.isin(y, classes)
    ben = y == "BENIGN"
    zd = ~known
    pb, yb = pred != "BENIGN", y != "BENIGN"
    per_class = [float((pred[y == c] == c).mean()) for c in classes]
    out["_views"] = {
        "view1_multiclass_known_acc": 100 * float((pred[known] == y[known]).mean()),
        "view1_balanced_acc": 100 * float(np.mean(per_class)),
        "view2_binary_known_acc": 100 * float((pb[known] == yb[known]).mean()),
        "view5_zero_day_acc": 100 * float(pb[zd].mean()),
        "false_alarm_rate": 100 * float(pb[ben].mean()),
        "per_class_recall": {c: 100 * r for c, r in zip(classes, per_class)},
    }
    return out


def main():
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
    out = {"splits": {}}
    for name, cfg in SPLITS.items():
        P = os.path.join(paths.PROCESSED, cfg["subdir"])
        y = np.load(os.path.join(P, "y_test_mc.npy"), allow_pickle=True)
        zd = set(np.load(os.path.join(P, "zero_day_classes.npy"), allow_pickle=True).tolist())
        H = lambda X: [hashlib.blake2b(r.tobytes(), digest_size=16).digest() for r in X]  # noqa: E731
        tr = set(H(np.load(os.path.join(P, "X_train.npy"))))
        dup = np.fromiter((h in tr for h in H(np.load(os.path.join(P, "X_test.npy")))),
                          bool, len(y))
        ytr = np.load(os.path.join(P, "y_train_mc.npy"), allow_pickle=True)
        row = {"subdir": cfg["subdir"], "n_test": int(len(y)),
               "n_benign_test": int((y == "BENIGN").sum()),
               "train_counts": {k: int(v) for k, v in sorted(Counter(ytr.tolist()).items())},
               "models": {}}
        # Benign test flows that share a 5-tuple with a zero-day flow. The grouped
        # split has to put them in test; they are candidate hard negatives, so the
        # zero-day metric is also reported without them.
        fid = pd.read_csv(os.path.join(P, "meta_test.csv"), usecols=["Flow ID"])["Flow ID"].astype(str).values
        zf = set(fid[np.isin(y, sorted(zd))])
        hard = (y == "BENIGN") & np.isin(fid, sorted(zf))
        row["benign_sharing_zero_day_5tuple"] = int(hard.sum())
        for model in ("cnn", "ae"):
            runs = {s: pred(cfg[model] % s) for s in SEEDS}
            if any(v is None for v in runs.values()):
                row["models"][model] = {"status": "not trained yet",
                                        "missing": [cfg[model] % s for s, v in runs.items() if v is None]}
                continue
            per = []
            for s in SEEDS:
                r = metrics.evaluate(y, runs[s], zd, fpr=0.01)
                rd = metrics.evaluate(y[~dup], runs[s][~dup], zd, fpr=0.01)
                per.append({
                    "seed": s,
                    "macro": r["macro"]["pr_auc"],
                    "family": {f: r["zeroday_family"][f]["pr_auc"] for f in FAMS},
                    "known_only_pr_auc": r["views"]["known_only"]["pr_auc"],
                    "known_only_pr_auc_dedup": rd["views"]["known_only"]["pr_auc"],
                    "known_only_f1": r["views"]["known_only"]["f1"],
                    "unknown_recall_1pct": float(np.mean(
                        [r["zeroday_family"][f]["recall"] for f in FAMS])),
                    "macro_without_shared_5tuple_benign":
                        metrics.evaluate(y[~hard], runs[s][~hard], zd, fpr=0.01)["macro"]["pr_auc"],
                })
                if model == "cnn":
                    per[-1]["absorption"] = absorption(cfg[model] % s, P, y)
            mean = lambda k: float(np.mean([p[k] for p in per]))  # noqa: E731
            row["models"][model] = {
                "per_seed": per,
                "macro_mean": mean("macro"), "macro_sd": float(np.std([p["macro"] for p in per], ddof=1)),
                "family_mean": {f: float(np.mean([p["family"][f] for p in per])) for f in FAMS},
                "known_only_pr_auc_mean": mean("known_only_pr_auc"),
                "known_only_pr_auc_dedup_mean": mean("known_only_pr_auc_dedup"),
                "macro_without_shared_5tuple_benign_mean": mean("macro_without_shared_5tuple_benign"),
            }
        c, a = row["models"].get("cnn", {}), row["models"].get("ae", {})
        if "per_seed" in c and "per_seed" in a:
            dd = {}
            for f in FAMS:
                d = np.array([pc["family"][f] - pa["family"][f]
                              for pc, pa in zip(c["per_seed"], a["per_seed"])])
                dd[f] = {"cnn_minus_ae_mean": float(d.mean()),
                         "per_seed": d.round(4).tolist(),
                         "direction_consistent": bool((d > 0).all() or (d < 0).all())}
            row["double_dissociation"] = dd
        integ = load_json(cfg["integrity"])
        if integ:
            row["boundary"] = {"exact_duplicates": integ["duplicates"]["fraction"],
                               "flow_id_overlap": integ["group_overlap"]["flow_id_fraction"],
                               "test_inside_train_time_range":
                                   integ["temporal"]["test_inside_train_range"]}
        out["splits"][name] = row

    # ---- report ---------------------------------------------------------------
    print("=" * 104)
    print("SPLIT VARIANTS — deterministic CNN and autoencoder, seeds 42/43/44")
    print("=" * 104)
    print("%-14s %8s %8s %9s | %-9s %8s %8s %8s %8s | %s"
          % ("split", "dup", "5-tuple", "known PR", "model", "macro", "Bot", "WebBF", "XSS",
             "known PR (dedup)"))
    for name, row in out["splits"].items():
        b = row.get("boundary", {})
        for model in ("cnn", "ae"):
            m = row["models"].get(model, {})
            if "macro_mean" not in m:
                print("%-14s %s: %s" % (name, model, m.get("status")))
                continue
            fm = m["family_mean"]
            print("%-14s %7.1f%% %7.1f%% %9s | %-9s %8.4f %8.4f %8.4f %8.4f | %.4f"
                  % (name, 100 * b.get("exact_duplicates", float("nan")),
                     100 * b.get("flow_id_overlap", float("nan")),
                     "%.4f" % m["known_only_pr_auc_mean"], model, m["macro_mean"],
                     fm["Bot"], fm["Web Attack Brute Force"], fm["Web Attack XSS"],
                     m["known_only_pr_auc_dedup_mean"]))
        if "double_dissociation" in row:
            print("%-14s double dissociation (CNN - AE): %s" % ("", "  ".join(
                "%s %+.3f%s" % (f.replace("Web Attack ", ""), v["cnn_minus_ae_mean"],
                                "" if v["direction_consistent"] else " (inconsistent)")
                for f, v in row["double_dissociation"].items())))

    print("\nCNN absorption (mean over seeds): family -> modal class (fraction)")
    for name, row in out["splits"].items():
        c = row["models"].get("cnn", {})
        if "per_seed" not in c:
            continue
        v = {k: float(np.mean([p_["absorption"]["_views"][k] for p_ in c["per_seed"]]))
             for k in ("view1_multiclass_known_acc", "view1_balanced_acc",
                       "view2_binary_known_acc", "view5_zero_day_acc", "false_alarm_rate")}
        c["views_mean"] = v
        print("  %-14s views: known multi %.2f%% (balanced %.2f%%) | known binary %.2f%% | "
              "view 5 %.2f%% | FAR %.2f%%" % (name, v["view1_multiclass_known_acc"],
                                               v["view1_balanced_acc"], v["view2_binary_known_acc"],
                                               v["view5_zero_day_acc"], v["false_alarm_rate"]))
        parts = []
        for f in FAMS:
            ab = [p_["absorption"][f] for p_ in c["per_seed"]]
            modes = sorted({a["modal_class"] for a in ab})
            parts.append("%s -> %s %.0f%%" % (f.replace("Web Attack ", ""), "/".join(modes),
                                              100 * np.mean([a["modal_frac"] for a in ab])))
        print("  %-14s %s | macro without the %d benign flows sharing a zero-day 5-tuple: %.4f"
              % (name, "  ".join(parts), row["benign_sharing_zero_day_5tuple"],
                 c["macro_without_shared_5tuple_benign_mean"]))

    p = os.path.join(paths.METADATA, "split_variants.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print("\nwrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())

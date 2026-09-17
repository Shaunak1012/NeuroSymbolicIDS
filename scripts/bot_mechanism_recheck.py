"""
bot_mechanism_recheck.py — do the Bot-mechanism measurements survive the re-base?

WHY THIS EXISTS (audit F-01 / F-12, 2026-09-17)
-----------------------------------------------
Two of the paper's mechanism figures were measured on one population each:

  * the CNN's Bot ranking is unstable across seeds (Spearman rho = -0.090) and
    100 % of Bot flows are classified BENIGN -- measured on the three PRE-FLAG
    reference runs (cnn_paper, _s43, _s44), the same three runs that carried the
    withdrawn fusion gain;
  * "a random forest shows the same pattern" (rho = 0.068) -- measured on the
    UNTUNED forest (max_depth=20, max_features="sqrt").

On 2026-09-17 `baselines_tuned.py` selected max_features=0.3 on validation, and a
quick look showed that forest's Bot ranking at rho = +0.92 and the deterministic
CNN's probability-scale ranking at +0.51. Probability-scale ranks saturate and
tie, so the CNN comparison was not like-for-like. This script measures both
properly. ⚠️ The expectations below were written AFTER that look, so they are
not blind; they are stated so the result can be read against them.

  E1  deterministic CNN, log-odds, Bot cross-seed rho: the paper's claim needs it
      near zero; the quick look suggests it is not.
  E2  deterministic CNN still classifies (nearly) all Bot flows as BENIGN
      (absorption, H1) -- this does not depend on ranking.
  E3  tuned forest's Bot rho is high, so "a random forest shows the same pattern"
      depends on one hyperparameter.
  E4  (RECHECK_FOREST=1; written 2026-09-17 BEFORE that section was first run)
      the paper's mechanism says a closed-set learner reaches a family in
      proportion to how far its learned features overlap the family's. The tuned
      forest reaches Bot (PR-AUC 0.2196) and the default forest barely does
      (0.1311), so if the mechanism is right the tuned forest should put MORE of
      its importance on Bot's eight oracle-discriminative features, on every seed.
      If it does not, the forest's reach is not explained by overlap as we measure
      it, and the paper must say so.

Method, identical to bot_failure_analysis.py H1 / H2(b): Spearman correlation
between each pair of seeds over one family's test flows, averaged over the three
pairs; absorption = argmax class of each Bot flow. Log-odds are
logsumexp(attack logits) - benign logit, as in rescore_logits.py. Nothing is
logged to runs.jsonl (no new method).

The paper's figures come from three runs per population. The script also widens
them to every CNN run on disk -- the 11 pre-flag runs and the 6 distinct
deterministic runs -- and reports the spread over all pairs, separating
different-seed pairs from same-seed pairs (six pre-flag runs are seed 42).

Run:  python scripts/bot_mechanism_recheck.py
      RECHECK_FOREST=1 python scripts/bot_mechanism_recheck.py   # + E4, six forest fits
Out:  outputs/metadata/bot_mechanism_recheck.json
      outputs/predictions/y_prob_<run>_logodds_test.npy for runs that had none
"""
import os
import sys
import json
import pickle
import itertools

import numpy as np
from scipy.special import logsumexp
from scipy.stats import spearmanr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                        # noqa: E402
import config                                       # noqa: E402
import features                                     # noqa: E402

cfg = config.get()
P, PR = paths.PAPER, paths.PREDICTIONS
TFM = cfg["protocol"]["feature_transform"]
FAMS = ["Bot", "Web Attack Brute Force", "Web Attack XSS"]
DET_CNN = ["c4_log1p_s42", "c4_log1p_s43", "c4_log1p_s44"]
from fusion_population import PRE_FLAG, DETERMINISTIC, DUPLICATES_OF   # noqa: E402
DET_ALL = [t for t in DETERMINISTIC if t not in DUPLICATES_OF]
# cnn_paper, cnn_repro_s42 and cnn_noise_r1-4 are six runs of seed 42 (noise floor).
SEED_OF = {t: (int(t.rsplit("_s", 1)[1]) if "_s4" in t else 42) for t in PRE_FLAG + DET_ALL}
POPULATIONS = {
    "CNN, pre-flag reference (log-odds)": ["cnn_paper_logodds", "cnn_paper_s43_logodds",
                                           "cnn_paper_s44_logodds"],
    "CNN, deterministic (log-odds)": [t + "_logodds" for t in DET_CNN],
    "RandomForest, untuned (max_features=sqrt)": ["random_forest", "random_forest_s43",
                                                  "random_forest_s44"],
    "RandomForest, tuned (max_features=0.3)": ["random_forest_tuned_s42",
                                               "random_forest_tuned_s43",
                                               "random_forest_tuned_s44"],
    "Autoencoder, pre-flag": ["autoencoder_paper", "autoencoder_paper_s43",
                              "autoencoder_paper_s44"],
    "Autoencoder, deterministic": ["ae_det_s42", "ae_det_s43", "ae_det_s44"],
    "IsolationForest, untuned": ["isolation_forest", "isolation_forest_s43",
                                 "isolation_forest_s44"],
    "IsolationForest, tuned": ["isolation_forest_tuned_s42", "isolation_forest_tuned_s43",
                               "isolation_forest_tuned_s44"],
}


def forest_overlap():
    """Refit both forests exactly as logged, check the refit reproduces the logged
    predictions, and measure how much importance each puts on Bot's oracle
    features (bot_failure_analysis.json H3/H4)."""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    with open(os.path.join(paths.METADATA, "bot_failure_analysis.json"), encoding="utf-8") as f:
        h3 = json.load(f)["results"]["H3_feature_neglect"]
    bot8, known8 = h3["bot_oracle_top8"], h3["known_class_top8"]
    import csv
    with open(os.path.join(paths.PROCESSED, "features_train.csv"), encoding="utf-8") as f:
        names = next(csv.reader(f))
    Xtr = features.transform(np.load(os.path.join(P, "X_train.npy")), TFM)
    Xte = features.transform(np.load(os.path.join(P, "X_test.npy")), TFM)
    sc = StandardScaler().fit(Xtr)
    Xtr, Xte = sc.transform(Xtr), sc.transform(Xte)
    ytr = np.load(os.path.join(P, "y_train_bin.npy"))
    ib = [names.index(n) for n in bot8]
    ik = [names.index(n) for n in known8]
    res = {"bot_oracle_top8": bot8, "known_class_top8": known8}
    for cfg_name, mf, tag in (("default", "sqrt", lambda s: "random_forest" + ("" if s == 42 else "_s%d" % s)),
                              ("tuned", 0.3, lambda s: "random_forest_tuned_s%d" % s)):
        per = []
        for s in (42, 43, 44):
            m = RandomForestClassifier(n_estimators=200, max_depth=20, max_features=mf,
                                       n_jobs=-1, random_state=s).fit(Xtr, ytr)
            logged = np.load(os.path.join(PR, "y_prob_%s_test.npy" % tag(s)))
            same = bool(np.allclose(m.predict_proba(Xte)[:, 1], logged, atol=1e-6))
            imp = m.feature_importances_
            top8 = [names[i] for i in np.argsort(imp)[::-1][:8]]
            row = {"seed": s, "refit_reproduces_logged_predictions": same,
                   "top8": top8,
                   "top8_overlap_with_bot": sorted(set(top8) & set(bot8)),
                   "share_on_bot_top8": float(imp[ib].sum()),
                   "share_on_known_top8": float(imp[ik].sum())}
            per.append(row)
            print("forest %-7s s%d reproduces=%s  share on Bot's 8: %.3f  on known 8: %.3f  top-8 overlap with Bot: %d %s"
                  % (cfg_name, s, same, row["share_on_bot_top8"], row["share_on_known_top8"],
                     len(row["top8_overlap_with_bot"]), row["top8_overlap_with_bot"]))
        res[cfg_name] = {"max_features": str(mf), "per_seed": per,
                         "mean_share_on_bot_top8": float(np.mean([r["share_on_bot_top8"] for r in per])),
                         "mean_top8_overlap_with_bot": float(np.mean([len(r["top8_overlap_with_bot"]) for r in per]))}
    return res


def main():
    y = np.load(os.path.join(P, "y_test_mc.npy"), allow_pickle=True)
    out = {"method": "mean pairwise Spearman over one family's test flows (3 seeds); "
                     "absorption = argmax class of each flow",
           "absorption": {}, "rank_stability": {}}

    # ---- every CNN run on disk: log-odds + absorption ------------------------
    # The 3-run populations above are what the paper measured. The full ones are
    # the 11 pre-flag runs and the 6 distinct deterministic runs
    # (fusion_population.py). Log-odds are computed only where missing; existing
    # files (rescore_logits.py) are left untouched.
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
    import tensorflow as tf
    with open(os.path.join(paths.MODELS, "scaler_paper.pkl"), "rb") as f:
        sc = pickle.load(f)
    with open(os.path.join(paths.MODELS, "label_encoder_paper.pkl"), "rb") as f:
        classes = list(pickle.load(f).classes_)
    ben = classes.index("BENIGN")
    att = [i for i in range(len(classes)) if i != ben]
    X = sc.transform(features.transform(np.load(os.path.join(P, "X_test.npy")), TFM))
    X = X.reshape(-1, X.shape[1], 1).astype(np.float32)
    for pop, runs in (("pre_flag", PRE_FLAG), ("deterministic", DET_ALL)):
        out["absorption"][pop] = {}
        for tag in runs:
            m = tf.keras.models.load_model(os.path.join(paths.MODELS, tag + ".keras"), compile=False)
            head = m.layers[-1]
            W, b = head.get_weights()
            z = tf.keras.Model(m.input, head.input).predict(X, batch_size=4096, verbose=0) @ W + b
            lp = os.path.join(PR, "y_prob_%s_logodds_test.npy" % tag)
            if not os.path.exists(lp):
                np.save(lp, (logsumexp(z[:, att], axis=1) - z[:, ben]).astype(np.float64))
            pr = np.exp(z - logsumexp(z, axis=1, keepdims=True))
            am = pr.argmax(1)
            rec = {}
            for fam in FAMS:
                sel = y == fam
                top = np.bincount(am[sel], minlength=len(classes)).argmax()
                rec[fam] = {"frac_argmax_BENIGN": float((am[sel] == ben).mean()),
                            "mean_p_BENIGN": float(pr[sel, ben].mean()),
                            "modal_class": classes[top],
                            "modal_frac": float((am[sel] == top).mean())}
            out["absorption"][pop][tag] = rec
            print("%-16s Bot argmax=BENIGN %5.1f%% (mean p %.4f) | WebBF %s %.0f%% | XSS %s %.0f%%"
                  % (tag, 100 * rec["Bot"]["frac_argmax_BENIGN"], rec["Bot"]["mean_p_BENIGN"],
                     rec["Web Attack Brute Force"]["modal_class"],
                     100 * rec["Web Attack Brute Force"]["modal_frac"],
                     rec["Web Attack XSS"]["modal_class"], 100 * rec["Web Attack XSS"]["modal_frac"]))

    # ---- Bot rank stability over every pair of runs --------------------------
    print("\nall-pairs Spearman, per family (median [min, max]; n pairs)")
    out["all_pairs"] = {}
    for pop, runs in (("pre_flag", PRE_FLAG), ("deterministic", DET_ALL)):
        lo = {t: np.load(os.path.join(PR, "y_prob_%s_logodds_test.npy" % t)) for t in runs}
        res = {}
        for kind in ("all", "different_seed", "same_seed"):
            pairs = [(a, c) for a, c in itertools.combinations(runs, 2)
                     if kind == "all" or (SEED_OF[a] != SEED_OF[c]) == (kind == "different_seed")]
            if not pairs:
                continue
            res[kind] = {}
            for fam in FAMS + ["BENIGN"]:
                sel = y == fam
                v = np.array([spearmanr(lo[a][sel], lo[c][sel]).correlation for a, c in pairs])
                res[kind][fam] = {"n_pairs": len(v), "median": float(np.median(v)),
                                  "mean": float(v.mean()), "min": float(v.min()),
                                  "max": float(v.max()),
                                  "frac_below_0.3": float((v < 0.3).mean())}
            print("  %-13s %-15s " % (pop, kind) + "  ".join(
                "%s %+.2f [%+.2f, %+.2f]" % (f.replace("Web Attack ", "")[:5], r["median"], r["min"], r["max"])
                for f, r in res[kind].items()) + "  (n=%d)" % res[kind]["Bot"]["n_pairs"])
        out["all_pairs"][pop] = res

    # ---- rank stability, every population -----------------------------------
    print("\n%-44s %8s %8s %8s %8s" % ("population", "Bot", "WebBF", "XSS", "BENIGN"))
    for name, tags in POPULATIONS.items():
        arr = [np.load(os.path.join(PR, "y_prob_%s_test.npy" % t)).astype(np.float64) for t in tags]
        row = {}
        for fam in FAMS + ["BENIGN"]:
            s = y == fam
            pairs = [spearmanr(a[s], c[s]).correlation for a, c in itertools.combinations(arr, 2)]
            row[fam] = {"mean": float(np.mean(pairs)), "pairs": [round(float(v), 4) for v in pairs]}
        row["runs"] = tags
        out["rank_stability"][name] = row
        print("%-44s %+8.3f %+8.3f %+8.3f %+8.3f" % (name, row["Bot"]["mean"],
              row["Web Attack Brute Force"]["mean"], row["Web Attack XSS"]["mean"],
              row["BENIGN"]["mean"]))

    if os.environ.get("RECHECK_FOREST") == "1":
        out["forest_overlap"] = forest_overlap()

    rs = out["rank_stability"]
    out["expectations"] = {
        "E1_det_cnn_bot_rho_near_zero": bool(abs(rs["CNN, deterministic (log-odds)"]["Bot"]["mean"]) < 0.3),
        "E2_det_cnn_absorbs_bot": bool(min(v["Bot"]["frac_argmax_BENIGN"]
                                           for v in out["absorption"]["deterministic"].values()) > 0.8),
        "E3_tuned_rf_bot_rho_high": bool(rs["RandomForest, tuned (max_features=0.3)"]["Bot"]["mean"] > 0.5),
    }
    if "forest_overlap" in out:
        fo = out["forest_overlap"]
        out["expectations"]["E4_tuned_forest_weights_bot_features_more"] = bool(all(
            t["share_on_bot_top8"] > d["share_on_bot_top8"]
            for t, d in zip(fo["tuned"]["per_seed"], fo["default"]["per_seed"])))
    print("\n", out["expectations"])
    p = os.path.join(paths.METADATA, "bot_mechanism_recheck.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print("wrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())

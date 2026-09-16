"""
rebase_deterministic.py — re-state the headline numbers on the deterministic CNN population.

WHY THIS EXISTS (audit F-01, 2026-09-16)
----------------------------------------
Every improvement in this project is quoted against a CNN baseline of 0.6399
(seeds 42/43/44 = 0.6446 / 0.6355 / 0.6396). Those three runs were made BEFORE
`determinism.py` existed. `determinism.py` itself says pre- and post-flag runs are
different populations and must never be pooled, yet the fusion, operational and
base-paper comparisons all pair the pre-flag CNN with everything else.

The deterministic population already exists: `c4_log1p_s{42,43,44}` were trained by
`cnn_paper.py` with the default transform, 50 epochs and determinism on (the C4
A/B), and `det_verify_a/b` showed seed 42 is byte-identical across runs.
`audit_rebase.sh` lane A re-checks that against today's code.

This script re-states, on that population, everything whose headline is measured
against the CNN, and puts the old value beside every new one:

  1. CNN alone, macro zero-day PR-AUC                                  (F-01)
  2. CNN + KG rank fusion, k = 200 and 800, causal and transductive    (F-01, F-05)
  3. paired deltas against the deterministic CNN                       (F-01)
  4. the operating point taken from VALIDATION, not test               (F-07)
  5. macro at capture-faithful benign prevalence                       (F-04)
  6. the base paper's five views for the deterministic CNN             (F-01)
  7. the matched LTN comparison, once `audit_rebase.sh` has run        (CL-02)
  8. whether `<tag>.keras` and `<tag>_best.keras` hold the same weights (F-25)

The operating-point sweep and the held-out k selection are re-run by their own
scripts with `CNN_CHANNEL=c4_log1p` and read back here.

The base-paper view code is VALIDATED before it is used: it must reproduce
`paper_metrics.json`'s "CNN (ours)" column from the pre-flag models exactly.

Run:  python scripts/rebase_deterministic.py
Out:  outputs/metadata/rebase_deterministic.json
"""
import os
import sys
import json
import pickle

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
import numpy as np
from scipy.stats import rankdata
from sklearn.metrics import accuracy_score, f1_score, average_precision_score

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                        # noqa: E402
import config                                       # noqa: E402
import features                                     # noqa: E402
import metrics                                      # noqa: E402

SEEDS = [42, 43, 44]
FPR = 0.01
PREVALENCE_DRAWS = 200
OLD = {s: "cnn_paper" if s == 42 else "cnn_paper_s%d" % s for s in SEEDS}
NEW = {s: "c4_log1p_s%d" % s for s in SEEDS}
LTN_ARMS = {"ltn_repro_det": "CE + base axioms, omega=1 (the base paper's Hybrid-LTN)",
            "ltn_repro_ctrl": "CE + base axioms, omega=0 (its matched control)"}

cfg = config.get()
P, PR, MD = paths.PAPER, paths.PREDICTIONS, paths.METADATA
TFM = cfg["protocol"]["feature_transform"]


def load_json(name):
    p = os.path.join(MD, name + ".json")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def pred(tag):
    p = os.path.join(PR, "y_prob_%s_test.npy" % tag)
    return np.load(p) if os.path.exists(p) else None


def rk(x):
    return rankdata(x) / len(x)


def kg_file(k, s, causal):
    suf = "_causal" if causal else ""
    if k == 200:
        return ("kg%s" % suf) if s == 42 else ("kg_s%d%s" % (s, suf))
    return "kg_k%d_s%d%s" % (k, s, suf)


def paired(a, b):
    d = np.asarray(a) - np.asarray(b)
    sd = d.std(ddof=1)
    return {"mean_delta": float(d.mean()), "paired_sd": float(sd),
            "sigma": float(abs(d.mean()) / sd) if sd > 0 else None,
            "seeds_better": int((d > 0).sum()),
            "direction_consistent": bool((d > 0).all() or (d < 0).all())}


def main():
    import tensorflow as tf
    y = np.load(os.path.join(P, "y_test_mc.npy"), allow_pickle=True)
    yv = np.load(os.path.join(P, "y_val_mc.npy"), allow_pickle=True)
    zd = set(np.load(os.path.join(P, "zero_day_classes.npy"), allow_pickle=True).tolist())
    known = set(np.load(os.path.join(P, "known_classes.npy"), allow_pickle=True).tolist())
    ben, is_zd = y == "BENIGN", np.isin(y, list(zd))
    powered = [f for f in sorted(zd) if (y == f).sum() >= metrics.MIN_FAMILY_N]
    out = {"seeds": SEEDS, "old_population": OLD, "new_population": NEW,
           "note": "old = pre-determinism runs every existing record uses; new = "
                   "deterministic runs of the same code (determinism.py)."}

    def macro(sc, **kw):
        return metrics.evaluate(y, sc, zd, fpr=FPR, **kw)["macro"]["pr_auc"]

    # ---- 1. CNN alone ---------------------------------------------------------
    cnn_old = {s: pred(OLD[s]) for s in SEEDS}
    cnn_new = {s: pred(NEW[s]) for s in SEEDS}
    if any(v is None for v in cnn_new.values()):
        sys.exit("deterministic CNN predictions missing")
    diag = {s: metrics.evaluate(y, cnn_new[s], zd, fpr=FPR)["diagnostics"] for s in SEEDS}
    out["cnn_new_score_health"] = {str(s): diag[s] for s in SEEDS}
    m_old = np.array([macro(cnn_old[s]) for s in SEEDS])
    m_new = np.array([macro(cnn_new[s]) for s in SEEDS])
    out["cnn_alone"] = {"old_per_seed": m_old.round(4).tolist(), "old_mean": float(m_old.mean()),
                        "new_per_seed": m_new.round(4).tolist(), "new_mean": float(m_new.mean()),
                        "new_sd": float(m_new.std(ddof=1)),
                        "shift": float(m_new.mean() - m_old.mean())}
    print("1. CNN alone   old %.4f  ->  new %.4f  (per seed %s)"
          % (m_old.mean(), m_new.mean(), m_new.round(4).tolist()))

    # ---- 2/3. fusion with the KG ---------------------------------------------
    fus = {}
    for k in (200, 800):
        for causal in (True, False):
            label = "CNN + KG k=%d (%s)" % (k, "causal" if causal else "s_kg")
            kg = {s: pred(kg_file(k, s, causal)) for s in SEEDS}
            if any(v is None for v in kg.values()):
                continue
            old = np.array([macro(0.5 * rk(cnn_old[s]) + 0.5 * rk(kg[s])) for s in SEEDS])
            new = np.array([macro(0.5 * rk(cnn_new[s]) + 0.5 * rk(kg[s])) for s in SEEDS])
            fus[label] = {"online": causal,
                          "old_per_seed": old.round(4).tolist(), "old_mean": float(old.mean()),
                          "new_per_seed": new.round(4).tolist(), "new_mean": float(new.mean()),
                          "old_vs_old_cnn": paired(old, m_old),
                          "new_vs_new_cnn": paired(new, m_new)}
            p = fus[label]["new_vs_new_cnn"]
            print("2. %-26s old %.4f -> new %.4f | vs det CNN %+.4f, %.2f sigma, %d/3"
                  % (label, old.mean(), new.mean(), p["mean_delta"], p["sigma"] or 0,
                     p["seeds_better"]))
    out["fusion"] = fus

    # ---- 8. are the two saved checkpoints the same weights? -------------------
    same = {}
    for tag in (OLD[42], NEW[42]):
        a = tf.keras.models.load_model(os.path.join(paths.MODELS, tag + ".keras"), compile=False)
        b = tf.keras.models.load_model(os.path.join(paths.MODELS, tag + "_best.keras"), compile=False)
        wa, wb = a.get_weights(), b.get_weights()
        same[tag] = bool(len(wa) == len(wb) and all(np.array_equal(u, v) for u, v in zip(wa, wb)))
        del a, b
    out["checkpoint_pair_identical"] = same
    print("8. <tag>.keras == <tag>_best.keras:", same)

    # ---- shared model inputs ---------------------------------------------------
    def prepared(split, scaler_name):
        with open(os.path.join(paths.MODELS, scaler_name), "rb") as f:
            sc = pickle.load(f)
        X = sc.transform(features.transform(np.load(os.path.join(P, "X_%s.npy" % split)), TFM))
        return X.reshape(-1, X.shape[1], 1).astype(np.float32)

    # ---- 4. operating point from VALIDATION -----------------------------------
    op = {}
    for s in SEEDS:
        tag = NEW[s]
        with open(os.path.join(paths.MODELS, "label_encoder_paper_%s.pkl" % tag), "rb") as f:
            bi = list(pickle.load(f).classes_).index("BENIGN")
        mdl = tf.keras.models.load_model(os.path.join(paths.MODELS, tag + ".keras"), compile=False)
        pv = 1.0 - mdl.predict(prepared("val", "scaler_paper_%s.pkl" % tag),
                               batch_size=4096, verbose=0)[:, bi]
        del mdl
        thr_val = metrics.threshold_from(pv[yv == "BENIGN"], FPR)
        r_val = metrics.evaluate(y, cnn_new[s], zd, fpr=FPR, thr=thr_val)
        r_tst = metrics.evaluate(y, cnn_new[s], zd, fpr=FPR)
        rec = lambda r, thr: float((cnn_new[s][is_zd] >= thr).mean())   # noqa: E731
        op[str(s)] = {
            "threshold_val": thr_val, "threshold_test": r_tst["threshold"],
            "achieved_test_fpr_with_val_threshold": r_val["diagnostics"]["achieved_fpr"],
            "unknown_recall_val_threshold": rec(r_val, thr_val),
            "unknown_recall_test_threshold": rec(r_tst, r_tst["threshold"]),
            "family_recall_val_threshold": {f: r_val["zeroday_family"][f]["recall"] for f in powered},
            "family_recall_test_threshold": {f: r_tst["zeroday_family"][f]["recall"] for f in powered},
        }
    def mean_of(key):
        return float(np.mean([op[str(s)][key] for s in SEEDS]))
    out["operating_point_from_validation"] = {
        "cnn_per_seed": op,
        "achieved_test_fpr_mean": mean_of("achieved_test_fpr_with_val_threshold"),
        "unknown_recall_val_threshold_mean": mean_of("unknown_recall_val_threshold"),
        "unknown_recall_test_threshold_mean": mean_of("unknown_recall_test_threshold"),
        "fused_channels": "not definable: the KG score exists only for the test stream "
                          "(kg.py streams test), and the rank fusion normalises within the "
                          "evaluated set, so no validation threshold transfers. Stated as a "
                          "limitation rather than approximated.",
    }
    o = out["operating_point_from_validation"]
    print("4. val-derived 1%% threshold: achieved test FPR %.4f | unknown recall %.3f (test-fitted %.3f)"
          % (o["achieved_test_fpr_mean"], o["unknown_recall_val_threshold_mean"],
             o["unknown_recall_test_threshold_mean"]))

    # ---- 5. capture-faithful prevalence ---------------------------------------
    si = load_json("split_integrity")
    factor = si["benign"]["undersample_factor"] if si else 4.112
    rng = np.random.RandomState(0)
    ben_idx = np.flatnonzero(ben)
    fam_idx = {f: np.flatnonzero(y == f) for f in powered}
    draws = [{f: rng.choice(ix, max(2, int(round(len(ix) / factor))), replace=False)
              for f, ix in fam_idx.items()} for _ in range(PREVALENCE_DRAWS)]

    def faithful(sc):
        per_fam = {}
        for f, ix in fam_idx.items():
            vals = []
            for d in draws:
                yy = np.r_[np.zeros(len(ben_idx), np.int8), np.ones(len(d[f]), np.int8)]
                vals.append(average_precision_score(yy, np.r_[sc[ben_idx], sc[d[f]]]))
            per_fam[f] = float(np.mean(vals))
        return float(np.mean(list(per_fam.values()))), per_fam

    prev = {"benign_undersample_factor": factor, "draws": PREVALENCE_DRAWS, "rows": {}}
    rows = {"CNN alone": {s: cnn_new[s] for s in SEEDS}}
    for label in ("CNN + KG k=200 (causal)", "CNN + KG k=800 (causal)"):
        k = int(label.split("k=")[1].split()[0])
        rows[label] = {s: 0.5 * rk(cnn_new[s]) + 0.5 * rk(pred(kg_file(k, s, True))) for s in SEEDS}
    for label, per_seed in rows.items():
        mac, fams = [], []
        for s in SEEDS:
            m_, f_ = faithful(per_seed[s])
            mac.append(m_)
            fams.append(f_)
        prev["rows"][label] = {
            "as_reported_mean": float(np.mean([macro(per_seed[s]) for s in SEEDS])),
            "capture_faithful_mean": float(np.mean(mac)),
            "capture_faithful_per_family": {f: float(np.mean([x[f] for x in fams])) for f in powered}}
        print("5. %-26s macro %.4f as reported -> %.4f at capture prevalence"
              % (label, prev["rows"][label]["as_reported_mean"], np.mean(mac)))
    out["capture_faithful_prevalence"] = prev

    # ---- 6/7. the base paper's five views -------------------------------------
    def views(model_tag, scaler_name, encoder_name):
        with open(os.path.join(paths.MODELS, encoder_name), "rb") as f:
            classes = list(pickle.load(f).classes_)
        assert set(classes) == known
        bi = classes.index("BENIGN")
        mdl = tf.keras.models.load_model(os.path.join(paths.MODELS, model_tag + ".keras"), compile=False)
        pc = mdl.predict(prepared("test", scaler_name), batch_size=4096, verbose=0).argmax(1)
        del mdl
        pb = (pc != bi).astype(int)
        yb = (~ben).astype(int)
        tc = np.array([classes.index(c) if c in known else -1 for c in y])
        kn = ~is_zd
        return {"Multi-class 9 known classes": 100 * accuracy_score(tc[kn], pc[kn]),
                "Binary 9 known classes": 100 * accuracy_score(yb[kn], pb[kn]),
                "Multi-class 15 classes": 100 * accuracy_score(tc, pc),
                "Binary 15 classes": 100 * accuracy_score(yb, pb),
                "Binary 6 unknown classes": 100 * accuracy_score(yb[is_zd], pb[is_zd]),
                "_f1_Binary 6 unknown classes": 100 * f1_score(yb[is_zd], pb[is_zd], zero_division=0)}

    def mean_views(runs):
        return {k: float(np.mean([r[k] for r in runs])) for k in runs[0]}

    pm = load_json("paper_metrics")
    # validation: the pre-flag models must reproduce paper_metrics.json exactly
    old_views = mean_views([views(OLD[s], "scaler_paper.pkl", "label_encoder_paper.pkl")
                            for s in SEEDS])
    ref = pm["ours"]["CNN (ours)"]
    bad = {k: (v, ref[k]) for k, v in old_views.items() if abs(v - ref[k]) > 1e-9}
    out["base_paper_views_validation"] = {"reproduces_paper_metrics": not bad, "mismatch": bad}
    print("6. view code reproduces paper_metrics.json:", not bad, bad or "")
    if bad:
        sys.exit("view code does not reproduce paper_metrics.json - refusing to report")

    new_views = mean_views([views(NEW[s], "scaler_paper_%s.pkl" % NEW[s],
                                  "label_encoder_paper_%s.pkl" % NEW[s]) for s in SEEDS])
    paper = pm["paper_table_50ep"]
    out["base_paper_views"] = {
        "cnn_old": old_views, "cnn_new": new_views,
        "delta_vs_their_1d_cnn_new": {v: new_views[v] - paper[v]["1D CNN"] for v in paper},
        "delta_vs_their_1d_cnn_old": {v: old_views[v] - paper[v]["1D CNN"] for v in paper},
    }
    print("6. det CNN vs their 1D CNN: " + " / ".join(
        "%+.2f" % out["base_paper_views"]["delta_vs_their_1d_cnn_new"][v] for v in paper))

    ltn = {}
    for stem, desc in LTN_ARMS.items():
        tags = ["%s_s%d" % (stem, s) for s in SEEDS]
        if not all(os.path.exists(os.path.join(paths.MODELS, t + ".keras")) for t in tags):
            ltn[stem] = {"description": desc, "status": "not yet trained (audit_rebase.sh)"}
            continue
        # ltn_paper.py fits its scaler on train with the same transform, so the
        # reference scaler is valid (checked: identical statistics).
        runs = [views(t, "scaler_paper.pkl", "label_encoder_paper.pkl") for t in tags]
        mac = [macro(pred(t)) for t in tags]
        ltn[stem] = {"description": desc, "views_mean": mean_views(runs),
                     "view5_per_seed": [r["Binary 6 unknown classes"] for r in runs],
                     "macro_per_seed": mac, "macro_mean": float(np.mean(mac))}
    if all("views_mean" in v for v in ltn.values()):
        a, b = ltn["ltn_repro_det"], ltn["ltn_repro_ctrl"]
        ltn["matched_comparison"] = {
            "question": "does the base paper's SAT term (omega=1 vs 0, everything else equal) "
                        "raise zero-day accuracy on our data?",
            "view5_delta": paired(a["view5_per_seed"], b["view5_per_seed"]),
            "macro_delta": paired(a["macro_per_seed"], b["macro_per_seed"]),
            "base_paper_claim_pp": 12.13,
        }
        mc = ltn["matched_comparison"]
        print("7. SAT term, matched: view-5 %+.2f pp (%d/3), macro %+.4f (%d/3)"
              % (mc["view5_delta"]["mean_delta"], mc["view5_delta"]["seeds_better"],
                 mc["macro_delta"]["mean_delta"], mc["macro_delta"]["seeds_better"]))
    else:
        print("7. matched LTN comparison: waiting for audit_rebase.sh")
    out["ltn_matched"] = ltn

    # ---- the re-based downstream records, if they have been generated ---------
    for name in ("operational_best_c4_log1p", "ksweep_heldout_c4_log1p_raw"):
        r = load_json(name)
        if r is not None:
            out[name] = r
    p = os.path.join(MD, "rebase_deterministic.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print("wrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())

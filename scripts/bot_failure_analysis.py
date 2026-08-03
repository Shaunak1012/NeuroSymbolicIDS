"""
bot_failure_analysis.py — WHY does the CNN fail specifically on Bot?

The puzzle
----------
The skyline oracle (`skyline_oracle.py`) settled that this is NOT an
information-theoretic limit: revealing ~1,000 labelled Bot flows to XGBoost lifts Bot
PR-AUC from 0.0314 to **0.9764** (56x chance). The signal is fully present in the 68
per-flow features. Yet every closed-set method sits near chance on never-seen Bot:
CNN 1.3x, MSP 1.3x, XGBoost 1.8x, every LTN variant ~1-2x.

So this is a **zero-day transfer failure**, and it has no explanation. This script
tries to produce one. It is the last open research question before Phase 4.

Two further clues, both pointing the same way:
  * The CNN's *classification* is seed-stable (macro spread 0.009) while its
    *Bot-specific open-set geometry* is a lottery (cluster purity 87.9/86.6/44.4%,
    Mahalanobis Bot 1.2x-4.3x).
  * 2026-08-03: RandomForest shows the SAME signature — its score arrays correlate
    ~1.0 across seeds, yet Bot PR-AUC swings 0.0576/0.1933/0.1423 (3.4x). Two
    unrelated model families, same instability, same single family.

PRE-REGISTERED PREDICTIONS (written before the first run, 2026-08-03)
--------------------------------------------------------------------
H1 — ABSORPTION. Bot is not "uncertain"; it is confidently absorbed by a specific
     known class. Predict: >80% of Bot flows get argmax = BENIGN, and mean
     p(BENIGN | Bot) > 0.8 — i.e. the CNN actively asserts benign rather than
     spreading mass.
H2 — BOUNDARY ADJACENCY. Bot sits closer to the benign/attack decision boundary
     than the web attacks do, which is why tiny model differences reshuffle it.
     Predict: (a) Bot's attack-log-odds distribution overlaps benign's far more
     than Web BF/XSS's does; (b) Bot's per-flow rank correlation ACROSS SEEDS is
     markedly lower than Web BF/XSS's.
H3 — FEATURE NEGLECT. The features that separate Bot from benign (per the oracle:
     Destination Port, Bwd Packet Length Mean, Init_Win_bytes_forward) are NOT the
     features the known-class problem needs, so the CNN never learns to weight them.
     Predict: a known-classes-only model's top features and a Bot-vs-benign
     oracle's top features are largely disjoint (overlap <= 2 of top 8).
H4 — NOT RAW OVERLAP. Bot is not simply "closer to benign" in a way that makes the
     task hard. Predict FALSE: benign-vs-Bot is *easily* separable in raw space
     when labels are given (already known: 0.976), so raw overlap is NOT the cause.

Anti-circularity note: this project has already been burned once by measuring a
mechanism inside the CNN's own embedding space, where the statistic just restated
the CNN's decision (the +0.933 that became -0.388 in raw space). So: feature-space
claims are measured in RAW feature space; CNN-space measurements are labelled as
such and never used to explain the CNN's own behaviour.

Run:  python scripts/bot_failure_analysis.py
Writes: outputs/metadata/bot_failure_analysis.json
"""
import os
import json
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import average_precision_score, roc_auc_score
from scipy.stats import spearmanr
from xgboost import XGBClassifier

import paths, config, features

cfg = config.get()
SEED = cfg["seed"]
P = paths.PAPER
TFM = cfg["protocol"]["feature_transform"]
FAMS = ["Bot", "Web Attack Brute Force", "Web Attack XSS"]
OUT = {"predictions_preregistered": {
    "H1_absorption": ">80% of Bot argmax=BENIGN and mean p(BENIGN|Bot)>0.8",
    "H2_boundary": "Bot overlaps benign more; Bot cross-seed rank corr < web attacks'",
    "H3_feature_neglect": "known-class top features vs Bot-oracle top features overlap <=2 of 8",
    "H4_raw_overlap": "PREDICTED FALSE - Bot is easily separable in raw space given labels",
}, "results": {}}

print("=" * 100)
print("BOT FAILURE ANALYSIS")
print("=" * 100)

# ------------------------------------------------------------------ data ----
Xtr = np.load(os.path.join(P, "X_train.npy"))
Xte = np.load(os.path.join(P, "X_test.npy"))
ytr = np.load(os.path.join(P, "y_train_mc.npy"), allow_pickle=True)
yte = np.load(os.path.join(P, "y_test_mc.npy"), allow_pickle=True)
# Real feature column order comes from the preprocessed CSV header (same source
# `check.py` prints). Never hardcode indices — see CLAUDE.md.
import csv as _csv
with open(os.path.join(paths.PROCESSED, "features_train.csv"), "r", encoding="utf-8") as _f:
    feat_names = next(_csv.reader(_f))
assert len(feat_names) == Xtr.shape[1], \
    f"feature-name/column mismatch: {len(feat_names)} names vs {Xtr.shape[1]} columns"

Xtr_t = features.transform(Xtr, TFM)
Xte_t = features.transform(Xte, TFM)
sc = StandardScaler().fit(Xtr_t)
Xtr_s, Xte_s = sc.transform(Xtr_t), sc.transform(Xte_t)
is_ben_te = yte == "BENIGN"
print(f"train {Xtr.shape}  test {Xte.shape}  |  {len(feat_names)} features")

# =============================================================== H2 (b) ======
# Cross-seed rank stability, per family. Uses ONLY saved score arrays (no models).
print("\n" + "-" * 100)
print("H2(b) — CROSS-SEED RANK STABILITY per family (higher = more reproducible ranking)")
print("-" * 100)
PRED = paths.PREDICTIONS
CH = {
    "cnn_paper": ["y_prob_cnn_paper_logodds_test.npy",
                  "y_prob_cnn_paper_s43_logodds_test.npy",
                  "y_prob_cnn_paper_s44_logodds_test.npy"],
    "random_forest": ["y_prob_random_forest_test.npy",
                      "y_prob_random_forest_s43_test.npy",
                      "y_prob_random_forest_s44_test.npy"],
    "autoencoder": ["y_prob_autoencoder_paper_test.npy",
                    "y_prob_autoencoder_paper_s43_test.npy",
                    "y_prob_autoencoder_paper_s44_test.npy"],
}
rank_res = {}
for ch, files in CH.items():
    arrs = [np.load(os.path.join(PRED, f)) for f in files if os.path.exists(os.path.join(PRED, f))]
    if len(arrs) < 2:
        continue
    rank_res[ch] = {}
    for fam in FAMS:
        m = yte == fam
        # Spearman between seed pairs, computed ONLY over that family's flows:
        # "do the seeds agree on which Bot flows are most suspicious?"
        cors = [spearmanr(arrs[i][m], arrs[j][m]).correlation
                for i, j in [(0, 1), (0, 2), (1, 2)] if j < len(arrs)]
        rank_res[ch][fam] = float(np.mean(cors))
    # benign reference
    cors = [spearmanr(arrs[i][is_ben_te], arrs[j][is_ben_te]).correlation
            for i, j in [(0, 1), (0, 2), (1, 2)] if j < len(arrs)]
    rank_res[ch]["BENIGN(ref)"] = float(np.mean(cors))
    row = "  ".join(f"{k[:14]:>14s}={v:6.3f}" for k, v in rank_res[ch].items())
    print(f"  {ch:14s} {row}")
OUT["results"]["H2b_cross_seed_rank_corr"] = rank_res

# =============================================================== H4 ==========
# Raw-space separability GIVEN labels, per family (oracle view, upper bound).
print("\n" + "-" * 100)
print("H4 — RAW-SPACE SEPARABILITY GIVEN LABELS (oracle upper bound, per family)")
print("-" * 100)
rng = np.random.RandomState(SEED)
sep = {}
ben_te_idx = np.flatnonzero(is_ben_te)
for fam in FAMS:
    fi = np.flatnonzero(yte == fam)
    # split family + benign into fit/eval halves — no leakage across the split
    rng.shuffle(fi)
    bi = ben_te_idx.copy(); rng.shuffle(bi)
    bi = bi[:min(20000, len(bi))]
    fh, bh = len(fi) // 2, len(bi) // 2
    tr_i = np.concatenate([fi[:fh], bi[:bh]])
    ev_i = np.concatenate([fi[fh:], bi[bh:]])
    ytr_o = np.concatenate([np.ones(fh), np.zeros(bh)])
    yev_o = np.concatenate([np.ones(len(fi) - fh), np.zeros(len(bi) - bh)])
    clf = XGBClassifier(n_estimators=150, max_depth=6, learning_rate=0.1, n_jobs=-1,
                        tree_method="hist", eval_metric="logloss", random_state=SEED)
    clf.fit(Xte_s[tr_i], ytr_o)
    s = clf.predict_proba(Xte_s[ev_i])[:, 1]
    sep[fam] = {"oracle_pr_auc": float(average_precision_score(yev_o, s)),
                "oracle_roc_auc": float(roc_auc_score(yev_o, s)),
                "top_features": [feat_names[i] for i in np.argsort(clf.feature_importances_)[::-1][:8]]}
    print(f"  {fam:24s} oracle PR-AUC={sep[fam]['oracle_pr_auc']:.4f} "
          f"ROC={sep[fam]['oracle_roc_auc']:.4f}")
    print(f"      top-8: {', '.join(sep[fam]['top_features'])}")
OUT["results"]["H4_raw_oracle_separability"] = sep

# =============================================================== H3 ==========
# What does the KNOWN-CLASS problem actually need? Fit benign-vs-known-attack on
# TRAIN (exactly the CNN's supervision), take its top features, compare to Bot's.
print("\n" + "-" * 100)
print("H3 — FEATURE NEGLECT: does the known-class task need Bot's discriminative features?")
print("-" * 100)
sub = rng.choice(len(Xtr_s), size=min(300_000, len(Xtr_s)), replace=False)
yk = (ytr[sub] != "BENIGN").astype(int)
known_clf = XGBClassifier(n_estimators=150, max_depth=6, learning_rate=0.1, n_jobs=-1,
                          tree_method="hist", eval_metric="logloss", random_state=SEED)
known_clf.fit(Xtr_s[sub], yk)
known_top = [feat_names[i] for i in np.argsort(known_clf.feature_importances_)[::-1][:8]]
bot_top = sep["Bot"]["top_features"]
overlap = [f for f in bot_top if f in known_top]
print(f"  known-class task top-8 : {', '.join(known_top)}")
print(f"  Bot-oracle      top-8 : {', '.join(bot_top)}")
print(f"  OVERLAP ({len(overlap)}/8): {', '.join(overlap) if overlap else '(none)'}")
web_top = sep["Web Attack Brute Force"]["top_features"]
web_overlap = [f for f in web_top if f in known_top]
print(f"  [contrast] WebBF-oracle top-8 overlap with known-class task: "
      f"{len(web_overlap)}/8 -> {', '.join(web_overlap) if web_overlap else '(none)'}")
OUT["results"]["H3_feature_neglect"] = {
    "known_class_top8": known_top, "bot_oracle_top8": bot_top,
    "bot_overlap": overlap, "bot_overlap_n": len(overlap),
    "webbf_oracle_top8": web_top, "webbf_overlap": web_overlap,
    "webbf_overlap_n": len(web_overlap)}

# =============================================================== H1/H2(a) ====
# Needs the actual CNN: where does the softmax mass go, and how do the log-odds
# distributions overlap?
print("\n" + "-" * 100)
print("H1 — ABSORPTION + H2(a) — BOUNDARY ADJACENCY (requires loading the CNN)")
print("-" * 100)
try:
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    import tensorflow as tf
    import pickle

    with open(os.path.join(paths.MODELS, "label_encoder_paper.pkl"), "rb") as f:
        le = pickle.load(f)
    classes = list(le.classes_)
    ben_i = classes.index("BENIGN")
    absorb = {}
    for sfx, seed in [("", 42), ("_s43", 43), ("_s44", 44)]:
        mp = os.path.join(paths.MODELS, f"cnn_paper{sfx}.keras")
        if not os.path.exists(mp):
            continue
        model = tf.keras.models.load_model(mp, compile=False)
        nf = Xte_s.shape[1]
        probs = model.predict(Xte_s.reshape(-1, nf, 1), batch_size=8192, verbose=0)
        argmax = probs.argmax(1)
        rec = {}
        for fam in FAMS + ["BENIGN"]:
            m = yte == fam
            am = argmax[m]
            frac_ben = float((am == ben_i).mean())
            top = np.bincount(am, minlength=len(classes)).argmax()
            rec[fam] = {"frac_argmax_BENIGN": frac_ben,
                        "mean_p_BENIGN": float(probs[m, ben_i].mean()),
                        "modal_class": classes[top],
                        "modal_frac": float((am == top).mean())}
        absorb[str(seed)] = rec
        print(f"\n  --- CNN seed {seed} ---")
        for fam in FAMS + ["BENIGN"]:
            r = rec[fam]
            print(f"    {fam:24s} argmax=BENIGN {r['frac_argmax_BENIGN']:6.1%} | "
                  f"mean p(BENIGN)={r['mean_p_BENIGN']:.4f} | "
                  f"modal={r['modal_class']} ({r['modal_frac']:.1%})")
    OUT["results"]["H1_absorption"] = absorb

    # H2(a): overlap of attack-log-odds distributions with benign
    lo = np.load(os.path.join(PRED, "y_prob_cnn_paper_logodds_test.npy"))
    ben_scores = lo[is_ben_te]
    q = {}
    for fam in FAMS:
        fs = lo[yte == fam]
        # fraction of family flows scoring below the benign MEDIAN — i.e. flows the
        # model finds *less* suspicious than a typical benign flow
        q[fam] = {"frac_below_benign_median": float((fs < np.median(ben_scores)).mean()),
                  "median_score": float(np.median(fs)),
                  "auc_vs_benign": float(roc_auc_score(
                      np.r_[np.zeros(len(ben_scores)), np.ones(len(fs))],
                      np.r_[ben_scores, fs]))}
    q["_benign_median"] = float(np.median(ben_scores))
    print("\n  H2(a) — CNN attack-log-odds vs the benign distribution (seed 42):")
    for fam in FAMS:
        r = q[fam]
        print(f"    {fam:24s} {r['frac_below_benign_median']:6.1%} of flows score BELOW the "
              f"benign median | AUC vs benign={r['auc_vs_benign']:.4f}")
    OUT["results"]["H2a_boundary"] = q
except Exception as e:  # noqa: BLE001
    print(f"  !! CNN-based part skipped: {type(e).__name__}: {e}")
    OUT["results"]["H1_absorption"] = f"SKIPPED: {type(e).__name__}: {e}"

outp = os.path.join(paths.METADATA, "bot_failure_analysis.json")
with open(outp, "w") as f:
    json.dump(OUT, f, indent=1)
print(f"\nwrote {outp}")

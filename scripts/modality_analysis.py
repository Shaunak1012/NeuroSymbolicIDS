"""
modality_analysis.py — test the Phase-3 "modality analogue" account.

THE CLAIM UNDER TEST (docs/STATUS.md, "PHASE 3 RESULTS", 2026-08-02)
--------------------------------------------------------------------
Zero-day performance is governed not by method family ((A) supervised vs (B)
distance/reconstruction) but by whether the unseen class shares a behavioural
modality with some KNOWN class:
    * shares a modality (Web BF/XSS ~ FTP/SSH-Patator brute force) -> the CNN
      transfers within-modality and wins (0.92-0.96); the autoencoder sees
      structurally-normal traffic and scores 0.0000 recall.
    * no known analogue (Bot, Infiltration, Heartbleed) -> every supervised
      method sits at 1.5-1.8x; only distance/reconstruction methods work
      (Mahalanobis 4.3x, AE 3.6x).

OPERATIONALISATION
------------------
For the CNN to flag a zero-day flow as an attack it must look more like some
known ATTACK than like BENIGN. For the AE to flag it, it must look UNLIKE
BENIGN (large reconstruction error). Those are different quantities, so we
measure both, per flow, as tied-covariance Mahalanobis distances to known-class
centroids fitted on the TRAIN split:

    d_benign  = distance to the BENIGN centroid
    d_attack  = min distance to any KNOWN-ATTACK centroid
    margin    = d_benign - d_attack       (>0 => looks more like a known attack)

Predictions, stated BEFORE running:
    P1. Web BF / XSS / SQLi  -> margin > 0 (closer to a known attack than to
        benign), and their nearest known attack should be a PATATOR class.
    P2. Bot / Infiltration / Heartbleed -> margin <= 0, i.e. no known-attack
        analogue; they should sit far from every known attack centroid.
    P3. Across families, `margin` should track the (A)-advantage
        (CNN PR-AUC - AE PR-AUC).
    P4. Per flow, `d_benign` should track AE detection.

GUARDING AGAINST CIRCULARITY
----------------------------
The CNN embedding is *trained* to separate known classes, so "zero-day class X
lands near known class Y" is partly built in. Three guards:
  1. every measurement is repeated in RAW (log1p + scaled) feature space, which
     no model was trained to shape;
  2. we report WHICH known class is nearest -- a specific named prediction that
     can fail (if Web BF's nearest neighbour is BENIGN or DoS Hulk rather than a
     Patator class, the account is wrong);
  3. per-flow tests (thousands of points) rather than a 6-point family-level
     correlation, which would be far too small to mean anything.

Run:  python scripts/modality_analysis.py
"""
import os
import json

import numpy as np
from sklearn.preprocessing import StandardScaler

import paths, config, features

cfg = config.get()
PAPER = paths.PAPER
TFM = cfg["protocol"]["feature_transform"]
CHANCE = {"Bot": 0.0342, "Web Attack Brute Force": 0.0266, "Web Attack XSS": 0.0117}

# Per-family PR-AUC already measured (docs/STATUS.md "PHASE 3 RESULTS").
# CNN = cnn_paper_logodds (seed 42), AE = autoencoder_paper (seed 42).
CNN_PR = {"Bot": 0.0591, "Heartbleed": 0.0001, "Infiltration": 0.0010,
          "Web Attack Brute Force": 0.9194, "Web Attack Sql Injection": 0.3486,
          "Web Attack XSS": 0.9554}
AE_PR = {"Bot": 0.1217, "Heartbleed": 0.0207, "Infiltration": 0.1015,
         "Web Attack Brute Force": 0.1168, "Web Attack Sql Injection": 0.0009,
         "Web Attack XSS": 0.0615}


def tied_mahalanobis(E_fit, y_fit, E_eval, classes):
    """Per-class centroids + tied covariance from the FIT set; returns
    (N_eval, n_classes) Mahalanobis distances."""
    means = np.stack([E_fit[y_fit == c].mean(0) for c in classes])
    idx = {c: i for i, c in enumerate(classes)}
    centred = E_fit - means[np.array([idx[c] for c in y_fit])]
    cov = np.cov(centred.T) + 1e-6 * np.eye(E_fit.shape[1])
    inv = np.linalg.inv(cov)
    d = E_eval[:, None, :] - means[None, :, :]
    m2 = np.einsum("ncd,de,nce->nc", d, inv, d)
    return np.sqrt(np.clip(m2, 0, None))


def analyse(space_name, E_tr, y_tr, E_te, y_te, known, zero_day, out):
    classes = sorted(known)
    D = tied_mahalanobis(E_tr, y_tr, E_te, classes)
    bi = classes.index("BENIGN")
    atk_cols = [i for i, c in enumerate(classes) if c != "BENIGN"]

    d_benign = D[:, bi]
    d_attack = D[:, atk_cols].min(1)
    nearest_atk = np.array(classes, dtype=object)[np.array(atk_cols)][D[:, atk_cols].argmin(1)]
    margin = d_benign - d_attack

    print(f"\n{'='*88}\n{space_name}\n{'='*88}")
    print(f"{'family':28s} {'n':>6s} {'d_benign':>9s} {'d_attack':>9s} {'margin':>8s}  nearest known attack")
    print("-" * 88)
    rows = {}
    for fam in sorted(zero_day) + ["BENIGN"]:
        m = y_te == fam
        if m.sum() == 0:
            continue
        vals, counts = np.unique(nearest_atk[m], return_counts=True)
        top = vals[counts.argmax()]
        share = counts.max() / m.sum()
        rows[fam] = dict(n=int(m.sum()), d_benign=float(np.median(d_benign[m])),
                         d_attack=float(np.median(d_attack[m])),
                         margin=float(np.median(margin[m])),
                         nearest=str(top), nearest_share=float(share))
        tag = "  " if fam == "BENIGN" else "ZD"
        print(f"{tag} {fam:25s} {m.sum():6d} {np.median(d_benign[m]):9.2f} "
              f"{np.median(d_attack[m]):9.2f} {np.median(margin[m]):8.2f}  "
              f"{top} ({share:.0%})")

    # P3: does margin track the (A)-advantage across families?
    fams = [f for f in sorted(zero_day) if f in CNN_PR]
    adv = np.array([CNN_PR[f] - AE_PR[f] for f in fams])
    mrg = np.array([rows[f]["margin"] for f in fams if f in rows])
    dbn = np.array([rows[f]["d_benign"] for f in fams if f in rows])
    if len(mrg) == len(adv) and len(adv) > 2:
        print(f"\n  P3  corr(margin, CNN_PR - AE_PR)   = {np.corrcoef(mrg, adv)[0,1]:+.3f}   (n={len(adv)} families)")
        print(f"      corr(d_benign, AE PR-AUC)       = "
              f"{np.corrcoef(dbn, np.array([AE_PR[f] for f in fams]))[0,1]:+.3f}")
    out[space_name] = rows
    return d_benign, d_attack, margin


# ---------------- load ----------------
X_tr = np.load(os.path.join(PAPER, "X_train.npy"))
y_tr = np.load(os.path.join(PAPER, "y_train_mc.npy"), allow_pickle=True)
X_te = np.load(os.path.join(PAPER, "X_test.npy"))
y_te = np.load(os.path.join(PAPER, "y_test_mc.npy"), allow_pickle=True)
zero_day = set(np.load(os.path.join(PAPER, "zero_day_classes.npy"), allow_pickle=True).tolist())
known = sorted(set(y_tr))

sc = StandardScaler().fit(features.transform(X_tr, TFM))
Xtr_s = sc.transform(features.transform(X_tr, TFM))
Xte_s = sc.transform(features.transform(X_te, TFM))

E_tr = np.load(os.path.join(paths.EMBEDDINGS, "X_train_cnn_paper_emb.npy"))
E_te = np.load(os.path.join(paths.EMBEDDINGS, "X_test_cnn_paper_emb.npy"))

out = {}
print("\nPredictions stated before running:")
print("  P1 Web BF/XSS/SQLi -> margin > 0, nearest known attack is a PATATOR class")
print("  P2 Bot/Infiltration/Heartbleed -> margin <= 0 (no known-attack analogue)")
print("  P3 margin tracks (CNN PR-AUC - AE PR-AUC) across families")
print("  P4 d_benign tracks AE detection, per flow")

analyse("RAW FEATURE SPACE (68 features, log1p+scaled -- untrained by any model)",
        Xtr_s, y_tr, Xte_s, y_te, known, zero_day, out)
db_e, da_e, mg_e = analyse("CNN EMBEDDING SPACE (64-d -- trained to separate KNOWN classes)",
                           E_tr, y_tr, E_te, y_te, known, zero_day, out)

# ---------------- P4: per-flow, does d_benign explain AE detection? ----------------
ae = np.load(os.path.join(paths.PREDICTIONS, "y_prob_autoencoder_paper_test.npy"))
cnnp = np.load(os.path.join(paths.PREDICTIONS, "y_prob_cnn_paper_logodds_test.npy"))
zd_mask = np.isin(y_te, list(zero_day))
print(f"\n{'='*88}\nP4  PER-FLOW (zero-day flows only, n={zd_mask.sum()}) -- CNN embedding space\n{'='*88}")
print(f"  corr(d_benign, AE reconstruction error) = {np.corrcoef(db_e[zd_mask], ae[zd_mask])[0,1]:+.3f}")
print(f"  corr(margin,   CNN attack log-odds)     = {np.corrcoef(mg_e[zd_mask], cnnp[zd_mask])[0,1]:+.3f}")
print(f"  corr(d_benign, CNN attack log-odds)     = {np.corrcoef(db_e[zd_mask], cnnp[zd_mask])[0,1]:+.3f}")

with open(os.path.join(paths.METADATA, "modality_analysis.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1)
print(f"\nwrote {os.path.join(paths.METADATA, 'modality_analysis.json')}")
print("DONE (modality_analysis)")

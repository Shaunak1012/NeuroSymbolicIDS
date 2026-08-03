"""
kg_readiness.py — the two measurements that gate Phase 4. Run BEFORE writing kg.py.

`kg_precheck.py` established the blocker (CNN embeddings are a Bot seed lottery).
This answers the two questions that remained open after it, and that the KG spec
cannot be built responsibly without:

  PART A — WHICH REPRESENTATION SHOULD THE KG CLUSTER?
      The Bot failure analysis showed the CNN embedding ranks Bot at noise
      (cross-seed rho = -0.090) while the AE bottleneck ranks it reproducibly
      (0.827). That made (c) "AE bottleneck" the data-backed lean — but
      clustering purity under (b) raw features and (c) AE bottleneck was never
      actually measured. Rank stability and cluster purity are different things.

  PART B — DOES "UNEXPLAINED CLUSTER" DISCRIMINATE ANYTHING AT ALL?
      STATUS calls this "the single most important untested quantity."
      The KG spec flags an emerging pattern partly by *weak or no
      `associated_with` edges to known AttackType*. But 25 of 50 clusters were
      already >90% benign in training, and 100% of Bot / Web-BF / Infiltration /
      Heartbleed test flows landed in benign-dominated clusters. So the criterion
      may fire on ordinary benign traffic as readily as on zero-day. If it does,
      the KG's detection mechanism does not work and that is worth knowing BEFORE
      building the graph, not after.

PRE-REGISTERED PREDICTIONS (written before the first run, 2026-08-03)
---------------------------------------------------------------------
P1. AE bottleneck Bot purity will be MORE STABLE across seeds than the CNN's
    (spread << 43.4 pp), because its Bot ranking is reproducible.
P2. AE bottleneck ABSOLUTE Bot purity will be LOWER than the CNN's best seed
    (87.9%) — a benign-only representation has no reason to carve out Bot
    specifically; it should spread attacks by degree-of-abnormality instead.
P3. Raw features will be stable by construction (no training => no lottery) and
    competitive, since Bot is fully separable in raw space given labels (0.9988).
P4. "Unexplained cluster" will have POOR precision for zero-day — lift < 3x over
    the base rate — because benign-dominated clusters are the overwhelming
    majority. This is the prediction that would kill the mechanism as specified.

Anti-circularity: purity/recall here use test labels, so they are an ORACLE UPPER
BOUND on what an unsupervised KG could achieve, exactly as in kg_precheck.py.
Part B is deliberately different: its "unexplained" criterion uses ONLY training
labels (which the KG legitimately has), and is then scored against test labels.
That makes it an honest simulation of the real mechanism rather than an upper bound.

Run:    python scripts/kg_readiness.py
Writes: outputs/metadata/kg_readiness.json
        outputs/embeddings/X_{train,test}_ae_bottleneck{,_s43,_s44}.npy  (cached)
"""
import os
import json
import pickle
import numpy as np
from sklearn.cluster import MiniBatchKMeans
from sklearn.preprocessing import StandardScaler

import paths, config, features

cfg = config.get()
TFM = cfg["protocol"]["feature_transform"]
P, E = paths.PAPER, paths.EMBEDDINGS
FAMS = ["Bot", "Web Attack Brute Force", "Web Attack XSS"]
KS = (200, 400)
CLUST_SEED = 42
SUB = 200_000

ytr = np.load(os.path.join(P, "y_train_mc.npy"), allow_pickle=True)
yte = np.load(os.path.join(P, "y_test_mc.npy"), allow_pickle=True)
zero_day = set(np.load(os.path.join(P, "zero_day_classes.npy"), allow_pickle=True).tolist())
OUT = {"predictions_preregistered": {
    "P1": "AE bottleneck Bot purity more stable across seeds than CNN (spread << 43.4pp)",
    "P2": "AE bottleneck absolute Bot purity LOWER than CNN best seed (87.9%)",
    "P3": "raw features stable by construction and competitive",
    "P4": "unexplained-cluster precision for zero-day is POOR (lift < 3x) -- would kill the mechanism",
}, "partA_representations": {}, "partB_unexplained_cluster": {}}


# ------------------------------------------------ AE bottleneck extraction ----
def ae_bottleneck(sfx):
    """16-d benign-trained bottleneck for train+test. Cached to disk."""
    ftr = os.path.join(E, f"X_train_ae_bottleneck{sfx}.npy")
    fte = os.path.join(E, f"X_test_ae_bottleneck{sfx}.npy")
    if os.path.exists(ftr) and os.path.exists(fte):
        return np.load(ftr), np.load(fte)
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    import tensorflow as tf
    tag = "autoencoder_paper" + sfx
    model = tf.keras.models.load_model(
        os.path.join(paths.MODELS, f"{tag}.keras"), compile=False)
    enc = tf.keras.Model(model.input, model.get_layer("bottleneck").output)
    # AE's own scaler, fitted on ALL of train (matches autoencoder_paper.py)
    spath = os.path.join(paths.MODELS,
                         f"scaler_ae_paper{'' if sfx == '' else sfx}.pkl")
    with open(spath, "rb") as f:
        sc = pickle.load(f)
    out = []
    for split in ("train", "test"):
        X = features.transform(np.load(os.path.join(P, f"X_{split}.npy")), TFM)
        out.append(enc.predict(sc.transform(X), batch_size=8192, verbose=0))
    np.save(ftr, out[0]); np.save(fte, out[1])
    print(f"    extracted + cached AE bottleneck{sfx or ' (seed42)'}: {out[0].shape}")
    return out[0], out[1]


def raw_scaled():
    Xtr = features.transform(np.load(os.path.join(P, "X_train.npy")), TFM)
    Xte = features.transform(np.load(os.path.join(P, "X_test.npy")), TFM)
    sc = StandardScaler().fit(Xtr)
    return sc.transform(Xtr), sc.transform(Xte)


def fit_assign(Etr, Ete, K, seed=CLUST_SEED):
    rng = np.random.RandomState(0)
    idx = rng.choice(len(Etr), size=min(SUB, len(Etr)), replace=False)
    km = MiniBatchKMeans(n_clusters=K, random_state=seed, n_init=5,
                         batch_size=4096).fit(Etr[idx])
    return km.predict(Etr), km.predict(Ete)


def purity(te_lab, K):
    out = {}
    for fam in FAMS:
        m = yte == fam
        counts = np.bincount(te_lab[m], minlength=K)
        best = counts.argmax()
        tot = (te_lab == best).sum()
        out[fam] = {"purity": float(counts[best] / tot) if tot else 0.0,
                    "recall": float(counts[best] / m.sum())}
    return out


# ============================================================== PART A ========
print("=" * 100)
print("PART A -- WHICH REPRESENTATION SHOULD THE KG CLUSTER?")
print("=" * 100)

REPS = {
    "cnn_embedding_64d": [("", 42), ("_s43", 43), ("_s44", 44)],
    "ae_bottleneck_16d": [("", 42), ("_s43", 43), ("_s44", 44)],
    "raw_features_68d":  [("", None)],
}
cache = {}
for rep, seeds in REPS.items():
    print(f"\n--- {rep} ---")
    OUT["partA_representations"][rep] = {}
    for sfx, seed in seeds:
        if rep == "cnn_embedding_64d":
            Etr = np.load(os.path.join(E, f"X_train_cnn_paper{sfx}_emb.npy"))
            Ete = np.load(os.path.join(E, f"X_test_cnn_paper{sfx}_emb.npy"))
        elif rep == "ae_bottleneck_16d":
            Etr, Ete = ae_bottleneck(sfx)
        else:
            Etr, Ete = raw_scaled()
        for K in KS:
            tr_lab, te_lab = fit_assign(Etr, Ete, K)
            r = purity(te_lab, K)
            key = f"k{K}_seed{seed}"
            OUT["partA_representations"][rep][key] = r
            cells = " | ".join(f"{f[:12]:>12s} p={r[f]['purity']:5.1%} r={r[f]['recall']:5.1%}"
                               for f in FAMS)
            print(f"  k={K:3d} seed={str(seed):>4s} | {cells}")
            if rep == "cnn_embedding_64d" and K == 200:
                cache.setdefault("cnn_labels", {})[seed] = (tr_lab, te_lab)
            if rep == "ae_bottleneck_16d" and K == 200:
                cache.setdefault("ae_labels", {})[seed] = (tr_lab, te_lab)
            if rep == "raw_features_68d" and K == 200:
                cache["raw_labels"] = (tr_lab, te_lab)

print("\n" + "-" * 100)
print("CROSS-SEED SPREAD (the number that decides the representation):")
spread = {}
for rep, seeds in REPS.items():
    if len(seeds) < 2:
        print(f"  {rep:22s} single representation (no training) -> spread 0.0 pp by construction")
        continue
    for K in KS:
        for f in FAMS:
            ps = [OUT["partA_representations"][rep][f"k{K}_seed{s}"][f]["purity"]
                  for _, s in seeds]
            spread[f"{rep}_k{K}_{f}"] = (max(ps) - min(ps)) * 100
            if f == "Bot":
                print(f"  {rep:22s} k={K:3d} Bot purity {min(ps):5.1%}-{max(ps):5.1%} "
                      f"(spread {(max(ps)-min(ps))*100:5.1f} pp)")
OUT["partA_spread_pp"] = spread

# ============================================================== PART B ========
print("\n" + "=" * 100)
print('PART B -- DOES "UNEXPLAINED CLUSTER" DISCRIMINATE ZERO-DAY FROM BENIGN?')
print("=" * 100)
print('  "unexplained" = cluster whose TRAINING flows contain < tau known-attack fraction.')
print("  Uses ONLY train labels to decide (which the KG legitimately has), then scores")
print("  against test labels. This is the real mechanism, not an oracle upper bound.\n")

is_zd_te = np.isin(yte, list(zero_day))
is_ben_te = yte == "BENIGN"
base_rate = is_zd_te.sum() / (is_zd_te.sum() + is_ben_te.sum())
print(f"  base rate: zero-day / (zero-day + benign) in test = {base_rate:.4f}")
print(f"  ({is_zd_te.sum()} zero-day vs {is_ben_te.sum()} benign)\n")
OUT["partB_unexplained_cluster"]["base_rate_zd_vs_benign"] = float(base_rate)

is_known_atk_tr = ytr != "BENIGN"
TAUS = (0.01, 0.05, 0.10)

for repname, labels in [("cnn_embedding_64d", cache["cnn_labels"][42]),
                        ("ae_bottleneck_16d", cache["ae_labels"][42]),
                        ("raw_features_68d", cache["raw_labels"])]:
    tr_lab, te_lab = labels
    K = 200
    atk_frac = np.array([
        is_known_atk_tr[tr_lab == c].mean() if (tr_lab == c).any() else 0.0
        for c in range(K)])
    res = {}
    print(f"--- {repname} (k=200) ---")
    print(f"    clusters with ZERO known-attack training flows: "
          f"{int((atk_frac == 0).sum())}/{K}")
    for tau in TAUS:
        unexplained = np.flatnonzero(atk_frac < tau)
        flagged = np.isin(te_lab, unexplained)
        n_flag = int(flagged.sum())
        zd_flag = int((flagged & is_zd_te).sum())
        ben_flag = int((flagged & is_ben_te).sum())
        denom = zd_flag + ben_flag
        prec = zd_flag / denom if denom else 0.0
        rec = zd_flag / is_zd_te.sum()
        lift = prec / base_rate if base_rate else 0.0
        res[f"tau_{tau}"] = {"n_clusters_unexplained": int(len(unexplained)),
                            "n_test_flagged": n_flag, "zd_flagged": zd_flag,
                            "benign_flagged": ben_flag, "precision_zd": prec,
                            "recall_zd": rec, "lift_over_base_rate": lift}
        print(f"    tau={tau:<5} | {len(unexplained):3d}/{K} clusters unexplained | "
              f"flags {n_flag:6d} test flows | zd {zd_flag:5d} benign {ben_flag:6d} | "
              f"precision {prec:.4f} recall {rec:.4f} | LIFT {lift:.2f}x")
    OUT["partB_unexplained_cluster"][repname] = res
    print()

outp = os.path.join(paths.METADATA, "kg_readiness.json")
with open(outp, "w", encoding="utf-8") as f:
    json.dump(OUT, f, indent=1)
print(f"wrote {outp}")

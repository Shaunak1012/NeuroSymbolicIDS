"""
kg_precheck.py — Phase-4 (Knowledge Graph) VIABILITY pre-check. Run before building
the graph; this is a falsification test, not a deliverable.

The question
------------
The KG spec clusters CNN embeddings and treats a dense cluster with weak links to
known AttackTypes as an "emerging pattern" — its zero-day mechanism. That assumes
zero-day flows form distinguishable clusters in the cnn_paper embedding space. But
that is the same 64-dim space in which Bot scores at chance (PR-AUC 0.059, 1.7x
lift). If Bot doesn't separate there, cluster-membership cannot surface it.

Falsifiable prediction stated BEFORE the first run (2026-07-29):
    "Bot flows will distribute across benign-dominated clusters rather than
     concentrating in distinct ones."

Result: HALF WRONG, in the useful direction. Zero-day flows DO land ~100% in
benign-dominated clusters, but they CONCENTRATE rather than smear — Bot forms a
~90%-pure cluster at k>=200, stable across seeds, capturing ~34% of Bot.

What this does NOT show
-----------------------
Purity/recall here are computed WITH test labels — an oracle view, and therefore an
UPPER BOUND on what an unsupervised KG could achieve. A real KG must infer
"unexplained/emerging" from unlabelled structure, and at k=50 fully half the
clusters were already >90% benign in training. The false-positive rate of
"unexplained cluster" is the quantity that actually decides whether the mechanism
works, and it is NOT measured here. Measure it before building the graph.

These are geometric measures, not detection metrics. n=2 seeds — provisional.

Run:  python scripts/kg_precheck.py
"""
import os
import numpy as np
from sklearn.cluster import MiniBatchKMeans

import paths

P = paths.PAPER
E = paths.EMBEDDINGS

ytr = np.load(os.path.join(P, "y_train_mc.npy"), allow_pickle=True)
yte = np.load(os.path.join(P, "y_test_mc.npy"), allow_pickle=True)

FAMS = ["Bot", "Web Attack Brute Force", "Web Attack XSS"]  # the powered zero-day families
# CNN seeds whose embeddings we test. CRITICAL (2026-08-02): the original version of
# this script varied only the CLUSTERING seed on a FIXED seed-42 embedding, and
# reported "stable across 2 seeds" -- which measured clustering stability, NOT
# stability of the embedding itself across CNN training runs. Those are different
# claims, and the train-vs-score decomposition found the CNN's open-set geometry is
# far less seed-stable than its classification (Mahalanobis Bot swings 3.6x across
# these same seeds while CNN macro moves 0.009). This now varies BOTH.
CNN_SEEDS = [(42, ""), (43, "_s43"), (44, "_s44")]


def measure(Etr, ytr, Ete, K, clust_seed, sub_rng=0):
    rng = np.random.RandomState(sub_rng)
    idx = rng.choice(len(Etr), size=min(200_000, len(Etr)), replace=False)
    km = MiniBatchKMeans(n_clusters=K, random_state=clust_seed, n_init=5,
                         batch_size=4096).fit(Etr[idx])
    te_lab = km.predict(Ete)
    out = {}
    for fam in FAMS:
        m = yte == fam
        counts = np.bincount(te_lab[m], minlength=K)
        best = counts.argmax()
        tot = (te_lab == best).sum()
        out[fam] = (counts[best] / tot if tot else 0.0, counts[best] / m.sum())
    return out


print("=" * 96)
print("PART 1 -- vary the CNN SEED (the embedding itself), clustering seed FIXED at 42")
print("=" * 96)
print(f"{'CNN seed':>9s} {'k':>5s} | " + " | ".join(f"{f[:20]:>20s}" for f in FAMS))
print("-" * 96)
part1 = {}
for K in (200, 400):
    for cnn_seed, sfx in CNN_SEEDS:
        Etr = np.load(os.path.join(E, f"X_train_cnn_paper{sfx}_emb.npy"))
        Ete = np.load(os.path.join(E, f"X_test_cnn_paper{sfx}_emb.npy"))
        r = measure(Etr, ytr, Ete, K, clust_seed=42)
        part1[(K, cnn_seed)] = r
        cells = [f"p={r[f][0]:5.1%} r={r[f][1]:5.1%}" for f in FAMS]
        print(f"{cnn_seed:9d} {K:5d} | " + " | ".join(f"{c:>20s}" for c in cells))
    print("-" * 96)

print("\nSPREAD ACROSS CNN SEEDS (this is the number that matters for Phase 4):")
for K in (200, 400):
    for f in FAMS:
        ps = [part1[(K, s)][f][0] for s, _ in CNN_SEEDS]
        rs = [part1[(K, s)][f][1] for s, _ in CNN_SEEDS]
        print(f"  k={K:3d} {f:24s} purity {min(ps):5.1%}-{max(ps):5.1%} "
              f"(spread {max(ps)-min(ps):5.1%}) | recall {min(rs):5.1%}-{max(rs):5.1%}")

print("\n" + "=" * 96)
print("PART 2 -- ORIGINAL TEST for comparison: vary only the CLUSTERING seed, CNN seed FIXED at 42")
print("=" * 96)
Etr = np.load(os.path.join(E, "X_train_cnn_paper_emb.npy"))
Ete = np.load(os.path.join(E, "X_test_cnn_paper_emb.npy"))
print(f"{'k':>5s} {'clust':>6s} | " + " | ".join(f"{f[:20]:>20s}" for f in FAMS))
print("-" * 96)
for K in (50, 100, 200, 400, 800):
    for cs in (42, 43):
        r = measure(Etr, ytr, Ete, K, clust_seed=cs)
        cells = [f"p={r[f][0]:5.1%} r={r[f][1]:5.1%}" for f in FAMS]
        print(f"{K:5d} {cs:6d} | " + " | ".join(f"{c:>20s}" for c in cells))

print("""
p = purity of that family's single best cluster (frac of the cluster that IS the family)
r = recall  (frac of the family captured by that one cluster)

A KG "emerging pattern" node is only useful if BOTH are decent: high purity means the
cluster means something; high recall means it covers the family. High r with low p is a
big benign blob that happens to contain the family -- useless as a detector.
""")

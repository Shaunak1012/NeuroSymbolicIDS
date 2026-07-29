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

Etr = np.load(os.path.join(E, "X_train_cnn_paper_emb.npy"))
ytr = np.load(os.path.join(P, "y_train_mc.npy"), allow_pickle=True)
Ete = np.load(os.path.join(E, "X_test_cnn_paper_emb.npy"))
yte = np.load(os.path.join(P, "y_test_mc.npy"), allow_pickle=True)

FAMS = ["Bot", "Web Attack Brute Force", "Web Attack XSS"]  # the powered zero-day families
rng = np.random.RandomState(0)
idx = rng.choice(len(Etr), size=200_000, replace=False)
Xs, ys = Etr[idx], ytr[idx]

print(f"{'k':>5s} {'seed':>5s} | " + " | ".join(f"{f[:18]:>18s}" for f in FAMS))
print("      purity of the family's OWN best cluster (what frac of that cluster is this family)")
print("-" * 88)

for K in (50, 100, 200, 400, 800):
    for seed in (42, 43):
        km = MiniBatchKMeans(n_clusters=K, random_state=seed, n_init=5,
                             batch_size=4096).fit(Xs)
        te_lab = km.predict(Ete)
        row = []
        for fam in FAMS:
            m = yte == fam
            labs = te_lab[m]
            counts = np.bincount(labs, minlength=K)
            best = counts.argmax()
            # purity: of ALL test flows assigned to that cluster, what frac are this family?
            tot_in_best = (te_lab == best).sum()
            purity = counts[best] / tot_in_best if tot_in_best else 0.0
            recall = counts[best] / m.sum()
            row.append(f"p={purity:5.1%} r={recall:5.1%}")
        print(f"{K:5d} {seed:5d} | " + " | ".join(f"{c:>18s}" for c in row))

print("""
p = purity of that family's single best cluster (frac of the cluster that IS the family)
r = recall  (frac of the family captured by that one cluster)

A KG "emerging pattern" node is only useful if BOTH are decent: high purity means the
cluster means something; high recall means it covers the family. High r with low p is a
big benign blob that happens to contain the family -- useless as a detector.
""")

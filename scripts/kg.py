"""
kg.py — Phase 4: the adaptive Knowledge Graph.

⚠️ EVERY DESIGN DECISION HERE WAS FORCED BY MEASUREMENT, NOT BY THE ORIGINAL SPEC.
Read `docs/STATUS.md` -> "LAST PHASE-4 GATE CLOSED" before changing any of them.

  * **Representation: RAW FEATURES.** Not CNN embeddings (Bot cluster purity swings
    87.9/86.6/44.4% across CNN seeds) and not the AE bottleneck (52.1 pp spread,
    measured worst of all options -- rank stability is not cluster stability).
    Raw features give Bot purity 77.6% at k=200 with no training-seed lottery.
  * **Scope: CORROBORATION + EXPLANATION, not primary detection.** The spec called
    the KG "the system's zero-day signal". Measured, its "unexplained cluster"
    criterion scores lift <= 1.00x -- at or below chance. That path is dead.
  * **Emerging-pattern rule: GROWTH RATE ONLY.** Of the spec's three criteria only
    burstiness survives (lift 5.94x [5.66, 6.11] n=3, ~81% recall). "Unexplained"
    is dead; behaviour co-occurrence is weak (2.81x at 1.5% recall) and is kept
    only as an EXPLANATION attribute, never as a detector.
  * **Decay: KEPT (adaptive).** Time = flow-count position in TRUE chronological
    order via `timeline.py`. Never parse meta_*.csv timestamps directly.
  * **Behaviours: `active_behaviour_matrix()`.** `RepeatedConnections` is constant
    zero (dead edge type) and `BeaconLike` is binary (bimodal as an edge weight).

⚠️ **THE CAVEAT THAT MUST REACH THE WRITE-UP.** Growth works substantially because
CIC-IDS2017's attacks are scripted into fixed windows (Bot Fri 09:34-12:59, Web BF
Thu 09:15-10:00, XSS Thu 10:15-10:35). A real network with continuous low-rate C2
would not produce this signal -- and Bot is precisely the family whose real
signature is persistence, not bursts. Also: *"temporal burstiness of a raw-feature
cluster" does not require a knowledge graph.* The KG earns its place through
explanation and corroboration, NOT through this detection number. Say that first;
a reviewer will say it otherwise.

Architecture
------------
Nodes   Cluster:<id>  (200, k-means on train raw features)
        Behaviour:<name>  (6 active)
        AttackType:<name>  (BENIGN + 8 known)
Edges   Cluster -exhibits->        Behaviour     w = decayed mean behaviour value
        Cluster -associated_with-> AttackType    w = decayed class share

Memory is initialised from TRAIN (what the system already knows), then TEST is
streamed in chronological order so patterns genuinely *emerge* over time. Edge
weights decay each window, so stale associations fade and recently-reinforced
ones dominate -- the "adaptive" half of the project title.

Run:  python scripts/kg.py
Outputs: models/kg.gpickle · outputs/metadata/kg_report.json
         outputs/predictions/y_prob_kg_test.npy   (s_kg, corroboration score)
"""
import os
import json
import pickle
import numpy as np
import networkx as nx
from sklearn.cluster import MiniBatchKMeans
from sklearn.preprocessing import StandardScaler

import paths, config, features, behavior, timeline, metrics, tracking

cfg = config.get()
SEED = int(os.environ.get("KG_SEED", cfg["seed"]))
TFM = cfg["protocol"]["feature_transform"]
P = paths.PAPER
K = int(os.environ.get("KG_K", 200))
N_WINDOWS = int(os.environ.get("KG_WINDOWS", 20))
TAU = float(os.environ.get("KG_TAU", 3.0))        # decay constant, in windows
BURST_THR = float(os.environ.get("KG_BURST", 8.0))  # measured operating point
# KG_TAG lets a sweep vary K without every run overwriting the same report.
# Additive and inert when unset -- without it, kg_k100_s42 / kg_k400_s42 /
# kg_k800_s42 would all write "kg" and silently clobber each other, and the
# sweep would "finish" having measured only its last k.
_DEFAULT_TAG = "kg" if SEED == cfg["seed"] else f"kg_s{SEED}"
TAG = os.environ.get("KG_TAG", _DEFAULT_TAG)
print(f"CONFIG: seed={SEED} k={K} windows={N_WINDOWS} tau={TAU} burst_thr={BURST_THR}")

# ------------------------------------------------------------------ data ----
ytr = np.load(os.path.join(P, "y_train_mc.npy"), allow_pickle=True)
yte = np.load(os.path.join(P, "y_test_mc.npy"), allow_pickle=True)
zero_day = set(np.load(os.path.join(P, "zero_day_classes.npy"), allow_pickle=True).tolist())
Xtr_raw = np.load(os.path.join(P, "X_train.npy"))
Xte_raw = np.load(os.path.join(P, "X_test.npy"))

Xtr = features.transform(Xtr_raw, TFM)
Xte = features.transform(Xte_raw, TFM)
sc = StandardScaler().fit(Xtr)
Xtr_s, Xte_s = sc.transform(Xtr), sc.transform(Xte)
print(f"train {Xtr_s.shape} | test {Xte_s.shape}")

# ------------------------------------------------------------ clustering ----
rng = np.random.RandomState(0)
sub = rng.choice(len(Xtr_s), size=min(200_000, len(Xtr_s)), replace=False)
km = MiniBatchKMeans(n_clusters=K, random_state=SEED, n_init=5, batch_size=4096).fit(Xtr_s[sub])
tr_lab, te_lab = km.predict(Xtr_s), km.predict(Xte_s)
print(f"clustered into {K} raw-feature clusters")

# ------------------------------------------------------------ behaviours ----
thr = behavior.load_thresholds()
BEH = behavior.active_behaviour_names()
Btr = behavior.active_behaviour_matrix(Xtr_raw, thr)
Bte = behavior.active_behaviour_matrix(Xte_raw, thr)
print(f"active behaviours ({len(BEH)}): {', '.join(BEH)}")

# --------------------------------------------------- chronological stream ----
ts_te = timeline.load_timestamps("test")
timeline.selftest("test", verbose=False)          # fail loudly if timestamps drift
order = np.argsort(ts_te.to_numpy(), kind="stable")
win = np.zeros(len(te_lab), dtype=int)
win[order] = np.minimum((np.arange(len(order)) * N_WINDOWS) // len(order), N_WINDOWS - 1)
print(f"test stream: {N_WINDOWS} windows, {ts_te.min()} -> {ts_te.max()}")


# ================================================================ THE KG =====
from kg_graph import KnowledgeGraph  # noqa: E402  (moved verbatim, audit F-22)


# ---------------------------------------------------- build initial memory ---
print("\nbuilding memory from TRAIN (what the system already knows)...")
kg = KnowledgeGraph(K, BEH, TAU)
kg.observe(tr_lab, Btr, classes=ytr, record_history=False)
print(f"  {kg.G.number_of_nodes()} nodes, {kg.G.number_of_edges()} edges")

# --------------------------------------- stream TEST chronologically ---------
print(f"\nstreaming TEST in chronological order ({N_WINDOWS} windows, decay tau={TAU})...")
for w in range(N_WINDOWS):
    m = win == w
    if not m.any():
        kg.history_pad = True
        for c in range(K):
            kg.history[c].append(0)
        continue
    kg.decay()                                  # stale memory fades first
    kg.observe(te_lab[m], Bte[m], classes=None)  # no labels at inference time
burst = kg.burstiness()
emerging = kg.emerging(BURST_THR)
print(f"  emerging clusters (burstiness >= {BURST_THR}): {len(emerging)}/{K}")

# ------------------------------------------------------------- s_kg score ----
# Corroboration score in [0,1]: how strongly does memory say this flow belongs to
# a pattern that is emerging right now? Deliberately NOT fed to a fitted combiner
# (see "THE FUSION WALL" -- a combiner calibrated on zero-day-free validation data
# cannot learn to weight a zero-day-specific channel).
b_norm = np.clip((burst - 1.0) / (N_WINDOWS - 1.0), 0, 1)
s_kg = b_norm[te_lab]
np.save(os.path.join(paths.predictions_dir(TAG), f"y_prob_{TAG}_test.npy"),
        s_kg.astype(np.float32))

# ---- CAUSAL / ONLINE variant -------------------------------------------------
# s_kg above is TRANSDUCTIVE: burstiness is computed over the WHOLE test stream,
# so a flow in window 3 is scored using information from window 17. That is not
# label leakage (no labels are used anywhere), but it IS an offline/batch setting
# that a live IDS could not reproduce. The causal variant scores each flow using
# ONLY the windows that had already arrived when it did -- the honest real-time
# number. Both are reported; the gap between them is itself the finding.
hist = np.array([kg.history[c] for c in range(K)], dtype=float)   # (K, W)
s_causal = np.zeros(len(te_lab))
for w in range(N_WINDOWS):
    seen = hist[:, :w + 1]
    tot = seen.sum(1, keepdims=True)
    b_w = np.where(tot.ravel() > 0,
                   np.divide(seen, np.where(tot == 0, 1, tot)).max(1) * (w + 1), 0.0)
    m = win == w
    s_causal[m] = np.clip((b_w[te_lab[m]] - 1.0) / max(N_WINDOWS - 1.0, 1), 0, 1)
np.save(os.path.join(paths.predictions_dir(TAG), f"y_prob_{TAG}_causal_test.npy"),
        s_causal.astype(np.float32))

# --------------------------------------------------------------- evaluate ----
print("\n" + "=" * 92)
print("EVALUATION — s_kg as a standalone channel (reported honestly, not as the headline)")
print("=" * 92)
r = metrics.evaluate(yte, s_kg, zero_day, fpr=0.01)
metrics.print_report(r)
tracking.log_run(TAG, {"protocol": "paper", "seed": SEED, "k": K,
                       "windows": N_WINDOWS, "tau": TAU, "burst_thr": BURST_THR,
                       "representation": "raw_features", "scope": "corroboration",
                       "mode": "transductive"},
                 metrics.flatten(r))

r_causal = metrics.evaluate(yte, s_causal, zero_day, fpr=0.01)
tracking.log_run(f"{TAG}_causal",
                 {"protocol": "paper", "seed": SEED, "k": K, "windows": N_WINDOWS,
                  "tau": TAU, "representation": "raw_features",
                  "scope": "corroboration", "mode": "causal_online"},
                 metrics.flatten(r_causal))
print(f"\n  TRANSDUCTIVE (whole stream) macro = {r['macro']['pr_auc']:.4f}"
      f"  Bot = {r['zeroday_family']['Bot']['pr_auc']:.4f}")
print(f"  CAUSAL / ONLINE (past only) macro = {r_causal['macro']['pr_auc']:.4f}"
      f"  Bot = {r_causal['zeroday_family']['Bot']['pr_auc']:.4f}")
print("  ^ the gap is the price of doing this in real time rather than in batch")

# score-tie diagnostic: s_kg takes one value per cluster, so it is massively tied
_u = len(np.unique(s_kg))
print(f"\n  ⚠️ s_kg takes only {_u} distinct values (one per cluster) across "
      f"{len(s_kg)} flows.\n     PR-AUC is rank-based and remains valid, but "
      f"recall@1%FPR is degenerate — do not cite it.")

is_zd = np.isin(yte, list(zero_day)); is_ben = yte == "BENIGN"
base = is_zd.sum() / (is_zd.sum() + is_ben.sum())
flag = np.isin(te_lab, list(emerging))
zd_f, bn_f = int((flag & is_zd).sum()), int((flag & is_ben).sum())
prec = zd_f / (zd_f + bn_f) if (zd_f + bn_f) else 0.0
print(f"\nEMERGING-PATTERN FLAG (burstiness >= {BURST_THR}):")
print(f"  flags {int(flag.sum())} test flows | zero-day {zd_f} | benign {bn_f}")
print(f"  precision {prec:.4f}  recall {zd_f/is_zd.sum():.4f}  "
      f"LIFT {prec/base:.2f}x  (base rate {base:.4f})")

# ------------------------------------------ MANDATORY CONFOUND CONTROL -------
# The causal score rises with arrival position, and CIC-IDS2017 schedules its
# attacks LATE in the week (Bot Fri 09:34-12:59). So a trivial "later = more
# suspicious" baseline could explain the result. It must be ruled out explicitly,
# every run -- not argued away.
#
# Measured 2026-08-03: lateness ALONE scores Bot PR-AUC 0.1575 globally, which
# BEATS the previous best Bot channel (autoencoder, 0.1314). That is a finding
# about the dataset, and it means the global number cannot be reported alone.
#
# The honest measure is WITHIN-WINDOW: score family-vs-benign inside each time
# window separately, so lateness is held constant and only the cluster signal can
# contribute. The lateness control must collapse to ~1.0x lift there, by
# construction -- if it does not, this test is broken.
print("\n" + "=" * 92)
print("CONFOUND CONTROL — is this just detecting 'later in the week'?")
print("=" * 92)
lateness = win.astype(float) / max(N_WINDOWS - 1, 1)


def _within_window(score, fam):
    aps, ns, chs = [], [], []
    for w in sorted(set(win[yte == fam].tolist())):
        m = (win == w) & ((yte == fam) | is_ben)
        y = (yte[m] != "BENIGN").astype(int)
        if y.sum() < 10 or y.sum() == len(y):
            continue
        from sklearn.metrics import average_precision_score as _ap
        aps.append(_ap(y, score[m])); ns.append(int(y.sum())); chs.append(float(y.mean()))
    if not aps:
        return None, None
    return float(np.average(aps, weights=ns)), float(np.average(chs, weights=ns))


control = {}
print(f"  {'channel':22s} {'Bot global':>11s} {'lift':>6s} | {'within-window':>14s} {'lift':>6s}")
for nm, sc in (("s_kg (causal)", s_causal), ("s_kg (transductive)", s_kg),
               ("lateness ONLY", lateness)):
    from sklearn.metrics import average_precision_score as _ap
    mm = (yte == "Bot") | is_ben
    yy = (yte[mm] != "BENIGN").astype(int)
    g = float(_ap(yy, sc[mm])); gc = float(yy.mean())
    ww, wc = _within_window(sc, "Bot")
    control[nm] = {"bot_global": g, "bot_global_lift": g / gc,
                   "bot_within_window": ww, "bot_within_window_lift": ww / wc if ww else None}
    print(f"  {nm:22s} {g:>11.4f} {g/gc:>5.1f}x | {ww:>14.4f} {ww/wc:>5.1f}x")
print(f"\n  Bot occupies windows {sorted(set(win[yte=='Bot'].tolist()))} of {N_WINDOWS} "
      f"— within-window chance is {wc:.4f}, vs {gc:.4f} globally.")
print("  The lateness control MUST read ~1.0x within-window; anything else means "
      "this test is broken.")
report_control = control

# ------------------------------------------------------------ explanations ---
print("\n" + "=" * 92)
print("EXPLANATIONS — the KG's actual deliverable (top emerging clusters)")
print("=" * 92)
explanations = []
for cid in sorted(emerging, key=lambda c: -burst[c])[:8]:
    e = kg.explain(cid, burst[cid], True)
    m = te_lab == cid
    fams, cts = np.unique(yte[m], return_counts=True)
    e["actual_composition"] = {str(f): int(c) for f, c in
                               sorted(zip(fams, cts), key=lambda t: -t[1])[:3]}
    explanations.append(e)
    print(f"\n  {e['path']}")
    print(f"      (ground truth, for validation only: {e['actual_composition']})")

# ----------------------------------------------------------------- persist ---
with open(os.path.join(paths.MODELS, f"{TAG}.gpickle"), "wb") as f:
    pickle.dump({"graph": kg.G, "history": kg.history, "burstiness": burst,
                 "emerging": sorted(emerging), "k": K, "behaviours": BEH}, f)

report = {
    "config": {"seed": SEED, "k": K, "windows": N_WINDOWS, "tau": TAU,
               "burst_threshold": BURST_THR, "representation": "raw_features",
               "scope": "corroboration + explanation, NOT primary detection"},
    "graph": {"nodes": kg.G.number_of_nodes(), "edges": kg.G.number_of_edges(),
              "clusters": K, "behaviours": BEH,
              "attack_types": sorted(n.split(":", 1)[1] for n, d in kg.G.nodes(data=True)
                                     if d["kind"] == "AttackType")},
    "emerging": {"threshold": BURST_THR, "n_clusters": len(emerging),
                 "clusters": sorted(emerging),
                 "precision": prec, "recall": zd_f / float(is_zd.sum()),
                 "lift": prec / base, "base_rate": float(base)},
    "s_kg_metrics": metrics.flatten(r),
    "s_kg_causal_metrics": metrics.flatten(r_causal),
    "confound_control": report_control,
    "explanations": explanations,
    "caveats": [
        "Growth works substantially because CIC-IDS2017's attacks are scripted into "
        "fixed windows; a real network with continuous low-rate C2 would not produce it.",
        "'Temporal burstiness of a raw-feature cluster' does not require a knowledge "
        "graph. The KG earns its place through explanation/corroboration, not this number.",
        "s_kg is deliberately NOT fed to a fitted combiner: validation contains no "
        "zero-day by construction, so a fitted fuser cannot learn to weight it.",
        "LATENESS CONFOUND: a trivial 'later in the week' baseline scores Bot 0.1575 "
        "globally, beating the previous best channel (autoencoder, 0.1314). The global "
        "KG number is therefore inflated by CIC-IDS2017's attack schedule. Report the "
        "WITHIN-WINDOW figure alongside it -- that is the schedule-free measure.",
    ],
}
with open(os.path.join(paths.METADATA, f"{TAG}_report.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, indent=1)
print(f"\nwrote models/{TAG}.gpickle and outputs/metadata/{TAG}_report.json")

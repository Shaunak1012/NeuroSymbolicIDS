"""
latency.py — Phase 5's last unmeasured rigor item: how fast is this thing, and
WHICH PART is slow?

WHY THIS EXISTS
---------------
An IDS is a real-time system. Every other number in this project describes
*ranking quality*; none of them says whether the pipeline can keep up with a
network. `enhancements.md` #6 scoped it as *"one benchmark — 'X flows/sec on
CPU, KG adds Y ms' — answers the deployability question for almost no effort."*

That framing is too generous to a single number, and this script deliberately
does not produce one. **A throughput figure without its batch size is not a
claim**, and the project's own selling point — explanation — is not on the same
cost scale as detection. So the benchmark is per-COMPONENT and per-BATCH-SIZE,
and the headline is the ratio between components, not any absolute rate.

WHAT IS MEASURED, AND WHY EACH ONE
-----------------------------------
  1. `transform`   log1p + StandardScaler. The cheapest stage; included so the
                   others have a floor to be compared against.
  2. `behaviours`  `behavior.active_behaviour_matrix` — the symbolic pillar's
                   input. Pure numpy ramps over raw features.
  3. `cnn`         the neural pillar's forward pass, `model(x, training=False)`.
  4. `kg_assign`   MiniBatchKMeans.predict over K=200 centroids in 68-d — the
                   KG's per-flow cost.
  5. `kg_update`   `KnowledgeGraph.observe(...)` — the NetworkX edge reinforce.
                   **A batch/window operation by construction**, not per-flow.
  6. `kg_burst`    `KnowledgeGraph.burstiness()` — O(K x windows), independent
                   of batch size. The emerging-pattern score itself.
  7. `fusion`      `rankdata` per channel + mean, exactly as `fusion_multi.py`
                   does it. **Note what this implies** — see THE TRANSDUCTIVE
                   CAVEAT below.
  8. `explain_ig`  `integrated_gradients` at IG_STEPS=32, per flow, matching
                   `explain.py`'s definition.

THE KG CLASS IS EXEC'D FROM kg.py's OWN SOURCE
-----------------------------------------------
`kg.py` is a top-to-bottom script, so it cannot be imported without running the
whole Phase-4 build. Rather than *reimplement* `KnowledgeGraph` here — which
would silently measure a different thing the moment either copy changed — the
class node is located with `ast` and exec'd from `kg.py`'s source text. The
benchmark therefore cannot drift from the implementation. This is the
*"a 'same as X' comment is not evidence; read X"* lesson applied to a benchmark.

THE TRANSDUCTIVE CAVEAT (read before quoting the fusion cost)
--------------------------------------------------------------
`fusion_multi.py` fuses by `rankdata(scores) / n` per channel. **Ranking is a
global operation over the scored set**, so the +0.0527 fusion gain is measured
transductively: scoring one flow requires the whole test distribution. A
streaming deployment cannot do that — it would need a frozen reference
distribution, which is a different estimator and may be a different number.
This script measures the COST of the operation as implemented. It does **not**
establish what a streaming variant would score. Filed in KNOWN_ISSUES.

PRE-REGISTERED PREDICTIONS (written and committed before the first run)
------------------------------------------------------------------------
P1  **Detection is not the bottleneck.** At batch >= 2048 the CNN forward pass
    exceeds 10,000 flows/s on this CPU — comfortably above any flow rate this
    protocol's 114,658-flow test set implies. Detection throughput is a
    non-issue and the paper should not claim it as a contribution.

P2  **Explanation costs 2+ orders of magnitude more per flow than detection.**
    IG runs 32 forward+backward passes for ONE flow, versus one batched forward
    pass amortised over thousands. If confirmed, the operational rule is
    "explain alerts, not flows" — which is compatible with, and made safe by,
    Tier 1's alert-budget result: at 100 alerts the explanation bill is trivial,
    at 114,658 flows it is not.

P3  **The KG is cheap, and its cost is dominated by cluster ASSIGNMENT, not by
    the graph.** `observe()` touches O(clusters-in-batch x behaviours) edges per
    *window*, while `kg_assign` computes 200 distances per *flow*. If the graph
    update instead dominates, the KG's "adds Y ms" story is about NetworkX and
    not about the method.

P4  **Batch size dominates every throughput claim.** Batch 1 (true per-flow
    streaming) is >= 10x worse in flows/s than batch 8192 for the CNN. This is
    the reason the script refuses to emit a single headline rate.

Run:  scripts/run_long.sh latency.py            (LATENCY_DETERMINISM=0 for the
                                                 unpinned-threads arm)
Out:  outputs/metadata/latency_<arm>.json
"""
import os
import sys
import ast
import json
import time
import pickle
import platform

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import paths                                     # noqa: E402
import config                                    # noqa: E402
import features                                  # noqa: E402
import behavior                                  # noqa: E402

cfg = config.get()
SEED = cfg["seed"]
TFM = cfg["protocol"]["feature_transform"]
P = paths.PAPER

# Determinism pins intra=16/inter=2, which changes the threadpool and therefore
# the throughput. It is ON by default because it is the project's current
# default for every trainable script; the OFF arm is a separate invocation so
# both numbers are reportable. Thread counts must be set before TF initialises,
# so this cannot be swept inside one process.
DET = os.environ.get("LATENCY_DETERMINISM", "1") == "1"
ARM = "determinism_on" if DET else "determinism_off"

import determinism                               # noqa: E402
det_info = determinism.enable(SEED) if DET else {"deterministic": False}

import tensorflow as tf                          # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402
from sklearn.cluster import MiniBatchKMeans      # noqa: E402
from scipy.stats import rankdata                 # noqa: E402
import networkx as nx                            # noqa: E402

BATCHES = [1, 32, 256, 2048, 8192]
REPEATS = 15          # for the cheap components
REPEATS_IG = 60       # per-flow IG; each repeat is one flow
WARMUP = 3
IG_STEPS = 32         # must match explain.py
K = 200               # must match kg.py's default
N_WINDOWS = 20        # must match kg.py's default
TAU = 3.0             # must match kg.py's default

print("=" * 100)
print("PHASE 5 - LATENCY / THROUGHPUT  [%s]" % ARM)
print("=" * 100)


def bench(fn, repeats=REPEATS, warmup=WARMUP):
    """Median + IQR of wall time, warm-up discarded.

    MEDIAN, NOT MEAN, and IQR, NOT SD. Latency on a shared desktop is
    right-skewed: one scheduler hiccup drags a mean but not a median. This is
    the same discipline the rest of the project applies to seeds — report the
    spread, never a bare point estimate.
    """
    for _ in range(warmup):
        fn()
    ts = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn()
        ts.append((time.perf_counter() - t0) * 1000.0)   # ms
    ts = np.asarray(ts)
    return {"median_ms": float(np.median(ts)),
            "p25_ms": float(np.percentile(ts, 25)),
            "p75_ms": float(np.percentile(ts, 75)),
            "min_ms": float(ts.min()),
            "n": int(repeats)}


def with_rate(stat, n_flows):
    stat = dict(stat)
    stat["flows_per_s"] = (float(n_flows / (stat["median_ms"] / 1000.0))
                           if stat["median_ms"] > 0 else None)
    stat["us_per_flow"] = float(stat["median_ms"] * 1000.0 / n_flows)
    return stat


# ============================================================== SETUP ========
# Nothing in this block is timed: it is the cold-start cost a deployed system
# pays once, not the per-flow cost the benchmark is about.
print("\n[setup] loading arrays + fitting scaler/kmeans (not timed)")
t0 = time.perf_counter()
Xtr_raw = np.load(os.path.join(P, "X_train.npy"))
Xte_raw = np.load(os.path.join(P, "X_test.npy"))

Xtr = features.transform(Xtr_raw, TFM)
Xte = features.transform(Xte_raw, TFM)
sc = StandardScaler().fit(Xtr)
Xtr_s = sc.transform(Xtr).astype(np.float32)
Xte_s = sc.transform(Xte).astype(np.float32)
nf = Xte_s.shape[1]

rng = np.random.RandomState(0)
sub = rng.choice(len(Xtr_s), size=min(200_000, len(Xtr_s)), replace=False)
km = MiniBatchKMeans(n_clusters=K, random_state=SEED, n_init=5,
                     batch_size=4096).fit(Xtr_s[sub])

model = tf.keras.models.load_model(
    os.path.join(paths.MODELS, "cnn_paper.keras"), compile=False)
# Class order comes from the FITTED LABEL ENCODER, exactly as explain.py does it.
# There is no class_names.npy under the paper split -- the only such file in the
# project belongs to the superseded temporal pipeline and carries a
# wrong-protocol zero-day list (see paths.METADATA_LEGACY).
with open(os.path.join(paths.MODELS, "label_encoder_paper.pkl"), "rb") as fh:
    classes = list(pickle.load(fh).classes_)
BEN = classes.index("BENIGN")
thr = behavior.load_thresholds()
BEH = behavior.active_behaviour_names()
setup_s = time.perf_counter() - t0
print("[setup] done in %.1fs | test %s | %d active behaviours"
      % (setup_s, Xte_s.shape, len(BEH)))

# --- KnowledgeGraph, exec'd from kg.py's own source (see module docstring) ---
kg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kg.py")
with open(kg_path, encoding="utf-8") as fh:
    kg_src = fh.read()
kg_tree = ast.parse(kg_src)
kg_cls = next(n for n in kg_tree.body
              if isinstance(n, ast.ClassDef) and n.name == "KnowledgeGraph")

# The exec'd class still closes over kg.py's MODULE scope -- on the first run it
# raised NameError on `behavior`, which `__init__` uses for BEHAVIOUR_KIND. That
# is the exec approach earning its keep: a hand-copied class would have silently
# dropped the same dependency. Rather than hardcode the list, resolve kg.py's
# module-level imports/assignments against the ones latency.py already holds, so
# a new dependency in kg.py is picked up instead of needing a fix here.
kg_mod_names = set()
for _n in kg_tree.body:
    if isinstance(_n, (ast.Import, ast.ImportFrom)):
        for _a in _n.names:
            kg_mod_names.add(_a.asname or _a.name.split(".")[0])
    elif isinstance(_n, ast.Assign):
        for _t in _n.targets:
            if isinstance(_t, ast.Name):
                kg_mod_names.add(_t.id)
ns = {n: globals()[n] for n in kg_mod_names if n in globals()}
exec(compile(ast.Module(body=[kg_cls], type_ignores=[]), "kg.py", "exec"), ns)
KnowledgeGraph = ns["KnowledgeGraph"]
print("[setup] KnowledgeGraph exec'd from kg.py source (line %d), "
      "globals bridged: %s" % (kg_cls.lineno, ", ".join(sorted(
          n for n in kg_mod_names if n in globals()))))

OUT = {
    "arm": ARM,
    "env": {
        "platform": platform.platform(),
        "processor": platform.processor(),
        "python": platform.python_version(),
        "tensorflow": tf.__version__,
        "cpu_count": os.cpu_count(),
        "determinism": det_info,
        "intra_op": tf.config.threading.get_intra_op_parallelism_threads(),
        "inter_op": tf.config.threading.get_inter_op_parallelism_threads(),
    },
    "config": {"batches": BATCHES, "repeats": REPEATS, "repeats_ig": REPEATS_IG,
               "warmup": WARMUP, "ig_steps": IG_STEPS, "k_clusters": K,
               "n_windows": N_WINDOWS, "setup_seconds": round(setup_s, 2)},
    "components": {},
}

# ========================================================== COMPONENTS =======
print("\n" + "-" * 100)
print("PER-COMPONENT, PER-BATCH  (median ms over %d repeats, warm-up discarded)"
      % REPEATS)
print("-" * 100)
print("%-14s %6s %11s %16s %10s %14s"
      % ("component", "batch", "median ms", "IQR ms", "us/flow", "flows/s"))

comp = OUT["components"]
for name in ("transform", "behaviours", "cnn", "kg_assign", "pipeline_detect"):
    comp[name] = {}

for bs in BATCHES:
    xr = Xte_raw[:bs]
    xs = Xte_s[:bs]
    xt = xs.reshape(-1, nf, 1)

    r = with_rate(bench(lambda: sc.transform(features.transform(xr, TFM))), bs)
    comp["transform"][str(bs)] = r

    rb = with_rate(bench(lambda: behavior.active_behaviour_matrix(xr, thr)), bs)
    comp["behaviours"][str(bs)] = rb

    rc = with_rate(bench(lambda: model(xt, training=False).numpy()), bs)
    comp["cnn"][str(bs)] = rc

    rk = with_rate(bench(lambda: km.predict(xs)), bs)
    comp["kg_assign"][str(bs)] = rk

    # End-to-end detection path: raw flow -> transform -> (behaviours || CNN ||
    # cluster assign). Explanation is deliberately NOT in it -- P2 is the reason.
    def _detect(xr=xr):
        z = sc.transform(features.transform(xr, TFM)).astype(np.float32)
        behavior.active_behaviour_matrix(xr, thr)
        model(z.reshape(-1, nf, 1), training=False).numpy()
        km.predict(z)

    rp = with_rate(bench(_detect), bs)
    comp["pipeline_detect"][str(bs)] = rp

    for nm, st in (("transform", r), ("behaviours", rb), ("cnn", rc),
                   ("kg_assign", rk), ("pipeline_detect", rp)):
        print("%-14s %6d %11.3f %7.3f-%-8.3f %10.2f %14s"
              % (nm, bs, st["median_ms"], st["p25_ms"], st["p75_ms"],
                 st["us_per_flow"], format(st["flows_per_s"], ",.0f")))
    print()

# ---------------------------------------------------------------- KG graph ---
# observe() is a WINDOW operation in kg.py: the test stream is cut into 20
# windows and the graph is updated once per window. Timing it per-flow would
# misrepresent how it is actually called, so it is timed per window at the real
# window size, and the per-flow figure is the amortised one.
print("-" * 100)
print("KG GRAPH OPS  (window-level by construction, not per-flow)")
print("-" * 100)
win_n = len(Xte_s) // N_WINDOWS
lab_w = km.predict(Xte_s[:win_n])
beh_w = behavior.active_behaviour_matrix(Xte_raw[:win_n], thr)

kg_obj = KnowledgeGraph(K, BEH, TAU)
r_obs = with_rate(bench(lambda: kg_obj.observe(lab_w, beh_w, record_history=True),
                        repeats=REPEATS), win_n)
r_dec = bench(lambda: kg_obj.decay(), repeats=REPEATS)
r_bst = bench(lambda: kg_obj.burstiness(), repeats=REPEATS)
comp["kg_update_per_window"] = r_obs
comp["kg_decay_per_window"] = r_dec
comp["kg_burstiness"] = r_bst
print("%-14s %6d %11.3f %7.3f-%-8.3f %10.2f %14s   (per WINDOW of %s flows)"
      % ("kg_update", win_n, r_obs["median_ms"], r_obs["p25_ms"], r_obs["p75_ms"],
         r_obs["us_per_flow"], format(r_obs["flows_per_s"], ",.0f"),
         format(win_n, ",")))
print("%-14s %6s %11.3f %7.3f-%-8.3f   (whole graph, per window)"
      % ("kg_decay", "-", r_dec["median_ms"], r_dec["p25_ms"], r_dec["p75_ms"]))
print("%-14s %6s %11.3f %7.3f-%-8.3f   (K=%d x %d windows)"
      % ("kg_burstiness", "-", r_bst["median_ms"], r_bst["p25_ms"],
         r_bst["p75_ms"], K, N_WINDOWS))

# ----------------------------------------------------------------- fusion ---
# Exactly fusion_multi.py's operation: rankdata per channel, then mean. Timed
# at several set sizes because the cost is O(N log N) in the SCORED SET, not in
# any per-flow sense -- which is the transductive caveat, in timing form.
print("\n" + "-" * 100)
print("FUSION  (rank fusion is a GLOBAL op over the scored set - see the")
print("        transductive caveat in the docstring)")
print("-" * 100)
comp["fusion"] = {}
s1 = np.random.RandomState(0).rand(len(Xte_s))
s2 = np.random.RandomState(1).rand(len(Xte_s))
for n in (10_000, len(Xte_s)):
    a, b = s1[:n], s2[:n]

    def _fuse(a=a, b=b, n=n):
        return np.mean([rankdata(a) / n, rankdata(b) / n], axis=0)

    rf = with_rate(bench(_fuse, repeats=5), n)
    comp["fusion"][str(n)] = rf
    print("%-14s %6d %11.3f %7.3f-%-8.3f %10.2f %14s   (2 channels)"
          % ("fusion", n, rf["median_ms"], rf["p25_ms"], rf["p75_ms"],
             rf["us_per_flow"], format(rf["flows_per_s"], ",.0f")))

# -------------------------------------------------------------- explain IG ---
# Matches explain.py's definition (IG_STEPS=32, mean-flow baseline). Unlike the
# KG class this is a short function, so it is reproduced rather than exec'd --
# but the constant and the baseline are pinned to explain.py's.
print("\n" + "-" * 100)
print("EXPLANATION - Integrated Gradients, PER FLOW (this is P2)")
print("-" * 100)
BASELINE = Xtr_s.mean(0).astype(np.float32)


def integrated_gradients(x, steps=IG_STEPS):
    alphas = np.linspace(0, 1, steps, dtype=np.float32)
    path = BASELINE[None, :] + alphas[:, None] * (x[None, :] - BASELINE[None, :])
    t = tf.convert_to_tensor(path.reshape(-1, nf, 1))
    with tf.GradientTape() as tape:
        tape.watch(t)
        s = 1.0 - model(t, training=False)[:, BEN]
    g = tape.gradient(s, t).numpy().reshape(steps, nf)
    avg_grad = (g[:-1] + g[1:]).mean(0) / 2.0
    return (x - BASELINE) * avg_grad


_ig_i = {"n": 0}


def _one_ig():
    # A different flow each repeat, so this measures IG and not one flow's cache.
    i = _ig_i["n"] % len(Xte_s)
    _ig_i["n"] += 1
    integrated_gradients(Xte_s[i])


r_ig = with_rate(bench(_one_ig, repeats=REPEATS_IG), 1)
comp["explain_ig_per_flow"] = r_ig
print("%-14s %6d %11.3f %7.3f-%-8.3f %10.2f %14s"
      % ("explain_ig", 1, r_ig["median_ms"], r_ig["p25_ms"], r_ig["p75_ms"],
         r_ig["us_per_flow"], format(r_ig["flows_per_s"], ",.0f")))

# ========================================================== VERDICTS =========
print("\n" + "=" * 100)
print("PRE-REGISTERED PREDICTIONS")
print("=" * 100)

cnn_2048 = comp["cnn"]["2048"]["flows_per_s"]
cnn_1 = comp["cnn"]["1"]["flows_per_s"]
cnn_max = comp["cnn"]["8192"]["flows_per_s"]
det_us = comp["cnn"]["8192"]["us_per_flow"]
ig_us = r_ig["us_per_flow"]
ratio_ig = ig_us / det_us
ratio_batch = cnn_max / cnn_1
kg_assign_us = comp["kg_assign"]["8192"]["us_per_flow"]
kg_update_us = r_obs["us_per_flow"]

V = {
    "P1_detection_not_bottleneck": {
        "cnn_flows_per_s_batch2048": cnn_2048,
        "threshold": 10_000,
        "confirmed": bool(cnn_2048 > 10_000)},
    "P2_explanation_dominates": {
        "ig_us_per_flow": ig_us, "cnn_us_per_flow_batch8192": det_us,
        "ratio": float(ratio_ig), "threshold": 100.0,
        "confirmed": bool(ratio_ig > 100.0)},
    "P3_kg_assign_dominates_graph": {
        "kg_assign_us_per_flow": kg_assign_us,
        "kg_update_us_per_flow_amortised": kg_update_us,
        "confirmed": bool(kg_assign_us > kg_update_us)},
    "P4_batch_dominates_throughput": {
        "cnn_flows_per_s_batch1": cnn_1, "cnn_flows_per_s_batch8192": cnn_max,
        "ratio": float(ratio_batch), "threshold": 10.0,
        "confirmed": bool(ratio_batch >= 10.0)},
}
OUT["predictions"] = V
for k, v in V.items():
    print("  %-10s  %s" % ("CONFIRMED" if v["confirmed"] else "FALSIFIED", k))
print("\n  explanation / detection cost ratio : %s x" % format(ratio_ig, ",.0f"))
print("  batch-1 vs batch-8192 throughput   : %s x" % format(ratio_batch, ",.1f"))
print("  KG adds (assign + amortised update): %.2f us/flow"
      % (kg_assign_us + kg_update_us))

# The operational sentence this whole script exists to make sayable.
alerts_100 = 100 * ig_us / 1e6
all_flows = len(Xte_s) * ig_us / 1e6
OUT["explanation_budget"] = {
    "seconds_to_explain_100_alerts": alerts_100,
    "seconds_to_explain_all_test_flows": all_flows,
    "n_test": int(len(Xte_s))}
print("\n  explaining 100 alerts   : %8.2f s" % alerts_100)
print("  explaining all %s : %8.0f s (%.1f h)  <- why 'explain alerts, not flows'"
      % (format(len(Xte_s), ","), all_flows, all_flows / 3600))

out_path = os.path.join(paths.METADATA, "latency_%s.json" % ARM)
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(OUT, f, indent=2)
print("\nwrote %s" % out_path)
print("DONE")

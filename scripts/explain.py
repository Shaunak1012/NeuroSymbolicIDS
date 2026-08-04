"""
explain.py — the explainability half of canonical Phase 4, plus the faithfulness
measurement the roadmap lists as Tier-A.

Phase 4 = "Knowledge Graph + explainability". `kg.py` delivered the KG and one of
the three explanations. This delivers the other two, assembles the Final Alert,
and — the part almost nobody in this field does — **measures whether the neural
explanation is actually faithful to the model**.

THE THREE EXPLANATIONS (per docs/target/explainability.md)
----------------------------------------------------------
1. **Neural** — feature attribution over the 68 flow features.
   Uses **Integrated Gradients** (Sundararajan et al.) rather than SHAP's
   DeepExplainer: IG is implemented directly against `tf.GradientTape`, has an
   exactness check (the completeness axiom, verified below), and does not depend
   on SHAP's brittle Keras-2 Conv1D support. Baseline = the training mean, i.e.
   "an average flow", so attributions read as *deviation from typical traffic*.
2. **Logic** — per-axiom satisfaction for this flow.
   ⚠️ Only the **behaviour-grounded** axioms (Ax3-Ax6) are usable at inference.
   Ax1/Ax2 are *label anchors* — they condition on the ground-truth class, which
   does not exist at prediction time. Reporting them as explanations would be
   circular. This is why only 4 of 6 axioms appear.
3. **KG** — reasoning path from `kg.py` (cluster -> behaviours -> known attacks,
   plus whether the cluster is currently emerging).

FAITHFULNESS (the Tier-A measurement)
-------------------------------------
An explanation that looks plausible but does not reflect the model is worse than
none. Standard ERASER-style deletion metrics, each against a **random-feature
control** — without the control the numbers are meaningless:

  * **Comprehensiveness** — mask the top-k attributed features; the model's attack
    score should DROP. Higher is better. If top-k ≈ random-k, the attribution is
    not identifying what the model uses.
  * **Sufficiency** — keep ONLY the top-k; the score should stay close to the
    original. Lower gap is better.

Run:  python scripts/explain.py
Out:  outputs/metadata/explanations.json  (alerts + faithfulness)
"""
import os
import csv
import json
import pickle
import numpy as np

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
import paths, config, features, behavior

cfg = config.get()
SEED = cfg["seed"]
TFM = cfg["protocol"]["feature_transform"]
P = paths.PAPER
N_ALERTS = int(os.environ.get("EXPLAIN_ALERTS", 6))
N_FAITH = int(os.environ.get("EXPLAIN_FAITH_N", 1500))
IG_STEPS = 32

# ------------------------------------------------------------------ data ----
yte = np.load(os.path.join(P, "y_test_mc.npy"), allow_pickle=True)
zero_day = set(np.load(os.path.join(P, "zero_day_classes.npy"), allow_pickle=True).tolist())
Xtr_raw = np.load(os.path.join(P, "X_train.npy"))
Xte_raw = np.load(os.path.join(P, "X_test.npy"))
with open(os.path.join(paths.PROCESSED, "features_train.csv"), encoding="utf-8") as f:
    FEAT = next(csv.reader(f))

from sklearn.preprocessing import StandardScaler
Xtr = features.transform(Xtr_raw, TFM); Xte = features.transform(Xte_raw, TFM)
sc = StandardScaler().fit(Xtr)
Xtr_s, Xte_s = sc.transform(Xtr), sc.transform(Xte)
nf = Xte_s.shape[1]

import tensorflow as tf
import pickle as pk
model = tf.keras.models.load_model(os.path.join(paths.MODELS, "cnn_paper.keras"), compile=False)
with open(os.path.join(paths.MODELS, "label_encoder_paper.pkl"), "rb") as f:
    classes = list(pk.load(f).classes_)
BEN = classes.index("BENIGN")
print(f"loaded CNN ({len(classes)} classes) · {nf} features · test {Xte_s.shape}")


def attack_score(Xs, bs=8192):
    """p(attack) = 1 - softmax[BENIGN]."""
    out = []
    for i in range(0, len(Xs), bs):
        p = model.predict(Xs[i:i+bs].reshape(-1, nf, 1), verbose=0)
        out.append(1.0 - p[:, BEN])
    return np.concatenate(out)


# =========================================================== 1. NEURAL =======
BASELINE = Xtr_s.mean(0).astype(np.float32)     # "an average flow"


def integrated_gradients(x, steps=IG_STEPS):
    """IG attribution of p(attack) w.r.t. each of the 68 features."""
    alphas = np.linspace(0, 1, steps, dtype=np.float32)
    path = BASELINE[None, :] + alphas[:, None] * (x[None, :] - BASELINE[None, :])
    t = tf.convert_to_tensor(path.reshape(-1, nf, 1))
    with tf.GradientTape() as tape:
        tape.watch(t)
        s = 1.0 - model(t, training=False)[:, BEN]
    g = tape.gradient(s, t).numpy().reshape(steps, nf)
    avg_grad = (g[:-1] + g[1:]).mean(0) / 2.0        # trapezoidal
    return (x - BASELINE) * avg_grad


def ig_completeness(x, attr):
    """IG's completeness axiom: sum(attr) ~= f(x) - f(baseline). A correctness check."""
    fx = attack_score(x[None, :])[0]
    fb = attack_score(BASELINE[None, :])[0]
    return float(attr.sum()), float(fx - fb)


# ============================================================ 2. LOGIC =======
thr = behavior.compute_thresholds(Xtr_raw)
b_te = behavior.abstract_behaviours(Xte_raw, thr)
AXIOMS = {   # only the behaviour-grounded ones are usable at inference time
    "Ax3 LargePackets AND HighEntropy => attack": b_te["LargePackets"] * b_te["HighEntropy"],
    "Ax4 BurstTraffic => attack":                 b_te["BurstTraffic"],
    "Ax5 ScanProbe => attack":                    b_te["ScanProbe"],
    "Ax6 BeaconLike => attack":                   b_te["BeaconLike"],
}


def logic_explanation(i, p_atk):
    """Per-flow axiom firing + whether the model agrees. Satisfaction = p(attack)
    when the antecedent holds, so a strongly-firing axiom on a low-p(attack) flow
    is a genuine VIOLATION worth surfacing."""
    out = []
    for name, w in AXIOMS.items():
        fire = float(w[i])
        if fire <= 0.01:
            continue
        out.append({"axiom": name, "antecedent_strength": round(fire, 3),
                    "satisfaction": round(float(p_atk), 4),
                    "status": "satisfied" if p_atk >= 0.5 else "VIOLATED"})
    return sorted(out, key=lambda d: -d["antecedent_strength"])


# =============================================================== 3. KG =======
kg_expl = {}
kgp = os.path.join(paths.MODELS, "kg.gpickle")
if os.path.exists(kgp):
    with open(kgp, "rb") as f:
        blob = pickle.load(f)
    Gk, burst_k, emerging_k = blob["graph"], blob["burstiness"], set(blob["emerging"])
    from sklearn.cluster import MiniBatchKMeans
    rng = np.random.RandomState(0)
    sub = rng.choice(len(Xtr_s), size=min(200_000, len(Xtr_s)), replace=False)
    km = MiniBatchKMeans(n_clusters=blob["k"], random_state=SEED, n_init=5,
                         batch_size=4096).fit(Xtr_s[sub])
    te_cl = km.predict(Xte_s)

    def kg_path(i):
        c = int(te_cl[i]); cn = f"Cluster:{c}"
        top = {}
        for _, v, d in Gk.out_edges(cn, data=True):
            top.setdefault(d["rel"], []).append((v.split(":", 1)[1], d["weight"]))
        parts = {}
        for rel, lst in top.items():
            tot = sum(w for _, w in lst) or 1.0
            parts[rel] = [(k, round(w / tot, 3)) for k, w in sorted(lst, key=lambda t: -t[1])[:3]]
        return {"cluster": c, "burstiness": round(float(burst_k[c]), 2),
                "emerging": c in emerging_k,
                "exhibits": parts.get("exhibits", []),
                "associated_with": parts.get("associated_with", [])}
else:
    print("  !! kg.gpickle missing — KG explanation will be omitted")
    def kg_path(i):  # noqa: E306
        return None

# ================================================ FINAL ALERT ASSEMBLY =======
print("\n" + "=" * 96)
print("FINAL ALERT — 3 explanations assembled per flow")
print("=" * 96)
p_all = attack_score(Xte_s)
rng = np.random.RandomState(SEED)
picks = []
for fam in ["Bot", "Web Attack Brute Force", "BENIGN"]:
    idx = np.flatnonzero(yte == fam)
    picks += list(rng.choice(idx, min(2, len(idx)), replace=False))
alerts = []
for i in picks[:N_ALERTS]:
    attr = integrated_gradients(Xte_s[i].astype(np.float32))
    order = np.argsort(-np.abs(attr))[:5]
    s, tgt = ig_completeness(Xte_s[i].astype(np.float32), attr)
    a = {
        "true_class": str(yte[i]), "is_zero_day": bool(yte[i] in zero_day),
        "verdict": "malicious" if p_all[i] >= 0.5 else "benign",
        "confidence": round(float(p_all[i]), 4),
        "neural": [{"feature": FEAT[j], "attribution": round(float(attr[j]), 5)} for j in order],
        "ig_completeness": {"sum_attributions": round(s, 4), "f(x)-f(base)": round(tgt, 4)},
        "logic": logic_explanation(i, p_all[i]),
        "kg": kg_path(i),
    }
    alerts.append(a)
    zd = " [ZERO-DAY]" if a["is_zero_day"] else ""
    print(f"\n  flow #{i} — true={a['true_class']}{zd} → verdict={a['verdict']} "
          f"(p_attack={a['confidence']:.4f})")
    print(f"    NEURAL : " + ", ".join(f"{d['feature']}={d['attribution']:+.4f}" for d in a["neural"][:3]))
    if a["logic"]:
        print(f"    LOGIC  : " + " | ".join(
            f"{d['axiom'].split()[0]} fires {d['antecedent_strength']:.2f} → {d['status']}" for d in a["logic"]))
    else:
        print("    LOGIC  : no behaviour axiom fires for this flow")
    if a["kg"]:
        k = a["kg"]
        print(f"    KG     : Cluster:{k['cluster']} burst={k['burstiness']}x "
              f"{'EMERGING' if k['emerging'] else 'stable'} | "
              f"exhibits {k['exhibits'][:2]} | known {k['associated_with'][:2]}")

# ==================================================== 4. FAITHFULNESS ========
print("\n" + "=" * 96)
print("FAITHFULNESS OF THE NEURAL EXPLANATION (Tier-A) — vs a random-feature control")
print("=" * 96)
fi = rng.choice(len(Xte_s), N_FAITH, replace=False)
X = Xte_s[fi].astype(np.float32)
base_scores = attack_score(X)
A = np.stack([integrated_gradients(x) for x in X])
rank = np.argsort(-np.abs(A), axis=1)
rnd = np.stack([rng.permutation(nf) for _ in range(len(X))])
FA = {}
for k in (3, 5, 10):
    def mask_top(sel, keep_only):
        Xm = X.copy()
        for r in range(len(X)):
            idx = sel[r, :k]
            if keep_only:
                m = np.full(nf, True); m[idx] = False
                Xm[r, m] = BASELINE[m]
            else:
                Xm[r, idx] = BASELINE[idx]
        return attack_score(Xm)
    comp_ig = float(np.mean(base_scores - mask_top(rank, False)))
    comp_rd = float(np.mean(base_scores - mask_top(rnd, False)))
    suff_ig = float(np.mean(np.abs(base_scores - mask_top(rank, True))))
    suff_rd = float(np.mean(np.abs(base_scores - mask_top(rnd, True))))
    FA[f"k={k}"] = {"comprehensiveness_ig": comp_ig, "comprehensiveness_random": comp_rd,
                    "comp_ratio": comp_ig / comp_rd if comp_rd else None,
                    "sufficiency_gap_ig": suff_ig, "sufficiency_gap_random": suff_rd}
    print(f"  top-{k:2d} | COMPREHENSIVENESS  IG {comp_ig:+.4f}  random {comp_rd:+.4f}  "
          f"ratio {comp_ig/comp_rd if comp_rd else float('nan'):5.2f}x")
    print(f"         | SUFFICIENCY gap    IG {suff_ig:.4f}   random {suff_rd:.4f}  "
          f"(lower = the top-k alone reproduce the decision)")
print("\n  A faithful attribution beats the random control on BOTH. If ratio ~= 1.0,")
print("  the explanation is decorative — it is not identifying what the model uses.")

out = {"n_alerts": len(alerts), "alerts": alerts, "faithfulness": FA,
       "faithfulness_n_flows": N_FAITH, "ig_steps": IG_STEPS,
       "notes": [
           "Only behaviour-grounded axioms (Ax3-Ax6) appear: Ax1/Ax2 are label anchors "
           "that condition on ground truth and are unavailable (and circular) at inference.",
           "IG baseline is the training mean, so attributions read as deviation from "
           "typical traffic.",
           "Faithfulness is meaningless without the random-feature control; both are reported.",
       ]}
with open(os.path.join(paths.METADATA, "explanations.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1)
print(f"\nwrote {os.path.join(paths.METADATA, 'explanations.json')}")

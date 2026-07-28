"""
fusion_beaconlike.py — Phase-2, inference-level integration point (#3 from the
"three symbolic integration points" table in conference_roadmap.md — the one point
never tried this session; loss-level (Ax6-in-SAT) and representation-level (aux-head)
both touch training, and both cost macro PR-AUC because they compete with every other
family for the same shared decision boundary.

Idea: BeaconLike gets ROC 0.887 on Bot-vs-benign standing completely alone (see
skyline_oracle.py / behavior.py). Instead of injecting it into the loss, calibrate a
tiny combiner (base model's attack log-odds + BeaconLike's raw score) fit ONLY on
KNOWN-class validation data (never touches zero-day labels — the paper split's val set
has no zero-day flows by construction, so this cannot leak), then apply blind to the
zero-day test set. If this recovers Bot's lift without the CNN's macro dropping, that
is a genuinely different (and better) mechanism than loss-level injection.

Run: python scripts/fusion_beaconlike.py
"""
import os
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
import numpy as np
import tensorflow as tf
from tensorflow.keras import models
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.linear_model import LogisticRegression
from scipy.special import logsumexp

import paths, config, features, behavior, metrics, tracking

cfg = config.get()
PAPER = os.path.join(paths.PROCESSED, cfg["paths"]["paper_subdir"])
TFM = cfg["protocol"]["feature_transform"]
BASE_TAG = "cnn_paper"   # fuse with the strongest available baseline, not the weaker control


def load(s):
    return (np.load(os.path.join(PAPER, f"X_{s}.npy")),
            np.load(os.path.join(PAPER, f"y_{s}_mc.npy"), allow_pickle=True))


Xtr_raw, ytr = load("train")
Xval_raw, yval = load("val")
Xte_raw, yte = load("test")
zero_day = np.load(os.path.join(PAPER, "zero_day_classes.npy"), allow_pickle=True).tolist()
assert not any(c in yval for c in zero_day), "val set must contain no zero-day flows"

sc = StandardScaler().fit(features.transform(Xtr_raw, TFM))
def prep(Xraw): return sc.transform(features.transform(Xraw, TFM)).reshape(-1, Xraw.shape[1], 1).astype(np.float32)
Xval, Xte = prep(Xval_raw), prep(Xte_raw)

le = LabelEncoder().fit(ytr)
benign_idx = list(le.classes_).index("BENIGN")
attack_idx = [i for i in range(len(le.classes_)) if i != benign_idx]


def logit_scores(model, Xprepped):
    """Attack log-odds = logsumexp(attack logits) - benign logit, from the pre-softmax head."""
    head = None
    for layer in reversed(model.layers):
        if isinstance(layer, tf.keras.layers.Dense) and \
           getattr(layer.activation, "__name__", "") == "softmax":
            head = layer
            break
    penult = models.Model(model.input, head.input)
    W, b = head.get_weights()
    z = penult.predict(Xprepped, batch_size=1024, verbose=0) @ W + b
    return logsumexp(z[:, attack_idx], axis=1) - z[:, benign_idx]


print(f"Loading base model: {BASE_TAG} ...")
base_model = models.load_model(os.path.join(paths.MODELS, f"{BASE_TAG}.keras"), compile=False)
base_val = logit_scores(base_model, Xval)
base_te = logit_scores(base_model, Xte)

# BeaconLike (and, for a richer variant, all behaviour signals) — pure numpy, no TF
thr = behavior.compute_thresholds(Xtr_raw)
beh_val = behavior.abstract_behaviours(Xval_raw, thr)
beh_te = behavior.abstract_behaviours(Xte_raw, thr)

is_attack_val = (yval != "BENIGN").astype(int)


def fit_and_eval(name, feat_val, feat_te):
    clf = LogisticRegression(max_iter=1000)
    clf.fit(feat_val, is_attack_val)
    score_te = clf.predict_proba(feat_te)[:, 1]
    res = metrics.evaluate(yte, score_te, zero_day, fpr=0.01)
    print("=" * 78)
    print(f"{name}  (fit on val: n={len(feat_val):,}, coefs={clf.coef_[0]}, intercept={clf.intercept_[0]:.3f})")
    metrics.print_report(res)
    tracking.log_run(name, {"protocol": "paper", "base": BASE_TAG, "fusion": "logistic_val_fit",
                            "features": feat_val.shape[1]}, metrics.flatten(res))
    return res, score_te


# Variant A: base model logit + BeaconLike alone (clean, isolates BeaconLike's marginal value)
fA_val = np.stack([base_val, beh_val["BeaconLike"]], axis=1)
fA_te = np.stack([base_te, beh_te["BeaconLike"]], axis=1)
res_a, score_a = fit_and_eval("fusion_cnn_beaconlike", fA_val, fA_te)
np.save(os.path.join(paths.PREDICTIONS, "y_prob_fusion_cnn_beaconlike_test.npy"), score_a.astype(np.float32))

# Variant B: base model logit + ALL behaviour signals (more expressive combiner)
beh_names = [n for n in behavior.BEHAVIOUR_NAMES if n != "RepeatedConnections"]
fB_val = np.stack([base_val] + [beh_val[n] for n in beh_names], axis=1)
fB_te = np.stack([base_te] + [beh_te[n] for n in beh_names], axis=1)
res_b, score_b = fit_and_eval("fusion_cnn_allbehaviours", fB_val, fB_te)
np.save(os.path.join(paths.PREDICTIONS, "y_prob_fusion_cnn_allbehaviours_test.npy"), score_b.astype(np.float32))

# Baseline for comparison: base model alone, no fusion at all
res_base = metrics.evaluate(yte, base_te, zero_day, fpr=0.01)
print("=" * 78)
print(f"{BASE_TAG} ALONE (no fusion, for comparison):")
metrics.print_report(res_base)

print("\n" + "=" * 78)
print("HEAD-TO-HEAD SUMMARY")
print(f"{'variant':30s} {'macro':>8s} {'Bot PR':>8s} {'Bot lift':>9s}")
for name, r in [(f"{BASE_TAG} alone", res_base), ("fusion +BeaconLike", res_a), ("fusion +all behaviours", res_b)]:
    m = r["macro"]; f = r["zeroday_family"]["Bot"]
    print(f"{name:30s} {m['pr_auc']:>8.4f} {f['pr_auc']:>8.4f} {f['lift']:>9.1f}")
print("DONE (fusion_beaconlike)")

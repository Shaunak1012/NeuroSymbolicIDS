"""
rescore_logits.py — recompute zero-day scores in LOG-ODDS space from saved models.

Why this exists
---------------
Every score saved so far was `patk = 1 - softmax(...)[benign]` in float32. For a
confident model `p(benign)` rounds to exactly 1.0, so `patk` underflows to exactly
0.0 — measured on `ltn_ctrl_w0`: 99.25% of benign flows and 51.7% of zero-day flows
sit at exactly 0.0. Consequences:
  * the 1%-FPR threshold lands at 0.0, flags everything, and reports recall=1.0 for
    every family (an artefact, not detection),
  * `zd_f1` collapses to the algebraic predict-all constant (0.1315 at 7% prevalence),
  * PR-AUC compares a saturated model against a non-saturated one — not like-for-like.

Log-odds fixes this at the source: read the model's PRE-SOFTMAX logits and score

    s = logsumexp(attack_logits) - benign_logit      # == log( P(attack) / P(benign) )

which keeps resolution across many orders of magnitude. The saved probability
arrays cannot be repaired after the fact (the information is already gone), so we
re-run inference from the saved .keras models.

Writes `y_prob_{tag}_logodds_test.npy` and logs each run as `{tag}_logodds`.
NOTE: `cnn_auxhead_l0.5` has no saved model (cnn_auxhead_paper.py never calls
model.save) and is therefore skipped — it needs a retrain to be re-scored.

FIXED 2026-08-02 (see docs/KNOWN_ISSUES.md, C5): every logged entry used to be
stamped with `cfg["seed"]` (always the config default, 42) regardless of which
seed's model was actually being rescored -- wrong on every `_s43`/`_s44` tag.
Seed is now parsed from the `_s<seed>` suffix already used by every multi-seed
tag in this codebase (cnn_paper_s43, ltn_ctrl_w0_s43, ...), falling back to the
config default only for unsuffixed tags.
"""
import os
import re
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
import numpy as np
import tensorflow as tf
tf.config.threading.set_intra_op_parallelism_threads(16)
tf.config.threading.set_inter_op_parallelism_threads(2)
from tensorflow.keras import models
from sklearn.preprocessing import StandardScaler, LabelEncoder
from scipy.special import logsumexp

import paths, config, features, metrics, tracking

cfg = config.get()
PAPER = os.path.join(paths.PROCESSED, cfg["paths"]["paper_subdir"])
TFM = cfg["protocol"]["feature_transform"]

TAGS = ["cnn_paper", "ltn_ctrl_w0", "ltn_repro", "ltn_v2",
        "ltn_anat_w0p5", "ltn_anat_w1p0", "ltn_anat_w2p0",
        "ltn_ax6_w0p5", "ltn_ax6_w1p0", "cnn_auxhead_l0.5",
        "ltn_ctrl_w0_s43", "ltn_ctrl_w0_s44",
        "ltn_ax6_w0p5_s43", "ltn_ax6_w0p5_s44",
        "ltn_ax6_w1p0_s43", "ltn_ax6_w1p0_s44",
        "ltn_ax6_ratio_w1p0_s42", "ltn_ax6_ratio_w1p0_s43", "ltn_ax6_ratio_w1p0_s44",
        "cnn_paper_s43", "cnn_paper_s44"]  # added 2026-08-02 for STATUS audit C2
# NOTE: re-running this full list re-scores everything and appends a fresh
# runs.jsonl entry per tag every time -- do not run it just to add one new tag
# (see KNOWN_ISSUES C5, "runs.jsonl mixes... duplicated 3x").
#
# ⚠️ The old workaround was "temporarily edit TAGS, run, then restore". That is
# exactly the kind of manual edit-run-restore dance that gets forgotten halfway
# through, and it is how the duplicate rows in runs.jsonl were created in the
# first place. Use the env var instead -- no edit, nothing to restore:
#
#     RESCORE_TAGS=cnn_paper_s45,cnn_paper_s46 python scripts/rescore_logits.py
#
# Added 2026-08-03 when seeds 45-47 needed rescoring for the n=6 seed-level test.
_env_tags = os.environ.get("RESCORE_TAGS", "").strip()
if _env_tags:
    TAGS = [t.strip() for t in _env_tags.split(",") if t.strip()]
    print(f"RESCORE_TAGS set -> scoped to {len(TAGS)} tag(s): {', '.join(TAGS)}")


def tag_seed(tag):
    """Parse the seed from a `..._s<seed>` tag suffix; else the config default."""
    m = re.search(r"_s(\d+)$", tag)
    return int(m.group(1)) if m else cfg["seed"]


def load(s):
    return (np.load(os.path.join(PAPER, f"X_{s}.npy")),
            np.load(os.path.join(PAPER, f"y_{s}_mc.npy"), allow_pickle=True))


Xtr_raw, ytr = load("train")
Xte_raw, yte = load("test")
zero_day = np.load(os.path.join(PAPER, "zero_day_classes.npy"), allow_pickle=True).tolist()

# identical preprocessing to training: signed-log1p then train-fitted StandardScaler
sc = StandardScaler().fit(features.transform(Xtr_raw, TFM))
Xte = sc.transform(features.transform(Xte_raw, TFM)).reshape(-1, Xtr_raw.shape[1], 1).astype(np.float32)

le = LabelEncoder().fit(ytr)
benign_idx = list(le.classes_).index("BENIGN")
attack_idx = [i for i in range(len(le.classes_)) if i != benign_idx]
print(f"classes={list(le.classes_)}\nbenign_idx={benign_idx}\n")


def logit_scores(model):
    """Pre-softmax log-odds of attack vs benign."""
    # find the classification head (last Dense with softmax)
    head = None
    for layer in reversed(model.layers):
        if isinstance(layer, tf.keras.layers.Dense) and \
           getattr(layer.activation, "__name__", "") == "softmax":
            head = layer
            break
    if head is None:
        raise RuntimeError("no softmax Dense head found")

    # rebuild up to the head's INPUT, then apply W,b manually -> raw logits
    penult = models.Model(model.input, head.input)
    W, b = head.get_weights()
    z = penult.predict(Xte, batch_size=1024, verbose=0) @ W + b
    return logsumexp(z[:, attack_idx], axis=1) - z[:, benign_idx], head.name


for tag in TAGS:
    path = os.path.join(paths.MODELS, f"{tag}.keras")
    if not os.path.exists(path):
        print(f"[skip] {tag}: no saved model")
        continue

    model = models.load_model(path, compile=False)
    s, head_name = logit_scores(model)
    np.save(os.path.join(paths.PREDICTIONS, f"y_prob_{tag}_logodds_test.npy"),
            s.astype(np.float64))

    res = metrics.evaluate(yte, s, zero_day, fpr=0.01)
    print("=" * 78)
    print(f"{tag}   (head='{head_name}', log-odds range "
          f"[{s.min():.1f}, {s.max():.1f}], {len(np.unique(s)):,} distinct)")
    metrics.print_report(res)
    tracking.log_run(f"{tag}_logodds",
                     {"protocol": "paper", "scoring": "logodds", "seed": tag_seed(tag)},
                     metrics.flatten(res))
    print()

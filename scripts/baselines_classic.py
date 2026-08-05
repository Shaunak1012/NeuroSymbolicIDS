"""
baselines_classic.py — Tier A: the classic ML baselines every NIDS paper reports
and this project had never run.

WHY
---
`baselines.py` covers XGBoost / RandomForest / IsolationForest. The CIC-IDS2017
literature's standard comparison table also carries **Decision Tree, k-NN, Naive
Bayes, Logistic Regression, SVM and MLP**, and a capstone comparison table
without them looks incomplete regardless of what the numbers say.

Same protocol as `baselines.py`: paper split, log1p + StandardScaler fit on
train, **binary** target (benign vs attack), evaluated by `metrics.py` with macro
zero-day PR-AUC as the headline, logged to `runs.jsonl`, scores saved so any of
them can be fused like any other channel.

  BASELINE_SEED=43 python scripts/baselines_classic.py   # -> `<name>_s43` tags

⚠️ TWO SCALE DEVIATIONS, BOTH DELIBERATE AND BOTH REPORTED
-----------------------------------------------------------
1. **k-NN is fitted on a stratified 50,000-row subsample** of the 883,796-row
   train set. Brute-force k-NN scores every test row against every train row;
   at full size that is ~10^11 distance computations per prediction pass. The
   subsample is stratified so class proportions are preserved, and the size is
   fixed in advance rather than tuned.
2. **RBF-SVM is approximated** via Nystroem kernel features + a linear SGD
   classifier. An exact RBF SVM is O(n^2) in kernel evaluations and is simply
   not runnable on 883k rows. A linear SVM is also included, exactly.

Neither deviation is hidden in a footnote — both are printed in the output table
and stored in `runs.jsonl` params.

PRE-REGISTERED PREDICTIONS (written before running — see git history)
---------------------------------------------------------------------
T1  **Every supervised method here lands in, or below, the existing top tier**
    (~0.58-0.63 macro), and the ones that land inside it will be statistically
    INDISTINGUISHABLE from the CNN. Rationale: the n=6 sweep already showed CNN,
    LTN control, RandomForest and MSP are mutually indistinguishable at a
    ~0.0256 threshold. Adding more closed-set supervised learners to a saturated
    task should not escape that band.

T2  **None of them reliably detects Bot**, and any that appears to should be
    treated as noise until cross-seed rank stability is checked. Rationale: the
    Bot failure is representational and shared across closed-set discriminative
    methods — the CNN's cross-seed Bot rank correlation is -0.090 and
    RandomForest's is 0.068, i.e. both noise, even though RF's *mean* Bot score
    (0.1311) looks respectable.

T3  **k-NN is the most likely Tier-A method to do well on Bot** — the one
    interesting prediction here. It is the only instance-based method in the
    tier: it makes decisions from local neighbourhoods in RAW feature space,
    which is the same substrate the KG clusters (and the KG is the best Bot
    channel at 0.3103). If Bot flows are locally coherent but globally
    non-separable, k-NN should see what a global decision boundary cannot.
    Falsified if k-NN's Bot lands in the same ~1-2x band as the rest.

Run:  scripts/run_long.sh baselines_classic.py
Out:  outputs/metadata/baselines_classic.json + runs.jsonl + per-model scores
"""
import os
import sys
import json
import time

import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.svm import LinearSVC
from sklearn.neural_network import MLPClassifier
from sklearn.kernel_approximation import Nystroem
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import train_test_split

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths, config, features, metrics, tracking      # noqa: E402

cfg = config.get()
_DEFAULT_SEED = cfg["seed"]
SEED = int(os.environ.get("BASELINE_SEED", _DEFAULT_SEED))
SUFFIX = "" if SEED == _DEFAULT_SEED else f"_s{SEED}"
PAPER = os.path.join(paths.PROCESSED, cfg["paths"]["paper_subdir"])
TFM = cfg["protocol"]["feature_transform"]
KNN_SUBSAMPLE = 50_000
NYSTROEM_COMPONENTS = 300
print(f"CONFIG: seed={SEED} suffix={SUFFIX or '(reference)'}", flush=True)


def load(split):
    X = np.load(os.path.join(PAPER, f"X_{split}.npy"))
    yb = np.load(os.path.join(PAPER, f"y_{split}_bin.npy"))
    ymc = np.load(os.path.join(PAPER, f"y_{split}_mc.npy"), allow_pickle=True)
    return X, yb, ymc


Xtr, ytr, _ = load("train")
Xte, yte, yte_mc = load("test")
zero_day = set(np.load(os.path.join(PAPER, "zero_day_classes.npy"), allow_pickle=True).tolist())

Xtr = features.transform(Xtr, TFM); Xte = features.transform(Xte, TFM)
sc = StandardScaler().fit(Xtr); Xtr, Xte = sc.transform(Xtr), sc.transform(Xte)
print(f"train {Xtr.shape}  test {Xte.shape}", flush=True)

# Stratified subsample for k-NN only. Fixed size, not tuned.
Xk, _, yk, _ = train_test_split(Xtr, ytr, train_size=KNN_SUBSAMPLE,
                                stratify=ytr, random_state=SEED)
print(f"k-NN subsample {Xk.shape} (stratified, fixed in advance)", flush=True)

results, RES = {}, {}


def run(name, model, Xfit, yfit, note=""):
    """Fit, score, evaluate, log. Uses predict_proba when available, else
    decision_function — PR-AUC is rank-based so either is valid."""
    tag = f"{name}{SUFFIX}"
    t0 = time.time()
    print(f"\n--- {tag} --- fitting on {Xfit.shape[0]:,} rows ...", flush=True)
    model.fit(Xfit, yfit)
    fit_s = time.time() - t0
    t1 = time.time()
    if hasattr(model, "predict_proba"):
        s = model.predict_proba(Xte)[:, 1]
    else:
        s = model.decision_function(Xte)
    pred_s = time.time() - t1

    r = metrics.evaluate(yte_mc, np.asarray(s, float), zero_day, fpr=0.01)
    results[tag] = r
    macro = r["macro"]["pr_auc"]
    fam = {k: v["pr_auc"] for k, v in r["zeroday_family"].items()}
    # 🔴 TIE DIAGNOSTICS ARE NOT OPTIONAL FOR THIS TIER. A depth-limited decision
    # tree emits leaf-purity probabilities, so most test rows share a handful of
    # values; PR-AUC is rank-based, so a tie-heavy score is not comparable to a
    # continuous one and a low number may mean "degenerate", not "bad". This is
    # the same failure mode as the float32 saturation bug (2026-07-27) and the
    # isotonic thresholding problem found in operational.py.
    dg = r["diagnostics"]
    print(f"    macro {macro:.4f} | Bot {fam.get('Bot', float('nan')):.4f} "
          f"| fit {fit_s:.0f}s predict {pred_s:.0f}s "
          f"| distinct {dg['score_resolution']:.4f} tie {dg['largest_tie_frac']:.3f}"
          f"{'  ⚠️ SATURATED' if dg['saturated'] else ''}", flush=True)

    params = {"protocol": "paper", "transform": TFM, "seed": SEED,
              "family": "A", "tier": "classic", "fit_seconds": round(fit_s, 1)}
    if note:
        params["deviation"] = note
    tracking.log_run(tag, params, metrics.flatten(r))
    # 🔴 SAVE float64, NOT float32 — the saved array must reproduce the logged
    # metric exactly. Casting to float32 on save (the first version of this
    # script) silently changed the numbers: GaussianNB's probabilities underflow
    # toward exactly 0/1, and the narrower mantissa collapsed distinct scores
    # into ties, moving its logged macro 0.1264 -> 0.0597 when a consumer
    # reloaded the file. Same float32-precision class as the 2026-07-27
    # saturation bug. baselines.py already saves float64; match it.
    np.save(os.path.join(paths.PREDICTIONS, f"y_prob_{tag}_test.npy"),
            np.asarray(s, np.float64))
    RES[tag] = {"macro": macro, "families": fam, "fit_seconds": fit_s,
                "predict_seconds": pred_s, "deviation": note or None,
                "score_resolution": dg["score_resolution"],
                "largest_tie_frac": dg["largest_tie_frac"],
                "saturated": bool(dg["saturated"]),
                # The field's metric, from the same run. Reported next to macro
                # so the protocol gap is visible per-model rather than only for
                # the CNN (comparability.py makes the same point for one model).
                "overall_binary_pr_auc": r["views"]["all"]["pr_auc"],
                "known_only_pr_auc": r["views"]["known_only"]["pr_auc"]}
    return r


# ---- the tier ---------------------------------------------------------------
run("decision_tree",
    DecisionTreeClassifier(max_depth=20, random_state=SEED), Xtr, ytr)

run("naive_bayes", GaussianNB(), Xtr, ytr)

run("logistic_regression",
    LogisticRegression(max_iter=200, n_jobs=-1, random_state=SEED), Xtr, ytr)

run("linear_svm",
    LinearSVC(dual=False, C=1.0, random_state=SEED), Xtr, ytr)

run("rbf_svm_nystroem",
    make_pipeline(Nystroem(n_components=NYSTROEM_COMPONENTS, random_state=SEED),
                  SGDClassifier(loss="hinge", random_state=SEED, n_jobs=-1)),
    Xtr, ytr,
    note=f"RBF approximated by Nystroem({NYSTROEM_COMPONENTS}) + linear SGD; "
         f"exact RBF-SVM is O(n^2) and not runnable at 883k rows")

run("mlp",
    MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=30, random_state=SEED,
                  early_stopping=True), Xtr, ytr)

run("knn_k5",
    KNeighborsClassifier(n_neighbors=5, n_jobs=-1), Xk, yk,
    note=f"fitted on a stratified {KNN_SUBSAMPLE:,}-row subsample of 883,796; "
         f"brute-force k-NN over the full train set is ~10^11 distance "
         f"computations per pass")

# ---- table + verdicts --------------------------------------------------------
print("\n" + "=" * 96)
print(f"TIER A — CLASSIC BASELINES (seed {SEED}). Headline is MACRO zero-day PR-AUC.")
print("=" * 96)
print(f"  {'model':22s} {'MACRO zd':>9s} {'Bot':>8s} {'lift':>7s} {'WebBF':>8s} "
      f"{'XSS':>8s} | {'FIELD binary':>12s} {'ties':>6s}")
BOT_CHANCE = 1956 / (1956 + 55237)
for tag, d in sorted(RES.items(), key=lambda kv: -kv[1]["macro"]):
    f = d["families"]
    bot = f.get("Bot", float("nan"))
    flag = " ⚠️" if d.get("saturated") else ""
    print(f"  {tag:22s} {d['macro']:>9.4f} {bot:>8.4f} {bot/BOT_CHANCE:>6.2f}x "
          f"{f.get('Web Attack Brute Force', float('nan')):>8.4f} "
          f"{f.get('Web Attack XSS', float('nan')):>8.4f} | "
          f"{d['overall_binary_pr_auc']:>12.4f} {d['largest_tie_frac']:>6.3f}{flag}")

print("\n  🔴 THE TWO COLUMNS TELL OPPOSITE STORIES, AND THAT IS THE POINT.")
print("     'FIELD binary' is benign-vs-all-attacks including the 8 families the model")
print("     TRAINED on — the metric published CIC-IDS2017 work reports as 99%+. 'MACRO zd'")
print("     is detection of the 6 families never seen. The same model can be excellent at")
print("     one and useless at the other, and only the second is the zero-day claim.")
print("     ⚠️ 'ties' = largest tied score block. A depth-limited tree emits leaf-purity")
print("     probabilities, so its PR-AUC is computed over a near-degenerate ranking — a low")
print("     value there may mean DEGENERATE rather than BAD, and is not comparable to a")
print("     continuous scorer's. Same failure mode as the 2026-07-27 float32 saturation bug.")

print("\n  Reference (existing channels, n=6 where available):")
print("    CNN 0.6250 | LTN control 0.6110 | RandomForest 0.5985 | MSP 0.5761")
print("    Distinguishable only if the gap exceeds ~0.0256 (2*SE*sqrt(2) at n=6, SD 0.0222)")

print("\n" + "=" * 96)
print("PRE-REGISTERED PREDICTIONS")
print("=" * 96)
CNN_N6 = 0.6250
THRESH = 0.0256
in_band = [t for t, d in RES.items() if abs(d["macro"] - CNN_N6) <= THRESH]
above = [t for t, d in RES.items() if d["macro"] - CNN_N6 > THRESH]
t1 = len(above) == 0
print(f"  T1 none escapes the top tier upward : {'CONFIRMED' if t1 else 'FALSIFIED'}")
print(f"     indistinguishable from the CNN: {in_band or 'none'}")
print(f"     ABOVE the band: {above or 'none'}")

knn_bot = RES.get(f"knn_k5{SUFFIX}", {}).get("families", {}).get("Bot", float("nan"))
others = [d["families"].get("Bot", 0) for t, d in RES.items() if "knn" not in t]
t3 = np.isfinite(knn_bot) and knn_bot > max(others) if others else False
print(f"  T3 k-NN is the best Tier-A on Bot   : {'CONFIRMED' if t3 else 'FALSIFIED'}")
print(f"     k-NN Bot {knn_bot:.4f} vs best other {max(others):.4f}" if others else "")
best_bot = max(RES.items(), key=lambda kv: kv[1]["families"].get("Bot", 0))
t2 = best_bot[1]["families"].get("Bot", 0) < 0.20
print(f"  T2 none reliably detects Bot        : {'CONFIRMED' if t2 else 'CHECK'}")
print(f"     best is {best_bot[0]} at {best_bot[1]['families'].get('Bot', 0):.4f} "
      f"(KG causal, for scale, is 0.3103)")
print("     ⚠️  A single-seed Bot score means little here — the CNN's cross-seed Bot rank")
print("        correlation is -0.090 and RandomForest's is 0.068, i.e. both NOISE. Re-run")
print("        with BASELINE_SEED=43/44 before citing any Bot number from this table.")

RES["_predictions"] = {"T1_none_above_band": bool(t1), "T2_no_bot": bool(t2),
                       "T3_knn_best_on_bot": bool(t3)}
RES["_meta"] = {"seed": SEED, "knn_subsample": KNN_SUBSAMPLE,
                "nystroem_components": NYSTROEM_COMPONENTS,
                "cnn_n6_reference": CNN_N6, "distinguishable_threshold": THRESH}
outp = os.path.join(paths.METADATA, f"baselines_classic{SUFFIX}.json")
with open(outp, "w", encoding="utf-8") as f:
    json.dump(RES, f, indent=1)
print(f"\nwrote {outp}")
print("DONE (baselines_classic)")

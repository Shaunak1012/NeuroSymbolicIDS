"""
evasion.py — does a simple evasion move the zero-day results? (itinerary 6.4, F-16)

WHY THIS EXISTS
---------------
The paper evaluates no adversary (audit F-16). This is a basic, bounded test: three
things an attacker controls on its own traffic, applied to the zero-day test flows
only, scored by models that are already trained. No retraining, so it measures
evasion of a deployed detector, not an arms race.

THREAT MODEL
------------
The attacker controls its FORWARD packets (Bot -> C2, web attacker -> server).
Benign and known-attack traffic is untouched. Each perturbation is applied in
feature space, and every feature CICFlowMeter derives from a changed quantity is
recomputed with it:

  pad    d bytes added to every DATA-carrying forward packet (act_data_pkt_fwd).
         CIC packet lengths are payload lengths, so packets without data are 0 and
         the forward sum and sum of squares update exactly: S' = S + dA,
         Q' = Q + 2dS + d^2 A. Mean, sample std, max, min follow; the flow-level
         length stats, average packet/segment size, subflow bytes and Flow Bytes/s
         are delta-updated. Strengths d = 32, 256 bytes.
  slow   the whole flow stretched in time by k: duration, all IATs and active/idle
         times x k, every per-second rate / k. Strengths k = 2, 10.
  jitter an independent delay U[0, J] on every forward packet (order kept). IAT means
         telescope (unchanged); forward IAT variance + J^2/6, flow IAT variance +
         (forward share) J^2/6, max + J/2, min - J/2 (floored at 0). Expected
         values, so deterministic. Strengths J = 10 ms, 100 ms.

"Delta-update" means new = old + f(new inputs) - f(old inputs), so a zero-strength
perturbation reproduces the stored features exactly whatever CICFlowMeter's exact
convention was. Limitations, stated: no MTU cap on padding, jitter by expectation,
backward traffic assumed unaffected by the forward change.

MODELS (each at seeds 42/43/44)
  CNN          the deterministic runs c4_log1p_s<seed> (p(attack))
  autoencoder  the deterministic runs ae_det_s<seed> (reconstruction MSE)
  RandomForest the validation-tuned forest (baselines_tuned.py), refit; refits were
               shown to reproduce the logged predictions exactly (2026-09-17)

PRE-REGISTERED PREDICTIONS (written 2026-09-18, committed before the first run)
  V1  No perturbation makes Bot reachable for the CNN: its Bot PR-AUC stays < 0.08.
  V2  For each supervised model (CNN, RF), at least one high-strength perturbation
      lowers macro zero-day PR-AUC by more than 0.0285 (the uncertainty on an
      absolute number), averaged over seeds.
  V3  The perturbation that moves flows furthest from benign in feature space
      (slow, k=10) RAISES the autoencoder's macro: evasion can backfire on an
      anomaly detector.
  Sanity: every strength-0 perturbation reproduces the stored scores exactly.

Run:  python scripts/evasion.py
Out:  outputs/metadata/evasion.json
"""
import os
import sys
import json
import pickle

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                        # noqa: E402
import config                                       # noqa: E402
import features                                     # noqa: E402
import metrics                                      # noqa: E402

cfg = config.get()
P = paths.PAPER
TFM = cfg["protocol"]["feature_transform"]
SEEDS = (42, 43, 44)
FAMS = ["Bot", "Web Attack Brute Force", "Web Attack XSS"]
STRENGTHS = {"pad": (0, 32, 256), "slow": (1, 2, 10), "jitter": (0, 10_000, 100_000)}
NOISE = 0.0285

with open(os.path.join(paths.PROCESSED, "features_train.csv"), encoding="utf-8") as _f:
    NAMES = _f.readline().strip().split(",")
C = {n: i for i, n in enumerate(NAMES)}


def _col(name):
    return C[name]


def _sample_var_update(old_col, n, s_old, q_old, s_new, q_new, std=True):
    """Delta-update a sample std / variance column from exact sums."""
    def f(s, q):
        with np.errstate(invalid="ignore", divide="ignore"):
            v = np.where(n > 1, (q - s * s / np.maximum(n, 1)) / np.maximum(n - 1, 1), 0.0)
        v = np.maximum(v, 0.0)
        return np.sqrt(v) if std else v
    return old_col + f(s_new, q_new) - f(s_old, q_old)


def pad(X, d):
    if d == 0:
        return X.copy()
    X = X.astype(np.float64).copy()
    nf, nb = X[:, _col("Total Fwd Packets")], X[:, _col("Total Backward Packets")]
    a = np.minimum(X[:, _col("act_data_pkt_fwd")], nf)
    mf, sdf = X[:, _col("Fwd Packet Length Mean")], X[:, _col("Fwd Packet Length Std")]
    mb, sdb = X[:, _col("Bwd Packet Length Mean")], X[:, _col("Bwd Packet Length Std")]
    s_f = mf * nf
    q_f = np.where(nf > 1, sdf ** 2 * (nf - 1), 0.0) + nf * mf ** 2
    s_b = mb * nb
    q_b = np.where(nb > 1, sdb ** 2 * (nb - 1), 0.0) + nb * mb ** 2
    s_f2 = s_f + d * a
    q_f2 = q_f + 2 * d * s_f + d * d * a
    n = nf + nb
    with np.errstate(invalid="ignore", divide="ignore"):
        mean_f2 = np.where(nf > 0, s_f2 / np.maximum(nf, 1), 0.0)
        mean_all_old = np.where(n > 0, (s_f + s_b) / np.maximum(n, 1), 0.0)
        mean_all_new = np.where(n > 0, (s_f2 + s_b) / np.maximum(n, 1), 0.0)
    dm_f = mean_f2 - mf
    X[:, _col("Total Length of Fwd Packets")] += d * a
    X[:, _col("Fwd Packet Length Max")] += np.where(a > 0, d, 0)
    fwd_min_new = X[:, _col("Fwd Packet Length Min")] + np.where((a == nf) & (nf > 0), d, 0)
    X[:, _col("Fwd Packet Length Min")] = fwd_min_new
    X[:, _col("Fwd Packet Length Mean")] += dm_f
    X[:, _col("Avg Fwd Segment Size")] += dm_f
    X[:, _col("Fwd Packet Length Std")] = _sample_var_update(sdf, nf, s_f, q_f, s_f2, q_f2)
    X[:, _col("Packet Length Mean")] += mean_all_new - mean_all_old
    X[:, _col("Average Packet Size")] += mean_all_new - mean_all_old
    X[:, _col("Packet Length Std")] = _sample_var_update(
        X[:, _col("Packet Length Std")], n, s_f + s_b, q_f + q_b, s_f2 + s_b, q_f2 + q_b)
    X[:, _col("Packet Length Variance")] = _sample_var_update(
        X[:, _col("Packet Length Variance")], n, s_f + s_b, q_f + q_b, s_f2 + s_b, q_f2 + q_b,
        std=False)
    X[:, _col("Max Packet Length")] = np.maximum(X[:, _col("Max Packet Length")],
                                                  X[:, _col("Fwd Packet Length Max")])
    sub = X[:, _col("Subflow Fwd Bytes")]
    with np.errstate(invalid="ignore", divide="ignore"):
        X[:, _col("Subflow Fwd Bytes")] = np.where(s_f > 0, sub * s_f2 / np.where(s_f > 0, s_f, 1),
                                                   sub + d * a)
    dur = X[:, _col("Flow Duration")]
    X[:, _col("Flow Bytes/s")] += np.where(dur > 0, d * a / np.where(dur > 0, dur, 1) * 1e6, 0.0)
    return X


TIME_COLS = ["Flow Duration", "Flow IAT Mean", "Flow IAT Std", "Flow IAT Max", "Flow IAT Min",
             "Fwd IAT Total", "Fwd IAT Mean", "Fwd IAT Std", "Fwd IAT Max", "Fwd IAT Min",
             "Bwd IAT Total", "Bwd IAT Mean", "Bwd IAT Std", "Bwd IAT Max", "Bwd IAT Min",
             "Active Mean", "Active Std", "Active Max", "Active Min",
             "Idle Mean", "Idle Std", "Idle Max", "Idle Min"]
RATE_COLS = ["Flow Bytes/s", "Flow Packets/s", "Fwd Packets/s", "Bwd Packets/s"]


def slow(X, k):
    X = X.astype(np.float64).copy()
    if k == 1:
        return X
    for c in TIME_COLS:
        X[:, _col(c)] *= k
    for c in RATE_COLS:
        X[:, _col(c)] /= k
    return X


def jitter(X, j):
    X = X.astype(np.float64).copy()
    if j == 0:
        return X
    nf, nb = X[:, _col("Total Fwd Packets")], X[:, _col("Total Backward Packets")]
    add = j * j / 6.0
    has_f = nf >= 2
    sd = X[:, _col("Fwd IAT Std")]
    X[:, _col("Fwd IAT Std")] = np.where(has_f, np.sqrt(sd ** 2 + add), sd)
    X[:, _col("Fwd IAT Max")] += np.where(has_f, j / 2.0, 0.0)
    X[:, _col("Fwd IAT Min")] = np.where(has_f, np.maximum(X[:, _col("Fwd IAT Min")] - j / 2.0, 0.0),
                                         X[:, _col("Fwd IAT Min")])
    share = np.where(nf + nb > 0, nf / np.maximum(nf + nb, 1), 0.0)
    has = (nf + nb) >= 2
    sd = X[:, _col("Flow IAT Std")]
    X[:, _col("Flow IAT Std")] = np.where(has, np.sqrt(sd ** 2 + share * add), sd)
    X[:, _col("Flow IAT Max")] += np.where(has, share * j / 2.0, 0.0)
    X[:, _col("Flow IAT Min")] = np.where(has, np.maximum(X[:, _col("Flow IAT Min")] - share * j / 2.0, 0.0),
                                          X[:, _col("Flow IAT Min")])
    return X


PERTURB = {"pad": pad, "slow": slow, "jitter": jitter}


def main():
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
    import tensorflow as tf
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler

    y = np.load(os.path.join(P, "y_test_mc.npy"), allow_pickle=True)
    zd = set(np.load(os.path.join(P, "zero_day_classes.npy"), allow_pickle=True).tolist())
    Xte = np.load(os.path.join(P, "X_test.npy")).astype(np.float64)
    zmask = np.isin(y, sorted(zd))
    Xz = Xte[zmask]
    print("zero-day test flows perturbed: %d of %d" % (zmask.sum(), len(y)))

    # ---- scorers: one function per model and seed, taking raw features ----
    scorers = {}
    for s in SEEDS:
        with open(os.path.join(paths.MODELS, "scaler_paper_c4_log1p_s%d.pkl" % s), "rb") as f:
            sc = pickle.load(f)
        with open(os.path.join(paths.MODELS, "label_encoder_paper_c4_log1p_s%d.pkl" % s), "rb") as f:
            ben = list(pickle.load(f).classes_).index("BENIGN")
        m = tf.keras.models.load_model(os.path.join(paths.MODELS, "c4_log1p_s%d.keras" % s), compile=False)

        def cnn(X, sc=sc, m=m, ben=ben):
            Z = sc.transform(features.transform(X, TFM)).reshape(-1, X.shape[1], 1).astype(np.float32)
            return 1.0 - m.predict(Z, batch_size=4096, verbose=0)[:, ben]
        scorers[("cnn", s)] = cnn

        with open(os.path.join(paths.MODELS, "scaler_ae_paper_ae_det_s%d.pkl" % s), "rb") as f:
            asc = pickle.load(f)
        am = tf.keras.models.load_model(os.path.join(paths.MODELS, "ae_det_s%d.keras" % s), compile=False)

        def ae(X, asc=asc, am=am):
            Z = asc.transform(features.transform(X, TFM))
            R = am.predict(Z, batch_size=4096, verbose=0)
            return np.mean((Z - R) ** 2, axis=1).astype(np.float32)
        scorers[("ae", s)] = ae

    Xtr = features.transform(np.load(os.path.join(P, "X_train.npy")), TFM)
    ytr = np.load(os.path.join(P, "y_train_bin.npy"))
    rsc = StandardScaler().fit(Xtr)
    Xtr = rsc.transform(Xtr)
    for s in SEEDS:
        rf = RandomForestClassifier(n_estimators=200, max_depth=20, max_features=0.3,
                                    n_jobs=-1, random_state=s).fit(Xtr, ytr)
        scorers[("rf", s)] = (lambda X, rf=rf: rf.predict_proba(rsc.transform(features.transform(X, TFM)))[:, 1])
        print("refit tuned forest s%d" % s, flush=True)
    del Xtr

    stored = {"cnn": "c4_log1p_s%d", "ae": "ae_det_s%d", "rf": "random_forest_tuned_s%d"}
    base = {}
    for (model, s), fn in scorers.items():
        full = fn(Xte)
        ref = np.load(os.path.join(paths.PREDICTIONS, "y_prob_%s_test.npy" % (stored[model] % s)))
        same = bool(np.allclose(full, ref, atol=1e-6))
        base[(model, s)] = full.astype(np.float64)
        print("baseline %-3s s%d reproduces stored scores: %s" % (model, s, same), flush=True)
        if not same:
            sys.exit("baseline scores do not reproduce the stored predictions")

    out = {"threat_model": "forward-traffic perturbations of zero-day test flows only; "
                           "models not retrained", "strengths": STRENGTHS, "results": {}}
    for name, fn in PERTURB.items():
        out["results"][name] = {}
        for st in STRENGTHS[name]:
            Xp = fn(Xz, st)
            if st == STRENGTHS[name][0]:
                assert np.allclose(Xp, Xz), "strength-0 %s changed the features" % name
            row = {}
            for (model, s), sfn in scorers.items():
                sc = base[(model, s)].copy()
                sc[zmask] = sfn(Xp)
                r = metrics.evaluate(y, sc, zd, fpr=0.01)
                row.setdefault(model, []).append({
                    "seed": s, "macro": r["macro"]["pr_auc"],
                    "family": {f: r["zeroday_family"][f]["pr_auc"] for f in FAMS},
                    "recall_1pct": {f: r["zeroday_family"][f]["recall"] for f in FAMS}})
            summ = {}
            for model, runs in row.items():
                summ[model] = {"macro_mean": float(np.mean([q["macro"] for q in runs])),
                               "family_mean": {f: float(np.mean([q["family"][f] for q in runs]))
                                               for f in FAMS},
                               "per_seed": runs}
            out["results"][name][str(st)] = summ
            print("%-6s %-7s  " % (name, st) + "  ".join(
                "%s %.4f (Bot %.4f)" % (m_, v["macro_mean"], v["family_mean"]["Bot"])
                for m_, v in summ.items()), flush=True)

    # ---- deltas and the pre-registered predictions ----
    res = out["results"]

    def mac(name, st, model):
        return res[name][str(st)][model]["macro_mean"]

    base_macro = {m_: mac("pad", 0, m_) for m_ in ("cnn", "ae", "rf")}
    out["delta_vs_unperturbed"] = {
        name: {str(st): {m_: mac(name, st, m_) - base_macro[m_] for m_ in base_macro}
               for st in STRENGTHS[name][1:]} for name in STRENGTHS}
    high = {name: str(STRENGTHS[name][-1]) for name in STRENGTHS}
    bot_max = max(res[n][str(st)]["cnn"]["family_mean"]["Bot"] for n in STRENGTHS for st in STRENGTHS[n])
    out["predictions"] = {
        "V1_cnn_bot_stays_below_0.08": bool(bot_max < 0.08),
        "V1_cnn_bot_max": bot_max,
        "V2_each_supervised_model_loses_more_than_noise": {
            m_: bool(min(out["delta_vs_unperturbed"][n][high[n]][m_] for n in STRENGTHS) < -NOISE)
            for m_ in ("cnn", "rf")},
        "V3_slow10_raises_autoencoder": bool(out["delta_vs_unperturbed"]["slow"]["10"]["ae"] > 0),
    }
    print("\nmacro change vs unperturbed (mean over seeds):")
    for n in STRENGTHS:
        for st in STRENGTHS[n][1:]:
            dd = out["delta_vs_unperturbed"][n][str(st)]
            print("  %-6s %-7s CNN %+.4f  AE %+.4f  RF %+.4f" % (n, st, dd["cnn"], dd["ae"], dd["rf"]))
    print("\n", json.dumps(out["predictions"], indent=1))
    p = os.path.join(paths.METADATA, "evasion.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print("wrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())

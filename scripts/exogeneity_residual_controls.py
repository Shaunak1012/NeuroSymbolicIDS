"""
exogeneity_residual_controls.py — is the host-window residual's Bot signal behaviour,
or identity / time-of-day / the flow features in disguise?

WHY THIS EXISTS
---------------
`exogeneity_residual.py` returned R2 for both views: the residual r = W - E[W|X]
reaches Bot where the raw view does not (window view: Bot lift 5.55 / 7.42 / 4.94x
vs 1.25-1.48x raw). Before that can be believed, three cheaper explanations have to be
excluded. The STATIC view already fails one of them on inspection: Web Brute Force,
XSS, DoS Hulk and PortScan share identical predicate values (pair count e^13, fan-out
2.08) because every external attack in CIC-IDS2017 arrives from one NAT address,
172.16.0.1, so its residual is an attacker-identity proxy -- the leakage
`exogenous_predicate.py` set out to exclude. Only the WINDOW view (causal, computed on
the full capture, symmetric across the split) is tested here.

  C1  X-ONLY. r is a function of X as well as W. If a novelty model on the prediction
      Ŵ = E[W|X] alone -- no W at all -- reaches Bot as well, the signal came from the
      flow features, not from host behaviour.
  C2  SAME HOST, SAME TIME. The five infected internal hosts also send 26,503 benign
      test flows. Compare Bot flows from those hosts with benign flows from THE SAME
      hosts inside the Bot attack's own time span. Identity and time of day are then
      held fixed; only behaviour differs. The CNN's score is the reference.
  C3  THE C2 SERVER. 36 % of Bot flows are sourced from the C2 address
      205.174.165.73. Reported separately, because a source that sends almost nothing
      but Bot traffic is identity by construction.
  Web Brute Force / XSS are NOT tested: all of them come from 172.16.0.1, which sends
  80 benign test flows. On this capture their window signal cannot be separated from
  identity, and that is reported as a limit, not a result.

PRE-REGISTERED PREDICTIONS (written before the first run)
---------------------------------------------------------
  K1  (behaviour) The residual channel's ROC-AUC on C2 (same host, same time) is
      >= 0.75 on 3/3 seeds AND exceeds the Ŵ-only channel's C2 AUC on 3/3 seeds.
      Then the window residual carries Bot evidence that is neither identity, time,
      nor the flow features, and the paper gains its first positive exogenous result.
  K0  (artefact) Either condition fails. Then the residual's Bot lift is explained by
      identity, time or X, and §6 changes only in its METHOD (the conditional test
      replaces the marginal one), not in its conclusion.
  Expectation, stated so it can be wrong: K0 is more likely -- the raw window view
  reaches Bot at only ~1.4x, and C2 removes the between-host contrast that a
  per-source window most easily encodes.

Run:  python scripts/exogeneity_residual_controls.py
Out:  outputs/metadata/exogeneity_residual_controls.json
"""
import os
import sys
import json

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                          # noqa: E402
import config                                         # noqa: E402
import features as featmod                            # noqa: E402
import metrics                                        # noqa: E402
import tracking                                       # noqa: E402
from exogeneity_residual import (SEEDS, N_FIT, VIEWS,  # noqa: E402
                                 load_view, residuals, novelty)

C2_ADDR = "205.174.165.73"
AUC_PASS = 0.75


def main():
    from sklearn.metrics import roc_auc_score
    cfg = config.get()
    zd = cfg["zero_day_classes"]
    tfm = cfg["protocol"]["feature_transform"]
    P = paths.PAPER
    X = {sp: featmod.transform(np.load(os.path.join(P, "X_%s.npy" % sp)), tfm)
         for sp in ("train", "val", "test")}
    y = {sp: np.asarray(np.load(os.path.join(P, "y_%s_mc.npy" % sp),
                                allow_pickle=True)).astype(str)
         for sp in ("val", "test")}
    ben_val = y["val"] == "BENIGN"
    yt = y["test"]
    src = pd.read_csv(os.path.join(P, "meta_test.csv"), low_memory=False,
                      usecols=["Source IP"])["Source IP"].astype(str).values
    # corrected timestamps (non-negotiable #8), persisted by timeline.py --backfill
    ts = pd.to_datetime(pd.Series(np.load(os.path.join(P, "timestamp_test.npy"),
                                          allow_pickle=True))).values

    bot = yt == "Bot"
    bot_hosts = sorted(set(src[bot]) - {C2_ADDR})
    t0, t1 = ts[bot].min(), ts[bot].max()
    in_span = (ts >= t0) & (ts <= t1)
    c2_neg = (yt == "BENIGN") & np.isin(src, bot_hosts) & in_span
    c2_pos = bot & np.isin(src, bot_hosts)
    c3_pos = bot & (src == C2_ADDR)
    print("Bot span %s -> %s ; infected hosts %s" % (t0, t1, bot_hosts))
    print("C2 same-host-same-time: %d Bot vs %d benign ; C3 C2-server Bot flows: %d "
          "(benign from C2 address: %d)"
          % (c2_pos.sum(), c2_neg.sum(), c3_pos.sum(),
             ((yt == "BENIGN") & (src == C2_ADDR)).sum()))
    if c2_neg.sum() < 100 or c2_pos.sum() < 100:
        sys.exit("control C2 underpowered -- stop")

    stem, cols, binary = VIEWS["host_window"]
    W = load_view(stem, len(cols))
    cnn = {s: np.load(os.path.join(paths.PREDICTIONS, "y_prob_c4_log1p_s%d_test.npy" % s))
           for s in SEEDS}

    def auc(score, pos, neg):
        m = pos | neg
        return float(roc_auc_score(pos[m].astype(int), score[m]))

    rows = []
    for s in SEEDS:
        itr = np.random.RandomState(s).choice(len(X["train"]), N_FIT, replace=False)
        R, _ = residuals(X, W, binary, itr, s)
        What = {sp: W[sp] - R[sp] for sp in ("val", "test")}      # = E[W|X]
        sc = {"residual": novelty(R["val"][ben_val], R["test"], s),
              "what_only": novelty(What["val"][ben_val], What["test"], s),
              "raw": novelty(W["val"][ben_val], W["test"], s),
              "cnn": cnn[s].astype(float)}
        row = {"seed": s}
        for k, v in sc.items():
            ev = metrics.evaluate(yt, v, zd)
            row[k] = {"macro_pr_auc": ev["macro"]["pr_auc"],
                      "bot_lift": ev["zeroday_family"]["Bot"]["lift"],
                      "c2_same_host_same_time_auc": auc(v, c2_pos, c2_neg),
                      "c3_c2_server_vs_all_benign_auc": auc(v, c3_pos, yt == "BENIGN")}
        rows.append(row)
        print("\n  seed %d" % s)
        for k in sc:
            r = row[k]
            print("    %-9s macro %.4f | Bot lift %5.2fx | C2 same-host AUC %.3f | "
                  "C3 C2-server AUC %.3f" % (k, r["macro_pr_auc"], r["bot_lift"],
                                             r["c2_same_host_same_time_auc"],
                                             r["c3_c2_server_vs_all_benign_auc"]))

    res_c2 = [r["residual"]["c2_same_host_same_time_auc"] for r in rows]
    wh_c2 = [r["what_only"]["c2_same_host_same_time_auc"] for r in rows]
    k1 = all(a >= AUC_PASS for a in res_c2) and all(a > b for a, b in zip(res_c2, wh_c2))
    verdict = "K1" if k1 else "K0"
    print("\nVERDICT %s: residual C2 AUC %s vs Ŵ-only %s"
          % (verdict, ", ".join("%.3f" % a for a in res_c2),
             ", ".join("%.3f" % a for a in wh_c2)))
    out = {"bot_span": [str(t0), str(t1)], "bot_hosts": bot_hosts, "c2_addr": C2_ADDR,
           "n": {"c2_pos": int(c2_pos.sum()), "c2_neg": int(c2_neg.sum()),
                 "c3_pos": int(c3_pos.sum())},
           "per_seed": rows, "verdict": verdict, "auc_pass": AUC_PASS}
    p = os.path.join(paths.METADATA, "exogeneity_residual_controls.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("wrote %s" % p)
    tracking.log_run("exo_residual_controls", {"seeds": SEEDS, "view": "host_window"},
                     {"c2_auc_residual_mean": float(np.mean(res_c2)),
                      "c2_auc_what_only_mean": float(np.mean(wh_c2)),
                      "verdict_K1": k1})


if __name__ == "__main__":
    main()

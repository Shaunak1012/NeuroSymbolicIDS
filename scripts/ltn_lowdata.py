"""
ltn_lowdata.py — do the (endogenous) axioms help when training data is SCARCE?

WHY THIS EXISTS
---------------
The paper's precondition says knowledge the network could compute from its own input
can at most act as an inductive bias. The obvious reviewer reply: an inductive bias is
exactly what helps when data is scarce, and at 883,796 training flows it has nothing to
do. The paper had no measurement in the scarce regime. This is that measurement.

DESIGN
------
Same trainer, same two configurations the paper compares (run_all.py LTN_CTRL vs
LTN_AX6: focal loss; no-axiom control omega 0 vs both axiom sets omega 1.0 ratio), same
log-odds scoring, seeds 42-44, deterministic -- on `paper_subsampled`: the 70,384-flow
training set (natural class mix, 12.6x smaller) whose test set is byte-identical to the
canonical one (`split_variants.py`, itinerary 5.4). The CNN on this split scores 0.2118,
with the web attacks falling to BENIGN in 90-100 % of flows -- so there is room for a
behaviour axiom ("burst / scan / beacon -> not benign") to help.

The training runs are made by `ltn_lowdata.sh`; this script only evaluates them.

PRE-REGISTERED PREDICTIONS (written before any low-data run)
------------------------------------------------------------
  L1  (the precondition holds in the scarce regime too) The paired delta
      axioms - control on macro zero-day PR-AUC is NOT positive on 3/3 seeds with a
      mean above 2 x 0.0171 (the post-flag seed SD).
  L2  (endogenous knowledge helps when data is scarce) Positive on 3/3 seeds AND mean
      above 0.0342. Then the paper must scope the precondition to the data-rich
      regime and say that endogenous knowledge can pay as an inductive bias.
  Expectation, stated so it can be wrong: L1, but with less confidence than anything
  else in this project -- the axioms target exactly the BENIGN absorption this split
  exhibits.

Run:  bash scripts/run_long.sh ltn_lowdata.sh      (trains, rescores, then runs this)
Out:  outputs/metadata/ltn_lowdata.json
"""
import os
import sys
import json

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                          # noqa: E402
import config                                         # noqa: E402
import metrics                                        # noqa: E402
import tracking                                       # noqa: E402

SEEDS = [42, 43, 44]
NOISE_SD = 0.0171
SUBDIR = "paper_subsampled"
CTRL = "ltn_ctrl_w0_sub_s%d"
AX = "ltn_ax6_ratio_w1p0_sub_s%d"


def main():
    cfg = config.get()
    zd = cfg["zero_day_classes"]
    y = np.asarray(np.load(os.path.join(paths.PROCESSED, SUBDIR, "y_test_mc.npy"),
                           allow_pickle=True)).astype(str)
    canon = np.asarray(np.load(os.path.join(paths.PAPER, "y_test_mc.npy"),
                               allow_pickle=True)).astype(str)
    if not np.array_equal(y, canon):
        sys.exit("%s test labels differ from the canonical test set -- stop" % SUBDIR)

    rows = []
    for s in SEEDS:
        r = {"seed": s}
        for arm, tag in (("control", CTRL % s), ("axioms", AX % s)):
            p = os.path.join(paths.PREDICTIONS, "y_prob_%s_logodds_test.npy" % tag)
            if not os.path.exists(p):
                sys.exit("missing %s -- run ltn_lowdata.sh" % p)
            ev = metrics.evaluate(y, np.load(p), zd)
            r[arm] = {"macro_pr_auc": ev["macro"]["pr_auc"],
                      "family": {f: d["pr_auc"] for f, d in ev["zeroday_family"].items()
                                 if not d["underpowered"]}}
        r["delta"] = r["axioms"]["macro_pr_auc"] - r["control"]["macro_pr_auc"]
        rows.append(r)
        print("seed %d: control %.4f | axioms %.4f | delta %+.4f   (Bot %.4f -> %.4f)"
              % (s, r["control"]["macro_pr_auc"], r["axioms"]["macro_pr_auc"], r["delta"],
                 r["control"]["family"]["Bot"], r["axioms"]["family"]["Bot"]))
    d = np.array([r["delta"] for r in rows])
    l2 = bool((d > 0).all() and d.mean() > 2 * NOISE_SD)
    verdict = "L2" if l2 else "L1"
    print("\nmean delta %+.4f (%d of 3 seeds positive) = %.2f x noise SD -> VERDICT %s"
          % (d.mean(), (d > 0).sum(), d.mean() / NOISE_SD, verdict))
    out = {"subdir": SUBDIR, "seeds": SEEDS, "noise_sd": NOISE_SD, "per_seed": rows,
           "delta_mean": float(d.mean()), "seeds_positive": int((d > 0).sum()),
           "verdict": verdict}
    p = os.path.join(paths.METADATA, "ltn_lowdata.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("wrote %s" % p)
    tracking.log_run("ltn_lowdata", {"subdir": SUBDIR, "seeds": SEEDS},
                     {"delta_mean": float(d.mean()), "verdict_L2": l2})


if __name__ == "__main__":
    main()

"""
ablation_population.py — do the ablation's conclusions hold beyond the three
reference CNN runs?

WHY THIS EXISTS (audit F-01, 2026-09-17)
----------------------------------------
`fusion_population.py` withdrew the CNN + KG gain: it held for the three reference
CNN runs (cnn_paper, _s43, _s44) and not across the 11 pre-flag or 6 deterministic
runs of the same configuration, because whole-set rank fusion inherits each CNN
run's placement of zero-day flows among the known attacks.

`ablation.py` is built on the same three runs, and the paper's ABSTRACT quotes one
of its rungs: the symbolic channel "lowered performance" when added on top of the
KG (CNN+KG 0.6926 -> CNN+LTN-Ax6+KG 0.6708, p < 0.0001). This script re-tests the
ablation's rungs across every CNN run on disk, holding the LTN and KG channels at
their three seeds exactly as `ablation.py` does. Nothing is trained.

Rungs re-tested, each as a paired difference against the run it adds to:
  +LTN-ctrl   (CNN + LTN-ctrl)      - CNN
  +LTN-Ax6    (CNN + LTN-Ax6)       - CNN
  Ax6 on KG   (CNN + LTN-Ax6 + KG)  - (CNN + KG)      <- the abstract's claim
  ctrl on KG  (CNN + LTN-ctrl + KG) - (CNN + KG)

Raw-probability CNN arrays are used for every run, because only the reference
runs have log-odds twins; the two rank almost identically (Spearman 0.999996).
The reference rows are printed beside `ablation.json` so the substitution is
visible.

RESULT (2026-09-17). The abstract's rung does not hold: "Ax6 on KG" is -0.0245 on
the reference three, +0.0294 across 11 pre-flag runs (5/11 positive) and +0.0886
on all 6 deterministic runs -- and the axiom-free control added the same way does
more (+0.1211, 6/6). When CNN+KG is broken, any third channel repairs it. The
axiom-specific rows (axioms on vs off, same position) are the ones that answer
the symbolic question; see the summary they print.

Run:  python scripts/ablation_population.py
Out:  outputs/metadata/ablation_population.json
"""
import os
import sys
import json

import numpy as np
from scipy.stats import rankdata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                        # noqa: E402
import metrics                                      # noqa: E402

from fusion_population import PRE_FLAG, DETERMINISTIC, DUPLICATES_OF   # noqa: E402

SEEDS = [42, 43, 44]
CHANNELS = {
    "LTN-ctrl": ["ltn_ctrl_w0_logodds", "ltn_ctrl_w0_s43_logodds", "ltn_ctrl_w0_s44_logodds"],
    "LTN-Ax6": ["ltn_ax6_ratio_w1p0_s42_logodds", "ltn_ax6_ratio_w1p0_s43_logodds",
                "ltn_ax6_ratio_w1p0_s44_logodds"],
    "KG": ["kg_causal", "kg_s43_causal", "kg_s44_causal"],
    # deterministic matched pair from audit_rebase.sh (CE, base axioms, omega 1 vs 0)
    "Base-det": ["ltn_repro_det_s42", "ltn_repro_det_s43", "ltn_repro_det_s44"],
    "Base-ctrl": ["ltn_repro_ctrl_s42", "ltn_repro_ctrl_s43", "ltn_repro_ctrl_s44"],
}
RUNGS = {
    "+LTN-ctrl": (["CNN", "LTN-ctrl"], ["CNN"]),
    "+LTN-Ax6": (["CNN", "LTN-Ax6"], ["CNN"]),
    "Ax6 on KG": (["CNN", "LTN-Ax6", "KG"], ["CNN", "KG"]),
    "ctrl on KG": (["CNN", "LTN-ctrl", "KG"], ["CNN", "KG"]),
    # THE AXIOM EFFECT: same fusion position, same trainer, axioms on vs off.
    # This is what "does the symbolic pillar help?" asks; the rungs above also
    # measure what ANY third channel does to a two-channel fusion.
    "axioms, alone (Ax6 vs ctrl)": (["CNN", "LTN-Ax6"], ["CNN", "LTN-ctrl"]),
    "axioms, on KG (Ax6 vs ctrl)": (["CNN", "LTN-Ax6", "KG"], ["CNN", "LTN-ctrl", "KG"]),
    "axioms, alone (base det, matched)": (["CNN", "Base-det"], ["CNN", "Base-ctrl"]),
    "axioms, on KG (base det, matched)": (["CNN", "Base-det", "KG"], ["CNN", "Base-ctrl", "KG"]),
}


def load(tag):
    return np.load(os.path.join(paths.PREDICTIONS, "y_prob_%s_test.npy" % tag))


def rk(x):
    return rankdata(x) / len(x)


def main():
    y = np.load(os.path.join(paths.PAPER, "y_test_mc.npy"), allow_pickle=True)
    zd = set(np.load(os.path.join(paths.PAPER, "zero_day_classes.npy"),
                     allow_pickle=True).tolist())
    ch = {k: [rk(load(t)) for t in v] for k, v in CHANNELS.items()}

    def macro(sc):
        return metrics.evaluate(y, sc, zd, fpr=0.01)["macro"]["pr_auc"]

    runs = PRE_FLAG + [t for t in DETERMINISTIC if t not in DUPLICATES_OF]
    out = {"channels": CHANNELS, "rungs": {k: {"with": v[0], "without": v[1]}
                                           for k, v in RUNGS.items()},
           "per_run": {}, "summary": {}}
    cache = {}
    for tag in runs:
        rc = rk(load(tag))
        row = {}
        for i, s in enumerate(SEEDS):
            def fused(parts):
                key = (tag, i, tuple(parts))
                if key not in cache:
                    cache[key] = macro(np.mean([rc if p == "CNN" else ch[p][i] for p in parts],
                                               axis=0))
                return cache[key]
            for rung, (a, b) in RUNGS.items():
                row.setdefault(rung, []).append(fused(a) - fused(b))
        out["per_run"][tag] = {r: {"per_seed": v, "mean": float(np.mean(v))}
                               for r, v in row.items()}
        print("%-16s " % tag + "  ".join("%s %+.4f" % (r, np.mean(v)) for r, v in row.items()),
              flush=True)

    ref = ["cnn_paper", "cnn_paper_s43", "cnn_paper_s44"]
    for rung in RUNGS:
        s = {}
        for pop, tags in (("reference_three", ref),
                          ("pre_flag", PRE_FLAG),
                          ("deterministic", [t for t in DETERMINISTIC if t not in DUPLICATES_OF])):
            v = np.array([out["per_run"][t][rung]["mean"] for t in tags])
            s[pop] = {"n_runs": len(tags), "mean": float(v.mean()),
                      "runs_positive": int((v > 0).sum()), "runs_negative": int((v < 0).sum()),
                      "min": float(v.min()), "max": float(v.max())}
        out["summary"][rung] = s

    abl = None
    p = os.path.join(paths.METADATA, "ablation.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            abl = json.load(f)
    if abl:
        full, kg = abl["CNN + LTN-Ax6 + KG (FULL)"], abl["CNN + KG"]
        out["reference_check"] = {
            "ablation_json_ax6_on_kg": float(np.mean(np.array(full["per_seed_macro"])
                                                     - np.array(kg["per_seed_macro"]))),
            "this_script_ax6_on_kg_reference_three":
                out["summary"]["Ax6 on KG"]["reference_three"]["mean"],
            "note": "ablation.json uses log-odds CNN arrays; this script uses raw ones"}

    print("\n%-12s %-16s %9s %10s %10s" % ("rung", "population", "mean", "runs +", "runs -"))
    for rung, s in out["summary"].items():
        for pop, v in s.items():
            print("%-12s %-16s %+9.4f %6d/%-3d %6d/%-3d"
                  % (rung, pop, v["mean"], v["runs_positive"], v["n_runs"],
                     v["runs_negative"], v["n_runs"]))
    if abl:
        rc_ = out["reference_check"]
        print("\nreference check, Ax6 on KG: ablation.json %+.4f | this script %+.4f"
              % (rc_["ablation_json_ax6_on_kg"], rc_["this_script_ax6_on_kg_reference_three"]))

    p = os.path.join(paths.METADATA, "ablation_population.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print("wrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())

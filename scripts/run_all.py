"""
run_all.py — the pipeline, declared once, in order, with the artifacts each
stage produces.

WHY THIS EXISTS
---------------
`conference_roadmap.md` Phase 7 lists a reproducibility package with a `run_all`
and it has never existed. The pipeline lives in three places instead —
`README.md`'s Quick Start, `CLAUDE.md`'s "How to run the pipeline", and
`docs/scripts_reference.md` — which is the same duplication that produced five
component-status drift defects in the status docs. **A pipeline documented in
three prose lists is a pipeline that will disagree with itself.**

This file is the fourth copy only until the other three point at it. What it adds
over prose is that it is **executable and checkable**: the stage list and the
artifacts each stage writes are data, so `--check` can tell you what is actually
on disk rather than what a README believes.

DEFAULT MODE IS `--check`, AND THAT IS DELIBERATE
--------------------------------------------------
A full reproduction retrains every model on CPU and takes hours. Making that the
default behaviour of a script called `run_all` is a foot-gun, so the default
**verifies and reports** and `--run` is opt-in.

⚠️ **HONEST LIMIT, and it must not be smoothed over in the paper.** The stage
list has been **checked** end to end; it has **never been executed** end to end
in one pass. Every stage has run individually, many of them dozens of times, but
"each stage works" and "the sequence works from a clean checkout" are different
claims and only the first is evidenced. `--run` is offered as a convenience, not
as a validated reproduction path.

Also note: **pre-flag runs are not reproducible at fixed seed** (SD 0.0222).
Determinism flags are on now and verified byte-identical, so a fresh run should
reproduce the post-flag numbers; it will **not** reproduce figures computed
before the flags landed, and those two populations are never pooled.

Run:
  python scripts/run_all.py                  # check artifacts, print the order
  python scripts/run_all.py --run            # execute every stage in order
  python scripts/run_all.py --run --from kg  # resume from a named stage
"""
import os
import sys
import argparse
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                        # noqa: E402

P, MD, PR = paths.PAPER, paths.METADATA, paths.MODELS
EMB, PRED = paths.EMBEDDINGS, paths.PREDICTIONS

# (name, script, what it is for, [artifacts that prove it ran])
#
# Artifacts are the SEED-42 canonical ones only. Multi-seed variants are produced
# by the same scripts under CNN_SEED / AE_SEED / etc. and are deliberately not
# listed -- this is the reproduction path, not the full experimental record.
STAGES = [
    ("preprocess", "preprocess.py",
     "clean raw CIC-IDS2017 CSVs -> 68 features + meta side-table",
     [os.path.join(paths.PROCESSED, "labels_test_multiclass.npy")]),

    ("split", "preprocess_paper.py",
     "paper-aligned split: 9 known stratified 80/10/10, 6 zero-day test-only",
     [os.path.join(P, "X_train.npy"), os.path.join(P, "X_test.npy"),
      os.path.join(P, "y_test_mc.npy"), os.path.join(P, "zero_day_classes.npy")]),

    ("timeline", "timeline.py --backfill",
     "corrected timestamps (D/M/YYYY + 12h no AM/PM) -> timestamp_*.npy",
     [os.path.join(P, "timestamp_test.npy")]),

    ("behaviour", "behavior.py",
     "fuzzy behaviour thresholds from train (the symbolic pillar's input)",
     [os.path.join(MD, "behaviour_thresholds.npy")]),

    ("cnn", "cnn_paper.py",
     "neural pillar -> model, embeddings, p(attack) channel",
     [os.path.join(PR, "cnn_paper.keras"),
      os.path.join(PR, "label_encoder_paper.pkl"),
      os.path.join(PRED, "y_prob_cnn_paper_test.npy")]),

    ("baselines", "baselines.py",
     "XGBoost / RandomForest / IsolationForest",
     [os.path.join(PRED, "y_prob_isolation_forest_test.npy")]),

    ("novelty", "novelty.py",
     "MSP + Mahalanobis, post-hoc on the trained CNN (no retraining)",
     [os.path.join(PRED, "y_prob_msp_test.npy"),
      os.path.join(PRED, "y_prob_mahalanobis_test.npy")]),

    ("ltn", "ltn_paper.py",
     "symbolic pillar (configured by LTN_* env vars)",
     [os.path.join(PRED, "y_prob_ltn_ctrl_w0_logodds_test.npy")]),

    ("autoencoder", "autoencoder_paper.py",
     "anomaly pillar -- benign-only autoencoder",
     [os.path.join(PR, "autoencoder_paper.keras"),
      os.path.join(EMB, "X_test_ae_bottleneck.npy")]),

    ("kg", "kg.py",
     "Phase 4 knowledge graph: clusters, decaying edges, burstiness",
     [os.path.join(MD, "kg_report.json")]),

    ("explain", "explain.py",
     "IG + per-axiom SAT + KG paths + faithfulness",
     [os.path.join(MD, "explanations.json")]),

    ("fusion", "fusion_multi.py",
     "parameter-free equal-weight rank fusion over channels",
     [os.path.join(MD, "fusion_multi.json")]),

    ("fitted_fusion", "fitted_fusion.py",
     "the FITTED combiner, fitted on zero-day-free validation",
     [os.path.join(MD, "fitted_fusion.json")]),

    ("significance", "significance.py",
     "paired bootstrap over per-flow scores (no training)",
     [os.path.join(MD, "significance.json")]),

    ("ablation", "ablation.py",
     "CNN -> +LTN -> +KG -> FULL, paired over shared seeds",
     [os.path.join(MD, "ablation.json")]),

    ("operational", "operational.py",
     "Phase 7.5 Tier 1: ensemble, calibration/ECE, alert budget, abstention",
     [os.path.join(MD, "operational.json")]),

    ("latency", "latency.py",
     "per-component, per-batch throughput; determinism arms",
     [os.path.join(MD, "latency_determinism_on.json")]),

    ("field_gap", "field_gap.py",
     "the resolution-failure figure: 40 methods on both metrics",
     [os.path.join(MD, "field_gap.json")]),

    ("figures", "paper_figures.py",
     "figures 2-5, recomputed from outputs/metadata only",
     [os.path.join(paths.FIGURES, "field_gap.png")]),
]

PY = os.path.join(paths.ROOT, ".venv", "Scripts", "python.exe")
if not os.path.exists(PY):
    PY = os.path.join(paths.ROOT, ".venv", "bin", "python")


# NOTE: every PRINTED string below is ASCII. The Windows console default is
# cp1252 and non-ASCII output raises UnicodeEncodeError -- this script is meant
# to be run directly, not only through run_long.sh (which forces UTF-8), so it
# must survive a bare `python scripts/run_all.py`. The first version of this
# file crashed on its own warning banner, which is the same bug CLAUDE.md
# records being fixed three times as separate incidents.
def check():
    print("=" * 96)
    print("PIPELINE CHECK - stage order and the artifacts each stage should have written")
    print("=" * 96)
    missing_total = 0
    for i, (name, script, why, arts) in enumerate(STAGES, 1):
        have = [a for a in arts if os.path.exists(a)]
        miss = [a for a in arts if not os.path.exists(a)]
        missing_total += len(miss)
        if not arts:
            mark = "  --  "          # no declared artifact; cannot be checked
        elif not miss:
            mark = "  OK  "
        elif len(have):
            mark = "PARTIAL"
        else:
            mark = "MISSING"
        print(f"{i:2d}. [{mark}] {name:14s} {script:26s} {why}")
        for a in miss:
            print(f"              missing: {os.path.relpath(a, paths.ROOT)}")
    print("-" * 96)
    n_unchecked = sum(1 for s in STAGES if not s[3])
    print(f"{len(STAGES)} stages | {missing_total} declared artifacts missing | "
          f"{n_unchecked} stages declare no artifact and are NOT checked")
    if n_unchecked:
        print("WARNING: a stage with no declared artifact cannot fail this check. That is a gap in")
        print("    the check, not evidence the stage ran - the same shape as the script-count")
        print("    regex that passed on a wrong count in 2026-08-05.")
    print("=" * 96)
    return 1 if missing_total else 0


def run(start=None):
    started = start is None
    for name, script, why, _ in STAGES:
        if not started:
            if name == start:
                started = True
            else:
                print(f"-- skipping {name}")
                continue
        parts = script.split()
        cmd = [PY, "-u", os.path.join(paths.ROOT, "scripts", parts[0])] + parts[1:]
        print("\n" + "=" * 96)
        print(f"RUN  {name}  ->  {script}")
        print("=" * 96, flush=True)
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        rc = subprocess.call(cmd, cwd=paths.ROOT, env=env)
        if rc != 0:
            print(f"\nFAILED: stage '{name}' exited {rc} - stopping. "
                  f"Resume with: python scripts/run_all.py --run --from {name}")
            return rc
    print("\nall stages completed")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", action="store_true",
                    help="actually execute the stages (default is check only)")
    ap.add_argument("--from", dest="start", default=None,
                    help="resume execution from this stage name")
    a = ap.parse_args()
    sys.exit(run(a.start) if a.run else check())

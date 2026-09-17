"""
run_all.py — the pipeline, declared once, in order, with what each stage needs
and what it produces.

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

WHAT THE FIRST EXECUTION SHOWED (2026-09-17, audit item 7.4)
-------------------------------------------------------------
Until 2026-09-17 the stage list had been checked and never executed. The first
`--run --keep-going` (into a sandbox, see NSIDS_WORKDIR below) reproduced
preprocess, split, timeline and the seed-42 CNN **byte for byte** from the raw
CSVs, and showed that the list as declared could not reproduce the rest:

  * it declared seed-42 artifacts only, but fusion, significance, ablation and the
    fitted fuser read seeds 43 and 44 of the CNN, the novelty scores, the LTN
    control, the autoencoder and the KG;
  * the `ltn` stage ran `ltn_paper.py` with its default settings, which write a
    different tag than the LTN control every downstream script reads, and the
    +Ax6 arm the ablation reads was not declared at all;
  * nothing produced the log-odds scores (`rescore_logits.py`) or the CNN + KG
    fusion channel (`fusion_kg.py`) that later stages read;
  * `operational`, `field_gap` and `figures` read records from experiments that
    are not pipeline stages (the 11-run noise-floor CNN population, the method
    sweeps behind field_gap, noise_postdet, protocol_variance).

So each stage now declares `runs` (one environment per execution: seeds, LTN
settings), `needs` (inputs another stage must make) and `external` (inputs only
an experiment outside this list makes). `--check` verifies statically that every
`needs` entry is made by an EARLIER stage, and lists the external inputs, so the
reproduction claim cannot quietly outrun what this file can actually rebuild.

Pre-flag runs are not reproducible at fixed seed (SD 0.0222). A fresh run
reproduces the deterministic population; figures computed from pre-flag runs
come out as deterministic re-runs, which are a different population and are
never pooled with them.

To reproduce WITHOUT touching the canonical artifacts, point NSIDS_WORKDIR at an
empty directory: raw inputs are still read from the repository, everything
generated goes under the work directory (paths.py).

Run:
  python scripts/run_all.py                  # check artifacts and declarations
  python scripts/run_all.py --run            # execute every stage in order
  python scripts/run_all.py --run --from kg  # resume from a named stage
  python scripts/run_all.py --run --keep-going
"""
import os
import sys
import argparse
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                        # noqa: E402

P, MD, MODELS = paths.PAPER, paths.METADATA, paths.MODELS
EMB, PRED = paths.EMBEDDINGS, paths.PREDICTIONS
SEEDS = (42, 43, 44)


def sfx(s):
    """The project's tag convention: seed 42 is unsuffixed, others get _s<seed>."""
    return "" if s == 42 else "_s%d" % s


def pred(tag):
    return os.path.join(PRED, "y_prob_%s_test.npy" % tag)


def model(tag):
    return os.path.join(MODELS, "%s.keras" % tag)


LTN_CTRL = {"LTN_LOSS": "focal", "LTN_AXIOMS": "base", "LTN_OMEGA": "0.0",
            "LTN_OMEGA_MODE": "fixed"}
LTN_AX6 = {"LTN_LOSS": "focal", "LTN_AXIOMS": "both", "LTN_OMEGA": "1.0",
           "LTN_OMEGA_MODE": "ratio"}
RESCORE = ([f"cnn_paper{sfx(s)}" for s in SEEDS] + [f"ltn_ctrl_w0{sfx(s)}" for s in SEEDS]
           + [f"ltn_ax6_ratio_w1p0_s{s}" for s in SEEDS])


def stage(name, script, why, makes, runs=None, needs=(), external=()):
    return {"name": name, "script": script, "why": why, "makes": list(makes),
            "runs": runs or [{}], "needs": list(needs), "external": list(external)}


STAGES = [
    stage("preprocess", "preprocess.py",
          "clean raw CIC-IDS2017 CSVs -> 68 features + meta side-table",
          [os.path.join(paths.PROCESSED, "labels_test_multiclass.npy"),
           os.path.join(paths.PROCESSED, "features_train.csv")]),

    stage("split", "preprocess_paper.py",
          "paper-aligned split: 9 known stratified 80/10/10, 6 zero-day test-only",
          [os.path.join(P, f) for f in ("X_train.npy", "X_val.npy", "X_test.npy",
                                        "y_train_bin.npy", "y_test_mc.npy",
                                        "zero_day_classes.npy", "meta_test.csv")],
          needs=[os.path.join(paths.PROCESSED, "labels_test_multiclass.npy")]),

    stage("timeline", "timeline.py --backfill",
          "corrected timestamps (D/M/YYYY + 12h no AM/PM) -> timestamp_*.npy",
          [os.path.join(P, "timestamp_test.npy")],
          needs=[os.path.join(P, "meta_test.csv")]),

    stage("behaviour", "behavior.py",
          "fuzzy behaviour thresholds from train (the symbolic pillar's input)",
          [os.path.join(MD, "behaviour_thresholds.npy")],
          needs=[os.path.join(paths.PROCESSED, "features_train.csv")]),

    stage("cnn", "cnn_paper.py",
          "neural pillar, seeds 42/43/44 -> models, embeddings, p(attack)",
          [p for s in SEEDS for p in (
              model(f"cnn_paper{sfx(s)}"), model(f"cnn_paper{sfx(s)}_best"),
              os.path.join(MODELS, f"scaler_paper{sfx(s)}.pkl"),
              os.path.join(MODELS, f"label_encoder_paper{sfx(s)}.pkl"),
              os.path.join(EMB, f"X_train_cnn_paper{sfx(s)}_emb.npy"),
              os.path.join(EMB, f"X_test_cnn_paper{sfx(s)}_emb.npy"),
              pred(f"cnn_paper{sfx(s)}"))],
          runs=[{"CNN_SEED": str(s)} for s in SEEDS],
          needs=[os.path.join(P, "X_train.npy")]),

    stage("baselines", "baselines.py",
          "XGBoost / RandomForest / IsolationForest, seeds 42/43/44",
          [pred(f"{m}{sfx(s)}") for s in SEEDS
           for m in ("xgboost", "random_forest", "isolation_forest")],
          runs=[{"BASELINE_SEED": str(s)} for s in SEEDS],
          needs=[os.path.join(P, "X_train.npy")]),

    stage("novelty", "novelty.py",
          "MSP + Mahalanobis, post-hoc on each CNN seed (no retraining)",
          [pred(f"{m}{sfx(s)}") for s in SEEDS for m in ("msp", "mahalanobis")],
          runs=[{"NOVELTY_SEED": str(s)} for s in SEEDS],
          needs=[p for s in SEEDS for p in (
              model(f"cnn_paper{sfx(s)}_best"),
              os.path.join(MODELS, f"scaler_paper{sfx(s)}.pkl"),
              os.path.join(EMB, f"X_test_cnn_paper{sfx(s)}_emb.npy"))]),

    stage("ltn_ctrl", "ltn_paper.py",
          "symbolic pillar, no-axiom control (focal, base axioms, omega 0), 3 seeds",
          [model(f"ltn_ctrl_w0{sfx(s)}") for s in SEEDS],
          runs=[dict(LTN_CTRL, LTN_SEED=str(s), LTN_TAG=f"ltn_ctrl_w0{sfx(s)}") for s in SEEDS],
          needs=[os.path.join(MD, "behaviour_thresholds.npy")]),

    stage("ltn_ax6", "ltn_paper.py",
          "symbolic pillar with Ax6 (focal, both, omega 1.0 ratio), 3 seeds",
          [model(f"ltn_ax6_ratio_w1p0_s{s}") for s in SEEDS],
          runs=[dict(LTN_AX6, LTN_SEED=str(s), LTN_TAG=f"ltn_ax6_ratio_w1p0_s{s}") for s in SEEDS],
          needs=[os.path.join(MD, "behaviour_thresholds.npy")]),

    stage("rescore", "rescore_logits.py",
          "log-odds scores from the saved CNN and LTN models",
          [pred(f"{t}_logodds") for t in RESCORE],
          runs=[{"RESCORE_TAGS": ",".join(RESCORE)}],
          needs=[model(t) for t in RESCORE]),

    stage("autoencoder", "autoencoder_paper.py",
          "anomaly pillar -- benign-only autoencoder, seeds 42/43/44",
          [p for s in SEEDS for p in (model(f"autoencoder_paper{sfx(s)}"),
                                      pred(f"autoencoder_paper{sfx(s)}"))],
          runs=[{"AE_SEED": str(s)} for s in SEEDS],
          needs=[os.path.join(P, "X_train.npy")]),

    stage("kg", "kg.py",
          "Phase 4 knowledge graph (clusters, decaying edges, burstiness), 3 seeds",
          [p for s in SEEDS for p in (os.path.join(MD, f"kg{sfx(s)}_report.json"),
                                      os.path.join(MODELS, f"kg{sfx(s)}.gpickle"),
                                      pred(f"kg{sfx(s)}"), pred(f"kg{sfx(s)}_causal"))],
          runs=[{"KG_SEED": str(s)} for s in SEEDS],
          needs=[os.path.join(P, "timestamp_test.npy")]),

    stage("fusion_kg", "fusion_kg.py",
          "parameter-free CNN + KG rank fusion, per seed",
          [pred(f"fusion_cnn_kg{sfx(s)}") for s in SEEDS],
          needs=[pred(f"cnn_paper{sfx(s)}_logodds") for s in SEEDS]
          + [pred(f"kg{sfx(s)}_causal") for s in SEEDS]),

    stage("explain", "explain.py",
          "IG + per-axiom SAT + KG paths + faithfulness",
          [os.path.join(MD, "explanations.json")],
          needs=[model("cnn_paper"), os.path.join(MODELS, "label_encoder_paper.pkl"),
                 os.path.join(MODELS, "kg.gpickle")]),

    stage("fusion", "fusion_multi.py",
          "parameter-free equal-weight rank fusion over channels",
          [os.path.join(MD, "fusion_multi.json")],
          needs=[pred(t) for s in SEEDS for t in (
              f"cnn_paper{sfx(s)}_logodds", f"ltn_ctrl_w0{sfx(s)}_logodds",
              f"autoencoder_paper{sfx(s)}", f"isolation_forest{sfx(s)}",
              f"random_forest{sfx(s)}", f"msp{sfx(s)}", f"mahalanobis{sfx(s)}",
              f"kg{sfx(s)}_causal")] + [pred("xgboost")]),

    stage("fitted_fusion", "fitted_fusion.py",
          "the FITTED combiner, fitted on zero-day-free validation",
          [os.path.join(MD, "fitted_fusion.json")],
          needs=[model(f"{b}{sfx(s)}") for s in SEEDS for b in ("cnn_paper", "autoencoder_paper")]),

    stage("significance", "significance.py",
          "paired bootstrap over per-flow scores (no training)",
          [os.path.join(MD, "significance.json")],
          needs=[pred(t) for s in SEEDS for t in (
              f"cnn_paper{sfx(s)}_logodds", f"ltn_ctrl_w0{sfx(s)}_logodds",
              f"autoencoder_paper{sfx(s)}", f"random_forest{sfx(s)}", f"msp{sfx(s)}",
              f"mahalanobis{sfx(s)}", f"kg{sfx(s)}", f"kg{sfx(s)}_causal")] + [pred("xgboost")]),

    stage("ablation", "ablation.py",
          "CNN -> +LTN -> +KG -> FULL, paired over shared seeds",
          [os.path.join(MD, "ablation.json")],
          needs=[pred(t) for s in SEEDS for t in (
              f"cnn_paper{sfx(s)}_logodds", f"ltn_ctrl_w0{sfx(s)}_logodds",
              f"ltn_ax6_ratio_w1p0_s{s}_logodds", f"kg{sfx(s)}_causal")]),

    stage("bot_failure", "bot_failure_analysis.py",
          "why the CNN fails on Bot: absorption, feature overlap, oracle",
          [os.path.join(MD, "bot_failure_analysis.json")],
          needs=[pred(t) for s in SEEDS for t in (
              f"cnn_paper{sfx(s)}_logodds", f"random_forest{sfx(s)}",
              f"autoencoder_paper{sfx(s)}")] + [model(f"cnn_paper{sfx(s)}") for s in SEEDS]),

    stage("baselines_tuned", "baselines_tuned.py",
          "the three baselines with hyperparameters selected on validation",
          [os.path.join(MD, "baselines_tuned.json"), pred("xgboost_tuned")]
          + [pred(f"{m}_tuned_s{s}") for s in SEEDS for m in ("random_forest", "isolation_forest")],
          needs=[os.path.join(P, "X_val.npy")],
          external=["the deterministic CNN runs c4_log1p_s42-44 (c4_transform_ab.sh), "
                    "read for the comparison only"]),

    stage("bot_recheck", "bot_mechanism_recheck.py",
          "Bot absorption and rank agreement over every CNN run (paper Figure 2)",
          [os.path.join(MD, "bot_mechanism_recheck.json")],
          needs=[pred(f"{m}{sfx(s)}") for s in SEEDS for m in ("random_forest", "isolation_forest",
                                                                "autoencoder_paper")]
          + [pred(f"{m}_tuned_s{s}") for s in SEEDS for m in ("random_forest", "isolation_forest")]
          + [pred(f"cnn_paper{sfx(s)}_logodds") for s in SEEDS],
          external=["the 11 pre-flag CNN runs (fusion_population.PRE_FLAG) and the 6 "
                    "deterministic ones (c4_log1p_s42-44, postdet_s45-47: noise_postdet.sh)",
                    "ae_det_s42-44 (ae_seeds.sh)"]),

    stage("operational", "operational.py",
          "Phase 7.5 Tier 1: ensemble, calibration/ECE, alert budget, abstention",
          [os.path.join(MD, "operational.json")],
          needs=[model("cnn_paper"), pred("cnn_paper"), pred("fusion_cnn_kg"),
                 pred("kg_causal")],
          external=["the 11-run pre-flag CNN population (fusion_population.PRE_FLAG): "
                    "cnn_paper_s45-47 (rigor_n6.sh), cnn_repro_s42, cnn_noise_r1-4 "
                    "(noise_floor.sh)"]),

    stage("latency", "latency.py",
          "per-component, per-batch throughput; determinism arms",
          [os.path.join(MD, "latency_determinism_on.json")],
          needs=[model("cnn_paper"), os.path.join(MODELS, "label_encoder_paper.pkl")]),

    stage("field_gap", "field_gap.py",
          "the resolution-failure figure: 42 pinned method groups on both metrics",
          [os.path.join(MD, "field_gap.json")],
          external=["runs.jsonl entries for the 42 pinned method groups (field_gap.METHODS), "
                    "most of them from experiment scripts outside this list (deep_zoo.py, "
                    "baselines_classic.py, anomaly_zoo.py, the LTN anatomy arms, c4_transform_ab.sh)"]),

    stage("figures", "paper_figures.py",
          "figures 2-5, recomputed from outputs/metadata only",
          [os.path.join(paths.FIGURES, "fig2_bot_mechanism.png")],
          needs=[os.path.join(MD, "ablation.json"), os.path.join(MD, "bot_failure_analysis.json"),
                 os.path.join(MD, "operational.json")],
          external=["noise_postdet.json (noise_postdet.sh)", "protocol_variance.json "
                    "(protocol_variance.py)"]),

    stage("paper_figures", "paper_figures.py --nesy",
          "the paper's Figures 1 and 2",
          [os.path.join(paths.FIGURES, "nesy_fig2_mechanism.png")],
          needs=[os.path.join(MD, "bot_mechanism_recheck.json")]),
]

PY = os.path.join(paths.ROOT, ".venv", "Scripts", "python.exe")
if not os.path.exists(PY):
    PY = os.path.join(paths.ROOT, ".venv", "bin", "python")


def unproduced_needs():
    """Static closure: every `needs` path must be made by an EARLIER stage."""
    made, gaps = set(), []
    for st in STAGES:
        for n in st["needs"]:
            if n not in made:
                gaps.append((st["name"], n))
        made.update(st["makes"])
    return gaps


# NOTE: every PRINTED string below is ASCII. The Windows console default is
# cp1252 and non-ASCII output raises UnicodeEncodeError -- this script is meant
# to be run directly, not only through run_long.sh (which forces UTF-8), so it
# must survive a bare `python scripts/run_all.py`. The first version of this
# file crashed on its own warning banner, which is the same bug CLAUDE.md
# records being fixed three times as separate incidents.
def check():
    print("=" * 96)
    print("PIPELINE CHECK - stage order, what each stage makes, and what it needs")
    print("=" * 96)
    missing_total = 0
    for i, st in enumerate(STAGES, 1):
        arts = st["makes"]
        miss = [a for a in arts if not os.path.exists(a)]
        missing_total += len(miss)
        mark = ("  OK  " if not miss else "MISSING" if len(miss) == len(arts) else "PARTIAL")
        runs = len(st["runs"])
        print(f"{i:2d}. [{mark}] {st['name']:14s} {st['script']:26s} x{runs}  {st['why']}")
        for a in miss[:6]:
            print(f"              missing: {os.path.relpath(a, paths.WORK)}")
        if len(miss) > 6:
            print(f"              ... and {len(miss) - 6} more")
        for e in st["external"]:
            print(f"              EXTERNAL input: {e}")
    gaps = unproduced_needs()
    print("-" * 96)
    print(f"{len(STAGES)} stages | {missing_total} declared artifacts missing | "
          f"{len(gaps)} needs not made by an earlier stage | "
          f"{sum(len(s['external']) for s in STAGES)} external inputs")
    for name, n in gaps:
        print(f"  UNPRODUCED: stage '{name}' needs {os.path.relpath(n, paths.WORK)}")
    print("A stage with an EXTERNAL input cannot be reproduced by this file alone; the")
    print("experiments named above have to be run first (see docs/scripts_reference.md).")
    print("=" * 96)
    return 1 if (missing_total or gaps) else 0


def run(start=None, keep_going=False):
    """Execute stages in order.

    Changed 2026-09-17 (audit item 7.4): a stage FAILS if any of its executions
    exits non-zero or if, afterwards, its declared artifacts are not on disk and
    newer than the stage's start -- a file left over from an earlier run does not
    count. Every stage's outcome is written to run_all_report.json in METADATA
    (which NSIDS_WORKDIR relocates).
    """
    import json
    import time
    started = start is None
    report = {"workdir": paths.WORK, "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
              "keep_going": keep_going, "stages": []}
    rc_total = 0

    def save():
        rp = os.path.join(paths.METADATA, "run_all_report.json")
        with open(rp, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=1)

    for st in STAGES:
        name = st["name"]
        if not started:
            if name == start:
                started = True
            else:
                print(f"-- skipping {name}")
                continue
        parts = st["script"].split()
        cmd = [PY, "-u", os.path.join(paths.ROOT, "scripts", parts[0])] + parts[1:]
        t0 = time.time()
        codes = []
        for env_extra in st["runs"]:
            label = " ".join(f"{k}={v}" for k, v in env_extra.items())
            print("\n" + "=" * 96)
            print(f"RUN  {name}  ->  {st['script']}  {label}")
            print("=" * 96, flush=True)
            env = dict(os.environ, PYTHONIOENCODING="utf-8", **env_extra)
            codes.append(subprocess.call(cmd, cwd=paths.ROOT, env=env))
        arts = st["makes"]
        fresh = [a for a in arts if os.path.exists(a) and os.path.getmtime(a) >= t0 - 1]
        missing = [os.path.relpath(a, paths.WORK) for a in arts if a not in fresh]
        rc = next((c for c in codes if c != 0), 0)
        ok = rc == 0 and not missing
        report["stages"].append({"name": name, "script": st["script"], "exit_codes": codes,
                                 "seconds": round(time.time() - t0, 1),
                                 "declared_artifacts_missing": missing,
                                 "external_inputs": st["external"], "ok": ok})
        save()
        if not ok:
            why_ = (f"exited {rc}" if rc != 0 else
                    f"exited 0 but did not write: {', '.join(missing)}")
            print(f"\nFAILED: stage '{name}' {why_}. "
                  f"Resume with: python scripts/run_all.py --run --from {name}")
            rc_total = rc_total or rc or 3
            if not keep_going:
                return rc_total
    n_ok = sum(s_["ok"] for s_ in report["stages"])
    print(f"\n{n_ok}/{len(report['stages'])} stages completed and wrote their artifacts")
    report["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    return rc_total


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", action="store_true",
                    help="actually execute the stages (default is check only)")
    ap.add_argument("--from", dest="start", default=None,
                    help="resume execution from this stage name")
    ap.add_argument("--keep-going", action="store_true",
                    help="record a failed stage and continue with the next one")
    a = ap.parse_args()
    if a.start and a.start not in [s["name"] for s in STAGES]:
        sys.exit(f"unknown stage '{a.start}'")
    sys.exit(run(a.start, a.keep_going) if a.run else check())

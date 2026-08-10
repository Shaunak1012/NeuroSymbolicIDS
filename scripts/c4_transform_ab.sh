#!/usr/bin/env bash
# c4_transform_ab.sh — the log1p A/B, re-run on the metric that actually matters.
#
# WHY
# ---
# config.yaml pins `feature_transform: log1p` citing "0.980 vs 0.965 PR-AUC". That
# is the OVERALL BINARY metric: the one inflated by the 17% train/test duplicate
# overlap, and the one metrics.py explicitly forbids as an optimisation target.
# The transform has never been A/B'd on macro zero-day PR-AUC, the actual headline
# (KNOWN_ISSUES: "the feature transform was selected on the contaminated metric").
#
# TAGS — why not the default ones
# -------------------------------
# cnn_paper.py's default tag for seed 43 is `cnn_paper_s43`, which ALREADY EXISTS
# from the pre-flag era. Re-running under that name would put two populations
# (pre- and post-determinism-flag) under one run name in runs.jsonl -- precisely
# the defect that cost three wrong-model rows on 2026-08-05. So every run here
# gets an explicit `c4_<arm>_s<seed>` tag that has never been used.
#
# SEED 42 log1p IS RE-RUN RATHER THAN REUSED. `det_verify_a/b` already provide it
# (0.6297683082, byte-identical pair). Re-running it under c4_log1p_s42 is a
# control on THIS session's code change: cnn_paper.py was edited to add the
# FEATURE_TRANSFORM override, and if that edit is genuinely inert the run must
# return 0.6297683082 exactly. A cheap, decisive check on my own change.
#
#   scripts/c4_transform_ab.sh raw      # -> outputs/c4_raw.log
#   scripts/c4_transform_ab.sh log1p    # -> outputs/c4_log1p.log
#
# Output goes straight to the log with no tail/head/grep in the pipeline: those
# buffer until EOF and starve the heartbeat monitor of the log growth it watches
# (2026-08-03 seed_sweep.sh, 2026-08-05 verify_determinism.sh).
set -u
cd "$(dirname "$0")/.." || exit 1
PY=".venv/Scripts/python.exe"
[ -x "$PY" ] || PY=".venv/bin/python"

ARM="${1:-}"
case "$ARM" in
  raw|log1p) ;;
  *) echo "usage: c4_transform_ab.sh <raw|log1p>"; exit 2;;
esac

LOG="outputs/c4_${ARM}.log"
mkdir -p outputs
: > "$LOG"

for SEED in 42 43 44; do
  TAG="c4_${ARM}_s${SEED}"
  echo "=== $TAG (arm=$ARM seed=$SEED) ===" >> "$LOG"
  FEATURE_TRANSFORM="$ARM" CNN_SEED="$SEED" CNN_TAG="$TAG" CNN_EPOCHS=50 \
    PYTHONIOENCODING=utf-8 "$PY" -u scripts/cnn_paper.py >> "$LOG" 2>&1
  echo "=== $TAG exit=$? ===" >> "$LOG"
done

echo "ALL DONE ($ARM)" >> "$LOG"

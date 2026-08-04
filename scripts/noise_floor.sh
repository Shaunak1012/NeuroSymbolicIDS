#!/usr/bin/env bash
# Characterise RUN-TO-RUN NOISE at fixed seed.
#
# The seed-42 reproduction (2026-08-03) showed training is NOT reproducible at a
# fixed seed: rerunning seed 42 moved macro from 0.6446 to 0.6295 (-0.0151).
# That single observation settles the binary question but not the magnitude, and
# the magnitude is what every claim in this project must now be judged against:
# a delta is only meaningful as a MULTIPLE OF THIS NOISE FLOOR.
#
# Runs seed 42 repeatedly. All runs must be on an idle machine -- concurrent work
# perturbs TF's CPU thread scheduling and is itself a candidate cause of the
# non-determinism being measured here.
#
# ⚠️ No tail/head piping (see lint_conventions.py launcher-suppresses-log-growth).
set -u
cd "$(dirname "$0")/.." || exit 1
PY=".venv/Scripts/python.exe"
N="${NOISE_RUNS:-4}"
for i in $(seq 1 "$N"); do
  echo "########## noise run $i/$N (seed 42) ##########"
  CNN_SEED=42 CNN_TAG="cnn_noise_r${i}" PYTHONIOENCODING=utf-8 "$PY" -u scripts/cnn_paper.py
  echo "########## noise run $i/$N exit=$? ##########"
done
echo "ALL NOISE RUNS DONE"

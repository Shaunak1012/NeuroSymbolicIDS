#!/usr/bin/env bash
# noise_postdet.sh — measure SEED variance with determinism ON.
#
# THE QUESTION
# ------------
# The project's ~0.0256 "indistinguishable" threshold derives from the noise floor
# SD 0.0222. That floor was measured as SIX RUNS OF SEED 42 WITH DETERMINISM OFF
# -- i.e. it is thread-scheduling nondeterminism at a FIXED seed, not seed-to-seed
# variance. Those are different quantities, and the project has been using one as
# a proxy for the other.
#
# C4 measured three DIFFERENT seeds with determinism ON, twice, and got SD 0.0031
# (log1p) and 0.0039 (raw) -- ~6-7x smaller. If that holds at n=6, the dominant
# variance source was never the seed, and comparisons currently filed as "within
# noise" become decidable.
#
# WHY ONLY THREE RUNS ARE NEEDED
# ------------------------------
# Seeds 42/43/44 post-flag ALREADY EXIST as c4_log1p_s42/43/44. Those are
# cnn_paper.py verbatim at the config-default transform: FEATURE_TRANSFORM=log1p
# equals the default, so _TFM_SFX is empty and the code path is identical; only
# CNN_TAG differs, and a tag affects output filenames only.
#
# This is not an assumption -- it is verified. c4_log1p_s42 returned
# 0.629768308213, IDENTICAL TO TWELVE DECIMALS to det_verify_a/det_verify_b, which
# were plain cnn_paper runs with only CNN_TAG set. So the six-run population is:
#
#   c4_log1p_s42 · c4_log1p_s43 · c4_log1p_s44 · postdet_s45 · postdet_s46 · postdet_s47
#
# TAGS: `cnn_paper_s45` etc. ALREADY EXIST as PRE-flag runs. Reusing them would put
# two populations under one run name -- the defect that cost three wrong-model rows
# on 2026-08-05. Hence postdet_s<seed>.
#
#   scripts/noise_postdet.sh 45        # -> outputs/postdet_s45.log
set -u
cd "$(dirname "$0")/.." || exit 1
PY=".venv/Scripts/python.exe"
[ -x "$PY" ] || PY=".venv/bin/python"

SEED="${1:-}"
[ -n "$SEED" ] || { echo "usage: noise_postdet.sh <seed>"; exit 2; }

TAG="postdet_s${SEED}"
LOG="outputs/${TAG}.log"
mkdir -p outputs
: > "$LOG"

echo "=== $TAG (cnn_paper.py, log1p, 50 epochs, determinism ON) ===" >> "$LOG"
CNN_SEED="$SEED" CNN_TAG="$TAG" CNN_EPOCHS=50 \
  PYTHONIOENCODING=utf-8 "$PY" -u scripts/cnn_paper.py >> "$LOG" 2>&1
echo "=== $TAG exit=$? ===" >> "$LOG"
echo "ALL DONE ($TAG)" >> "$LOG"

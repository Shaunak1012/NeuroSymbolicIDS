#!/usr/bin/env bash
# split_variants.sh — train the anchor models on the audit's variant splits (D4).
#
# WHY
# ---
# Every reported result uses a stratified random split over a chronologically
# ordered capture, with no grouping: 54.88 % of test flows share a 5-tuple with a
# training flow and 100 % of test lies inside the training time range (audit
# F-02, F-03; split_integrity.json). preprocess_paper.py now builds two variants:
#
#   paper_grouped   no Flow ID on both sides of the boundary
#   paper_chrono    within each known class, train precedes val precedes test
#
# This trains the CNN (the anchor every comparison is measured against) and the
# benign-only autoencoder (the other half of the double dissociation) on each,
# three deterministic seeds, new tags only. split_variants.py reads the results.
#
# Launch (non-negotiable #2), one lane per split:
#   RUN_LONG_NAME=split_variants_grouped scripts/run_long.sh split_variants.sh paper_grouped grouped
#   RUN_LONG_NAME=split_variants_chrono  scripts/run_long.sh split_variants.sh paper_chrono  chrono
set -u
cd "$(dirname "$0")/.." || exit 1
PY=".venv/Scripts/python.exe"
[ -x "$PY" ] || PY=".venv/bin/python"
export PYTHONIOENCODING=utf-8

SUB="${1:-}"; NAME="${2:-}"
[ -n "$SUB" ] && [ -n "$NAME" ] || { echo "usage: split_variants.sh <paper_subdir> <name>"; exit 2; }
[ -f "data/processed/$SUB/X_train.npy" ] || { echo "no split at data/processed/$SUB"; exit 2; }

for s in 42 43 44; do
  echo "=== cnn_${NAME}_s${s} start $(date -u +%FT%TZ) ==="
  PAPER_SUBDIR="$SUB" CNN_SEED="$s" CNN_TAG="cnn_${NAME}_s${s}" CNN_EPOCHS=50 \
    "$PY" -u scripts/cnn_paper.py
  echo "=== cnn_${NAME}_s${s} exit=$? end $(date -u +%FT%TZ) ==="
done
for s in 42 43 44; do
  echo "=== ae_${NAME}_s${s} start $(date -u +%FT%TZ) ==="
  PAPER_SUBDIR="$SUB" AE_SEED="$s" AE_TAG="ae_${NAME}_s${s}" AE_EPOCHS=50 \
    "$PY" -u scripts/autoencoder_paper.py
  echo "=== ae_${NAME}_s${s} exit=$? end $(date -u +%FT%TZ) ==="
done
echo "ALL DONE ($NAME)"

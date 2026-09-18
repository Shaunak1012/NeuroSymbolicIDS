#!/usr/bin/env bash
# ae_seeds.sh — train the benign-only autoencoder at seeds 42/43/44 on one split.
#
# WHY (audit F-01 / D4, 2026-09-17): every autoencoder run on the canonical split
# predates the determinism flags (added to autoencoder_paper.py on 2026-08-05), so
# the split-variant comparison had no deterministic canonical reference for the
# CNN-vs-autoencoder double dissociation. New tags only.
#
#   RUN_LONG_NAME=ae_det_paper scripts/run_long.sh ae_seeds.sh paper ae_det
set -u
cd "$(dirname "$0")/.." || exit 1
PY=".venv/Scripts/python.exe"
[ -x "$PY" ] || PY=".venv/bin/python"
export PYTHONIOENCODING=utf-8
SUB="${1:-}"; STEM="${2:-}"
[ -n "$SUB" ] && [ -n "$STEM" ] || { echo "usage: ae_seeds.sh <paper_subdir> <tag-stem>"; exit 2; }
for s in 42 43 44; do
  echo "=== ${STEM}_s${s} start $(date -u +%FT%TZ) ==="
  PAPER_SUBDIR="$SUB" AE_SEED="$s" AE_TAG="${STEM}_s${s}" AE_EPOCHS=50 \
    "$PY" -u scripts/autoencoder_paper.py
  echo "=== ${STEM}_s${s} exit=$? end $(date -u +%FT%TZ) ==="
done
echo "ALL DONE (${STEM})"

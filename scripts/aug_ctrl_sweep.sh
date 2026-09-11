#!/usr/bin/env bash
# aug_ctrl_sweep.sh — EXPERIMENT 5's feature-count control.
#
# 2017 ONLY, 67 features. Same data as every historical baseline, with the
# duplicate `Fwd Header Length.1` column removed so the input width matches the
# augmented arm.
#
# WHY THIS EXISTS. The augmented model takes 67 inputs; every previous number in
# this project came from a 68-input model. The dropped column is byte-identical
# to `Fwd Header Length` across all 883,796 training rows, so no INFORMATION
# differs -- but input width sets the conv/flatten dimensions, so the
# architectures are not identical. Reading WIDE against the historical 0.6399
# would confound "wider basis" with "narrower input tensor". This arm removes
# that, and it was specified and built BEFORE any augmented result existed.
#
# It also tests its own premise: CTRL67 vs BASE68 should be ~0 if dropping a
# duplicate column is as inert as claimed. If it is not, that is a finding about
# this pipeline worth having, and it invalidates every WIDE-vs-BASE68 reading.
#
# Kept separate from aug_sweep.sh deliberately: that script was already running
# when this arm was designed, and editing a script bash is mid-execution makes it
# resume from a byte offset into different content.
set -u
cd "$(dirname "$0")/.." || exit 1
PY=".venv/Scripts/python.exe"; [ -x "$PY" ] || PY=".venv/bin/python"
export PYTHONIOENCODING=utf-8

[ -d "data/processed/paper_67" ] || { echo "run scripts/build_augmented.py first"; exit 1; }

SEEDS="${AUG_SEEDS:-42 43 44}"
FAILED=""
for s in $SEEDS; do
  TAG="cnn_67_s${s}"
  if [ -f "models/${TAG}.keras" ]; then echo "[SKIP] $TAG"; continue; fi
  echo "=============================================================================="
  echo "[RUN ] $TAG  (2017 only, 67 features, seed $s)  $(date '+%H:%M:%S')"
  echo "=============================================================================="
  if PAPER_SUBDIR=paper_67 CNN_SEED=$s CNN_TAG="$TAG" "$PY" -u scripts/cnn_paper.py; then
    [ -f "models/${TAG}.keras" ] && echo "[OK  ] $TAG" || { echo "[FAIL] $TAG - no model"; FAILED="$FAILED $TAG"; }
  else
    echo "[FAIL] $TAG - exit $?"; FAILED="$FAILED $TAG"
  fi
done
echo
echo "AUG CONTROL SWEEP DONE${FAILED:+ WITH FAILURES:$FAILED}"
[ -z "$FAILED" ] || exit 1

#!/usr/bin/env bash
# audit_rebase.sh — the training runs the 2026-09-16 audit's re-base needs (Stage 4).
#
# WHY
# ---
# F-01: the CNN baseline every result is quoted against (0.6399) came from runs made
# before the determinism flags existed; today's code gives 0.6298 / 0.6269 / 0.6330.
# The deterministic CNN population already exists as c4_log1p_s{42,43,44}. Lane A
# FIRST re-trains seed 42 under a new tag and checks it is byte-identical to
# c4_log1p_s42 -- which proves those runs are what the current code produces, and,
# because lane B is training at the same time, that pinned-thread determinism
# survives a concurrently loaded machine.
#
# CL-02: `ltn_repro` (CE + omega=1, the base paper's configuration) had no matched
# control; every "control" in the record used focal loss. Both arms are run here at
# three seeds, deterministic, 50 epochs (the base paper's Table II setting):
#
#   lane A   cnn_det_verify_s42, then ltn_repro_det_s{42,43,44}   (CE, base axioms, omega=1)
#   lane B   ltn_repro_ctrl_s{42,43,44}                           (CE, base axioms, omega=0)
#
# Nothing here overwrites an existing artefact: every run has a new tag.
#
# Launch (non-negotiable #2 -- through run_long.sh, one lane per log):
#   RUN_LONG_NAME=audit_rebase_A scripts/run_long.sh audit_rebase.sh A
#   RUN_LONG_NAME=audit_rebase_B scripts/run_long.sh audit_rebase.sh B
set -u
cd "$(dirname "$0")/.." || exit 1
PY=".venv/Scripts/python.exe"
[ -x "$PY" ] || PY=".venv/bin/python"
export PYTHONIOENCODING=utf-8

ltn() {   # ltn <omega> <tag-stem> <seed>
  echo "=== ${2}_s${3} (CE, base, omega=$1, seed=$3) start $(date -u +%FT%TZ) ==="
  LTN_LOSS=ce LTN_AXIOMS=base LTN_OMEGA="$1" LTN_OMEGA_MODE=fixed LTN_EPOCHS=50 \
    LTN_SEED="$3" LTN_TAG="${2}_s${3}" "$PY" -u scripts/ltn_paper.py
  echo "=== ${2}_s${3} exit=$? end $(date -u +%FT%TZ) ==="
}

case "${1:-}" in
  A)
    echo "=== cnn_det_verify_s42 start $(date -u +%FT%TZ) ==="
    CNN_SEED=42 CNN_TAG=cnn_det_verify_s42 CNN_EPOCHS=50 "$PY" -u scripts/cnn_paper.py
    echo "=== cnn_det_verify_s42 exit=$? end $(date -u +%FT%TZ) ==="
    for s in 42 43 44; do ltn 1.0 ltn_repro_det "$s"; done
    ;;
  B)
    for s in 42 43 44; do ltn 0.0 ltn_repro_ctrl "$s"; done
    ;;
  *) echo "usage: audit_rebase.sh <A|B>"; exit 2 ;;
esac
echo "ALL DONE (lane ${1})"

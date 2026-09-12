#!/usr/bin/env bash
# improved_sweep.sh — retrain on Engelen et al.'s CORRECTED CIC-IDS2017.
#
# THE ROBUSTNESS CHECK THIS PROJECT'S CENTRAL FINDING NEEDS.
# Engelen et al. (WTMC 2021) re-ran CIC-IDS2017 through a fixed CICFlowMeter and
# relabelled it: mutual-FIN termination, RST handling, no post-close direction
# flip, and recomputed Idle/Bulk/Down-Up-ratio/flow-length features. Over 20 % of
# traces are reconstructed or relabelled, and a new `X - Attempted` class marks
# attack flows that transmitted NO PAYLOAD.
#
# Under the corrected labels our three powered zero-day families become
#     Bot     1,966 ->   738 effective + 1,470 attempted
#     Web BF  1,507 ->   151 effective + 1,214 attempted
#     Web XSS   652 ->    27 effective +   652 attempted
# so ~9 in 10 web-attack flows, and 2 in 3 Bot flows, are bare connection
# attempts -- and Web XSS falls BELOW the power bar.
#
# TWO ARMS, both pre-registered in preprocess_improved.py before any training:
#   MERGE   attempted folded back into the attack class. Maximally comparable to
#           the original labelling, so the delta isolates FLOW/FEATURE fixes.
#   STRICT  attempted dropped. Only flows where an attack actually transmitted.
#           Two powered families remain, so its macro is NOT comparable to
#           0.6399 -- only per-family numbers transfer.
#
# PRE-REGISTERED: section 4 SURVIVES if effective Bot (n=738) stays at or near
# chance, and is WEAKENED if effective Bot becomes detectable -- that would mean
# Bot's unreachability was substantially an artefact of empty flows.
#
# 67 features, so the comparison arm is cnn_67_s* (paper_67), NOT the 68-feature
# cnn_paper baseline.
set -u
cd "$(dirname "$0")/.." || exit 1
PY=".venv/Scripts/python.exe"; [ -x "$PY" ] || PY=".venv/bin/python"
export PYTHONIOENCODING=utf-8

FAILED=""
for arm in merge exclude; do
  [ -d "data/processed/paper_improved_${arm}" ] || { echo "[SKIP] no split for $arm"; continue; }
  for s in 42 43 44; do
    TAG="cnn_fixed_${arm}_s${s}"
    if [ -f "models/${TAG}.keras" ]; then echo "[SKIP] $TAG"; continue; fi
    echo "=============================================================================="
    echo "[RUN ] $TAG  (corrected 2017, attempted=$arm, seed $s)  $(date '+%H:%M:%S')"
    echo "=============================================================================="
    if PAPER_SUBDIR="paper_improved_${arm}" CNN_SEED=$s CNN_TAG="$TAG" "$PY" -u scripts/cnn_paper.py; then
      [ -f "models/${TAG}.keras" ] && echo "[OK  ] $TAG" || { echo "[FAIL] $TAG - no model"; FAILED="$FAILED $TAG"; }
    else
      echo "[FAIL] $TAG - exit $?"; FAILED="$FAILED $TAG"
    fi
  done
done
echo
echo "IMPROVED SWEEP DONE${FAILED:+ WITH FAILURES:$FAILED}"
[ -z "$FAILED" ] || exit 1

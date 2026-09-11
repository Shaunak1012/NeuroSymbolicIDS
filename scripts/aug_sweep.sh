#!/usr/bin/env bash
# aug_sweep.sh — EXPERIMENT 5: train the CNN on the augmented 2017+2018 basis.
#
# Builds nothing: `build_augmented.py` produces data/processed/paper_aug/ and
# asserts the two things that could silently ruin this -- feature-order alignment
# (2017's 68 minus the verified duplicate `Fwd Header Length.1` equals 2018's 67,
# in order) and NO LEAK (2018's train/val contain none of 2017's six zero-day
# families, because 2018's own split already holds that exact set out).
#
# TEST IS UNTOUCHED 2017. The measuring stick does not move, so every number
# stays comparable to every other number in this project.
#
# PRE-REGISTERED PREDICTION, written before the first run:
#   This FAILS on Bot. 2018's known pool is DDoS / DoS / FTP-BruteForce /
#   SSH-Bruteforce -- the same attack CATEGORIES 2017 already trains on -- so the
#   basis widens in directions it already covered, and Bot's features have 0/8
#   overlap with that task. Expect Bot unchanged, small movement at most on the
#   web families.
#   FALSIFIER: macro zero-day PR-AUC beating the baseline PAIRED against the
#   SEED-MATCHED CNN on 3/3 seeds. Paired, because comparing against the n=3 mean
#   0.6399 is precisely the unpaired error that nearly produced a false positive
#   in the reject-class experiment (locoR_hetero_s44 scored 0.6406 -- above the
#   mean, +0.0010 against its own seed).
#
# ⚠️ THIS ARM CONFOUNDS "wider basis" WITH "twice the data" (1,767,592 rows against
# 883,796). The NARROW control -- equal added volume drawn from a single family
# group -- is specified in build_augmented.py's docstring and is built ONLY if
# this moves the headline. A null needs no such control.
#
# Resumable and fail-soft, same contract as replicate_2018.sh.
set -u
cd "$(dirname "$0")/.." || exit 1
PY=".venv/Scripts/python.exe"; [ -x "$PY" ] || PY=".venv/bin/python"
export PYTHONIOENCODING=utf-8

[ -d "data/processed/paper_aug" ] || { echo "run scripts/build_augmented.py first"; exit 1; }

SEEDS="${AUG_SEEDS:-42 43 44}"
FAILED=""
for s in $SEEDS; do
  TAG="cnn_aug_s${s}"
  if [ -f "models/${TAG}.keras" ]; then echo "[SKIP] $TAG"; continue; fi
  echo "=============================================================================="
  echo "[RUN ] $TAG  (2017 + 2018 known pool, 67 features, seed $s)  $(date '+%H:%M:%S')"
  echo "=============================================================================="
  if PAPER_SUBDIR=paper_aug CNN_SEED=$s CNN_TAG="$TAG" "$PY" -u scripts/cnn_paper.py; then
    [ -f "models/${TAG}.keras" ] && echo "[OK  ] $TAG" || { echo "[FAIL] $TAG - no model"; FAILED="$FAILED $TAG"; }
  else
    echo "[FAIL] $TAG - exit $?"; FAILED="$FAILED $TAG"
  fi
done
echo
echo "AUG SWEEP DONE${FAILED:+ WITH FAILURES:$FAILED}"
echo "NEXT: python scripts/aug_analyse.py   # paired vs the SEED-MATCHED baseline"
[ -z "$FAILED" ] || exit 1

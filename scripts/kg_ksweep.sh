#!/usr/bin/env bash
# kg_ksweep.sh — EXPERIMENT 2: does a finer KG clustering improve the fusion?
#
# WHY: kg_readiness measured Bot cluster purity at 77.6 % (k=200) and 80.6 %
# (k=400), but every fusion result to date used k=200 only. The KG is the one
# component that improves on the CNN (+0.0528, 3/3), so its one free
# hyperparameter has never been swept against the number that matters.
#
# Resumable and fail-soft, same contract as replicate_2018.sh: a run whose report
# exists is skipped, and one failure does not abort the sweep.
#
# ⚠️ THE BAR: CNN+KG = 0.6926 and an absolute number carries 0.0285. A k that
# looks better by less than that is noise. The PAIRED delta over shared seeds
# decides it.
set -u
cd "$(dirname "$0")/.." || exit 1
PY=".venv/Scripts/python.exe"; [ -x "$PY" ] || PY=".venv/bin/python"
export PYTHONIOENCODING=utf-8

FAILED=""
for k in 100 400 800; do
  for s in 42 43 44; do
    TAG="kg_k${k}_s${s}"
    REPORT="outputs/metadata/${TAG}_report.json"
    if [ -f "$REPORT" ]; then echo "[SKIP] $TAG"; continue; fi
    echo "=============================================================================="
    echo "[RUN ] $TAG  (k=$k seed=$s)  $(date '+%H:%M:%S')"
    echo "=============================================================================="
    if KG_K=$k KG_SEED=$s KG_TAG="$TAG" "$PY" -u scripts/kg.py; then
      [ -f "$REPORT" ] && echo "[OK  ] $TAG" || { echo "[FAIL] $TAG - no report"; FAILED="$FAILED $TAG"; }
    else
      echo "[FAIL] $TAG - exit $?"; FAILED="$FAILED $TAG"
    fi
  done
done
echo
echo "SWEEP DONE${FAILED:+ WITH FAILURES:$FAILED}"
[ -z "$FAILED" ] || exit 1

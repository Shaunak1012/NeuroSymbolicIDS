#!/usr/bin/env bash
# loco_sweep.sh — EXPERIMENT 3: does an explicit reject class transfer?
#
# THE IDEA. Every model so far is a CLOSED-SET classifier: 9 classes, no way to
# say "attack I don't recognise". LOCO holds out one KNOWN attack family and
# relabels its training flows "UNKNOWN", so the model learns an explicit reject
# region. p(UNKNOWN) then becomes a TRAINED novelty detector, tested against the
# six real zero-day families it has never seen.
#
# This is the only structural idea left. Everything else swept - 4 deep
# architectures, 7 classical baselines, 4 benign-only methods, 9 post-hoc OOD
# scorers - tried to detect novelty WITHOUT ever training for it.
#
# PRE-REGISTERED PREDICTION, written before the first run:
#   4's mechanism says this FAILS. If the model learns "UNKNOWN = this specific
#   held-out signature" rather than a generic reject region, nothing transfers to
#   Bot, whose features have 0/8 overlap with the known-class task. Expect
#   p(UNKNOWN) to score the held-out-LIKE families and to leave Bot at chance.
#   FALSIFIER: if macro zero-day PR-AUC beats the CNN's 0.6399 on 3/3 seeds for
#   ANY held-out class, the mechanism's scope is narrower than 4 claims and the
#   section needs revising.
#
# FOUR HOLD-OUTS, chosen a priori for MAXIMUM DIVERSITY rather than picked after
# looking: a volumetric flood, a slow-rate DoS, a credential brute-force, and a
# scan. If a transferable reject region exists, one of these four should find it.
#
# Resumable and fail-soft, same contract as replicate_2018.sh.
set -u
cd "$(dirname "$0")/.." || exit 1
PY=".venv/Scripts/python.exe"; [ -x "$PY" ] || PY=".venv/bin/python"
export PYTHONIOENCODING=utf-8

HOLDOUTS=("DDoS" "DoS Hulk" "FTP-Patator" "PortScan")
FAILED=""
for h in "${HOLDOUTS[@]}"; do
  slug=$(echo "$h" | tr ' ' '_')
  for s in 42 43 44; do
    TAG="loco_${slug}_s${s}"
    if [ -f "models/${TAG}.keras" ]; then echo "[SKIP] $TAG"; continue; fi
    echo "=============================================================================="
    echo "[RUN ] $TAG  (hold out '$h', seed $s)  $(date '+%H:%M:%S')"
    echo "=============================================================================="
    if CNN_SEED=$s CNN_TAG="$TAG" CNN_LOCO_HOLDOUT="$h" "$PY" -u scripts/cnn_paper.py; then
      [ -f "models/${TAG}.keras" ] && echo "[OK  ] $TAG" || { echo "[FAIL] $TAG - no model"; FAILED="$FAILED $TAG"; }
    else
      echo "[FAIL] $TAG - exit $?"; FAILED="$FAILED $TAG"
    fi
  done
done
echo
echo "LOCO SWEEP DONE${FAILED:+ WITH FAILURES:$FAILED}"
[ -z "$FAILED" ] || exit 1

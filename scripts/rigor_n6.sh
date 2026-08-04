#!/usr/bin/env bash
# Phase 5 rigor: bring every channel to n=6 so comparisons sit on equal footing.
#
# WHY n=6, quantified against the measured noise floor (SD 0.0222):
#   SE of the mean = SD/sqrt(n)  ->  n=3: 0.0128   n=6: 0.0091
#   Two channels must differ by ~0.051 (n=3) or ~0.036 (n=6) to be distinguishable.
#   The gain is modest because SE falls only as sqrt(n) -- but equal n across
#   channels matters more than the absolute value, since an ASYMMETRIC comparison
#   (one side better sampled) is how the C2 confusion arose in the first place.
#
# ⚠️ KEY POINT: fixed-seed SD is comparable to seed-varied SD, so "more seeds" and
# "more runs" are nearly the same lever. Seeds are NOT the dominant variance
# source here -- run-to-run nondeterminism is.
#
# Order: cheapest first. MSP/Mahalanobis are POST-HOC on already-trained CNNs
# (no training at all); RF/IsoForest are sklearn-only (no TF).
# ⚠️ No tail/head piping (lint: launcher-suppresses-log-growth).
set -u
cd "$(dirname "$0")/.." || exit 1
PY=".venv/Scripts/python.exe"
for s in 45 46 47; do
  echo "########## novelty (MSP + Mahalanobis) seed $s ##########"
  NOVELTY_SEED=$s PYTHONIOENCODING=utf-8 "$PY" -u scripts/novelty.py
  echo "########## novelty seed $s exit=$? ##########"
done
for s in 45 46 47; do
  echo "########## baselines (RF + IsoForest + XGB) seed $s ##########"
  BASELINE_SEED=$s PYTHONIOENCODING=utf-8 "$PY" -u scripts/baselines.py
  echo "########## baselines seed $s exit=$? ##########"
done
echo "ALL RIGOR RUNS DONE"

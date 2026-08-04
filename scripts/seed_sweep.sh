#!/usr/bin/env bash
# Extend the key trainable channels from n=3 to n=6 seeds.
#
# WHY: at n=3 the Wilcoxon signed-rank floor is p=0.25, so NO seed-level claim in
# this project can reach p<0.05 regardless of effect size. At n=6 the floor is
# p=0.031, which makes seed-level significance achievable for the first time.
#
# ⚠️ DO NOT PIPE THE TRAINING RUNS THROUGH tail/head.
# The first version of this script did (`... | tail -5`) and it caused a FALSE
# STALL alert on 2026-08-03: tail buffers until EOF, so the log stayed empty for
# the entire ~20-minute training run while the heartbeat monitor -- which watches
# LOG GROWTH -- concluded the job had hung. The heartbeat rule is only as good as
# the launcher preserving the signal it depends on. `lint_conventions.py` now
# fails on this pattern so it cannot recur silently.
set -u
cd "$(dirname "$0")/.." || exit 1
PY=".venv/Scripts/python.exe"

for s in 45 46 47; do
  echo "########## CNN seed $s ##########"
  CNN_SEED=$s PYTHONIOENCODING=utf-8 "$PY" -u scripts/cnn_paper.py
  echo "########## CNN seed $s exit=$? ##########"
  echo "########## AE seed $s ##########"
  AE_SEED=$s PYTHONIOENCODING=utf-8 "$PY" -u scripts/autoencoder_paper.py
  echo "########## AE seed $s exit=$? ##########"
  echo "########## SEED $s DONE ##########"
done
echo "ALL SEEDS DONE"

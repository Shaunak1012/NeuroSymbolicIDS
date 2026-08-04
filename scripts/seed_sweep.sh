#!/usr/bin/env bash
# Extend the key trainable channels from n=3 to n=6 seeds.
# WHY: at n=3 the Wilcoxon signed-rank floor is p=0.25, so NO seed-level claim in
# this project can reach p<0.05 regardless of effect size. At n=6 the floor is
# p=0.031, which makes seed-level significance achievable for the first time.
set -u
cd "$(dirname "$0")/.." || exit 1
PY=".venv/Scripts/python.exe"
for s in 45 46 47; do
  echo "########## CNN seed $s ##########"
  CNN_SEED=$s PYTHONIOENCODING=utf-8 "$PY" -u scripts/cnn_paper.py 2>&1 | tail -5
  echo "########## AE seed $s ##########"
  AE_SEED=$s PYTHONIOENCODING=utf-8 "$PY" -u scripts/autoencoder_paper.py 2>&1 | tail -5
  echo "########## SEED $s DONE ##########"
done
echo "ALL SEEDS DONE"

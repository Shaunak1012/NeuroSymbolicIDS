#!/usr/bin/env bash
# loco_sweep.sh — EXPERIMENT 4: does an explicit reject class transfer?
#
# 🔴 RETRACTED AND REDESIGNED 2026-09-10 — READ THIS BEFORE THE REST.
# The first version of this sweep held out ONE family per run and relabelled it
# "UNKNOWN". That is a NO-OP. Renaming one class leaves nine classes and the same
# partition of the training set, and a softmax objective is invariant to class
# NAMES -- so training was identical to the baseline up to a permutation of
# output units, and p(UNKNOWN) was simply p(held-out family).
# `loco_reject.py` measured exactly that on the one model the sweep produced:
#     p(UNKNOWN) puts the held-out DDoS flows at the 94.4th percentile
#     and the REAL zero-day families at 0.569, against benign at 0.475.
#     macro on p(UNKNOWN) = 0.1684, vs the CNN's 0.6399.
# A family detector, not a novelty detector. The sweep was stopped 1.5 runs in
# and its headline (loco_DDoS_s42 = 0.6240) is a re-seed of the baseline, NOT
# evidence about reject classes in either direction. It does not touch the
# pre-registered falsifier.
#
# THE IDEA, CORRECTLY IMPLEMENTED. To create a reject class you must REDUCE the
# class count: merge SEVERAL known families into one shared UNKNOWN. 9 -> 7 is a
# real structural change -- the model must now cover heterogeneous signatures
# with a single output unit, which is what "none of the above" means. That is the
# only structural idea left; everything else swept (4 deep architectures, 7
# classical baselines, 4 benign-only methods, 9 post-hoc OOD scorers) tried to
# detect novelty WITHOUT ever training for it.
#
# TWO ARMS, and the CONTRAST is the point rather than either arm alone:
#   HETERO  DDoS + FTP-Patator + PortScan          flood + brute-force + scan
#   HOMOG   DoS GoldenEye + Hulk + Slowhttptest    three variants of one thing
# If a reject region genuinely GENERALISES, HETERO must transfer better than
# HOMOG. If both behave alike, the unit is learning a signature union and not a
# region -- the same failure as the retracted version, one level up.
#
# PRE-REGISTERED PREDICTION, written before the first run of the new design:
#   4's mechanism still says this FAILS. Bot's discriminative features have 0/8
#   overlap with the known-class task, and merging known families reorganises the
#   decision boundary without adding the features Bot needs. Expect Bot to stay
#   at chance under p(UNKNOWN) in BOTH arms.
#   FALSIFIER: macro zero-day PR-AUC beating the CNN's 0.6399 on every seed in
#   either arm means 4's scope is narrower than claimed and the section needs
#   revising. Evaluate with `loco_reject.py`, on p(UNKNOWN) -- NOT on the default
#   1-p(BENIGN) headline, which folds the reject mass back into the attack mass
#   and is what hid the no-op for a whole run.
#
# ⚠️ COST OF THE MERGE, stated up front: three known classes leave the supervised
# task, so a drop in the 1-p(BENIGN) headline is EXPECTED and is not the result.
# The result is p(UNKNOWN)'s behaviour on the six real zero-day families.
#
# PILOT FIRST. Two seeds per arm (4 runs, ~90 min). Seed 44 is added only if
# something moves -- LOCO_SEEDS overrides. Resumable and fail-soft, same contract
# as replicate_2018.sh.
set -u
cd "$(dirname "$0")/.." || exit 1
PY=".venv/Scripts/python.exe"; [ -x "$PY" ] || PY=".venv/bin/python"
export PYTHONIOENCODING=utf-8

ARMS=("hetero:DDoS,FTP-Patator,PortScan"
      "homog:DoS GoldenEye,DoS Hulk,DoS Slowhttptest")
SEEDS="${LOCO_SEEDS:-42 43}"
FAILED=""
for arm in "${ARMS[@]}"; do
  name="${arm%%:*}"; families="${arm#*:}"
  for s in $SEEDS; do
    TAG="locoR_${name}_s${s}"
    if [ -f "models/${TAG}.keras" ]; then echo "[SKIP] $TAG"; continue; fi
    echo "=============================================================================="
    echo "[RUN ] $TAG  (merge '$families' -> UNKNOWN, seed $s)  $(date '+%H:%M:%S')"
    echo "=============================================================================="
    if CNN_SEED=$s CNN_TAG="$TAG" CNN_LOCO_HOLDOUT="$families" "$PY" -u scripts/cnn_paper.py; then
      [ -f "models/${TAG}.keras" ] && echo "[OK  ] $TAG" || { echo "[FAIL] $TAG - no model"; FAILED="$FAILED $TAG"; }
    else
      echo "[FAIL] $TAG - exit $?"; FAILED="$FAILED $TAG"
    fi
  done
done
echo
echo "LOCO SWEEP DONE${FAILED:+ WITH FAILURES:$FAILED}"
echo "NEXT: python scripts/loco_reject.py   # evaluate p(UNKNOWN), not the headline"
[ -z "$FAILED" ] || exit 1

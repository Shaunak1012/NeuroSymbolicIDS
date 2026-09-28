#!/usr/bin/env bash
# Low-data axiom test (2026-09-28): the paper's LTN_CTRL vs LTN_AX6 comparison on the
# 70,384-flow `paper_subsampled` training set, seeds 42-44, then log-odds rescoring and
# the pre-registered evaluation in ltn_lowdata.py. Predictions are in that docstring.
# Launch through run_long.sh (non-negotiable #2). Do NOT pipe through tail/head -- it
# buffers to EOF and blinds the heartbeat monitor.
set -u
cd "$(dirname "$0")/.." || exit 1
PY=".venv/Scripts/python.exe"
[ -x "$PY" ] || PY=".venv/bin/python"
export PAPER_SUBDIR=paper_subsampled PYTHONIOENCODING=utf-8
TAGS=""
for s in 42 43 44; do
  echo "########## control seed $s ##########"
  LTN_SEED=$s LTN_LOSS=focal LTN_AXIOMS=base LTN_OMEGA=0.0 LTN_OMEGA_MODE=fixed \
    LTN_TAG="ltn_ctrl_w0_sub_s$s" "$PY" -u scripts/ltn_paper.py || { echo "exit=$? control $s"; exit 1; }
  echo "########## axioms seed $s ##########"
  LTN_SEED=$s LTN_LOSS=focal LTN_AXIOMS=both LTN_OMEGA=1.0 LTN_OMEGA_MODE=ratio \
    LTN_TAG="ltn_ax6_ratio_w1p0_sub_s$s" "$PY" -u scripts/ltn_paper.py || { echo "exit=$? axioms $s"; exit 1; }
  TAGS="$TAGS,ltn_ctrl_w0_sub_s$s,ltn_ax6_ratio_w1p0_sub_s$s"
done
echo "########## rescore ##########"
RESCORE_TAGS="${TAGS#,}" "$PY" -u scripts/rescore_logits.py || { echo "exit=$? rescore"; exit 1; }
echo "########## evaluate ##########"
"$PY" -u scripts/ltn_lowdata.py || { echo "exit=$? evaluate"; exit 1; }
echo "ALL LOW-DATA RUNS DONE"

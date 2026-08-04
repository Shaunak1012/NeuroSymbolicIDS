#!/usr/bin/env bash
# Extend the LTN no-axiom control from n=3 to n=6, matching the CNN's seed set.
#
# WHY THIS IS NECESSARY, not optional:
# Extending the CNN to n=6 dropped its macro mean from 0.6399 to 0.6250 and
# widened its range 5.2x. The CNN-vs-control gap collapsed from +0.0204 (which a
# paired bootstrap called SIGNIFICANT, p=0.001) to +0.0055. But the control is
# still n=3, so the comparison is now ASYMMETRIC -- the better-sampled channel is
# ours. That is exactly the C2 defect ("the reference baseline was single-seed
# while its comparators were not") in mirror image, and C2 cannot be honestly
# closed either way until both sides share a seed set.
#
# Config reproduces ltn_ctrl_w0 exactly: focal loss, base axioms, omega=0 (i.e.
# the axiom term is switched off -- this is the NO-AXIOM control), fixed mode.
# ⚠️ Do NOT pipe through tail/head -- it buffers to EOF and blinds the heartbeat
# monitor (see lint_conventions.py, launcher-suppresses-log-growth).
set -u
cd "$(dirname "$0")/.." || exit 1
PY=".venv/Scripts/python.exe"
for s in 45 46 47; do
  echo "########## LTN control seed $s ##########"
  LTN_SEED=$s LTN_LOSS=focal LTN_AXIOMS=base LTN_OMEGA=0.0 \
    LTN_OMEGA_MODE=fixed LTN_TAG="ltn_ctrl_w0_s${s}" \
    PYTHONIOENCODING=utf-8 "$PY" -u scripts/ltn_paper.py
  echo "########## LTN control seed $s exit=$? ##########"
done
echo "ALL LTN CONTROL SEEDS DONE"

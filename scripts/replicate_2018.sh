#!/usr/bin/env bash
# replicate_2018.sh — Phase 6: the four-architecture replication on CSE-CIC-IDS2018.
#
# WHY THIS EXISTS
# ---------------
# 12 trainings (4 architectures x 3 seeds) on CPU. A bare loop loses everything
# to one failure or one power cut -- and this project has already lost a session
# to a power cut once. So this launcher is RESUMABLE and FAIL-SOFT:
#
#   * RESUMABLE  — a run whose model artifact already exists is skipped. Re-run
#                  the script after any interruption and it continues where it
#                  stopped. Nothing is recomputed.
#   * FAIL-SOFT  — a failing run does NOT abort the batch. It is recorded and the
#                  remaining runs proceed. Losing 11 good runs to 1 bad one is
#                  the failure mode this guards against; the summary at the end
#                  names every failure and the exit code is non-zero if any.
#
# THE CONFIGS ARE RECOVERED FROM runs.jsonl, NOT GUESSED
# -------------------------------------------------------
# The LTN arms' exact settings were read out of the research record:
#   control : loss=focal axioms=base  omega=0.0 mode=fixed
#   +Ax6    : loss=focal axioms=both  omega=1.0 mode=ratio
# The tag "ltn_ax6_ratio_w1p0" does not decode to those on its own -- AXIOMS has
# no "ax6" value -- so inferring from the name would have produced a different
# experiment wearing the right label. This is what the run record is for.
#
# PAPER_SUBDIR POINTS THE TRAINERS AT 2018
# -----------------------------------------
# The four trainers are NOT forked: they produced every number in the paper.
# PAPER_SUBDIR is an additive env override, verified inert when unset (the same
# pattern C4 used for FEATURE_TRANSFORM and verified to twelve decimals).
#
# ⚠️ Training data is MATCHED to 2017's 883,796 rows by default (see
# preprocess_2018.py's MATCH_2017_TRAIN), so 2018-vs-2017 differences are not
# confounded with having 4x the data.
#
# Usage:  scripts/run_long.sh replicate_2018.sh
#         scripts/replicate_2018.sh --dry-run     # print the plan, run nothing
set -u
cd "$(dirname "$0")/.." || exit 1
PY=".venv/Scripts/python.exe"
[ -x "$PY" ] || PY=".venv/bin/python"

DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1

SEEDS="42 43 44"
export PAPER_SUBDIR="paper_2018"
export PYTHONIOENCODING="utf-8"

declare -a FAILED=()
declare -a SKIPPED=()
declare -a RAN=()

# run_one <tag> <script> <env assignments...>
run_one() {
  local tag="$1"; shift
  local script="$1"; shift
  local marker="models/${tag}.keras"

  if [ -f "$marker" ]; then
    echo "[SKIP] ${tag} — ${marker} exists (resume)"
    SKIPPED+=("$tag")
    return 0
  fi
  if [ "$DRY" -eq 1 ]; then
    echo "[PLAN] ${tag} <- ${script}  ($*)"
    return 0
  fi

  echo "=============================================================================="
  echo "[RUN ] ${tag}  <- ${script}   $(date '+%H:%M:%S')"
  echo "=============================================================================="
  # shellcheck disable=SC2086
  if env $* "$PY" -u "scripts/${script}" ; then
    if [ -f "$marker" ]; then
      echo "[OK  ] ${tag}"
      RAN+=("$tag")
    else
      echo "[FAIL] ${tag} — exited 0 but ${marker} was not written"
      FAILED+=("$tag")
    fi
  else
    echo "[FAIL] ${tag} — exit $?"
    FAILED+=("$tag")
  fi
}

echo "PHASE 6 REPLICATION — 4 architectures x 3 seeds on ${PAPER_SUBDIR}"
echo "resumable (skips existing models) · fail-soft (one failure does not abort)"
echo

for s in $SEEDS; do
  run_one "cnn_paper_2018_s${s}" "cnn_paper.py" \
    "CNN_SEED=${s}" "CNN_TAG=cnn_paper_2018_s${s}"

  run_one "ltn_ctrl_w0_2018_s${s}" "ltn_paper.py" \
    "LTN_SEED=${s}" "LTN_LOSS=focal" "LTN_AXIOMS=base" "LTN_OMEGA=0.0" \
    "LTN_OMEGA_MODE=fixed" "LTN_TAG=ltn_ctrl_w0_2018_s${s}"

  run_one "ltn_ax6_ratio_w1p0_2018_s${s}" "ltn_paper.py" \
    "LTN_SEED=${s}" "LTN_LOSS=focal" "LTN_AXIOMS=both" "LTN_OMEGA=1.0" \
    "LTN_OMEGA_MODE=ratio" "LTN_TAG=ltn_ax6_ratio_w1p0_2018_s${s}"

  run_one "autoencoder_paper_2018_s${s}" "autoencoder_paper.py" \
    "AE_SEED=${s}" "AE_TAG=autoencoder_paper_2018_s${s}"
done

echo
echo "=============================================================================="
echo "SUMMARY   ran ${#RAN[@]} · skipped ${#SKIPPED[@]} · FAILED ${#FAILED[@]}"
echo "=============================================================================="
[ ${#SKIPPED[@]} -gt 0 ] && printf '  skipped: %s\n' "${SKIPPED[*]}"
if [ ${#FAILED[@]} -gt 0 ]; then
  printf '  FAILED : %s\n' "${FAILED[*]}"
  echo "  Re-run this script to retry only the failures — completed runs are skipped."
  echo "BATCH DONE WITH FAILURES"
  exit 1
fi
echo "BATCH DONE"

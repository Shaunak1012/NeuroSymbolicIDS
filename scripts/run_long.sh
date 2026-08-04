#!/usr/bin/env bash
# run_long.sh — launch a long job WITH monitoring already attached.
#
# WHY THIS EXISTS
# ---------------
# CLAUDE.md requires a heartbeat monitor on any background job expected to run
# >10-15 min. On 2026-08-03 that rule lapsed on SIX jobs in one session. The root
# cause was not carelessness: the harness already notifies on *completion*, which
# feels like monitoring but does not cover a STALL or a HANG — which is the only
# thing the heartbeat rule is actually for.
#
# A rule that depends on correctly self-assessing "will this take >15 min?" at
# launch time is a rule that will lapse. This makes the compliant path the easy
# path: one command that launches AND arms monitoring, so there is no judgement
# call to forget.
#
#   scripts/run_long.sh cnn_paper.py                    # -> outputs/cnn_paper.log
#   CNN_SEED=43 scripts/run_long.sh cnn_paper.py        # env vars pass through
#   scripts/run_long.sh kg.py --some-flag
#
# Then watch it (log-growth staleness is authoritative; `ps` is advisory only,
# per the 2026-08-01 known issue about false "process died" reads on Git-Bash):
#
#   scripts/run_long.sh --watch cnn_paper.py
set -u
cd "$(dirname "$0")/.." || exit 1
PY=".venv/Scripts/python.exe"
[ -x "$PY" ] || PY=".venv/bin/python"

WATCH=0
if [ "${1:-}" = "--watch" ]; then WATCH=1; shift; fi
[ $# -ge 1 ] || { echo "usage: run_long.sh [--watch] <script.py> [args...]"; exit 2; }

SCRIPT="$1"; shift
BASE="$(basename "$SCRIPT" .py)"
LOG="outputs/${BASE}.log"
mkdir -p outputs

# PYTHONIOENCODING is forced: the console default is cp1252 on Windows, which
# crashes on any non-ASCII output (hit 3x on 2026-08-03).
PYTHONIOENCODING=utf-8 "$PY" -u "scripts/$SCRIPT" "$@" >"$LOG" 2>&1 &
PID=$!
echo "launched $SCRIPT (pid $PID) -> $LOG"
echo "monitor with:  scripts/run_long.sh --watch $SCRIPT"

if [ "$WATCH" -eq 0 ]; then
  echo "$PID" > "outputs/.${BASE}.pid"
  exit 0
fi

# --- heartbeat: log-growth staleness is the authoritative dead/hung signal -----
last=0; stale=0
while true; do
  sz=$(stat -c %s "$LOG" 2>/dev/null || echo 0)
  if kill -0 "$PID" 2>/dev/null; then alive=1; else alive=0; fi
  if [ "$sz" -gt "$last" ]; then
    stale=0
    grep -aE "Traceback|Error|FAILED|MemoryError|Killed|HEADLINE|DONE|exit [0-9]" "$LOG" | tail -2
  else
    stale=$((stale + 1))
  fi
  last=$sz
  if [ "$alive" -eq 0 ] && [ "$stale" -ge 2 ]; then
    echo "HEARTBEAT: $BASE finished; final log ${sz}B"
    tail -3 "$LOG"; break
  fi
  if [ "$stale" -ge 12 ]; then
    # Distinguish FINISHED from HUNG before crying wolf. A 2026-08-03 monitor
    # reported STALLED for a job that had already completed cleanly, because log
    # growth stopping is ambiguous between the two and the liveness check was
    # unreliable. Check the process explicitly before declaring a stall.
    if kill -0 "$PID" 2>/dev/null; then
      echo "HEARTBEAT: $BASE STALLED — process alive but no log growth for ~10 min. Investigate."
    else
      echo "HEARTBEAT: $BASE finished (log quiet, process gone); final log ${sz}B"
      tail -3 "$LOG"
    fi
    break
  fi
  sleep 50
done

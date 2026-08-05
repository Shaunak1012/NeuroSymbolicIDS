#!/usr/bin/env bash
# verify_determinism.sh — does the determinism config actually reproduce?
#
# Phase 7.5 Tier 2 #5. `determinism.enable()` pins seeds, enables op determinism
# and FIXES the threadpool sizes (intra=16 / inter=2 by default) rather than
# dropping to a single thread. That choice is an empirical claim -- "pinning is
# enough on one machine" -- so it gets tested instead of asserted.
#
# THE TEST: train seed 42 TWICE with identical settings and compare the saved
# probability arrays for BYTE-level identity. Byte-identical is the only
# unambiguous pass; "close" is what we already had (SD 0.0222).
#
# Runs use a tag containing "smoke", so paths.predictions_dir() quarantines the
# undertrained arrays into outputs/predictions/_smoke_archive/ and they can never
# be mistaken for a real fusion channel. CNN_SUBSET also suppresses runs.jsonl
# logging, so this cannot pollute the research record.
#
#   scripts/verify_determinism.sh          # fast: 50k rows, 2 epochs
#   FULL=1 scripts/verify_determinism.sh   # full training, both runs (slow)
set -u
cd "$(dirname "$0")/.." || exit 1
PY=".venv/Scripts/python.exe"
[ -x "$PY" ] || PY=".venv/bin/python"

ative_dir() {  # where cnn_paper.py will have written this tag's prediction
  case "$1" in *smoke*) echo "outputs/predictions/_smoke_archive";;
              *) echo "outputs/predictions";; esac
}

if [ "${FULL:-0}" = "1" ]; then
  # FULL mode trains for real, so CNN_SUBSET=0 and cnn_paper.py DOES log to
  # runs.jsonl. Using a "smoke" tag here would be a lie in two directions: it
  # would quarantine two genuinely-trained channels into the smoke archive, AND
  # it would stamp the research record with rows named "smoke". These are real
  # seed-42 runs, so they get real tags and are logged as such.
  SUB=0; EP=50; A=det_verify_a; B=det_verify_b
  echo "FULL verification: 2 x complete training run (logged to runs.jsonl as real runs)"
else
  # FAST mode trains a throwaway. CNN_SUBSET>0 suppresses runs.jsonl logging, and
  # the "smoke" tag routes the undertrained arrays to _smoke_archive/ so they can
  # never be picked up as a real fusion channel.
  SUB=50000; EP=2; A=smoke_det_a; B=smoke_det_b
  echo "FAST verification: 2 x (50k rows, 2 epochs)"
fi

for TAG in "$A" "$B"; do
  echo "=== $TAG ==="
  CNN_SEED=42 CNN_TAG="$TAG" CNN_SUBSET="$SUB" CNN_EPOCHS="$EP" \
    PYTHONIOENCODING=utf-8 "$PY" -u scripts/cnn_paper.py 2>&1 \
    | grep -a --line-buffered -E "DETERMINISM|macro|Traceback|Error|DONE"
done

echo
echo "=== COMPARISON ==="
DA="$(ative_dir "$A")"; DB="$(ative_dir "$B")"
PYTHONIOENCODING=utf-8 A="$A" B="$B" DA="$DA" DB="$DB" "$PY" - <<'PY'
import numpy as np, os, hashlib, sys
pa = os.path.join(os.environ["DA"], f"y_prob_{os.environ['A']}_test.npy")
pb = os.path.join(os.environ["DB"], f"y_prob_{os.environ['B']}_test.npy")
for p in (pa, pb):
    if not os.path.exists(p):
        sys.exit(f"MISSING {p} -- a run failed; read the log above")
a, b = np.load(pa), np.load(pb)
ha = hashlib.blake2b(a.tobytes(), digest_size=16).hexdigest()
hb = hashlib.blake2b(b.tobytes(), digest_size=16).hexdigest()
print(f"  run A hash {ha}")
print(f"  run B hash {hb}")
if ha == hb:
    print("\n  RESULT: BYTE-IDENTICAL -- determinism CONFIRMED at this thread config.")
else:
    d = np.abs(a - b)
    print(f"\n  RESULT: DIFFER. max|diff| {d.max():.3e}  mean|diff| {d.mean():.3e}  "
          f"n_differing {(d > 0).sum():,}/{len(a):,}")
    print("  -> pinned multi-threading is NOT sufficient on this machine.")
    print("     Re-run with TF_THREADS=1 TF_THREADS_INTER=1 and pay the speed cost.")
PY

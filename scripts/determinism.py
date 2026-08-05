"""
determinism.py — Phase 7.5 Tier 2 #5: make training reproducible at fixed seed.

THE DEFECT THIS ADDRESSES
-------------------------
Six runs of **seed 42, identical code, idle machine** produced macro zero-day
PR-AUC of 0.6446 / 0.6295 / 0.6366 / 0.6124 / 0.5825 / 0.6280 — **SD 0.0222,
range 0.0621, CV 3.6 %**. A fixed seed did NOT pin the result.

That noise floor is the most consequential measurement in this project. It
**retracted C2** (a +0.0204 gap that had already passed a paired bootstrap at
p=0.001 is only 0.9 SD — smaller than re-running one model twice), made every
published n=3 range an artefact, and revealed that the headline `cnn_paper =
0.6446` is the **max of 11 runs**, not a typical result.

**Root cause: no determinism flags were set anywhere in this project.**
TensorFlow on CPU parallelises reductions across threads, and floating-point
addition is not associative, so the order in which threads finish changes the
result. Seeding only controls the *pseudo-random* sources (initialisation,
shuffling, dropout); it does nothing about *scheduling*.

WHAT `enable()` SETS, AND WHY EACH ONE IS NEEDED
------------------------------------------------
  * `PYTHONHASHSEED`          — Python's string hashing is randomised per process.
  * `TF_DETERMINISTIC_OPS`    — the pre-2.8 env-var form; harmless and belt-and-braces.
  * `TF_CUDNN_DETERMINISTIC`  — no-op on CPU; set so a future GPU move inherits it.
  * `tf.keras.utils.set_random_seed` — seeds Python `random`, numpy AND TF in one call.
  * `tf.config.experimental.enable_op_determinism()` — the real fix. Forces
    deterministic kernels and deterministic reduction order.
  * **PINNED thread counts** — the part people miss. `enable_op_determinism()`
    makes each *op* deterministic, but the threadpool size still affects
    reduction order, so it must be FIXED rather than left to TF's core-count
    default. Defaults here are `intra=16 / inter=2`, matching what `ltn_paper.py`
    already used — **fixed, not minimal.**

**Why not `threads=1`?** One thread is the only setting reproducible *across
machines with different core counts*, but it is drastically slower and this
project has one machine. Pinning to a fixed count should give same-machine
reproducibility at full speed. **That is an empirical claim, so it is tested
rather than assumed** — see `verify_determinism.sh`. If a pinned multi-thread
config turns out not to be reproducible, set `TF_THREADS=1` and pay the cost.

⚠️ **THIS COSTS SOME WALL-CLOCK TIME.** That trade is the point: the project
cannot publish deltas smaller than its own reproducibility. Set
`TF_DETERMINISM=0` to opt out for a throwaway exploratory run.

⚠️ **The thread config must be set BEFORE any op runs.** TensorFlow snapshots the
threadpool configuration on first use and raises if it changes afterwards, so
`enable()` must be called immediately after `import tensorflow`, before any
tensor is created. All callers do this.

⚠️ **Determinism does NOT make old and new runs comparable.** Pinning the threads
changes the reduction order, so a deterministic seed-42 run will not reproduce
any of the 11 historical seed-42 values — it defines a *new* fixed point. Runs
before and after this flag are different populations; do not pool them. This is
the same trap as the session/environment effect recorded in KNOWN_ISSUES.
"""
import os
import random


def enable(seed, intra=16, inter=2, verbose=True):
    """Pin every source of run-to-run variation. Call right after importing TF.

    Returns a dict describing what was applied, suitable for logging into
    `runs.jsonl` so a run's determinism state travels with its numbers.
    """
    on = os.environ.get("TF_DETERMINISM", "1") != "0"
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)

    import numpy as np
    import tensorflow as tf
    np.random.seed(seed)

    if not on:
        tf.random.set_seed(seed)
        if verbose:
            print(f"DETERMINISM: DISABLED (TF_DETERMINISM=0) — seed {seed} only. "
                  f"Expect run-to-run SD ~0.0222 on macro.")
        return {"deterministic": False, "seed": seed, "intra": None, "inter": None}

    os.environ["TF_DETERMINISTIC_OPS"] = "1"
    os.environ["TF_CUDNN_DETERMINISTIC"] = "1"

    # Seeds python-random, numpy and TF together.
    tf.keras.utils.set_random_seed(seed)

    applied = {"deterministic": True, "seed": seed, "intra": intra, "inter": inter,
               "op_determinism": False, "threads_pinned": False}
    try:
        tf.config.experimental.enable_op_determinism()
        applied["op_determinism"] = True
    except Exception as e:                                    # pragma: no cover
        print(f"DETERMINISM: enable_op_determinism() unavailable ({e})")

    # Must happen before the threadpools are instantiated; TF raises otherwise.
    try:
        tf.config.threading.set_intra_op_parallelism_threads(intra)
        tf.config.threading.set_inter_op_parallelism_threads(inter)
        applied["threads_pinned"] = True
    except RuntimeError as e:
        print(f"DETERMINISM: thread config REJECTED — TF was already initialised "
              f"({e}). enable() must be called before any op runs; this run is "
              f"NOT fully deterministic.")

    if verbose:
        print(f"DETERMINISM: ON — seed {seed}, op_determinism="
              f"{applied['op_determinism']}, intra={intra} inter={inter} "
              f"(pinned={applied['threads_pinned']}).")
    return applied

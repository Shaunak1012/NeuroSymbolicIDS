"""
noise_postdet.py — decompose this project's uncertainty into its actual sources.

THE PROBLEM
-----------
The ~0.0256 "indistinguishable" threshold -- which retracted C2 and demoted every
within-tier comparison the project has made -- rests on the noise floor SD 0.0222.
That floor was measured as **six runs of SEED 42 with determinism OFF**. It is
therefore *thread-scheduling nondeterminism at a fixed seed*, and the project has
been using it as though it were *seed-to-seed variance*. Those are different
quantities and nobody had ever measured the second one in isolation.

`determinism.enable()` makes that separation possible for the first time: with
threads pinned, a fixed seed reproduces byte-identically, so varying the seed
measures seed variance ALONE.

THE THREE QUANTITIES
--------------------
  A  pre-flag,  seed FIXED  (n=6)  -> nondeterminism only          [SD 0.0222 documented]
  B  pre-flag,  seed VARIES (n=6)  -> nondeterminism + seed (+ any session drift)
  C  post-flag, seed VARIES (n=6)  -> SEED ONLY

If C << A, the dominant source of this project's uncertainty was never the seed,
and the threshold that retracted C2 was measuring the wrong thing.

PRE-REGISTERED PREDICTIONS (written and committed BEFORE seeds 45/46/47 finished
-- see git history; the n=3 estimate from C4 was SD 0.0031/0.0039)
-------------------------------------------------------------------------------
P1  **Post-flag seed SD at n=6 will be < 0.010**, i.e. materially below the 0.0222
    floor. If it lands near 0.0222 instead, C4's n=3 estimate was a small-sample
    artifact and the existing threshold is vindicated -- a clean, useful negative.

P2  **The pre-flag "session effect" will NOT reproduce.** Pre-flag, macro declined
    perfectly monotonically with seed number (rho = -1.000 for XSS, -0.943 macro;
    seeds 45/46/47 gave 0.6250 / 0.6086 / 0.5966). That was attributed to a
    session/environment effect and later withdrawn as "probably nondeterminism".
    This tests it directly: with determinism ON, the same three seeds should NOT
    continue the decline. **A withdrawn claim gets a real experiment.**

P3  **The decomposition will be internally consistent**: sqrt(A^2 + C^2) should
    approximate B, within the ~30% relative error an SD estimate carries at n=6.
    This is the check that the three populations are actually measuring what they
    are claimed to measure.

⚠️ WHAT THIS CANNOT DO, STATED UP FRONT
---------------------------------------
It cannot reopen C2. C2's numbers (CNN vs LTN control, +0.0204) are **pre-flag on
both sides**, and pre/post-flag runs are different populations that must not be
pooled. Applying a post-flag threshold to pre-flag measurements would be exactly
the mixing error that manufactured the 2026-08-03 "C2 collapse". Reopening C2
requires re-running the LTN control post-flag too -- named here as the follow-on,
not smuggled in as a conclusion.
"""
import json
import os
import sys

import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths  # noqa: E402

# A — six runs of seed 42, determinism OFF. Verified to reproduce the documented
# floor exactly (SD 0.02222, range 0.0621), which is how this population was
# identified rather than guessed.
PREFLAG_FIXED = ["cnn_paper_logodds", "cnn_noise_r1", "cnn_noise_r2",
                 "cnn_noise_r3", "cnn_noise_r4", "cnn_repro_s42"]

# B — the pre-flag n=6 seed sweep (log-odds rescored, as published).
PREFLAG_SEEDS = [f"cnn_paper_s{s}_logodds" for s in (43, 44, 45, 46, 47)]
PREFLAG_SEEDS = ["cnn_paper_logodds"] + PREFLAG_SEEDS

# C — post-flag. Seeds 42/43/44 already exist from C4's log1p arm: identical
# configuration to a plain cnn_paper run (FEATURE_TRANSFORM=log1p IS the config
# default), verified by c4_log1p_s42 == det_verify_a to twelve decimals.
POSTFLAG = [f"c4_log1p_s{s}" for s in (42, 43, 44)] + \
           [f"postdet_s{s}" for s in (45, 46, 47)]

MACRO = "macro_zd_pr_auc"
DOC_FLOOR = 0.0222


def load(names, idx, required=True):
    out = {}
    for n in names:
        r = idx.get(n)
        if r is None:
            if required:
                print(f"  ⚠️  MISSING run: {n}")
            continue
        out[n] = float(r["metrics"][MACRO])
    return out


def sd(v):
    return float(np.std(list(v), ddof=1))


def main():
    p = os.path.join(paths.METADATA, "runs.jsonl")
    rows = [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
    idx = {}
    for r in rows:
        idx[r["name"]] = r          # last write wins

    A = load(PREFLAG_FIXED, idx)
    B = load(PREFLAG_SEEDS, idx)
    C = load(POSTFLAG, idx)

    print("=" * 92)
    print("VARIANCE DECOMPOSITION — what is this project's uncertainty actually made of?")
    print("=" * 92)

    for lbl, d, desc in (("A", A, "pre-flag,  seed FIXED  -> nondeterminism only"),
                         ("B", B, "pre-flag,  seed VARIES -> nondeterminism + seed"),
                         ("C", C, "post-flag, seed VARIES -> SEED ONLY")):
        if not d:
            print(f"\n  {lbl}  {desc}\n     (no runs found)")
            continue
        v = np.array(list(d.values()))
        print(f"\n  {lbl}  {desc}")
        print(f"     n={len(v)}  mean {v.mean():.4f}  SD {sd(v):.4f}  "
              f"range [{v.min():.4f}, {v.max():.4f}]  spread {v.max()-v.min():.4f}")
        for k, x in d.items():
            print(f"        {k:<26} {x:.4f}")

    if len(A) >= 2:
        print(f"\n  Sanity: A reproduces the documented floor SD {DOC_FLOOR} "
              f"-> measured {sd(A.values()):.4f}  "
              f"{'✅' if abs(sd(A.values())-DOC_FLOOR) < 0.001 else '🔴 MISMATCH'}")

    if len(C) < 6:
        print(f"\n  ⏳ Post-flag population incomplete ({len(C)}/6). "
              f"Re-run once seeds 45/46/47 finish.")
        return

    sA, sB, sC = sd(A.values()), sd(B.values()), sd(C.values())

    # ---------------- P1 ----------------
    print("\n" + "=" * 92)
    print("P1 — is post-flag seed SD materially below the 0.0222 floor?")
    print("=" * 92)
    print(f"  nondeterminism (A) SD : {sA:.4f}")
    print(f"  SEED ONLY      (C) SD : {sC:.4f}")
    print(f"  ratio A/C             : {sA/sC:.1f}x")
    # F-test on variances. Two independent samples, both n=6 -> df 5,5.
    F = (sA ** 2) / (sC ** 2)
    pF = 2 * min(stats.f.cdf(F, len(A) - 1, len(C) - 1),
                 1 - stats.f.cdf(F, len(A) - 1, len(C) - 1))
    print(f"  F({len(A)-1},{len(C)-1}) = {F:.2f}   p = {pF:.4f}")
    p1 = sC < 0.010
    print(f"\n  ==> P1 {'CONFIRMED' if p1 else 'FALSIFIED'} (SD {sC:.4f} vs the 0.010 line "
          f"fixed in advance)")
    if p1:
        print("      The dominant source of this project's uncertainty was NOT the seed.")
        print("      It was thread-scheduling nondeterminism, and determinism.enable()")
        print("      has removed it.")
    else:
        print("      C4's n=3 estimate was a small-sample artifact. The existing")
        print("      threshold stands, and that is a useful negative result.")

    # ---------------- P2 ----------------
    print("\n" + "=" * 92)
    print("P2 — does the withdrawn 'session effect' reproduce with determinism ON?")
    print("=" * 92)
    seeds = np.array([42, 43, 44, 45, 46, 47])
    pre = np.array([B[n] for n in PREFLAG_SEEDS])
    post = np.array([C[n] for n in POSTFLAG])
    rho_pre, _ = stats.spearmanr(seeds, pre)
    rho_post, ppost = stats.spearmanr(seeds, post)
    print(f"  pre-flag  macro vs seed number : rho = {rho_pre:+.3f}   {pre.round(4).tolist()}")
    print(f"  post-flag macro vs seed number : rho = {rho_post:+.3f}   {post.round(4).tolist()}")
    p2 = rho_post > -0.9
    print(f"\n  ==> P2 {'CONFIRMED' if p2 else 'FALSIFIED'} — the monotonic decline "
          f"{'does NOT' if p2 else 'DOES'} reproduce")
    if p2:
        print("      The pre-flag decline tracked RUN ORDER, not seed number. Pinning")
        print("      threads removed it. The 'session/environment effect' asserted and")
        print("      withdrawn on 2026-08-03 now has a direct experimental answer:")
        print("      it was nondeterminism under CPU contention.")

    # ---------------- P3 ----------------
    print("\n" + "=" * 92)
    print("P3 — is the decomposition internally consistent?")
    print("=" * 92)
    pred = float(np.sqrt(sA ** 2 + sC ** 2))
    print(f"  predicted B = sqrt(A^2 + C^2) = sqrt({sA:.4f}^2 + {sC:.4f}^2) = {pred:.4f}")
    print(f"  measured  B                   = {sB:.4f}")
    ratio = sB / pred
    p3 = 0.6 <= ratio <= 1.6
    print(f"  ratio measured/predicted      = {ratio:.2f}")
    print(f"\n  ==> P3 {'CONFIRMED' if p3 else 'FALSIFIED'} (an SD estimate at n=6 carries "
          f"~30% relative error, so 0.6–1.6 is the consistency band)")

    # ---------------- consequence ----------------
    print("\n" + "=" * 92)
    print("WHAT THIS LICENSES — AND WHAT IT DOES NOT")
    print("=" * 92)
    thr_old = 2 * (DOC_FLOOR / np.sqrt(6)) * np.sqrt(2)
    thr_new = 2 * (sC / np.sqrt(6)) * np.sqrt(2)
    print(f"  threshold from the OLD floor (SD {DOC_FLOOR}, n=6) : {thr_old:.4f}  "
          f"(the ~0.0256 in use)")
    print(f"  threshold from POST-FLAG seed SD ({sC:.4f}, n=6)   : {thr_new:.4f}")
    print(f"\n  🔴 THIS DOES NOT REOPEN C2. C2's +0.0204 was measured PRE-FLAG on both")
    print( "     sides. Pre- and post-flag runs are different populations; applying a")
    print( "     post-flag threshold to pre-flag numbers is exactly the mixing error")
    print( "     that manufactured the 2026-08-03 'C2 collapse'. C2 STAYS RETRACTED.")
    print( "  ➡️  To reopen it: re-run the LTN control post-flag at n=6 and compare")
    print( "     within the post-flag population. That is the follow-on experiment.")
    print(f"\n  ⚠️  The data-split SD (0.0228) is UNAFFECTED by any of this. It is a")
    print( "     separate, independent source, so an ABSOLUTE number still carries")
    print(f"     sqrt(0.0228^2 + {sC:.4f}^2) = {np.sqrt(0.0228**2 + sC**2):.4f}, not {thr_new:.4f}.")
    print( "     Determinism tightened COMPARISONS on a shared split. It did nothing")
    print( "     for the uncertainty on a single quoted value.")

    RES = {
        "A_preflag_fixed_seed": {"runs": A, "sd": sA, "n": len(A)},
        "B_preflag_varying_seed": {"runs": B, "sd": sB, "n": len(B)},
        "C_postflag_varying_seed": {"runs": C, "sd": sC, "n": len(C)},
        "P1": {"prediction": "post-flag seed SD < 0.010", "sd": sC,
               "F": float(F), "p": float(pF), "confirmed": bool(p1)},
        "P2": {"rho_preflag": float(rho_pre), "rho_postflag": float(rho_post),
               "confirmed": bool(p2)},
        "P3": {"predicted_B": pred, "measured_B": sB, "ratio": float(ratio),
               "confirmed": bool(p3)},
        "threshold_old": float(thr_old), "threshold_postflag": float(thr_new),
        "absolute_number_uncertainty": float(np.sqrt(0.0228 ** 2 + sC ** 2)),
        "c2_reopened": False,
    }
    outp = os.path.join(paths.METADATA, "noise_postdet.json")
    with open(outp, "w", encoding="utf-8") as f:
        json.dump(RES, f, indent=1)
    print(f"\nwrote {outp}")
    print("DONE (noise_postdet)")


if __name__ == "__main__":
    main()

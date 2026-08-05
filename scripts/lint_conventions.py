"""
lint_conventions.py — mechanical enforcement of this repo's conventions.

WHY THIS EXISTS
---------------
On 2026-08-03 the same latent bug (`open()` with no explicit encoding → cp1252 on
Windows) was found and fixed **three separate times** in one session — `config.py`,
`tracking.py`, `dashboard_server.py` — because each was treated as an incident
rather than as an instance of a *class*. Separately, the heartbeat-monitor rule in
CLAUDE.md lapsed on six long-running jobs.

Conventions written as prose in a long file depend on a human (or a model)
remembering them at exactly the right moment. This script converts the mechanical
subset into something that fails loudly instead.

**Run it at the end of every session, and after any refactor:**

    python scripts/lint_conventions.py          # report
    python scripts/lint_conventions.py --strict # exit 1 on any FAIL (for CI)

Each check names the incident that motivated it, so nobody has to re-derive why.
"""
import os
import re
import sys
import json
import glob
import collections

import paths

ROOT = paths.ROOT
SCRIPTS = os.path.join(ROOT, "scripts")
STRICT = "--strict" in sys.argv
FAILURES, WARNINGS = [], []


def _py_files():
    return sorted(glob.glob(os.path.join(SCRIPTS, "*.py")))


def _read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def check(name, motivation):
    def deco(fn):
        print(f"\n[{name}]")
        print(f"  why: {motivation}")
        try:
            bad = fn()
        except Exception as e:  # a broken check must not mask the others
            print(f"  ERROR running check: {type(e).__name__}: {e}")
            WARNINGS.append(name)
            return fn
        if bad:
            print(f"  FAIL ({len(bad)}):")
            for b in bad[:12]:
                print(f"    - {b}")
            if len(bad) > 12:
                print(f"    ... and {len(bad)-12} more")
            FAILURES.append(name)
        else:
            print("  PASS")
        return fn
    return deco


# ---------------------------------------------------------------------------
@check("open-without-encoding",
       "cp1252 on Windows corrupts/crashes on non-ASCII. Found 3x in one session "
       "(config.py, tracking.py, dashboard_server.py) before being linted.")
def _c1():
    bad = []
    # Binary modes are legitimately exempt (pickle, np.load). Check the whole
    # LINE for a binary mode rather than trying to regex the arg list — the args
    # routinely contain nested calls like os.path.join(...), so a naive
    # `open\(([^)]*)\)` truncates at the inner paren and misses the mode.
    binary = re.compile(r"""['"][rwax]b\+?['"]""")
    for p in _py_files():
        for i, line in enumerate(_read(p).splitlines(), 1):
            s = line.strip()
            if "open(" not in line or "encoding" in line or s.startswith("#"):
                continue
            if binary.search(line):
                continue
            bad.append(f"{os.path.basename(p)}:{i}: {s[:90]}")
    return bad


@check("timestamp-bypass",
       "meta_*.csv Timestamp is D/M/YYYY AND 12-hour with no AM/PM. Naive parsing "
       "moved ALL 114,658 test rows. Must go through timeline.py.")
def _c2():
    bad = []
    for p in _py_files():
        if os.path.basename(p) in ("timeline.py", "preprocess.py", "preprocess_paper.py"):
            continue
        src = _read(p)
        if re.search(r"to_datetime\s*\(", src) and "timeline" not in src:
            bad.append(f"{os.path.basename(p)}: parses datetimes without importing timeline")
        if re.search(r'\[["\']Timestamp["\']\]', src) and "timeline" not in src:
            bad.append(f"{os.path.basename(p)}: reads a Timestamp column without timeline")
    return bad


@check("smoke-namespace",
       "Undertrained *_SUBSET output must not land in the real fusion-channel "
       "namespace; use paths.predictions_dir(tag).")
def _c3():
    bad = []
    for p in _py_files():
        src = _read(p)
        # Only scripts that HAVE a smoke mode can pollute the namespace. A script
        # with no *_SUBSET path writes real channels and is legitimately direct.
        if "SUBSET" not in src:
            continue
        for i, line in enumerate(src.splitlines(), 1):
            if "paths.PREDICTIONS" in line and "np.save" in line and "predictions_dir" not in line:
                bad.append(f"{os.path.basename(p)}:{i}: smoke-capable script writes to PREDICTIONS directly")
    return bad


@check("single-component-table",
       "Component status duplicated across 4 files caused the same drift error in "
       "3 consecutive sessions. STATUS.md is the single source of truth.")
def _c4():
    hits = []
    for p in glob.glob(os.path.join(ROOT, "**", "*.md"), recursive=True):
        if ".venv" in p:
            continue
        if re.search(r"^\| Component \| Status", _read(p), re.M):
            hits.append(os.path.relpath(p, ROOT))
    return [] if hits == ["docs\\STATUS.md" if os.sep == "\\" else "docs/STATUS.md"] \
        else [f"expected only docs/STATUS.md, found: {hits}"]


@check("script-count",
       "CLAUDE.md once said '22 scripts' 13 lines above saying '26'. Docs must "
       "match disk. And on 2026-08-05 this check PASSED on a wrong count: the old "
       "regex was `(\\d+) scripts`, which never matched the actual phrasing '40 "
       "Python scripts', so 9 undocumented scripts slid through. A mechanical "
       "check that cannot fire is worse than no check -- it buys false confidence.")
def _c5():
    n = len(_py_files())
    bad = []
    # Tolerate a qualifier between the number and the word ("40 scripts",
    # "40 Python scripts") -- the qualifier is what hid the original bug.
    # Constraints that matter: stay on ONE line (\s+ would span newlines and
    # match a numbered list item followed by `python scripts/foo.py`), and
    # reject `scripts/` so command lines are not counted as prose.
    pat = re.compile(r"(\d+)[ \t]+(?:Python[ \t]+)?scripts\b(?!/)", re.IGNORECASE)
    for rel in ("CLAUDE.md", "docs/scripts_reference.md"):
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            continue
        for m in pat.finditer(_read(p)):
            if int(m.group(1)) != n:
                bad.append(f"{rel}: says {m.group(0)!r}, disk has {n}")
    return bad


@check("undocumented-scripts",
       "The count sentence can be right while the file is still incomplete. On "
       "2026-08-05 scripts_reference.md documented 32 of 41 scripts -- the whole "
       "Phase-4/fusion/explainability toolchain was missing. Check membership, "
       "not just arithmetic.")
def _c5b():
    ref = os.path.join(ROOT, "docs", "scripts_reference.md")
    if not os.path.exists(ref):
        return ["docs/scripts_reference.md is missing"]
    src = _read(ref)
    missing = [os.path.basename(p) for p in _py_files()
               if os.path.basename(p) not in src]
    return [f"docs/scripts_reference.md: {name} is not documented"
            for name in missing]


@check("hardcoded-paths",
       "All artifact locations come from paths.py. preprocess.py once bypassed it "
       "and silently read the abandoned data dir.")
def _c6():
    bad = []
    for p in _py_files():
        if os.path.basename(p) == "paths.py":
            continue
        for i, line in enumerate(_read(p).splitlines(), 1):
            if line.strip().startswith("#"):
                continue
            if re.search(r'os\.path\.join\(\s*paths\.ROOT\s*,\s*["\'](data|models|outputs)', line):
                bad.append(f"{os.path.basename(p)}:{i}: builds a path from ROOT instead of a paths.* constant")
    return bad


@check("runs-jsonl-integrity",
       "The research record backs every published number. Wrong seeds / exact "
       "duplicates / missing schema all silently corrupt aggregation.")
def _c7():
    p = os.path.join(paths.METADATA, "runs.jsonl")
    if not os.path.exists(p):
        return ["runs.jsonl missing"]
    rows = [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
    bad = []
    for r in rows:
        m = re.search(r"_s(\d+)(?:_|$)", r["name"])
        if m and r.get("params", {}).get("seed") != int(m.group(1)):
            bad.append(f"wrong seed: {r['name']} has seed={r.get('params',{}).get('seed')}")
    missing = [r["name"] for r in rows if "schema" not in r]
    if missing:
        bad.append(f"{len(missing)} rows missing a schema version")
    sig = collections.Counter(
        json.dumps({"n": r["name"], "p": r.get("params"), "m": r.get("metrics")}, sort_keys=True)
        for r in rows)
    dupes = sum(v - 1 for v in sig.values() if v > 1)
    if dupes:
        bad.append(f"{dupes} exact-duplicate rows (run scripts/repair_runs_log.py --apply)")
    return bad


@check("launcher-suppresses-log-growth",
       "The heartbeat rule watches LOG GROWTH. A launcher that pipes a long job "
       "through tail/head buffers until EOF, so the log stays empty for the whole "
       "run and the monitor reports a false STALL. Happened 2026-08-03 with "
       "seed_sweep.sh — the rule was fixed, then a launcher broke its precondition.")
def _c9():
    bad = []
    for p in glob.glob(os.path.join(SCRIPTS, "*.sh")):
        # Join backslash continuations into LOGICAL lines before checking.
        # 2026-08-05: this check PASSED on verify_determinism.sh, which pipes a
        # training run through a bare `grep`, because the pipe sat on a
        # continuation line and the "python" token sat on the previous one --
        # so the two conditions could never be true of the same physical line
        # and the check was structurally unable to fire. Second check found
        # inert on the same day as the script-count regex; the shared lesson is
        # that a check must be tested against the code it is meant to catch.
        raw, logical, buf, start = _read(p).splitlines(), [], "", 1
        for i, line in enumerate(raw, 1):
            if not buf:
                start = i
            buf += " " + line.rstrip()
            if line.rstrip().endswith("\\"):
                buf = buf.rstrip("\\")
                continue
            logical.append((start, buf.strip()))
            buf = ""
        if buf:
            logical.append((start, buf.strip()))

        for i, s in logical:
            if s.startswith("#") or "python" not in s.lower():
                continue
            # tail/head buffer; grep --line-buffered is fine, plain grep is not
            if re.search(r"\|\s*(tail|head)\b", s):
                bad.append(f"{os.path.basename(p)}:{i}: pipes a job through tail/head "
                           f"(buffers to EOF, kills log-growth monitoring)")
            elif re.search(r"\|\s*grep\b", s) and "--line-buffered" not in s:
                bad.append(f"{os.path.basename(p)}:{i}: pipes through grep without "
                           f"--line-buffered")
    return bad


@check("gitignored-research-record",
       "outputs/metadata/ was gitignored, leaving the entire research record with "
       "no history or backup.")
def _c8():
    gi = _read(os.path.join(ROOT, ".gitignore"))
    bad = []
    if re.search(r"^outputs/metadata/\s*$", gi, re.M):
        bad.append("outputs/metadata/ is gitignored — the research record is unprotected")
    return bad


# ---------------------------------------------------------------------------
print("=" * 78)
print("CONVENTION LINT — mechanical checks for rules that have actually lapsed")
print("=" * 78)
for _n, _f in sorted(globals().items()):
    pass  # checks already ran at decoration time

print("\n" + "=" * 78)
if FAILURES:
    print(f"FAILED {len(FAILURES)} check(s): {', '.join(FAILURES)}")
else:
    print("ALL CHECKS PASS")
if WARNINGS:
    print(f"WARNINGS (check itself errored): {', '.join(WARNINGS)}")
print("=" * 78)
sys.exit(1 if (STRICT and FAILURES) else 0)

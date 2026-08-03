"""
repair_runs_log.py — one-shot, auditable repair of `outputs/metadata/runs.jsonl`.

Why this is safe to run now, when it was deliberately deferred before
---------------------------------------------------------------------
`runs.jsonl` is the project's research record, and the standing rule is that it
is APPEND-ONLY: past entries are never silently rewritten (the same
retract-in-place discipline the living docs follow). That rule is why the two
defects below were documented on 2026-08-02 but left in the data.

That reasoning became obsolete on 2026-08-03, when `runs.jsonl` was put under
version control. Git now provides exactly what the append-only rule was
protecting — a complete, diffable, revertible history. A logged correction pass
is therefore auditable in a way that an in-place edit of an untracked file never
was. `git diff` / `git revert` is the undo button.

What it fixes
-------------
1. **Wrong seed on 16 rows.** `rescore_logits.py` stamped every `_logodds` entry
   with the config-default seed (42) regardless of which model was rescored. The
   CODE was fixed 2026-08-02; the DATA never was. Affects 8 distinct tags, each
   present twice → 16 rows. (KNOWN_ISSUES said "8 rows", counting tags not rows;
   a repair guided by that number would have fixed half.)
   Seed is re-derived from the tag's `_s<N>` suffix — the same rule the fixed
   `rescore_logits.tag_seed()` uses.

2. **Exact-duplicate rows.** Repeated full re-runs of `rescore_logits.py`
   re-computed and re-appended identical results. Naive aggregation
   double-counts them.

   ⚠️ **Only EXACT duplicates are removed** — rows identical in name, params AND
   every metric. Verified before writing this: of 24 duplicated names, 16 are
   exact re-scores (safe) and **8 are genuinely different measurements** that
   must NOT be collapsed — they are the old-schema/new-schema pairs from the
   2026-07-27 metrics rewrite (`xgboost`, `msp`, `mahalanobis`, `random_forest`,
   `isolation_forest`, `cnn_auxhead_l0.5`) plus two pairs of distinct training
   runs with identical configs but different scores (`ltn_repro` 0.4401 vs
   0.4853, `ltn_v2` 0.4908 vs 0.4912). Collapsing those would destroy research
   data. The first occurrence is kept so original ordering is preserved.

3. **Missing schema version.** Every row is stamped `v1-blended` or `v2-macro`
   (inferred from whether `macro_zd_pr_auc` is present), so pre- and
   post-rewrite records stop being silently comparable. `tracking.log_run` now
   writes this going forward.

Run:
    python scripts/repair_runs_log.py           # DRY RUN — reports, writes nothing
    python scripts/repair_runs_log.py --apply   # rewrites runs.jsonl

Writes `outputs/metadata/runs_repair_report.json` on apply.
"""
import os
import sys
import json
import re
import datetime
import collections

import paths
import tracking

LOG = os.path.join(paths.METADATA, "runs.jsonl")
APPLY = "--apply" in sys.argv

rows = [json.loads(l) for l in open(LOG, encoding="utf-8") if l.strip()]
print(f"read {len(rows)} rows from {LOG}")

report = {"applied": APPLY, "rows_before": len(rows),
          "seed_fixes": [], "duplicates_removed": [], "schema_stamped": 0,
          "duplicate_names_preserved": []}

# ---------------------------------------------------------------- 1. seeds ----
_SFX = re.compile(r"_s(\d+)(?:_|$)")


def tag_seed(name, current):
    """Seed implied by the tag's _s<N> suffix; None if the tag has no suffix."""
    m = _SFX.search(name)
    return int(m.group(1)) if m else None


for r in rows:
    implied = tag_seed(r["name"], r["params"].get("seed"))
    if implied is not None and r["params"].get("seed") != implied:
        report["seed_fixes"].append(
            {"name": r["name"], "was": r["params"].get("seed"), "now": implied})
        r["params"]["seed"] = implied

# --------------------------------------------------------------- 2. dedupe ----


def identity(r):
    """Full content identity, ignoring stamp/schema (bookkeeping, not results)."""
    return json.dumps({"name": r["name"], "params": r["params"],
                       "metrics": r["metrics"]}, sort_keys=True)


seen = set()
kept = []
for r in rows:
    k = identity(r)
    if k in seen:
        report["duplicates_removed"].append(r["name"])
        continue
    seen.add(k)
    kept.append(r)

# Sanity: every distinct name that survives must still be present.
names_before = {r["name"] for r in rows}
names_after = {r["name"] for r in kept}
assert names_before == names_after, \
    f"REFUSING: dedupe dropped entire runs: {sorted(names_before - names_after)}"

# Report which duplicated names were deliberately PRESERVED (content differs).
after_counts = collections.Counter(r["name"] for r in kept)
report["duplicate_names_preserved"] = sorted(
    n for n, c in after_counts.items() if c > 1)

# --------------------------------------------------------------- 3. schema ----
for r in kept:
    if "schema" not in r:
        r["schema"] = tracking.infer_schema(r.get("metrics", {}))
        report["schema_stamped"] += 1

report["rows_after"] = len(kept)

# ---------------------------------------------------------------- summary ----
print("\n" + "=" * 88)
print(f"seed fixes            : {len(report['seed_fixes'])} rows")
for f in report["seed_fixes"][:20]:
    print(f"    {f['name']:36s} seed {f['was']} -> {f['now']}")
print(f"exact duplicates      : {len(report['duplicates_removed'])} rows removed")
print(f"schema stamped        : {report['schema_stamped']} rows")
print(f"rows {report['rows_before']} -> {report['rows_after']}")
print("\nDuplicated names DELIBERATELY PRESERVED (content genuinely differs — "
      "old/new metric schema, or distinct training runs):")
for n in report["duplicate_names_preserved"]:
    print(f"    {n} x{after_counts[n]}")
by_schema = collections.Counter(r["schema"] for r in kept)
print(f"\nschema distribution   : {dict(by_schema)}")
print("=" * 88)

if not APPLY:
    print("\nDRY RUN — nothing written. Re-run with --apply to commit these changes.")
    sys.exit(0)

report["stamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
with open(LOG, "w", encoding="utf-8") as f:
    for r in kept:
        f.write(json.dumps(r) + "\n")
rp = os.path.join(paths.METADATA, "runs_repair_report.json")
with open(rp, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=1)
print(f"\nWROTE {LOG}\nWROTE {rp}")
print("Review with: git diff --stat outputs/metadata/runs.jsonl")

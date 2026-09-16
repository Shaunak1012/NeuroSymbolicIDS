"""
Lightweight experiment tracker — appends one JSON line per run so the ablation
table self-assembles. (TensorBoard is used separately for epoch curves.)

    import tracking
    tracking.log_run("cnn_paper", {"protocol":"paper","seed":42},
                     {"pr_auc": 0.97, "zd_pr_auc": 0.61})

Read all runs with tracking.load_runs() -> list[dict].

`outputs/metadata/runs.jsonl` is the project's research record and is
**version-controlled** (since 2026-08-03) — it backs every number in
docs/STATUS.md. Treat it as append-only in normal use; corrections go through
`scripts/repair_runs_log.py`, which is auditable and reversible via git.

Three defects fixed 2026-08-03
------------------------------
1. **No schema version.** Records written before the 2026-07-27 metrics.py
   rewrite carry only the blended `zd_pr_auc`; later ones carry per-family +
   macro. Nothing marked which was which, so a naive read compared incomparable
   numbers. Every record now carries `schema`.
2. **`stamp` was always empty.** It defaulted to "" and no caller ever passed
   one, so all 97 existing rows have no time information at all — impossible to
   order runs or tell a re-run from an original. Now auto-populated (UTC ISO-8601).
3. **No explicit encoding.** `open(_LOG, "a")` / `open(_LOG)` used the platform
   default, which is cp1252 on Windows — so a single non-ASCII character in a
   class name (CIC-IDS2017 labels contain them) would raise UnicodeEncodeError
   on write, or mojibake/crash on read. Same bug class that broke config.py.

Which score array (added 2026-09-16, audit F-20)
------------------------------------------------
The CNN channels exist twice: `y_prob_<tag>_test.npy` (raw probability) and
`y_prob_<tag>_logodds_test.npy` (re-scored in float64 by `rescore_logits.py`).
They rank almost identically but break ties differently, so they disagree in the
FOURTH decimal (s43: macro 0.6355 raw vs 0.6353 log-odds; Bot 0.0245 vs 0.0241).
The project quotes four decimals, and the flagship scripts do not agree on which
family they read: fusion_kg / significance / ablation / comparability read the
log-odds arrays, while ksweep_fusion / fusion_weight / operational_best /
best_config read the raw ones. Every record therefore now carries `scoring`
("raw" unless the caller says otherwise), and a 4-dp number in a doc should be
traceable to one family, not a mixture.
"""
import os
import json
import datetime
import paths

_LOG = os.path.join(paths.METADATA, "runs.jsonl")

# Bump when the METRICS dict shape changes in a way that makes old rows
# incomparable. Consumers should filter on this rather than probing for keys.
#   v1-blended  : pre-2026-07-27, only `zd_pr_auc` (size-weighted mixture)
#   v2-macro    : per-family PR-AUC + macro over powered families (the headline)
SCHEMA = "v2-macro"


def infer_schema(metrics: dict) -> str:
    """Classify a record written before `schema` existed."""
    return "v2-macro" if "macro_zd_pr_auc" in metrics else "v1-blended"


def log_run(name, params: dict, metrics: dict, stamp: str = None):
    if not stamp:
        stamp = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    params = dict(params)
    params.setdefault("scoring", "raw")      # audit F-20: which score array
    rec = {"name": name, "stamp": stamp, "schema": SCHEMA,
           "params": params, "metrics": metrics}
    with open(_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


def load_runs(schema: str = None):
    """All runs, newest last. Pass schema='v2-macro' to exclude pre-rewrite rows."""
    if not os.path.exists(_LOG):
        return []
    with open(_LOG, encoding="utf-8") as f:
        rows = [json.loads(l) for l in f if l.strip()]
    for r in rows:
        r.setdefault("schema", infer_schema(r.get("metrics", {})))
    if schema:
        rows = [r for r in rows if r["schema"] == schema]
    return rows

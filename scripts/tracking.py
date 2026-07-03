"""
Lightweight experiment tracker — appends one JSON line per run so the ablation
table self-assembles. (TensorBoard is used separately for epoch curves.)

    import tracking
    tracking.log_run("cnn_paper", {"protocol":"paper","seed":42},
                     {"pr_auc": 0.97, "zd_pr_auc": 0.61})

Read all runs with tracking.load_runs() -> list[dict].
"""
import os
import json
import paths

_LOG = os.path.join(paths.METADATA, "runs.jsonl")


def log_run(name, params: dict, metrics: dict, stamp: str = ""):
    rec = {"name": name, "stamp": stamp, "params": params, "metrics": metrics}
    with open(_LOG, "a") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


def load_runs():
    if not os.path.exists(_LOG):
        return []
    with open(_LOG) as f:
        return [json.loads(l) for l in f if l.strip()]

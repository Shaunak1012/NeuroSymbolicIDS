"""
dashboard_server.py — local LIVE ops console for Phase 2.

This is the real-time counterpart to the static published Artifact
(see docs/DASHBOARD.md): a tiny localhost HTTP server that reads actual
machine state on every poll — CPU/RAM, git branch/dirty count, running
training processes, the tail of the most recently touched log file, and
runs.jsonl — and a single HTML page that polls it. A published Artifact
cannot do this (no capability reaches local machine state); this can,
because it never leaves localhost.

Run:
    .venv\\Scripts\\python.exe scripts\\dashboard_server.py [--port 8787]

View: through the Browser pane (preview_start), not by publishing this
file anywhere. Binds to 127.0.0.1 only.
"""
import os
import sys
import json
import glob
import time
import argparse
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import paths

try:
    import psutil
except ImportError:
    psutil = None

ROOT = paths.ROOT
TRAIN_SCRIPTS = {
    "ltn_paper.py", "ltn.py", "cnn3.py", "cnn_paper.py", "cnn_auxhead_paper.py",
    "baselines.py", "skyline_oracle.py", "rescore_logits.py",
    "fusion_beaconlike.py", "preprocess.py", "eval.py", "behavior.py",
}


# ---------------------------------------------------------------- data ----
def git(*args):
    try:
        return subprocess.check_output(
            ["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return None


def git_status():
    branch = git("rev-parse", "--abbrev-ref", "HEAD") or "?"
    porcelain = git("status", "--porcelain") or ""
    dirty = len([l for l in porcelain.splitlines() if l.strip()])
    last_commit = git("log", "-1", "--format=%h %s")
    return {"branch": branch, "dirty": dirty, "last_commit": last_commit}


def cpu_ram():
    if psutil is None:
        return {"available": False}
    vm = psutil.virtual_memory()
    return {
        "available": True,
        "cpu_pct": psutil.cpu_percent(interval=0.15),
        "ram_pct": vm.percent,
        "ram_used_gb": round(vm.used / 1e9, 1),
        "ram_total_gb": round(vm.total / 1e9, 1),
    }


def running_training_processes():
    if psutil is None:
        return {"available": False, "processes": []}
    procs = []
    for p in psutil.process_iter(["pid", "cmdline", "create_time", "memory_info"]):
        try:
            cmd = p.info["cmdline"] or []
        except Exception:
            continue
        script = next((os.path.basename(c) for c in cmd if c.endswith(".py")), None)
        if script not in TRAIN_SCRIPTS:
            continue
        try:
            mem_mb = p.info["memory_info"].rss / 1e6 if p.info["memory_info"] else 0
            elapsed = time.time() - p.info["create_time"]
            procs.append({
                "pid": p.info["pid"],
                "script": script,
                "cmd": " ".join(cmd),
                "cpu_pct": p.cpu_percent(interval=None),
                "mem_mb": round(mem_mb, 1),
                "elapsed_s": round(elapsed, 0),
            })
        except Exception:
            continue
    return {"available": True, "processes": procs}


def _decode_best_effort(raw, n, _min_run=8):
    """Decode a PowerShell `*>>` batch log, which is MIXED-ENCODING by construction.

    These files interleave **UTF-8** (the Python subprocess's own stdout, passed
    through) with **UTF-16LE** (PowerShell's `Add-Content` header lines) in a
    single file with no marker — see docs/KNOWN_ISSUES.md.

    🔴 The previous whole-buffer approach could not work, and was visibly broken in
    the live dashboard (2026-08-03): it tried `utf-8` first, which **raises** at the
    first UTF-16LE section, then fell through to `utf-16-le`, which decodes the
    whole file — rendering the *majority* UTF-8 content as CJK mojibake
    (`㴽‽低䕖呌彙䕓䑅` for what is actually `=== NOVELTY_SEED=42 ===`).
    Any single codec is guaranteed to mangle one of the two halves.

    Fix: segment on null-byte density and decode each run with its own codec.
    UTF-8 never contains 0x00, so a byte pair `(non-zero, 0x00)` is a reliable
    UTF-16LE marker. `_min_run` avoids flapping on incidental byte pairs.
    """
    out, i, N = [], 0, len(raw)

    def _is_u16_at(k):
        return k + 1 < N and raw[k] != 0 and raw[k + 1] == 0

    while i < N:
        if _is_u16_at(i):
            j = i
            while _is_u16_at(j):
                j += 2
            if j - i >= _min_run:                      # genuine UTF-16LE run
                out.append(raw[i:j].decode("utf-16-le", errors="replace"))
                i = j
                continue
        j = i + 1
        while j < N and not (_is_u16_at(j) and j + _min_run <= N):
            j += 1
        out.append(raw[i:j].decode("utf-8", errors="replace"))
        i = j
    return "".join(out).splitlines()[-n:]


def latest_log_tail(n=40):
    logs = glob.glob(os.path.join(ROOT, "outputs", "*.log"))
    if not logs:
        return {"file": None, "mtime": None, "lines": []}
    latest = max(logs, key=os.path.getmtime)
    with open(latest, "rb") as f:
        raw = f.read()
    return {
        "file": os.path.basename(latest),
        "mtime": os.path.getmtime(latest),
        "lines": _decode_best_effort(raw, n),
    }


def runs_summary():
    path = os.path.join(paths.METADATA, "runs.jsonl")
    if not os.path.exists(path):
        return []
    out = []
    # encoding is explicit: the platform default is cp1252 on Windows, which
    # corrupts or crashes on any non-ASCII class name. Same bug class that broke
    # config.py and tracking.py (fixed 2026-08-03).
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def build_status():
    return {
        "ts": time.time(),
        "system": cpu_ram(),
        "git": git_status(),
        "training": running_training_processes(),
        "log": latest_log_tail(),
        "runs": runs_summary(),
    }


# ---------------------------------------------------------------- HTML ----
PAGE = """<!doctype html>
<meta charset="utf-8">
<title>NeuroSymbolic-IDS — LIVE Console</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root {
    --accent: #c9793f; --accent-dim: #c9793f33;
    --status-good: #10937d; --status-good-bg: #10937d1a;
    --status-warn: #c9a222; --status-warn-bg: #c9a2221a;
    --status-critical: #c23b52; --status-critical-bg: #c23b521a;
    --status-neutral: #6b7280; --status-neutral-bg: #6b72801a;
    --bg: #f6f4ef; --surface: #ffffff; --surface-2: #efece3; --border: #e0ddd3;
    --text-primary: #1c1e22; --text-secondary: #52565e; --text-muted: #90928f;
    --shadow: 0 1px 2px rgba(30,25,15,.06), 0 4px 16px rgba(30,25,15,.05);
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #12151b; --surface: #191d25; --surface-2: #20242e; --border: #2a2f3a;
      --text-primary: #e9e7e0; --text-secondary: #a5a8b0; --text-muted: #676b74;
      --status-good: #10937d; --status-good-bg: #10937d33;
      --status-warn: #ad8a1e; --status-warn-bg: #ad8a1e33;
      --status-critical: #c23b52; --status-critical-bg: #c23b5233;
      --status-neutral: #868a93; --status-neutral-bg: #868a9326;
      --shadow: 0 1px 2px rgba(0,0,0,.3), 0 8px 24px rgba(0,0,0,.35);
    }
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--text-primary);
    font: 14px/1.5 -apple-system,"Segoe UI",system-ui,sans-serif; padding: 24px 20px 60px; }
  .wrap { max-width: 1180px; margin: 0 auto; display: flex; flex-direction: column; gap: 16px; }
  code, .mono { font-family: ui-monospace,"Cascadia Code","SF Mono",Consolas,monospace; font-variant-numeric: tabular-nums; }
  header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; }
  h1 { font: 600 19px/1 ui-monospace,Consolas,monospace; margin: 0; letter-spacing: -.01em; }
  h1 .accent { color: var(--accent); }
  .live-badge { display: inline-flex; align-items: center; gap: 6px; font-size: 12px;
    padding: 4px 10px; border-radius: 999px; border: 1px solid var(--border); background: var(--surface); }
  .live-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--status-good); }
  .live-badge.ok .live-dot { animation: pulse 1.6s ease-in-out infinite; }
  .live-badge.stalled { border-color: var(--status-critical); color: var(--status-critical); }
  .live-badge.stalled .live-dot { background: var(--status-critical); animation: none; }
  @media (prefers-reduced-motion: reduce) { .live-dot { animation: none !important; } }
  @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: .35; } }
  #reconnect { font: inherit; font-size: 12px; padding: 4px 10px; border-radius: 999px;
    border: 1px solid var(--border); background: var(--surface-2); color: var(--text-primary); cursor: pointer; }
  #reconnect:hover { border-color: var(--accent); color: var(--accent); }
  .card { background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
    box-shadow: var(--shadow); padding: 16px 18px; }
  .card h2 { font: 600 11px/1 ui-monospace,Consolas,monospace; text-transform: uppercase;
    letter-spacing: .07em; color: var(--text-muted); margin: 0 0 12px; }
  .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px,1fr)); gap: 12px; }
  .stat { display: flex; flex-direction: column; gap: 3px; }
  .stat .label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: .05em; }
  .stat .value { font: 600 20px/1.2 ui-monospace,Consolas,monospace; }
  .chip { display: inline-flex; align-items: center; gap: 5px; font-size: 12px; padding: 2px 8px;
    border-radius: 999px; width: fit-content; }
  .chip.good { color: var(--status-good); background: var(--status-good-bg); }
  .chip.warn { color: var(--status-warn); background: var(--status-warn-bg); }
  .chip.critical { color: var(--status-critical); background: var(--status-critical-bg); }
  .chip.neutral { color: var(--status-neutral); background: var(--status-neutral-bg); }
  table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
  th { text-align: left; color: var(--text-muted); font-weight: 600; font-size: 11px;
    text-transform: uppercase; letter-spacing: .04em; padding: 6px 8px; border-bottom: 1px solid var(--border); }
  td { padding: 6px 8px; border-bottom: 1px solid var(--border); }
  tr:last-child td { border-bottom: none; }
  .empty { color: var(--text-muted); font-size: 12.5px; padding: 4px 0; }
  pre.log { margin: 0; max-height: 320px; overflow: auto; background: var(--surface-2);
    border: 1px solid var(--border); border-radius: 8px; padding: 10px 12px;
    font-family: ui-monospace,Consolas,monospace; font-size: 12px; white-space: pre-wrap; word-break: break-word; }
  .log-meta { color: var(--text-muted); font-size: 11.5px; margin-bottom: 6px; }
  .table-wrap { overflow-x: auto; }
</style>
<div class="wrap">
  <header>
    <h1>NeuroSymbolic-IDS <span class="accent">●</span> LIVE Console</h1>
    <div style="display:flex; align-items:center; gap:10px;">
      <span id="badge" class="live-badge ok"><span class="live-dot"></span><span id="badge-text">connecting…</span></span>
      <button id="reconnect">↻ Reconnect now</button>
    </div>
  </header>

  <div class="card">
    <h2>System</h2>
    <div class="stat-grid" id="stat-grid"><div class="empty">loading…</div></div>
  </div>

  <div class="card">
    <h2>Training processes</h2>
    <div class="table-wrap"><table id="proc-table"><thead>
      <tr><th>PID</th><th>Script</th><th>CPU%</th><th>Mem</th><th>Elapsed</th></tr>
    </thead><tbody><tr><td class="empty" colspan="5">loading…</td></tr></tbody></table></div>
  </div>

  <div class="card">
    <h2>Latest log</h2>
    <div class="log-meta" id="log-meta">loading…</div>
    <pre class="log" id="log-body">loading…</pre>
  </div>

  <div class="card">
    <h2>Run history (runs.jsonl)</h2>
    <div class="table-wrap"><table id="runs-table"><thead>
      <tr><th>Run</th><th>Macro ZD PR-AUC</th><th>ZD PR-AUC</th><th>Saturated</th></tr>
    </thead><tbody><tr><td class="empty" colspan="4">loading…</td></tr></tbody></table></div>
  </div>
</div>
<script>
const POLL_MS = 4000;
let timer = null;

function fmtElapsed(s) {
  s = Math.round(s);
  if (s < 60) return s + 's';
  if (s < 3600) return Math.floor(s/60) + 'm ' + (s%60) + 's';
  return Math.floor(s/3600) + 'h ' + Math.floor((s%3600)/60) + 'm';
}
function fmtAgo(ts) {
  const s = Math.round(Date.now()/1000 - ts);
  if (s < 5) return 'just now';
  if (s < 60) return s + 's ago';
  return Math.floor(s/60) + 'm ago';
}
function chip(text, cls) { return `<span class="chip ${cls}">${text}</span>`; }

function renderStats(d) {
  const sys = d.system, git = d.git, training = d.training;
  const running = training.available ? training.processes.length : 0;
  const cells = [];
  if (sys.available) {
    cells.push(`<div class="stat"><div class="label">CPU</div><div class="value mono">${sys.cpu_pct.toFixed(0)}%</div></div>`);
    cells.push(`<div class="stat"><div class="label">RAM</div><div class="value mono">${sys.ram_pct.toFixed(0)}% <span style="font-size:11px;color:var(--text-muted)">(${sys.ram_used_gb}/${sys.ram_total_gb} GB)</span></div></div>`);
  } else {
    cells.push(`<div class="stat"><div class="label">CPU / RAM</div><div class="value">${chip('psutil not installed','warn')}</div></div>`);
  }
  cells.push(`<div class="stat"><div class="label">Branch</div><div class="value mono">${git.branch}</div>${git.dirty ? chip(git.dirty + ' uncommitted', 'warn') : chip('clean', 'good')}</div>`);
  cells.push(`<div class="stat"><div class="label">Active run</div><div class="value">${running ? chip(running + ' running', 'good') : chip('idle', 'neutral')}</div></div>`);
  document.getElementById('stat-grid').innerHTML = cells.join('');
}

function renderProcs(d) {
  const tb = document.querySelector('#proc-table tbody');
  const t = d.training;
  if (!t.available) { tb.innerHTML = '<tr><td class="empty" colspan="5">psutil not installed — no process visibility</td></tr>'; return; }
  if (!t.processes.length) { tb.innerHTML = '<tr><td class="empty" colspan="5">no training scripts currently running</td></tr>'; return; }
  tb.innerHTML = t.processes.map(p => `<tr>
    <td class="mono">${p.pid}</td><td class="mono">${p.script}</td>
    <td class="mono">${p.cpu_pct.toFixed(0)}%</td><td class="mono">${p.mem_mb.toFixed(0)} MB</td>
    <td class="mono">${fmtElapsed(p.elapsed_s)}</td></tr>`).join('');
}

function renderLog(d) {
  const l = d.log;
  document.getElementById('log-meta').textContent = l.file ? `${l.file} · updated ${fmtAgo(l.mtime)}` : 'no log files found in outputs/';
  document.getElementById('log-body').textContent = l.lines.length ? l.lines.join('\\n') : '(empty)';
  const body = document.getElementById('log-body');
  body.scrollTop = body.scrollHeight;
}

function renderRuns(d) {
  const tb = document.querySelector('#runs-table tbody');
  const runs = d.runs.slice().reverse();
  if (!runs.length) { tb.innerHTML = '<tr><td class="empty" colspan="4">no runs logged yet</td></tr>'; return; }
  tb.innerHTML = runs.map(r => {
    const m = r.metrics || {};
    const macro = m.macro_zd_pr_auc, zd = m.zd_pr_auc, sat = m.saturated;
    const fmt = v => (v === null || v === undefined) ? '—' : Number(v).toFixed(4);
    return `<tr><td class="mono">${r.name || '—'}</td><td class="mono">${fmt(macro)}</td><td class="mono">${fmt(zd)}</td>
      <td>${sat ? chip('saturated','critical') : chip('ok','good')}</td></tr>`;
  }).join('');
}

async function poll(manual) {
  try {
    const res = await fetch('/api/status', {cache: 'no-store'});
    if (!res.ok) throw new Error('status ' + res.status);
    const d = await res.json();
    renderStats(d); renderProcs(d); renderLog(d); renderRuns(d);
    const badge = document.getElementById('badge');
    badge.className = 'live-badge ok';
    document.getElementById('badge-text').textContent = 'live · updated ' + fmtAgo(d.ts);
  } catch (e) {
    const badge = document.getElementById('badge');
    badge.className = 'live-badge stalled';
    document.getElementById('badge-text').textContent = 'stalled — server unreachable';
  }
}
document.getElementById('reconnect').addEventListener('click', () => poll(true));
poll();
timer = setInterval(poll, POLL_MS);
</script>
"""


# --------------------------------------------------------------- server ---
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # keep stdout clean; the console itself is the feedback loop

    def do_GET(self):
        if self.path.startswith("/api/status"):
            body = json.dumps(build_status()).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        elif self.path in ("/", "/index.html"):
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8787)
    args = ap.parse_args()
    if psutil is None:
        print("[dashboard_server] WARNING: psutil not installed — CPU/RAM/process "
              "panels will show 'not installed'. `pip install psutil` to enable.")
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"[dashboard_server] live at http://127.0.0.1:{args.port}  (Ctrl+C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

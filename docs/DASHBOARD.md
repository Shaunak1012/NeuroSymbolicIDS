# Dashboard / "open preview" convention

> 🔴 Living document — keep this current whenever the dashboard changes.

## The convention

When the user says **"open preview"** (or equivalent — "show me the dashboard," "pull up the console"), Claude opens the **LIVE local console**, not the static Artifact snapshot. Concretely:

1. Start it: `preview_start` with `name: "phase2-dashboard"` (config lives in `.claude/launch.json`, runs `scripts/dashboard_server.py`).
2. That opens a Browser-pane tab at `http://localhost:8787`, polling real machine state every 4s.

The static Artifact link below still exists as a shareable, no-server-needed snapshot, but it is **not** what "open preview" means anymore.

**Static snapshot (for sharing outside a session):** https://claude.ai/code/artifact/70ae26e2-ffdc-4aaf-9381-0f7f6d57ccf1

## Status: live realtime — ✅ built (2026-07-29)

This was flagged as a gap in the previous version of this doc ("latest" was true, "live realtime" wasn't) and is now closed:

- **`scripts/dashboard_server.py`** — a localhost-only (`127.0.0.1`, not network-exposed) Python HTTP server, stdlib `http.server` + `psutil`. Serves a single HTML page and a polled `/api/status` JSON endpoint that reads **real** state on every request:
  - CPU% / RAM% via `psutil`
  - git branch + uncommitted-file count + last commit, via `git` subprocess calls against the repo root
  - Running training processes — scans for python processes whose command line matches a known pipeline script (`ltn_paper.py`, `cnn3.py`, etc.), reporting PID/CPU/mem/elapsed
  - Tail of whichever `outputs/*.log` file was modified most recently, decoded leniently to survive the mixed UTF-8/UTF-16LE encoding issue (see [KNOWN_ISSUES.md](KNOWN_ISSUES.md))
  - Full run history from `outputs/metadata/runs.jsonl` (macro zero-day PR-AUC, ZD PR-AUC, saturation flag)
- **The page** reuses the same validated status palette as the static Artifact (`#c9793f` accent, `#10937d`/`#c9a222`/`#c23b52` light-mode good/warn/critical, `#10937d`/`#ad8a1e`/`#c23b52` dark-mode) so the two feel like one product.
- **The "stalled" state is real, not decorative.** If a poll fails (server not running, crashed, etc.) the LIVE badge flips to a red "stalled — server unreachable" state, and the **Reconnect now** button forces an immediate retry rather than waiting for the next 4s tick. This directly answers the original ask ("add a refresh button so if it stalls I can click it") — the button now reflects genuine connectivity, not a fixed re-render of stale data.

**Dependency added:** `psutil==6.1.0`, installed in `.venv` and recorded in `requirements.txt` under a comment marking it dashboard-only (not part of the core ML pipeline).

**Verified 2026-07-29:** started via `preview_start`, screenshotted through the Browser pane — CPU/RAM/branch/uncommitted-count/log-tail/run-history all populated with real values (e.g. branch `main`, 4 uncommitted files, `p2_rescore3.log` tail, full `runs.jsonl` table sorted newest-first). Zero console errors. Stopped cleanly after verification.

## Starting it manually (outside the "open preview" phrase)

```bash
.venv/Scripts/python.exe scripts/dashboard_server.py --port 8787
```

Then open `http://localhost:8787` directly, or let Claude do it via `preview_start`/the Browser pane.

## Source files

- `scripts/dashboard_server.py` — the live server (repo-tracked, real source, not a generated artifact).
- `.claude/launch.json` — the `preview_start` config (`"phase2-dashboard"`).
- `<scratchpad>/phase2_console.html` — the static Artifact's HTML source. Session-scratchpad path, not committed (it's a generated snapshot, not source). A future session regenerating/editing it should recreate it there and republish to the **same URL** above via the Artifact tool's `url` parameter — never mint a new URL for what is conceptually the same snapshot.

## When to update which one

- **Palette, layout, or "what the dashboard looks like" changes** → edit both: `scripts/dashboard_server.py`'s embedded `PAGE` HTML (live) and `phase2_console.html` (static snapshot, republish after).
- **New live data source** (e.g. a future GPU panel, KG-build progress) → `scripts/dashboard_server.py` only; the static Artifact structurally cannot poll anything, so don't try to fake it there.
- **A finding worth freezing for external sharing** (e.g. a chart to send someone without repo access) → republish the static Artifact only.

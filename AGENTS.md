# AGENTS.md — pointer, deliberately not a copy

**Read [CLAUDE.md](CLAUDE.md) first and follow it exactly.** It is the one onboarding file for every
assistant working in this repository (Codex included): non-negotiables, current state, how to run the
pipeline, and the git conventions.

This file used to be a full copy of `CLAUDE.md`. By 2026-09-28 it already disagreed with the original
(it still cited a retracted result as the project's mechanism) — the same duplication defect that
non-negotiable #7 exists for. `scripts/lint_conventions.py` (`onboarding-single-source`) fails if this
file grows back into a copy.

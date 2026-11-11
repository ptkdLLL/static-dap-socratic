## 2.0.3-requirements — 2026-11-11

- Document the hard prerequisites: codebase_memory MCP and DAP MCP.
- Clarify that the plugin does not produce facts and does not install MCP servers.
- No code behavior changes.

## 2.0.2-isolation — 2026-11-11

- Remove the stage table and stage names from the installed plugin README.
- Skill remains an activation stub; stage content is injected one stage at a time.
- No code behavior changes.

## 2.0.1-fact-driven — 2026-11-11

- Public Chinese name: 事实驱动编程.
- README: prominent activation instructions.
- No code changes; display name and documentation update.

# Changelog

## 2.0.0-report-handoff — 2026-11-11

Initial public release.

- Six-stage workflow: research/plan → plan verification → change document → block evaluation → implementation → acceptance.
- One stage prompt at a time; future stages are not described in the current prompt.
- Stage report handoff with a per-stage token.
- Local fact ledger and report archive under `~/.zcode/methodology/`.
- Static + runtime evidence guidance, including `PASS-STATIC / BLOCKED / UNVERIFIED` statuses for block evaluation.
- Contextual exploration reminders for source grep / awk / sed / full-file reads.
- No tool denial, no report scoring, no telemetry.

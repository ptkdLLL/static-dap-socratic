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

## Unreleased

- Add `docs/fact-driven-programming.md`: a methodology paper (research draft) formalizing Fact-Driven Programming, the six-stage workflow, the distinction between topology constraints / process gates / outcome verification, and the two preliminary studies.
- Link the paper from the README documentation index and the introduction header.
- Add `docs/s1-symbol-exploration-experiment.md`: a desensitized S1 symbol-exploration experiment comparing the original S1 prompt with a small symbol-query discipline addition.
- Document that `codebase_memory` alone is not enough for C/C++: add `cscope` and `clang/clang++` prerequisites on the homepage, INSTALL, introduction, and plugin README.
- No code behavior changes.

## 2.0.8-case-study — 2026-11-11

- Add a desensitized real-task case study: PDF subsystem repair, with methodology summary, flow, and report screenshots on the homepage.
- No code behavior changes.

## 2.0.7-dap-libs — 2026-11-11

- Add the DAP dependency stack and limitation attribution: CodeLLDB/LLDB, debugpy, Node Inspector/CDP, native JDWP/JVMTI, netcoredbg, esbuild/tsx.
- Clarify that the documented limitations mostly come from these adapters/protocols, not from plugin-added semantics.
- No code behavior changes.

## 2.0.6-fallback — 2026-11-11

- Remove static reasoning from the runtime DAP fallback chain.
- If sandbox logs/probes/unit tests/logcat/DB/UI cannot provide the fact, stop and report to the user with what is missing and what is needed.
- Static reasoning is only for hypotheses/D-level inference, never runtime evidence.
- No code behavior changes.

## 2.0.5-sanitize — 2026-11-11

- Replace a project-specific thread name in `docs/dap-spec.md` with the generic `worker`.
- No code or behavior changes.

## 2.0.4-dap-spec — 2026-11-11

- Add `docs/dap-spec.md`: required DAP MCP contract, current capability matrix, known limitations (including Android/ART/JDWP), evidence rules, and fallback guidance.
- Link the DAP spec from README, INSTALL, plugin README, and introduction.
- No code behavior changes.

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

# Static + DAP Socratic

A stage-by-stage workflow assistant for AI coding agents. It breaks a complex coding task into six stages, gives the agent only the current stage, and waits for a stage report before moving on.

- Plugin: `static-dap-socratic`
- Version: `2.0.0-report-handoff`
- Paired skill: `plugin/static-dap-socratic/skills/static-dap-socratic/SKILL.md`
- License: MIT

## What it does

Complex coding tasks often fail in predictable ways:

- the agent starts editing before understanding the codebase;
- guesses are presented as verified facts;
- long tasks drift, skip steps, or lose the original goal;
- the user cannot see what was checked, what was changed, or what remains unverified.

This plugin addresses those problems with **staged task sheets + stage reports**:

1. the plugin sends only the current stage;
2. the agent does the work for that stage;
3. the agent writes a stage report and runs a handoff command;
4. the plugin records the report and sends the next stage.

The plugin does not write code, score the report, or approve/reject tool calls. It controls **when information arrives** and **what gets recorded**.

## Six stages

| Stage | What the agent does | Report |
|---|---|---|
| 1. Research & plan | Read the codebase map and real samples; write a plan | `REPORT-research.md` |
| 2. Plan verification | Verify the plan's key assumptions one by one | `REPORT-hypotheses.md` |
| 3. Change document | Write purpose, constraints, and the proposed code blocks | `REPORT-change.md` |
| 4. Block evaluation | For each block: check existing code, run small experiments/tests, confirm feasibility | `REPORT-blocks.md` |
| 5. Implementation | Apply the plan, build, install, test | `REPORT-landing.md` |
| 6. Acceptance | Verify scenario by scenario with actual evidence | `REPORT-acceptance.md` |

The agent only sees the current stage. Future stages are not described in the current prompt.

## Why it helps

- **Research before editing**: the first stages force a global view and assumption checks before code changes.
- **One thing at a time**: long tasks are less likely to drift or skip work.
- **Written stage reports**: progress is auditable; the user can review evidence and unverified boundaries.
- **Static + runtime evidence**: reports separate code-structure evidence from actual runtime evidence (debugger, logs, tests, small probes).
- **Honest unknowns**: items without evidence are marked `UNVERIFIED` instead of being presented as passed.
- **No approval loop**: the plugin does not block or deny tools; stage boundaries are driven by reports.

## Install

Add this repository root as a local marketplace in ZCode, install `static-dap-socratic`, then restart ZCode.

Manual install and troubleshooting: see [INSTALL.md](INSTALL.md).

## Activate

Include this phrase in the task prompt:

```text
基于静态工具与dap联合
```

The plugin starts with stage 1.

## Work loop

1. Read the current stage prompt.
2. Do the work for that stage.
3. Write the stage report.
4. Run the handoff command shown in the prompt:

```sh
python3 <plugin-root>/scripts/handoff.py --report REPORT-xxx.md --token <current-stage-token>
```

5. The plugin records the report and injects the next stage.
6. Repeat until `DONE`.

The token is issued by the plugin for the current stage. Reports are copied to `~/.zcode/methodology/reports/`, and handoff records are added to the local fact ledger.

## Privacy

- The plugin runs locally and does not send data to any external service.
- Stage reports and the fact ledger are stored under `~/.zcode/methodology/` on the local machine.
- Reports can contain project details. Do not commit them to a public repository.
- The plugin does not collect telemetry.

## Limitations

- The plugin does not guarantee correct code or a correct plan; it structures the process.
- The plugin does not parse or score reports; a thin report can still advance. Users should review the reports.
- Runtime evidence depends on the environment. On Android, debugger breakpoints on already-loaded Kotlin classes may not hit; reports should say so and use logs/DB/UI/probes instead.
- For small fixes or pure Q&A, the stage/report overhead is usually not worth it.

## Documentation

- [Introduction: design, usage, advantages](docs/introduction.md)
- [Field notes: two sanitized real-task case studies](docs/field-notes-two-tasks.md)

## License

MIT. See [LICENSE](LICENSE).

# Install / Activate / Uninstall

## 1. Recommended: add this repository as a local marketplace

This repository root is a local marketplace:

```text
.
├── marketplace.json
├── plugin/static-dap-socratic/
└── docs/
```

In ZCode's plugin/marketplace settings, add this directory as a local marketplace (directory source), then install `static-dap-socratic`.

Restart ZCode after installation so hooks and the skill reload.

## 2. Manual install

Copy the plugin into the installed cache:

```sh
mkdir -p ~/.zcode/cli/plugins/cache/static-dap-socratic/static-dap-socratic/2.0.0-report-handoff
rsync -a --delete ./plugin/static-dap-socratic/ \
  ~/.zcode/cli/plugins/cache/static-dap-socratic/static-dap-socratic/2.0.0-report-handoff/
```

Then point the plugin entry in `~/.zcode/cli/plugins/installed_plugins.json` at that path and make sure the plugin is enabled in `~/.zcode/cli/config.json`. Restart ZCode.

## 3. Activate

Send a task containing:

```text
基于静态工具与dap联合
```

The plugin injects stage 1 on `UserPromptSubmit`.

## 4. Stage loop

1. Read the current stage prompt.
2. Do the work.
3. Write the report named in the prompt.
4. Run:

```sh
python3 ~/.zcode/cli/plugins/cache/static-dap-socratic/static-dap-socratic/2.0.0-report-handoff/scripts/handoff.py \
  --report REPORT-xxx.md \
  --token <current-stage-token>
```

5. The plugin records the report and sends the next stage.
6. Repeat until `DONE`.

Report names:

- stage 1: `REPORT-research.md`
- stage 2: `REPORT-hypotheses.md`
- stage 3: `REPORT-change.md`
- stage 4: `REPORT-blocks.md`
- stage 5: `REPORT-landing.md`
- stage 6: `REPORT-acceptance.md`

## 5. Local state

```text
~/.zcode/methodology/
├── state/<session-hash>.json
├── facts/<session>.jsonl
├── tokens/<token>.json
├── handoff/<token>.json
└── reports/<token>/
```

Reports and the fact ledger stay local. They can contain project details; do not commit them to a public repository.

## 6. Uninstall / rollback

- Disable or uninstall `static-dap-socratic` in ZCode's plugin manager, or remove its cache directory.
- To roll back to a previous version, point the installed_plugins entry back to that version.
- `~/.zcode/methodology/` is not removed automatically; delete the relevant session state/reports manually if needed.

## 7. Notes

- The plugin does not send data to external services.
- It does not block or deny tool calls.
- It does not score reports; review them yourself.

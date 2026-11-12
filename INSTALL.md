# Install / Activate / Uninstall

## 0. 前置条件（必须）

本插件不包含、也不安装 MCP 服务。它依赖外部事实工具：

- `codebase_memory` MCP：代码索引、符号、调用关系、数据形状；
- `cscope`：C/C++ 调用者/被调用者/引用，含 static 函数；
- `clang` / `clang++`：C/C++ AST dump，用于函数/变量/类型边界和声明/实现核验；
- DAP MCP：实际运行值、线程、分支、生命周期；
- Python 3 + ZCode 插件系统。

**只有 `codebase_memory` 不够。** 它对普通符号很强，但 C++ 的嵌套类、重载、条件编译/多构建配置有已知长尾缺口；C/C++ 任务还应安装 `cscope` 与 `clang/clang++` 做交叉验证。`SCIP` / Joern / CodeGraph 可选，但不能替代 cscope/AST 的边界核验。

缺 `codebase_memory`：静态证据只剩 grep/读文件；缺 DAP：运行时证据只能靠日志/测试/探针，相关项必须标 `UNVERIFIED`；C/C++ 任务缺 cscope/clang：复杂符号只能靠图或读码，报告应写明未做交叉验证。两者都缺：只能当阶段提示器用，不能称为事实驱动。

最小检查：

```bash
command -v cscope
clang --version
# 以及 codebase_memory MCP 的 index_repository / search_graph 可调用
# 以及 DAP MCP 的 dap.capabilities / dap.start 可调用
```

实验记录：[S1 符号探索实验](docs/s1-symbol-exploration-experiment.md)。


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
mkdir -p ~/.zcode/cli/plugins/cache/static-dap-socratic/static-dap-socratic/2.0.8-case-study
rsync -a --delete ./plugin/static-dap-socratic/ \
  ~/.zcode/cli/plugins/cache/static-dap-socratic/static-dap-socratic/2.0.8-case-study/
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
python3 ~/.zcode/cli/plugins/cache/static-dap-socratic/static-dap-socratic/2.0.8-case-study/scripts/handoff.py \
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

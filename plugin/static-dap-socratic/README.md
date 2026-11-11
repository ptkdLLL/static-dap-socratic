# 事实驱动编程（static-dap-socratic 2.0.3-requirements）

给 AI 编程助手用的阶段式事实/证据工作流：一次只发当前阶段，收到阶段报告后进入下一阶段。

默认休眠；用户消息包含触发词时激活。

## 如何触发

在给 AI 的任务描述里包含：

```text
基于静态工具与dap联合
```

没有这句话不会触发。

## 依赖（必须）

- `codebase_memory` MCP：提供代码索引、符号、调用关系、数据形状；
- DAP MCP：提供实际运行值、线程、分支、生命周期；
- Python 3 + ZCode 插件 hooks。

插件不包含、也不安装这些 MCP 服务；没有它们，工作流只剩阶段提示，不能提供事实约束。

## 工作方式

1. 插件一次只注入**当前阶段**的提示。
2. 每个阶段结束时，代理写一份阶段报告，然后运行：
   ```sh
   python3 <plugin-root>/scripts/handoff.py --report REPORT-xxx.md --token <当前阶段令牌>
   ```
3. 插件收到报告事件后：记录到事实账本、推进一格、注入下一阶段。
4. 写 PLAN、写 CHANGE、索引完成、构建成功、源码修改都**不推进**；唯一推进边是 handoff。
5. 插件不解析、不评分报告；它只记录和转发。

## 阶段信息隔离

- Skill 文件只是激活 stub；它不包含阶段名称、顺序或报告清单。
- 阶段提示由 hook 在运行时逐段注入；本 README 也不列出阶段信息。
- 报告文件名会在当前阶段提示里给出，不需要预先知道。
- 不要在插件目录里寻找后续阶段；按当前阶段提示工作即可。

## 设计要点

- **Hooks add context only**: reminders never deny a tool call and never score evidence.
- **Information isolation**: the skill is an activation stub; stage content is internal to the hook and is not injected wholesale.
- **Block evaluation**: static evidence A + runtime evidence B; old code via DAP, new code via isolated harness/unit tests/sandbox; per-block transition matrix + red line; at least A+B before implementation; no dynamic evidence means `PASS-STATIC / BLOCKED / UNVERIFIED`.
- **Report as handshake**: a report is the stage summary the agent hands to the user; the plugin records and forwards it.
- **Exploration reminders**: pre-index source reads, source grep (source extensions or `app/src`/`src` paths), whole-file awk/sed, and full-file reads get contextual reminders; data/log searches are exempt.

## 文件

- `hooks/supervisor.py`：激活、当前阶段注入、事实记录、handoff 处理、探索提醒；
- `hooks/hooks.json`：5 个事件；
- `scripts/stages.py`：阶段数据的内部实现（hook 使用，不随 Skill 加载）；
- `scripts/handoff.py`：token + 报告 + handoff 队列；
- `scripts/ledger.py`：hash-chain 事实账本；
- `skills/static-dap-socratic/SKILL.md`：激活 stub。

## 状态目录

`~/.zcode/methodology/`：

- `state/<session-hash>.json`
- `facts/<session>.jsonl`
- `tokens/<token>.json`
- `handoff/<token>.json`
- `reports/<token>/REPORT-*.md`

安装/更新后需要重启 ZCode 才加载新 hook。

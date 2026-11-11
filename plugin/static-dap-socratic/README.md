# static-dap-socratic (2.0 report handshake)

A staged workflow plugin for the static+DAP methodology. It injects one stage at a time, records stage reports, and advances only after a report handoff.

Dormant by default; activated when the user prompt contains the activation phrase.

## 工作方式

1. 插件一次只注入**当前阶段**的提示；代理看不到后续阶段的名称、内容和验收方式。
2. 每个阶段结束时，代理写一份阶段报告，然后运行：
   ```sh
   python3 <plugin-root>/scripts/handoff.py --report REPORT-xxx.md --token <当前阶段令牌>
   ```
3. 插件收到报告事件后：记录到事实账本、推进一格、注入下一阶段。
4. 写 PLAN、写 CHANGE、索引完成、构建成功、源码修改都**不推进**；唯一推进边是 handoff。
5. The plugin does not parse or score reports; it records and forwards them.

## 阶段

| 内部阶段 | 注入标题 | 报告 |
|---|---|---|
| S1 | 建立全局视野与计划初稿 | `REPORT-research.md` |
| S2 | 计划验证 | `REPORT-hypotheses.md` |
| S3 | 修改文档 | `REPORT-change.md` |
| S4 | 逐块评估 | `REPORT-blocks.md` |
| S5 | 落码 | `REPORT-landing.md` |
| S6 | 验收 | `REPORT-acceptance.md` |

内部编号不会出现在注入文本里；代理只看到当前阶段标题。

## 设计要点

- **Hooks add context only**: reminders never deny a tool call and never score evidence.
- **Information isolation**: the skill is an activation stub; `stages.py` holds the full map but is never injected wholesale; `handoff.py` usage does not list stages.
- **S4 block evaluation**: static evidence A + runtime evidence B; old code via DAP, new code via isolated harness/unit tests/sandbox; per-block transition matrix + red line; at least A+B before implementation; no dynamic evidence means `PASS-STATIC / BLOCKED / UNVERIFIED`.
- **Report as handshake**: a report is the stage summary the agent hands to the user; the plugin records and forwards it.
- **Exploration reminders**: pre-index source reads, source grep (source extensions or `app/src`/`src` paths), whole-file awk/sed, and full-file reads get contextual reminders; data/log searches are exempt.

## 文件

- `hooks/supervisor.py`：激活、当前阶段注入、事实记录、handoff 处理、盲操作提醒；
- `hooks/hooks.json`：5 个事件；
- `scripts/stages.py`：六段阶段提示与顺序；
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

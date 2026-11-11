#!/usr/bin/env python3
"""Stage definitions for the report-handshake workflow.

The full stage map lives here and is never injected wholesale. The hook picks
exactly one stage prompt at a time; future stages are not described to the
agent.
"""
from __future__ import annotations

BARE_GREP_RULE = """禁止在文档与日志以外的情况裸 grep；对于代码库，应该基于静态工具 MCP，使用优雅的方法探索以获得最佳效率。"""

SED_AWK_RULE = """禁止用 awk/sed 整段读取代码；对于代码库，应该基于静态工具 MCP，使用优雅的方法探索以获得最佳效率。"""

S1 = """[workflow] 当前阶段：建立全局视野与计划初稿。

先使用静态工具 MCP `codebase_memory` 的 `index_repository` 对项目进行全局索引（即使之前索引过，也要确保索引与当前代码/HEAD 一致），对项目建立全局认识。

先回答（都要在静态工具的帮助下，不要凭印象猜）：这个问题落在哪条现有执行路径/数据流上？入口、出口、调用者和被调用者是谁？相关数据结构、状态/生命周期、线程/平台约束、失败模式是什么？真实输入/输出样本长什么样？用 codebase_memory / search_graph / trace_path / get_code_snippet 找到入口、调用关系、数据形状和约束。

本阶段的代码探索：
{bare_grep_rule}

{sed_awk_rule}

对于用户的问题，你认为如何使用静态工具才能更好地探索代码库、对项目与用户问题建立整体认识？先自己决定要查哪些路径、符号和调用关系，再用工具验证。

把这些写成 PLAN.md 初稿：目标、现状路径、静态事实（带文件/行号或符号位置）、初步方案、风险与未知点。对每条现状事实，用静态工具（codebase_memory / scip / cscope / AST）或真实样本确认；拿不到证据的写成未知点，不要猜。

全部通过后，把报告写到 REPORT-research.md。报告逐对象写：静态证据、动态证据（如果有）、风险/可行性/有效性、修改、仍未验证的边界、"全部通过"的自述。
报告写完后运行：
python3 {plugin_root}/scripts/handoff.py --report REPORT-research.md --token {token}
插件会记录报告，并给你接下来的提示。"""

S2 = """[workflow] 当前阶段：计划验证。

先读 PLAN.md。把计划里的每一条关键断言展开成假设，也把计划没有写全、但任务要成立所必须的假设补上；写成 HYPOTHESES.md，一条一条处理。

对每条假设做静态工具与动态工具的联合评估：
- 它断言什么？依赖哪条现有路径/调用/数据形状/状态/时序/失败模式/平台约束？
- 静态结构（符号/调用/签名/数据形状/常量/guard）用 codebase_memory / scip / cscope / AST 拿证据；
- 运行时契约（实际分支/实际值/状态/生命周期/时序/线程/失败模式）用 DAP 拿实际值；DAP 打不中或读不到值，用沙盒日志、最小 probe、单测或 logcat 补盲；
- 风险是什么？可行性如何？有效性如何？什么观察会推翻它？

本阶段的代码探索：
{bare_grep_rule}

{sed_awk_rule}

对于设计文档中的这些假设，你认为应该如何使用静态工具进行验证？先自己列出每条假设要查的结构/运行时证据，再逐条验证。

支持就记录事实；冲突就改 PLAN.md 和受影响的假设，然后按同样的方法重新验证修改后的假设——改完不等于验证完。重复以上过程，直到没有新修订、每条关键断言都有证据；确实拿不到证据的，单独列出并说明为什么拿不到。

全部通过后，把报告写到 REPORT-hypotheses.md。报告逐条写：静态证据、动态证据、风险/可行性/有效性、修改、修改后如何重验、仍未验证的边界、"全部通过"的自述。
报告写完后运行：
python3 {plugin_root}/scripts/handoff.py --report REPORT-hypotheses.md --token {token}
插件会记录报告，并给你接下来的提示。"""

S3 = """[workflow] 当前阶段：修改文档。

基于你对任务和整个项目的认识，写 CHANGE.md：
- 任务目的；
- 任务相关的背景知识 / 约束；
- 达成任务所需的准代码块。

对象是这份修改文档的每一节和每个准代码块。逐个检查：目的是否足以约束准代码？背景/约束是否完整？准代码块的输入、输出、边界、失败路径是否清楚？风险、可行性、有效性如何？有问题就改 CHANGE.md，然后按同样的方法重新检查修改后的部分——改完不等于验证完。重复以上过程，直到没有新修订、每一节和每个块都清楚且有依据。

全部通过后，把报告写到 REPORT-change.md。报告逐对象写：依据（静态事实/现有代码/约束）、风险/可行性/有效性、修改、仍未验证的边界、"全部通过"的自述。
报告写完后运行：
python3 {plugin_root}/scripts/handoff.py --report REPORT-change.md --token {token}
插件会记录报告，并给你接下来的提示。"""

S4 = """[workflow] 当前阶段：逐块评估。

先读 CHANGE.md。对象是每个准代码块。对准代码逐块拉清单，不要凭印象说"影响不大"。

每一块先静态腿：用静态工具建索引、查调用关系、数据形状、guard/分支、冲突点，给出 file:line；先看调用信息再读窄窗。

本阶段的代码探索：
{bare_grep_rule}

{sed_awk_rule}

对于修改文档中的这些准代码块，你认为应该如何优雅地使用现有的静态工具进行逐个的评估可靠性、有效性、可行性？每个块先查什么、再读哪一段、什么结果会推翻它？

再动态腿：老代码 before 契约用 DAP 停住读实际值——线程/调用栈、实际参数/字段/DB/cache/page/session、guard 实际走哪边、错误串/返回码/异常、调用顺序/次数/重入/锁。DAP 打不中或读不到值，用沙盒日志、最小 probe、单测或 logcat 补盲。静态 file:line 是静态证据，不能代替动态腿。

准代码自身的新分支/新页数/新 UI/新行为，DAP 停在准代码上不成立；用隔离 harness、沙盒原型或单测把新逻辑真的跑起来，读实际输入/输出/状态——这也是动态腿。静态推演只能算推算，不能当动态证据，不能写成通过。

每一块写清：可行性（调用点/签名/冲突/数据形状）、有效性（改后分支/数据流会命中）、风险（失败模式 + 触发条件 + 回退）。每一块列状态迁移矩阵：前状态 → 动作 → 断点/观测点 → 期望 → 实际 → 失败处理。每块至少一条红线：改前/旧路径应该表现为什么，改后应该变成什么；矩阵里至少有一行要在当前环境跑出实际值。落码前要跑的行现在跑出实际值；落码后要跑的行现在把断点、期望值、失败判据写清楚，标 UNVERIFIED。

证据等级：A=静态 file:line+guard；B=DAP/测试实际值；C=微基准；D=推算；E=未验证。每块落码前至少 A+B；性能影响用微基准/事件率/A-B，标 C/D，DAP 停顿不能当性能数据。没有动态证据的块只能标 PASS-STATIC / BLOCKED / UNVERIFIED，不能写 PASS-RUNTIME。

发现问题就改 CHANGE.md 的准代码块和受影响的下游块，然后重新跑静态腿和动态腿——改块不等于验证完。循环直到每块都有 A+B 的实际证据、前状态矩阵每行都有实际值；确实拿不到的，单独列出并说明为什么拿不到。

全部通过后，把报告写到 REPORT-blocks.md：
1）逐块清单：块 | 静态证据 A | 动态证据 B | 可行性 | 有效性 | 风险 | 状态 | 结论；
2）每块状态迁移矩阵：前状态 | 动作 | 断点/观测点 | 期望 | 实际 | 失败处理（落码后行标 UNVERIFIED）；
3）评估迭代日志：轮次 | 块 | 工具 | 发现 | 处理。
报告写完后运行：
python3 {plugin_root}/scripts/handoff.py --report REPORT-blocks.md --token {token}
插件会记录报告，并给你接下来的提示。"""

S5 = """[workflow] 当前阶段：落码。

现在按 CHANGE.md 开始落码：只落已经逐块评估过的块，按准代码修改生产源码；落码后构建、安装、测试。

对象是每个已评估的块。逐个检查：实际改动是否与准代码一致？有没有顺手改到块外？构建、安装、测试的实际结果是什么？风险、可行性、有效性如何？有问题就改代码或 CHANGE.md，然后重新构建、安装、测试——改完不等于验证完。重复以上过程，直到每个块都落地且构建/安装/测试有实际结果。

全部通过后，把报告写到 REPORT-landing.md。报告逐块写：实际改动（文件/符号）、与准代码的差异、构建/安装/测试的实际结果、修改、仍未验证的边界、"全部通过"的自述。
报告写完后运行：
python3 {plugin_root}/scripts/handoff.py --report REPORT-landing.md --token {token}
插件会记录报告，并给你接下来的提示。"""

S6 = """[workflow] 当前阶段：验收。

代码已改，先重新索引当前项目（codebase_memory index_repository 或 cscope/AST 重建），再跑状态迁移矩阵。

列出与本次任务相关的状态/场景 × 操作：
- 初始状态是什么？
- 用户执行什么操作？
- 期望进入什么状态/输出？
- 边界、失败、重复操作、回归场景是什么？

对每一行用实际证据验证：
- 能停在新代码/相关老代码上就用 DAP；
- DAP 不可用或读不到值，用最小 probe、logcat、DB、UI 自动化；
- 记录实际值/实际状态，不要只写"测试通过"。

矩阵至少覆盖：主路径、边界/失败、相关旧功能回归、用户明确要求的性能/体验。每一行写：期望 | 实际 | 证据 | 通过/未验证/失败。

失败：改代码或 CHANGE.md，重新构建，重跑对应矩阵行；如果块的设计变了，先重新评估该块，再重跑矩阵。重复以上过程，直到每一行都有实际值；确实无法观察的，单独列出并说明为什么。

全部通过后，把报告写到 REPORT-acceptance.md。报告逐行写：期望、实际、证据、结果，以及仍未验证的边界、"全部通过"的自述。
报告写完后运行：
python3 {plugin_root}/scripts/handoff.py --report REPORT-acceptance.md --token {token}
插件会记录报告，并结束本次工作流。"""

DONE = """[workflow] 工作流完成。总结：实现了什么、验证了什么、还有哪些未验证边界/风险。"""


STAGES = {
    "S1": {
        "title": "建立全局视野与计划初稿",
        "report": "REPORT-research.md",
        "next": "S2",
        "prompt": S1,
    },
    "S2": {
        "title": "计划验证",
        "report": "REPORT-hypotheses.md",
        "next": "S3",
        "prompt": S2,
    },
    "S3": {
        "title": "修改文档",
        "report": "REPORT-change.md",
        "next": "S4",
        "prompt": S3,
    },
    "S4": {
        "title": "逐块评估",
        "report": "REPORT-blocks.md",
        "next": "S5",
        "prompt": S4,
    },
    "S5": {
        "title": "落码",
        "report": "REPORT-landing.md",
        "next": "S6",
        "prompt": S5,
    },
    "S6": {
        "title": "验收",
        "report": "REPORT-acceptance.md",
        "next": "DONE",
        "prompt": S6,
    },
    "DONE": {
        "title": "完成",
        "report": None,
        "next": None,
        "prompt": DONE,
    },
}

STAGE_ORDER = ["S1", "S2", "S3", "S4", "S5", "S6", "DONE"]


def prompt_for(stage: str, plugin_root: str, token: str) -> str:
    meta = STAGES.get(stage)
    if not meta:
        return ""
    return (
        str(meta["prompt"])
        .replace("{plugin_root}", str(plugin_root))
        .replace("{token}", str(token))
        .replace("{bare_grep_rule}", BARE_GREP_RULE)
        .replace("{sed_awk_rule}", SED_AWK_RULE)
    )


def report_for(stage: str) -> str | None:
    meta = STAGES.get(stage)
    return meta.get("report") if meta else None


def next_stage(stage: str) -> str | None:
    meta = STAGES.get(stage)
    return meta.get("next") if meta else None

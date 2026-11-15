# 量化小模型中的介入式因果：外部注意力与工具纪律的作用

**——一次 Q2 量化模型上的事实驱动研究（研究讨论稿）**

**作者**：待署名

**版本**：研究讨论稿

**日期**：2026 年 11 月 15 日
**代码与文档**：`ptkdLLL/static-dap-socratic`

---

## 摘要

大语言模型编程代理的失败，往往不是“不会写代码”，而是把局部印象、词法命中或未经运行验证的推断当成事实，并围绕错误计划组织后续实现与报告。本文研究一个更窄的问题：**经过 Q2 量化的本地模型，能否在外部注意力管理与工具纪律的约束下，产生一次真实的介入式因果轨迹**——即提出反事实、做干预、用实际值推翻自己的先验、并重写计划。我们在一个混合语言 Android 漫画阅读器上，对 S1（计划生成）与 S2（假设验证）进行了多轮提示词与拓扑迭代，并报告一次完整成功案例：模型用真实样本、运行时数据与构建探针，推翻了“先 Kotlin 封面、页缓存主修、可见 cell 懒生成足够”三个先验，把 PDF 从归档模型里拆出，改为原生引擎 + 范围读主线，并将 PDF 整文件缓存从默认路径移除。与此同时，我们记录了同一模型在更多轮次中的失败：全库扫描、先读源码、快速草稿不提交、账本滞后、缓存盲区。我们的结论是：**该模型不是可靠的因果代理，而是概率性的因果轨迹生成器；外部拓扑可以把命中概率从接近零抬到可收割，但抬不到可托付。** 本文不主张统计显著性，只报告方法可行性、失败模式与设计边界。

**关键词**：事实驱动编程；量化模型；编程代理；介入式因果；注意力外置；工具纪律；grep

## Abstract

Coding agents often fail not by being unable to write code, but by mistaking lexical matches, local impressions, or untested inferences for facts, and then organizing implementation and reporting around a flawed plan. This paper asks a narrower question: can a locally Q2-quantized model, under external attention management and tool discipline, produce a genuine interventional causal trajectory—proposing a counterfactual, running an intervention, refuting its own prior with measured values, and rewriting the plan? On a mixed-language Android comic reader, we iterated the S1 (plan generation) and S2 (hypothesis verification) prompts and topology, and report one complete success: using real samples, runtime data, and build probes, the model overturned three priors—Kotlin-first cover generation, page-cache-as-primary-fix, and visible-cell-only generation—separated PDF from the archive model, adopted a native engine with range reads as the main path, and removed the default whole-file PDF cache. We also document the same model's failures across more runs: whole-library scanning, source-first reading, failure to commit a quick draft, delayed ledger updates, and cache blindness. We conclude that the model is not a reliable causal agent but a stochastic generator of causal trajectories; external topology raises the hit probability from near zero to harvestable, but not to trustworthy. We claim feasibility, failure modes, and design boundaries, not statistical significance.

**Keywords**: fact-driven programming; quantized models; coding agents; interventional causality; attention externalization; tool discipline; grep

---

## 1 引言

### 1.1 问题背景

大语言模型编程代理已经能够在仓库级任务中规划、修改、构建和测试软件，但其计划经常把局部印象、词法命中或未运行验证的推断误认为事实。仓库级软件工程的事实分布在符号边界、调用关系、构建配置、运行时状态、平台约束和用户目标之间，任何单一工具都不能提供完整真相。更麻烦的是，代理一旦形成计划，后续实验和报告容易围绕原计划组织，而不是围绕能够推翻原计划的事实组织。

工程上常见的应对是流程门禁：要求先计划再实现、要求提交结构化报告、要求调用特定工具、或在阶段边界设置自动检查。问题在于，门禁的可见形式很容易被代理当作新的优化目标：要求“必须调用调试器”，代理可能寻找最便宜的调试器调用；要求“必须填写证据表”，代理可能把输出改写成看似合规的证据；要求“测试通过”，代理可能优化测试通过而不是满足自然语言规格。这与奖励错误指定、规格博弈和 Goodhart 型代理指标失真具有同一结构。

事实驱动编程（FDP）采取了相反的设计：外部状态机只管理阶段拓扑、交接和注意力，不把“必须调用某工具”写成推进条件；阶段话术通过强指令、任务局部设问和证据阈值，要求代理把计划改写为可证伪假设，再根据信息需求选择静态分析、真实样本、探针、日志、测试、构建和调试器，用可复核事实支持、否定或重构计划。

### 1.2 项目与历史：一个非 FDP 的 PDF bolt-on

研究对象是一个 Android 漫画阅读器。它最初只做三件事：读 SMB 分享目录、读 zip、快。C++ 主干在 Windows 上写成，后移植到 Android 成为主干；UI 是 Kotlin/Compose，核心是 C++，中间隔着 JNI；构建同时依赖 Gradle 与 CMake/NDK；第三方库覆盖 SMB、解压、图像解码、SQLite 与推理。复杂度不在“文件多”，而在边界多：Windows C++ 的路径/IO/线程/编码假设到 Android 的 VFS/文件描述符/scoped storage/JNI，Kotlin 与 C++ 的对象所有权/线程/生命周期，双构建系统，远端读取与缓存，Compose 隐式调用，第三方库的 ABI/编译开关/许可证。

更早的功能（翻译、标签数据库、动图、阅读模式、性能调优）是在 4.1 版模型 + 人工监督下用 FDP 一点点加入的。**PDF/EPUB 那一版不是 FDP 产物**：代理自行考古过去成功的工作流，生成了一个插件，在质量门禁的监督下表演式地使用工具，把 PDF/EPUB 接进归档模型。因此它是 bolt-on，带着“归档假设”：统一容器入口、整文件 materialize、封面后置、页数打开才有。质量门禁保证了流程/报告的形状，但没有做架构前提审计；这解释了后来暴露的整库下载/缓存膨胀副作用。

这一区别是本文的起点：**FDP 的失败与“门禁监督下的表演式工具使用”的失败不能混为一谈。** 前者是假设循环没有闭合，后者是流程形状正确但架构前提从未被审判。后续的 Q2 研究，正是要为后者补一次前提审计。

### 1.3 研究问题与贡献

本文研究四个问题：

- **RQ1**：Q2 量化模型能否自己发起前提审计/介入式因果，即在没有用户点名“缓存有问题”时，自己问“这个机制该不该存在、没有它会怎样”？
- **RQ2**：如果不能，外部提示词/拓扑/框架能否把它逼出来？哪些部分有效：注意力拆分、工具纪律、账本/门禁、随机采样、验证器？
- **RQ3**：为什么盲 grep/rg 在混合语言项目上会致命？什么样的工具政策能让它写出可编译的修改？
- **RQ4**：这套工作流的稳定上限是什么：半自动、概率性轨迹收割，还是可以托付？

本文的贡献是：

1. 给出一个量化小模型的能力剖面：知识/选项生成基本保留，执行控制/先验突破/持续维持显著削弱；
2. 记录 S1/S2 多轮提示词与拓扑迭代，说明“加规则”为什么经常反噬注意力，以及什么结构有效；
3. 报告一次完整的介入式因果轨迹：用实测推翻三个先验、重写 PLAN、把 PDF 整文件缓存从默认路径移除；
4. 给出可复用的设计规则与有效性威胁，明确“一次成功”不等于“稳定能力”。

---

## 2 相关工作

### 2.1 事实驱动编程

FDP 把复杂编程任务拆成六步，一次只让代理做一步；每步以报告交接，外部状态机只管理拓扑与注意力。其核心不是“让代理更自由”，而是让代理持续受到与任务目的相关的外部事实约束。本文沿用该框架，并把 S1/S2 的提示词与账本作为主要变量。

### 2.2 工具使用与代码导航

代码导航工具存在明显的分层：文本搜索（grep/ripgrep）、语法结构（tree-sitter/ast-grep）、符号索引（ctags/LSIF/SCIP）、语义服务（LSP）和嵌入检索。Aider 的 repo map 用 tree-sitter + PageRank 提供“目录”而不是全文；LocAgent 用异构图做多跳定位；Agentless 用分层定位（文件→类/函数→行）结合 LLM 与 IR；ast-grep 用 AST 结构搜索替代正则。它们的共同结论是：**grep 是强 baseline，但 grep-only 在结构查询、跨文件关系和大仓库上不够。**

### 2.3 注意力、上下文与量化

“注意力容量”至少分四层：架构窗口、训练分布决定的可用比例、执行控制、量化/运行时。量化主要伤执行控制：知识/选项生成可能保留，但在多约束、长上下文、需要持续维持目标时更容易退化。本文的 Q2 模型只量化 routed experts，shared experts、attention/projections/output、router 与 Engram 保留较高精度；这与“能列出方案、守不住循环”的观察一致。

### 2.4 评测与真实问题解决的差距

主流编程代理评测多集中在 Python、单语言、issue 带符号名、测试可运行的仓库；它们测 issue 解决、定位精度、检索质量或轨迹效率，而不是混合语言项目的构建健康。SWE-bench 类测试会隐式包含构建（编译语言），但 build 失败被折进 test 失败；定位/检索类研究甚至不生成 patch。混合语言、JNI/ABI、双构建系统、Compose 隐式调用的项目在这些评测的分布之外。本文的案例正是这一分布外样本。

---

## 3 研究设计

### 3.1 环境与对象

- 项目：混合语言 Android 漫画阅读器（Kotlin/Compose + C++ + JNI，Gradle + CMake/NDK，SMB/本地库）。
- 设备：模拟器为主，个别外部补验在真机；Android 14/SDK 34 为主。
- 模型：本地 Q2 量化模型（DeepSeek-V4.1-Flash-1017 的 Q2 版本），与官方版本对照。
- 工具：codebase_memory 静态结构、DAP、DB、logcat、UI dump、最小 probe、Gradle/NDK 构建。

### 3.2 S1 协议

读需求 → 索引/定向结构 → 现状路径/状态/失败模式 → 静态+动态研究方法论 → 写 `PLAN-v0`。目标是让 PLAN 自己暴露“被选 vs 替代”的分叉，而不是直接给实现补丁。

### 3.3 S2 协议

读 PLAN → A/B/C 三层假设（A 方案先验选择、B 动机/方案分叉、C 实现事实）→ 每条至少一个实验 → 拿实际值 → 判断是否重构 PLAN → 重写 PLAN → 报告/交接。B 层必须写“被选/替代、判据、为什么预期胜、什么测量会让它输、若输改哪条”。

### 3.4 证据与度量

- 结构证据：符号/调用图/字段/类型/JNI 边界；
- 运行时证据：DB/logcat/UI/DAP/probe；
- 度量：调用数、上下文、时长、构建/测试结果、关键实际值、未验证项；
- 证据等级：静态存在/静态路径/单次运行时/重复受控/单变量 probe；推断不得冒充实际值。

### 3.5 效度控制

每个 run 新 session；不并行；单驻留模型；prompt/工具政策作为变量记录；失败也计入；未验证项单列。本文报告的是可行性证据，不是受控统计实验。

---

## 4 研究一：S1 计划生成

### 4.1 初始失败

S1 的第一版把“真实规模”执行成了全库逐文件扫描：约 53 分钟、204k tokens，仍未产出 PLAN。第二版要求先写方法论，模型转而读源码；约 10 分钟、85k，无 METHODOLOGY。第三版把方法论前置、分析分离，写出了 20.8KB 的方法论（需求映射、采样、证据等级、实验序列、候选轴），但候选轴没有“移除持久状态”，最终仍在 66 分钟、188k 时没有 PLAN。

### 4.2 快速草稿的失败

把 S1 改成“立刻写 PLAN-v0，允许不完美”后，模型仍持续 rg/read 源码；17 分钟、81k，无 PLAN。加入 grep/rg/awk/sed 禁令后，模型改用 `read` 源码绕过；13 分钟、95k，无 PLAN。随后一次运行被 `adb jdwp` 挂起 13 分钟，并且上一轮的 pi 孤儿进程占住单驻留模型槽，58 分钟、177k，无 PLAN。

这些失败的共同点不是“不会写 PLAN”，而是**无法从收集切换到承诺**：只要还有工具可用，它就会继续取证，而不是在信息不足时先交一个带先验的方案。

### 4.3 正式 S1 与 PLAN-v0

最终版恢复正式 S1 结构：需求复述 → 索引 → 路径/状态/失败模式 → 代码探索硬约束（禁盲 grep/rg/awk/sed、禁 read 源码、只允许静态 MCP 与 ≤20 行 narrow window）→ 静态/动态研究方法论 → PLAN-v0 写完即停。约 52 分钟、184 调用、262k，写出 30.2KB 的 PLAN-v0。

PLAN-v0 已经明文写了三件关键事：

- 封面不得整本下载；SMB 封面应只读 page0 对象 + 页树/xref；
- `smbcache` 无自动上限，需要容量上限/LRU/按书清理；
- Phase 1 仍是 Kotlin 封面 + 整文件阅读，Phase 2 才是原生引擎——即问题被命名，但还没有成为第一决策。

### 4.4 研究一的回答

S1 可以在外部结构下产出“带显式分叉的 PLAN”，但它不会自己把“删除某个状态”写成候选；它会把问题命名，却不一定把它升为第一决策。S1 的产出质量取决于：需求先行、正式路径问题、代码禁令及理由、PLAN-v0 的停止条件；只加“更凶的话术”没有用。

---

## 5 研究二：S2 假设循环

### 5.1 旧版 S2：事实充分，宾语错误

旧版 S2 运行约 1 小时 54 分、219 调用、395k tokens，写出了 HYPOTHESES、REPORT 和 PLAN v2，但整文件缓存保留。其 B5 的被选与替代都是下载策略：buffer + 封面预热 vs range/流式；整文件缓存是两者的共同底座，不是候选。它拿到了 7.16GB、175KB vs 52MB 等事实，但把这些事实用来杀“UI 懒生产者”“封面预热”“buffer”，没有用来杀缓存本身。

根因不是事实不足，而是**假设提取以 PLAN 为边界**：PLAN 把缓存写成环境，B 层就没有“删除这个状态”的格子。

### 5.2 提示词与账本调整

后续 S2 的调整包括：

- 删除 L/S/B 先验分级：分级会变成填表，实验围绕标签转；改为“实验后才有权重”。
- 建立 A/B/C 三层，B 层强制“被选 vs 替代 + 杀死测量”。
- 把“PLAN 得以实现所依赖的假设”改为“PLAN 所蕴含的假设”，避免与动机假设矛盾。
- 删除提示性例子，避免泄漏答案。
- 要求每次实验后回填 HYPOTHESES；账本是活账本，不是一次性清单。

这些调整解决了“怎么写假设”，但没有解决“谁来提交/收束”：长 session 里账本仍会滞后，模型仍会继续做实验而不回写。

### 5.3 结果：一次完整的介入式轨迹

在 PLAN-v0 已经写明 A3/F17/Phase2/Phase3.6 的前提下，S2 运行 1 小时 54 分、299 调用、366k tokens，没有触发 450k 自动压缩；写出 HYPOTHESES 27.1KB、PLAN 31.3KB、REPORT 26KB，并 handoff。它先写 A/B/C 与 17 组实验计划，再做静态/动态实验、回填、重写 PLAN。

### 5.4 B 层裁决

| 分叉 | 实际值 | 裁决 |
|---|---|---|
| Kotlin 封面 vs native 引擎 | 124 本 PDF 中 119 本未缓存（96%）；Kotlin 路径必须整档下载（1.3MB→207ms，52MB≈5s，慢块 1MB→8976ms）；native page0 0.17MB+39KB xref≈60ms，Android render 17ms | native 胜；Kotlin 降 fallback |
| 未缓存策略：占位/手动 vs 阈值下载 vs range | 全库远程 PDF 7.5GB；page0 压缩样本 0.02–1.89MB；SMB 180KB≈22.6ms | range 胜；手动只作兜底 |
| MuPDF vs PDFium vs 系统渲染器+缓存 | 原生引擎构建成功（约 7.9MB 动态库），page count 1.46ms，render 17–37ms；系统渲染器 125–465ms；许可需整体开源或商业授权 | 技术胜，许可 gate |
| 页缓存/预取 vs 队列/当前页优先/原生 | 顺序 125–167ms；回看 137–206ms；首次 5 页并发锁等待 373–693ms | 页缓存不是主修；队列/当前页优先/native 先 |
| 可见 cell 懒生成 vs 全库队列 vs 手动 | 完整墙 143/165 缺封面；每个可见 cell 一次远端会话 | 可见-only 不足；持久队列+预取 |
| smbcache LRU vs 每书流式 vs 仅手动 | 缓存目录 8 文件 108MB，无自动淘汰；PDF 整档 55MB vs native page0 0.2MB | PDF 默认流式；其他格式/离线走 LRU+上限 |

### 5.5 其他确认

- 清封面后缩略图 0、DB 仍 26 个 key、UI 全占位、冷启动仍全占位；`clear_all_covers` 只清缩略图。
- 后台翻译会话关闭后仍残留 1 个文件描述符；切分模式同一 raw 页被解码 2–3 次。
- 损坏 PDF 无明确错误态，UI 停在 `1/0`。

### 5.6 研究二的回答

S2 能产生一次完整的介入式因果轨迹，但条件是：PLAN 已经写出可检验的分叉、B 层强制杀死测量、模型真的跑实验、账本回填、报告/PLAN 重写。缺任何一项，它就退回“优化当前路径”。

---

## 6 案例：从归档假设到范围读

### 6.1 关键证据

- 全库远程 PDF 7.5GB；119/124 未缓存（96%）。
- Kotlin 路径：1.3MB→207ms，52MB≈5s，慢块 1MB→8976ms。
- native：52MB 样本 page0 0.17MB+39KB xref，约 60ms；Android 渲染 page0 17ms；page count 1.46ms。
- 原生引擎构建成功，约 7.9MB 动态库；渲染 17–37ms，对比系统 PDF 渲染器 125–465ms。
- 缓存目录 8 文件 108MB，无自动淘汰；封面墙 143/165 缺封面。
- 清封面后 DB 26 key/UI 全占位；后台会话残留 1 FD；切分同 raw 解码 2–3 次；首次 5 页并发 3 个 waiter、373–693ms。
- 更早的完整 S1–S6 运行约 3 小时 25 分、250 调用、429k tokens；应用可构建、可见需求基本完成，但留下 3.6–4.1GB 整库 PDF 缓存，真机存储打满。

### 6.2 计划重写

S2 后的 PLAN 做了结构性改动：

1. PDF 原生引擎 + 范围读主线；系统 PDF 渲染器降 fallback。
2. 远端 PDF 打开不再整档 materialize；page count/render/cover 走原生。
3. 封面队列：可见 + 前后一屏预取 + 持久队列；清封面/重生成复位。
4. 性能：当前页优先队列 + 限并发 + 原生 context；页缓存后置；切分共享 raw 位图。
5. 缓存：PDF 默认不再整档缓存；其他格式/显式离线整档走有界 LRU + 容量上限 + 按书清理。
6. 隐藏毛病：job 关闭、删除清理、损坏 PDF 错误态、EPUB 早退。
7. 许可/构建 gate：许可决策、项目内构建 spike、失败回退。

### 6.3 未验证边界

原生引擎许可、项目内构建集成、context 并发、视觉/裁剪/色彩回归、慢网/坏网、真机性能、全库 page0 字节分布、EPUB 原生范围读、删除书运行时清理。全部写成 gate，不写成结论。

---

## 7 讨论

### 7.1 注意力必须外置

观察到的失效包括：旧 S2 在十余次调用后从“假设验证”滑到“核对设计”；快速草稿要求在“立刻写 PLAN-v0”下仍持续 rg/read；全库扫描没有采样/代价边界；`adb jdwp` 挂起与孤儿进程占模型槽。注意力不是一个单一容量：架构窗口、训练分布、执行控制、量化/运行时各占一层。Q2 的量化主要伤执行控制，所以“能列出方案，守不住循环”。

外置注意力的做法是：拆节点（一条可证伪 claim + 一个证据工件）、单 item 注入（需求 + 当前项 + 相关事实/决定切片 + 前置工件 + schema + 预算）、账本/议程（跨节点记忆）、硬预算/提交门、随机采样 + 验证器。压缩是 fallback：成功轮在 366–395k 结束，未触发 450k；如果账本未回填，压缩摘要会丢掉关键实际值。

### 7.2 盲 grep 的致命性

在混合语言项目里，grep 能找到符号名，但找不到 JNI 注册/ABI、Kotlin↔C++ 所有权/线程/生命周期、Gradle+CMake 构建依赖、Compose 隐式调用、SMB VFS 的会话/FD 约束、第三方库的编译开关/许可证。基于文本片段的修改，调用者/被调用者、线程/锁、ABI 往往对不上，编译不过或运行即崩。禁令不是风格要求，是正确性要求；而且必须配外部 tool-call 检查，否则模型会换 `read` 绕过。

### 7.3 知识与执行控制的分离

Q2 的量化 recipe 只量化 routed experts；shared experts、attention/projections/output、router、Engram 保留较高精度。因此它“能列出 MuPDF/PDFium、SMB range、状态机、证据等级”，但“不能自己发起并守住先验粉碎”。这解释了为什么同一个模型在节点内可以高质量，节点外却会漂移。

### 7.4 概率性轨迹收割与半自动上限

这次成功是**一次命中**，不是稳定能力；成功率/复现率未测。外部拓扑的作用是把命中概率从“接近零”抬到“可收割”：禁盲 grep、拆节点、账本、随机采样、验证器。高确定性工作仍需强模型/人做 framing 与最终验收；弱模型适合节点执行 + 多次采样 + 验证。半自动不是失败，是匹配。

### 7.5 与行业评测/工具话语的关系

“grep 胜过 RAG”是伪比较：它只说明 naive RAG 不适合精确符号检索，不说明 grep 足够。主流评测多集中在 Python/单语言/issue 带符号名/测试可运行；混合语言、编译门禁、JNI/ABI/Compose 的分布外样本，grep-only 会系统性失败。行业代理默认仍偏 grep/rg，LSP/hooks 是外部补丁；本文的“禁盲 grep + 静态 MCP + 动态证据 + 账本/门禁”补的是这个空白。

### 7.6 与表演式工具使用的区别

本文开头区分了 FDP 与“门禁监督下的表演式工具使用”：后者可以产出流程/报告形状正确的轨迹，但没有架构前提审计；前者要求事实否定计划、计划回改、未验证边界显式保留。S2 的成功不是“工具调用更多”，而是“事实改变了计划”；这正是两者最根本的区别。

---

## 8 有效性威胁

**内部效度**：只有一次完整的 S2 成功案例；prompt、模型版本、设备状态都是变量；没有同任务的多轮对照。成功可能包含抽样运气，不能当作稳定能力。

**外部效度**：项目是混合语言 Android 应用，结果不外推到 Python/Web/其他仓库；模拟器与真机、快网与慢网、不同 SMB 实现都可能改变量值。

**构念效度**：我们用“是否推翻先验、是否重写 PLAN、是否移除无界状态”衡量介入式因果，而不是形式化因果图；用量/构建/测试/DB 实际值衡量证据，但仍可能漏掉未测路径。

**结论效度**：没有做“grep-only vs 静态结构”的同模型受控构建 A/B；本文的 grep 结论来自多轮失败观察与项目结构分析，不是统计实验。

---

## 9 结论

本文报告了一次量化小模型上的事实驱动研究。核心结论是：

1. Q2 的知识/选项生成基本保留，执行控制/先验突破/持续维持显著削弱；
2. 在外部注意力管理、禁盲 grep、账本/门禁、随机采样与验证器的条件下，它能以一定概率产生真实的介入式因果轨迹；S2-on-PLAN-v0 是一次完整命中；
3. 这次命中的价值是把 PDF 从归档模型里拆出：原生引擎 + 范围读主线、PDF 默认不整档缓存、封面持久队列、页缓存后置、生命周期/错误态修复；
4. 但这仍是概率收割，不是稳定能力；高确定性工作仍需强模型/人做 framing 与最终验收；
5. 对混合语言项目，盲 grep/rg 不是低效，是致命；静态结构 + 动态证据是能否构建的前提。

**一句话：Q2 不是可靠的因果 agent，它是一个概率性的因果轨迹生成器；外部拓扑把它从“接近零”抬到“可收割”，但抬不到“可托付”。**

---

## 附录 A 关键数据

| 阶段 | 时长 | 调用 | 上下文 | 结果 |
|---|---|---:|---:|---|
| 完整 S1–S6 | 约 3h25m | 250 | 429k | DONE/可构建；3.6–4.1GB 缓存副作用 |
| 旧版 S2 | 约 1h54m | 219 | 395k | REPORT/PLAN；整文件缓存保留 |
| S1 正式版 | 约 52m | 184 | 262k | PLAN-v0 30.2KB |
| S2-on-PLAN-v0 | 约 1h54m | 299 | 366k | REPORT/PLAN；PDF 默认不整档缓存 |

## 附录 B 证据与复现说明

本文为脱敏研究记录：不包含凭据、主机/IP/共享名、设备标识、应用包名、个人书库书名、文件路径或会话 ID。证据来自原始会话、阶段报告/计划、构建与运行时记录；内部完整记录不随本文发布。复现需要同类混合语言项目、相同工具政策（禁盲 grep/read 源码、静态 MCP + 动态证据）与独立 session；具体量值受设备/网络/样本影响。

## 参考文献

[1] 事实驱动编程：以设问、假设与工具取证约束单代理软件工程的方法论研究. `docs/fact-driven-programming.md`.
[2] 实战案例：一次 PDF 子系统级修复（脱敏）. `docs/case-study-pdf-subsystem.md`.
[3] DAP 设计规范与当前限制. `docs/dap-spec.md`.
[4] Aider. Building a better repository map with tree-sitter. https://aider.chat/2023/10/22/repomap.html
[5] Chen et al. LocAgent: Graph-Guided LLM Agents for Code Localization. ACL 2025. https://arxiv.org/abs/2503.09089
[6] Xia et al. Agentless: Demystifying LLM-based Software Engineering Agents. https://github.com/OpenAutoCoder/Agentless
[7] ast-grep. https://ast-grep.github.io/
[8] S1 符号探索实验：增强注入是否改善找符号. `docs/s1-symbol-exploration-experiment.md`

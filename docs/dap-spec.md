# DAP 设计规范与当前限制

> 适用：事实驱动编程插件 2.0.x  
> 目的：说明插件需要 DAP MCP 提供什么、当前实现支持什么、哪些能力不可用、失败如何降级。  
> 原则：**声明即契约；空结果不算命中；不把 attach/pause 当断点证据。**

---

## 1. 插件为什么需要 DAP

静态工具回答“代码怎么写”：符号、调用关系、数据形状、guard/分支。  
DAP 回答“代码实际怎么跑”：实际参数/字段、线程/调用栈、分支走向、生命周期、时序、失败模式。

插件在两类节点依赖 DAP：

- **逐块评估**：验证准代码要接/改/复用的老代码 before 契约；
- **验收**：在状态迁移矩阵里读取实际值，而不是只写“测试通过”。

没有 DAP，工作流仍能跑，但运行时契约只能靠日志、测试、探针、数据库、界面补盲；相关结论必须标 `PARTIAL` / `UNVERIFIED`，不能冒充 DAP 命中。

---

## 2. 所需 DAP MCP 契约

### 2.1 工具面

一个可用的 DAP MCP 至少提供：

| 工具 | 作用 |
|---|---|
| `dap_capabilities` | 返回后端/能力矩阵（`supported: true/partial/false` + note） |
| `dap_start` | launch/attach，设置断点，等待首次停止 |
| `dap_continue` | 继续到下一次停止/退出 |
| `dap_step` | `over/into/out` 单步 |
| `dap_pause` | 暂停运行中的程序 |
| `dap_threads` | 列出线程及栈顶帧 |
| `dap_stack` | 当前/指定线程调用栈 |
| `dap_vars` | 当前帧局部变量（支持嵌套展开更好） |
| `dap_eval` | 当前帧表达式求值 |
| `dap_output` | 读取程序 stdout/stderr |
| `dap_stop` | 停止并清理会话 |
| `dap_sessions` | 列出活跃会话 |

### 2.2 启动/附加

- 后端至少覆盖目标语言：`lldb`（C/C++/Rust）、`python`、`node`（JS/TS）、`java`、`cs`（C#/.NET）。
- 支持 `launch` 与 `attach`（端口或 pid）；attach 不应杀掉目标进程。
- 启动结果至少包含：`sessionId`、`state`（`running/stopped/exited/failed`）、`reason`、`frame`、`hitBreakpoints`、`outputTail`、`unverifiedBreakpoints`（如有）。
- Java 需要 `classpath`、类名/源文件、`-g`（LocalVariableTable）；Port 模式需要目标提前监听 JDWP。

### 2.3 断点

至少支持：

- 行断点（`file` + `line`）；
- 函数断点（`functionBreakpoints: [{name}]`）；
- 条件断点（`condition`）；
- 命中计数（`hitCondition`）；
- logpoint（`logMessage`，命中打印不停止）；
- 异常断点（`exceptionFilters: ["uncaught"|"all"|异常类名]`）。

要求：

- 断点未绑定时必须通过 `unverifiedBreakpoints` 或其他可见字段报告，不能静默失效；
- 命中信息必须能区分“停了”与“没停”：`hitBreakpoints` 为空就是没命中；
- 条件/logpoint 失败要有可见错误（如 `[bp-condition-error]`），不能假装命中。

### 2.4 停止后读取

- `dap_stack`：调用栈（函数名、文件、行号）；
- `dap_vars`：局部变量实际值（支持对象/数组/字典嵌套展开更好）；
- `dap_eval`：当前帧简单表达式求值；
- `dap_threads`：线程列表与栈顶帧；
- `dap_output`：程序输出，用于崩溃/日志补盲。

### 2.5 生命周期

- 每个会话有唯一 `sessionId`；
- `dap_stop` 必须清理 debuggee/adapter，不留下孤儿进程；
- 支持多会话/多端口，不互相污染；
- attach 会话停止时默认不杀目标（除非显式要求）；
- `continue` 超时、JDWP 断开、adapter 退出都要有明确错误，不伪装成“命中”。

### 2.6 底层依赖栈与限制归因

插件本身不捆绑 DAP 实现；它调用外部 MCP/工具，底层是这些现成的 adapter、库与协议：

| backend | 底层 adapter / 库 | 协议 | 限制主要来自 |
|---|---|---|---|
| lldb | CodeLLDB（codelldb）+ LLDB | DAP over TCP | LLDB/CodeLLDB：attach、断点 resolve 竞态、DWARF/源码名匹配、异常过滤 |
| python | debugpy | DAP over stdio | debugpy：attach 握手、单行循环 pause 事件 |
| node | Node Inspector / V8 + Chrome DevTools Protocol | WebSocket | CDP/Node Inspector：函数断点需启发式、主线程模型、输出延迟 |
| java | 原生 JDWP 客户端（无外部 adapter） | JDWP over TCP | JVM/ART 的 JDWP/JVMTI：`CLASS_PREPARE`、已加载类、`LocalVariableTable`、无通用 eval |
| cs | netcoredbg | DAP over stdio | netcoredbg：pause/attach、单次命中限制 |
| TS | node 后端 + esbuild（可选 tsx） | CDP + source map | esbuild/tsx 与 source map：行映射精度 |
| Android | `adb forward` + ART JDWP agent | JDWP over TCP | ART 的 JDWP/JVMTI 实现：已加载类断点、pause 帧、eval |
| native Android | LLDB/CodeLLDB + lldb-server（未作为默认验证路径） | DAP/LLDB | 符号、ptrace、attach 环境 |

这些是外部依赖，不是插件自带；`dap_capabilities` 声明的是这些 adapter 的当前能力。下面列的限制大多继承自这些 adapter/协议，不是插件新增的语义；插件只负责调用、记录和标注。

---

## 3. 当前实现能力矩阵

以下是当前 DAP MCP 的**声明状态**；实际使用前先调用 `dap_capabilities`，以它为准。

| 能力 | lldb | python | node | java | cs |
|---|---|---|---|---|---|
| pause | ✅ | ⚠️ 单行循环可能无 stopped 事件 | ✅ | ✅ | ❌ |
| attach | ❌（常报不可达/超时） | ✅（需 debugpy `--wait-for-client`） | ✅（`--inspect`） | ✅（JDWP port） | ❌（attach 即退出） |
| 函数断点 | ✅ | ✅ | ⚠️ 启发式源码定位 | ✅（CLASS_PREPARE） | ✅ |
| 条件断点 | ⚠️ 单行循环/快程序有竞态 | ✅ | ✅ | ✅（工具层求值） | ✅ |
| logpoint | ⚠️ 快程序/多行有限制 | ✅ | ✅ | ✅ | ⚠️ 单次命中 |
| 异常断点 | ⚠️ `uncaught` 可靠，`all` 有限制 | ✅ | ✅ | ✅ | ✅ |
| threads | ✅ | ✅ | ⚠️ 仅主线程 | ✅ | ✅ |
| 嵌套变量 | ✅ | ✅ | ✅ | ⚠️ 行吸附时可能缺局部变量 | ✅ |
| eval | ✅ | ✅ | ✅ | ✅ 迷你文法 | ✅ |

> 这些是当前实现的**声明边界**，不是所有平台/构建/运行形态的保证。平台差异见下一节。

---

## 4. 已知限制

### 4.1 Android / ART / JDWP（当前最重要的限制）

在 Android 真机/模拟器测试中，Java DAP 后端的实际表现：

- **attach 可以成功**，`threads` 能看到 `main`、`worker`、`DefaultDispatcher-*` 等线程；
- 但对**已加载**的 Kotlin/Java 类，函数断点、行断点经常不命中；`String.length` 这类基础方法断点也可能不命中；
- Java 函数断点依赖 `CLASS_PREPARE`：类首次加载时才能挂起；已经加载的类不会再触发；
- `pause` 可能返回 `stopped`，但 `stack` 为空；此时 `vars`/`eval` 报 `no frame`，`step` 报 `no thread`；
- JDWP 可能超时/断开；`set-debug-app -w` 等冷启策略不保证断点命中；
- Kotlin 包声明/类名解析、Compose/优化构建、类加载器、应用重启都可能影响断点绑定；
- **结论：在 Android 上，attach + pause + threads 只能证明“连上了、线程可见”，不能证明任何运行时契约；断点未命中时必须改用 logcat、数据库、界面、探针或单测，并在报告中标 `PARTIAL` / `UNVERIFIED`。**

可尝试的路径（仍需实测，不保证）：

1. 在类**首次加载前**设断点（新类/冷启动）；
2. 对纯逻辑用 JVM 单测 + DAP（不依赖 Android ART）；
3. 对 native C/C++ 用 `lldb` 后端（需符号/attach 环境，当前未作为默认验证路径）；
4. 用 logpoint/条件断点降低停点数量，但仍要检查 `hitBreakpoints`；
5. 用沙盒日志/最小 probe 替代，并明确标注替代证据。

### 4.2 其他后端限制（来自底层 adapter/协议）

以下限制大多来自上一节的 adapter/协议，不是插件新增的语义。

- **lldb（CodeLLDB/LLDB）**：attach 常不可用/超时；launch 可用；快程序有断点 resolve 竞态；头文件/宏展开行可能不 resolve；同名源文件（如 `mod.rs`）会全部绑定；`all` 异常过滤有限制；Rust panic 行可能偏移。
- **java（JDWP/JVMTI）**：vars 需要 `-g`；eval 是迷你文法（字面量/局部变量/简单算术/比较），不是通用表达式；attach 场景 vars 可能为空；断点行吸附可能导致 codeIndex 偏移。
- **cs（netcoredbg）**：pause 不可用；attach 不可用；logpoint/hitCondition 受 netcoredbg 单次命中限制。
- **python（debugpy）**：单行 `while`/`sleep` 循环 pause 可能不触发 stopped 事件（程序已暂停但事件缺失）；attach 需要 debugpy `--wait-for-client`；`raised` 异常过滤会停在解释器内部异常。
- **node（CDP/Node Inspector）**：函数断点是源码定位启发式，方法/闭包不保证；threads 只有主线程；崩溃输出有秒级延迟。
- **通用**：DAP 停顿会改变时序，不能当性能测量；优化/裁剪构建、source map、远程/容器环境都可能改变断点行为。

---

## 5. 证据判定规则

只有同时满足以下条件，才算一次 **DAP 命中**：

1. `state=stopped` 且 `reason` 是断点/异常/步进/暂停；
2. `hitBreakpoints` 非空（断点场景）或明确是异常/步进停止；
3. `frame` 非空；`stack` 可读；
4. `vars` / `eval` 读到了**实际值**（不是对象身份 `Foo@123` 占位）。

以下都**不算** DAP 命中：

| 现象 | 判定 |
|---|---|
| `hitBreakpoints=[]` | 没命中 |
| `frames=[]` | 没有可用栈 |
| `vars={}` | 没有值 |
| `output=""` | 没有输出证据 |
| `pause` 后 `stopped` 但无 frame | 只能算“暂停成功”，不能 eval |
| `continue` 超时 | 没有停止，不是命中 |
| `state=exited` + `unverifiedBreakpoints` | 断点没绑上 |
| logcat/CLI/日志文本 | 替代证据，不是 DAP |
| `ClassName@N` 对象身份 | 读值不完整，不能当实际值 |

---

## 6. 失败分类与降级

DAP 失败先分类：

1. **工具**：手动精确指挥也失败（后端/adapter/协议缺陷）→ 记录错误，换后端/换路径；
2. **环境**：attach 不可达、端口冲突、符号缺失、ART/JDWP 限制 → 记录已尝试命令，换环境或降级；
3. **假设**：断点位置/条件/类加载时机不对 → 改断点、改假设、重跑。

降级路径（仅用于运行时证据）：沙盒日志 → 最小 probe → 单测 → logcat/数据库/界面。

到这里仍拿不到事实，就停止推进并报告用户，说明：

- 缺的是什么证据；
- 已经尝试了哪些路径、失败原因是什么；
- 需要用户提供什么（环境/权限/样本/调试目标/决策）。

静态推演只能用于形成假设或标注为 D 级推断，**不能替代运行时事实，也不能作为 DAP 的降级项**。如果只剩静态推演，该结论应标 `UNVERIFIED`，交给用户决定是否继续；不要为了推进而把它写成已验证。替代证据必须标注类型；DAP 不可用时写 `DAP-UNAVAILABLE` + 已尝试项。

---

## 7. 最小就绪检查

在把 DAP 作为证据来源之前，至少确认：

1. `dap_capabilities` 可调用，目标后端存在；
2. `dap_start` 的 launch/attach 能建立会话；
3. `dap_threads` 能看到预期线程；
4. 在一个**已知答案**的调试目标上，断点能命中并读到 `vars/eval`；
5. `dap_stop` 能清理会话，`dap_sessions` 为空，无孤儿进程；
6. Android 上不要用“已加载类”的断点做已知答案；用 JVM 单测或首次加载的新类。

任何一项失败，先配置/修复 DAP，再把它写进报告；不要用 attach/pause 冒充断点命中。

---

## 8. 与插件阶段的对应

- **逐块评估**：老代码 before 契约用 DAP；新代码不能停在准代码上，用隔离 harness/单测/沙盒。
- **验收**：状态迁移矩阵的每一行尽量用 DAP 读实际值；DAP 不可用则用 probe/log/DB/UI，并标 `UNVERIFIED`。
- **报告**：证据类型、DAP 命中情况、未命中原因、替代路径都要写清；插件不解析报告，但用户会看。

---

## 9. 维护

- 本文件描述的是**当前 DAP MCP 的契约与限制**，不是插件自带的 DAP 服务。
- `dap_capabilities` 是能力状态的单一事实源；实现更新后，本文件应同步更新。
- 任何“未实测”的能力都应标 `[未知]`，不要写成可用。

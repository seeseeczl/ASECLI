# 方案优化计划书：吸收 ASE Editor API 创建链路

> 生成时间：2026-09-01 19:06:56
> 项目根目录：/Users/long/GitHub/ASECLI
> Skill：first-principles

## 0. 原方案输入摘要

- 输入来源：用户口述的另一个会话执行方案；当前 AseCLI 仓库的 `README.md`、`src/asecli/bridge/recompile.py`、`src/asecli/cli/create_command.py`、`src/asecli/schema/data/schemas.json` 与质量文档。
- 原方案核心主张：通过 Unity MCP 在已经运行的团结编辑器进程内执行一次性 C#，直接调用 ASE 的 `CreateNewTemplateShader`、`CreateNode`、`ParentGraph.CreateConnection`、`SaveToDisk` 和 `LoadFromDisk`；对没有公开 setter 的节点字段、Custom Expression 内容和动态输入端口使用反射；最终 ShaderLab/HLSL 与 `ASEBEGIN` 均由 ASE 生成。
- 原方案关键约束：
  1. `SamplerNode`、`CustomExpressionNode` 等节点的序列化结构会随配置和端口变化，不能可靠地从单个默认 schema 猜造。
  2. 部分 ASE API 依赖真实 GUI 生命周期；从普通后台代码调用会触发“GUI functions 必须位于 OnGUI”。
  3. Caster 的投影矩阵属于运行时绘制状态，由 `VehicleLocalShadowBaker` 在 CommandBuffer 绘制前注入，不应伪装成静态 ASE 节点。
  4. 生成后的可编辑性以真实 ASE 窗口保存、关闭、重新打开后图和端口不丢失为准。
- 当前痛点 / 触发原因：AseCLI 已能离线解析、修改、布局、校验和触发 ASE 重存，但 `create` 仍是“克隆编译壳 + 注入图”，而 `SamplerNode`、`CustomExpressionNode` 被标记为 `layout_ok=false`，无法通过 schema 安全创建。一次性 C# 已证明 Editor API 路线可行，但没有保留为可复用、可校验、可回滚的正式能力。

## 1. 重写后的真实目标

- 目标：为了让 AI Agent 在重复创建包含动态/不透明节点的 ASE Shader 时获得可复现结果，需要在保留 AseCLI 离线快速链路的前提下，增加一个由真实 ASE API 负责“创建并序列化”的窄范围 Editor 后端，并把保存后重载、语义回读和失败回滚纳入统一契约。
- 非目标：
  - 不把所有 ASE 操作迁移回 Unity/团结编辑器。
  - 不用鼠标自动化搭图。
  - 不自行生成或伪造编译后的 ShaderLab/HLSL。
  - 不在用户项目中长期驻留自动生成工具或引入新的 Editor 插件依赖。
  - 首期不覆盖任意 ASE 节点、任意私有字段和任意旧版本。
  - 不把运行时矩阵、CommandBuffer 状态或每帧数据搬进静态节点图。
- 成功判据（可证伪）：
  1. 在隔离团结工程中，通过一份声明式 JSON 规格创建 Caster：`SamplerNode(_CasterMask) → Template Master Color`；保存并重载后节点类型、属性名和连接全部一致。
  2. 通过同一入口创建 Receiver：普通属性节点 + 一个具有多输入端口的 `CustomExpressionNode`；保存并重载后表达式正文、输入端口数量/名称/类型、Master 连接全部一致。
  3. 两个样例的 ShaderLab/HLSL 和 `ASEBEGIN` 均由 ASE `SaveToDisk` 生成；AseCLI 不提交手写编译区文本。
  4. Editor 后端失败时目标文件和 `.meta` 不发生半写入；已有目标可恢复到操作前 SHA-256，临时资产无残留。
  5. 现有离线命令和非 bridge 测试不回归；普通可安全 schema 化的节点仍无需启动编辑器。
- 硬约束（含证据）：
  1. 当前 `add-node` 仅允许 `source=runtime && layout_ok=true` 且 schema 版本与图版本完全匹配；`SamplerNode`、`CustomExpressionNode` 均不满足该条件。
  2. 当前 MCP `execute_code` 等同编辑器内代码执行，必须继续沿用 loopback 默认、显式远程 opt-in、token 脱敏和失败关闭。
  3. Editor API 后端必须在受支持的 ASE 版本和成员能力探测通过后才允许写入；反射字段不存在时禁止猜测或降级为手写节点行。
  4. 可编辑性验证与渲染等价性是两种证据；Save/Load 回读通过不能代替目标场景画面验收。

## 2. 拆解清单

| ID | 陈述 | 类型 | 处置 | 理由 |
| --- | --- | --- | --- | --- |
| D1 | AseCLI 必须比一次性 C# 更会调用 ASE API，才有存在价值 | ASSUME | 删除 | AseCLI 的价值是可重复编排、防错、批量和离线效率，不是排他性能力 |
| D2 | 动态节点应由当前安装的 ASE 实例创建和序列化 | FACT | 保留 | `SamplerNode` 和 `CustomExpressionNode` 的字段/端口随配置变化，默认 schema 不充分 |
| D3 | 所有节点都应改走 Editor API，避免直接文本操作 | ASSUME | 删除 | 已验证的静态节点、连线、布局和语义元数据离线处理更快、失败域更小 |
| D4 | 真实 ASE 窗口和当前 Graph 上下文可以绕过 OnGUI 限制 | FACT | 吸收 | 已有一次性方案成功；当前 `recompile` 也已通过窗口 + Layout/Repaint 事件处理 GUI 生命周期 |
| D5 | 反射可作为通用无限扩展入口 | ASSUME | 替换 | 反射只允许进入版本化白名单适配器；成员探测失败时停止 |
| D6 | SaveToDisk 成功就证明图可编辑 | ASSUME | 替换 | 必须再 LoadFromDisk/重新打开并对节点、端口、连接做语义清单回读 |
| D7 | 只要保存后图不丢失，就证明渲染结果正确 | ASSUME | 验证 | 保存/重载只证明编辑性；目标 Shader 仍需材质属性和真实画面验收 |
| D8 | Caster 投影矩阵也应在 ASE 创建流程中表达 | INHERIT | 删除 | 该矩阵是 CommandBuffer 绘制前注入的运行时状态，静态图只消费它 |
| D9 | 临时 C# 不保留可以减少项目污染 | PREFER | 保留结果、替换手段 | 不在用户 Assets 留脚本，但把固定受控执行器作为 AseCLI 包资源版本化保存 |
| D10 | 新后端需要支持修改任意已有复杂图 | ASSUME | 后置 | 首个真实缺口是“创建动态节点”；现有离线链路已覆盖多数修改，先做窄切片 |
| D11 | 直接复用真实序列化行可以替代 Editor API | ASSUME | 仅保留专家兜底 | 行内可能包含实例 ID、动态端口和版本私有布局，不应成为默认创建路径 |
| D12 | Editor 创建后端可以通过声明式规格安全驱动 | ASSUME | 验证 | 需要用 Caster/Receiver 两个样例证明规格足够且不演变成任意 C# 执行入口 |

## 3. 伪约束击穿

| 被击穿的假设 | 新认识 | 设计含义 |
| --- | --- | --- |
| “纯文本或 Editor API 必须二选一” | 静态、已验证结构适合离线；动态/私有结构适合由 ASE 自己序列化 | 后端按能力路由，不建立两套同等范围的实现 |
| “Editor 后端就是把一次性 C# 原样保存” | 真正缺失的是稳定规格、版本门禁、事务、回读和机器可判定结果 | C# 只是受控执行器，Python CLI 仍拥有输入校验和结果契约 |
| “反射成功一次即可长期复用” | 私有成员名是版本相关实现细节 | 反射入口必须白名单化并绑定 ASE 版本/能力探测 |
| “新建成功就是交付完成” | 创建、可编辑、编译成功、材质绑定和画面正确是不同验收层 | 自动门禁分层报告，不把 Save/Load 当成视觉验收 |
| “运行时数据也应该进入节点图，图才算完整” | Shader 图负责算法与可编辑参数，运行时系统负责每帧矩阵和绘制状态 | 保持 Baker/CommandBuffer 注入边界，不制造假属性或伪节点 |

## 4. 候选方案（2–3）

### 方案 A：继续纯文本，为动态节点增加专用序列化器

- 核心机制：为 `SamplerNode`、`CustomExpressionNode` 编写专用 Python 编解码器和字段生成逻辑，继续完全离线创建。
- 删除了什么：Editor 创建后端、GUI 生命周期管理。
- 关键风险：需要复制 ASE 的动态端口、私有字段和版本迁移逻辑；与“不猜造不透明结构”的现有安全策略冲突。
- 验证方式：将 Python 产物交给真实 ASE 打开、重存并比较语义清单；任何版本差异都需继续维护逆向规则。

### 方案 B：窄范围混合后端（推荐）

- 核心机制：AseCLI 先验证声明式 `EditorGraphSpec v1`；普通节点仍走离线 core，遇到新建 Shader 或 `layout_ok=false` 动态节点时，调用固定的 ASE Editor API 执行器。执行器只支持首期白名单操作：创建模板、创建属性/Sampler/CustomExpression、配置动态端口、连接、保存、重载、回传语义清单。
- 删除了什么：默认 raw 节点行猜造、每个任务临时生成一套 C#、全量 Editor 化、用户项目常驻脚本。
- 关键风险：ASE 私有字段和 OnGUI 生命周期随版本变化；需要能力探测、隔离真实 Editor 测试和失败恢复。
- 验证方式：Caster/Receiver 两个真实 Editor 夹具；在 Save→Load 后逐项核对 manifest，并验证失败注入不会污染目标。

### 方案 C：所有创建和修改全部走 ASE Editor API

- 核心机制：废弃大部分纯文本 mutation，统一在 ASE 窗口当前 Graph 上调用 API。
- 删除了什么：schema 驱动离线 add/set/connect 的主要价值。
- 关键风险：每次操作都依赖编辑器/MCP；秒级延迟、会话占用、GUI 状态和调试链显著扩大，且重复实现已有稳定功能。
- 验证方式：对同一批图操作比较端到端时间、失败率和差异可审计性。

## 5. 推荐方案

- 选择：**方案 B——窄范围混合后端**。
- 为何优于增量修补：它不继续给动态节点堆手写字段特例，也不推翻已验证的离线架构；只把 ASE 自己最擅长且 AseCLI 当前无法安全表达的“动态节点创建与序列化”交回 ASE。
- 明确放弃的东西：首期不做任意节点、任意反射、任意已有图 API 修改；不提供任意 C# 透传；不把 raw `--line` 升级为推荐路径；不宣称 Save/Load 等于渲染等价。
- 原方案 vs 新方案对照：

| 维度 | 当前 AseCLI | 吸收后 | 处置 |
| --- | --- | --- | --- |
| 新 Shader | 克隆编译壳并替换/修改 `ASEBEGIN` | 可选 `--backend editor` 调 `CreateNewTemplateShader` | 增量新增 |
| 普通节点 | schema 驱动离线创建 | 保持不变 | 保留 |
| 动态节点 | `layout_ok=false`，拒绝或要求真实 raw 行 | ASE API 创建，反射白名单配置 | 替换默认兜底 |
| 连线 | 离线写 `WireConnection` | Editor 创建事务内用 `ParentGraph.CreateConnection`；后续普通修改仍离线 | 按场景路由 |
| 编译/序列化 | 最后 `SaveToDisk` 重编译 | 创建时即由 ASE 生成；CLI 再 parse/validate | 强化 |
| 验收 | `saved=true`、文件 hash、结构校验 | Save→Load→manifest 回读→结构校验→目标画面分层报告 | 强化 |
| C# 形态 | Python 内嵌重编译片段 | AseCLI 包内版本化固定执行器；用户项目零常驻 | 重组 |
| 运行时矩阵 | CLI 未定义 | 明确留在 Baker/CommandBuffer，不进入创建规格 | 固化边界 |

### 推荐的最小接口

```text
asecli create <target.shader> --backend editor --spec <graph.json>
asecli create <target.shader> --backend auto   --spec <graph.json>
```

- `auto`：规格全部可由安全 schema 表达时走离线；包含模板创建、Sampler、CustomExpression 或其他不透明节点时走 editor。
- `graph.json` 只描述受限语义操作，不接受任意 C#。Custom Expression 的 HLSL 正文作为节点数据传递，但最终 ShaderLab/HLSL 仍由 ASE 生成。
- 首期只扩展 `create`；不新增通用 `apply-via-editor`，待两个真实场景证明必要后再决定。

## 6. 优化实施计划

| 任务 ID | 优先级 | 内容 | 验收标准 | 依赖 | 风险/回滚 |
| --- | --- | --- | --- | --- | --- |
| FP-ASE-001 | P0 | 定义 `EditorGraphSpec v1` 和后端路由契约：模板、Property、Sampler、CustomExpression、端口、连接、目标路径、预期 manifest；禁止任意 C# 和任意反射字段 | JSON schema 能完整表达 Caster/Receiver；未知字段、重复别名、错误端口类型在调用 MCP 前失败；现有 CLI JSON 契约不变 | — | 规格只作为新增输入；不启用 editor 后端即可回滚 |
| FP-ASE-002 | P0 | 提取可复用 ASE 窗口生命周期执行器：保存/恢复 `UIUtils.CurrentWindow` 与 Selection，在真实窗口/当前 Graph 上执行，发送必要 GUI 事件并在 `finally` 关闭销毁 | 正常、异常、取消三条路径均无窗口泄漏；OnGUI 错误不再出现；原 `recompile` 共用同一生命周期实现且回归通过 | FP-ASE-001 | 若共用改造影响现有桥，先保留旧 `recompile` 片段并让新后端独立试验 |
| FP-ASE-003 | P0 | 实现版本门禁和白名单节点适配器：调用 `CreateNewTemplateShader`、`CreateNode`、`CreateConnection`；仅为 Sampler/CustomExpression 的已知字段和动态端口使用反射 | 返回 ASE 程序集版本、图版本、已解析成员清单；成员缺失/版本未验证时零写入并返回稳定错误；不得自动退化为 raw 行 | FP-ASE-002 | 版本不支持时关闭 editor create，保留现有模板克隆路径 |
| FP-ASE-004 | P0 | 增加事务式创建与语义回读：在项目内隔离暂存资产上创建，`SaveToDisk` 后重新 `LoadFromDisk`/重新打开，回传节点、端口、属性、连接 manifest；成功后再提交目标 | 失败注入覆盖创建中断、Save=false、Load 失败、manifest 不一致；目标 SHA/`.meta` 保持或恢复；暂存资产和 `.meta` 清零 | FP-ASE-003 | 若安全移动资产不可稳定实现，首期限制目标必须不存在，并在失败时用已锁定的明确暂存路径恢复/清理 |
| FP-ASE-005 | P1 | 接入 `create --backend auto|text|editor --spec`，延续 dry-run、loopback、token 脱敏、单行 JSON、退出码和 `.bak`/冲突检测；Editor 成功后再走现有 parse/validate | `text` 行为逐字节兼容；`auto` 路由可解释；editor 返回 `saved/reloaded/manifest/changed`；MCP 失败不报告假成功 | FP-ASE-004 | 默认后端先保持 `text` 一个版本周期；出现回归可关闭 editor feature flag/入口 |
| FP-ASE-006 | P1 | 建立两级验收：隔离工程中的 Caster/Receiver 真实 Editor E2E；目标项目单独做材质属性、运行时矩阵注入和画面验收。同步 Skill/质量边界，正式保留受控执行器而删除一次性原型依赖 | 自动测试全绿；真实 E2E 两次连续创建/重载 manifest 一致、Console 0 error；Caster/Receiver 图可编辑；目标画面证据单列，不以结构测试替代 | FP-ASE-005 | 真实渲染不一致时只回退目标 Shader，不否定 editor create 的结构能力；停止推广 `auto` |

## 7. 残留假设与验证实验

| 假设 | 低成本实验 | 失败时的回退 |
| --- | --- | --- |
| MCP `execute_code` 中可稳定完成 `CreateNewTemplateShader` 并驱动所需 GUI 生命周期 | 在隔离工程只创建一个空模板，发送 Layout/Repaint，Save→Load，重复 3 次并检查窗口/Console | 将创建动作做成受控的 `EditorApplication.delayCall` 状态机；仍不落用户项目常驻脚本 |
| 一份受限规格足以表达 Caster/Receiver，而无需任意 C# | 用真实节点参数反推两份最小 JSON，检查是否只有 Custom Expression HLSL 属于自由文本 | 给特定节点增加语义字段；不开放反射字段名或 C# 代码透传 |
| 暂存资产可以在成功后安全提交到目标路径并正确处理 `.meta` | 在临时项目验证新建、目标已存在、保存失败三种路径的 AssetDatabase 行为和文件 hash | 首期仅允许创建不存在的目标；已有目标继续走当前 `create --force` + `.bak` 链路 |
| ASE 版本差异可以通过能力探测而非完整多版本框架控制 | 在当前已用版本上读取程序集版本、方法签名和目标私有成员；篡改一项预期验证失败关闭 | 只支持一个明确版本 Profile，其他版本返回 `UNSUPPORTED_ASE_VERSION` |
| Save→Load manifest 足以证明可编辑性 | 关闭窗口后重新打开，比较节点数/类型、CustomExpression 输入、连接和 Material.HasProperty | 增加专用回读字段；仍把像素/运行时结果留给目标工程验收 |

## 8. 下一步建议

- 是否需 `$adversarial-audit`：需要。在 FP-ASE-001～005 形成可运行切片后，重点攻击任意代码注入、反射越权、暂存资产清理、目标覆盖、窗口泄漏和“saved 文本假成功”。
- 是否需 `$project-architect` 治理落盘：实施前需要建立一个增量 CR/ADR，将 MOD-BRIDGE 的职责从“重编译”扩展到“受控 Editor 图创建”，并更新需求、模块地图、追溯矩阵、测试策略和回滚协议；本计划阶段不修改这些治理文件。

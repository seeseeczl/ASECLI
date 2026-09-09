# Shader Graph → ASE 转换器功能需求说明

- 日期：2026-09-07
- 状态：待另一会话立项，尚未登记为 ASECLI 的 FR/CR
- 写手前提：ASE 图的创建、校验、布局、编译只通过现有 ASECLI，不另写 ASE 文本

下一会话把本文当作唯一需求基线。先对齐范围，再设计实现；不要把转换器做进 `asecli` 现有 16 个命令里。

---

## 1. 背景与要解决的问题

ASECLI 已经能按 ASE 能看见的词汇表写图：模板 Master、Property/Sampler、白名单普通节点、Custom Expression、连线，并走 `validate` / `layout` / `recompile`。

现在缺的是：读 Unity Shader Graph（`.shadergraph`），把它降成 ASE 画布上真实存在的节点图，再交给 ASECLI 落盘。

目标用户打开结果时，应看到一张可编辑的 ASE 图，而不是一段无法拆开的编译 HLSL。

## 2. 一句话目标

读一份 Shader Graph，输出 ASECLI 能直接 `create --backend editor` 的 `EditorGraphSpec v2` JSON；属性变量名、数值范围、精度按 ASE 语义平移；Shader Graph 没有对应 ASE 节点时，降级为 Custom Expression。

## 3. 非目标

- 不宣称无损、不保证 SG → ASE → SG round-trip。
- 不把 Shader Graph 的 Master Stack、Target、Keyword 面板、Blackboard UI 原样搬进 ASE。
- 不输出 `/*ASEBEGIN*/` 原文、不输出整份编译 ShaderLab 当“转换结果”。
- 不把 Shader Graph 代码生成器的 `#include` / 宏原样贴进 Custom Expression。
- 不在第一期支持 HDRP、VFX Graph、Shader Graph UI Target、复杂 Sub Graph 资源身份保留。
- 不修改用户生产 Shader，除非用户在该会话明确指定隔离输出路径。
- 不把转换逻辑做成 `asecli` 核心子命令；ASECLI 只当写手。

## 4. 系统边界

```
.shadergraph
    → 转换器（本需求）
        → graph.json     EditorGraphSpec v2（给 ASECLI）
        → report.json    降级/改名/精度/范围对照（给人与 Agent）
    → asecli create --backend editor --spec graph.json
    → asecli validate
    → asecli layout（可选）
    → asecli recompile
```

转换器负责：解析 SG、降级、生成两份 JSON。
ASECLI 负责：创建 ASE 资产、CHKSM、结构校验、排版、编译。

内部 IR 可以自定，不得作为对外契约。对外机器契约只有 `graph.json`。

## 5. 输入

- 主输入：Unity Shader Graph 资产 `.shadergraph`（YAML）。
- 绑定版本（第一期必须写死，未知版本失败关闭）：
  - ASE `1.9.6.2`
  - 团结/Unity 版本与现有 ASECLI Editor 创建证据对齐（当前隔离证据为团结 `2022.3.61t9` 或后续已验证版本）
  - Shader Graph 以该编辑器内实际可打开的 URP Unlit 图为第一期样本
- 第一期只接受能映射到 ASE URP Unlit 模板的图。模板 GUID 固定为：

  `2992e84f91cbeb14eab234972e07ea9d`

  Master 输入端口契约（ASECLI 已有）：

  | 端口 | 类型 | 含义 |
  | --- | --- | --- |
  | 0 | FLOAT3 | Baked Albedo |
  | 1 | FLOAT3 | Baked Emission |
  | 2 | FLOAT3 | Color |
  | 3 | FLOAT | Alpha |
  | 4 | FLOAT | Alpha Clip Threshold |
  | 5 | FLOAT3 | Vertex Offset / Position |
  | 6 | FLOAT3 | Vertex Normal |
  | 7 | FLOAT | Alpha Clip Threshold Shadow |

- 无法判断 Target / Stack 时失败关闭，不得猜模板。

## 6. 输出契约

### 6.1 `graph.json` — EditorGraphSpec v2

现有字段必须合法，可被当前 `asecli create --spec` 解析。连接方向必须是 ASE 数据流，不是 ASE 文件里 `WireConnection` 的字段顺序：

- `from`：数据源（输出端口）
- `to`：消费者（输入端口）
- Master 不得作为 `from`
- 同一输入口最多一条入边
- `nodes` 按从左到右拓扑排列，Master 只出现在连接的 `to` 端
- 视觉含义：数据从左向右，Master 在最右

节点 `kind` 只允许 ASECLI 已支持的四种：

| kind | 用途 |
| --- | --- |
| `property` | 属性节点。Float 滑条必须用 `RangedFloatNode` |
| `sampler` | 贴图采样器 / 贴图属性采样 |
| `node` | 当前 generic allowlist 内的普通节点 |
| `custom_expression` | 无 ASE 同义节点时的降级 |

Property / Sampler 仍须满足 ASECLI 属性呈现契约：

- `property_name`：Shader 变量名
- `inspector_name`：含中文的显示名
- `tooltip`：含中文
- `parameter_type`：`Property` / `Constant` / `InstancedProperty` / `Global`

### 6.2 必须平移的属性语义（当前 Spec 若缺字段，先作为加性提案）

当前 EditorGraphSpec v2 **还没有** `precision` / `default` / `min` / `max`。本需求要求转换器 IR 必填这些语义；落地时二选一，不得静默丢弃：

1. 先给 ASECLI 提加性 CR，扩展 v2 字段后再 `create`；或
2. 第一期 `create` 后用已验证的语义命令写入范围/精度，禁止 `set-field` 猜私有槽位。

平移规则：

- **变量名**：优先原样复制 Shader Graph `referenceName`。必须匹配 `^_[A-Za-z][A-Za-z0-9_]{0,126}$`。合法则不得改名。
- **显示名**：SG display name 若已含中文可用；否则转换器生成中文 `inspector_name`，并在 `report.json` 标记“显示名机翻/待审”。不得用中文显示名覆盖变量名。
- **默认值**：原值平移，不自行归一化到 0–1。
- **数值范围**：SG Slider/Range 的 min/max 写入 ASE `RangedFloatNode`（或后续 Vector 范围字段）。没有范围的 Float 不要无故变成 0–1 滑条。
- **精度**：SG `Single` → ASE `Float`；`Half` → `Half`；`Inherit` → `Inherit`。普通节点与 Custom Expression 都带精度；降级节点继承被替换 SG 节点的精度。

非法变量名才允许改名（补前导下划线、去掉非法字符）。`report.json` 必须记录旧名 → 新名。

### 6.3 `report.json`

给人与 Agent 看，不喂给 `create --spec`。至少包含：

- 源文件、SG/ASE/编辑器版本
- 选用的模板 GUID
- 节点对照表：SG 节点 id/类型 → ASE alias/kind/type
- 降级为 Custom Expression 的清单及原因
- 属性对照：变量名、显示名、default、min、max、precision
- 改名清单
- 未映射的 Stack Block / Keyword / Sub Graph
- `structural_ok` / `visual_validation=requires_editor_review`

## 7. 节点降级规则

按优先级：

1. ASE 有稳定同义节点，且在 ASECLI 允许创建的类型内 → `kind: node` / `property` / `sampler`。
2. 否则 → `kind: custom_expression`。
   - 输入口名称、类型与 SG 节点输入对齐（映射到 ASECLI 的 `INT/FLOAT/FLOAT2/.../SAMPLER2D` 等白名单类型）。
   - `code` 必须是可在 **ASE 模板 / Unity 着色库** 下编译的 HLSL，禁止原样粘贴 Shader Graph 生成代码及其 include。
   - 一个 SG 节点对应一个 Custom Expression，不要把整张图收成一个黑盒函数。
3. SG Fragment/Vertex Stack Block → 接到上表 Master 端口。对不上的 Block 失败关闭或写入 report 并拒绝该图，第一期不要猜。
4. Sub Graph 第一期：内联摊平进同一张 ASE 图，或失败关闭。不要假装保留独立 `.asset` 函数身份，除非另开需求。

第一期建议白名单（可在实现时用真实 SG 样本修订，但不得默默扩大）：

- 属性：Float（含 Range）、Vector、Color、Texture2D
- 数学：Add / Subtract / Multiply / Divide / Lerp / Saturate / One Minus 等可直接对应的 ASE 节点
- 采样：Sample Texture 2D → Sampler
- UV / Position 等 ASECLI generic allowlist 已有类型：`WorldPosInputsNode`、`TextureCoordinatesNode`、`BreakToComponentsNode`

不在白名单且无法安全写成 Custom Expression 的节点：整图失败关闭，列出节点 id。

## 8. 成功标准

结构（自动 + ASECLI）：

1. `graph.json` 能通过当前 `EditorGraphSpec.from_dict`（若已扩展字段，则以扩展后的校验为准）。
2. `asecli create --backend editor --spec graph.json` 在隔离工程成功，目标位于 `Assets/` 且事先不存在。
3. `asecli validate` 无 error。
4. 重新打开 ASE：节点类型、连线、Custom Expression 输入名/类型/代码、属性 `property_name`、范围、精度与 spec/report 一致。
5. 公开属性的 Shader 变量名与源 SG `referenceName` 一致（仅 report 中登记过的改名除外）。
6. Float 滑条的 min/max/default 与源 SG 一致（允许浮点误差 1e-5）。
7. 精度与映射表一致。

视觉 / 渲染（必须单独报告，不得用结构成功冒充）：

- 真实 ASE 画布：节点从左到右、Master 最右、连线可追踪。
- 目标工程材质与画面：列为待验收；第一期可用“结构通过 + 画布可编辑”交付，但文档必须写明画面未证明。

## 9. 失败关闭

出现以下情况必须停止写入：

- 无法识别 `.shadergraph` 或版本不在允许集
- 模板/Target 不是第一期 URP Unlit
- `property_name` 无法变成合法 Shader 标识符
- Custom Expression 代码含 ASE 分隔符或 C# 运行时标记（沿用 ASECLI 现有拒绝规则）
- 需要 `set-field` 猜 Master 或未知私有字段才能补范围/精度
- 输出路径在 `Assets/` 外，或目标已存在

## 10. 第一期垂直切片（建议下一会话先做这个）

样本：一张最小 URP Unlit Shader Graph，包含：

- 一个 Range Float 属性（非 0–1 默认值，带 min/max）
- 一张 2D 贴图采样
- 若干可映射数学节点
- 接到 Color / Alpha

交付：

1. 转换器 CLI 或脚本：输入 `.shadergraph`，输出 `graph.json` + `report.json`
2. 用 ASECLI Editor 创建、validate、隔离工程重开对账
3. 需求中明确哪些 SG 节点走原生 ASE、哪些走 Custom Expression

不要第一期做 HDRP、Keyword、完整 Lit Stack、动画/材质升级迁移工具。

## 11. 给下一会话的启动提示

新会话第一轮直接粘贴：

```text
根据仓库 ASECLI 文档 docs/proposals/2026-09-07-shadergraph-to-ase-requirements.md 做第一期：SG → ASE。

产品形态：
- 新建独立 CLI，工作名 SGCLI，不要做成 Unity/团结引擎内工具，也不要做成 asecli 的子命令。
- asecli 只当 ASE 写手。SGCLI 读 .shadergraph，写出 graph.json + report.json，再调用 asecli create / validate。
- 对照表（SG 节点 → ASE 原生节点或 custom_expression 模板）必须是可版本化的 JSON 数据，跟 SGCLI 一起发布，方便以后更新。不要把规则写死在 C# 或 Editor 菜单里。
- 第一期不要做：通用 JSON 的 add-node/connect 编辑器、asecli export（ASE→JSON）、ASE→SG、引擎窗口、HDRP、Keyword、完整 Lit Stack。通用中间格式可以在 SGCLI 内部先用，但对外先只保证 graph.json 能喂给 asecli。

硬约束：
- 最高优先是一张真实 URP Unlit Shader Graph 变成隔离工程里可编辑的 ASE 图，作为 ASE 可用素材；结构通过不等于画面通过。
- graph.json 必须是 EditorGraphSpec v2。连接 from=数据源、to=消费者，Master 只出现在 to；nodes 按 ASE 从左到右排。
- 属性变量名原样平移（合法 _Identifier 不得改名）；同时平移 default / min / max / precision。当前 Spec 缺这些字段时，先给 ASECLI 做加性扩展或用已验证语义命令写入，禁止 set-field 猜私有槽位。
- 无 ASE 同义节点时用 custom_expression；HLSL 按 ASE/Unity 库重写，禁止粘贴 Shader Graph 生成代码。
- 第一期只支持 ASE 1.9.6.2 + URP Unlit 模板 GUID 2992e84f91cbeb14eab234972e07ea9d。
- 不要写生产 Shader，不要宣称无损。开始前先读 ASECLI 的 EditorGraphSpec 校验和 README 的 create --backend editor，列出 Spec 要加的字段再动手。
```

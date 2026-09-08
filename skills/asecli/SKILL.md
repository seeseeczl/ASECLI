---
name: asecli
description: Create, modify, validate, and strictly lay out Amplify Shader Editor (ASE) graphs; configure explained material properties, native Comment frames, and compilation through asecli. Use for ASE shader work in Unity or Tuanjie, especially when graph layout or canvas readability matters.
---

# AseCLI — Agent 操作 ASE Shader 指南

当任务涉及节点图新建、转换、整理或验收时，先读取本文引用的“ASE 节点图精排规范”；它是 ASECLI 交付物的一部分，不是临时 Agent 记忆。离线结构检查和真实 ASE 画布视觉验收必须分开报告。

从 SG JSON/EditorGraphSpec 创建或整理转换图时，还必须读取 [转换后图交付流程](references/conversion-workflow.md)。以当前 Shader 为基线，先 `graph-review` 锁定计算连接/常量，再处理复用、递归鱼骨与计算岛；不得把 JSON 初排或创建成功当作完成。`graph-review` 是只读计划与对照，不是自动 Local Var 创建器。用户明确指定按输出端口两次消费注册时，用 `--reuse-policy fanout` 覆盖本任务默认门槛，不修改其他任务的消费组策略。

## Agent 兼容性

本 Skill 遵循通用 Agent Skills 目录结构：标准 YAML frontmatter、`SKILL.md` 正文和相对路径引用。它只要求 Agent 能运行本地 shell 命令并读取 ASECLI 的单行 JSON，不依赖 Codex、Claude Code、Cursor、Gemini CLI 或 GitHub Copilot 的专属工具名、权限模型或消息格式。

- Codex、Cursor、Gemini CLI 与 GitHub Copilot 可从 `.agents/skills` / `~/.agents/skills` 发现本 Skill。
- Claude Code 使用 `.claude/skills` / `~/.claude/skills`。
- 安装到所有主流 Agent：`asecli install-skill --agent all`。
- 随仓库共享：`asecli install-skill --agent all --scope project --project-root <项目目录>`。

执行下文命令时，使用当前 Agent 自带的 shell/terminal 能力即可；不要假定存在某一家 Agent 的专属调用 API。若当前运行环境不允许写文件、连接 Editor 或访问目标工程，应明确报告该层未执行，不得把静态检查冒充实际写入或 Editor 验收。

## 核心事实（必读）

1. ASE 节点图以纯文本嵌在 `.shader` 文件的 `/*ASEBEGIN ... ASEEND*/` 块中，行式格式。
2. `WireConnection;<入节点>;<入端口>;<出节点>;<出端口>` —— **目的地在前，来源在后**。
3. `//CHKSM=` 是 SHA1（大写 hex），对 `//CHKSM=` 之前的**整个文件**计算；校验失败**不阻断** ASE 加载。
4. `connect --from` 是输出端（数据源），`--to` 是输入端（消费者）。
5. Master 节点（TemplateMultiPassMasterNode 等）布局为 opaque，只能整行替换或用 `layout` 移动。
6. 自定义材质面板分两层：ASE 图只序列化主 Master 的 `CustomEditor` 与 PropertyNode 尾部属性，Unity `ShaderGUI` 负责实际显示。先用 `gui-support` 选择唯一 provider：原生 MZGUI 存在则使用它并只补 authoring/条件 Drawer，确认缺失才安装 ASECLI fallback；两者统一使用 `FoldoutMzgui`、`TooltipMzgui`、`HelpBoxMzgui`、`EnableIfMzgui`。工具默认只生成 Tooltip 说明，HelpBox 仅由用户显式添加。未知 ASE 尾部不得猜写。
7. PropertyNode 绝对字段 9 是 `m_orderIndex`，决定材质 Inspector 顺序；ASE `CommentaryNode` 保存框尺寸、说明、成员 ID、标题和颜色，必须用语义命令维护可变长字段。

## 三条链路

### 链路 A：查看图（无 Unity）

```bash
asecli parse <file>          # 节点/连线摘要
asecli validate <file>       # 结构校验（悬空线/重复ID/CHKSM）
```

### 链路 B：修改图（无 Unity，毫秒级）

```bash
# 改属性值（field 为绝对下标：0=Node, 1=类型, 2=Id, 3=坐标, 4+=参数）
asecli set-field <file> --node 5 --field 12 --value 0.85 --write

# 加节点（schema 驱动，自动补参数默认值）
asecli add-node <file> --type AmplifyShaderEditor.SaturateNode --id 99 --pos -320,0 --write

# 连线：把 99 的输出 0 接到 6 的输入 0
asecli connect <file> --from 99:0 --to 6:0 --write

# 删节点（自动清理附属连线）
asecli remove-node <file> --node 99 --write

# 兼容布局（分层对齐等距，只动 x/y）
asecli layout <file> --write

# 递归鱼骨式精排：单次读取 ASE 真实节点/标题/端口尺寸
asecli layout <file> --mode meticulous --audit --mcp-url http://127.0.0.1:8080/mcp
asecli layout <file> --mode meticulous --write --mcp-url http://127.0.0.1:8080/mcp

# 显式授权 WireNode 路由；默认精排不移动或新增走线锚点
asecli layout <file> --mode meticulous --route-wires --audit --mcp-url http://127.0.0.1:8080/mcp
asecli layout <file> --mode meticulous --route-wires --write --mcp-url http://127.0.0.1:8080/mcp

# 修复 checksum（默认只预览；显式写入会保留 .bak）
asecli fix-checksum <file> --write
```

创建、转换或重新整理节点图时，必须先读 [ASE 节点图精排规范](references/layout-standard.md)。核心目标是严格对齐、从左到右层层递进、重复结构一致和整体“经过精心排列”的秩序感；不是机械追求零交叉。

选择或整理 Master / Output 节点设置时，必须先读 [ASE Master / Output 设置规范](references/master-output-settings-standard.md)。上方基础生成设置默认保持模板和现有 Shader 原值，以最大平台兼容性为先；下方功能开关按真实需求选择，并避免无用 Pass、变体和重复计算。Master 序列化仍视为 opaque，不得用通用字段写入猜改。

### 链路 C：提示文案与分组（写元数据不需要 Unity，最终生效需要重编译）

创建或整理公开材质属性时，必须先读 [ASE 材质属性呈现规范](references/material-property-standard.md)。CLI 以 `asecli.property-presentation.v2` 强制：中文显示名；每个公开属性一条中文 Tooltip；GUI 自动追加英文变量名与 Shader 默认值。HelpBox 不必填、不参与门禁，只在用户明确提供内容时写入。中文 Foldout 按材质功能层组织，组内按开关、输入、颜色、混合和表面响应的实际依赖顺序排列。

```bash
# 检查唯一 provider；仅 provider=missing 时才安装 Editor fallback
asecli gui-support /path/to/UnityProject
asecli gui-support /path/to/UnityProject --write
asecli gui-support /path/to/UnityProject --runtime-probe --handoff-native
asecli gui-support /path/to/UnityProject --runtime-probe --handoff-native --write

# 先查询，返回主 Master/编译区 Inspector 是否一致，以及可操作的 PropertyNode id
asecli custom-gui <file>

# 使用 gui-support 返回的 recommended_editor。给组内首项加折叠标题和中文悬浮说明
asecli custom-gui <file> --editor MZGUI.MZGUI --property _PaintColor \
  --group "固有色" \
  --tooltip "控制车辆基础漆面颜色。Alpha 当前不参与透明度计算。"
asecli custom-gui <file> --editor MZGUI.MZGUI --property _PaintColor \
  --group "固有色" \
  --tooltip "控制车辆基础漆面颜色。Alpha 当前不参与透明度计算。" --write

# Tooltip 是默认且必填的属性说明渠道，不能清空后正式写入
asecli custom-gui <file> --property _Contrast \
  --tooltip "车身明暗对比度，数值越大，对比越小" --write

# 由另一个数值属性控制是否可编辑；条件不满足时只置灰，不清空原值
asecli custom-gui <file> --property _BaseEnvironmentTint \
  --enabled-if _BaseReflectionSource --enabled-if-operator Equal \
  --enabled-if-value 2 --write

asecli validate <file>
asecli recompile <file>
```

若返回 `provider=native_mzgui`，使用工程已有 MZGUI；`gui-support --write` 只安装 authoring/条件 Drawer，不创建第二个 provider。若安装了 `asecli_compat`，则使用 fallback。等待 Unity 编译后打开 `Window > Amplify Shader Editor > MZGUI Attributes (ASECLI)`；在 ASE 中选择一个 Property 节点，用 Foldout/Tooltip/HelpBox/条件启用控件编辑，点击“应用并保存 Shader”。不要让用户手写 Custom Attribute 字符串。

- `--group` 写 `FoldoutMzgui`，`--tooltip` 写 `TooltipMzgui`。把 group 加在组内第一个 PropertyNode；后续属性归入该组，直到下一个非空分组标题。
- Property 的公开显示名强制包含中文；创建新节点时使用 EditorGraphSpec v2/v3 的 `inspector_name`，已有节点通过 `custom-gui --spec` 的 `display_name` 原子修改图字段与编译区标签。
- 选中的 ShaderGUI（原生 MZGUI 或 ASECLI fallback）会自动在 Tooltip 末尾追加变量名与默认基线，并从默认 `Material(shader)` 读取真实 Shader 默认值；Tooltip 正文写用途、调节方向、通道、单位或限制，不手工抄写技术信息。
- HelpBox 是用户可选内容：工具默认不创建，也不把存在 HelpBox 视为违规。用户可用 `--help-box`、`--clear-help-box` 或批量 spec 的可选 `help` 字段增删；它不能替代必填 Tooltip。
- 条件置灰用 `enabled_if` / `--enabled-if` 写为 `EnableIfMzgui(source,operator,value)`。支持 `Less`、`LessEqual`、`Equal`、`NotEqual`、`GreaterEqual`、`Greater`；控制属性缺失或多选材质并非全部满足时置灰。它只控制 Editor 可编辑状态，不清空值，不代替 Shader Keyword、Static Switch 或运行时分支。
- 新增属性前必须运行 `gui-support` 并使用其 `recommended_editor`：原生与 fallback 的公共 Editor 名均为 `MZGUI.MZGUI`；确认缺失时才以 `--write` 注入 fallback。检测不确定或两者共存时停止；两条路径都写标准 `*Mzgui` 标记。fallback 工程生成的 Shader 移入原生 MZGUI 工程时不得改写 `CustomEditor`。
- fallback/原生扩展不修改 ASE 源码，也不绑定固定 ASE 版本号；EditorWindow 运行时探测 ASE 窗口、选中 Property、Custom Attributes、Master Custom Editor 和 Save 能力。成员变化时显示错误并停止写入。打开图时从编译 Shader 补齐 Foldout/Tooltip/HelpBox/EnableIf；应用时保留或按用户选择更新这些元数据。
- 原生 MZGUI 后装导致双 provider 时，仅在 V2 runtime probe 确认唯一 native、唯一已知 fallback 和原生 authoring capability 后使用 `--handoff-native`；默认 dry-run。交接保留 authoring-only bridge 做 Custom Attributes→原生 Toggle/文本迁移，唯一 provider 复验失败可恢复。
- `--add-attribute` 接受 `FoldoutMzgui`、`TooltipMzgui`、`HelpBoxMzgui`、`EnableIfMzgui` 及对应旧标记；正式写入仍需满足 Tooltip 契约。
- `--write` 同步图内主 Master 与编译区 `CustomEditor`、重算 CHKSM 并生成 `.bak`；Property 声明仍必须经 `recompile` 由 ASE 正式生成。

### 批量整理属性的规范

当用户要求“整理材质属性、分组并补说明”时，创建 JSON 规范并一次应用；不要逐条写盘。数组顺序就是最终顺序，未列属性保持原相对顺序并追加。JSON 的 `editor` 使用 `gui-support` 返回的 `recommended_editor`：

```json
{
  "editor": "MZGUI.MZGUI",
  "reorder": true,
  "properties": [
    {"name": "_PaintColor", "display_name": "车漆颜色", "group": "固有色", "tooltip": "控制车辆基础漆面颜色。Alpha 当前不参与透明度计算。"},
    {"name": "_Contrast", "display_name": "明暗对比", "tooltip": "控制车身明暗对比度；数值越大，对比越弱。", "enabled_if": {"property": "_BaseReflectionSource", "operator": "Equal", "value": 2}},
    {"name": "_Coat_IO", "display_name": "清漆开关", "group": "清漆层", "tooltip": "控制是否启用清漆层。"},
    {"name": "_CoatSaturation", "display_name": "清漆饱和度", "tooltip": "控制清漆饱和度；饱和度越高，反射强度越弱。"},
    {"name": "_FresnelPow", "display_name": "菲涅尔范围", "tooltip": "控制菲涅尔边缘范围；数值越大，边缘范围越窄。"},
    {"name": "_HDRLitTex", "display_name": "光照数据贴图", "tooltip": "R 通道为直接光，G 通道为反射 GI，B 通道为清漆数据；编码为 RGB9e5 32 bit。"}
  ]
}
```

```bash
asecli custom-gui <file> --spec material-gui.json          # dry-run
asecli custom-gui <file> --spec material-gui.json --write  # 一次备份、一次写入
asecli validate <file>
asecli recompile <file>
```

- 参考分组名称：固有色、阴影层、底漆层、清漆层、环境层、AO层、法线层、珠光层、伪装层。
- 每组只有第一个 PropertyNode 写 `group`/`FoldoutMzgui`；组内其他属性不要重复写组名。
- 每个导出属性必须有中文 `display_name` 和中文 `tooltip`；变量名和 Shader 默认值由 GUI 提供者自动追加。`custom-gui --spec` 会同步图内与编译区显示名，但不会修改真实默认值。
- 每个 `tooltip` 至少覆盖实际需要的内容：用途；贴图通道或数值单位；数值调大/调小时结果。无法确认时不编造因果。
- `group`、`tooltip`、`help`、`enabled_if` 的值为 `null` 时清除对应属性及同语义旧标记；受管文件缺少 Tooltip 时正式写入会被契约拒绝。`help` 可选，省略时不会自动创建或删除既有 HelpBox。

### 链路 D：ASE 节点图 Comment 打组与说明

```bash
# 先查询已有 Comment 及其成员
asecli comment-group <file>

# 用运行中 ASE 的真实节点尺寸检查并校正框；默认 dry-run
asecli comment-group <file> --check-bounds --mcp-url http://127.0.0.1:8080/mcp
asecli comment-group <file> --fit --padding 30 --mcp-url http://127.0.0.1:8080/mcp --write

# 内层：标题写清因果关系
asecli comment-group <file> --nodes 1212,1218 \
  --title "明度越高，强度越小" --note "" --write

# 外层：把上一步返回的 Comment node_id（例如 1069）作为成员，标题描述功能
asecli comment-group <file> --nodes 1069,1215,1216 \
  --title "控制不同颜色明度下的不同灯光强度" --write
```

- `layout --mode legacy` 把已有 Comment 及其成员视为固定复合单元；`--mode meticulous` 则使用真实尺寸移动成员，并在同一内存事务中自内向外重算 Comment bounds。
- 整理和连线清晰优先于分组数量。默认单层小组，只包围紧密算法单元；不建立大总框、不强求组套组。若分组造成交叉线、蜘蛛网或大量留白，则缩小组或不分组。
- 同层或无父子关系的 Comment 组之间禁止重叠；边框可以相邻但不得相交或互相遮挡。只有显式“外层功能、内层因果”的父子组允许嵌套，且必须完整包含，禁止部分交叠和边框穿插。完成前执行 `--check-bounds`，结果不得包含 `COMMENT_GROUP_OVERLAP`。
- 标题回答“这一块做什么”或“参数如何影响结果”，应具体，不使用“处理1”“临时”等无语义名称。
- 离线模式只能估算普通节点尺寸；`--editor-bounds`、`--check-bounds` 和 `--fit` 经 MCP 读取 live ASE `TruePosition`。`--fit --padding 30` 可统一紧凑边距，且只改 Comment 位置/尺寸，不移动成员、不改参数和连线。
- 标题/说明拒绝分号与换行。默认 dry-run；写入会保留 `.bak`、重算 CHKSM，并返回 `requires_editor_reload=true`。

### 精排与画布验收规范

- `meticulous` 以最终 Output 为根，从右向左递归形成局部鱼骨。每个节点都可成为上游主骨：单来源直接水平；3 个以上奇数来源取中位分支；偶数来源在中间两支中优先选择更完整的主要数据链；其余完整子树按端口顺序均分到上下两侧。
- 水平关系使用真实输入/输出端口锚点，不使用节点矩形中心。同一父节点的直属来源以主要输出端口局部右对齐；每一级递归沿短水平线生长，相邻层边界保持 `64–160px`（目标 `96px`），无关并行模块不得通过全图深度列互相拉长。
- 真实节点宽高决定列距。父子边界默认相隔 `96px`，普通兄弟子树至少 `32px`，跨 Comment/模块至少 `96px`；相同输入必须得到稳定坐标。
- MCP 返回的端口位置属于缩放后的 Editor 窗口坐标，精排桥必须依据 `GlobalPosition / TruePosition` 还原到图坐标。多 Pass 的无连接零尺寸 Master 只是休眠占位，应保持原位；带连接的零尺寸节点仍须失败关闭。
- Register/Get 作为局部接口处理：Register 贴近生产者右侧，Get 贴近消费者左侧。布局只报告远端直连，不自动创建、删除或改写 Local Var。
- Comment 在节点完成后自内向外收框，左右/底部留 `30px`、顶部标题区留 `48px`，无关组之间保留至少 `96px` 通道。已有框、成员、嵌套和颜色不得删除或改变；有效作用标题保持原样，空/Comment/Group/处理等占位标题只在唯一 Register、唯一框外消费者或唯一局部终点可可靠推断时补齐，否则写入失败关闭。
- 排版首先表达数据结构：主数据流从左向右逐层递进，Master 位于最右；同阶段节点严格列对齐，主链尽量水平，重复分支复用相同列坐标、行距和内部模板。
- 组内紧凑、组间留出清楚通道；并列模块及其 Comment 边框也要对齐。同层或无父子关系的组不得重叠，父子组只允许完整包含。
- 同组直连不等于允许线路交叉、重叠或贴线。普通 `meticulous` 保持既有 WireNode 坐标且绝不新增锚点；只有用户显式给出 `--route-wires`，才先移动既有 WireNode，再为仍有穿越/交叉的直连增加每条最多 2 个锚点。
- 新 WireNode 必须由当前 ASE Editor API 创建、连接并保存，不拼接版本相关序列化；写后折叠 WireNode 链复核来源/目标端口完全等价。能力缺失、保存失败、并发变化或清单不符时恢复写前 `.bak`，不得留下部分路由。
- 修复顺序为：先对齐阶段和重复结构，再移动源节点或挡线节点形成通道；显式授权时才执行 WireNode 路由；最后收紧 Comment。Local Var 以消费组边界为准：同一节点或算法结果被两个及以上不同 Comment/算法组消费时必须注册；全部消费者都在同一组内时，无论复用多少次都允许直连。
- 移动 Comment 内节点后，重新检查成员仍在原框内；移动整个算法块时，框与全部成员作为复合单元一起平移，保持内部相对布局。
- 完成前必须在真实 ASE 画布的正常阅读缩放下复核精排感、线路径和组间关系。ASE 文本不保存普通节点真实宽高、端口锚点和最终贝塞尔曲线路径，因此离线检查不能证明视觉验收通过；编辑器或 MCP 不可用时必须明确标记为未验证。

### 链路 D2：无效节点审计与安全清理

```bash
asecli graph-audit <file>
asecli remove-node <file> --node 99 --write
```

- 从 Master 输出反向追踪 Wire 与 Register/Get Local Var；只有 `unused_candidates` 才进入人工清理候选。
- Property 即使没有 ASE 连线，也可能由 Custom ShaderGUI 或 HLSL 消费。此类节点列入 `external_consumers`，不得按“孤立节点”删除。
- `remove-node` 默认拒绝删除工程源码仍引用的 Property。`--force-external` 只用于已经同步迁移外部消费者、且完成编译验证的显式操作。

### Local Var 复用与防蜘蛛网规范

节点图治理同时使用两层结构：Comment 框说明算法边界，`Register Local Var` / `Get Local Var` 治理模块接口。注册门槛按不同消费组计数，不按 Wire 数、同组扇出次数、跨阶段数或固定像素长度计数。

- 必须注册：同一节点输出或算法结果进入两个及以上不同 Comment/算法组；结果已经有 Register，但模块外消费者仍直接连接 Register/生产者输出。是否长线不影响这个结论。
- 保持直连：全部消费者都在同一 Comment/局部算法内，即使同组内多次使用；只有一个消费组且直连清晰的关系。
- 允许混合：生产者附近的局部消费者直连，模块外消费者通过各自就近 Get；边界必须与模块职责一致。
- 稳定业务语义只是命名和接口价值依据，例如 `CoatFresnelMask`、`LitValueControl`、`NormalSwitchRef`，不能在没有真实跨模块消费时单独触发注册。

排版与命名规则：

- `Register Local Var` 放在生产该结果的算法块右侧，仍属于生产者 Comment；只注册一次。
- 每个消费算法块在输入侧放自己的 `Get Local Var`，之后只做短距离局部连线。外层不再保留从生产者直拉到各消费者的长线。
- 变量名使用唯一、稳定、能说明结果含义的英文标识符，建议 `PascalCase`；禁止 `Value`、`Temp1`、`base` 等模糊名称，也不要用纯数字开头。
- 一个语义结果对应一个 Register 和多个 Get；不要为了视觉隐藏而重复计算、重复注册或让多个 Register 使用同名。
- 一次性、同组、相邻且连线清晰的结果保持直连；不要把每条线都转换成本地变量，否则真实依赖反而更难追踪。
- 直连必须继续治理线路质量：不得与节点本体或其他线路重叠，线线交叉应优先通过移动节点和已有 WireNode 消除；新增 WireNode 只改变走线路径，不得改变数据类型、端口语义或计算结果。
- 每次治理都要记录候选的来源节点、Wire 扇出数、去重后的消费组数量及组 ID、生产者/消费者模块和“直连 / Local Var / 混合”理由；跨阶段数与遮挡只作为排版证据，不得覆盖消费组门槛。
- 修改完成后同时检查：各 Get 指向正确 Register；数据类型一致；不存在自引用/循环；删除或改名 Register 时同步所有 Get；最后执行 `validate` 和真实 `recompile`。
- `validate` 会把 Get 缺失目标、错误目标类型、名称/数据类型不一致和 Local Var 参与的循环判为 error；`remove-node` 会拒绝删除仍被 Get 引用的 Register。不要用 `set-field` 或 raw 节点行绕过这些错误。

当前 ASECLI 对 `RegisterLocalVarNode` 的 schema 标记为 `layout_ok=false`，因为端口类型和序列化尾部会随输入变化。因此不要用普通 schema `add-node` 猜造 Register。纯文本新建时只能复用同 ASE 版本、同数据类型的真实 Register/Get 序列化样本并修改唯一 ID、引用 ID 和语义名；无法确认字段时，应在 ASE 编辑器中创建，再交给 ASECLI 做布局、Comment 和校验。

### 链路 E：文本/Editor 创建 + 编译

```bash
# 从编译壳克隆新 shader（可注入 donor 图），纯文本
asecli create Assets/Exp/New.shader --from <compiled-template.shader> --name "MyShader" --force

# 动态/不透明节点：让 ASE 1.9.6.2 根据严格 JSON 规格创建、保存并重载
asecli create Assets/Exp/NewEditor.shader --backend editor --spec graph.json

# auto 仅在提供 spec 时选择 Editor；未提供 spec 时仍走兼容的文本后端
asecli create Assets/Exp/NewEditor.shader --backend auto --spec graph.json

# 触发 Unity 内 ASE 重新生成 HLSL（走 MCP for Unity）
asecli recompile Assets/Exp/New.shader

# 只有明确授权的远程 MCP 才允许 opt-in；token 从环境读取，不得放进 argv
ASECLI_MCP_INSTANCE_TOKEN='<由安全渠道注入>' asecli recompile Assets/Exp/New.shader
```

Editor 创建规则：

- 只用于尚不存在、位于当前 Unity/Tuanjie 工程 `Assets/` 下的 `.shader`；禁止 `--force`，不得拿它覆盖或迁移生产 Shader。
- 正式 CLI 创建使用 `EditorGraphSpec v2/v3`，每个 Property/Sampler 必填中文 `inspector_name` 与中文 `tooltip`；旧 `help` 输入只迁移为 Tooltip，底层 v1 仅保留桥接兼容。v3 必填 `primitives_version: 1`，只接受版本化 primitive 闭包和无前向引用的 recipe；支持的 Property 可携带 `precision/default/min/max`。未知版本、primitive、模板、端口、字段或类型均在 MCP 前失败关闭。
- 固定执行器调用 ASE 的 `CreateNewTemplateShader`、`CreateNode`、`ParentGraph.CreateConnection`、`SaveToDisk`、`LoadFromDisk`；不要生成或要求用户提供一次性 C#，也不要手工拼 ShaderLab/HLSL/ASEBEGIN 冒充 Editor 结果。
- 成功结果必须对账 `template_guid`、`shader_name`、节点/属性/Custom Expression 输入输出和连接 manifest。创建调用只重载并核对暂存图：JSON 的 `reloaded`/`staging_reloaded=true` 不等于目标图已重开，`target_graph_reloaded` 为 `false`。提交后由独立 `recompile` 重载目标，避免 MCP 插件重连吞掉成功回执；最终发布前仍要用新 Editor 进程重开目标。结构通过不等于目标材质和渲染画面通过。
- MCP 3.4.7 的模式扫描会拦截固定回滚代码中的 `DeleteAsset`；CLI 只对包内固定、nonce 隔离的创建执行器设置该次 `safety_checks=false`，规格不能传入任意 C#。
- MCP 超时是未知完成状态。重试前检查目标和同目录 `ASECLI-Temp-*`；若目标已出现，先 `validate` 并在 ASE 中重开核对，不能直接再次创建。

## JSON 契约

- stdout 恒为 `{"ok": true, "data": {...}}` 或 `{"ok": false, "error": {"code", "message"}}`。
- 错误码：`PARSE_ERROR` / `NOT_FOUND` / `USAGE_ERROR` / `SCHEMA_UNAVAILABLE` / `GUI_SUPPORT_ERROR` / `CUSTOM_GUI_ERROR` / `PROPERTY_PRESENTATION_ERROR` / `COMMENT_GROUP_ERROR` / `EXTERNAL_REFERENCE` / `VALIDATION_ERROR` / `CHECKSUM_FORMAT_ERROR` / `WRITE_CONFLICT` / `UNSAFE_PATH` / `WRITE_ERROR` / `BRIDGE_ERROR` / `INTERNAL`。
- 退出码：0 成功；2 用法/校验/解析错误；3 桥接错误。
- 不加 `--write` 时命令只做 dry-run（`data.written=false`）。
- Editor `create` 成功 data 保留 `reloaded` 作为暂存重载兼容别名，并含 `staging_reloaded=true` 与 `target_graph_reloaded=false`；目标图重载必须走随后的独立 `recompile`。

## 桥接前提

1. Tuanjie/Unity 编辑器已打开目标工程。
2. MCP for Unity 会话已启动（编辑器里 Start Session；服务器默认 `http://127.0.0.1:8080/mcp`）。
3. `recompile` 成功返回 `data.changed=true` 表示 HLSL 已重新生成；`changed=false` 表示图未变。
4. 默认只连接 loopback；远程 URL 必须显式 `--allow-remote-mcp`，并仅连接可信会话。
5. token 只从 `ASECLI_MCP_INSTANCE_TOKEN` 读取；不要把 token 写进 argv、文档或日志。客户端不跟随重定向。
6. MCP 工具使用 `execute_code`，会在编辑器内执行受控 ASE 保存片段；连接错误会话等同于扩大代码执行信任边界。
7. Editor 创建当前只支持 ASE 1.9.6.2 和有端口契约的模板；不支持版本、模板或反射成员缺失必须失败关闭，不能退化为 raw Shader 文本。
8. Editor 事务内部失败会回滚目标/暂存资产；若提交后 Python parse/validate 失败，目标与 `.meta` 会保留并返回事务 nonce/hash，禁止按路径自动删除，人工核对身份后再处理。

## 错误处理约定

- 修改前先 `validate`；发现 `DANGLING_WIRE`/`DUPLICATE_NODE_ID` 先修复再继续。
- `SCHEMA_UNAVAILABLE` 时：用 `parse` 拿节点行原文，改用 `--line` 整行插入或整行替换。
- `GUI_SUPPORT_ERROR` 时：检查目标是否为 Unity/Tuanjie 工程根目录；固定安装路径若已有不同内容，停止并人工辨认，不得覆盖。
- `CUSTOM_GUI_ERROR` 时：检查目标是否为 `Property` 节点、当前图尾部是否可识别，以及 `CustomEditor` 是否为 `gui-support` 返回的 ASECLI Editor；不要改用 `set-field` 绕过。
- `COMMENT_GROUP_ERROR` 时：检查成员是否重复/已属于其他 Comment、是否同时选择了内层框与其子节点，以及标题是否包含分号或换行；不要用 raw `--line` 绕过树形归属检查。
- `WRITE_CONFLICT` 时：文件已被另一个 Agent 或编辑器修改；重新加载、比较差异后再执行，不得直接覆盖。`UNSAFE_PATH` 时检查目标、备份或旧 `.tmp` 是否为符号链接。
- Editor 创建返回 `BRIDGE_ERROR` 时：检查 ASE 版本、模板 GUID、目标、同目录 `ASECLI-Temp-*` 和 Editor 日志。若响应含 `cleanup=skipped_untrusted_post_commit_asset`，目标是为防误删而保留的后验失败现场，先核对 nonce/hash；若 MCP 超时，按未知完成状态处理，不要立刻重试。
- 所有写操作用 `validate` + `parse` 复核后再向用户报告。

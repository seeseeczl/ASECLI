---
name: asecli
description: Create, modify, validate, layout, install or configure grouped and explained custom material GUI, organize graphs with native Comment frames, and compile Amplify Shader Editor (ASE) shader files via the asecli CLI. Use whenever the user asks to edit or create ASE shaders in a Tuanjie/Unity project.
---

# AseCLI — Agent 操作 ASE Shader 指南

## 核心事实（必读）

1. ASE 节点图以纯文本嵌在 `.shader` 文件的 `/*ASEBEGIN ... ASEEND*/` 块中，行式格式。
2. `WireConnection;<入节点>;<入端口>;<出节点>;<出端口>` —— **目的地在前，来源在后**。
3. `//CHKSM=` 是 SHA1（大写 hex），对 `//CHKSM=` 之前的**整个文件**计算；校验失败**不阻断** ASE 加载。
4. `connect --from` 是输出端（数据源），`--to` 是输入端（消费者）。
5. Master 节点（TemplateMultiPassMasterNode 等）布局为 opaque，只能整行替换或用 `layout` 移动。
6. 自定义材质面板分两层：ASE 图只序列化主 Master 的 `CustomEditor` 与 PropertyNode 尾部属性，Unity `ShaderGUI` 负责实际显示。先用 `gui-support` 检查或安装唯一的 ASECLI GUI，再用 `custom-gui` 操作；未知 ASE 尾部不得猜写。
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

# 整理布局（分层对齐等距，只动 x/y）
asecli layout <file> --write

# 修复 checksum（默认只预览；显式写入会保留 .bak）
asecli fix-checksum <file> --write
```

创建、转换或重新整理节点图时，必须先读 [ASE 节点图精排规范](references/layout-standard.md)。核心目标是严格对齐、从左到右层层递进、重复结构一致和整体“经过精心排列”的秩序感；不是机械追求零交叉。

选择或整理 Master / Output 节点设置时，必须先读 [ASE Master / Output 设置规范](references/master-output-settings-standard.md)。上方基础生成设置默认保持模板和现有 Shader 原值，以最大平台兼容性为先；下方功能开关按真实需求选择，并避免无用 Pass、变体和重复计算。Master 序列化仍视为 opaque，不得用通用字段写入猜改。

### 链路 C：提示文案与分组（写元数据不需要 Unity，最终生效需要重编译）

创建或整理公开材质属性时，必须先读 [ASE 材质属性呈现规范](references/material-property-standard.md)。默认采用四层结构：中文显示名；Tooltip 展示准确变量名与 Shader 默认值；控件下方 HelpBox 解释用途和调节结果；最后按语义使用中文 Foldout 分组。

```bash
# 检查唯一 ASECLI GUI 的固定安装路径；provider=missing 时安装内置层
asecli gui-support /path/to/UnityProject
asecli gui-support /path/to/UnityProject --write

# 先查询，返回主 Master/编译区 Inspector 是否一致，以及可操作的 PropertyNode id
asecli custom-gui <file>

# 使用 gui-support 返回的 recommended_editor。给组内首项加折叠标题、可选悬浮说明和常驻说明
asecli custom-gui <file> --editor ASECLI.MaterialGUI.ASECLIMaterialGUI --property _PaintColor \
  --group "固有色" \
  --tooltip "车身基础漆色。" \
  --help-box "控制车辆基础漆面颜色。Alpha 当前不参与透明度计算。"
asecli custom-gui <file> --editor ASECLI.MaterialGUI.ASECLIMaterialGUI --property _PaintColor \
  --group "固有色" \
  --tooltip "车身基础漆色。" \
  --help-box "控制车辆基础漆面颜色。Alpha 当前不参与透明度计算。" --write

# 常驻说明和清理
asecli custom-gui <file> --property _Contrast \
  --help-box "车身明暗对比度，数值越大，对比越小" --write
asecli custom-gui <file> --property _PaintColor --clear-help-box --clear-group --write

asecli validate <file>
asecli recompile <file>
```

- `--group` 写 `ASECLIFoldout`，`--tooltip` 写 `ASECLITooltip`，`--help-box` 写 `ASECLIHelpBox`。把 group 加在组内第一个 PropertyNode；后续属性归入该组，直到下一个非空分组标题。
- Property 的公开显示名以中文为主；创建新节点时用 EditorGraphSpec 的 `inspector_name`，已有节点先通过 `custom-gui` 查询 `display_name`，再走 ASE Editor 或该节点类型确认过的固定字段修改。不要只改编译区 `Properties` 行。
- ASECLI GUI 会自动在 Tooltip 末尾追加变量名与默认基线，并从默认 `Material(shader)` 读取真实 Shader 默认值；`--tooltip` 只用于可选的额外悬浮说明，不手工抄写技术信息。
- `--help-box` 写属性下方的常驻说明，是规范的主说明方式：说明用途、调节方向、通道、单位或限制，不重复变量名和默认值。工具按已验证的 UTF-16 `#XXXX` 规则编码中文、换行和 emoji。
- 新增属性前必须运行 `gui-support`，并使用返回的唯一 `recommended_editor`：`ASECLI.MaterialGUI.ASECLIMaterialGUI`。旧三种 `*Mzgui` 标记只读兼容；同语义写入或 clear 会迁移被触碰属性。固定安装路径冲突时停止，工具不会扫描、选择或写入原生 MZGUI。
- `--add-attribute` / `--remove-attribute` 是专家入口，只接受 `ASECLIFoldout`、`ASECLITooltip`、`ASECLIHelpBox`。
- `--write` 同步图内主 Master 与编译区 `CustomEditor`、重算 CHKSM 并生成 `.bak`；Property 声明仍必须经 `recompile` 由 ASE 正式生成。

### 批量整理属性的规范

当用户要求“整理材质属性、分组并补说明”时，创建 JSON 规范并一次应用；不要逐条写盘。数组顺序就是最终顺序，未列属性保持原相对顺序并追加。JSON 的 `editor` 固定使用 ASECLI GUI：

```json
{
  "editor": "ASECLI.MaterialGUI.ASECLIMaterialGUI",
  "reorder": true,
  "properties": [
    {"name": "_PaintColor", "group": "固有色", "tooltip": "车身基础漆色。", "help": "控制车辆基础漆面颜色。Alpha 当前不参与透明度计算。"},
    {"name": "_Contrast", "help": "控制车身明暗对比度；数值越大，对比越弱。"},
    {"name": "_Coat_IO", "group": "清漆层", "help": "控制是否启用清漆层。"},
    {"name": "_CoatSaturation", "help": "控制清漆饱和度；饱和度越高，反射强度越弱。"},
    {"name": "_FresnelPow", "help": "控制菲涅尔边缘范围；数值越大，边缘范围越窄。"},
    {"name": "_HDRLitTex", "help": "R 通道为直接光，G 通道为反射 GI，B 通道为清漆数据；编码为 RGB9e5 32 bit。"}
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
- 每组只有第一个 PropertyNode 写 `group`/`ASECLIFoldout`；组内其他属性不要重复写组名。
- 每个公开属性应有中文 `display_name`；变量名和 Shader 默认值由 GUI 提供者自动生成技术 Tooltip。`custom-gui` 规范只写额外注解，不修改显示名或真实默认值；两者不正确时先在 PropertyNode/Editor 规格中修正。
- 每个 `help` 至少覆盖实际需要的内容：用途；贴图通道或数值单位；数值调大/调小时结果。无法从图或项目语义确认时，不编造因果，先保留待确认说明。
- `group`、`help`、`tooltip` 的值为 `null` 时清除对应 ASECLI 属性及同语义旧标记。重复属性、未知字段、错误类型和非 ASECLI 新增会使整批操作失败且不写文件。

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

- `layout` 把已有 Comment 及其成员视为固定复合单元；打组后仍应以 `--check-bounds` 和真实 ASE 界面复核框选关系。
- 整理和连线清晰优先于分组数量。默认单层小组，只包围紧密算法单元；不建立大总框、不强求组套组。若分组造成交叉线、蜘蛛网或大量留白，则缩小组或不分组。
- 同层或无父子关系的 Comment 组之间禁止重叠；边框可以相邻但不得相交或互相遮挡。只有显式“外层功能、内层因果”的父子组允许嵌套，且必须完整包含，禁止部分交叠和边框穿插。完成前执行 `--check-bounds`，结果不得包含 `COMMENT_GROUP_OVERLAP`。
- 标题回答“这一块做什么”或“参数如何影响结果”，应具体，不使用“处理1”“临时”等无语义名称。
- 离线模式只能估算普通节点尺寸；`--editor-bounds`、`--check-bounds` 和 `--fit` 经 MCP 读取 live ASE `TruePosition`。`--fit --padding 30` 可统一紧凑边距，且只改 Comment 位置/尺寸，不移动成员、不改参数和连线。
- 标题/说明拒绝分号与换行。默认 dry-run；写入会保留 `.bak`、重算 CHKSM，并返回 `requires_editor_reload=true`。

### 精排与画布验收规范

- 排版首先表达数据结构：主数据流从左向右逐层递进，Master 位于最右；同阶段节点严格列对齐，主链尽量水平，重复分支复用相同列坐标、行距和内部模板。
- 组内紧凑、组间留出清楚通道；并列模块及其 Comment 边框也要对齐。同层或无父子关系的组不得重叠，父子组只允许完整包含。
- 连线不是绝对不能交叉。少量线与线可以在空白通道中简洁交叉，但不得穿过无关节点本体、端口或标题栏，也不得形成难以追踪的蜘蛛网。不要用大幅绕行换取表面的零交叉。
- 修复顺序为：先对齐阶段和重复结构，再移动源节点或挡线节点形成通道；最后按需调整 Comment。只有跨组长线仍不清晰时才使用 `Register Local Var` / `Get Local Var`。
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

节点图治理同时使用两层结构：Comment 框说明算法边界，`Register Local Var` / `Get Local Var` 治理跨区域数据流。满足下列任一条件时，优先注册本地变量：

- 同一中间结果被两个及以上、且位置分散的消费者复用。
- 连线需要跨越 Comment 分组，或会横穿其他算法块形成长距离交叉线。
- 中间结果本身具有稳定业务语义，值得成为算法模块的输出接口，例如 `CoatFresnelMask`、`LitValueControl`、`NormalSwitchRef`。

排版与命名规则：

- `Register Local Var` 放在生产该结果的算法块右侧，仍属于生产者 Comment；只注册一次。
- 每个消费算法块在输入侧放自己的 `Get Local Var`，之后只做短距离局部连线。外层不再保留从生产者直拉到各消费者的长线。
- 变量名使用唯一、稳定、能说明结果含义的英文标识符，建议 `PascalCase`；禁止 `Value`、`Temp1`、`base` 等模糊名称，也不要用纯数字开头。
- 一个语义结果对应一个 Register 和多个 Get；不要为了视觉隐藏而重复计算、重复注册或让多个 Register 使用同名。
- 一次性、同组、相邻且连线清晰的结果保持直连；不要把每条线都转换成本地变量，否则真实依赖反而更难追踪。
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
- `EditorGraphSpec v1` 当前开放 URP Unlit 模板 GUID `2992e84f91cbeb14eab234972e07ea9d` 的已验证 Master 端口，以及白名单 Property/Sampler/CustomExpression/普通节点。端口、方向、基本类型和 `property_name` 唯一性均在 MCP 前校验。
- 固定执行器调用 ASE 的 `CreateNewTemplateShader`、`CreateNode`、`ParentGraph.CreateConnection`、`SaveToDisk`、`LoadFromDisk`；不要生成或要求用户提供一次性 C#，也不要手工拼 ShaderLab/HLSL/ASEBEGIN 冒充 Editor 结果。
- 成功结果必须对账 `template_guid`、`shader_name`、节点/属性/Custom Expression 输入输出和连接 manifest；随后仍要用新 Editor 进程重开目标。结构通过不等于目标材质和渲染画面通过。
- MCP 超时是未知完成状态。重试前检查目标和同目录 `ASECLI-Temp-*`；若目标已出现，先 `validate` 并在 ASE 中重开核对，不能直接再次创建。

## JSON 契约

- stdout 恒为 `{"ok": true, "data": {...}}` 或 `{"ok": false, "error": {"code", "message"}}`。
- 错误码：`PARSE_ERROR` / `NOT_FOUND` / `USAGE_ERROR` / `SCHEMA_UNAVAILABLE` / `GUI_SUPPORT_ERROR` / `CUSTOM_GUI_ERROR` / `COMMENT_GROUP_ERROR` / `EXTERNAL_REFERENCE` / `VALIDATION_ERROR` / `CHECKSUM_FORMAT_ERROR` / `WRITE_CONFLICT` / `UNSAFE_PATH` / `WRITE_ERROR` / `BRIDGE_ERROR` / `INTERNAL`。
- 退出码：0 成功；2 用法/校验/解析错误；3 桥接错误。
- 不加 `--write` 时命令只做 dry-run（`data.written=false`）。

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

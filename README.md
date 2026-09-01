# AseCLI

**让 AI Agent 创建、修改、校验、整理与编译 Amplify Shader Editor（ASE）文件。**

AseCLI 是一个面向 AI Agent 的本地 CLI 工具。它把 ASE 嵌在 `.shader` / `.asset` 文件里的节点图当作纯文本数据来解析和修改——不依赖 Unity 即可完成 90% 的操作；只在需要重新生成编译后 HLSL 时，通过 MCP for Unity 触发一次 Unity/团结引擎重编译。

```
你：提需求（"给这个 shader 加个可调描边"）
Agent：设计节点图 → asecli 写文件 → 校验 → 触发编译 → 你验收效果
```

## 特性

- **纯文本读写引擎**：真实样本逐字节 roundtrip 一致，修改产生最小差异
- **节点 schema 库**：295 种节点类型的参数结构由 ASE 运行时序列化自动提取（格式由 ASE 自己保证）
- **结构校验**：悬空连线、重复节点 ID、CHKSM 校验（SHA1，已逆向验证）
- **自动布局**：Sugiyama-lite 分层排列——输入在左、输出在右、Master 靠右、对齐等距，只动 x/y
- **自定义材质 GUI**：按属性名批量排序；原生 MZGUI 缺失时可安装内置兼容层，继续提供中文折叠分组、常驻帮助说明，以及自动显示变量名和 Shader 默认值的悬停提示
- **节点图语义分组**：用 ASE 原生 `CommentaryNode` 自动包围节点，支持“外层功能、内层因果”的嵌套说明
- **无 UI**：stdout 恒为 JSON，专为 agent 子进程调用设计
- **编译桥**：经 MCP for Unity（`execute_code`）触发 Unity 内 ASE 重新生成并保存
- **受控 Editor 创建**：用严格 `EditorGraphSpec v1` 驱动 ASE 1.9.6.2 自己创建节点、连线、生成 ShaderLab/HLSL/ASEBEGIN，并保存、关闭、重载核对

## 环境要求

- Python >= 3.10，[uv](https://docs.astral.sh/uv/)
- 查看/修改/校验/布局：不需要 Unity
- Editor 创建/编译（`create --backend editor` / `recompile`）：Unity/团结引擎打开目标工程 + MCP for Unity 会话已启动

## 安装

```bash
git clone git@github.com:seeseeczl/ASECLI.git
cd ASECLI
uv tool install .          # 安装为全局 asecli 命令
# 或开发模式：uv sync && uv run asecli --help
```

## 快速上手

```bash
# 1. 查看 shader 的节点图
asecli parse MyShader.shader

# 2. 校验结构
asecli validate MyShader.shader

# 3. 改一个节点的某个字段（field 是绝对下标：0=Node, 1=类型, 2=Id, 3=坐标, 4+=参数）
asecli set-field MyShader.shader --node 5 --field 12 --value 0.85 --write

# 4. schema 驱动加节点
asecli add-node MyShader.shader --type AmplifyShaderEditor.SaturateNode --id 99 --pos -320,0 --write

# 5. 连线：把 99 的输出 0 接到 6 的输入 0
asecli connect MyShader.shader --from 99:0 --to 6:0 --write

# 6. 整理节点布局（分层对齐等距，只动 x/y）
asecli layout MyShader.shader --write

# 7. 修复 checksum（默认只预览，显式写入才落盘并保留 .bak）
asecli fix-checksum MyShader.shader --write

# 8. 先检测目标工程的 GUI 提供者；默认 dry-run，缺失时才显式安装
asecli gui-support /path/to/UnityProject
asecli gui-support /path/to/UnityProject --write

# 使用上一步 JSON 返回的 recommended_editor；也可直接用 ShaderLab 属性名定位
asecli custom-gui MyShader.shader
asecli custom-gui MyShader.shader --editor ASECLI.MaterialGUI.ASECLIMaterialGUI --property _PaintColor \
  --group "固有色" \
  --tooltip "车身基础漆色。" \
  --help-box "控制车辆基础漆面颜色。" --write

# 9. 给现有节点增加原生 Comment 框（默认只预览）
asecli comment-group MyShader.shader --nodes 1212,1218 \
  --title "明度越高，强度越小" --write

# 10. 触发 Unity 内 ASE 重新生成 HLSL（需编辑器开启 + MCP 会话启动）
asecli recompile Assets/MyShader.shader

# 11. 从已有编译壳克隆新 shader
asecli create Assets/NewShader.shader --from MyShader.shader --name "NewShader" --force

# 12. 让运行中的 ASE 根据声明式规格创建全新、可重开的节点图
asecli create Assets/NewEditorShader.shader --backend editor --spec graph.json
```

所有修改类命令不加 `--write` 时为 dry-run（只预览不落盘）。

## 命令参考

| 命令 | 说明 | 需要 Unity |
| --- | --- | --- |
| `parse <file>` | 节点/连线摘要 | 否 |
| `validate <file>` | 结构校验（悬空线/重复 ID/CHKSM） | 否 |
| `set-field <file> --node N --field I --value V` | 设置节点某个序列化字段 | 否 |
| `add-node <file> --type T [--id N] [--pos X,Y]` | schema 驱动加节点（或 `--line` 整行插入） | 否 |
| `connect <file> --from SRC:port --to DST:port` | 连线（from=输出端，to=输入端） | 否 |
| `disconnect <file> --from SRC:port --to DST:port` | 删连线 | 否 |
| `remove-node <file> --node N` | 删节点；外部源码仍引用的 Property 默认拒删 | 否 |
| `graph-audit <file>` | 查找不通向输出的节点，区分真正候选与 Custom GUI/HLSL 外部消费者 | 否 |
| `layout <file> [--gap-x] [--gap-y]` | 自动整理节点布局 | 否 |
| `gui-support <project> [--write]` | 检测原生 MZGUI；缺失时安全安装内置 Foldout/Tooltip/HelpBox 支持 | 不需运行；安装后需 Editor 重编译 |
| `custom-gui <file> [--spec JSON] [--property P --group/--tooltip/--help-box T]` | 查询、批量排序或修改 CustomEditor/MZGUI | 写元数据否；生效需重编译 |
| `comment-group <file> [--nodes IDS --title T]` | 查询、创建或用 `--check-bounds`/`--fit` 校正 ASE 原生 Comment 框 | 精确边界检查/校正需要 |
| `fix-checksum <file> [--write]` | 重算 `//CHKSM`（默认预览；写入保留 `.bak`） | 否 |
| `create <out> --from TPL [--name N] [--graph-from D]` | 从编译壳克隆新 shader | 否 |
| `create <out> --backend editor --spec GRAPH.json` | 用受控 ASE Editor API 创建不存在的新 shader | **是** |
| `recompile <file> [--mcp-url U] [--allow-remote-mcp]` | 触发 Unity 内 ASE 重新生成并保存 | **是** |

### Editor API 创建

默认 `create` 仍是原有纯文本后端。`--backend editor --spec graph.json` 明确使用 Editor；`--backend auto` 在提供 `--spec` 时选择 Editor，否则选择文本后端。Editor 目标必须位于 Unity/Tuanjie 工程的 `Assets/` 下且尚不存在，不允许 `--force`。

最小 Caster-like 规格：

```json
{
  "version": 1,
  "template": {
    "guid": "2992e84f91cbeb14eab234972e07ea9d",
    "shader_name": "Vehicle/LocalShadow/Caster"
  },
  "nodes": [
    {
      "alias": "mask",
      "kind": "sampler",
      "position": [-520, 20],
      "property_name": "_CasterMask",
      "inspector_name": "Caster Mask",
      "parameter_type": "Property"
    }
  ],
  "connections": [
    {"from": {"node": "mask", "port": 1}, "to": {"node": "master", "port": 2}}
  ]
}
```

- 首期绑定 ASE `1.9.6.2`；Master 端口契约只开放已实测的 URP Unlit 模板 GUID。未知版本、模板 Master 端口、节点、字段、端口或类型在写入前失败。
- 规格只传 JSON 数据。执行的 C# 来自包内固定资源；Custom Expression 的 HLSL 是可编辑节点内容，但任意 C#、任意反射字段和危险运行时标记不会透传。
- 保存成功必须同时满足 Save、暂存重载、模板 GUID/Shader 名、节点/属性/动态端口/连接 manifest、移动提交和目标重载一致；失败回滚明确的目标与暂存资产并恢复原 ASE 窗口状态。
- MCP 客户端超时代表完成状态未知，不等同于 Editor 已停止或已回滚。重试前先检查目标文件及同目录 `ASECLI-Temp-*`，避免把迟到成功误判为失败。
- 隔离团结 E2E 已证明 Caster-like/Receiver-like 图可创建、保存、关闭并由新进程重载；这不证明目标工程的运行时矩阵注入、材质绑定或最终渲染画面正确。

## JSON 契约

stdout 恒为单行 JSON，agent 可直接解析：

```json
{"ok": true,  "data": {"node_count": 7}}
{"ok": false, "error": {"code": "NOT_FOUND", "message": "..."}}
```

错误码：`PARSE_ERROR` `NOT_FOUND` `USAGE_ERROR` `SCHEMA_UNAVAILABLE` `CUSTOM_GUI_ERROR` `COMMENT_GROUP_ERROR` `EXTERNAL_REFERENCE` `BRIDGE_ERROR` `INTERNAL`
退出码：`0` 成功 · `2` 用法/校验/解析错误 · `3` 桥接错误

## ASE 格式备忘（Agent 必读）

1. 节点图嵌在 `/*ASEBEGIN ... ASEEND*/` 块中，行式指令流：`Node;...` 与 `WireConnection;...`
2. `WireConnection;<入节点>;<入端口>;<出节点>;<出端口>` —— **目的地在前，来源在后**
3. `//CHKSM=` = 整个文件（`//CHKSM=` 之前部分）的 SHA1 大写 hex；校验失败**不阻断** ASE 加载
4. Master 节点（TemplateMultiPassMasterNode 等）序列化布局为 opaque：用 `--line` 整行替换或 `layout` 移动
5. 主 Master 节点字段 9 保存 `CustomEditor`；已验证的 ASE 1.9.6.2 PropertyNode 尾部保存 MZGUI 数量与属性。请用 `custom-gui`，不要用通用 `set-field` 猜这些结构；未知 ASE 版本无法识别合法尾部时会失败关闭

### 自定义 GUI 分组规则

- 公开属性默认使用中文显示名。新 Property 通过 EditorGraphSpec 的 `inspector_name` 写入；已有属性先用 `custom-gui` 查看 `display_name`，再由 ASE Editor 或确认过的节点字段修改，不要只编辑重编译后会被覆盖的 ShaderLab `Properties` 行。
- `--group` 会给目标属性写入 `FoldoutMzgui`。目标属性成为分组首项，后续属性一直归入该组，直到下一个带非空分组标题的属性；因此应选择材质面板中该组的第一个 PropertyNode。
- `--property _PaintColor` 可替代节点 ID；批量整理使用 `--spec`。`reorder=true` 按 `properties` 数组重写 PropertyNode 的 `m_orderIndex`，未列属性保持原相对顺序并追加。
- 原生 MZGUI 和 ASECLI 内置 GUI 都会在 Tooltip 中自动追加准确变量名与默认基线；内置 GUI 通过默认 `Material(shader)` 读取真实 Shader 默认值，不使用当前材质实例值。`--tooltip` 只写可选的额外悬浮说明，不再人工复制变量名和默认值。
- `--help-box` 是属性下方的常驻中文说明，应写清用途、通道/单位和“调大/调小”的结果，不重复变量名和默认值。中文、换行和 emoji 会按 MZGUI 的 UTF-16 `#XXXX` 规则编码。
- 先运行 `gui-support <project>`：原生 MZGUI 存在时使用返回的 `MZGUI.MZGUI`；缺失时用 `--write` 安装固定资源，再使用 `ASECLI.MaterialGUI.ASECLIMaterialGUI`。命令不会悄悄替换 Shader 的 CustomEditor。若返回 `provider=multiple`，必须先人工移除固定内置资源 `Assets/Editor/ASECLI/ASECLIMaterialGUI.cs`，等待 Editor 重编译后再选择原生 MZGUI；工具会失败关闭，不会猜选提供者。
- `custom-gui --write` 会同步图内主 Master 与编译区 `CustomEditor`、重算 `CHKSM` 并保留 `.bak`；Property 属性声明由 ASE 生成，因此随后必须执行 `validate` 和 `recompile`。

批量规范示例（`editor` 必须使用 `gui-support` 返回的 `recommended_editor`）：

```json
{
  "editor": "ASECLI.MaterialGUI.ASECLIMaterialGUI",
  "reorder": true,
  "properties": [
    {"name": "_PaintColor", "group": "固有色", "tooltip": "车身基础漆色。", "help": "控制车辆基础漆面颜色。"},
    {"name": "_Contrast", "help": "控制车身明暗对比度；数值越大，对比越弱。"},
    {"name": "_Coat_IO", "group": "清漆层", "help": "控制是否启用清漆层。"}
  ]
}
```

### ASE 节点图 Comment 规范

- 以连线清晰和紧凑为先。默认使用单层小组，只包围一个紧密算法单元；不建立覆盖整片区域的大总框，不为了分组强行组套组。
- 离线创建只能按坐标和保守尺寸估算；普通节点的真实宽高并不写入 ASE 文本。使用 `--editor-bounds` 创建，或在创建后用 `--check-bounds`/`--fit` 读取 live ASE `TruePosition` 做精确验收和校正。
- `--fit` 只调整 Comment 的位置和宽高，不移动成员、不改参数和连线。可用 `--padding 30` 生成统一紧凑边距；命令默认 dry-run。
- 先完成节点和 Local Var 排布，再创建/校正 Comment；若 Comment 造成交叉线、蜘蛛网或大面积留白，则缩小分组或不分组。
- 标题和说明禁止分号/换行；默认 dry-run，`--write` 才写入、重算 CHKSM 并保留 `.bak`。

```bash
# 精确检查是否有节点超出框
asecli comment-group My.shader --check-bounds --mcp-url http://127.0.0.1:9080/mcp

# 按 ASE 真实节点尺寸统一留 30 单位边距，先预览再写入
asecli comment-group My.shader --fit --padding 30 --mcp-url http://127.0.0.1:9080/mcp
asecli comment-group My.shader --fit --padding 30 --mcp-url http://127.0.0.1:9080/mcp --write
```

### 节点图精排规范

- 核心目标是“经过人工精心排列”的秩序感：主数据流从左向右层层递进，Master 最右；同阶段严格列对齐，主链尽量水平，重复分支使用完全一致的列、行距和内部模板。
- 组内紧凑、组间留出明显通道，并列模块和 Comment 边框也要对齐；无父子关系的组不得重叠，父子组只允许完整包含。
- 连线并非绝对不能交叉。允许少量线与线在空白通道中简洁、可追踪地交叉；但连线不得穿过无关节点本体、端口或标题栏，也不得形成蜘蛛网。不要用大幅绕线换取表面的零交叉。
- 排版修复只能改变位置和必要的 Comment 边界，不得改变 Shader 参数、端口连接、计算顺序或引入重复计算。跨组长线仍不清晰时才使用 `Register Local Var` / `Get Local Var`。
- 完整规则与量化/视觉验收边界见 [`skills/asecli/references/layout-standard.md`](skills/asecli/references/layout-standard.md)。真实 ASE 画布仍需复核精排感、贝塞尔线路径和组间关系；编辑器或 MCP 不可用时应明确报告未验证。

### 无效节点审计

- `graph-audit` 从有效 Master 输出反向追踪 Wire 和 Register/Get Local Var，列出不通向输出的节点。
- 无 ASE 连线不等于无效。Property 若被 Custom ShaderGUI、HLSL 或其他工程源码引用，会进入 `external_consumers`，不会被报告为 `unused_candidates`。
- `remove-node` 默认拒绝删除存在外部源码引用的 Property；只有人工确认同时迁移外部消费者时才可显式使用 `--force-external`。

### Local Var 防蜘蛛网规范

- 同一中间结果被多处复用、跨 Comment 分组或需要长距离连线时，优先在生产者模块右侧放一个 `Register Local Var`，在各消费模块输入侧分别放 `Get Local Var`。
- Comment 表达“算法块做什么”，Local Var 表达“算法块之间传递什么”。两者配合，把跨区长线收敛成模块边界附近的短线。
- 变量名应唯一且语义明确，例如 `CoatFresnelMask`、`LitValueControl`；避免 `Value`、`Temp1`、`base`。同组相邻、只使用一次的结果仍保持直连，避免过度抽象。
- 当前 `RegisterLocalVarNode` 的端口类型会随输入变化，ASECLI 不允许用不完整 schema 猜造；优先在 ASE 编辑器创建，或只复用同 ASE 版本、同类型的真实序列化样本，随后执行 `validate` 和 `recompile`。

完整操作手册见 [`skills/asecli/SKILL.md`](skills/asecli/SKILL.md)；材质属性四层信息规范见 [`skills/asecli/references/material-property-standard.md`](skills/asecli/references/material-property-standard.md)。

## 编译桥接前提

1. Tuanjie/Unity 编辑器已打开目标工程
2. MCP for Unity 会话已启动（编辑器内 Start Session，默认 `http://127.0.0.1:8080/mcp`）
3. MCP 不能被其他会话独占（`recompile` 报 `BRIDGE_ERROR` 时先检查占用）
4. `recompile` 成功时 `data.changed=true` 表示 HLSL 已重新生成；`changed=false` 表示文件本已最新。Editor 创建成功会返回 `template_guid`、`shader_name` 和 Save/Load manifest

安全边界：默认只允许 `127.0.0.1`、`localhost`、`::1`；远程 MCP 必须显式加 `--allow-remote-mcp`。实例 token 只能通过当前进程环境变量 `ASECLI_MCP_INSTANCE_TOKEN` 提供，禁止写入命令参数、脚本或日志。客户端拒绝 URL 凭证、query、fragment 和 HTTP 重定向，避免 token 被转发。`recompile` 会调用 MCP 的 `execute_code`，因此只能连接你明确信任的编辑器会话。

## 测试

```bash
uv run pytest -q                # 全量（桥接测试无环境时自动跳过）
ASECLI_TEST_SHADER=Assets/xxx.shader uv run pytest -m bridge   # 桥接端到端
ASECLI_EDITOR_CREATE_PROJECT=/path/to/isolated-project \
ASECLI_TUANJIE_PATH=/path/to/Tuanjie \
uv run pytest -q -m bridge tests/test_editor_create_e2e.py     # 真实 Editor 创建/新进程重载
```

## 架构与文档

- 需求基线：[`docs/01-architecture/project-architecture-and-requirements.md`](docs/01-architecture/project-architecture-and-requirements.md)
- 技术决策：[`docs/01-architecture/technical-route.md`](docs/01-architecture/technical-route.md)（ADR-0001~0005）
- 模块边界：[`docs/01-architecture/module-map.md`](docs/01-architecture/module-map.md)
- 第一性原理计划书：[`docs/first-principles/2026-08-31-231401-optimization-plan.md`](docs/first-principles/2026-08-31-231401-optimization-plan.md)
- 实验记录：[`docs/01-architecture/assumption-experiments.md`](docs/01-architecture/assumption-experiments.md)

```
src/asecli/
├── core/      解析器/序列化器/图模型/布局引擎
├── schema/    节点 schema 库（data/schemas.json）
├── checks/    结构校验与 checksum
├── bridge/    MCP for Unity 客户端、重编译触发与材质 GUI 支持安装器
└── cli/       命令入口与 JSON 契约
```

## License

内部专有工具，见 [`LICENSE`](LICENSE)；未获书面授权不得公开分发。

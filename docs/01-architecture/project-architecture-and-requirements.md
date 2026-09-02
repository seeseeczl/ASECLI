---
id: ARCH-REQ-0001
type: project-architecture-and-requirements
status: 已确认
version: 1.9.0
created_at: 2026-08-31T23:25:00+08:00
owner: long
related: [PRJ-ASECLI, CR-0002, CR-0003, CR-0004, CR-0005, CR-0007, CR-0008, CR-0010, CR-0011, CR-0012, BUG-0015, BUG-0017, BUG-0018, FR-0009, FR-0010, FR-0011, AUD-20260901]
supersedes: 无（首次启动）
evidence: [ASE 源码分析; MCP for Unity 桥接实验; 2026-09-01 标准审计与整改]
kickoff_completion: complete
---

# 项目架构与需求总纲 — AseCLI

## 启动输入与假设

| 项目启动问卷项 | 答案 | 状态（已确认/假设/未决/风险） |
| --- | --- | --- |
| 项目目标 | 让 AI Agent 通过自然语言创建/修改 ASE Shader 文件并触发编译 | 已确认 |
| 目标用户与角色 | 用户本人（long）：Unity/团结引擎开发者；直接使用者是 AI Agent（Codex/Claude Code/Codely） | 已确认 |
| 首个场景 / MVP | 用户说"给这个 shader 加一个可调描边"，Agent 完成设计节点图、连线、写文件、校验、触发编译 | 已确认 |
| 产品形态 | 本地 Python CLI（`asecli`）+ Agent 技能文档 + MCP for Unity 桥接；无 UI | 已确认 |
| 数据与集成 | 读写用户指定 .shader/.asset；默认仅调用 loopback MCP；远程需显式授权；token 仅从环境注入 | 已确认 |
| 约束与风险 | 编译必须经 Unity；目标引擎是团结引擎；schema 覆盖 400+ 节点存在遗漏风险 | 已确认 |
| 设计来源 | 第一性原理计划书方案 B + ASE 源码静态分析 | 已确认 |
| 项目根目录与写入授权 | /Users/long/GitHub/ASECLI；用户已授权执行 2026-09-01 优化任务 | 已确认 |

## 目标、范围与成功标准

- 要解决的问题：ASE 节点图文本格式复杂（400+ 节点参数 schema 各异），Agent 直接手写易错且无法触发 Unity 编译，导致"AI 替用户做 shader"不可靠。
- 目标用户与价值：用户只提需求与验收效果；Agent 负责设计节点图、连线、设参、写文件、编译的全过程。
- MVP / 首个核心垂直切片：对项目内一个已有 ASE shader，Agent 完成"改一个属性值 → 校验 → 触发重新编译 → HLSL 更新"全链路。
- 本期包含：FR-0001～FR-0011；图修改、材质 GUI 批量规范、节点 Comment 分组、文本创建/编译链路可用，Editor API 动态节点创建按 CR-0008 实施。
- 本期不包含：CLI-Anything Hub 发布（ADR-0004 后置）、可视化界面、ASE 功能替代、通用 schema 覆盖 100% 节点（未知节点 passthrough）。
- 成功指标：既有 REG-0001～REG-0036 保持全绿；REG-0037 覆盖 `asecli.property-presentation.v1` 的逐属性报告、治理、创建和写入失败关闭；ASE 1.9.6.2 MZGUI_Test 与 CommentaryNode 真实序列化样本可读；1000 个附加节点单轮 <1s（REG-0011）。

## 需求整理与验收

| ID | 类型 | 需求/场景 | 关键验收 | OpenSpec/REG 链接 | 状态 |
| --- | --- | --- | --- | --- | --- |
| FR-0001 | 功能 | 解析 ASE 图数据（.shader 与 .asset m_functionInfo），输出结构化模型与 JSON | 真实样本 roundtrip 逐字节一致 | REG-0001 REG-0011 | 已确认 |
| FR-0002 | 功能 | set-field/add-node/connect/remove；schema 版本匹配且写前结构有效 | 最小差异；10 种 schema；重复 ID/输入多来源被拒绝 | REG-0002 REG-0009 REG-0013 REG-0015 | 已确认 |
| FR-0003 | 功能 | validate 结构错误失败退出；CHKSM 默认预览、显式修复 | 破坏样本被检出；无 `--write` 文件不变 | REG-0003 REG-0004 REG-0018 | 已确认 |
| FR-0004 | 功能 | 经 MCP for Unity 触发 ASE 重编译 | tool error 失败；`saved=True`；目标平台 HLSL/CHKSM 验收 | REG-0005 REG-0016 REG-0017 | 已确认 |
| FR-0005 | 功能 | 以模板文件壳组合 donor ASE graph 创建 shader | 单一文件壳；最终文件满足属性呈现契约；Editor 中打开正常 | REG-0006 REG-0014 REG-0037 | 已确认 |
| FR-0006 | 功能 | Agent 技能文档 SKILL.md：格式说明+三链路手册+错误处理 | Agent 按文档完成一次全流程 | REG-0010 | 已确认 |
| FR-0007 | 功能 | CLI JSON 输出契约：stdout 恒为合法 JSON（含 ok 字段），统一错误码 | 所有子命令契约测试通过 | REG-0007 | 已确认 |
| FR-0008 | 功能 | 节点精排：按数据流拓扑从左向右分层递进，同阶段严格列对齐、同列等距、重复分支复用同一模板，Master 最右；保持连线与参数不变 | 布局后连线集合不变；同输入确定性输出；仅 x/y 字段变化；DAG 边向右推进；给定间距下列/行网格精确；真实 ASE 画布具备人工精排感 | REG-0012 | 已确认 |
| FR-0009 | 功能 | 操作自定义材质 GUI：查询/同步 Shader `CustomEditor`，对已识别的 PropertyNode 尾部增删分组、悬停提示和常驻说明；安装唯一的 ASECLI 内置 GUI | 新写入仅为 `ASECLIFoldout`、`ASECLITooltip`、`ASECLIHelpBox`；不覆盖冲突文件；旧三标记可读取并在同语义写入/清理时迁移；内置 Tooltip 自动读取变量名和 Shader 默认值；说明条遵循可查询、写前强制的 `asecli.inline-help.v1` 呈现契约；未知尾部或失效内置资源失败关闭 | REG-0022 REG-0030 REG-0035 REG-0036 | 已确认 |
| FR-0010 | 功能 | 按参考规范整理材质属性与 ASE 图：每个导出属性强制使用中文显示名，Tooltip 自动展示英文变量名与 Shader 默认值，属性下方强制提供中文用途/调节说明，并按 ShaderLab 属性名批量排序和中文分组；用原生 Comment 框形成“外层功能、内层因果”的嵌套分组；跨区或多消费者结果用 Register/Get Local Var 治理复用；Master / Output 上方基础设置默认保持，下方功能开关按需选择 | `asecli.property-presentation.v1` 可查询且写前强制；JSON 可原子治理显示名/说明并保持未列属性；显示名、变量名、默认值与说明在真实 Inspector 一致；Comment 不移动节点/连线；同层或无父子关系的组不重叠，父子组仅允许完整包含；复用结果形成一个语义 Register/多个就近 Get，一次性相邻链路保持直连；失败可恢复 | REG-0010 REG-0023 REG-0024 REG-0037 | 已确认 |
| FR-0011 | 功能 | 通过受控 ASE Editor API 创建包含动态/不透明节点的新 Shader；声明式规格只允许白名单节点/字段，ASE 自己生成 ShaderLab/HLSL/ASEBEGIN | CLI 使用 EditorGraphSpec v2，所有 Property/Sampler 必填中文显示名与中文说明；Caster-like/Receiver-like 保存重载 manifest 一致；不支持版本/字段零写入；失败无目标半写或暂存残留 | REG-0026 REG-0027 REG-0028 REG-0029 REG-0037 REG-0038 REG-0039 REG-0040 | 已验证（v1 双进程结构；v2 当前团结创建/重编译及 Inspector 现场通过；验证资产已清理；CI 包版本路径与可移植校验清单已补强；新进程重开按用户约束未执行） |
| NFR-0001 | 非功能 | Roundtrip 保真：未修改字段逐字节不变 | roundtrip 测试断言 | REG-0001 | 已确认 |
| NFR-0002 | 非功能 | 未知节点 passthrough：schema 未覆盖时保真透传 | 混合样本测试 | REG-0002 | 已确认 |
| NFR-0003 | 非功能 | 性能：千节点级文件单命令 <1s | perf 基线测试 | REG-0011 | 已确认 |
| NFR-0004 | 非功能 | ASE 版本容忍：记录 Version 字段，未知新参数保持原样 | 版本混合样本测试 | REG-0002 | 已确认 |

## 推荐技术路径

### 主推荐

- 架构形态：模块化单体 Python CLI + 受控 MCP execute_code 片段 + 可安装的 Unity Editor GUI 资源 + Agent 技能文档
- 运行时/语言：Python >=3.10（uv 管理）；C# 仅用于仓库固定的受控保存片段与固定材质 GUI 兼容资源
- 前端/UI（如适用）：无 UI；stdout JSON 即 Agent 契约界面
- 后端/API（如适用）：不适用（本地 CLI，无长运行服务）
- 数据与迁移（如适用）：产物为版本化 `schemas.json`；不迁移用户数据；安装升级即重装
- 部署、CI、可观测性：`uv tool install .`；pytest/strict/构建门禁；stdout 单行 JSON；退出码 0/2/3
- 适用原因、成本与不变量：零运行时依赖；core 不依赖上层；未知节点保真；图写前结构有效；MCP 默认 loopback

### 备选

1. 纯 Agent 直改 + 校验器（删除 CLI 层）：依赖 D4 假设成立，复杂节点出错率不可控；作为 NFR-0002 之上的自然退化路径保留。
2. 全桥接（一切经 Unity 执行）：每操作秒级延迟、调试链长；被延迟与出错率证据否决。

## 架构与模块边界

| MOD ID | 模块/路径 | 职责与数据所有权 | 公开 API/事件 | 允许/禁止依赖 | 关联 FR/CR/ADR | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| MOD-CORE | src/asecli/core | ASE 文本解析、序列化、图块替换；唯一持有图数据模型 | `AseFile.from_path` / `parse_graph_text` / `parse_node_line` / `replace_graph` | 仅标准库；禁止依赖 schema/bridge/cli | FR-0001 FR-0002 ADR-0001 ADR-0008 | long |
| MOD-SCHEMA | src/asecli/schema | 节点参数 schema 库与提取工具；schema JSON 产物所有权 | schema_for | 允许依赖 core 类型；禁止 bridge/cli | FR-0002 ADR-0003 | long |
| MOD-CHECK | src/asecli/checks | 结构校验与 CHKSM 修复 | validate/fix_checksum | 允许 core；禁止 bridge/cli | FR-0003 ADR-0003 | long |
| MOD-BRIDGE | src/asecli/bridge | MCP 传输、URL/token 信任边界、tool result、重编译、受控 Editor 图创建与 GUI 支持安装 | `McpClient` / `recompile_via_mcp` / `create_shader_via_mcp` / `inspect_gui_support` / `install_gui_support` | 标准库；禁止依赖 cli | FR-0004 FR-0009 FR-0011 CR-0008 CR-0012 ADR-0002 ADR-0007 ADR-0012 ADR-0013 ADR-0015 | long |
| MOD-CLI | src/asecli/cli | 命令入口与 JSON 输出契约；组合根；create 后端路由、属性呈现写入门禁与版本化可校验 CI 打包 | `asecli <command>` | 允许 core/schema/check/bridge | FR-0007 FR-0010 FR-0011 CR-0008 CR-0012 BUG-0017 BUG-0018 ADR-0001 ADR-0009 ADR-0012 ADR-0015 | long |
| MOD-SKILL | skills/asecli | Agent 技能、节点精排、材质属性呈现与 Master / Output 设置规范（文档资产） | `SKILL.md`；`references/layout-standard.md`；`references/material-property-standard.md`；`references/master-output-settings-standard.md` | 无代码依赖 | FR-0006 FR-0008 FR-0009 FR-0010 CR-0007 ADR-0001 ADR-0010 ADR-0011 | long |
| MOD-LAYOUT | src/asecli/core/layout.py | 节点布局算法（左到右分层递进 + 严格列/行网格 + 交叉减少）；布局结果所有权 | `layout_positions(graph) -> dict[id, (x, y)]` | 允许依赖 core 模型；禁止依赖 schema/bridge/cli | FR-0008 ADR-0005 | long |
| MOD-CUSTOM-GUI | src/asecli/core/custom_gui.py; material_gui_spec.py; property_presentation.py | ASE 1.9.6.2 CustomEditor/ASECLI 元数据解析、UTF-16 文本编码、显示名/属性定位、声明式批量写回与属性呈现契约 | `inspect_custom_gui` / `resolve_property_node` / `apply_material_gui_spec` / `require_property_presentation` | 仅依赖 core model/标准库；CLI 只能走公开 API | FR-0009 FR-0010 ADR-0010 ADR-0011 ADR-0014 ADR-0015 CR-0010 CR-0012 | long |
| MOD-GUI-SUPPORT | src/asecli/bridge/gui_support.py; bridge/resources/asecli_material_gui.cs.txt | 安全安装 clean-room ASECLI ShaderGUI；解释三类 ASECLI 元数据并读取旧三标记；动态生成技术 Tooltip | `inspect_gui_support` / `install_gui_support`; `ASECLI.MaterialGUI.ASECLIMaterialGUI` | Python 仅标准库；C# 仅 UnityEditor/UnityEngine；禁止依赖 ASE API | FR-0009 ADR-0014 CR-0010 | long |
| MOD-COMMENTARY | src/asecli/core/commentary.py | ASE CommentaryNode 可变长序列化、成员树与自动包围框 | `inspect_comment_groups` / `create_comment_group` | 仅依赖 core model/graph_ops；禁止依赖 check/bridge/cli | FR-0010 ADR-0011 | long |

### FR-0009 影响分析与兼容边界

- 受影响模块：MOD-CUSTOM-GUI、MOD-GUI-SUPPORT、MOD-CLI 与 MOD-SKILL；`gui-support` 保留安全安装职责，但删除原生提供者检测和 MCP runtime probe 的公共选项。
- CR-0011 在不改变三种元数据名称的前提下，为 `gui-support` 增加只读的 `capabilities.inline_help_presentation` 输出，并把契约校验作为 `--write` 前置门禁；属于 additive JSON 契约，旧调用方可忽略新字段。
- 数据/格式：新写入只生成 `ASECLIFoldout`、`ASECLITooltip`、`ASECLIHelpBox`。旧 `FoldoutMzgui`、`TooltipMzgui`、`HelpBoxMzgui` 仅由读取路径解释；写同一语义或执行对应 clear 时会移除旧标记。版本矩阵精确限定：`19109/19602` 可读写 CustomEditor，只有真实 `19602` 可读写 `<count>;<attributes...>` 尾部；其他版本失败关闭。
- 安全：自定义类名仅接受命名空间限定的 C# 标识符；禁止分号、引号、换行注入；元数据只允许导出的 `Property` 节点；原始专家入口只接受三种 ASECLI 标记；无法确定唯一主 Master 或尾部时失败关闭。
- 兼容/迁移：唯一推荐 Editor 为 `ASECLI.MaterialGUI.ASECLIMaterialGUI`；固定安装路径冲突仍拒绝覆盖。旧 Shader 不批量修改；要写入新元数据时，用户在同一命令显式指定该 Editor 后才迁移。零运行时 Python 依赖、零批量迁移。
- 运行边界：CLI 同步 ShaderLab `CustomEditor`、已确认版本的 PropertyNode 中文显示名和对应编译 Properties 标签；元数据写入后仍需 `recompile` 由真实 ASE 重新生成。内置 C# 的编译和属性读取需隔离 Editor 验证，真实 Foldout/悬停/HelpBox 外观仍需目标平台 UI 验收。
- 呈现规范：`asecli.property-presentation.v1` 强制每个导出属性具有中文 `display_name` 和中文 `ASECLIHelpBox`；ASECLI GUI 在显示时追加英文变量名与默认基线，并从默认 `Material(shader)` 读取，不把技术信息硬编码进节点尾部。常驻说明继续使用 `asecli.inline-help.v1`；`custom-gui` 必须逐属性报告合规状态，任何已经声明 ASECLI GUI 的文件不得通过 CLI 写入破坏该契约。

### FR-0010 影响分析与兼容边界

- 受影响模块：MOD-CUSTOM-GUI 增加声明式批量规范；新增 MOD-COMMENTARY；MOD-CLI 增加 additive `comment-group`；MOD-SKILL 固化截图中的属性说明和 Comment 层级规范。
- CR-0012 将原建议提升为 CLI 硬门禁：`custom-gui --spec` 新增 `display_name`，与 `help` 一次性治理；文本创建检查最终组合文件；ASECLI-managed 文件的相关写入必须保持完整契约，不能通过清空 CustomEditor 绕过。
- 数据/格式：属性排序仅改 PropertyNode 字段 9；Comment 使用 ASE 1.9.6.2 原生 `<width>;<height>;<note>;<count>;<members...>;<title>;<color>;0;0`，不引入旁路注释文件。
- 安全/失败：JSON 未知键、重复属性、错误类型、非 ASECLI 元数据新增、Comment 重复归属/缺失成员/注入字符均在写盘前失败；一个命令最多一次原子写入和一个 `.bak`。
- 运行边界：普通节点尺寸不在 ASE 文本中序列化，Comment 自动框采用保守 `200x120` 估计；结构、成员和 CHKSM 可自动验证，真实边距与 Inspector 视觉仍需目标编辑器验收。
- 操作顺序：先识别复用结果和算法边界；跨区/多消费者结果以一个语义 Register 和多个就近 Get 收敛长线；再布局节点并从内到外建立 Comment。现有全图 `layout` 不维护 Comment 层级，打组后禁止再次全图布局。
- 视觉规范：严格对齐与阶段递进优先于机械追求零交叉。线与线可在空白通道中少量、简洁地交叉，但不得穿过无关节点；重复分支必须保持相同列、行距和内部模板，最终精排感必须由真实 ASE 画布验收。
- Local Var 边界：Comment 表达算法职责，Local Var 表达模块间数据接口；Register 放生产者右侧、Get 放消费者输入侧。一次性同组相邻链路保持直连，禁止为表面整齐隐藏关键依赖或使用 `Value/Temp1/base` 等模糊名。
- 工具边界：真实 ASE 1.9.6.2 将 Register 端口类型随输入同步，当前 schema `layout_ok=false`；CLI 不通过不完整 schema猜造，必须由真实 ASE 创建或复用同版本同类型序列化样本后 validate/recompile。
- Master / Output 边界：上方基础生成设置默认继承模板和现有 Shader，不主动缩窄平台或提高特性等级；下方功能开关按实际消费者、Pass / variant 成本和目标效果选择。Master 行仍按 opaque 管理，只能在真实 ASE Editor 或已登记的语义能力中修改；目标平台未实测时不得宣称兼容或性能通过。

### FR-0011 影响分析与兼容边界

- 受影响模块：MOD-BRIDGE 新增声明式规格验证、固定 C# 执行器和 Save→Load manifest；MOD-CLI 为 `create` 增加 `text/editor/auto` 后端；MOD-SKILL 补充动态节点创建路径。
- 数据/格式：底层继续兼容 `EditorGraphSpec v1`；正式 CLI 创建要求 v2，并为每个 Property/Sampler 增加中文 `help` 与中文 `inspector_name` 门禁。Custom Expression HLSL 是节点数据，不是任意 C#；最终 ShaderLab/HLSL/ASEBEGIN 仍由当前 ASE `SaveToDisk` 生成，属性呈现元数据由 CLI 在提交后原子同步并复验。
- 安全：规格在联系 MCP 前完成节点/字段/属性唯一性/端口方向与类型校验；C# 执行器固定且参数采用安全编码；反射成员白名单并绑定能力探测；缺成员、版本不支持、Save/Load/模板与 Shader 身份/manifest 任一失败均失败关闭。
- 兼容/迁移：`create --from` 仍保留文本组合方式，但不合规结果写前拒绝；EditorGraphSpec v1 可继续由底层 API 解析/桥接，CLI 新建必须使用 v2。既有 Shader 不自动迁移，可通过完整 `custom-gui --spec` 治理。运行时矩阵和 CommandBuffer 状态继续留在宿主系统。
- 证据边界：mock/pytest 只证明规格、路由和响应契约；隔离团结 2022.3.61t9 + ASE 1.9.6.2 已完成创建、保存、关闭和第二进程重载，解除结构可编辑性风险；运行时矩阵、材质绑定与渲染正确性仍需目标工程单独验收。

- 数据、权限、第三方集成与安全边界：仅读写显式路径；MCP 默认 loopback；远程需 `--allow-remote-mcp`；token 仅从 `ASECLI_MCP_INSTANCE_TOKEN` 读取并脱敏；禁止重定向。`execute_code` 只注入仓库固定 ASE 保存片段，但仍按编辑器内代码执行信任边界管理。
- UI/设计来源、令牌与无障碍约束：不适用（无 UI）；JSON 输出结构即对外界面，字段变更视为 CR。
- 质量门禁、回归与发布要求：`uv run pytest -q`、REG catalog collect、strict 架构检查、可复现构建/哈希/隔离安装；目标平台证据与 mock 分层。
- 关键风险、未决 ADR 与复审日期：真实 Tuanjie/MCP 与 Agent E2E 已在隔离工程验收；GitHub Actions run 33510909955 与下载 artifact 已验证，GitHub Release/PyPI 和目标 GUI/渲染仍未验；下次复审 2026-09-08。

## 追溯与下游计划

- 交付计划与任务卡：`docs/04-delivery/project-plan-task-charter.md`（PLAN-0001）
- 追溯矩阵：`docs/00-governance/traceability.csv`
- 上游输入：`docs/first-principles/2026-08-31-231401-optimization-plan.md`

## 启动完成确认

- [x] 两份启动文档已按模板填充并通过严格校验
- [x] 技术路径与需求基线已经用户确认（本会话对话确认）
- [x] 模块边界与依赖方向已定义并写入模块地图
- [x] 首批 14 张任务卡与追溯矩阵已建立且双向链接

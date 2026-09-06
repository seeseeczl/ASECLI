---
id: ARCH-REQ-0001
type: project-architecture-and-requirements
status: 已确认
version: 1.9.0
created_at: 2026-08-31T23:25:00+08:00
owner: long
related: [PRJ-ASECLI, CR-0002, CR-0003, CR-0004, CR-0005, CR-0007, CR-0008, CR-0010, CR-0011, CR-0012, CR-0013, BUG-0015, BUG-0017, BUG-0018, FR-0009, FR-0010, FR-0011, AUD-20260901]
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
- 成功指标：既有 REG-0001～REG-0036 保持全绿；REG-0037/REG-0049 覆盖 `asecli.property-presentation.v2` 的逐属性报告、治理、创建、条件置灰和写入失败关闭；ASE 1.9.6.2 MZGUI_Test 与 CommentaryNode 真实序列化样本可读；1000 个附加节点单轮 <1s（REG-0011）。

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
| FR-0008 | 功能 | 节点精排：保留旧分层模式；`meticulous` 使用 ASE 真实节点/标题/端口几何，以 Output 为根从右向左递归形成局部鱼骨，每个父节点的直属来源输出端口局部右对齐，并自内向外收紧 Comment | 主骨端口水平误差 ≤8px；直属来源输出端口 x 偏差 ≤8px；主骨上下分支数差 ≤1；层间边界 64–160px；节点/子树/Comment 零重叠和零越界；默认保持 WireNode，显式路由后逻辑边等价；同输入第二次移动为零 | REG-0012 REG-0050 REG-0051 | 已确认 |
| FR-0009 | 功能 | 为 ASE 提供 MZGUI-compatible 材质 GUI：原生 `MZGUI.MZGUI` 存在时直接使用；确认缺失时安装提供同名入口的独立 fallback，并在 Unity Editor 内可视化编辑 Foldout、Tooltip、HelpBox | 新写入统一为 `CustomEditor "MZGUI.MZGUI"` 与 `FoldoutMzgui`、`TooltipMzgui`、`HelpBoxMzgui`；fallback 工程生成的 Shader 移入原生 MZGUI 工程无需改名；fallback 不修改 ASE 源码，通过运行时能力探测读写 ASE 原生 Custom Attributes；打开图时从编译 Shader 恢复三类属性，避免普通 Save 丢失；未知成员、双 provider 或冲突文件失败关闭 | REG-0022 REG-0030 REG-0035 REG-0036 REG-0047 | 已确认 |
| FR-0010 | 功能 | 按参考规范整理材质属性与 ASE 图：每个导出属性强制使用中文显示名，Tooltip 自动展示英文变量名与 Shader 默认值，属性下方强制提供中文用途/调节说明，并按 ShaderLab 属性名批量排序和中文分组；用原生 Comment 框表达算法边界；同一节点输出或算法结果被两个及以上不同组消费时使用 Register/Get Local Var；Master / Output 上方基础设置默认保持，下方功能开关按需选择 | Local Var 以去重后的消费组数量为门槛：两个及以上组必须注册，同组内无论复用多少次都允许不注册，但直连仍须避免重叠并尽量消除线线交叉；先移动节点/子树与已有 WireNode，明确允许结构调整时可增加最少锚点；已有 Register 的模块外消费者必须用就近 Get；允许生产者组内直连/其他消费组 Get 的混合；Comment 与 Shader 语义保持不变；失败可恢复 | REG-0010 REG-0023 REG-0024 REG-0037 REG-0050 | 已确认 |
| FR-0011 | 功能 | 通过受控 ASE Editor API 创建包含动态/不透明节点的新 Shader；声明式规格只允许白名单节点/字段，ASE 自己生成 ShaderLab/HLSL/ASEBEGIN | CLI 使用 EditorGraphSpec v2，所有 Property/Sampler 必填中文显示名与中文 Tooltip，HelpBox 可选；Caster-like/Receiver-like 保存重载 manifest 一致；不支持版本/字段零写入；失败无目标半写或暂存残留 | REG-0026 REG-0027 REG-0028 REG-0029 REG-0037 REG-0038 REG-0039 REG-0040 REG-0044 REG-0045 REG-0049 | 已验证（v2 团结创建/重编译、Inspector 现场及完全退出后的新进程重开通过；验证资产已清理；CI 包版本路径与可移植校验清单已补强） |
| NFR-0001 | 非功能 | Roundtrip 保真：未修改字段逐字节不变 | roundtrip 测试断言 | REG-0001 | 已确认 |
| NFR-0002 | 非功能 | 未知节点 passthrough：schema 未覆盖时保真透传 | 混合样本测试 | REG-0002 | 已确认 |
| NFR-0003 | 非功能 | 性能：千节点级文件单命令 <1s | perf 基线测试 | REG-0011 | 已确认 |
| NFR-0004 | 非功能 | ASE 版本容忍：记录 Version 字段，未知新参数保持原样 | 版本混合样本测试 | REG-0002 | 已确认 |

## 推荐技术路径

### 主推荐

- 架构形态：模块化单体 Python CLI + 受控 MCP execute_code 片段 + 可安装的 Unity Editor GUI 资源 + Agent 技能文档
- 运行时/语言：Python >=3.10（uv 管理）；C# 仅用于仓库固定的受控保存片段与固定材质 GUI 兼容资源
- 前端/UI（如适用）：CLI stdout JSON 是 Agent 契约；fallback 额外提供 `Window/Amplify Shader Editor/MZGUI Attributes (ASECLI)` 原生 EditorWindow
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
| MOD-BRIDGE | src/asecli/bridge | MCP 传输、URL/token 信任边界、tool result、重编译、受控 Editor 图创建、WireNode 路由事务、确定性资源拼装与 GUI 支持升级 | `McpClient` / `recompile_via_mcp` / `create_shader_via_mcp` / `apply_wire_routes_via_mcp` / `inspect_gui_support` / `install_gui_support` | 标准库；禁止依赖 cli | FR-0004 FR-0008 FR-0009 FR-0011 CR-0008 CR-0012 CR-0014 CR-0021 ADR-0002 ADR-0007 ADR-0012 ADR-0013 ADR-0015 ADR-0016 | long |
| MOD-CLI | src/asecli/cli | 命令入口与 JSON 输出契约；组合根；create 后端路由、属性呈现写入门禁与版本化可校验 CI 打包 | `asecli <command>` | 允许 core/schema/check/bridge | FR-0007 FR-0010 FR-0011 CR-0008 CR-0012 BUG-0017 BUG-0018 ADR-0001 ADR-0009 ADR-0012 ADR-0015 | long |
| MOD-SKILL | skills/asecli | Agent 技能、节点精排、材质属性呈现与 Master / Output 设置规范（文档资产） | `SKILL.md`；`references/layout-standard.md`；`references/material-property-standard.md`；`references/master-output-settings-standard.md` | 无代码依赖 | FR-0006 FR-0008 FR-0009 FR-0010 CR-0007 ADR-0001 ADR-0010 ADR-0011 | long |
| MOD-LAYOUT | src/asecli/core/layout.py; meticulous_layout.py; layout_audit.py; comment_layout.py; wire_geometry.py; wire_router.py | 兼容分层布局；递归局部鱼骨、同层端口右对齐、次级边/Local Var/Comment 质量审计与显式路由计划 | `layout_positions`；`meticulous_layout_positions`；`audit_meticulous_layout`；`plan_wire_routes` | 允许依赖 core 模型；禁止依赖 schema/bridge/cli | FR-0008 ADR-0005 CR-0019 CR-0020 CR-0021 | long |
| MOD-CUSTOM-GUI | src/asecli/core/custom_gui.py; material_gui_spec.py; property_presentation.py | ASE 1.9.6.2 CustomEditor/ASECLI 元数据解析、UTF-16 文本编码、显示名/属性定位、声明式批量写回与属性呈现契约 | `inspect_custom_gui` / `resolve_property_node` / `apply_material_gui_spec` / `require_property_presentation` | 仅依赖 core model/标准库；CLI 只能走公开 API | FR-0009 FR-0010 ADR-0010 ADR-0011 ADR-0014 ADR-0015 CR-0010 CR-0012 | long |
| MOD-GUI-SUPPORT | src/asecli/bridge/gui_support.py; gui_provider_detection.py; bridge/_gui_resource_*.py; bridge/resources/asecli_material_gui*.cs.txt | 原生 MZGUI 优先选择；安全安装/升级 clean-room fallback；Material Inspector 渲染；ASE Editor 可视化属性编辑与保存前自动恢复 | `inspect_gui_support` / `install_gui_support`; `MZGUI.MZGUI`; `ASECLIGUIAttributesWindow` | Python 仅标准库；C# 仅 UnityEditor/UnityEngine，ASE 交互只允许字符串反射和能力探测，禁止源码补丁或编译期 ASE 引用 | FR-0009 ADR-0013 ADR-0016 ADR-0017 CR-0016 | long |
| MOD-COMMENTARY | src/asecli/core/commentary.py | ASE CommentaryNode 可变长序列化、成员树与自动包围框 | `inspect_comment_groups` / `create_comment_group` | 仅依赖 core model/graph_ops；禁止依赖 check/bridge/cli | FR-0010 ADR-0011 | long |

### FR-0009 影响分析与兼容边界

- 受影响模块：MOD-CUSTOM-GUI、MOD-GUI-SUPPORT、MOD-CLI 与 MOD-SKILL；`gui-support` 先静态/运行时识别原生 MZGUI，确认缺失时才安装 fallback。
- CR-0011 在不改变三种元数据名称的前提下，为 `gui-support` 增加只读的 `capabilities.inline_help_presentation` 输出，并把契约校验作为 `--write` 前置门禁；属于 additive JSON 契约，旧调用方可忽略新字段。
- 数据/格式：原生 MZGUI 与 fallback 都使用 `FoldoutMzgui`、`TooltipMzgui`、`HelpBoxMzgui`。旧 `ASECLI*` 仅保留读取迁移。原生 MZGUI 继续使用其尾部；fallback EditorWindow 使用 ASE 自带 Custom Attributes，并从编译 Shader 自动恢复缺失属性。
- 安全：自定义类名仅接受命名空间限定的 C# 标识符；禁止分号、引号、换行注入；元数据只允许导出的 `Property` 节点；原始专家入口只接受三种 ASECLI 标记；无法确定唯一主 Master 或尾部时失败关闭。
- 兼容/迁移：原生与 fallback 的公共 Editor 名统一为 `MZGUI.MZGUI`；原生存在时零注入，确认缺失时由 fallback 提供同名入口。旧 `ASECLI.MaterialGUI.ASECLIMaterialGUI` 只保留为读取兼容别名。已安装 `0.3.1` material-only 或 authoring preview 资源按已知哈希备份升级；未知内容不覆盖。
- 运行边界：CLI 同步 ShaderLab `CustomEditor`、已确认版本的 PropertyNode 中文显示名和对应编译 Properties 标签；元数据写入后仍需 `recompile` 由真实 ASE 重新生成。内置 C# 的编译和属性读取需隔离 Editor 验证，真实 Foldout/悬停/HelpBox 外观仍需目标平台 UI 验收。
- 呈现规范：`asecli.property-presentation.v2` 强制每个导出属性具有中文 `display_name` 和中文 `TooltipMzgui`；选中的 GUI 在 Tooltip 中追加英文变量名与默认基线。`HelpBoxMzgui` 是用户可选内容，存在不违规、缺失不阻断。

### FR-0010 影响分析与兼容边界

- 受影响模块：MOD-CUSTOM-GUI 增加声明式批量规范；新增 MOD-COMMENTARY；MOD-CLI 增加 additive `comment-group`；MOD-SKILL 固化截图中的属性说明和 Comment 层级规范。
- CR-0012 将原建议提升为 CLI 硬门禁：`custom-gui --spec` 新增 `display_name`，与 `help` 一次性治理；文本创建检查最终组合文件；ASECLI-managed 文件的相关写入必须保持完整契约，不能通过清空 CustomEditor 绕过。
- 数据/格式：属性排序仅改 PropertyNode 字段 9；Comment 使用 ASE 1.9.6.2 原生 `<width>;<height>;<note>;<count>;<members...>;<title>;<color>;0;0`，不引入旁路注释文件。
- 安全/失败：JSON 未知键、重复属性、错误类型、非 ASECLI 元数据新增、Comment 重复归属/缺失成员/注入字符均在写盘前失败；一个命令最多一次原子写入和一个 `.bak`。
- 运行边界：普通节点尺寸不在 ASE 文本中序列化，Comment 自动框采用保守 `200x120` 估计；结构、成员和 CHKSM 可自动验证，真实边距与 Inspector 视觉仍需目标编辑器验收。
- 操作顺序：先识别算法边界并按 Comment/算法组归类消费者；两个及以上不同消费组必须使用一个语义 Register 和各组就近 Get，同组内复用次数不触发注册。随后按递归局部鱼骨对齐端口并留出通道；默认保持 WireNode，只有 `--route-wires` 才先移动既有锚点、再由 Editor API 增加每条最多两个锚点；最后从内到外收紧 Comment 并补齐可可靠推断的作用标题。
- 视觉规范：严格对齐与阶段递进优先于机械追求零交叉。线与线可在空白通道中少量、简洁地交叉，但不得穿过无关节点；重复分支必须保持相同列、行距和内部模板，最终精排感必须由真实 ASE 画布验收。
- Local Var 边界：Comment 表达算法职责，Local Var 表达模块间数据接口；同一节点或算法结果被两个及以上不同消费组使用时必须注册，全部消费者位于同组时无论复用多少次均可不注册。Register 放生产者右侧、Get 放其他消费组输入侧；允许生产者组内直连/其他组 Get 的混合；Register 已存在时禁止继续向模块外消费者直连。同组直连仍须通过节点布局、通道和已有 WireNode 尽量消除交叉/重叠，新增 WireNode 必须是明确允许的结构调整。每个决定必须记录去重消费组数量、组 ID、模块归属和理由。
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

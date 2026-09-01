# 模块地图 — AseCLI

| 模块 ID | 模块/路径 | 关联 FR/CR | 职责 | 公开 API/事件 | 依赖方向 |
| --- | --- | --- | --- | --- | --- |
| MOD-CORE | src/asecli/core | FR-0001 FR-0002 FR-0005 CR-0002 CR-0005 BUG-0002 BUG-0007 BUG-0009 | 行式模型、图块替换、最小差异写回 | `AseFile.from_path`；`parse_graph_text`；`parse_node_line`；`replace_graph` | 仅标准库；禁止依赖 schema/bridge/cli |
| MOD-SCHEMA | src/asecli/schema | FR-0002 CR-0002 BUG-0001 | 节点 schema、版本兼容与 mutation allowlist | `schema_for`；`schema_version`；`is_version_compatible` | 允许依赖 MOD-CORE 类型；禁止依赖 bridge/cli |
| MOD-CHECK | src/asecli/checks | FR-0003 CR-0002 CR-0003 BUG-0003 BUG-0006 | 图结构校验与 CHKSM 重算 | `validate_file`；`verify_checksum`；`fix_checksum` | 允许依赖 MOD-CORE；禁止依赖 bridge/cli |
| MOD-BRIDGE | src/asecli/bridge | FR-0004 FR-0009 FR-0011 CR-0001 CR-0004 CR-0008 BUG-0005 | MCP 客户端、loopback 信任边界、tool result、重编译、受控 Editor 图创建与 GUI 支持安装 | `recompile_via_mcp`；`create_shader_via_mcp`；`inspect_gui_support`；`install_gui_support`；`McpClient` | 仅标准库；禁止依赖 cli；远程需显式授权 |
| MOD-CLI | src/asecli/cli | FR-0003 FR-0005 FR-0007 FR-0009 FR-0010 FR-0011 CR-0002 CR-0003 CR-0004 CR-0005 CR-0006 CR-0008 BUG-0004 BUG-0006 BUG-0008 BUG-0009 | 15 个命令、单行 JSON、写入/信任组合根与 create 后端路由 | `asecli <command>` | 允许依赖 core/schema/check/bridge；只能使用公开 API |
| MOD-SKILL | skills/asecli | FR-0006 FR-0008 FR-0009 FR-0010 CR-0007 | Agent 技能文档：ASE 格式说明、精排规范、材质属性四层呈现规范、图/GUI/Comment/Local Var/编译操作手册、错误处理指引 | `SKILL.md`；`references/layout-standard.md`；`references/material-property-standard.md`（文档资产） | 无代码依赖；文档引用 CLI 契约 |
| MOD-LAYOUT | src/asecli/core/layout.py | FR-0008 | 节点精排算法：数据流左到右分层、同阶段严格列对齐、同列等距、重复结构模板化、确定性输出 | `layout_positions(graph, gap_x, gap_y) -> dict` | 允许依赖 core 模型；禁止依赖 schema/bridge/cli |
| MOD-CUSTOM-GUI | src/asecli/core/custom_gui.py; custom_gui_versions.py; material_gui_spec.py | FR-0009 FR-0010 | 真实版本能力矩阵；主 Master/ShaderLab CustomEditor 同步；PropertyNode MZGUI 尾部、UTF-16 文案编码、属性定位和批量规范 | `inspect_custom_gui`；`resolve_property_node`；`apply_material_gui_spec` | 仅依赖 MOD-CORE model；禁止依赖 schema/check/bridge/cli |
| MOD-GUI-SUPPORT | src/asecli/bridge/gui_support.py; gui_provider_detection.py; bridge/resources/asecli_material_gui.cs.txt | FR-0009 | 原生 MZGUI 静态/Editor 反射检测、unknown 门禁、内置 GUI 固定路径安装与技术 Tooltip | `inspect_gui_support`；`probe_native_mzgui_via_mcp`；`install_gui_support`；`ASECLI.MaterialGUI.ASECLIMaterialGUI` | Python 仅标准库；C# 仅 UnityEditor/UnityEngine；禁止依赖 ASE API |
| MOD-COMMENTARY | src/asecli/core/commentary.py | FR-0010 | CommentaryNode 可变长序列化、成员树检查与自动包围框 | `inspect_comment_groups`；`create_comment_group` | 仅依赖 MOD-CORE model/graph_ops；禁止依赖 schema/check/bridge/cli |

## 依赖规则

1. 依赖方向唯一：CLI → {core, schema, check, bridge}；schema/check/bridge → core；core 无内部依赖。
2. 任何模块禁止反向依赖 CLI；禁止跨层直接调用 bridge 内部函数（只能走公开 API）。
3. 未知节点类型不得被 schema 层丢弃或改写（passthrough 保真）。
4. 布局只改节点位置的 x/y 字段，禁止改动任何其他字段；连线集合布局前后必须一致。DAG 数据边应从左向右递进，Master 最右，同阶段和重复分支遵循精确网格；线与线可在空白通道中少量交叉，但不得穿过无关节点。
5. 自定义 GUI 只改唯一主 Master 的 Inspector 字段、编译区 CustomEditor 指令和目标 PropertyNode 的 MZGUI 尾部；不猜写其他 Pass 或编译 Properties。
6. GUI 支持安装器只允许创建固定资源且不覆盖不同内容；原生 MZGUI 优先。内置 ShaderGUI 只解释公开 Shader attribute，不引用 ASE 类型，因此 ASE 版本差异不得进入 Inspector 层。
7. Comment 分组只新增原生 CommentaryNode，不移动成员、不改参数/连线；一个节点只能直属一个 Comment，嵌套时外层只引用内层 Comment ID。
8. Editor 图创建只接受 `EditorGraphSpec v1` 白名单语义；禁止任意 C#、任意反射字段和不支持版本的猜测写入。普通静态节点继续优先走离线 core。

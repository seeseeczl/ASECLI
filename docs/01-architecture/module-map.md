# 模块地图 — AseCLI

| 模块 ID | 模块/路径 | 关联 FR/CR | 职责 | 公开 API/事件 | 依赖方向 |
| --- | --- | --- | --- | --- | --- |
| MOD-CORE | src/asecli/core | FR-0001 FR-0002 | ASE 文本解析器与序列化引擎：提取 `/*ASEBEGIN...ASEEND*/` 图数据，行式 Node/WireConnection 模型，最小差异写回 | `parse(path) -> AseGraph`；`serialize(graph) -> str` | 仅依赖标准库；禁止依赖 schema/bridge/cli |
| MOD-SCHEMA | src/asecli/schema | FR-0002 | 节点参数 schema 库与源码提取工具；未知节点降级为 passthrough | `schema_for(node_type) -> NodeSchema` | 允许依赖 MOD-CORE 类型；禁止依赖 bridge/cli |
| MOD-CHECK | src/asecli/checks | FR-0003 | 图结构校验（节点引用/连线完整性）与 CHKSM 重算修复 | `validate(graph) -> list[Issue]`；`fix_checksum(text) -> str` | 允许依赖 MOD-CORE；禁止依赖 bridge/cli |
| MOD-BRIDGE | src/asecli/bridge | FR-0004 FR-0005 CR-0001 | MCP for Unity 客户端（主通道）与重编译触发；Codely/batchmode 为备选 | `recompile_via_mcp(shader_path)` | 允许依赖 MOD-CORE（只读路径工具）；禁止依赖 cli |
| MOD-CLI | src/asecli/cli | FR-0007 | 命令入口与 JSON 输出契约：stdout 恒为机器可读 JSON，诊断走 stderr，统一错误码 | `asecli <command>` 子命令族 | 允许依赖 core/schema/check/bridge；组合根 |
| MOD-SKILL | skills/asecli | FR-0006 | Agent 技能文档：ASE 格式说明、三链路操作手册、错误处理指引 | SKILL.md（文档资产） | 无代码依赖；文档引用 CLI 契约 |
| MOD-LAYOUT | src/asecli/core/layout.py | FR-0008 | 节点布局算法：数据流分层（Sugiyama-lite）、行内对齐与等距、确定性输出 | `layout_positions(graph, gap_x, gap_y) -> dict` | 允许依赖 core 模型；禁止依赖 schema/bridge/cli |

## 依赖规则

1. 依赖方向唯一：CLI → {core, schema, check, bridge}；schema/check/bridge → core；core 无内部依赖。
2. 任何模块禁止反向依赖 CLI；禁止跨层直接调用 bridge 内部函数（只能走公开 API）。
3. 未知节点类型不得被 schema 层丢弃或改写（passthrough 保真）。
4. 布局只改节点位置的 x/y 字段，禁止改动任何其他字段；连线集合布局前后必须一致。

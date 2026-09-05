# 测试策略 — AseCLI

## 层级

1. **单元测试**（pytest）：core 解析/序列化、check 校验规则、checksum 重算；schema 查询。
2. **Roundtrip 测试**：真实 ASE `.shader` 样本 parse -> serialize -> 逐字节比对；变异操作后与预期最小差异比对。
3. **契约测试**：CLI 每个子命令 stdout 必须为合法 JSON 且含 `ok` 字段；错误码枚举固定。
4. **桥接集成测试**（需 Unity/Tuanjie 开启）：标记 `@pytest.mark.bridge`，验证 recompile 后 HLSL 变更与 CHKSM 更新；2026-09-01 已在 Tuanjie 2022.3.62t2 隔离工程通过。
5. **Agent 端到端**：SKILL.md 指引下完成 create→add-node→validate→recompile；2026-09-01 已在隔离工程完成并保留脱敏日志、前后哈希和 JSON 结果。
6. **安全契约**：MCP URL、token、重定向、tool error、SSE/JSON 请求 ID 一一关联与脱敏使用纯本地 mock；真实 loopback 另行验收。
7. **性能**：1000 个附加节点、精确 1007 节点、5 轮 parse+layout+serialize+roundtrip；每轮 <1s。
8. **节点精排**：同阶段 x 严格一致、相邻阶段间距等于 `gap_x`、同列行距等于 `gap_y`、DAG 数据边向右推进、重复分支共用列/行模板、Master 最右；同时保持确定性、连线和非位置字段不变。
9. **自定义 GUI**：真实 `19109` 仅验证 CustomEditor；ASE 1.9.6.2 图版本 `19602` 验证 ASECLI 三标记、旧三标记读取兼容、触碰迁移与未知未来版本/尾随数字歧义写前拒绝。`gui-support` 覆盖唯一资源的安装安全、`asecli.inline-help.v1` 和已知旧哈希升级；未知内容、符号链接、冲突备份、并发变化或替换失败必须零覆盖。`custom-gui` 输出 `asecli.property-presentation.v1` 的逐属性状态。任何已声明 ASECLI GUI 的文件若缺中文显示名、中文说明或一致 Editor，相关写入必须失败。真实编译和 Inspector 只使用团结引擎，不以 Unity 2021 结果作为当前验收。
10. **批量材质规范**：属性名/节点 ID 唯一定位；字段 9 排序；未列属性稳定追加；`display_name` 同步已确认的 PropertyNode 字段和编译 Properties；中文显示名与中文 `ASECLIHelpBox` 可在单份 JSON 内原子修复；JSON 重复、未知键、错误类型和非 ASECLI 元数据全量失败且零写盘。
11. **Comment 分组**：真实 CommentaryNode 行解码；自动边界、嵌套成员树、无关组重叠拒绝与检查、父子完整包含、非法标题/重复归属/缺失节点、dry-run、备份、CHKSM、roundtrip 与 CLI 单行 JSON。
12. **Local Var 图治理**：Agent 设计审查检查“多处/跨区复用才注册、一个语义 Register/多个就近 Get、同组一次性链路直连、命名唯一明确”；当前以真实参考静态证据与 Skill 契约为准，下一个目标 Shader 任务补实际图验收。
13. **Editor API 创建**：底层 v1 继续覆盖白名单、端口、参数编码和已验证的隔离团结结构 E2E；正式 CLI 只接受 EditorGraphSpec v2，并在 MCP 前强制每个 Property/Sampler 的中文 `inspector_name/help`。ASE 暂存 Save/Load 与 manifest 对账后提交，CLI 写入 ASECLI GUI 与说明并执行文件级契约复验；目标图由独立 `recompile` 重载，避免 MCP 插件重连吞掉创建回执。覆盖 MCP 3.4.7 裸文本/`data.result`、`success=false`、固定事务 `safety_checks=false` 和零暂存残留；后验失败保留目标和 `.meta`。真实 Inspector 与新进程重开必须单独记录，不能复用结构 E2E 结论。
14. **可复现交付**：锁定 build backend，双构建输出位于 checkout 外；比较 wheel/sdist hash，失败报告 gzip header、tar 成员元数据和内容差异，正式 artifact 继续阻塞。
15. **真实 ASE 画布**：结构结果始终保持 `visual_validation=pending`，由团结 `2022.3.61t9` + ASE `1.9.6.2` 的正常缩放截图和人工清单独立签收；检查阶段、重复分支、Comment containment、连线不穿无关节点/端口/标题栏及语义 diff，证据固定在 REG-0041。
16. **Material Inspector UI 矩阵**：在同一隔离 Editor 覆盖 300/480px、深/浅色、Retina、长中文、Foldout、mixed、disabled、focus/Tab；自动测试验证展示实现与 Tooltip 格式，真实截图验证可读性，二者不能互相替代，证据固定在 REG-0042。
17. **打包 C# 与升级恢复**：GUI/Editor 源码按显式列表确定性拼装，逐片段 LOC、拼装 SHA-256、wheel/sdist 成员、单 payload/单事务边界均作为门禁；旧 GUI 只在 SHA-256 命中已登记版本时执行“备份→fsync→复核 digest/inode→同目录原子替换”，备份冲突和 TOCTOU 注入必须失败关闭。干净 Editor E2E 用隐藏占位文件保护首次刷新前的空输出目录。

## 门禁

| 场景 | 命令 | 要求 |
| --- | --- | --- |
| 本地/PR | `uv run pytest -q` | 全绿 |
| REG 文档 | `python3 tools/check_regression_catalog.py` | 所有 pytest 代码片段可解析，环境变量/uv 选项被分类，登记文件/节点单进程可收集且 `missed=0` |
| 里程碑 | `uv run pytest -q -m "not bridge"` + 架构校验脚本 | 全绿且追溯完整 |
| 发布前 | 全量含 bridge + 快速审计 | S0/S1 清零 |

## 夹具来源

- 真实样本：从 `/Users/long/Documents/Tuanjie/Genesis` 工程收集 5+ 个不同复杂度 ASE shader（脱敏路径后入 `tests/fixtures/`）。
- 函数样本：ASE 自带 ShaderFunction `.asset`（m_functionInfo 提取）。
- MZGUI 样本：ASE 1.9.6.2 自带 `Examples/MZGUI_Test.shader` 只读采证；仓库回归保留真实旧 Foldout 节点行作为读取兼容夹具，不分发第三方完整示例，也不以其标记做新写入。
- 内置 GUI 样本：仓库只分发 clean-room `ASECLIMaterialGUI.cs` 资源。隔离团结引擎 `2022.3.61t9` 空工程编译该资源，并用最小 Shader 验证三种 ASECLI attribute 的真实装饰器实例和值、旧三标记读取，以及 `_Value=1.25` 的默认 Material 读取。执行入口为 `tests/test_material_gui_e2e.py`，必须显式传入带 `.asecli-gui-e2e-isolated` 标记的临时工程和团结可执行文件。
- Commentary 样本：ASE 1.9.6.2 `CommentaryNode.cs` 与 `/Users/long/GitHub/ShaderOpt/原生ASE文件.shader` 只读采证；仓库仅保留最小合成图和单行序列化回归，不修改或分发参考工程。

## 证据边界

- 普通 `pytest` 与 mock 证明纯文本、CLI、MCP 响应解析和安全契约，不替代真实 Tuanjie/MCP。
- `@pytest.mark.bridge` 只有在隔离工程、真实编辑器和实际 MCP 会话中运行后才能标为目标平台通过；当前证据为 `1 passed, 79 deselected`，测试 shader 前后 SHA-256 不同且最终 validate 0 errors。
- 本地构建/安装/回滚只证明可复制交付流程；`v0.1.0@fbd9941` 的 GitHub Actions run 33594698477 已完成双 Python、可复现构建、SPDX、供应链与隔离安装。私有正式 Release 的六项资产已下载复验，最终 wheel 的在线依赖漏洞扫描未发现依赖漏洞；PyPI/CLI Hub/公开分发仍未执行。
- REG-0022 的纯文本读写只证明 ASE 元数据与编译指令正确；材质 Inspector 中折叠、悬停和帮助框的真实视觉/交互效果，必须在写回并重编译后的目标 Tuanjie/Unity 工程单独验收。
- REG-0030 的 Python 测试证明 ASECLI 安装、冲突保护和资源契约；隔离团结 `2022.3.61t9` 已通过当前 C# 资源编译、三种 ASECLI attribute 实例化、旧标记读取和 Shader 默认值读取（`1 passed`）。同版本当前运行实例还确认了原生同名旧 drawer 冲突、fallback 源读取、新/旧 HelpBox 与标题点击的展开/收起。用户提供的实机截图还确认实际悬停浮层显示变量名 `_BaseColor` 和默认值 `RGBA(1.000, 1.000, 1.000, 1.000)`；桌面自动化不具备独立鼠标停留 API，但不再将 Tooltip 视觉列为未验收。
- REG-0036 的自动门禁证明固定说明条结构和 CLI 写前失败关闭；最终视觉仍以真实 Inspector 为准。2026-09-02 当前团结 `2022.3.61t9` 已确认 Receiver 材质说明无图标、无原生外框，具备弱背景、左侧强调线和弱化斜体，Console 0 error。
- REG-0037 的自动门禁证明属性呈现契约可查询、可原子治理且所有 CLI `create` 结果失败关闭；当前 Receiver/Caster 的文件级只读合规可作为现有资产证据。当前团结 `2022.3.61t9` 已完成 EditorGraphSpec v2 创建、独立 recompile 和临时材质 Inspector 验收：中文显示名/说明可见，运行时反射得到 `_AuditMask`/`None` 与 `_AuditStrength`/`0`，用户现场确认两项 Tooltip 气泡正常；随后恢复原选择并精确清理验证资产。新进程重开按用户“仅使用当前实例”的约束未执行，不复用当前实例证据。
- REG-0039 的失败优先证据来自 GitHub run 33623943475：双 Python verify 通过，但 package 使用硬编码 `0.1.0` wheel 路径而失败。修复后工作流只从 `uv version --short` 产生一个版本变量，SBOM 从 `uv.lock` 读取项目版本，CI governance 拒绝任何工作流中的 `asecli-X.Y.Z` 硬编码；远端 package 必须以修复提交重新通过。
- REG-0040 的失败优先证据来自 run 33624498244 下载 artifact：CI 内 package 全绿，但 SHA256SUMS 条目含 `dist/` 工作区前缀，解压后无法直接校验。修复后必须在 `dist` 目录内生成只含文件名的清单，并以真实下载 artifact 的 `shasum -a 256 -c SHA256SUMS` 作为最终证据。
- REG-0023/0024 自动测试证明规范的原子文本行为和原生 Comment 结构，不证明普通节点默认尺寸估计后的视觉边距；目标 ASE 编辑器仍需检查折叠顺序、说明可读性、框边距和连线可读性。
- REG-0012 自动测试证明精确网格、左到右递进和重复分支模板，不证明真实节点宽高、端口锚点、贝塞尔曲线路径或整体“精排感”；线与线少量交叉是否简洁仍需在真实 ASE 画布验收。
- CR-0007 当前只证明真实参考中 Register/Get 序列化与复用模式存在，以及 Agent Skill 已固化规则；尚未在用户指定的新目标 Shader 上执行 Local Var 改造，因此不宣称目标图已消除蜘蛛网。
- REG-0026～0028 的 pytest/mock 不证明 ASE 私有字段或 GUI 生命周期在目标版本可用；REG-0029 已在隔离团结 2022.3.61t9 + ASE 1.9.6.2 完成 v1 创建与新进程回读；REG-0037/0038 的 v2 已在同版本隔离工程完成退出后新进程重开；REG-0041/0042 分别补齐真实画布和 Inspector UI 矩阵。目标工程运行时材质绑定、目标平台编译和最终渲染仍需具体 Shader 任务独立验收。
- 已安装内容仅在命中 `GUI_SUPPORT_KNOWN_PREVIOUS` 时报告 `asecli_upgrade_available` 并允许可恢复升级；任意未知内容仍按 `target_conflict` 失败关闭，不放宽覆盖安全契约。REG-0045 已验证备份、复核、原子替换和失败保留。

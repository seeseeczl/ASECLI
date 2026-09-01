# 测试策略 — AseCLI

## 层级

1. **单元测试**（pytest）：core 解析/序列化、check 校验规则、checksum 重算；schema 查询。
2. **Roundtrip 测试**：真实 ASE `.shader` 样本 parse -> serialize -> 逐字节比对；变异操作后与预期最小差异比对。
3. **契约测试**：CLI 每个子命令 stdout 必须为合法 JSON 且含 `ok` 字段；错误码枚举固定。
4. **桥接集成测试**（需 Unity/Tuanjie 开启）：标记 `@pytest.mark.bridge`，验证 recompile 后 HLSL 变更与 CHKSM 更新；2026-09-01 已在 Tuanjie 2022.3.62t2 隔离工程通过。
5. **Agent 端到端**：SKILL.md 指引下完成 create→add-node→validate→recompile；2026-09-01 已在隔离工程完成并保留脱敏日志、前后哈希和 JSON 结果。
6. **安全契约**：MCP URL、token、重定向、tool error 与脱敏使用纯本地 mock；真实 loopback 另行验收。
7. **性能**：1000 个附加节点、精确 1007 节点、5 轮 parse+layout+serialize+roundtrip；每轮 <1s。
8. **节点精排**：同阶段 x 严格一致、相邻阶段间距等于 `gap_x`、同列行距等于 `gap_y`、DAG 数据边向右推进、重复分支共用列/行模板、Master 最右；同时保持确定性、连线和非位置字段不变。
9. **自定义 GUI**：HLIT 验证主 Master/编译 Inspector 读取；ASE 1.9.6.2 `MZGUI_Test.shader` 验证七类 PropertyNode 尾部；中文显示名读取、常驻 HelpBox、中文分组、非法输入、dry-run、备份与 CHKSM 自动回归。`gui-support` 另覆盖原生 MZGUI 检测、内置层 dry-run/安装/幂等、固定路径冲突拒绝、资源哈希和双 CustomEditor 契约。
10. **批量材质规范**：属性名/节点 ID 唯一定位；字段 9 排序；未列属性稳定追加；中文 `inspector_name` 可经 EditorGraphSpec 保存；JSON 重复、未知键、错误类型和非 MZGUI 全量失败且零写盘。
11. **Comment 分组**：真实 CommentaryNode 行解码；自动边界、嵌套成员树、无关组重叠拒绝与检查、父子完整包含、非法标题/重复归属/缺失节点、dry-run、备份、CHKSM、roundtrip 与 CLI 单行 JSON。
12. **Local Var 图治理**：Agent 设计审查检查“多处/跨区复用才注册、一个语义 Register/多个就近 Get、同组一次性链路直连、命名唯一明确”；当前以真实参考静态证据与 Skill 契约为准，下一个目标 Shader 任务补实际图验收。
13. **Editor API 创建**：纯 Python 覆盖 `EditorGraphSpec v1` 白名单、端口方向/类型、属性唯一性、后端路由、参数编码、Shader/模板身份、MCP 结果与失败事务；隔离团结工程分别创建 Caster-like 和 Receiver-like 图，关闭后由第二进程重载并比较节点、端口、属性、连接 manifest。

## 门禁

| 场景 | 命令 | 要求 |
| --- | --- | --- |
| 本地/PR | `uv run pytest -q` | 全绿 |
| REG 文档 | `python3 tools/check_regression_catalog.py` | 所有登记 pytest 文件/节点可收集 |
| 里程碑 | `uv run pytest -q -m "not bridge"` + 架构校验脚本 | 全绿且追溯完整 |
| 发布前 | 全量含 bridge + 快速审计 | S0/S1 清零 |

## 夹具来源

- 真实样本：从 `/Users/long/Documents/Tuanjie/Genesis` 工程收集 5+ 个不同复杂度 ASE shader（脱敏路径后入 `tests/fixtures/`）。
- 函数样本：ASE 自带 ShaderFunction `.asset`（m_functionInfo 提取）。
- MZGUI 样本：ASE 1.9.6.2 自带 `Examples/MZGUI_Test.shader` 只读采证；仓库回归保留其真实 Foldout 节点行并使用最小合成 Shader 覆盖写入，不分发第三方完整示例。
- 内置 GUI 样本：仓库只分发 clean-room `ASECLIMaterialGUI.cs` 资源。隔离 Unity 2021.3 空工程编译该资源，并用最小 Shader 验证三种 attribute 的真实装饰器实例和值、以及 `_Value=1.25` 的默认 Material 读取。
- Commentary 样本：ASE 1.9.6.2 `CommentaryNode.cs` 与 `/Users/long/GitHub/ShaderOpt/原生ASE文件.shader` 只读采证；仓库仅保留最小合成图和单行序列化回归，不修改或分发参考工程。

## 证据边界

- 普通 `pytest` 与 mock 证明纯文本、CLI、MCP 响应解析和安全契约，不替代真实 Tuanjie/MCP。
- `@pytest.mark.bridge` 只有在隔离工程、真实编辑器和实际 MCP 会话中运行后才能标为目标平台通过；当前证据为 `1 passed, 79 deselected`，测试 shader 前后 SHA-256 不同且最终 validate 0 errors。
- 本地构建/安装/回滚只证明可复制交付流程；远程 GitHub Actions/Release 在未 push 前保持未验证。
- REG-0022 的纯文本读写只证明 ASE 元数据与编译指令正确；材质 Inspector 中折叠、悬停和帮助框的真实视觉/交互效果，必须在写回并重编译后的目标 Tuanjie/Unity 工程单独验收。
- REG-0030 的 Python 测试证明检测、安装和资源契约；隔离 Unity E2E 证明 C# 编译、attribute 实例化和 Shader 默认值读取。BatchMode 没有执行真实 Inspector 的鼠标悬停与折叠点击，因此仍不能宣称目标 GUI 视觉验收通过。
- REG-0023/0024 自动测试证明规范的原子文本行为和原生 Comment 结构，不证明普通节点默认尺寸估计后的视觉边距；目标 ASE 编辑器仍需检查折叠顺序、说明可读性、框边距和连线可读性。
- REG-0012 自动测试证明精确网格、左到右递进和重复分支模板，不证明真实节点宽高、端口锚点、贝塞尔曲线路径或整体“精排感”；线与线少量交叉是否简洁仍需在真实 ASE 画布验收。
- CR-0007 当前只证明真实参考中 Register/Get 序列化与复用模式存在，以及 Agent Skill 已固化规则；尚未在用户指定的新目标 Shader 上执行 Local Var 改造，因此不宣称目标图已消除蜘蛛网。
- REG-0026～0028 的 pytest/mock 不证明 ASE 私有字段或 GUI 生命周期在目标版本可用；REG-0029 已在隔离团结 2022.3.61t9 + ASE 1.9.6.2 完成创建与新进程回读，证明当前白名单结构可编辑。目标工程运行时矩阵、材质绑定、平台编译和画面仍需独立验收。

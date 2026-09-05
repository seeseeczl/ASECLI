---
id: PLAN-0001
type: project-plan-task-charter
status: 已确认
version: 1.9.0
created_at: 2026-08-31T23:30:00+08:00
owner: long
related: [ARCH-REQ-0001, PRJ-ASECLI, FR-0008, FR-0009, FR-0010, FR-0011, CR-0007, CR-0008, CR-0010, CR-0011, CR-0012, CR-0013, BUG-0015, BUG-0017, BUG-0018, BUG-0019, BUG-0020, AUD-20260901, AUD-FLOW-002, AUD-FLOW-003, AUD-UI-001, AUD-CI-001]
supersedes: 无（首次启动）
evidence: [ARCH-REQ-0001 需求基线; 第一性原理计划书; 2026-09-01 标准审计与整改]
kickoff_completion: complete
---

# 交付计划与任务卡 — AseCLI

## 计划依据与目标

- 上游架构与需求总纲版本/链接：ARCH-REQ-0001 v1.0.0 — docs/01-architecture/project-architecture-and-requirements.md
- 本计划覆盖的 FR/NFR/CR：FR-0001～FR-0011、NFR-0001～NFR-0004、CR-0001～CR-0013
- 首个可交付垂直切片：MS-2 结束时——对真实 ASE shader 完成 parse→set-prop→写回→roundtrip 校验（纯文本链路，无 Unity）
- 交付假设、依赖与不包含范围：D4/D6/D10 已由 TASK-0001 验证；真实桥接依赖隔离 Tuanjie 工程与 MCP 会话；不包含 Hub/PyPI 远程发布与 UI

## 里程碑与审计

| 里程碑 | 目标/交付物 | 关联 ID | 依赖 | 验收/验证 | Owner | 目标日期 | AUD 日期 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MS-1 假设验证与骨架 | 三实验结论归档 + Git/uv/pytest 工程骨架 | TASK-0001 TASK-0002 | 无 | 实验结论写入架构文档；pytest 空跑通过 | long | 2026-09-02 | 2026-09-02 | 已完成 |
| MS-2 文本引擎与 schema | core 解析/序列化 + schema 提取 v1 + 修改命令 | TASK-0003 TASK-0004 TASK-0005 TASK-0006 TASK-0007 | MS-1 | REG-0001 REG-0002 REG-0009 REG-0011 全绿 | long | 2026-09-05 | 2026-09-05 | 已完成 |
| MS-3 校验修复与 CLI 契约 | validate/checksum-fix + JSON 契约 + 布局引擎 | TASK-0008 TASK-0009 TASK-0010 TASK-0015 | MS-2 | REG-0003 REG-0004 REG-0007 REG-0012 全绿 | long | 2026-09-07 | 2026-09-07 | 已完成 |
| MS-4 桥接与技能 | MCP 桥 + 模板创建 + SKILL.md | TASK-0011 TASK-0012 TASK-0013 | MS-3 | REG-0005 REG-0006 REG-0010（隔离 Tuanjie/MCP 已验收） | long | 2026-09-10 | 2026-09-01 | 已验证 |
| MS-5 验收与复审 | 端到端验收 + 标准增量复审 | TASK-0014 TASK-0016 TASK-0017 TASK-0018 TASK-0019 | MS-4 | 审计 S0/S1 清零；本地发布候选可恢复 | long | 2026-09-12 | 2026-09-01 | 已验证 |
| MS-6 自定义材质 GUI | ASE 1.9.6.2 CustomEditor、分组、提示和帮助框语义命令 | TASK-0020 | MS-3 | REG-0022 自动通过；真实 MZGUI_Test 隔离副本读写/validate 通过 | long | 2026-09-01 | 2026-09-08 | 已验证（真实 UI 待目标工程验收） |
| MS-7 参考规范吸收 | 属性批量排序/分组/说明规范；原生 Comment 嵌套分组 | TASK-0021 TASK-0022 | MS-6 | REG-0023 REG-0024 与双 Python/strict 全绿；真实 Inspector/ASE 视觉另行验收 | long | 2026-09-01 | 2026-09-08 | 已验证（真实 UI 待目标工程验收） |
| MS-8 Editor API 创建 | 受控规格创建模板、Sampler、CustomExpression；Save→Load manifest 与事务失败关闭 | TASK-0023~0028 | MS-4 | REG-0026~0029；自动门禁全绿，隔离团结 Caster/Receiver-like 重载一致 | long | 2026-09-02 | 2026-09-01 | 已验证（结构；目标画面待验） |
| MS-9 ASECLI GUI 协议迁移 | ASECLI 三标记、唯一内置 GUI、旧标记读取兼容与文档治理同步 | TASK-0030 | MS-6 | 定向 67 passed/1 skipped、Python 3.10/3.12 全量均 203 passed/3 skipped、双构建通过；当前团结 2022.3.61t9 验证新/旧 metadata、HelpBox、默认值和标题点击折叠；用户实机截图确认 Tooltip 悬停；`v0.1.0@fbd9941` CI、私有 Release 五项载荷哈希和清单摘要、隔离安装与回滚通过 | long | 2026-09-02 | 2026-09-02 | 已发布（REL-0002） |
| MS-10 说明条呈现契约 | `asecli.inline-help.v1` 可查询、可阻断安装，并以真实团结 Inspector 为最终视觉证据 | TASK-0031 | MS-9 | REG-0036；旧实现先失败；全量 208 passed/3 skipped；REG/CI governance/供应链/diff 通过；当前团结实例视觉对照与 Console 0 error；strict 仅复现 HEAD 的 29 项历史问题 | long | 2026-09-02 | 2026-09-02 | 已验证（待后续发布） |
| MS-11 属性呈现强制契约 | `asecli.property-presentation.v1` 可查询、可原子治理，并阻断所有不合规的 CLI 创建与 ASECLI-managed 写入 | TASK-0032 | MS-10 | REG-0037/0038/0039/0040；新用例先失败 5 项；双 Python 223 passed/3 skipped；REG/CI governance/供应链/Skill/可复现构建通过；两个真实 Shader 共 7 属性零违规；当前团结 v2 创建与独立重编译后两属性零差异；Inspector 中文显示名/说明与 Tooltip 现场通过；验证资产已清理；CI 包路径、SBOM 和下载校验清单已去除历史版本/工作区路径耦合；`v0.2.0` 私有正式 Release 已发布 | long | 2026-09-02 | 2026-09-02 | 已发布（REL-0003；新进程重开未执行） |
| MS-12 发布后成熟度整改 | 指定 ASE v2 双进程、治理事实源、真实画布、Inspector 矩阵、C# 例外清零/升级恢复和 Node 24 远程门禁闭环 | TASK-0033 TASK-0034 TASK-0035 TASK-0036 TASK-0037 TASK-0038 TASK-0039 TASK-0040 TASK-0041 | MS-11 | REG-0038/0041/0042/0043/0044/0045；Project Architect strict、全量 pytest、可复现构建、真实团结和 Node 24 远程 run | long | 2026-09-03 | 2026-09-03 | 已发布（REL-0004）；正式资产安装/升级/回滚闭环 |

## 原子任务卡

| TASK ID | 关联 ID | 单一目标/产物 | 输入/前置 | 允许路径 | 禁止路径 | 依赖/Owner/期限 | 验收、REG 与验证命令 | 停止条件 | 时间线/证据回写 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TASK-0001 | FR-0004 FR-0005 NFR-0004 | 三个假设实验结论归档 | ARCH-REQ-0001；ASE 样本 | docs/01-architecture/assumption-experiments.md；系统临时目录 | 修改 ASE 源码或用户工程 | 无/long/2026-09-01 | REG-0008：人工实验记录 | 需修改生产工程时停止 | assumption-experiments.md | 已完成 |
| TASK-0002 | FR-0001 NFR-0003 | Git + uv + pytest 工程骨架 | TASK-0001 | pyproject.toml；uv.lock；src/**；tests/** | 新增无关依赖 | TASK-0001/long/2026-09-02 | REG-0001：`uv run pytest -q` | pytest 不可用时停止 | 当前工作树基于 8883425 | 已完成 |
| TASK-0003 | FR-0001 NFR-0001 | ASEBEGIN/Node/Wire 解析 | TASK-0002 | src/asecli/core/model.py；tests/test_roundtrip.py | 引入第三方解析器 | TASK-0002/long/2026-09-03 | REG-0001：`uv run pytest tests/test_roundtrip.py` | 新格式无法保真时停止 | REG-0001 | 已验证 |
| TASK-0004 | FR-0001 NFR-0001 | 字节保真序列化 | TASK-0003 | src/asecli/core/model.py；tests/test_roundtrip.py；tests/fixtures/** | 格式化原始字段 | TASK-0003/long/2026-09-03 | REG-0001 | roundtrip 不一致时停止 | REG-0001 | 已验证 |
| TASK-0005 | FR-0002 NFR-0002 CR-0002 BUG-0001 | 生成并验证 schemas.json | ASE 源码只读 | tools/build_schema.py；src/asecli/schema/**；tests/test_schema_samples.py | 运行时依赖 ASE 源码 | TASK-0004/long/2026-09-04 | REG-0009 REG-0013 | 样本不匹配时停止 | REG-0009 REG-0013 | 已验证 |
| TASK-0006 | FR-0002 NFR-0002 | set-field 最小差异写回 | TASK-0005 | core/graph_ops.py；cli/commands.py；tests/test_mutate.py | 改结构字段 0-2 | TASK-0005/long/2026-09-04 | REG-0002：`uv run pytest tests/test_mutate.py::test_replace_node_minimal_diff` | 最小差异失败时停止 | REG-0002 REG-0015 | 已验证 |
| TASK-0007 | FR-0002 NFR-0002 CR-0002 BUG-0003 | add/connect/remove 图修改 | TASK-0006 | core/graph_ops.py；cli/commands.py；tests/test_graph_safety.py | 绕过 schema/写前门禁 | TASK-0006/long/2026-09-05 | REG-0013 REG-0015 | 未知节点保真失败时停止 | REG-0013 REG-0015 | 已验证 |
| TASK-0008 | FR-0003 CR-0002 BUG-0003 | validate 检出结构错误并失败退出 | TASK-0007 | checks/validate.py；cli/commands.py；tests/test_graph_safety.py | validate 自动修复 | TASK-0007/long/2026-09-06 | REG-0003 REG-0015 | 错误级别不明时停止 | REG-0003 REG-0015 | 已验证 |
| TASK-0009 | FR-0003 CR-0003 BUG-0006 | checksum 默认预览、显式写回 | TASK-0008 | checks/checksum.py；cli/**；tests/test_cli_contract.py | 默认隐式写盘 | TASK-0008/long/2026-09-06 | REG-0004 REG-0018 | checksum 算法不一致时停止 | REG-0004 REG-0018 | 已验证 |
| TASK-0010 | FR-0007 CR-0003 BUG-0004 | 11 个 CLI 的单行 JSON 错误契约 | TASK-0007 | cli/main.py；cli/commands.py；tests/test_cli_contract.py | stdout 非 JSON | TASK-0007/long/2026-09-07 | REG-0007 | 公共契约冲突时走 CR | REG-0007 | 已验证 |
| TASK-0011 | FR-0004 CR-0001 CR-0004 BUG-0005 | MCP 重编译与严格 tool result | TASK-0001 | src/asecli/bridge/**；tests/test_bridge_*.py | 任意外部代码；未授权远程 | TASK-0001/long/2026-09-08 | REG-0005 REG-0016 REG-0017 | 真实 MCP 失败时停止 | 隔离成功 `saved=true/changed=true`；失败 `BRIDGE_ERROR`/3 | 已验证 |
| TASK-0012 | FR-0005 CR-0002 BUG-0002 | create 组合模板壳与 donor 图 | TASK-0011 | core/model.py；cli/commands.py；tests/test_create.py | 复制 donor 外壳 | TASK-0011/long/2026-09-09 | REG-0006 REG-0014 | 真实 Editor 失败时停止 | 自动通过；隔离 Editor 重存后 11 nodes/0 errors | 已验证 |
| TASK-0013 | FR-0006 FR-0007 FR-0010 CR-0007 | Agent 技能操作链路、节点治理与错误处理 | TASK-0010 TASK-0012 | skills/asecli/SKILL.md | 描述未实现能力；用不完整 schema 猜造 Register | TASK-0012/long/2026-09-10 | REG-0010：隔离 Agent E2E；Local Var 规范静态核对 | 非文档原因失败时停止 | Skill 已增加防蜘蛛网规范；真实参考 31 Register/47 Get | 已验证（新规范目标图应用待实际任务） |
| TASK-0014 | FR-0001 NFR-0003 REG-0011 BUG-0007 | 1000 个附加节点的性能与正确性门禁 | TASK-0010 | tests/test_perf.py | 降低规模或恒真断言 | TASK-0010/long/2026-09-12 | REG-0011：`uv run pytest tests/test_perf.py` | 单轮 >1s 时登记 AUD | 1007 节点、5 轮通过 | 已验证 |
| TASK-0015 | FR-0008 | 确定性布局且仅修改 x/y | TASK-0004 | core/layout.py；tests/test_layout.py | 改其他字段/连线 | TASK-0010/long/2026-09-06 | REG-0012 | 破坏保真时停止 | REG-0012 | 已验证 |
| TASK-0016 | BUG-0008 AUD-GOV-001 | REG/TASK/追溯路径可执行 | 2026-09-01 审计 | governance/quality/delivery 文档；tools/check_regression_catalog.py | 删除历史 ID；伪造 Editor/CI 证据 | long/2026-09-01 | REG-0020 | 任一登记命令不可收集时停止 | catalog collect + strict | 已验证 |
| TASK-0017 | CR-0005 BUG-0009 AUD-ARCH-001 | 公开 core node parser API | TASK-0003 | core/model.py；core/__init__.py；cli/commands.py | 删除兼容 alias | long/2026-09-01 | REG-0019 | 私有跨模块导入仍存在时停止 | REG-0019 + fitness | 已验证 |
| TASK-0018 | CR-0006 AUD-OPS-001 | 双 Python CI、artifact 与 REL 回滚 | TASK-0016 | .github/workflows/ci.yml；docs/04-delivery/releases/** | 未单独授权的 push/远程 Release | long/2026-09-01 | REG-0021 + 本地双构建/安装回滚 | artifact 不可复现时停止 | REL-0001；后续正式发布见 REL-0002 | 基础链路已验证；`v0.1.0` 在后续单独授权下完成私有正式发布 |
| TASK-0019 | CR-0006 AUD-SUPPLY-001 | 内部许可、供应链策略和 SPDX SBOM | TASK-0018 | LICENSE；SECURITY.md；supply-chain-policy.md；tools/*sbom* | 上传源码/secret；新增项目依赖 | long/2026-09-01 | REG-0021 | secret/license/hash 失败时停止 | REL-0001 | 已验证 |
| TASK-0020 | FR-0009 | CustomEditor 与 MZGUI 分组/提示/帮助框的安全查询、预演和写回 | ASE 1.9.6.2 源码/MZGUI_Test；TASK-0010 | core/custom_gui.py；core/__init__.py；cli/main.py；cli/commands.py；cli/custom_gui_command.py；tests/test_custom_gui.py；README/SKILL/治理增量 | 修改 MZGUI C#；批量改 Pass Master；直接猜写编译 Properties；生产工程；新依赖 | TASK-0010/long/2026-09-01 | REG-0022：`uv run pytest tests/test_custom_gui.py`；双 Python 全量；strict | 无唯一主 Master、未知尾部或真实样本 roundtrip 失败时停止 | 真实 19602 样本 14 Property/13 属性/7 类型可读；隔离副本写入、备份、validate 0 errors | 已验证（真实 UI 待目标工程验收） |
| TASK-0021 | FR-0009 FR-0010 | 按 ShaderLab 属性名原子应用排序、分组与逐项说明 JSON 规范 | 三张参考图；TASK-0020 | core/material_gui_spec.py；cli/custom_gui_command.py；core/__init__.py；cli/main.py；tests/test_custom_gui.py；README/SKILL/治理增量 | 多次逐项写盘；编造属性语义；修改生产 Shader；新依赖 | TASK-0020/long/2026-09-01 | REG-0023：`uv run pytest tests/test_custom_gui.py`；双 Python 全量；strict | 未列属性丢失、重复 order 或整批失败仍写盘时停止 | Python 3.10/3.12 各 115 passed/1 skipped；strict 通过 | 已验证（真实 UI 待目标工程验收） |
| TASK-0022 | FR-0010 | 原生 CommentaryNode 自动包围、嵌套和语义标题命令 | 真实 CommentaryNode.cs/原生ASE文件.shader 只读证据；TASK-0010 | core/commentary.py；cli/commentary_command.py；core/__init__.py；cli/main.py；tests/test_commentary.py；README/SKILL/治理增量 | 修改参考/生产 Shader；移动成员或连线；旁路注释格式；新依赖 | TASK-0021/long/2026-09-01 | REG-0024：`uv run pytest tests/test_commentary.py`；双 Python 全量；strict | 可变长字段不匹配、重复归属或成员/连线变化时停止 | 真实参考 25 组/4 关键嵌套标题只读解析；0 Comment 错误；真实视觉待验收 | 已验证（真实 UI 待目标工程验收） |
| TASK-0023 | FR-0011 CR-0008 | `EditorGraphSpec v1` 严格规格与后端路由 | 第一性原理吸收计划；真实 Caster/Receiver 只读样本 | bridge/editor_spec.py；tests/test_editor_create_spec.py；治理文档 | 任意 C#/反射字段；生产工程写入；新依赖 | long/2026-09-01 | REG-0026 | 规格不能无歧义表达两样例时停止 | 端口/类型/属性唯一性在 MCP 前失败 | 已验证 |
| TASK-0024 | FR-0011 CR-0008 | 受控 ASE 窗口生命周期、版本/成员门禁与白名单节点适配器 | TASK-0023；ASE 1.9.6.2 源码只读证据 | bridge/editor_create.py；bridge C# 资源；tests/test_editor_create_bridge.py | 用户 C# 透传；无限反射；修改 ASE 源码 | TASK-0023/long/2026-09-01 | REG-0027 | 不支持版本或成员缺失未失败关闭时停止 | 固定资源/版本/反射门禁与关闭前成功契约通过 | 已验证 |
| TASK-0025 | FR-0011 CR-0008 | Save→Load manifest、目标不存在门禁和暂存失败恢复 | TASK-0024 | bridge/editor_create.py；cli/create_command.py；tests/test_editor_create_cli.py | 覆盖生产 Shader；宽泛清理路径 | TASK-0024/long/2026-09-01 | REG-0028 | 失败残留或目标半写时停止 | 模板/Shader/图 manifest 与事务回归通过 | 已验证 |
| TASK-0026 | FR-0011 CR-0008 | `create --backend text/editor/auto --spec` additive CLI 契约 | TASK-0023~0025 | cli/main.py；cli/create_command.py；README/SKILL；tests/test_editor_create_cli.py | 改变现有 text 默认语义 | TASK-0025/long/2026-09-01 | REG-0026 REG-0028 | 旧 create 回归时停止 | text 默认兼容；editor/auto/spec JSON 回归通过 | 已验证 |
| TASK-0027 | FR-0011 CR-0008 | 隔离团结工程 Caster-like/Receiver-like 真实创建与关闭重载 | TASK-0026；隔离工程/MCP | tests/test_editor_create_e2e.py；系统临时目录证据 | 修改 FlymeAuto3Test 生产文件；用 mock 代替 Editor | TASK-0026/long/2026-09-02 | REG-0029 | 需写生产工程或 Save/Load 不稳定时停止 | 1 passed/39.60s；11/14 nodes；双进程重载；关闭异常回滚；Console 0 error | 已验证（目标画面待验） |
| TASK-0028 | FR-0011 CR-0008 | 对抗性审计、必要修复、治理与交付回写 | TASK-0027 | tests/**；docs/adversarial-audits/**；治理文档 | push/Release；把未跑目标画面写成通过 | TASK-0027/long/2026-09-02 | REG-0027 REG-0028 REG-0029；全量/strict/REG catalog | P0/P1 未清零时阻塞 | 2026-09-01-193521 审计 4 项已修；全量/治理/REG/diff 门禁通过 | 已验证 |
| TASK-0029 | CR-0009 BUG-0010 BUG-0011 BUG-0012 BUG-0013 BUG-0014 | 执行第二轮对抗性审计优化计划并恢复发布门禁 | TASK-0028 | CI/build 诊断；custom_gui versions；MCP ID；Editor 后验；GUI provider；tests/docs | 删除一致性门禁；未知版本猜写；按路径清理；把 mock 写成真实 UI | TASK-0028/long/2026-09-01 | REG-0031 REG-0032 REG-0033 REG-0034 REG-0035；全量/strict/远程 CI | 远程 artifact 或未知版本门禁失败时阻塞 | 206 passed/2 skipped；GitHub run 33510909955 与下载 artifact 复验通过；真实 GUI probe/Inspector/渲染待验 | 已验证（目标 GUI 待验） |
| TASK-0030 | CR-0010 FR-0009 | 将新写入迁移为 ASECLI 自有三标记和唯一内置 GUI；旧三标记只读兼容；移除原生提供者选择 | 用户 2026-09-02 批准；TASK-0029 | core/custom_gui*；bridge/gui_support.py；C# resource；CLI；tests；README/SKILL/治理 | 批量修改用户 Shader；恢复原生扫描/反射；新增依赖；宣称未跑的 Tooltip 悬停已通过 | long/2026-09-02 | REG-0022 REG-0023 REG-0030 REG-0032 REG-0035；定向 67 passed/1 skipped、Python 3.10/3.12 全量均 203 passed/3 skipped、双构建通过；团结 `2022.3.61t9` 当前实例验证原生同名旧 drawer fallback、新/旧 HelpBox/默认值/标题点击折叠；用户截图确认 Tooltip 悬停；`v0.1.0@fbd9941` 的 run `33594698477` 全绿，私有 Release 五项载荷哈希和清单摘要、正式 wheel 隔离安装与回滚通过 | C# 编译或安全门禁失败时停止 | CR-0010 ADR-0014 REL-0002；未创建 PyPI/CLI Hub 或公开分发 | 已发布（内部正式 CLI） |
| TASK-0031 | FR-0009 CR-0011 BUG-0015 | 将轻量说明条样式固化为 CLI 可报告、可失败关闭的呈现契约 | 用户当前团结实例两张截图对照；TASK-0030 | bridge/gui_presentation.py；bridge/gui_support.py；C# resource；tests/test_gui_support.py；README 与治理增量 | 修改用户 Shader/材质参数；依赖 Agent 记忆或规则；用静态测试冒充最终视觉 | TASK-0030/long/2026-09-02 | REG-0036；`uv run pytest -q`、治理/供应链/diff；当前团结 `2022.3.61t9` Inspector 与 Console | 呈现契约无效、C# error 或真实界面未对照时停止 | 先失败 2 项；全量 208 passed/3 skipped；REG/CI governance/供应链/diff 通过；当前实例视觉通过；strict 同 HEAD 复现 29 项历史问题；尚未提交或发布 | 已验证（待后续发布） |
| TASK-0032 | FR-0005 FR-0010 FR-0011 CR-0012 CR-0013 BUG-0016 BUG-0017 BUG-0018 | 将中文显示名、自动变量名/默认值 Tooltip 和中文说明固化为所有 CLI 创建文件的强制契约，并闭合当前 MCP v2 创建回执及 0.2.0 CI 打包/校验路径 | 用户 2026-09-02 明确要求；TASK-0031 | core/property_presentation.py；custom_gui/material spec；EditorGraphSpec；create/写入门禁；CI/SBOM/SHA256SUMS；tests；README/治理 | 自动编造中文语义；修改生产 Shader；把 v1 真实 Editor 证据冒充 v2；依赖 Agent 规则；透传任意 C#；在 CI 硬编码历史包版本或工作区路径 | TASK-0031/long/2026-09-02 | REG-0037 REG-0038 REG-0039 REG-0040；双 Python全量、REG/CI governance/供应链/Skill/构建；当前团结 v2 创建/recompile/Inspector；远端 package 与下载 artifact 校验 | 契约可被绕过、MCP 失败被误报成功、非合规 create 能落盘、历史非 ASECLI 文件无法维护、CI 安装错误版本或下载清单不可直接校验时停止 | 新用例先失败 5 项；双 Python 223 passed/3 skipped；REG 36 条、CI governance、供应链、Skill、可复现 0.2.0 构建与隔离安装/回滚通过；Caster 1 属性/Receiver 6 属性零违规；当前团结 v2 创建与 recompile 后两属性零差异；Inspector 中文显示名/说明可见，用户现场确认 Tooltip 正常；验证资产已清理；create JSON 区分暂存重载与目标图重载；packed C# 执行器已具名 LOC 豁免；strict 历史项已校准；首次推送依次暴露旧版本硬编码和 SHA256SUMS 路径前缀，均已最小修复并等待最终远端 artifact 复验；新进程重开按用户约束未执行；0.2.0 已作为私有正式 Release 发布 | 已发布（REL-0003；限当前实例，新进程重开未执行） |
| TASK-0033 | FR-0011 CR-0012 CR-0013 AUD-FLOW-002 AUD-FE-001 | 在精确 ASE 1.9.6.2 上完成 EditorGraphSpec v2 创建进程与全新重开进程的 manifest/presentation 对账 | v0.2.0；团结 2022.3.61t9；隔离工程 | tests/test_editor_create_e2e.py；bridge/create 契约；系统临时证据 | Unity 2021；生产工程写入；以同进程 reload 冒充重开 | TASK-0032/long/2026-09-03 | REG-0038；真实 bridge E2E；0 Shader/CS error；0 staging 残留 | 版本不精确、MCP 完成状态未知或原工程 hash 变化时停止 | 两进程一致；原工程未变化；隔离资产最终清理 | 已验证 |
| TASK-0034 | AUD-GOV-002 AUD-GOV-003 AUD-SIZE-001 | 使 release-record、安全版本、FM/LOC 事实源和有期限 C# 例外通过完整治理门禁 | 最新增量审计；TASK-0033 | SECURITY；三份 REL；`.project-architect.json`；audit supplement；governance tests/docs | 改远端 Release；删除历史 ID；永久豁免；放宽 LOC | TASK-0033/long/2026-09-03 | REG-0020；Project Architect `--check-release --strict`；CI governance；连续 collect/coverage | 历史发布事实不一致或例外超过 30 天时停止 | release finding 清零；14 FM/15 FE 稳定；例外带退出条件 | 已验证 |
| TASK-0035 | FR-0008 FR-0010 AUD-FLOW-003 AUD-FE-002 | 固化小/中/复杂 ASE 图的结构不变与正常缩放真实画布验收 | TASK-0033；隔离画布样本 | layout/comment-group；REG-0041 证据；tests | 修改计算图；写生产 Shader；用结构 JSON 冒充视觉通过 | TASK-0033/long/2026-09-03 | REG-0041；语义 diff、TruePosition、截图人工清单 | wire/非布局字段变化或连线穿无关节点时停止 | `docs/03-quality/evidence/REG-0041/`；原工程 hash 一致 | 已验证 |
| TASK-0036 | FR-0009 FR-0010 CR-0010 CR-0012 BUG-0019 BUG-0020 AUD-UI-001 | 完成 Material Inspector 窄宽/主题/缩放/交互状态矩阵并修复长中文截断和浮点噪声 | TASK-0033；隔离 Inspector fixture | C# GUI 资源；tests/test_gui_support.py；REG-0042 证据 | 改 Shader 属性/材质值；重新设计 UI；覆盖未知旧 GUI | TASK-0035/long/2026-09-03 | REG-0042；定向 pytest；团结编译；真实截图矩阵 | C# error、属性值变化或任一必测组合不可读时停止 | `docs/03-quality/evidence/REG-0042/`；主题恢复；旧 GUI 升级另行设计 | 已验证 |
| TASK-0037 | CR-0006 AUD-CI-001 | 将三个 GitHub Action 升级到官方 Node 24 版本并以固定 SHA allowlist 防回退 | 官方 tag/API 只读核对；TASK-0034 | `.github/workflows/ci.yml`；tools/check_ci_governance.py；tests/test_governance.py；supply-chain-policy | 升级 Python 依赖；改变 job；推送或重发 Release | TASK-0034/long/2026-09-03 | REG-0043；CI governance/供应链/pytest；真实 run 全日志无 Node 20/Node 弃用警告 | runner 不满足 `>=2.327.1`、artifact 行为改变或仍输出弃用警告时继续阻塞 | run 33713836753 暴露 setup-uv v7.1.6 弃用；升级 v10.0.1 后 run 33714089230 全绿且零相关警告，artifact `9877900476` 下载复验通过 | 已验证 |
| TASK-0038 | CR-0014 BUG-0021 AUD-SIZE-001 | 将 Editor executor 拆为确定性片段并保持单 payload/单 nonce/单回滚边界，修复干净隔离目录 E2E | TASK-0033 TASK-0034；旧/当前资源 SHA | resource_text.py；editor_create.py；editor_create.part00/01；test_editor_create_e2e.py | 改 ASE 事务语义；多次 execute_code；使用 Unity 2021；写生产工程 | TASK-0034/long/2026-09-03 | REG-0044 REG-0045；拼装 hash、事务结构、团结双进程 | 字节变化、多个回滚边界或真实重载失败时恢复单资源 | `52fce4c…6cc4` 不变；干净隔离工程 1 passed/39.86s | 已验证 |
| TASK-0039 | CR-0014 AUD-SIZE-001 | 将 MaterialGUI 拆为确定性片段并删除两项 LOC 例外 | TASK-0038；REG-0042 | resource_text.py；gui_support.py；asecli_material_gui.part00/01 | 改 Inspector 行为/文本；新增 LOC 豁免；改变安装目标 | TASK-0038/long/2026-09-03 | REG-0044；片段 LOC、拼装/安装 hash、wheel 成员、治理 0 finding | 拼装 hash 或 Inspector 回归变化时恢复单资源 | `9541c54…c5b7a` 不变；片段 300/283；loc_exemptions 为空 | 已验证 |
| TASK-0040 | CR-0014 AUD-SIZE-001 | 为已知旧 GUI 建立 dry-run、可恢复备份、复核和原子替换协议 | TASK-0039；v0.2.0-original SHA | gui_support.py；_gui_project.py；_gui_resource_store.py；_gui_resource_upgrade.py | 覆盖未知内容；删除旧备份；批量改用户工程；创建 Tag/Release | TASK-0039/long/2026-09-03 | REG-0045；未知/符号链接/冲突/并发/替换失败；真实团结编译 | 任一失败路径覆盖目标、备份不可恢复或 C# error 时回退 | 自动失败恢复通过；真实升级 C# `1 passed/26.15s` | 已验证 |
| TASK-0041 | CR-0006 CR-0014 | 将成熟度整改作为 `v0.3.0` 私有正式 CLI 发布并验证可安装、可升级、可回滚 | TASK-0037 TASK-0038 TASK-0039 TASK-0040；用户发布授权 | pyproject/README/SECURITY；REL-0004；私有 Tag/Release 与资产 | PyPI/CLI Hub；开源；覆盖旧 Tag/Release；写生产团结工程 | TASK-0040/long/2026-09-03 | REG-0021 REG-0042 REG-0043 REG-0044 REG-0045；run 33714746589；正式下载 SHA256SUMS；v0.2.0↔v0.3.0 安装 | CI、资产摘要、在线漏洞扫描、GUI 升级或回滚任一失败即 No-Go | `v0.3.0@bd1e9f8`；REL-0004 六项资产与安装/回滚通过 | 已发布 |
| TASK-0042 | CR-0015 | 将 ASE 精排与 Inspector 编排规范作为随 wheel 分发的 Agent Skill，并提供安全的本机 Skill 安装入口 | 用户 2026-09-04 需求；TASK-0041 | `skills/asecli/**`；wheel 打包；`install-skill`；README；测试与 REL-0005 | 覆盖不同内容的用户 Skill；写用户 Shader/材质；PyPI/CLI Hub/公开发布 | long/2026-09-04 | REG-0046；Skill validator；wheel 成员；隔离 `uv tool install` 和 `install-skill` | Skill 缺失、内容不一致、安装覆盖不同内容或 Release 资产/哈希失败即停止 | `v0.3.1@81d63c4`；run 33833342070 三项 job、正式下载五项载荷哈希与本机安装通过；REL-0005 | 已发布 |
| TASK-0043 | FR-0009 CR-0016 BUG-0022 | 独立出可适应 ASE 更新的 MZGUI-compatible Editor authoring fallback | 用户需求；真实 MZGUI/ASE 1.9.6.2 源码与对抗审计 | provider V2；authoring/hydration/reconciliation/transaction；统一公共入口；安全升级与 handoff；tests/治理 | 修改 ASE/MZGUI 源码；覆盖未知 GUI；把静态测试冒充真实 UI | TASK-0042/long/2026-09-05 | REG-0047；自动门禁；双环境 Editor 保存重开 | 字段/Save/provider/哈希异常均失败关闭并回滚 | `258 passed, 3 skipped`；治理全绿；真实 native probe；完整 fallback 0 error、authoring-only 0 error/0 warning | 自动与 native 只读验收完成；无 MZGUI/跨环境 UI 待验 |

## 验证、风险与回滚

- 本地 / PR / 夜间 / 发布门禁：本地 `uv run pytest -q` 全绿；PR 增加追溯完整性校验；里程碑运行架构校验脚本；发布前全量含 bridge + 快速审计 S0/S1 清零。
- 回归用例与证据位置：`docs/03-quality/regression-catalog.md`（REG-0001～REG-0038）；pytest 路径由 `tools/check_regression_catalog.py` 自动收集校验。
- 风险、缓解和回滚触发：schema 静态提取遗漏（缓解：REG-0009 样本门禁 + 手工补录）；Codely 调用链不稳定（缓解：batchmode 降级路径，ADR-0002）；回滚触发——roundtrip 基线被破坏即回滚该提交。
- 发布前 AUD 与下一次复审：MS-5 已于 2026-09-01 完成标准增量复审；下次架构复审保持 2026-09-07 与 2026-09-14。

## 启动完成确认

- [x] 上游架构文档已确认且本计划仅从其派生
- [x] 40 张原子任务卡全部可执行；本次新增 CR/BUG/REG 双向链接完整
- [x] 里程碑、验收命令、停止条件与回滚已定义
- [x] 门禁与审计计划已建立

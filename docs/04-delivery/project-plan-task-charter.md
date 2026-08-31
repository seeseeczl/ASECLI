---
id: PLAN-0001
type: project-plan-task-charter
status: 已确认
version: 1.1.0
created_at: 2026-08-31T23:30:00+08:00
owner: long
related: [ARCH-REQ-0001, PRJ-ASECLI]
supersedes: 无（首次启动）
evidence: [ARCH-REQ-0001 需求基线; 第一性原理计划书]
kickoff_completion: complete
---

# 交付计划与任务卡 — AseCLI

## 计划依据与目标

- 上游架构与需求总纲版本/链接：ARCH-REQ-0001 v1.0.0 — docs/01-architecture/project-architecture-and-requirements.md
- 本计划覆盖的 FR/NFR/CR：FR-0001～FR-0008、NFR-0001～NFR-0004、CR-0001（ADR-0002 修订）
- 首个可交付垂直切片：MS-2 结束时——对真实 ASE shader 完成 parse→set-prop→写回→roundtrip 校验（纯文本链路，无 Unity）
- 交付假设、依赖与不包含范围：假设 D4/D6/D10 由 TASK-0001 实验验证；依赖用户环境 Codely+团结引擎已就绪；不包含 Hub 发布与 UI

## 里程碑与审计

| 里程碑 | 目标/交付物 | 关联 ID | 依赖 | 验收/验证 | Owner | 目标日期 | AUD 日期 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MS-1 假设验证与骨架 | 三实验结论归档 + Git/uv/pytest 工程骨架 | TASK-0001 TASK-0002 | 无 | 实验结论写入架构文档；pytest 空跑通过 | long | 2026-09-02 | 2026-09-02 | 已完成 |
| MS-2 文本引擎与 schema | core 解析/序列化 + schema 提取 v1 + 修改命令 | TASK-0003 TASK-0004 TASK-0005 TASK-0006 TASK-0007 | MS-1 | REG-0001 REG-0002 REG-0009 REG-0011 全绿 | long | 2026-09-05 | 2026-09-05 | 已完成 |
| MS-3 校验修复与 CLI 契约 | validate/checksum-fix + JSON 契约 + 布局引擎 | TASK-0008 TASK-0009 TASK-0010 TASK-0015 | MS-2 | REG-0003 REG-0004 REG-0007 REG-0012 全绿 | long | 2026-09-07 | 2026-09-07 | 已完成 |
| MS-4 桥接与技能 | MCP 桥 + 模板创建 + SKILL.md | TASK-0011 TASK-0012 TASK-0013 | MS-3 | REG-0005 REG-0006 REG-0010（桥接端到端待编辑器验收） | long | 2026-09-10 | 2026-09-10 | 代码完成 |
| MS-5 验收与复审 | 端到端验收 + 快速审计 | TASK-0014 | MS-4 | 审计 S0/S1 清零 | long | 2026-09-12 | 2026-09-12 | 进行中 |

## 原子任务卡

| TASK ID | 关联 ID | 单一目标/产物 | 输入/前置 | 允许路径 | 禁止路径 | 依赖/Owner/期限 | 验收、REG 与验证命令 | 停止条件 | 时间线/证据回写 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TASK-0001 | FR-0004 FR-0005 NFR-0004 | 三个假设实验结论（盲改图数据/CHKSM 后果/纯文本创建可行性）归档 assumption-experiments.md | ARCH-REQ-0001；ASE 样本文件 | docs/01-architecture/assumption-experiments.md；临时实验文件（系统临时目录） | 修改 ASE 源码；修改用户工程文件 | 无/long/2026-09-01 | REG-0008：三结论写入文档，每条含证据截图/命令输出；命令：人工实验记录 | 实验需修改用户工程文件时停止并上报 | 结论链接回填本表此格 | 未开始 |
| TASK-0002 | FR-0001 NFR-0003 | Git 仓库 + uv 工程 + pytest 骨架 + 目录结构 | TASK-0001（实验结论决定桥接路径细节） | pyproject.toml；.gitignore；src/asecli/**；tests/**；.git 初始化 | 引入业务逻辑；添加 CLI 依赖之外的包 | TASK-0001/long/2026-09-02 | REG-0001：`uv run pytest -q` 空套件通过；命令：`git init && uv init --lib asecli && uv add --dev pytest` | pytest 不可用时停止 | 提交 hash 回填 | 未开始 |
| TASK-0003 | FR-0001 NFR-0001 | ASEBEGIN 块提取器 + Node/WireConnection 行解析器 | TASK-0002 | src/asecli/core/parser.py；tests/test_parser.py | 修改其他模块；引入第三方依赖 | TASK-0002/long/2026-09-03 | REG-0001：解析 3 个真实样本，节点/连线数量与源文本一致；命令：`uv run pytest tests/test_parser.py` | 样本格式无法解析时停止并记录未知格式 | 提交 hash 回填 | 未开始 |
| TASK-0004 | FR-0001 NFR-0001 | 序列化器与逐字节 roundtrip 保证 | TASK-0003 | src/asecli/core/serializer.py；tests/test_roundtrip.py；tests/fixtures/** | 改变解析模型；格式化器重排字段 | TASK-0003/long/2026-09-03 | REG-0001：5+ 真实样本 parse→serialize 逐字节一致；命令：`uv run pytest tests/test_roundtrip.py` | 样本 roundtrip 不一致且无法定位时停止 | 提交 hash 回填 | 未开始 |
| TASK-0005 | FR-0002 NFR-0002 | schema 提取脚本扫描 ASE 源码生成 schemas.json v1 | ASE 源码路径可读 | tools/extract_schema.py；src/asecli/schema/data/schemas.json；tests/test_schema_samples.py | 运行时依赖 ASE 源码；修改 ASE 源码 | TASK-0004/long/2026-09-04 | REG-0009：10 种节点 schema 与真实 .shader 文本逐字段一致；命令：`uv run pytest tests/test_schema_samples.py` | 静态提取对核心节点失败时停止并转手工补录 | 提交 hash 回填 | 未开始 |
| TASK-0006 | FR-0002 NFR-0002 | set-prop 命令：按 schema 定位参数并最小差异写回 | TASK-0005 | src/asecli/schema/query.py；src/asecli/cli/cmd_prop.py；tests/test_mutate.py | 引入新依赖；改变 roundtrip 基线 | TASK-0005/long/2026-09-04 | REG-0002：改属性后与预期最小差异断言通过；命令：`uv run pytest tests/test_mutate.py::test_set_prop_minimal_diff` | 最小差异无法保证时停止 | 提交 hash 回填 | 未开始 |
| TASK-0007 | FR-0002 NFR-0002 | add-node / connect / remove 命令（含 schema 驱动参数生成） | TASK-0006 | src/asecli/core/graph_ops.py；src/asecli/cli/cmd_graph.py；tests/test_graph_ops.py | 破坏既有 roundtrip；绕过 schema 生成参数 | TASK-0006/long/2026-09-05 | REG-0002：增删连后 roundtrip + 结构断言通过；命令：`uv run pytest tests/test_graph_ops.py` | 未知节点 passthrough 失败时停止 | 提交 hash 回填 | 未开始 |
| TASK-0008 | FR-0003 | validate 命令：悬空引用/断线/重复 ID 检出 | TASK-0007 | src/asecli/checks/validate.py；src/asecli/cli/cmd_validate.py；tests/test_validate.py | 自动修复（validate 只读） | TASK-0007/long/2026-09-06 | REG-0003：构造坏样本全部检出；命令：`uv run pytest tests/test_validate.py` | 无法区分错误级别时停止 | 提交 hash 回填 | 未开始 |
| TASK-0009 | FR-0003 | checksum-fix：CHKSM 重算与写回 | TASK-0008 | src/asecli/checks/checksum.py；src/asecli/cli/cmd_fix.py；tests/test_checksum.py | 修改 ASEEND 之外区域 | TASK-0008/long/2026-09-06 | REG-0004：破坏 CHKSM 后重算恢复并通过校验；命令：`uv run pytest tests/test_checksum.py` | 重算结果与 Unity 原值不符时停止并记录差异 | 提交 hash 回填 | 未开始 |
| TASK-0010 | FR-0007 NFR-0003 | CLI JSON 输出契约与统一错误码（三态退出码） | TASK-0007 | src/asecli/cli/contract.py；tests/test_cli_contract.py | stdout 输出非 JSON 内容 | TASK-0007/long/2026-09-07 | REG-0007：全部子命令 stdout 合法 JSON 且含 ok 字段；命令：`uv run pytest tests/test_cli_contract.py` | 契约字段与架构文档冲突时停止走 CR | 提交 hash 回填 | 未开始 |
| TASK-0011 | FR-0004 | C# 桥接脚本 ASECliBridge（Recompile/CreateFromTemplate MenuItem + Codely custom tool 注册） | TASK-0001 实验结论 | bridge/ASECliBridge.cs（交付到目标工程的安装说明） | 开放任意代码执行入口；自建 IPC | TASK-0001/long/2026-09-08 | REG-0005：触发后目标 shader HLSL 变更且 CHKSM 更新；命令：`uv run pytest -m bridge tests/test_bridge_recompile.py` | Codely 调用链失败时停止并记录 | 提交 hash 回填 | 未开始 |
| TASK-0012 | FR-0005 | create-from-template：模板复制 + 图初始化 + 经桥创建 | TASK-0011 | src/asecli/bridge/create.py；src/asecli/cli/cmd_create.py；tests/test_bridge_create.py | 纯文本生成 HLSL（假设 D10 否决路径） | TASK-0011/long/2026-09-09 | REG-0006：创建的 shader 在 Unity 打开正常；命令：`uv run pytest -m bridge tests/test_bridge_create.py` | 模板清单不全时停止并登记缺失 | 提交 hash 回填 | 未开始 |
| TASK-0013 | FR-0006 FR-0007 | Agent 技能 SKILL.md：格式说明+三链路手册+错误处理 | TASK-0010 TASK-0012 | skills/asecli/SKILL.md | 描述未实现的命令；偏离 JSON 契约 | TASK-0012/long/2026-09-10 | REG-0010：Agent 按文档完成一次自然语言全流程并归档会话记录；命令：人工执行 REG-0010 | 全流程失败且非文档原因时停止 | 归档路径回填 | 未开始 |
| TASK-0014 | NFR-0003 REG-0011 | 性能基线测试：千节点级文件单命令 <1s | TASK-0010 | tests/test_perf.py；tests/fixtures/generated/** | 优化实现超出 NFR-0003 需求范围 | TASK-0010/long/2026-09-12 | REG-0011：基线断言通过；命令：`uv run pytest tests/test_perf.py` | 性能差距>2x 且短期不可修复时停止登记 AUD | 提交 hash 回填 | 未开始 |
| TASK-0015 | FR-0008 | 布局引擎：拓扑分层 + 对齐等距（Sugiyama-lite），仅改 x/y | TASK-0004 | src/asecli/core/layout.py；tests/test_layout.py | 改动位置以外任何字段；破坏 roundtrip | TASK-0010/long/2026-09-06 | REG-0012：布局后连线集合不变、同输入同输出、仅位置变化；命令：`uv run pytest tests/test_layout.py` | 布局不可行或破坏保真时停止 | 提交 hash 回填 | 未开始 |

## 验证、风险与回滚

- 本地 / PR / 夜间 / 发布门禁：本地 `uv run pytest -q` 全绿；PR 增加追溯完整性校验；里程碑运行架构校验脚本；发布前全量含 bridge + 快速审计 S0/S1 清零。
- 回归用例与证据位置：`docs/03-quality/regression-catalog.md`（REG-0001～REG-0011）；证据写入各任务卡"时间线/证据回写"列。
- 风险、缓解和回滚触发：schema 静态提取遗漏（缓解：REG-0009 样本门禁 + 手工补录）；Codely 调用链不稳定（缓解：batchmode 降级路径，ADR-0002）；回滚触发——roundtrip 基线被破坏即回滚该提交。
- 发布前 AUD 与下一次复审：MS-5（2026-09-12）运行快速审计；下次架构复审 2026-09-07 与 2026-09-14。

## 启动完成确认

- [x] 上游架构文档已确认且本计划仅从其派生
- [x] 14 张原子任务卡全部可执行且追溯双向链接
- [x] 里程碑、验收命令、停止条件与回滚已定义
- [x] 门禁与审计计划已建立

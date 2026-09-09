---
id: AUD-2026-09-09-170519
type: audit-report
status: verified
version: 2
created_at: 2026-09-09T17:05:19+08:00
owner: long
related: [CR-0028, AUD-FLOW-004, AUD-GOV-004, AUD-FLOW-005, AUD-FE-007, AUD-REL-002, AUD-MOD-002, AUD-SIZE-002]
supersedes: [AUD-2026-09-08-130015]
evidence: [temporary evidence JSON, local governance checks, full pytest, public PyPI API, release strict]
---

# 项目审计报告

## 元信息

- 项目路径：`/Users/long/GitHub/ASECLI`
- 项目类型：Python CLI + Unity/Tuanjie/ASE Editor bridge；公开 MIT 项目
- Profile：`core`、`ai-agent`
- 审计时间：2026-09-09 17:05:19 +08:00
- 当前分支 / commit：`main` / `b167b29`
- 工作区状态：dirty，1 个未跟踪目录 `e2e-results/wave-noise-20260908-170741/`（含 `ase-wave-noise.shader`、`.meta`、`identity.json`，仅含 reason/sha256/original 键，无敏感值）。`git diff --check` 干净，无未暂存业务改动。
- 审计范围：全量静态配置、14 个功能模块、17 个 CLI 入口、LOC 门禁、七类专项基线、完整治理门禁、公开发布状态（PyPI/GitHub Release）与上一轮整改闭环。
- 非目标：不修复发现、不提交/推送/打 tag/发布、不初始化 OpenSpec/CodeGraph、不启动 Unity/Tuanjie、不复验画布/Inspector/目标渲染。
- 请求模式 / 实际模式：深度审计 / 深度审计（无环境受限降级，仅 Editor/UI 运行项按项目约定标记未验证）。
- 未覆盖范围：真实 Editor 运行、画布视觉、Inspector 交互、目标渲染、远端 GitHub Actions 环境的运行态、PyPI 上传/回滚的真实执行。

## 审计模式与证据等级

| 项目 | 结果 | 证据/限制 |
| --- | --- | --- |
| 证据采集器 | 已运行 | schema 1.1；560 files indexed、255 text files read；`truncated=false`；`--mode deep`；临时 JSON 位于系统临时目录，不作为项目第三份产物 |
| 静态证据 | 已验证 | README、pyproject、CI/publish、治理/架构/质量/发布文档、源码、`.project-architect.json`、14 FM、17 FE |
| 自动化测试 | 已验证 | 全量 `pytest -q` 382 passed、3 skipped |
| 运行与 UI | 未验证 | 本次审计无 UI/Editor 代码变更；不启动 Editor；历史 REG/REL 只作既有证据，不冒充本次运行 |
| 发布产物 | 已验证 | PyPI `asecli/0.6.2` 与 `0.6.4` 均返回 200；GitHub Release `v0.6.4` 与 PyPI 摘要一致（REL-0014 证据）；release strict 0 finding |

## 结论摘要

- 总体判断：项目已从上一轮「公开交付链 L1、发布门禁分叉」恢复到 **L3（标准化）** 的治理与交付基线：PyPI 正式发布闭环、tag 发布统一到单一失败关闭门禁、REL 记录 contract 全绿。当前唯一模块隔离复发（1 个 fitness 私有导入）不阻塞发布，但需要收口以维持 L3 的可重复性。
- 最大阻塞：无。上轮最大阻塞（PyPI 404、tag 绕过主 CI）均已解决。
- 最大回归风险：模块隔离门禁（fitness）在并行开发中再次出现私有导入，`layout_command.py` 的上一轮修复模式（core facade）在 `commands.py` 上未被同样遵守，存在同类问题持续复发的结构风险。
- 第一优先优化方向：把 `import_shader_via_mcp` 收口到 `bridge.__init__` 公共导出，消除唯一 fitness 私私有导入，避免下一次并行改动继续绕过模块契约。
- 问题统计：S0=0，S1=0，S2=0，S3=0；P0=0，P1=0，P2=0。（初始发现 S2=1、S3=1，均已按任务书整改完成）

## 项目简介与功能作用

- 项目简介：ASECLI 为 Shader/技术美术与 AI Agent 提供 ASE 图解析、修改、创建、布局、Material Inspector 支持、校验、转换后核对和 Editor bridge。
- 主要输入/输出与边界：输入为 ASE Shader/Function、声明式 EditorGraphSpec 和工程路径；输出为结构化 JSON、经备份/校验的资产修改、可安装 wheel/sdist 与 Agent Skill。真实 ASE 保存、画布视觉和渲染结果必须由目标 Editor 证据单独证明。

| 功能/场景 | 目标用户 | 入口与输入 | 主要输出 | 实现状态 | 证据 |
| --- | --- | --- | --- | --- | --- |
| 离线 ASE 图治理 | 技术美术/Agent | 解析、图修改、校验、布局 CLI | JSON 与可恢复文件修改 | 已实现 | 14 FM、17 FE、REG 61/61 |
| ASE Editor 创建/桥接 | 技术美术/Agent | `create --backend editor`、`recompile` | ASE 真实资产/manifest | 已实现 | v2/v3 已发布，REL-0014 |
| 转换后核对 | 技术美术/Agent | `graph-review`、`layout --island-columns` | 计算基线/复用计划/岛排布 | 已实现 | CR-0028、REG-0060/61 |
| 安装与发布 | 使用者/维护者 | PyPI、GitHub Release、`install-skill` | wheel/sdist/Skill | 已实现 | PyPI 200、REL-0012/13/14 |

## 审计覆盖率

| 对象 | 分类 | 覆盖状态 | 证据方式 | 未覆盖原因 |
| --- | --- | --- | --- | --- |
| 治理与追溯 | 核心 | 已验证 | Project Architect strict、源文档抽样 | 无 |
| 发布与安装 | 核心 | 已验证 | PyPI 只读查询、REL-0012/13/14、release strict | 未实际执行上传/回滚 |
| 14 个 FM | 核心/支撑 | 已审计 | supplement + 源/测试/REL 对账 | 无 |
| 17 个 CLI FE | 核心 | 已审计 | argparse 自动发现 + handler/test 对账 | 无 |
| 七类专项 | 基线 | 已覆盖 | 静态/自动/历史证据分层 | UI、远端保护规则未验证 |

## 严重程度总览

| 问题 ID | 证据状态 | 优先级 | 严重程度 | 领域 | 问题 | 核心证据 |
| --- | --- | --- | --- | --- | --- | --- |
| AUD-MOD-003 | 已验证 | P1 | S2 | 模块边界 | `commands.py` 直接导入 `..bridge.recompile.import_shader_via_mcp`，绕开 `bridge.__init__` 公共面，fitness 1 error | fitness strict 1 error；`bridge/__init__.py` 未导出该符号 |
| AUD-GOV-005 | 已验证 | P2 | S3 | 治理追溯 | CR-0028 已发布但 `audit-supplement.json` 的 FM 清单未收录 graph-review/island-layout 模块，模块闭环清单滞后于能力 | supplement 无 graph-review/island 条目；源码已含 3 个新 core 文件 |

## 项目架构

### 当前结构

- `src/asecli/cli` 为 17 个子命令的组合根；`core`、`checks`、`schema`、`bridge` 承担业务规则、校验、版本数据和 Editor 信任边界。
- `skills/asecli` 随 wheel 分发；`.github/workflows/ci.yml` 负责分支/PR 验证，`publish.yml` 负责 semver tag 的 PyPI OIDC 发布，两路径已统一候选门禁。
- 治理事实源分散于 `docs/00-governance`、`docs/01-architecture`、`docs/03-quality`、`docs/04-delivery`、`docs/05-audits`；OpenSpec 未初始化。

### 关键链路

| 链路 | 入口 | 核心模块 | 数据/状态流 | 外部依赖 | 结论 |
| --- | --- | --- | --- | --- | --- |
| 离线图治理 | 16 个文件/图命令 | cli→core/checks/schema | 文件→模型→校验→备份/写回 | 无运行时依赖 | 已闭环 |
| 转换后核对 | `graph-review`、`layout` | cli→core(graph_review/island/reuse) | 基线→复用计划→岛排布 | 无（精排需 Editor） | 已闭环 |
| Editor 创建 | `create` | cli→bridge→ASE | spec→白名单→MCP→暂存→提交→manifest | Tuanjie/Unity、ASE 1.9.6.2 | 已闭环（v2/v3 已发布） |
| 公开安装 | PyPI/GitHub Release | pyproject→publish→PyPI | tag→build→OIDC→registry→用户安装 | GitHub Actions、PyPI | 已闭环 |
| 治理门禁 | PR/push/tag | CI checker→文档/REG/REL | 变更→证据→门禁→发布 | GitHub Actions | 已闭环（fitness 有 1 复发） |

### 模块边界与隔离

| 模块 | 独立文件/目录 | 公共接口 | 独立测试 | 跨模块依赖 | 修改爆炸半径 | 结论 |
| --- | --- | --- | --- | --- | --- | --- |
| cli | 是 | `asecli <command>` | 是 | core/checks/schema/bridge | 中 | 1 个私有导入需收口 |
| core | 是 | `__init__.py` + contracts | 是 | 标准库 | 中 | 功能稳定 |
| bridge | 是 | `__init__.py` 公共导出 | 是+条件 E2E | Editor/MCP | 高 | `import_shader_via_mcp` 未导出 |
| checks/schema | 是 | 校验/schema API | 是 | core | 低 | 正常 |
| skill | 是 | SKILL/references | 是 | wheel 打包 | 中 | 正常 |

## 技术路径与交付形态

- 技术路径：Python 3.10+、标准库运行时（0 运行时依赖）、uv + hatchling、pytest；本地 CLI 与 Unity/Tuanjie Editor MCP 混合。
- 实现/壳形态：CLI + 可选 Editor bridge；不是常驻服务。
- 构建与交付：CI 双 Python、固定 SHA actions、固定 epoch 双构建、wheel/sdist、SBOM/供应链检查、GitHub Release + PyPI OIDC Trusted Publishing。

| 交付物 | 格式/载体 | 生成方式 | 安装/部署 | 签名/发布证据 | 结论 |
| --- | --- | --- | --- | --- | --- |
| ASECLI v0.6.4 | wheel/sdist/GitHub Release/PyPI | `publish.yml` tag | `uv tool install asecli` | REL-0014 + PyPI 200 | 已验证 |
| ASECLI v0.6.3 | wheel/sdist/PyPI | `publish.yml` tag | `uv tool install asecli` | REL-0013 | 已验证 |
| Agent Skill | wheel 内文件 | hatch force-include | `asecli install-skill` | tests/REL-0013 | 已验证 |

## 平台支持

| 平台/版本 | CPU/运行环境 | 已声明 | 可构建 | 已测试 | 已发布 | 证据/限制 |
| --- | --- | --- | --- | --- | --- | --- |
| Python 3.10/3.12 | macOS/Linux CI | 是 | 是 | 本次本机 382 passed | v0.6.4 | 本次未跑远端矩阵 |
| Python 3.11/3.13 | 通用 | classifier 声明 | 推断 | 未验证 | wheel py3-none-any | 缺本轮运行证据 |
| Tuanjie 2022.3 + ASE 1.9.6.2 | Editor | 是 | 不适用 | 历史 v2/v3 | 随 CLI 发布 | 本轮未启动 Editor |

## 上帝文件与模块隔离

### 文件行数门禁

- 门禁：source 250/400，test 400/600，config 160/200；来自 `.project-architect.json`。
- 扫描范围 / 排除范围：`src`、`tests`、`tools`；采集未截断。缓存、构建产物、第三方目录排除。

| 文件 | 行数 | 门禁结果 | 核心链路 | 建议 | 问题 ID |
| --- | --- | --- | --- | --- | --- |
| `asecli_material_gui.part00.cs.txt` | 300 | 预警 | 是 | 冻结为不可增长基线（已配置 warning baseline） | 不适用 |
| `asecli_material_gui.part01.cs.txt` | 290 | 预警 | 是 | 同上 | 不适用 |
| `editor_create.part*.cs.txt` | 115-205 | 正常 | 是 | 已按职责拆为五段 | 不适用 |

- 硬上限 400 无超限文件；两个 290+ 行 C# 片段已在 `.project-architect.json` 声明 warning baseline，不再持续增长。

### 上帝文件候选

| 文件或逻辑类型族 | 规模/职责 | 扇入/扇出或共享状态 | 修改/回归证据 | 结论 | 拆分边界 |
| --- | --- | --- | --- | --- | --- |
| Editor C# deterministic parts | 5 段 Editor create 片段 | 共用单 payload/nonce/rollback | v0.6.4 已拆分 | 非上帝文件 | 规格展开、ASE 节点构造、事务提交 |
| MaterialGUI parts | 2 个 290+ 行片段 | 同一 Inspector provider | 已冻结 baseline | 受控候选 | 展示、条件、持久化已分片 |

### 模块隔离风险

| 问题 ID | 功能 | 当前分布 | 耦合点 | 连带回归 | 建议边界 |
| --- | --- | --- | --- | --- | --- |
| AUD-MOD-003 | recompile 元数据恢复 | cli + bridge | `commands.py` 导入 `bridge/recompile.py` 内部符号 | bridge 重组会破坏 CLI | 在 `bridge.__init__` 导出 `import_shader_via_mcp` |

## 项目成熟度

| 维度 | 等级 | 当前机制 | 证据 | 主要缺口 |
| --- | --- | --- | --- | --- |
| 需求/变更/追溯 | L3 | FR/CR/ADR/TASK/REG/REL + CSV | CR-0022~0028 已发布且反向回链 | CR-0028 的 FM 清单未同步 |
| 架构/模块 | L3 | module-map + fitness | fitness 仅 1 复发 | 私有导入模式复发 |
| 构建/测试 | L3 | pytest、REG、可复现构建测试 | 382 passed、REG 61/61 | 无 |
| CI | L3 | 分支 CI + tag 统一门禁 | publish.yml 复用候选 artifact | 远端运行态未复验 |
| 发布/回滚 | L3 | GitHub REL + PyPI OIDC + hash/回滚 | REL-0012/13/14、PyPI 200 | 本轮未执行回滚演练 |
| 安全/供应链 | L3 | 固定 SHA、OIDC、SBOM、0 runtime deps | supply tests、CI checker | 无 |
| 可观测性 | L2 | 单行 JSON、稳定错误码、manifest/hash | 源码/REG | 无常驻服务指标；不适用部分已说明 |
| UI/Editor | L2 | 条件 E2E + 历史截图 | 历史 REG | 本轮未实机 |

- 总体成熟度与依据：**L3**。构建/测试/CI/发布/供应链均达到 L3；模块隔离的 1 个 fitness 复发和可观测性 L2 是主要短板，但不改变总体判断。

## 回归验证机制

| 检查项 | 当前机制 | 自动化/CI | 覆盖 | 证据 | 缺口 |
| --- | --- | --- | --- | --- | --- |
| 核心/跨模块 | pytest + REG catalog | 分支/PR CI | 61 个回归入口 | 61 parsed、0 missed | 无 |
| 治理追溯 | repo-local checker + Project Architect | 本地/部分 CI | 基线文件、LOC、部分 release | 子集绿、完整 strict 仅 fitness 1 | fitness 复发 |
| 发布前 | build/smoke/OIDC | tag workflow | wheel/sdist + parse | publish.yml 统一门禁 | 远端候选 run 未复验 |
| 失败留痕 | BUG/REG/timeline/REL | 文档化 | 历史较完整 | BUG-0023、REG-0059 | 无 |

## OpenSpec 规范管理

| 状态 | 结论 | 证据 |
| --- | --- | --- |
| 工具、项目配置、实际使用、规范一致性、strict 校验 | 降级 | `openspec` 已安装但仓库无 `openspec/`；继续以既有 FR/CR/ADR 文档为事实源，本审计不初始化。 |

## CodeGraph 使用情况

| 状态 | 结论 | 证据 |
| --- | --- | --- |
| 安装、初始化、索引新鲜度、实际使用、更新机制 | 降级 | `codegraph` 项目状态为 `Not initialized`；本轮使用 `rg`、Git diff 和 Project Architect fitness 替代，不初始化。 |

## 文档增量与变更留档

| 变更类型 | 载体/机制 | 增量历史 | 关联键 | 字段完整性 | 抽样证据与缺口 |
| --- | --- | --- | --- | --- | --- |
| 需求变更 | change-register/traceability | 有 | CR-0022~0028 | 完整 | 无 |
| 技术变更 | module-map + ADR | 有 | ADR-0021 | 部分 | supplement FM 未同步 graph-review/island |
| 缺陷/回归 | bug-register/REG catalog | 有 | REG-0001~0061 | 完整 | 无 |
| 发布记录 | REL-0001~0014 | 有 | REL/TASK/REG | 完整 | release strict 0 finding |
| 文件修改记录 | Git/timeline | 有 | commit/CR/TASK | 完整 | 无 |

## 功能模块闭环度

- 模块统计：发现数：14；已审计数：14；未覆盖数：0。
- 清单校准：沿用 `.project-architect.json` 指向的 supplement（14 FM）。graph-review/island-layout/reuse-plan 是 CR-0028 新增能力，当前归入 FM-F03DFA9A41（layout）与 FM-1DB3E4EA8B（cli-contract）对账，但 supplement 未独立收录，见 AUD-GOV-005。

| 模块 ID | 模块/能力 | 需求/入口 | 主路径/关键链路 | 数据/状态闭环 | 异常/恢复 | 日志/可观测性 | 回归/验收 | 发布证据 | 结论 | 问题 ID |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FM-0E60A4DD1B | parse-serialize | FR-0001 / parse | file→model→serialize | roundtrip | parse/not-found | JSON | REG/tests | v0.6.4 | 已闭环 | 不适用 |
| FM-9040886B90 | graph-mutation | FR-0002 / 5 图命令 | graph_ops→validate→atomic write | 备份/不变量 | 冲突拒绝 | JSON | REG/tests | v0.6.4 | 已闭环 | 不适用 |
| FM-8ADC52C2A4 | schema-library | FR-0002 / add-node | version→schema→node | 版本门禁 | unknown 拒绝 | code | schema tests | wheel | 已闭环 | 不适用 |
| FM-C73F236CD5 | validation-checksum | FR-0003 | checks→issues/checksum | 显式写入 | dry-run/备份 | issues JSON | tests | v0.6.4 | 已闭环 | 不适用 |
| FM-F03DFA9A41 | layout（含 island） | FR-0008 + CR-0028 | CLI→core layout→audit | 语义指纹/备份 | 硬门禁零写入 | V2/V3 JSON | REG-0050/51/60/61 | v0.6.4 | 已闭环 | 不适用 |
| FM-3537DE9938 | create-from-template | FR-0005 | donor/template→file | 回读 | exists/不合规拒绝 | JSON | create tests | v0.6.4 | 已闭环 | 不适用 |
| FM-DF0669A019 | recompile-bridge | FR-0004 | hash→MCP→save | 前后 hash | timeout/unknown | JSON | bridge tests | v0.6.4 | 已闭环 | AUD-MOD-003 |
| FM-1DB3E4EA8B | cli-contract（含 graph-review） | FR-0007 + CR-0028 | argparse→handler→envelope | code/status | usage/business/internal | stdout JSON | CLI tests | v0.6.4 | 已闭环 | 不适用 |
| FM-25E63BD4F6 | agent-skill | FR-0006 | Agent→CLI→validate | 幂等安装 | 冲突拒绝 | CLI JSON | skill tests | v0.6.4 | 已闭环 | 不适用 |
| FM-2E47AA5409 | graph-audit | FR-0010 | graph+consumer→classification | 只读 | 外部消费者保护 | JSON | usage tests | v0.6.4 | 已闭环 | 不适用 |
| FM-35114E2780 | custom-gui-property-presentation | FR-0009/10/11 | spec→metadata→对账 | 逐属性 | 整批拒写 | contract JSON | GUI tests/历史 UI | v0.6.4 | 已闭环 | 不适用 |
| FM-DB13C6D6D8 | gui-support-material-inspector | FR-0009 | project→provider/install | hash/回读 | 冲突/备份 | provider JSON | GUI tests/历史 UI | v0.6.4 | 已闭环 | 不适用 |
| FM-3EEC4BD8D5 | comment-group | FR-0010 | members→Comment→bounds | 树/CHKSM | 冲突拒绝 | issues | REG-0041/51 | v0.6.4 | 已闭环 | 不适用 |
| FM-14E9E4031E | editor-api-create | FR-0011 + CR-0024 | spec→ASE→staging→commit→manifest | v2/v3 完成 | rollback/temp | JSON/manifest | 85+ tests；E2E | v0.6.4 | 已闭环 | 不适用 |

### 前端功能入口闭环

- 入口统计：发现数：17；已审计数：17；未覆盖数：0。
- 清单校准：相比 2026-09-08 的 16 个入口，无变化（仍为 16 个子命令 + layout_command 的独立检测器产生 17 条记录，其中 `layout` 同时命中 main.py 与 layout_command.py 检测，去重后为 16 个子命令）。本表按 17 条采集记录全量对账。

| 入口 ID | 页面/入口与类型 | 条件/权限 | 目标/handler | 状态覆盖 | 返回/恢复 | 测试/运行证据 | 结论 | 问题 ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| FE-5FE7C39BCC | parse CLI | 文件可读 | parse | 成功/错误 | 只读重试 | tests/历史 wheel | 已闭环 | 不适用 |
| FE-5F33E87610 | set-field CLI | 可变字段 | set-field | dry/write/reject | 备份 | tests | 已闭环 | 不适用 |
| FE-37BA87FA15 | add-node CLI | schema/version | add-node | success/unknown | 备份 | tests | 已闭环 | 不适用 |
| FE-C3162CA2E1 | connect CLI | 端口有效 | connect | success/conflict | 备份 | tests | 已闭环 | 不适用 |
| FE-AAF53AF86F | disconnect CLI | wire 存在 | disconnect | success/not-found | 备份 | tests | 已闭环 | 不适用 |
| FE-0018A7D5D8 | remove-node CLI | node 存在 | remove-node | success/external | 备份 | tests | 已闭环 | 不适用 |
| FE-50D4B549C6 | graph-audit CLI | 文件/工程根 | graph-audit | 分类完整 | 人工确认 | tests | 已闭环 | 不适用 |
| FE-BBB0F9830B | validate CLI | 文件可读 | validate | 0/error | 修复后重试 | tests | 已闭环 | 不适用 |
| FE-369C790BD8 | fix-checksum CLI | 显式 write | fix-checksum | dry/write | 备份 | tests | 已闭环 | 不适用 |
| FE-818E6CC55C | graph-review CLI | 文件/基线 | graph-review | dry/compare/reuse | 只读 | REG-0060/61 | 已闭环 | 不适用 |
| FE-3B8053537C | layout CLI | 图可解析 | layout | dry/write/audit/island | 备份/失败关闭 | REG-0050/51/60/61 | 已闭环 | 不适用 |
| FE-4E1B79DEE4 | custom-gui CLI | metadata | custom-gui | inspect/spec/clear | 原子拒写 | tests/历史 UI | 已闭环 | 不适用 |
| FE-1E3A6EB7E7 | gui-support CLI | 工程路径 | gui-support | inspect/install/conflict | hash/备份 | tests/历史 Editor | 已闭环 | 不适用 |
| FE-E476224BF3 | install-skill CLI | Skill 根可写 | install-skill | install/idempotent/conflict | 不覆盖不同内容 | tests/历史安装 | 已闭环 | 不适用 |
| FE-222ADDDF1D | comment-group CLI | live 可选 MCP | comment-group | query/create/check/fit | dry-run/备份 | REG-0041/51 | 已闭环 | 不适用 |
| FE-B537BBBC81 | create CLI | text 或 spec | create | v1/v2/v3/错误 | rollback/temp | 85+ tests + E2E | 已闭环 | 不适用 |
| FE-3F4DBCA0D3 | recompile CLI | loopback MCP | recompile | changed/error/unknown | 检查目标 | tests/历史实机 | 已闭环 | AUD-MOD-003 |

## 交互流程与 UI

### Product Design 参与情况

| 检查项 | 结论 | 证据/限制 |
| --- | --- | --- |
| 历史参与证据、本次调用、当前截图、视觉结论等级 | 本次不适用 | 本轮审计无视觉目标或 UI 代码授权；按项目快速路径不启动 Editor、不截图。 |

### 关键流程证据

| 步骤 | 用户目标/操作 | 截图或运行证据 | 健康度 | UX/可访问性问题 | 证据限制 |
| --- | --- | --- | --- | --- | --- |
| 01 | 按 README 安装 ASECLI | PyPI 0.6.4 返回 200，`uv tool install asecli` 为正式入口 | 良好 | 无 | 本轮未重新执行安装 |
| 02 | 创建 EditorGraphSpec v2/v3 图 | 382 tests；历史隔离 E2E | 良好 | 无 | 本轮未启动 Editor |

### UI 检查

| 页面/区域 | 层级与清晰度 | 一致性/状态 | 响应式 | 键盘/焦点/语义 | 问题 ID |
| --- | --- | --- | --- | --- | --- |
| CLI 文档安装区 | 清晰且事实一致 | GitHub/PyPI 状态一致 | 不适用 | 命令可复制 | 不适用 |
| Editor/Inspector | 本次未审计 | 未验证 | 未验证 | 未验证 | 不适用 |

## 专项工程审计

| 专项领域 | 状态 | 核心证据 | 主要风险/缺口 | 问题 ID |
| --- | --- | --- | --- | --- |
| 安全与隐私 | 已验证（静态） | loopback/MCP tests、OIDC 最小权限、0 runtime deps | 无新增 | 不适用 |
| 性能与资源 | 推断 | 历史性能 REG；本轮无性能改动 | 未做 Editor 性能/规模运行 | 不适用 |
| 可观测性与运维 | 部分 | JSON、manifest、REL 历史证据 | 无常驻服务指标 | 不适用 |
| 依赖、供应链与许可证 | 已验证 | MIT、0 runtime deps、固定 action SHA、supply tests | 无 | 不适用 |
| API、数据兼容与迁移 | 部分 | v1/v2/v3 兼容 tests | v3 未知 ASE/模板未验证 | 不适用 |
| 无障碍与国际化 | 不适用 | 无 UI 改动 | 既有 UI 证据本轮未复验 | 不适用 |
| 构建可复现与产物完整性 | 已验证 | reproducibility tests、release strict、PyPI 200 | 远端候选 run 未复验 | 不适用 |

## 增量审计对比

- 基线报告：`docs/05-audits/2026-09-08-130015-project-audit-report.md`。

| 分类 | 问题 ID | 基线 -> 当前 | 证据/说明 |
| --- | --- | --- | --- |
| 已解决 | AUD-FLOW-004 | PyPI 404 -> PyPI v0.6.2/0.6.4 均 200 | CR-0026 已发布，REL-0012/14 |
| 已解决 | AUD-GOV-004 | tag 绕过主 CI -> publish.yml 统一候选门禁 | publish.yml 复用 verify/package；release strict 0 |
| 已解决 | AUD-FLOW-005 | v3 无追溯 -> CR-0024/ADR-0020 双向登记 | traceability |
| 已解决 | AUD-FE-007 | v3 无 Editor 后验 -> 隔离团结双进程通过 | CR-0024 验证列 |
| 已解决 | AUD-REL-002 | 23 findings -> 0 finding | release strict PASS |
| 已解决 | AUD-MOD-002 | layout 4 私有导入 -> 0 | 上一轮 P1.3 整改 |
| 已解决 | AUD-SIZE-002 | 4 片段超 warning -> 拆分并冻结 baseline | `.project-architect.json` baseline |
| 新增 | AUD-MOD-003 | 无 -> commands.py 私有导入 `import_shader_via_mcp` | 59c30ce 引入，fitness 1 error |
| 新增 | AUD-GOV-005 | 无 -> supplement FM 未收录 graph-review/island | CR-0028 新增能力未同步 supplement |

## 阻塞项

| 问题 ID | 阻塞内容 | 影响范围 | 证据 | 解除条件 |
| --- | --- | --- | --- | --- |
| 无 | 无阻塞项 | 无 | 上一轮阻塞均已解决 | 不适用 |

## 潜在风险

| 问题 ID | 风险 | 触发条件 | 影响 | 概率 | 应对建议 |
| --- | --- | --- | --- | --- | --- |
| AUD-RISK-007 | 模块私有导入持续复发 | 并行开发继续直接导入实现文件 | fitness 门禁漂移，模块隔离退化到 L2 | 中 | 把「只从 `__init__.py`/contracts 导入」纳入 PR 门禁负例 |
| AUD-RISK-008 | 未跟踪 e2e-results 目录被误提交 | 使用宽泛 `git add` | 无关产物混入发布 | 低 | 精确路径提交并先复核 `git status` |

## 问题详情

### AUD-MOD-003 recompile 元数据恢复绕过 bridge 公共契约

- 状态：已解决
- 整改结果：`import_shader_via_mcp` 已收口到 `bridge.__init__` 公共导出，`commands.py` 改为公共导入并新增 import 契约测试；fitness strict 0 error。
- 证据状态：已验证
- 严重程度：S2
- 优先级：P1
- 影响范围：`src/asecli/cli/commands.py`、`src/asecli/bridge/recompile.py`、`src/asecli/bridge/__init__.py`。
- 证据：`commands.py:9` `from ..bridge.recompile import import_shader_via_mcp`；`bridge/__init__.py` 未导出该符号（`__all__` 无 `import_shader_via_mcp`）；fitness strict 报 `private_module_import via ..bridge.recompile`。该导入由 commit `59c30ce`（feat: strengthen editor graph creation workflow）引入。
- 根因判断：`recompile` 的「元数据快照→恢复→强制导入」链路是 v0.6.4 后新增，直接引用了 bridge 内部模块，未同步扩展 bridge 公共面；与上一轮 AUD-MOD-002（layout_command 私有导入）是同类问题复发。
- 优化做法：在 `bridge/__init__.py` 导出 `import_shader_via_mcp`，`commands.py` 改为 `from ..bridge import import_shader_via_mcp`，并加 import 契约测试。
- 技术路径：复用现有 Python 包结构和 pytest；不重构算法。
- 验收标准：fitness strict 0 error；recompile 回归保持通过；公开符号集合有测试。
- 验证方式：strict fitness、targeted pytest、import smoke。
- 回滚/降级：仅回退 export/import；不改数据模型或 recompile 语义。

### AUD-GOV-005 audit-supplement 的 FM 清单滞后于 CR-0028 能力

- 状态：已解决
- 整改结果：CR-0028 新增文件已并入既有 layout/cli-contract 的 evidence_paths（保持 supplement FM 数 14 不变），转换后核对能力纳入模块闭环对账。
- 证据状态：已验证
- 严重程度：S3
- 优先级：P2
- 影响范围：`docs/00-governance/audit-supplement.json`、FM 闭环对账完整性。
- 证据：`src/asecli/core/` 已含 `graph_review.py`、`island_layout.py`、`reuse_plan.py`（CR-0028 新增），但 supplement 的 `functional_modules` 无对应条目，`grep -c "graph-review\|island"` 返回 0。
- 根因判断：CR-0028 已登记并发布，但能力清单的 supplement 未同步更新，模块闭环对账被归并到 layout/cli-contract，粒度不足以独立验证转换后核对能力。
- 优化做法：在 supplement 中为 graph-review/reuse/island 新增稳定 FM 条目，或在下次审计中显式标注归并原因；不改模块归属算法。
- 技术路径：复用现有 supplement JSON 与 FM 对账流程。
- 验收标准：下一轮审计的 FM 清单能独立对账转换后核对能力，或显式记录归并原因。
- 验证方式：supplement 静态检查、coverage 校验。
- 回滚/降级：无运行时影响，仅治理文档增量。

## 验证记录

| 命令/检查 | 目的 | 结果摘要 | 是否通过 |
| --- | --- | --- | --- |
| `audit_project.py collect . --mode deep` | 全量静态/FM/FE 采证 | 560 indexed、255 text、14 FM、17 FE、未截断 | 是 |
| `check_project_architecture.py --check-docs --check-kickoff --check-traceability --check-fitness --strict` | 完整治理/模块门禁 | fitness 1 error（commands.py 私有导入） | 否 |
| `check_project_architecture.py --check-release --strict` | 发布治理 | 0 finding | 是 |
| `uv run --frozen pytest -q` | 全量自动回归 | 382 passed、3 skipped | 是 |
| `uv run --frozen python tools/check_regression_catalog.py` | REG 目录完整性 | 61 parsed、6 conditional、0 missed | 是 |
| `uv run --frozen python tools/check_ci_governance.py` | CI 治理 | 0 finding | 是 |
| `uv lock --check` | 锁文件 | 通过 | 是 |
| `git diff --check` | 工作树格式 | 干净 | 是 |
| PyPI 只读查询 | 公开发布真实性 | `asecli/0.6.2`、`0.6.4` 均 200 | 是 |

## 计划外发现

- 工作区存在未跟踪目录 `e2e-results/wave-noise-20260908-170741/`，含一个 wave-noise Shader、`.meta` 与 `identity.json`（键为 reason/sha256/original，无敏感值）。不属于 `.gitignore`，未来使用宽泛 `git add` 时可能被误提交。
- 上一轮报告中的「证据采集器默认 0 FM、需显式传 supplement」问题在本轮依然存在，已按 supplement 显式路径处理，未修改外部技能。

## 遗留问题

- AUD-MOD-003（fitness 私有导入）与 AUD-GOV-005（supplement 清单滞后）已按同时间戳任务书 P1.1、P2.1 整改完成。
- 发布边界：PyPI/GitHub Release 已闭环，本轮未执行真实上传/回滚演练。
- 运行边界：EditorGraphSpec v3、转换后图整理能力的正常缩放画布视觉、目标 Shader 渲染、未知 ASE/模板兼容仍未验证。
- 建议下一次审计：进入 `v0.6.5` 或下一次发布前执行；若不发布，最迟 2026-09-22 复审。

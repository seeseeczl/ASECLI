---
id: AUD-2026-09-08-130015
type: audit-report
status: verified
version: 2
created_at: 2026-09-08T13:00:15+08:00
owner: long
related: [CR-0023, CR-0024, OPT-2026-09-08-130015, AUD-FLOW-004, AUD-FLOW-005, AUD-FE-007, AUD-GOV-004, AUD-REL-002, AUD-MOD-002, AUD-SIZE-002]
supersedes: []
evidence: [temporary evidence JSON, local governance checks, targeted and full pytest, isolated Tuanjie Editor E2E, public PyPI API]
---

# 项目审计报告

## 元信息

- 项目路径：`/Users/long/GitHub/ASECLI`
- 项目类型：Python CLI + Unity/Tuanjie/ASE Editor bridge；公开 MIT 项目
- Profile：`core`、`ai-agent`
- 审计时间：2026-09-08 13:00:15 +08:00
- 当前分支 / commit：`main` / `0ac998583da18edfa1aea0f2a9af70db0c27b35d`
- 工作区状态：审计开始时 dirty，17 个路径；其中包含 EditorGraphSpec v3 代码/测试、历史对抗审计和 SG→ASE 提案。上述用户改动均未修改或清理；本审计另新增同时间戳两份产物。
- 审计范围：治理与追溯、变更门禁、发布治理、模块边界、审计证据源；按标准模式补齐 FM/FE、LOC 和七类专项最低基线。
- 非目标：不修复发现、不提交/推送/打 tag/发布、不初始化 OpenSpec/CodeGraph、不启动 Unity/Tuanjie、不复验画布、Inspector 或目标渲染。
- 请求模式 / 实际模式：治理审计 / 标准审计。
- 未覆盖范围：完整 pytest、真实 Editor/UI、远端 GitHub Actions 环境保护规则、未发布 PyPI 版本的真实上传与回滚。

## 审计模式与证据等级

| 项目 | 结果 | 证据/限制 |
| --- | --- | --- |
| 证据采集器 | 已运行 | schema 1.1；470 files indexed、220 text files read；`truncated=false`；临时 JSON 位于系统临时目录，不作为项目第三份产物 |
| 静态证据 | 已验证 | README、pyproject、CI/publish、治理/架构/质量/发布文档、当前 diff、14 FM、16 FE |
| 自动化测试 | 已验证 | 治理/审计/供应链/可复现/安装 25 passed；EditorSpec/CLI 相关 85 passed；REG 53/53，0 missed |
| 运行与 UI | 未验证 | 本次是治理审计且没有 UI 变更，不启动 Editor；历史 REG/REL 只作为既有证据，不冒充本次运行 |
| 发布产物 | 部分验证 | 只读确认无本地/远端 `v0.6.2` tag，PyPI JSON API 返回 404；未重验历史 GitHub Release 资产 |

## 结论摘要

- 总体判断：项目已具备较完整的 FR/CR/ADR/TASK/REG/REL 体系和强自动化基础，但治理门禁在连续发布后发生复发性漂移。当前总体仍为 **L2（可重复）**，构建/测试和既有私有 Release 证据局部 L3；公开 PyPI 交付链仅 L1。
- 最大阻塞：README 后部和供应链文档把 PyPI 写成当前正式入口，但 PyPI 项目不存在；顶部 GitHub Release 一键安装仍可用，问题是发布状态与文档声明不一致。
- 最大回归风险：`publish.yml` 的 tag 路径不依赖主 CI，缺少全量测试、完整治理、供应链、可复现构建和 tag/version 一致性门禁，可把未完成治理的包直接交给 OIDC 发布作业。
- 第一优先优化方向：在任何 `v0.6.2` tag 前，先让“文档声明—版本—测试—治理—构建—发布—安装—REL”形成单一可失败关闭的公开发布链。
- 审计初始发现规模：S0 0 项、S1 3 项、S2 3 项、S3 1 项；对应 P0 2 项、P1 4 项、P2 1 项。
- 问题统计：S0=0，S1=0，S2=0，S3=0；P0=0，P1=0，P2=0。

### 2026-09-08 整改后增量结论

- 原审计快照与严重度统计保留；本轮 7 个问题均按任务书完成整改，当前开放整改项为 0。
- 公开安装已恢复为真实可用的 GitHub Release `v0.6.1`；PyPI、`v0.6.2` tag 和远端 OIDC 均未执行，CR-0023 保持进行中。这是事实对齐闭环，不是 PyPI 发布完成。
- tag 发布已统一到本地可失败关闭的候选门禁；远端 GitHub candidate run 仍须等下一次明确发布授权，不以 workflow 静态/fixture 证据冒充远端成功。
- EditorGraphSpec v3 已通过治理追溯、自动回归和隔离团结双进程后验，但仍是未发布能力；真实画布视觉、目标渲染和未知 ASE/模板仍未验证。

## 项目简介与功能作用

- 项目简介：ASECLI 为 Shader/技术美术与 AI Agent 提供 ASE 图解析、修改、创建、布局、Material Inspector 支持、校验和 Editor bridge。
- 主要输入/输出与边界：输入为 ASE Shader/Function、声明式 EditorGraphSpec 和工程路径；输出为结构化 JSON、经备份/校验的资产修改、可安装 wheel/sdist 与 Agent Skill。真实 ASE 保存、画布视觉和渲染结果必须由目标 Editor 证据单独证明。

| 功能/场景 | 目标用户 | 入口与输入 | 主要输出 | 实现状态 | 证据 |
| --- | --- | --- | --- | --- | --- |
| 离线 ASE 图治理 | 技术美术/Agent | 解析、图修改、校验、布局 CLI | JSON 与可恢复文件修改 | 已实现 | 14 FM、16 FE、REG catalog |
| ASE Editor 创建/桥接 | 技术美术/Agent | `create --backend editor`、`recompile` | ASE 真实资产/manifest | v2 已发布；v3 工作中 | 历史 REL/REG；当前 85 tests |
| 安装与发布 | 使用者/维护者 | GitHub Release、计划中的 PyPI | wheel/sdist/Skill | GitHub v0.6.1 已有；PyPI 未闭环 | tag 列表、PyPI 404、CR-0023 |

## 审计覆盖率

| 对象 | 分类 | 覆盖状态 | 证据方式 | 未覆盖原因 |
| --- | --- | --- | --- | --- |
| 治理与追溯 | 核心 | 已验证 | Project Architect strict、源文档抽样 | 无 |
| 发布与安装 | 核心 | 已验证/部分运行 | workflow 静态审查、tag/PyPI 只读查询 | 未实际发布 0.6.2 |
| 14 个 FM | 核心/支撑 | 已审计 | supplement + 源/测试/REL 对账 | v3 Editor 实机未跑 |
| 16 个 CLI FE | 核心 | 已审计 | argparse 自动发现 + handler/test 对账 | v3 create 真实 Editor 未跑 |
| 七类专项 | 基线 | 已覆盖 | 静态/自动/历史证据分层 | UI、远端保护规则未验证 |

## 严重程度总览

| 问题 ID | 证据状态 | 优先级 | 严重程度 | 领域 | 问题 | 核心证据 |
| --- | --- | --- | --- | --- | --- | --- |
| AUD-FLOW-004 | 已验证 | P0 | S1 | 公开交付 | PyPI 正式入口声明领先于真实可用性；GitHub Release 一键安装仍可用 | README；PyPI API 404；无 `v0.6.2` tag；CR-0023 进行中 |
| AUD-GOV-004 | 已验证 | P0 | S1 | 自动门禁 | CI 子集为绿但完整治理门禁失败，tag 发布又绕过主 CI | 25 passed；CI governance 0；strict 17/23 finding；workflow |
| AUD-FLOW-005 | 已验证 | P1 | S1 | 变更闭环 | EditorGraphSpec v3 工作树没有正式 CR/ADR/TASK/REG/时间线链 | proposal 自述“尚未登记”；17-path dirty worktree |
| AUD-FE-007 | 已验证 | P1 | S2 | CLI 入口 | `create` 的 v3 自动测试通过，但真实 Editor 保存/重开未验证 | 85 passed；未运行 Editor |
| AUD-REL-002 | 已验证 | P1 | S2 | 发布记录 | REL-0008～0011 再次不符合完整 release-record 契约 | `--check-release --strict` 23 findings |
| AUD-MOD-002 | 已验证 | P1 | S2 | 模块边界 | layout CLI 直接导入 4 个 core 私有模块 | fitness 4 errors；配置只允许 `__init__.py`/`contracts/**` 公开 |
| AUD-SIZE-002 | 已验证 | P2 | S3 | LOC | 4 个 C# 资源片段超过 250 行预警线 | 300/290/284/274 行；均低于 400 硬上限 |

## 项目架构

### 当前结构

- `src/asecli/cli` 为 16 个子命令的组合根；`core`、`checks`、`schema`、`bridge` 承担业务规则、校验、版本数据和 Editor 信任边界。
- `skills/asecli` 随 wheel 分发；`.github/workflows/ci.yml` 负责分支/PR 验证，`publish.yml` 负责 semver tag 的 PyPI OIDC 发布。
- 治理事实源分散于 `docs/00-governance`、`docs/01-architecture`、`docs/03-quality`、`docs/04-delivery`、`docs/05-audits`；OpenSpec 未初始化。

### 关键链路（审计时快照）

| 链路 | 入口 | 核心模块 | 数据/状态流 | 外部依赖 | 结论 |
| --- | --- | --- | --- | --- | --- |
| 离线图治理 | 15 个文件/图命令 | cli→core/checks/schema | 文件→模型→校验→备份/写回 | 无运行时依赖 | 已闭环 |
| Editor 创建 | `create` | cli→bridge→ASE | spec→白名单→MCP→暂存→提交→manifest | Tuanjie/Unity、ASE 1.9.6.2 | v2 已闭环；v3 部分闭环，AUD-FLOW-005 |
| 公开安装 | README/PyPI | pyproject→publish→PyPI | tag→build→OIDC→registry→用户安装 | GitHub Actions、PyPI | 断链，AUD-FLOW-004 |
| 治理门禁 | PR/push/tag | CI checker→文档/REG/REL | 变更→证据→门禁→发布 | GitHub Actions | 部分闭环，AUD-GOV-004 |

### 模块边界与隔离

| 模块 | 独立文件/目录 | 公共接口 | 独立测试 | 跨模块依赖 | 修改爆炸半径 | 结论 |
| --- | --- | --- | --- | --- | --- | --- |
| cli | 是 | `asecli <command>` | 是 | core/checks/schema/bridge | 中 | 4 个私有导入需收口 |
| core | 是 | `__init__.py` + contracts | 是 | 标准库 | 中 | 功能稳定，公开面不足 |
| bridge | 是 | MCP/Editor API | 是+条件 E2E | Editor/MCP | 高 | v3 WIP 尚未完成治理闭环 |
| checks/schema | 是 | 校验/schema API | 是 | core | 低 | 正常 |
| skill | 是 | SKILL/references | 是 | wheel 打包 | 中 | 正常 |

## 技术路径与交付形态

- 技术路径：Python 3.10+、标准库运行时、uv + hatchling、pytest；本地 CLI 与 Unity/Tuanjie Editor MCP 混合。
- 实现/壳形态：CLI + 可选 Editor bridge；不是常驻服务。
- 构建与交付：CI 双 Python、固定 SHA actions、固定 epoch 双构建、wheel/sdist、SBOM/供应链检查、GitHub Release；PyPI Trusted Publishing 已配置但未闭环。

| 交付物 | 格式/载体 | 生成方式 | 安装/部署 | 签名/发布证据 | 结论 |
| --- | --- | --- | --- | --- | --- |
| ASECLI v0.6.1 | wheel/sdist/GitHub Release | 历史 release 流程 | `uv tool install` from wheel | 历史 REL-0011 | 历史已验证，本轮未重验 |
| ASECLI v0.6.2 | wheel/sdist/PyPI | `publish.yml` tag | 文档后部曾声明 `uv tool install asecli` | 无 tag、PyPI 404 | 未发布；当前应保持 GitHub Release 入口 |
| Agent Skill | wheel 内文件 | hatch force-include | `asecli install-skill` | tests/历史 release | 已验证 |

## 平台支持

| 平台/版本 | CPU/运行环境 | 已声明 | 可构建 | 已测试 | 已发布 | 证据/限制 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Python 3.10/3.12 | macOS/Linux CI | 是 | 是 | 本轮当前 Python 定向通过；历史双矩阵 | v0.6.1 | 本轮未跑远端矩阵 |
| Python 3.11/3.13 | 通用 | classifier 声明 | 推断 | 未验证 | wheel 为 py3-none-any | 缺本轮运行证据 |
| Tuanjie 2022.3 + ASE 1.9.6.2 | Editor | 是 | 不适用 | 历史 v2/V3 layout | 随 CLI 能力发布 | 本轮未启动 Editor |

## 上帝文件与模块隔离

### 文件行数门禁

- 门禁：source 250/400，test 400/600，config 160/200；来自 `.project-architect.json`。
- 扫描范围 / 排除范围：`src`、`tests`、`tools`；采集未截断。缓存、构建产物、第三方目录排除。

| 文件 | 行数 | 门禁结果 | 核心链路 | 建议 | 问题 ID |
| --- | --- | --- | --- | --- | --- |
| `asecli_material_gui.part00.cs.txt` | 300 | 预警 | 是 | 保持确定性拼装，新增逻辑前先拆职责 | AUD-SIZE-002 |
| `asecli_material_gui.part01.cs.txt` | 290 | 预警 | 是 | 同上 | AUD-SIZE-002 |
| `editor_create.part01.cs.txt` | 284 | 预警 | 是 | v3 扩展不得继续堆入同一片段 | AUD-SIZE-002 |
| `editor_create.part02.cs.txt` | 274 | 预警 | 是 | 按事务阶段拆分并保持单 payload | AUD-SIZE-002 |

### 上帝文件候选

| 文件或逻辑类型族 | 规模/职责 | 扇入/扇出或共享状态 | 修改/回归证据 | 结论 | 拆分边界 |
| --- | --- | --- | --- | --- | --- |
| Editor C# deterministic parts | 3 个 Editor create 片段 | 共用单 payload/nonce/rollback | 当前 v3 WIP 同时改两片并新增一片 | 候选，不是已确认上帝文件 | 规格展开、ASE 节点构造、事务提交 |
| MaterialGUI parts | 2 个 290+ 行片段 | 同一 Inspector provider | 历史 REG-0044 | 受控候选 | 展示、条件、持久化职责已部分分片 |

### 模块隔离风险

| 问题 ID | 功能 | 当前分布 | 耦合点 | 连带回归 | 建议边界 |
| --- | --- | --- | --- | --- | --- |
| AUD-MOD-002 | meticulous layout CLI | cli + core | `layout_command.py` 直接导入 4 个 core 模块文件 | core 文件重组会破坏 CLI | 在 `core.__init__` 或 `core/contracts` 暴露稳定 facade |

## 项目成熟度

| 维度 | 等级 | 当前机制 | 证据 | 主要缺口 |
| --- | --- | --- | --- | --- |
| 需求/变更/追溯 | L2 | FR/CR/ADR/TASK/REG/REL + CSV | 文档体系完整 | v3 WIP 未登记；strict 断链 |
| 架构/模块 | L2 | module-map + fitness | 14 FM | 4 个私有导入 |
| 构建/测试 | L3 | pytest、REG、可复现构建测试 | 25+85 passed；53/53 REG | 本轮未全量/双 Python |
| CI | L2 | 分支 CI + repo-local checker | CI 配置与 checker 为绿 | checker 未覆盖完整治理；tag 路径绕过 |
| 发布/回滚 | L2 | 历史 GitHub REL/hash/回滚 | v0.6.1 历史证据 | PyPI 链 L1；近四份 REL 格式复发 |
| 安全/供应链 | L3（既有链）/L1（PyPI） | 固定 SHA、OIDC、SBOM、0 runtime deps | 本地 supply tests | OIDC 发布前门禁不足 |
| 可观测性 | L2 | 单行 JSON、稳定错误码、manifest/hash | 源码/REG | 无常驻服务指标；不适用部分已说明 |
| UI/Editor | L2 | 条件 E2E + 历史截图 | 历史 REG | v3 本轮未实机 |

- 总体成熟度与依据：**L2**。最低关键链路是公开安装/发布与治理门禁，而不是测试实现能力。

## 回归验证机制

| 检查项 | 当前机制 | 自动化/CI | 覆盖 | 证据 | 缺口 |
| --- | --- | --- | --- | --- | --- |
| 核心/跨模块 | pytest + REG catalog | 分支/PR CI | 53 个回归入口 | 53 parsed、0 missed | v3 尚未写入 REG catalog |
| 治理追溯 | repo-local checker + Project Architect | 本地/部分 CI | 基线文件、LOC、部分 release | 子集绿、完整 strict 红 | 单一事实源未统一 |
| 发布前 | build/smoke/OIDC | tag workflow | wheel/sdist + parse | workflow 静态可见 | 不依赖全量 CI、无 tag/version check |
| 失败留痕 | BUG/REG/timeline/REL | 文档化 | 历史较完整 | 旧 release 记录 | 连续四次发布记录格式复发 |

## OpenSpec 规范管理

| 状态 | 结论 | 证据 |
| --- | --- | --- |
| 工具、项目配置、实际使用、规范一致性、strict 校验 | 降级 | `openspec` 已安装但仓库无 `openspec/`，`openspec list` 返回无 active changes；继续以既有 FR/CR/ADR 文档为事实源，本审计不初始化。 |

## CodeGraph 使用情况

| 状态 | 结论 | 证据 |
| --- | --- | --- |
| 安装、初始化、索引新鲜度、实际使用、更新机制 | 降级 | `codegraph` 已安装，项目状态为 `Not initialized`；本轮使用 `rg`、Git diff 和 Project Architect fitness 替代，不初始化。 |

## 文档增量与变更留档

| 变更类型 | 载体/机制 | 增量历史 | 关联键 | 字段完整性 | 抽样证据与缺口 |
| --- | --- | --- | --- | --- | --- |
| 需求变更 | change-register/traceability/technical-route | 有 | CR-0022/0023、ADR-0019 | 部分 | CR-0022/23 的 module/task/REG 回链不合格 |
| 技术变更 | module-map + ADR | 有 | CR-0018～21 | 部分 | module-map 漏多个 CR 回链；v3 WIP 无正式 CR/ADR |
| 缺陷/回归 | bug-register/REG catalog | 有 | REG-0001～0051 | 完整到 v0.6.1 | v3 tests 尚未登记新 REG |
| 发布记录 | REL-0001～0011 | 有 | REL/TASK/REG | 部分 | REL-0008～11 共 23 个完整门禁发现 |
| 文件修改记录 | Git/timeline | 有 | commit/CR/TASK | 部分 | 当前 v3 dirty diff 尚无来源 ID；合理作为 WIP，但禁止合并/发布 |

## 功能模块闭环度

- 模块统计：发现数：14；已审计数：14；未覆盖数：0。
- 清单校准：显式传入 `.project-architect.json` 指向的 supplement 后得到稳定 14 FM。按技能文档的不带参数命令采集时曾返回 0 FM，作为工具降级记录；未改动外部技能。

| 模块 ID | 模块/能力 | 需求/入口 | 主路径/关键链路 | 数据/状态闭环 | 异常/恢复 | 日志/可观测性 | 回归/验收 | 发布证据 | 结论 | 问题 ID |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FM-0E60A4DD1B | parse-serialize | FR-0001 / parse | file→model→serialize | roundtrip | parse/not-found | JSON | REG/tests | v0.6.1 | 已闭环 | 不适用 |
| FM-9040886B90 | graph-mutation | FR-0002 / 5 图命令 | graph_ops→validate→atomic write | 备份/不变量 | 冲突拒绝 | JSON | REG/tests | v0.6.1 | 已闭环 | 不适用 |
| FM-8ADC52C2A4 | schema-library | FR-0002 / add-node | version→schema→node | 版本门禁 | unknown 拒绝 | code | schema tests | wheel | 已闭环 | 不适用 |
| FM-C73F236CD5 | validation-checksum | FR-0003 | checks→issues/checksum | 显式写入 | dry-run/备份 | issues JSON | tests | v0.6.1 | 已闭环 | 不适用 |
| FM-F03DFA9A41 | layout | FR-0008 | CLI→core layout→audit | 语义指纹/备份 | 硬门禁零写入 | V2/V3 JSON | REG-0050/51 | v0.6.1 | 已闭环 | 不适用 |
| FM-3537DE9938 | create-from-template | FR-0005 | donor/template→file | 回读 | exists/不合规拒绝 | JSON | create tests | v0.6.1 | 已闭环 | 不适用 |
| FM-DF0669A019 | recompile-bridge | FR-0004 | hash→MCP→save | 前后 hash | timeout/unknown | JSON | bridge tests/历史实机 | v0.6.1 | 已闭环 | 不适用 |
| FM-1DB3E4EA8B | cli-contract | FR-0007 / 16 commands | argparse→handler→envelope | code/status | usage/business/internal | stdout JSON | CLI tests | v0.6.1 | 已闭环 | 不适用 |
| FM-25E63BD4F6 | agent-skill | FR-0006 | Agent→CLI→validate | 幂等安装 | 冲突拒绝 | CLI JSON | skill tests | v0.6.1 | 已闭环 | 不适用 |
| FM-2E47AA5409 | graph-audit | FR-0010 | graph+consumer→classification | 只读 | 外部消费者保护 | JSON | usage tests | v0.6.1 | 已闭环 | 不适用 |
| FM-35114E2780 | custom-gui-property-presentation | FR-0009/10/11 | spec→metadata→对账 | 逐属性 | 整批拒写 | contract JSON | GUI tests/历史 UI | v0.6.1 | 已闭环 | 不适用 |
| FM-DB13C6D6D8 | gui-support-material-inspector | FR-0009 | project→provider/install | hash/回读 | 冲突/备份 | provider JSON | GUI tests/历史 UI | v0.6.1 | 已闭环 | 不适用 |
| FM-3EEC4BD8D5 | comment-group | FR-0010 | members→Comment→bounds | 树/CHKSM | 冲突拒绝 | issues | REG-0041/51 | v0.6.1 | 已闭环 | 不适用 |
| FM-14E9E4031E | editor-api-create | FR-0011 + 未登记 v3 | spec→ASE→staging→commit→manifest | v2 完成；v3 静态/测试 | rollback/temp | JSON/manifest | 85 tests；v3 实机未跑 | v2 in v0.6.1 | 部分闭环 | AUD-FLOW-005 |

### 前端功能入口闭环

- 入口统计：发现数：16；已审计数：16；未覆盖数：0。
- 清单校准：相比 2026-09-03 基线的 15 个入口，本轮补回当时遗漏的既有 `install-skill`；不是新增命令。

| 入口 ID | 页面/入口与类型 | 条件/权限 | 目标/handler | 状态覆盖 | 返回/恢复 | 测试/运行证据 | 结论 | 问题 ID |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FE-5FE7C39BCC | parse CLI | 文件可读 | parse | 成功/错误 | 只读重试 | tests/历史 wheel | 已闭环 | 不适用 |
| FE-5F33E87610 | set-field CLI | 可变字段 | set-field | dry/write/reject | 备份 | tests | 已闭环 | 不适用 |
| FE-37BA87FA15 | add-node CLI | schema/version | add-node | success/unknown | 备份 | tests | 已闭环 | 不适用 |
| FE-C3162CA2E1 | connect CLI | 端口有效 | connect | success/conflict | 备份 | tests | 已闭环 | 不适用 |
| FE-AAF53AF86F | disconnect CLI | wire 存在 | disconnect | success/not-found | 备份 | tests | 已闭环 | 不适用 |
| FE-0018A7D5D8 | remove-node CLI | node 存在 | remove-node | success/external | 备份 | tests | 已闭环 | 不适用 |
| FE-50D4B549C6 | graph-audit CLI | 文件/工程根 | graph-audit | 分类完整 | 人工确认 | tests | 已闭环 | 不适用 |
| FE-BBB0F9830B | validate CLI | 文件可读 | validate | 0/error | 修复后重试 | tests | 已闭环 | 不适用 |
| FE-369C790BD8 | fix-checksum CLI | 显式 write | fix-checksum | dry/write | 备份 | tests | 已闭环 | 不适用 |
| FE-C71A570BA7 | layout CLI | 图可解析 | layout | dry/write/audit | 备份/失败关闭 | REG-0050/51 | 已闭环 | 不适用 |
| FE-4E1B79DEE4 | custom-gui CLI | metadata | custom-gui | inspect/spec/clear | 原子拒写 | tests/历史 UI | 已闭环 | 不适用 |
| FE-1E3A6EB7E7 | gui-support CLI | 工程路径 | gui-support | inspect/install/conflict | hash/备份 | tests/历史 Editor | 已闭环 | 不适用 |
| FE-E476224BF3 | install-skill CLI | Skill 根可写 | install-skill | install/idempotent/conflict | 不覆盖不同内容 | tests/历史安装 | 已闭环 | 不适用 |
| FE-222ADDDF1D | comment-group CLI | live 可选 MCP | comment-group | query/create/check/fit | dry-run/备份 | REG-0041/51 | 已闭环 | 不适用 |
| FE-B537BBBC81 | create CLI | text 或 spec | create | v1/v2/v3/错误 | rollback/temp | v3 85 tests；无本轮 Editor | 部分闭环 | AUD-FE-007 |
| FE-3F4DBCA0D3 | recompile CLI | loopback MCP | recompile | changed/error/unknown | 检查目标 | tests/历史实机 | 已闭环 | 不适用 |

## 交互流程与 UI

### Product Design 参与情况

| 检查项 | 结论 | 证据/限制 |
| --- | --- | --- |
| 历史参与证据、本次调用、当前截图、视觉结论等级 | 本次不适用 | 本轮只审计治理，没有视觉目标或 UI 代码授权；按项目快速路径不启动 Editor、不截图。 |

### 关键流程证据

| 步骤 | 用户目标/操作 | 截图或运行证据 | 健康度 | UX/可访问性问题 | 证据限制 |
| --- | --- | --- | --- | --- | --- |
| 01 | 按 README 安装 ASECLI | 顶部脚本指向最新 GitHub Release；PyPI API 404 | 有风险 | 当前脚本可用，但后部正式入口声明失真 | 未发布 v0.6.2 |
| 02 | 创建 EditorGraphSpec v3 图 | 85 targeted tests | 有风险 | CLI 错误契约已覆盖 | 未运行真实 Editor |

### UI 检查

| 页面/区域 | 层级与清晰度 | 一致性/状态 | 响应式 | 键盘/焦点/语义 | 问题 ID |
| --- | --- | --- | --- | --- | --- |
| CLI 文档安装区 | 文案明确但事实错误 | GitHub/PyPI 状态不一致 | 不适用 | 命令可复制但失败 | AUD-FLOW-004 |
| Editor/Inspector | 本次未审计 | 未验证 | 未验证 | 未验证 | 不适用 |

## 专项工程审计

| 专项领域 | 状态 | 核心证据 | 主要风险/缺口 | 问题 ID |
| --- | --- | --- | --- | --- |
| 安全与隐私 | 已验证（静态） | loopback/MCP tests、OIDC 最小权限 | 发布前缺完整门禁会扩大供应链风险 | AUD-GOV-004 |
| 性能与资源 | 推断 | 历史性能 REG；本轮无性能改动 | v3 未做 Editor 性能/规模运行 | AUD-FLOW-005 |
| 可观测性与运维 | 部分 | JSON、manifest、GitHub REL 历史证据 | PyPI 发布/回滚尚无运行证据 | AUD-FLOW-004 |
| 依赖、供应链与许可证 | 已验证/部分 | MIT、0 runtime deps、固定 action SHA、25 tests | tag workflow 未运行供应链/可复现门禁 | AUD-GOV-004 |
| API、数据兼容与迁移 | 部分 | v1/v2 compatibility tests；v3 tests | v3 没有 CR/ADR/真实 Editor | AUD-FLOW-005 |
| 无障碍与国际化 | 不适用 | 治理审计无 UI 改动 | 既有 UI 证据本轮未复验 | 不适用 |
| 构建可复现与产物完整性 | 部分 | reproducibility tests 通过 | PyPI workflow 单构建且无 hash/SBOM/attestation gate | AUD-GOV-004 |

## 增量审计对比

- 基线报告：`docs/05-audits/2026-09-03-092053-project-audit-report.md`。该报告末尾记录完整 strict 为 0 finding，可作为当前复发判断基线。

| 分类 | 问题 ID | 基线 -> 当前 | 证据/说明 |
| --- | --- | --- | --- |
| 新增 | AUD-FLOW-004 | 私有 GitHub 安装已闭环 -> README 声明未存在的 PyPI 正式入口 | CR-0023/0.6.2 尚未发布 |
| 新增 | AUD-FLOW-005 / AUD-FE-007 | v2 已闭环 -> v3 工作树静态/测试完成但无正式追溯和 Editor 证据 | dirty diff + proposal |
| 复发 | AUD-GOV-004 | 完整 strict 0 -> kickoff 3、trace 14、fitness 4；release 23 | repo-local CI 子集仍为绿；使用新 ID 记录本轮复发 |
| 复发 | AUD-REL-002 | 旧 REL 整改完成 -> REL-0008～11 再次不合规 | 连续发布未复用完整模板/门禁 |
| 复发 | AUD-MOD-002 | BUG-0009 已解决 -> layout CLI 再次直接导入 core 文件 | fitness 4 errors |
| 新增发现 | AUD-SIZE-002 | 硬上限清零 -> 4 个片段超过 warning 线 | 本轮按 warning/limit 双阈值报告 |
| 改善 | FE inventory | 15/15 -> 16/16 | 补回既有 `install-skill`，无遗漏 |

## 阻塞项

| 问题 ID | 阻塞内容 | 影响范围 | 证据 | 解除条件 |
| --- | --- | --- | --- | --- |
| AUD-FLOW-004 | PyPI 项目不存在 | README 正式安装路径 | `https://pypi.org/pypi/asecli/json` 返回 404 | 正式发布并复验，或发布前恢复 GitHub Release 为真实入口 |
| AUD-GOV-004 | 完整治理/发布 strict 不通过 | 下一次 tag/公开发布 | 17 + 23 findings | 所有 finding 清零且 tag workflow 强制依赖同一门禁 |

## 潜在风险

| 问题 ID | 风险 | 触发条件 | 影响 | 概率 | 应对建议 |
| --- | --- | --- | --- | --- | --- |
| AUD-RISK-004 | 错 tag 发布错误 pyproject 版本 | tag 与 version 不一致 | 发布错误或不可重用版本 | 中 | 发布作业首步比较 tag/version 并失败关闭 |
| AUD-RISK-005 | 公开包回滚语义失真 | 把“撤回”当作可逆删除 | 已下载用户无法回滚，版本不可复用 | 中 | 使用 yank + 修复版本 + 公告；保留旧 wheel hash |
| AUD-RISK-006 | 用户 WIP 被审计产物混入提交 | 提交时使用宽泛 `git add` | v3/旧审计/本报告范围混杂 | 中 | 后续按精确路径提交并先复核状态 |

## 问题详情

### AUD-FLOW-004 正式 PyPI 安装链未闭环

- 状态：已解决
- 整改结果：当前入口已恢复为 GitHub Release，PyPI 保持未发布。
- 证据状态：已验证
- 严重程度：S1
- 优先级：P0
- 影响范围：依赖 README 分发说明判断渠道的用户、CR-0023、v0.6.2。
- 证据：README 顶部一键脚本仍从最新 GitHub Release 安装，但后部和供应链文档声明正式入口为 PyPI；公开 PyPI API 返回 404；本地/远端都没有 `v0.6.2` tag；traceability 将 CR-0023 标为进行中。
- 根因判断：文档和版本号先切换，外部发布与回读尚未完成，缺少“只有发布实证后才能切正式入口”的状态门禁。
- 优化做法：发布前先恢复真实可用的 GitHub Release 安装说明，或在 P0 门禁全部通过后完成 v0.6.2 PyPI 发布、下载、hash、安装、回滚/yank 演练，再把 CR/REL/README 同步为已发布。
- 技术路径：复用 uv、Trusted Publishing、GitHub Release 和现有隔离安装脚本。
- 验收标准：匿名环境可安装 `asecli==0.6.2`，PyPI 元数据/文件 hash 与候选一致，README 命令可执行，REL 与 traceability 为 released；发布前 README 不再声称已可用。
- 验证方式：PyPI JSON、下载 hash、隔离 `uv tool install`、CLI/Skill smoke、REL strict。
- 回滚/降级：PyPI 已发布版本只能 yank/发布修复版并公告，不能假设撤回下载；未发布时回退文档入口。

### AUD-GOV-004 自动治理门禁与发布路径分叉

- 状态：已解决
- 整改结果：候选门禁已统一；远端 tag run 待发布授权。
- 证据状态：已验证
- 严重程度：S1
- 优先级：P0
- 影响范围：PR/push/tag、公开供应链和所有治理文档。
- 证据：repo-local `check_ci_governance.py` 为 0 finding，25 tests 通过；完整 kickoff/trace/fitness strict 有 3/14/4 findings，release strict 有 23 findings；`ci.yml` 仅监听 branch/PR，`publish.yml` 的 publish 只依赖单次 build+parse。
- 根因判断：为提高速度建立的 CI 子集没有和 Project Architect 完整契约共同演进；发布工作流复制了构建步骤而未复用已验证 artifact/gate。
- 优化做法：把完整治理、REG、供应链、可复现构建和 tag/version 校验变成 tag 发布的硬依赖；publish job 只消费同一次候选验证的不可变 artifact。
- 技术路径：复用现有 Python checker、GitHub Actions reusable workflow/artifact、OIDC environment，不新增第三方依赖。
- 验收标准：故意制造任一 trace/release/tag mismatch 时 publish 不可达；正常候选一次构建、测试、hash 后才获得 OIDC；完整 strict 0 finding。
- 验证方式：workflow 静态测试、负例 fixture、GitHub dry candidate run、artifact digest 对账。
- 回滚/降级：保留手动 workflow_dispatch 的无发布验证模式；发布 job 失败时不创建 tag 以外的新外部状态。

### AUD-FLOW-005 EditorGraphSpec v3 变更缺正式治理链

- 状态：已解决
- 整改结果：CR-0024/ADR-0020/TASK-0054/REG-0053 已双向登记。
- 证据状态：已验证
- 严重程度：S1
- 优先级：P1
- 影响范围：FM-14E9E4031E、公开 spec 版本、SGCLI 写手契约、Editor C# payload。
- 证据：工作树约 660 additions/430 deletions，新增 v3/primitives/recipe/precision/default/min/max；提案明确写“尚未登记为 ASECLI 的 FR/CR”；治理文档无对应新 ID。
- 根因判断：需求提案与 ASECLI 公共契约实现发生交叉，尚未执行公共 API/跨模块变更前的架构审查和追溯登记。
- 优化做法：合并前创建加性 CR/ADR/TASK/REG，明确 v2/v3 兼容、SGCLI/ASECLI 边界、允许节点/recipe 安全模型、真实 Editor 门禁和回滚。
- 技术路径：保留当前模块化拆分与现有测试，不把 SG 转换器并入 ASECLI。
- 验收标准：CR→ADR/MOD→TASK→REG→REL 双向可查；v1/v2 兼容；未知 primitive/version 失败关闭；无未登记公共字段。
- 验证方式：strict traceability、targeted/full pytest、Editor 两进程 manifest、diff/checksum。
- 回滚/降级：合并前可保留为独立 WIP；不满足门禁则不提交 v3 公共契约，v2 保持发布基线。

### AUD-FE-007 create v3 入口缺真实 Editor 后验

- 状态：已解决
- 整改结果：隔离团结双进程后验通过，能力仍未发布。
- 证据状态：已验证
- 严重程度：S2
- 优先级：P1
- 影响范围：FE-B537BBBC81、primitive/recipe/property semantics。
- 证据：审计时 85 个定向测试通过但未启动 Editor；整改后自动定向 99 passed，隔离团结 2022.3.61t9 + ASE 1.9.6.2 双进程 `1 passed in 69.33s`，真实回读 primitive/recipe/属性/连接一致，0 Shader/CS error、0 staging。
- 根因判断：解析/序列化/mock 证据不能证明 ASE 1.9.6.2 的真实节点构造、端口、精度/范围和重开 manifest。
- 优化做法：治理登记后在隔离工程集中执行一次 v3 create→save→close→new process reopen→manifest/Inspector 对账。
- 技术路径：复用既有 v2 事务、临时前缀、Selection/UIUtils 恢复和双进程 E2E。
- 验收标准：primitive/recipe 展开、范围/默认值/精度、连接和 manifest 一致；0 error、0 staging、原工程不变。
- 验证方式：条件 bridge pytest、Editor log、前后 hash/manifest。
- 回滚/降级：仅隔离工程；MCP 超时先检查目标和临时资产，不立即重试。

### AUD-REL-002 REL-0008～0011 发布记录契约复发

- 状态：已解决
- 整改结果：release strict 0 finding。
- 证据状态：已验证
- 严重程度：S2
- 优先级：P1
- 影响范围：四份 released 记录、release strict、历史可追溯性。
- 证据：23 findings，涉及变更集合字段、验证与风险章节、回滚验证、CR/FR 反向链接。
- 根因判断：历史发布仍沿用人工自由格式，完整 validator 没有进入每次 release 的必经路径。
- 优化做法：不改发布事实，只按统一 release-record 结构补字段与反向 trace；将 checker 纳入 P0 发布门禁。
- 技术路径：复用现有 REL 模板和 Project Architect checker。
- 验收标准：`--check-release --strict` 0 finding；所有新增文字均可由现有 run/tag/hash/安装证据支持。
- 验证方式：release strict、链接/commit/REG 抽样。
- 回滚/降级：保留 Git 历史；若事实不明则标未验证，禁止编造。

### AUD-MOD-002 layout CLI 绕过 core 公共契约

- 状态：已解决
- 整改结果：CLI 只从 core public 导入，fitness 0 error。
- 证据状态：已验证
- 严重程度：S2
- 优先级：P1
- 影响范围：`src/asecli/cli/layout_command.py` 与 core layout/router/model/commentary。
- 证据：fitness 报 4 个 `private_module_import`；`.project-architect.json` 的公开模式为 `__init__.py` 和 `contracts/**`。
- 根因判断：v2/v3 layout 能力增量直接引用实现文件，但模块公开面未同步扩展。
- 优化做法：建立最小稳定 facade/export，CLI 只依赖公开符号；不重构算法。
- 技术路径：复用 core `__init__.py` 或新建受控 contracts 模块，更新 import 和契约测试。
- 验收标准：fitness 0 error，CLI/布局回归保持通过，公开符号集合有测试。
- 验证方式：strict fitness、layout/CLI tests、import smoke。
- 回滚/降级：仅回退 export/import，不改数据模型或布局语义。

### AUD-SIZE-002 C# 资源片段超过 LOC 预警线

- 状态：已解决
- 整改结果：增长门禁生效，Editor 资源已拆分。
- 证据状态：已验证
- 严重程度：S3
- 优先级：P2
- 影响范围：MaterialGUI 与 Editor create C# 资源的 review 半径。
- 证据：4 个片段为 300/290/284/274 行，超过 source warning 250，低于 limit 400。
- 根因判断：确定性分片解决了硬上限，但后续能力继续在现有片段增长。
- 优化做法：先加预警监控；只有职责边界清楚且拼装字节/事务不变时再拆分。
- 技术路径：复用 `resource_text.py` 确定性拼装和现有 hash/E2E。
- 验收标准：新增代码不继续扩大预警文件；拆分时输出与事务契约保持一致。
- 验证方式：LOC、拼装 hash、C# 静态契约、条件 Editor E2E。
- 回滚/降级：拆分不等价即恢复原分片；不得用永久豁免隐藏增长。

## 验证记录

| 命令/检查 | 目的 | 结果摘要 | 是否通过 |
| --- | --- | --- | --- |
| `audit_project.py collect ... --mode standard --supplement ...` | 全量静态/FM/FE 采证 | 470 indexed、220 text、14 FM、16 FE、未截断 | 是 |
| Project Architect docs/kickoff/trace/fitness strict | 完整治理/模块门禁 | kickoff 3、trace 14、fitness 4 | 否 |
| Project Architect release strict | 发布治理 | release 23，且包含同一 trace 缺口 | 否 |
| `uv run --frozen python tools/check_ci_governance.py` | 当前 CI 子集 | 0 finding | 是，但覆盖不足 |
| `uv run --frozen python tools/check_regression_catalog.py` | REG 目录完整性 | 53/53 parsed，6 conditional，0 missed | 是 |
| 治理/审计/供应链/构建/安装定向 pytest | 5 个治理链模块 | 25 passed | 是 |
| EditorSpec/bridge/CLI 定向 pytest | 当前 v3 WIP | 85 passed | 是（不含真实 Editor） |
| `uv lock --check` | 锁文件 | 通过 | 是 |
| `git diff --check` | 工作树格式 | `tests/test_editor_create_spec.py:398` EOF blank line | 否（用户 WIP，未修改） |
| `openspec list` / `codegraph status` | 工具状态 | 无 OpenSpec 项目；CodeGraph Not initialized | 降级 |
| tag/PyPI 只读查询 | 公开发布真实性 | 无 v0.6.2 tag；PyPI API 404 | 否（未发布） |
| 整改后 Project Architect docs/kickoff/trace/release/fitness strict | 完整治理/模块/发布门禁 | 全部 0 finding | 是 |
| 整改后 REG/自动回归 | 目录与受影响实现 | 57/57 parsed、6 conditional、0 missed；受影响组合均通过 | 是 |
| 整改后 `uv run --frozen pytest -q` | 全量自动回归 | 341 passed、3 skipped | 是 |
| `ASECLI_EDITOR_CREATE_PROJECT=<隔离工程> ... pytest -m bridge tests/test_editor_create_e2e.py` | v2/v3 真实 ASE 创建与全新进程重载 | 1 passed/69.33s；0 Shader/CS error、0 staging | 是 |
| 整改后 `git diff --check` | 工作树格式 | 通过 | 是 |

## 计划外发现

- 证据采集器只有显式传入 `--supplement docs/00-governance/audit-supplement.json` 才得到 14 FM；不带参数时虽配置已声明 supplement，结果仍为 0 FM。该问题位于外部 `project-architect` 技能，本轮只记录降级，不修改技能或项目。
- 审计时用户 WIP 的 `tests/test_editor_create_spec.py` 末尾多一个空行，曾导致 `git diff --check` 失败；整改收尾已通过格式门禁。
- 首次隔离 Editor 工程漏配 Newtonsoft 与 ASEZH locale 包，分别导致 ASE 程序集编译失败；按生产基线补齐隔离依赖后同一门禁通过。该失败属于测试环境准备，不通过删改 ASE 源码绕过。

## 遗留问题

- 本任务书整改遗留：无；P0/P1/P2 共 6 项已完成。
- 发布边界：CR-0023、PyPI、`v0.6.2` tag、远端 OIDC 与真实公开产物仍未执行；任何发布前必须重新运行候选门禁和发布前增量审计。
- 运行边界：EditorGraphSpec v3 的真实创建/重载已验证，但正常缩放画布视觉、目标 Shader 渲染、未知 ASE/模板兼容仍未验证。
- 建议下一次审计：进入 `v0.6.2` 发布前立即执行；若不发布，最迟 2026-09-15 复审。

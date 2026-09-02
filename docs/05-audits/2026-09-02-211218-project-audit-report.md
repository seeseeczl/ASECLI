# 项目审计报告

## 元信息

- 项目路径：/Users/long/GitHub/ASECLI
- 项目类型：Python CLI + Agent Skill + Unity/Tuanjie MCP 桥接
- 审计时间：2026-09-02T21:12:18+08:00（Asia/Shanghai）
- 当前分支 / commit：main / 8aaff193b76787b548daac6b9352866665976c68
- 工作区状态：clean；采证时 0 个变更路径
- 审计范围：207 个已索引项目文件；127 个文本文件、13 个功能模块、15 个 CLI 入口；Python 全量自动回归、CI governance、REG catalog、本地 CLI 冒烟、GitHub run 33625061100 下载 artifact 与可移植 SHA256SUMS
- 非目标：不修改业务代码、不创建 commit、不 push、不打 tag、不创建 GitHub Release、不写用户生产 Tuanjie 工程、不初始化 OpenSpec/CodeGraph
- 请求模式 / 实际模式：标准 / 标准增量复审（相对 `docs/05-audits/2026-09-01-132548-project-audit-report.md`）；真实 Editor 本次未重跑，沿用 2026-09-02 同日隔离团结证据
- 未覆盖范围：Windows/Linux 主机；Dependabot/在线漏洞库；0.2.0 tag 与 Release；Editor 创建后的新进程重开；目标平台渲染画面

## 审计模式与证据等级

| 项目 | 结果 | 证据/限制 |
| --- | --- | --- |
| 证据采集器 | 已运行 | schema 1.1；207 files indexed、127 text files read、未截断；supplement 校准 13 个 FM；证据 JSON 位于系统临时目录 |
| 静态证据 | 已验证 | 源码、CLI 15 入口、治理/追溯、CI 工作流、Skill、REL 与 Git 工作区 |
| 自动化测试 | 已验证 | `uv run --frozen pytest -q`：223 passed, 3 skipped；REG catalog 36 条可收集；CI governance 零 findings |
| 运行与 UI | 部分 | 本次 CLI `parse`/`validate` 冒烟通过；无独立 UI。隔离团结 v2 创建/Inspector 沿用同日 timeline 证据，本次未重开编辑器 |
| 发布产物 | 部分 | GitHub run 33625061100 artifact 下载后 `shasum -a 256 -c SHA256SUMS` 通过；0.2.0 仍无 tag/Release |

## 结论摘要

- 总体判断：相对 9 月 1 日基线，主链路已扩展到 15 个 CLI 入口和属性呈现/Editor 创建/自有 GUI；当天对抗性 P1 与 BUG-0017/0018 已在 HEAD 关闭。当前不能把 `main` 上的 0.2.0 候选当成已交付正式版，Editor 新进程重开仍缺证据。
- 最大阻塞：0.2.0 未获单独 tag/Release 授权；试用者按 README 仍安装 `v0.1.0`，拿不到当前契约。
- 最大回归风险：Editor 创建 JSON 的 `reloaded=true` 只证明暂存图 LoadFromDisk；提交后目标图依赖独立 `recompile`，新进程重开未做。
- 第一优先优化方向：在已验证的可移植 artifact 上完成 0.2.0 发布授权，并补跑 Editor v2 新进程重开。
- 问题统计：S0=0，S1=0，S2=3，S3=2；P0=0，P1=3，P2=2

## 项目简介与功能作用

- 项目简介：AseCLI 让 AI Agent 以单行 JSON CLI 解析、修改、校验、整理并受控创建 Amplify Shader Editor 文件；本地文本链路不依赖 Unity，HLSL 再生成与 Editor API 创建走 loopback MCP。
- 主要输入/输出与边界：输入为 `.shader`/规格 JSON/CLI 参数/受控 MCP；输出为单行 JSON、原子写回、`.bak` 与编辑器事务结果。默认只信任 loopback MCP。

| 功能/场景 | 目标用户 | 入口与输入 | 主要输出 | 实现状态 | 证据 |
| --- | --- | --- | --- | --- | --- |
| 解析、校验与图修改 | Agent/开发者 | parse/validate/set/add/connect/disconnect/remove/graph-audit | JSON、dry-run 或原子写回 | 已实现 | 本次 223 passed；HLIT parse/validate 冒烟 |
| 布局与 Comment | Agent/开发者 | layout、comment-group | 仅坐标或原生 Comment 框 | 已实现 | layout/commentary 自动测试；真实画布精排待目标图 |
| 材质 Inspector 契约 | Agent/开发者 | custom-gui、gui-support | ASECLI 元数据、固定 GUI 安装、呈现契约 JSON | 已实现 | 属性呈现双向对账测试；同日 Inspector/Tooltip 用户确认 |
| 文本/Editor 创建与重编译 | Agent/开发者 | create、recompile | 新 shader、saved/changed/manifest | 已实现/新进程未验证 | 文本创建门禁已测；v2 同日创建通过；新进程重开未执行 |
| Agent 操作指南 | Codex/Claude/Codely | skills/asecli/SKILL.md | 可恢复三链路 | 已实现 | Skill 与 CLI 契约测试、REG-0010 |
| 本地与远端交付 | 维护者 | uv build、GitHub Actions | wheel/sdist/SPDX/SHA256SUMS | 0.2.0 候选已构建；未发布 | run 33625061100 清单校验通过；无 tag |

## 审计覆盖率

| 对象 | 分类 | 覆盖状态 | 证据方式 | 未覆盖原因 |
| --- | --- | --- | --- | --- |
| 207 个项目文件 | 核心/支撑 | 已验证 | collect 索引、127 文本读取、LOC 扫描未截断 | 无 |
| 13 个 FM 能力模块 | 核心 | 已验证 | 基线 9 个 ID 复用 + 4 个新能力 supplement | 自动发现器对 `src/asecli` 为空，已人工校准 |
| 15 个 CLI FE 入口 | 核心 | 已验证 | argparse 自动清单与源码/测试对账 | 未覆盖数 0 |
| 隔离目标编辑器 | 外部集成 | 抽样 | 同日 timeline：团结 2022.3.61t9 + ASE 1.9.6.2 + MCP 3.4.7 | 本次会话未重跑；新进程重开未做 |
| 远端 package artifact | 交付 | 已验证 | 下载 run 33625061100 后文件名清单校验 | tag/Release 未授权 |
| Windows/Linux | 平台 | 未覆盖 | 当前无目标主机 | 需目标平台后解除 |

## 严重程度总览

| 问题 ID | 证据状态 | 优先级 | 严重程度 | 领域 | 问题 | 核心证据 |
| --- | --- | --- | --- | --- | --- | --- |
| AUD-REL-001 | 已验证 | P1 | S2 | 发布 | 0.2.0 候选已入 main 且 artifact 可校验，但无 tag/Release | `git tag` 仅 v0.1.0；pyproject 0.2.0；README 声明未发布 |
| AUD-FLOW-001 | 已验证 | P1 | S2 | 闭环 | EditorGraphSpec v2 创建缺少新进程重开证据 | REG-0037；timeline 明确未执行新进程 |
| AUD-FE-001 | 已验证 | P1 | S2 | 入口 | `create --backend editor` 的 `reloaded=true` 只覆盖暂存图，不覆盖提交后目标图 | `editor_create.cs.txt` LoadFromDisk(temporary)；Python 原样返回 |
| AUD-SIZE-001 | 已验证 | P2 | S3 | 规模 | 两份 Unity 执行器以 `.txt` 绕过 LOC 硬上限 | `asecli_material_gui.cs.txt` 536 行、`editor_create.cs.txt` 408 行 |
| AUD-GOV-001 | 已验证 | P2 | S3 | 治理 | `--strict` 仍有 31 项 kickoff/追溯/fitness 历史项，不能当发布阻断器 | kickoff 2、traceability 25、fitness 4 |

## 项目架构

### 当前结构

- 模块化单体：`cli` 组合 `core` / `schema` / `checks` / `bridge`；`skills/asecli` 为 Agent 接口；CI 与供应链为交付层。
- 生产运行时依赖为 0。公共写路径默认 dry-run，`create`/`recompile` 立即产生副作用。MCP 默认 loopback。

### 关键链路

| 链路 | 入口 | 核心模块 | 数据/状态流 | 外部依赖 | 结论 |
| --- | --- | --- | --- | --- | --- |
| 解析/校验 | parse/validate/graph-audit | core → checks → cli | 文件 → AseFile → issue JSON | 文件系统 | 已闭环 |
| 图修改 | set/add/connect/disconnect/remove/layout | cli → core/schema/checks | 读 → 写前校验 → atomic write + `.bak` | 文件系统 | 已闭环 |
| 文本创建 | create --from | cli/create_command | 模板壳 + donor 图 → 属性契约 → 新文件 | 文件系统 | 已闭环 |
| Editor 创建 | create --backend editor | bridge/editor_create | spec → 固定 C# 事务 → 暂存 Save/Load → MoveAsset | loopback MCP、ASE | 部分闭环 |
| 重编译 | recompile | bridge/recompile | 前哈希 → execute_code → saved/changed | loopback MCP | 已闭环（本次未重跑，沿用同日证据） |
| Inspector | custom-gui/gui-support | core + bridge GUI | 元数据/固定安装/呈现契约 | 目标工程 Assets | 已闭环（视觉沿用同日） |
| 发布候选 | CI package | uv/Hatchling | 双构建 → SHA256SUMS → SPDX | GitHub Actions | 本地/artifact 闭环；Release 未做 |

### 模块边界与隔离

| 模块 | 独立文件/目录 | 公共接口 | 独立测试 | 跨模块依赖 | 修改爆炸半径 | 结论 |
| --- | --- | --- | --- | --- | --- | --- |
| core | 是 | `core/__init__.py` | roundtrip/mutate/layout/property | 标准库 | 高 | 属性呈现已收口到公开 API |
| schema | 是 | `schema_for` | schema samples/add | 标准库 | 高 | 未知版本失败关闭 |
| checks | 是 | `validate_file` | graph safety/usage | core | 中 | fitness 仍报对 core 私有导入 |
| bridge | 是 | recompile/create/gui_support/McpClient | mcp/editor/gui tests | 标准库 | 高 | `safety_checks=false` 仅固定 nonce 事务 |
| cli | 是 | 15 个子命令 | CLI contract | 四核心模块 | 高 | 单行 JSON 退出码闭环 |
| Skill | 是 | SKILL.md | REG-0010 | 文档契约 | 中 | 与命令目录一致 |

## 技术路径与交付形态

- 技术路径：Python 3.10+ 标准库、argparse、Hatchling、uv；MCP streamable HTTP/SSE；Tuanjie/Unity 作为受控执行器。
- 实现/壳形态：无 UI 的本地 CLI + Agent Skill。
- 构建与交付：`uv.lock` 与 Action SHA 固定；`SOURCE_DATE_EPOCH=1788220800` 双构建；禁止自动发布。

| 交付物 | 格式/载体 | 生成方式 | 安装/部署 | 签名/发布证据 | 结论 |
| --- | --- | --- | --- | --- | --- |
| AseCLI 0.2.0 wheel | py3-none-any.whl | CI 双构建复制 | uv tool / 隔离 venv | SHA256 `52b66d2a…fab0`；未签名、未 Release | artifact 已验证 |
| source distribution | tar.gz | 同一固定环境 | 源码安装 | SHA256 `53a63dbc…67a6` | artifact 已验证 |
| SPDX SBOM | SPDX JSON | `tools/generate_sbom.py` | 随 artifact | 供应链检查同目录 | 已验证生成 |
| v0.1.0 正式版 | 私有 GitHub Release | REL-0002 | gh release download | 已发布且不可变 | 已验证；与 main 契约分叉 |

## 平台支持

| 平台/版本 | CPU/运行环境 | 已声明 | 可构建 | 已测试 | 已发布 | 证据/限制 |
| --- | --- | --- | --- | --- | --- | --- |
| macOS / Python 3.10 | 本机 CPython（uv） | 是 | 是 | 是 | 否 | 本次全量 pytest 在默认解释器；CI 亦跑 3.10 |
| GitHub ubuntu / Python 3.10+3.12 | X64 | 是 | 是 | 是 | 否 | run 33625061100 success |
| Tuanjie 2022.3.61t9 + ASE 1.9.6.2 | arm64 + MCP 3.4.7 | 是 | 不适用 | 同日是 | 否 | 不代表其他 Editor/MCP；新进程未跑 |
| Windows/Linux 桌面 | Python >=3.10 | 隐含 | 未验证 | 未验证 | 否 | 需目标主机 |

## 上帝文件与模块隔离

### 文件行数门禁

- 门禁：`.project-architect.json` 的 `loc_thresholds` 声明 source 250/400、test 400/600、config 160/200。实际 `check_project_architecture.py` 读取的是 `thresholds` 键，缺省时回落到技能默认值（source 同样 250/400）。扫描 `src` 下 `.py`，未截断。
- 扫描范围 / 排除范围：`src/asecli` Python；测试目录与 `.txt` 资源不计入。本次 LOC warnings=0、errors=0。

| 文件 | 行数 | 门禁结果 | 核心链路 | 建议 | 问题 ID |
| --- | --- | --- | --- | --- | --- |
| src/asecli/core/custom_gui.py | 250 | 正常（等于预警线） | 是 | 继续按公开 inspect/apply API 扩展，避免再涨 | 不适用 |
| src/asecli/cli/commands.py | 248 | 正常 | 是 | 保持写盘组合根 | 不适用 |
| src/asecli/bridge/resources/asecli_material_gui.cs.txt | 536 | 未计入（扩展名 .txt） | 是 | 纳入门禁或拆分绘制职责 | AUD-SIZE-001 |
| src/asecli/bridge/resources/editor_create.cs.txt | 408 | 未计入（扩展名 .txt） | 是 | 超过 source 400；保持事务单一文件但应显式豁免 | AUD-SIZE-001 |
| tests/test_custom_gui.py | 584 | 未计入（tests 不在 source_roots） | 否 | 接近 test 600；后续拆文件 | 不适用 |

### 上帝文件候选

| 文件或逻辑类型族 | 规模/职责 | 扇入/扇出或共享状态 | 修改/回归证据 | 结论 | 拆分边界 |
| --- | --- | --- | --- | --- | --- |
| asecli_material_gui.cs.txt | 536 行：折叠、Tooltip、说明条、旧标记兼容 | Inspector 运行时单例状态 | REG-0030/0036 与同日视觉 | 候选 | 呈现契约 vs 旧 drawer 兼容 |
| editor_create.cs.txt | 408 行：创建、暂存、manifest、回滚 | 无共享可变状态；nonce 隔离 | REG-0027/0038 | 候选 | 保持单事务文件，配置豁免 |
| test_custom_gui.py | 584 行多契约 | 无生产扇出 | REG-0022/0032 | 测试聚合，非生产上帝文件 | 按版本矩阵/spec 拆文件 |

### 模块隔离风险

| 问题 ID | 功能 | 当前分布 | 耦合点 | 连带回归 | 建议边界 |
| --- | --- | --- | --- | --- | --- |
| AUD-GOV-001 | usage/gui_support 导入 core 实现模块 | checks/bridge → core.model/custom_gui/local_vars | fitness 视非 `__init__.py` 为私有 | 误报阻断 `--strict` | 扩大 `module_public_patterns` 或改公开再导出 |

## 项目成熟度

等级：`L0 缺失`、`L1 临时`、`L2 可重复`、`L3 标准化`、`L4 可度量`。

| 维度 | 等级 | 当前机制 | 证据 | 主要缺口 |
| --- | --- | --- | --- | --- |
| 需求与追溯 | L3 | FR/CR/ADR/BUG/TASK/REG/REL | timeline、36 条 REG、traceability.csv | `--strict` 25 条双向链接失败 |
| 架构与模块 | L3 | 模块地图、公开 API、LOC | module-map；LOC 零超限 | CodeGraph 未建；fitness 4 项 |
| 构建与自动化测试 | L3 | 双 Python CI、可复现 build | 223 passed；run 33625061100 | 本地未重复跑 3.10 与 3.12 两次 |
| 目标编辑器 E2E | L2 | 隔离工程 + bridge marker | 同日 v2 创建/Inspector | 新进程重开、本次未重跑 |
| 发布与回滚 | L2 | REL、SBOM、artifact 哈希 | v0.1.0 已发布；0.2.0 artifact 可校验 | 0.2.0 无 tag；未签名 |
| 安全与供应链 | L3 | loopback、脱敏、Action SHA、SPDX | mcp_security 与 supply_chain 测试 | 在线 SCA 未跑 |
| UI/无障碍 | 不适用 | 无产品 UI；材质 Inspector 属 Unity | 同日 Tooltip/说明条确认 | 不按 Web a11y 评级 |

- 总体成熟度与依据：L2。开发与 CI 已标准化，但 0.2.0 发布与 Editor 新进程证据仍停在可重复、未完成交付。

## 回归验证机制

| 检查项 | 当前机制 | 自动化/CI | 覆盖 | 证据 | 缺口 |
| --- | --- | --- | --- | --- | --- |
| 核心模块与 CLI | pytest + REG catalog | 本地与 GitHub verify | 解析、写入、GUI、创建、安全、性能 | 223 passed / 36 REG | 3 条 bridge skipped |
| 目标编辑器 E2E | pytest -m bridge | 人工启动 Editor | create/recompile/GUI | 同日 timeline；本次未跑 | 新进程重开 |
| 构建与供应链 | 双 build + SHA256SUMS + SPDX | GitHub package | wheel/sdist/lock/Action | 清单文件名无 `dist/` 前缀 | 0.2.0 Release |
| 失败留痕与回滚 | BUG/REG/timeline + `.bak` + wheel 回滚 | 自动 + 人工 REL | BUG-0001～0018 | bug-register | 0.2.0 回滚演练未随 Release |

## OpenSpec 规范管理

| 状态 | 结论 | 证据 |
| --- | --- | --- |
| 工具、项目配置、实际使用、规范一致性、strict 校验 | 未发现证据 | 项目以架构总纲、CR/ADR/traceability 为事实源。本次只读，未初始化 OpenSpec。 |

## CodeGraph 使用情况

| 状态 | 结论 | 证据 |
| --- | --- | --- |
| 安装、初始化、索引新鲜度、实际使用、更新机制 | 降级 | 仓库无 `.codegraph/`。本次用 project-architect collect、源码审阅和 `rg` 替代，未擅自 init。 |

## 文档增量与变更留档

| 变更类型 | 载体/机制 | 增量历史 | 关联键 | 字段完整性 | 抽样证据与缺口 |
| --- | --- | --- | --- | --- | --- |
| 需求变更 | change-register + 架构总纲 | 有 | CR-0010～CR-0012、FR-0009～0011 | 部分 | 语义完整；`--strict` 反向链接不足 |
| 技术变更 | technical-route + module-map + ADR | 有 | ADR-0014/0015 | 完整 | 属性契约与 GUI 协议已登记 |
| 文件修改记录 | Git + timeline | 有 | TASK-0030～0032、BUG-0015～0018 | 完整 | HEAD 8aaff19 已推送 |
| 缺陷/回归 | bug-register + regression-catalog | 有 | BUG-0017/0018、REG-0039/0040 | 完整 | 本次已复验 BUG-0018 artifact |

## 功能模块闭环度

- 模块统计：发现数：13；已审计数：13；未覆盖数：0
- 清单校准：自动发现器对 `src/asecli` 返回空列表。复用 2026-09-01 基线 9 个 FM ID，并人工新增 `FM-A4E91C02B7`、`FM-3E8F1D90C2`、`FM-9B2C4E71A8`、`FM-5D0A8C33F1`。未排除模块。

| 模块 ID | 模块/能力 | 需求/入口 | 主路径/关键链路 | 数据/状态闭环 | 异常/恢复 | 日志/可观测性 | 回归/验收 | 发布证据 | 结论 | 问题 ID |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FM-0E60A4DD1B | parse-serialize | FR-0001 / parse | 文件 → AseFile → serialize | HLIT 冒烟与 fixture 回读 | PARSE/NOT_FOUND JSON | 单行节点摘要 | REG-0001/0011 | 0.2.0 wheel 含模块 | 已闭环 | 不适用 |
| FM-9040886B90 | graph-mutation | FR-0002 / set/add/connect/remove | graph_ops → 写前 validate → atomic write | 结构不变量与 `.bak` | 重复 ID/外部引用失败关闭 | written/path/code | REG-0013/0015 | wheel 含模块 | 已闭环 | 不适用 |
| FM-8ADC52C2A4 | schema-library | FR-0002 / add-node | schema_for → version gate | 固定字段完整 | 未知类型拒绝且不写盘 | SCHEMA_* 错误码 | REG-0009/0013 | 隔离 Editor 历史重存 | 已闭环 | 不适用 |
| FM-C73F236CD5 | validation-checksum | FR-0003 / validate/fix-checksum/graph-audit | graph/checksum/usage | error_count 与 exit 2 | dry-run、`.bak` | issue JSON | REG-0003/0004/0018 | wheel validate 冒烟 | 已闭环 | 不适用 |
| FM-F03DFA9A41 | layout | FR-0008 / layout | DAG 分层只改 x/y | 连线集合不变 | 环图确定性降级 | moved/written | REG-0012 | wheel 含模块 | 已闭环 | 不适用 |
| FM-3537DE9938 | create-from-template | FR-0005 / create text | 模板壳 + donor → 属性契约 | 单一 shader 壳回读 | 混合 donor 拒绝写盘 | created/presentation | REG-0006/0014/0037 | 文本路径自动通过 | 已闭环 | 不适用 |
| FM-DF0669A019 | recompile-bridge | FR-0004 / recompile | hash → MCP → saved/changed | tool result 与哈希 | BRIDGE_ERROR exit 3 | 脱敏 JSON | REG-0005/0016/0017 | 同日 MCP 证据 | 已闭环 | 不适用 |
| FM-1DB3E4EA8B | cli-contract | FR-0007 / 15 命令 | argparse → JSON envelope | 成功/失败退出码 | usage 走 JSON | stdout 单行 | REG-0007 | `asecli 0.2.0` 冒烟 | 已闭环 | 不适用 |
| FM-25E63BD4F6 | agent-skill | FR-0006 / SKILL.md | Agent → CLI → validate | 逐步回读、显式写入 | 失败即停 | 依赖 CLI JSON | REG-0010 | Skill 随仓库 | 已闭环 | 不适用 |
| FM-A4E91C02B7 | custom-gui-presentation | FR-0009 CR-0012 / custom-gui | inspect → 双向 reconciliation → spec 写入 | 图/编译区属性名与中文说明 | managed 检查失败关闭 | property_presentation JSON | REG-0022/0037 | 同日 Inspector | 已闭环 | 不适用 |
| FM-3E8F1D90C2 | gui-support | FR-0009 CR-0011 / gui-support | 固定路径检查/安装 | 冲突与 symlink 拒绝 | 契约失效写前拒绝 | inline_help_presentation | REG-0030/0036 | 同日安装与视觉 | 已闭环 | 不适用 |
| FM-9B2C4E71A8 | comment-group | FR-0010 / comment-group | 原生 Comment 包围 | 不移成员、不改连线 | dry-run、CHKSM | bounds JSON | REG-0024 | 离线测试；真实边距待目标图 | 已闭环 | 不适用 |
| FM-5D0A8C33F1 | editor-create | FR-0011 / create editor | spec v2 → 固定 C# 事务 → 独立 recompile | 暂存 Save/Load + MoveAsset | 失败保留无法证明产物 | saved/reloaded/committed | REG-0029/0038 | 同日创建通过；新进程未做 | 部分闭环 | AUD-FLOW-001 |

### 前端功能入口闭环

- 入口统计：发现数：15；已审计数：15；未覆盖数：0
- 清单校准：无人工新增或排除 FE。自动 15 个 argparse 子命令全部入表。相对基线新增 graph-audit、custom-gui、gui-support、comment-group。

| 入口 ID | 页面/入口与类型 | 条件/权限 | 目标/handler | 状态覆盖 | 返回/恢复 | 测试/运行证据 | 结论 | 问题 ID |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FE-5FE7C39BCC | parse CLI | 文件可读 | cmd_parse | 成功、not-found | 只读重试 | 本次 HLIT 冒烟 + CLI tests | 已闭环 | 不适用 |
| FE-5F33E87610 | set-field CLI | 可写；managed 契约 | cmd_set_field | dry-run/write/呈现失败关闭 | `.bak` | graph-safety + property tests | 已闭环 | 不适用 |
| FE-37BA87FA15 | add-node CLI | schema/version 有效 | cmd_add_node | 跨版本拒绝 | dry-run、`.bak` | schema-add | 已闭环 | 不适用 |
| FE-C3162CA2E1 | connect CLI | 两端存在 | cmd_connect | 重复输入拒绝 | `.bak` | graph-safety | 已闭环 | 不适用 |
| FE-AAF53AF86F | disconnect CLI | 连线存在 | cmd_disconnect | not-found | `.bak` | CLI/graph tests | 已闭环 | 不适用 |
| FE-0018A7D5D8 | remove-node CLI | 节点存在 | cmd_remove_node | 外部引用默认拒删 | `.bak` | usage tests | 已闭环 | 不适用 |
| FE-50D4B549C6 | graph-audit CLI | 文件可读 | cmd_graph_audit | unused vs 外部消费者 | 只读 | usage audit tests | 已闭环 | 不适用 |
| FE-BBB0F9830B | validate CLI | 文件可读 | cmd_validate | error exit 2 | 只读 | 本次 HLIT 0 errors | 已闭环 | 不适用 |
| FE-369C790BD8 | fix-checksum CLI | `--write` 才写 | cmd_fix_checksum | preview/write | `.bak` | CLI checksum tests | 已闭环 | 不适用 |
| FE-C71A570BA7 | layout CLI | 图可解析 | cmd_layout | 只改坐标 | `.bak` | layout + perf | 已闭环 | 不适用 |
| FE-4E1B79DEE4 | custom-gui CLI | ASECLI editor | cmd_custom_gui | spec 原子写/违规拒绝 | `.bak` | test_custom_gui / presentation | 已闭环 | 不适用 |
| FE-1E3A6EB7E7 | gui-support CLI | Unity 工程根 | cmd_gui_support | missing 才安装、冲突拒绝 | dry-run 默认 | test_gui_support | 已闭环 | 不适用 |
| FE-222ADDDF1D | comment-group CLI | 可选 MCP bounds | cmd_comment_group | 离线创建/check-bounds | dry-run | test_commentary | 已闭环 | 不适用 |
| FE-B537BBBC81 | create CLI | text 立即写；editor 禁 --force | cmd_create | 文本契约失败零落盘；editor 事务 | 保留无法证明目标 | test_create / editor_create_* | 部分闭环 | AUD-FE-001 |
| FE-3F4DBCA0D3 | recompile CLI | loopback MCP | cmd_recompile | saved/changed/BRIDGE_ERROR | 超时视为未知 | mock + 同日真实 MCP | 已闭环 | 不适用 |

## 交互流程与 UI

### Product Design 参与情况

| 检查项 | 结论 | 证据/限制 |
| --- | --- | --- |
| 历史参与证据、本次调用、当前截图、视觉结论等级 | 未发现证据 / 不适用 | 产品无自有 GUI。材质 Inspector 属于 Unity，沿用用户同日截图确认，不按 Product Design 流程审计。 |

### 关键流程证据

| 步骤 | 用户目标/操作 | 截图或运行证据 | 健康度 | UX/可访问性问题 | 证据限制 |
| --- | --- | --- | --- | --- | --- |
| 01 | CLI 读取与校验 fixture | `asecli parse/validate tests/fixtures/HLIT.shader` 成功 | 良好 | 机器 JSON，无交互 UI | 仅 19109 样本 |
| 02 | 远端 0.2.0 包完整性 | SHA256SUMS 两条 OK | 良好 | 不适用 | 未安装到隔离 venv 再 parse |
| 03 | Editor v2 新进程重开 | 无本次运行 | 有风险 | 不适用 | 见 AUD-FLOW-001 |

### UI 检查

| 页面/区域 | 层级与清晰度 | 一致性/状态 | 响应式 | 键盘/焦点/语义 | 问题 ID |
| --- | --- | --- | --- | --- | --- |
| 无自有 UI | 不适用 | 不适用 | 不适用 | 不适用 | 不适用 |

## 专项工程审计

| 专项领域 | 状态 | 核心证据 | 主要风险/缺口 | 问题 ID |
| --- | --- | --- | --- | --- |
| 安全与隐私 | 已验证 | loopback 默认、argv token 拒绝、禁重定向、脱敏、symlink 拒绝 | `execute_code` + `safety_checks=false` 仍依赖固定 C# 与信任会话 | 不适用 |
| 性能与资源 | 已验证 | REG-0011 千节点门禁仍在全量 pytest 中 | 未做发布包体积/冷启动度量 | 不适用 |
| 可观测性与运维 | 推断 | 单行 JSON 错误码；无 metrics/SLO | Agent 可解析但无运行指标 | 不适用 |
| 依赖、供应链与许可证 | 已验证 | 运行时依赖 0；lock；Action SHA；SPDX；专有许可 | 在线漏洞库未跑 | 不适用 |
| API、数据兼容与迁移 | 已验证 | EditorGraphSpec v2 拒绝 v1 CLI；0.2.0 版本已升 | 正式 Release 仍停在 0.1.0 | AUD-REL-001 |
| 无障碍与国际化 | 不适用 | CLI 无 GUI；属性契约强制中文显示名/说明 | 不按 WCAG 评级 | 不适用 |
| 构建可复现与产物完整性 | 已验证 | 双构建 CI；下载 artifact 清单可直接校验 | 未签名/未公证；0.2.0 未发布 | AUD-REL-001 |

## 增量审计对比

- 基线报告：`docs/05-audits/2026-09-01-132548-project-audit-report.md`

| 分类 | 问题 ID | 基线 -> 当前 | 证据/说明 |
| --- | --- | --- | --- |
| 已解决 | 基线 14 个 AUD-* | 开放 0 -> 仍关闭 | 无回归打开；HEAD 干净 |
| 已解决 | AA-COR-001 / AA-FAIL-002 | 对抗性 P1 -> 代码关闭 | `inspect_property_presentation` 双向对账；`require_managed_property_presentation` 失败关闭 |
| 已解决 | BUG-0017 / BUG-0018 | 远端 package 失败 -> HEAD CI 绿 | run 33625061100；SHA256SUMS 无 `dist/` 前缀且校验通过 |
| 新增 | AUD-REL-001 | 无 -> 开放 | 0.2.0 候选与 v0.1.0 正式版分叉 |
| 新增 | AUD-FLOW-001 / AUD-FE-001 | 无 -> 开放 | 新进程重开与 `reloaded` 语义 |
| 新增 | AUD-SIZE-001 | 无 -> 开放 | GUI/创建 C# 资源绕过 LOC |
| 未变化 | AUD-GOV-001 所描述的 31 项 PA strict | 历史债务仍在 | kickoff 2 + trace 25 + fitness 4 |
| 改善 | CLI 入口 | 11 -> 15 | graph-audit/custom-gui/gui-support/comment-group 已对账 |
| 不适用 | 远程 GitHub 完全未跑 | 已跑通 verify/package | 仅缺 0.2.0 Release |

## 阻塞项

| 问题 ID | 阻塞内容 | 影响范围 | 证据 | 解除条件 |
| --- | --- | --- | --- | --- |
| AUD-REL-001 | 不能把 0.2.0 标为已交付正式版 | 试用安装、契约回滚、对外说明 | 仅 tag `v0.1.0`；README 写明候选 | 单独书面授权后打 tag、写 REL、上传不可变 artifact |
| AUD-FLOW-001 | 不能宣称 v2 创建经新进程重载 | FR-0011 验收 | REG-0037 状态 | 新 Editor 进程打开目标，manifest 与呈现仍 valid |

## 潜在风险

| 问题 ID | 风险 | 触发条件 | 影响 | 概率 | 应对建议 |
| --- | --- | --- | --- | --- | --- |
| AUD-RISK-001 | MCP 超时后 Editor 仍提交成功 | 重试 create 同一路径 | 目标已存在或双产物 | 中 | 先查目标与 `ASECLI-Temp-*`，禁止盲目重试 |
| AUD-RISK-002 | `safety_checks=false` 被复用到非事务入口 | 改 MCP 调用参数 | 扩大 execute_code 攻击面 | 低 | 保持仅 nonce 执行器；回归锁定参数 |
| AUD-RISK-003 | 真实 ASE 画布精排/贝塞尔与离线 layout 不一致 | 只信 CLI layout | 视觉未达规范 | 中 | 目标图人工验收，不把 pytest 当画布通过 |

## 问题详情

### AUD-REL-001 0.2.0 候选未成为不可变正式发布

- 状态：开放
- 证据状态：已验证
- 严重程度：S2
- 优先级：P1
- 影响范围：安装渠道、CLI 契约消费者、回滚说明
- 证据：`pyproject.toml` version `0.2.0`；`git tag` 仅 `v0.1.0`；`docs/04-delivery/releases/` 无 REL-0003；README 写明 main 中 0.2.0 尚未打 tag。GitHub run 33625061100 artifact 已可校验，但不能替代 Release。
- 根因判断：项目禁止自动发布，0.2.0 含破坏性契约（EditorGraphSpec v2、属性呈现硬门禁），发布被单独授权门禁挡住。
- 优化做法：在用户授权后按 REL 协议打 `v0.2.0`、上传与 SHA256SUMS 一致的不可变资产，并写明相对 v0.1.0 的回滚。
- 技术路径：复用现有 CI artifact 与 REL-0002 流程，不改构建系统。
- 验收标准：存在 `v0.2.0` tag 与私有 Release；下载后 `shasum -a 256 -c SHA256SUMS` 通过；`asecli --version` 为 0.2.0。
- 验证方式：`git tag --list`、`gh release view v0.2.0`、隔离 `uv tool install`。
- 回滚/降级：保留 v0.1.0 不可变；未授权则继续只分发 v0.1.0。

### AUD-FLOW-001 Editor v2 创建缺少新进程重开闭环

- 状态：开放
- 证据状态：已验证
- 严重程度：S2
- 优先级：P1
- 影响范围：FM-5D0A8C33F1、FR-0011、REG-0037
- 证据：timeline 与 REG-0037 写明当前团结实例完成创建、暂存重载、提交、独立 recompile 与 Inspector，但“新进程重开按用户约束未执行”。本次会话未启动 Editor。
- 根因判断：为避免 MCP 插件重连吞回执，提交后不再加载目标图；完整重载改独立 `recompile`。新进程打开是另一层证据，尚未收集。
- 优化做法：在隔离工程关闭编辑器后用新进程打开目标 shader，核对模板 GUID、节点/连接 manifest 与 `property_presentation.valid`。
- 技术路径：现有 `pytest -m bridge tests/test_editor_create_e2e.py` 与手工重开清单。
- 验收标准：新进程 Load 后节点/属性/连线与创建 manifest 一致，呈现契约 valid，无暂存残留。
- 验证方式：隔离 Tuanjie + ASE 1.9.6.2；记录脱敏前后哈希。
- 回滚/降级：未完成前不得把 v2 创建写成“可重开已证明”。

### AUD-FE-001 create Editor 后端把暂存重载报成 reloaded=true

- 状态：开放
- 证据状态：已验证
- 严重程度：S2
- 优先级：P1
- 影响范围：FE-B537BBBC81、Agent 编排、独立 recompile 是否被跳过
- 证据：`editor_create.cs.txt` 对 `temporaryAssetPath` 做 `SaveToDisk`/`LoadFromDisk` 后设置 `reloaded`；提交是 `MoveAsset`。Python `_validate_result` 要求 `reloaded is True` 并原样返回。README 已说明提交后不重复加载目标图。
- 根因判断：字段名沿用旧“保存并重载”语义，实现改为只验证暂存图，避免插件重连。
- 优化做法：JSON 拆分 `staging_reloaded` 与 `target_reloaded`，或在 `reloaded=true` 同时明确 `target_graph_reloaded=false` 并要求后续 `recompile`。
- 技术路径：改 bridge 契约测试与 README/SKILL；不改事务成功条件。
- 验收标准：Agent 仅凭 JSON 能区分暂存重载与目标图重载；现有成功路径不报假的目标重载。
- 验证方式：`tests/test_editor_create_bridge.py` 与 CLI 快照字段。
- 回滚/降级：可先只加字段保留 `reloaded` 兼容。

### AUD-SIZE-001 Unity 执行器源码以 .txt 绕过 LOC 上限

- 状态：开放
- 证据状态：已验证
- 严重程度：S3
- 优先级：P2
- 影响范围：GUI 安装与 Editor 创建事务可维护性
- 证据：`wc -l` 得 536 与 408 行；LOC 扫描扩展名含 `.cs` 不含 `.txt`，故 warnings=0。source limit 为 400。
- 根因判断：C# 以包内文本资源嵌入，有意避免单独编译；门禁未覆盖该形态。
- 优化做法：在 `.project-architect.json` 显式豁免并记录理由，或拆分 GUI 绘制与兼容层；创建执行器保持单文件但登记超限。
- 技术路径：只改门禁配置或拆资源，不改运行时协议。
- 验收标准：超限文件要么降至 limit 下，要么在配置中具名豁免且审计不再误报通过。
- 验证方式：`check_project_architecture.py` 与 `wc -l`。
- 回滚/降级：维持现状并接受资源文件不计入 LOC。

### AUD-GOV-001 Project Architect --strict 仍有 31 项历史项

- 状态：开放
- 证据状态：已验证
- 严重程度：S3
- 优先级：P2
- 影响范围：治理门禁可信度、任务卡与模块反向链接
- 证据：`--check-docs --check-kickoff --check-traceability --check-fitness --strict` 退出码 1。kickoff：TASK-0026/0028 verification 缺 REG。traceability 25 条反向链接。fitness：`checks/usage.py` 与 `bridge/gui_support.py` 导入 core 实现文件。
- 根因判断：追溯表正向登记快于模块地图反向字段；fitness 只把 `__init__.py` 当公开 API，与 module-map 允许 checks→core 不一致。
- 优化做法：补 TASK REG 字段与 module-map 关联 ID；把 `core/__init__.py` 再导出或扩展 `module_public_patterns`。
- 技术路径：只改治理文件与公开导出，不改 CLI 行为。
- 验收标准：同一 `--strict` 命令退出 0，或把不可修复项写成已接受偏差。
- 验证方式：`check_project_architecture.py --strict --format json`。
- 回滚/降级：继续把 31 项当历史噪声，不用 `--strict` 做 CI 阻断。

## 验证记录

| 命令/检查 | 目的 | 结果摘要 | 是否通过 |
| --- | --- | --- | --- |
| `uv run --frozen pytest -q` | 全量自动回归 | 223 passed, 3 skipped | 是 |
| `python tools/check_ci_governance.py` | CI 治理 | findings 空 | 是 |
| `python tools/check_regression_catalog.py` | REG 可收集 | checked 36, failures 空 | 是 |
| `check_project_architecture.py`（仅 LOC/默认） | 文件行数 | warnings 0 errors 0 | 是 |
| `check_project_architecture.py --strict` 全开 | 治理严格门禁 | kickoff 2 + trace 25 + fitness 4 | 否 |
| `asecli parse/validate tests/fixtures/HLIT.shader` | CLI 冒烟 | ok true；error_count 0 | 是 |
| 下载 run 33625061100 SHA256SUMS | 远端产物完整性 | 两条文件名哈希 OK | 是 |
| `pytest -m bridge` / 新进程重开 | 真实 Editor | 本次未运行 | 未运行 |

## 计划外发现

- `.project-architect.json` 使用 `loc_thresholds` 键，检查器合并的是 `thresholds`。当前默认值碰巧与声明一致，因此未另立问题。若以后只改 `loc_thresholds`，门禁不会生效。
- 证据采集器的 `historical_audits` 为空，尽管 `docs/05-audits/` 已有历史报告。增量对比改为人工指定基线。

## 遗留问题

- 0.2.0 正式发布等待书面授权。
- Editor v2 新进程重开与目标平台渲染未做。
- OpenSpec 与 CodeGraph 按只读审计未初始化。
- Windows/Linux 桌面未测。

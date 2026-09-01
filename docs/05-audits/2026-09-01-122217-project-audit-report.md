# 项目审计报告

## 元信息

- 项目路径：/Users/long/GitHub/ASECLI
- 项目类型：Python CLI + Agent Skill + Unity/Tuanjie MCP 桥接
- 审计时间：2026-09-01T12:22:17+08:00（Asia/Shanghai）
- 当前分支 / commit：main / 8883425b22244141af7475ea1a0e7042d99c0067
- 工作区状态：采证开始时 clean；审计结束时仅新增本报告与同时间戳优化任务书
- 审计范围：全部 51 个已发现项目文件；源码、测试、治理文档、CLI 入口、构建产物与本地运行链路
- 非目标：不修改业务代码、配置、依赖、CI、用户 Unity/Tuanjie 工程或远程状态；不初始化 OpenSpec/CodeGraph
- 请求模式 / 实际模式：标准 / 标准（目标编辑器运行子门禁未验证）
- 未覆盖范围：真实 Tuanjie/Unity 重编译、真实 shader 创建后打开、Agent 自然语言端到端、远程 Release、签名/SBOM/SCA；解除条件见 AUD-FLOW-001

## 审计模式与证据等级

| 项目 | 结果 | 证据/限制 |
| --- | --- | --- |
| 证据采集器 | 已运行 | schema 1.1；51 文件索引、47 文本读取；未截断；证据 JSON 位于系统临时目录，不纳入项目产物 |
| 静态证据 | 已验证 | 全部 Python 源码、pyproject、治理文档、测试、Skill、Git 历史；schemas.json 做结构与统计检查 |
| 自动化测试 | 已验证 | Python 3.12 与 3.10 均为 29 passed、1 skipped；跳过项为真实 MCP 桥接 |
| 运行与 UI | 部分 | parse、validate、add-node、connect、create、fix-checksum、错误分支与桥接 mock 已运行；无 UI；真实编辑器未运行 |
| 发布产物 | 部分 | sdist/wheel 两次构建字节一致，wheel 隔离安装可运行；无 REL、tag、远程 Release、签名或发布后验收 |

## 结论摘要

- 总体判断：工程骨架、文本 roundtrip、模块 LOC、测试速度和本地打包表现良好，但当前不应宣称核心 Agent 工作流可发布；8 个 S1 涉及 schema 写入、图结构安全、创建、JSON 契约、桥接失败语义和真实端到端证据。
- 最大阻塞：`add-node` 与 `create --graph-from` 已复现会生成不满足预期结构的文件，真实 Tuanjie/MCP 闭环仍无本次运行证据。
- 最大回归风险：现有 29 项测试全部通过，却未覆盖上述负路径；治理回归目录还引用 5 个不存在的测试文件，容易产生“门禁已通过”的假象。
- 第一优先优化方向：先修复写入链路的结构不变量与错误契约，再在隔离的真实 Tuanjie 工程完成 create/recompile/Agent E2E 验收。
- 问题统计：S0=0，S1=8，S2=4，S3=2；P0=0，P1=12，P2=2

## 项目简介与功能作用

- 项目简介：AseCLI 面向 AI Agent 和 Unity/Tuanjie 开发者，以本地 CLI 解析、修改、校验、布局和创建 Amplify Shader Editor 文件，并通过 MCP for Unity 触发重编译。
- 主要输入/输出与边界：输入是用户指定的 `.shader` 或 ShaderFunction 文本和 CLI 参数；输出是 JSON、修改后的文件、`.bak` 备份或 MCP 调用结果。文本链路可脱离 Unity，HLSL 再生成必须依赖运行中的目标编辑器。

| 功能/场景 | 目标用户 | 入口与输入 | 主要输出 | 实现状态 | 证据 |
| --- | --- | --- | --- | --- | --- |
| 解析与结构校验 | Agent/开发者 | `parse`、`validate` + ASE 文件 | 图摘要、问题列表 | 已实现但校验规则不完整 | wheel 隔离运行；AUD-FE-003 |
| 图修改与布局 | Agent | `set-field/add-node/connect/disconnect/remove-node/layout` | dry-run 或写回文件 | 部分，存在结构破坏路径 | 负路径复现；AUD-FE-001/AUD-FE-003 |
| 模板创建 | Agent | `create --from/--graph-from` | 新 shader | 基础复制可用，donor 图注入断链 | 双 Shader 声明复现；AUD-FE-002 |
| 编辑器重编译 | Agent/开发者 | `recompile` + MCP 会话 | HLSL 再生成结果 | 代码存在，真实链路未验证 | 1 bridge test skipped；AUD-FE-005/AUD-FLOW-001 |
| Agent 操作指南 | Codex/Claude Code/Codely | `skills/asecli/SKILL.md` | 三链路操作约定 | 文档存在，Agent E2E 未验收 | REG-0010 无运行证据；AUD-FLOW-001 |

## 审计覆盖率

| 对象 | 分类 | 覆盖状态 | 证据方式 | 未覆盖原因 |
| --- | --- | --- | --- | --- |
| 26 个 Python 文件 | 核心/测试/工具 | 已验证 | 全量静态读取、LOC、pytest、构建 | 无扫描截断 |
| 9 个 FM 能力模块 | 核心/支撑 | 已验证 | 人工 supplement 校准并逐模块闭环对账 | 自动发现器不识别 `src/asecli/<capability>`，已人工补齐 |
| 11 个 CLI FE 入口 | 核心 | 已验证 | 自动入口清单、源码、测试和定向复现 | 真实 recompile 运行未覆盖 |
| schema 数据库 | 核心数据 | 抽样 | 299 类型统计、版本统计、SaturateNode 构造验证 | 未逐项审阅 299 类型语义 |
| 真实目标编辑器 | 外部集成 | 未覆盖 | 环境变量为空，8080 无监听 | 运行会修改目标 shader，未在无明确目标时执行 |
| 发布链路 | 交付 | 抽样 | 本地可复现构建、wheel 隔离安装 | 无 CI/tag/REL/远程产物 |

## 严重程度总览

| 问题 ID | 证据状态 | 优先级 | 严重程度 | 领域 | 问题 | 核心证据 |
| --- | --- | --- | --- | --- | --- | --- |
| AUD-FE-001 | 已验证 | P1 | S1 | CLI/Schema | `add-node` 漏写通用 precision/preview 字段 | 生成 12 字段，schema 契约要求 14 字段 |
| AUD-DATA-001 | 已验证 | P1 | S1 | 数据兼容 | schema 版本 19109 未对输入图版本设门禁 | fixture 同时含 19100/19109；CLI 无版本检查 |
| AUD-FE-002 | 已验证 | P1 | S1 | CLI/Create | `create --graph-from` 注入 donor 整个文件前缀 | 输出含 2 个 `Shader` 声明 |
| AUD-FE-003 | 已验证 | P1 | S1 | 图结构/校验 | 写命令可提交无效图，validate 仍可能以退出码 0 成功 | 改 node ID 后 3 个悬空引用；重复输入连接未检出 |
| AUD-FE-004 | 已验证 | P1 | S1 | CLI 契约 | argparse 参数错误不输出 JSON | `asecli parse`：stdout 0 字节、stderr usage、exit 2 |
| AUD-FE-005 | 已验证 | P1 | S1 | MCP 桥接 | MCP `tools/call` 的 `isError` 被包装为 CLI 成功 | mock 返回 isError 后函数正常返回 |
| AUD-FLOW-001 | 未验证 | P1 | S1 | 功能闭环 | create/recompile/Agent E2E 无真实目标编辑器和发布证据 | 29 passed、1 bridge skipped；无 8080 监听 |
| AUD-GOV-001 | 已验证 | P1 | S1 | 治理/追溯 | 治理状态与实现漂移，回归目录含不可执行命令 | 5 个登记测试文件不存在；任务卡仍大量“未开始” |
| AUD-FE-006 | 已验证 | P1 | S2 | CLI 安全默认 | `fix-checksum` 无 `--write` 且直接写盘，违背全局 dry-run 声明 | 临时文件哈希变化并生成备份 |
| AUD-PERF-001 | 已验证 | P1 | S2 | 性能 | “约 1200 节点”测试实际仅 207 节点且含恒真断言 | tests/test_perf.py:13-25 |
| AUD-OPS-001 | 已验证 | P1 | S2 | CI/发布 | 质量门禁只在本地，缺 CI、REL、远程产物与回滚演练 | 无 `.github` 工作流、tag、release 记录 |
| AUD-SEC-001 | 推断 | P1 | S2 | 安全 | Agent 可将 instance token 发往任意 `--mcp-url`，缺信任边界和脱敏策略 | main.py 与 mcp_client.py 参数流 |
| AUD-SUPPLY-001 | 已验证 | P2 | S3 | 供应链 | 无 SCA/SBOM/许可证决策记录 | 扫描工具未安装；LICENSE 缺失；生产依赖为 0 |
| AUD-ARCH-001 | 已验证 | P2 | S3 | 模块契约 | CLI 通过公共 facade 导入私有 `_parse_node_line` | core/__init__.py:3 与 cli/commands.py:15 |

## 项目架构

### 当前结构

- 采用单仓库、Python 3.10+、模块化单体 CLI；`cli` 是组合根，依赖 `core/schema/checks/bridge`，Agent Skill 作为文档交付物。
- `core/model.py` 拥有 ASE 文本模型和 roundtrip；`graph_ops.py/layout.py` 负责变更；`checks` 负责结构与 checksum；`bridge` 负责 MCP；`schema/data` 是版本化运行时数据。
- `.project-architect.json` 将 `src/asecli` 下一级目录视为模块，严格 fitness 检查无循环、私有跨模块导入或扇出超限；语义级私有符号泄漏仍见 AUD-ARCH-001。

### 关键链路

| 链路 | 入口 | 核心模块 | 数据/状态流 | 外部依赖 | 结论 |
| --- | --- | --- | --- | --- | --- |
| 解析/校验 | parse/validate | core → checks → cli | 文件文本 → AseFile/AseGraph → JSON | 文件系统 | 解析通过；校验不变量不完整 |
| 图修改 | set/add/connect/remove/layout | cli → core/schema/checks | 读文件 → 内存图 → atomic write + `.bak` | 文件系统 | 存在可提交无效结构的路径 |
| 创建 | create | cli/commands | 模板壳 + donor 图 → 新文件 | 文件系统 | 基础改名有测试，graph-from 断链 |
| 重编译 | recompile | cli → bridge → MCP | shader path → execute_code → 编辑器写回 | MCP for Unity/Tuanjie | 静态实现存在，失败语义与真实运行未闭环 |

### 模块边界与隔离

| 模块 | 独立文件/目录 | 公共接口 | 独立测试 | 跨模块依赖 | 修改爆炸半径 | 结论 |
| --- | --- | --- | --- | --- | --- | --- |
| core | 是 | `core/__init__.py` | roundtrip/mutate/layout/perf | 标准库 | 高 | 主模型集中但 185 行，未超限；私有解析函数被导出 |
| schema | 是 | `schema_for/load/allows_mutation` | schema_samples | 标准库 | 高 | 版本与字段组装契约断链 |
| checks | 是 | `checks/__init__.py` | 由契约/综合测试间接覆盖 | core | 中 | checksum 可用；图不变量覆盖不足 |
| bridge | 是 | `bridge/__init__.py` | 1 个环境条件测试 | 标准库 | 高 | 无真实本次证据，错误结果未升级 |
| cli | 是 | console script | cli_contract/audit_fixes | 四核心模块 | 高 | 组合根合理；负路径契约不足 |
| Skill | 是 | SKILL.md | 人工 REG-0010 | CLI 文档契约 | 中 | 未执行 Agent E2E |

## 技术路径与交付形态

- 技术路径：Python 标准库 + argparse + Hatchling + uv；本地文件存储；MCP streamable HTTP/SSE；无生产第三方 Python 依赖。
- 实现/壳形态：无 UI 的本地 CLI 与 Agent Skill，外接 Unity/Tuanjie 编辑器。
- 构建与交付：`uv build` 生成 sdist/wheel；`uv tool install .` 安装；当前没有 tag、REL、签名、公证、SBOM 或发布后验收。

| 交付物 | 格式/载体 | 生成方式 | 安装/部署 | 签名/发布证据 | 结论 |
| --- | --- | --- | --- | --- | --- |
| asecli wheel | py3-none-any.whl | `uv build` | 临时 venv 中 `uv pip install` | 两次 SHA-256 均为 ba001c9a…；未发布 | 本地已验证 |
| source distribution | tar.gz | `uv build` | 源码安装 | 两次 SHA-256 均为 6c98b4a6…；未发布 | 本地已验证 |
| Agent Skill | Markdown | 仓库随附 | 手工复制/由 Agent 读取 | 无版本化安装或 E2E 证据 | 未验证 |

## 平台支持

| 平台/版本 | CPU/运行环境 | 已声明 | 可构建 | 已测试 | 已发布 | 证据/限制 |
| --- | --- | --- | --- | --- | --- | --- |
| macOS 26.5 | arm64 / Python 3.12.11 | 是 | 是 | 是 | 否 | 29 passed、1 skipped；wheel 安装运行成功 |
| macOS / Python 3.10 | arm64 / CPython 3.10 | 是 | 是 | 是 | 否 | 隔离测试 29 passed、1 skipped |
| Windows/Linux | Python >=3.10 | 隐含 | 未验证 | 未验证 | 否 | 仅 CRLF 单测不能替代目标平台运行 |
| Tuanjie/Unity + ASE | Editor + MCP :8080 | 是 | 不适用 | 未验证 | 否 | 本次无监听且未指定安全测试 shader |

## 上帝文件与模块隔离

### 文件行数门禁

- 门禁：`.project-architect.json` 为唯一事实源；source 250 预警/400 上限，test 400/600，config 160/200。
- 扫描范围 / 排除范围：项目自有 Python 源码、测试和配置；schema JSON、fixture、锁文件、构建产物按类型不进入 Python LOC 门禁。采集未截断。

| 文件 | 行数 | 门禁结果 | 核心链路 | 建议 | 问题 ID |
| --- | ---: | --- | --- | --- | --- |
| src/asecli/cli/commands.py | 219 | 正常 | 是 | 保持职责聚焦；新增修复勿超过 250 预警 | 不适用 |
| src/asecli/core/model.py | 185 | 正常 | 是 | 继续以 roundtrip 测试保护 | 不适用 |
| src/asecli/core/layout.py | 127 | 正常 | 是 | 暂不拆分 | 不适用 |
| src/asecli/cli/main.py | 120 | 正常 | 是 | 错误契约修复应保留组合根定位 | 不适用 |
| tests/test_audit_fixes.py | 86 | 正常 | 否 | 补负路径时按能力放入对应测试文件 | 不适用 |

### 上帝文件候选

| 文件或逻辑类型族 | 规模/职责 | 扇入/扇出或共享状态 | 修改/回归证据 | 结论 | 拆分边界 |
| --- | --- | --- | --- | --- | --- |
| cli/commands.py | 219 行、11 个 handler + 写盘工具 | 扇出 4 个模块，无共享可变状态 | 最近一次由 main 拆分；测试覆盖多入口 | 非上帝文件 | 达到 250 预警前按 create/graph/bridge 能力拆分 |
| core/model.py | 185 行、模型 + 解析/序列化 | core 内高扇入，无全局状态 | 3 次提交，roundtrip 回归稳定 | 非上帝文件 | 仅在格式变体增加时拆 parser/serializer |

### 模块隔离风险

| 问题 ID | 功能 | 当前分布 | 耦合点 | 连带回归 | 建议边界 |
| --- | --- | --- | --- | --- | --- |
| AUD-ARCH-001 | raw Node 行解析 | core 私有函数经 facade 暴露给 cli | `_parse_node_line` | parser 内部变更可直接影响 CLI | 提供公开 `NodeLine.from_line` 或公开解析契约 |

## 项目成熟度

等级：`L0 缺失`、`L1 临时`、`L2 可重复`、`L3 标准化`、`L4 可度量`。

| 维度 | 等级 | 当前机制 | 证据 | 主要缺口 |
| --- | --- | --- | --- | --- |
| 需求与追溯 | L2 | FR/CR/ADR/TASK/REG 文档与 traceability.csv | 结构检查通过 | 状态/命令与实现漂移，缺真实验证回写 |
| 架构与模块 | L2 | 模块地图、配置化 LOC、fitness strict | strict 0 warning/error | 公共契约语义未完全受检 |
| 构建 | L2 | uv.lock + Hatchling + 本地可复现构建 | 两次产物哈希一致 | 无 CI 干净环境 artifact |
| 自动化测试 | L2 | pytest 29 项、双 Python 版本 | 29 passed、1 skipped | 核心负路径和真实桥接缺失 |
| CI | L0 | 无 | 未发现 `.github` 工作流 | PR/夜间/发布门禁均未自动执行 |
| 发布与回滚 | L1 | 本地安装说明、写盘 `.bak` | wheel 可安装 | 无 REL/tag/远程产物/回滚演练 |
| 可观测性 | L1 | stdout JSON、部分 changed/tool_result | 代码与运行输出 | 无关联 ID、结构化 stderr、桥接错误归一化 |
| 安全与供应链 | L1 | 默认 loopback URL、零生产依赖 | 静态检查 | token/MCP 信任策略、SCA/SBOM/许可证缺失 |
| UI/无障碍 | 不适用 | 明确无 UI | README/架构文档 | CLI 国际化不是当前发布门禁 |

- 总体成熟度与依据：L1；原因不是文件缺失，而是主链路目标编辑器验收、CI/发布证据和治理真实性仍依赖人工且存在已复现的 S1 负路径。

## 回归验证机制

| 检查项 | 当前机制 | 自动化/CI | 覆盖 | 证据 | 缺口 |
| --- | --- | --- | --- | --- | --- |
| 核心模块 | pytest | 本地自动、CI 无 | parse/roundtrip/mutate/layout/schema/CLI | 双版本 29 passed | add-node 输出、graph-from、错误 JSON、重复输入未覆盖 |
| 跨模块/架构 | project-architect strict | 本地自动、CI 无 | LOC/文档/追溯/fitness | 0 warning/error | 检查器不验证任务状态真实性和测试文件存在性 |
| 编辑器 E2E | `pytest -m bridge` | 环境条件测试 | recompile 单用例 | 本次 1 skipped | create/Agent E2E 不存在或无证据 |
| 发布前回归 | 文档声明 | 手工 | 声称全量 bridge + 快速审计 | 无执行记录 | 无 REL、artifact、后验收与回滚演练 |
| 失败留痕、Test-Fix Loop、回滚与复盘 | 历史对抗审计与 `.bak` | 部分 | 已修复 7 个历史 finding | adversarial audit + 29 tests | 当前新增 finding 尚未进入 BUG/REG/时间线 |

## OpenSpec 规范管理

| 状态 | 结论 | 证据 |
| --- | --- | --- |
| 工具、项目配置、实际使用、规范一致性、strict 校验 | 未发现项目使用证据 | OpenSpec 1.7.0 已安装，但仓库无 `openspec/`；本次只读审计未初始化。现有 FR/CR 由治理 Markdown/CSV 管理。 |

## CodeGraph 使用情况

| 状态 | 结论 | 证据 |
| --- | --- | --- |
| 安装、初始化、索引新鲜度、实际使用、更新机制 | 降级 | `codegraph status` 明确为 `Not initialized`；本次未 init，使用 project-architect fitness、`rg` 和源码阅读替代。 |

## 文档增量与变更留档

| 变更类型 | 载体/机制 | 增量历史 | 关联键 | 字段完整性 | 抽样证据与缺口 |
| --- | --- | --- | --- | --- | --- |
| 需求变更 | 架构总纲 + traceability + timeline | 部分 | FR/CR/ADR | 部分 | CR-0001 与 FR-0008 有记录；当前实现状态未完整回写 |
| 技术变更 | technical-route + Git commit | 有 | ADR/TASK/commit | 部分 | MCP 路线已记录，但章程/部分说明仍残留 Codely/旧路径 |
| 文件修改记录 | Git + task charter | 部分 | TASK/REG | 缺失 | Git 有 7 个提交；任务卡大量未开始且证据回写为空 |
| 缺陷/回归 | regression-catalog + adversarial audit | 部分 | REG/AA-OPT | 缺失 | 历史整改有证据；5 个 REG 命令引用不存在文件 |

## 功能模块闭环度

- 模块统计：发现数：9；已审计数：9；未覆盖数：0
- 清单校准：自动发现器未识别 `src/asecli` 能力目录；在临时 supplement 中人工新增 9 个稳定 FM，未排除任何模块。

| 模块 ID | 模块/能力 | 需求/入口 | 主路径/关键链路 | 数据/状态闭环 | 异常/恢复 | 日志/可观测性 | 回归/验收 | 发布证据 | 结论 | 问题 ID |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FM-0E60A4DD1B | parse-serialize | FR-0001 / parse | file → AseFile → AseGraph → serialize | 两个 fixture 可逐字节回读 | ValueError/NOT_FOUND；无格式版本迁移 | JSON 摘要，无结构化诊断 | roundtrip、CRLF、空行测试通过 | wheel 隔离 parse 通过；无 REL | 部分闭环 | AUD-FLOW-001 |
| FM-9040886B90 | graph-mutation | FR-0002 / set-field、connect、disconnect、remove-node | CLI → graph_ops → atomic_write | `.bak` 与原子替换存在，但结构不变量可被破坏 | 错误码存在；无写前结构阻断 | JSON 返回 written/path | mutate/CLI 测试通过，负路径失败 | 仅本地源码/临时运行 | 断链 | AUD-FLOW-001；AUD-FE-003 |
| FM-8ADC52C2A4 | schema-library | FR-0002 / add-node | schema_for → node_from_schema → graph | 299 类型可查，版本信息在数据中未被消费 | unknown/opaque 有错误码；版本不匹配无阻断 | add-node warnings | schema 抽样测试通过但未验生成行 | 无真实 Unity 节点打开证据 | 断链 | AUD-FLOW-001；AUD-FE-001；AUD-DATA-001 |
| FM-C73F236CD5 | validation-checksum | FR-0003 / validate、fix-checksum | AseGraph/checksum → issue JSON/写盘 | checksum 可复算；重复输入连接未建模 | checksum 警告和 dangling/duplicate ID | issue list + error_count | 综合测试通过；登记的专用测试路径失效 | 本地 wheel 含模块；无发布后验收 | 部分闭环 | AUD-FLOW-001；AUD-FE-003；AUD-FE-006 |
| FM-F03DFA9A41 | layout | FR-0008 / layout | graph → Sugiyama-lite → position write | 仅 x/y 改动由测试保护 | 环检测有降级；目标编辑器视觉未验 | moved/written JSON | 5 个布局测试通过 | wheel 构建含模块；无 Tuanjie 验收 | 部分闭环 | AUD-FLOW-001 |
| FM-3537DE9938 | create-from-template | FR-0005 / create | template + optional donor → checksum → atomic_write | 基础 rename 回读通过；donor 注入破坏壳结构 | exists/rename 错误有返回；无语法回读门禁 | created/name/graph_from JSON | rename 回归通过，graph-from 无测试 | 无 Unity 打开/发布证据 | 断链 | AUD-FLOW-001；AUD-FE-002 |
| FM-DF0669A019 | recompile-bridge | FR-0004/CR-0001 / recompile | file hash → MCP initialize/tools call → hash | changed 比较存在；tool `isError` 未上抛 | HTTP/URL 错误处理存在，工具级错误断链 | 返回 tool_result，缺统一失败态 | 1 bridge test本次跳过 | 无真实 MCP/Tuanjie 证据 | 断链 | AUD-FLOW-001；AUD-FE-005 |
| FM-1DB3E4EA8B | cli-contract | FR-0007 / 11 个命令 | argparse → handler → JSON envelope | 成功/业务异常多数封装；parse_args 在 try 外 | CliError/INTERNAL；usage 路径无 JSON | stdout JSON 是主契约 | cli_contract 仅覆盖部分负路径 | wheel 隔离入口可运行；无发布 | 断链 | AUD-FLOW-001；AUD-FE-004 |
| FM-25E63BD4F6 | agent-skill | FR-0006 / SKILL.md | Agent 读指南 → 调 CLI → validate/recompile | 文档规定回读，但无会话证据 | 描述常见错误；依赖 CLI 正确性 | 依赖 CLI JSON | REG-0010 仅登记 | 无安装版本与 Agent E2E | 未验证 | AUD-FLOW-001 |

### 前端功能入口闭环

- 入口统计：发现数：11；已审计数：11；未覆盖数：0
- 清单校准：无人工新增/排除 FE；CLI 自动发现 11 个 argparse 子命令。

| 入口 ID | 页面/入口与类型 | 条件/权限 | 目标/handler | 状态覆盖 | 返回/恢复 | 测试/运行证据 | 结论 | 问题 ID |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FE-5FE7C39BCC | `parse` CLI | 文件可读 | cmd_parse | 成功、NOT_FOUND/PARSE_ERROR；usage 不在 handler | 只读，可重试 | wheel 隔离运行 + CLI test | 已闭环 | 不适用 |
| FE-5F33E87610 | `set-field` CLI | 文件可写、node/field 有效 | cmd_set_field | dry-run/write/NOT_FOUND；保留字段无保护 | `.bak` 可恢复 | node ID 复现导致 3 悬空引用 | 断链 | AUD-FE-003 |
| FE-37BA87FA15 | `add-node` CLI | schema 或 raw line | cmd_add_node | dry-run/write/schema error/warning | `.bak` 可恢复 | schema add 生成 12/14 字段 | 断链 | AUD-FE-001 |
| FE-C3162CA2E1 | `connect` CLI | 两端节点存在 | cmd_connect | dry-run/write/NOT_FOUND | `.bak` 可恢复 | 同一输入端可写入两条连接且 validate 不报错 | 断链 | AUD-FE-003 |
| FE-AAF53AF86F | `disconnect` CLI | 连接存在 | cmd_disconnect | dry-run/write/NOT_FOUND | `.bak` 可恢复 | 源码检查；无独立入口测试 | 未验证 | AUD-FLOW-001 |
| FE-0018A7D5D8 | `remove-node` CLI | node 存在 | cmd_remove_node | dry-run/write/NOT_FOUND | `.bak` 可恢复 | CLI 合同测试覆盖附属线清理 | 已闭环 | 不适用 |
| FE-BBB0F9830B | `validate` CLI | 文件可读 | cmd_validate | issue JSON；即使 error_count>0 仍 exit 0 | 只读，但调用方门禁失效 | 无效图返回 3 errors 且进程成功 | 断链 | AUD-FE-003 |
| FE-369C790BD8 | `fix-checksum` CLI | 文件可写 | cmd_fix_checksum | 无 dry-run/`--write`；始终覆盖 | `.bak` 可恢复 | 临时文件哈希变化 | 部分闭环 | AUD-FE-006 |
| FE-C71A570BA7 | `layout` CLI | 文件可读写 | cmd_layout | dry-run/write | `.bak` 可恢复 | 5 个自动测试通过 | 已闭环 | 不适用 |
| FE-B537BBBC81 | `create` CLI | template 可读、out 可写 | cmd_create | exists/rename/force；donor 注入无语法门禁 | 覆盖时有 `.bak` | graph-from 输出双 Shader 声明 | 断链 | AUD-FE-002 |
| FE-3F4DBCA0D3 | `recompile` CLI | Unity 项目、MCP 会话 | cmd_recompile | HTTP 错误可映射；tools/call isError 未映射 | 可重试但无会话清理/可信成功判定 | mock 失败被当成功；真实 bridge skipped | 断链 | AUD-FE-005 |

## 交互流程与 UI

### Product Design 参与情况

| 检查项 | 结论 | 证据/限制 |
| --- | --- | --- |
| 历史参与证据、本次调用、当前截图、视觉结论等级 | 不适用 | 项目明确为无 UI 的机器调用 CLI；本次没有视觉目标，不调用 Product Design，不做 UI/无障碍合规声明。 |

### 关键流程证据

| 步骤 | 用户目标/操作 | 截图或运行证据 | 健康度 | UX/可访问性问题 | 证据限制 |
| --- | --- | --- | --- | --- | --- |
| 01 | Agent 解析真实 fixture | wheel 安装后的单行 JSON | 良好 | 机器契约清晰 | 仅本地 fixture |
| 02 | Agent 修改图并校验 | set/add/connect 定向复现 | 阻塞 | 无效写入仍可返回成功 | 未在 Unity 打开 |
| 03 | Agent 创建并重编译 | graph-from 复现 + bridge mock | 阻塞 | 工具级失败未提升 | 无真实编辑器 |

### UI 检查

| 页面/区域 | 层级与清晰度 | 一致性/状态 | 响应式 | 键盘/焦点/语义 | 问题 ID |
| --- | --- | --- | --- | --- | --- |
| 无 UI；CLI JSON | 机器输出清晰 | usage 与 fix-checksum 契约不一致 | 不适用 | 不适用 | AUD-FE-004；AUD-FE-006 |

## 专项工程审计

| 专项领域 | 状态 | 核心证据 | 主要风险/缺口 | 问题 ID |
| --- | --- | --- | --- | --- |
| 安全与隐私 | 推断 | 默认 loopback；未发现已跟踪 secret 文件；token 仅参数传递 | 任意 MCP URL + token/execute_code 缺信任策略；未读取任何敏感值 | AUD-SEC-001 |
| 性能与资源 | 已验证 | 现有 perf 测试运行通过 | 规模仅 207 节点、恒真断言；内存/磁盘/大 schema 路径无预算 | AUD-PERF-001 |
| 可观测性与运维 | 已验证 | JSON envelope、changed、tool_result | 无 CI/关联 ID/结构化 stderr/发布后验收；工具错误语义不可靠 | AUD-OPS-001；AUD-FE-005 |
| 依赖、供应链与许可证 | 已验证 | uv.lock check、零生产依赖、两次可复现构建 | 无 SCA/SBOM/许可证决策；扫描工具未安装 | AUD-SUPPLY-001 |
| API、数据兼容与迁移 | 已验证 | CLI JSON/错误码文档、schema 记录 ASE 版本 | argparse 绕开 JSON；19109 schema 可用于 19100 图；无弃用策略 | AUD-DATA-001；AUD-FE-004 |
| 无障碍与国际化 | 不适用 | 无 UI；UTF-8/中文 JSON 已由实现支持 | Windows/Linux 与本地化 CLI 未验证，但非当前核心门禁 | 不适用 |
| 构建可复现与产物完整性 | 已验证 | sdist/wheel 两次哈希逐字节一致；Python 3.10/3.12 测试通过 | 无 CI artifact、tag、签名、SBOM、远程 Release | AUD-OPS-001 |

## 增量审计对比

- 基线报告：不适用；仓库没有可比的 Project Architect 历史报告。`docs/adversarial-audits/2026-09-01-014104-*` 是不同方法/范围的补充证据，不作为正式 compare 基线。

| 分类 | 问题 ID | 基线 -> 当前 | 证据/说明 |
| --- | --- | --- | --- |
| 已解决（补充历史） | AA-COR-001/002/003、AA-OPS-004/007/008、AA-COR-005 | 历史开放 -> 当前代码与回归存在 | CRLF、空行、rename、atomic backup、窗口销毁、SSE、hex 告警均有测试/源码证据 |
| 未变化（补充历史） | AA-TST-006 | 真实 bridge 未验 -> 本次仍未验 | 本次 1 bridge skipped，8080 无监听 |
| 新增（本次正式审计） | AUD-FE-001 等 14 项 | 无可比基线 -> 开放 | 来自标准审计负路径与治理对账，不宣称为历史回归 |

## 阻塞项

| 问题 ID | 阻塞内容 | 影响范围 | 证据 | 解除条件 |
| --- | --- | --- | --- | --- |
| AUD-FLOW-001 | 无安全隔离的真实目标 editor/shader 与 MCP 会话 | FR-0004/0005/0006、REG-0005/0006/0010 | 环境变量为空；8080 无监听；bridge test skipped | 在临时或明确授权工程执行 create→open→recompile→validate，并归档前后哈希/日志/截图 |
| AUD-GOV-001 | 回归目录命令与当前文件布局不一致 | 发布门禁与追溯可信度 | 5 个 pytest 路径不存在 | 更新 REG→真实测试节点并逐命令回读通过 |

## 潜在风险

| 问题 ID | 风险 | 触发条件 | 影响 | 概率 | 应对建议 |
| --- | --- | --- | --- | --- | --- |
| AUD-SEC-001 | Agent 将实例 token 发往非预期 MCP 端点 | 提示或配置改变 `--mcp-url` | 凭证泄露、Unity 执行边界扩大 | 中 | 默认仅 loopback，显式远程授权，禁止命令行明文 token |
| AUD-DATA-001 | ASE 版本差异导致节点字段布局变化 | 在 Version 19100 或未知版本执行 add-node | 图无法打开或行为错误 | 中 | schema 版本门禁 + 版本 fixture |
| AUD-SUPPLY-001 | 未来增加依赖后无持续扫描 | 新增生产依赖或公开分发 | 漏洞/许可证风险 | 低 | 在首个外部依赖或发布前建立 SCA/SBOM |

## 问题详情

### AUD-FE-001 schema 驱动 add-node 漏写通用字段

- 状态：开放
- 证据状态：已验证
- 严重程度：S1
- 优先级：P1
- 影响范围：所有 runtime schema 驱动的 `add-node` 写入
- 证据：`node_from_schema` 只拼接 4 个前缀字段与 `schema["fields"]`，而 schema 明确定义 fixed prefix 6；SaturateNode 实测生成 12 字段，契约要求 14。
- 根因判断：schema 提取层与节点构造层对“fields 是否包含 precision/preview”的契约不一致。
- 优化做法：建立单一 `NodeSchema` 构造契约，补齐通用字段并对生成行做 parse/字段数/真实 fixture 回归。
- 技术路径：复用 Python/dataclass/pytest，不引入依赖；先加失败测试，再最小修正 graph_ops/schema/CLI。
- 验收标准：SaturateNode 和至少 10 个 runtime 类型生成字段数、通用前缀和 roundtrip 与同版本真实样本一致。
- 验证方式：新增 schema add-node 参数化测试，运行 `uv run pytest tests/test_schema_samples.py tests/test_mutate.py -q`。
- 回滚/降级：修复未完成前禁用 schema 写入，仅允许已验证 raw `--line` + validate。

### AUD-DATA-001 schema 与输入 ASE 版本未建立兼容门禁

- 状态：开放
- 证据状态：已验证
- 严重程度：S1
- 优先级：P1
- 影响范围：Version 非 19109 的 `.shader/.asset` 上执行 schema 驱动 add-node
- 证据：schemas.json 的 295 个 runtime 类型均标记 Version=19109；fixture 含 Version=19100；测试在版本不同时跳过字段数断言，CLI 仍无拒绝/告警。
- 根因判断：版本差异被测试识别为风险，但未进入生产命令前置条件。
- 优化做法：将 schema 版本与 AseGraph.version 比较；默认拒绝未知/不兼容写入，明确的兼容表才允许放行。
- 技术路径：在 schema API 暴露版本，在 cmd_add_node 统一执行兼容检查并返回稳定错误码。
- 验收标准：19100 fixture 使用 19109 schema 时不写盘并返回机器可读兼容错误；19109 fixture 正常生成。
- 验证方式：跨版本成功/失败参数化测试 + dry-run 文件哈希不变断言。
- 回滚/降级：继续允许 `--line` 专家路径，但必须显式标注绕过 schema 和后续 Unity 验收。

### AUD-FE-002 create --graph-from 注入 donor 整个文件壳

- 状态：开放
- 证据状态：已验证
- 严重程度：S1
- 优先级：P1
- 影响范围：所有使用 `create --graph-from` 的新 shader
- 证据：commands.py 使用 `donor.prefix`；同一 fixture 创建结果含 2 个 `Shader "HLIT"` 声明和 1 个 ASEBEGIN。
- 根因判断：代码把 donor 的“文件前缀 + ASEBEGIN”误当成仅 ASEBEGIN 标记。
- 优化做法：只替换模板 ASEBEGIN/ASEEND 之间的 graph body，保留模板壳和单一 marker/checksum。
- 技术路径：提取 AseFile 的块级替换 API，先对双声明建立失败回归，再最小修改 cmd_create。
- 验收标准：输出只有一个 Shader 声明和一对 ASE marker，donor 节点/连线一致，parse/validate 通过且 Unity 可打开。
- 验证方式：纯文本回归 + 隔离 Tuanjie 打开验收。
- 回滚/降级：临时禁用 `--graph-from`，只支持模板复制与改名。

### AUD-FE-003 图修改与 validate 未形成结构安全门禁

- 状态：开放
- 证据状态：已验证
- 严重程度：S1
- 优先级：P1
- 影响范围：set-field、add-node、connect、validate 及依赖退出码的 Agent 工作流
- 证据：set-field 将 node 5 的 field 2 改为 500 后成功写盘，validate 发现 3 个悬空引用但退出码仍为 0；connect 可向同一输入 3:0 写入两个来源且 validate 不报结构错误。
- 根因判断：生产写命令只验证局部参数，不维护图级不变量；validate 把“发现错误”当作成功数据而非门禁失败。
- 优化做法：保护 marker/type/id 等保留字段或提供原子 rename；拒绝重复目标输入/重复 ID；validate 在 error_count>0 时返回约定失败退出码。
- 技术路径：core/checks 定义不变量，CLI 在写前验证，保留 dry-run；新增失败优先的 REG。
- 验收标准：所有写命令无法提交 dangling/duplicate ID/duplicate input 图；validate 对 error issue 返回 JSON 且 exit 2。
- 验证方式：参数化负路径、文件哈希/备份断言、完整 pytest。
- 回滚/降级：在严格校验可能误报时提供显式专家 override，但默认不可写且必须记录 warning。

### AUD-FE-004 argparse 参数错误绕开 JSON 契约

- 状态：开放
- 证据状态：已验证
- 严重程度：S1
- 优先级：P1
- 影响范围：缺参数、未知子命令、类型错误等所有 argparse 失败路径
- 证据：`uv run asecli parse` 返回 exit 2，stdout 0 字节，stderr 94 字节 usage；`parse_args` 位于 app 的 try/JSON 包装之外。
- 根因判断：默认 ArgumentParser.error/SystemExit 未被机器契约适配。
- 优化做法：自定义 parser error 或在 app 边界捕获并输出 `USAGE_ERROR` JSON，帮助文本仍可显式输出。
- 技术路径：只调整 cli/main.py 与契约测试，不改变业务 handler。
- 验收标准：所有非 help 调用无论成功失败，stdout 都是单行 JSON；exit 与错误码保持文档一致。
- 验证方式：缺参数、未知命令、非法数字、互斥参数的 subprocess 测试。
- 回滚/降级：若需保留人类 usage，将其写 stderr，同时 stdout 保持 JSON。

### AUD-FE-005 MCP 工具级错误被报告为成功

- 状态：开放
- 证据状态：已验证
- 严重程度：S1
- 优先级：P1
- 影响范围：recompile 的 execute_code 失败、权限拒绝或 Unity 侧异常
- 证据：mock `call_tool` 返回 `{"isError": true}` 时 `recompile_via_mcp` 正常返回，外层 CLI 会输出 ok=true。
- 根因判断：客户端只处理 JSON-RPC error，未验证 MCP tool result 的 `isError`/content 语义，也未验证 save 结果。
- 优化做法：规范化 MCP tool result，遇 isError/缺失成功证据抛 McpError；区分“未变化”与“执行失败”。
- 技术路径：在 bridge 层集中解析，CLI 仅映射 BRIDGE_ERROR；补 HTTP/SSE/tool error 单测。
- 验收标准：工具失败稳定返回 ok=false/BRIDGE_ERROR/exit 3；成功必须包含可解析的 saved 结果。
- 验证方式：mock 单元测试 + 真实 MCP 成功/失败两条链路。
- 回滚/降级：无法解析旧服务器结果时标记未验证并返回失败，不得乐观成功。

### AUD-FLOW-001 核心目标编辑器与 Agent E2E 未闭环

- 状态：开放
- 证据状态：未验证
- 严重程度：S1
- 优先级：P1
- 影响范围：FR-0004/0005/0006、REG-0005/0006/0010、所有 9 个 FM 的发布证据
- 证据：全量测试为 29 passed、1 skipped；ASECLI_TEST_SHADER 未设置；8080 无监听；无 REL/tag/真实 editor 结果。
- 根因判断：项目把代码完成、静态实验和真实用户链路验收混合记录，缺可重复隔离验收夹具。
- 优化做法：准备临时 Tuanjie 工程和可丢弃 shader，执行 create→parse/validate→recompile→Editor 打开→前后哈希/名称/图检查→Agent 按 Skill 重跑。
- 技术路径：复用现有 bridge marker 与 pytest bridge；证据写入 REG/时间线/REL，不修改用户生产资产。
- 验收标准：REG-0005/0006/0010 在明确版本/项目/ASE/MCP 条件下通过且可复核，失败恢复和回滚同样有证据。
- 验证方式：真实 Tuanjie/MCP 运行日志、目标文件前后哈希、Editor 结果截图或可复核输出。
- 回滚/降级：保持文本只读/解析能力可用，暂不宣称 create+compile 或 Agent 全流程发布完成。

### AUD-GOV-001 治理状态与可执行证据漂移

- 状态：开放
- 证据状态：已验证
- 严重程度：S1
- 优先级：P1
- 影响范围：里程碑、任务、REG、追溯、发布决策
- 证据：timeline/commit 声明 TASK-0005~0015 完成，task charter 多数仍“未开始”；REG-0003/0004/0006 等命令指向 5 个不存在测试文件；strict checker仍通过。
- 根因判断：实现重组后没有按交付协议回写任务状态、真实测试节点和证据；结构校验不检查命令可执行性。
- 优化做法：以当前 commit 和测试节点为准增量更新状态/证据，不重写历史；增加“REG 命令目标存在且可执行”校验。
- 技术路径：仅更新治理文档与检查测试；必要时以 CR/ADR 记录 set-prop→set-field、Codely→MCP、runtime schema 路线变化。
- 验收标准：每个已完成 TASK 有 commit/REG/时间线证据；regression-catalog 全部命令可执行；追溯检查能发现失效路径。
- 验证方式：逐条运行 REG 命令 + project-architect strict + Git diff 人工复核。
- 回滚/降级：保留旧事实为历史记录，用状态和 supersedes 表达，不删除历史 ID。

### AUD-FE-006 fix-checksum 违背统一 dry-run 安全默认

- 状态：开放
- 证据状态：已验证
- 严重程度：S2
- 优先级：P1
- 影响范围：按 README“无 --write 即预览”调用 fix-checksum 的 Agent/开发者
- 证据：parser 未提供 `--write`，cmd_fix_checksum 总是 atomic_write；临时文件调用前后 SHA-256 改变并生成 `.bak`。
- 根因判断：单个修复命令沿用早期语义，未纳入后续统一写入契约。
- 优化做法：通过 CR 明确 dry-run 语义；推荐增加 `--write`，默认只返回 fixed_to/preview，不落盘。
- 技术路径：复用 `_save`/atomic_write，更新 CLI/README/SKILL/契约测试。
- 验收标准：无 `--write` 文件哈希不变；带 `--write` 才修改并生成备份；JSON 明确 written。
- 验证方式：subprocess + 文件哈希 + `.bak` 测试。
- 回滚/降级：若暂时保留兼容性，至少在 README/SKILL 明确例外并增加显著 warning。

### AUD-PERF-001 性能门禁样本规模和断言失真

- 状态：开放
- 证据状态：已验证
- 严重程度：S2
- 优先级：P1
- 影响范围：NFR-0003、REG-0011、千节点性能声明
- 证据：range(1000,1200) 仅生成 200 节点，加基础 7 节点共 207；`assert "1200,0" or True` 恒为真。
- 根因判断：测试名称/文档目标与 fixture 生成逻辑未对账，缺节点数和结果正确性的强断言。
- 优化做法：生成至少 1000 个额外节点，断言精确数量、最后节点、序列化可回读和时间预算。
- 技术路径：仅修 tests/test_perf.py 和测试策略/REG 证据；同时记录硬件/运行时。
- 验收标准：>=1000 节点的 parse+layout+serialize 在声明环境 <1s，结果结构断言有效且无恒真表达式。
- 验证方式：独立运行 REG-0011 多次，记录中位数/最大值和环境。
- 回滚/降级：若 CI 波动，分离正确性硬门禁与性能基线告警，不降低节点规模。

### AUD-OPS-001 缺少持续 CI 与可发布/可回滚证据

- 状态：开放
- 证据状态：已验证
- 严重程度：S2
- 优先级：P1
- 影响范围：PR 门禁、Python 兼容、构建、发布与恢复
- 证据：仓库无 CI 文件、tag、REL 或远程 artifact；本次仅证明同机两次构建一致和本地安装可用。
- 根因判断：交付协议停留在文档约定，未形成持续执行机制。
- 优化做法：先建立最小 CI：3.10/3.12 pytest、lock check、build、strict 架构校验、artifact hash；发布前补 REL 与回滚演练。
- 技术路径：复用 uv/pytest/Hatchling；不引入服务型架构。
- 验收标准：干净 CI 对同 commit 产出通过记录和可下载 artifact；REL 关联测试、哈希、安装/卸载/回滚。
- 验证方式：PR/主分支一次真实 CI + 安装后 smoke + 回滚演练记录。
- 回滚/降级：CI 不可用时提供可复制本地脚本和人工签字，但不得标为自动门禁。

### AUD-SEC-001 MCP URL 与实例 token 缺少显式信任边界

- 状态：开放
- 证据状态：推断
- 严重程度：S2
- 优先级：P1
- 影响范围：`recompile --mcp-url --instance-token` 与 Agent 工具调用环境
- 证据：任意 URL 被直接交给 urllib，instance token 作为请求头发送；架构文档同时声称“不接触凭证”。
- 根因判断：默认本地自用威胁模型未落实为代码约束、凭证输入方式和日志脱敏规则。
- 优化做法：默认强制 loopback；远程端点要求显式 opt-in/allowlist；token 从受保护环境或 stdin 读取且不得进入命令历史/日志。
- 技术路径：标准库 URL 解析 + CLI 参数策略 + 安全回归，不新增依赖。
- 验收标准：非 loopback URL 默认拒绝；错误/日志不包含 token；远程授权路径有清晰风险确认和测试。
- 验证方式：URL 矩阵、日志捕获、进程参数/错误输出人工检查。
- 回滚/降级：只保留默认 127.0.0.1 连接，暂停远程 MCP 支持。

### AUD-SUPPLY-001 供应链与许可证基线缺失

- 状态：开放
- 证据状态：已验证
- 严重程度：S3
- 优先级：P2
- 影响范围：未来增加依赖、外部分发或 CLI-Anything Hub 发布
- 证据：生产 dependencies 为空且 uv.lock 有哈希，但 pip-audit/gitleaks/syft/trivy 均未发现，仓库无 LICENSE/SBOM/许可证决策。
- 根因判断：当前内部零依赖阶段风险低，供应链治理被整体后置。
- 优化做法：记录内部/开源许可决策；在首个生产依赖或外部发布前加入 SCA、密钥扫描和 SBOM。
- 技术路径：优先使用平台/CI 原生能力，工具选型单独评估，未经批准不安装。
- 验收标准：许可证边界明确；锁文件、SCA、SBOM 与 release artifact 可追溯。
- 验证方式：CI 报告与 REL 关联；本地不读取任何 secret 值。
- 回滚/降级：保持内部不发布状态，并禁止新增未经审查的生产依赖。

### AUD-ARCH-001 公共模块契约暴露私有解析符号

- 状态：开放
- 证据状态：已验证
- 严重程度：S3
- 优先级：P2
- 影响范围：core 与 cli 的长期边界稳定性
- 证据：core/__init__.py 导出 `_parse_node_line`，cli/commands.py 从公共 facade 导入该下划线私有符号；fitness 只验证文件路径公开。
- 根因判断：为 LOC 拆分 CLI 时复用了内部 helper，未同步形成正式公共 API。
- 优化做法：提供公开构造/解析方法或把 raw line 校验封装在 core 的公开契约中。
- 技术路径：小范围重命名/封装并保留回归，不调整总体模块结构。
- 验收标准：cli 不再导入下划线私有符号，fitness 与测试保持通过。
- 验证方式：`rg` 私有跨模块导入 + pytest + strict fitness。
- 回滚/降级：保留旧别名一个版本并标注 deprecated，避免突然破坏内部调用。

## 验证记录

| 命令/检查 | 目的 | 结果摘要 | 是否通过 |
| --- | --- | --- | --- |
| `audit_project.py collect ... --mode standard` | 全量证据与 FE/FM 清单 | 51 indexed、47 text、未截断、11 FE、9 人工校准 FM | 是 |
| `check_project_architecture.py ... --strict` | docs/kickoff/traceability/fitness/LOC | 0 warnings、0 errors | 是 |
| `uv run pytest -q` | Python 3.12 自动回归 | 29 passed、1 bridge skipped，0.58s | 是（bridge 未验证） |
| `uv run --isolated --python 3.10 pytest -q` | 最低声明 Python 版本 | 29 passed、1 bridge skipped，0.55s | 是（bridge 未验证） |
| `uv lock --check` | 锁文件一致性 | exit 0 | 是 |
| 两次 `uv build` + SHA-256/cmp | 同机可复现构建 | sdist/wheel 两次逐字节一致 | 是 |
| wheel 隔离安装后 `asecli parse` | 真实本地产物 smoke | JSON 成功，schema 数据已打包 | 是 |
| `asecli add-node ... SaturateNode` | schema 写入链路 | 12 字段，不满足 6+8 契约 | 否 |
| `asecli create ... --graph-from` | donor 图创建链路 | 2 个 Shader 声明 | 否 |
| `asecli parse`（缺 file） | JSON 错误契约 | stdout 0 字节，stderr usage | 否 |
| set-field/connect/validate 负路径 | 图结构门禁 | 可写 dangling/重复输入；validate exit 0 | 否 |
| bridge `isError` mock | 工具失败语义 | 函数仍正常返回 | 否 |
| 登记 REG 路径存在性检查 | 治理可执行性 | 5 个 pytest 文件不存在 | 否 |
| `codegraph status` | 依赖分析工具状态 | Not initialized，按只读边界降级 | 未运行索引 |
| 真实 Tuanjie/MCP bridge | 目标平台验收 | 无目标 shader，8080 无监听 | 未运行 |

## 计划外发现

- 历史对抗性审计的 CRLF、空行、rename、原子写、窗口销毁和 SSE 修复均能在当前代码/测试中找到证据；本次未重复整改。
- `check_project_architecture.py --strict` 的结构检查通过不代表任务状态、REG 命令或真实运行证据语义正确；该边界已记录为 AUD-GOV-001，不修改检查器。

## 遗留问题

- 14 个开放问题全部进入同时间戳优化任务书；其中 12 个 P1 必须在发布/真实用户资产自动写入前处理。
- 下一次审计建议日期：2026-09-12，或所有 P1 修复并完成真实 Tuanjie/MCP 验收后立即复审，以较早者为准。

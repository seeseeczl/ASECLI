# 项目审计报告

## 元信息

- 项目路径：/Users/long/GitHub/ASECLI
- 项目类型：Python CLI + Agent Skill + Unity/Tuanjie MCP 桥接
- 审计时间：2026-09-01T13:25:48+08:00（Asia/Shanghai）
- 当前分支 / commit：main / 8883425b22244141af7475ea1a0e7042d99c0067
- 工作区状态：dirty；采证时 45 个变更路径，均为本轮已授权整改与审计增量，未覆盖或清理用户改动
- 审计范围：145 个已索引项目文件；69 个文本文件、9 个功能模块、11 个 CLI 入口、Python 3.10/3.12 回归、隔离 Tuanjie/MCP E2E、本地构建/安装/卸载/恢复与供应链证据
- 非目标：不创建 commit，不 push，不创建远程 GitHub Release，不写用户生产 Tuanjie 工程，不初始化 OpenSpec/CodeGraph
- 请求模式 / 实际模式：标准 / 标准增量复审（包含隔离目标编辑器运行证据）
- 未覆盖范围：远程 GitHub Actions 实际 run、Dependabot 在线执行、远程 artifact 下载与 Release 发布、Windows/Linux 目标平台；这些是未授权或缺少远程状态的验证边界，不计为本地整改缺陷

## 审计模式与证据等级

| 项目 | 结果 | 证据/限制 |
| --- | --- | --- |
| 证据采集器 | 已运行 | schema 1.1；145 files indexed、69 text files read、未截断；证据 JSON 位于系统临时目录 |
| 静态证据 | 已验证 | 源码、测试、CI 配置、治理/追溯、供应链策略、Skill、REL 草案和 Git 工作区 |
| 自动化测试 | 已验证 | Python 3.10/3.12 非 bridge 全量回归、18 条 REG 收集、strict、供应链检查均已执行；最终复验结果见验证记录 |
| 运行与 UI | 已验证 | 无 UI；隔离 Tuanjie 2022.3.62t2 + MCP 10.1.2 完成 create→add-node→validate→recompile，成功与失败路径均有脱敏证据 |
| 发布产物 | 部分 | 本地 wheel/sdist、SHA-256、SPDX、安装/卸载/恢复已验证；远程 CI/Release 未运行 |

## 结论摘要

- 总体判断：基线审计的 14 个问题在本地授权范围内全部完成整改并有静态、自动化、真实 Tuanjie/MCP 或本地产物证据；本次没有新的开放问题。
- 最大阻塞：无本地阻塞；远程 GitHub CI/Release 因未获 push/发布授权而保持未验证。
- 最大回归风险：未来修改 schema 写入、MCP 响应兼容或 CI/供应链配置时，仍需保留现有失败关闭门禁和真实隔离 Editor 复验。
- 第一优先优化方向：当前无需新增优化任务；后续获得远程授权后只补 GitHub CI/Release 运行证据，不扩大实现范围。
- 问题统计：S0=0，S1=0，S2=0，S3=0；P0=0，P1=0，P2=0

## 项目简介与功能作用

- 项目简介：AseCLI 为 AI Agent 和 Unity/Tuanjie 开发者提供 ASE 文件的解析、修改、校验、布局、创建与 MCP 重编译能力；本地文本链路可离线使用，HLSL 再生成由目标编辑器执行。
- 主要输入/输出与边界：输入是 `.shader`/ShaderFunction 文本、CLI 参数和受控 MCP 会话；输出为单行 JSON、原子写回文件、`.bak` 备份与编辑器保存结果。默认只信任 loopback MCP，远程端点必须显式授权。

| 功能/场景 | 目标用户 | 入口与输入 | 主要输出 | 实现状态 | 证据 |
| --- | --- | --- | --- | --- | --- |
| 解析、校验与图修改 | Agent/开发者 | 9 个文本/图命令 + ASE 文件 | JSON、dry-run 或原子写回 | 已实现 | Python 双版本回归、写前不变量与 CLI 契约测试 |
| 模板创建与编辑器重编译 | Agent/开发者 | `create`、`recompile` + 隔离 MCP | 新 shader、saved/changed 结果 | 已实现 | Tuanjie 2022.3.62t2、最终 11 nodes/0 errors、真实成功/失败路径 |
| Agent 操作指南 | Codex/Claude Code/Codely | `skills/asecli/SKILL.md` | 可恢复的三链路操作流程 | 已实现 | 隔离 Agent E2E 与 REG-0010 |
| 本地发布候选 | 工程维护者 | `uv build`、供应链工具 | wheel、sdist、SPDX、哈希 | 已实现/远程未发布 | REL-0001、本地可复现构建和安装回滚 |

## 审计覆盖率

| 对象 | 分类 | 覆盖状态 | 证据方式 | 未覆盖原因 |
| --- | --- | --- | --- | --- |
| 145 个项目文件 | 核心/支撑 | 已验证 | collect 索引、69 个文本读取、LOC/fitness/secret/license 检查 | 扫描未截断 |
| 9 个 FM 能力模块 | 核心/支撑 | 已验证 | supplement 校准后逐模块闭环对账 | 未覆盖数 0 |
| 11 个 CLI FE 入口 | 核心 | 已验证 | 自动入口清单、源码、契约测试、真实 bridge | 未覆盖数 0 |
| 隔离目标编辑器 | 外部集成 | 已验证 | Tuanjie 2022.3.62t2、MCP 10.1.2、6517 loopback、哈希/parse/validate/log | 只证明该隔离环境，不外推其他版本 |
| 本地发布链路 | 交付 | 已验证 | 双构建、逐字节比较、SHA-256、SPDX、安装/卸载/重装 | 远程 GitHub 仍未验证 |
| Windows/Linux 与远程 GitHub | 平台/交付 | 未覆盖 | 当前没有目标主机或 push/发布授权 | 需目标平台或远程授权后解除 |

## 严重程度总览

本次没有开放问题。基线问题的逐项解决分类与证据见“增量审计对比”。

| 问题 ID | 证据状态 | 优先级 | 严重程度 | 领域 | 问题 | 核心证据 |
| --- | --- | --- | --- | --- | --- | --- |

## 项目架构

### 当前结构

- 项目保持 Python 3.10+ 模块化单体：`cli` 为组合根，依赖 `core/schema/checks/bridge`；`skills/asecli` 作为 Agent 交付接口；CI、供应链和 REL 作为治理/交付层。
- 生产依赖仍为 0；公共 core parser、schema 版本门禁、图写前不变量、MCP 信任边界和 tool result 解析均有独立契约回归。

### 关键链路

| 链路 | 入口 | 核心模块 | 数据/状态流 | 外部依赖 | 结论 |
| --- | --- | --- | --- | --- | --- |
| 解析/校验 | parse/validate | core → checks → cli | 文件文本 → AseFile/AseGraph → issue JSON | 文件系统 | 已闭环 |
| 图修改 | set/add/connect/remove/layout | cli → core/schema/checks | 读文件 → 写前验证 → atomic write + `.bak` | 文件系统 | 已闭环 |
| 创建 | create | cli/commands + core | template 壳 + donor graph → checksum → 新文件 | 文件系统、隔离 Editor | 已闭环 |
| 重编译 | recompile | cli → bridge → MCP | 前哈希 → execute_code → saved/changed → 后哈希 | loopback MCP、Tuanjie | 已闭环 |
| 发布候选 | CI config/tools/REL | uv → artifact → SBOM/hash → install/rollback | 本地产物状态 | uv/Hatchling | 本地闭环；远程运行未验证 |

### 模块边界与隔离

| 模块 | 独立文件/目录 | 公共接口 | 独立测试 | 跨模块依赖 | 修改爆炸半径 | 结论 |
| --- | --- | --- | --- | --- | --- | --- |
| core | 是 | `core/__init__.py`、`parse_node_line` | roundtrip/mutate/layout/perf/core-contract | 标准库 | 高 | 公共契约已收口，旧 alias 兼容 |
| schema | 是 | `schema_for/load/allows_mutation` | schema samples/add/version | 标准库 | 高 | 未知/跨版本写入失败关闭 |
| checks | 是 | `validate_file`、checksum API | graph safety/CLI contract | core | 中 | error_count 与退出码闭环 |
| bridge | 是 | `recompile_via_mcp` | bridge contract/security/真实 bridge | 标准库 | 高 | loopback、脱敏、未知结果失败关闭 |
| cli | 是 | console script | CLI/create/governance tests | 四核心模块 | 高 | 11 个入口统一单行 JSON |
| Skill | 是 | SKILL.md | REG-0010 人工 E2E | CLI 文档契约 | 中 | 与真实命令及恢复语义一致 |

## 技术路径与交付形态

- 技术路径：Python 标准库 + argparse + Hatchling + uv；本地文件状态；MCP streamable HTTP/SSE；Tuanjie/Unity 编辑器作为受控外部执行器。
- 实现/壳形态：无 UI 的本地 CLI + Agent Skill，外接 loopback MCP/Editor。
- 构建与交付：固定 `uv.lock` 与 Action SHA，`uv build` 生成 wheel/sdist，生成 SPDX 与 SHA256SUMS，使用隔离 venv 完成安装、卸载、恢复；未进行签名、公证或远程发布。

| 交付物 | 格式/载体 | 生成方式 | 安装/部署 | 签名/发布证据 | 结论 |
| --- | --- | --- | --- | --- | --- |
| AseCLI wheel | py3-none-any.whl | `SOURCE_DATE_EPOCH=1788220800 uv build` | 隔离 venv/uv pip | SHA256SUMS + REL-0001；未签名/未远程发布 | 本地已验证 |
| source distribution | tar.gz | 同一固定环境 | 源码安装 | 两次逐字节比较；审计/REL 目录排除避免自引用 | 本地已验证 |
| SPDX SBOM | SPDX JSON | `tools/generate_sbom.py` | 与 artifact 同目录 | 供应链检查与 SHA-256 | 本地已验证 |
| Agent Skill | Markdown | 仓库随附 | Agent 读取 | 隔离 E2E；无远程包分发 | 已验证 |

## 平台支持

| 平台/版本 | CPU/运行环境 | 已声明 | 可构建 | 已测试 | 已发布 | 证据/限制 |
| --- | --- | --- | --- | --- | --- | --- |
| macOS 26.5 / Python 3.10 | arm64 / CPython 3.10.20 | 是 | 是 | 是 | 否 | 非 bridge 全量与构建门禁 |
| macOS 26.5 / Python 3.12 | arm64 / CPython 3.12.11 | 是 | 是 | 是 | 否 | 非 bridge 全量、安装/卸载/恢复 |
| Tuanjie 2022.3.62t2 | arm64 + MCP 10.1.2 | 是 | 不适用 | 是 | 否 | 隔离工程 6517 loopback；不代表其他 Editor/MCP 版本 |
| Windows/Linux | Python >=3.10 | 隐含 | 未验证 | 未验证 | 否 | 需目标主机运行 |

## 上帝文件与模块隔离

### 文件行数门禁

- 门禁：`.project-architect.json` 是唯一事实源；source 250 预警/400 硬上限，test 400/600，config 160/200，函数 40/60。
- 扫描范围 / 排除范围：145 个项目文件，排除 `.git/.venv/dist/build/cache/vendor` 等配置目录；扫描未截断；strict 为零 warning/零 error。

| 文件 | 行数 | 门禁结果 | 核心链路 | 建议 | 问题 ID |
| --- | ---: | --- | --- | --- | --- |
| src/asecli/cli/commands.py | 242 | 正常 | 是 | 保持组合命令职责，不做无关拆分 | 不适用 |
| src/asecli/core/model.py | 196 | 正常 | 是 | 继续由 roundtrip 与公共 API 契约保护 | 不适用 |
| src/asecli/bridge/mcp_client.py | 151 | 正常 | 是 | 保持传输/安全边界集中 | 不适用 |
| tests/test_cli_contract.py | 135 | 正常 | 否 | 保留失败路径参数化 | 不适用 |

### 上帝文件候选

| 文件或逻辑类型族 | 规模/职责 | 扇入/扇出或共享状态 | 修改/回归证据 | 结论 | 拆分边界 |
| --- | --- | --- | --- | --- | --- |
| cli/commands.py | 11 个 handler + 写盘工具 | 扇出 core/schema/checks/bridge；无共享可变状态 | CLI/graph/create/bridge 回归 | 非上帝文件 | 达预警后按 create/graph/bridge 分组 |
| core/model.py | 文本模型、解析与序列化 | core 内高扇入；无全局状态 | roundtrip、CRLF、公开 parser 契约 | 非上帝文件 | 仅在格式族增加时拆 parser/serializer |

### 模块隔离风险

| 问题 ID | 功能 | 当前分布 | 耦合点 | 连带回归 | 建议边界 |
| --- | --- | --- | --- | --- | --- |
| 不适用 | raw Node 行解析 | core 公共 API，CLI 仅使用命名公开入口 | 旧 `_parse_node_line` 仅作兼容 alias | REG-0019 | 在后续大版本按弃用策略移除 alias |

## 项目成熟度

等级：`L0 缺失`、`L1 临时`、`L2 可重复`、`L3 标准化`、`L4 可度量`。

| 维度 | 等级 | 当前机制 | 证据 | 主要缺口 |
| --- | --- | --- | --- | --- |
| 需求与追溯 | L3 | FR/CR/ADR/BUG/TASK/REG/REL 与 strict | traceability、timeline、18 条 REG 可收集 | 远程 commit/PR 链接尚不存在 |
| 架构与模块 | L3 | 模块地图、配置化 LOC/fitness、公共契约 | strict 零 warning/error、REG-0019 | CodeGraph 未初始化且当前不需要 |
| 构建与自动化测试 | L3 | 双 Python、本地 CI 等价门禁、可复现 build | pytest、cmp、SHA-256、wheel smoke | 远程 CI run 未验证 |
| 目标编辑器 E2E | L3 | 隔离工程、真实 MCP 成功/失败、脱敏证据 | saved/changed、前后哈希、0 errors | 其他 Editor/MCP 版本未形成矩阵 |
| 发布与回滚 | L2 | REL、SBOM、安装/卸载/恢复 | 本地候选与恢复演练 | 无 tag、签名、远程 Release |
| 安全与供应链 | L3 | loopback 默认、远程 opt-in、脱敏、固定 Action SHA、SPDX | 安全/供应链测试和离线检查 | 在线漏洞库与 Dependabot 未运行 |
| UI/无障碍 | 不适用 | 项目无 UI | CLI 机器契约 | 不适用 |

- 总体成熟度与依据：L2；核心开发与目标编辑器链路已达到标准化本地门禁，但正式发布与远程 CI 仍停留在可重复、未远程执行阶段。

## 回归验证机制

| 检查项 | 当前机制 | 自动化/CI | 覆盖 | 证据 | 缺口 |
| --- | --- | --- | --- | --- | --- |
| 核心模块与 CLI | pytest + REG catalog | 本地自动；CI 配置已定义 | 解析、写入、创建、错误 JSON、安全、性能 | Python 3.10/3.12；18 条 REG 可收集 | 远程 CI 未运行 |
| 目标编辑器 E2E | bridge marker + 隔离工程 | 人工启动 Editor/MCP，pytest 自动断言 | create/recompile/Agent 成功与失败 | 1 passed、79 deselected；前后 SHA-256、0 errors | 需显式隔离环境，未纳入公共 CI |
| 构建与供应链 | 双 build/cmp + SPDX/secret/license/hash | 本地自动；CI 配置已定义 | wheel/sdist/lock/Action/secret/license | REL-0001、dist 证据 | 远程 artifact 与在线 SCA 未验证 |
| 失败留痕、Test-Fix Loop、回滚与复盘 | BUG/REG/timeline + `.bak` + wheel reinstall | 自动测试与人工 REL | 9 个 BUG、21 个 REG、本地恢复 | bug-register、timeline、REL-0001 | 首次正式发布后再验证远程回滚 |

## OpenSpec 规范管理

| 状态 | 结论 | 证据 |
| --- | --- | --- |
| 工具、项目配置、实际使用、规范一致性、strict 校验 | 未发现证据 | 项目以架构总纲、CR/ADR/traceability 为事实源；本次未初始化 OpenSpec，避免扩大范围。 |

## CodeGraph 使用情况

| 状态 | 结论 | 证据 |
| --- | --- | --- |
| 安装、初始化、索引新鲜度、实际使用、更新机制 | 降级 | 项目未初始化 CodeGraph；本次使用 project-architect fitness、`rg`、公共接口契约测试和源码审阅替代。 |

## 文档增量与变更留档

| 变更类型 | 载体/机制 | 增量历史 | 关联键 | 字段完整性 | 抽样证据与缺口 |
| --- | --- | --- | --- | --- | --- |
| 需求变更 | change-register + 架构总纲 + traceability | 有 | CR-0002～CR-0006、FR/NFR | 完整 | 公共契约、MCP 信任和供应链语义均增量留档 |
| 技术变更 | technical-route + module-map + ADR | 有 | ADR/TASK/CR | 完整 | parser API、桥接、CI/供应链路线与实现一致 |
| 文件修改记录 | Git 工作树 + task charter + timeline | 有 | TASK/BUG/REG/REL | 完整 | 未创建 commit，因此 commit 字段如实保持待交付边界 |
| 缺陷/回归 | bug-register + regression-catalog | 有 | BUG-0001～0009、REG-0001～0021 | 完整 | 登记的 18 条 pytest 命令均可收集；人工/真实门禁独立标注 |

## 功能模块闭环度

- 模块统计：发现数：9；已审计数：9；未覆盖数：0
- 清单校准：自动发现器未识别 `src/asecli` 能力目录；复用基线 supplement 人工新增 9 个稳定 FM，未排除模块，ID 与基线一致。

| 模块 ID | 模块/能力 | 需求/入口 | 主路径/关键链路 | 数据/状态闭环 | 异常/恢复 | 日志/可观测性 | 回归/验收 | 发布证据 | 结论 | 问题 ID |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FM-0E60A4DD1B | parse-serialize | FR-0001 / parse | file → AseFile → AseGraph → serialize | fixture 逐字节回读 | PARSE/NOT_FOUND JSON，可重试 | 单行 JSON 摘要 | roundtrip/CRLF/性能 | wheel 隔离 parse | 已闭环 | 不适用 |
| FM-9040886B90 | graph-mutation | FR-0002 / set/add/connect/disconnect/remove | CLI → graph_ops → 写前 validate → atomic write | 结构不变量与 `.bak` | 保留字段、重复 ID/输入失败关闭 | JSON written/path/code | REG-0013/0015/0018 | wheel + Editor E2E | 已闭环 | 不适用 |
| FM-8ADC52C2A4 | schema-library | FR-0002 / add-node | schema_for → version gate → node line | 固定字段完整、版本匹配 | 未知/跨版本拒绝且不写盘 | warnings/error code | schema samples/add | 隔离 Editor 重存 | 已闭环 | 不适用 |
| FM-C73F236CD5 | validation-checksum | FR-0003 / validate/fix-checksum | graph/checksum → issue JSON/显式写回 | error_count 与 exit 2、checksum 回读 | 默认 dry-run、`.bak` 恢复 | issue/error_count/written | REG-0003/0004/0018 | wheel validate smoke | 已闭环 | 不适用 |
| FM-F03DFA9A41 | layout | FR-0008 / layout | graph → deterministic layout → position write | 仅 x/y 改动、连线不变 | 环/无根图确定性降级 | moved/written JSON | REG-0012、千节点性能 | wheel 包含模块 | 已闭环 | 不适用 |
| FM-3537DE9938 | create-from-template | FR-0005 / create | template shell + donor graph → checksum | 单一 shader 壳、名称/图回读 | exists/force/parse 失败可恢复 | created/name/graph_from | REG-0006/0014 | 隔离 Editor 11 nodes/0 errors | 已闭环 | 不适用 |
| FM-DF0669A019 | recompile-bridge | FR-0004/CR-0004 / recompile | hash → MCP call → saved/changed → hash | tool result 与文件哈希双确认 | RPC/tool/未知文本均 BRIDGE_ERROR | 脱敏 JSON、saved/changed | REG-0005/0016/0017 | 真实 MCP 成功/失败 | 已闭环 | 不适用 |
| FM-1DB3E4EA8B | cli-contract | FR-0007 / 11 个命令 | argparse → handler → 单行 envelope | 成功/失败状态与退出码固定 | usage/business/internal 分类 | stdout JSON，stderr 脱敏 | REG-0007/0020 | wheel console script | 已闭环 | 不适用 |
| FM-25E63BD4F6 | agent-skill | FR-0006 / SKILL.md | Agent → CLI → validate → recompile | 每步回读、显式写入 | 失败即停、备份恢复、远程需授权 | 依赖 CLI JSON | REG-0010 | 隔离 Agent E2E | 已闭环 | 不适用 |

### 前端功能入口闭环

- 入口统计：发现数：11；已审计数：11；未覆盖数：0
- 清单校准：无人工新增或排除 FE；自动发现的 11 个 argparse 子命令全部进入对账，ID 与基线一致。

| 入口 ID | 页面/入口与类型 | 条件/权限 | 目标/handler | 状态覆盖 | 返回/恢复 | 测试/运行证据 | 结论 | 问题 ID |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FE-5FE7C39BCC | `parse` CLI | 文件可读 | cmd_parse | 成功、usage、not-found、parse-error | 只读重试 | wheel smoke + CLI tests | 已闭环 | 不适用 |
| FE-5F33E87610 | `set-field` CLI | 文件可写、字段可变 | cmd_set_field | dry-run/write/结构字段拒绝 | `.bak` 恢复 | graph-safety + CLI tests | 已闭环 | 不适用 |
| FE-37BA87FA15 | `add-node` CLI | schema/version 或 raw line 有效 | cmd_add_node | 完整字段、跨版本/未知类型拒绝 | 默认 dry-run、`.bak` 恢复 | schema-add + Editor E2E | 已闭环 | 不适用 |
| FE-C3162CA2E1 | `connect` CLI | 两端存在且目标输入唯一 | cmd_connect | dry-run/write/重复输入拒绝 | `.bak` 恢复 | graph-safety tests | 已闭环 | 不适用 |
| FE-AAF53AF86F | `disconnect` CLI | 连接存在 | cmd_disconnect | dry-run/write/not-found | `.bak` 恢复 | CLI/graph tests | 已闭环 | 不适用 |
| FE-0018A7D5D8 | `remove-node` CLI | node 存在 | cmd_remove_node | dry-run/write/not-found | 附属线清理、`.bak` | CLI/graph tests | 已闭环 | 不适用 |
| FE-BBB0F9830B | `validate` CLI | 文件可读 | cmd_validate | 0 error 成功、error exit 2 | 只读修正后重试 | graph-safety + wheel smoke | 已闭环 | 不适用 |
| FE-369C790BD8 | `fix-checksum` CLI | 文件可读；写入需 `--write` | cmd_fix_checksum | preview/write/invalid | `.bak` 恢复 | CLI checksum tests | 已闭环 | 不适用 |
| FE-C71A570BA7 | `layout` CLI | 图可解析 | cmd_layout | dry-run/write/invalid | `.bak` 恢复 | layout + perf tests | 已闭环 | 不适用 |
| FE-B537BBBC81 | `create` CLI | template/donor 可读、out 可写 | cmd_create | create/force/exists/graph-parse | `.bak`/重新创建 | create tests + Editor 重存 | 已闭环 | 不适用 |
| FE-3F4DBCA0D3 | `recompile` CLI | loopback MCP；远程需 opt-in | cmd_recompile | saved+changed、unchanged、RPC/tool error | BRIDGE_ERROR/3、可重试 | contract/security + 真实 MCP | 已闭环 | 不适用 |

## 交互流程与 UI

### Product Design 参与情况

| 检查项 | 结论 | 证据/限制 |
| --- | --- | --- |
| 历史参与证据、本次调用、当前截图、视觉结论等级 | 不适用 | 项目明确为机器调用 CLI，无 UI/视觉目标；本次不调用 Product Design，不宣称 UI 或无障碍合规。 |

### 关键流程证据

| 步骤 | 用户目标/操作 | 截图或运行证据 | 健康度 | UX/可访问性问题 | 证据限制 |
| --- | --- | --- | --- | --- | --- |
| 01 | Agent 创建隔离 shader | create JSON + Editor 重存 | 良好 | 机器契约明确 | 仅隔离工程 |
| 02 | Agent 添加节点并校验 | 最终 parse 19602、11 nodes、0 wires；validate 0 errors | 良好 | 不适用 | 不证明所有 ASE 节点类型 |
| 03 | Agent 触发重编译 | saved=true、changed=true、前后 SHA-256 变化 | 良好 | 不适用 | Tuanjie 2022.3.62t2/MCP 10.1.2 |
| 04 | MCP 执行失败 | BRIDGE_ERROR、exit 3、未报告假成功 | 良好 | 失败信息脱敏 | 该服务版本可把异常作为普通文本返回 |

### UI 检查

| 页面/区域 | 层级与清晰度 | 一致性/状态 | 响应式 | 键盘/焦点/语义 | 问题 ID |
| --- | --- | --- | --- | --- | --- |
| 无 UI；CLI JSON | 单行 envelope 清晰 | 11 个入口成功/失败一致 | 不适用 | 不适用 | 不适用 |

## 专项工程审计

| 专项领域 | 状态 | 核心证据 | 主要风险/缺口 | 问题 ID |
| --- | --- | --- | --- | --- |
| 安全与隐私 | 已验证 | loopback 默认、远程 opt-in、禁重定向、token 环境输入与脱敏测试 | 远程端点仍需逐次授权；未读取任何敏感值 | 不适用 |
| 性能与资源 | 已验证 | 精确 1007 节点、5 轮 parse+layout+serialize+roundtrip，单轮 <1s | 仅当前 macOS/Python 环境，不外推资源受限设备 | 不适用 |
| 可观测性与运维 | 已验证 | CLI JSON、稳定错误码、saved/changed、脱敏 Editor/MCP 日志 | 无长期服务指标；本地 CLI 场景不适用 | 不适用 |
| 依赖、供应链与许可证 | 已验证 | 零运行时依赖、uv.lock、固定 Action SHA、LICENSE、secret/license/SBOM 检查 | 在线漏洞库/Dependabot 未运行 | 不适用 |
| API、数据兼容与迁移 | 已验证 | CLI 契约、schema 版本门禁、保留字段保护、公开 parser alias | 未来 ASE schema 版本需新增 fixture 后启用写入 | 不适用 |
| 无障碍与国际化 | 不适用 | 无 UI；UTF-8 JSON/路径测试 | Windows/Linux locale 未验证，非当前核心发布范围 | 不适用 |
| 构建可复现与产物完整性 | 已验证 | 固定 epoch 双构建逐字节一致、SHA256SUMS、SPDX、安装/卸载/恢复 | 无签名、公证、远程 artifact/Release | 不适用 |

## 增量审计对比

- 基线报告：docs/05-audits/2026-09-01-122217-project-audit-report.md
- 对比条件：同一项目/分支、同为标准审计；当前扫描范围从 51 扩展到 145 个文件且未截断，并增加真实隔离 Tuanjie/MCP 与本地产物证据，因此可判定解决，不以扫描消失代替验证。

| 分类 | 问题 ID | 基线 -> 当前 | 证据/说明 |
| --- | --- | --- | --- |
| 已解决 | AUD-FE-001 | 开放 S1/P1 → 不存在 | schema 固定字段完整、版本门禁与 REG-0013 |
| 已解决 | AUD-DATA-001 | 开放 S1/P1 → 不存在 | 跨版本 add-node 失败关闭且文件哈希不变 |
| 已解决 | AUD-FE-002 | 开放 S1/P1 → 不存在 | graph-only donor 组合测试 + 隔离 Editor 重存 |
| 已解决 | AUD-FE-003 | 开放 S1/P1 → 不存在 | 写前图不变量、validate exit 2 与 REG-0015 |
| 已解决 | AUD-FE-004 | 开放 S1/P1 → 不存在 | 11 个 argparse 入口统一单行 JSON/usage error |
| 已解决 | AUD-FE-005 | 开放 S1/P1 → 不存在 | tool/RPC/普通文本异常均失败关闭，真实失败 exit 3 |
| 已解决 | AUD-FLOW-001 | 开放 S1/P1 → 不存在 | 隔离 create→add-node→validate→recompile、Agent E2E、0 errors |
| 已解决 | AUD-GOV-001 | 开放 S1/P1 → 不存在 | REG catalog 18 条可收集、strict 零 warning/error、TASK/追溯回写 |
| 已解决 | AUD-FE-006 | 开放 S2/P1 → 不存在 | fix-checksum 默认 dry-run、显式 `--write` 与 `.bak` 回归 |
| 已解决 | AUD-PERF-001 | 开放 S2/P1 → 不存在 | 1007 节点、非恒真断言、5 轮性能与 roundtrip |
| 已解决 | AUD-OPS-001 | 开放 S2/P1 → 不存在 | CI 配置、本地双构建、artifact、REL/回滚；远程 run 单列未验证边界 |
| 已解决 | AUD-SEC-001 | 开放 S2/P1 → 不存在 | loopback allowlist、远程 opt-in、token 脱敏、禁重定向 |
| 已解决 | AUD-SUPPLY-001 | 开放 S3/P2 → 不存在 | LICENSE、策略、SPDX、secret/license/hash 离线检查 |
| 已解决 | AUD-ARCH-001 | 开放 S3/P2 → 不存在 | 公共 `parse_node_line`、兼容 alias、私有跨模块扫描与 REG-0019 |
| 新增 | 不适用 | 0 | 本次未发现新的开放问题 |
| 复发或回归 | 不适用 | 0 | 本次未发现复发问题 |
| 改善 | 不适用 | 0 | 所有基线问题均达到解决证据，未留下仅降级问题 |
| 未变化 | 不适用 | 0 | 没有保持开放且等级不变的问题 |

## 阻塞项

| 问题 ID | 阻塞内容 | 影响范围 | 证据 | 解除条件 |
| --- | --- | --- | --- | --- |
| 不适用 | 无本地阻塞 | 当前授权范围 | 全部本地门禁和隔离 E2E 已完成 | 不适用 |

## 潜在风险

| 问题 ID | 风险 | 触发条件 | 影响 | 概率 | 应对建议 |
| --- | --- | --- | --- | --- | --- |
| 不适用 | 远程 CI 配置尚未由 GitHub runner 实际执行 | 用户后续 push/启用 Actions | 首次远程 run 可能暴露平台或权限差异 | 中 | 获授权后读取真实 run 和 artifact，不预先宣称通过 |
| 不适用 | Tuanjie/MCP 版本响应结构变化 | 升级 Editor 或 MCP server | recompile 可能失败关闭 | 中 | 保留未知响应 BRIDGE_ERROR，新增版本 fixture 后再兼容 |
| 不适用 | 未来新增生产依赖 | 修改 pyproject/lock | 漏洞与许可证面扩大 | 低 | 保持供应链门禁和 SPDX 更新为合入条件 |

## 问题详情

无开放问题。14 个基线问题的解决证据已在“增量审计对比”逐项列出；远程 GitHub CI/Release 与未运行平台作为证据边界保留，不虚构为已验证，也不重复登记为本地实现缺陷。

## 验证记录

| 命令/检查 | 目的 | 结果摘要 | 是否通过 |
| --- | --- | --- | --- |
| `audit_project.py collect ... --mode standard --supplement ...` | 全量静态采证 | 145 indexed、69 text、truncated=false、9 FM、11 FE | 是 |
| `uv run --isolated --frozen --python 3.10 pytest -q` | Python 3.10 回归 | 79 passed、1 bridge skipped | 是 |
| `uv run --isolated --frozen --python 3.12 pytest -q` | Python 3.12 回归 | 79 passed、1 bridge skipped | 是 |
| `ASECLI_TEST_SHADER=... uv run pytest -m bridge ...` | 真实 Tuanjie/MCP | 1 passed、79 deselected；saved/changed true，失败 BRIDGE_ERROR/3 | 是 |
| `python3 tools/check_regression_catalog.py` | REG 可执行性 | checked: 18 | 是 |
| Project Architect strict | 架构、文档、追溯与 fitness | 0 warning、0 error | 是 |
| `tools/supply_chain_check.py` + SBOM | 供应链/许可/secret/hash | 0 finding、0 runtime dependency、lock checked；SPDX 10 packages | 是 |
| 两次固定 epoch build + `cmp` | 构建可复现 | wheel/sdist 逐字节一致；wheel `cc1d8e4c…`、sdist `b9c5ead6…`；sdist 排除 REL/审计目录 | 是 |
| wheel install→parse→uninstall→import fail→reinstall→validate | 安装与恢复 | parse/卸载/不可导入/重装/0 errors | 是 |
| `git diff --check` | 文本与补丁质量 | 无 whitespace error | 是 |

## 计划外发现

- sdist 若包含 REL/审计文档会造成 artifact 哈希自引用；已在 `pyproject.toml` 仅排除 `docs/04-delivery/releases` 与 `docs/05-audits`，不排除源码、测试或其他治理文档，并将在最终双构建中验证归档内容。

## 遗留问题

- 无开放整改问题。
- 未验证边界：远程 GitHub CI/Dependabot/Release、Windows/Linux、签名/公证；需要相应授权或目标环境后单独补证据。

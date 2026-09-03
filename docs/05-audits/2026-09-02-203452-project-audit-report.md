# 项目审计报告

## 元信息

- 项目路径：`/Users/long/GitHub/ASECLI`
- 项目类型：Python CLI + Agent Skill + 团结/Unity Editor MCP 桥接 + 自定义 Material Inspector
- 审计时间：2026-09-02T20:34:52+08:00（Asia/Shanghai）
- 当前分支 / commit：`main` / `8aaff193b76787b548daac6b9352866665976c68`，与 `origin/main` 一致
- 工作区状态：采证开始与报告生成前均为 clean；本轮只新增同时间戳审计报告和优化任务书
- 审计范围：308 个索引文件、127 个已读文本文件、14 个功能模块、15 个 CLI 入口；Profile 以项目配置的 `core + ai-agent` 为基线，并因 CLI 协议、Editor API 和 Material Inspector 扩展执行 `api-platform + ui` 检查
- 非目标：不修改业务代码、治理基线、团结工程、远端 tag/Release；不初始化 OpenSpec 或 CodeGraph；不复述宿主进程中可能出现的凭证
- 请求模式 / 实际模式：标准 / 标准增量审计
- 未覆盖范围：EditorGraphSpec v2 的新进程重开、目标平台编译、材质绑定与最终渲染；light skin/缩放/长中文/键盘焦点 UI 矩阵；本轮未配置三个真实 bridge pytest 的环境变量

## 审计模式与证据等级

| 项目 | 结果 | 证据/限制 |
| --- | --- | --- |
| 证据采集器 | 已运行 | schema 1.1；308 files indexed、127 text files read、`truncated=false`；校准后 14 FM / 15 FE，JSON 位于系统临时目录 |
| 静态证据 | 已验证 | 源码、测试、README、Skill、治理/追溯、CI、REL、包元数据和当前 Git 状态 |
| 自动化测试 | 已验证 | `uv lock --check`；全量 `223 passed, 3 skipped`；REG 36/36；CI governance、供应链和 70 条高价值定向测试通过 |
| 运行与 UI | 部分 | 同一会话历史中，当前团结 `2022.3.61t9` + ASE `1.9.6.2` 已完成 v2 创建、独立 recompile、中文属性/说明和两个 Tooltip 人工确认；本轮未重跑新进程与完整视觉矩阵 |
| 发布产物 | 部分 | GitHub Actions run `33625061100` 三个 job 全绿；artifact `9844457577` 的 wheel/sdist、SBOM 与 SHA-256 已下载复验；正式私有 Release 仍为 `v0.1.0` |

## 结论摘要

- 总体判断：项目总体成熟度为 **L2（可重复）**，构建、自动化测试、CI 和候选包已局部达到 L3；核心 CLI 功能可用且失败关闭较完整，但治理、真实 Editor/视觉验收与正式发布尚未形成同一条持续闭环。
- 最大阻塞：`main` 已是 `0.2.0` 且候选产物可安装，但严格治理/发布检查仍有 50 项发现，同时 `v0.2.0` 尚无正式 tag/Release；因此当前不满足“无条件正式发布”门槛。
- 最大回归风险：EditorGraphSpec v2、Comment/布局和自定义 Inspector 都依赖目标团结/ASE 的真实生命周期与视觉状态，纯文本/模拟测试无法覆盖重开、画布遮挡、平台编译和最终渲染。
- 第一优先优化方向：先修复严格治理基线与 LOC 扫描盲区，再补 Editor v2 新进程/目标平台和正常缩放画布证据，最后以一致的 REL 记录发布 `v0.2.0`。
- 问题统计：S0=0，S1=3，S2=4，S3=2；P0=0，P1=7，P2=2

## 项目简介与功能作用

- 项目简介：ASECLI 面向 Shader 开发者、美术和 AI Agent，以可脚本化 CLI 读取、治理和验证 Amplify Shader Editor 资产；对动态/不透明节点则通过受限 EditorGraphSpec 调用真实 ASE Editor API。它还内置统一 Material Inspector，使属性遵守“中文显示名 + 英文变量名和默认值 Tooltip + 中文使用说明”的呈现契约。
- 主要输入/输出与边界：输入为 ASE `.shader`/ShaderFunction、JSON spec、CLI 参数和可选 loopback MCP 会话；输出为单行 JSON、dry-run 差异、原子写回与 `.bak`、Editor 保存结果或可安装 wheel/sdist。CLI 能证明结构与契约，不能单独证明目标平台最终渲染正确。

| 功能/场景 | 目标用户 | 入口与输入 | 主要输出 | 实现状态 | 证据 |
| --- | --- | --- | --- | --- | --- |
| 解析、修改、校验 | Agent/Shader 开发者 | 9 个文本/图命令 + ASE 文件 | JSON、差异、原子写回、备份 | 已实现 | 全量 pytest、真实 VehicleLocalShadow 两文件 validate 0 error |
| 图治理 | Shader 开发者/美术 | `graph-audit`、`layout`、`comment-group` | 未使用候选、分层坐标、原生 Comment | 部分 | 结构/边界测试通过；normal zoom 视觉门禁未固化 |
| 属性与 Inspector 治理 | 美术/TA | `custom-gui`、`gui-support`、属性 JSON spec | 中文标签、技术 Tooltip、中文 HelpBox、唯一 GUI provider | 已实现/视觉部分 | 两真实 Shader 共 7 属性零违规；当前实例 Tooltip 已人工确认；矩阵不完整 |
| Shader 创建与重编译 | Agent/Shader 开发者 | `create --backend editor --spec`、`recompile` | ASE 自建图、manifest、保存/重载结果 | 部分 | v2 当前实例已通过；新进程/目标平台/最终渲染未验证 |
| 内部分发 | 维护者/试用者 | GitHub Actions、私有 Release、`uv tool install` | wheel、sdist、SBOM、SHA256SUMS | 部分 | `0.2.0` CI artifact 可安装；正式 Release 仍为 `v0.1.0` |

## 审计覆盖率

| 对象 | 分类 | 覆盖状态 | 证据方式 | 未覆盖原因 |
| --- | --- | --- | --- | --- |
| 308 个项目文件 | 核心/支撑 | 已验证 | standard collector、127 个文本读取、未截断 | 二进制/排除目录按采集器策略不读 |
| 14 个 FM 模块 | 核心/支撑 | 已验证 | supplement 校准、源码/测试/运行/发布逐项对账 | 未覆盖数 0 |
| 15 个 CLI FE 入口 | 核心 | 已验证 | argparse 自动发现、handler/测试/真实边界逐项对账 | 未覆盖数 0 |
| 当前目标 Shader | 外部资产 | 已验证 | Caster 19602/11 nodes/1 wire；Receiver 19602/28 nodes/6 wires；均 validate 0 error、呈现契约 0 violation | graph-audit 的 10 个 unused candidates 需人工判断，不作为 CLI 缺陷 |
| 团结/ASE 运行链路 | 外部集成 | 抽样 | 同会话当前实例历史证据与用户 Tooltip 确认 | 本轮无可调用 Editor MCP；未重跑三个 bridge pytest |
| CI 与候选包 | 交付 | 已验证 | run 33625061100、artifact 9844457577、SHA-256、SBOM、隔离 Python 3.12 安装 | 未形成 `v0.2.0` 正式 Release |

## 严重程度总览

| 问题 ID | 证据状态 | 优先级 | 严重程度 | 领域 | 问题 | 核心证据 |
| --- | --- | --- | --- | --- | --- | --- |
| AUD-GOV-002 | 已验证 | P1 | S1 | 治理 | 严格治理与发布门禁累计 50 项失败 | kickoff 2、traceability 25、fitness 4、release 19 |
| AUD-GOV-003 | 已验证 | P1 | S2 | 治理 | Project Architect 配置仍使用旧 LOC 字段并漏扫 tests/tools | `.project-architect.json` 的 `loc_thresholds` 与缺失 `source_roots` |
| AUD-SIZE-001 | 已验证 | P1 | S2 | 模块质量 | 两个生产 C# 资源超过 source 400 行硬上限但被 `.cs.txt` 漏扫 | 536/408 行；`tests/test_custom_gui.py` 584 行 |
| AUD-FLOW-002 | 已验证 | P1 | S1 | 功能闭环 | EditorGraphSpec v2 缺新进程、目标平台与最终渲染闭环 | 测试策略和 TASK-0032 明确保留边界 |
| AUD-FLOW-003 | 已验证 | P1 | S2 | 功能闭环 | layout/comment-group 缺可重复的正常缩放真实画布门禁 | 离线尺寸为估算，live bounds 本轮未重跑 |
| AUD-REL-001 | 已验证 | P1 | S1 | 发布 | `main`/artifact 为 0.2.0，正式私有 Release 与安全支持声明仍为 0.1.x | `pyproject.toml`、README、`SECURITY.md`、tag 列表 |
| AUD-UI-001 | 已验证 | P1 | S2 | UI | Material Inspector 视觉与可访问性验收矩阵不完整 | 当前实例仅覆盖中文标签/说明、折叠与 Tooltip |
| AUD-SUPPLY-002 | 推断 | P2 | S3 | 供应链 | 在线漏洞状态不可持续查询，正式 0.2.0 全载荷清单尚未生成 | 生产依赖 0；当前仅候选 artifact 清单 |
| AUD-CI-001 | 已验证 | P2 | S3 | CI | Actions 出现 Node.js 20 弃用/强制 Node 24 运行警告 | run 33625061100 日志，当前 job 仍全绿 |

## 项目架构

### 当前结构

- Python 3.10+ 模块化单体：`cli` 为组合根，调用 `core`、`schema`、`checks`、`bridge`；`skills/asecli` 是 Agent 操作契约；`docs`、`tools`、`.github` 提供治理与发布。
- 文本后端负责可安全序列化的节点；动态/opaque 节点由白名单 EditorGraphSpec + 固定 C# 执行器交给 ASE 自身创建，随后 Save/Load manifest 对账。
- Material Inspector 由随 wheel 打包的唯一 `ASECLI.MaterialGUI.ASECLIMaterialGUI` 提供，旧 MZGUI 标记仅做读取兼容。

### 关键链路

| 链路 | 入口 | 核心模块 | 数据/状态流 | 外部依赖 | 结论 |
| --- | --- | --- | --- | --- | --- |
| 解析/校验 | `parse`/`validate` | core → checks → cli | 文件 → AseFile/AseGraph → issue JSON | 文件系统 | 已闭环 |
| 图修改 | set/add/connect/disconnect/remove | cli → core/schema/checks | 读取 → 不变量验证 → dry-run/原子写回 + `.bak` | 文件系统 | 已闭环 |
| 图治理 | graph-audit/layout/comment-group | checks/core → cli | 图语义 → 候选/坐标/Comment → 校验 | 可选 Editor live bounds | 结构闭环，视觉部分 |
| 属性呈现 | custom-gui/gui-support | core → bridge → 固定 C# 资源 | 属性规范 → 图/编译标签 → GUI 安装/Inspector | 团结 Editor | 契约闭环，UI 矩阵部分 |
| Editor 创建 | create/recompile | cli → editor_spec/editor_create → MCP → ASE | v2 JSON → ASE Save/Load → manifest → 独立重编译 | 团结 2022.3.61t9、ASE 1.9.6.2 | 当前实例闭环，交付闭环不足 |
| 内部发布 | CI/REL | uv → build/SBOM/hash → artifact/Release | commit → 候选包 → 安装/回滚 | GitHub Actions/Release | 0.2.0 候选闭环，正式断点 |

### 模块边界与隔离

| 模块 | 独立文件/目录 | 公共接口 | 独立测试 | 跨模块依赖 | 修改爆炸半径 | 结论 |
| --- | --- | --- | --- | --- | --- | --- |
| core | 是 | `core/__init__.py` 与领域函数 | roundtrip/mutation/layout/comment/gui | 标准库 | 高 | 职责清楚；需补向 checks/bridge 的正式公共面 |
| schema | 是 | `schema_for`/版本能力矩阵 | schema samples/version/add | core model | 中 | 未知版本与 opaque 写入失败关闭 |
| checks | 是 | validate/usage audit | graph safety/usage/local var | 直接导入 3 个 core 私有模块 | 中 | 触发 AUD-GOV-002 |
| bridge | 是 | recompile/editor create/gui support | mock + 条件 bridge E2E | core、MCP、团结/ASE | 高 | 1 个 core 私有导入；真实生命周期是主要风险 |
| cli | 是 | `asecli` console script | CLI contract + 各命令测试 | 四核心模块 | 高 | 15 个入口统一 JSON 合同 |
| Agent Skill | 是 | `skills/asecli/SKILL.md` | 文档/命令契约与 REG | CLI | 中 | 能力清单完整，运行证据依赖宿主 |

## 技术路径与交付形态

- 技术路径：Python 标准库、argparse、Hatchling、uv、pytest；本地文件状态；MCP HTTP/SSE；团结/UnityEditor/UnityEngine 与 ASE 1.9.6.2 Editor API。
- 实现/壳形态：本地 CLI + Agent Skill + 可安装到团结工程的 C# MaterialGUI/Editor 执行资源；没有常驻服务或独立桌面壳。
- 构建与交付：`uv build` 生成通用 Python wheel 与 sdist；私有 GitHub Actions 生成 SBOM、供应链报告和哈希；试用者通过私有 Release 下载后用 `uv tool install` 安装。升级可装新 wheel，回滚可重装上一版本。

| 交付物 | 格式/载体 | 生成方式 | 安装/部署 | 签名/发布证据 | 结论 |
| --- | --- | --- | --- | --- | --- |
| ASECLI 0.2.0 wheel | `py3-none-any.whl` | GitHub Actions / Hatchling | `uv tool install <wheel>` | artifact digest `sha256:2d6fe0ce...8931`，内部 SHA256SUMS 复验成功 | 候选已验证 |
| source distribution | `.tar.gz` | 同一 package job | 源码安装/审查 | 与 wheel 同 artifact，清单复验成功 | 候选已验证 |
| SBOM/供应链报告 | SPDX JSON/文本 | `generate_sbom.py` / `supply_chain_check.py` | 与候选包一起下载 | name/version 为 `asecli-0.2.0` | 候选已验证 |
| Agent Skill | Markdown + references | 随仓库/源码包分发 | Agent 读取 | 无独立签名 | 已实现 |
| 正式私有 Release | Git tag + GitHub Release assets | 手动授权后发布 | `gh release download` + `uv tool install` | 目前只有 `v0.1.0` | 0.2.0 未闭环 |

## 平台支持

| 平台/版本 | CPU/运行环境 | 已声明 | 可构建 | 已测试 | 已发布 | 证据/限制 |
| --- | --- | --- | --- | --- | --- | --- |
| macOS / Python 3.10、3.12 | 当前 arm64 主机 | 是 | 是 | 是 | v0.1.0 | CI 与本地 223 passed/3 skipped；0.2.0 候选可安装 |
| 团结 2022.3.61t9 / ASE 1.9.6.2 | 当前运行实例 | 是 | 不适用 | 部分 | 随 CLI 资源 | v2 创建/recompile/Inspector 已验；新进程与最终渲染未验 |
| 其他 Unity/Tuanjie/ASE | 未固定 | 否 | 未验证 | 未验证 | 否 | EditorGraphSpec 对未知版本/成员失败关闭 |
| Windows/Linux Python | Python >=3.10 | 隐含 | 理论可用 | CI Python job 有自动证据但无目标 Editor | 否 | 不外推团结/ASE 集成能力 |

## 上帝文件与模块隔离

### 文件行数门禁

- 门禁：仓库意图为 source 250/400、test 400/600、config 160/200；但当前配置键为旧 `loc_thresholds`，新版检查器实际回退到默认 `thresholds`。函数 40/60 来自既有治理约定，不是当前 LOC 脚本的文件扫描结果。
- 扫描范围 / 排除范围：当前 `source_roots` 回退为 `src/app/lib/packages`，扩展名不含 `.txt`，因此 `tests/`、`tools/` 和 `.cs.txt` 资源没有进入真实 LOC 门禁；证据采集未截断。

| 文件 | 行数 | 门禁结果 | 核心链路 | 建议 | 问题 ID |
| --- | --- | --- | --- | --- | --- |
| `src/asecli/bridge/resources/asecli_material_gui.cs.txt` | 536 | 按生产 source 意图应不通过，当前漏扫 | 是 | 按职责拆分固定 C# 资源，或登记有 owner/到期日/补偿测试的 ADR 例外 | AUD-SIZE-001 |
| `src/asecli/bridge/resources/editor_create.cs.txt` | 408 | 按生产 source 意图应不通过，当前漏扫 | 是 | 拆分规格解析、ASE 生命周期与 manifest 回传，保持打包接口不变 | AUD-SIZE-001 |
| `tests/test_custom_gui.py` | 584 | test 预警、低于 600 硬上限；当前漏扫 | 否 | 修正扫描范围后纳入门禁，后续按行为域拆 fixture/测试 | AUD-GOV-003 |
| `src/asecli/cli/commands.py` | 248 | 正常，接近 source 250 预警 | 是 | 保持命令路由，不顺手重构 | 不适用 |

### 上帝文件候选

| 文件或逻辑类型族 | 规模/职责 | 扇入/扇出或共享状态 | 修改/回归证据 | 结论 | 拆分边界 |
| --- | --- | --- | --- | --- | --- |
| MaterialGUI C# 资源 | 536 行；drawer、状态、Tooltip、HelpBox、默认值读取 | 多种属性标记与 OnGUI 状态共享 | GUI 定向测试与当前实例验收 | 候选 | provider/元数据解析、drawer 呈现、默认值格式化 |
| Editor create C# 资源 | 408 行；窗口生命周期、节点创建、连线、保存/回滚、manifest | 依赖 ASE 静态窗口状态 | bridge 测试和当前实例 v2 验收 | 候选 | spec 执行、ASE 会话、manifest/回滚 |
| `tests/test_custom_gui.py` | 584 行；多版本、原子规范、失败关闭 | fixture 与多命令契约集中 | 相关回归密集 | 测试文件候选 | 解析/写入/属性呈现/CLI 分层 |

### 模块隔离风险

| 问题 ID | 功能 | 当前分布 | 耦合点 | 连带回归 | 建议边界 |
| --- | --- | --- | --- | --- | --- |
| AUD-GOV-002 | usage audit / GUI support | checks、bridge 直接引用 core 实现文件 | 4 个 `private_module_import` | core 文件移动或私有符号变化会跨模块破坏 | 从 `core/__init__.py` 或 contracts 暴露最小稳定接口 |
| AUD-SIZE-001 | MaterialGUI / Editor create | 两个打包 C# 文本资源承载多职责 | C# 内容由 Python 原样注入/编译 | 任一改动需重跑安装、编译、Inspector/Editor E2E | 保持资源入口名，内部按职责拆成可组合资源 |

## 项目成熟度

等级：`L0 缺失`、`L1 临时`、`L2 可重复`、`L3 标准化`、`L4 可度量`。

| 维度 | 等级 | 当前机制 | 证据 | 主要缺口 |
| --- | --- | --- | --- | --- |
| 需求与追溯 | L2 | FR/CR/BUG/TASK/REG/REL + CSV | 文档体系完整 | strict 25 条双向断链、2 条 TASK 验证字段缺 REG |
| 架构与模块 | L2 | module-map、technical-route、公共接口约定 | 模块边界清晰、零运行时依赖 | 4 个跨模块私有导入；CodeGraph 未初始化 |
| 构建 | L3 | uv.lock、Hatchling、可复现包 | lock check、CI package、隔离安装 | 配置和生成脚本仍需与正式 release 一致复验 |
| 自动化测试 | L3 | pytest + 36 条 REG catalog | 223 passed/3 skipped、70 条定向测试 | 三个真实 bridge 用例依赖环境变量，未常态执行 |
| CI | L3 | 双 Python verify、package、artifact | run 33625061100 三 job 全绿 | Node action runtime 弃用警告 |
| 目标 Editor E2E | L2 | 条件 pytest + 当前实例人工验收 | v2 创建/recompile/Inspector 已成功 | v2 新进程、目标平台、最终渲染缺失 |
| UI/无障碍 | L2 | 固定 MaterialGUI + 呈现契约 | 中文标签/说明、折叠、Tooltip 当前实例通过 | skin/缩放/长文本/键盘焦点矩阵缺失 |
| 发布与回滚 | L2 | 私有 Release、SBOM/hash、安装/回滚说明 | v0.1.0 正式；0.2.0 候选 artifact | 版本错位、REL 新结构门禁 19 项失败 |
| 安全 | L2 | loopback 默认、远程 opt-in、脱敏、SECURITY | 安全测试与静态策略 | 支持版本仍写 0.1.x；宿主外部进程 argv 可能暴露凭证 |
| 供应链 | L2 | 生产依赖 0、lock、固定 Action、SBOM | supply-chain check 通过 | 在线告警状态与 0.2.0 正式全载荷清单未闭环 |
| 可观测性 | L2 | 单行 JSON、稳定错误码、saved/changed | CLI 契约测试 | 非服务型项目无长期 SLO；MCP 超时仍是未知完成状态 |
| 文档治理 | L2 | README、Skill、架构/质量/发布文档 | 功能说明与运行边界较完整 | 严格检查规则升级后基线未同步 |

- 总体成熟度与依据：**L2（可重复），局部 L3**。核心功能不是“不可用”，而是主链路最低等级由目标 Editor E2E、视觉验收、正式发布和严格治理共同决定；这些门禁尚未统一为每次发布都能重复执行且全部通过的标准流程。

## 回归验证机制

| 检查项 | 当前机制 | 自动化/CI | 覆盖 | 证据 | 缺口 |
| --- | --- | --- | --- | --- | --- |
| 核心模块与 CLI | pytest + REG catalog | 本地/CI 自动 | 解析、写入、图安全、GUI 合同、bridge mock | 223 passed/3 skipped；REG 36/36 | strict 治理失败未作为一致绿门禁 |
| 跨模块链路 | CLI 契约 + 定向测试 | 70 条高价值测试 | create/custom-gui/gui-support/editor spec | 定向通过 | 私有导入使架构契约与实现不一致 |
| 目标 Editor | bridge marker + 人工当前实例 | 条件自动/人工 | 创建、重编译、Inspector | 同会话已验 | 新进程、目标平台和最终渲染未跑 |
| UI 回归 | C# 资源测试 + 人工截图/确认 | 部分 | Tooltip、HelpBox、折叠、中文显示名 | 当前实例通过 | 无系统化皮肤/缩放/输入矩阵 |
| 发布前回归 | CI verify/package + hash/SBOM | 远端自动 | wheel/sdist 安装与供应链 | 0.2.0 artifact 已验证 | 正式 tag/Release 与 REL 门禁未闭环 |
| 失败留痕、Test-Fix Loop、回滚与复盘 | BUG/REG/timeline/REL + `.bak` | 部分自动 | 代码回归、文件恢复、包回滚 | BUG-0017/0018 已闭环 | 新 REL schema 与追溯回写不一致 |

## OpenSpec 规范管理

| 状态 | 结论 | 证据 |
| --- | --- | --- |
| 工具、项目配置、实际使用、规范一致性、strict 校验 | 未发现项目配置 | OpenSpec 1.7.0 可执行，但仓库没有 `openspec/`；当前以架构总纲、CR/ADR/traceability 为事实源，本次审计不初始化。 |

## CodeGraph 使用情况

| 状态 | 结论 | 证据 |
| --- | --- | --- |
| 安装、初始化、索引新鲜度、实际使用、更新机制 | 降级 | CodeGraph 可执行但项目状态为 `Not initialized`；本轮使用 `rg`、Python AST、module-map 与 Project Architect fitness 替代，不宣称图谱证据。 |

## 文档增量与变更留档

| 变更类型 | 载体/机制 | 增量历史 | 关联键 | 字段完整性 | 抽样证据与缺口 |
| --- | --- | --- | --- | --- | --- |
| 需求变更 | architecture + traceability + timeline | 有 | FR/CR/BUG/TASK/REG | 部分 | CR-0012/FR-0011 已记录属性呈现契约；25 条双向追溯失败 |
| 技术变更 | technical-route + module-map + ADR | 有 | ADR/CR/TASK | 部分 | EditorGraphSpec v2、GUI provider 有记录；部分模块未回链新 CR/BUG |
| 文件修改记录 | Git + task charter + timeline | 有 | commit/TASK/BUG | 部分 | main 与 origin/main 同步；TASK-0026/0028 验证字段缺 REG |
| 发布记录 | REL-0001/REL-0002 + GitHub | 有 | REL/CR/FR/BUG/tag/run | 部分 | 旧 REL 结构不满足当前模板，发布检查 19 项失败 |

## 功能模块闭环度

- 模块统计：发现数：14；已审计数：14；未覆盖数：0
- 清单校准：复用历史 9 个稳定 FM ID，并通过 supplement 新增 `FM-2E47AA5409`、`FM-35114E2780`、`FM-DB13C6D6D8`、`FM-3EEC4BD8D5`、`FM-14E9E4031E`；没有排除模块。

| 模块 ID | 模块/能力 | 需求/入口 | 主路径/关键链路 | 数据/状态闭环 | 异常/恢复 | 日志/可观测性 | 回归/验收 | 发布证据 | 结论 | 问题 ID |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FM-0E60A4DD1B | parse-serialize | FR-0001 / `parse` | file → AseFile/AseGraph → serialize | roundtrip/CRLF 回读 | PARSE/NOT_FOUND 失败关闭 | 单行 JSON 摘要 | roundtrip + 真实两 Shader parse | 0.2.0 wheel smoke | 已闭环 | 不适用 |
| FM-9040886B90 | graph-mutation | FR-0002 / set/add/connect/disconnect/remove | CLI → graph_ops → 写前 validate → atomic write | 不变量、CHKSM、`.bak` 回读 | 重复 ID/端口/外部消费拒绝 | written/path/code | graph-safety/mutate | 0.2.0 artifact | 已闭环 | 不适用 |
| FM-8ADC52C2A4 | schema-library | FR-0002 / `add-node` | schema_for → version gate → node line | 字段数/版本一致 | unknown/opaque/跨版本拒绝 | warnings/error code | schema samples/add | wheel 内 schemas.json | 已闭环 | 不适用 |
| FM-C73F236CD5 | validation-checksum | FR-0003 / validate/fix-checksum | checks → issue JSON/显式写回 | error_count/exit code/checksum 回读 | 默认 dry-run、`.bak` | issues/error_count/written | graph safety + 真实目标 0 error | wheel validate smoke | 已闭环 | 不适用 |
| FM-F03DFA9A41 | layout | FR-0008 / `layout` | graph → staged columns → position write | 仅位置变化、连线不变 | 环/无根确定性降级 | moved/written JSON | layout/perf 结构测试 | wheel 包含模块 | 部分闭环 | AUD-FLOW-003 |
| FM-3537DE9938 | create-from-template | FR-0005 / `create` text | shell + donor graph → presentation gate → checksum | Shader 名/图/属性回读 | exists/force/契约不合规拒绝 | created/name/contract | create/property-presentation | 0.2.0 candidate | 已闭环 | 不适用 |
| FM-DF0669A019 | recompile-bridge | FR-0004 / `recompile` | hash → MCP → saved/changed → hash | tool result + 文件哈希 | RPC/tool/未知响应 BRIDGE_ERROR | 脱敏 JSON | bridge mock + 同会话真实重编译 | 资源随 wheel | 已闭环 | 不适用 |
| FM-1DB3E4EA8B | cli-contract | FR-0007 / 15 命令 | argparse → handler → envelope | 成功/失败与退出码固定 | usage/business/internal 分类 | stdout JSON/stderr 脱敏 | CLI contract + NOT_FOUND exit 2 | wheel console script | 已闭环 | 不适用 |
| FM-25E63BD4F6 | agent-skill | FR-0006 / SKILL.md | Agent → CLI → validate → recompile | 每步回读/显式写入 | 失败即停、备份恢复 | 依赖 CLI JSON | Skill/REG 与历史 Editor E2E | 随仓库和源码包 | 已闭环 | 不适用 |
| FM-2E47AA5409 | graph-audit | FR-0010 / `graph-audit` | graph + external consumers → 分类候选 | candidate/read-only 输出 | 外部消费者保护、无写盘 | 分类 JSON | usage/local-var 测试；目标 Receiver 10 候选 | 0.2.0 candidate | 已闭环 | 不适用 |
| FM-35114E2780 | custom-gui-property-presentation | FR-0009/0010/0011 / `custom-gui` | 属性 → 原子 spec → 图/编译标签与 metadata 对账 | 逐属性 valid/violations 回读 | 重复/未知/不合规整批拒写 | property-presentation v1 JSON | 两真实 Shader 7 属性零违规 | 0.2.0 candidate | 已闭环 | 不适用 |
| FM-DB13C6D6D8 | gui-support-material-inspector | FR-0009/CR-0010 / `gui-support` | project → provider 检查/安装 → Inspector | 安装状态与呈现契约回读 | 冲突拒绝、旧标记只读兼容 | provider/installed/valid | 临时工程安装 + 当前实例 Tooltip | 资源随 0.2.0 wheel | 已闭环 | 不适用 |
| FM-3EEC4BD8D5 | comment-group | FR-0010 / `comment-group` | nodes → CommentaryNode tree → live/estimated bounds | 成员树、CHKSM、边界回读 | 重复归属/重叠/非法标题拒绝 | groups/issues JSON | commentary 结构测试 | 0.2.0 candidate | 部分闭环 | AUD-FLOW-003 |
| FM-14E9E4031E | editor-api-create | FR-0005/CR-0012 / `create --backend editor` | v2 spec → ASE API → Save/Load manifest → presentation → recompile | staging/target/manifest/reconciliation | timeout unknown、失败回滚/后验保留 | bridge JSON/manifest | 当前实例 v2 创建与 Inspector | 0.2.0 candidate，未正式发布 | 部分闭环 | AUD-FLOW-002 |

### 前端功能入口闭环

- 入口统计：发现数：15；已审计数：15；未覆盖数：0
- 清单校准：无人工新增或排除；自动发现的 15 个 argparse 子命令全部逐项对账。

| 入口 ID | 页面/入口与类型 | 条件/权限 | 目标/handler | 状态覆盖 | 返回/恢复 | 测试/运行证据 | 结论 | 问题 ID |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FE-5FE7C39BCC | `parse` CLI | 文件可读 | cmd_parse | success/usage/not-found/parse-error | 只读修复后重试 | CLI tests + wheel smoke | 已闭环 | 不适用 |
| FE-5F33E87610 | `set-field` CLI | 文件可写、字段可变 | cmd_set_field | dry-run/write/结构字段拒绝 | `.bak` 恢复 | mutate/graph-safety | 已闭环 | 不适用 |
| FE-37BA87FA15 | `add-node` CLI | schema/version 或真实 raw line | cmd_add_node | schema/unknown/opaque/version | 默认 dry-run、`.bak` | schema-add | 已闭环 | 不适用 |
| FE-C3162CA2E1 | `connect` CLI | 两端/端口有效 | cmd_connect | dry-run/write/重复输入 | `.bak` | graph-safety | 已闭环 | 不适用 |
| FE-AAF53AF86F | `disconnect` CLI | 连接存在 | cmd_disconnect | dry-run/write/not-found | `.bak` | CLI/graph tests | 已闭环 | 不适用 |
| FE-0018A7D5D8 | `remove-node` CLI | 节点存在；外部消费需显式确认 | cmd_remove_node | dry-run/write/external reject | 线清理、`.bak` | usage/graph tests | 已闭环 | 不适用 |
| FE-50D4B549C6 | `graph-audit` CLI | 文件可读，可选工程根 | cmd_graph_audit | used/external/unused/error | 只读人工确认 | usage tests + 真实 Receiver | 已闭环 | 不适用 |
| FE-BBB0F9830B | `validate` CLI | 文件可读 | cmd_validate | 0 error/error exit 2 | 只读修正后重试 | 真实两 Shader 0 error | 已闭环 | 不适用 |
| FE-369C790BD8 | `fix-checksum` CLI | 写入需 `--write` | cmd_fix_checksum | preview/write/invalid | `.bak` | checksum tests | 已闭环 | 不适用 |
| FE-C71A570BA7 | `layout` CLI | 图可解析 | cmd_layout | dry-run/write/cycle | `.bak`；人工画布复核 | layout/perf；真实画布未复验 | 未验证 | AUD-FLOW-003 |
| FE-4E1B79DEE4 | `custom-gui` CLI | 19602 属性尾部；写入需 `--write` | cmd_custom_gui | inspect/spec/clear/invalid | 原子拒写、`.bak` | GUI/property tests + 真实资产 | 已闭环 | 不适用 |
| FE-1E3A6EB7E7 | `gui-support` CLI | 团结工程路径；安装需显式标志 | cmd_gui_support | inspect/install/conflict | 备份/冲突拒绝 | 临时工程安装与当前实例 | 已闭环 | 不适用 |
| FE-222ADDDF1D | `comment-group` CLI | 图可解析；live 操作需 MCP | cmd_comment_group | query/create/nest/check/fit | dry-run、`.bak`、拒绝重叠 | commentary tests；live bounds 未复验 | 未验证 | AUD-FLOW-003 |
| FE-B537BBBC81 | `create` CLI | template/donor 或 v2 spec；out 可写 | cmd_create | text/editor/auto/exists/contract error | 回滚或后验保留、检查 temp | create/editor spec + 当前实例；新进程未验 | 未验证 | AUD-FLOW-002 |
| FE-3F4DBCA0D3 | `recompile` CLI | loopback MCP；远程显式授权 | cmd_recompile | changed/unchanged/RPC/tool error | BRIDGE_ERROR/3、按未知状态检查 | mock + 当前实例真实重编译 | 已闭环 | 不适用 |

## 交互流程与 UI

### Product Design 参与情况

| 检查项 | 结论 | 证据/限制 |
| --- | --- | --- |
| 历史参与证据、本次调用、当前截图、视觉结论等级 | 本次未调用 | 本任务是证据审计而非重新设计；沿用当前真实 Inspector 截图/用户确认作为抽样证据，只给出“部分验证”，不外推完整 UI 合规。 |

### 关键流程证据

| 步骤 | 用户目标/操作 | 截图或运行证据 | 健康度 | UX/可访问性问题 | 证据限制 |
| --- | --- | --- | --- | --- | --- |
| 01 | 使用 v2 spec 创建 Sampler/RangedFloat 图 | 当前团结实例 Save/Load、manifest、reconciliation 零差异 | 良好 | 机器 spec 错误信息清楚 | 未新进程重开 |
| 02 | 独立 recompile 并打开临时材质 Inspector | 中文显示名/说明可见 | 良好 | HelpBox 信息明确 | 只覆盖当前 skin/缩放 |
| 03 | 悬停两个属性 | 用户现场确认两个 Tooltip 气泡正常 | 良好 | 技术信息包含变量名与默认值 | 非自动截图门禁 |
| 04 | 治理 VehicleLocalShadow 两 Shader | Caster/Receiver 契约有效、0 violation、validate 0 error | 良好 | 真实属性一致 | 未验证最终阴影画面 |
| 05 | 自动布局/Comment | 结构测试与规范齐备 | 有风险 | 可能存在穿节点/标题栏、边距或长线可读性问题 | 本轮未获取 normal zoom 画布证据 |

### UI 检查

| 页面/区域 | 层级与清晰度 | 一致性/状态 | 响应式 | 键盘/焦点/语义 | 问题 ID |
| --- | --- | --- | --- | --- | --- |
| Material Inspector 标签/HelpBox | 中文标签与说明层次已抽样通过 | 两属性 Tooltip、折叠状态通过 | 长中文/窄 Inspector/缩放未验 | 键盘焦点与读屏语义未验 | AUD-UI-001 |
| ASE 节点画布 | 左到右列和 Comment 规范已定义 | 结构/成员/重叠状态可检查 | 真实节点尺寸需 Editor | 节点画布可访问性非当前核心目标 | AUD-FLOW-003 |
| CLI JSON | 单行 envelope 清晰 | 15 入口错误码/状态基本一致 | 终端宽度不影响机器解析 | 文本可复制、无交互焦点依赖 | 不适用 |

## 专项工程审计

| 专项领域 | 状态 | 核心证据 | 主要风险/缺口 | 问题 ID |
| --- | --- | --- | --- | --- |
| 安全与隐私 | 已验证 | loopback 默认、远程 opt-in、脱敏、零运行时网络服务 | `SECURITY.md` 支持版本滞后；宿主团结 Hub 启动参数存在敏感令牌暴露风险，属外部环境边界 | AUD-REL-001 |
| 性能与资源 | 已验证 | 大图 parse/layout 性能回归，生产运行依赖 0 | Editor API/Inspector 未做正式性能预算；当前无阻塞证据 | 不适用 |
| 可观测性与运维 | 已验证 | JSON code、error_count、saved/changed、manifest、CI/REL | MCP timeout 为未知完成状态，只能检查目标与临时资产后恢复 | AUD-FLOW-002 |
| 依赖、供应链与许可证 | 部分 | `uv.lock --check`、固定构建依赖、SPDX、supply-chain check | 在线告警不可持续查询；正式 0.2.0 全载荷清单未生成 | AUD-SUPPLY-002 |
| API、数据兼容与迁移 | 已验证 | schema version gate、EditorGraphSpec v2、旧 GUI 标记只读兼容 | 仅 ASE 1.9.6.2/已验证模板开放；未知版本失败关闭 | 不适用 |
| 无障碍与国际化 | 部分 | UTF-8 JSON、中文显示名/说明与当前实例 Tooltip | light skin、缩放、长文本、键盘/焦点/读屏未系统验证 | AUD-UI-001 |
| 构建可复现与产物完整性 | 部分 | CI artifact、wheel/sdist/SBOM、SHA256SUMS、隔离安装 | 正式 Release 仍为 v0.1.0；REL schema 与追溯未通过 | AUD-REL-001 |

## 增量审计对比

- 基线报告：`docs/05-audits/2026-09-01-132548-project-audit-report.md`
- 对比口径：同一项目的标准增量审计；基线为 9 FM/11 FE、79 passed/1 skipped，本轮为 14 FM/15 FE、223 passed/3 skipped。当前 strict 的新增发现一部分来自功能增长，一部分来自 Project Architect 规则升级后暴露的历史盲区，不能一概标作代码回归。

| 分类 | 问题 ID | 基线 -> 当前 | 证据/说明 |
| --- | --- | --- | --- |
| 改善 | 不适用 | 9 FM / 11 FE → 14 FM / 15 FE | 新增 graph-audit、GUI、属性呈现、Comment、Editor API 创建 |
| 改善 | 不适用 | 79 passed/1 skipped → 223 passed/3 skipped | 测试数量与 GUI/Editor/发布回归显著扩大 |
| 已解决 | 历史远程边界 | 无远端 CI/Release → v0.1.0 正式、0.2.0 候选 | CI、artifact、SBOM、哈希、隔离安装均已有真实证据 |
| 新增发现 | AUD-GOV-002 | strict 0 → 当前 50 项 | 当前检查器增加/收紧 kickoff、双向追溯、私有导入和 release-record 契约；含历史盲区暴露 |
| 新增发现 | AUD-GOV-003 | 旧配置曾被当作有效 → 字段漂移与扫描盲区 | `loc_thresholds` 未被当前脚本读取，tests/tools/.cs.txt 未进门禁 |
| 新增发现 | AUD-SIZE-001 | 未扫描 → 536/408 行生产 C# 资源 | 功能增长与扩展名盲区共同造成 |
| 新增发现 | AUD-FLOW-002 | 旧 text/editor v1 结构链路 → v2 属性契约链路部分 | 当前实例成功，但 v2 新进程与目标平台未验 |
| 新增发现 | AUD-FLOW-003 | layout 被判闭环 → 结构闭环、视觉部分 | 当前验收标准提高到 normal zoom 无穿节点/标题栏 |
| 新增发现 | AUD-REL-001 | v0.1.0 发布完成 → main 0.2.0 与正式版本错位 | 候选包可用但不是正式 Release |
| 新增发现 | AUD-UI-001 | UI 不适用 → Material Inspector 成为正式能力 | Tooltip 抽样通过，完整 UI/可访问性矩阵未建立 |
| 新增发现 | AUD-SUPPLY-002 | 离线门禁完整 → 线上与正式全载荷证据不足 | 低风险，因生产依赖仍为 0 |
| 新增发现 | AUD-CI-001 | 无告警记录 → Node runtime 弃用告警 | job 全绿，属于前瞻性维护 |

## 阻塞项

| 问题 ID | 阻塞内容 | 影响范围 | 证据 | 解除条件 |
| --- | --- | --- | --- | --- |
| AUD-GOV-002 | 严格治理/发布门禁未通过 | 不能把当前 main 宣称为治理合规正式版本 | 50 项：2 kickoff + 25 traceability + 4 fitness + 19 release | strict（含 release）零 error/warning 或有明确、有期限的例外 |
| AUD-FLOW-002 | v2 目标 Editor/平台闭环不完整 | 0.2.0 的核心新增创建能力 | 当前实例通过，但新进程/目标平台/最终渲染未验 | 在受控团结/ASE 中完成重开、编译、材质绑定和目标画面验收 |
| AUD-REL-001 | 0.2.0 尚未正式发布 | 试用者默认仍只能安装 0.1.0 | tag 仅 `v0.1.0`，README/SECURITY 明示当前正式版 0.1.x | 创建一致的 v0.2.0 tag/Release、全载荷校验与回滚证据 |

## 潜在风险

| 问题 ID | 风险 | 触发条件 | 影响 | 概率 | 应对建议 |
| --- | --- | --- | --- | --- | --- |
| AUD-RISK-001 | MCP 超时后迟到完成 | Editor 忙、插件重连、网络超时 | 重试可能重复创建或覆盖判断错误 | 中 | timeout 后先检查目标、manifest 与 `ASECLI-Temp-*`，不要立即重试 |
| AUD-RISK-002 | 宿主 argv 暴露敏感凭证 | 团结 Hub/外部插件把 token 放进启动参数 | 本机其他诊断进程或日志可能读到 | 中 | 结束当前 Hub 会话并重新登录，后续避免凭证进入 argv |
| AUD-RISK-003 | 0.2.0 文档/代码与 0.1.0 Release 混用 | 试用者按 main README 下载正式版 | 安装后缺少 v2/属性呈现能力 | 高 | 发布前在命令、README、SECURITY、REL 和 artifact 中统一版本 |

## 问题详情

### AUD-GOV-002 严格治理与发布门禁失效

- 状态：开放
- 证据状态：已验证
- 严重程度：S1
- 优先级：P1
- 影响范围：治理可信度、变更追溯、模块边界与正式发布判断
- 证据：Project Architect strict（含 release）得到 kickoff 2、traceability 25、fitness 4、release 19，共 50 项；不含 release 时仍有 31 项。
- 根因判断：仓库功能快速扩展后，TASK/模块/REG/REL 的双向回链没有同步满足新版检查器契约，且 checks/bridge 绕过公共面直接导入 core 实现。
- 优化做法：逐条修正源记录与反向链接；为 checks/bridge 暴露最小公共 contract；按当前 release-record 模板迁移 REL，不降低 strict 规则。
- 技术路径：复用现有 Markdown/CSV、`core/__init__.py`/contracts 和 Project Architect 校验器，不引入依赖。
- 验收标准：`--check-docs --check-kickoff --check-traceability --check-fitness --check-release --strict` 零发现，且 223 条现有测试不回归。
- 验证方式：strict JSON、REG catalog、定向 import contract、全量 pytest、`git diff --check`。
- 回滚/降级：文档修正可逐文件回退；公共 API 变更保留旧内部实现并只增加导出，若测试失败则停止模块导入替换。

### AUD-GOV-003 LOC 配置字段漂移与扫描盲区

- 状态：开放
- 证据状态：已验证
- 严重程度：S2
- 优先级：P1
- 影响范围：source/test/config LOC 门禁的真实性
- 证据：`.project-architect.json` 使用 `loc_thresholds`，当前检查器读取 `thresholds`；未设置 `source_roots`，默认不扫描 `tests/`、`tools/`；扩展名不含 `.txt`。
- 根因判断：Project Architect 配置 schema 升级后，仓库配置未迁移，旧检查结果被误认为覆盖全项目。
- 优化做法：迁移到 `thresholds`，显式列出 `src`、`tests`、`tools`；为打包 C# 资源建立可执行的扫描策略或专用检查器。
- 技术路径：只调整现有 JSON 配置与治理检查脚本/测试，保持阈值本身不变。
- 验收标准：测试和 tools 文件进入正确分类；`.cs.txt` 两资源不再漏扫；故意超限 fixture 能使 strict 失败。
- 验证方式：运行 LOC/strict JSON 并核对候选文件路径、类别、warning/limit；补充配置回归测试。
- 回滚/降级：保留迁移前配置快照；若 `.cs.txt` 无法安全纳入通用扩展名，使用项目专用只读检查而不是扩大所有 `.txt`。

### AUD-SIZE-001 生产 C# 资源超过项目硬上限

- 状态：开放
- 证据状态：已验证
- 严重程度：S2
- 优先级：P1
- 影响范围：Material Inspector、EditorGraphSpec 执行器的可维护性与回归爆炸半径
- 证据：`asecli_material_gui.cs.txt` 536 行、`editor_create.cs.txt` 408 行，均超过 source 400 行意图硬上限；当前因扩展名盲区未触发。
- 根因判断：C# 以 Python 包资源形式交付，多类职责持续叠加，但 LOC 门禁只识别真实 `.cs` 后缀。
- 优化做法：先建立资源拼装/编译回归，再按 provider/drawer/default formatting 与 session/spec/manifest 职责拆分；如暂不拆，登记有到期日的 ADR 例外及补偿测试。
- 技术路径：复用 `importlib.resources`/现有安装器拼装多个固定资源，不改变 CLI、namespace 与安装目标。
- 验收标准：每个生产资源单元不超过 400 行或存在合规 ADR 例外；安装后的 C# 编译、Tooltip/HelpBox、Editor create/rollback 行为不变。
- 验证方式：资源内容/顺序测试、临时工程编译、相关 pytest、当前支持版本真实 Inspector/Editor E2E。
- 回滚/降级：保持旧单文件资源可恢复；拼装异常时回退上一已验证资源并阻止发布。

### AUD-FLOW-002 EditorGraphSpec v2 缺正式运行闭环

- 状态：开放
- 证据状态：已验证
- 严重程度：S1
- 优先级：P1
- 影响范围：0.2.0 新增属性呈现强制契约与真实 ASE 图创建
- 证据：当前团结 `2022.3.61t9` + ASE `1.9.6.2` 已完成 v2 创建、独立 recompile、Inspector 与 Tooltip；`test_editor_create_e2e.py` 本轮因缺隔离工程/团结路径跳过，且 v2 新进程重开、目标平台编译/材质绑定/最终画面未执行。
- 根因判断：真实 Editor E2E 成本高且依赖 GUI 生命周期，尚未转成发布前固定、可恢复的验收脚本和证据包。
- 优化做法：在受控工程执行 v2 create→close→新进程 reopen→parse/manifest→recompile→平台编译→材质绑定→渲染验收，并清理临时资产。
- 技术路径：复用现有 bridge marker、EditorGraphSpec、manifest/reconciliation 与团结命令行；目标画面采用项目已有金样或明确人工签收。
- 验收标准：新进程重开后节点/线/属性/GUI 契约一致，0 Shader/CS error，目标平台编译和材质绑定成功，最终渲染由证据或用户签收确认，临时资产为零。
- 验证方式：条件 bridge pytest、Editor log、前后 manifest/hash、目标平台构建日志、截图/签收记录。
- 回滚/降级：只在隔离或明确授权工程运行；失败时恢复备份、清理 staging/临时材质，不覆盖既有生产资产。

### AUD-FLOW-003 布局与 Comment 缺可重复视觉门禁

- 状态：开放
- 证据状态：已验证
- 严重程度：S2
- 优先级：P1
- 影响范围：`layout`、`comment-group` 的实际可读性
- 证据：结构测试覆盖确定性、成员树、重叠和离线估算；普通节点真实尺寸、贝塞尔线路径、无穿节点/端口/标题栏和 normal zoom 画布未形成本轮可复验结果，live bounds 未重跑。
- 根因判断：ASE 文本不保存所有真实 GUI 尺寸/线路径，纯结构算法无法替代 Editor `TruePosition` 和正常缩放视觉判断。
- 优化做法：建立代表性小/中/复杂图金样，在 Editor 读取 live bounds、执行 fit，并保存 normal zoom 画布截图与无穿越检查结果。
- 技术路径：复用 `comment-group --editor-bounds/--check-bounds/--fit` 和布局规范；只移动节点/Comment，不改变参数、连接或计算。
- 验收标准：重复阶段列对齐、Comment 不重叠/完整包含、连线不穿无关节点/端口/标题栏，normal zoom 可读；结构 hash 除位置/Comment 外不变。
- 验证方式：结构 diff、live bounds JSON、ASE 画布截图人工复核、相关 pytest。
- 回滚/降级：保留 `.asecli-backups` 和 `.meta` hash；视觉不达标时恢复位置/Comment，禁止自动改计算图。

### AUD-REL-001 0.2.0 正式发布断点

- 状态：开放
- 证据状态：已验证
- 严重程度：S1
- 优先级：P1
- 影响范围：内部试用安装、版本支持、安全响应与回滚
- 证据：`pyproject.toml` 和 CI artifact 为 0.2.0，tag/私有 Release 仅 `v0.1.0`；README 明确 0.2.0 尚未发布，`SECURITY.md` 仍仅支持 0.1.x；release strict 有 19 项。
- 根因判断：0.2.0 代码和候选产物已推送，但正式发布授权/验收与新版 REL 记录迁移尚未合并成单一门禁。
- 优化做法：先关闭 P1 治理和运行验收，再生成覆盖所有 Release 载荷的校验清单、更新支持范围/安装文档/REL，创建固定 commit 的 v0.2.0 tag 与私有正式 Release。
- 技术路径：复用 GitHub Actions、GitHub Release、uv tool、SBOM 和 SHA-256，不上传 PyPI/公开 Hub。
- 验收标准：v0.2.0 tag 指向审计通过 commit；Release 非 draft/prerelease；所有载荷下载校验；隔离安装列出 15 命令并完成 parse/custom-gui smoke；上一版可回滚。
- 验证方式：远端 run/Release URL、tag commit、asset 清单与 digest、隔离 Python 3.12 安装/卸载/回滚、strict release 零发现。
- 回滚/降级：发布失败不移动既有 v0.1.0；错误 Release 立即撤下/标记并通知试用者，按已验证 v0.1.0 wheel 回滚。

### AUD-UI-001 Inspector 验收矩阵不完整

- 状态：开放
- 证据状态：已验证
- 严重程度：S2
- 优先级：P1
- 影响范围：美术使用 Material Inspector 时的可读性、一致性与输入可达性
- 证据：当前实例已验证中文标签/说明、折叠和两个 Tooltip；没有 light skin、不同缩放/宽度、长中文换行、键盘/焦点、disabled/mixed-value 等系统证据。
- 根因判断：自定义 GUI 从辅助兼容能力升级为正式产品能力后，验收仍以单实例人工抽样为主。
- 优化做法：定义最小 UI 矩阵与代表性材质 fixture，逐项验证标签、Tooltip、HelpBox、折叠、默认值、长文本和焦点行为。
- 技术路径：复用当前 MaterialGUI、团结 Editor 测试和真实截图，不重新设计 Inspector。
- 验收标准：dark/light、100%/高缩放、窄/常规宽度、长中文、键盘导航/焦点与 mixed-value 状态均有结果；阻塞项修复后回归通过。
- 验证方式：Editor 自动断言可自动部分 + 标注环境的真实截图/人工清单；属性契约 JSON 继续 0 violation。
- 回滚/降级：任何呈现修复保持 Shader property/默认值不变；不能保证可用时回退上一 GUI 资源。

### AUD-SUPPLY-002 正式供应链在线与全载荷证据不足

- 状态：开放
- 证据状态：推断
- 严重程度：S3
- 优先级：P2
- 影响范围：正式 0.2.0 资产完整性和持续漏洞响应
- 证据：本地供应链检查通过且生产依赖为 0；当前无法确认 Dependabot/在线漏洞告警的持续状态，0.2.0 只有候选 artifact 内 wheel/sdist 清单。
- 根因判断：离线构建验证已成熟，但在线状态和正式 Release 全载荷清单只有在发布阶段才能最终生成/回读。
- 优化做法：发布时对 wheel、sdist、SBOM、供应链报告及清单自身之外的全部载荷生成根目录文件名清单，并记录在线告警查询结果。
- 技术路径：复用现有 `sha256sum`/Python 哈希脚本、GitHub security/release API。
- 验收标准：所有正式载荷均可由下载后的单一清单验证；在线告警状态有时间戳和权限边界；无凭证进入日志。
- 验证方式：全量下载到空目录后 `sha256 -c` 等价检查、SBOM name/version、GitHub 安全页/API 只读证据。
- 回滚/降级：在线 API 不可用时明确标为未验证，不阻止零生产依赖的本地构建，但不能宣称线上扫描通过。

### AUD-CI-001 GitHub Actions Node runtime 弃用告警

- 状态：开放
- 证据状态：已验证
- 严重程度：S3
- 优先级：P2
- 影响范围：未来 GitHub runner 对 checkout/setup action 的兼容性
- 证据：run 33625061100 全绿，但日志包含 Node.js 20 弃用并强制改用 Node 24 的警告。
- 根因判断：固定 action 版本/SHA 所带运行时落后于 GitHub runner 的迁移节奏。
- 优化做法：选择明确支持 Node 24 的官方 action 版本并固定完整 SHA，同时更新 CI governance allowlist/断言。
- 技术路径：只升级相关 action，不升级 Python 依赖或改 CI 任务结构。
- 验收标准：新 run 三个 job 全绿、无 Node 20 弃用警告、固定 SHA 与治理检查通过、artifact digest 可复验。
- 验证方式：CI 日志、workflow diff、`check_ci_governance.py`、artifact 安装 smoke。
- 回滚/降级：新 action 行为异常时恢复旧 SHA，并在 GitHub 强制切换前保留风险记录与到期日。

## 验证记录

| 命令/检查 | 目的 | 结果摘要 | 是否通过 |
| --- | --- | --- | --- |
| `audit_project.py collect ... --mode standard --supplement ...` | 全量静态采证 | 308 indexed、127 text、truncated=false、14 FM、15 FE | 是 |
| `uv lock --check` | 锁文件一致性 | 通过 | 是 |
| `uv run --frozen pytest -q` | 当前全量回归 | 223 passed、3 skipped | 是（真实 bridge 有边界） |
| 70 条高价值定向测试 | 核心新增能力回归 | 70 passed | 是 |
| `tools/check_regression_catalog.py` | REG 可执行性 | 36/36 | 是 |
| `tools/check_ci_governance.py` | CI 静态治理 | 通过 | 是 |
| `tools/supply_chain_check.py` | 依赖/供应链 | 通过；生产运行时依赖 0 | 是 |
| Project Architect strict（不含 release） | kickoff/追溯/fitness | 2 + 25 + 4 = 31 项发现 | 否 |
| Project Architect strict（含 release） | 完整治理与发布 | 31 + 19 = 50 项发现 | 否 |
| 当前目标两 Shader 只读 CLI 检查 | 真实资产结构/属性契约 | 19602；11/28 nodes；0 validate error；7 属性 0 violation | 是 |
| GitHub Actions run 33625061100 + artifact 9844457577 | 0.2.0 候选交付 | 3 jobs green；artifact digest 与内部清单、SBOM、隔离安装通过 | 是（候选） |
| CodeGraph status | 依赖图证据 | `Not initialized` | 降级 |

## 计划外发现

- 宿主团结 Hub 的启动参数可能携带敏感令牌；本报告已完全脱敏且不再采集完整进程参数。建议用户结束当前团结/Hub 会话并重新登录，使现有会话凭证失效。该问题属于外部运行环境，不纳入 ASECLI 代码整改。
- Receiver 的 `graph-audit` 返回 10 个 unused candidates；它们需要结合 HLSL/材质/设计意图人工确认，本轮不擅自删除，也不判为 ASECLI 缺陷。

## 遗留问题

- 9 个开放问题均已映射到同时间戳优化任务书；本轮只审计，不实施整改、提交、推送或正式发布。
- 0.2.0 候选具备安装试用条件，但在 AUD-GOV-002、AUD-FLOW-002、AUD-REL-001 关闭前，不应宣称达到完整正式发布门槛。

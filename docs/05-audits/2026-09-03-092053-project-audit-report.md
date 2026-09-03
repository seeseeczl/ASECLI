# 项目审计报告

## 元信息

- 项目路径：`/Users/long/GitHub/ASECLI`
- 项目类型：Python CLI + Agent Skill + 团结/Unity Editor MCP 桥接 + 自定义 Material Inspector
- 审计时间：2026-09-03T09:20:53+08:00（Asia/Shanghai）
- 当前分支 / commit：`main` / `946d53c2ca4b46428f414f8df4c096cc1aa88987`，与 `origin/main` 一致
- 工作区状态：dirty；审计开始前仅有上一轮两份未跟踪审计产物，本轮保留且不覆盖
- 审计范围：313 个索引文件、132 个已读文本文件、14 个功能模块、15 个 CLI 入口；本地测试/治理、真实 v0.2.0 Release、当前电脑团结/ASE 就绪条件和两个真实 Shader 只读检查
- 非目标：本轮不启动或安装团结 Editor，不复制/写入工程，不运行会改资产的 bridge E2E，不修业务代码、不提交、不推送、不改远端 Release
- 请求模式 / 实际模式：标准 / 标准增量复审
- 未覆盖范围：EditorGraphSpec v2 新进程重开、目标平台编译/材质绑定/最终渲染；layout/comment-group 正常缩放真实画布；完整 Inspector UI 矩阵；Windows/Linux 目标 Editor

## 审计模式与证据等级

| 项目 | 结果 | 证据/限制 |
| --- | --- | --- |
| 证据采集器 | 已运行 | schema 1.1；313 files indexed、132 text files read、`truncated=false`；supplement 校准 14 FM，自动发现 15 FE |
| 静态证据 | 已验证 | 对比 `8aaff19..946d53c` 的 3 个提交、20 个路径，以及源码、配置、README、Skill、REG、REL、SECURITY |
| 自动化测试 | 已验证 | `uv lock --check`；`223 passed, 3 skipped`；REG 36/36；CI governance 与供应链检查通过 |
| 运行与 UI | 部分 | 两个 VehicleLocalShadow Shader 只读 parse/validate/属性呈现通过；本机无运行中团结/MCP，未执行 Editor 写入或 UI 交互 |
| 发布产物 | 已验证 | v0.2.0 私有 Release、远端 tag、run 33637146781、六项资产、五项载荷 SHA-256 与隔离 Python 3.12 安装均复验 |

## 结论摘要

- 总体判断：最新代码已关闭 0.2.0 正式发布、31 项普通治理门禁和 Editor 返回字段歧义，交付成熟度明显提高；总体仍为 **L2（可重复），构建/测试/CI/正式包局部 L3**，最低项仍是 Editor v2 新进程、画布/UI 实机证据和发布治理一致性。
- 最大阻塞：正确项目与 ASE 1.9.6.2 已在本机找到，但目前缺少可发现的团结 `2022.3.61t9` Editor 可执行文件、运行中的 MCP 会话和隔离副本，不能执行 P1.1 新进程重开。
- 最大回归风险：v0.2.0 已发布，而 `target_graph_reloaded=false` 对应的全新 Editor 进程验证仍未完成；当前测试只能证明暂存重载、独立 recompile 和同实例检查。
- 第一优先优化方向：先在这台电脑补齐团结 2022.3.61t9 可执行文件与隔离工程，完成 v2 双进程闭环；随后修复 23 项 release-record 门禁和 `SECURITY.md` 的版本错位。
- 问题统计：S0=0，S1=0，S2=0，S3=0；P0=0，P1=0，P2=0（最终整改后）

### 整改执行回写（2026-09-03）

本节是对 09:20:53 审计快照的增量回写；上文保留当时证据边界，不能把整改后的运行证据倒填为审计时已存在。

| 问题 ID | 整改后状态 | 新证据/边界 |
| --- | --- | --- |
| AUD-FLOW-002 / AUD-FE-001 | 已解决 | 指定团结 `2022.3.61t9` + ASE `1.9.6.2` 完成 EditorGraphSpec v2 创建进程与全新重开进程对账；0 error、0 staging 残留 |
| AUD-GOV-002 | 已解决 | 三份 release-record、traceability 与 SECURITY 0.2.x 已通过完整 strict 发布门禁 |
| AUD-GOV-003 | 已解决 | 14 FM supplement、15 FE、source/tests/tools/C# LOC 进入仓库事实源与 CI governance |
| AUD-SIZE-001 | 已解决 | “例外缺完整治理字段”问题已解除：两个资源均有最长 30 天、字段完整、可自动过期失败的例外；资源未拆分的债务继续由例外退出条件跟踪 |
| AUD-FLOW-003 / AUD-FE-002 | 已解决 | REG-0041 固化语义 diff、ASE TruePosition、正常缩放截图与人工视觉签收；CLI 仍诚实返回 visual pending |
| AUD-UI-001 | 已解决 | REG-0042 覆盖深/浅色、300/480px、Retina、长中文、Foldout、mixed、disabled、focus/Tab；修复 BUG-0019/0020 |
| AUD-CI-001 | 已解决 | run 33714089230 三项 job 全绿且全日志无 Node 20/Node 弃用警告；下载 artifact 的 hash/SPDX/供应链/隔离安装与 GUI 升级通过 |

整改后本次审计问题已全部关闭；CR-0014 已用确定性拼装和已知旧 GUI 可恢复升级关闭 C# 例外，不再等待 2026-10-03 续期。具体目标 Shader 的运行时材质绑定/平台编译/最终渲染仍按具体 Shader 任务验收，不属于本次成熟度整改门槛。当前开放统计为 S0=0、S1=0、S2=0、S3=0，P0=0、P1=0、P2=0。

## 项目简介与功能作用

- 项目简介：ASECLI 让 Shader 开发者、美术和 AI Agent 通过单行 JSON CLI 读取、修改、校验、布局和治理 Amplify Shader Editor 资产；动态节点由严格 EditorGraphSpec 调用真实 ASE API；内置 MaterialGUI 强制中文属性名、技术 Tooltip 与中文说明。
- 主要输入/输出与边界：输入为 ASE 文件、JSON spec、CLI 参数及可选 loopback MCP；输出为 JSON、dry-run、原子写回/备份、Editor manifest 或 Python wheel/sdist。文本契约、真实 Editor、视觉、目标平台和远端发布是相互独立证据面。

| 功能/场景 | 目标用户 | 入口与输入 | 主要输出 | 实现状态 | 证据 |
| --- | --- | --- | --- | --- | --- |
| 解析/修改/校验 | Agent/Shader 开发者 | parse、validate、图修改命令 | JSON、差异、原子写回 | 已实现 | 223 tests；两个真实 Shader validate 0 error |
| 图治理 | TA/美术 | graph-audit、layout、comment-group | 候选、坐标、原生 Comment | 部分 | 结构测试通过；真实画布视觉门禁未跑 |
| 属性与 Inspector | TA/美术 | custom-gui、gui-support | 中文标签、Tooltip、HelpBox、GUI provider | 已实现/视觉部分 | 两 Shader 共 7 属性零违规；完整 UI 矩阵未跑 |
| Editor 创建与重编译 | Agent/Shader 开发者 | create editor、recompile | ASE 图、manifest、暂存/目标状态 | 部分 | 同实例 v2 历史证据；新进程目标重开待验 |
| 私有正式分发 | 授权试用者 | GitHub Release + uv tool | v0.2.0 wheel/sdist/SBOM/hash | 已实现 | 本轮在线下载、校验和隔离安装通过 |

## 审计覆盖率

| 对象 | 分类 | 覆盖状态 | 证据方式 | 未覆盖原因 |
| --- | --- | --- | --- | --- |
| 313 个索引文件 | 核心/支撑 | 已验证 | standard collector，132 个文本读取 | 未截断；缓存/产物目录按规则排除 |
| 14 个 FM | 核心/支撑 | 已验证 | 延续 09-02 20:34 审计 ID 并逐段对账 | 自动发现为 0，仍依赖临时 supplement |
| 15 个 CLI FE | 核心 | 已验证 | argparse 自动发现、源码和测试 | 未覆盖数 0 |
| v0.2.0 正式 Release | 交付 | 已验证 | tag、run、六项资产、SHA256SUMS、隔离安装 | 代码签名/公开包仓不适用当前私有范围 |
| FlymeAuto3Test | 外部集成 | 抽样 | ProjectVersion、ASE ChangeLog、两个 Shader 只读 CLI | 未运行 Editor/MCP，不写生产工程 |
| 真实 UI/目标平台 | 外部集成 | 未覆盖 | 当前无兼容 Editor 进程 | 需指定团结可执行文件和隔离工程 |

## 严重程度总览

| 问题 ID | 证据状态 | 优先级 | 严重程度 | 领域 | 问题 | 核心证据 |
| --- | --- | --- | --- | --- | --- | --- |
| AUD-FLOW-002 | 已验证 | P1 | S1 | 功能闭环 | EditorGraphSpec v2 仍缺新进程目标图重开 | `target_graph_reloaded=false`；本机当前无兼容团结可执行文件 |
| AUD-FE-001 | 已验证 | P1 | S2 | CLI 入口 | create editor 返回语义已修，但目标重开状态仍未从 false 变为实证 | bridge/CLI tests 与 README 明确后续门禁 |
| AUD-FLOW-003 | 已验证 | P1 | S2 | 功能闭环 | layout/comment-group 缺正常缩放真实画布门禁 | 相关代码在对比区间未变化；live bounds 未跑 |
| AUD-FE-002 | 已验证 | P1 | S2 | CLI 入口 | layout/comment-group 的视觉结果不可由当前自动测试闭环 | 结构测试通过，真实线路/节点遮挡未验 |
| AUD-GOV-002 | 已验证 | P1 | S2 | 治理/发布 | 普通 strict 已清零，但 release-record 检查仍有 23 项，安全支持版本仍写 0.1.x | 3 份 REL 的 type/章节/回链；`SECURITY.md` |
| AUD-GOV-003 | 已验证 | P1 | S2 | 审计治理 | LOC/模块证据源仍不完整，FM ID 在相邻审计中漂移 | `source_roots=[src]`；自动发现 0 FM；14 FM 与提交审计 13 FM/新 ID 不一致 |
| AUD-SIZE-001 | 已验证 | P1 | S2 | 模块质量 | 两个超限 C# 资源改为永久式具名豁免，但缺治理要求的期限和退出条件 | 536/408 行；loc_exemptions 仅 path/reason |
| AUD-UI-001 | 已验证 | P1 | S2 | UI | Inspector 仍缺皮肤、缩放、长中文、焦点/多选等矩阵 | 对比区间未改 MaterialGUI，当前无 Editor UI 会话 |
| AUD-CI-001 | 已验证 | P2 | S3 | CI | 正式发布 run 仍有 Node 20 弃用与强制 Node 24 警告 | run 33637146781 日志明确列出三个旧 runtime action |

## 项目架构

### 当前结构

- Python 3.10+ 模块化单体；`cli` 组合 `core/schema/checks/bridge`，Agent Skill 提供操作契约，GitHub Actions/REL 提供私有分发。
- 最新代码将 checks/bridge 对 core 的 4 个私有导入改走 `core/__init__.py` 公共面，fitness finding 已从 4 降到 0。
- Editor 创建保持固定 C# nonce 事务：Save/Load 暂存图、MoveAsset 提交；JSON 新增 `staging_reloaded=true` 与 `target_graph_reloaded=false`，避免把暂存重载误报为目标图重开。

### 关键链路

| 链路 | 入口 | 核心模块 | 数据/状态流 | 外部依赖 | 结论 |
| --- | --- | --- | --- | --- | --- |
| 解析/校验 | parse/validate | core → checks → cli | file → graph → issue JSON | 文件系统 | 已闭环 |
| 图修改 | set/add/connect/disconnect/remove | cli → core/schema/checks | 读取 → 不变量 → dry-run/atomic write | 文件系统 | 已闭环 |
| 图治理 | graph-audit/layout/comment-group | checks/core → JSON/位置/Comment | 结构语义 → 候选/布局/边界 | 可选 live ASE | 结构闭环，视觉部分 |
| 属性呈现 | custom-gui/gui-support | core/bridge → 固定 MaterialGUI | spec → 图/编译标签/GUI | 团结 Editor | 契约闭环，UI 部分 |
| Editor 创建 | create/recompile | editor_spec → MCP → ASE → manifest | v2 spec → staging → commit → recompile | 团结 2022.3.61t9 + ASE 1.9.6.2 | 同实例闭环，新进程断点 |
| 正式分发 | CI/Release | uv → package/SBOM/hash → Release | commit 6865aaa → v0.2.0 → uv tool | GitHub | 产物闭环，REL 治理部分 |

### 模块边界与隔离

| 模块 | 独立文件/目录 | 公共接口 | 独立测试 | 跨模块依赖 | 修改爆炸半径 | 结论 |
| --- | --- | --- | --- | --- | --- | --- |
| core | 是 | `core/__init__.py` | roundtrip/mutate/layout/gui | 标准库 | 高 | 公共导出已补齐，fitness 0 |
| schema | 是 | schema_for/能力矩阵 | schema tests | core model | 中 | 未知版本失败关闭 |
| checks | 是 | validate/usage | graph/usage tests | core 公共面 | 中 | 私有导入已清理 |
| bridge | 是 | create/recompile/gui-support | bridge + 条件 E2E | MCP、团结/ASE | 高 | 运行环境仍是主风险 |
| cli | 是 | 15 个子命令 | CLI contract | 四核心模块 | 高 | 单行 JSON 契约稳定 |
| Agent Skill | 是 | SKILL.md | REG-0010/文档一致性 | CLI | 中 | 正确说明 target reload 边界 |

## 技术路径与交付形态

- 技术路径：Python 标准库、argparse、Hatchling、uv、pytest；MCP HTTP/SSE；团结 Editor/UnityEditor/ASE 1.9.6.2。
- 实现/壳形态：本地 CLI + Agent Skill + 打包 C# Editor/MaterialGUI 资源，无常驻公网服务。
- 构建与交付：固定 uv.lock 与 Action SHA；GitHub Actions 构建 wheel/sdist、SPDX、供应链/漏洞报告和 SHA256SUMS；私有 Release 通过 `uv tool install` 安装并可回滚 v0.1.0。

| 交付物 | 格式/载体 | 生成方式 | 安装/部署 | 签名/发布证据 | 结论 |
| --- | --- | --- | --- | --- | --- |
| ASECLI v0.2.0 | universal wheel | run 33637146781 | `uv tool install` | tag 解引用到 6865aaa；wheel SHA-256 `5dd89f11…954e` | 已验证 |
| sdist | tar.gz | 同一 package job | 源码安装 | SHA-256 `112ec836…779a` | 已验证 |
| SBOM/供应链/漏洞 | SPDX/JSON | CI tools | 随 Release 下载 | 五项载荷全部通过 SHA256SUMS | 已验证 |
| Agent Skill | Markdown | 随仓库/sdist | Agent 读取 | 无独立签名 | 已实现 |
| REL 治理记录 | Markdown | 手工回写 | 不适用 | 三份记录当前不满足新版 release-record checker | 部分 |

## 平台支持

| 平台/版本 | CPU/运行环境 | 已声明 | 可构建 | 已测试 | 已发布 | 证据/限制 |
| --- | --- | --- | --- | --- | --- | --- |
| macOS / Python 3.10+ | 当前 arm64 | 是 | 是 | 是 | 是 | 本地 223 tests；v0.2.0 wheel 安装 |
| GitHub Ubuntu / Python 3.10、3.12 | X64 | 是 | 是 | 是 | 是 | run 33637146781 三 job 全绿 |
| 团结 2022.3.61t9 + ASE 1.9.6.2 | 当前项目基线 | 是 | 不适用 | 历史同实例；本轮静态确认 | CLI 资源随包 | 本机项目具备，Editor 可执行文件未找到 |
| `/Applications/Unity/Unity.app` 2021.3.7f1c1 | arm64 | 否 | 不适用 | 禁止用于本验收 | 否 | 不是团结且版本不符，不能替代 |
| Windows/Linux 目标 Editor | 未固定 | 否 | 未验证 | 未验证 | Python 包可下载 | 不外推 Editor 能力 |

## 上帝文件与模块隔离

### 文件行数门禁

- 门禁：`.project-architect.json` 的 `thresholds` 为 source 250/400、test 400/600、config 160/200；另保留旧 `loc_thresholds`。Project Architect 实际扫描根为 `src`，项目专用 CI 检查另外识别 `src/asecli/**/*.cs.txt`。
- 扫描范围 / 排除范围：标准 LOC 未覆盖 tests/tools；两个 `.cs.txt` 由专用检查器发现但通过 `loc_exemptions` 豁免。证据采集未截断。

| 文件 | 行数 | 门禁结果 | 核心链路 | 建议 | 问题 ID |
| --- | --- | --- | --- | --- | --- |
| `asecli_material_gui.cs.txt` | 536 | 具名豁免，治理字段不完整 | 是 | 补 owner/批准/到期/补偿控制/退出条件，或拆分 | AUD-SIZE-001 |
| `editor_create.cs.txt` | 408 | 具名豁免，治理字段不完整 | 是 | 为固定事务登记短期例外并设置复审点 | AUD-SIZE-001 |
| `tests/test_custom_gui.py` | 584 | 未进入标准 LOC；按 test 阈值为预警 | 否 | 将 tests 纳入真实扫描并按行为域逐步拆分 | AUD-GOV-003 |
| `src/asecli/core/custom_gui.py` | 250 | 等于预警线 | 是 | 保持职责不再增长 | 不适用 |

### 上帝文件候选

| 文件或逻辑类型族 | 规模/职责 | 扇入/扇出或共享状态 | 修改/回归证据 | 结论 | 拆分边界 |
| --- | --- | --- | --- | --- | --- |
| MaterialGUI 资源 | 536 行，drawer/Tooltip/HelpBox/默认值/兼容 | Inspector 状态集中 | GUI tests + 历史实机 | 候选 | provider/解析、呈现、默认值格式化 |
| Editor create 资源 | 408 行，ASE 生命周期/创建/保存/回滚/manifest | 固定 nonce 事务 | bridge tests + 历史实机 | 有条件例外候选 | 若拆分必须保持单次固定 payload |
| audit FM supplement | 当前仅系统临时 JSON | 每轮人工重建 | 14 FM 与提交审计 13 FM ID 漂移 | 治理候选 | 仓库化唯一能力清单或改进自动发现 |

### 模块隔离风险

| 问题 ID | 功能 | 当前分布 | 耦合点 | 连带回归 | 建议边界 |
| --- | --- | --- | --- | --- | --- |
| AUD-GOV-003 | 审计能力清单 | evidence collector + 临时 supplement + 报告表 | 自动发现为 0，人工 ID 可漂移 | 增量 compare 失真 | 持久化稳定 FM 清单并由 CI/coverage 复用 |
| AUD-SIZE-001 | C# 执行器 | Python 包资源 + 安装/执行器 | 单文件大 payload | GUI/Editor E2E 爆炸半径 | 合规时限例外或按固定拼装边界拆分 |

## 项目成熟度

等级：`L0 缺失`、`L1 临时`、`L2 可重复`、`L3 标准化`、`L4 可度量`。

| 维度 | 等级 | 当前机制 | 证据 | 主要缺口 |
| --- | --- | --- | --- | --- |
| 需求与追溯 | L3 | FR/CR/ADR/BUG/TASK/REG/REL | kickoff/traceability/fitness 均 0 | release-record 23 项、SECURITY 版本错位 |
| 架构与模块 | L3 | module-map、公共 API、fitness | 私有导入 4→0 | FM 自动发现/稳定 ID 未固化 |
| 构建与测试 | L3 | uv.lock、双 Python、pytest/REG | 223 passed/3 skipped；36 REG | 3 个真实 bridge 依赖环境 |
| CI | L3 | verify/package/SBOM/hash/install | 正式 run 三 job 全绿 | Node runtime 弃用告警 |
| 目标 Editor E2E | L2 | 条件 bridge + manifest | 正确项目/ASE 已确认；历史同实例通过 | 当前缺兼容 Editor/MCP 与新进程证据 |
| UI/画布 | L2 | 属性呈现合同、结构/边界测试 | 7 属性零违规 | 真实画布和 UI 矩阵未执行 |
| 发布与回滚 | L3 | 私有 Release、哈希、SBOM、隔离回滚 | v0.2.0 在线复验通过 | REL/SECURITY 治理一致性不足 |
| 安全与供应链 | L3 | loopback、脱敏、0 runtime deps、在线扫描资产 | vulnerability-scan 与 supply-chain assets | SECURITY 未覆盖 0.2.x |
| 可观测性 | L2 | JSON、稳定错误码、manifest/hash | CLI/bridge contract | MCP timeout 仍为未知完成状态 |
| 文档治理 | L2 | README/Skill/治理文档齐全 | 普通 strict 0 | release strict 23；审计 ID 漂移 |

- 总体成熟度与依据：**L2（可重复），局部 L3**。与上一轮相比，发布/回滚已达到 L3，普通治理恢复 L3；但核心 Editor v2 的新进程证据仍为 L2，且正式发布记录本身尚未通过完整治理门禁，因此总体不提升到 L3。

## 回归验证机制

| 检查项 | 当前机制 | 自动化/CI | 覆盖 | 证据 | 缺口 |
| --- | --- | --- | --- | --- | --- |
| 核心/跨模块 | pytest + REG + strict | 本地/CI | 解析、写入、GUI、bridge mock、公共导入 | 223/36；普通 strict 0 | release strict 未纳入零门禁 |
| Editor v2 | bridge marker + manifest | 条件自动/人工 | staging、commit、独立 recompile | 同实例历史证据 | target_graph_reloaded 新进程未验 |
| 图/UI | 结构测试 + 人工 Editor | 部分 | Comment/布局结构、属性契约 | 7 属性零违规 | normal zoom、skin/scale/focus 未验 |
| 正式发布 | CI + Release + hash + uv tool | 远端/本地 | 六资产、回滚 | 本轮在线复验 | REL checker 23 项 |
| 失败留痕 | BUG/REG/timeline/REL | 部分 | BUG-0016～18 | 真实 run/tag/asset | 阻塞记录把旧电脑环境写死，需更新当前电脑事实 |

## OpenSpec 规范管理

| 状态 | 结论 | 证据 |
| --- | --- | --- |
| 工具、项目配置、实际使用、规范一致性、strict 校验 | 未发现项目配置 | OpenSpec 1.7.0 已安装，仓库无 `openspec/`；继续以现有 FR/CR/ADR/traceability 为事实源，本轮不初始化。 |

## CodeGraph 使用情况

| 状态 | 结论 | 证据 |
| --- | --- | --- |
| 安装、初始化、索引新鲜度、实际使用、更新机制 | 降级 | CodeGraph 已安装但项目 `Not initialized`；本轮用 Git diff、`rg`、Project Architect fitness 和测试替代。 |

## 文档增量与变更留档

| 变更类型 | 载体/机制 | 增量历史 | 关联键 | 字段完整性 | 抽样证据与缺口 |
| --- | --- | --- | --- | --- | --- |
| 需求变更 | change-register/traceability | 有 | CR-0013/TASK-0032/REG-0038 | 完整 | target reload 语义已回写 |
| 技术变更 | module-map/core public API/config | 有 | ADR/TASK | 部分 | 普通 strict 已清零；LOC 例外治理字段不完整 |
| 文件修改记录 | 3 commits + timeline | 有 | 6865aaa/a724cc7/946d53c | 完整 | 20 个路径可追溯 |
| 发布记录 | REL-0003 + GitHub | 有 | v0.2.0/run 33637146781 | 运行证据完整、格式部分 | checker 23 项；SECURITY 仍为 0.1.x |
| 审计记录 | timestamped reports | 有 | AUD/FM/FE | 部分 | 自动 FM=0；两次相邻审计的新模块 ID 不稳定 |

## 功能模块闭环度

- 模块统计：发现数：14；已审计数：14；未覆盖数：0
- 清单校准：延续 `2026-09-02-203452` 的 14 个 FM ID；自动发现仍为 0。提交中的 `2026-09-02-211218` 报告将 graph-audit 合并并为 4 个新增能力重新编号，作为 AUD-GOV-003 的稳定性缺口记录，不再继续改 ID。

| 模块 ID | 模块/能力 | 需求/入口 | 主路径/关键链路 | 数据/状态闭环 | 异常/恢复 | 日志/可观测性 | 回归/验收 | 发布证据 | 结论 | 问题 ID |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FM-0E60A4DD1B | parse-serialize | FR-0001 / parse | file → graph → serialize | roundtrip | NOT_FOUND/PARSE JSON | 单行摘要 | tests + 真实 Shader | v0.2.0 | 已闭环 | 不适用 |
| FM-9040886B90 | graph-mutation | FR-0002 / 5 图命令 | graph_ops → validate → atomic write | 不变量/备份 | 重复/外部消费拒绝 | written/code | graph tests | v0.2.0 | 已闭环 | 不适用 |
| FM-8ADC52C2A4 | schema-library | FR-0002 / add-node | version gate → node line | 字段/版本一致 | unknown/opaque 拒绝 | SCHEMA code | schema tests | wheel 资源 | 已闭环 | 不适用 |
| FM-C73F236CD5 | validation-checksum | FR-0003 / validate/fix | checks → issue/checksum | error_count/exit | dry-run/备份 | issues JSON | 真实两 Shader 0 error | v0.2.0 | 已闭环 | 不适用 |
| FM-F03DFA9A41 | layout | FR-0008 / layout | graph → staged position | 仅坐标变化 | 环图降级 | moved JSON | 自动结构测试 | v0.2.0 | 部分闭环 | AUD-FLOW-003 |
| FM-3537DE9938 | create-from-template | FR-0005 / create text | shell+donor→presentation→file | 名称/图/属性回读 | exists/不合规拒绝 | created JSON | create tests | v0.2.0 | 已闭环 | 不适用 |
| FM-DF0669A019 | recompile-bridge | FR-0004 / recompile | hash→MCP→saved/changed | result+hash | BRIDGE_ERROR | 脱敏 JSON | mock+历史实机 | v0.2.0 | 已闭环 | 不适用 |
| FM-1DB3E4EA8B | cli-contract | FR-0007 / 15 命令 | argparse→handler→envelope | code/status 固定 | usage/business/internal | stdout JSON | CLI tests+wheel | v0.2.0 | 已闭环 | 不适用 |
| FM-25E63BD4F6 | agent-skill | FR-0006 / SKILL | Agent→CLI→validate | 逐步回读 | 失败即停/恢复 | CLI JSON | REG-0010 | 随包/仓库 | 已闭环 | 不适用 |
| FM-2E47AA5409 | graph-audit | FR-0010 / graph-audit | graph+source consumers→分类 | 只读候选 | 外部消费者保护 | 分类 JSON | usage tests | v0.2.0 | 已闭环 | 不适用 |
| FM-35114E2780 | custom-gui-property-presentation | FR-0009/10/11 | inspect/spec→图/编译对账 | 逐属性 valid | 整批拒写/备份 | contract JSON | 7 属性零违规 | v0.2.0 | 已闭环 | 不适用 |
| FM-DB13C6D6D8 | gui-support-material-inspector | FR-0009 / gui-support | project→provider/安装 | hash/contract 回读 | 冲突拒绝 | provider JSON | installed hash 一致 | v0.2.0 | 已闭环 | 不适用 |
| FM-3EEC4BD8D5 | comment-group | FR-0010 / comment-group | members→Comment→bounds | 树/CHKSM | 重叠/非法标题拒绝 | groups/issues | 结构 tests | v0.2.0 | 部分闭环 | AUD-FLOW-003 |
| FM-14E9E4031E | editor-api-create | FR-0011 / create editor | v2→ASE→staging→commit→recompile | manifest/reconciliation | timeout/回滚 | staging/target flags | 同实例历史；新进程待验 | v0.2.0 | 部分闭环 | AUD-FLOW-002 |

### 前端功能入口闭环

- 入口统计：发现数：15；已审计数：15；未覆盖数：0
- 清单校准：无人工新增或排除，自动发现的 15 个 argparse 子命令全部入表。

| 入口 ID | 页面/入口与类型 | 条件/权限 | 目标/handler | 状态覆盖 | 返回/恢复 | 测试/运行证据 | 结论 | 问题 ID |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FE-5FE7C39BCC | parse CLI | 文件可读 | cmd_parse | success/error | 只读重试 | tests+wheel | 已闭环 | 不适用 |
| FE-5F33E87610 | set-field CLI | 字段可变 | cmd_set_field | dry/write/reject | 备份 | tests | 已闭环 | 不适用 |
| FE-37BA87FA15 | add-node CLI | schema/version 有效 | cmd_add_node | schema/unknown | dry-run/备份 | tests | 已闭环 | 不适用 |
| FE-C3162CA2E1 | connect CLI | 端口有效 | cmd_connect | dry/write/conflict | 备份 | tests | 已闭环 | 不适用 |
| FE-AAF53AF86F | disconnect CLI | wire 存在 | cmd_disconnect | dry/write/not-found | 备份 | tests | 已闭环 | 不适用 |
| FE-0018A7D5D8 | remove-node CLI | node 存在 | cmd_remove_node | dry/write/external | 线清理/备份 | tests | 已闭环 | 不适用 |
| FE-50D4B549C6 | graph-audit CLI | 文件/可选工程根 | cmd_graph_audit | used/external/unused | 只读人工确认 | usage tests | 已闭环 | 不适用 |
| FE-BBB0F9830B | validate CLI | 文件可读 | cmd_validate | 0/error exit2 | 修复后重试 | 两 Shader 0 error | 已闭环 | 不适用 |
| FE-369C790BD8 | fix-checksum CLI | `--write` 才写 | cmd_fix_checksum | preview/write | 备份 | tests | 已闭环 | 不适用 |
| FE-C71A570BA7 | layout CLI | 图可解析 | cmd_layout | dry/write/cycle | 备份/人工复核 | 结构测试，画布未验 | 部分闭环 | AUD-FE-002 |
| FE-4E1B79DEE4 | custom-gui CLI | 19602 写 metadata | cmd_custom_gui | inspect/spec/clear/error | 原子拒写/备份 | 7 属性 valid | 已闭环 | 不适用 |
| FE-1E3A6EB7E7 | gui-support CLI | 工程路径 | cmd_gui_support | inspect/install/conflict | hash/备份 | 当前 installed | 已闭环 | 不适用 |
| FE-222ADDDF1D | comment-group CLI | live 需 MCP | cmd_comment_group | query/create/check/fit | dry-run/备份 | 结构测试，live 未验 | 部分闭环 | AUD-FE-002 |
| FE-B537BBBC81 | create CLI | text 或 v2 spec | cmd_create | text/editor/auto/error | rollback/temp 检查 | 字段已修，新进程未验 | 部分闭环 | AUD-FE-001 |
| FE-3F4DBCA0D3 | recompile CLI | loopback MCP | cmd_recompile | changed/error/unknown | BRIDGE_ERROR/检查目标 | mock+历史实机 | 已闭环 | 不适用 |

## 交互流程与 UI

### Product Design 参与情况

| 检查项 | 结论 | 证据/限制 |
| --- | --- | --- |
| 历史参与证据、本次调用、当前截图、视觉结论等级 | 本次未调用 | 当前没有运行中的团结 Editor，无法取得新 UI 状态；本轮只保留既有用户 Tooltip 确认并将未覆盖矩阵列为开放问题，不做重新设计。 |

### 关键流程证据

| 步骤 | 用户目标/操作 | 截图或运行证据 | 健康度 | UX/可访问性问题 | 证据限制 |
| --- | --- | --- | --- | --- | --- |
| 01 | 安装正式 v0.2.0 | 空目录下载、五载荷 hash、uv 安装 | 良好 | CLI 入口清楚 | 私有权限用户范围 |
| 02 | 治理两个 VehicleLocalShadow Shader | 19602、11/28 nodes、validate 0、7 属性 valid | 良好 | 中文属性契约完整 | 只读，不证明最终画面 |
| 03 | v2 Editor 创建 | 历史同实例；JSON 区分 staging/target | 有风险 | Agent 不再误判 reloaded | 当前未启动 Editor，新进程待验 |
| 04 | layout/Comment | 自动结构回归 | 有风险 | 真实线路/节点遮挡未知 | normal zoom 未验 |

### UI 检查

| 页面/区域 | 层级与清晰度 | 一致性/状态 | 响应式 | 键盘/焦点/语义 | 问题 ID |
| --- | --- | --- | --- | --- | --- |
| Material Inspector | 中文标签/说明与 Tooltip 历史通过 | provider/hash/契约当前一致 | light/scale/窄宽/长文本未验 | focus/mixed-value 未验 | AUD-UI-001 |
| ASE 画布 | 布局规范完整 | 结构/Comment 树可测 | 节点真实尺寸/缩放未验 | 非当前主要无障碍面 | AUD-FLOW-003 |
| CLI JSON | 单行清楚 | 15 入口一致 | 终端宽度不影响解析 | 文本可复制 | 不适用 |

## 专项工程审计

| 专项领域 | 状态 | 核心证据 | 主要风险/缺口 | 问题 ID |
| --- | --- | --- | --- | --- |
| 安全与隐私 | 部分 | loopback/脱敏/固定 payload；正式 vulnerability asset | `SECURITY.md` 仍只支持 0.1.x | AUD-GOV-002 |
| 性能与资源 | 已验证 | 大图性能回归、0 runtime dependencies | Editor/UI 未做量化预算，当前无阻塞证据 | 不适用 |
| 可观测性与运维 | 已验证 | JSON、manifest/hash、release/run 证据 | MCP timeout 仍是未知完成状态 | AUD-FLOW-002 |
| 依赖、供应链与许可证 | 已验证 | lock、SBOM、在线漏洞资产、五载荷 hash | 私有专有包本身不在 PyPI 漏洞库，已正确说明 | 不适用 |
| API、数据兼容与迁移 | 已验证 | schema gate、v2 spec、staging/target flags | Editor 仅支持 ASE 1.9.6.2 | AUD-FLOW-002 |
| 无障碍与国际化 | 部分 | UTF-8/中文属性合同 | Inspector UI 矩阵未跑 | AUD-UI-001 |
| 构建可复现与产物完整性 | 已验证 | run、Release、hash、SBOM、安装与回滚 | release-record 文档门禁不影响产物真实性但影响治理 | AUD-GOV-002 |

## 增量审计对比

- 基线报告：主对比为 `docs/05-audits/2026-09-02-203452-project-audit-report.md`；同时参考最新代码已提交的 `2026-09-02-211218` 报告和任务书。

| 分类 | 问题 ID | 基线 -> 当前 | 证据/说明 |
| --- | --- | --- | --- |
| 已解决 | AUD-REL-001 | 0.2.0 候选、仅 v0.1.0 正式 → v0.2.0 正式 | tag→6865aaa、run 33637146781、六资产与回滚均已验证 |
| 已解决 | AUD-SUPPLY-002 | 在线/全载荷未验证 → 正式资产完整 | vulnerability/supply-chain/SBOM/hash 全部下载复验 |
| 改善 | AUD-GOV-002 | 50 项 → 23 项 | kickoff 2、trace 25、fitness 4 已清零；只剩 release-record 23 项及 SECURITY 版本错位 |
| 改善 | AUD-GOV-003 | 旧 thresholds 且 `.cs.txt` 漏扫 → thresholds 与专用检查已补 | tests/tools 仍不在 source_roots；FM 自动发现 0/ID 漂移 |
| 改善 | AUD-SIZE-001 | 超限资源完全漏扫 → 专用发现 + 具名豁免 | 例外仍缺 owner/批准/到期/补偿控制/退出条件 |
| 改善 | AUD-FE-001 | `reloaded` 语义歧义 → staging/target 显式区分 | 目标仍为 false，新进程证据未完成 |
| 未变化 | AUD-FLOW-002 | v2 新进程/目标平台未验 → 仍未验 | 当前电脑已有正确项目/ASE，但缺兼容 Editor/MCP/隔离副本 |
| 未变化 | AUD-FLOW-003 | 真实画布门禁缺失 → 缺失 | 对比区间没有 layout/comment 实现或实机证据变化 |
| 未变化 | AUD-UI-001 | UI 矩阵缺失 → 缺失 | 对比区间没有 MaterialGUI 视觉证据变化 |
| 未变化 | AUD-CI-001 | Node 20 弃用警告 → 仍存在 | 正式 run 日志再次确认 |
| 新增发现 | AUD-FE-002 | 未单列 → layout/comment 两入口部分闭环 | 用入口级 ID 绑定既有 FLOW 缺口 |

## 阻塞项

| 问题 ID | 阻塞内容 | 影响范围 | 证据 | 解除条件 |
| --- | --- | --- | --- | --- |
| AUD-FLOW-002 | 当前电脑无法立即执行指定版本双进程 E2E | v0.2.0 EditorGraphSpec v2 的最终可重开证据 | FlymeAuto3Test 为 2022.3.61t9 + ASE 1.9.6.2；但无运行 Editor/MCP，仅发现 Unity 2021.3.7f1c1 | 定位/安装团结 2022.3.61t9 可执行文件；创建隔离副本；启动 MCP；执行创建→退出→新进程重开 |

## 潜在风险

| 问题 ID | 风险 | 触发条件 | 影响 | 概率 | 应对建议 |
| --- | --- | --- | --- | --- | --- |
| AUD-RISK-001 | 在 FlymeAuto3Test 原工程直接试验 | 未先隔离就运行 bridge E2E | 临时 Shader、选择或 Editor 状态污染生产工程 | 中 | 使用临时副本/隔离工程和唯一前缀，验证后核对清理 |
| AUD-RISK-002 | Unity 2021 被误作团结验收 | 只按 `Unity.app` 名称启动 | 产生无效兼容结论 | 中 | 启动前核对 bundle/Editor log/ProjectVersion，明确拒绝 Unity 2021 |
| AUD-RISK-003 | 审计 FM ID 持续漂移 | 每轮临时手工 supplement | compare 把同一能力误判为新增/消失 | 高 | 将稳定清单仓库化并纳入 coverage |

## 问题详情

### AUD-FLOW-002 EditorGraphSpec v2 新进程闭环仍未完成

- 状态：已解决
- 整改证据：REG-0038 / TASK-0033
- 证据状态：已验证
- 严重程度：S1
- 优先级：P1
- 影响范围：FM-14E9E4031E、FR-0011、正式 v0.2.0 Editor 创建能力
- 证据：返回值已明确 `staging_reloaded=true`、`target_graph_reloaded=false`；本机 FlymeAuto3Test 是团结 2022.3.61t9/ASE 1.9.6.2，但当前没有兼容团结可执行文件或活动 MCP。
- 根因判断：旧电脑阻塞记录已过时；当前电脑项目/ASE 已满足，剩余是 Editor 安装/定位和隔离执行条件。
- 优化做法：定位或安装指定团结，克隆最小隔离工程，执行 v2 create→recompile→退出→新进程重开→manifest/属性/清理复验。
- 技术路径：复用现有 bridge E2E、EditorGraphSpec v2、SHA-256/manifest 和临时资产前缀；禁止 Unity 2021。
- 验收标准：新进程打开后模板、节点、线、属性、CustomEditor 与 presentation valid 一致，0 编译错误、0 `ASECLI-Temp-*` 残留。
- 验证方式：指定团结 + ASE 1.9.6.2 隔离工程、条件 pytest、Editor log、前后 manifest/hash。
- 回滚/降级：仅操作隔离副本；超时后先查目标和暂存，不立即重试；失败删除隔离副本而非改生产工程。

### AUD-FE-001 create editor 入口仍缺目标重开实证

- 状态：已解决
- 整改证据：REG-0038 / TASK-0033
- 证据状态：已验证
- 严重程度：S2
- 优先级：P1
- 影响范围：FE-B537BBBC81、Agent 对 create 完成状态的判断
- 证据：代码/测试/文档已正确区分 staging 与 target；`target_graph_reloaded` 固定为 false，必须由后续新进程证据解除。
- 根因判断：字段歧义已修，运行闭环与结构契约是两个不同问题。
- 优化做法：P1.1 实机用例回读目标后，新增独立证据字段或测试报告，不把单次 create 的 false 强改为 true。
- 技术路径：保持兼容 JSON，另由 E2E 记录 target reopen manifest。
- 验收标准：Agent 可以区分 create 返回与双进程验收；新进程结果有结构化、可复核证据。
- 验证方式：bridge/CLI contract + 新进程 E2E 结果。
- 回滚/降级：未完成前继续保留 false 和文档警告。

### AUD-FLOW-003 layout/comment-group 缺真实画布门禁

- 状态：已解决
- 整改证据：REG-0041 / TASK-0035
- 证据状态：已验证
- 严重程度：S2
- 优先级：P1
- 影响范围：FM-F03DFA9A41、FM-3EEC4BD8D5
- 证据：对比区间没有相关实现/视觉证据变化；live bounds 和 normal zoom 未运行。
- 根因判断：ASE 文本不包含全部真实节点尺寸与贝塞尔路径，结构测试无法替代画布。
- 优化做法：在指定 Editor 中对代表性图执行 live bounds/check/fit，保存 normal zoom 截图并检查线路不穿节点/端口/标题栏。
- 技术路径：复用现有 CLI 与 layout standard，只允许位置/Comment 变化。
- 验收标准：列/重复分支对齐、Comment 完整包含且不重叠、normal zoom 可读、图计算语义不变。
- 验证方式：结构 diff、live bounds JSON、截图人工签收。
- 回滚/降级：使用备份/`.meta` hash；不达标恢复位置，不改计算图。

### AUD-FE-002 layout/comment-group 入口视觉返回不闭环

- 状态：已解决
- 整改证据：REG-0041 / TASK-0035
- 证据状态：已验证
- 严重程度：S2
- 优先级：P1
- 影响范围：FE-C71A570BA7、FE-222ADDDF1D
- 证据：入口能返回 moved/groups/bounds，但当前无真实画布证据证明最终可读。
- 根因判断：入口返回的是结构状态，不是视觉验收状态。
- 优化做法：在实机任务中关联截图/验收记录或显式标记 `visual_review_required`，防止 Agent 把结构成功当视觉成功。
- 技术路径：优先文档/结果契约增量，不引入图像识别依赖。
- 验收标准：每次生产图治理都能查到结构结果与真实视觉签收状态。
- 验证方式：CLI contract、真实画布验收清单。
- 回滚/降级：保留现有字段兼容；无视觉证据时保持 pending。

### AUD-GOV-002 发布治理与安全支持声明未对齐

- 状态：已解决
- 整改证据：TASK-0034
- 证据状态：已验证
- 严重程度：S2
- 优先级：P1
- 影响范围：三份 REL、traceability、SECURITY、完整 strict 发布门禁
- 证据：普通 strict 全零；加 `--check-release` 后 23 项，包括三份 REL 的 type/章节、REL-0001/2 回链；`SECURITY.md` 仍只支持 0.1.x。
- 根因判断：实际发布流程沿用旧 `delivery-evidence/release` 文档结构，检查器已升级为 `release-record` 契约；发布时漏改安全支持范围。
- 优化做法：兼容迁移 REL-0001～3 的 frontmatter/章节和反向追溯，更新 SECURITY 支持 0.2.x，不改历史事实或资产。
- 技术路径：复用现有 release 模板与 strict checker，仅修改治理文档。
- 验收标准：完整 strict（含 release）0 finding；SECURITY 与最新正式版本一致；历史 v0.1.0 仍保留。
- 验证方式：check-release strict、traceability、文档链接与 release URL 复核。
- 回滚/降级：保留 Git 历史，不删除 REL；如模板迁移失真则停止并逐记录修正。

### AUD-GOV-003 LOC/功能清单事实源仍不完整

- 状态：已解决
- 整改证据：REG-0020 / TASK-0034
- 证据状态：已验证
- 严重程度：S2
- 优先级：P1
- 影响范围：LOC 可信度、FM 覆盖和增量 compare
- 证据：`source_roots` 只有 `src`，test/config 阈值无法覆盖 tests/tools；collector 自动 FM=0；203452 报告 14 FM 与提交报告 13 FM/4 个新 ID 不一致。
- 根因判断：配置修复只解决当前 strict，不提供持久化能力清单和全分类扫描。
- 优化做法：持久化唯一 FM supplement/清单并纳入 CI coverage；显式纳入 tests/tools 或提供等价专用检查，禁止后续重发 ID。
- 技术路径：复用 collector supplement 与 coverage validator，不引入 CodeGraph。
- 验收标准：无临时文件也能发现同一组稳定 FM；tests/tools 分类 LOC 可见；连续两次审计 ID 集合一致。
- 验证方式：两次 clean collect/coverage、LOC fixture、compare。
- 回滚/降级：先仓库化只读清单；若通用 scanner 无法区分根目录，保留专用检查并明确范围。

### AUD-SIZE-001 C# 资源例外缺完整治理字段

- 状态：已解决
- 整改证据：TASK-0034；例外到期 2026-10-03
- 证据状态：已验证
- 严重程度：S2
- 优先级：P1
- 影响范围：536/408 行 MaterialGUI 与 Editor create 固定 payload
- 证据：loc_exemptions 只有 path/reason；项目治理要求 owner、批准人、创建/到期、补偿控制、退出条件。
- 根因判断：最新代码把“漏扫”改成“具名豁免”，但将临时技术债固化成无期限配置。
- 优化做法：优先补完整、短期限 ADR 例外与复审任务；可低风险拆分 MaterialGUI，Editor nonce 事务仅在不破坏单 payload 时拆。
- 技术路径：扩展现有 CI governance 对例外字段/到期的检查。
- 验收标准：每项例外字段完整且未过期，过期必失败；补偿测试覆盖 C# 编译和对应 E2E。
- 验证方式：CI governance fixture、LOC、GUI/Editor bridge tests。
- 回滚/降级：保持运行资源不动，先收紧治理；拆分失败恢复单文件。

### AUD-UI-001 Inspector UI 矩阵仍未完成

- 状态：已解决
- 整改证据：REG-0042 / TASK-0036
- 证据状态：已验证
- 严重程度：S2
- 优先级：P1
- 影响范围：正式 Material Inspector 的可读性与输入可达性
- 证据：当前只读合同 valid；无运行 Editor，最新区间没有 light/scale/长文本/focus/mixed-value 新证据。
- 根因判断：GUI 已正式发布，但验证仍依赖此前单实例人工抽样。
- 优化做法：在 P1.1 同一隔离环境跑最小 UI 矩阵，不重新设计界面。
- 技术路径：现有 MaterialGUI fixture + Editor 自动断言 + 标注环境截图。
- 验收标准：dark/light、常规/高缩放、窄宽/长中文、焦点/多选状态可读可操作，属性契约仍 0 violation。
- 验证方式：真实 Inspector 清单、截图和 GUI pytest。
- 回滚/降级：只改展示层；任何语义/默认值变化立即回退。

### AUD-CI-001 Actions Node runtime 弃用告警

- 状态：已解决
- 整改证据：REG-0043 / TASK-0037；run 33714089230 与 artifact 9877900476
- 证据状态：已验证
- 严重程度：S3
- 优先级：P2
- 影响范围：未来 GitHub runner 兼容性
- 证据：run 33637146781 全绿，但 checkout、setup-uv、upload-artifact 被警告从 Node 20 强制运行于 Node 24，并伴随弃用 API 警告。
- 根因判断：固定 action SHA 对应的 action runtime 落后。
- 优化做法：升级到官方 Node 24 兼容 action 版本并继续固定完整 SHA。
- 技术路径：只更新 action SHA 与 governance allowlist。
- 验收标准：新 run 全绿且无 Node 20/相关 Node API 弃用警告，artifact hash/安装不变。
- 验证方式：CI log、governance、artifact smoke。
- 回滚/降级：异常则恢复上一 SHA 并登记到期风险。

## 验证记录

| 命令/检查 | 目的 | 结果摘要 | 是否通过 |
| --- | --- | --- | --- |
| standard collect + supplement | 项目/FM/FE 采证 | 313 indexed、132 text、14 FM、15 FE、未截断 | 是 |
| `uv lock --check` + `uv run --frozen pytest -q` | 锁文件/全量回归 | 223 passed、3 skipped | 是（bridge 未运行） |
| REG/CI governance/supply-chain | 质量与供应链 | 36/36；findings 0；runtime deps 0 | 是 |
| Project Architect strict（不含 release） | kickoff/trace/fitness | 全部 0 | 是 |
| Project Architect strict（含 release） | 发布治理 | release_findings 23 | 否 |
| `gh release view/download v0.2.0` | 正式发布真实性 | tag/release 非 draft；六资产在线 | 是 |
| `shasum -a 256 -c SHA256SUMS` | 载荷完整性 | wheel/sdist/SBOM/supply/vulnerability 全 OK | 是 |
| 隔离 Python 3.12 `uv pip install` | 正式包可用性 | asecli 0.2.0；15 子命令 | 是 |
| 两个 VehicleLocalShadow Shader 只读检查 | 真实资产 | 19602、11/28 nodes、1/6 wires、0 error、7 属性 0 violation | 是 |
| 当前电脑 Editor/ASE 就绪检查 | P1.2 恢复条件 | 项目/ASE 就绪；兼容团结 Editor/MCP/隔离副本未就绪 | 部分 |
| CodeGraph/OpenSpec | 工具状态 | CodeGraph Not initialized；OpenSpec 无项目配置 | 降级/不适用 |

## 计划外发现

- 本地只存在 v0.1.0 tag ref，但远端 v0.2.0 annotated tag 已验证并解引用到 6865aaa；这是先前 `git pull` 未同步 tag 的本地状态，不影响 Release 真实性。本轮未执行 `git fetch --tags`，避免超出只读审计产物范围。
- 当前电脑已具备 FlymeAuto3Test 的正确 ProjectVersion 和 ASE 1.9.6.2，这与旧阻塞记录“当前环境没有正确 ASE 工程”不同；新任务书已按当前事实重写恢复条件。

## 遗留问题

- P1.1 已在隔离团结 `2022.3.61t9` + ASE `1.9.6.2` 双进程解除；P1.5/P1.6 真实画布与 Inspector 证据见 REG-0041/0042。
- AUD-CI-001 已由 setup-uv v10.0.1 的真实 Node 24 run 33714089230 和下载 artifact 复验关闭。
- C# 资源已通过 CR-0014 确定性拆分，EXC-0001/0002 已删除；已知 `0.2.0-original` GUI 的备份/复核/原子升级纳入公共能力，未知内容继续 `target_conflict`。

## 整改后验证记录

| 检查 | 结果 | 状态 |
| --- | --- | --- |
| 全量 pytest | Python 3.10/3.12 均 `243 passed, 3 skipped` | 通过；3 项为条件 bridge，真实双进程/UI 另有本轮实机证据 |
| REG catalog | `39/39` | 通过 |
| standard collect + coverage + audit validate | 14 FM、15 FE、未遗漏；报告/任务书有效 | 通过 |
| Project Architect 完整 strict | kickoff/trace/release/fitness 全部 0 finding | 通过 |
| CI governance / supply chain | Action Node 24 allowlist、C# 分片 LOC、lock/hash/secret/license 均 0 finding；loc_exemptions 为空 | 通过 |
| 可复现构建 | 两次 wheel/sdist SHA-256 完全一致；质量截图不进入 sdist | 通过 |
| Editor/画布/Inspector | REG-0038、REG-0041、REG-0042 | 通过；目标业务渲染不在本次范围 |
| Node 24 远程 CI | run 33714089230 三项 job 全绿；全日志零 Node 20/Node 弃用警告；artifact `9877900476` 下载复验通过 | 通过 |

## CR-0014 门槛清零补充（2026-09-03）

- REG-0044：GUI 300/283 行、Editor 205/205 行；拼装 SHA-256 与拆分前一致，单 payload/单 catch/finally 保持；两项 LOC 例外删除。
- REG-0045：已知旧 GUI dry-run、备份、digest/inode 复核、同目录原子替换与失败恢复自动通过；团结 `2022.3.61t9` C# `1 passed/26.15s`。
- Editor：ASE `1.9.6.2` 从干净隔离 Assets 创建并完全退出，再由新进程重载，`1 passed/39.86s`。首次重载的包源 DNS 超时与随后暴露的空目录夹具缺陷均单独记录；BUG-0021 修复后以完整命令复验。
- 证据：`docs/03-quality/evidence/REG-0044/`、`docs/03-quality/evidence/REG-0045/`。未使用 Unity 2021，未写生产工程。

## Node 24 首次远程复验补充（2026-09-03）

- [run 33713836753](https://github.com/seeseeczl/ASECLI/actions/runs/33713836753) 的 Python 3.10、Python 3.12 和 package 三项 job 全绿，已使用 Node 24 action 固定 SHA，不再出现 Node 20 强制兼容警告。
- 全日志仍出现 setup-uv v7.1.6 的 `DEP0040`（`punycode`）与 `DEP0169`（`url.parse()`）弃用警告，因此 AUD-CI-001/REG-0043 保持开放，不能把“CI 全绿”冒充“弃用门槛清零”。
- 上游最新不可变 release 为 setup-uv v10.0.1，tag 提交 `20cfd1bf945f4377ade1205e4dbc17946fc9a30d` 经 GitHub 验证签名且 `action.yml` 声明 `node24`；据此更新 CI 与唯一 allowlist并进入第二次真实 run，最终结果见下节。

## Node 24 最终远程复验补充（2026-09-03）

- [run 33714089230](https://github.com/seeseeczl/ASECLI/actions/runs/33714089230) 在 setup-uv v10.0.1 下完成 Python 3.10、Python 3.12、package；两套 Python 均为 `243 passed, 3 skipped`，全日志搜索 Node 20、`DeprecationWarning`、强制兼容与 warning 均为零命中。
- artifact `9877900476`（GitHub digest `sha256:64443d0cdceee29265af89595b96aee0f5e2abd27a93450a371ca593a536724d`）下载后清单校验通过：wheel `8fe52d366ad2958eb7107f03b799183d68f89356bef6c2817d7262fe5feb203d`，sdist `4b0bade4650a686254b925d79de602e3c30818ddc5f58f22d086e4af0b594947`。
- SPDX 2.3（14 packages）、供应链 0 finding/0 runtime dependency、wheel/sdist C# 分片成员、隔离 Python 3.12 安装/parse、已知旧 GUI `cf45c7d…b41b8` 到 `9541c54…c5b7a` 的 dry-run/备份/升级全部通过。AUD-CI-001/REG-0043 关闭。

Product Design 本轮不适用：视觉方向和目标样式已经由用户与既有规范确定，本次只做真实界面验证和两个阻塞性展示缺陷的最小修复；使用 Computer Use 留存真实团结截图，不进行重新设计。

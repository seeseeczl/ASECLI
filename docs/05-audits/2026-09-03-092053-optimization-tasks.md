# 项目优化任务书

## 执行原则

- 先完成指定版本 Editor 实机闭环，再处理治理和视觉任务；同一时间只推进一个可观察结果。
- 真实 Editor、静态检查、自动测试、UI、目标平台和远端发布分别记录，不以其中一种替代另一种。
- 只使用团结引擎，不使用 `/Applications/Unity/Unity.app` 的 Unity 2021.3.7f1c1 冒充验证。
- 不直接写 FlymeAuto3Test 生产状态；获得用户确认后创建隔离副本或专用隔离工程，所有验证资产使用唯一前缀并清理回读。
- 默认复用现有 Python/uv/pytest/MCP/ASECLI/GitHub 技术栈，不为通过门禁降低标准或引入无关重构。

## 总目标

- 让 v0.2.0 的 EditorGraphSpec、发布治理、图/UI 验收和审计事实源从“部分可重复”达到可持续、可追溯、可恢复的标准化闭环。

## 范围

- 对应同时间戳报告中的 9 个开放问题，重点是本机 ASE 1.9.6.2 双进程验证、23 项 release-record、LOC/FM 事实源、C# 例外、layout/Comment/Inspector 实机矩阵和 Actions runtime。

## 非目标

- 不公开仓库、不上传 PyPI/CLI Hub、不更改 v0.2.0 既有 Release 资产、不支持未知 ASE 版本、不修改 VehicleLocalShadow 计算效果、不删除任何 unused candidate。

## 问题到任务映射

| 问题 ID | 严重程度 | 优先级 | TODO ID | 处理方式 |
| --- | --- | --- | --- | --- |
| AUD-FLOW-002 | S1 | P1 | P1.1 | 与 create 入口证据合并执行 |
| AUD-FE-001 | S2 | P1 | P1.1 | 与 Editor v2 双进程证据合并 |
| AUD-GOV-002 | S2 | P1 | P1.2 | 单独修复发布记录/安全声明 |
| AUD-GOV-003 | S2 | P1 | P1.3 | 单独固化审计事实源 |
| AUD-SIZE-001 | S2 | P1 | P1.4 | 单独治理例外债务 |
| AUD-FLOW-003 | S2 | P1 | P1.5 | 与两个图入口实机验收合并 |
| AUD-FE-002 | S2 | P1 | P1.5 | 与图治理视觉闭环合并 |
| AUD-UI-001 | S2 | P1 | P1.6 | 单独完成 Inspector 矩阵 |
| AUD-CI-001 | S3 | P2 | P2.1 | 单独升级 action runtime |

## TODO

P0 必须完成

- 当前无 P0。

P1 应该完成

- [x] P1.1 在本机完成 ASE 1.9.6.2 EditorGraphSpec v2 双进程闭环
- [x] P1.2 迁移三份 release-record 并同步 SECURITY 支持版本
- [x] P1.3 固化稳定 FM 清单并补齐 tests/tools LOC 覆盖
- [x] P1.4 为两个超限 C# 资源建立有期限的治理例外或安全拆分
- [x] P1.5 完成 layout/comment-group 真实画布与入口状态闭环
- [x] P1.6 完成 Material Inspector 最小 UI/可访问性矩阵

P2 可选优化

- [x] P2.1 升级 GitHub Actions 到原生 Node 24 runtime（本地配置与门禁完成；远程 run 待下一次获准推送）

## 任务详情

### P1.1 在本机完成 ASE 1.9.6.2 EditorGraphSpec v2 双进程闭环

- 来源问题 ID：AUD-FLOW-002 AUD-FE-001
- 依赖：用户确认或提供团结 2022.3.61t9 可执行文件；允许创建隔离副本
- 严重程度：S1
- 目标：证明 v0.2.0 创建的目标 Shader 在完全退出后的全新团结 Editor 进程中仍可加载，manifest 与属性呈现一致。
- 范围：`/Users/long/Tuanjie3D/FlymeAuto3Test` 的隔离副本、团结 2022.3.61t9、ASE 1.9.6.2、MCP、EditorGraphSpec v2 fixture、REG-0037/0038。
- 非目标：不使用 Unity 2021；不直接改原 FlymeAuto3Test；本任务先证明创建/重开，不把最终 VehicleLocalShadow 渲染效果一并冒充通过。
- 涉及文件/模块/符号：`src/asecli/bridge/editor_create.py`、`editor_create.cs.txt`、`tests/test_editor_create_e2e.py`、`staging_reloaded`、`target_graph_reloaded`、manifest/reconciliation。
- 现有技术栈复用：现有 bridge E2E、MCP 3.4.7 兼容、团结命令行、SHA-256、ASECLI 临时资产前缀。
- 新增依赖：无；若团结 2022.3.61t9 未安装，只通过 Tuanjie Hub 安装官方版本，不引入第三方运行时。
- 技术路径：先定位/安装匹配 Editor，再从正确项目建立最小隔离副本；进程 A 创建/recompile/记录，完全退出后进程 B 加载同一资产并结构化回读。
- 执行步骤：
  1. 核对团结可执行文件版本、工程 ProjectVersion 和 ASE VersionInfo 均精确匹配；复制到系统临时或明确隔离目录，记录初始 hash/进程/MCP 状态。
  2. 进程 A 用固定 v2 spec 创建唯一前缀 Shader，执行独立 recompile，记录 staging/target flags、manifest、Shader/meta hash 与 0 编译错误。
  3. 完全退出进程 A 和 MCP 后启动进程 B，重新打开目标、对账模板/节点/线/属性/CustomEditor/presentation，清理验证资产并确认无 `ASECLI-Temp-*`。
- 验收标准：两个进程均为团结 2022.3.61t9 + ASE 1.9.6.2；进程 B 的 manifest 与进程 A 一致；presentation valid；0 Shader/CS error；0 临时残留；原工程未变化。
- 验证方式：`ASECLI_EDITOR_CREATE_PROJECT=<隔离工程> ASECLI_TUANJIE_PATH=<团结可执行文件> uv run --frozen pytest -m bridge tests/test_editor_create_e2e.py`，辅以进程 B 回读、Editor log、hash 和清理扫描。
- 风险：MCP 重连/超时造成未知完成状态；复制不完整；误将原工程当隔离目标；新进程启动时触发导入写入。
- 回滚/降级方案：所有写入限定隔离副本；超时后先查目标和 staging，不立即重试；失败关闭进程并删除或移入废纸篓隔离副本，原工程不回滚也不触碰。
- 变更留档：更新 REG-0037/0038、TASK-0032、timeline 和新审计问题状态，写入团结/ASE/MCP 精确版本及脱敏证据路径。
- 计划外问题处理规则：记录，不展开；只有阻塞 P1.1 时暂停并请求确认。

### P1.2 迁移三份 release-record 并同步 SECURITY 支持版本

- 来源问题 ID：AUD-GOV-002
- 依赖：无
- 严重程度：S2
- 目标：完整 Project Architect strict（含 release）零发现，安全支持范围与 v0.2.0 正式版本一致。
- 范围：REL-0001、REL-0002、REL-0003、`traceability.csv`、`SECURITY.md`。
- 非目标：不改 Git tag、Release 资产、hash 或历史发布事实，不重发 v0.2.0。
- 涉及文件/模块/符号：frontmatter `type: release-record`、`变更集合`、`验证与风险`、`回滚`、REL 反向来源 ID、0.2.x 支持范围。
- 现有技术栈复用：Project Architect release checker、现有 REL 内容、GitHub Release 只读证据。
- 新增依赖：无。
- 技术路径：逐份按当前模板做兼容迁移，复用原有正文和真实资产证据；只补双向关联，不重写历史。
- 执行步骤：
  1. 将 23 项 release finding 固定成逐项清单，按 REL-0001→0002→0003 修正 type、章节和来源集合。
  2. 补 traceability 反向链接并把 SECURITY 当前支持范围升级到 0.2.x，同时保留 v0.1.0 回滚/历史说明。
  3. 运行完整 strict、文档链接/Release 只读复核和 diff check，确认 finding 为 0。
- 验收标准：`--check-release --strict` 所有列表为空；SECURITY 明确覆盖 v0.2.x；REL 中 commit/tag/hash 与现有远端完全一致。
- 验证方式：Project Architect strict JSON、`gh release view`/`git ls-remote --tags` 只读核对、`git diff --check`。
- 风险：迁移模板时篡改历史事实或错误扩大已发布范围。
- 回滚/降级方案：逐份 REL 独立提交/回退；任何远端证据不一致时停止，不修改远端资产。
- 变更留档：timeline 追加治理迁移，traceability 使用原 FR/CR/BUG/TASK/REG/REL 关联键。
- 计划外问题处理规则：记录，不展开；只有阻塞 P1.2 时暂停并请求确认。

### P1.3 固化稳定 FM 清单并补齐 tests/tools LOC 覆盖

- 来源问题 ID：AUD-GOV-003
- 依赖：无
- 严重程度：S2
- 目标：连续审计无需临时 supplement 即可得到同一组 FM ID，LOC 分类真正覆盖 source、tests、tools 和专用 C# 资源。
- 范围：项目级审计 supplement/配置、`.project-architect.json`、CI governance/coverage 测试。
- 非目标：不初始化 CodeGraph/OpenSpec，不改变功能模块实现，不重新编号已有 14 个稳定 FM。
- 涉及文件/模块/符号：`source_roots`、test/config 分类、14 个 `FM-*`、collector supplement、coverage validator。
- 现有技术栈复用：`audit_project.py collect/coverage`、JSON、现有 CI governance 与 pytest。
- 新增依赖：无。
- 技术路径：在仓库治理目录持久化唯一能力清单并由 collect/CI 引用；扩展扫描根或项目检查器，使 tests/tools 按其类别门禁。
- 执行步骤：
  1. 将本轮 14 FM 名称、ID、路径与证据路径固化，增加唯一 ID、路径存在和连续审计集合一致测试。
  2. 让 tests/tools 进入相应 LOC 分类，同时保持 `.cs.txt` 由专用检查和例外治理处理。
  3. 在 clean checkout 连续运行两次 collect/coverage/compare，确认无 ID 漂移和未覆盖项。
- 验收标准：自动/配置化采集输出 14 个相同 FM；15 FE 不变；tests/test_custom_gui.py 正确判为 test；故意超限 fixture 能使门禁失败。
- 验证方式：两次 `audit_project.py collect`、coverage、LOC JSON、CI governance 与测试。
- 风险：把临时审计文件打入发行包，或将 docs/fixtures 误计为生产源码。
- 回滚/降级方案：能力清单只作为治理输入并排除发行包；扫描分类异常时保留专用检查，不放宽阈值。
- 变更留档：module-map/toolchain/timeline 记录唯一事实源和 14 个稳定 ID；需求变更、技术决策和实际修改文件用 TASK/REG 关联。
- 计划外问题处理规则：记录，不展开；只有阻塞 P1.3 时暂停并请求确认。

### P1.4 为两个超限 C# 资源建立有期限的治理例外或安全拆分

- 来源问题 ID：AUD-SIZE-001
- 依赖：P1.3 的例外校验机制
- 严重程度：S2
- 目标：536/408 行资源不再依赖永久 path/reason 豁免，过期技术债可自动失败。
- 范围：`.project-architect.json`、例外 ADR/登记、CI governance；可选低风险 MaterialGUI 资源拆分。
- 非目标：不为了 LOC 数字破坏 Editor nonce 单事务、C# 编译、namespace 或 GUI 行为。
- 涉及文件/模块/符号：两个 `loc_exemptions`、owner、approved_by、created_at、expires_at、compensating_controls、exit_condition。
- 现有技术栈复用：现有配置、CI governance、GUI/Editor bridge tests、团结实机门禁。
- 新增依赖：无。
- 技术路径：先收紧例外 schema 和到期检查；再评估 MaterialGUI 的解析/呈现拆分。Editor create 仅在能确定性拼装为单 payload 时拆，否则用短期例外。
- 执行步骤：
  1. 为每项例外补完整治理字段和最长 30 天到期，并增加缺字段/过期会失败的测试。
  2. 评估并优先拆分低耦合 MaterialGUI；为 Editor create 记录单事务约束和退出条件。
  3. 运行资源 hash/打包、C# 编译、GUI/Editor bridge 与 P1.1 实机回归。
- 验收标准：例外字段完整、未过期且有明确 owner/批准/补偿控制/退出条件；过期测试失败；运行资源行为不变。
- 验证方式：CI governance tests、`wc -l`、wheel 内容/hash、GUI/Editor pytest 和团结实机。
- 风险：拆分改变 C# 拼装顺序或 MCP 固定 payload，造成运行回归。
- 回滚/降级方案：优先只收紧治理；任何实机回归恢复单文件资源，保留短期例外继续跟踪。
- 变更留档：新增 ADR/例外债务记录、TASK/REG/timeline，关联 AUD-SIZE-001。
- 计划外问题处理规则：记录，不展开；只有阻塞 P1.4 时暂停并请求确认。

### P1.5 完成 layout/comment-group 真实画布与入口状态闭环

- 来源问题 ID：AUD-FLOW-003 AUD-FE-002
- 依赖：P1.1 提供可用的指定版本隔离 Editor
- 严重程度：S2
- 目标：结构成功与真实画布可读性都能被 Agent 和维护者明确判断。
- 范围：代表性小/中/复杂 ASE 图、layout、comment-group live bounds/check/fit、normal zoom 截图/状态。
- 非目标：不改 Shader 参数、连接和计算，不为整齐增加无用节点或重复计算。
- 涉及文件/模块/符号：`layout.py`、`comment_bounds.py`、`commentary.py`、FE layout/comment-group、layout standard。
- 现有技术栈复用：现有 CLI、ASE `TruePosition`、结构 diff、pytest、截图人工验收。
- 新增依赖：无。
- 技术路径：在隔离工程执行 dry-run→live bounds→fit→normal zoom 复核；入口输出或治理记录显式区分 structural success 与 visual pending/passed。
- 执行步骤：
  1. 固定三类金样和只允许位置/Comment 变化的语义 diff。
  2. 运行 layout/comment-group live 检查，保存 bounds、截图与无穿节点/端口/标题栏结果。
  3. 将结构条件自动化，将视觉状态加入入口契约或关联验收记录，并复验备份/`.meta`。
- 验收标准：左到右阶段、重复分支和 Comment 对齐；Comment 不重叠/完整包含；连线不穿无关节点/端口/标题栏；normal zoom 可读；计算语义不变。
- 验证方式：结构 hash/diff、live bounds JSON、CLI contract、真实画布截图和人工签收。
- 风险：节点尺寸/贝塞尔路径随版本变化；自动布局误改生产图。
- 回滚/降级方案：只用隔离副本和 `.asecli-backups`；视觉失败恢复位置/Comment，禁止改计算图。
- 变更留档：新增 REG/视觉验收记录并关联 FR-0008/0010、两个 AUD ID 和实际截图环境。
- 计划外问题处理规则：记录，不展开；只有阻塞 P1.5 时暂停并请求确认。

### P1.6 完成 Material Inspector 最小 UI/可访问性矩阵

- 来源问题 ID：AUD-UI-001
- 依赖：P1.1 提供可用的指定版本隔离 Editor；若 P1.4 拆分 GUI，必须在拆分后执行
- 严重程度：S2
- 目标：正式 MaterialGUI 在主要皮肤、缩放、宽度、文本和多选/焦点状态下可读可操作。
- 范围：Color/Float/Range/Texture/Toggle 代表属性，中文 display/help、技术 Tooltip、Foldout、disabled/mixed-value/focus。
- 非目标：不重新设计 Inspector，不改变 Shader property、默认值或材质实例值。
- 涉及文件/模块/符号：`asecli_material_gui.cs.txt`、GUI fixtures、默认 Material(shader) 读取、inline-help contract。
- 现有技术栈复用：现有 MaterialGUI、团结 Editor、GUI/property pytest、真实截图。
- 新增依赖：无。
- 技术路径：在 P1.1 同一隔离环境执行 dark/light、常规/高缩放、窄/常规宽度、长中文、焦点和 mixed-value 最小矩阵。
- 执行步骤：
  1. 固定代表 Shader/材质与矩阵，定义每项可自动断言和人工观察内容。
  2. 逐组合验证中文标签/换行、Tooltip 变量名/默认值、HelpBox、Foldout、焦点和多选状态。
  3. 只对阻塞性 UI 缺陷做最小展示层修复，再跑 C# 编译、属性合同和全矩阵。
- 验收标准：必测组合无裁切/遮挡/错误默认值；鼠标与键盘关键操作可达；属性合同 0 violation。
- 验证方式：Editor 自动断言、带环境标注的截图/人工清单、GUI/属性全量 pytest。
- 风险：IMGUI Tooltip/focus 自动化不稳定；系统缩放影响截图比较。
- 回滚/降级方案：自动化不了的状态保留人工门禁；展示修复回归时恢复上一 GUI 资源。
- 变更留档：新增 UI REG/验收矩阵，关联 FR-0009/0011、CR-0010/0012、AUD-UI-001。
- 计划外问题处理规则：记录，不展开；只有阻塞 P1.6 时暂停并请求确认。

### P2.1 升级 GitHub Actions 到原生 Node 24 runtime

- 来源问题 ID：AUD-CI-001
- 依赖：P1.2 可独立；避免与正式 v0.2.0 资产重发混合
- 严重程度：S3
- 目标：CI action 自身声明 Node 24，正式 run 不再依赖 GitHub 强制兼容层。
- 范围：`.github/workflows/ci.yml`、CI governance allowlist/测试。
- 非目标：不升级 Python 依赖、不改变 job 结构、不重新发布 v0.2.0。
- 涉及文件/模块/符号：actions/checkout、astral-sh/setup-uv、actions/upload-artifact 的官方 Node 24 兼容版本和固定 SHA。
- 现有技术栈复用：官方 GitHub Actions、完整 SHA、现有治理脚本。
- 新增依赖：无。
- 技术路径：只读确认官方版本与 commit，最小替换固定 SHA，同步治理断言后观察新 run。
- 执行步骤：
  1. 核对三个 action 的官方 Node 24 支持版本、release notes 和完整 commit SHA。
  2. 最小更新 workflow/allowlist，运行本地 CI governance 与测试。
  3. 推送后核对三 job、日志、artifact digest 和隔离安装，确认弃用警告消失。
- 验收标准：新 run 全绿；无 Node 20/相关弃用 API 警告；action 仍固定 SHA；包 hash/安装流程不回归。
- 验证方式：CI 日志、`tools/check_ci_governance.py`、pytest、artifact 下载/安装 smoke。
- 风险：新 action 版本改变缓存、上传或权限语义。
- 回滚/降级方案：恢复上一固定 SHA，记录 GitHub 强制迁移截止日期和临时风险。
- 变更留档：更新 technical-route/REG/timeline，关联 AUD-CI-001 和新 run URL。
- 计划外问题处理规则：记录，不展开；只有阻塞 P2.1 时暂停并请求确认。

## 执行结果（2026-09-03）

- P1.1：团结 `2022.3.61t9` + ASE `1.9.6.2` 的 v2 创建进程与全新重开进程 manifest/presentation 一致，0 Shader/CS error，0 staging 残留；原工程 hash 不变。
- P1.2～P1.3：三份 REL、安全支持版本、14 FM/15 FE 与 tests/tools/C# LOC 已进入唯一事实源和治理门禁。
- P1.4 后续清零：CR-0014 将 GUI/Editor C# 分别拆为 300/283 与 205/205 行片段，拼装字节与单事务边界不变；EXC-0001/0002 删除。已知旧 GUI 的备份/复核/原子升级及失败恢复自动通过，团结 `2022.3.61t9` GUI 编译 `1 passed/26.15s`，ASE `1.9.6.2` 干净隔离双进程 `1 passed/39.86s`。
- P1.5：四类真实图的 wire/计算语义保持不变，TruePosition containment 与正常缩放画布人工验收通过；证据见 `docs/03-quality/evidence/REG-0041/`。
- P1.6：发现并修复长中文标签截断和 Tooltip 浮点噪声；深/浅色、300/480px、Retina、Foldout、mixed、disabled、focus/Tab 通过；证据见 `docs/03-quality/evidence/REG-0042/`。
- P2.1：checkout v5.0.1、setup-uv、upload-artifact 已切换官方 Node 24 固定 SHA并新增 allowlist 防回退。首次授权推送后的 run 33713836753 三项 job 全绿且清除了 Node 20 强制兼容警告，但日志仍暴露 setup-uv v7.1.6 的 `DEP0040`/`DEP0169`；门槛保持开放并升级到当前官方不可变 v10.0.1，等待第二次远程 run。
- 计划外发现已处理：已知 `0.2.0-original` 旧 GUI 已具备可恢复升级；任意未知内容仍以 `target_conflict` 安全拒绝。干净 E2E 的空 Generated 目录会被首次刷新移除，已登记 BUG-0021 并用隐藏占位修复。

## 进度更新模板

```markdown
## TODO

P1 应该完成
- [*] P1.1 在本机完成 ASE 1.9.6.2 EditorGraphSpec v2 双进程闭环
- [ ] P1.2 迁移三份 release-record 并同步 SECURITY 支持版本

当前进展：
- 已完成：
- 正在做：
- 下一步：
- 阻塞/风险：
```

## Definition of Done

- [x] 所有 S0/S1 和 P0/P1 问题均映射到 TODO，且每个 TODO 有完整详情。
- [x] 已按 `.project-architect.json` 的分类阈值执行 LOC 门禁，source/tests/tools/C# 资源、排除项、截断和超限/例外均有证据。
- [x] P0 完成并通过相关测试、构建或替代验证；当前无 P0，交付时明确为不适用。
- [x] 回归覆盖受影响模块和关键链路，Editor/画布/UI/CI 分层证据均不互相替代。
- [x] OpenSpec 与 CodeGraph 的更新或不适用原因已说明；当前不为整改机械初始化。
- [x] 需求变更、技术决策和实际修改文件已按现有机制增量留档并关联。
- [x] 审计范围内每个功能模块均完成需求→入口→主路径→数据/状态→异常恢复→可观测性→回归→发布证据对账。
- [x] 审计范围内每个前端入口均有闭环结论，create/layout/comment-group 的问题由 P1.1/P1.5 解除。
- [x] 七类专项工程审计均有状态，P0/P1 专项问题均映射 TODO。
- [x] 请求/实际审计模式及降级原因已说明；增量对比区分已解决、改善、未变化和新增发现。
- [x] UI 任务的 Product Design 不适用原因、真实视觉证据和可访问性验证情况已说明。
- [x] 计划外发现已记录但未扩展处理；不使用 Unity 2021，不写生产工程，不泄露凭证。

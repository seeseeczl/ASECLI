# 项目优化任务书

## 执行原则

- 只执行本任务书事项，先 P0，再 P1，再 P2；当前没有 P0，P1 按依赖顺序推进，每次只处理一个可观察结果。
- 证据必须区分静态、自动测试、当前 Editor 实例、新进程/目标平台、远端 CI 与正式 Release；未运行门禁不得标为通过。
- 默认复用 Python/uv/pytest、现有团结/ASE bridge、GitHub Actions/Release 和 Project Architect，不引入新依赖、不降低 strict 规则。
- 测试失败执行 Test-Fix Loop；非阻塞计划外问题只记录，不顺手重构或扩大公开发布范围。

## 总目标

- 将 ASECLI 从“核心 CLI 与 0.2.0 候选可重复”提升为“治理、Editor/视觉验收和私有正式发布均可标准化重复”的 L3 交付状态。

## 范围

- 同时间戳审计报告中的 9 个开放问题：严格治理、LOC 扫描、C# 资源规模、EditorGraphSpec v2、布局/Comment 视觉、0.2.0 私有发布、Inspector UI 矩阵、供应链在线证据和 CI runtime 告警。

## 非目标

- 不公开仓库，不上传 PyPI/CLI Hub，不支持未经验证的 ASE/团结版本，不修改 VehicleLocalShadow 设计效果，不删除 Receiver 的 10 个候选节点，不以重写架构替代最小整改。

## 问题到任务映射

| 问题 ID | 严重程度 | 优先级 | TODO ID | 处理方式 |
| --- | --- | --- | --- | --- |
| AUD-GOV-002 | S1 | P1 | P1.1 | 单独处理：恢复 strict 治理/发布零发现 |
| AUD-GOV-003 | S2 | P1 | P1.2 | 单独处理：迁移 LOC 配置与覆盖范围 |
| AUD-SIZE-001 | S2 | P1 | P1.3 | 单独处理：拆分资源或登记合规例外 |
| AUD-FLOW-002 | S1 | P1 | P1.4 | 单独处理：完成 v2 新进程和目标平台闭环 |
| AUD-FLOW-003 | S2 | P1 | P1.5 | 单独处理：建立真实画布视觉门禁 |
| AUD-REL-001 | S1 | P1 | P1.6 | 单独处理：发布 0.2.0 私有正式版本 |
| AUD-UI-001 | S2 | P1 | P1.7 | 单独处理：完成 Inspector UI 矩阵 |
| AUD-SUPPLY-002 | S3 | P2 | P2.1 | 单独处理：补在线状态与全载荷校验 |
| AUD-CI-001 | S3 | P2 | P2.2 | 单独处理：升级固定 Action runtime |

## TODO

P0 必须完成

- 当前无 P0。

P1 应该完成

- [ ] P1.1 恢复完整 Project Architect strict 治理与发布门禁
- [ ] P1.2 修正 LOC 配置并消除 tests/tools/C# 资源扫描盲区
- [ ] P1.3 收敛两个超限生产 C# 资源的职责与例外债务
- [ ] P1.4 完成 EditorGraphSpec v2 新进程与目标平台端到端验收
- [ ] P1.5 建立 layout/comment-group 正常缩放真实画布验收
- [ ] P1.6 将 0.2.0 作为一致、可回滚的私有正式 CLI 发布
- [ ] P1.7 完成 Material Inspector UI 与可访问性最小矩阵

P2 可选优化

- [ ] P2.1 补齐正式载荷校验与在线漏洞状态证据
- [ ] P2.2 升级 GitHub Actions Node runtime 并保持固定 SHA

## 任务详情

### P1.1 恢复完整 Project Architect strict 治理与发布门禁

- 来源问题 ID：AUD-GOV-002
- 依赖：无
- 严重程度：S1
- 目标：当前治理、追溯、模块边界和 REL 记录通过包含 release 的 strict 检查。
- 范围：`docs/00-governance/traceability.csv`、`docs/01-architecture/module-map.md`、`docs/03-quality/regression-catalog.md`、`docs/04-delivery/project-plan-task-charter.md`、`docs/04-delivery/releases/**`、core 公共接口与 4 个私有导入调用点。
- 非目标：不改变业务行为，不删减追溯对象，不放宽或关闭 strict 规则。
- 涉及文件/模块/符号：TASK-0026/0028、CR-0008/0009/0010、FR-0011、BUG-0010～0014、REG-0031～0035、REL-0001/0002、`core/__init__.py`/contracts、`checks/usage.py`、`bridge/gui_support.py`。
- 现有技术栈复用：Project Architect、Markdown/CSV、Python 公共 re-export、pytest。
- 新增依赖：无。
- 技术路径：按 strict JSON 的 50 项逐条修复双向链接与 REL schema；为 checks/bridge 增加最小公共导出并替换私有导入；每组变更后回归对应模块。
- 执行步骤：
  1. 锁定 2 项 kickoff、25 项 traceability、4 项 fitness、19 项 release 的逐项修复表，避免合并时漏项。
  2. 先修复文档双向追溯和 REL 当前模板，再增加 core 最小公共接口并迁移 4 个导入。
  3. 运行 strict（含 release）、REG catalog、相关定向测试和全量 pytest，回写真实证据。
- 验收标准：strict JSON 各 finding 列表为空；所有源 ID 均可双向回链；跨模块私有导入为 0；现有 223 条测试不回归。
- 验证方式：Project Architect strict、`tools/check_regression_catalog.py`、import contract 测试、`uv run --frozen pytest -q`、`git diff --check`。
- 风险：为通过检查而补错关联，或公共接口迁移导致循环依赖。
- 回滚/降级方案：文档按对象分批回退；公共 API 采用 additive re-export，若出现循环依赖则恢复调用并保留 finding，不伪造通过。
- 变更留档：新增/更新对应 TASK、REG、timeline、traceability 与 release-record；需求变更、技术决策和实际修改文件使用原关联键回写。
- 计划外问题处理规则：记录，不展开；只有阻塞 P1 时暂停并请求确认。

### P1.2 修正 LOC 配置并消除扫描盲区

- 来源问题 ID：AUD-GOV-003
- 依赖：P1.1 可并行设计，最终验证与 P1.3 联动
- 严重程度：S2
- 目标：LOC 门禁实际扫描 source、test、tools 和打包 C# 资源，并使用仓库声明的分类阈值。
- 范围：`.project-architect.json`、Project Architect 项目级检查适配、对应治理测试。
- 非目标：不改变 250/400、400/600、160/200 阈值，不把所有普通文档 `.txt` 当生产源码。
- 涉及文件/模块/符号：`thresholds`、`source_roots`、`extensions` 或专用 `.cs.txt` 发现规则、LOC fixture。
- 现有技术栈复用：现有 JSON 配置、Project Architect LOC 检查器、pytest。
- 新增依赖：无。
- 技术路径：把 `loc_thresholds` 迁移为 `thresholds`，显式加入 `tests`/`tools`；优先以受限规则识别 `src/asecli/bridge/resources/*.cs.txt`，避免全局 `.txt` 误报。
- 执行步骤：
  1. 添加配置解析和故意超限 fixture，使旧配置/漏扫问题先稳定复现。
  2. 迁移配置与扫描规则，核对每类文件的 category、warning、limit。
  3. 运行 LOC、strict 和全量测试，记录新增真实 finding 并交给 P1.3，不隐藏超限。
- 验收标准：三个目标根目录与两个 C# 资源均被发现；`tests/test_custom_gui.py` 判为 test；阈值来自唯一 `thresholds`；超限 fixture 必然使门禁失败。
- 验证方式：LOC JSON 路径/类别断言、Project Architect strict、自测试与仓库全量 pytest。
- 风险：简单加入 `.txt` 导致文档大量误报，或 tests 被误分到 source。
- 回滚/降级方案：若通用扫描器无法表达双后缀，保留标准扩展列表并新增项目专用只读检查，不扩大 `.txt` 扫描面。
- 变更留档：登记配置 schema 迁移的 ADR/TASK/REG，timeline 记录旧结果为何存在盲区及新的扫描口径。
- 计划外问题处理规则：记录，不展开；只有阻塞 P1 时暂停并请求确认。

### P1.3 收敛两个超限生产 C# 资源的职责与例外债务

- 来源问题 ID：AUD-SIZE-001
- 依赖：P1.2
- 严重程度：S2
- 目标：两个生产 C# 资源均满足 400 行硬上限，或存在具备 owner、批准人、到期日、补偿测试和退出条件的临时 ADR 例外。
- 范围：`src/asecli/bridge/resources/asecli_material_gui.cs.txt`、`editor_create.cs.txt`、资源加载/安装代码和相关测试。
- 非目标：不改 namespace、CLI 协议、属性呈现契约、EditorGraphSpec schema 或目标安装路径。
- 涉及文件/模块/符号：MaterialGUI provider/drawer/default value formatting；Editor session/spec execution/manifest/rollback；`importlib.resources` 加载与 C# 拼装。
- 现有技术栈复用：现有 Python 包资源、团结 C# 编译、bridge/UI pytest。
- 新增依赖：无。
- 技术路径：先冻结最终拼装文本和运行行为，再把独立职责拆为多个固定资源由安装器确定性组合；若当期风险过高，先创建最短期限 ADR 例外。
- 执行步骤：
  1. 建立资源顺序、namespace、类名和最终生成文本的契约测试，并保存当前支持环境 smoke 基线。
  2. 分别拆分 MaterialGUI 与 Editor create 的低耦合职责，保持最终 API 和行为不变。
  3. 运行 LOC、临时工程 C# 编译、Inspector/Editor E2E 与全量测试；无法安全拆分则登记到期例外。
- 验收标准：每个生产源单元不超过 400 行或例外字段完整未过期；GUI 与 Editor create 的成功/失败/回滚结果与基线一致。
- 验证方式：LOC strict、资源契约测试、临时工程编译、`test_custom_gui.py`/`test_gui_support.py`/editor bridge E2E。
- 风险：资源拼装顺序破坏 C# 声明、Unity 编译或反射成员定位。
- 回滚/降级方案：保留旧单资源载荷的可恢复版本；任何实机回归立即回退，不以 LOC 通过覆盖功能失败。
- 变更留档：ADR 记录拆分边界或临时例外，TASK/REG/timeline 记录实际文件、支持版本和实机证据。
- 计划外问题处理规则：记录，不展开；只有阻塞 P1 时暂停并请求确认。

### P1.4 完成 EditorGraphSpec v2 新进程与目标平台端到端验收

- 来源问题 ID：AUD-FLOW-002
- 依赖：P1.3（若资源被拆分）；否则可先在当前资源版本执行
- 严重程度：S1
- 目标：证明 v2 创建结果跨 Editor 进程可重开，并在目标平台完成编译、材质绑定和最终渲染验收。
- 范围：隔离或明确授权的团结 `2022.3.61t9` + ASE `1.9.6.2` 工程、EditorGraphSpec v2 fixture、bridge E2E、目标平台证据。
- 非目标：不使用 Unity 2021 代替团结，不修改未经授权生产 Shader，不扩展未知 ASE 版本。
- 涉及文件/模块/符号：`tests/test_editor_create_e2e.py`、`editor_create.py`、v2 spec、manifest/reconciliation、临时材质/场景/渲染金样。
- 现有技术栈复用：现有 MCP bridge、团结命令行、pytest marker、manifest/hash、`.asecli-backups`。
- 新增依赖：无。
- 技术路径：执行 create→关闭 Editor→新进程启动→Load/manifest 对账→独立 recompile→目标平台编译→材质绑定→渲染验收，全程使用可清理临时资产。
- 执行步骤：
  1. 准备固定 v2 Caster/Receiver-like fixture 和安全清理清单，记录初始工程/进程状态。
  2. 完成当前进程创建后关闭并以新进程重开，核对节点、线、属性、CustomEditor、默认值与零暂存残留。
  3. 运行目标平台编译、材质绑定和最终画面验收，保存脱敏日志/截图/manifest，并清理验证资产。
- 验收标准：新进程语义 manifest 一致；0 Shader/CS error；目标平台编译与材质绑定成功；最终画面有人工签收或金样；临时目标、`.meta`、`ASECLI-Temp-*` 清理结果明确。
- 验证方式：条件 bridge pytest、Editor log、manifest/hash、平台构建日志、材质/截图证据、清理后扫描。
- 风险：GUI 生命周期/MCP 超时导致完成状态未知，或目标平台验证修改工程状态。
- 回滚/降级方案：只用隔离/授权工程和唯一测试前缀；超时后先查目标与 staging，不立即重试；失败恢复备份并保留日志。
- 变更留档：更新 REG-0037/0038、TASK-0032、test-strategy、timeline 和对应 REL 验证字段。
- 计划外问题处理规则：记录，不展开；只有阻塞 P1 时暂停并请求确认。

### P1.5 建立 layout/comment-group 正常缩放真实画布验收

- 来源问题 ID：AUD-FLOW-003
- 依赖：无；若使用 Editor 自动化则复用 P1.4 的受控环境
- 严重程度：S2
- 目标：把“结构正确”提升为“在 ASE 正常缩放下可重复验证的视觉可读”。
- 范围：代表性小/中/复杂 ASE 图、layout、comment-group live bounds、现有布局规范与截图证据。
- 非目标：不修改 Shader 参数、端口连接、计算顺序，不为整齐而增加无用 Local Var 或重复计算。
- 涉及文件/模块/符号：`core/layout.py`、`core/comment_bounds.py`、`commentary.py`、`references/layout-standard.md`、布局/Comment fixtures。
- 现有技术栈复用：现有 CLI、ASE `TruePosition`、pytest、结构 diff 和人工画布复核。
- 新增依赖：无。
- 技术路径：以三类图执行 dry-run→live bounds→fit→normal zoom 截图；自动断言框包含/重叠和结构不变，人工检查连线不穿无关节点、端口、标题栏。
- 执行步骤：
  1. 固定三类最小金样及“只允许位置/Comment 变化”的语义 diff 规则。
  2. 在真实 ASE 运行 layout/comment-group check/fit，保存 live bounds 与 normal zoom 截图。
  3. 将可自动条件固化为 REG，视觉条件形成可重复签收清单并验证备份/`.meta` 不变。
- 验收标准：阶段从左到右、重复分支对齐、Comment 不重叠且父子完整包含、线路不穿无关节点/端口/标题栏、normal zoom 可读；计算语义不变。
- 验证方式：结构 hash/diff、live bounds JSON、截图人工清单、布局/Comment 全量测试。
- 风险：ASE 贝塞尔路径或节点尺寸随版本/缩放变化，导致离线结论不稳定。
- 回滚/降级方案：视觉失败立即恢复 `.asecli-backups`；保留结构验证通过但视觉未通过的明确状态，不自动改计算图。
- 变更留档：新增 REG 与视觉验收记录，关联 FR-0008/0010、TASK 和实际金样/截图路径。
- 计划外问题处理规则：记录，不展开；只有阻塞 P1 时暂停并请求确认。

### P1.6 将 0.2.0 作为一致、可回滚的私有正式 CLI 发布

- 来源问题 ID：AUD-REL-001
- 依赖：P1.1、P1.4；P1.5/P1.7 若被定义为 0.2.0 release gate 也必须完成
- 严重程度：S1
- 目标：私有仓库授权用户可从固定 v0.2.0 Release 安装、验证和回滚，代码、文档、支持范围与发布记录一致。
- 范围：`pyproject.toml`、README、SECURITY、REL、Git tag、GitHub Actions/Release assets、隔离 uv tool 安装。
- 非目标：不公开仓库，不发布 PyPI/CLI Hub，不删除或移动 v0.1.0 tag/Release。
- 涉及文件/模块/符号：version 0.2.0、15 子命令、`asecli.property-presentation.v1`、EditorGraphSpec v2、SHA256SUMS、SBOM、release-record。
- 现有技术栈复用：GitHub Actions/Release、uv tool、Hatchling、现有 SBOM/供应链/hash 脚本。
- 新增依赖：无。
- 技术路径：冻结通过门禁的 commit，统一 README/SECURITY/REL 版本和安装命令，生成候选并下载复验，随后创建 v0.2.0 tag 与私有非预发布 Release。
- 执行步骤：
  1. 确认依赖任务和 strict/测试/Editor 门禁全绿，锁定 commit 与完整载荷清单。
  2. 更新支持范围与 release-record，创建 tag/Release，上传 wheel、sdist、SBOM、供应链报告和校验资产。
  3. 从空目录下载全部资产，验证 hash/SBOM，隔离安装并运行 15 命令发现与 parse/custom-gui smoke，再演练回滚 v0.1.0。
- 验收标准：v0.2.0 tag 指向唯一通过 commit；Release 非 draft/prerelease；所有载荷可校验；隔离 `uv tool` 安装可用；回滚成功；release strict 零发现。
- 验证方式：远端 run/Release URL、tag commit、asset digest、空目录校验、隔离安装/卸载/回滚、README 命令复跑。
- 风险：tag 指错 commit、清单路径再次漂移、文档仍引导安装 v0.1.0 或遗漏安全支持范围。
- 回滚/降级方案：发布前不移动 v0.1.0；失败时撤下错误资产/Release 并通知试用者，回滚到已验证 v0.1.0 wheel。
- 变更留档：使用当前 release-record 模板回写 CR/FR/BUG/TASK/REG、run、tag、artifact、哈希与回滚；需求变更、技术决策和实际修改文件全部可双向追溯。
- 计划外问题处理规则：记录，不展开；只有阻塞 P1 时暂停并请求确认。

### P1.7 完成 Material Inspector UI 与可访问性最小矩阵

- 来源问题 ID：AUD-UI-001
- 依赖：P1.3（若 MaterialGUI 资源拆分）；可与 P1.5 共用真实 Editor 环境
- 严重程度：S2
- 目标：正式支持环境中的 Inspector 在常见皮肤、缩放、宽度、文本和输入状态下保持可读可操作。
- 范围：ASECLI MaterialGUI、代表性 Color/Float/Range/Texture/Toggle 属性、中文显示名/HelpBox、技术 Tooltip、Foldout。
- 非目标：不重新设计 Inspector，不改变 Shader 属性语义、默认值或用户材质实例值。
- 涉及文件/模块/符号：`asecli_material_gui.cs.txt`、GUI fixtures、default `Material(shader)` 读取、mixed-value/disabled/focus 状态。
- 现有技术栈复用：团结 Editor、现有临时工程/材质、截图、GUI/property pytest。
- 新增依赖：无。
- 技术路径：定义 dark/light、100%/高缩放、窄/常规宽度、长中文、键盘焦点、disabled/mixed-value 的最小矩阵；自动断言数据层，真实界面完成视觉签收。
- 执行步骤：
  1. 固定代表性 Shader/材质和验收矩阵，明确每项期望与证据类型。
  2. 运行各组合并记录中文标签、换行、Tooltip 技术信息、HelpBox、Foldout、焦点和多选状态。
  3. 对发现的阻塞 UI 缺陷做最小修复，重跑属性契约、C# 编译和矩阵。
- 验收标准：所有必测组合无裁切/遮挡/错误默认值；鼠标和键盘均可完成关键操作；属性契约保持 0 violation。
- 验证方式：Editor 自动断言、标注环境的真实截图/人工签收、GUI/属性全量 pytest。
- 风险：团结/IMGUI 对系统缩放和皮肤行为差异大，自动化无法稳定触发所有 Tooltip/焦点状态。
- 回滚/降级方案：只修改展示层；若某组合无法自动化则保留人工门禁，出现回归时恢复上一 C# 资源。
- 变更留档：新增 UI REG/验收矩阵，关联 FR-0009/0011、CR-0010/0012、TASK 和截图环境信息。
- 计划外问题处理规则：记录，不展开；只有阻塞 P1 时暂停并请求确认。

### P2.1 补齐正式载荷校验与在线漏洞状态证据

- 来源问题 ID：AUD-SUPPLY-002
- 依赖：P1.6
- 严重程度：S3
- 目标：正式 v0.2.0 的每个发布载荷可离线校验，在线漏洞/Dependabot 状态有带时间戳的只读证据。
- 范围：Release assets、SHA256SUMS、SBOM、供应链报告、GitHub security 状态。
- 非目标：不在日志/报告写入 token，不因第三方在线服务不可用而伪造通过。
- 涉及文件/模块/符号：CI package job、hash 生成脚本、SBOM name/version、Release 下载复验。
- 现有技术栈复用：现有 Python hash/SBOM/supply-chain 工具、GitHub API/CLI。
- 新增依赖：无。
- 技术路径：从单一 manifest 生成根目录文件名条目，上传后在空目录下载并逐项校验；只读查询在线告警并记录权限/时间边界。
- 执行步骤：
  1. 定义正式载荷集合和清单自引用排除规则，增加治理回归。
  2. 发布后下载全部资产并逐项校验 hash、SBOM name/version 与包内容。
  3. 查询在线漏洞/Dependabot 状态，脱敏回写 REL；不可查询则标为未验证。
- 验收标准：除清单自身外所有载荷均有唯一条目并校验成功；SBOM 为 0.2.0；在线状态结论有时间戳和权限说明。
- 验证方式：空目录 SHA-256 校验、SBOM JSON 断言、wheel/sdist 内容检查、GitHub 只读证据。
- 风险：不同平台 hash 工具语法、Release 下载重命名或在线 API 权限不足。
- 回滚/降级方案：校验失败撤下错误资产并重新生成；在线不可用明确降级为未验证，不扩大权限。
- 变更留档：更新 REL 验证与风险、供应链策略、REG 和 timeline，关联 v0.2.0 tag/run。
- 计划外问题处理规则：记录，不展开；只有阻塞 P1 时暂停并请求确认。

### P2.2 升级 GitHub Actions Node runtime 并保持固定 SHA

- 来源问题 ID：AUD-CI-001
- 依赖：P1.6 可前置执行；不得与正式发布混入无法归因的大改
- 严重程度：S3
- 目标：CI 使用明确支持 Node 24 的 action 版本，消除 Node 20 弃用警告且保持供应链固定 SHA。
- 范围：`.github/workflows/ci.yml`、`tools/check_ci_governance.py` 及相关测试。
- 非目标：不升级 Python 工具链、改变 job 拆分或增加第三方 action。
- 涉及文件/模块/符号：checkout/setup-uv 等固定 action 引用、allowlist/版本断言。
- 现有技术栈复用：GitHub 官方 actions、完整 commit SHA、现有 CI governance。
- 新增依赖：无。
- 技术路径：核对上游官方 release/commit，选择 Node 24 兼容版本并固定 SHA；同步静态治理断言后观察真实 run。
- 执行步骤：
  1. 只读确认各 action 的官方 Node 24 支持版本和固定 commit SHA。
  2. 最小更新 workflow 与 governance fixture，运行本地静态检查和测试。
  3. 推送后核对三 job、告警、artifact digest 与隔离安装 smoke。
- 验收标准：真实 run 全绿、无 Node 20 弃用警告、所有 action 固定完整 SHA、候选包和 hash 行为不变。
- 验证方式：workflow diff、`check_ci_governance.py`、相关 pytest、GitHub Actions 日志与 artifact 复验。
- 风险：action 主版本行为变化或新 SHA 尚未稳定。
- 回滚/降级方案：恢复上一固定 SHA，并在 GitHub 强制迁移日期前登记明确到期风险。
- 变更留档：更新 CI 治理 REG、technical-route/timeline 和对应 run URL；实际修改文件与 commit 双向关联。
- 计划外问题处理规则：记录，不展开；只有阻塞 P1 时暂停并请求确认。

## 进度更新模板

```markdown
## TODO

P1 应该完成
- [*] P1.1 恢复完整 Project Architect strict 治理与发布门禁
- [ ] P1.2 修正 LOC 配置并消除 tests/tools/C# 资源扫描盲区

当前进展：
- 已完成：
- 正在做：
- 下一步：
- 阻塞/风险：
```

## Definition of Done

- [ ] 所有 S0/S1 和 P0/P1 问题均映射到 TODO，且每个 TODO 有完整详情；本任务书 7 个 P1、2 个 P2 已双向映射。
- [ ] 已按 `.project-architect.json` 的分类阈值执行 LOC 门禁，排除项、截断和超限项均已记录，`.cs.txt` 不再漏扫。
- [ ] P0 完成并通过相关测试、构建或替代验证；当前无 P0，此项在交付时明确记为不适用而非伪造执行。
- [ ] 回归覆盖受影响模块和关键链路，strict（含 release）、REG、pytest、Editor/UI/远端证据按风险分层通过。
- [ ] OpenSpec 与 CodeGraph 的更新或不适用原因已说明；除非另有架构决策，不为整改机械初始化。
- [ ] 需求变更、技术决策和实际修改文件已按现有机制增量留档并关联。
- [ ] 审计范围内每个功能模块均完成“需求→入口→主路径→数据/状态→异常恢复→可观测性→回归→发布证据”闭环对账。
- [ ] 审计范围内每个前端入口均有闭环结论；layout、comment-group、create 的部分闭环均由对应 P1 解除。
- [ ] 七类专项工程审计均有状态，P0/P1 专项问题均映射 TODO。
- [ ] 请求/实际审计模式及降级原因已说明；增量对比已写入报告并区分回归、功能增长和规则升级暴露的历史盲区。
- [ ] UI 任务的 Product Design 不适用原因、真实视觉证据和可访问性验证情况已说明。
- [ ] 计划外发现已记录但未扩展处理，未公开仓库、未删除业务资产、未泄露宿主凭证。

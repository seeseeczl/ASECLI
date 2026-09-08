---
id: OPT-2026-09-08-130015
type: optimization-tasks
status: verified
version: 2
created_at: 2026-09-08T13:00:15+08:00
owner: long
related: [AUD-2026-09-08-130015]
supersedes: []
evidence: [docs/05-audits/2026-09-08-130015-project-audit-report.md]
---

# 项目优化任务书

## 执行原则

- 只执行本任务书事项，先 P0，再 P1，再 P2；每次只推进一个任务，不擅自扩大范围。
- 整改已获用户授权并按原 TODO 顺序完成；发布、tag、PyPI 和 CLI Hub 仍需独立授权。
- 保留用户现有 EditorGraphSpec v3 WIP、历史审计和提案，不 stash/reset/clean，不使用宽泛 `git add`。
- 默认复用现有 Python/uv/pytest/GitHub Actions/Project Architect 技术栈；不新增运行时依赖。
- 测试失败执行 Test-Fix Loop；非阻塞计划外问题只记录。

## 总目标

- 在下一次公开 tag 前，让 ASECLI 达到“声明可用、变更可追、门禁唯一、产物可验、发布可恢复”的 L3 发布治理基线。

## 范围

- PyPI 安装声明与发布状态、tag 发布门禁、完整治理 strict、v3 WIP 追溯、REL-0008～11、core/cli 边界、C# LOC 预警。

## 非目标

- 不在本任务书中实现 SGCLI、不重写 EditorGraphSpec v3、不修改 ASE 图算法、不启动生产工程、不自动发布 PyPI/CLI Hub、不删除历史 Release/tag。

## 问题到任务映射

| 问题 ID | 严重程度 | 优先级 | TODO ID | 处理方式 |
| --- | --- | --- | --- | --- |
| AUD-FLOW-004 | S1 | P0 | P0.1 | 单独闭合公开安装事实 |
| AUD-GOV-004 | S1 | P0 | P0.2 | 单独统一发布硬门禁 |
| AUD-FLOW-005 | S1 | P1 | P1.1 | 与同一 create 入口证据合并 |
| AUD-FE-007 | S2 | P1 | P1.1 | 与 v3 变更链合并 |
| AUD-REL-002 | S2 | P1 | P1.2 | 单独修复历史发布记录 |
| AUD-MOD-002 | S2 | P1 | P1.3 | 单独收口模块公共面 |
| AUD-SIZE-002 | S3 | P2 | P2.1 | 可选、受控优化 |

## TODO

P0 必须完成

- [x] P0.1 恢复真实可用的正式安装入口并闭合 CR-0023/REL 状态
- [x] P0.2 让公开 tag 发布强制经过完整且唯一的候选门禁

P1 应该完成

- [x] P1.1 为 EditorGraphSpec v3 建立正式追溯并完成真实 Editor 后验
- [x] P1.2 修复 REL-0008～0011 的发布记录与反向追溯
- [x] P1.3 将 layout CLI 改为只依赖 core 公共契约

P2 可选优化

- [x] P2.1 对 4 个 C# 预警片段建立增长门禁并按职责安全拆分

## 任务详情

### P0.1 恢复真实可用的正式安装入口并闭合 CR-0023/REL 状态

- 来源问题 ID：AUD-FLOW-004
- 依赖：P0.2 在实际发布前必须完成；若先回退 README 声明则无依赖。
- 严重程度：S1
- 目标：公开文档中的正式安装命令在匿名干净环境中可执行，并与 CR/REL/版本状态一致。
- 范围：`README.md`、`pyproject.toml`、`docs/00-governance/traceability.csv`、`docs/04-delivery/releases/REL-0012-*.md`、必要的 timeline/change-register 回写。
- 非目标：CLI Hub、覆盖历史 tag、删除历史 Release、假设 PyPI 下载可逆。
- 涉及文件/模块/符号：安装文档、CR-0023、版本 0.6.2、REL-0012。
- 现有技术栈复用：uv、PyPI Trusted Publishing、GitHub Release、SHA-256、隔离安装 smoke。
- 新增依赖：无。
- 技术路径：在 P0.2 完成前，README 和供应链文档明确使用真实可用的 GitHub Release 一键安装作为当前入口；发布获批后创建唯一候选、上传 PyPI、回读元数据和文件摘要，再原子回写 released 状态。
- 执行步骤：
  1. 锁定候选 commit/version，确认 PyPI 名称与 Trusted Publisher 配置，不创建 tag。
  2. 先运行 P0.2 全部门禁；通过后按用户发布授权创建 `v0.6.2` tag。
  3. 从 PyPI 匿名下载并核对 wheel/sdist hash，执行安装、版本、help、parse、Skill smoke。
  4. 创建 REL-0012 并回写 CR-0023、traceability、timeline、README；失败则保留“未发布”事实。
- 验收标准：以当前真实入口恢复或完成 PyPI 发布二选一闭环；本轮采用未发布回退路径，GitHub Release `v0.6.1` 安装声明一致、PyPI/CR/REL 状态无超前，完整 release strict 0。
- 验证方式：README/供应链/技术路径静态对账、GitHub Release URL 与版本核对、`curl https://pypi.org/pypi/asecli/0.6.2/json`、Project Architect release strict；仅在另行授权发布后执行 PyPI 安装与 SHA-256 后验。
- 风险：PyPI 版本不可复用，发布错误影响所有公开用户。
- 回滚/降级方案：未发布时回退 README；已发布时 yank 错误版本、发布修复版并公告，不删除/覆盖同版本。
- 变更留档：CR-0023、REL-0012、REG-0021 或新增公开安装 REG、timeline、traceability。
- 计划外问题处理规则：记录，不展开；只有阻塞 P0 时暂停并请求确认。
- 执行结果：README、供应链政策与技术路径已统一为当前真实可用的 GitHub Release `v0.6.1`；PyPI 仍明确为未发布，CR-0023 保持进行中，未创建虚假 REL-0012。

### P0.2 让公开 tag 发布强制经过完整且唯一的候选门禁

- 来源问题 ID：AUD-GOV-004
- 依赖：无；必须早于 P0.1 的实际 tag。
- 严重程度：S1
- 目标：任何 semver tag 都只有在版本一致、全量测试、完整治理、供应链和可复现构建全部通过后才能获得 PyPI OIDC 发布权限。
- 范围：`.github/workflows/ci.yml`、`.github/workflows/publish.yml`、`tools/check_ci_governance.py`、`tests/test_governance.py`、必要的 repo-local 完整治理 checker。
- 非目标：更换 CI 平台、增加长期服务、降低现有测试/供应链门禁。
- 涉及文件/模块/符号：tag trigger、build artifact、publish job needs、tag/version validator、release strict。
- 现有技术栈复用：GitHub Actions、uv、pytest、固定 action SHA、现有 artifact digest、OIDC environment。
- 新增依赖：无。
- 技术路径：把候选验证抽成 reusable job/workflow，tag 路径复用同一 artifact；显式比较 `refs/tags/vX.Y.Z` 与 pyproject version；OIDC publish 只依赖验证成功的 digest。
- 执行步骤：
  1. 为 tag/version 不一致、trace 断链、release-record 不合格和 artifact digest 变化增加失败测试。
  2. 统一 repo-local checker 与 Project Architect 所需的 docs/kickoff/trace/release/fitness 契约。
  3. 让 publish workflow 运行或依赖双 Python全量、REG、治理、供应链、双构建可复现和隔离安装。
  4. 用无发布权限的候选 run 验证正/负路径，再保留 OIDC job 的最小权限。
- 验收标准：所有负例都在 publish job 前失败；正常候选只构建一次并以 digest 交接；完整 strict 0 finding；OIDC job 不检出源码也不重建。远端 candidate run 属于下一次获授权 tag 的发布后验，不以本地证据冒充。
- 验证方式：pytest workflow fixtures、repo-local checker、artifact digest 和 job dependency 图；获发布授权后再执行 GitHub candidate run。
- 风险：错误的依赖关系可能阻断发布或让 OIDC job消费非候选 artifact。
- 回滚/降级方案：保留只验证不发布的 workflow_dispatch；新流程失败时不创建外部发行版。
- 变更留档：CR-0023、ADR-0019 增量、TASK、REG、timeline。
- 计划外问题处理规则：记录，不展开；只有阻塞 P0 时暂停并请求确认。
- 执行结果：tag/version、双 Python 全量、完整治理、REG、双构建摘要、SBOM、供应链、隔离安装和同 commit artifact→OIDC 已统一到 `publish.yml`；本地正负例通过，远端 tag/OIDC 因未授权未执行。

### P1.1 为 EditorGraphSpec v3 建立正式追溯并完成真实 Editor 后验

- 来源问题 ID：AUD-FLOW-005、AUD-FE-007
- 依赖：确认当前 WIP 的业务边界；不得与 SGCLI 实现混为同一模块。
- 严重程度：S1/S2
- 目标：v3 公共契约具备批准来源、兼容设计、永久回归和 ASE 1.9.6.2 双进程证据。
- 范围：治理文档、当前 `src/asecli/bridge/**`/`cli/create_command.py` WIP、相关 tests、隔离 Editor E2E。
- 非目标：实现 SGCLI、支持未知 ASE/模板、修改生产 Shader、把整图降级为单一黑盒。
- 涉及文件/模块/符号：EditorGraphSpec v3、`primitives_version`、primitive/recipe、precision/default/min/max、C# resource parts。
- 现有技术栈复用：EditorGraphSpec parser、MCP transaction、manifest、pytest、现有 temporary asset protocol。
- 新增依赖：无。
- 技术路径：先登记 CR/ADR/TASK/REG，再完成自动与真实 Editor 两层验收；保持 v1/v2 向后兼容和未知输入失败关闭。
- 执行步骤：
  1. 把提案中的 ASECLI 加性变更提炼为 CR，明确 v2/v3 选择和 SGCLI 边界。
  2. 回链 module-map、task charter、REG catalog、traceability、timeline。
  3. 运行定向与全量测试，修复 `git diff --check`，再只启动一次隔离 Editor 会话集中验证。
  4. 完全退出后新进程重开，对账节点/端口/范围/精度/manifest/临时资产。
- 验收标准：完整 strict 0；v1/v2 回归全绿；v3 未知版本/操作失败关闭；真实 Editor 双进程 0 error/0 staging；公共字段有版本化文档。
- 验证方式：pytest、REG checker、Project Architect strict、Editor log、manifest/hash。
- 风险：primitive 动态类型、recipe fallback 或 C# serialization 与 ASE 实际端口不一致。
- 回滚/降级方案：不合并 v3；继续以发布的 v2 为写手基线，保留 WIP 分支/补丁。
- 变更留档：新 CR/ADR/TASK/REG/REL，禁止复用旧 ID 冒充。
- 计划外问题处理规则：记录，不展开；只有阻塞 P1 时暂停并请求确认。
- 执行结果：CR-0024/ADR-0020/TASK-0054/REG-0053 已双向登记；自动定向 99 passed，隔离团结 2022.3.61t9 + ASE 1.9.6.2 双进程 `1 passed in 69.33s`，真实节点/属性/连接重载一致，0 Shader/CS error、0 staging。

### P1.2 修复 REL-0008～0011 的发布记录与反向追溯

- 来源问题 ID：AUD-REL-002
- 依赖：P0.2 确认统一 release contract。
- 严重程度：S2
- 目标：四份历史发布记录在不改事实的前提下通过完整 release strict。
- 范围：REL-0008～0011、traceability、必要的 module-map/task charter 回链。
- 非目标：重发或删除 Release/tag、修改远端资产、补写无法证明的运行结论。
- 涉及文件/模块/符号：变更集合、验证与风险、回滚验证、CR/FR/REG/commit links。
- 现有技术栈复用：Project Architect release checker、现有 run/tag/hash/安装证据。
- 新增依赖：无。
- 技术路径：按 validator 逐项补结构；对不确定事实标记未验证，不编造。
- 执行步骤：
  1. 导出 23 findings 并按 REL 分组锁定现有证据。
  2. 补 required fields/sections 与回滚验证，不改变历史 SHA/版本。
  3. 修复 CR-0006/FR-0008 等反向 trace 和任务 REG 字段。
  4. 运行 docs/kickoff/trace/release/fitness 完整 strict。
- 验收标准：23 findings 清零；Git diff 只含证据支持的治理增量；历史状态仍 released。
- 验证方式：release strict、人工核对 run/tag/hash、diff review。
- 风险：格式迁移时把未验证事实写成已验证。
- 回滚/降级方案：逐 REL 独立提交/回滚；不删除原文证据。
- 变更留档：关联 AUD-REL-002、TASK、timeline。
- 计划外问题处理规则：记录，不展开；只有阻塞 P1 时暂停并请求确认。
- 执行结果：REL-0008～0011 已补齐固定字段与反向追溯，未改变历史版本、SHA 或未验证边界；release strict 0 finding。

### P1.3 将 layout CLI 改为只依赖 core 公共契约

- 来源问题 ID：AUD-MOD-002
- 依赖：无；避免与 v3 Editor WIP 文件重叠。
- 严重程度：S2
- 目标：layout CLI 不再直接耦合 core 实现文件，fitness 0 error 且行为不变。
- 范围：`src/asecli/core/__init__.py` 或 `src/asecli/core/contracts/**`、`src/asecli/cli/layout_command.py`、相关契约测试。
- 非目标：重写布局算法、调整 CLI JSON、移动模型所有权。
- 涉及文件/模块/符号：wire router、model、commentary、meticulous layout 的最小 facade。
- 现有技术栈复用：现有 Python 包结构和 pytest。
- 新增依赖：无。
- 技术路径：只导出 CLI 真正需要的稳定符号，以 public facade 替换 4 个私有模块 import。
- 执行步骤：
  1. 列出 layout_command 使用的最小符号集与兼容承诺。
  2. 在允许的公共路径导出并加入 import contract 测试。
  3. 替换 CLI import，运行 layout/CLI/fitness。
- 验收标准：fitness 0；相关 JSON/布局结果不变；无新的跨模块私有 import。
- 验证方式：strict fitness、targeted pytest、CLI smoke。
- 风险：过度导出会扩大公共 API。
- 回滚/降级方案：回退 facade/import；不改算法文件。
- 变更留档：AUD-MOD-002、TASK、REG、module-map。
- 计划外问题处理规则：记录，不展开；只有阻塞 P1 时暂停并请求确认。
- 执行结果：`layout_command.py` 只从 `asecli.core` 公共入口导入；59 个布局/契约测试通过，fitness strict 0 error。

### P2.1 对 4 个 C# 预警片段建立增长门禁并按职责安全拆分

- 来源问题 ID：AUD-SIZE-002
- 依赖：P1.1 v3 结构稳定后再评估；不阻塞当前治理修复。
- 严重程度：S3
- 目标：预警片段不继续无界增长，后续拆分保持字节、单事务和 Editor 行为等价。
- 范围：4 个 `.cs.txt` 片段、`resource_text.py`、LOC/hash/bridge tests。
- 非目标：改变 C# 行为、引入永久豁免、为了行数做机械拆分。
- 涉及文件/模块/符号：MaterialGUI parts、Editor create parts、deterministic composition。
- 现有技术栈复用：现有分片拼装、SHA-256、REG-0044/45、条件 Editor E2E。
- 新增依赖：无。
- 技术路径：先让 CI 报 warning 趋势；只有职责边界稳定时拆分并证明拼装/事务等价。
- 执行步骤：
  1. 为 `.cs.txt` warning/limit 双阈值增加报告与增长负例。
  2. 冻结拆分前拼装 hash/事务结构基线。
  3. 按职责拆分一个资源族并执行静态/Editor 回归；失败立即回退。
- 验收标准：无片段新增超过 warning 的净增长；拆分后拼装 hash或经批准的语义基线一致；单 payload/rollback 不变。
- 验证方式：LOC、hash、static contract、bridge pytest、必要时一次 Editor E2E。
- 风险：机械拆分破坏 C# 作用域或 nonce/rollback 边界。
- 回滚/降级方案：恢复拆分前资源；保留预警监控，不创建永久例外。
- 变更留档：AUD-SIZE-002、TASK、REG，若改变结构则 module-map/ADR 增量。
- 计划外问题处理规则：记录，不展开；只有阻塞 P2 时暂停并请求确认。
- 执行结果：warning 增长门禁已加入；MaterialGUI 300/290 行冻结为不可增长基线，Editor create 拆为 176/145/139/161/114 五段，拼装语义 hash 与单 payload/rollback 契约保持，并由 REG-0053 真实 E2E 覆盖。

## 进度更新模板

```markdown
## TODO

P0 必须完成
- [*] P0.1 当前任务
- [ ] P0.2 下一个任务

当前进展：
- 已完成：
- 正在做：
- 下一步：
- 阻塞/风险：
```

## Definition of Done

- [x] 所有 S0/S1 和 P0/P1 问题均映射到 TODO，且每个 TODO 有完整详情。
- [x] 已按 `.project-architect.json` 的分类阈值执行 LOC 门禁，排除项、截断和超限项均已记录。
- [x] P0 完成并通过相关测试、构建或替代验证。
- [x] 回归覆盖受影响模块和关键链路。
- [x] OpenSpec 与 CodeGraph 的更新或不适用原因已说明。
- [x] 需求变更、技术决策和实际修改文件已按现有机制增量留档并关联。
- [x] 审计范围内每个功能模块均完成“需求→入口→主路径→数据/状态→异常恢复→可观测性→回归→发布证据”闭环对账；14 个 `FM-*` 均有稳定结论。
- [x] 审计范围内每个前端入口均有闭环结论或未验证原因；16 个 `FE-*` 均有稳定结论，create v3 具备真实 Editor 后验并明确保持未发布。
- [x] 七类专项工程审计均有状态，P0/P1 专项问题均映射 TODO。
- [x] 请求/实际审计模式及降级原因已说明；增量对比已写入报告。
- [x] UI/Product Design 不适用原因和 Editor 证据边界已说明。
- [x] 计划外发现已记录但未扩展处理。

## 本轮状态

- 审计产物：已完成。
- 整改执行：6/6 已完成；自动、治理和隔离 Editor 证据均已闭环。
- 发布边界：未创建 `v0.6.2` tag，未上传 PyPI/CLI Hub，未执行远端 OIDC；CR-0023 继续保持进行中。
- 下一门禁：任何 `v0.6.2` tag 或 PyPI 发布前，必须重新执行候选门禁与发布前增量审计。

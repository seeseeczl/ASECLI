# 项目优化任务书

## 执行原则

- 只执行本任务书事项，先 P0，再 P1，再 P2；每次只推进一个任务，不擅自扩大范围。
- 每完成一个步骤立即更新原 TODO 和当前进展，不重建或重新计数。
- 默认复用 Python、uv、pytest、Hatchling 和现有模块；新增依赖必须单独说明必要性、替代方案、成本与影响。
- 缺陷先增加会失败的 REG，再做最小修复；失败执行 Test-Fix Loop，计划外问题只记录。
- 本任务书是整改建议，不代表已授权修改业务代码、CI、用户 Unity/Tuanjie 工程或远程状态。

## 总目标

- 让 AseCLI 的 schema 写入、图修改、创建、JSON 契约与 MCP 重编译形成可失败、可恢复、可追溯的真实端到端闭环，并以可执行回归和发布证据证明。

## 范围

- `src/asecli/{core,schema,checks,cli,bridge}`、直接相关测试、README/SKILL、治理/REG/时间线、最小 CI 与 REL 证据。
- 真实验收只允许使用临时或用户明确授权的 Tuanjie 工程与可丢弃 shader。

## 非目标

- 不重写 ASE 文本引擎，不引入 UI/微服务/数据库，不升级无关依赖，不初始化 OpenSpec/CodeGraph，不修改用户生产 shader，不自动发布远程 Release。

## 问题到任务映射

| 问题 ID | 严重程度 | 优先级 | TODO ID | 处理方式 |
| --- | --- | --- | --- | --- |
| AUD-FE-001 | S1 | P1 | P1.1 | 与 schema 版本门禁合并，交付可靠 add-node |
| AUD-DATA-001 | S1 | P1 | P1.1 | 与字段构造同模块处理 |
| AUD-FE-002 | S1 | P1 | P1.2 | 单独修复 create donor 图注入 |
| AUD-FE-003 | S1 | P1 | P1.3 | 合并为图结构安全门禁一个业务结果 |
| AUD-FE-004 | S1 | P1 | P1.4 | 单独修复 CLI JSON 错误边界 |
| AUD-FE-005 | S1 | P1 | P1.5 | 单独修复 MCP 工具失败语义 |
| AUD-FLOW-001 | S1 | P1 | P1.6 | 独立真实目标平台验收 |
| AUD-GOV-001 | S1 | P1 | P1.7 | 独立治理证据校准 |
| AUD-FE-006 | S2 | P1 | P1.8 | 独立统一写入安全默认 |
| AUD-PERF-001 | S2 | P1 | P1.9 | 独立修复千节点性能门禁 |
| AUD-OPS-001 | S2 | P1 | P1.10 | 独立建立持续交付证据 |
| AUD-SEC-001 | S2 | P1 | P1.11 | 独立收紧 MCP 信任边界 |
| AUD-SUPPLY-001 | S3 | P2 | P2.1 | 发布前供应链基线 |
| AUD-ARCH-001 | S3 | P2 | P2.2 | 小范围公共 API 收口 |

## TODO

P0 必须完成

- 当前无 P0。

P1 应该完成

- [x] P1.1 修复 schema 节点构造并建立 ASE 版本兼容门禁
- [x] P1.2 修复 create donor 图块替换，保证单一 shader 壳
- [x] P1.3 建立图修改写前不变量与 validate 失败退出契约
- [x] P1.4 统一 argparse 失败路径的单行 JSON 契约
- [x] P1.5 将 MCP 工具级错误映射为可靠 BRIDGE_ERROR
- [x] P1.6 完成隔离 Tuanjie/MCP 与 Agent E2E 验收
- [x] P1.7 校准 TASK/REG/追溯/时间线的可执行证据
- [x] P1.8 统一 fix-checksum 的 dry-run/--write 安全语义
- [x] P1.9 重建真实千节点性能回归门禁
- [x] P1.10 建立最小 CI、构建 artifact 与 REL/回滚证据（本地交付完成；远程首次运行未授权、未验证）
- [x] P1.11 收紧 MCP URL、instance token 与 execute_code 信任边界

P2 可选优化

- [x] P2.1 建立供应链、许可证与 SBOM 基线
- [x] P2.2 收口 core 私有解析符号的公共模块契约

## 执行结果

- 代码与自动回归：13 项任务均已实现；Python 3.10/3.12 各 `79 passed, 1 skipped`，跳过项为需单独会话的 bridge 测试。
- 目标平台：隔离 Tuanjie `2022.3.62t2`、ASE 图重存版本 `19602`、MCP for Unity/server `10.1.2`；create→add-node→validate→recompile 成功，`saved=true`、`changed=true`、最终 11 nodes/0 errors。
- 失败路径：真实 MCP 无法确认保存时返回 `BRIDGE_ERROR`、exit 3；真实 bridge 标记测试 `1 passed, 79 deselected`。
- 交付：最小 CI、固定 Action SHA、内部许可、SPDX、供应链离线门禁、可复现构建和安装/卸载/恢复演练已在本地通过。
- 边界：未 push、未创建远程 Release、未写生产 Tuanjie 工程；因此远程 GitHub Actions/Dependabot 只标记“未验证”，不冒充通过。

## 任务详情

### P1.1 修复 schema 节点构造并建立 ASE 版本兼容门禁

- 来源问题 ID：AUD-FE-001 AUD-DATA-001
- 依赖：无
- 严重程度：S1
- 目标：`add-node` 只在兼容 ASE 版本上生成字段完整、可回读的节点行。
- 范围：schema 数据契约、节点构造、add-node 前置检查与直接回归。
- 非目标：不重建 299 个 schema，不支持未经证据证明的跨版本自动迁移。
- 涉及文件/模块/符号：`src/asecli/core/graph_ops.py::node_from_schema`、`src/asecli/schema/__init__.py`、`src/asecli/cli/commands.py::cmd_add_node`、schema/mutate 测试。
- 现有技术栈复用：Python 标准库、现有 schemas.json、pytest。
- 新增依赖：无。
- 技术路径：先用 SaturateNode 建立 12 vs 14 字段失败回归；定义 fixed prefix 6 的唯一契约；暴露 schema ASE 版本并默认拒绝不兼容输入。
- 执行步骤：按以下顺序执行。
  1. 新增同版本生成成功、19100/19109 不匹配失败、文件哈希不变三个 REG。
  2. 补齐 precision/preview 或把完整 fixed prefix 纳入 schema 构造 API，并在 CLI 统一版本检查。
  3. 参数化抽查至少 10 个 runtime 类型，运行全量 pytest 与 strict 架构门禁。
- 验收标准：同版本节点字段数、前缀、roundtrip 与真实样本一致；跨版本默认不写盘并返回稳定 JSON 错误码。
- 验证方式：`uv run pytest tests/test_schema_samples.py tests/test_mutate.py tests/test_cli_contract.py -q`；再运行全量 pytest。
- 风险：schema 中 134 个 layout_ok=false runtime 类型可能需要单独禁写，不能仅靠字段数放行。
- 回滚/降级方案：禁用 schema add-node，只保留 raw `--line` 专家路径和强制 validate。
- 变更留档：新增 BUG/REG，若错误码或兼容语义变化则创建 CR/ADR，并回写 traceability/timeline/commit。
- 计划外问题处理规则：记录，不展开；只有阻塞 P1 时暂停并请求确认。

### P1.2 修复 create donor 图块替换，保证单一 shader 壳

- 来源问题 ID：AUD-FE-002
- 依赖：P1.1 非强依赖，可并行；真实验收依赖 P1.6。
- 严重程度：S1
- 目标：`create --graph-from` 只替换 ASE graph body，不复制 donor 的 Shader/YAML 文件壳。
- 范围：AseFile 图块替换 API、cmd_create、create 回归。
- 非目标：不新增模板管理系统，不改变基础 `--from/--name` 语义。
- 涉及文件/模块/符号：`src/asecli/core/model.py`、`src/asecli/cli/commands.py::cmd_create`、create 相关测试。
- 现有技术栈复用：AseFile、atomic_write、checksum、pytest。
- 新增依赖：无。
- 技术路径：以 BEGIN/END 块为边界组合模板 prefix + donor graph body + 模板 suffix，禁止使用 donor.prefix 替换模板壳。
- 执行步骤：按以下顺序执行。
  1. 新增复现双 Shader 声明的失败测试，并断言单一 marker、donor 节点/连线、checksum。
  2. 提供块级替换函数，最小修改 cmd_create，保留 rename 与 `.bak` 行为。
  3. 用 shader donor 和 function donor 分别验证；在 P1.6 中完成 Tuanjie 打开。
- 验收标准：输出仅一个合法文件壳和一对 ASE marker；parse/validate 通过；Editor 可打开且图与 donor 一致。
- 验证方式：新增 create 测试 + `uv run pytest -q` + 隔离 Editor 验收。
- 风险：`.shader` 与 `.asset` 外壳不同，必须明确 donor 只提供 graph 而不混合文件类型壳。
- 回滚/降级方案：暂时移除/拒绝 `--graph-from`，保留模板复制与改名。
- 变更留档：登记 BUG/REG，更新 FR-0005、SKILL、README、timeline 和追溯。
- 计划外问题处理规则：记录，不展开；只有阻塞 P1 时暂停并请求确认。

### P1.3 建立图修改写前不变量与 validate 失败退出契约

- 来源问题 ID：AUD-FE-003
- 依赖：P1.1 完成后统一复测 add-node；其余无。
- 严重程度：S1
- 目标：任何默认写命令都不能成功提交已知无效图，validate 检出 error 时返回 JSON + exit 2。
- 范围：保留字段、节点 ID、目标输入唯一性、重复 ID、写前 validate 与退出码。
- 非目标：不实现 ASE 全部端口类型系统，不自动修复未知语义错误。
- 涉及文件/模块/符号：`core/graph_ops.py`、`checks/validate.py`、`cli/commands.py`、`cli/main.py`、直接测试。
- 现有技术栈复用：AseGraph、validate_file、CliError、atomic_write、pytest subprocess。
- 新增依赖：无。
- 技术路径：把图级不变量置于 core/checks，CLI 在写前调用；保留字段禁止通用 set-field，ID rename 另设原子操作或明确不支持。
- 执行步骤：按以下顺序执行。
  1. 新增 node ID 悬空、duplicate ID、同输入多连接、validate exit 的失败 REG。
  2. 实现保留字段保护、目标输入唯一检查和 error_count 到 exit 2 的映射。
  3. 验证 dry-run、写盘、`.bak`、checksum warning 与已有命令无回归。
- 验收标准：复现输入全部被写前拒绝或由原子语义安全处理；无效图 validate 返回 ok=false 或明确的校验失败 envelope 且 exit 2。
- 验证方式：图操作/CLI/validate 参数化测试、文件哈希断言、全量 pytest。
- 风险：改变 validate 现有 ok=true 数据语义属于公共契约变化，必须先确认 envelope 兼容方案。
- 回滚/降级方案：保留旧 validate 输出字段，但新增专用非零退出；无法统一时禁止 Agent 自动继续写链路。
- 变更留档：创建 CR + BUG/REG，更新 CLI 契约、traceability、timeline 与 SKILL。
- 计划外问题处理规则：记录，不展开；只有阻塞 P1 时暂停并请求确认。

### P1.4 统一 argparse 失败路径的单行 JSON 契约

- 来源问题 ID：AUD-FE-004
- 依赖：与 P1.3 的错误 envelope 决策一致。
- 严重程度：S1
- 目标：除显式 help 外，所有 CLI 失败路径 stdout 都是一个合法 JSON 对象。
- 范围：ArgumentParser error/SystemExit、缺参数、未知命令、非法类型、错误码/退出码。
- 非目标：不替换 argparse，不改变命令名称。
- 涉及文件/模块/符号：`src/asecli/cli/main.py::build_parser/app`、`tests/test_cli_contract.py`。
- 现有技术栈复用：argparse、json、subprocess、pytest。
- 新增依赖：无。
- 技术路径：自定义 parser/error 或捕获 SystemExit，将 usage 诊断送 stderr，将 `USAGE_ERROR` envelope 写 stdout。
- 执行步骤：按以下顺序执行。
  1. 新增缺 file、未知 command、非法 `--field` 三条失败测试。
  2. 统一 parser 错误边界并保持 exit 2。
  3. 对全部 11 个入口做最小参数矩阵，确保 stdout 仅一行 JSON。
- 验收标准：所有测试可 `json.loads(stdout)`，错误码固定，stderr 不含敏感值。
- 验证方式：`uv run pytest tests/test_cli_contract.py -q` 与全量 pytest。
- 风险：help/usage 的人类体验可能变化。
- 回滚/降级方案：保留原 usage 文本到 stderr，stdout 额外输出 JSON，不删除帮助能力。
- 变更留档：以 CR 更新 FR-0007/README/SKILL/traceability/timeline。
- 计划外问题处理规则：记录，不展开；只有阻塞 P1 时暂停并请求确认。

### P1.5 将 MCP 工具级错误映射为可靠 BRIDGE_ERROR

- 来源问题 ID：AUD-FE-005
- 依赖：无；真实确认依赖 P1.6。
- 严重程度：S1
- 目标：JSON-RPC 成功但 MCP tool `isError`/Unity 执行失败时，CLI 必须返回 ok=false、BRIDGE_ERROR、exit 3。
- 范围：MCP result 解析、saved 结果、changed 语义、错误脱敏。
- 非目标：不实现完整 MCP SDK，不更换传输协议。
- 涉及文件/模块/符号：`bridge/mcp_client.py::call_tool`、`bridge/recompile.py::recompile_via_mcp`、`cli/commands.py::cmd_recompile`、bridge 测试。
- 现有技术栈复用：urllib/json、McpError、pytest mock。
- 新增依赖：无。
- 技术路径：bridge 层集中验证 result；isError、空 content、无法确认 saved 均拒绝乐观成功；changed=false 仅在成功保存语义明确时成立。
- 执行步骤：按以下顺序执行。
  1. 新增 JSON-RPC error、tool isError、成功但 unchanged、成功 changed 四类测试。
  2. 实现统一 result parser 与脱敏错误消息。
  3. 在 P1.6 对真实 MCP 成功/失败各运行一次。
- 验收标准：mock isError 稳定映射为 BRIDGE_ERROR/exit 3；成功响应包含可判定 saved/changed。
- 验证方式：bridge 单测、CLI subprocess、真实 MCP 日志。
- 风险：不同 MCP for Unity 版本的 content 结构可能变化。
- 回滚/降级方案：未知响应一律失败并保留原始脱敏摘要，禁止返回 ok=true。
- 变更留档：BUG/REG + ADR-0002 兼容说明 + timeline/traceability。
- 计划外问题处理规则：记录，不展开；只有阻塞 P1 时暂停并请求确认。

### P1.6 完成隔离 Tuanjie/MCP 与 Agent E2E 验收

- 来源问题 ID：AUD-FLOW-001
- 依赖：P1.1、P1.2、P1.3、P1.4、P1.5、P1.8 完成；需要明确可丢弃工程/文件授权。
- 严重程度：S1
- 目标：用真实目标平台证明 create、recompile 与 Agent Skill 三条链路可用、可失败、可恢复。
- 范围：REG-0005/0006/0010、临时 Tuanjie 工程、MCP 会话、产物哈希与 Editor 结果。
- 非目标：不修改用户生产工程，不做跨平台矩阵，不发布远程 Release。
- 涉及文件/模块/符号：`tests/test_bridge_recompile.py`、新增 create/Agent 验收记录、`docs/03-quality`、timeline/REL。
- 现有技术栈复用：pytest bridge marker、MCP for Unity、AseCLI、现有 fixture。
- 新增依赖：无。
- 技术路径：复制 fixture 到隔离工程，锁定 Tuanjie/ASE/MCP 版本，执行前后哈希和图/名称检查，保留失败路径与回滚证据。
- 执行步骤：按以下顺序执行。
  1. 获取用户对临时工程/测试 shader 的明确授权，记录版本、路径、备份和停止条件。
  2. 运行 create→Editor 打开→recompile→validate，并验证 HLSL、名称、checksum、窗口/会话恢复。
  3. 让 Agent 仅按 SKILL.md 完成一次自然语言修改全流程，归档脱敏证据并回写 REG/REL。
- 验收标准：REG-0005/0006/0010 全部 verified；失败可返回稳定错误并恢复原文件；证据可由第三方复核。
- 验证方式：真实命令输出、Editor 截图/日志、前后 SHA-256、Git/文件 diff。
- 风险：MCP 会话占用、Editor 版本差异、测试文件被 ASE 重写。
- 回滚/降级方案：只操作副本；失败立即停止、恢复 `.bak`/副本并保留日志，文本只读能力继续可用。
- 变更留档：REG、timeline、traceability、REL 与实际环境清单；不得把 mock 证据写成真实通过。
- 计划外问题处理规则：记录，不展开；只有阻塞 P1 时暂停并请求确认。

### P1.7 校准 TASK/REG/追溯/时间线的可执行证据

- 来源问题 ID：AUD-GOV-001
- 依赖：P1.1 至 P1.6 的最终 ID/测试路径稳定后完成。
- 严重程度：S1
- 目标：所有“完成/验证”状态都有当前 commit、真实测试节点和时间线证据，所有 REG 命令可执行。
- 范围：task charter、regression catalog、traceability、timeline、架构/技术路线中的已变更语义。
- 非目标：不删除历史 ID，不把未运行的 Editor/发布门禁标为通过。
- 涉及文件/模块/符号：`docs/00-governance`、`docs/01-architecture`、`docs/03-quality`、`docs/04-delivery`、必要的 checker 测试。
- 现有技术栈复用：Project Architect strict、Git、pytest、CSV/Markdown。
- 新增依赖：无。
- 技术路径：以当前源码和可执行命令为事实源，增量修订状态/证据；必要时用 CR/ADR/supersedes 表达语义变化。
- 执行步骤：按以下顺序执行。
  1. 建立 TASK/REG/FR/commit/测试文件的对账表，标出缺失、过期和未验证。
  2. 修正测试路径与任务状态，补证据/owner/date，不覆盖历史结论。
  3. 增加 REG 命令目标存在/可执行检查并运行 strict + 全部 REG。
- 验收标准：不存在指向缺失文件的 REG；已完成任务有双向证据；bridge/Agent 未验仍明确开放。
- 验证方式：逐条执行 regression-catalog 命令、strict 检查、人工抽样 Git 历史。
- 风险：大批文档机械修改可能制造假追溯。
- 回滚/降级方案：按单个 ID 分批提交；发现证据不足即保留未验证，不猜测补齐。
- 变更留档：timeline 追加事件、traceability 增量更新、Git commit 按 AUD-GOV-001 关联。
- 计划外问题处理规则：记录，不展开；只有阻塞 P1 时暂停并请求确认。

### P1.8 统一 fix-checksum 的 dry-run/--write 安全语义

- 来源问题 ID：AUD-FE-006
- 依赖：P1.3/P1.4 的 CLI envelope 决策。
- 严重程度：S2
- 目标：`fix-checksum` 与其他修改命令一样默认预览，只有显式 `--write` 才改文件。
- 范围：parser 参数、cmd_fix_checksum、README/SKILL、契约测试。
- 非目标：不改变 checksum 算法，不删除 `.bak`。
- 涉及文件/模块/符号：`cli/main.py`、`cli/commands.py::cmd_fix_checksum`、README、SKILL、测试。
- 现有技术栈复用：verify/fix_checksum、atomic_write、pytest。
- 新增依赖：无。
- 技术路径：先走 CR 确认公共语义；默认计算并返回 preview，`--write` 调用 atomic_write。
- 执行步骤：按以下顺序执行。
  1. 新增无 `--write` 哈希不变、带 `--write` 哈希变化和 `.bak` 存在测试。
  2. 实现参数与 written 字段，更新文档示例。
  3. 运行 CLI 契约、checksum 和全量回归。
- 验收标准：默认文件不变；显式写入可恢复；stdout JSON 明确 `written` 与目标 checksum。
- 验证方式：subprocess + SHA-256 + `.bak` 断言。
- 风险：已有脚本可能依赖当前隐式写入。
- 回滚/降级方案：提供一个明确的短期兼容期或版本说明，不静默切换行为。
- 变更留档：CR、FR-0003、README/SKILL、REG、traceability/timeline。
- 计划外问题处理规则：记录，不展开；只有阻塞 P1 时暂停并请求确认。

### P1.9 重建真实千节点性能回归门禁

- 来源问题 ID：AUD-PERF-001
- 依赖：P1.3 的结构不变量稳定后执行。
- 严重程度：S2
- 目标：REG-0011 对至少 1000 节点的正确性和耗时都进行有效断言。
- 范围：tests/test_perf.py、测试策略、REG-0011 环境记录。
- 非目标：不提前优化算法，不建立分布式基准平台。
- 涉及文件/模块/符号：`tests/test_perf.py::test_big_graph_pipeline_under_one_second`、`docs/03-quality`。
- 现有技术栈复用：time.perf_counter、pytest、AseFile/layout。
- 新增依赖：无。
- 技术路径：生成 >=1000 个有效节点，精确断言数量/最后节点/roundtrip，再记录 3-5 次中位数和最大值。
- 执行步骤：按以下顺序执行。
  1. 修正生成范围与恒真断言，先让旧实现对真实规模运行。
  2. 若超预算，仅对测得瓶颈做最小优化并保持正确性回归。
  3. 在 Python 3.10/3.12 和 CI 环境记录结果与阈值依据。
- 验收标准：>=1000 节点，结构断言非恒真，声明环境 parse+layout+serialize <1s。
- 验证方式：`uv run pytest tests/test_perf.py -q` 多次 + 全量 pytest。
- 风险：CI 共享资源产生抖动。
- 回滚/降级方案：正确性为硬门禁，性能改为带环境基线的告警，但不得降低节点规模冒充通过。
- 变更留档：REG-0011、test-strategy、timeline 和性能证据。
- 计划外问题处理规则：记录，不展开；只有阻塞 P1 时暂停并请求确认。

### P1.10 建立最小 CI、构建 artifact 与 REL/回滚证据

- 来源问题 ID：AUD-OPS-001
- 依赖：P1.7 修复可执行命令，P1.9 修复性能门禁。
- 严重程度：S2
- 目标：每个主分支/PR 由干净环境持续验证 Python 兼容、测试、架构、构建和 artifact 完整性。
- 范围：最小 CI、3.10/3.12 矩阵、lock/test/strict/build、artifact/hash、首个 REL 与回滚演练。
- 非目标：不自动发布到 PyPI/Hub，不引入复杂部署平台。
- 涉及文件/模块/符号：CI 配置、pyproject/uv.lock（仅必要时）、delivery protocol、REL/roadmap。
- 现有技术栈复用：uv、pytest、Hatchling、project-architect checker、GitHub 仓库。
- 新增依赖：无；若选择额外 Action，必须固定版本并记录来源。
- 技术路径：最小 job 固定 uv/Python，运行现有命令，上传 wheel/sdist 和 SHA-256；REL 记录安装/卸载/回滚。
- 执行步骤：按以下顺序执行。
  1. 经用户授权后创建 CI，先跑 lock、双版本 pytest、strict、build。
  2. 保存 artifact 与哈希，隔离安装并执行 parse smoke。
  3. 创建首个 REL 草案，演练升级/卸载/恢复旧 wheel，记录观察窗口和停止条件。
- 验收标准：真实 CI 全绿且 artifact 可下载/校验/安装；REL 可追溯到 commit、REG、哈希和回滚结果。
- 验证方式：CI run 链接、artifact SHA-256、安装 smoke、回滚演练记录。
- 风险：远程 CI/Release 是外部状态变更，必须单独获得授权。
- 回滚/降级方案：先保留本地可复制脚本和人工 gate；CI 配置失败可独立回退，不影响源码。
- 变更留档：delivery protocol、REL、timeline、traceability 与 CI run 链接。
- 计划外问题处理规则：记录，不展开；只有阻塞 P1 时暂停并请求确认。

### P1.11 收紧 MCP URL、instance token 与 execute_code 信任边界

- 来源问题 ID：AUD-SEC-001
- 依赖：P1.5 的 result 解析契约。
- 严重程度：S2
- 目标：默认只连接可信 loopback MCP，token 不进入命令历史/日志，远程端点需显式授权。
- 范围：URL 校验、token 输入、错误脱敏、execute_code 安全说明与测试。
- 非目标：不自建认证服务，不存储用户凭证，不读取现有 secret 值。
- 涉及文件/模块/符号：`cli/main.py`、`bridge/mcp_client.py`、`bridge/recompile.py`、README/SKILL、安全测试。
- 现有技术栈复用：urllib.parse、环境变量/stdin、pytest mock。
- 新增依赖：无。
- 技术路径：默认 allowlist 127.0.0.1/localhost/[::1]；远程需显式 opt-in；token 走受保护输入并在所有输出中脱敏。
- 执行步骤：按以下顺序执行。
  1. 定义本地/远程信任模型、授权开关和 token 生命周期。
  2. 实现 URL/重定向检查、脱敏与不经 argv 的 token 输入。
  3. 增加恶意 URL、重定向、错误回显和正常本地 MCP 测试。
- 验收标准：非 loopback 默认拒绝；任何 JSON/stderr/异常不含 token；远程授权路径可审计。
- 验证方式：URL 矩阵单测、日志捕获、真实 loopback smoke。
- 风险：部分 MCP 部署可能使用局域网地址，需要明确兼容入口。
- 回滚/降级方案：完全禁用远程 URL，仅保留默认本地 MCP。
- 变更留档：安全 ADR/CR、README/SKILL、REG、timeline；不落盘任何敏感值。
- 计划外问题处理规则：记录，不展开；只有阻塞 P1 时暂停并请求确认。

### P2.1 建立供应链、许可证与 SBOM 基线

- 来源问题 ID：AUD-SUPPLY-001
- 依赖：P1.10 CI 与发布形态明确后执行。
- 严重程度：S3
- 目标：在外部发布或新增生产依赖前，明确许可证、SCA、密钥扫描与 SBOM 证据。
- 范围：许可证决策、依赖更新策略、CI 扫描、SBOM 与 REL 链接。
- 非目标：不在本任务中安装未选定工具，不上传源码到未知服务。
- 涉及文件/模块/符号：LICENSE 或内部许可说明、SECURITY/交付文档、CI/REL。
- 现有技术栈复用：uv.lock、平台原生扫描、release artifact。
- 新增依赖：待工具评估；默认无。
- 技术路径：先确定内部/公开分发边界，再选择最小 SCA/secret/SBOM 能力并固定版本。
- 执行步骤：按以下顺序执行。
  1. 记录许可证与分发决策、漏洞严重度门槛和修复 SLA。
  2. 经授权选择扫描/SBOM 工具并在 CI 对 lock/artifact 执行。
  3. 将结果和例外到期日关联 REL。
- 验收标准：许可证明确；SCA/secret/SBOM 有可复核输出；例外有 owner/到期/退出条件。
- 验证方式：CI artifact、SBOM 内容抽样、REL 链接。
- 风险：工具引入维护成本和误报。
- 回滚/降级方案：保持内部不发布和零新增依赖，先用人工依赖清单。
- 变更留档：安全/供应链策略、REL、timeline、例外记录。
- 计划外问题处理规则：记录，不展开；只有阻塞 P0 时暂停并请求确认。

### P2.2 收口 core 私有解析符号的公共模块契约

- 来源问题 ID：AUD-ARCH-001
- 依赖：P1.1/P1.2 稳定 AseFile/NodeLine API 后执行。
- 严重程度：S3
- 目标：cli 只依赖 core 的命名公开 API，不跨模块使用下划线私有 helper。
- 范围：raw Node 行解析公开方法、旧别名兼容、module map 与测试。
- 非目标：不重构整个 parser/serializer，不调整目录架构。
- 涉及文件/模块/符号：`core/model.py::_parse_node_line`、`core/__init__.py`、`cli/commands.py`、module-map。
- 现有技术栈复用：Python 模块 API、pytest、fitness checker。
- 新增依赖：无。
- 技术路径：提供 `parse_node_line` 或 `NodeLine.from_line`，CLI 改用公开入口；旧私有函数按兼容需要保留一个周期。
- 执行步骤：按以下顺序执行。
  1. 为公开 raw-line 解析行为建立契约测试。
  2. 新增公开 API、迁移 CLI 调用并决定旧别名弃用窗口。
  3. 运行 `rg` 私有跨模块检查、pytest 与 strict fitness。
- 验收标准：cli 不导入 `_parse_node_line`，模块文档与真实 API 一致，测试/fitness 全绿。
- 验证方式：`rg -n 'from .* import _' src/asecli`、全量 pytest、strict checker。
- 风险：内部调用者可能依赖旧符号。
- 回滚/降级方案：保留旧 alias 并标注 deprecated，不立即删除。
- 变更留档：ADR 或模块契约增量、module-map、timeline、commit。
- 计划外问题处理规则：记录，不展开；只有阻塞 P0 时暂停并请求确认。

## 进度更新模板

```markdown
## TODO

P1 应该完成
- [*] P1.1 当前任务
- [ ] P1.2 下一个任务

当前进展：
- 已完成：
- 正在做：
- 下一步：
- 阻塞/风险：
```

## Definition of Done

- [x] 所有 S0/S1 和 P0/P1 问题均映射到任务，且每个任务有失败优先的回归、精确命令、回滚与证据回写。
- [x] 已按 `.project-architect.json` 分类阈值执行 LOC/fitness，未制造新超限或跨模块私有依赖。
- [x] P1.1-P1.5、P1.8 的修复通过 Python 3.10/3.12 全量测试，P1.6 在真实隔离 Tuanjie/MCP 环境通过。
- [x] 需求变更、技术决策和实际修改文件均以 CR/ADR/BUG/REG/TASK 增量留档；本轮未擅自创建 commit。
- [x] 审计范围内每个功能模块完成需求→入口→主路径→状态→异常恢复→可观测性→回归→发布证据对账。
- [x] 审计范围内每个前端入口都有成功/失败/恢复结论，11 个 CLI 入口清单无遗漏。
- [x] 七类专项工程审计的 P1 缺口均关闭；远程 CI 作为未授权验证边界保留。
- [x] 请求/实际审计模式、真实运行与静态/mock 证据继续分层记录。
- [x] 增量对比在复审时区分新增、已解决、复发、改善和未变化。
- [x] OpenSpec/CodeGraph/Product Design 的实际使用或不适用原因如实记录；未经授权不初始化。
- [x] CI/远程 Release/用户工程写入等外部状态变更均未越权执行。

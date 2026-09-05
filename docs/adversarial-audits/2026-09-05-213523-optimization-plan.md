# 对抗性审计优化计划：ASECLI v0.4.1 快速验证与 MCP 分阶段超时

> 生成时间：2026-09-05 21:35:23 CST
> 项目根目录：`/Users/long/GitHub/ASECLI`
> 关联报告：`docs/adversarial-audits/2026-09-05-213523-audit-report.md`

## 1. 执行摘要

- 审计对象：v0.4.1 的快速验证、MCP 分阶段超时、CI 门禁和发布记录。
- Findings 统计：P0=0 P1=2 P2=3 P3=0。
- 发布建议：现有 v0.4.1 保留为不可变历史；修复两个 P1 后再继续扩大分发，优先发布 v0.4.2 补丁。
- 建议执行顺序：先恢复公共 API 兼容，再修回归目录完整性；随后归一化超时、收紧整体连接预算，最后修正发布事实源。
- 范围控制：复用 Python 标准库、pytest、现有治理脚本和 CI；不引入依赖，不启动 Editor，不修改 Shader/GUI 资源。

## 2. 修复与加固任务

| 任务 ID | 优先级 | 来源 Finding | 内容 | 验收标准 | 依赖 | 风险/回滚 |
| --- | --- | --- | --- | --- | --- | --- |
| AA-OPT-001 | P1 | AA-COMPAT-001 | 恢复 v0.4.0 构造参数顺序，将 `connect_timeout` 移到 `allow_remote` 后并设为仅关键字参数或提供等价兼容层。 | `McpClient(remote_url, token, 120.0, True)` 成功保留 `allow_remote=True`；关键字 `connect_timeout=20.0` 仍有效；内部四条 bridge 调用通过。 | — | 参数调整局部可回滚；不得用启发式猜测布尔值属于哪个参数。 |
| AA-OPT-002 | P1 | AA-GOV-001 | 重写目录命令提取为可对账解析：支持环境赋值、`uv run` 选项和同一验证单元中的多个 pytest 命令；聚合只合并安全 selector。 | 当前 50 个 pytest 代码片段全部被分类为“自动 collect”或“条件 bridge”，解析遗漏数为 0；REG-0044/0045/0046 的 `--frozen` 命令进入 collect；人为加入不可解析 pytest 片段时门禁失败。 | — | 保留失败时逐项诊断；若结构化 Markdown 解析风险过高，先将验证命令迁移到机器可读清单并由文档引用。 |
| AA-OPT-003 | P2 | AA-PROTO-001 | 在 MCP HTTP 传输边界把 socket 读超时统一转换为 `McpError`，保持 token 脱敏和异常链。 | 本地停滞 socket 触发 CLI JSON `BRIDGE_ERROR`，退出码为 3；连接拒绝、HTTP 错误和正常响应既有测试不变。 | AA-OPT-001 | 仅收窄异常分类；若捕获过宽导致编程错误被掩盖，回滚到只捕获 `TimeoutError/socket.timeout`。 |
| AA-OPT-004 | P2 | AA-PERF-001 | 用 monotonic deadline 约束整个 `connect()`，第二阶段使用剩余预算，并在错误中标明阶段。 | 设定 0.20 秒连接预算时，两阶段累计耗时在允许调度误差内不超过约 0.25 秒；`tools/call` 仍使用独立 120 秒预算。 | AA-OPT-001, AA-OPT-003 | 慢服务会更早失败；保留可配置项，必要时仅回滚总 deadline 而不回滚异常归一化。 |
| AA-OPT-005 | P2 | AA-REL-001 | 完成 `REL-0007` 最终证据回填，明确候选 CI 和证据提交 CI。 | 已发布记录无 `pending/待回填`；记录候选 run `33959329071` 与最终 run `33959451750` 的角色；治理检查能拒绝 released 记录中的 pending 状态。 | — | 只修文档事实源，不改 tag、Release 或资产；可由单提交回滚。 |

## 3. 测试补强任务

| 任务 ID | 优先级 | 覆盖缺口 | 内容 | 验收标准 |
| --- | --- | --- | --- | --- |
| AA-TEST-001 | P1 | 公共构造器位置参数兼容未测 | 增加 v0.4.0 四位置参数、当前全关键字参数、loopback/remote 两类用例。 | 旧调用语义与 v0.4.0 一致；参数值逐项断言，不只断言“未抛错”。 |
| AA-TEST-002 | P1 | parser 没有完整性 oracle | 参数化环境变量、`--frozen`、`--python`、marker、node id 和多命令输入；对账文档中全部 pytest 片段。 | 任一片段未解析、重复解析或产生非 selector 垃圾参数时测试失败。 |
| AA-TEST-003 | P2 | mock 未覆盖真实 urllib 超时类型 | 使用本地临时 TCP listener 接受请求后停滞，分别覆盖 `_post`、bridge 命令和 CLI 退出码。 | 无外网、亚秒完成；稳定得到脱敏 `BRIDGE_ERROR`/3，不出现 `INTERNAL`。 |
| AA-TEST-004 | P2 | 两阶段总预算未测 | 用可控 fake clock/transport 模拟第一阶段消耗大部分预算以及第二阶段超时。 | 断言传入第二阶段的是剩余时间，并覆盖预算耗尽前不再发请求的分支。 |
| AA-TEST-005 | P2 | 发布状态自洽未治理 | 在 release governance 测试中加入已发布记录禁止 `in-progress`、`pending`、`待回填` 的规则。 | 当前 `REL-0007` 通过；临时反例稳定失败并指出字段。 |

## 4. 观测与运维任务

| 任务 ID | 优先级 | 内容 | 验收标准 |
| --- | --- | --- | --- |
| AA-OBS-001 | P2 | MCP 超时 JSON 中加入 `phase`、`elapsed_ms`、`budget_ms`，不得包含 URL credential 或 instance token。 | initialize、initialized、tools/call 三阶段可区分；脱敏测试通过。 |
| AA-OBS-002 | P2 | CI 恢复一个命名明确的快速 regression-catalog step，直接输出 parsed/conditional/missed 计数。 | 工作流日志可见三类计数且 `missed=0`；该 step 目标耗时低于 2 秒，不重复执行全量 pytest。 |

## 5. 发布门禁

- [x] AA-OPT-001、AA-OPT-002 完成，两个 P1 已在工作树修复。
- [x] 旧四位置参数与新关键字参数兼容测试通过。
- [x] 回归目录 parser 对账为 `missed=0`，`--frozen` 与条件 bridge 命令均被正确分类。
- [x] 真实 socket 慢响应返回 `BRIDGE_ERROR`/3，单次 connect 总耗时受统一预算约束。
- [x] `REL-0007` 状态、候选 CI、最终 CI 与发布资产证据一致。
- [x] 完成相关定向测试、一次全量 pytest、快速治理检查和 `git diff --check`；未启动 Editor、未截图。

## 6. 未映射项（如有）

- 无。所有 P1/P2 finding 均已映射到 AA-OPT 任务；本轮无 P0/P3。

## 7. 执行结果

- 完成时间：2026-09-05 22:29:19 CST。
- AA-OPT-001～005、AA-TEST-001～005、AA-OBS-001～002 均已实现；现有 v0.4.1 tag、Release 和资产保持不变。
- 自动验证：`268 passed, 3 skipped in 20.67s`；三个 skip 为需要真实 Editor 环境的既有 bridge 边界。
- 目录门禁：`50 parsed / 6 conditional / 0 missed`，耗时 `0.56s`。
- 治理与格式：CI governance 零 finding，`uv lock --check`、`git diff --check` 通过。
- 发布状态：当前仅完成工作树修复，没有提交、推送、创建 v0.4.2 Release 或覆盖本机 v0.4.1；这些外部动作需单独授权。

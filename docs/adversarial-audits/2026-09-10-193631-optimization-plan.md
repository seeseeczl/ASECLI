# 对抗性审计优化计划：ASECLI CLI JSON 输出契约

> 生成时间：2026-09-10 19:36:31
> 项目根目录：`/Users/long/GitHub/ASECLI`
> 关联报告：`docs/adversarial-audits/2026-09-10-193631-audit-report.md`

## 1. 执行摘要

- 审计对象：当前 CLI stdout JSON envelope、错误码目录、argparse 出口和 REG-0007。
- Findings 统计：P0=0 P1=2 P2=3 P3=0。
- 发布建议：阻塞；两条 P1 会让机器契约在常见编码环境或损坏 ASE 数值下真实失效。
- 建议执行顺序：AA-OPT-001 → AA-OPT-002 → AA-OPT-003/004 → AA-OPT-005 → 定向回归与安装态 smoke。

## 2. 修复与加固任务

| 任务 ID | 优先级 | 来源 Finding | 内容 | 验收标准 | 依赖 | 风险/回滚 |
| --- | --- | --- | --- | --- | --- | --- |
| AA-OPT-001 | P1 | AA-DATA-001 | 新增统一 JSON writer：先以内存 `json.dumps(..., ensure_ascii=True, allow_nan=False)` 生成完整内容，再一次写入 stdout；将 writer 自身错误纳入最外层纯 ASCII 兜底。 | `PYTHONIOENCODING=ascii ... parse 不存在.shader` 返回 exit 2；stdout 恰为一个完整 JSON 对象；stderr 无 Python traceback；普通 UTF-8 中文仍可还原。 | — | 输出从直写流改为一次写出；若兼容性异常，可保留 envelope 构造，仅回滚底层 writer 实现。 |
| AA-OPT-002 | P1 | AA-DATA-002 | 对所有 ASE/Editor 几何浮点执行 `math.isfinite`；优先修复 Commentary position/width/height，并让 writer 禁止 NaN/Infinity。 | `nan`、`inf`、`-inf` 的坐标/尺寸均返回非零退出码和标准 JSON error；不得出现 `ok=true`/`structural_validation=passed`；全仓输出扫描不含裸 NaN/Infinity。 | AA-OPT-001 | 旧损坏资产会从“勉强读取”变为失败关闭；不应降级放行，可提供明确定位信息。 |
| AA-OPT-003 | P2 | AA-CONTRACT-001 | 明确 help/version 协议；推荐 version JSON 化，help 作为唯一文档化文本例外，或两者都 JSON 化。 | Skill、README、CLI 行为一致；自动测试覆盖顶层和子命令 help/version；Agent 探测路径不再误判协议。 | AA-OPT-001 | 人类 CLI 展示可能变化；通过保留 stderr/显式 `--human-help` 等兼容入口回滚展示，不回滚机器契约。 |
| AA-OPT-004 | P2 | AA-CONTRACT-002 | 建立单一错误码注册表并校验实现、Skill 与测试集合。 | 当前 22 个实现错误码全部被登记；AST/注册表契约测试集合相等；新增错误码必须显式更新公开契约。 | — | 文档和实现可能暴露历史遗漏；仅做加法同步，删除或重命名错误码需独立兼容决策。 |
| AA-OPT-005 | P2 | AA-TEST-001 | 将 REG-0007 改为从 parser 动态枚举命令的契约矩阵；使用拒绝非有限常量的严格解析；覆盖编码和 writer 失败。 | parser 17 个 subcommand 全部被测试收集；新增命令自动进入门禁；AA-DATA-001/002 和 help/version 都有回归用例。 | AA-OPT-001, AA-OPT-002, AA-OPT-003, AA-OPT-004 | 动态矩阵可能增加测试维护；用每命令最小 fixture 控制时长，Editor 路径继续 mock，不引入真实 Editor 到快速门禁。 |

## 3. 测试补强任务

| 任务 ID | 优先级 | 覆盖缺口 | 内容 | 验收标准 |
| --- | --- | --- | --- | --- |
| AA-TEST-001 | P1 | stdout 编码和原子性 | 增加 ASCII stdout、中文路径/消息、writer 序列化失败、stderr traceback 禁止用例。 | 每个场景 stdout 都能被严格解析为单个对象，退出码为 0/2/3 之一。 |
| AA-TEST-002 | P1 | 非有限浮点 | 对 Commentary、layout/geometry 和 bridge 数值注入 `nan`/`±inf`；解析阶段和最终 writer 双门禁。 | 所有非有限数失败关闭；任何成功 JSON 中不存在非标准数值。 |
| AA-TEST-003 | P2 | 子命令覆盖漂移 | 测试集合动态等于 `build_parser()` 子命令集合，并包含安装型、审计型和 graph-review 命令。 | 不再维护易漏项的手写 14 命令列表；新增 parser command 时未补策略会直接失败。 |
| AA-TEST-004 | P2 | help/version 与错误码 | 覆盖顶层/子命令 help、version、错误码注册表和文档同步。 | 行为与公开契约逐项一致，未知/遗漏码测试失败。 |
| AA-TEST-005 | P2 | 安装态与平台 | 修复后运行定向契约测试、完整 pytest、wheel console-script smoke，并保留 Windows CI 结果。 | 源码入口与 wheel 入口输出一致；Windows/UTF-8/ASCII 模拟均通过。 |

## 4. 观测与运维任务

| 任务 ID | 优先级 | 内容 | 验收标准 |
| --- | --- | --- | --- |
| AA-OBS-001 | P2 | 为 envelope 增加向后兼容的 `contract_version`，记录 CLI version 与 command，不包含路径内容或 token。 | Agent 可判定协议版本；新增字段为 additive；敏感值测试通过。 |
| AA-OBS-002 | P2 | 定义 writer 兜底错误的纯 ASCII 最小格式和日志策略。 | 即使 locale/编码/序列化失败，仍有确定退出码；stderr 不含 traceback 和 token；stdout 不产生半截前缀。 |

## 5. 发布门禁

- [ ] AA-OPT-001、AA-OPT-002 完成并有动态复现转绿证据。
- [ ] help/version 的机器协议已明确并与文档一致。
- [ ] 实现、错误码注册表、Skill 文档和测试集合一致。
- [ ] REG-0007 动态覆盖所有当前子命令，严格拒绝 NaN/Infinity。
- [ ] 定向测试、完整 pytest、wheel console-script smoke 通过；Windows 结果单独记录。
- [ ] 真实 Editor/MCP 未涉及本修复时不作为 JSON writer 门禁；若 data shape 被改动，则补相应桥接 mock/实机证据。

## 6. 未映射项（如有）

- 无。5 条 finding 均已映射到 AA-OPT 任务。

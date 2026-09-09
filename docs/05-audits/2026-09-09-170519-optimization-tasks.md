---
id: OPT-2026-09-09-170519
type: optimization-tasks
status: verified
version: 2
created_at: 2026-09-09T17:05:19+08:00
owner: long
related: [AUD-2026-09-09-170519]
supersedes: [OPT-2026-09-08-130015]
evidence: [docs/05-audits/2026-09-09-170519-project-audit-report.md]
---

# 项目优化任务书

## 执行原则

- 只执行本任务书事项，先 P0，再 P1，再 P2；每次只推进一个任务，不擅自扩大范围。
- 本轮无 P0；P1、P2 各一项，均为低风险收口，不涉及发布、tag、PyPI 或 Editor 运行。
- 保留用户未跟踪的 `e2e-results/wave-noise-20260908-170741/`，不使用宽泛 `git add`。
- 默认复用现有 Python/uv/pytest/Project Architect 技术栈；不新增运行时依赖。
- 测试失败执行 Test-Fix Loop；非阻塞的计划外问题只记录。

## 总目标

- 消除唯一 fitness 私有导入并同步 FM 清单，恢复模块隔离门禁全绿，维持 L3 治理基线。

## 范围

- `bridge/__init__.py` 公共导出、`cli/commands.py` 导入收口、import 契约测试、`audit-supplement.json` FM 清单。

## 非目标

- 不重构 recompile 语义、不改数据模型、不动布局/图算法、不启动 Editor、不发布、不提交/推送（除非用户另行授权）。

## 问题到任务映射

| 问题 ID | 严重程度 | 优先级 | TODO ID | 处理方式 |
| --- | --- | --- | --- | --- |
| AUD-MOD-003 | S2 | P1 | P1.1 | 收口 bridge 公共契约 |
| AUD-GOV-005 | S3 | P2 | P2.1 | 同步 supplement FM 清单 |

## TODO

P0 必须完成

- 无。

P1 应该完成

- [x] P1.1 将 `import_shader_via_mcp` 收口到 bridge 公共导出，fitness 0 error

P2 可选优化

- [x] P2.1 为 graph-review/island-layout/reuse-plan 同步 supplement FM 清单

## 任务详情

### P1.1 将 `import_shader_via_mcp` 收口到 bridge 公共导出

- 来源问题 ID：AUD-MOD-003
- 依赖：无。
- 严重程度：S2
- 目标：`commands.py` 不再直接导入 `bridge.recompile` 内部符号，fitness strict 0 error 且行为不变。
- 范围：`src/asecli/bridge/__init__.py`、`src/asecli/cli/commands.py`、相关 import 契约测试。
- 非目标：不改 recompile 语义、不改 MCP 调用、不重构 bridge 模块结构。
- 涉及文件/模块/符号：`import_shader_via_mcp`、`bridge.__all__`、`commands.py:9`。
- 现有技术栈复用：现有 Python 包结构、pytest、Project Architect fitness。
- 新增依赖：无。
- 技术路径：在 `bridge/__init__.py` 从 `.recompile` 导入并加入 `__all__`；`commands.py` 改为从 `..bridge` 导入；新增/更新 import 契约测试覆盖公开符号。
- 执行步骤：
  1. 在 `bridge/__init__.py` 增加 `from .recompile import recompile_via_mcp, import_shader_via_mcp` 并在 `__all__` 加 `import_shader_via_mcp`。
  2. 将 `commands.py:9` 改为 `from ..bridge import import_shader_via_mcp`，合并到现有 bridge import。
  3. 运行 fitness strict、recompile 相关定向 pytest、import smoke。
- 验收标准：fitness strict 0 error；`test_custom_gui.py` 中 monkeypatch 路径（`asecli.cli.commands.import_shader_via_mcp`）不受影响；recompile 回归通过。
- 验证方式：`check_project_architecture.py --check-fitness --strict`、targeted pytest、`python -c "from asecli.bridge import import_shader_via_mcp"`。
- 风险：monkeypatch 目标若从 `commands` 移到 `bridge` 会破坏 `test_custom_gui.py:377`；需确认 `commands.py` 内仍保留绑定名。
- 回滚/降级方案：回退 import 改动即可；不改运行时行为。
- 变更留档：AUD-MOD-003、TASK、REG（如需）、module-map。
- 计划外问题处理规则：记录，不展开；只有阻塞 P1 时暂停并请求确认。
- 执行结果：`bridge/__init__.py` 从 `.recompile` 导入并在 `__all__` 导出 `import_shader_via_mcp`；`commands.py:9` 改为从 `..bridge` 导入；新增 `test_import_shader_via_mcp_is_exported_from_bridge_public_surface`。fitness strict 0 error；定向 62 passed、全量 383 passed。

### P2.1 同步 supplement 的 FM 清单

- 来源问题 ID：AUD-GOV-005
- 依赖：无；可在 P1.1 后执行。
- 严重程度：S3
- 目标：下一轮审计能独立对账转换后核对能力，或显式记录归并原因。
- 范围：`docs/00-governance/audit-supplement.json`。
- 非目标：不改 FM 归属算法、不改模块边界、不启动外部技能。
- 涉及文件/模块/符号：`functional_modules` 清单、`graph_review.py`、`island_layout.py`、`reuse_plan.py`。
- 现有技术栈复用：supplement JSON、Project Architect coverage 校验。
- 新增依赖：无。
- 技术路径：为转换后核对新增稳定 FM 条目（或把 graph-review/reuse/island 归入既有 layout/cli-contract 并记录归因），在下一轮审计前完成清单校准。
- 执行步骤：
  1. 确定 graph-review/reuse/island 是独立 FM 还是 layout 的子能力。
  2. 在 supplement 中新增稳定 FM 条目（含 id/name/path/evidence_paths），或记录归并原因。
  3. 运行 coverage 校验确认清单与报告一致。
- 验收标准：下一轮审计 FM 清单覆盖转换后核对能力，或显式记录归并原因；coverage 无遗漏。
- 验证方式：supplement 静态检查、coverage 校验。
- 风险：过度拆分会稀释 FM 粒度。
- 回滚/降级方案：仅治理文档增量，无运行时影响。
- 变更留档：AUD-GOV-005、TASK。
- 计划外问题处理规则：记录，不展开；只有阻塞 P2 时暂停并请求确认。
- 执行结果：graph-review/island-layout/reuse-plan 是 CR-0028 在既有 layout/cli-contract 模块内的新文件，未新增 FM（CI governance checker 与 test_governance 将 supplement FM 数硬编码为 14）。改为把 `island_layout.py`、`reuse_plan.py` 并入 FM-F03DFA9A41（layout）、`graph_review.py`、`graph_review_command.py` 并入 FM-1DB3E4EA8B（cli-contract）的 evidence_paths，保持 14 不变。CI governance 0 finding、REG 61/61。

## 进度更新模板

```markdown
## TODO

P0 必须完成
- 无

P1 应该完成
- [*] P1.1 当前任务

当前进展：
- 已完成：
- 正在做：
- 下一步：
- 阻塞/风险：
```

## Definition of Done

- [x] 所有 S0/S1 和 P0/P1 问题均映射到 TODO，且每个 TODO 有完整详情。（本轮无 S0/S1/P0；P1 一项已映射）
- [x] 已按 `.project-architect.json` 的分类阈值执行 LOC 门禁，排除项、截断和超限项均已记录。
- [x] OpenSpec 与 CodeGraph 的更新或不适用原因已说明。
- [x] 需求变更、技术决策和实际修改文件已按现有机制增量留档并关联。
- [x] 审计范围内每个功能模块均完成闭环对账；14 个 `FM-*` 均有稳定结论。
- [x] 审计范围内每个前端入口均有闭环结论或未验证原因；17 个 `FE-*` 均有稳定结论。
- [x] 七类专项工程审计均有状态，P0/P1 专项问题均映射 TODO。
- [x] 请求/实际审计模式及降级原因已说明；增量对比已写入报告。
- [x] UI/Product Design 不适用原因和 Editor 证据边界已说明。
- [x] 计划外发现已记录但未扩展处理。

## 本轮状态

- 审计产物：已完成（报告 + 任务书同时间戳）。
- 整改执行：P1.1、P2.1 均已完成；均不涉及发布或 Editor 运行。
- 发布边界：无发布授权；本轮不改动任何发布相关配置或状态。
- 下一门禁：fitness strict 0 error、CI governance 0 finding、REG 61/61、全量 383 passed；后续合并需复核 `git status` 并排除未跟踪的 e2e-results 目录。

# 优化计划（红队循环）：CLI 接线完整性

> 生成时间：2026-11-17 20:59:18
> 项目根目录：/Users/long/GitHub/ASECLI
> 关联审计报告：`docs/adversarial-audits/2026-11-17-205918-audit-report.md`
> 来源 Skill：adversarial-audit

## 目标

消除「CLI 接受了开关但下游没收到」的静默失效，使 `--editor-backend` 在所有 Editor 类命令上真实生效。

## 任务总表

| 任务 ID | 优先级 | 标题 | 对应 Finding | 验收 | 回滚 |
| --- | --- | --- | --- | --- | --- |
| AA-OPT-030 | P1 | create / comment-group 传递后端 | AA-LOGIC-030 | CLI 用例观察到下游收到 backend | 移除实参 |
| AA-OPT-031 | P1 | gui-support 探针改走统一入口 | AA-LOGIC-031 | 无 MCP 硬编码残留 | 还原 |
| AA-OPT-032 | P2 | 加 CLI 级「开关生效」回归 | 测试缺口 | 每条 Editor 命令有用例 | 删除用例 |

---

## AA-OPT-030（P1）create / comment-group 传递后端

**实施**：
1. `cli/commentary_command.py` 的 `measure_node_bounds_via_mcp(...)` 增加 `backend=args.editor_backend, codely_port=args.codely_port`
2. `cli/create_command.py` 的 `create_shader_via_mcp(...)` 同上

**验收**：
- 新用例：以 spy 替换 `measure_node_bounds_via_mcp`，经 `app([...])` 执行 `comment-group --editor-backend codely`，断言 spy 收到 `backend="codely"`
- 对 `create` 同样一条

**回滚**：移除实参。

---

## AA-OPT-031（P1）gui-support 探针改走统一入口

**实施**：
1. `probe_native_mzgui_for_assets` 增加 `backend` / `codely_port` 参数
2. 内部改为 `run_editor_code(project_assets, GUI_SUPPORT_PROBE_SNIPPET, backend=..., ...)` + `extract_payload`
3. 保留原有 marker 解析与 `validate_runtime_probe` 校验
4. `cli/gui_support_command.py` 传递后端参数

**验收**：
- 新用例：spy 观察 `run_editor_code` 被调用且收到正确 backend
- 保证 marker 缺失时仍报错

**回滚**：还原为 McpClient 直连。

---

## AA-OPT-032（P2）CLI 级「开关生效」回归

**实施**：新增用例覆盖 `create` / `comment-group` / `gui-support` / `recompile` / `layout` 五条命令，均断言 `--editor-backend` 到达下游。

**验收**：`pytest -q` 全绿，用例数增加 ≥5。

---

## 执行顺序

```
AA-OPT-030 → AA-OPT-031 → AA-OPT-032
```

## 统一验收命令

```bash
.venv/bin/python -m pytest tests/ -q
.venv/bin/python tools/check_ci_governance.py
git diff --check
```

## 循环说明

本轮结束后将重新跑一轮红队审计，检查是否还有 P2 及以上问题；仍有则继续，直至清零。

---

## 第 2 轮新增任务

| 任务 ID | 优先级 | 标题 | 对应 Finding | 验收 |
| --- | --- | --- | --- | --- |
| AA-OPT-033 | P2 | 错误文案去 MCP 化 | AA-DOC-033 | 无 `"MCP ` 硬编码残留 |
| AA-OPT-034 | P2 | 实现 `capability_level` | AA-DOC-034 | `probe()` 返回该字段 |

### AA-OPT-033（P2）

将 `bridge/editor_create.py`（4 处）与 `bridge/graph_geometry_parser.py`（9 处）的 "MCP ..." 前缀改为中性描述。

**验收**：`grep -rn '"MCP ' src/asecli/bridge/*.py` 无结果；现有断言消息的测试同步更新。

### AA-OPT-034（P2）

`probe()` 增加 `capability_level: "unrestricted-code"`，说明该后端可执行任意代码。

**验收**：新用例断言字段存在且取值正确。

---

## 第 3 轮新增任务

| 任务 ID | 优先级 | 标题 | 对应 Finding | 验收 |
| --- | --- | --- | --- | --- |
| AA-OPT-035 | P2 | 超时后短宽限轮询 | AA-DATA-035 | 迟到成功可被采纳 |
| AA-OPT-036 | P3 | Bridge 解包语义独立 | AA-LOGIC-036 | 不再借 codely 分支 |
| AA-OPT-037 | P3 | 未知后端名报错 | AA-LOGIC-037 | 非法值抛 ValueError |

### AA-OPT-035（P2）

`_await` 超时后增加至多 `GRACE_POLLS`（2 次）的额外轮询；仍无则抛超时，并在 `data` 中带 `outbox_file` 供核查。

**验收**：新用例：探针延迟略超 timeout，客户端仍能拿到结果。

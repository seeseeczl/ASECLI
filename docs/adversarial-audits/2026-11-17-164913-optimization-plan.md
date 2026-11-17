# 优化计划：ASECLI 双桥接入加固

> 生成时间：2026-11-17 16:49:13
> 项目根目录：/Users/long/GitHub/ASECLI
> 关联审计报告：`docs/adversarial-audits/2026-11-17-164913-audit-report.md`
> 来源 Skill：adversarial-audit

## 目标

在不降低现有能力的前提下，消除双桥接入引入的**队列饿死**与**重复探测开销**，并把 `code.execute` 的权限语义如实告知使用者。

## 任务总表

| 任务 ID | 优先级 | 标题 | 对应 Finding | 验收 | 回滚 |
| --- | --- | --- | --- | --- | --- |
| AA-OPT-010 | P1 | 披露 `code.execute` 权限等级 | AA-SEC-010 | CLI 结果与文档标注权限 | 移除标注 |
| AA-OPT-011 | P1 | 邮箱队列健康检查 | AA-DATA-011 | 毒消息不再饿死后续请求 | 移除检查 |
| AA-OPT-012 | P2 | 后端选择结果缓存 | AA-LOGIC-012 | 连续调用不重复探测 | 移除缓存 |
| AA-OPT-013 | P2 | 修正响应目录文档 | AA-DATA-013 | docstring 与实现一致 | 还原文本 |
| AA-OPT-014 | P2 | 超时后区分“可能已执行” | AA-DATA-014 | 错误信息含状态提示 | 还原消息 |
| AA-OPT-015 | P3 | 保持 UUID 并记录 id | AA-LOGIC-015 | 结果含 request id | 移除字段 |

---

## AA-OPT-010（P1）披露 `code.execute` 权限等级

**问题**：该能力默认开启且可读任意文件，但调用方无从得知。

**实施**：
1. `bridge_client.py` 模块文档写明：`unity.code.execute` 以编辑器进程权限执行任意 C#，**不受桥的危险能力白名单约束**
2. `probe()` 返回 `capability_level: "unrestricted-code"`，让上层可展示
3. README「后端」章节增加一段说明，讲清三条通道的权限差异

**验收**：文档与 probe 输出均含该说明。

**回滚**：移除字段与段落。

---

## AA-OPT-011（P1）邮箱队列健康检查

**问题**：`inbox/` 中一个坏 JSON 会让后续请求长时间排队（实测 205 次轮询）。

**实施**（仅改 ASECLI 侧，不改探针）：
1. 投递前枚举 `inbox/*.json`；若存在**早于本次**的残留，记录到 `BridgeError.data` 并在超时错误中提示“队列可能被阻塞”
2. 投递前清理**本进程**遗留的 `.tmp`（仅匹配自己的命名前缀），避免自污染
3. 超时错误信息附带 `inbox_backlog` 计数

**验收**：
- 新用例：inbox 预置坏文件时，超时错误含 `inbox_backlog >= 1`
- 正常路径不受影响

**回滚**：移除预检与提示。

---

## AA-OPT-012（P2）后端选择结果缓存

**问题**：`run_editor_code` 每次调用都重新探测三后端，最坏叠加约 90s。

**实施**：
1. 模块内维护 `(backend_choice, timestamp)` 缓存，TTL 30s
2. 命中且未过期时直接复用，不再探测
3. 显式 `--editor-backend` 不入缓存（严格模式无探测）
4. 探测全失败时缓存“不可用”结论 5s，避免连续命令各自等 90s

**验收**：
- 新用例：连续两次 `select_backend("auto", ...)` 只触发一次探测（用计数桩验证）
- TTL 过期后重新探测

**回滚**：删除缓存层。

---

## AA-OPT-013（P2）修正响应目录文档

**实施**：`bridge_client.py` docstring 改为：请求写 `inbox/`，响应写 `outbox/`，`done/` 存放被处理过的请求副本。同时说明为何不能读 `done/`。

**验收**：docstring 与 `_read_response` 一致。

---

## AA-OPT-014（P2）超时后区分“可能已执行”

**实施**：`BridgeError` 超时分支的 `data` 增加 `delivery: "delivered"`，消息改为“已投递但未收到结果；操作可能已执行，请先确认目标状态再重试”。

**验收**：新用例断言超时错误含该提示。

---

## AA-OPT-015（P3）记录 request id

**实施**：`probe()` 与错误 `data` 中带 `request_id`，便于对照邮箱文件排障。

**验收**：错误 data 含 `request_id`。

---

## 执行顺序

```
AA-OPT-013（文档，零风险）→ AA-OPT-011（P1）→ AA-OPT-010（P1）
→ AA-OPT-012（P2）→ AA-OPT-014（P2）→ AA-OPT-015（P3）
```

## 统一验收命令

```bash
.venv/bin/python -m pytest tests/ -q
.venv/bin/python tools/check_ci_governance.py
git diff --check
```

## 对外（DSH-Bridge）建议项

以下不属于 ASECLI 仓库，作为跨仓需求记录：

| 建议 | 理由 |
| --- | --- |
| 探针 `Poll()` 遇坏文件跳过并记录，不阻塞队列 | 消除 AA-DATA-011 的根因 |
| 响应增加 `executionState`（`not-started` / `executed` / `unknown`） | 让调用方能机器判断 AA-DATA-014 |
| 探针检测重复 `id` | 补齐 AA-LOGIC-015 |
| 若可能，提供“注册脚本白名单”模式 | 收敛 AA-SEC-010 的风险面 |

---

## 执行结果（2026-11-17 完成）

6 项任务全部实施并通过验证。

| 任务 | 状态 | 关键证据 |
| --- | --- | --- |
| AA-OPT-010 | ✅ | 模块文档新增权限说明：`code.execute` 以编辑器进程权限运行任意 C#，不受危险能力白名单约束 |
| AA-OPT-011 | ✅ | 投递前统计队列积压、清理自身 `.tmp` 残留；超时错误带 `inbox_backlog` |
| AA-OPT-012 | ✅ | `auto` 决策缓存 30s、失败负缓存 5s；实测第二次调用 0.000s，探测仅 1 次 |
| AA-OPT-013 | ✅ | docstring 改为「响应在 `outbox/`，`done/` 存被处理的请求」 |
| AA-OPT-014 | ✅ | 超时错误带 `delivery: "delivered"` 与「可能已执行，重试前先确认目标状态」 |
| AA-OPT-015 | ✅ | 错误 `data` 含 `request_id` |

### 实施中的结构变更

- `probe()` 拆出到 `src/asecli/bridge/bridge_probe.py`，与 Codely 侧结构对齐，并让 `bridge_client.py` 回到 250 行治理上限内
- `backend.py` 新增 `clear_backend_cache()` 供测试与长驻进程使用

### 新增回归测试（5 个）

`tests/test_bridge_transport.py` 追加：超时上报 delivery+backlog、清理自身 tmp、文档与实现一致、auto 决策缓存、失败负缓存。

### 验证

```
pytest:      529 passed, 4 skipped
governance:  {"ok": true, "findings": []}
diff check:  OK
真机:        1st bridge ASE=True 6.76s → 2nd 3.49s（缓存省掉探测）
```

### 对外（DSH-Bridge）建议保持不变

探针侧四项建议仍待 Bridge 维护者评估：坏文件跳过、`executionState` 标记、重复 id 检测、注册脚本白名单模式。

# 优化计划（三轮红队审计）：双桥信任边界与资源卫生加固

> 生成时间：2026-11-17 20:05:30
> 项目根目录：/Users/long/GitHub/ASECLI
> 关联审计报告：`docs/adversarial-audits/2026-11-17-200530-audit-report.md`
> 来源 Skill：adversarial-audit

## 目标

把"探针校验请求、客户端信任响应"的单向信任补成双向；清理失败路径留下的资源；让缓存键与凭据、工程根一致。

## 任务总表

| 任务 ID | 优先级 | 标题 | 对应 Finding | 验收 | 回滚 |
| --- | --- | --- | --- | --- | --- |
| AA-OPT-020 | P1 | 响应归属校验 | AA-SEC-020 | 伪造响应被拒并继续等待 | 去掉校验 |
| AA-OPT-023 | P1 | 迟到响应与残留清理 | AA-DATA-023 | 超时后不残留 | 去掉清理 |
| AA-OPT-021 | P2 | 未来时间戳保护 | AA-DATA-021 | 时钟前移判 stale | 去掉保护 |
| AA-OPT-022 | P2 | 缓存键纳入凭据 | AA-LOGIC-022 | 不同 token 不共享缓存 | 还原键 |
| AA-OPT-024 | P2 | 错误仅取首行 | AA-SEC-024 | 消息无栈帧 | 还原消息 |
| AA-OPT-025 | P2 | 补对抗性测试 | AA-TEST-025 | 每条 P1/P2 有用例 | 删除用例 |
| AA-OPT-026 | P3 | 缓存键用工程根 | AA-LOGIC-026 | 两种路径写法共用缓存 | 还原键 |

---

## AA-OPT-020（P1）响应归属校验

**问题**：`_read_response` 只认 `ok` 字段，任何同名文件都会被当作本次响应。

**实施**：
1. `_read_response` 增加 `expect` 参数（含 `id` / `instanceId` / `bootId` / `nonce`）
2. 读到内容后逐项比对；不匹配视为无效，**不返回**，继续轮询（给迟到或被替换的文件一个被覆盖的机会）
3. 连续无效超过 N 次（如 50）则抛出 `BridgeError(phase="protocol")`，避免无限等待
4. 保留最终超时兜底

**验收**：
- 新用例：`outbox` 预置同 id 但 `nonce` 不同的响应 → 客户端不采纳，最终超时且错误说明"响应归属不符"
- 新用例：`outbox` 预置正确响应 → 正常返回

**回滚**：移除比对，恢复只看 `ok`。

---

## AA-OPT-023（P1）迟到响应与残留清理

**问题**：超时后探针仍会写 `outbox`，客户端从不清理，残留无限累积且成为伪造源。

**实施**：
1. `execute_code` 的 `finally` 中：先尝试删除 `outbox/<id>.json`（若已存在）
2. 投递前：清理**本进程**遗留的 `outbox/req_asecli_*.json` 中**已过期**条目（按文件 mtime 超过一定阈值，如 10 分钟）
3. 清理失败不抛错（尽力而为），但记录到 `BridgeError.data` 或调试日志

**验收**：
- 新用例：短 timeout 触发超时后，`outbox` 中不残留该 id
- 新用例：预置 10 分钟前的残留 → 下次投递时被清掉

**回滚**：移除清理步骤。

---

## AA-OPT-021（P2）未来时间戳保护

**实施**：`instance_is_stale` 计算 `age = current - stamp`；若 `age < -allowance`（如 60s，容忍时钟抖动）则同样判 stale，并在 `probe()` 的 reason 中说明"心跳时间在未来，疑似时钟异常"。

**验收**：
- 新用例：`lastSeenAt` 为 2099 年 → `instance_is_stale` 为 True
- 新用例：`lastSeenAt` 仅超前 5s → 仍为 False（容忍）

---

## AA-OPT-022（P2）缓存键纳入凭据

**实施**：`cache_key` 增加 `instance_token`、`allow_remote_mcp`。

**验收**：新用例：不同 `instance_token` 触发两次独立探测。

---

## AA-OPT-024（P2）错误仅取首行

**实施**：`_await` 构造错误消息时只取 `message` 的第一行；完整内容保留在 `BridgeError.data["detail"]`。

**验收**：新用例：注入含多行栈的 message → `str(exc)` 不含 `\n` 与栈帧特征。

---

## AA-OPT-025（P2）补对抗性测试

**实施**：为 AA-SEC-020 / AA-DATA-021 / AA-DATA-023 / AA-LOGIC-022 各补至少一个用例，全部构造"外部主动制造的异常状态"。

**验收**：`pytest tests/test_bridge_transport.py -q` 全绿且用例数增加 ≥4。

---

## AA-OPT-026（P3）缓存键用工程根

**实施**：`cache_key` 使用 `resolve_project_root(target)` 的结果；解析失败时不入缓存。

**验收**：新用例：`.../Assets` 与 `.../Assets/./` 共用同一缓存条目。

---

## 执行顺序

```
AA-OPT-020 → AA-OPT-023 → AA-OPT-021 → AA-OPT-022 → AA-OPT-024 → AA-OPT-026 → AA-OPT-025
```

先修两条 P1，再补边界，最后统一用 AA-OPT-025 补齐用例并全量验证。

## 统一验收命令

```bash
.venv/bin/python -m pytest tests/ -q
.venv/bin/python tools/check_ci_governance.py
git diff --check
```

## 对外（DSH-Bridge）建议补充

本轮新增两条，与既有四条并列：

| 建议 | 理由 |
| --- | --- |
| 探针侧回收 `outbox` 中超过一定时长的响应 | 与 AA-OPT-023 呼应，根治残留 |
| 响应携带 `requestHash`（请求内容摘要），供调用方校验配对 | 比 UUID 更强的归属证据 |

---

## 执行结果（2026-11-17 完成）

7 项任务全部实施并通过验证。

| 任务 | 状态 | 关键证据 |
| --- | --- | --- |
| AA-OPT-020 | ✅ | 响应校验 `id`/`instanceId`/`bootId`/`nonce`；不符即 `phase="protocol"` 拒绝，实测 0.1s 返回 |
| AA-OPT-021 | ✅ | 未来时间戳判 stale，容忍 60s 时钟抖动 |
| AA-OPT-022 | ✅ | 缓存键纳入 `instance_token`/`allow_remote_mcp`；不同 token 产生 2 条目 |
| AA-OPT-023 | ✅ | 投递前清扫超龄 `outbox` 残留，超时后删除自身响应 |
| AA-OPT-024 | ✅ | 错误消息只取首行，完整内容留在 `data["detail"]` |
| AA-OPT-025 | ✅ | 新增 7 个对抗性用例（伪造响应、未来心跳、残留、凭据缓存、路径规范化、栈剥离） |
| AA-OPT-026 | ✅ | 缓存键改用 `resolve_project_root`；等价路径共用 1 条目 |

### 实施中的设计修正

原计划对归属不符采用「连续 50 次后放弃」，实测发现该阈值依赖轮询间隔（2s 超时下约 40 次轮询，永远触发不到），改为**发现即拒绝**：同名文件的归属不会随时间变成正确，等待没有意义。修正后该用例从 10s 超时降到 0.1s 返回。

### 结构变更

- 新增 `bridge_instance.py`（实例记录与存活判定）、`bridge_mailbox.py`（归属校验与 outbox 清扫）
- 测试拆分为 `tests/test_bridge_transport.py`（协议基础）与 `tests/test_bridge_adversarial.py`（对抗场景），共享 `tests/_bridge_harness.py`

### 验证

```
pytest:      536 passed, 4 skipped
governance:  {"ok": true, "findings": []}
diff check:  OK
真机:        #1 bridge ASE=True 3.74s → #2 1.97s
```

---

## 对外建议的落地回执（Bridge 侧已实施，2026-11-17）

DSH-Bridge 探针升到 **v10**（`sourceHash=467224a300d6ba4c`），两条对外建议均已落地：

| 建议 | 落地方式 | 真机证据 |
| --- | --- | --- |
| 探针侧回收超龄 `outbox` 响应 | 每 60 秒扫一次，删除最后写入超 10 分钟的 `*.json`（含无人消费的 `*.rejected.json`）；只清 `outbox`，不动 `done/` | 20 分钟前的响应在清扫周期内被删除，新鲜响应保留 |
| 响应携带 `requestHash` | `sha256(请求文件**原始字节**)` 前 16 位十六进制。基于原始字节而非解析后字段，避免跨语言 JSON 规范化差异 | 调用方算 `19ec70520866055b`，探针返回同值 |

`instance.json` 的 `protocolFeatures` 现为上表五项，消费方据字段判断能力，不要比版本号。

**边界声明**：这两项提供的是「防误配对」与「通道卫生」，**不是身份认证**。文件邮箱协议在同机同用户模型下无法认证，
`requestHash` 也不能防伪造（能写 `inbox/` 的进程同样能读它并算出同一 hash）。

## ASECLI 侧本次响应（迟到响应抢救）

针对「超时是否已执行」这一遗留问题，本侧实现（`src/asecli/bridge/bridge_client.py`）：

- 主超时到点后**再补读一次** `outbox/`：探针可能刚写完，或已写但错过最后一次轮询（`POLL_INTERVAL=0.05`）
- 补读到的响应走同一条 `_accept` 校验链（归属四元组 → `ok`/`error` → `resultTruncated` → `result`），
  因此**迟到响应不会绕过 AA-SEC-020 的归属校验**
- 抢救成功则直接返回真实结果，不再报超时；计数器 `client.late_recovered` 供调用方观测
- 补读仍为空时，超时错误新增 `data["execution_state"]="unknown"` 与 `data["evidence"]="no-response"`，
  与探针侧 `executionState` 语义对齐（此时确实无法判断执行到哪一步）

新增用例（`tests/test_bridge_transport.py`）：迟到响应被采纳、无响应标 `unknown`、迟到但归属不符仍被拒。

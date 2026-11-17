# 优化计划（第 5 轮）：超时侧信道证据与真机冒烟

> 生成时间：2026-11-17 21:56:09
> 项目根目录：/Users/long/GitHub/ASECLI
> 关联审计报告：`docs/adversarial-audits/2026-11-17-215609-audit-report.md`
> 来源 Skill：adversarial-audit

## 目标

在不依赖外部探针改造的前提下，让 ASECLI 在超时后能**用侧信道证据**判断请求是否已被处理；并把真机验证固化为可重复执行的用例。

## 任务总表

| 任务 ID | 优先级 | 标题 | 对应 Finding | 验收 | 回滚 |
| --- | --- | --- | --- | --- | --- |
| AA-OPT-040 | P2 | 超时后检查 `done/` 侧信道 | AA-DATA-040 | 错误 data 含 `processed` 标记 | 移除检查 |
| AA-OPT-041 | P3 | 真机冒烟用例（`@pytest.mark.bridge`） | 测试缺口 | 编辑器在线时可用，离线跳过 | 删除用例 |

---

## AA-OPT-040（P2）超时后检查 `done/` 侧信道

**问题**：探针不给 `executionState`，超时后客户端无法判断请求是否已被处理。

**实施**：
1. `bridge_client.execute_code` 在抛出超时错误前，检查 `done/<id>.json` 是否存在
2. 探针处理完请求会把**原始请求**移入 `done/`，因此该文件存在 = 请求**已被取走处理**（无论结果如何）
3. 将该判定写入 `BridgeError.data["processed"]`（`True` / `False` / `None` 表示无法判定）
4. 错误消息据此分流：
   - `processed=True` → "请求已被编辑器取走处理，操作可能已生效，请先确认目标状态"
   - `processed=False` → "请求未被取走，可安全重试"

**验收**：
- 新用例：探针处理但超时 → `data["processed"] is True`，消息含"可能已生效"
- 新用例：探针未处理 → `data["processed"] is False`，消息含"可安全重试"

---

## AA-OPT-041（P3）真机冒烟用例

**实施**：新增 `tests/test_bridge_live.py`，全部用例标记 `@pytest.mark.bridge`：
1. `probe()` 返回 `ok=True` 且 `capability_level` 正确
2. `run_editor_code` 执行 `return 1+1;` 得 `2`
3. ASE 类型可达（`AmplifyShaderEditorWindow` 存在时）
4. 环境无 `DSHBridge/instance.json` 时整体 `pytest.skip`

**验收**：`pytest -q` 默认全绿（跳过真机用例）；`pytest -m bridge` 在编辑器在线时通过。

---

## 对外（DSH-Bridge）建议（累计）

| 建议 | 来源 | 状态 |
| --- | --- | --- |
| 探针 `Poll()` 跳过坏文件 | 第 2 轮 | ✅ v11 已修复 |
| 响应增加 `executionState` | 第 2 轮 | ❌ 仍未实现（v11 未采纳） |
| 探针检测重复 `id` | 第 2 轮 | 未验证 |
| 回收超龄 `outbox` 响应 | 第 3 轮 | 未验证 |
| 清理未处理请求的滞留（如穿越探针） | 第 5 轮 | 新增建议 |
| 响应携带 `requestHash` | 第 3 轮 | 新增建议 |

## 执行顺序

```
AA-OPT-040 → AA-OPT-041
```

---

## 执行结果（2026-11-17 完成）

| 任务 | 状态 | 关键证据 |
| --- | --- | --- |
| AA-OPT-040 | ✅ | 超时前检查 `done/<id>.json`；`execution_state` 由 `unknown` 细分为 `processed` / `not-processed` |
| AA-OPT-041 | ✅ | 新增 `tests/test_bridge_live.py`，4 个 `@pytest.mark.bridge` 用例；真机全部通过，离线自动跳过 |

### 语义改进

原实现超时后一律报 `execution_state: "unknown"`。现在利用探针「处理即把请求移入 `done/`」的行为作为侧信道：

- 有 `done/` 标记 → `processed`，提示「操作可能已生效，重试前先确认目标状态」
- 无标记 → `not-processed`，提示「可安全重试」

这把原本只能靠人判断的问题变成了机器可判定。

### 真机验证（编辑器 pid 67166，探针 v11）

```
bridge  -> win=True;field=m_mzguiAttribs | 3.73s
codely  -> win=True;field=m_mzguiAttribs | 10.27s
auto    -> bridge, win=True             | 6.61s
pytest -m bridge: 4 passed
```

### 验证

```
pytest:      553 passed, 4 skipped
governance:  {"ok": true, "findings": []}
diff check:  OK
```

---

## 第 6 轮新增任务

| 任务 ID | 优先级 | 标题 | 对应 Finding | 验收 |
| --- | --- | --- | --- | --- |
| AA-OPT-042 | P2 | 实现 `ASECLI_TEST_PROJECT` | AA-DOC-042 | 设置环境变量后用例指向新工程 |

### AA-OPT-042（P2）

`PROJECT = Path(os.environ.get("ASECLI_TEST_PROJECT", "/Users/long/Tuanjie3D/P376"))`。

**验收**：新用例以临时目录为 `ASECLI_TEST_PROJECT` 运行时，`_instance()` 因找不到 instance.json 而 skip（证明变量生效）。

---

## 第 7 轮新增任务

| 任务 ID | 优先级 | 标题 | 对应 Finding | 验收 |
| --- | --- | --- | --- | --- |
| AA-OPT-043 | P2 | 50000 上限按后端区分 | AA-LOGIC-043 | 非 MCP 后端不套用该限制；措辞准确 |

### AA-OPT-043（P2）

`build_executor_code` 增加 `limit` 参数（默认沿用 50000）；`create_shader_via_mcp` 仅在 `backend` 解析为 `mcp` 时套用，其余后端使用更宽松上限（如 4 MiB，与 Codely 帧上限一致）。

**验收**：
- 新用例：`limit=None` 时超长 payload 不被拒
- 新用例：默认（mcp）路径仍拒绝超限

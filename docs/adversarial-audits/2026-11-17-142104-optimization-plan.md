# 优化计划：ASECLI Codely 后端接入加固

> 生成时间：2026-11-17 14:21:04
> 项目根目录：/Users/long/GitHub/ASECLI
> 关联审计报告：`docs/adversarial-audits/2026-11-17-142104-audit-report.md`
> 来源 Skill：adversarial-audit

## 目标

消除 Codely 后端接入引入的跨工程误投递（P0）与资源泄漏/诊断缺失（P1），使 `auto` 模式在多工程、多编辑器环境下可安全启用。

## 任务总表

| 任务 ID | 优先级 | 标题 | 对应 Finding | 验收 | 回滚 |
| --- | --- | --- | --- | --- | --- |
| AA-OPT-001 | P0 | 端口发现必须归属目标工程 | AA-DATA-001, AA-DATA-002 | 空工程目录不再读到其它工程端口 | 恢复 home 回退（不推荐） |
| AA-OPT-002 | P1 | Codely/Backend 错误映射为 BRIDGE_ERROR | AA-UX-005 | CLI 输出 `code=BRIDGE_ERROR` | 移除映射 |
| AA-OPT-003 | P1 | 失败路径关闭 socket 且遵循 timeout | AA-SEC-004, AA-LOGIC-006 | fd 不增长；探测耗时 ≤ timeout | 还原异常处理 |
| AA-OPT-004 | P2 | `auto` 遇 `unity_instance` 跳过 Codely | AA-LOGIC-007 | `auto --unity-instance` 走 MCP | 移除条件 |
| AA-OPT-005 | P2 | 解包失败必须报错而非返回信封 | AA-DATA-008 | 空 result 抛 `EditorExecutionError` | 还原 return text |
| AA-OPT-006 | P3 | 探测可选验证 ASE 能力 | AA-LOGIC-009 | 探测可区分 ASE 缺失 | 关闭开关 |

---

## AA-OPT-001（P0）端口发现必须归属目标工程

**问题**：`registry_candidates` 回退到 `$HOME/.unity-tcp/unity-tcp-port.json`，该文件属于最近一次运行的任一工程，读取后不校验归属。

**实施**：
1. 删除 `LEGACY_HOME_REGISTRY` 回退，只保留工程内路径
2. `read_port_registry` 增加归属校验：
   - 若存在 `project_path`，要求其父目录（或自身）与目标工程的 `Assets` 路径一致；不一致则跳过该候选并继续
   - 若 `reloading` 为 true，返回但附带标记，由调用方决定是否等待/重试
3. 校验失败时错误信息明确写出「注册文件属于 X，目标是 Y」

**验收**：
- 新用例：空工程 + 存在 home 级注册文件 → `discover_port` 抛 `DiscoveryError`，绝不返回 home 里的端口
- 新用例：`project_path` 指向他处 → 视为未发现
- 真机：`/tmp/probe_proj`（无注册）执行 `--editor-backend codely` 必须报"未发现注册"，而不是连到 53996

**回滚**：恢复 home 回退并去掉归属校验（会重新引入 P0，不建议）

---

## AA-OPT-002（P1）Codely/Backend 错误映射为 BRIDGE_ERROR

**问题**：CLI 各命令仅 `except McpError`，新异常落入兜底 `INTERNAL`。

**实施**：
1. 在 `cli` 层引入统一映射：`(McpError, CodelyError, BackendError)` → `CliError("BRIDGE_ERROR", ...)`
2. 全量替换 6 个调用点的 `except McpError` 分支
3. 保留 `exc.data` 透传（含 `phase`、`handshake`）

**验收**：
- 现复现命令的输出 code 从 `INTERNAL` 变为 `BRIDGE_ERROR`
- 新增用例：模拟 Codely 脚本失败 → CLI envelope `code == "BRIDGE_ERROR"`

**回滚**：删除映射元组中的新类型

---

## AA-OPT-003（P1）失败路径关闭 socket 且遵循 timeout

**问题**：握手超时/读帧超时后 socket 不关闭；`_recv_until` 忽略调用方 timeout。

**实施**：
1. `connect()`：握手异常时 `finally` 确保 `close()`
2. `_roundtrip()`：`timeout`/`io` 异常分支先 `close()` 再抛出
3. `_recv_until` 使用 `min(WELCOME_TIMEOUT, self.timeout)`

**验收**：
- 新用例：握手超时后断言 `client._sock is None`
- 新用例：`probe(timeout=1)` 在握手迟滞下耗时 ≤ 2s
- 长跑 100 次失败探测后 fd 数不增长

**回滚**：还原异常处理与常量

---

## AA-OPT-004（P2）`auto` 遇 `unity_instance` 跳过 Codely

**问题**：多编辑器场景下 `auto` 选中 Codely 后必然失败且不回退。

**实施**：`run_editor_code` 在 `backend=="auto"` 且 `unity_instance is not None` 时直接解析为 `mcp`。

**验收**：新用例 `run_editor_code(..., backend="auto", unity_instance="A@1")` 解析为 mcp。

**回滚**：移除该条件

---

## AA-OPT-005（P2）解包失败必须报错

**问题**：`extract_payload` 对空/非字符串 `result` 返回整信封。

**实施**：`data` 为 dict 但无可识别字符串 payload 时抛 `EditorExecutionError`，消息含 `data` 的键名便于定位。

**验收**：新用例空 `result`、非字符串 `result` 均抛异常。

**回滚**：恢复 `return text`

---

## AA-OPT-006（P3）探测可选验证 ASE 能力

**实施**：`probe(..., check_ase=False)`；为 True 时脚本附带 `AmplifyShaderEditorWindow` 类型检测，结果写入 `details["ase_available"]`。

**验收**：ASE 未加载时 `ase_available is False`，且不阻塞探测通过。

**回滚**：默认参数关闭即可

---

## 执行顺序

```
AA-OPT-001 (P0) → AA-OPT-003 (P1) → AA-OPT-002 (P1) → AA-OPT-005 (P2) → AA-OPT-004 (P2) → AA-OPT-006 (P3)
```

前三项完成即可重新评估发布；后三项可并行。

## 统一验收命令

```bash
.venv/bin/python -m pytest tests/ -q
.venv/bin/python tools/check_ci_governance.py
git diff --check
```

## 观测补强（无对应 finding，与 P0/P1 一并落地）

- 连接成功后记录 `port` 与注册文件的 `project_path`，输出到 CLI 结果字段，便于排查跨工程问题
- 探测失败时把实际 `handshake` 原串透出到 CLI 错误信息

---

## 执行结果（2026-11-17 完成）

全部 6 项任务已实施并通过验证。

| 任务 | 状态 | 关键证据 |
| --- | --- | --- |
| AA-OPT-001 | ✅ 完成 | 删除 home 级回退；`_registry_belongs` 校验 `project_path`；空工程不再读到 P376 端口 |
| AA-OPT-002 | ✅ 完成 | 新增 `EDITOR_ERRORS` 元组；CLI 输出 `code=BRIDGE_ERROR` |
| AA-OPT-003 | ✅ 完成 | 握手超时返回 `CodelyError(phase=handshake)` 且 `_sock is None`；`probe(timeout=1)` 实测 1.0s |
| AA-OPT-004 | ✅ 完成 | `auto` + `unity_instance` 路由到 mcp |
| AA-OPT-005 | ✅ 完成 | 空/非字符串 `result` 抛 `EditorExecutionError` |
| AA-OPT-006 | ✅ 完成 | `probe(check_ase=True)` 返回 `ase_available` |

### 实施中的结构变更

- `probe` 拆出到新模块 `src/asecli/bridge/codely_probe.py`（避免 `codely_client.py` 触达 250 行治理上限）
- `DiscoveryError` 增加 `data` 属性，使 CLI 的 `exc.data` 访问对所有后端错误统一成立

### 新增回归测试（8 个）

`tests/test_codely_bridge.py` 追加：home 级注册拒绝、他工程注册拒绝、匹配注册接受、`reloading` 报可重试错、握手超时关 socket、probe 遵循超时、`auto`+`unity_instance` 走 mcp、缺失 payload 报错。

### 验证

```
pytest:      512 passed, 4 skipped
governance:  {"ok": true, "findings": []}
diff check:  OK
端到端:      backend=codely, win=True;field=m_mzguiAttribs
```

### 发布建议更新

**条件通过** → 原阻塞项 AA-DATA-001 / AA-SEC-004 / AA-UX-005 均已修复并有用例覆盖。
剩余 P2/P3 已一并处理，无遗留阻塞。

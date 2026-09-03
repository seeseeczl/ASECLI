---
id: REL-0001
type: release-record
status: verified
version: 0.1.0-rc.local.1
created_at: 2026-09-01T13:02:00+08:00
owner: long
related: [FR-0004, FR-0005, FR-0006, CR-0001, CR-0002, CR-0003, CR-0004, CR-0005, CR-0006, BUG-0002, BUG-0005, AUD-OPS-001, AUD-SUPPLY-001]
supersedes: []
evidence: [dist/SHA256SUMS, dist/asecli-0.1.0.spdx.json, dist/supply-chain-check.json, docs/05-audits/2026-09-01-132548-project-audit-report.md]
---

# REL-0001 — 本地发布候选与回滚演练

## 变更集合

- FR/CR/BUG/ADR：FR-0004、FR-0005、FR-0006；CR-0001～CR-0006；BUG-0002、BUG-0005；ADR-0002、ADR-0006～ADR-0009。
- 版本/提交/PR：`0.1.0-rc.local.1`；基线 `main@8883425`；本地候选，无 PR、Tag 或远端 Release。
- 兼容性说明：只增加 CLI、桥接和治理能力；无数据库、API 破坏性迁移或用户 Shader 批量改写。
- 来源：2026-09-01 标准审计的 P1.1～P1.11、P2.1～P2.2 整改。
- 基线：`main@8883425` 上的当前未提交整改工作树；最终 commit 待本轮全部门禁后回填。
- 分发：内部本地候选，不是 GitHub Release/PyPI/Hub 发布；没有远程 CI run 或可下载链接。
- 数据/配置：无数据库、迁移或持久配置；MCP token 仅来自进程环境，不进入 artifact。

## 验证与风险

- 测试/构建/审计证据：下表的双 Python、可复现构建、strict、REG catalog、供应链和隔离团结/MCP 证据。
- 已知风险与监控：远程 CI、Release、Windows/Linux 和在线漏洞库当时未验证；观察本地 hash、隔离安装、Editor 非目标写入和凭证泄漏信号。
- Go / No-Go 决定与负责人：负责人 long；本地候选 Go，任何 hash、REG、strict、隔离安装或 Editor 写入门禁失败即 No-Go。

环境：macOS arm64、uv 0.11.14、CPython 3.10.20/3.12.11、`SOURCE_DATE_EPOCH=1788220800`。

| 门禁 | 结果 |
| --- | --- |
| Python 3.10 `uv run --isolated --frozen --python 3.10 pytest -q` | 79 passed / 1 bridge skipped |
| Python 3.12 `uv run --isolated --frozen --python 3.12 pytest -q` | 79 passed / 1 bridge skipped |
| 两次 `uv build` + `cmp` | wheel 与 sdist 均逐字节一致 |
| Project Architect strict | PASS，零 warning/零 error |
| REG catalog collect | 18 条 pytest 命令可收集 |
| 供应链离线检查 | 0 finding；运行时依赖 0；lock hash/Action SHA/secret/license 通过 |

本地 artifact：

| 文件 | SHA-256 |
| --- | --- |
| `dist/asecli-0.1.0-py3-none-any.whl` | `cc1d8e4c2109ae4706a9b910edc9857dcfabd5e42e68927585e7abcdc0b653ae` |
| `dist/asecli-0.1.0.tar.gz` | `b9c5ead6c69c2b6060c8a136bef949251a65662fed49479ccbfa761b22baa32a` |
| `dist/SHA256SUMS` | `38f8f1e20c643b9c5b24dff74f620afa08a282f76c95e03541c65e34f7783190` |
| `dist/asecli-0.1.0.spdx.json` | `5866862e8da71504d5aae879576e4b279aaac0a8d0c91123553f308fc710e2de` |
| `dist/supply-chain-check.json` | `2c44e2b494c82463847530f309175e3144f813f92f44bf42d57f57813e220e3f` |

## 隔离 Tuanjie/MCP 端到端证据

- 环境：Tuanjie 2022.3.62t2、MCP for Unity/server 10.1.2、独立 loopback 端口 6517。
- 成功路径：`recompile` exit 0，`saved=true`、`changed=true`；测试 shader SHA-256 从 `6579c5e6…` 变为 `e760180d…`。
- 结果回读：最终 ASE version 19602、11 nodes、0 wires；`validate` 为 0 errors；真实 bridge `1 passed, 79 deselected`。
- 失败路径：MCP 执行异常即使以普通文本返回，CLI 仍因缺少 `saved=True` 确认返回 `BRIDGE_ERROR`、exit 3，不报告假成功。
- 隔离与脱敏：未写用户生产工程；Editor、代理和 MCP 服务已关闭；测试 token 与原始日志已删除，仅保留脱敏日志和 JSON 证据。

## 安装、卸载与回滚演练

在新的临时 Python 3.12 venv 中：

1. 从 wheel 安装，`asecli parse tests/fixtures/step-antialiasing.function.txt` 返回 `ok=true`、7 nodes/7 wires。
2. `uv pip uninstall asecli` 后，`import asecli` 按预期失败，证明卸载完整。
3. 重新安装同一已校验 wheel，`asecli validate tests/fixtures/HLIT.shader` 返回 `ok=true`、0 errors。

当前没有更早的正式 wheel，因此本次验证的是“移除候选并恢复到已校验 0.1.0 wheel”的恢复机制，不宣称跨版本数据回滚。目标恢复时间实测低于 2 秒；artifact 无数据兼容风险。

## 回滚

- 触发条件：hash 不一致、隔离安装失败、REG/strict 失败、真实 Editor 写入非目标文件或敏感值进入输出。
- 步骤：停止分发并卸载候选；按 SHA256SUMS 验证后重装最后已验证 wheel；测试文件仅从副本或 `.bak` 恢复。
- 验证：重新执行 `asecli parse`、`asecli validate`、包版本检查和 hash 校验；目标恢复时间实测低于 2 秒。
- 观察窗口：本地候选已完成隔离 Tuanjie 验收并进入 verified；push 后仍需至少观察一轮真实双 Python CI 才能进入远程 released。
- 停止条件：hash 不一致、隔离安装失败、REG/strict 失败、真实 Editor 写入非目标文件、token 出现在输出。
- 回滚：停止分发，卸载候选，按 SHA256SUMS 验证并重装最后已验证 wheel；恢复测试文件只使用副本或 `.bak`。
- 未验证：真实远程 CI、GitHub artifact 下载、远程 Release、Windows/Linux、在线漏洞数据库；这些边界不得由本地证据替代。

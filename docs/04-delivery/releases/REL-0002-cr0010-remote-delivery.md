---
id: REL-0002
type: release-record
status: released
version: 0.1.0
created_at: 2026-09-02T13:30:00+08:00
owner: long
related: [FR-0009, CR-0006, CR-0010, TASK-0030, REG-0030]
supersedes: []
evidence: [GitHub Actions run 33594698477, GitHub Release v0.1.0, release asset SHA256SUMS]
---

# REL-0002 — ASECLI v0.1.0 私有正式发布

## 变更集合

- FR/CR/BUG/ADR：FR-0009、CR-0006、CR-0010、ADR-0014；交付任务 TASK-0030、回归 REG-0030。
- 版本/提交/PR：`v0.1.0`；提交 `fbd994125398bae5562028c869453ea367e9c3ea`；直接推送私有仓库，无 PR。
- 兼容性说明：新写入迁移为 ASECLI 自有三标记和唯一内置 GUI；旧 MZGUI 标记只读兼容，不批量迁移用户 Shader。
- 发布提交：`fbd994125398bae5562028c869453ea367e9c3ea`（`main`）。
- 正式标签：`v0.1.0`，固定指向上述发布提交。
- 发布对象：[ASECLI v0.1.0（内部正式版）](https://github.com/seeseeczl/ASECLI/releases/tag/v0.1.0)，状态为非 Draft、非 Prerelease。
- 分发形式：私有 GitHub Release 中的 Python wheel；不上传 PyPI、CLI Hub 或其他公开包仓。
- GUI 验收：团结 `2022.3.61t9` 的当前实例完成新旧标记、HelpBox、默认值和折叠交互；用户提供的实机截图确认 Tooltip 显示变量名 `_BaseColor` 与默认值 `RGBA(1.000, 1.000, 1.000, 1.000)`。

## 验证与风险

- 测试/构建/审计证据：GitHub Actions run 33594698477、Release 资产摘要、SHA256SUMS、SBOM、供应链/漏洞扫描和隔离安装。
- 已知风险与监控：专有项目不在 PyPI 漏洞库；公开分发、签名和未知 ASE 版本不在本次范围，持续监控 CI、资产摘要和安装 smoke。
- Go / No-Go 决定与负责人：负责人 long；六项资产上传并复下载校验、三个 CI job 和隔离安装均通过后 Go，否则 No-Go 并停止发布。
- [GitHub Actions run 33594698477](https://github.com/seeseeczl/ASECLI/actions/runs/33594698477)：发布提交的 Python 3.10、Python 3.12、package 三个 job 全绿。
- 发布前对最终 wheel 的隔离环境执行在线 `pip-audit`：运行时依赖为 0，未发现依赖漏洞；专有 `asecli` 本身不在 PyPI 漏洞数据库中，因此按工具语义跳过，不把跳过项误报为已扫描。
- Release 上传完成后重新下载全部六个资产；`SHA256SUMS` 中登记的五个载荷资产执行 `shasum -a 256 -c SHA256SUMS` 全部通过，清单文件自身再与 GitHub 返回的资产摘要核对。

## Release 资产

| 文件 | SHA-256 |
| --- | --- |
| `asecli-0.1.0-py3-none-any.whl` | `8d19a0abe2f9083acaac6a3c1801cc5da38ba2c6a0aa64136d352667ec202318` |
| `asecli-0.1.0.tar.gz` | `c00034e2a790d90116738d1134c172df40fe07d9bf288d48b269b67eac68b205` |
| `asecli-0.1.0.spdx.json` | `2bd95c540887ce4c08fa79315991912428db4819bfd80ef833e0b43e8476264a` |
| `supply-chain-check.json` | `2c44e2b494c82463847530f309175e3144f813f92f44bf42d57f57813e220e3f` |
| `vulnerability-scan.json` | `abace7ea9dedf4804b2fa2f6251805fa197f91db0192fb05cdbc02165ed27067` |
| `SHA256SUMS` | GitHub 资产摘要 `6e20b398a1ecf91ceedc7cb01cdc59142c4aa2dd0380a23bbad46ea4ce72e0fb` |

从正式 Release 下载 wheel 后，在全新 CPython 3.12 隔离环境安装，`asecli --help` 成功列出全部 15 个公开子命令。

## 试用者安装

安装者需先获得私有仓库权限，并完成 GitHub CLI 登录：

```bash
gh auth login
mkdir asecli-v0.1.0
cd asecli-v0.1.0
gh release download v0.1.0 --repo seeseeczl/ASECLI
shasum -a 256 -c SHA256SUMS
uv tool install ./asecli-0.1.0-py3-none-any.whl
asecli --help
```

## 回滚

- 触发条件：Release 资产 hash、安装 smoke、GUI 兼容或供应链门禁任一失败。
- 步骤：停止分发并卸载当前 wheel；按已校验摘要重装上一版 `main@2b4d76c` artifact；不修改用户 Shader 或团结工程。
- 验证：确认包版本、`asecli parse` 的 7 nodes/7 wires 结果和 wheel SHA-256；上一版→当前→上一版三段演练均通过。
正式发布前，在临时 CPython 3.12 环境中先校验上一版 `main@2b4d76c` artifact 的 wheel SHA-256（`6b92cfb4287c5d46a288966ca11fb92d52bf706201a1615a8cc413f158cb6446`），随后执行：

1. 安装上一版 wheel，`asecli parse tests/fixtures/step-antialiasing.function.txt` 成功（7 nodes / 7 wires）。
2. 强制重装本次 wheel，重复 parse 成功。
3. 强制重装上一版 wheel，重复 parse 成功。

该演练只在临时环境发生，不写入用户团结工程，也不改动任何用户 Shader。

## 边界

- 本记录证明 `v0.1.0` 已作为可安装的正式 CLI，通过私有 GitHub Release 完成交付，并具备 CI、哈希、SBOM、供应链、漏洞扫描和安装/回滚证据。
- 本次发布仍使用 `LicenseRef-ASECLI-Proprietary`。只有获得私有仓库权限的授权试用者可以下载；不得公开转发源码或 Release 资产。
- 未创建 PyPI、CLI Hub 或其他公开包仓条目；开源、公开分发、代码签名和后续版本发布仍需单独授权与门禁。

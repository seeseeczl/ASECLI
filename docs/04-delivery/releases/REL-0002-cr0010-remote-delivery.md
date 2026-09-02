---
id: REL-0002
type: delivery-evidence
status: verified
version: 0.1.0
created_at: 2026-09-02T13:30:00+08:00
owner: long
related: [CR-0010, TASK-0030, REG-0030]
supersedes: []
evidence: [GitHub Actions run 33594344611, GitHub artifact asecli-0.1.0-python-X64]
---

# REL-0002 — CR-0010 远端交付证据

## 范围

- 基线提交：`e513fc5a425a21401c55ee7ea8c744c974739774`（`main`）。
- 交付对象：GitHub Actions 生成的内部 CI artifact；不是 GitHub Release、PyPI、CLI Hub 或公开分发。
- GUI 验收：团结 `2022.3.61t9` 的当前实例完成新旧标记、HelpBox、默认值和折叠交互；用户提供的实机截图确认 Tooltip 显示变量名 `_BaseColor` 与默认值 `RGBA(1.000, 1.000, 1.000, 1.000)`。

## 远端 CI 与 artifact

- [GitHub Actions run 33594344611](https://github.com/seeseeczl/ASECLI/actions/runs/33594344611)：Python 3.10、Python 3.12、package 三个 job 全绿。
- 下载 artifact `asecli-0.1.0-python-X64` 后，以 artifact 内 `SHA256SUMS` 重新校验：

| 文件 | SHA-256 |
| --- | --- |
| `asecli-0.1.0-py3-none-any.whl` | `8d19a0abe2f9083acaac6a3c1801cc5da38ba2c6a0aa64136d352667ec202318` |
| `asecli-0.1.0.tar.gz` | `c43e699aa88a67ddd528f1920a0672fbedd878d02c1e7400d2a107ae6304da32` |

## 隔离回滚观察

在临时 CPython 3.12 环境中，先校验上一版 `main@2b4d76c` artifact 的 wheel SHA-256（`6b92cfb4287c5d46a288966ca11fb92d52bf706201a1615a8cc413f158cb6446`），随后执行：

1. 安装上一版 wheel，`asecli parse tests/fixtures/step-antialiasing.function.txt` 成功（7 nodes / 7 wires）。
2. 强制重装本次 wheel，重复 parse 成功。
3. 强制重装上一版 wheel，重复 parse 成功。

该演练只在临时环境发生，不写入用户团结工程，也不改动任何用户 Shader。

## 边界

- 本记录证明本次提交的远端自动门禁、artifact 完整性和安装回滚路径。
- 未创建 GitHub Release、PyPI、CLI Hub 或其他公开包仓条目；对外分发仍需单独授权。

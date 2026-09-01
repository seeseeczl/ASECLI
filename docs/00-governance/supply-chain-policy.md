---
id: SUPPLY-0001
type: security-supply-chain-policy
status: approved
version: 1.0.0
created_at: 2026-09-01T12:54:38+08:00
owner: long
related: [AUD-SUPPLY-001, P2.1, REL-0001]
supersedes: []
evidence: [uv.lock, LICENSE, SECURITY.md, tools/supply_chain_check.py, tools/generate_sbom.py]
---

# 供应链与许可证基线

## 分发与许可

- AseCLI 当前是内部专有工具，许可证标识为 `LicenseRef-ASECLI-Proprietary`；未获得书面批准不得公开发布、上传 PyPI/Hub 或转授权。
- 当前生产运行时依赖为 0；开发依赖由 `uv.lock` 固定来源、版本和 SHA-256。第三方依赖继续遵守其自身许可证。
- 新增生产依赖、修改许可或公开分发属于单独 CR，必须先完成许可证与漏洞评估。

## 自动门禁

- `uv lock --check` 与 `uv sync --frozen`：禁止未锁定解析。
- `tools/supply_chain_check.py`：检查 lock hash、固定 Action SHA、常见高置信 secret 形态与内部许可证。
- `tools/generate_sbom.py`：生成 SPDX 2.3 JSON，包含项目、锁定包和构建 artifact SHA-256。
- CI 使用固定 commit 的 GitHub Actions；artifact 同时上传 wheel、sdist、SHA256SUMS、SBOM 和供应链检查结果。

## 漏洞、密钥与例外

严重度与 SLA 遵循 `SECURITY.md`。生产依赖目前为空，因此本地 SCA 只验证“零运行时依赖 + lock 完整性”；远程漏洞数据库/Dependabot 状态在实际 CI 启用前明确标为未验证。任何密钥不得进入 argv、仓库、artifact、日志或截图。

例外最长 30 天，必须记录 owner、批准人、风险、补偿控制、到期日和退出条件。当前无已批准例外。

## 工具来源

| 工具 | 固定版本/来源 | 用途 |
| --- | --- | --- |
| uv | 0.11.14 / astral-sh | lock、双 Python、构建、隔离安装 |
| actions/checkout | v4.2.2 / `11bd719...` | CI checkout |
| astral-sh/setup-uv | v6.7.0 / `b75a909...` | CI uv/Python |
| actions/upload-artifact | v4.6.2 / `ea165f8...` | CI artifact |

远程 GitHub CI、Dependabot 和漏洞数据库尚未由本地配置证明运行成功；解除条件是 push 后提供真实 run/alert 链接。

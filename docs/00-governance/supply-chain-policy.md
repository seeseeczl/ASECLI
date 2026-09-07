---
id: SUPPLY-0001
type: security-supply-chain-policy
status: approved
version: 1.1.0
created_at: 2026-09-01T12:54:38+08:00
owner: long
related: [AUD-SUPPLY-001, P2.1, REL-0001]
supersedes: []
evidence: [uv.lock, LICENSE, SECURITY.md, tools/supply_chain_check.py, tools/generate_sbom.py]
---

# 供应链与许可证基线

## 分发与许可

- AseCLI 以 MIT 许可证开源，标识为 `MIT`。用户安装入口为 PyPI 项目 `asecli`；源码与 GitHub Release 仍公开。CLI Hub 仍须单独 CR。
- 当前生产运行时依赖为 0；开发依赖由 `uv.lock` 固定来源、版本和 SHA-256。第三方依赖继续遵守其自身许可证。
- 新增生产依赖、修改许可或改变分发渠道属于单独 CR，必须先完成许可证与漏洞评估。

## 自动门禁

- `uv lock --check` 与 `uv sync --frozen`：禁止未锁定解析。
- `tools/supply_chain_check.py`：检查 lock hash、固定 Action SHA、常见高置信 secret 形态与内部许可证。
- `tools/generate_sbom.py`：生成 SPDX 2.3 JSON，包含项目、锁定包和构建 artifact SHA-256。
- CI 使用经官方 tag 核对、固定 commit 且原生声明 Node 24 的 GitHub Actions；`tools/check_ci_governance.py` 固定 allowlist，阻止 SHA/runtime 回退。`ci.yml` 必须包含 checkout、setup-uv 与 upload-artifact；`publish.yml` 额外固定 download-artifact。artifact 同时上传 wheel、sdist、SHA256SUMS、SBOM 和供应链检查结果。
- 推送 `vX.Y.Z` tag 后，`publish.yml` 以 Trusted Publishing 上传 PyPI，不在仓库中保存 PyPI token。

## 漏洞、密钥与例外

严重度与 SLA 遵循 `SECURITY.md`。生产依赖目前为空，因此本地 SCA 只验证“零运行时依赖 + lock 完整性”；远程漏洞数据库/Dependabot 状态在实际 CI 启用前明确标为未验证。任何密钥不得进入 argv、仓库、artifact、日志或截图。

例外最长 30 天，必须记录 owner、批准人、风险、补偿控制、到期日和退出条件。CR-0014 已关闭两项 C# LOC 例外，当前 `.project-architect.json` 的 `loc_exemptions` 为空；后续新增例外也不得放宽 Action、依赖、密钥或 artifact 门禁。

## 工具来源

| 工具 | 固定版本/来源 | 用途 |
| --- | --- | --- |
| uv | 0.11.14 / astral-sh | lock、双 Python、构建、隔离安装 |
| actions/checkout | v5.0.1 / `93cb6efe18208431cddfb8368fd83d5badbf9bfd` / Node 24 | CI checkout |
| astral-sh/setup-uv | v10.0.1 / `20cfd1bf945f4377ade1205e4dbc17946fc9a30d` / Node 24 | CI uv/Python |
| actions/upload-artifact | v6.0.0 / `b7c566a772e6b6bfb58ed0dc250532a479d7789f` / Node 24 | CI artifact；要求 GitHub Actions Runner `>=2.327.1`，当前 `ubuntu-latest` 满足，若引入 self-hosted runner 必须重新核对 |
| actions/download-artifact | v8.0.1 / `3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c` / Node 24 | PyPI 发布作业下载已构建发行包，不在持有 OIDC 凭据的作业中重新构建 |

上述版本与 SHA 已通过官方 GitHub tag/API 只读核对；本地治理只证明配置与 allowlist 正确。Node 24 新组合的远程 GitHub CI 仍需下一次获准推送后的真实 run 验证；Dependabot 和漏洞数据库状态仍需远程 alert 证据。

# 交付协议 — AseCLI

## 分支与提交

- 主分支 `main`；任务分支 `task/<task-id>-<slug>`。
- 每张任务卡至少一次提交；提交信息以 `TASK-xxxx:` 开头，便于追溯。

## 变更门禁

1. 新 FR/CR 先更新需求基线（ARCH-REQ-0001）与 `traceability.csv`，再动代码。
2. 缺陷修复先在回归目录登记会失败的 REG-*，再最小修复。
3. 公开 CLI 契约（命令名、JSON 输出结构、错误码）变更必须走 CR 并更新 MOD-CLI 契约段。
4. 每次提交前本地门禁：`uv run pytest -q` 必须全绿。

## 完成定义

- 任务卡状态变更需在 `docs/00-governance/timeline.md` 追加时间线记录。
- 验收命令输出粘贴进任务卡"时间线/证据回写"列。
- 追溯链（FR→MOD→TASK→REG）在 `traceability.csv` 中双向成立。

## 审计与复审

- 里程碑完成时运行架构校验脚本与快速审计。
- 发布前必须有一次 AUD 报告（S0/S1 清零）。

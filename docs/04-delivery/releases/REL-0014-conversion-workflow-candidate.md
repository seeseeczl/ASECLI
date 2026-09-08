---
id: REL-0014
type: release-record
status: released
version: 0.6.4
created_at: 2026-09-08T19:42:50+08:00
owner: long
related: [CR-0028, TASK-0061, TASK-0062, TASK-0063, REG-0060, REG-0061]
supersedes: []
evidence: [94 targeted tests passed; REG catalog 61 of 61; Skill validator passed]
---

# ASECLI v0.6.4 — 转换后图整理能力

## 变更集合

- FR/CR/BUG/ADR：CR-0028；输出端口级复用计划、折叠接口计算基线、刚性岛排布、转换后 Skill 流程。
- 版本/提交/PR：v0.6.4；用户授权推送、发布、安装 CLI 与全局 Skill；仅发布本会话 CR-0028 增量，使用暂存区的独立干净快照验证，不纳入并行创建器与渲染设置改动。最终提交以新 tag 解引用为准。
- 兼容性说明：原布局默认不变；fanout 显式选择；基线比较不猜未知默认值。未修改 SGCLI 与并行创建器。

## 验证与风险

- 测试/构建/审计证据：定向 94 passed，REG 61/61、Skill validator、diff 检查通过；全量 380 passed、3 skipped、1 failed（既有并行 editor_spec.py 行数门禁）。后追加的四岛三列用例已纳入定向通过。整体 fitness 还受并行 commands.py 私有导入影响。
- 发布快照：暂存内容独立导出后 Python 3.10/3.12 各 371 passed、3 skipped；完整治理含 fitness/release 全通过，REG 61/61、离线供应链、双构建相同、wheel 安装和 `0.6.4 → 0.6.3 → 0.6.4` version/parse 通过。此前工作区的并行失败项未进入发布内容；不修改门禁阈值。
- 正式 tag：`v0.6.4@d4a5a462bd4ffde6bd288a1da363f737bb9639ec`；[publish run 34224245874](https://github.com/seeseeczl/ASECLI/actions/runs/34224245874) 双 verify、package、OIDC publish 全部成功。
- [GitHub Release](https://github.com/seeseeczl/ASECLI/releases/tag/v0.6.4) 五项资产与 [PyPI](https://pypi.org/project/asecli/0.6.4/) wheel/sdist 匿名下载摘要核对一致。wheel SHA-256 `c44fc0f377b6f75c678e9e3fd9a17e3600b5ae3cbafebb5e73993cf11da52fc0`；sdist `2bc3f299e5728fbe7e0b43e4c2bb0e0a9b460838b048dbfccc37acbd8a8611d7`，与本地独立快照相同。
- 本机官方 PyPI 安装 `asecli 0.6.4`，graph-review 基线 smoke 通过。全局安装 `/Users/long/.agents/skills/asecli`、`/Users/long/.claude/skills/asecli`、`/Users/long/.codex/skills/asecli`；tag/包内/三目录完整树摘要均为 `73cbe34a80fd82709dc8254d97f7f4d8deb005545e1c6496686e091fac46098a`，重复安装幂等。
- 原 Codex Skill 备份：`/Users/long/.codex/skill-backups/asecli-pre-v0.6.4-20260908-3j5FX5`，可恢复。发布验证资产保留于 `/private/tmp/asecli-release-064.3j5FX5`；未改 SGCLI/生产 Shader，未启动 Editor。
- 已知风险与监控：不提供自动批量 Local Var Editor 创建；含固定 WireNode 的岛包装失败关闭；复杂现有 GUI 元数据变化采用保守不等比较；未进行真实 Editor、完整画布/悬浮交互或效果比较。
- Go / No-Go 决定与负责人：long 在已知未完成项披露后授权本次发布，独立快照与远端门禁通过，Go。仅图核对与布局计划自动环节已验证，真实画布/GUI/效果仍待验，不宣称完整 SG→ASE 等价转换。

## 回滚

- 触发条件：计算端口/常量变化、布局硬失败或实机与基线不等。
- 步骤：不用新增 graph-review/island-columns 参数即可沿用原有默认流程；若撤销开发增量，只回退 CR-0028 涉及的逐项 diff，不回退并行创建器改动。现有 Shader 不由旧 JSON 重建。
- 验证：定向测试验证旧默认布局、精排幂等与只读命令不写盘；发布执行隔离 0.6.4 → 0.6.3 → 0.6.4 version/parse。全局 Skill 更新前将不同内容移入唯一备份目录；回滚用 `uv tool install --force asecli==0.6.3` 并恢复对应 Skill 备份。无 Shader 数据迁移。

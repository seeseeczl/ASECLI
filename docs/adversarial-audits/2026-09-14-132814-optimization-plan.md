# 对抗性审计优化计划：ASECLI / SGCLI 各自独立

> 生成时间：2026-09-14 13:28:14（Asia/Shanghai）
> 落盘根目录：/Users/long/GitHub/ASECLI
> 关联报告：2026-09-14-132814-audit-report.md

## 1. 执行摘要

P0=0、P1=2、P2=2、P3=0。运行代码未发现互相依赖，独立维护/发布目标尚不通过。保留公开 JSON 协议、严格验证和失败关闭，移除强制跨仓发布与源码目录关联。

本轮仅审计。后续严格分两次执行：ASECLI 任务只修改 ASECLI；SGCLI 任务只修改 SGCLI。任何迁移到第三方集成测试工程也需另行确定目标和授权，不在本轮创建。

## 2. 修复与加固任务

| 任务 | 优先级 | 来源 | 内容 | 验收标准 | 依赖 | 风险/回滚 |
| --- | --- | --- | --- | --- | --- | --- |
| AA-OPT-001 | P1 | AA-COUP-001 | 各仓各自移除默认 CI/发布对另一仓 checkout/build 的必需依赖；同步本仓 workflow 回归 | 无对方源码、凭据和候选 SHA 时，自身测试/打包/发布路径正常；不删除本仓语义门禁 | 分仓授权 | 恢复本仓 workflow，不操作对方 |
| AA-OPT-002 | P1 | AA-COUP-002 | 本地固定协议修订及能力集；自完整性摘要与跨版本兼容分开 | 目标 Schema 兼容排版/描述变化不迫使双方同时发布；未知能力仍拒绝；协议声明对应夹具 | 无需对方代码 | 保留旧协议支持与不可变快照 |
| AA-OPT-003 | P2 | AA-COUP-003 | 移出兄弟仓库源码、虚拟环境和 git 状态相关脚本；跨产品测试另行管理 | 单仓克隆可开发；任何本仓必需命令不访问 ../另一仓；外部黑盒测试仅依赖发布接口 | 先列迁移范围，分别授权 | 保留可追溯历史，不删除用户资产 |
| AA-OPT-004 | P2 | AA-COUP-004 | 仅自身 wheel 的隔离导出、消费校验和负向回归 | 环境无对方模块、命令、源码，全部本仓相关路径可运行；新增耦合被门禁抓到 | 无 | 不以混装测试替代隔离证明 |
| AA-OPT-005 | P2 | 用户新边界 | 在各自仓库规则/技能明确“单仓任务不跨仓修改” | 对方缺能力时生成接口问题说明，停止于本仓边界；任何跨仓写入另行授权 | 各仓单独执行 | 保留转换编排能力，不禁止只读协议查阅 |

## 3. 测试补强任务

- AA-TEST-001：自身 wheel 安装在独立 venv，PATH 无另一 CLI，执行版本、导出、Schema 校验、失败报告；检查未导入另一包。
- AA-TEST-002：冻结协议正负 JSON 夹具，检查节点/资源/混合/报告语义；协议扩展不自动意味着旧消费者支持。
- AA-TEST-003：CI 静态检查不再要求另一仓 checkout、credential、branch、SHA、wheel 或脚本；对方全部不可用时本仓必要门禁仍可通过。
- AA-TEST-004：跨仓目录读写/互相 import/调用负例能被独立性门禁识别；集成测试不得掩盖本工具缺依赖。

## 4. 观测与运维任务

- AA-OBS-001：发布说明列出支持的协议修订、能力限制，不承诺另一 CLI 已同步升级。
- AA-OBS-002：可选外部兼容矩阵记录两边发布版本与 JSON SHA；结果不替代自身门禁，不回写两仓。
- AA-OBS-003：任务结束列明实际写入的单仓范围，确认另一仓未被该任务修改。

## 5. 发布门禁

- [ ] 本仓必需检查不执行另一仓代码、不要求另一仓权限或可用性。
- [ ] 只安装本工具即可执行相关导出/校验。
- [ ] 固定 JSON 规范和语义负向测试仍严格有效。
- [ ] 能独立构建、安装、回滚；报告已区分离线与 Editor/渲染证据。
- [ ] 没有修改另一仓库；对方任务独立安排。

## 6. 未映射项

无。静态 JSON Schema、规则实现及名称中的对方标识允许保留；它们是格式适配，不应为“无关联代码”而删除协议校验。联合工作流技能是否移至独立分发位置可另行讨论，本轮不新增运行依赖或架构项目。

## 7. ASECLI 单仓整改回执

- 已移除 ASECLI CI / publish 的 cross-cli job，publish 仍依赖自身 verify→package 的完整链路；删除本仓 `.github/workflows/cross-cli.yml`（Git 可恢复），不再 checkout 对方、使用对方 SSH secret/候选 SHA 或运行对方脚本。没有修改 GitHub 远程变量、Secret 或 SGCLI。
- 改为自身固定 Schema/语义正负回归及独立 wheel smoke；保留本包快照 SHA 校验，不读取另一仓实时 Schema。README/contracts 注释明确版本只是快照来源，不是运行依赖。
- 新增 `tools/independent_wheel_smoke.py`：仅安装 ASECLI wheel、检查 SGCLI 模块不可用，子进程 PATH 仅当前 venv，清除 PYTHONPATH，在临时工程运行版本、契约、实际 export-sg、非法 spec 拒绝及 CustomEditor 失败报告检查。CI 和 publish 的 package job 均运行该脚本。
- 本仓 AGENTS、ASECLI Skill 和已安装 `.agents/skills/asecli/SKILL.md` 同步单仓边界；不更新 SGCLI Skill、不修改对方仓库。跨仓静态回归改为禁止运行源码互相 import/固定开发目录和 CI 跨仓引用。
- 验证：相关测试 64 passed；CI governance 与 regression catalog 通过；独立 wheel 实测返回 `standalone_wheel=true`、`consumer_executed=false`；git diff --check 通过。隔离产物位于 `/tmp/asecli-independent-wheel.T0VXC8`。
- 此隔离 wheel 沿用当前工作树版本 0.8.2，仅用于候选测试，不是新版本正式发布，也没有替换本机 CLI。未启动 Editor，未提交/推送/发布。本轮移除的跨仓 YAML 是唯一删除的配置文件，可由 Git 历史恢复。
- 完成范围：AA-OPT-001/002/004/005 的 ASECLI 部分；AA-OPT-003 在 ASECLI 中的对方源码执行入口已移除。SGCLI 自有 CI、脚本与规则保持原样，其任务仍待独立执行，不能声明两个仓库都已解耦。

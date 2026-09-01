---
id: GOV-CHANGE-REGISTER-0001
type: change-register
status: in-progress
version: 1.0.0
created_at: 2026-09-01T12:54:38+08:00
owner: long
related: [AUD-20260901, ARCH-REQ-0001, PLAN-0001]
supersedes: []
evidence: [docs/05-audits/2026-09-01-122217-optimization-tasks.md]
---

# 变更登记 — 2026-09-01 审计整改

| CR ID | 修改语义 | 影响模块/API | 兼容与迁移 | 回归 | 发布/回滚 | 状态 |
| --- | --- | --- | --- | --- | --- | --- |
| CR-0002 | schema add-node 增加 ASE 版本门禁；create 仅替换 donor graph；所有图写入执行结构门禁 | MOD-CORE MOD-SCHEMA MOD-CHECK MOD-CLI | raw `--line` 保留；不兼容 schema 拒绝写入 | REG-0013 REG-0014 REG-0015 | 回滚到禁止 add-node/graph-from；文本只读能力保留 | 自动已验证，Editor 待验 |
| CR-0003 | argparse 失败统一单行 JSON；validate error 返回 exit 2；fix-checksum 默认 dry-run | MOD-CLI MOD-CHECK | 调用方需为 fix-checksum 增加 `--write`；help 仍为文本 | REG-0004 REG-0007 REG-0018 | 回滚单个 CLI 入口，不改变 checksum 算法 | 已验证 |
| CR-0004 | MCP tool error/保存语义严格判定；默认仅 loopback；token 改由环境注入；禁止重定向 | MOD-BRIDGE MOD-CLI MOD-SKILL | 远程端点需 `--allow-remote-mcp`；拒绝 argv token | REG-0016 REG-0017 | 可完全禁用远程，仅保留 loopback | mock 已验证，真实 MCP 待验 |
| CR-0005 | core 新增公开 `parse_node_line`，CLI 停止使用私有 helper | MOD-CORE MOD-CLI | `_parse_node_line` 保留一个兼容周期 | REG-0019 | 恢复旧 alias 调用，不删除公开 API | 已验证 |
| CR-0006 | 建立双 Python CI、可复现 artifact、内部许可、离线供应链检查、SPDX SBOM 与本地回滚 | MOD-CLI 交付链 | 不自动发布；远程 run 未发生时不得称为通过 | REG-0021 | 删除 CI 配置不影响运行时；恢复最后已验证 wheel | 本地与 GitHub run 33510909955/artifact 已验证；远程 Release 未创建 |
| CR-0007 | FR-0010 增加节点复用治理：跨区域或多消费者结果优先使用 Register/Get Local Var，Comment 管算法边界、Local Var 管模块数据接口 | MOD-SKILL | 不改变 CLI/API；一次性相邻链路继续直连；Register schema 不安全时必须经真实 ASE 创建或复用同版本样本 | REG-0010 | 回滚文档规范即可，不改现有 Shader 或运行时 | 文档与真实参考静态证据已验证；目标图应用待实际任务 |
| CR-0008 | FR-0011 增加受控 ASE Editor API 创建后端：声明式规格驱动模板、Sampler、CustomExpression、连线、Save→Load 回读；静态安全节点继续走离线文本链路 | MOD-BRIDGE MOD-CLI MOD-SKILL | `create` 现有文本模式保持兼容；Editor/auto 为 additive opt-in；不支持版本失败关闭 | REG-0026 REG-0027 REG-0028 REG-0029 | 禁用 Editor 后端即可回退到模板壳创建；不迁移已有 Shader | 已验证（结构创建；目标画面待验） |
| CR-0009 | 执行 `2026-09-01-203438` 对抗性审计计划：可复现构建隔离、精确 ASE 版本矩阵、JSON-RPC ID、后验失败保留、GUI unknown/反射门禁 | MOD-CUSTOM-GUI MOD-GUI-SUPPORT MOD-BRIDGE MOD-CLI 交付链 | 未知 ASE 版本从猜测兼容改为拒绝；post-commit 后验失败从自动删除改为保留诊断；gui-support 新增可选 `--runtime-probe` | REG-0031 REG-0032 REG-0033 REG-0034 REG-0035 | 可分别回滚；AA-OPT-003 回滚仅允许继续保留，不恢复危险 unlink | 自动与 GitHub run/artifact 已验证；真实 GUI probe/Inspector/渲染待验 |

授权来源：用户于 2026-09-01 明确要求“执行优化任务，全部完成”，并于同日批准吸收 ASE Editor API 方案后要求“执行”；随后明确要求先推送并执行对抗性审计优化计划。整改提交与 CI 修复已 push；未执行 GitHub Release、PyPI 发布或生产 Tuanjie 工程写入。

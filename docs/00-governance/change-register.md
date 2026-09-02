---
id: GOV-CHANGE-REGISTER-0001
type: change-register
status: in-progress
version: 1.1.0
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
| CR-0006 | 建立双 Python CI、可复现 artifact、内部许可、离线供应链检查、SPDX SBOM 与本地回滚 | MOD-CLI 交付链 | 不自动发布；远程 run 未发生时不得称为通过 | REG-0021 | 删除 CI 配置不影响运行时；恢复最后已验证 wheel | 本地与 GitHub artifact 已验证；`v0.1.0` 私有正式 Release 的 CI、五项载荷哈希和清单摘要通过；REL-0002 released |
| CR-0007 | FR-0010 增加节点复用治理：跨区域或多消费者结果优先使用 Register/Get Local Var，Comment 管算法边界、Local Var 管模块数据接口 | MOD-SKILL | 不改变 CLI/API；一次性相邻链路继续直连；Register schema 不安全时必须经真实 ASE 创建或复用同版本样本 | REG-0010 | 回滚文档规范即可，不改现有 Shader 或运行时 | 文档与真实参考静态证据已验证；目标图应用待实际任务 |
| CR-0008 | FR-0011 增加受控 ASE Editor API 创建后端：声明式规格驱动模板、Sampler、CustomExpression、连线、Save→Load 回读；静态安全节点继续走离线文本链路 | MOD-BRIDGE MOD-CLI MOD-SKILL | `create` 现有文本模式保持兼容；Editor/auto 为 additive opt-in；不支持版本失败关闭 | REG-0026 REG-0027 REG-0028 REG-0029 | 禁用 Editor 后端即可回退到模板壳创建；不迁移已有 Shader | 已验证（结构创建；目标画面待验） |
| CR-0009 | 执行 `2026-09-01-203438` 对抗性审计计划：可复现构建隔离、精确 ASE 版本矩阵、JSON-RPC ID、后验失败保留、GUI unknown/反射门禁 | MOD-CUSTOM-GUI MOD-GUI-SUPPORT MOD-BRIDGE MOD-CLI 交付链 | 未知 ASE 版本从猜测兼容改为拒绝；post-commit 后验失败从自动删除改为保留诊断；gui-support 新增可选 `--runtime-probe` | REG-0031 REG-0032 REG-0033 REG-0034 REG-0035 | 可分别回滚；AA-OPT-003 回滚仅允许继续保留，不恢复危险 unlink | 自动与 GitHub run/artifact 已验证；真实 GUI probe/Inspector/渲染待验 |
| CR-0010 | 自定义材质 GUI 元数据从 MZGUI-compatible 属性和原生提供者选择，迁移为 ASECLI 自有通用标记与唯一内置提供者 | MOD-CUSTOM-GUI MOD-GUI-SUPPORT MOD-BRIDGE MOD-CLI MOD-SKILL | 新写入 `ASECLIFoldout`/`ASECLITooltip`/`ASECLIHelpBox`；旧三标记只读兼容，触碰即迁移；无属性 API 且原生同名旧 drawer 存在时，仅从同一 `Assets/` 源 Shader 补齐缺失元数据；删除原生探测、优先级和 `gui-support --runtime-probe` | REG-0022 REG-0023 REG-0030 REG-0032 REG-0035 | 回滚仅恢复上一版 CLI/资源；不批量修改用户 Shader 或删除已安装资源 | 定向 67 passed/1 skipped；Python 3.10/3.12 全量均 203 passed/3 skipped；团结 2022.3.61t9 Inspector 与用户 Tooltip 截图通过；`v0.1.0@fbd9941` 的 CI run 33594698477 全绿，私有正式 Release 五项载荷哈希和清单摘要、隔离安装与上一版回滚通过；REL-0002 released |
| CR-0011 | 将常驻说明的目标视觉从人工约定提升为 ASECLI 可查询、写前强制的版本化呈现契约 | MOD-GUI-SUPPORT MOD-BRIDGE MOD-CLI | `gui-support` JSON additive 新增 `capabilities.inline_help_presentation`；`--write` 在内置资源违反 `asecli.inline-help.v1` 时拒绝安装；不改现有 Shader 元数据或材质值 | REG-0036 | 可回滚 Python 契约模块与 C# 轻量渲染；已安装工程文件由其原内容哈希识别，不自动覆盖 | 先失败 2 项；全量 208 passed/3 skipped；当前团结 2022.3.61t9 Inspector 与 Console 通过；待后续发布 |
| CR-0012 | 将公开属性的中文显示名、自动技术 Tooltip 和中文使用说明从建议提升为所有 ASECLI 创建文件的强制契约 | MOD-CUSTOM-GUI MOD-BRIDGE MOD-CLI | 新增 `asecli.property-presentation.v1`；`custom-gui` 公开逐属性状态，ASECLI-managed 写入不得破坏契约；文本创建只接受合规组合，Editor CLI 创建升级到 v2，v1 保留底层桥接兼容；MCP 3.4.7 envelope/安全扫描/回执时序兼容；CI 包路径、SBOM 版本和可移植校验清单随项目版本生成 | REG-0037 REG-0038 REG-0039 REG-0040 | 恢复本 CR 前 CLI 可回滚；已创建文件不自动迁移，非 ASECLI-managed 旧文件仍可只读/普通维护 | 新用例先失败 5 项；双 Python `223 passed, 3 skipped`，REG 36 条、CI governance、供应链、Skill、可复现 0.2.0 构建与隔离安装/回滚通过；两个既有 Shader 共 7 属性零违规；当前团结 v2 创建、暂存重载、提交、独立 recompile 后两属性零差异；Inspector 中文显示名/说明可见，用户现场确认两项 Tooltip 正常；验证资产已精确清理；首次推送先后暴露历史版本硬编码和下载清单路径前缀，已登记 BUG-0017/0018 并修复；新进程重开受限未执行，0.2.0 尚未打 tag 或发布 |
| CR-0013 | Editor `create` 成功 JSON 区分暂存图重载与已提交目标图重载，避免 Agent 把 `reloaded=true` 理解成目标图已在 ASE 中重开 | MOD-BRIDGE MOD-CLI MOD-SKILL | additive 增加 `staging_reloaded` 与 `target_graph_reloaded`；保留 `reloaded` 作为暂存重载兼容别名；同一次创建调用仍不 Load 已提交目标图 | REG-0038 | 去掉新字段即可回退到仅 `reloaded` 兼容别名；不得恢复提交后立刻 Load 目标图 | 失败优先契约测试先暴露缺字段；修复后 editor_create/CLI 回归断言 `reloaded=true`、`staging_reloaded=true`、`target_graph_reloaded=false` |

授权来源：用户于 2026-09-01 明确要求“执行优化任务，全部完成”，并于同日批准吸收 ASE Editor API 方案后要求“执行”；随后明确要求先推送并执行对抗性审计优化计划。2026-09-02 用户要求推送并进一步明确“以正式的 CLI 形式发布”，据此创建私有正式 GitHub Release `v0.1.0`；同日进一步明确说明条样式一致性必须成为 CLI 的规范能力，据此登记 CR-0011/BUG-0015，并明确所有通过 CLI 构建的 ASE 文件都必须使用中文属性显示名、自动变量名/默认值 Tooltip 和中文使用说明，据此登记 CR-0012。同日用户要求执行 `2026-09-02-211218` 优化计划，据此登记 CR-0013。未执行 PyPI、CLI Hub、公开分发或本轮远程发布。

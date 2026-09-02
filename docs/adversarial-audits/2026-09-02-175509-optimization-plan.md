# 对抗性审计优化计划：CR-0012 属性呈现强制契约

> 生成时间：2026-09-02 17:55:09 +08:00
> 项目根目录：`/Users/long/GitHub/ASECLI`
> 关联报告：`docs/adversarial-audits/2026-09-02-175509-audit-report.md`

## 1. 执行摘要

- 审计对象：当前未提交的 `asecli.property-presentation.v1`、文本/Editor 创建、managed 通用写入门禁和正式包版本。
- Findings 统计：P0=0 P1=2 P2=1 P3=0。
- 发布建议：阻塞；当前不能提交为“属性规范已强制完成”，也不能基于 `0.1.0` 重新发布。
- 建议执行顺序：AA-OPT-001 → AA-OPT-002 → AA-TEST-001 → AA-TEST-002 → AA-OPT-003 → AA-TEST-003。

## 2. 修复与加固任务

| 任务 ID | 优先级 | 来源 Finding | 内容 | 验收标准 | 依赖 | 风险/回滚 |
| --- | --- | --- | --- | --- | --- | --- |
| AA-OPT-001 | P1 | AA-COR-001 | 为 ShaderLab `Properties` 建立只读解析结果，并与图内导出 PropertyNode 双向核对属性名、中文显示名和 ASECLIHelpBox；文本 `--graph-from` 无法证明一致时拒绝创建。 | Caster 壳 + Receiver donor 返回 `PROPERTY_PRESENTATION_ERROR` 且目标不存在；编译区-only、图-only、显示名不一致、HelpBox 不一致均返回明确 violation；匹配文件保持通过；现有两个 Shader 仍为零违规。 | — | Parser 只覆盖已验证的 ShaderLab 属性语法；遇到未知语法失败关闭。回滚时可禁用文本 donor 创建，但不能恢复真空通过。 |
| AA-OPT-002 | P1 | AA-FAIL-002 | 删除 `require_managed_property_presentation` 的宽泛 `ValueError → None`；建立显式 not-managed 判定和 managed/疑似 managed 检查错误。 | 对重复 CustomEditor 的 managed 文件执行 `set-field`、`layout` 等写命令均返回 `PROPERTY_PRESENTATION_ERROR`；源文件 SHA-256 不变；明确不含 ASECLI 痕迹的普通文件维持原兼容行为。 | AA-OPT-001 | 可能收紧损坏文件的写入能力；提供只读诊断和明确修复入口，不允许以通用写命令绕过。 |
| AA-OPT-003 | P2 | AA-REL-003 | P1 修复和真实验证完成后升级包版本；建议因正式 CLI 拒绝 EditorGraphSpec v1 使用 `0.2.0`。 | `pyproject.toml` 与 `uv.lock` 版本一致；构建产物名为新版本；新 tag/Release 不覆盖 `v0.1.0`；隔离安装后 `asecli --version`、v2 创建门禁和回滚安装均可验证。 | AA-OPT-001 AA-OPT-002 AA-TEST-003 | 不提前打 tag/上传；版本变更可在发布前撤回，已发布的 `v0.1.0` 保持不可变。 |

## 3. 测试补强任务

| 任务 ID | 优先级 | 覆盖缺口 | 内容 | 验收标准 |
| --- | --- | --- | --- | --- |
| AA-TEST-001 | P1 | 文本 create 的双源一致性与真空循环 | 新增实际不同模板/donor 的失败优先测试；把 `tests/test_create.py` 的“合规 fixture”换成至少含一个可识别 PropertyNode 的 19602 样本，并先断言属性数量。 | 修复前用例失败；修复后 Caster/Receiver 混合零写盘，匹配组合成功，helper 不再允许零次循环。 |
| AA-TEST-002 | P1 | 检查异常时的 fail-closed | 参数化重复 CustomEditor、未知图版本、损坏属性尾部；覆盖所有走 `_save` 的代表性写命令和写入冲突。 | 每种异常都返回稳定错误码和 violations；修改前后文件 digest 相同；普通非 managed 文件不受影响。 |
| AA-TEST-003 | P1 | EditorGraphSpec v2 真实链路 | 在当前团结 `2022.3.61t9`、ASE `1.9.6.2` 的受控目标中创建含多种 Property/Sampler 的临时 Shader，核对 Inspector、Tooltip、中文说明、保存重载及新进程重载。 | CLI 返回 v2 合规；Editor 重载后图/编译区 reconciliation 仍为 valid；真实 Tooltip 展示英文变量名与 Shader 默认值；失败资产按事务规则处理。 |

## 4. 观测与运维任务

| 任务 ID | 优先级 | 内容 | 验收标准 |
| --- | --- | --- | --- |
| AA-OBS-001 | P2 | 扩展 `property_presentation` JSON，分别报告图属性、编译区属性、双向缺失、显示名/HelpBox一致性和检查是否完整。 | 调用方可仅凭单行 JSON 区分 `valid`、`invalid`、`inspection_error`，不存在空列表真空通过。 |
| AA-OBS-002 | P2 | 在发布/治理证据中分离文件契约、GUI 资源安装、真实 Inspector 和远程 Release 四层状态。 | 任一层未验证时不得汇总为“规范已完整生效”；发布记录带新版本 artifact digest 和真实 Editor 证据。 |

## 5. 发布门禁

- [x] AA-OPT-001 完成，编译区与图属性双向一致性检查通过。
- [x] AA-OPT-002 完成，managed 检查异常全部失败关闭。
- [x] AA-TEST-001、AA-TEST-002 的失败优先证据和修复后回归均落盘。
- [x] 全量 pytest、REG catalog、CI governance、供应链、双 Python 和可复现构建通过。
- [x] AA-TEST-003 已在当前真实团结实例完成 v2 创建、暂存重载、提交、独立 recompile、reconciliation 和 Inspector 验收；中文显示名/中文说明可见，用户现场确认两项 Tooltip 气泡正常。新进程重开受“仅用当前实例”约束未执行，不冒充已验证。
- [x] AA-OPT-003 已完成 `0.2.0` 版本、可复现构建、隔离安装与 0.1.0 回滚演练；提交/tag/Release 属于后续发布动作，本轮未获授权，因此没有执行。
- [x] 残留风险已在 README、REG-0037/0038、TASK-0032 和本计划中分层披露。

## 6. 未映射项

- 无。两个 P1 和一个 P2 finding 均有对应 AA-OPT；测试与观测缺口分别映射到 AA-TEST/AA-OBS。

## 7. 执行记录（2026-09-02）

- 自动回归：Python 3.10/3.12 均 `223 passed, 3 skipped`；REG catalog 34 条、CI governance、离线供应链、ASECLI Skill 和 `git diff --check` 通过。
- 构建：`asecli-0.2.0-py3-none-any.whl` 与 `asecli-0.2.0.tar.gz` 双构建逐字节一致；隔离环境完成 0.2.0 安装、0.1.0 回滚和 0.2.0 恢复。最终产物 SHA-256 仅在构建完成后的外部回执/Release manifest 记录，避免 sdist 收录本文后形成自引用哈希。
- 架构：Project Architect strict 当前工作树与 HEAD 均为同一批 31 项历史问题（kickoff 2、traceability 25、fitness 4），本次未新增。
- 真实 Editor：当前团结 `2022.3.61t9`、ASE `1.9.6.2`、MCP 3.4.7 成功创建 v2 Sampler/RangedFloat，Save/暂存重载/manifest/commit 均确认；独立 `recompile` 后 `_AuditMask`、`_AuditStrength` 图/编译区双向一致、中文显示名和中文 HelpBox 零违规。Inspector 中“验证遮罩”“验证强度”及各自中文说明可见，当前实例反射得到 Tooltip 为 `_AuditMask`/`None` 与 `_AuditStrength`/`0`，用户现场确认两项气泡正常。
- 实测新增缺陷：BUG-0016/REG-0038 记录 MCP `data.result` envelope、安全扫描拦截固定回滚代码和回执前插件重连；已最小修复并在当前实例复验。
- 清理与边界：视觉验收后已恢复 `VehicleLocalShadowReceiver.mat` 选择，并由当前实例精确删除验证 `.shader/.meta/.mat` 四个文件；磁盘与 AssetDatabase 均确认不存在，且无 `ASECLI-Temp-*` 残留。新进程重开因用户明确要求仅使用当前实例而未执行；目标平台渲染、远程 CI、commit/tag/Release 也未执行。

# 对抗性审计优化计划：ASECLI Editor 创建后端

> 生成时间：2026-09-01 19:35:21 CST
> 项目根目录：`/Users/long/GitHub/ASECLI`
> 关联报告：`docs/adversarial-audits/2026-09-01-193521-audit-report.md`

## 1. 执行摘要

- 审计对象：`EditorGraphSpec v1` 到 ASE 1.9.6.2 真实资产提交的完整 Editor 创建链路。
- Findings 统计：P0=0 P1=2 P2=2 P3=0。
- 发布建议：初始阻塞；四项必要修复与对应门禁已完成后，结构创建能力条件通过，目标渲染能力仍不在本轮结论内。
- 建议执行顺序：先修正 Shader 身份和 manifest，再封闭端口/属性规格，最后收紧关闭与回滚事务；随后统一执行自动和真实 Editor 回归。

## 2. 修复与加固任务

| 任务 ID | 优先级 | 来源 Finding | 内容 | 验收标准 | 依赖 | 风险/回滚 |
| --- | --- | --- | --- | --- | --- | --- |
| AA-OPT-001 | P1 | AA-COR-001 | 将规格 Shader 名传给 ASE，manifest 增加模板 GUID 与 Shader 名并在保存/重载后核对 | Caster/Receiver 最终声明分别为 `ASECLI/E2E/Caster`、`ASECLI/E2E/Receiver`；返回 manifest 与规格一致 | — | 保持暂存路径不变；若 ASE 参数语义与实测不符，停止交付而非文本改写 Shader |
| AA-OPT-002 | P1 | AA-COR-002 | 为 v1 节点和当前模板建立端口/类型契约，在 Python 侧完整预检连接 | 不存在端口和已知不兼容类型均由 `EditorGraphSpec.from_dict` 抛 `SpecError`，MCP 不被调用；现有有效规格继续通过 | AA-OPT-001 | 只开放实测契约；未知模板/节点拒绝，不猜测 ASE API |
| AA-OPT-003 | P2 | AA-DATA-001 | 对 property/sampler 的 `property_name` 做全局唯一性校验 | 重复属性规格在 Python 解析阶段失败；不同属性名和无属性节点不受影响 | AA-OPT-002 | 不自动改名，避免请求语义漂移 |
| AA-OPT-004 | P2 | AA-FAIL-001 | 把窗口关闭和状态恢复纳入成功事务；清理异常触发已提交目标回滚，finally 保留无害兜底 | 静态契约和注入异常用例证明成功标志晚于关闭；关闭失败时目标/暂存均不存在，原窗口和选择恢复 | AA-OPT-001 | 不吞主异常；回滚失败必须附加报告，不能伪报成功 |

## 3. 测试补强任务

| 任务 ID | 优先级 | 覆盖缺口 | 内容 | 验收标准 |
| --- | --- | --- | --- | --- |
| AA-TEST-001 | P1 | Shader 身份未断言 | 单元测试 expected manifest；真实 E2E 读取最终 ShaderLab 声明并与规格精确比较 | 自动测试和隔离团结 E2E 均通过，错误暂存名不再出现为 Shader 声明 |
| AA-TEST-002 | P1 | 端口契约不完整 | 覆盖每类白名单节点的有效端口、越界端口、方向错误和已知类型不兼容 | 所有错误均在构造 payload/MCP 前以稳定 `SpecError` 失败 |
| AA-TEST-003 | P2 | 属性唯一性未测 | 添加 property/property、property/sampler、sampler/sampler 重名用例 | 三类重名均失败，合法 Caster/Receiver 规格不回归 |
| AA-TEST-004 | P2 | 关闭异常事务未测 | 增加 C# 结构契约，并在可控 harness 中注入关闭失败 | 失败无最终资产、无暂存资产、无窗口/静态状态残留 |

## 4. 观测与运维任务

| 任务 ID | 优先级 | 内容 | 验收标准 |
| --- | --- | --- | --- |
| AA-OBS-001 | P2 | Editor 结果记录 `template_guid`、`shader_name`、最终 `asset_path` 和提交状态 | 调用方可把请求身份与保存/重载后的真实身份逐字段对账 |
| AA-OBS-002 | P3 | 文档披露 MCP 客户端超时后的未知完成状态和人工复核路径 | README/Skill 不把超时描述为确定回滚，并给出目标/暂存资产检查方法 |

## 5. 发布门禁

- [x] 所有 P0 任务完成（本轮无 P0）。
- [x] 所有 P1 任务完成或已接受风险并记录。
- [x] 对应回归、规格预检、关闭异常和真实团结 E2E 通过。
- [x] 残留风险已在报告、README 和 Skill 中披露。
- [x] 自动测试、真实 Editor 结构可编辑性、目标渲染画面三类证据分别报告，不互相替代。

## 6. 未映射项（如有）

- 无。P1/P2 Findings 均映射到 AA-OPT；MCP 超时竞态作为 AA-OBS-002 和残留风险记录，本轮不扩展协议。

## 7. 执行结果

| 任务 | 状态 | 完成证据 |
| --- | --- | --- |
| AA-OPT-001 / AA-TEST-001 / AA-OBS-001 | 已完成 | Shader 声明名、Master 名、Asset `Shader.name`、模板 GUID 和返回 manifest 逐项核对；真实 Caster/Receiver 名称正确 |
| AA-OPT-002 / AA-TEST-002 | 已完成 | 端口契约独立模块；不存在端口、方向错误、未知 Master 契约和基本类型不兼容在 MCP 前失败 |
| AA-OPT-003 / AA-TEST-003 | 已完成 | 三种 property/sampler 重名组合均有回归并失败关闭 |
| AA-OPT-004 / AA-TEST-004 | 已完成 | `success=true` 晚于状态恢复与窗口关闭；真实团结注入关闭异常后目标/meta/暂存均回滚 |
| AA-OBS-002 | 已完成 | README/Skill 明确 MCP 超时为未知完成状态并给出复核路径 |

最终证据：Python 全量 `171 passed, 2 skipped`；隔离团结 2022.3.61t9 + ASE 1.9.6.2 E2E `1 passed in 39.60s`；CI governance、25 条 REG catalog 与 `git diff --check` 通过。wheel 已确认包含 `asecli/bridge/resources/editor_create.cs.txt`。隔离工程及日志已移动到可恢复的 `/Users/long/.Trash/asecli-editor-e2e-20260901-193521-CfmDypRTeJ`；生产工程未修改，目标渲染画面未执行。

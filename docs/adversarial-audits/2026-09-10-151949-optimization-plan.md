# 对抗性审计优化计划：ASE → Shader Graph 导出功能

> 生成时间：2026-09-10 15:19:49 +08:00
> 项目根目录：`/Users/long/GitHub/ASECLI`
> 关联报告：`docs/adversarial-audits/2026-09-10-151949-audit-report.md`

## 1. 执行摘要

- 审计对象：当前工作树的 `asecli export-sg` 与 SGCLI 契约交接。
- Findings 统计：P0=0 P1=4 P2=2 P3=0。
- 发布建议：阻塞。
- 建议执行顺序：结构 fail-closed → Master 语义 → 属性完整性 → 契约边界 → 确定性与资源证据。

## 2. 修复与加固任务

| 任务 ID | 优先级 | 来源 Finding | 内容 | 验收标准 | 依赖 | 风险/回滚 |
| --- | --- | --- | --- | --- | --- | --- |
| AA-OPT-001 | P1 | AA-COR-001 | 复用 ASE 结构校验并对所有丢失端点阻断 | 悬空源/目标、重复输入、Local Var 断链均返回非零；只写失败报告 | — | 可能拒绝过去容忍的手工图；回滚仅限新门禁 |
| AA-OPT-002 | P1 | AA-COR-002 | 为标准 URP Unlit Master 建立完整、版本化的设置证据表 | 每个效果选项或映射到 Target 且经 Editor 读回，或以源节点 ID 和选项名阻断 | AA-OPT-001 | 错误枚举映射会改变效果；未认证前保持阻断 |
| AA-OPT-003 | P1 | AA-DATA-003 | 对账 ShaderLab 属性、ASE Property 节点和外部消费 | 任一仅在 ShaderLab 中的属性都有显式诊断；无法证明无效时导出失败 | AA-OPT-001 | 模板内建属性需建立证据白名单，不得通配忽略 |
| AA-OPT-004 | P1 | AA-CONTRACT-004 | 统一文档、Schema、ASECLI 输出与 SGCLI loader 边界 | 最终交付的图规格整体通过正式 Schema；报告不出现在规格白名单内；无需修改 SGCLI 即可消费 | — | 会影响当前复合包使用者；保留显式迁移工具而非默认双解析 |
| AA-OPT-005 | P2 | AA-DATA-005 | 将瞬态 Editor 身份与可重现交付物分离 | 同一输入与同一环境的图规格字节一致；报告明确区分稳定证据和运行证据 | AA-OPT-004 | 删除证据前先保留语义端口和环境摘要 |
| AA-OPT-006 | P2 | AA-RES-006 | 增加目标资产类型和 importer 只读核对 | 纹理类型、sRGB、Normal Map、Wrap/Filter 等已声明语义有可追溯证据；冲突或缺失时阻断 | AA-OPT-001 | Editor 不可用时不能回落为文件存在即成功 |

## 3. 测试补强任务

| 任务 ID | 优先级 | 覆盖缺口 | 内容 | 验收标准 |
| --- | --- | --- | --- | --- |
| AA-TEST-001 | P1 | 结构错误未进入导出门禁 | 将本次悬空目标变异样本改为回归测试 | CLI 非零退出，`semantic_mapping=blocked`，不生成图规格 |
| AA-TEST-002 | P1 | Master 选项折叠 | 对 Cast/Receive Shadows、LOD CrossFade、透明、混合、深度做逐项变异 | 每次变异要么改变预期 Target，要么明确阻断 |
| AA-TEST-003 | P1 | 外部属性丢失 | 增加无 ASE 节点的可见/隐藏 ShaderLab 属性样本 | 报告指向具体属性并阻断 |
| AA-TEST-004 | P1 | 交付物 Schema 假覆盖 | 对 CLI 实际写出的整个图文件执行 Draft 2020-12 校验 | 整个文件通过，无需预先提取子对象 |
| AA-TEST-005 | P2 | 确定性 | 相同输入连续导出两次并比较稳定产物 | 规格字节和规范化报告一致 |
| AA-TEST-006 | P2 | 资源导入设置 | 构造同 GUID 映射但类型、sRGB 或 Normal Map 不同的目标资产 | 所有效果相关冲突被拒绝并报告差异 |

## 4. 观测与运维任务

| 任务 ID | 优先级 | 内容 | 验收标准 |
| --- | --- | --- | --- |
| AA-OBS-001 | P2 | 报告记录源结构校验 issue 数量和代码 | 每个阻断问题可定位到文件、节点或端口 |
| AA-OBS-002 | P2 | 报告区分「已解析路径」与「已核对资产语义」 | 仅文件存在时不使用 `resolved` 表示效果已证明 |

## 5. 发布门禁

- [x] 所有 P0 任务完成（本次无 P0）。
- [x] 所有 P1 任务完成。
- [x] 对应结构、Master、属性、Schema、确定性和资源回归通过。
- [x] 已在同一受控 ASECLI/SGCLI 基线运行真实 Editor create、保存重载和编译。
- [x] 画布与效果未运行，已在验收记录中保持 `not_run`。

## 6. 未映射项

- 无。

## 7. 执行结果（2026-09-10）

- AA-OPT-001～006、AA-TEST-001～006、AA-OBS-001～002 均已实施。
- 自动验证：`422 passed, 3 skipped`；导出与对抗定向验证 `63 passed`。
- 真实 Editor：`ASEToSG_UV_20260910.shader` 已导出裸规格，SGCLI 实际创建、读回和 Editor 校验通过；节点、连接及 Cast/Receive Shadows、LOD CrossFade 设置与源语义对账通过。
- 失败路径：悬空连线变异返回非零，只生成 `report.json`，没有生成 `graph.sg.json`。
- 验收证据：`e2e-results/ase-to-sg-adversarial-20260910/acceptance.json`。
- 本次没有运行 Shader Graph 画布人工检查或材质渲染效果对比，因此不声明视觉或效果等价。

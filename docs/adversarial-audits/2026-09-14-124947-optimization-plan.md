# 对抗性审计优化计划：ASECLI → SGCLI JSON 交接

> 时间：2026-09-14 12:49:47（Asia/Shanghai）
> 项目根目录：/Users/long/GitHub/ASECLI
> 关联报告：2026-09-14-124947-audit-report.md

## 1. 执行摘要

发现 P0=0、P1=3、P2=2、P3=0。当前建议阻塞完整语义认证的合并/发布声明。本轮仅审计，以下任务尚未执行。沿现有裸 spec + report + receipt 架构修复，不引入中间 wrapper 或两 CLI 相互调用。

## 2. 修复任务

| 任务 | 优先级 | 来源 | 最小修复 | 验收标准 | 依赖 | 风险与回滚 |
| --- | --- | --- | --- | --- | --- | --- |
| AA-OPT-001 | P1 | AA-JSON-001 | 加载、校验、认证、创建共享不可变 spec bytes/SHA | 两次读之间替换的确定性反例被拒绝，或根本不再第二次读 spec；create 与 contract 两入口一致 | 无 | 接口改动影响调用方；回退相关提交，保留失败关闭，不用关闭摘要校验作为回滚 |
| AA-OPT-002 | P1 | AA-JSON-002 | 统一别名与完整类型的语义分类 | 同一 Custom Function 两种命名均拒绝重复调制；未知函数认证策略一致；精确模式合法函数继续通过 | 无 | 原生类型合法作者路径受影响，测试等价输入；不删除原生类型支持 |
| AA-OPT-003 | P1 | AA-JSON-003 | 添加资源内容/有效导入设置证据及交接重查 | 红蓝同 GUID 拒绝；仅平台覆盖变化可检测；导出后内容或 meta 变化不可继续认证为旧资源；相同资源仍通过 | 可能涉及 report 契约同步 | 新证据字段需两端 Schema、哈希及版本策略同步；不修改纹理或以默认白纹理恢复 |
| AA-OPT-004 | P2 | AA-JSON-004 | 内部降级映射进公开报告并影响对应语义状态 | CustomEditor/MZGUI 夹具公开 report 保留定位与原因；未知渲染副作用不能被笼统认定纯 UI | 与 005 协同 | 既有有损输入可能开始阻断，这是预期；需明确兼容策略 |
| AA-OPT-005 | P2 | AA-JSON-005 | 生产与消费采用一致的语义/降级一致性规则 | verified+SEM-RESOURCE unsupported 拒绝；正常生产者下游 not_run 仍允许进入 Editor；哈希不变的原 bundle 校验正常 | 与 004 协同 | 不得一刀切禁止所有 evidence_gap，避免阻断正常创建前报告 |

## 3. 定向测试补强

| 任务 | 优先级 | 测试内容 | 完成判据 |
| --- | --- | --- | --- |
| AA-TEST-001 | P1 | 使用真实 _load_request/_contract 和受控读取序列模拟 A→B | 创建对象的 SHA 必须与被认证 spec 相同 |
| AA-TEST-002 | P1 | 别名/完整类型 × String/File × 直接/间接调制 | 相同语义输入有相同认证结果；不只断言字符串 matcher |
| AA-TEST-003 | P1 | 两个小 Unity 项目资源夹具：不同内容、不同 GUID、不同平台覆盖、导出后变更 | 各差异被准确定位，完全一致控制组通过 |
| AA-TEST-004 | P2 | 从实际 cmd_export_sg 输出接到 SGCLI 校验入口 | 内部和公开 report 已知降级一致；不使用人工补写正确标志掩盖生产者错误 |
| AA-TEST-005 | P2 | 矛盾 report 与正常 not_run report 配对 | 前者拒绝、后者允许；保持 receipt SHA/path 绑定原有回归 |

只运行相关模块回归。JSON/报告修复本身先离线验证；如修改实际 Editor 绑定或资源应用逻辑，再在所有候选修改完成后集中进行 Editor 验证。

## 4. 观测与证据

| 任务 | 优先级 | 内容 | 验收 |
| --- | --- | --- | --- |
| AA-OBS-001 | P1 | 返回/记录被消费快照及资源证据摘要 | 不会将 A 的 spec SHA 与 B 的认证拼接；错误指出具体失配资产 |
| AA-OBS-002 | P2 | 用机器可读方式保留已知降级及其阶段 | producer、consumer、Editor、render 状态可区分；报告有矛盾时明确失败 |

## 5. 门禁与回滚

- [ ] 三项 P1 及对应反例回归全部通过。
- [ ] 两项报告缺陷处理完成，正常证据缺口不被误拒绝。
- [ ] 若合同变更，两端权威 Schema 与 vendored 摘要一致。
- [ ] 真实 ASECLI 生成三件套原字节直接交给 SGCLI，通过一致快照验证。
- [ ] 失败不产生部分正式 spec/目标资产，原文件和用户改动保留。
- [ ] 回滚按各任务的代码/合同版本进行，不回滚或改写用户 Shader、纹理、生产证据。

## 6. 未映射项

无。所有发现均对应修复任务。此计划不包含发布、推送、无关重构或重做既有 Shader 效果。

## 7. 本轮修复回执（2026-09-14）

- AA-OPT-001：create/contract 初读 SHA 传入认证，两次读取 A→B 的确定性反例均拒绝。
- AA-OPT-002：CustomFunction 别名和完整类型统一分类，认证与 prepare 回归覆盖两种写法。
- AA-OPT-003：生产端比较纹理内容、GUID、完整 TextureImporter（含平台覆盖），发布前重查；报告携带四份文件摘要。消费者绑定纹理属性、目标路径和实际工程，认证时及暂存导入后的提交前重查。内容、meta、缺快照、错工程、错属性/路径、重复快照均拒绝。完整 importer 文本采取保守相等策略，未知或非渲染字段差异也可能阻断，不默许降级。
- AA-OPT-004：公开报告保留内部降级代码、详情、源文件/属性位置和 CustomEditor 类名；属性语义标 unsupported。实际 cmd_export_sg 的 MZGUI 反例只留下失败报告，不产生正式 spec/receipt。
- AA-OPT-005：生产者、消费者和独立报告校验器拒绝 verified 与对应语义降级矛盾；正常下游 evidence_gap 仍允许。快照字段 Schema 和校验脚本已通过官方安装入口同步至已安装 shader-conversion，回读 changed=false，其余技能内容不变。

验证：ASECLI 定向测试 47 passed；SGCLI native 模块测试 420 passed。其后补充畸形证据防御和提交前重查测试，最终相关 gate/resource 测试 34 passed。两仓库 git diff --check 通过。没有修改本轮范围外的已有工作树改动，没有启动 Editor，没有提交或推送。

真实离线交接控制组：ASECLI cmd_export_sg 生成三件套，未改写产物，SGCLI sg contract --version 3 返回 validated=true、semantic_certified=true；独立报告校验器返回零错误。产物目录：`/private/var/folders/0f/lrhkp7jn3tz03szvlws2cm380000gn/T/ase-json-handoff-fixed-ulsgjyx3/out`，spec SHA-256：`8521cbb81d834768a48654595a80214094fdcffa1018a8ebb5da6b05bcc0a384`。这是无纹理控制组；资源差异通过定向文件夹具验证，不冒充真实 Unity 导入/渲染结果。

兼容边界：含非空纹理但缺 resource_snapshots 的旧报告将被拒绝，须由 ASECLI 重新导出，不允许补写旧报告证据。本轮修复 JSON 交接可信度，不新增或替代已有视觉等价证据。

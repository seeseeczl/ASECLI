# 对抗性审计优化计划：ASE → SG 精确 Alpha 转换增量

> 生成时间：2026-09-14 12:36:40（Asia/Shanghai）
> 项目根目录：/Users/long/GitHub/ASECLI
> 关联报告：2026-09-14-123640-audit-report.md

## 1. 执行摘要

P0=0，P1=2，P2=1，P3=0。建议阻塞合并/发布。本文件仅给出本次发现对应的修复任务，未执行业务代码修改。顺序：001、002 → 003 → 集中 Editor 验证。

## 2. 修复与加固任务

| 任务 | 优先级 | 来源 | 内容 | 验收标准 | 依赖 | 风险/回滚 |
| --- | --- | --- | --- | --- | --- | --- |
| AA-OPT-001 | P1 | AA-COR-001 | 在创建和编辑的最终 Target 状态中拒绝精确模式 + allowMaterialOverride；在完整实现材质支持前保持拒绝 | 新建非法组合、先设置模式后打开覆盖、先覆盖后改模式均明确拒绝；图文件 SHA 不变；普通模式不受影响 | 无 | 精确图允许的操作收窄；仅回退对应校验补丁，不恢复用户图 |
| AA-OPT-002 | P1 | AA-COR-002 | 恢复普通 Multiply 未证明函数的失败关闭；精确模式独立处理；允许普通无害函数前提供明确证明路径 | 报告中的多语句反例不能认证；文件函数/局部变量/多输出函数有拒绝或证明；精确模式保留原表达式并通过 | 无 | 部分此前误放行输入重新阻断；不要以关闭门禁回滚 |
| AA-OPT-003 | P2 | AA-COMPAT-003 | 对确认的完整项目 URP 包施加最小补丁，保留 FXAA 和 meta | 解包文件清单/哈希对账；FXAA 类型与 GUID 保持；UniversalTarget 预期改动可读；包可由明确源重建 | 无 | 全局渲染依赖，先记录包与 manifest/lock SHA；保留当前包备份，按明确版本回滚，禁止覆盖其他用户依赖改动 |

## 3. 测试补强任务

| 任务 | 优先级 | 覆盖缺口 | 内容与验收标准 |
| --- | --- | --- | --- |
| AA-TEST-001 | P1 | 配置组合 | 对创建/编辑最终状态增加正反例；对应修复完成后一次 Editor 会话确认拒绝无副作用 |
| AA-TEST-002 | P1 | 非单赋值调制 | 复用隔离转换夹具，覆盖本报告反例；断言无法获得 semantic_certified，而不只测正则返回值 |
| AA-TEST-003 | P2 | 包和反向转换 | 解包哈希清单断言只改白名单；SG AlphaMode=4 经实际 ASE 生成核对 RGB/Alpha Blend 与表达式次数 |
| AA-TEST-004 | P2 | 精确渲染结论 | 对最终包重做受影响的真实材质对比；保留条件、差异像素和非零差结论，未测设备写未执行 |

先执行定向自动测试并完成全部候选修改，再集中使用一个 Editor 会话验证。不得为文档交付重复启动 Editor。

## 4. 观测与交付任务

| 任务 | 优先级 | 内容 | 验收标准 |
| --- | --- | --- | --- |
| AA-OBS-001 | P2 | 记录实际加载的 URP 能力和包标识 | 证据包含包 SHA、Target 模式、材质覆盖状态以及生成代码 Blend/AlphaModulate；枚举存在不冒充完整行为验证 |
| AA-OBS-002 | P2 | 分离生产者 report 和下游验收 | 保留原三件套绑定，另记录消费者、重载、编译、画布、渲染证据；有未执行/不匹配时不将整体成功置真 |

## 5. 合并/发布门禁

- [ ] 两项 P1 修复及反例回归通过。
- [ ] 原包 FXAA 扩展保留，或另有明确迁移依据。
- [ ] 定向测试和 diff 检查通过。
- [ ] 受影响 Editor 路径验证完成，未执行平台明确披露。
- [ ] 不将样本近似一致表述成全参数、全平台逐像素全等。

## 6. 未映射项

无。所有发现均已映射；其余缺口仅作为相关修复后的验证任务，不扩大为无关重构。

## 7. 本次修复与实测回执（2026-09-14）

- AA-OPT-001 已修复：Python 拒绝完整非法组合；C# 在编辑前检查合并后的 Target 状态；URP 生成路径也拒绝直接从 Inspector 绕入的非法组合。可复用 Editor 探针为 SGCLI `tests/native/probes/exact_blend_audit.cs`。
- Editor 探针 10/10 通过：Unlit/Lit 各验证创建非法组合、开启覆盖、切换 Blend、两个合法组合切换。四个拒绝编辑用例的序列化内容均保持不变。所有对象仅在内存创建，不写用户图。
- AA-OPT-002 已修复：恢复普通 Multiply 的 fail_unproved 认证及 ASECLI 折叠前上游函数保护。局部变量调制反例拒绝；精确模式的相同函数仍可认证。本次实际 spec/report/receipt 重新消费通过，semantic_certified=true，三件套原字节未变。
- AA-OPT-003 已修复：新增 SGCLI `scripts/build_exact_blend_urp.py`，从完整项目 LFS 原包构建，未知源形状拒绝，输出不得覆盖已有文件。新包逐项核对 2,945 个归档条目，名称/类型相同，仅 UniversalTarget.cs 内容变化。FXAA 及原 meta 均保留；真实 Editor 已能解析 RenderAntiAliasing 类型。
- 新包 SHA-256：`16177f39c34916dd4a9ddfd977eab1bb0d10918ef16b652d923845c84aaf059b`；实际 Editor PackageCache：`com.unity.render-pipelines.universal@462d79d17c5a`。
- 回滚副本：`/tmp/urp-audit-fix.TFSWQS/previous-urp.tgz`；manifest/lock 写前副本同目录。本次修复结束两份依赖配置与写前副本 SHA 相同，未覆盖其他依赖变更。
- 自动验证：SGCLI `tests/native` + `tests/test_complete.py` 为 423 passed, 1 skipped；ASECLI 三个相关测试文件为 57 passed。三个工作区 diff 检查通过。
- 最终 Shader Graph 的 `sg validate --editor` 返回 ok=true；原 SHA `664a788b15198282ba55441150b2021c92cd8bbb78b001c63cb6e51f448ce5cf` 保持。生成代码检查：精确 Blend、无隐式 AlphaModulate、保留 float 表达式、隐藏纹理是材质属性，均通过。
- 新包下重新比较 Night/Day × 时间 0、1.2、3.62 × 透明量 0、0.5、1，共 18 组。Alpha 全部零差，RGB 17 组零差；Night/3.62/1 的 (209,133) 仍为源 RGBA(6,13,22,255)、目标 RGBA(6,12,22,255)。没有新增差异，不声明逐像素完全等价。
- 边界：本轮未重新执行 SG→ASE 真实创建、画布视觉验收或目标设备测试；反向转换相关 Python 回归通过。三项发现的实现修复和对应回归已完成，不将这些额外证据缺口标为通过。
- 原生产者 report/receipt 保留原样，下游本轮证据记录在此，未将 conversion_success/visual_equivalent 人工改真。未提交、推送或发布。

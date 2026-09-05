# 对抗性审计优化计划：MZGUI-compatible GUI 对接与跨环境迁移

> 生成时间：2026-09-05 16:09:45 CST
> 项目根目录：`/Users/long/GitHub/ASECLI`
> 关联报告：`docs/adversarial-audits/2026-09-05-160945-audit-report.md`

## 1. 执行摘要

- 审计对象：原生/fallback 同名 provider、ASE Editor authoring、保存事务、旧数据升级和跨工程迁移。
- Findings 统计：P0=0 P1=2 P2=3 P3=0。
- 发布建议：代码与自动门禁已解除阻塞；完整双环境 UI 验收仍阻塞发布声明。
- 建议执行顺序：AA-OPT-001 → AA-OPT-002 → AA-OPT-003 → AA-OPT-004 → AA-OPT-005 → 双环境真实 Editor 门禁。

## 2. 修复与加固任务

| 任务 ID | 优先级 | 来源 Finding | 内容 | 验收标准 | 依赖 | 风险/回滚 |
| --- | --- | --- | --- | --- | --- | --- |
| AA-OPT-001 | P1 | AA-DATA-001 | **已实现** canonical authoring store 与 capability-checked reconciliation；仅在唯一非 fallback 原生 provider 和完整字段/方法均存在时，把 Custom Attributes 搬入 `m_mzguiAttribs`/`m_selectedMzguiAttribs` 并删除旧存储 | 自动契约和真实原生类型探测通过；双环境保存重开 UI 待验 | 真实无 MZGUI 与原生 MZGUI 工程 | 未知字段、重复 provider、重复属性均失败关闭 |
| AA-OPT-002 | P1 | AA-COR-001 | **已实现** Apply 预检、节点/Master/Shader 磁盘快照、单 Undo group、异常捕获和回滚日志 | 源码契约与真实 Editor 内存编译通过；注入式 Editor 失败路径待真实 harness | AA-OPT-001 的存储契约 | 保存异常恢复内存及 Shader 文件，回滚失败写 Console |
| AA-OPT-003 | P2 | AA-COMPAT-001 | **已实现** `ASECLI*` 旧别名读取、canonical 优先、冲突拒绝、写入只保留 `*Mzgui` | 自动回归通过 | AA-OPT-002 | 不批量扫描用户 Shader；仅触碰选中节点 |
| AA-OPT-004 | P2 | AA-OPS-001 | **已实现** `fallback_external` 与 V2 provider 数组；V1 继续兼容 | 外部 fallback、双 provider、项目路径和真实 native assembly 探测通过 | — | 模糊状态 `would_write=false` |
| AA-OPT-005 | P2 | AA-OPS-002 | **已实现** 默认 dry-run handoff；已知 fallback 原子备份后换成不声明 `MZGUI.MZGUI` 的 authoring-only bridge，复验失败可恢复 | 临时工程 dry-run/成功/失败回滚通过；真实 native 工程未执行写入 | AA-OPT-001、AA-OPT-004 | 只接受已知哈希、唯一 native+fallback 和 native authoring capability |

## 3. 测试补强任务

| 任务 ID | 优先级 | 覆盖缺口 | 内容 | 验收标准 |
| --- | --- | --- | --- | --- |
| AA-TEST-001 | P1 | fallback 保存重开未实测 | 在隔离无 MZGUI Unity/Tuanjie 工程通过真实 UI 或受控 Editor harness 完成三项编辑、保存、退出、新进程重开 | 属性文本、Custom Editor、节点 Custom Attributes、编译 Shader 四层一致且 Console 0 error |
| AA-TEST-002 | P1 | 跨 provider authoring 未实测 | 把 AA-TEST-001 的同一 Shader 复制到真实原生 MZGUI 工程，读取原生 Toggle/文本，再保存和新进程重开 | 无改名、无重复 Attribute、Inspector 和原生 authoring UI 同义 |
| AA-TEST-003 | P1 | Apply 失败路径未测 | 建立可注入反射能力与 Save 异常的 C# 测试接口，逐步验证回滚 | 三个失败点均零残留；异常转换为结构化错误而非打断 OnGUI |
| AA-TEST-004 | P2 | provider 枚举不完整 | 覆盖固定 fallback、外部 fallback、原生源码、原生 DLL、双程序集同名类型和静态漏检后 runtime 命中 | 状态机与预期表逐项相等，所有冲突路径 `would_write=false` |
| AA-TEST-005 | P2 | 旧属性 Editor 迁移未测 | 为三种旧名、混合新旧名、重复同名建立 authoring 回归 | Load/Apply 后 canonical 唯一且文本不重复 |

## 4. 观测与运维任务

| 任务 ID | 优先级 | 内容 | 验收标准 |
| --- | --- | --- | --- |
| AA-OBS-001 | P2 | `gui-support` 输出全部同名 provider 的 assembly、source/target 证据、native/fallback 分类和冲突原因 | 单 provider、外部 fallback、multiple 三种结果足以定位要移除的确切资产 |
| AA-OBS-002 | P2 | EditorWindow 将 Apply 阶段、失败原因、回滚结果写入 Console，并在窗口保留最后一次结果 | notification 消失后仍能确认“未写入/已回滚/需手工恢复”之一 |

## 5. 发布门禁

- [x] 所有 P0 任务完成（无 P0）。
- [x] 所有 P1 代码任务完成，未完成的双环境 UI 风险已保留。
- [ ] AA-TEST-001/002/003 的真实或可控 Editor 回归通过。
- [x] provider 枚举与 handoff 对未知文件保持失败关闭。
- [x] 残留风险已在本计划披露：AA-TEST-001/002/003 尚缺隔离 Editor UI/harness。

## 7. 本轮执行证据

- 自动回归：`uv run pytest -q` → `258 passed, 3 skipped`。
- 治理/回归目录/供应链/补丁格式：全部通过。
- 真实 Editor 只读探测：`FlymeAuto3.0Test@06f8d75a5e500169`，Unity `2022.3.62t13`；唯一 provider 为 `MZGUI.MZGUI` / assembly `MZGUI`，`native_authoring_capable=true`，固定 fallback 目标不存在且 `would_write=false`。
- 真实 Editor 内存编译：authoring-only bridge 为 0 error / 0 warning；完整 fallback 为 0 error，因该 Editor 已加载同名旧 `ASECLIMaterialGUI` 出现 1 条类型冲突 warning，因此未向该工程写入。

## 6. 未映射项

- 无。全部 P2 finding 已映射到修复任务；当前未授权接受任何 finding。

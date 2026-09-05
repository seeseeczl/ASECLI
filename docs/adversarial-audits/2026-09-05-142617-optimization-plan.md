# 对抗性审计优化计划：自定义 GUI 在打开/保存后的持久化链路

> 生成时间：2026-09-05 14:26:17 CST
> 项目根目录：`/Users/long/GitHub/ASECLI`
> 关联报告：`docs/adversarial-audits/2026-09-05-142617-audit-report.md`

## 1. 执行摘要

- 审计对象：ASECLI 自定义材质 GUI 的保存、重编译、旧 MZGUI 兼容与 Inspector provider 选择。
- Findings 统计：P0=0 P1=2 P2=1 P3=0。
- 发布建议：阻塞；先修复数据持久化，再宣称 GUI 能跨 ASE 保存保留。
- 建议执行顺序：先建立可恢复真相源（AA-OPT-001），随后修正 CLI 快照范围（AA-OPT-002），最后处理属性身份迁移/失败诊断（AA-OPT-003），并以真实 Editor 矩阵验收。

## 2. 修复与加固任务

| 任务 ID | 优先级 | 来源 Finding | 内容 | 验收标准 | 依赖 | 风险/回滚 |
| --- | --- | --- | --- | --- | --- | --- |
| AA-OPT-001 | P1 | AA-DATA-001 | 引入以 Shader GUID 绑定的 GUI manifest，保存 provider、稳定 PropertyNode ID、属性名、显示名、折叠/Tooltip/HelpBox（新旧协议）。`custom-gui` 与 `recompile` 使用该 manifest；在 Editor 保存/导入后恢复图与编译区。 | 真实 Unity/Tuanjie：新/旧/混合标记各一份 Shader，ASE 打开保存、进程关闭重开后，CustomEditor、图尾部和编译区三方与 manifest 一致。 | 需确认 ASE 保存/导入回调时机 | manifest 写失败时拒绝声明成功并保留原 Shader 与 manifest；可删除新增 hook/manifest 回滚，不修改用户属性值。 |
| AA-OPT-002 | P1 | AA-DATA-002 | 改造 `snapshot_recompile_metadata()`：CustomEditor、legacy 与 ASECLI 属性分开快照；只要存在任何受管状态即返回快照。恢复后显式校验 graph/compiled editor、属性数及属性值。 | editor-only、legacy-only、mixed 三种 mock ASE 保存均返回 `metadata_restored`/`editor_restored`，恢复后检查完全一致；无受管状态才返回 `None`。 | AA-OPT-001 的数据模型 | 先保持当前 `.bak` 语义；新检查失败返回 `GUI_PERSISTENCE_ERROR`，不把未验证结果标为成功。 |
| AA-OPT-003 | P2 | AA-FAIL-003 | 使用 PropertyNode ID + 名称双键恢复；定义改名、删除、重复名的迁移策略与专用错误。保存后缺少匹配项时保留 manifest 和一份诊断 JSON。 | `_BaseColor → _BaseColour` 可被显式迁移或稳定报出未恢复项；删除/重复名不误绑任何其他属性；原始快照仍可恢复。 | AA-OPT-001 | 默认不按近似名称自动绑定；出现歧义仅报告，不写错误属性。 |

## 3. 测试补强任务

| 任务 ID | 优先级 | 覆盖缺口 | 内容 | 验收标准 |
| --- | --- | --- | --- | --- |
| AA-TEST-001 | P1 | 快照门槛假覆盖 | 为 editor-only、legacy-only、mixed metadata 增加单元测试；断言 snapshot 不为 `None` 且恢复后的两处 CustomEditor 一致。 | 当前已验证反例在修复前失败、修复后通过。 |
| AA-TEST-002 | P1 | 没有“已有 Shader 再保存”实机回归 | 新增隔离 Editor E2E：创建受管 Shader → 打开 ASE → `SaveToDisk` → 关闭进程 → 新进程加载并核对 manifest/图/编译区/Inspector metadata。 | 覆盖 ASE 1.9.6.2 与发布支持的每个 Unity/Tuanjie 版本；Console 无 C#/Shader error。 |
| AA-TEST-003 | P2 | 属性身份变化 | 覆盖改名、删除、重复名与外部并发改写；确保不会把元数据写到错误属性，失败输出完整诊断。 | 所有歧义场景零错误写入、manifest 不丢失。 |

## 4. 观测与运维任务

| 任务 ID | 优先级 | 内容 | 验收标准 |
| --- | --- | --- | --- |
| AA-OBS-001 | P2 | `custom-gui` inspect 输出 manifest 状态、graph/compiled/manifest 的 provider 与摘要 hash；`recompile` 输出恢复来源和未恢复项。 | 用户可用单次 JSON 比较保存前后哪一层被覆盖，错误不再只表现为默认 Inspector。 |
| AA-OBS-002 | P2 | 在 ASECLI ShaderGUI 中，当检测到 graph/compiled/manifest 不一致时显示非阻塞但醒目的修复提示与 CLI 命令。 | Inspector 不会静默伪装成已配置；提示不改写资产。 |

## 5. 发布门禁

- [ ] AA-OPT-001 和 AA-OPT-002 完成并经代码审阅。
- [ ] 新/旧/混合标记的真实 Editor “打开—保存—重开”回归通过。
- [ ] 属性改名/删除/重复名的恢复策略通过 AA-TEST-003。
- [ ] `custom-gui inspect` 可诊断 graph、compiled 与 manifest 任意一层不一致。
- [ ] 保留 MZGUI 共存 E2E；不把“工程中同时安装两套 GUI”误判为本问题根因。

## 6. 未映射项（如有）

- 无。三个 P1/P2 finding 均有对应修复任务。

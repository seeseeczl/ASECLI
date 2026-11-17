# 优化计划 — 为 ASECLI 补齐「shader 管线切换」能力

- 时间戳：2026-10-14-163548
- 配套审计报告：`docs/adversarial-audits/2026-10-14-163548-audit-report.md`
- 结论前提：ASECLI 当前**不具备**管线切换能力（详见报告 §1）；本计划不是「修 bug」，而是「若要补齐，按什么顺序补才安全」
- 适用范围：本计划全部任务只修改 ASECLI 本仓；HMIRP 模板等外部事实由用户另行提供（见 §0 前置门禁）

---

## 0. 前置门禁（未满足则全部任务不得开工）

本次审计最重要的结论是**顺序问题**：先写端口表、后拿真实模板，会制造出「通过全部门禁但语义错误」的图——比现在的不支持更危险。

因此以下三项为**硬前置**，缺一不可：

| 编号 | 前置条件 | 为什么不能省 | 状态 |
| --- | --- | --- | --- |
| PRE-1 | 拿到**真实 HMIRP 模板**（ASE 模板资源 + 其 GUID），并能在一个隔离工程中真实打开 | AA-TARGET-006：端口语义无法从代码推导，只能实测 | ⬜ 待用户提供 |
| PRE-2 | 在编辑器内**实测**该模板的 Master 输入端口序号 ↔ 语义对照表（0..N 逐个连一根常数线，观察 ASE 的端口标签与生成代码） | 这是唯一能替代当前 `_URP_UNLIT_MASTER_INPUTS` 手写表的证据来源 | ⬜ 待用户提供 |
| PRE-3 | 确认 HMIRP 在 ASE 里对应的 **Pass 集合**与模板选项标签（Surface/Blend/Two Sided/…） | `decoder.py` 与 `render_settings.py` 都按标签字符串匹配，标签不同则解析静默失败 | ⬜ 待用户提供 |

> **明确反对**：在没有 PRE-1/PRE-2 的情况下直接新增一个 HMIRP 的 GUID 常量并猜测端口号。按 AA-TARGET-006，`expected_manifest` 只做自反比较，猜错的端口表会一路通过 create → validate → recompile 而不被发现。

---

## 1. 任务总表

| 任务 ID | 标题 | 优先级 | 对应 Finding | 依赖 | 类型 |
| --- | --- | --- | --- | --- | --- |
| AA-OPT-010 | `set-field` 保护模板身份字段，阻断「批量改坏管线」路径 | **P1** | AA-TARGET-009 | 无（可立即做） | 加固（**建议最先做**） |
| AA-OPT-001 | 建立单一「模板注册表」，收拢 4 处 GUID 字面量与 2 份端口表 | P1 | AA-TARGET-001 / 004 / 005 | 无（可立即做） | 重构（行为不变） |
| AA-OPT-002 | 模板合法性改为集中白名单校验，去掉「副作用式」把关 | P1 | AA-TARGET-004 / 005 | AA-OPT-001 | 加固 |
| AA-OPT-003 | 让 spec/manifest 携带声明式端口类型，产出可独立核查的连接证据 | P1 | AA-TARGET-006 | AA-OPT-001 | 契约扩展 |
| AA-OPT-004 | `export-sg` 模板准入与写路径对齐（拒绝 ≠ 仅诊断） | P2 | AA-TARGET-002 / 008 | AA-OPT-001 | 加固 |
| AA-OPT-005 | 端口类型兼容性从「数值族一律放行」改为显式提升表 | P2 | AA-TARGET-003 | AA-OPT-003 | 加固 |
| AA-OPT-006 | 为「管线」引入一等概念（pipeline 字段 + 注册表） | P3 | AA-TARGET-001 | AA-OPT-001/002、PRE-1~3 | 特性 |
| AA-OPT-007 | 跨模块端口表一致性测试（防两份表漂移） | P2 | AA-TARGET-006 | AA-OPT-001 | 测试补强 |
| AA-OPT-008 | 「非本模板资产」的行为矩阵回归测试 | P2 | AA-TARGET-002/004/005/008 | AA-OPT-002/004 | 测试补强 |
| AA-OPT-009 | 补齐 HMIRP 模板端到端验收（真机） | P1 | AA-TARGET-006/007 | 全部 + PRE-1~3 | 验收 |

---

## 2. 任务详述

### AA-OPT-010 — `set-field` 保护模板身份字段（**建议最先做**）

**问题**：AA-TARGET-009（P1，已实测）。`set_node_field` 只保护字段 0-2，field 13（模板 GUID）可被任意改写；改完后 `validate` 报 0 error，`export-sg` 只诊断不阻断，并返回 URP Unlit 语义的 target。用户提出的「批量改管线」诉求正好会走进这条路。

**做法**（三选一或组合，按侵入性递增）：

- **A（最小，推荐先做）**：把 field 13 加入保护集合，与 0-2 同级。但这会让「合法地改模板」也不可能——需确认是否真的需要该能力。
- **B（推荐最终形态）**：field 13 改为**需要显式确认**才能写：新增 `--allow-template-identity-change` 之类的显式开关，默认拒绝；一旦使用，命令返回中明确标记 `template_identity_changed: true`，并在写后自动跑一次"目标模板是否在注册表中"的校验。
- **C（配合 AA-OPT-002）**：任何写操作后（不限于 set-field），若 Master 的 f13 不在注册表内，则**拒绝写入**（`--write` 时失败关闭）。

**关键约束**：不要只是"允许改但不报错"。本发现的核心危害是**静默**——用户会以为批量改 GUID 就完成了管线切换。

**验收**（必须先失败后通过）：
- 现有行为：`set-field --field 13` + `--write` → 成功、`validate` 0 error（**这就是当前 bug**）
- 修复后：默认拒绝，错误信息说明"这会改变模板身份，可能导致图语义失效"
- 显式开关下允许，但返回值带 `template_identity_changed` 标记
- 新增测试：改成一个不在注册表中的 GUID 后 `validate` **必须**报 error（当前为 0 error）

**回滚**：独立 commit；若影响合法流程，可只保留"写后校验"部分（方案 C）而放开写入。

**同时建议**：在 README 的 `set-field` 说明处补一句它属于低层原始写入、会绕过语义校验。现有 README 对 `set-field` 的风险描述不足。

---

### AA-OPT-001 — 建立单一「模板注册表」

**问题**：GUID `2992e84f91cbeb14eab234972e07ea9d` 以裸字面量散落在 4 个模块（`_editor_port_contract.py:12`、`render_settings.py:18`、`compiled_metadata.py:22`、`sg_export/model.py:19`）；Master 端口语义以两份互不相干的手写表存在（`_URP_UNLIT_MASTER_INPUTS` 与 `MASTER_OUTPUTS`）。

**做法**：新增 `src/asecli/core/template_registry.py`（或 `bridge/`，取决于放置后的依赖方向），定义单一数据源：

```python
# 示意，非最终代码
TEMPLATES = {
    "2992e84f91cbeb14eab234972e07ea9d": TemplateContract(
        pipeline="urp",
        model="Unlit",
        master_inputs={0: "FLOAT3", 1: "FLOAT3", 2: "FLOAT3", 3: "FLOAT",
                       4: "FLOAT", 5: "FLOAT3", 6: "FLOAT3", 7: "FLOAT"},
        master_input_semantics={0: "BakedGI", 2: "BaseColor", 3: "Alpha", ...},
        render_settings=OPTIONS,                 # 现 render_settings.OPTIONS
        compiled_only_properties=frozenset({...}),  # 现 compiled_metadata 内字典
        passes=URP_UNLIT_PASSES,
    ),
}
```

`master_input_semantics` 是关键：它让**同一份数据**同时服务写路径（`_editor_port_contract`）与读路径（`sg_export` 的 `MASTER_OUTPUTS`），从根本上消除两份表漂移的可能。

**验收**：
- 全仓 `grep -c "2992e84f91cbeb14eab234972e07ea9d"` 在生产代码中结果为 **1**（仅注册表内）
- `pytest -q` 全绿（重构不改行为）
- `git diff --check` 通过

**回滚**：纯重构，`git revert` 单个 commit 即可。

---

### AA-OPT-002 — 模板合法性集中白名单校验

**问题**：AA-TARGET-004 实测显示，未知 GUID 被拒绝是**偶然完备**——靠「有 master 连接」和「恰好传了 settings」两条副作用挡住。零连接图存在缺口。AA-TARGET-005 进一步指出 `editor_create.py:186` 只做自反比较。

**做法**：
1. 在 `_parse_template()`（`_editor_spec_validation.py:93`）内，解析完 guid 后**直接**查注册表；不在注册表内 → `SpecError`。不再依赖后续端口校验。
2. `editor_create._validate_result()` 增加一条：响应 GUID 必须 ∈ 注册表，而不是只等于请求 GUID。保留自反比较（防篡改），**追加**白名单校验。

**验收**（新增测试，必须能复现当前的缺口）：
- 零连接 + 未知 GUID → `SpecError`（**当前会通过**，修后必须拒绝——此用例应先失败）
- 有 settings + 未知 GUID → `SpecError`
- 合法 GUID + 零连接 → 通过

**回滚**：独立 commit；若误拒合法模板，回退该校验块不影响其他任务。

---

### AA-OPT-003 — 声明式端口类型与可独立核查的连接证据

**问题**：AA-TARGET-006 是本次审计的**核心发现**。`expected_manifest` 只证明「回读 == 请求」，不证明「端口语义正确」。「保证连接正确」在当前架构下是人肉保证。

**做法**（分两步，避免一次改动过大）：
1. **先做证据**：在 `EditorGraphSpec` 增加可选的 `master_port_contract` 声明（端口号 → 语义名 + 类型），由注册表填充，写入 `expected_manifest()`。创建回执校验时，要求 ASE 侧回读的端口连接**与声明的语义名对应**，而不只是端口号相同。
2. **再做校验**：`validate_connections()` 对 destination 为 `master` 的连接，同时校验 `(port → 类型)` 与 `(port → 语义名)` 两项。

**验收**：
- 新增测试：同一端口号在两份不同端口语义的注册表条目下，校验结果不同 → 证明校验真的依赖语义而非仅仅端口号
- 现有 URP Unlit 图全部仍通过（语义名与端口号在当前模板下一一对应）

**风险与缓解**：这是本计划中**唯一触及公共契约**的任务。缓解：`master_port_contract` 设为可选字段，先加性扩展，不改动现有 spec 的必填项；并同步更新 `contracts/editor-graph-spec.v3.schema.json` 与 README §JSON 契约。

**回滚**：新增可选字段 + 新增校验分支，回滚时旧 spec 仍可解析。

---

### AA-OPT-004 — `export-sg` 模板准入与写路径对齐

**问题**：AA-TARGET-002/008。`decoder.py:185-187` 检测到非 URP 模板后只追加诊断、继续构建候选图，按 URP 选项标签去解析未知模板的字段（`decoder.py:199` 起），可能得到「看起来合法的错误 target」。

**做法**（二选一，推荐 A）：

- **方案 A（推荐）**：在 `build_candidate()` 中，当 `TARGET_UNSUPPORTED` 被追加后**立即短路**——写出包含该诊断的失败报告并抛 `ExportError`，不再构建候选图。与写路径的失败关闭语义一致。
- **方案 B**：保留继续构建，但把 `TARGET_UNSUPPORTED` 加入 `report_semantics._SEMANTIC_CODES`，让它以显式语义降级的形式出现，并在报告顶部标记为阻断级，避免人工误读为「部分成功」。

**验收**：
- 构造模板 GUID ≠ URP Unlit 的 ASE fixture → `export-sg` 返回 `SG_EXPORT_BLOCKED`，且**不写** spec 文件（只写失败 report）
- 报告内 `target_mapping` 不得包含任何基于 URP 标签解析出的值

**回滚**：短路逻辑加条件开关即可；方案 A 与 B 可互换。

---

### AA-OPT-005 — 端口类型兼容性改为显式提升表

**问题**：AA-TARGET-003。`_compatible_port_types` 对 `_NUMERIC_TYPES` 内任意两类型一律返回 True（实测 `FLOAT → master:2(FLOAT3)` 被接受）。

**做法**：把「数值族一律放行」改为**显式允许的提升集合**，例如：

```python
_ALLOWED_WIDENING = {
    ("FLOAT", "FLOAT2"), ("FLOAT", "FLOAT3"), ("FLOAT", "FLOAT4"),
    ("FLOAT2", "FLOAT3"), ("FLOAT3", "FLOAT4"),
    # 反向（窄化）默认不允许，除非该端口在注册表中显式声明允许
}
```

每一项的来源必须是**实测证据**（ASE 在该端口确实做隐式提升），而不是推测。

**验收**：
- 现有 E2E fixture 全部仍通过（证明没有误拒真实用法）
- 新增测试：`FLOAT4x4 → FLOAT` 被拒；注册表声明允许的窄化被接受

**风险**：可能误拒当前依赖隐式提升的真实图。缓解：先在全量 fixture 上跑一遍，把所有「当前能过、改后不过」的用例逐个人工确认为「真实 ASE 行为」后再放行。

**回滚**：提升表是纯数据，回退为旧的「数值族一律 True」即恢复原行为。

---

### AA-OPT-006 — 为「管线」引入一等概念

**前置**：AA-OPT-001/002 完成 + PRE-1~3 满足。**在此之前不得开工。**

**做法**：
1. `TemplateContract` 增加 `pipeline` 字段（`"urp"` / `"hmirp"` / …）。
2. 新增 CLI 能力（建议 `asecli pipelines` 只读命令）列出当前已认证的管线与模板，让能力和边界对用户可见。
3. HMIRP 契约条目**由实测数据填充**（PRE-2/PRE-3），并配套登记真实机证据文档（对齐 `docs/03-quality/evidence/REG-0053/README.md` 的格式与诚实边界写法）。

**验收**：
- `asecli pipelines` 输出与注册表一致
- HMIRP 条目存在真实 Editor 证据，且证据文档明确区分「结构通过」与「画面通过」

**回滚**：新增注册表条目 + 只读命令，删除条目即回到单管线状态。

---

### AA-OPT-007 — 跨模块端口表一致性测试

**问题**：AA-TARGET-006 指出两份端口表（`_URP_UNLIT_MASTER_INPUTS` 与 `MASTER_OUTPUTS`）数值一致但无交叉校验。这是「沉默的定时炸弹」。

**做法**：新增测试，断言注册表内 `master_inputs` 的键集合与 `master_input_semantics` 的键集合完全一致，且语义名与 `MASTER_OUTPUTS` 的 `SurfaceDescription.*` 后缀一一对应。

**验收**：故意改错任一份 → 测试失败。

**回滚**：纯测试，无行为影响。

---

### AA-OPT-008 — 「非本模板资产」行为矩阵回归测试

**做法**：把本次审计的离线探针固化为参数化测试，覆盖 `{未知 GUID, 已知 GUID} × {有 settings, 无 settings} × {有 master 连接, 零连接} × {create 路径, export-sg 路径}` 的行为矩阵，逐格断言期望结果（拒绝 / 通过 / 阻断报告）。

**验收**：矩阵中每一格的期望值都有注释说明依据（引用具体文件行）。

**回滚**：纯测试。

---

### AA-OPT-009 — HMIRP 端到端验收（真机）

**前置**：PRE-1~3 + AA-OPT-001~008。

**做法**：按 AGENTS.md「Editor 与截图按需执行」与「同一验证阶段最多进行一次正常 Editor 启动」：

1. 静态 + 自动测试全部先完成
2. **一个** Editor 会话内集中验证：HMIRP 模板创建 → 保存 → 重载 → `validate` → `recompile` → 材质 Inspector → 渲染画面
3. 证据落盘到 `docs/03-quality/evidence/<REG-id>/README.md`，明确写出「未验证项」

**验收**：验收内容必须包含报告 AA-TARGET-006 所要求的**端口语义独立核查**——即不只证明「连上了」，还要证明「连到了正确的语义端口」。

---

## 3. 执行顺序建议

```
阶段零（立即，止血，不依赖任何前置）
  AA-OPT-010  set-field 保护模板身份  ← 唯一一条"正在造成实际损坏风险"的修复

阶段一（可立即开始，不需 HMIRP）
  AA-OPT-001  注册表收拢          ← 其余一切的基础
  AA-OPT-007  一致性测试          （与 001 同批）
  AA-OPT-002  白名单校验
  AA-OPT-008  行为矩阵测试
  AA-OPT-004  export-sg 准入对齐

阶段二（契约扩展）
  AA-OPT-003  端口语义证据        ← 核心，「保证连接正确」的关键
  AA-OPT-005  提升表

阶段三（等 PRE-1~3）
  AA-OPT-006  管线一等概念 + HMIRP 条目
  AA-OPT-009  真机端到端验收
```

**关键判断**：阶段一、二**完全不需要 HMIRP 模板**即可完成，且它们的价值独立于管线切换——它们修的是「URP Unlit 单模板下的证据链薄弱」。建议先做这两阶段，等真实模板到位后阶段三才动手。

---

## 4. 验收与回滚总则

- **验证等级**：阶段一/二属局部 Python 修改，按 AGENTS.md 走「快速」等级（定向测试 + `git diff --check`）；AA-OPT-003 触及公共契约，升级为「标准」等级并跑一次全量 `pytest`
- **回滚粒度**：每个 AA-OPT 独立 commit，可单独 revert
- **不修改的业务边界**：本计划全部任务不触及 `sg_export` 的语义映射算法本身、不改动已有 URP Unlit 的认证结论
- **跨仓边界**：不修改 SGCLI；若需要 SGCLI 侧配合（例如 HMIRP 的 target 表达），只记录协议需求，由用户另行授权

---

## 5. 本计划的诚实边界

- 阶段三完全依赖外部提供的 HMIRP 事实（模板 GUID、端口语义、Pass 集合），本计划**无法**自行推进
- AA-OPT-005 的提升表需要真实 ASE 行为证据，本次无测试环境，未采集
- AA-OPT-003 的契约扩展形式（字段名、位置）建议在开工前由一次设计评审确认，本计划只给出方向
- 本计划不声称「补齐后即可无损切换任意管线」。按审计报告 §1，管线间的语义鸿沟（尤其是 Lit/Lighting 输出）远超端口映射范围，那属于方案层面的问题，应另行评估，不在本计划范围内

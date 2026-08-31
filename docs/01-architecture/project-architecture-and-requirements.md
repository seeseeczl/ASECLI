---
id: ARCH-REQ-0001
type: project-architecture-and-requirements
status: 已确认
version: 1.0.0
created_at: 2026-08-31T23:25:00+08:00
owner: long
related: [PRJ-ASECLI, docs/first-principles/2026-08-31-231401-optimization-plan.md]
supersedes: 无（首次启动）
evidence: [ASE 源码分析 464 个 C# 文件; Codely CLI 与桥接包已安装检测; 第一性原理计划书]
kickoff_completion: complete
---

# 项目架构与需求总纲 — AseCLI

## 启动输入与假设

| 项目启动问卷项 | 答案 | 状态（已确认/假设/未决/风险） |
| --- | --- | --- |
| 项目目标 | 让 AI Agent 通过自然语言创建/修改 ASE Shader 文件并触发编译 | 已确认 |
| 目标用户与角色 | 用户本人（long）：Unity/团结引擎开发者；直接使用者是 AI Agent（Codex/Claude Code/Codely） | 已确认 |
| 首个场景 / MVP | 用户说"给这个 shader 加一个可调描边"，Agent 完成设计节点图、连线、写文件、校验、触发编译 | 已确认 |
| 产品形态 | 本地 Python CLI（`asecli`）+ Agent 技能文档 + C# Unity 桥接脚本；无 UI | 已确认 |
| 数据与集成 | 读写用户指定 .shader/.asset；调用本机 Codely CLI 与团结引擎；不联网、不接触凭证 | 已确认 |
| 约束与风险 | 编译必须经 Unity；目标引擎是团结引擎；schema 覆盖 400+ 节点存在遗漏风险 | 已确认 |
| 设计来源 | 第一性原理计划书方案 B + ASE 源码静态分析 | 已确认 |
| 项目根目录与写入授权 | /Users/long/GitHub/AseCLI，用户已授权创建基线文档 | 已确认 |

## 目标、范围与成功标准

- 要解决的问题：ASE 节点图文本格式复杂（400+ 节点参数 schema 各异），Agent 直接手写易错且无法触发 Unity 编译，导致"AI 替用户做 shader"不可靠。
- 目标用户与价值：用户只提需求与验收效果；Agent 负责设计节点图、连线、设参、写文件、编译的全过程。
- MVP / 首个核心垂直切片：对项目内一个已有 ASE shader，Agent 完成"改一个属性值 → 校验 → 触发重新编译 → HLSL 更新"全链路。
- 本期包含：FR-0001～FR-0007；三链路（改属性/改图/创建+编译）全部可用。
- 本期不包含：CLI-Anything Hub 发布（ADR-0004 后置）、可视化界面、ASE 功能替代、通用 schema 覆盖 100% 节点（未知节点 passthrough）。
- 成功指标：REG-0001～REG-0011 全绿；Agent 端到端全流程一次通过（REG-0010）；千节点文件单命令 <1s（REG-0011）。

## 需求整理与验收

| ID | 类型 | 需求/场景 | 关键验收 | OpenSpec/REG 链接 | 状态 |
| --- | --- | --- | --- | --- | --- |
| FR-0001 | 功能 | 解析 ASE 图数据（.shader 与 .asset m_functionInfo），输出结构化模型与 JSON | 真实样本 roundtrip 逐字节一致 | REG-0001 REG-0011 | 已确认 |
| FR-0002 | 功能 | 图数据修改：set-prop / add-node / connect / remove，写回后仅目标字段变化 | 最小差异断言通过；schema 抽查 10 种节点一致 | REG-0002 REG-0009 | 已确认 |
| FR-0003 | 功能 | 校验图完整性（悬空引用/断线）与 CHKSM 重算修复 | 破坏样本被检出；修复后恢复 | REG-0003 REG-0004 | 已确认 |
| FR-0004 | 功能 | 经 Codely 桥触发 Unity 内 ASE 重新编译指定 shader | 触发后 HLSL 变更且 CHKSM 更新 | REG-0005 REG-0008 | 已确认 |
| FR-0005 | 功能 | 经桥从模板创建新 shader | Unity 中打开正常 | REG-0006 REG-0008 | 已确认 |
| FR-0006 | 功能 | Agent 技能文档 SKILL.md：格式说明+三链路手册+错误处理 | Agent 按文档完成一次全流程 | REG-0010 | 已确认 |
| FR-0007 | 功能 | CLI JSON 输出契约：stdout 恒为合法 JSON（含 ok 字段），统一错误码 | 所有子命令契约测试通过 | REG-0007 | 已确认 |
| NFR-0001 | 非功能 | Roundtrip 保真：未修改字段逐字节不变 | roundtrip 测试断言 | REG-0001 | 已确认 |
| NFR-0002 | 非功能 | 未知节点 passthrough：schema 未覆盖时保真透传 | 混合样本测试 | REG-0002 | 已确认 |
| NFR-0003 | 非功能 | 性能：千节点级文件单命令 <1s | perf 基线测试 | REG-0011 | 已确认 |
| NFR-0004 | 非功能 | ASE 版本容忍：记录 Version 字段，未知新参数保持原样 | 版本混合样本测试 | REG-0002 | 已确认 |

## 推荐技术路径

### 主推荐

- 架构形态：模块化单体 Python CLI（六模块）+ C# MenuItem 桥接脚本 + Agent 技能文档
- 运行时/语言：Python >=3.10（uv 管理）；C# 仅一个编辑器桥接文件
- 前端/UI（如适用）：无 UI；stdout JSON 即 Agent 契约界面
- 后端/API（如适用）：不适用（本地 CLI，无长运行服务）
- 数据与迁移（如适用）：产物为版本化 `schemas.json`；不迁移用户数据；安装升级即重装
- 部署、CI、可观测性：`uv tool install .` 本地部署；pytest 门禁；stdout 仅 JSON、诊断走 stderr、退出码三态（成功/校验失败/桥接失败）
- 适用原因、成本与不变量：用户环境 Python/Codely 全就绪，增量成本最低；不变量——core 不依赖上层、未知节点保真、stdout JSON 契约稳定

### 备选

1. 纯 Agent 直改 + 校验器（删除 CLI 层）：依赖 D4 假设成立，复杂节点出错率不可控；作为 NFR-0002 之上的自然退化路径保留。
2. 全桥接（一切经 Unity 执行）：每操作秒级延迟、调试链长；被延迟与出错率证据否决。

## 架构与模块边界

| MOD ID | 模块/路径 | 职责与数据所有权 | 公开 API/事件 | 允许/禁止依赖 | 关联 FR/CR/ADR | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| MOD-CORE | src/asecli/core | ASE 文本解析与序列化引擎；唯一持有图数据模型 | parse/serialize | 仅标准库；禁止依赖 schema/bridge/cli | FR-0001 FR-0002 ADR-0001 | long |
| MOD-SCHEMA | src/asecli/schema | 节点参数 schema 库与提取工具；schema JSON 产物所有权 | schema_for | 允许依赖 core 类型；禁止 bridge/cli | FR-0002 ADR-0003 | long |
| MOD-CHECK | src/asecli/checks | 结构校验与 CHKSM 修复 | validate/fix_checksum | 允许 core；禁止 bridge/cli | FR-0003 ADR-0003 | long |
| MOD-BRIDGE | src/asecli/bridge | Codely/Unity 调用适配；进程调用所有权 | recompile/create_from_template | 允许 core（只读工具）；禁止 cli | FR-0004 FR-0005 ADR-0002 | long |
| MOD-CLI | src/asecli/cli | 命令入口与 JSON 输出契约；组合根 | `asecli <command>` | 允许 core/schema/check/bridge | FR-0007 ADR-0001 | long |
| MOD-SKILL | skills/asecli | Agent 技能文档（文档资产） | SKILL.md | 无代码依赖 | FR-0006 ADR-0001 | long |

- 数据、权限、第三方集成与安全边界：仅读写用户显式指定的文件路径；仅调用本机 `codely` 命令；不联网；不读取/存储任何凭证；桥接脚本不开放任意代码执行入口（只暴露 recompile/create 两个 MenuItem）。
- UI/设计来源、令牌与无障碍约束：不适用（无 UI）；JSON 输出结构即对外界面，字段变更视为 CR。
- 质量门禁、回归与发布要求：`uv run pytest -q` 全绿；REG-0001～REG-0011 目录化；语义化版本；发布前快速审计 S0/S1 清零。
- 关键风险、未决 ADR 与复审日期：三个假设实验结论待回填（Owner long，到期 2026-09-07，结论归档 `docs/01-architecture/assumption-experiments.md`）；无未决 ADR；下次复审 2026-09-07。

## 追溯与下游计划

- 交付计划与任务卡：`docs/04-delivery/project-plan-task-charter.md`（PLAN-0001）
- 追溯矩阵：`docs/00-governance/traceability.csv`
- 上游输入：`docs/first-principles/2026-08-31-231401-optimization-plan.md`

## 启动完成确认

- [x] 两份启动文档已按模板填充并通过严格校验
- [x] 技术路径与需求基线已经用户确认（本会话对话确认）
- [x] 模块边界与依赖方向已定义并写入模块地图
- [x] 首批 14 张任务卡与追溯矩阵已建立且双向链接

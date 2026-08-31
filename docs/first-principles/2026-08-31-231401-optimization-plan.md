# 方案优化计划书：AseCLI — 让 AI Agent 创建/修改 ASE Shader 文件

> 生成时间：2026-08-31 23:14:01
> 项目根目录：/Users/long/GitHub/AseCLI
> Skill：first-principles

## 0. 原方案输入摘要

- 输入来源：用户口述 + 本会话前期分析（ASE 插件源码位于 `/Users/long/Documents/Tuanjie/Genesis/Assets/AmplifyShaderEditor`，464 个 C# 文件，约 12.6 万行）。
- 原方案核心主张：为 Amplify Shader Editor（ASE）适配一个 agent-native CLI（注册进 CLI-Anything），分层实现——Python 层解析/修改 ASE 图数据（方案 A），Codely 桥触发 Unity 重新编译（方案 B）。
- 原方案关键约束：
  1. ASE 节点图以纯文本嵌入 `.shader` 文件（`/*ASEBEGIN ... ASEEND*/`）与 `.asset` 文件（`m_functionInfo` 字段）。
  2. 编译后的 HLSL 代码由 Unity Editor 内的 ASE 生成，无法脱离 Unity 重建。
  3. 用户项目是团结引擎（Tuanjie），Codely CLI v1.0.0-release.20 与桥接包 `cn.tuanjie.codely.bridge@1.0.54` 已安装。
- 当前痛点 / 触发原因：用户真实需求收敛为「通过 agent 工具来创建/修改 ASE 文件」，需要用第一性原理检验：此前「做一个 CLI」是否是最小充分解，还是被「CLI-Anything 方法论」惯性带偏的多余层。

## 1. 重写后的真实目标

- 目标：为了让 AI Agent（Codex / Claude Code / Codely）在团结引擎项目内直接创建和修改 ASE Shader（节点图与最终编译产物），需要 Agent 具备对 ASE 文件格式的可靠读写能力与一条可靠的 Unity 编译触发链路。
- 非目标：
  - 不做 ASE 功能替代品（可视化编辑器、预览窗口）。
  - 不做通用「任意软件 CLI」注册表提交（后续可作为产物提交，但不是本目标）。
  - 不脱离用户现有环境引入新编辑器插件体系。
- 成功判据（可证伪，一周内可验证）：
  1. Agent 用文本方式把一个已有 ASE shader 的某属性值/节点连接改对，Unity 打开后不报错且图正确加载——直接证明「图数据修改不需要专用 CLI」或证伪之。
  2. Agent 通过桥接工具触发 ASE 重新生成，`.shader` 文件 HLSL 部分发生变更且 checksum 更新——证明编译链路可用。
  3. Agent 能从模板创建一个新 shader 文件并在 Unity 中正确打开——证明「创建」路径可用。
- 硬约束（含证据）：
  1. 编译后 HLSL 必须由 Unity 生成（证据：ASE 生成逻辑深度绑定 UnityEditor API，源码 12.6 万行中无独立编译器）。
  2. 目标引擎是团结引擎，非原版 Unity（证据：项目路径 `/Users/long/Documents/Tuanjie/Genesis`；Codely 为团结官方工具）。
  3. `.shader` 文件含 `//CHKSM` 校验行（证据：`IOUtils.cs:132` 定义 CHECKSUM 常量），ASE 打开时可能校验。

## 2. 拆解清单

| ID | 陈述 | 类型 | 处置 | 理由 |
| --- | --- | --- | --- | --- |
| D1 | ASE 图数据是行式纯文本（`Node;类型;Id;x,y;参数...` / `WireConnection;...`） | FACT | 保留 | 已从 `.asset` 实例与源码常量验证 |
| D2 | Agent 本身就能读写文本文件，无需专用 CLI 才能改图 | FACT | 保留 | 这是击穿原方案的关键事实 |
| D3 | 每种节点类型的参数 schema（顺序、类型、默认值）各不相同，共 400+ 种 | FACT | 保留 | `Constants.cs` 与各 Node 类定义了参数序列化顺序 |
| D4 | Agent 不可能可靠记住 400+ 种节点的参数顺序，直接手写图数据易出错 | ASSUME | 验证 | 待实验：让 Agent 盲写一个 5 节点图，看 Unity 是否正常加载 |
| D5 | 需要 CLI 封装图操作才能保证正确性 | INHERIT（来自 CLI-Anything 方法论） | 质疑 | 真正需要的可能是「schema 数据 + 校验器」，CLI 只是壳 |
| D6 | 校验 checksum 是硬需求 | ASSUME | 验证 | 低成本实验：故意改错 CHKSM，看 Unity/ASE 行为 |
| D7 | 编译必须过 Unity，桥可用 Codely | FACT | 保留 | 编译逻辑绑定 UnityEditor；Codely 已装且有 `unity_menu`/`unity_script`/`execute_custom_tool` |
| D8 | 注册进 CLI-Anything Hub 是必要发布渠道 | PREFER | 降级 | 对「Agent 能用」无直接影响；可后置 |
| D9 | 必须支持从零创建新 shader | FACT | 保留 | 用户明确说「创建修改」 |
| D10 | 创建新 shader 可以纯文本完成 | ASSUME | 验证 | 新建需要完整 HLSL + 模板结构，可能必须经 Unity 一次 |

## 3. 伪约束击穿

| 被击穿的假设 | 新认识 | 设计含义 |
| --- | --- | --- |
| 「要给 ASE 做 CLI，就得做一个完整的 CLI 工具」 | Agent 自己就是编辑器，文本文件它直接能改；它缺的不是「编辑器」而是**领域知识**（节点 schema、格式规则）和**防错校验** | 核心产物是 **schema 数据库 + 校验/修复工具 + Agent 技能文档**，CLI 命令只是可选糖衣 |
| 「创建新 shader 可以纯文本搞定」 | 新建需要从模板生成完整 HLSL，模板编译在 Unity 内；纯文本创建只对「复制已有 shader 再改」可行 | 创建路径走 Unity 桥（Codely），修改路径走纯文本 |
| 「注册进 CLI-Anything 是目标的一部分」 | 用户目标是「Agent 能创建/修改 ASE 文件」，与发布渠道无关 | 发布降为后续可选项，不进 MVP |
| 「需要一个自定义 C# 桥接脚本」 | Codely 已有 `execute_custom_tool` 与 `unity_menu`；ASE 重新生成可通过菜单项或注册 custom tool 触发，无需自建 IPC | 桥接层复用 Codely 既有机制，只补一个薄注册文件 |

## 4. 候选方案（2–3）

### 方案 A：Agent 原生直改 + 校验器（极简）

- 核心机制：写一份 SKILL.md 教会 Agent ASE 文件格式规则；附带一个纯 Python 校验器（`validate` + `checksum-fix`），Agent 直接用文本编辑改 `.shader`，改完跑校验。
- 删除了什么：CLI 命令层、schema 数据库、桥接层、包管理、注册表。
- 关键风险：Agent 对复杂节点参数顺序出错率不可控（D4 未验证）；无法保证 400+ 节点全正确。
- 验证方式：成功判据 1——让 Agent 盲改一个真实 shader，Unity 验证。

### 方案 B：ASE Schema 库 + 校验/修复工具 + 桥接（分层最小充分）

- 核心机制：
  1. **Schema 层**：从 ASE 源码自动提取每种节点的参数 schema（名称、顺序、类型、默认值），生成 JSON。
  2. **图操作层**：Python 库 + 薄 CLI（`parse / inspect / set-prop / add-node / connect / remove / validate / checksum-fix`），基于 schema 生成正确的文本行。
  3. **Agent 技能层**：SKILL.md 教 Agent 何时用库、何时直接改文本、何时走桥。
  4. **桥接层**：一个 C# 编辑器脚本（MenuItem + Codely custom tool 注册），提供 `recompile(shader)` 与 `create(template, path)` 两个入口，通过 Codely 的 `unity_menu` / `execute_custom_tool` 调用。
- 删除了什么：完整 CLI 发布流程、自建 IPC、对 Unity Editor 窗口的模拟、通用注册表集成。
- 关键风险：Schema 提取脚本对 ASE 源码的静态分析有遗漏面；checksum 行为未验证。
- 验证方式：成功判据 1/2/3 分别覆盖修改、编译、创建三条链路。

### 方案 C：全桥接（Agent 不直接碰文件，全部经 Unity 执行）

- 核心机制：所有创建/修改/查询都封装为 C# 编辑器方法，Agent 全部通过 Codely 调用。
- 删除了什么：文本解析层。
- 关键风险：Agent 每次操作都要等 Unity 响应（秒级 vs 毫秒级）；Codely 调用链长、调试难；与「Agent 天生会改文本」的优势相悖。
- 验证方式：对比方案 B 的延迟与出错率（不推荐，列作对照）。

## 5. 推荐方案

- 选择：**B**
- 为何优于增量修补：原方案把「做 CLI」当目标，本方案把「给 Agent 补齐领域知识与防错能力」当目标。Agent 已有的文件编辑能力被充分利用，只有 schema/校验/桥接三件事真正新增。
- 明确放弃的东西：CLI-Anything 注册表提交（降为后续可选）；纯文本创建新 shader（改走桥）；方案 C 的全桥接实时性。
- 原方案 vs 新方案对照：

| 维度 | 原方案 | 新方案 | 处置 |
| --- | --- | --- | --- |
| 核心产物 | Python CLI 工具 | Schema JSON + 校验器 + 薄 CLI + SKILL.md + C# 桥 | 重组 |
| 图修改路径 | CLI 命令 | Agent 直接文本编辑 + 校验器把关（或 CLI 生成） | 简化 |
| 创建路径 | 未明确 | Unity 桥 + 模板复制 | 新增 |
| 编译触发 | 「Codely 触发」（模糊） | C# MenuItem + Codely custom tool 注册，两个明确入口 | 具体化 |
| 发布 | CLI-Anything Hub | 本地技能 + 本地 CLI，发布后置 | 降级 |

## 6. 优化实施计划

| 任务 ID | 优先级 | 内容 | 验收标准 | 依赖 | 风险/回滚 |
| --- | --- | --- | --- | --- | --- |
| FP-001 | P0 | 验证三个关键假设：① Agent 盲改图数据 Unity 能否正常加载；② 错误 CHKSM 的后果；③ 从模板纯文本创建 shader 是否可行 | 三个实验各出一行结论，写入本文件 §7 | — | 均为只读/临时文件实验，无风险 |
| FP-002 | P0 | 编写 ASE schema 提取脚本：扫描 `AmplifyShaderEditor` 源码中所有 Node 类的序列化参数，生成 `schemas.json`（节点名→参数列表[名称/类型/默认值/顺序]） | 对 400+ 节点全部提取成功；抽查 10 种与真实 `.shader` 文本逐字段比对一致 | FP-001 | 提取脚本可重跑，JSON 可手工修正 |
| FP-003 | P0 | 实现 Python 图操作库：parse/inspect/set-prop/add-node/connect/remove/validate/checksum-fix，输出 JSON | 对项目内已有 `.shader` 样本全部 parse 成功；对每种操作有 roundtrip（读→写→读）一致性测试 | FP-002 | 库为纯函数式，无副作用，回滚即删文件 |
| FP-004 | P1 | 写 C# 桥接脚本（MenuItem `ASECli/Recompile` + `ASECli/CreateFromTemplate`）并注册进 Codely custom tool | 通过 Codely 调用后：目标 shader 的 HLSL 变更且 CHKSM 更新；新建 shader 在 Unity 打开正常 | FP-003 | 脚本独立文件，删除即回滚 |
| FP-005 | P1 | 编写 SKILL.md（AseCLI Agent 技能）：格式说明、三链路使用手册（改属性/改图/创建+编译）、错误处理 | Agent 按技能文档完成一次「改属性→校验→触发编译→确认 HLSL 更新」全流程 | FP-003, FP-004 | 文档可迭代 |

## 7. 残留假设与验证实验

| 假设 | 低成本实验 | 失败时的回退 |
| --- | --- | --- |
| Agent 直接文本编辑 ASE 图数据可被 Unity 正确加载 | 复制一个真实 `.shader`，让 Agent 只改一个属性默认值，Unity 打开对比 | 全部修改走 FP-003 的 CLI 生成路径 |
| CHKSM 错误不影响 Unity 加载（ASE 只在特定时机校验） | 手动破坏 CHKSM 后 Unity 打开观察 | 校验器提供 `checksum-fix` 自动重算 |
| 新建 shader 必须经 Unity（模板 HLSL 无法纯文本生成） | 取一个模板的完整 `.shader`，删掉图数据看能否被 ASE 加载 | 创建全部走 FP-004 桥接路径 |

## 8. 下一步建议

- 是否需 `$adversarial-audit`：建议在 FP-003 完成后对 roundtrip 测试与 schema 覆盖面打洞。
- 是否需 `$project-architect` 治理落盘：MVP 完成后如需发布（CLI-Anything Hub 提交），再引入。

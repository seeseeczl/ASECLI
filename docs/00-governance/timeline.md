# 时间线 — AseCLI

| 日期 | 类型 | 记录 | 关联 ID |
| --- | --- | --- | --- |
| 2026-08-31 | 启动 | 第一性原理计划书落盘，推荐方案 B（Schema 库 + 校验器 + Codely 桥） | PRJ-ASECLI |
| 2026-08-31 | 启动 | 项目架构师首次启动：计划书审计通过（6 项缺口补齐），治理基线与两份启动文档建立 | ARCH-REQ-0001 |
| 2026-08-31 | 执行 | TASK-0001 完成：三假设实验全部通过，D6/D10 证伪（CHKSM 非必需、纯文本创建可行），结论归档 | TASK-0001 |
| 2026-09-01 | CR | ADR-0002 修订：桥接传输通道由 Codely 为主改为 MCP for Unity 为主（Codely 备选、batchmode 兜底），用户确认 | FR-0004 |
| 2026-09-01 | CR | 用户新增需求：节点布局整理（分层对齐等距），登记 FR-0008/TASK-0015/REG-0012 与 ADR-0005 | FR-0008 |
| 2026-09-01 | 执行 | TASK-0005~0015 全部实施：schema 库 295 节点、布局引擎、12 个 CLI 命令、JSON 契约、MCP 桥接、SKILL.md、性能基线；21 测试通过 | PRJ-ASECLI |
| 2026-09-01 | 验证 | MCP 桥接实测：连接与 execute_code 往返打通；端到端重编译因编辑器无响应待用户验收（REG-0005/0006） | FR-0004 |
| 2026-09-01 | 审计 | 对抗性审计：P0=0 P1=3 P2=3 P3=2；AA-OPT-001~005/007 已修复（CRLF/空行/改名/原子写/guid 告警/窗口泄漏/SSE），29 测试全绿 | PRJ-ASECLI |
| 2026-09-01 | 审计 | 标准审计形成同时间戳报告与 13 项整改任务；用户授权全部执行，基线 commit 8883425 | AUD-20260901 |
| 2026-09-01 | 变更 | schema/version、create graph、图写前不变量完成失败优先回归；自动门禁通过，Editor 证据保留到隔离验收 | CR-0002 BUG-0001 BUG-0002 BUG-0003 |
| 2026-09-01 | 变更 | argparse 单行 JSON、validate 失败退出、fix-checksum dry-run/--write 契约完成 | CR-0003 BUG-0004 BUG-0006 |
| 2026-09-01 | 安全 | MCP tool result 严格判定、loopback 默认、远程 opt-in、环境 token、禁重定向与脱敏完成 mock 回归 | CR-0004 BUG-0005 |
| 2026-09-01 | 验证 | REG-0011 改为 1000 个附加节点、精确 1007 节点、5 轮正确性与耗时门禁 | BUG-0007 REG-0011 |
| 2026-09-01 | 治理 | REG 编号/路径、TASK 状态、追溯和模块 API 校准；catalog 18 条可收集；strict 零发现；全量 77 passed/1 bridge skipped | BUG-0008 BUG-0009 REG-0019 REG-0020 |
| 2026-09-01 | 验证 | 隔离 Tuanjie 2022.3.62t2 + MCP 10.1.2 完成 create→add-node→validate→recompile；`saved=true`、`changed=true`、真实 bridge 1 passed，失败路径 `BRIDGE_ERROR`/3 | REG-0005 REG-0006 REG-0010 REG-0014 REG-0016 REG-0017 |
| 2026-09-01 | 交付 | 最小 CI、固定 Action SHA、内部许可、SPDX、供应链离线检查、可复现构建和 wheel 安装/卸载/恢复演练完成；远程 CI 因未 push 保持未验证 | CR-0006 REG-0021 REL-0001 |
| 2026-09-01 | 验证 | 整改收口门禁：Python 3.10/3.12 各 79 passed/1 bridge skipped，REG catalog 18 条可收集，strict 零 warning/error，真实 bridge 单独 1 passed | AUD-20260901 REG-0020 REG-0021 |
| 2026-09-01 | 审计 | 标准增量复审：基线 14 个 AUD 问题在本地授权范围全部解决，开放问题 0；本地 REL-0001 已验证，远程 CI/Release 保持未验证 | AUD-20260901 REL-0001 |
| 2026-09-01 | 功能 | 用户批准吸收 ASE 1.9.6.2 自定义 GUI，并明确要求 Agent 能用提示文案和分组；登记 FR-0009/TASK-0020/REG-0022/ADR-0010 | FR-0009 TASK-0020 |
| 2026-09-01 | 验证 | `custom-gui` 完成：真实 MZGUI_Test 识别 14 个 Property、13 个属性、7 种类型；隔离副本分组/提示写回、备份、validate 0 errors；Python 3.10/3.12 各 93 passed/1 bridge skipped | TASK-0020 REG-0022 |
| 2026-09-01 | 功能 | 用户提供三张参考图并要求吸收：材质属性排序/中文折叠/逐项常驻说明，以及 ASE 图“外层功能、内层因果”的嵌套 Comment 规范；登记 FR-0010/TASK-0021~0022/REG-0023~0024/ADR-0011 | FR-0010 TASK-0021 TASK-0022 |
| 2026-09-01 | 执行 | `custom-gui --property/--spec` 与 `comment-group` 完成；JSON 规范一次写回，Comment 自动包围且不动成员/连线，定向 56 测试通过 | TASK-0021 TASK-0022 REG-0023 REG-0024 |
| 2026-09-01 | 验证 | Python 3.10/3.12 各 115 passed/1 bridge skipped；REG catalog 21 条、CI governance、供应链、strict 与 diff-check 全通过；真实参考文件 25 个 Comment/4 个关键嵌套标题只读解析且 validate 0 Comment 错误；目标 Inspector/ASE 视觉仍待实际工程验收 | TASK-0021 TASK-0022 REG-0023 REG-0024 |
| 2026-09-01 | 规范 | 用户新增防蜘蛛网要求：可复用或跨算法块的中间结果优先 Register/Get Local Var；Skill 固化触发条件、排版、命名、例外与 schema 安全边界。真实参考静态核对 31 Register/47 Get，10 个变量有至少两处 Get | CR-0007 FR-0010 TASK-0013 |
| 2026-09-01 | 功能 | 用户批准吸收“编辑器内 C# + ASE Editor API”创建方法并要求执行；登记 FR-0011/CR-0008/ADR-0012/TASK-0023~0028/REG-0026~0029，采用离线文本 + 窄范围 Editor 创建混合后端 | FR-0011 CR-0008 ADR-0012 |
| 2026-09-01 | 验证 | 隔离团结 2022.3.61t9 + ASE 1.9.6.2 双进程完成 Caster-like/Receiver-like 创建、Save/Load、关闭与重载；Shader 名、模板 GUID、节点/端口/连接 manifest 一致，无编译错误和暂存残留 | TASK-0027 REG-0029 |
| 2026-09-01 | 功能/验证 | 将 MZGUI 拆为 ASE attribute 协议层与可替换 Inspector 提供者；新增 `gui-support` 和 clean-room 内置 GUI。专项自动回归通过，隔离 Unity 2021.3 实际编译并读取三类 attribute 与 Shader 默认值；目标 Inspector 视觉待验 | FR-0009 ADR-0013 REG-0030 |
| 2026-09-01 | 审计 | Editor 创建后端对抗性审计发现 P1=2/P2=2；Shader 身份、端口预检、属性唯一性和关闭回滚均已修复，结构能力条件通过；生产工程与目标渲染画面未执行 | TASK-0028 AA-COR-001 AA-COR-002 AA-DATA-001 AA-FAIL-001 |

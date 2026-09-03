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
| 2026-09-02 | 批准/实现 | 用户批准 CR-0010：新写入迁移为 ASECLI 三种元数据和唯一内置 GUI；旧三标记保留读取兼容；移除原生 MZGUI 探测、优先级与 runtime probe。定向自动回归 65 passed，新的 C# 编译与目标 Inspector 待验 | CR-0010 ADR-0014 TASK-0030 REG-0022 REG-0030 |
| 2026-09-02 | 验证 | CR-0010 的最终 Python 3.10/3.12 全量回归各 `203 passed, 3 skipped`；CI 治理、REG 目录、供应链与 diff 检查通过；固定 `SOURCE_DATE_EPOCH` 的 wheel/sdist 双构建一致。隔离团结 `2022.3.61t9` 通过 wheel 安装烟测和当前 C# BatchMode 编译，新/旧标记、decorator、metadata 与 `_Value=1.25` 默认值验证通过；真实 Inspector 鼠标交互/视觉仍待独占隔离窗口验收 | CR-0010 TASK-0030 REG-0022 REG-0023 REG-0030 REG-0032 REG-0035 |
| 2026-09-01 | 审计 | Editor 创建后端对抗性审计发现 P1=2/P2=2；Shader 身份、端口预检、属性唯一性和关闭回滚均已修复，结构能力条件通过；生产工程与目标渲染画面未执行 | TASK-0028 AA-COR-001 AA-COR-002 AA-DATA-001 AA-FAIL-001 |
| 2026-09-01 | 审计/交付 | 第二轮对抗性审计 AA-OPT-001～005 完成；本地 206 passed/2 skipped，GitHub Actions run 33510909955 的 Python 3.10/3.12/package 全绿，下载 artifact 哈希/SPDX/隔离安装复验通过；目标 GUI probe、Inspector 与渲染仍待验 | CR-0009 TASK-0029 REG-0031~0035 |
| 2026-09-02 | 验证/修复 | 使用当前运行的团结 `2022.3.61t9` 实机发现旧 drawer 同名冲突和 ShaderGUI 实例跨 Layout/Repaint 丢失折叠状态；改为仅从 `Assets/` 源 Shader 补齐缺失旧元数据，并持久化折叠状态。新/旧样例的分组、默认值、HelpBox、标题点击展开/收起通过；用户实机截图确认 Tooltip 悬停浮层显示变量名和默认值 | CR-0010 AA-COMPAT-001 AA-UI-001 REG-0030 |
| 2026-09-02 | 交付 | `e513fc5` 已推送 `main`；[GitHub Actions run 33594344611](https://github.com/seeseeczl/ASECLI/actions/runs/33594344611) 的 Python 3.10、3.12、package 全绿。下载 artifact 后 SHA256SUMS 校验 wheel `8d19a0…2318`、sdist `c43e69…da32`；隔离环境完成上一版→当前→上一版 wheel 回滚并三次 parse 成功 | TASK-0030 CR-0010 REG-0030 |
| 2026-09-02 | 正式发布 | `v0.1.0` 固定指向 `fbd9941`；[GitHub Actions run 33594698477](https://github.com/seeseeczl/ASECLI/actions/runs/33594698477) 全绿。[私有正式 Release](https://github.com/seeseeczl/ASECLI/releases/tag/v0.1.0) 已发布 wheel、sdist、SPDX、供应链、漏洞扫描与专用 SHA256SUMS；五项载荷哈希和清单资产摘要通过，正式 wheel 在隔离 Python 3.12 安装并成功列出 15 个子命令 | REL-0002 TASK-0030 CR-0010 |
| 2026-09-02 | 缺陷/规范 | 用户以当前团结实例截图发现原生 Info HelpBox 与目标轻量说明条样式不一致，并明确要求成为 CLI 规范能力；登记 CR-0011/BUG-0015/REG-0036/TASK-0031。C# 改为无图标/外框的弱背景左线说明，`gui-support` 新增 `asecli.inline-help.v1` 契约报告并在资源失效时写前拒绝；自动用例先失败 2 项后通过，全量 208 passed/3 skipped，REG/CI governance/供应链/diff 通过；当前团结 `2022.3.61t9` Inspector 对照通过且 Console 0 error；strict 与 HEAD 同样复现 29 项历史问题 | CR-0011 BUG-0015 REG-0036 TASK-0031 FR-0009 |
| 2026-09-02 | 需求变更/实现 | 用户明确要求所有经 ASECLI 构建的 ASE 文件强制采用中文属性显示名、自动英文变量名与 Shader 默认值 Tooltip、属性下方中文使用说明；登记 CR-0012/ADR-0015/REG-0037/TASK-0032。新增 `asecli.property-presentation.v1` 逐属性检查，`custom-gui --spec` 可原子修复显示名/说明，ASECLI-managed 写入和两种 create 后端失败关闭；正式 Editor CLI 创建升级到 v2，底层 v1 兼容保留。新用例先失败 5 项后自动通过；全量 216 passed/3 skipped，REG/CI governance/供应链/diff 通过；Caster 1 属性与 Receiver 6 属性只读检查零违规；strict 与 HEAD 同为 31 项历史问题；v2 真实 Editor 创建待验 | CR-0012 ADR-0015 REG-0037 TASK-0032 FR-0005 FR-0010 FR-0011 |
| 2026-09-02 | 对抗修复/验证 | 执行 `2026-09-02-175509` 优化计划：图与 ShaderLab 属性双向对账、managed 检查失败关闭和 0.2.0 版本完成；实测补获 MCP 3.4.7 `data.result` envelope、安全扫描拦截事务回滚及回执前插件重连问题，登记 BUG-0016/REG-0038。当前团结 `2022.3.61t9` + ASE `1.9.6.2` 成功创建 v2 Sampler/RangedFloat、暂存 Save/Load、manifest、提交并独立 recompile，两属性 reconciliation 零差异；Inspector 中文显示名/说明可见，用户现场确认两项 Tooltip 正常；恢复原选择后验证资产和暂存资产均无残留。双 Python 223 passed/3 skipped，REG 34 条、治理、供应链、Skill、可复现构建和隔离安装/回滚通过。新进程重开按用户约束未执行，0.2.0 尚未提交或发布 | CR-0012 BUG-0016 REG-0037 REG-0038 TASK-0032 AA-OPT-001 AA-OPT-002 AA-OPT-003 |
| 2026-09-02 | 推送/缺陷修复 | `0.2.0` 候选首次推送后，GitHub run 33623943475 的 Python 3.10/3.12 verify 全绿，但 package 已构建 `0.2.0` 后仍安装硬编码的 `0.1.0` wheel，远端门禁失败；登记 BUG-0017/REG-0039。CI 改为由 `uv version --short` 驱动安装、SPDX 和 artifact 名，SBOM 从 `uv.lock` 读取项目版本，治理检查拒绝工作流重新硬编码版本；本地回归通过，等待修复提交的远端 package 复验 | CR-0012 BUG-0017 REG-0039 TASK-0032 |
| 2026-09-02 | 推送/缺陷修复 | BUG-0017 修复后的 GitHub run 33624498244 全绿，动态 `0.2.0` 安装、SPDX、供应链、GUI 烟测和 artifact 上传通过；下载 artifact 时又发现 SHA256SUMS 条目含 CI 工作区 `dist/` 前缀，标准校验找不到根目录文件，登记 BUG-0018/REG-0040。CI 改为在 `dist` 内生成只含文件名的清单，并增加治理/测试门禁；本地回归通过，等待最终远端 artifact 复验 | CR-0012 BUG-0017 BUG-0018 REG-0039 REG-0040 TASK-0032 |
| 2026-09-02 | 治理/契约 | 执行 `2026-09-02-211218` 优化计划：Editor create JSON 增加 `staging_reloaded`/`target_graph_reloaded` 并保留 `reloaded` 兼容别名（CR-0013）；packed C# `.cs.txt` 执行器纳入 CI LOC 扫描并具名豁免；校准 TASK-0026/0028/0029 与 module-map 反向链接，core 公开导出 `is_material_property_node` | CR-0013 REG-0038 TASK-0032 AUD-FE-001 AUD-SIZE-001 AUD-GOV-001 |
| 2026-09-02 | 正式发布 | `v0.2.0` 固定指向 `6865aaa`；[GitHub Actions run 33637146781](https://github.com/seeseeczl/ASECLI/actions/runs/33637146781) 全绿。[私有正式 Release](https://github.com/seeseeczl/ASECLI/releases/tag/v0.2.0) 已发布 wheel、sdist、SPDX、供应链、漏洞扫描与专用 SHA256SUMS；五项载荷哈希和清单资产摘要通过，正式 wheel 在隔离 Python 3.12 安装并成功列出 15 个子命令；`v0.1.0` 回滚安装通过 | REL-0003 TASK-0032 CR-0012 CR-0013 |
| 2026-09-03 | 验证/治理 | 指定团结 `2022.3.61t9` + ASE `1.9.6.2` 隔离工程完成 EditorGraphSpec v2 创建进程与全新重开进程 manifest/presentation 对账；0 Shader/CS error、0 staging 残留，原工程 hash 不变；三份 REL、SECURITY 0.2.x、14 FM/15 FE 与 LOC 例外治理同步闭环 | TASK-0033 TASK-0034 REG-0038 AUD-FLOW-002 AUD-FE-001 AUD-GOV-002 AUD-GOV-003 AUD-SIZE-001 |
| 2026-09-03 | 真实画布验收 | small/medium/complex-caster/complex-receiver 四类图仅改变节点位置或 Commentary bounds，wire/计算语义不变；ASE TruePosition containment 与 normal zoom 人工检查通过，结构 JSON 和视觉截图分层归档 | TASK-0035 REG-0041 AUD-FLOW-003 AUD-FE-002 |
| 2026-09-03 | UI 缺陷/验收 | Inspector 矩阵发现 BUG-0019 长中文单行截断与 BUG-0020 Tooltip 浮点噪声；展示层最小修复后 62 项定向测试、团结编译及深/浅色、300/480px、Retina、Foldout、mixed、disabled、focus/Tab 通过；主题恢复 | TASK-0036 REG-0042 BUG-0019 BUG-0020 AUD-UI-001 |
| 2026-09-03 | CI 治理 | checkout v5.0.1、setup-uv v7.1.6、upload-artifact v6.0.0 切换至官方 Node 24 固定 SHA；治理 allowlist 与回退测试通过。未提交/未推送，真实 GitHub run 保持未验证 | TASK-0037 REG-0043 AUD-CI-001 |
| 2026-09-03 | 需求变更/治理 | CR-0014 将 583/410 行 C# 资源拆为确定性有序片段，拼装 SHA-256 和 Editor 单事务边界不变；EXC-0001/0002 删除。已知 `0.2.0-original` GUI 新增 dry-run、备份、复核和原子替换，未知/并发/符号链接仍拒绝 | CR-0014 ADR-0016 TASK-0038 TASK-0039 TASK-0040 REG-0044 REG-0045 AUD-SIZE-001 |
| 2026-09-03 | 实机验证/缺陷 | 旧 GUI 升级后团结 `2022.3.61t9` C# 编译与元数据读取 `1 passed/26.15s`；ASE `1.9.6.2` 从干净 Assets 创建后全新进程重载先暴露空 Generated 目录被刷新移除，BUG-0021 修复后完整命令 `1 passed/39.86s`。包源 DNS 临时失败单独记录，不冒充代码失败或通过 | CR-0014 BUG-0021 REG-0045 TASK-0038 TASK-0040 |
| 2026-09-03 | 远程 CI 复验 | [run 33713836753](https://github.com/seeseeczl/ASECLI/actions/runs/33713836753) 的 Python 3.10、3.12、package 全绿且不再有 Node 20 强制兼容警告；日志审计仍发现 setup-uv v7.1.6 输出 `DEP0040`/`DEP0169`，因此 REG-0043 未关闭并继续升级到官方不可变 v10.0.1 | TASK-0037 REG-0043 AUD-CI-001 |

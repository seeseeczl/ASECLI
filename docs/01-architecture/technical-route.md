# 技术路径 — AseCLI

## 架构决策记录

### ADR-0001 采用 Python + uv 的模块化单体 CLI

- 状态：已确认（2026-08-31）
- 背景：需要跨平台本地工具，被 AI Agent 以子进程方式调用。
- 决策：Python >=3.10 + uv 管理；`src/asecli` 六模块单仓；CLI 为组合根。
- 理由：用户环境 Python 3.12 已就绪；Agent 生态（skill 文档 + CLI 调用）天然匹配；打包分发用 `uv tool install`。
- 备选被拒：Node/Go 单二进制（跨语言维护成本高，无团队熟悉度收益）；纯 shell 脚本（无法承载 schema 数据库与 roundtrip 测试）。

### ADR-0002 编译桥接：Unity 侧薄能力层 + MCP for Unity 主传输（修订 2026-09-01）

- 状态：已确认（2026-08-31）
- 背景：ASE 编译后 HLSL 必须由 Unity/团结引擎生成。TASK-0001 实验确认了确切的 Unity 侧调用序列（隐藏 ASE 窗口实例 + ParentGraph.Init + LoadFromMeta），且用户工程已运行 MCP for Unity（HTTP :8080），其 `execute_code`/`execute_custom_tool` 可直接执行该序列。
- 决策：三层传输——① 主通道：MCP for Unity（确定性 RPC，无 LLM 介入，asecli 内置最小 MCP 客户端）；② 备选：Codely（`unity_menu`/`execute_custom_tool` 触发同一 C# 方法）；③ 兜底：Unity batchmode（已验证，约 10-20s/次）。Unity 侧能力封装为约 30 行的可复用 C# 片段/方法（ASECliBridge），随 MCP execute_code 注入或注册为 custom tool，不强依赖工程内常驻脚本文件。
- 理由：MCP 传输最薄且用户环境已就绪并实测可达；Codely 为交互式 agent 设计，非交互脚本化不是其主路径，作为备选保留；batchmode 无需编辑器常开。
- 备选被拒：自建 Editor WebSocket 服务（维护成本高、权限面大）；以 Codely 为主通道（多一层 agent 运行时间接层，故障定位链长）。
- 修订记录：原决策以 Codely 为主通道；TASK-0001 实验与用户环境实测（MCP 会话可达）后于 2026-09-01 修订，经用户确认。

### ADR-0003 节点 schema 由 ASE 源码静态提取 + 样本比对验证

- 状态：已确认（2026-08-31）
- 背景：400+ 节点类型的参数顺序/类型/默认值各不相同，Agent 无法可靠记忆。
- 决策：一次性提取脚本扫描 ASE C# 源码中节点序列化字段，生成版本化 `schemas.json`；对真实 `.shader` 样本逐字段抽查验证；未知节点 passthrough。
- 理由：手工维护 400+ schema 不可持续；运行时依赖 ASE 源码不可分发。
- 风险与缓解：静态分析遗漏面 → 以真实样本比对为门禁（REG-0009），遗漏项手工补录进 JSON。

### ADR-0004 发布策略：本地优先，Hub 提交后置

- 状态：已确认（2026-08-31）
- 决策：MVP 以本地 `uv tool install` + Agent 技能交付；CLI-Anything Hub 提交在稳定运行一个版本周期后评估。
- 理由：用户目标是自用自动化；发布流程不应阻塞核心链路验证。

### ADR-0005 节点布局采用 Sugiyama-lite 分层算法

- 状态：已确认（2026-09-01）
- 背景：用户要求节点排列整洁（FR-0008）；ASE 数据流图天然左进右出。
- 决策：最长路径分层（Master 节点强制末层）+ 行内按前驱均值排序（两轮 barycenter 交叉减少）+ 固定间距网格（gap_x=280, gap_y=120，可配）。只写 x/y，其余字段零改动。
- 备选被拒：力导向布局（结果不稳定、不满足"整齐"）；完全保持原位（不解决需求）。

## 质量与部署约束

- 门禁：`uv run pytest -q` 全绿；roundtrip fixture 测试覆盖真实 ASE 样本。
- 可观测性：stdout 仅 JSON（Agent 契约），诊断与进度走 stderr；退出码区分成功/校验失败/桥接失败。
- 部署：`uv tool install .` 本地安装；升级即重装，无数据迁移。

### ADR-0006 图写入采用结构门禁与显式写入语义

- 状态：已确认（2026-09-01，CR-0002/CR-0003）
- 决策：schema add-node 先校验 ASE 版本；所有图修改在写入前执行结构校验；结构字段 0-2 不允许通用 set-field 修改；fix-checksum 默认 dry-run。
- 兼容：raw `--line` 专家路径保留但仍走结构门禁；旧 fix-checksum 自动写入调用必须增加 `--write`。
- 回滚：禁用 schema add-node/graph-from，保留 parse/validate 与 raw 只读链路。

### ADR-0007 MCP 使用最小远程信任边界

- 状态：已确认（2026-09-01，CR-0004）
- 决策：默认只允许 `127.0.0.1`、`localhost`、`::1`；远程端点需显式 opt-in；URL 禁止凭证/query/fragment；客户端不跟随重定向；instance token 仅从环境读取并全链路脱敏。
- 理由：MCP `execute_code` 等同编辑器内代码执行能力，传输成功不能替代 tool `isError` 与 `saved=True` 确认。
- 回滚：完全关闭远程端点，只保留 loopback。

### ADR-0008 core 解析符号提供稳定公共入口

- 状态：已确认（2026-09-01，CR-0005）
- 决策：公开 `parse_node_line`，CLI 仅使用公开入口；`_parse_node_line` 保留一个兼容周期。
- 替代被拒：CLI 继续导入私有 helper，会使模块边界和重命名兼容不可验证。

### ADR-0009 内部发布采用零运行时依赖、可复现 artifact 与 SPDX

- 状态：已确认（2026-09-01，CR-0006）
- 决策：内部专有许可；Python 3.10/3.12 矩阵；uv/lock frozen；固定 commit 的 Actions；固定 epoch 双构建；wheel/sdist SHA-256；SPDX 2.3；隔离安装/卸载/恢复。
- 可复现实现：Hatchling 版本进入 dev lock，CI 使用 `--no-build-isolation`；两次构建输出写入 runner 临时目录，禁止第一次产物进入第二个 sdist。比较失败时保存 hash、gzip header 与 tar 成员元数据/内容差异，但正式 dist 仍阻塞。
- 安全：离线高置信 secret、Action pin、lock hash 门禁；生产依赖为 0。在线漏洞数据库必须用真实 CI/Dependabot 证据单独解除“未验证”。
- 发布：本地 REL draft 不等于远程 Release；没有 push/run/artifact 链接时不得标 released。

### ADR-0010 自定义材质 GUI 采用语义命令与图元数据事实源

- 状态：已确认（2026-09-01，FR-0009）
- 背景：ASE 1.9.6.2 的自定义 GUI 同时存在于主 Master 的 `customInspectorName`、编译 ShaderLab `CustomEditor` 和 PropertyNode MZGUI 尾部；通用字段写入无法安全表达中文提示、分组边界和属性数量。
- 决策：新增 `custom-gui` 语义命令。CustomEditor 写入时同步唯一主 Master 字段 9 与编译指令；Tooltip/HelpBox 复刻 C# UTF-16 `#XXXX` 编码，Foldout 复刻非 ASCII 编码；PropertyNode 尾部按 `<count>;<attributes...>` 最小写回。
- 安全：类名不是 hard allowlist，但必须满足 C# 命名空间标识符格式；CustomEditor 只开放真实采证的 `19109/19602`，MZGUI 尾部只开放 `19602`。新增属性要求显式使用已检测的提供者；非 Property、未知版本/尾部、非唯一主 Master 和注入字符失败关闭。
- 生成边界：编译 Properties 由 ASE 负责，CLI 不做脆弱的 ShaderLab 行映射；写元数据后返回 `requires_recompile=true`，Agent 必须执行 validate→recompile。
- 回滚：每次显式写入保留 `.bak`；恢复备份后重编译。禁用 `custom-gui` 不影响其他命令。

### ADR-0011 参考规范采用声明式材质清单与原生 CommentaryNode

- 状态：已确认（2026-09-01，FR-0010）
- 背景：参考 Inspector 要同时控制属性顺序、中文折叠组和逐项常驻说明；参考 ASE 图又需要可嵌套的功能/因果说明。逐属性多次调用不具原子性，旁路文档也不会显示在真实编辑器。
- 决策：材质侧用 JSON `properties` 数组作为一次性操作规范，以 ShaderLab 属性名或节点 ID 定位，字段 9 重排，`group/help/tooltip` 写 MZGUI；图侧直接生成 ASE 1.9.6.2 原生 CommentaryNode，按成员位置计算边界，已有 Comment ID 可作为外层成员。
- 安全：整份 JSON 先验证后一次写盘；未列属性稳定追加；Comment 禁止重复直属、祖孙同时选中、缺失 ID、分号和换行。两条命令均默认 dry-run，显式写入保留 `.bak` 并重算 CHKSM。
- 取舍：普通节点真实宽高不在序列化中，自动框使用保守默认尺寸并把真实编辑器边距列为视觉验收边界；不新增 Unity 插件或旁路元数据格式。
- 回滚：恢复同名 `.bak`；材质侧随后重新编译，Comment 侧重新加载 ASE 图。禁用新增命令不影响既有图计算和材质结果。

#### CR-0007：以 Local Var 作为算法模块间的数据接口

- 增量语义：同一结果被分散复用、跨 Comment 或产生长距离交叉线时，使用一个 `Register Local Var` 和各消费块就近的 `Get Local Var`；Comment 负责算法职责，Local Var 负责模块数据接口。
- 约束：一次性同组相邻链路保持直连；变量名必须唯一且语义明确；禁止以 Local Var 隐藏关键单次依赖、重复计算或制造同名 Register。
- 实现边界：`RegisterLocalVarNode` 的端口类型随输入变化，现有 runtime schema 明确 `layout_ok=false`，因此不开放不完整的 schema add-node；由真实 ASE 创建或复用同版本/同类型真实行，随后 validate/recompile。
- 证据：真实参考文件包含 31 个 Register、47 个 Get，`SunShadow` 5 次、`Saturation`/`LitValueControl` 各 4 次获取，验证该模式用于跨区复用而非单纯装饰。

### ADR-0012 动态/不透明节点采用窄范围 ASE Editor API 后端

- 状态：已确认（2026-09-01，FR-0011/CR-0008）
- 背景：一次性编辑器内 C# 已证明 `CreateNewTemplateShader`、`CreateNode`、`CreateConnection`、`SaveToDisk`、`LoadFromDisk` 可创建可编辑图；当前 `SamplerNode`/`CustomExpressionNode` 为 `layout_ok=false`，离线 schema 不足以安全猜造动态端口和私有字段。
- 决策：保留离线文本链路为默认；新增受限 `EditorGraphSpec v1` 和 `create --backend editor|auto`。固定 C# 执行器只允许模板、Sampler、CustomExpression、白名单普通节点、连接、保存/重载与 manifest 回读；反射字段白名单并先做能力探测。
- 安全与事务：禁止任意 C#/任意反射；参数安全编码；默认 loopback；JSON-RPC 响应 ID 必须与当前请求一致。不支持版本、成员缺失、Save/Load/manifest 不一致均零成功。Editor 提交前失败删除明确事务资产；提交后 Python 后验失败保留目标并返回 nonce/hash，避免 TOCTOU 误删；已有文件仍走文本创建/备份链路。
- 取舍：不把全部修改搬回 Editor；不手写动态节点序列化；不把运行时矩阵/CommandBuffer 状态塞进静态图。可编辑性和渲染等价性分别验收。
- 回滚：关闭 Editor/auto 后端并保留 `create --backend text`；现有文件格式、schema 和命令不迁移。

### ADR-0013 MZGUI 能力拆为 ASE 协议层与可替换 Inspector 提供者

- 状态：已确认（2026-09-01，FR-0009）
- 背景：MZGUI 的 PropertyNode 尾部只负责让 ASE 生成 ShaderLab attribute；Foldout、Tooltip 和 HelpBox 的实际显示发生在 Unity `ShaderGUI` / `MaterialPropertyDrawer`。目标工程不一定安装同一套 MZGUI，且本地参考源码未发现允许再分发的许可证。
- 决策：保留 `[FoldoutMzgui]`、`[TooltipMzgui]`、`[HelpBoxMzgui]` 作为兼容协议。`gui-support` 识别裸/全限定/global/alias 源码；预编译 DLL 只能静态定为 `unknown`，连接同一工程后由 Editor 反射 `MZGUI.MZGUI : ShaderGUI`。只有确认缺失才安装 clean-room 固定资源。
- 默认值：内置 GUI 从新建的默认 `Material(shader)` 读取每个属性的真实 Shader 默认值，并在显示时与变量名一起追加到 Tooltip；不把当前材质值或人工抄写的默认值当作事实源。
- 兼容：ASE 版本差异只存在于 PropertyNode 元数据写入端；无法动态识别合法尾部时失败关闭。Inspector 层对 ASE 版本无感。Unity 2021.3 已验证 `MaterialPropertyHandler` 路径；新版 `ShaderUtil.GetShaderPropertyAttributes` 作为后备。
- 安全与许可：不复制或打包 MZGUI 专有源码；只实现 Foldout/Tooltip/HelpBox 与技术 Tooltip。原生提供者存在时不安装；固定路径存在不同内容时拒绝覆盖；不实现 Ramp、搜索、还原按钮和关键字面板。
- 验收边界：Python 覆盖检测、dry-run、安装、哈希、冲突和 CLI 契约；隔离 Unity 覆盖 C# 编译、三种 attribute 实例化与默认值读取；目标 Inspector 的折叠点击、悬停触发和视觉排版仍需真实 UI 验收。

### ADR-0014 ASECLI 自有元数据协议与唯一内置 GUI

- 状态：已确认（2026-09-02，CR-0010 / FR-0009）
- 背景：`*Mzgui` 既是序列化属性类型又绑定原生提供者选择，继续把新资产写为该名称会把外部 GUI 标识带入项目。静态扫描和 Editor 反射也使仅安装自有 GUI 的路径依赖无关 MCP 与外部实现。
- 决策：新写入只使用 `[ASECLIFoldout(...)]`、`[ASECLITooltip(...)]`、`[ASECLIHelpBox(...)]`，唯一推荐 `CustomEditor` 为 `ASECLI.MaterialGUI.ASECLIMaterialGUI`。`gui-support` 只检查和安装固定 ASECLI 资源，移除原生提供者探测、优先级与 `--runtime-probe`。C# 正常属性读取与 Python inspection 仍识别旧三标记；同语义写入或 clear 时只迁移被触碰的属性。
- 兼容与迁移：不批量修改用户 Shader，不写入或选择 `MZGUI.MZGUI`。含旧属性的 Shader 可查询和由内置 GUI 读取；要开始新写入，用户必须显式把主 Master/编译指令改为 ASECLI Editor。原始专家入口仅接受三种 ASECLI 类型。
- 安全与回滚：固定目标路径的内容冲突和符号链接仍拒绝覆盖；安装使用创建时排他写入。回滚本变更仅恢复上一版 CLI/资源，不自动更改用户 Shader 或删除内置安装资源。
- 验收边界：Python 回归证明协议写入、旧属性读取、触碰迁移、安装、冲突与 CLI 契约；新的 C# 资源尚需隔离 Unity/Tuanjie 编译和目标 Inspector 的视觉/交互验收。

# SG 转换后 ASE 图交付流程

适用：SGCLI 直接输出 `<stem>.sgcli-to-asecli.spec.json`（裸 EditorGraphSpec v3），ASECLI 原样消费并创建 ASE 图；或整理这类现有 Shader。源 `.shadergraph`、创建规格、独立 report、发布 receipt 和当前 `.shader` 是不同资产；receipt 只证明 spec/report 提交状态，不进入创建输入。创建规格中的拓扑分列只是初排；以最新已确认效果正确的 Shader 为基线，不能用旧规格覆盖它。

## 先锁定语义，再整理

- 将当前 Shader 复制为唯一备份，记录 SHA-256；不复用会被后续命令覆盖的 `.bak` 作为整个任务的永久基线。
- 运行 `asecli graph-review <shader> --reuse-policy consumer-groups`，保留单行 JSON 结果。它保留非布局节点原始字段、精度/常量/纹理引用/不透明 Master 数据，并按来源输出端口折叠 Register/Get/WireNode。输出可达节点、无连接 Master 与输出外保留支路分别列出，输出外节点不是删除许可。
- SG 转换时还必须检查未连输入的真实默认值、向量宽度、子图绑定、空间变换、噪声算法、混合状态，以及当前 SG Editor 生成的 HLSL。ASE 快照不知道源 SG 默认值，不能代替这项对照。未知默认值格式应回到转换端报错，禁止补零；不要通过改生成 HLSL、为 pow 加 abs/clamp/Saturate 来掩盖差异。
- 编辑完运行 `asecli graph-review <shader> --baseline <唯一备份.shader>`。`computation_equal=false` 必须解释并修复；`generated_source_equal` 是生成源码整体摘要，不是语义等价证明。GUI 元数据和真实再生成造成的源码变化应单独审查，不能删除比较门禁或声称摘要相等就是画面相同。

## 明确复用策略，保留真实接口

默认 `consumer-groups` 仍按不同消费组判断。仅当用户明确要求“同一输出使用两次就注册”时，使用 `--reuse-policy fanout`。门槛按 `(来源节点 ID, 输出端口)`，不是节点 ID；例如 RGB、R、A 不能混计。

`graph-review` 是只读计划，不会创建 Register/Get。计划列出使用次数、真实目标端口、消费组、现有 Register 与需替换的直接消费者。已有正确接口保持不动；部分接入时复用已有 Register，不再新建同名注册。复杂 WireNode/嵌套接口计划需要人工核对，不把它直接当成写入规格。

落实计划时通过当前 ASE Editor API 创建动态节点，或使用本版本、本类型已核验的真实样本；不能猜序列化。先给结果确定稳定语义名，生产者右侧注册、每个消费者左侧就近 Get，保留精度/数据类型和源输出分量。操作后立即用 `graph-review --baseline` 核对折叠后的计算连接，多一条、少一条或端口变化均不放行。无法获得安全创建能力时明确报告未完成，不只输出计划就宣称已治理。

## 递归鱼骨，然后摆放独立岛

- 复用已运行 Editor，一次获取节点矩形、标题和已连接端口真实几何。从实际连接的 Output 端口反查各直接来源，每个消费者都是一个局部终点。全局深度与创建顺序不能决定所有节点的列、行。
- 使用 `layout --mode meticulous`：主要输入沿水平主骨，余下完整子树按输入端口顺序分配上下空间；按端口 y 对齐。父子边界目标 96px，通常 64–160px；兄弟至少 32px、跨模块至少 96px。调整完整子树包围盒，不整体倍增所有 y。
- 如果本地变量已断开大量长线，使用 `asecli layout <shader> --mode meticulous --island-columns 3 --audit --mcp-url <URL>` 预演；无硬失败后同参数改 `--write`。列数可为 2–8，默认 1 保持旧行为。计算岛内部只做整体平移，按 Register/Get 逻辑依赖及语义标题排序，输出在右；不按最小节点 ID 排版。
- 包装保留 Comment 归属和跨物理岛的框；不会拆开一个已有框的成员。含固定 WireNode 的多列摆放目前失败关闭，不自动搬动锚点，也不自动开启 `--route-wires`。需要独立路由授权和验收。
- 几何只可在同一未变化的图、相同显示名/节点类型/端口集合下复用。新增接口或改名导致尺寸改变后重新测量；不得拿旧缓存冒充新节点的真实尺寸。先完成全部候选修改，再集中 Editor 验证，不反复重启 Editor。

## 说明与 GUI 放在布局之后

先稳定节点，再以原生 `comment-group` 添加紧密算法单元的中文标题、短说明；不为凑组数框全部上游。保留支路注明是否影响当前输出。按最终标题与节点真实尺寸收框，左右/底部通常 30px、顶部至少 48px；同级重叠必须拆分或缩小语义范围，不能忽略错误。

`gui-support` 确认唯一 provider 后，用一份 `custom-gui --spec` 批量配置：每组首项 Foldout，中文显示名、功能排序与 Tooltip；保留英文变量名、类型、默认值、范围、HDR、纹理绑定和材质兼容性。名字和用途来自真实消费者，向量注明 XY/ZW、颜色注明 Alpha，未启用/未接入参数说明当前无效。变量名与默认值由 GUI 自动追加；默认不添加 HelpBox。

## 分层验收，不能互相代替

1. **结构**：折叠接口后的计算端口/连接、常量、精度、属性、Master 保持；Comment 无越界/同级重叠；属性契约 `valid=true, violations=[]`；Checksum 正确。新命令的基线比较故意保守，修改 GUI 后会报告节点字段变化，需结合原有属性契约核对。
2. **Editor**：经真实 ASE 生成、导入并独立重载；MCP 超时先核对目标与暂存状态，禁止盲目重试。
3. **画布/GUI**：正常阅读缩放下看代表鱼骨、重复分支、长线、所有分组；连线只在明确空白通道交叉，不穿无关节点/标题；展开、收起并真实悬停提示。
4. **效果**：新转换图在相同材质参数、模型、镜头、光照和时间下对照 SG 与 ASE。公开属性相同、编译成功、151 条计算连接一致等结构证据不能代替画面对比。

分别报告通过、失败、未执行。历史 Wave Noise 的说明框阶段仅有尺寸及 GUI 静态契约证据，不能沿用为悬浮交互和完整正常缩放验收。数字如 12 Register、27 Get、19 框和 14 属性只属于历史样本，不是通用目标。


## ASE 转换后 SG 侧节点图交付

适用：ASE Shader → `asecli export-sg` → `<stem>.asecli-to-sgcli.spec.json`（裸 `sgcli.native.v3`）→ `sgcli sg create` → `.shadergraph`。不生成 ASE 自有中间 JSON，不调用 SGCLI，不允许脚本或 Agent 改写规格。独立 report 只记录转换证据，receipt 只记录 spec/report 提交状态；二者都不能传给 `--spec`。以下数字来自历史 WaveNoise 转换记录：源 ASE 1.9.6.2 图有 205 节点（64 CustomExpression、12 RegisterLocalVar、27 GetLocalVar、19 Commentary、10 Master）、15 属性；目标曾读回 147 节点、157 连线、15 属性、19 组。数量仅用于该样本对账，不能推广为转换模板，也不能证明当前直连实现已通过 Editor/视觉验收。

### 1. 先锁语义，再选择原生节点或函数兜底

保留源 Shader、候选规格、独立 report 和最终资产的独立摘要。逐图核对属性默认值、范围、精度、纹理、空间、时间、噪声算法、输出及混合状态；Register/Get 按源输出分量还原逻辑依赖，Commentary 保留语义归属，多个 Master 按实际 Pass/输出作用核对，不能按数量直接删减。

优先还原具有相同语义的 SG 原生节点；只有当前环境中没有已验证等价实现时才用 Custom Function。Saturation、Contrast、Gamma 块和 ASE 特有噪声是本次候选示例，不表示 SG 永远没有同名节点。判断依据是公式、颜色空间、精度和边界行为，而非名字。选择哪段表达式兜底、函数如何拆分以及布局和说明由 Agent 决策；端口号、类型字典、序列化解码交给 CLI 的目录、数据和代码。

### 2. 生产者写名称槽位，消费者解析目标端口

```bash
asecli export-sg Assets/WaveNoise.shader --out-dir ./out
sgcli sg create Assets/WaveNoise.shadergraph \
  --spec ./out/WaveNoise.asecli-to-sgcli.spec.json --mcp-url <URL>
```

ASECLI 输出 `sgcli.native.v3` 名称槽位，不把 ASE 数字端口或某次 SG catalog 数字 ID 写成公共规则。SGCLI 消费端先按自身 Schema/运行校验器检查，再在目标 Editor 中创建并配置节点，按输入/输出方向解析唯一槽位；名称基础匹配只允许唯一结果，多匹配或缺槽立即失败。生产者输出文件到消费者读取前字节不得改变，并记录两端 SHA-256。

生产者以一次不可变源字节快照完成解析和哈希，并在转换后、报告后、发布前复核源文件；任何变化只留失败报告。报告必须区分 `source_snapshot_sha256`、`source_recheck_sha256`、`producer_schema_validated` 与 `consumer_loaded`。需要只验证交接文件时，使用 `sgcli sg contract --version 3 --spec FILE`，不能由 ASECLI 预填消费者已通过。

旧 `{graph,report}` wrapper 不得传给正常消费者。仅在内层已经是 `sgcli.native.v3` 时使用 `asecli migrate-package OLD --out-dir DIR --extract-sg-spec` 显式提取；v2、未知字段或其他历史格式失败关闭。

Vector2/3/4 的 X/Y/Z/W 仍是独立标量槽，不能把整段数组塞给单个分量；Custom Function 和动态节点接口由 SGCLI v3 消费端拥有。函数端口中的 `FLOAT`/`FLOAT3` 等 ASE 类型必须通过经过校验的 ASE→SG 类型表转换；未知类型失败关闭，禁止默认按 float 处理。

### 3. Custom Function 保留源算法，机械转换单独核对

保留原始编码体、解码体与 SG 函数体，便于逐步对照。当前 CLI 缺少解码器时，使用针对来源版本验证过的确定性辅助转换，不让 LLM 随意重写公式。

本次素材有 `@$`（语句终结符）、`@`（裸语句分隔标记）、`\n`（行分隔）。应先识别较长标记 `@$`，区分 JSON 解码后的真实换行与字面转义，再按来源格式还原；`#if/#else/#endif` 保持独立行。不能对注释、字符串或已解码内容反复全局替换。

对已确认的单输出顶层 `return X;` 可改为 `Out = X;`；纯表达式可包装为 `Out = ...;`。输入偏移和输出槽位从上一节的目录读取。局部函数的 return、多个提前返回、条件编译和多输出不能用正则统一替换；需要保留控制流并逐图审查，无法确定时停止该块转换。禁止通过补零、添加 abs/clamp 或换噪声公式让编译暂时通过。

### 4. 先预演再写入，失败先核对事务

```bash
sgcli sg create <目标.shadergraph> --spec <stem>.asecli-to-sgcli.spec.json --mcp-url <URL>
sgcli sg create <目标.shadergraph> --spec <stem>.asecli-to-sgcli.spec.json --mcp-url <URL> --write
sgcli sg inspect <目标.shadergraph> --mcp-url <URL>
```

本次曾出现编译失败后约 460KB 残件；不能据此断言所有失败都会留文件。`create` 从不覆盖，遇失败先保留错误、事务 ID、journal 和文件摘要，检查目标与 `.meta`、before/candidate 摘要及恢复状态，不立即删文件或重发写入。

```bash
sgcli sg recover --project <工程目录> --transaction-id <事务ID> --mcp-url <URL>
sgcli sg recover --project <工程目录> --transaction-id <事务ID> --mcp-url <URL> --write
```

优先使用现有恢复入口。仅在确认残件属于本事务、`had_asset:false`、没有外部修改且恢复后目标应不存在时清理残件；已有资产必须恢复 before 状态及原 `.meta`，不能按新建残件删除。

遇 `TRANSACTION_BUSY`，核对 `.sgcli-transactions/write.lock` 的事务 ID、PID 与 journal。只有属主已退出、锁未被替换、资产及元数据已完成恢复核对，才可清除对应 stale 锁并重落地。PID 存活、权限不足、属主不明或外部变更时停止；仅 TTL 超时不是删锁依据。当前恢复器已具备 PID 检查，自动化升级见独立清单。

### 5. MCP 瞬断有限重试，写入结果不明先查证

本次 `execute_code` 五次探测中首调 `success:False`、后四次成功，只证明该会话的现象，不构成所有失败都可重试的规律。对确认的只读探测或未执行请求，最多追加两次重试，间隔 1 秒、2 秒，保留原错误；类型/能力/编译错误不重试，不因单次失败改数据，也不据此改 SGCLI transport。

写请求失败或超时可能已经执行：先查询结果、目标摘要与 journal，已完成则读取结果；未完成则先恢复，结果不明则停止。禁止把 `success:False` 当作未写入证明，也不通过换请求 ID 强行重复创建。

### 6. 逐层验收 SG 交付

1. **结构**：`sg inspect` 读回属性、默认值、方向/端口连接、分组和输出；Custom Function 核对 `m_FunctionSource`、`m_FunctionBody` 或当前 inspect 对应字段，检查源码模式、函数体/文件引用与签名一致。文件模式不要求内联体非空，字段未暴露需通过支持的 Editor 读取补证，不能推断存在。
2. **Editor**：核对 `editor_graph_validated: true`，并保留真实导入、编译和重载结果；单个布尔值不能替代未执行的独立重载或平台编译。
3. **画布**：正常阅读缩放检查层次、19 组的实际成员（仅本样本）、连线穿越和可读性。
4. **效果**：在同材质参数、模型、镜头、光照、时间与目标平台下比较源 ASE 与目标 SG，特别检查颜色空间、Gamma、噪声、透明混合和动态输入。

Target、内建输入折叠和噪声等价的具体核对规则见第 7–10 节；最终验收边界见本章末尾。

### 7. Target 混合/阴影状态必须从源 Master 读取，禁止硬编码

1. 定位源 ASE **活跃 Master**，按实际 Pass 和模板读取选项，不以任意 Master 或默认值替代。本次 ASE 1.9.6.2 样本的选项位于序列化尾部 `Standard;` 后，按 `Name;value;0;...` 三元组排列，第三位为布局哨兵；按 `i += 3` 步进，不能按 `i += 2` 解析，也不能先删空字段造成错位。先确认当前版本的选项起点与格式，不把样本布局推广到所有模板；未知字段或格式须保留并核对。
2. 将源选项转换为 Target：本样本 `Surface;1` = Transparent、`Blend;3` = Multiply、`Cast Shadows;0` = 关。v2 已支持 `target.surface: Transparent`、`target.blend: Multiply`、`target.options.castShadows: false`；这类失真首先检查转换器是否正确读取源 Target，不归因于 SGCLI 缺能力。
3. 同时核对混合模式与颜色链。ASE 常以 `lerp(float3(1,1,1), C, _Transparent)` 配 Multiply，白色表示不改变背景；原 Shader 的 `Blend DstColor Zero, One Zero` 与该颜色链共同决定效果。任何混合模式变动都必须连同颜色链及透明参数一起审查，不能只改 Target 数值。
4. 落地后运行 `sgcli sg inspect <目标.shadergraph> --mcp-url <URL>`，将 `m_AlphaMode`（本样本 0=Alpha、3=Multiply）、`m_CastShadows`、`m_SurfaceType`、`m_RenderFace` 或当前版本对应字段，与源 Master 逐项对照。inspect 未暴露的字段必须从原生资产或受支持的 Editor 读取补证，不把字段缺失视为默认值正确。

事故样例：曾把 Multiply 硬编码为 Alpha，并按 Alpha 0.5 再次混合，造成大面积乳白、发灰和遮挡背景；恢复 `m_AlphaMode: 0` → `3` 是该次失真的主要修正。

### 8. 世界坐标内建输入的折叠是预期，不是降级

1. 目标 SG 节点没有对应输入端口时，先沿源 ASE 连接核对上游类型和实际计算。只有输入确实来自 `WorldPosInputsNode`、`WorldNormalVector` 等对应世界坐标内建量，且未经过偏移、扰动或其他运算，才继续判定为内建输入折叠；不能仅凭类型名称跳过语义核对。
2. 按空间与向量语义选择目标：`TransformWorldToObject(P)` 对应 Object 空间 `position`，`GetWorldSpaceNormalizeViewDir(P)` 对应 World 空间 `view-direction`。`TransformWorldToViewDir(N,true)` 只有在 N 确为世界法线、归一化及法线来源一致时，才对应 View 空间 `normal`；任意世界方向不能直接替换为法线。通过配置目录确认 `settings.spacePopup` 的 Object/World/View 等实际取值。
3. 确认 SG 内建节点自行计算的量与源输入相同后，折叠该输入连接，不登记 `degradation`；在映射记录中注明“内建输入折叠”及来源，便于对账。SG 没有输入槽不等于丢失计算，也不是删除源节点全部其他消费者的许可。
4. 来源不是对应内建量，或空间、阶段、归一化、法线来源尚未证明一致时，登记缺口并人工核对，保留原计算或选择函数兜底，禁止静默丢弃。

### 9. 噪声等价对照 SG 实现，不凭名字臆断

1. 取得源表达式与当前 SG 版本、算法模式的实现，逐节点比较哈希序列、渐变方向、距离度量、插值曲线、输入缩放及输出范围；判定依据是公式和边界行为，不是“自定义表达式 = 不保真”。
2. 本次样本的 Gradient Noise 使用 `Hash_Tchou_2_1`，哈希、渐变、五次平滑和 `+0.5` 与 SG 14.1 Deterministic 实现一致；满足这些条件时可等价还原为 `gradient-noise`，不登记降级。本次曾将三个 Gradient Noise 标成“算法不同”，属于误报，不应沿用。
3. 本次 Voronoi 使用 `length(...)` 返回距离，并非距离平方；对照 SG Deterministic 的 `Hash_Tchou_2_2` 与 `distance(...)`，同时确认随机偏移、邻域搜索及所用输出一致后，可等价还原为 `voronoi`，不登记降级。不能把某一版本/模式的结论套到所有 Voronoi。
4. 保存实现版本和对照结论；一致则记录等价映射，有差异或未确认则明确登记并继续核对，不能凭节点名判定相同，也不能凭 CustomExpression 类型判定降级。

### 10. 结构验收必须包含 Target 渲染状态

1. 在第 6 节结构验收中建立源与目标的逐项对照，至少包含：输出依赖、常量与属性、纹理绑定、空间/精度/阶段、关键词，以及 **Target 表面类型、混合模式、阴影与剔除状态**。字段缺失、默认值未核实和未知枚举均不得直接判通过。
2. 联合审查 Target 和颜色链，特别检查 Multiply 被改成 Alpha、Cast Shadows 从 false 变为 true 等变化；Target 状态变化对画面的影响可能大于单条节点差异，节点/连线数量和编译通过不能补偿这些差异。
3. 将每项差异标为等价映射、经用户确认的语义调整或待修复问题，并附来源及读回证据。Target 核对仍属于结构/语义验收，后续继续执行第 6 节的真实画布与同条件渲染对照。


### SGCLI 升级实现状态（2026-09-11）

SGCLI 工作树已新增 v3 名称绑定、机械类型/编码接口及事务诊断。使用前确认实际 CLI 和桥接能力；未发布的工作树修改不能当作已安装版本能力。v3 优先精确匹配槽位名；仅在没有精确结果时允许唯一的去类型后缀基础名匹配，例如 `X`→`X(1)`，零个或多个候选都失败关闭。v2 数字创建及编辑契约继续保留。


**验收边界：结构证据 ≠ 视觉等价。** 类型映射、设置名、函数字段存在、147 节点/157 连线/15 属性/19 组读回，以及 Editor 编译成功，均只能证明对应层面的结果。即使 Target/混合与阴影状态已逐项对齐、颜色链语义已核对、噪声算法已有等价依据，也不能替代相同材质参数、模型、镜头、光照、时间与目标平台下的渲染比较。分别记录 Target 状态、颜色链语义、噪声算法对照、真实画布及渲染验收的通过/失败/未执行；未实际完成的部分必须标记“未执行”，禁止用结构或编译结果补写为视觉通过。

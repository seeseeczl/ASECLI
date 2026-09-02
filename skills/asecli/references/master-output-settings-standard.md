# ASE Master / Output 设置规范

## 目标

在不改变既有 Shader 表现的前提下，优先保持模板默认值和最大平台兼容性；只按项目真实需求启用 Master / Output 节点下方的可选能力，避免生成无用 Pass、Shader 变体或运行时计算。

## 基础设置默认保持不变

- 以当前 Shader、同项目模板和渲染管线的既有 Master / Output 设置为基线。上方基础生成设置默认只读；没有明确需求和目标平台证据时，不主动调整 Workflow、Surface、Blend、Cull / Two Sided、Render Queue、Tags、Precision、Shader Model、渲染路径或模板。
- 不主动缩窄 renderer / platform 列表，不添加平台排除，不为单一开发机提高 Shader Model。需要新增能力时，使用能满足效果的最低特性等级，并确认目标 Unity / Tuanjie、渲染管线和目标设备支持。
- 不把“可能更快”当作修改基础设置的充分理由。会改变透明排序、深度写入、光照路径、法线空间、剔除或混合结果的选项，必须由明确效果需求驱动。
- 若现有基础设置与目标平台已经冲突，先报告冲突、受影响平台和最小修改方案；没有用户授权时保持原值，不顺手迁移模板或渲染路径。

## 下方端口与功能开关按需判断

下方可选端口和功能开关可以根据实际用途启用或关闭，但每个决定都必须能对应到真实节点链、场景能力或验收效果。没有使用证据的选项默认不新增；已有选项不能仅凭名称猜测后关闭。

- Normal、Emission、Metallic / Specular、Smoothness、Occlusion、Alpha / Alpha Clip、Vertex Position 等可选输出，只在图中确有对应计算链且最终效果需要时勾选。没有输入数据或只会使用模板默认值时，不为了“完整”全部打开。
- Alpha、Alpha Clip、Vertex deformation、Refraction、Transmission、Tessellation 等会连带改变渲染路径、Pass 或平台要求的端口，先满足上方基础设置不变的约束；若两者冲突，先报告再修改，不能为勾选端口静默改 Surface、Blend、Cull 或 Shader Model。
- 勾选后必须把它接入真实计算并验证生成结果；取消勾选前确认其计算链和外部消费者都已不再需要，避免隐藏端口后遗留无效节点或改变现有效果。

| 能力 | 启用依据 | 不需要时的成本控制 |
| --- | --- | --- |
| Cast Shadows | 物体必须参与实时或烘焙投影 | 可避免额外 ShadowCaster 绘制；关闭前确认不会丢失阴影 |
| Receive Shadows | 材质需要接收主光或附加光阴影 | 可减少相关片元计算；关闭会直接改变受光结果 |
| GPU Instancing | 同材质存在大量实例，且实例数据路径兼容 | 不因“可能有用”强开；也不要为减少变体而关闭已验证的批处理收益 |
| LOD CrossFade | 项目确实使用 LODGroup 淡入淡出 | 未使用时关闭，避免无用关键字、变体和抖动计算 |
| Built-in Fog | 目标场景和渲染管线使用该 Shader 的雾效 | 未使用时关闭，避免无用插值与片元雾计算 |
| Meta Pass | 材质参与 Lightmap、烘焙 GI 或发光烘焙 | 纯实时且不参与烘焙时才可关闭；先确认烘焙链路 |
| Extra Pre Pass / Write Depth / Early Z | 透明排序、深度预写或明确的过绘制治理需要 | 默认不额外增加 Pass；启用前用目标场景证明收益大于额外绘制 |
| Forward Only | 材质能力无法或不应进入 Deferred / GBuffer | 由渲染路径要求决定，不为局部调试随意切换 |
| Transmission / Translucency / Clear Coat | 画面明确使用对应光照层 | 未使用时关闭，避免额外采样、光照分支与变体 |
| DOTS Instancing | 项目实际使用 Entities / DOTS 对应渲染路径 | 非 DOTS 项目不启用 |
| Tessellation | 目标平台支持，且轮廓或位移确实依赖细分 | 默认关闭；它会显著缩小平台覆盖并增加几何阶段计算 |
| Debug Display | 目标调试流程明确依赖 | 生产交付不因临时排查长期保留 |

表中未列出的可选开关沿用同一原则：先确认功能消费者，再判断生成的 Pass、关键字、变体、顶点 / 片元计算和平台约束，最后选择最小充分集合。

## 计算与复用原则

- 相同结果优先复用已有输出、Register / Get Local Var 或公共子链，不复制一套等价节点；一次性、相邻且清晰的计算保持直连。
- 不连接到有效 Master 输出、也没有 Custom GUI、HLSL 或工程源码外部消费者的节点，先用 `graph-audit` 进入人工候选；确认无效后再清理，不能仅凭“没有连线”删除 Property。
- 不为一个默认关闭的功能预先搭建完整计算链。确需开关时，确认关闭路径不会仍执行昂贵采样或重复计算；静态分支、动态分支和 Shader variant 的选择以目标管线实测为准。
- 优化只处理已证明无用或可复用的计算，不以降低精度、改变光照模型或牺牲平台一致性换取未经测量的收益。

## 修改与验收边界

- 当前 ASECLI 将 Master 节点序列化视为 opaque。除已登记的语义命令外，不使用 `set-field` 或 raw 行猜写这些设置；通过真实 ASE Editor 修改，并保留修改前后对照。
- 修改前记录 Master / Output 上方基础设置和下方开关；修改后执行 `asecli validate`、真实 `recompile`，并核对生成的 Pass / keywords / variants 是否与决定一致。
- 在声明支持的每个目标平台或图形 API 上检查编译与画面；“本机编译通过”不能证明最大平台兼容性。任何目标平台不可用时，都应把该平台明确标记为未验证。
- 性能结论必须来自目标场景的变体数量、Pass / draw call、GPU 时间或平台分析数据之一；仅凭节点更少或代码更短不能宣称性能提升。

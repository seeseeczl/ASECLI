# AseCLI

**让 AI Agent 创建、修改、校验、整理与编译 Amplify Shader Editor（ASE）文件。**

AseCLI 是一个面向 AI Agent 的本地 CLI 工具。它把 ASE 嵌在 `.shader` / `.asset` 文件里的节点图当作纯文本数据来解析和修改——不依赖 Unity 即可完成 90% 的操作；只在需要重新生成编译后 HLSL 时，通过 MCP for Unity 触发一次 Unity/团结引擎重编译。

```
你：提需求（"给这个 shader 加个可调描边"）
Agent：设计节点图 → asecli 写文件 → 校验 → 触发编译 → 你验收效果
```

## 能力总览

| 领域 | 能力清单 | 是否需要运行中的 Unity/Tuanjie |
| --- | --- | --- |
| 图读取与安全检查 | 解析节点/连线、结构校验、CHKSM 校验与修复、无效节点审计 | 否 |
| 图编辑 | 设置已知字段、schema 驱动或原始行加节点、连线/断线、受保护删节点、最小差异写回 | 否 |
| 图整理 | 分层网格布局、原生 Comment 框创建/嵌套、真实节点边界检查与自动收框、Local Var 治理规则 | 创建/检查真实边界时需要 |
| 材质 Inspector | 原生 MZGUI 优先；缺失时才注入 ASECLI ShaderGUI fallback。两者兼容 `FoldoutMzgui`、`TooltipMzgui`、`HelpBoxMzgui` 和条件置灰 `EnableIfMzgui`；默认只生成 Tooltip，HelpBox 由用户按需添加 | 写元数据否；安装、重编译和最终 Inspector 验收需要 |
| Shader 创建 | 从已满足属性呈现契约的编译壳克隆；或由严格 `EditorGraphSpec v2` 让 ASE 自己创建节点、连线、保存和重载核对 | Editor 后端需要 |
| 编译桥接 | 通过 MCP for Unity 请求 ASE 重新生成 HLSL，并验证工具结果/保存语义 | 是 |
| Agent 集成 | 全部子命令单行 JSON 输出；稳定错误码与退出码，适合 Agent 子进程编排 | 否 |
| 工程交付 | 双 Python CI、锁文件、回归目录、可复现 wheel/sdist、SBOM、供应链与许可证检查 | 否 |

核心实现特性：

- **纯文本读写引擎**：真实样本逐字节 roundtrip 一致；布局只改变坐标，其他写操作会先执行结构校验。
- **节点 schema 库**：295 种节点类型的参数结构来自 ASE 运行时序列化提取；未知或版本不兼容的结构拒绝猜写。
- **安全写入**：写前比对 SHA-256 快照、加独占锁、拒绝符号链接和陈旧快照；既有文件写入前生成相邻 `.bak` 备份。
- **受控 Editor 创建**：固定 C# 执行器 + 白名单 JSON 规格，拒绝任意 C#、任意反射字段和不支持版本的降级写入。
- **属性呈现契约**：所有由 `create` 生成的 ASE Shader 必须满足 `asecli.property-presentation.v2`；公开属性使用中文显示名和中文 Tooltip，GUI 自动追加英文变量名与 Shader 默认值。HelpBox 是用户可选内容，不参与合规门禁。
- **证据分层**：文本/自动化通过不等于真实 Editor、目标 Inspector 或最终渲染画面通过；README 会明确标注这些边界。

## 环境要求

- Python >= 3.10，[uv](https://docs.astral.sh/uv/)
- 查看/修改/校验/布局：不需要 Unity
- Editor 创建/编译（`create --backend editor` / `recompile`）：Unity/团结引擎打开目标工程 + MCP for Unity 会话已启动

## 安装与运行

项目以 MIT 许可证开源，源码在 [seeseeczl/ASECLI](https://github.com/seeseeczl/ASECLI)。当前版本为 `v0.6.1`；尚未上传 PyPI 或 CLI Hub。需要回滚时可安装不可变的 `v0.6.0`、`v0.5.0`、`v0.4.2`、`v0.4.1`、`v0.4.0`、`v0.3.1`、`v0.3.0`、`v0.2.0` 或 `v0.1.0`。

### 方式一：从 GitHub 安装（推荐）

先安装 [uv](https://docs.astral.sh/uv/)：

```bash
uv tool install git+https://github.com/seeseeczl/ASECLI.git
asecli install-skill
asecli --help
```

锁定正式版本：

```bash
uv tool install git+https://github.com/seeseeczl/ASECLI.git@v0.6.1
asecli install-skill
```

或从 GitHub Release 安装已校验的 wheel：

```bash
mkdir asecli-v0.6.1
cd asecli-v0.6.1
gh release download v0.6.1 --repo seeseeczl/ASECLI
shasum -a 256 -c SHA256SUMS
uv tool install ./asecli-0.6.1-py3-none-any.whl
asecli install-skill
asecli --help
```

`uv tool install` 会为 ASECLI 创建独立 Python 环境，并把 `asecli` 命令放到用户命令路径，不污染现有项目环境。升级或覆盖本机安装时使用：

```bash
uv tool install --force git+https://github.com/seeseeczl/ASECLI.git
asecli install-skill
```

### 配套安装 Agent Skill（后续正式版本）

`v0.3.1` 起，正式 wheel 会同时携带 `asecli` Agent Skill；安装时使用下面的一条命令即可把 CLI 与 Skill 一并安装：

```bash
uv tool install --force git+https://github.com/seeseeczl/ASECLI.git && asecli install-skill
```

`install-skill` 会把随 wheel 校验并打包的 `asecli` Agent Skill 安装到 `$CODEX_HOME/skills/asecli`（未设置时为 `~/.codex/skills/asecli`）。其中包含正式的 ASE 节点图精排规范：左到右阶段列、重复分支模板、Comment 边界、连线通道与真实 ASE 画布验收边界。它是幂等的；若目标已有不同内容会拒绝覆盖，避免改写用户自定义 Skill。

Python wheel 安装遵循无 post-install 副作用的规范，`uv tool install` 本身不会擅自写入 Codex 配置目录；上面的命令将两个受控安装步骤串成一次操作，不依赖隐藏的安装副作用。

回滚到上一正式版：

```bash
gh release download v0.6.0 --repo seeseeczl/ASECLI
uv tool install --force ./asecli-0.6.0-py3-none-any.whl
```

卸载：

```bash
uv tool uninstall asecli
```

正式版本与校验资产见 [ASECLI v0.6.1](https://github.com/seeseeczl/ASECLI/releases/tag/v0.6.1)。`v0.6.0`、`v0.5.0`、`v0.4.2`、`v0.4.1`、`v0.4.0`、`v0.3.1`、`v0.3.0`、`v0.2.0` 与 `v0.1.0` 仍保留为不可变回滚点。

### 方式二：源码开发运行

```bash
git clone https://github.com/seeseeczl/ASECLI.git
cd ASECLI
uv sync --frozen
uv run --frozen asecli --help
```

后续所有示例中的 `asecli` 都可替换为 `uv run --frozen asecli`，无需向全局环境安装任何内容。

### 方式三：从源码安装为本机命令

```bash
git clone https://github.com/seeseeczl/ASECLI.git
cd ASECLI
uv tool install .
asecli --help
```

### 方式四：安装受控的本地 wheel

适用于管理员通过其他受控渠道交付 wheel 的情况。只安装同时提供 `SHA256SUMS` 且校验通过的文件：

```bash
shasum -a 256 -c SHA256SUMS
uv tool install /path/to/asecli-0.1.0-py3-none-any.whl
asecli --help
```

升级源码副本时使用 `git pull --ff-only` 后重新执行 `uv sync --frozen`。若 lock 检查失败，不要跳过冻结安装；先解决 `uv.lock` 与项目声明的不一致。

## 快速上手

```bash
# 1. 查看 shader 的节点图
asecli parse MyShader.shader

# 2. 校验结构
asecli validate MyShader.shader

# 3. 改一个节点的某个字段（field 是绝对下标：0=Node, 1=类型, 2=Id, 3=坐标, 4+=参数）
asecli set-field MyShader.shader --node 5 --field 12 --value 0.85 --write

# 4. schema 驱动加节点
asecli add-node MyShader.shader --type AmplifyShaderEditor.SaturateNode --id 99 --pos -320,0 --write

# 5. 连线：把 99 的输出 0 接到 6 的输入 0
asecli connect MyShader.shader --from 99:0 --to 6:0 --write

# 6. 兼容模式整理节点布局（只动 x/y）
asecli layout MyShader.shader --write

# 连接运行中的 ASE 后，使用真实节点/端口尺寸做递归鱼骨式精排
asecli layout MyShader.shader --mode meticulous --audit
asecli layout MyShader.shader --mode meticulous --write

# 7. 修复 checksum（默认只预览，显式写入才落盘并保留 .bak）
asecli fix-checksum MyShader.shader --write

# 8. 选择唯一 GUI provider；原生 MZGUI 优先，确认缺失才安装 fallback
asecli gui-support /path/to/UnityProject
asecli gui-support /path/to/UnityProject --write

# 原生包后来加入且检测到双 provider：先预演，再显式交接
asecli gui-support /path/to/UnityProject --runtime-probe --handoff-native
asecli gui-support /path/to/UnityProject --runtime-probe --handoff-native --write

# provider=native_mzgui 时继续使用工程已有 MZGUI。
# --write 只补 authoring/条件置灰扩展，不会注入第二个 MZGUI.MZGUI。
# 安装 fallback 或原生扩展后，在 Unity 中打开：
# Window > Amplify Shader Editor > MZGUI Attributes (ASECLI)

# 使用上一步 JSON 返回的 recommended_editor；也可直接用 ShaderLab 属性名定位
asecli custom-gui MyShader.shader
asecli custom-gui MyShader.shader --editor MZGUI.MZGUI --property _PaintColor \
  --group "固有色" \
  --tooltip "控制车辆基础漆面颜色；Alpha 当前不参与透明度计算。" --write

# 当反射来源等于 2 时启用本地环境属性，否则只置灰且保留原值
asecli custom-gui MyShader.shader --property _BaseEnvironmentTint \
  --enabled-if _BaseReflectionSource --enabled-if-operator Equal \
  --enabled-if-value 2 --write

# 9. 给现有节点增加原生 Comment 框（默认只预览）
asecli comment-group MyShader.shader --nodes 1212,1218 \
  --title "明度越高，强度越小" --write

# 10. 触发 Unity 内 ASE 重新生成 HLSL（需编辑器开启 + MCP 会话启动）
asecli recompile Assets/MyShader.shader

# 11. 从已有编译壳克隆新 shader
asecli create Assets/NewShader.shader --from MyShader.shader --name "NewShader" --force

# 12. 让运行中的 ASE 根据声明式规格创建全新、可重开的节点图
asecli create Assets/NewEditorShader.shader --backend editor --spec graph.json
```

除 `create` 与 `recompile` 外，所有会修改已有 ASE 文件或项目资源的命令都必须显式传 `--write`；未传时仅返回预演结果。`create` 会立即创建目标文件，`recompile` 会立即请求编辑器写回，使用前应先完成路径与目标确认。

## 完整命令目录

所有命令都可用 `asecli <command> --help` 查看参数。下表列出当前全部 16 个公开子命令及其实际副作用。

| 命令 | 做什么 | 写入/运行边界 |
| --- | --- | --- |
| `parse <file>` | 输出 ASE 图版本、节点数、连线数及节点摘要。 | 只读。 |
| `validate <file>` | 检查悬空连线、重复 ID、输入多来源、Local Var 一致性和 CHKSM。 | 只读；有 error 时返回退出码 2。 |
| `graph-audit <file>` | 从 Master 反向分析未参与输出的节点，区分 `unused_candidates` 与外部消费者。 | 只读；Property 的源码/HLSL/GUI 引用不会被误报为可删。 |
| `set-field <file> --node N --field I --value V [--write]` | 修改一个已知节点的绝对序列化字段。 | 默认预演；`--write` 后写入。不要用它猜写 Master 或未知版本尾部。 |
| `add-node <file> --type T [--id N] [--pos X,Y] [--write]` | 按 schema 创建可写节点与默认参数。 | 默认预演；未知、opaque 或版本不兼容节点会拒绝。`--line` 是复用真实序列化行的专家入口。 |
| `connect <file> --from A:P --to B:P [--write]` | 将来源节点输出端接到目标节点输入端。 | 默认预演；`--from` 是数据源，`--to` 是消费者。 |
| `disconnect <file> --from A:P --to B:P [--write]` | 删除一条精确连线。 | 默认预演；找不到该连线会失败。 |
| `remove-node <file> --node N [--force-external] [--write]` | 删除节点及附属连线。 | 默认预演；外部源码仍引用的 Property 默认拒删。`--force-external` 只用于已迁移消费者的明确操作。 |
| `fix-checksum <file> [--write]` | 重算 `//CHKSM`，并报告旧值、实际值和是否已有效。 | 默认预演；`--write` 后写入并备份原文件。 |
| `layout <file> [--mode legacy\|meticulous] [--audit] [--write]` | `legacy` 保留原分层布局；`meticulous` 以 Output 为根递归展开上游子树，按输入端口顺序居中分布，并联动收紧 Comment。 | 默认仍为 `legacy` 且只预演。`meticulous` 单次连接 Editor 获取真实节点、标题栏和端口几何；硬门禁失败或几何缺失时不写盘。 |
| `gui-support <project> [--runtime-probe] [--handoff-native] [--write]` | 优先检测并选用原生 MZGUI；原生环境只安装 authoring/条件置灰扩展，缺失时安装 fallback；原生后来加入时可恢复交接。 | 不创建第二个原生 provider；V2 枚举全部 provider；handoff 默认预演，只处理已知哈希并保留 authoring-only bridge，复验失败可恢复。 |
| `custom-gui <file> [--node N \| --property P] … [--write]` | 查询/同步 CustomEditor；设置或清除 Foldout、Tooltip、用户 HelpBox 和由另一数值属性控制的置灰条件。 | 条件写为 `EnableIfMzgui(source,operator,value)`；不满足时只禁用控件，不清空材质值。`--clear-enabled-if` 可清除。 |
| `install-skill [--skill-root DIR]` | 安装 wheel 内置的 ASECLI Agent Skill。 | 相同内容幂等；目标已有不同内容时拒绝覆盖，不修改 Shader、材质或 Unity/Tuanjie 工程。 |
| `comment-group <file> [--nodes IDS --title T] … [--write]` | 查询、创建、嵌套 ASE 原生 Comment 框；可检查成员越框或重叠。 | 创建默认用离线尺寸估算。`--editor-bounds`、`--check-bounds`、`--fit` 需连接 Editor。 |
| `create <out> --from TEMPLATE [--name NAME] [--graph-from DONOR]` | 复制一个已编译模板壳；可替换图或同步 Shader 名与 CHKSM。 | **立即创建/覆盖目标**；模板和 donor 组合后的文件必须已满足属性呈现契约，否则写前拒绝。 |
| `create <out> --backend editor --spec graph.json` | 用白名单 `EditorGraphSpec v2` 让 ASE 自身创建、保存和重载目标图。 | **立即请求 Editor 写入**；每个 Property 必填中文 `inspector_name` 和中文 `tooltip`，可选 `help` 写用户 HelpBox。仅含旧 `help` 的规格会迁移为 Tooltip。 |
| `recompile <file> [--mcp-url URL] [--allow-remote-mcp]` | 调用运行中 ASE 重新生成 HLSL/保存，并报告 `changed`。 | **立即触发 Editor 操作**；默认仅允许 loopback MCP。 |

### 推荐使用流程

#### 1. 只读检查与结构编辑

```bash
# 先建立基线：读图、校验、审计
asecli parse Assets/Example.shader
asecli validate Assets/Example.shader
asecli graph-audit Assets/Example.shader

# 每一步先预演；确认 JSON 中 written=false 的结果后才落盘
asecli add-node Assets/Example.shader \
  --type AmplifyShaderEditor.SaturateNode --id 99 --pos -320,0
asecli add-node Assets/Example.shader \
  --type AmplifyShaderEditor.SaturateNode --id 99 --pos -320,0 --write
asecli connect Assets/Example.shader --from 99:0 --to 6:0 --write
asecli validate Assets/Example.shader
```

若文件在读取后被 Unity、另一个 Agent 或人工修改，写入会以 `WRITE_CONFLICT` 停止，而非覆盖对方变更。先重新 `parse` / 比较差异，再重新预演。

#### 2. 整理材质 Inspector

```bash
# 先确认唯一 GUI provider；原生 MZGUI 优先
asecli gui-support /path/to/UnityProject

# 仅在 provider=missing 时，预演结果会给出 would_write=true；确认后安装
asecli gui-support /path/to/UnityProject --write

# fallback 安装完成后不需要编写 Attribute 代码：
# Window > Amplify Shader Editor > MZGUI Attributes (ASECLI)
# 选择 Property 节点，编辑 Foldout/Tooltip；需要时再启用 HelpBox 或“条件启用”，然后点击“应用并保存 Shader”。

# 查询属性，再以属性名进行预演和写入
asecli custom-gui Assets/Example.shader
asecli custom-gui Assets/Example.shader --editor MZGUI.MZGUI --property _PaintColor \
  --group "固有色" \
  --tooltip "控制车身基础漆面颜色；Alpha 当前不参与透明度计算。" --write
asecli validate Assets/Example.shader
asecli recompile Assets/Example.shader
```

批量整理时使用 `--spec`，一次预演、一次备份、一次写入；不要逐项反复落盘：

```json
{
  "editor": "MZGUI.MZGUI",
  "reorder": true,
  "properties": [
    {
      "name": "_PaintColor",
      "display_name": "车漆颜色",
      "group": "固有色",
      "tooltip": "控制车身基础漆面颜色；Alpha 当前不参与透明度计算。"
    },
    {
      "name": "_Contrast",
      "display_name": "明暗对比",
      "tooltip": "控制车身明暗对比度；数值越大，对比越弱。",
      "enabled_if": {
        "property": "_BaseReflectionSource",
        "operator": "Equal",
        "value": 2
      }
    }
  ]
}
```

```bash
asecli custom-gui Assets/Example.shader --spec material-gui.json
asecli custom-gui Assets/Example.shader --spec material-gui.json --write
asecli validate Assets/Example.shader
asecli recompile Assets/Example.shader
```

`editor` 必须采用 `gui-support` 输出中的 `recommended_editor`，无论由原生 MZGUI 还是 ASECLI fallback 提供都固定为 `MZGUI.MZGUI`。因此在 fallback 工程中制作的 Shader 可以原样放入已有原生 MZGUI 的工程；四种属性和 `CustomEditor` 都不需要改名。原生工程执行 `gui-support --write` 时只安装 `EnableIfMzguiDrawer` 与可视化 authoring 扩展，不定义第二个 `MZGUI.MZGUI`。`ASECLI.MaterialGUI.ASECLIMaterialGUI` 仅作为旧文件读取兼容别名。`target_conflict`、`unknown` 或 `multiple` 必须人工处理，工具不会覆盖或猜选。

#### 3. 整理图布局、Local Var 与 Comment

```bash
# 兼容布局只移动 x/y，不改参数或连线
asecli layout Assets/Example.shader --gap-x 280 --gap-y 120
asecli layout Assets/Example.shader --gap-x 280 --gap-y 120 --write

# 递归鱼骨式精排：先只读审计，再一次性写入节点坐标、Comment bounds/缺失作用标题
asecli layout Assets/Example.shader --mode meticulous --audit \
  --mcp-url http://127.0.0.1:8080/mcp
asecli layout Assets/Example.shader --mode meticulous --write \
  --mcp-url http://127.0.0.1:8080/mcp

# 只有显式授权时才移动/新增 WireNode；新增锚点由当前 ASE Editor API 完成
asecli layout Assets/Example.shader --mode meticulous --route-wires --audit \
  --mcp-url http://127.0.0.1:8080/mcp
asecli layout Assets/Example.shader --mode meticulous --route-wires --write \
  --mcp-url http://127.0.0.1:8080/mcp

# 先离线预演 Comment，再在连接的 Editor 中以真实尺寸验收/收框
asecli comment-group Assets/Example.shader --nodes 1212,1218 \
  --title "明度越高，强度越小"
asecli comment-group Assets/Example.shader --nodes 1212,1218 \
  --title "明度越高，强度越小" --write
asecli comment-group Assets/Example.shader --check-bounds
asecli comment-group Assets/Example.shader --fit --padding 30 --write
```

先按 Comment/算法组归类消费者。同一节点或算法结果被两个及以上不同组消费时，必须在生产者右侧使用一个 `Register Local Var`，并在各消费组输入侧使用就近的 `Get Local Var`；全部消费者都在同一组内时，无论复用多少次都允许直连。普通 schema 不会猜造动态 `RegisterLocalVarNode`，应通过真实 ASE 创建或复用同版本、同类型的真实序列化样本。

#### 4. 创建与编译

```bash
# 文本后端：立即新建目标；模板和 donor 组合结果必须已经满足属性呈现契约
asecli create Assets/NewShader.shader --from Assets/Template.shader \
  --name "Vehicle/NewShader" --graph-from Assets/Donor.shader

# Editor 后端：严格 JSON 规格，目标必须尚不存在且在 Assets/ 中
asecli create Assets/NewEditorShader.shader --backend editor --spec graph.json

# auto 在有 --spec 时路由到 editor；无 spec 时仍走 text
asecli create Assets/NewEditorShader.shader --backend auto --spec graph.json
```

Editor 后端当前只支持 ASE `1.9.6.2` 的已验证白名单和模板端口。成功会返回模板、Shader 名、节点/端口/连线 manifest；随后仍须在新 Editor 进程重开目标并完成材质、平台编译和渲染画面验收。

### Editor API 创建

默认 `create` 仍是原有纯文本后端。`--backend editor --spec graph.json` 明确使用 Editor；`--backend auto` 在提供 `--spec` 时选择 Editor，否则选择文本后端。Editor 目标必须位于 Unity/Tuanjie 工程的 `Assets/` 下且尚不存在，不允许 `--force`。

最小 Caster-like 规格：

```json
{
  "version": 2,
  "template": {
    "guid": "2992e84f91cbeb14eab234972e07ea9d",
    "shader_name": "Vehicle/LocalShadow/Caster"
  },
  "nodes": [
    {
      "alias": "mask",
      "kind": "sampler",
      "position": [-520, 20],
      "property_name": "_CasterMask",
      "inspector_name": "投射遮罩",
      "tooltip": "控制投射遮罩贴图；白色区域显示阴影，黑色区域不显示。",
      "parameter_type": "Property"
    }
  ],
  "connections": [
    {"from": {"node": "mask", "port": 1}, "to": {"node": "master", "port": 2}}
  ]
}
```

- CLI 创建要求 `EditorGraphSpec v2`。每个 Property/Sampler 必须提供含中文的 `inspector_name` 和 `tooltip`；用户可另加可选 `help` 生成 HelpBox。旧 v2 只有 `help`、没有 `tooltip` 时按 Tooltip 迁移读取且不生成 HelpBox；v1 仅保留底层桥接兼容。
- 首期绑定 ASE `1.9.6.2`；Master 端口契约只开放已实测的 URP Unlit 模板 GUID。未知版本、模板 Master 端口、节点、字段、端口或类型在写入前失败。
- 规格只传 JSON 数据。执行的 C# 来自包内固定资源；Custom Expression 的 HLSL 是可编辑节点内容，但任意 C#、任意反射字段和危险运行时标记不会透传。
- 保存成功必须同时满足 Save、暂存重载、模板 GUID/Shader 名、节点/属性/动态端口/连接 manifest、移动提交和目标 Shader 身份一致；Editor 事务失败会回滚明确的目标/暂存资产并恢复原 ASE 窗口状态。为避免 MCP 插件重连吞掉成功回执，同一次创建调用不再重复加载目标图。成功 JSON 中 `reloaded` 与 `staging_reloaded` 表示暂存图已 LoadFromDisk；`target_graph_reloaded` 恒为 `false`。CLI 属性收尾后必须使用独立 `recompile` 完成目标图重载复验。若提交后 Python 后验解析失败，CLI 为避免竞态误删会保留目标和 `.meta`，并返回 `transaction_nonce`、Shader/meta SHA-256 供人工核对。
- MCP 3.4.7 默认按源码模式拦截 `AssetDatabase.DeleteAsset`。CLI 仅对包内固定、参数已校验且暂存名带随机 nonce 的事务执行器设置该次 `safety_checks=false`；不会把用户 C# 透传到这一入口。
- MCP 客户端超时代表完成状态未知，不等同于 Editor 已停止或已回滚。初始化握手共用 20 秒总预算，真实 `tools/call` 保留 120 秒执行预算；超时 JSON 会给出 `phase`、`elapsed_ms`、`budget_ms` 并返回 `BRIDGE_ERROR`/3。重试前先检查目标文件及同目录 `ASECLI-Temp-*`，避免把迟到成功误判为失败。
- 隔离团结 E2E 已证明 Caster-like/Receiver-like 图可创建、保存、关闭并由新进程重载；这不证明目标工程的运行时矩阵注入、材质绑定或最终渲染画面正确。

## JSON 契约

stdout 恒为单行 JSON，agent 可直接解析：

```json
{"ok": true,  "data": {"node_count": 7}}
{"ok": false, "error": {"code": "NOT_FOUND", "message": "..."}}
```

常见错误码：`PARSE_ERROR`、`NOT_FOUND`、`USAGE_ERROR`、`SCHEMA_UNAVAILABLE`、`SCHEMA_VERSION_MISMATCH`、`VALIDATION_ERROR`、`PROPERTY_PRESENTATION_ERROR`、`LAYOUT_ERROR`、`CHECKSUM_FORMAT_ERROR`、`GUI_SUPPORT_ERROR`、`CUSTOM_GUI_ERROR`、`COMMENT_GROUP_ERROR`、`EXTERNAL_REFERENCE`、`WRITE_CONFLICT`、`UNSAFE_PATH`、`WRITE_ERROR`、`BRIDGE_ERROR`、`INTERNAL`。
退出码：`0` 成功 · `2` 用法/校验/解析错误 · `3` 桥接错误

## ASE 格式备忘（Agent 必读）

1. 节点图嵌在 `/*ASEBEGIN ... ASEEND*/` 块中，行式指令流：`Node;...` 与 `WireConnection;...`
2. `WireConnection;<入节点>;<入端口>;<出节点>;<出端口>` —— **目的地在前，来源在后**
3. `//CHKSM=` = 整个文件（`//CHKSM=` 之前部分）的 SHA1 大写 hex；校验失败**不阻断** ASE 加载
4. Master 节点（TemplateMultiPassMasterNode 等）序列化布局为 opaque：用 `--line` 整行替换或 `layout` 移动
5. 主 Master `CustomEditor` 的离线同步仍受已验证图版本约束；fallback 的属性编辑不再读写 ASE 私有 PropertyNode 尾部，而是通过 Editor 内运行时能力探测使用 ASE 原生 Custom Attributes。请用 `gui-support` 与 `custom-gui`，不要用通用 `set-field` 猜私有结构；关键成员无法确认时会失败关闭

### 自定义 GUI 分组规则

- `asecli.property-presentation.v2` 是硬门禁：每个导出 Property 必须使用中文 `display_name` 和一条中文 `TooltipMzgui`。HelpBox 可有可无，不参与门禁。GUI 自动在 Tooltip 末尾追加英文变量名与 Shader 默认值。
- 新 Property 通过 EditorGraphSpec v2 的 `inspector_name`/`tooltip` 写入；已有属性使用 `custom-gui --spec` 的 `display_name`/`tooltip` 原子治理。只有用户显式提供 `help` 时才新增或更新 HelpBox，省略不会清理既有内容。
- `--group` 写 `FoldoutMzgui`，`--tooltip` 写 `TooltipMzgui`。目标属性成为分组首项，后续属性一直归入该组，直到下一个带非空分组标题的属性。
- `--property _PaintColor` 可替代节点 ID；批量整理使用 `--spec`。`reorder=true` 按 `properties` 数组重写 PropertyNode 的 `m_orderIndex`，未列属性保持原相对顺序并追加。
- ASECLI GUI 会在中文 Tooltip 后自动追加准确变量名与默认基线，并通过默认 `Material(shader)` 读取真实 Shader 默认值，不使用当前材质实例值；不要手工复制这些技术信息。
- `--help-box` 写入用户自定义常驻内容，`--clear-help-box` 清除它。fallback 编辑窗口提供 HelpBox 开关和文本框，但默认关闭；HelpBox 不能替代必填 Tooltip。
- `--enabled-if SOURCE --enabled-if-value VALUE` 写入 `EnableIfMzgui`；比较方式默认为 `Equal`，也支持 `Less`、`LessEqual`、`NotEqual`、`GreaterEqual`、`Greater`。条件不满足、控制属性缺失或多选材质中任一项不满足时，Drawer 用 `EditorGUI.DisabledScope` 置灰；不会改写目标属性值，也不是 Shader 渲染分支。
- 先运行 `gui-support <project>`；发现原生 `MZGUI.MZGUI` 时直接使用它，并以 `--write` 安装不含第二 provider 的 authoring/条件置灰扩展。只有确认不存在 MZGUI 时，`--write` 才注入 ASECLI fallback。两种路径使用相同的 `FoldoutMzgui`、`TooltipMzgui`、`HelpBoxMzgui`、`EnableIfMzgui` 名称。
- 若 fallback 安装后又导入原生 MZGUI，使用 `--runtime-probe --handoff-native` 预演并以 `--write` 执行。工具保留 authoring-only bridge 负责把便携 Custom Attributes 幂等迁入原生 Toggle/文本状态，不保留第二个 `MZGUI.MZGUI` provider；未知哈希或复验失败不会静默删除文件。
- `custom-gui --write` 会同步图内主 Master 与编译区 `CustomEditor`、重算 `CHKSM` 并保留 `.bak`；Property 属性声明由 ASE 生成，因此随后必须执行 `validate` 和 `recompile`。

### GUI Editor 支持边界

| Editor / API 条件 | 当前结论 | 证据 |
| --- | --- | --- |
| 团结引擎 `2022.3.61t9`，具备 `ShaderUtil.GetShaderPropertyAttributes` | fallback 支持 `FoldoutMzgui`、`TooltipMzgui`、`HelpBoxMzgui` 的读取、编辑和轻量常驻说明渲染；可读取默认值 | 隔离工程 `tests/test_material_gui_e2e.py` BatchMode 与既有 Inspector 实测证据 |
| 缺少该 `ShaderUtil` 方法、仅依赖 `MaterialPropertyHandler` fallback 的版本 | 代码提供 legacy decorator fallback，但尚无实机验证；不纳入已发布兼容矩阵 | 需要在目标版本补跑同一隔离测试后才可宣称支持 |

BatchMode 只验证编译与元数据，不替代实际 Inspector 中的 Tooltip 悬停、Foldout 点击和 HelpBox 视觉验收。

批量规范示例（`editor` 必须使用 `gui-support` 返回的 `recommended_editor`）：

```json
{
  "editor": "MZGUI.MZGUI",
  "reorder": true,
  "properties": [
    {"name": "_PaintColor", "display_name": "车漆颜色", "group": "固有色", "tooltip": "控制车辆基础漆面颜色。"},
    {"name": "_Contrast", "display_name": "明暗对比", "tooltip": "控制车身明暗对比度；数值越大，对比越弱。"},
    {"name": "_Coat_IO", "display_name": "清漆开关", "group": "清漆层", "tooltip": "控制是否启用清漆层。"}
  ]
}
```

### ASE 节点图 Comment 规范

- 以连线清晰和紧凑为先。默认使用单层小组，只包围一个紧密算法单元；不建立覆盖整片区域的大总框，不为了分组强行组套组。
- 离线创建只能按坐标和保守尺寸估算；普通节点的真实宽高并不写入 ASE 文本。使用 `--editor-bounds` 创建，或在创建后用 `--check-bounds`/`--fit` 读取 live ASE `TruePosition` 做精确验收和校正。
- `--fit` 只调整 Comment 的位置和宽高，不移动成员、不改参数和连线。可用 `--padding 30` 生成统一紧凑边距；命令默认 dry-run。
- 先完成节点和 Local Var 排布，再创建/校正 Comment；若 Comment 造成交叉线、蜘蛛网或大面积留白，则缩小分组或不分组。
- 标题和说明禁止分号/换行；默认 dry-run，`--write` 才写入、重算 CHKSM 并保留 `.bak`。

```bash
# 精确检查是否有节点超出框
asecli comment-group My.shader --check-bounds --mcp-url http://127.0.0.1:9080/mcp

# 按 ASE 真实节点尺寸统一留 30 单位边距，先预览再写入
asecli comment-group My.shader --fit --padding 30 --mcp-url http://127.0.0.1:9080/mcp
asecli comment-group My.shader --fit --padding 30 --mcp-url http://127.0.0.1:9080/mcp --write
```

### 节点图精排规范

- `meticulous` 从最终 Output 向左递归形成局部鱼骨：每个节点都可成为上游的主骨；1 个来源直接水平，3/5/7 等奇数来源以中位分支水平，偶数来源在中间两支中优先选择更完整的主要数据链，其余完整子树平均分布到上下两侧。
- 水平对齐以真实输入/输出端口为准；同一父节点的直属来源共享一条局部输出对齐线。每一级都重复同一规则，相邻层边界保持 `64–160px`（目标 `96px`），不会因无关并行模块宽度不同而拉成长线，也不会用最上方分支持续拉出长斜线。
- 普通兄弟子树垂直间距至少 `32px`，父子节点边界水平间距为 `96px`，不同 Comment/语义模块之间至少 `96px`。真实节点尺寸决定列宽，不再使用 `200x120` 估算值做精排。
- Editor 几何桥会把缩放后的 `GlobalPosition`/端口坐标还原为 `TruePosition` 图坐标；多 Pass 中没有连线且不参与当前画布的零尺寸 Master 占位保持原位，若零尺寸节点仍有连接则失败关闭。
- Register 靠近生产者右侧，Get 靠近直接消费者左侧；布局器不会自动创建、删除或改写 Local Var。共享节点只选择一个主父级，其余连线作为次级边审计，不复制节点。
- 精排完成后 Comment 自内向外收框：左右/底部 `30px`、顶部标题区 `48px`，无关组保留至少 `96px` 通道。已有 Comment、成员、嵌套和颜色不得删除或改变；有效标题原样保留，占位标题只在唯一 Register、唯一框外消费者或唯一局部终点可可靠推断时补齐，否则阻止写入。
- 审计输出 `asecli.graph-layout.v2`，区分硬性失败与允许但需关注的线线交叉；自动通过后仍返回 `visual_validation=requires_editor_review`，不冒充正常缩放下的最终人工视觉签收。
- 核心目标是“经过人工精心排列”的秩序感：主数据流从左向右层层递进，Master 最右；同阶段严格列对齐，主链尽量水平，重复分支使用完全一致的列、行距和内部模板。
- 组内紧凑、组间留出明显通道，并列模块和 Comment 边框也要对齐；无父子关系的组不得重叠，父子组只允许完整包含。
- 同组直连也必须整理线路。普通 `meticulous` 保持既有 WireNode 坐标且不新增锚点；只有 `--route-wires` 才先移动既有 WireNode、再为仍有穿越/交叉的直连增加最多 2 个锚点。新增节点通过运行时能力探测后的 ASE Editor API 创建，折叠 WireNode 后逻辑连接必须完全等价，失败恢复写前备份。
- Local Var 以去重后的消费组数量为准：两个及以上不同组必须注册；同组内多次使用允许不注册。跨阶段数、线长和遮挡只用于排版与 Get 放置，不覆盖这个门槛。
- 完整规则与量化/视觉验收边界见 [`skills/asecli/references/layout-standard.md`](skills/asecli/references/layout-standard.md)。真实 ASE 画布仍需复核精排感、贝塞尔线路径和组间关系；编辑器或 MCP 不可用时应明确报告未验证。

### Master / Output 设置规范

- 上方基础生成设置默认继承当前 Shader 和项目模板，不主动改变 Workflow、Surface、Blend、Cull、Render Queue、Precision、Shader Model、渲染路径或平台列表；优先保持最大平台兼容性。
- 下方 Normal、Emission、Alpha、Vertex Position 等可选端口，以及 Cast/Receive Shadows、GPU Instancing、Fog、Meta、Depth、Clear Coat、DOTS、Tessellation、Debug 等功能开关按真实用途判断，只保留有节点链、消费者或验收依据的能力。
- 不为可能使用的功能预建昂贵计算链，不复制等价计算；但也不能只为减少 Pass 或变体就关闭会改变既有效果的能力。
- Master 节点序列化仍是 opaque。除已登记的语义命令外，必须在真实 ASE Editor 中修改并完成编译、画面与目标平台核对，不得用 `set-field` 或 raw 行猜写。
- 完整决策表、成本边界与验收要求见 [`skills/asecli/references/master-output-settings-standard.md`](skills/asecli/references/master-output-settings-standard.md)。

### 无效节点审计

- `graph-audit` 从有效 Master 输出反向追踪 Wire 和 Register/Get Local Var，列出不通向输出的节点。
- 无 ASE 连线不等于无效。Property 若被 Custom ShaderGUI、HLSL 或其他工程源码引用，会进入 `external_consumers`，不会被报告为 `unused_candidates`。
- `remove-node` 默认拒绝删除存在外部源码引用的 Property；只有人工确认同时迁移外部消费者时才可显式使用 `--force-external`。

### Local Var 防蜘蛛网规范

- 同一节点输出或算法结果被两个及以上不同 Comment/算法组消费时，必须使用一个 Register 和各消费组就近的 Get；判断按去重后的消费组数量，不按 Wire 数量。
- Comment 表达“算法块做什么”，Local Var 表达“算法块之间传递什么”。两者配合，把跨区长线收敛成模块边界附近的短线。
- 同组/同算法内无论使用多少次都允许不注册，但直连仍不得重叠节点或放任线线交叉；优先整理节点与已有 WireNode，必要时用最少锚点绕开。允许“生产者组内直连、其他消费组用 Get”的有边界混合，禁止 Register 已存在却仍给模块外消费者直连。
- 变量名应唯一且语义明确，例如 `CoatFresnelMask`、`LitValueControl`；避免 `Value`、`Temp1`、`base`。治理记录必须说明去重后的消费组数量、组 ID、模块归属和采用直连/Local Var/混合的理由。
- 当前 `RegisterLocalVarNode` 的端口类型会随输入变化，ASECLI 不允许用不完整 schema 猜造；优先在 ASE 编辑器创建，或只复用同 ASE 版本、同类型的真实序列化样本，随后执行 `validate` 和 `recompile`。

完整操作手册见 [`skills/asecli/SKILL.md`](skills/asecli/SKILL.md)；材质属性四层信息规范见 [`skills/asecli/references/material-property-standard.md`](skills/asecli/references/material-property-standard.md)。

## 编译桥接前提

1. Tuanjie/Unity 编辑器已打开目标工程
2. MCP for Unity 会话已启动（编辑器内 Start Session，默认 `http://127.0.0.1:8080/mcp`）
3. MCP 不能被其他会话独占（`recompile` 报 `BRIDGE_ERROR` 时先检查占用）
4. `recompile` 成功时 `data.changed=true` 表示 HLSL 已重新生成；`changed=false` 表示文件本已最新。Editor 创建成功会返回 `template_guid`、`shader_name` 和 Save/Load manifest

安全边界：默认只允许 `127.0.0.1`、`localhost`、`::1`；远程 MCP 必须显式加 `--allow-remote-mcp`。实例 token 只能通过当前进程环境变量 `ASECLI_MCP_INSTANCE_TOKEN` 提供，禁止写入命令参数、脚本或日志。客户端拒绝 URL 凭证、query、fragment 和 HTTP 重定向，避免 token 被转发。`recompile` 会调用 MCP 的 `execute_code`，因此只能连接你明确信任的编辑器会话。

## 测试

```bash
uv lock --check
uv run --frozen pytest -q                # 全量（桥接测试无环境时自动跳过）
ASECLI_TEST_SHADER=Assets/xxx.shader uv run --frozen pytest -m bridge   # 桥接端到端
ASECLI_EDITOR_CREATE_PROJECT=/path/to/isolated-project \
ASECLI_TUANJIE_PATH=/path/to/Tuanjie \
uv run --frozen pytest -q -m bridge tests/test_editor_create_e2e.py     # 真实 Editor 创建/新进程重载
```

## 开发、质量与交付治理

本项目的治理不是额外的项目管理流程，而是让 CLI 行为、文档、回归与交付证据保持可追溯的最小约束。详细来源分别是 [项目章程](docs/00-governance/project-charter.md)、[交付协议](docs/00-governance/delivery-protocol.md)、[回归目录](docs/03-quality/regression-catalog.md)、[供应链策略](docs/00-governance/supply-chain-policy.md) 和 [追溯表](docs/00-governance/traceability.csv)。

### 日常变更规则

| 变更类型 | 开始前 | 实现与验收要求 |
| --- | --- | --- |
| 一般实现或文档任务 | 在 `task/<task-id>-<slug>` 分支工作；任务至少一次提交，提交信息以 `TASK-xxxx:` 开头。 | 提交前全量测试通过；不要顺带重构、升级依赖或修改无关 Shader。 |
| 新功能 / 需求变更（FR/CR） | 先更新需求基线 `ARCH-REQ-0001` 与 `traceability.csv`，再修改代码。 | 关联模块、任务与回归，保持 `FR → MOD → TASK → REG` 双向可追溯。 |
| 缺陷修复 | 先在回归目录登记能复现失败的 `REG-*`。 | 做最小修复；验证修复前失败场景与修复后回归。 |
| 公共 CLI 契约变更 | 先建立 CR；命令名、JSON 字段、错误码和退出码都属于兼容性边界。 | 更新 `MOD-CLI` 契约、README、SKILL 与相关回归，不以“内部重构”名义静默改变调用方行为。 |
| Unity / MCP / GUI 改动 | 先锁定目标工程与 ASE 版本，避免生产工程作为试验环境。 | 纯 Python 通过后，补隔离 Editor、目标 Inspector 或目标渲染验收；不得用 mock 替代真实界面结论。 |

完成一个有任务卡的工作时，在 `docs/00-governance/timeline.md` 追加时间线，并把验收命令输出/证据回写到任务卡。没有代码行为或公开契约变化的纯 README 校正，不应伪造 FR、CR 或发布记录。

### 本地提交门禁

最小提交前检查如下；应按本次改动风险补充相关的定向测试，而不是只依赖格式检查。

```bash
git diff --check
uv lock --check
uv sync --frozen --python 3.10
uv run --frozen --python 3.10 pytest -q
uv run --frozen --python 3.10 python tools/check_ci_governance.py
uv run --frozen --python 3.10 python tools/check_regression_catalog.py

uv sync --frozen --python 3.12
uv run --frozen --python 3.12 pytest -q
uv run --frozen --python 3.12 python tools/check_ci_governance.py
uv run --frozen --python 3.12 python tools/check_regression_catalog.py
```

如果改动触及 bridge、Editor 创建、材质 GUI、Comment 可视边界或最终渲染，以上自动测试仍不足够：应在隔离工程或目标工程补跑对应 `pytest -m bridge`、Inspector 交互/视觉、平台编译和画面验收，并在交付记录中注明实际环境。

### CI、构建与发布门禁

`.github/workflows/ci.yml` 在 push 到 `main`、PR 和手动触发时执行：

1. Python 3.10 与 3.12：`uv lock --check`、冻结同步、全量 pytest、治理检查、回归目录收集检查。
2. Python 3.12 package：在 checkout 外双次构建 wheel/sdist，逐项比较可复现性。
3. 产物：生成 `SHA256SUMS`、SPDX 2.3 SBOM、供应链检查结果；从生成 wheel 建立隔离虚拟环境并执行 `asecli parse` 冒烟验证。

CI 通过只证明远端自动门禁通过。进入“已交付”还需要真实的 push run 链接、可下载 artifact 与 hash 核对、以及需要时的回滚观察。项目禁止自动发布；每次 GitHub Release、PyPI、Hub 上传或对外分发均须获得单独书面授权。`v0.6.0` 按用户 2026-09-06 的明确授权发布为私有正式 Release，后续版本不会因此自动发布。

### 供应链、许可证与密钥

- 当前许可证为 MIT；源码与 GitHub Release 公开。上传 PyPI、CLI Hub 或其他包仓仍须单独书面授权。
- 当前生产运行时依赖为 0；新增运行时依赖、改许可证或改分发方式均是单独 CR，必须完成许可证与漏洞评估。
- `uv.lock` 固定开发依赖的来源、版本和 SHA-256；CI 中所有 GitHub Actions 必须固定为 40 位 commit SHA。
- `tools/supply_chain_check.py` 会检查 lock、Action pin、常见高置信密钥模式与许可证；`tools/generate_sbom.py` 生成 artifact 清单。离线检查不等同于真实漏洞数据库或 Dependabot 状态。
- MCP 实例 token 只能由 `ASECLI_MCP_INSTANCE_TOKEN` 环境变量提供，严禁放进 argv、仓库、文档示例、日志、截图或 artifact；远端 MCP 必须显式 `--allow-remote-mcp`。

### 证据边界

| 证据 | 可以证明 | 不能替代 |
| --- | --- | --- |
| `pytest` / mock | 文本解析、写入不变量、CLI JSON、MCP 响应处理和安全契约。 | 真实 Editor API、材质 Inspector 交互、目标平台或渲染画面。 |
| 隔离 Unity/Tuanjie bridge | 特定编辑器版本、MCP 会话与隔离资产上的编译/创建链路。 | 用户目标工程的材质绑定、平台编译和最终效果。 |
| 本地双构建/安装 | 可重复构建流程与包内容。 | 远端 CI、Release 上传或下载 artifact 完整性。 |
| GitHub Actions 运行记录 | 该 commit 的远端 CI 结果与 artifact 生成。 | 真实 GUI 视觉、目标 DCC/平台运行时验收。 |

报告时必须把已运行、未运行和受环境限制跳过的门禁分别说明；不要把“可静态验证”写成“最终用户画面已验收”。

## 架构与文档

- 需求基线：[`docs/01-architecture/project-architecture-and-requirements.md`](docs/01-architecture/project-architecture-and-requirements.md)
- 技术决策：[`docs/01-architecture/technical-route.md`](docs/01-architecture/technical-route.md)（ADR-0001~0005）
- 模块边界：[`docs/01-architecture/module-map.md`](docs/01-architecture/module-map.md)
- 第一性原理计划书：[`docs/first-principles/2026-08-31-231401-optimization-plan.md`](docs/first-principles/2026-08-31-231401-optimization-plan.md)
- 实验记录：[`docs/01-architecture/assumption-experiments.md`](docs/01-architecture/assumption-experiments.md)

```
src/asecli/
├── core/      解析器/序列化器/图模型/布局引擎
├── schema/    节点 schema 库（data/schemas.json）
├── checks/    结构校验与 checksum
├── bridge/    MCP for Unity 客户端、重编译触发与材质 GUI 支持安装器
└── cli/       命令入口与 JSON 契约
```

## License

MIT License，见 [`LICENSE`](LICENSE)。

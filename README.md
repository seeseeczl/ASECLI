# AseCLI

**让 AI Agent 创建、修改、校验、整理与编译 Amplify Shader Editor（ASE）文件。**

AseCLI 是面向 AI Agent 的本地 CLI：离线读取、编辑和校验 ASE 节点图；通过运行中的 Unity/团结引擎与 MCP，让真实 ASE 创建节点、提供精排几何并重新生成 HLSL。Skill 提供跨 Agent 的操作规则，CLI 提供可验证的执行结果。

当前正式版：**[0.6.4](https://github.com/seeseeczl/ASECLI/releases/tag/v0.6.4)** · [PyPI](https://pypi.org/project/asecli/0.6.4/) · [Agent 操作手册](skills/asecli/SKILL.md) · [SG 转换后整理流程](skills/asecli/references/conversion-workflow.md)

ASECLI 接收 `EditorGraphSpec`，不直接承担任意 Shader Graph 的转换。SGCLI 导出的源图 JSON、转换后的创建规格和已经整理的 `.shader` 是不同资产；创建成功不代表转换效果等价。

```
你：提需求（"给这个 shader 加个可调描边"）
Agent：设计节点图 → asecli 写文件 → 校验 → 触发编译 → 你验收效果
```

## 能力总览

| 领域 | 能力清单 | 是否需要运行中的 Unity/Tuanjie |
| --- | --- | --- |
| 图读取与安全检查 | 解析节点/连线、结构校验、CHKSM 校验与修复、无效节点审计 | 否 |
| 图编辑 | 设置已知字段、schema 驱动或原始行加节点、连线/断线、受保护删节点、最小差异写回 | 否 |
| 图整理 | 离线初排、真实几何递归鱼骨、独立计算岛多列摆放、原生 Comment 与边界检查 | 精排、真实边界检查需要 |
| 转换后核对 | `graph-review` 保守比较计算基线，按输出端口生成 Local Var 复用计划 | 只读计划不需要；不会自动创建 Register/Get |
| 材质 Inspector | 原生 MZGUI 优先；缺失时才注入 ASECLI ShaderGUI fallback。两者兼容 `FoldoutMzgui`、`TooltipMzgui`、`HelpBoxMzgui` 和条件置灰 `EnableIfMzgui`；默认只生成 Tooltip，HelpBox 由用户按需添加 | 写元数据否；安装、重编译和最终 Inspector 验收需要 |
| Shader 创建 | 从已满足属性呈现契约的编译壳克隆；或由严格 `EditorGraphSpec v2/v3` 让 ASE 自己创建节点、连线、保存和重载核对 | Editor 后端需要 |
| 编译桥接 | 通过 MCP for Unity 请求 ASE 重新生成 HLSL，并验证工具结果/保存语义 | 是 |
| Agent 集成 | 全部子命令单行 JSON 输出；稳定错误码与退出码，适合 Agent 子进程编排 | 否 |
| 工程交付 | 双 Python CI、锁文件、回归目录、可复现 wheel/sdist、SBOM、供应链与许可证检查 | 否 |

核心实现特性：

- **纯文本读写引擎**：真实样本逐字节 roundtrip 一致；普通布局保留计算连接，精排还可联动 Comment，显式路由需另外授权与核对。
- **节点 schema 库**：295 种节点类型的参数结构来自 ASE 运行时序列化提取；未知或版本不兼容的结构拒绝猜写。
- **安全写入**：写前比对 SHA-256 快照、加独占锁、拒绝符号链接和陈旧快照；既有文件写入前生成相邻 `.bak` 备份。
- **受控 Editor 创建**：固定 C# 执行器 + 白名单 JSON 规格，拒绝任意 C#、任意反射字段和不支持版本的降级写入。
- **属性呈现契约**：所有由 `create` 生成的 ASE Shader 必须满足 `asecli.property-presentation.v2`；公开属性使用中文显示名和中文 Tooltip，GUI 自动追加英文变量名与 Shader 默认值。HelpBox 是用户可选内容，不参与合规门禁。
- **证据分层**：文本/自动化通过不等于真实 Editor、目标 Inspector 或最终渲染画面通过；README 会明确标注这些边界。

## 环境要求

- 离线：查看、已知结构编辑、校验、计算基线比较和 `legacy` 初排，不需要 Unity。
- Editor：创建、编译、`meticulous` 精排及真实 Comment 边界检查，需要目标工程已打开且 MCP 会话已启动。Editor 创建当前以 ASE `1.9.6.2` 为支持边界。
- 安装脚本会自动安装 [uv](https://docs.astral.sh/uv/) 和 Python >= 3.10，不必预先配置

## 安装与运行

推荐通过 PyPI 安装 CLI 与 Agent Skill：

```bash
uv tool install asecli
asecli install-skill --agent all
```

`--agent all` 使用最少的非重复目录覆盖当前主流 Agent：

- `~/.agents/skills/asecli`：Codex、Cursor、Gemini CLI、GitHub Copilot。
- `~/.claude/skills/asecli`：Claude Code。

Skill 使用通用 `SKILL.md`、相对引用和 CLI 子进程，不依赖某一家 Agent 的专属工具 API。需要把 Skill 随仓库共享时，使用：

```bash
asecli install-skill --agent all --scope project --project-root /path/to/project
```

项目级安装会写入 `<project>/.agents/skills/asecli` 与 `<project>/.claude/skills/asecli`。也可只安装一个原生目标：

| `--agent` | 用户级目录 | 项目级目录 |
| --- | --- | --- |
| `agents` | `~/.agents/skills` | `.agents/skills` |
| `codex` | `~/.agents/skills` | `.agents/skills` |
| `claude` | `~/.claude/skills` | `.claude/skills` |
| `cursor` | `~/.cursor/skills` | `.cursor/skills` |
| `gemini` | `~/.gemini/skills` | `.gemini/skills` |
| `copilot` | `~/.copilot/skills` | `.github/skills` |

不带新参数的 `asecli install-skill` 继续安装到原有 Codex 用户目录，保证旧脚本兼容；`--skill-root DIR` 仍可精确指定任意 Skill 根目录。所有目标都保持同内容幂等、不同内容拒绝覆盖；`--agent all` 会先检查全部目标，发现内容冲突时不会先写入其他目录。

目录矩阵依据各产品当前公开文档：[Codex](https://developers.openai.com/codex/skills)、[Claude Code](https://docs.anthropic.com/en/docs/claude-code/skills)、[Cursor](https://cursor.com/docs/context/skills)、[Gemini CLI](https://geminicli.com/docs/cli/skills/) 与 [GitHub Copilot](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills)。

也可使用 GitHub Release 一键脚本同时安装 uv、CLI 与 Agent Skill。macOS / Linux：

```bash
curl -fsSL https://raw.githubusercontent.com/seeseeczl/ASECLI/main/scripts/install.sh | sh
```

Windows PowerShell 一条命令：

```powershell
irm https://raw.githubusercontent.com/seeseeczl/ASECLI/main/scripts/install.ps1 | iex
```

脚本会安装 uv、当前 GitHub Release 的 `asecli`，以及该版本支持的 Agent Skill。支持 `--agent` 的版本会采用上面的主流 Agent 通用安装；旧 Release 仍回退到原有 Codex 目录。同内容幂等，已有不同内容时跳过覆盖。

升级与卸载：

CLI 升级不会覆盖独立安装的 Skill；再次安装若提示内容冲突，先将旧 Skill 移到发现目录之外备份，再安装新版，保留自己的定制。卸载 CLI 不会自动删除这些 Skill。

```bash
# PyPI 安装的升级
uv tool upgrade asecli
asecli install-skill --agent all

# GitHub Release 一键安装的升级
curl -fsSL https://raw.githubusercontent.com/seeseeczl/ASECLI/main/scripts/install.sh | sh

# 卸载
uv tool uninstall asecli
```

当前正式版本为 `0.6.4`（转换图计算基线与计算岛布局），可从 [PyPI](https://pypi.org/project/asecli/0.6.4/) 或 [GitHub Release](https://github.com/seeseeczl/ASECLI/releases/tag/v0.6.4) 安装。历史版本见 [GitHub Releases](https://github.com/seeseeczl/ASECLI/releases)，`v0.6.3` 保留为回滚点。

已知限制：真实 MCP 下，属性+纹理 v2 和 Reciprocal 降级 v2 的 create、manifest、validate、独立 recompile 已通过；SGCLI SphereMask v3 spec 在重载时仍可能返回 `node missing after reload: Radius` 并回滚。本次不承诺该 recipe 端到端可用，也不改变 SGCLI v2 默认值契约。

### 源码开发运行

```bash
git clone https://github.com/seeseeczl/ASECLI.git
cd ASECLI
uv sync --frozen
uv run --frozen asecli --help
```

后续所有示例中的 `asecli` 都可替换为 `uv run --frozen asecli`，无需向全局环境安装任何内容。

### 从源码安装为本机命令

```bash
git clone https://github.com/seeseeczl/ASECLI.git
cd ASECLI
uv tool install .
asecli --help
```

### 安装受控的本地 wheel

适用于管理员通过其他受控渠道交付 wheel 的情况。只安装同时提供 `SHA256SUMS` 且校验通过的文件：

```bash
shasum -a 256 -c SHA256SUMS
uv tool install /path/to/asecli-0.6.4-py3-none-any.whl
asecli --help
```

升级源码副本时使用 `git pull --ff-only` 后重新执行 `uv sync --frozen`。若 lock 检查失败，不要跳过冻结安装；先解决 `uv.lock` 与项目声明的不一致。

## 快速上手

### 先只读检查现有 Shader

```bash
asecli parse Assets/Example.shader
asecli validate Assets/Example.shader
asecli graph-audit Assets/Example.shader
```

修改已知节点前先预演，确认节点 ID、端口与字段含义，再加 `--write`。不要直接复制其他图的节点 ID 或序列化字段下标。

多数修改命令默认预演；`create` 会立即创建资产，`recompile` 会立即请求 Editor 写回，`install-skill` 会写入安装目录。它们不是 dry-run。

### 从 SG 转换规格创建 ASE 图

前提：SGCLI 已生成合法的 EditorGraphSpec；目标工程已打开，MCP 地址与当前实例一致。下面的目标必须尚不存在。

```bash
asecli create Assets/ConvertedNew.shader --backend editor --spec graph.json \
  --mcp-url http://127.0.0.1:9080/mcp
asecli validate Assets/ConvertedNew.shader
asecli recompile Assets/ConvertedNew.shader --mcp-url http://127.0.0.1:9080/mcp
```

核对创建结果的节点、端口、连接及属性 manifest。`staging_reloaded=true` 只表示暂存图重载成功；目标图仍需独立 `recompile`。超时后先检查目标与同目录 `ASECLI-Temp-*`，禁止盲目重试。

### 整理转换后的复杂图

先将当前已确认正确的 Shader 另存为**唯一基线备份**；相邻 `.bak` 会被后续写入更新，不能充当整个任务的永久基线。

```bash
# 只读：锁定计算连接、常量与属性，分析复用
asecli graph-review Assets/ConvertedNew.shader

# 需要运行中 Editor：读取真实尺寸，预演鱼骨及三列计算岛
asecli layout Assets/ConvertedNew.shader --mode meticulous --island-columns 3 --audit \
  --mcp-url http://127.0.0.1:9080/mcp

# 审计无硬失败后，以同样参数写入
asecli layout Assets/ConvertedNew.shader --mode meticulous --island-columns 3 --write \
  --mcp-url http://127.0.0.1:9080/mcp

asecli graph-review Assets/ConvertedNew.shader --baseline /path/to/unique-baseline.shader
asecli validate Assets/ConvertedNew.shader
```

- `graph-review` 比较折叠 Register/Get/WireNode 后的计算连接及非布局节点字段；它是保守对照，不是完整语义等价证明。
- 默认复用按不同消费组判断；仅在用户指定“同一输出使用两次就注册”时用 `--reuse-policy fanout`。计划按来源节点和输出端口计数，**不会自动创建 Register/Get**。
- 计算岛整体摆放保留岛内关系；不把所有模块机械塞进全局深度列。默认不新增 WireNode，`--route-wires` 需要单独明确授权。
- 稳定布局后再添加 Comment、整理属性 GUI。不得从旧 JSON 重建已整理的 Shader，也不能仅回写坐标而遗漏新增节点和连线。
- SG 与 ASE 还需对照未连输入默认值、向量宽度、子图绑定及生成 HLSL；未知默认值不能补零。最后分别验收结构、Editor、画布/GUI、同条件效果。

完整流程见 [转换后图交付流程](skills/asecli/references/conversion-workflow.md)。新增计算岛流程的正常缩放画布、GUI 交互与效果对比仍需目标环境验收，不以自动测试代替。

### 整理材质面板

```bash
asecli gui-support /path/to/UnityProject
asecli custom-gui Assets/Example.shader --editor MZGUI.MZGUI --property _PaintColor \
  --group "固有色" --tooltip "控制车身基础漆面颜色；Alpha 当前不参与透明度计算。" --write
asecli custom-gui Assets/Example.shader --spec material-gui.json
# 确认预演后再写入
asecli custom-gui Assets/Example.shader --spec material-gui.json --write
asecli validate Assets/Example.shader
asecli recompile Assets/Example.shader
```

采用 `gui-support` 返回的 `recommended_editor` 作为 `--editor`；已有原生 MZGUI 时不注入第二套 GUI。批量规格保留英文变量名、类型、默认值、范围和 HDR，只按实际用途设置中文显示名、分组和 Tooltip。规格示例与交互验收见 [Skill](skills/asecli/SKILL.md) 和 [属性规范](skills/asecli/references/material-property-standard.md)。

## 完整命令目录

所有命令都可用 `asecli <command> --help` 查看参数。下表列出公开子命令及其实际副作用。

| 命令 | 做什么 | 写入/运行边界 |
| --- | --- | --- |
| `parse <file>` | 输出 ASE 图版本、节点数、连线数及节点摘要。 | 只读。 |
| `validate <file>` | 检查悬空连线、重复 ID、输入多来源、Local Var 一致性和 CHKSM。 | 只读；有 error 时返回退出码 2。 |
| `graph-review <file> [--baseline FILE] [--reuse-policy consumer-groups\\|fanout]` | 保守核对计算基线并列出复用计划。 | 只读；基线不一致返回 `SEMANTIC_MISMATCH` / 2，不自动创建 Local Var。 |
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
| `install-skill [--agent A] [--scope user\|project] [--project-root DIR] [--skill-root DIR]` | 将 wheel 内置的通用 ASECLI Agent Skill 安装到开放 `.agents` 目录或 Codex、Claude Code、Cursor、Gemini CLI、GitHub Copilot 原生目录。 | 无参数保持旧 Codex 目录；`all` 以两个非重复目标覆盖五类 Agent；相同内容幂等，任一冲突先整体拒绝，不修改 Shader、材质或 Unity/Tuanjie 工程。 |
| `comment-group <file> [--nodes IDS --title T] … [--write]` | 查询、创建、嵌套 ASE 原生 Comment 框；可检查成员越框或重叠。 | 创建默认用离线尺寸估算。`--editor-bounds`、`--check-bounds`、`--fit` 需连接 Editor。 |
| `create <out> --from TEMPLATE [--name NAME] [--graph-from DONOR]` | 复制一个已编译模板壳；可替换图或同步 Shader 名与 CHKSM。 | **立即创建/覆盖目标**；模板和 donor 组合后的文件必须已满足属性呈现契约，否则写前拒绝。 |
| `create <out> --backend editor --spec graph.json` | 用白名单 `EditorGraphSpec v2/v3` 让 ASE 自身创建、保存和重载目标图。 | **立即请求 Editor 写入**；每个 Property 必填中文 `inspector_name` 和中文 `tooltip`，可选 `help` 写用户 HelpBox。v3 另支持版本化 primitive/recipe 与属性精度、默认值和范围。 |
| `recompile <file> [--mcp-url URL] [--allow-remote-mcp]` | 调用运行中 ASE 重新生成 HLSL/保存，并报告 `changed`。 | **立即触发 Editor 操作**；默认仅允许 loopback MCP。 |

### 详细操作入口

| 任务 | 参考 |
| --- | --- |
| 已知结构编辑、批量 GUI、Comment、错误处理 | [Agent 操作手册](skills/asecli/SKILL.md) |
| SG 转换后的基线、复用、计算岛与分层验收 | [转换后图交付流程](skills/asecli/references/conversion-workflow.md) |
| 真实几何鱼骨、端口对齐、框与连线边界 | [布局规范](skills/asecli/references/layout-standard.md) |
| 中文显示名、Foldout、Tooltip、默认值与保留接口 | [材质属性规范](skills/asecli/references/material-property-standard.md) |
| Master/Pass、平台兼容性与功能开关 | [Master/Output 规范](skills/asecli/references/master-output-settings-standard.md) |

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

- CLI 创建接受 `EditorGraphSpec v2/v3`。每个 Property/Sampler 必须提供含中文的 `inspector_name` 和 `tooltip`；用户可另加可选 `help` 生成 HelpBox。v3 必填 `primitives_version: 1`，增加受控 `primitive`、可原生展开或降级为单节点 Custom Expression 的 `recipe`，并为已支持节点增加 `precision/default/min/max`。未知版本、primitive 或字段在 MCP 前失败关闭；v1 仅保留底层桥接兼容。
- v3 的 primitive 闭包绑定 ASE `1.9.6.2`；recipe 只按声明顺序引用输入或此前 primitive，禁止前向引用/循环。原生闭包不完整时才使用规格内已校验的逐节点 HLSL fallback，不会把整张图收成单一黑盒。
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

## 安全与验收边界

- 写入前检查基线，出现 `WRITE_CONFLICT` 先重新读取并比较，不覆盖其他 Agent 或 Editor 的改动。备份、锁与路径检查不能代替语义验收。
- 未知动态节点、Master 或版本字段不得猜写；使用已支持的语义命令或真实 ASE Editor API，不手工拼 Shader/HLSL 冒充 Editor 创建。
- `graph-audit` 分析输出可达性；`graph-review` 分析计算基线与复用。未连 Property 可能被 GUI/HLSL 或项目源码消费，审计候选不是删除许可。
- 属性 GUI 优先复用原生 MZGUI；未知或多个 provider 时停止。团结 `2022.3.61t9` 有既有验证，其他 Editor/API fallback 不自动视为已实测支持。
- 编译通过、属性相同、计算连接一致，都不能独立证明 SG 转换等价。正常缩放画布、Foldout 点击、Tooltip 悬停和同条件渲染对照要分别报告。

## 编译桥接前提

1. Tuanjie/Unity 编辑器已打开目标工程
2. MCP for Unity 会话已启动（编辑器内 Start Session，默认 `http://127.0.0.1:8080/mcp`）
3. MCP 不能被其他会话独占（`recompile` 报 `BRIDGE_ERROR` 时先检查占用）
4. `recompile` 成功时 `data.changed=true` 表示 HLSL 已重新生成；`changed=false` 表示文件本已最新。Editor 创建成功会返回 `template_guid`、`shader_name` 和 Save/Load manifest

安全边界：默认只允许 `127.0.0.1`、`localhost`、`::1`；远程 MCP 必须显式加 `--allow-remote-mcp`。实例 token 只能通过当前进程环境变量 `ASECLI_MCP_INSTANCE_TOKEN` 提供，禁止写入命令参数、脚本或日志。客户端拒绝 URL 凭证、query、fragment 和 HTTP 重定向，避免 token 被转发。`recompile` 会调用 MCP 的 `execute_code`，因此只能连接你明确信任的编辑器会话。

## 开发测试

以下为开发入口，不是每次文档修改的必跑清单。Editor 创建 E2E 只允许带有 `.asecli-e2e-isolated` 标记的隔离工程；不得给生产工程补标记绕过保护。无实机环境时的 skip 不代表通过。

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

### 按改动范围验证

以 [AGENTS.md](AGENTS.md) 为当前执行规则，不为小修改重复启动完整发布流程。

| 变更 | 最小验证 |
| --- | --- |
| 文档、注释、不改变行为的配置 | 相关 diff、格式和直接引用；不启动 Editor、不跑全量测试、不构建发布包 |
| 局部 Python 行为 | 直接相关测试与必要 CLI smoke；跨核心模块或公共契约时再追加全量 |
| Editor API、真实几何、Inspector 或渲染 | 自动检查通过后，复用一个 Editor 会话集中验证相关实机项 |
| 用户明确要求推送或发布 | 完整治理、可复现构建、远端 CI、资产校验与回滚检查 |

有任务卡时回填实际证据；纯 README 校正不补造 FR、CR 或发布记录。未运行、跳过与失败分别说明。

### CI、构建与发布门禁

`.github/workflows/ci.yml` 在 push 到 `main`、PR 和手动触发时执行：

1. Python 3.10 与 3.12：`uv lock --check`、冻结同步、全量 pytest、治理检查、回归目录收集检查。
2. Python 3.12 package：在 checkout 外双次构建 wheel/sdist，逐项比较可复现性。
3. 产物：生成 `SHA256SUMS`、SPDX 2.3 SBOM、供应链检查结果；从生成 wheel 建立隔离虚拟环境并执行 `asecli parse` 冒烟验证。

CI 通过只证明远端自动门禁通过。进入“已交付”还需要真实的 push run 链接、可下载 artifact 与 hash 核对、以及需要时的回滚观察。普通 push 不会发版。PyPI Trusted Publisher 与 GitHub `pypi` environment 已激活，tag workflow 从同一份已校验 artifact 上传；GitHub 一键安装脚本继续使用最新 Release。CLI Hub 仍不自动提交。

### 供应链、许可证与密钥

- 当前许可证为 MIT；源码公开，正式安装入口为 PyPI `uv tool install asecli`，GitHub Release 一键脚本保留为安装 CLI 与 Skill 的完整入口。CLI Hub 不是当前分发入口，后续启用需要新的明确授权。
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
- 技术决策：[`docs/01-architecture/technical-route.md`](docs/01-architecture/technical-route.md)
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

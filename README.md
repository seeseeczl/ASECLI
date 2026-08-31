# AseCLI

**让 AI Agent 创建、修改、校验、整理与编译 Amplify Shader Editor（ASE）文件。**

AseCLI 是一个面向 AI Agent 的本地 CLI 工具。它把 ASE 嵌在 `.shader` / `.asset` 文件里的节点图当作纯文本数据来解析和修改——不依赖 Unity 即可完成 90% 的操作；只在需要重新生成编译后 HLSL 时，通过 MCP for Unity 触发一次 Unity/团结引擎重编译。

```
你：提需求（"给这个 shader 加个可调描边"）
Agent：设计节点图 → asecli 写文件 → 校验 → 触发编译 → 你验收效果
```

## 特性

- **纯文本读写引擎**：真实样本逐字节 roundtrip 一致，修改产生最小差异
- **节点 schema 库**：295 种节点类型的参数结构由 ASE 运行时序列化自动提取（格式由 ASE 自己保证）
- **结构校验**：悬空连线、重复节点 ID、CHKSM 校验（SHA1，已逆向验证）
- **自动布局**：Sugiyama-lite 分层排列——输入在左、输出在右、Master 靠右、对齐等距，只动 x/y
- **无 UI**：stdout 恒为 JSON，专为 agent 子进程调用设计
- **编译桥**：经 MCP for Unity（`execute_code`）触发 Unity 内 ASE 重新生成并保存

## 环境要求

- Python >= 3.10，[uv](https://docs.astral.sh/uv/)
- 查看/修改/校验/布局：不需要 Unity
- 编译（`recompile`）：Unity/团结引擎打开目标工程 + MCP for Unity 会话已启动

## 安装

```bash
git clone git@github.com:seeseeczl/ASECLI.git
cd ASECLI
uv tool install .          # 安装为全局 asecli 命令
# 或开发模式：uv sync && uv run asecli --help
```

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

# 6. 整理节点布局（分层对齐等距，只动 x/y）
asecli layout MyShader.shader --write

# 7. 触发 Unity 内 ASE 重新生成 HLSL（需编辑器开启 + MCP 会话启动）
asecli recompile Assets/MyShader.shader

# 8. 从已有编译壳克隆新 shader
asecli create Assets/NewShader.shader --from MyShader.shader --name "NewShader" --force
```

所有修改类命令不加 `--write` 时为 dry-run（只预览不落盘）。

## 命令参考

| 命令 | 说明 | 需要 Unity |
| --- | --- | --- |
| `parse <file>` | 节点/连线摘要 | 否 |
| `validate <file>` | 结构校验（悬空线/重复 ID/CHKSM） | 否 |
| `set-field <file> --node N --field I --value V` | 设置节点某个序列化字段 | 否 |
| `add-node <file> --type T [--id N] [--pos X,Y]` | schema 驱动加节点（或 `--line` 整行插入） | 否 |
| `connect <file> --from SRC:port --to DST:port` | 连线（from=输出端，to=输入端） | 否 |
| `disconnect <file> --from SRC:port --to DST:port` | 删连线 | 否 |
| `remove-node <file> --node N` | 删节点（自动清理附属连线） | 否 |
| `layout <file> [--gap-x] [--gap-y]` | 自动整理节点布局 | 否 |
| `fix-checksum <file>` | 重算 `//CHKSM`（SHA1） | 否 |
| `create <out> --from TPL [--name N] [--graph-from D]` | 从编译壳克隆新 shader | 否 |
| `recompile <file> [--mcp-url U]` | 触发 Unity 内 ASE 重新生成并保存 | **是** |

## JSON 契约

stdout 恒为单行 JSON，agent 可直接解析：

```json
{"ok": true,  "data": {"node_count": 7}}
{"ok": false, "error": {"code": "NOT_FOUND", "message": "..."}}
```

错误码：`PARSE_ERROR` `NOT_FOUND` `USAGE_ERROR` `SCHEMA_UNAVAILABLE` `BRIDGE_ERROR` `INTERNAL`
退出码：`0` 成功 · `2` 用法/校验/解析错误 · `3` 桥接错误

## ASE 格式备忘（Agent 必读）

1. 节点图嵌在 `/*ASEBEGIN ... ASEEND*/` 块中，行式指令流：`Node;...` 与 `WireConnection;...`
2. `WireConnection;<入节点>;<入端口>;<出节点>;<出端口>` —— **目的地在前，来源在后**
3. `//CHKSM=` = 整个文件（`//CHKSM=` 之前部分）的 SHA1 大写 hex；校验失败**不阻断** ASE 加载
4. Master 节点（TemplateMultiPassMasterNode 等）序列化布局为 opaque：用 `--line` 整行替换或 `layout` 移动

完整操作手册见 [`skills/asecli/SKILL.md`](skills/asecli/SKILL.md)（可装进 agent 技能系统）。

## 编译桥接前提

1. Tuanjie/Unity 编辑器已打开目标工程
2. MCP for Unity 会话已启动（编辑器内 Start Session，默认 `http://127.0.0.1:8080/mcp`）
3. MCP 不能被其他会话独占（`recompile` 报 `BRIDGE_ERROR` 时先检查占用）
4. 成功时 `data.changed=true` 表示 HLSL 已重新生成；`changed=false` 表示文件本已最新

## 测试

```bash
uv run pytest -q                # 全量（桥接测试无环境时自动跳过）
ASECLI_TEST_SHADER=Assets/xxx.shader uv run pytest -m bridge   # 桥接端到端
```

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
├── bridge/    MCP for Unity 客户端与重编译触发
└── cli/       命令入口与 JSON 契约
```

## License

内部工具，未设开源许可。

---
name: asecli
description: Create, modify, validate, layout and compile Amplify Shader Editor (ASE) shader files via the asecli CLI. Use whenever the user asks to edit or create ASE shaders in a Tuanjie/Unity project.
---

# AseCLI — Agent 操作 ASE Shader 指南

## 核心事实（必读）

1. ASE 节点图以纯文本嵌在 `.shader` 文件的 `/*ASEBEGIN ... ASEEND*/` 块中，行式格式。
2. `WireConnection;<入节点>;<入端口>;<出节点>;<出端口>` —— **目的地在前，来源在后**。
3. `//CHKSM=` 是 SHA1（大写 hex），对 `//CHKSM=` 之前的**整个文件**计算；校验失败**不阻断** ASE 加载。
4. `connect --from` 是输出端（数据源），`--to` 是输入端（消费者）。
5. Master 节点（TemplateMultiPassMasterNode 等）布局为 opaque，只能整行替换或用 `layout` 移动。

## 三条链路

### 链路 A：查看图（无 Unity）

```bash
asecli parse <file>          # 节点/连线摘要
asecli validate <file>       # 结构校验（悬空线/重复ID/CHKSM）
```

### 链路 B：修改图（无 Unity，毫秒级）

```bash
# 改属性值（field 为绝对下标：0=Node, 1=类型, 2=Id, 3=坐标, 4+=参数）
asecli set-field <file> --node 5 --field 12 --value 0.85 --write

# 加节点（schema 驱动，自动补参数默认值）
asecli add-node <file> --type AmplifyShaderEditor.SaturateNode --id 99 --pos -320,0 --write

# 连线：把 99 的输出 0 接到 6 的输入 0
asecli connect <file> --from 99:0 --to 6:0 --write

# 删节点（自动清理附属连线）
asecli remove-node <file> --node 99 --write

# 整理布局（分层对齐等距，只动 x/y）
asecli layout <file> --write
```

### 链路 C：创建 + 编译（需要 Unity 开启 + MCP 会话已启动）

```bash
# 从编译壳克隆新 shader（可注入 donor 图），纯文本
asecli create Assets/Exp/New.shader --from <compiled-template.shader> --name "MyShader" --force

# 触发 Unity 内 ASE 重新生成 HLSL（走 MCP for Unity）
asecli recompile Assets/Exp/New.shader
```

## JSON 契约

- stdout 恒为 `{"ok": true, "data": {...}}` 或 `{"ok": false, "error": {"code", "message"}}`。
- 错误码：`PARSE_ERROR` / `NOT_FOUND` / `USAGE_ERROR` / `SCHEMA_UNAVAILABLE` / `BRIDGE_ERROR` / `INTERNAL`。
- 退出码：0 成功；2 用法/校验/解析错误；3 桥接错误。
- 不加 `--write` 时命令只做 dry-run（`data.written=false`）。

## 桥接前提

1. Tuanjie/Unity 编辑器已打开目标工程。
2. MCP for Unity 会话已启动（编辑器里 Start Session；服务器默认 `http://127.0.0.1:8080/mcp`）。
3. `recompile` 成功返回 `data.changed=true` 表示 HLSL 已重新生成；`changed=false` 表示图未变。

## 错误处理约定

- 修改前先 `validate`；发现 `DANGLING_WIRE`/`DUPLICATE_NODE_ID` 先修复再继续。
- `SCHEMA_UNAVAILABLE` 时：用 `parse` 拿节点行原文，改用 `--line` 整行插入或整行替换。
- 所有写操作用 `validate` + `parse` 复核后再向用户报告。

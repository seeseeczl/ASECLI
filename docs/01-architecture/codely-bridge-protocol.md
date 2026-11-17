# Codely Bridge 协议说明（团结官方 `cn.tuanjie.codely.bridge`）

本文记录 ASECLI 接入 Codely Bridge 所需的协议事实。全部内容来自**实机验证与静态分析**，
不是官方文档（官方 README 已过时，其描述的 "echo server" 与实际实现不符）。

- 分析对象：`Library/PackageCache/cn.tuanjie.codely.bridge@1.0.66`
- 原生库：`Plugins/macOS/libNativeTcpBridge.dylib`（arm64 + x86_64 universal）
- 验证环境：P376 / Tuanjie 2022.3.61t15 / pid 70407
- 记录日期：2026-11-17

---

## 1. 传输层

### 1.1 启停行为

Codely Bridge 随编辑器**自动启动**，无需手动操作：

- `UnityTcpBridge` 标记 `[InitializeOnLoad]`
- 静态构造函数：`if (!EditorPrefs.GetBool("UnityTcp.ManualStop", false)) Start();`
- 域重载后自动重启，除非曾手动 Stop（写入 `UnityTcp.ManualStop` 标记）
- Batch 模式下默认不启动，除非设置环境变量 `UNITY_TCP_ALLOW_BATCH=1`

### 1.2 连接握手

TCP 连接建立后，服务端立即发送一行欢迎串，以 `\n` 结尾：

```
WELCOME UNITY-TCP 1 FRAMING=1 SERVER_VERSION=2
```

注意两处易错点：

- 握手是 **`UNITY-TCP`**，不是 CHANGELOG 曾提到的 `Codely-Bridge`
- `FRAMING=1` 与 `SERVER_VERSION=2` 是**两套独立编号**，包版本 `1.0.66` 又是第三套

### 1.3 帧格式

**「8 字节大端序无符号长度」+「UTF-8 JSON 负载」**，请求与响应同构。

```
┌──────────────────┬─────────────────────────┐
│ length: u64 (BE) │ payload: UTF-8 JSON     │
└──────────────────┴─────────────────────────┘
```

依据：原生库 `TcpUtils_ReadFrame` 反汇编。

```asm
62b0: mov  w24, #0x8    ; 固定读 8 字节长度头
62e8: rev  x1, x8       ; 字节序反转 → 大端
62f0: cmp  x8, w21      ; 与长度上限校验
```

约束：

- 单帧上限 **64 MiB**（`MaxFrameBytes`）
- 读取超时 **3000 ms**（`FrameIOTimeoutMs`），超时后连接被断开

**易错点**：只发 JSON 不发长度头时，服务端把它当作 `length` 的前 8 字节解析，
导致长度校验失败并**静默关闭连接**（表现为 `recv` 返回空）。这是初次接入最常见的失败模式。

---

## 2. 请求 / 响应格式

### 2.1 请求

```jsonc
{
  "type": "<命令名>",     // 必填，snake_case
  "params": { }           // 可选，命令参数对象
}
```

`type` 为空时返回：

```json
{"success":false,"code":"Command type cannot be empty","error":"Command type cannot be empty","data":"A valid command type is required for processing"}
```

`type` 未知时返回：

```json
{"success":false,"code":"Unknown or unsupported command type: <type>","error":"...","data":{"command":"<type>","stackTrace":"..."}}
```

### 2.2 响应

成功（`read_console` 示例）：

```json
{"success":true,"message":"Command executed successfully","data":{"success":true,"message":"Retrieved 0 log entries.","data":[]}}
```

失败时带 `code` / `error` / `data`，`data` 内可能含 `stackTrace`。

**注意**：响应是**两层结构** —— 外层 `success` 是传输层状态，内层 `data.success` 是
命令本身的结果。两层都要检查。

---

## 3. 命令清单

共 17 个，均从 `UnityTcpBridge.ExecuteCommand` 的 switch 分支确认：

| 命令 | 说明 |
|---|---|
| `manage_script` | 脚本文件 CRUD |
| `manage_scene` | 场景操作 |
| `manage_editor` | 编辑器状态与操作 |
| `manage_gameobject` | GameObject CRUD |
| `manage_asset` | 资产操作 |
| `read_console` | 读取控制台 |
| `execute_menu_item` | 执行编辑器菜单 |
| **`manage_shader`** | Shader 文件 CRUD（**不含 ASE 图操作**） |
| **`execute_csharp_script`** | **执行任意 C# 脚本（Roslyn）** |
| `manage_package` | 包管理 |
| `manage_bake` | 烘焙 |
| `manage_ui_toolkit` | UI Toolkit |
| `manage_gameview` | Game 视图 |
| `manage_workflow` | 工作流 |
| `execute_custom_tool` | 自定义工具 |
| `manage_window_bridge` | 原生窗口桥 |
| `_internal_state_dirty` | 内部状态通知（不对 LLM 暴露） |

---

## 4. `execute_csharp_script`（ASECLI 的核心依赖）

这是与 MCP `execute_code` **语义等价**的能力，ASECLI 现有 C# 片段可零改造复用。

### 4.1 参数

| 参数 | 说明 |
|---|---|
| `script` | C# 脚本文本 |
| `script_path` | 脚本文件路径（与 `script` 二选一） |
| `description` | 日志描述 |

### 4.2 实现

- 引擎：Microsoft.CodeAnalysis.CSharp.Scripting（Roslyn，随包分发）
- 语法自动修复：8 个 `ScriptFixProvider`，最多迭代 50 轮
  - `FixMissingImports` / `FixMissingAssemblyReference` / `FixUnqualifiedUnityStaticMethod`
  - `FixMissingParenthesis` / `FixMissingBrace` / `FixMissingSquareBracket`
  - `FixMissingSemicolon` / `FixAmbiguousReference`
- 脚本以 `return` 直接产出结果值

### 4.3 响应

```json
{"success":true,"message":"Command executed successfully","data":{
  "success":true,
  "message":"C# script executed successfully.",
  "data":{"result":"2","logs":[],"log_count":0},
  "state_delta":{"scene":{"dirty":true}}
}}
```

编译失败时：

```json
{"success":true,"data":{"success":true,"message":"C# script execution failed: (2,48): error CS1010: Newline in constant","state_delta":{...}}}
```

**注意**：编译失败时**外层仍是 `success:true`**，失败信息藏在 `data.message` 的文本里，
`data.result` 缺失。ASECLI 必须显式判定 `data.result` 是否存在，不能只看外层 `success`。

### 4.4 已验证可达性

| 验证项 | 实测结果 |
|---|---|
| 执行 `return 1+1;` | `result: "2"`，耗时约 2.3s |
| 解析 ASE 窗口类型 | `result: "AmplifyShaderEditor.AmplifyShaderEditorWindow"` |
| 读取 ASE 私有字段 | `result: "m_mzguiAttribs"`（`NonPublic\|Instance` 可达） |

结论：**ASE 私有字段与实例方法全部可达**，ASECLI 的 15 个 `.cs.txt` 片段可直接复用。

---

## 5. 实例发现

### 5.1 端口注册文件（推荐）

端口持久化在**工程根目录**的 `.com-unity-codely.json`：

```json
{
  "unity_port": 53996,
  "stream_port": 0,
  "created_date": "2026-05-21T01:52:48.7469400Z",
  "project_path": "/Users/long/Tuanjie3D/P376/Assets",
  "reloading": false,
  "reason": "ready",
  "seq": 1,
  "last_heartbeat": "2026-11-17T04:11:25.9743330Z"
}
```

字段语义：

| 字段 | 用途 |
|---|---|
| `unity_port` | **TCP 监听端口**，ASECLI 的连接目标 |
| `stream_port` | 原生窗口桥的信令端口（ASECLI 无需使用） |
| `project_path` | 指向 `Assets` 目录，可用于反推工程根 |
| `reloading` | 程序集是否正在重载 |
| `reason` | 状态原因，`ready` 表示就绪 |
| `last_heartbeat` | 心跳时间戳，用于 stale 判定（**官方未定义阈值**） |

### 5.2 回退路径

若工程内文件缺失，按顺序回退：

1. `<工程根>/unity-tcp-port.json`（旧版，已废弃）
2. `~/.unity-tcp/unity-tcp-port.json`（用户级，已废弃）

实测三处内容一致。

### 5.3 已知限制

- `last_heartbeat` 的**更新频率无文档**，ASECLI 不宜据此做严格 stale 判定
- 无 `instanceId` / `bootId`，**无法区分同工程多编辑器实例**
- 端口动态分配，不可假设默认值 25916（实测该端口未监听）

---

## 6. 与 DSH-Bridge 的对比

| 维度 | Codely Bridge | DSH-Bridge |
|---|---|---|
| 传输 | TCP + 8 字节大端长度帧 | 文件系统邮箱 IPC |
| 端口 | 有（动态） | 无 |
| 载荷 | C# 源码字符串 | 结构化反射调用 |
| ASE 私有字段 | 天然可达 | 需 `NonPublic` 反射 |
| 实例发现 | `.com-unity-codely.json` | `Library/DSHBridge/instance.json` |
| 多实例区分 | ❌ 无 | ✅ `instanceId` + `bootId` |
| 危险能力门禁 | 无 | `allowDangerous` |
| 对 ASECLI 的改造量 | **极小**（仅换传输层） | 大（片段需翻译） |

---

## 7. 复现验证

```python
import socket, struct, json

def codely_call(port: int, command: str, params: dict, timeout: float = 30):
    payload = json.dumps({"type": command, "params": params}).encode()
    with socket.create_connection(("127.0.0.1", port), timeout=timeout) as s:
        s.settimeout(timeout)
        s.recv(4096)                              # 消费握手，勿跳过
        s.sendall(struct.pack(">Q", len(payload)) + payload)
        header = s.recv(8)
        if len(header) != 8:
            raise RuntimeError("connection closed before response header")
        size = struct.unpack(">Q", header)[0]
        buf = b""
        while len(buf) < size:
            chunk = s.recv(size - len(buf))
            if not chunk:
                break
            buf += chunk
        return json.loads(buf)

# 实测通过的调用
print(codely_call(53996, "read_console", {}))
print(codely_call(53996, "execute_csharp_script", {"script": "return 1+1;"}))
```

---

## 8. 待确认项

- `last_heartbeat` 的更新周期与推荐 stale 阈值
- 多编辑器实例并存时的端口注册覆盖行为
- `manage_shader` 之外是否存在 ASE 感知能力（当前确认：无）

---

## 9. 实现落点与实测数据（2026-11-17）

ASECLI 侧实现位于 `src/asecli/bridge/`：

| 文件 | 职责 |
|---|---|
| `codely_discovery.py` | 定位工程根与端口注册文件 |
| `codely_client.py` | 帧编解码、握手、`execute_csharp_script` |
| `editor_result.py` | 统一两种后端的响应解包 |
| `backend.py` | 后端选择（auto 优先 Codely，回退 MCP） |

### 9.1 耗时实测（编辑器 pid 70407）

| 场景 | 字符数 | 耗时 |
|---|---|---|
| 小脚本稳态（5 次） | 8 | 0.93–1.37s |
| 真实 `GEOMETRY_SNIPPET` | 11080 | 2.29 / 2.41 / 3.30s |
| `editor_create` 执行器 | 46663 | 首次 7.81s，其后 0.84–1.92s |

结论：单次读取的 3000ms 上限**不会中断大脚本**；服务端处理完成后正常回包。
客户端超时因此设为 180s，并在连接后执行一次预热探测以消化 Roslyn 冷启动。

### 9.2 已验证的 ASE 可达性

```
win=True;node=True;field=m_mzguiAttribs
```

ASE 窗口类型与私有字段均可经 `execute_csharp_script` 访问，ASECLI 现有 C# 片段无需改写。

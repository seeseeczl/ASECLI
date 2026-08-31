# 假设验证实验记录 — TASK-0001

> 执行时间：2026-08-31 23:50（Asia/Shanghai）
> 执行环境：一次性临时 Tuanjie 工程 `/private/tmp/asecli-proj`（2022.3.62t7 batchmode，拷入 ASE 插件 1.9.1.9 + 真实样本 `HLIT.shader`，10 节点 URP Lit）
> 隔离声明：未修改用户工程任何文件；实验脚本与产物均在临时目录
> 原始输出归档：`/private/tmp/asecli-exp-result.txt`

## 实验结论

| 实验 | 假设 | 结果 | 证据 | 架构影响 |
| --- | --- | --- | --- | --- |
| EXP1-BASELINE | 原始 ASE 图文本可被 `LoadFromMeta` 加载 | 通过（10 节点） | result 第 2 行 | 纯文本链路成立 |
| EXP1-MUTATED | Agent 盲改图数据（Node 行末尾参数值）后仍可加载 | 通过（10 节点，无异常） | result 第 3 行 | D4 假设部分证伪：格式层面盲改不致崩；语义正确性仍需 schema 库保障（NFR-0002） |
| EXP2-BADCHKSM | CHKSM 校验失败是否阻断加载 | 通过——不阻断（10 节点正常加载） | result 第 4 行 + 源码 `AmplifyShaderEditorWindow.cs:3932`（仅 DeveloperMode 检查且提示已注释） | D6 假设证伪：checksum-fix 降级为可选命令，非链路必需 |
| EXP3-CREATE | 纯文本创建新 shader（编译壳 + 全新最小图）能否被 Unity 导入且 ASE 可加载 | 通过（导入为合法 Shader 资产 + 图加载 1 节点） | result 第 5-6 行 | D10 假设证伪：创建路径可纯文本完成（克隆编译壳 + 注入图文本）；桥接仅剩重编译 HLSL 职责 |

## 技术要点（实验过程中确认的实现细节）

1. 内存加载入口：`AmplifyShaderEditorWindow.LoadFromMeta(ref ParentGraph, GraphContextMenu, string meta)`，meta 为 `/*ASEBEGIN` 起至文件尾（含 CHKSM 行）。
2. 构造裸 graph 的三个前置条件：`graph.ParentWindow` 赋值、显式调用 `graph.Init()`、之后再 `new GraphContextMenu(graph)`（否则 `RefreshNodes`/`CleanNodes` NRE）。
3. CHKSM 算法可复现：`IOUtils.CreateChecksum(buffer)`（buffer 为 meta 去掉 CHKSM 行的部分）。
4. batchmode 下必须先创建 ASE 窗口实例以初始化 `UIUtils.CurrentWindow` 静态状态。

## 对计划的回写

- TASK-0001 完成（验证命令输出归档于本文件与临时目录 result 文件）。
- TASK-0012 的停止条件（纯文本生成 HLSL 为否决路径）不再成立：创建默认走纯文本，桥接保留为重编译触发器。
- REG-0008 状态：已验证关闭。

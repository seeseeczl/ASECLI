# Editor create MCP 编译修复验证

环境：FlymeAuto3Test，团结 2022.3.61t9，ASE 1.9.6.2，http://127.0.0.1:9080/mcp。

实际 MCP 源码 `Library/PackageCache/com.coplaydev.unity-mcp@4ce7dd3cc5/Editor/Tools/ExecuteCode.cs:357` 的 `WrapUserCode` 将用户片段插入 `public static object Execute()` 方法体。方法内声明 `public struct InputTarget` 因而无法编译。

最小修复：删除该类型声明，以 `System.Collections.Generic.KeyValuePair<int,int>` 保存节点 ID（Key）与端口（Value）。保留 delegate 的 `values` 改名；不恢复 System.Tuple。E2E harness 不再搬移声明，直接使用同一执行片段。byte-stable SHA 随实际 C# 修改更新为 `dd1467b22b506d8fbcca2f6d5387521a7b32e7bf61d5ea5ec8a5c43b4d03c7f6`。

自动验证：358 passed / 3 skipped；git diff --check 通过。未运行要求隔离标记的 Editor E2E；以下为真实 CLI 经 MCP 执行的结果。

| spec | create / manifest | validate | 独立 recompile / 再 validate |
| --- | --- | --- | --- |
| property_texture v2 | 通过，与 expected_manifest 相等 | 通过 | 均通过 |
| sphere_mask v3 | C# 编译通过，执行至重载后失败：node missing after reload: Radius | 未执行，目标已回滚 | 未执行 |
| defaults_degradation v2 | 通过，与 expected_manifest 相等 | 通过 | 均通过 |

前两项逐命令原始 JSON 和目标路径见本目录及 `summary.json`。第三项见相邻目录 `../mcp-create-fix-20260908_161756_0e3bb9/summary.json` 与各命令 JSON。

SphereMask 失败后确认目标不存在，`Assets/ASECLIProbe` 内没有 `ASECLI-Temp-*`；未盲目重试。该运行时节点重载问题尚未修复，不能声称三类 P0.2 回归全部通过。两个成功创建的唯一测试 Shader 及其 .meta 保留供 SGCLI 侧核验。SGCLI 源码、fixture、既有证据未修改，未 commit/push。

# REG-0053 — EditorGraphSpec v3 真实团结回归

- 日期：2026-09-08；隔离工程位于系统临时目录并带 `.asecli-e2e-isolated` 标记，未修改生产团结工程或既有 Shader。
- 环境：团结 `2022.3.61t9`、ASE `1.9.6.2`、URP Unlit 模板 GUID `2992e84f91cbeb14eab234972e07ea9d`。
- 自动契约：v1/v2/v3 spec、bridge、CLI、MCP 安全定向组合 `99 passed`；最终 E2E 前复测核心 spec/bridge 为 `53 passed`。
- Editor 命令：`ASECLI_EDITOR_CREATE_PROJECT=<隔离工程> ASECLI_TUANJIE_PATH=<团结> uv run --frozen pytest -q -m bridge tests/test_editor_create_e2e.py`。
- 最终结果：创建进程完全退出后由全新进程重载，`1 passed in 69.33s`；create/reload 日志均为 0 `Shader error`、0 `failed to compile`、0 `error CS`、0未捕获 `Exception:`。
- v3 回读：`world_position` 为真实 `WorldPosInputsNode`；`sphere_mask` 展开为 `DistanceOpNode`、`SimpleSubtractOpNode`、两个 `OneMinusNode`、`SimpleDivideOpNode`、`SaturateNode`；`_AuditRadius` 为 Half/0.5/[0,2]，`_AuditHardness` 为 Float/0.25/[0,1]；Master unique port 3 已连接。
- 事务结果：Caster/Receiver/AlgorithmV3 均 `saved=true`、`reloaded=true`、`committed=true`；注入关闭失败路径成功回滚；0 `ASECLI-Temp-*`，没有 `CloseFailure.shader` 残留。
- 失败优先记录：第一次隔离启动缺 `com.unity.nuget.newtonsoft-json`，第二次暴露缺 `com.asezh.locale`；两次均导致 ASE 程序集无法编译，不计为代码通过。隔离 manifest 按生产基线补齐精确依赖后，同一门禁通过；没有修改 ASE 源码来绕过失败。
- 证据边界：本次证明受支持版本下的真实 ASE 创建、保存和跨进程重载，不证明画布视觉、目标 Shader 渲染、未知 ASE/模板兼容或远端发布产物。

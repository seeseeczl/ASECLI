# ASE → Shader Graph 转换报告 v1

`report.json` 使用 `asecli.sg-conversion-report.v1`。它只记录转换证据，不是
`sgcli.native.v2` 的一部分，也不能传给 `sgcli sg create --spec`。同目录的 `graph.sg.json`
是独立裸规格，整个文件必须通过正式 Draft 2020-12 Schema。

顶层字段：

- `source`：源文件绝对路径、SHA-256、ASE 版本和模板 GUID。
- `source_validation`：导出前 ASE 结构校验的错误数、警告数和原始问题代码。
- `target_environment`：目标工程以及 SGCLI doctor 返回的 Unity、URP、Shader Graph 和桥接信息。
- `mapping_version`、`receiver_schema`：ASE→SG 规则版本和实际校验的接收契约摘要。
- `mappings`：源节点、源端口到目标节点、配置后有符号端口的逐项关系；一对多展开单独列出。
- `dependencies`：资源属性、源 GUID、源/目标路径、TextureImporter 语义和解析状态；空资源明确记录为 `explicit_null`。
- `degradations`：已保留计算数据但无法迁移的 Inspector 或画布语义。
- `diagnostics`：阻断规格生成的问题，包含源节点、原因和影响。
- `equivalence`：只能为 `not_proven` 或 `degraded`；自动导出不声明效果等价。
- `verification`：每层使用 `passed`、`failed`、`blocked` 或 `not_run`，并附证据。

验证层分别记录源解析、源结构、语义映射、Draft 2020-12 Schema、SGCLI Python 预检、
目标动态端口、create 预览、实际创建、保存重载、编译、画布和效果。未执行的层必须保持
`not_run`。create 预览只保存稳定摘要，不保存每次运行随机生成的 Editor 节点 GUID。
存在阻断诊断时不得生成 `graph.sg.json`；失败路径使用 `--write` 时只写独立 `report.json`。

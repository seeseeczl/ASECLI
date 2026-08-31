# 测试策略 — AseCLI

## 层级

1. **单元测试**（pytest）：core 解析/序列化、check 校验规则、checksum 重算；schema 查询。
2. **Roundtrip 测试**：真实 ASE `.shader` 样本 parse -> serialize -> 逐字节比对；变异操作后与预期最小差异比对。
3. **契约测试**：CLI 每个子命令 stdout 必须为合法 JSON 且含 `ok` 字段；错误码枚举固定。
4. **桥接集成测试**（需 Unity/Tuanjie 开启）：标记 `@pytest.mark.bridge`，验证 recompile 后 HLSL 变更与 CHKSM 更新。
5. **Agent 端到端**：SKILL.md 指引下完成一次自然语言改属性全流程。

## 门禁

| 场景 | 命令 | 要求 |
| --- | --- | --- |
| 本地/PR | `uv run pytest -q` | 全绿 |
| 里程碑 | `uv run pytest -q -m "not bridge"` + 架构校验脚本 | 全绿且追溯完整 |
| 发布前 | 全量含 bridge + 快速审计 | S0/S1 清零 |

## 夹具来源

- 真实样本：从 `/Users/long/Documents/Tuanjie/Genesis` 工程收集 5+ 个不同复杂度 ASE shader（脱敏路径后入 `tests/fixtures/`）。
- 函数样本：ASE 自带 ShaderFunction `.asset`（m_functionInfo 提取）。

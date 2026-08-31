# 回归目录 — AseCLI

| REG ID | 关联对象 | 名称 | 验证命令 | 状态 |
| --- | --- | --- | --- | --- |
| REG-0001 | FR-0001 | roundtrip-parse-serialize：真实样本逐字节一致 | `uv run pytest tests/test_roundtrip.py` | 已登记 |
| REG-0002 | FR-0002 | mutate-set-prop-minimal-diff：仅目标字段变化 | `uv run pytest tests/test_mutate.py::test_set_prop_minimal_diff` | 已登记 |
| REG-0003 | FR-0003 | validate-invalid-graph：断线/悬空引用被检出 | `uv run pytest tests/test_validate.py` | 已登记 |
| REG-0004 | FR-0003 | checksum-fix：破坏 CHKSM 后重算恢复 | `uv run pytest tests/test_checksum.py` | 已登记 |
| REG-0005 | FR-0004 CR-0001 | bridge-recompile：触发后 HLSL 变更且 CHKSM 更新 | `uv run pytest -m bridge tests/test_bridge_recompile.py` | 已登记 |
| REG-0006 | FR-0005 | create-from-template：模板创建在 Unity 正常打开 | `uv run pytest -m bridge tests/test_bridge_create.py` | 已登记 |
| REG-0007 | FR-0007 | cli-json-contract：所有子命令 stdout 合法 JSON | `uv run pytest tests/test_cli_contract.py` | 已登记 |
| REG-0008 | FR-0004 FR-0005 | assumption-experiments：盲改图数据/CHKSM/纯文本创建三实验结论回填 | 人工实验记录归档 `docs/01-architecture/assumption-experiments.md` | 已登记 |
| REG-0009 | FR-0002 | schema-extract-sample-match：10 种节点 schema 与真实文本逐字段一致 | `uv run pytest tests/test_schema_samples.py` | 已登记 |
| REG-0010 | FR-0006 FR-0007 | agent-end-to-end：技能指引下自然语言全流程 | 人工执行并归档会话记录 | 已登记 |
| REG-0011 | FR-0001 | perf-baseline：千节点级文件单命令 <1s | `uv run pytest tests/test_perf.py` | 已登记 |
| REG-0012 | FR-0008 | layout-deterministic-and-safe：布局确定性、连线不变、仅位置字段变化 | `uv run pytest tests/test_layout.py` | 已登记 |

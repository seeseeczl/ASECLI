# 回归目录 — AseCLI

| REG ID | 关联对象 | 名称 | 验证命令 | 状态 |
| --- | --- | --- | --- | --- |
| REG-0001 | FR-0001 | roundtrip-parse-serialize：真实样本逐字节一致 | `uv run pytest tests/test_roundtrip.py` | 已登记 |
| REG-0002 | FR-0002 | mutate-set-prop-minimal-diff：仅目标字段变化 | `uv run pytest tests/test_mutate.py::test_replace_node_minimal_diff` | 自动通过 |
| REG-0003 | FR-0003 | validate-invalid-graph：重复 ID/输入多来源等结构错误被检出 | `uv run pytest tests/test_graph_safety.py` | 自动通过 |
| REG-0004 | FR-0003 CR-0003 BUG-0006 | checksum-fix：破坏 CHKSM 后显式写入恢复 | `uv run pytest tests/test_cli_contract.py::test_fix_checksum_write_is_explicit_and_recoverable` | 自动通过 |
| REG-0005 | FR-0004 CR-0001 | bridge-recompile：触发后 HLSL 变更且 CHKSM 更新 | `ASECLI_TEST_SHADER=<隔离副本> uv run pytest -m bridge tests/test_bridge_recompile.py` | 真实 Tuanjie/MCP 已验证（1 passed） |
| REG-0006 | FR-0005 | create-from-template：模板壳与 donor 图组合正确并由 Editor 打开重存 | `uv run pytest tests/test_create.py` + 隔离 Editor 验收 | 自动与真实 Editor 已验证 |
| REG-0007 | FR-0007 CR-0003 BUG-0004 | cli-json-contract：所有子命令 stdout 合法 JSON | `uv run pytest tests/test_cli_contract.py` | 自动通过 |
| REG-0008 | FR-0004 FR-0005 | assumption-experiments：盲改图数据/CHKSM/纯文本创建三实验结论回填 | 人工实验记录归档 `docs/01-architecture/assumption-experiments.md` | 已登记 |
| REG-0009 | FR-0002 | schema-extract-sample-match：10 种节点 schema 与真实文本逐字段一致 | `uv run pytest tests/test_schema_samples.py` | 已登记 |
| REG-0010 | FR-0006 FR-0007 FR-0010 CR-0007 | agent-end-to-end：技能指引下自然语言 create→add-node→validate→recompile；Local Var 治理规则已进入 Skill，目标图应用在下一次实际 Shader 任务验收 | 按 `skills/asecli/SKILL.md` 在隔离工程人工执行并归档脱敏证据 | 原链路已验证；CR-0007 文档/真实参考静态通过，目标图待应用 |
| REG-0011 | FR-0001 BUG-0007 | perf-baseline：1000 个附加节点单轮 <1s | `uv run pytest tests/test_perf.py` | 自动通过 |
| REG-0012 | FR-0008 | layout-meticulous-progressive：布局确定性、连线不变、仅位置字段变化；严格列/行网格、DAG 向右递进、重复分支模板一致、Master 最右 | `uv run pytest tests/test_layout.py` | 自动验证几何契约；真实 ASE 精排感和贝塞尔线路径待实际图验收 |
| REG-0013 | FR-0002 CR-0002 BUG-0001 AUD-FE-001 AUD-DATA-001 | schema-add-version-safe：固定字段完整、跨版本不写入 | `uv run pytest tests/test_schema_add.py` | 自动通过 |
| REG-0014 | FR-0005 CR-0002 BUG-0002 AUD-FE-002 | create-graph-shell-safe：只替换 graph、不复制 donor 壳 | `uv run pytest tests/test_create.py` + 隔离 Editor 重存 | 自动与真实 Editor 已验证 |
| REG-0015 | FR-0002 FR-0003 CR-0002 BUG-0003 AUD-FE-003 | graph-write-invariants：拒绝重复 ID/输入多来源/结构字段修改 | `uv run pytest tests/test_graph_safety.py` | 自动通过 |
| REG-0016 | FR-0004 CR-0004 BUG-0005 AUD-FE-005 | mcp-tool-result：JSON-RPC/tool error/saved/changed 语义可靠 | `uv run pytest tests/test_bridge_contract.py` + 隔离 MCP 成功/失败路径 | mock 与真实 MCP 已验证；失败 exit 3 |
| REG-0017 | FR-0004 FR-0007 CR-0004 AUD-SEC-001 | mcp-trust-boundary：loopback 默认、远程 opt-in、token 脱敏、禁重定向 | `uv run pytest tests/test_mcp_security.py` + `127.0.0.1` smoke | 自动与真实 loopback 已验证 |
| REG-0018 | FR-0003 FR-0007 CR-0003 BUG-0006 AUD-FE-006 | checksum-dry-run：默认不写、显式写入可恢复 | `uv run pytest tests/test_cli_contract.py::test_fix_checksum_is_dry_run_by_default tests/test_cli_contract.py::test_fix_checksum_write_is_explicit_and_recoverable` | 自动通过 |
| REG-0019 | FR-0001 CR-0005 BUG-0009 AUD-ARCH-001 | core-public-parser：公开 parse_node_line 且旧 alias 兼容 | `uv run pytest tests/test_core_contract.py` | 自动通过 |
| REG-0020 | BUG-0008 AUD-GOV-001 | governance-catalog：登记的 pytest 文件/节点均可收集 | `uv run pytest tests/test_governance.py` | 自动通过 |
| REG-0021 | CR-0006 AUD-OPS-001 AUD-SUPPLY-001 | supply-delivery：CI governance、lock/Action/secret/license、SPDX 与可复现构建 | `uv run pytest tests/test_supply_chain.py` + 本地双构建/安装回滚 | 本地与 GitHub run 33510909955 已验证；下载 artifact 哈希/安装通过，远程 Release 未创建 |
| REG-0022 | FR-0009 CR-0010 | custom-gui-metadata-roundtrip：真实 HLIT/旧 MZGUI 样本格式读取；主 Master/编译指令同步；ASECLI 三标记写回、UTF-16 编码、旧标记读取和触碰迁移；dry-run/备份/CHKSM/注入/非 Property 失败路径 | `uv run pytest tests/test_custom_gui.py` | 自动通过（2026-09-02 定向 65 passed）；新的材质 Inspector UI 待目标工程验收 |
| REG-0023 | FR-0009 FR-0010 CR-0010 | material-gui-spec-atomic：属性名定位；JSON 顺序/中文分组/技术 Tooltip/常驻说明以 ASECLI 标记原子写回；未列属性稳定追加；重复/未知/错误类型/非 ASECLI 新增/dry-run/备份/CHKSM | `uv run pytest tests/test_custom_gui.py` | 自动通过（2026-09-02 定向 65 passed）；中文 `inspector_name` 由 EditorGraphSpec 契约覆盖；真实材质 Inspector UI 待目标工程验收 |
| REG-0024 | FR-0010 | commentary-native-grouping：原生可变长字段；自动边界；无关组不重叠、父子组完整包含；成员/节点/连线不变；重复归属/缺失/注入失败；dry-run/备份/CHKSM/roundtrip/CLI JSON | `uv run pytest tests/test_commentary.py` | 自动通过；真实参考 25 组只读解析且 validate 0 Comment 错误；真实 ASE 边距与层级视觉待目标工程验收 |
| REG-0025 | AA-OPT-009~016 | adversarial-hardening：Comment/Local Var 语义布局与校验；symlink/并发写保护；mixed-EOL；语义改名；尾部 CHKSM；Editor 窗口 finally 清理 | `uv run pytest tests/test_adversarial_hardening.py` | 自动通过；真实 303 节点图 25/25 Comment 保持；团结 2022.3.62t2 成功/异常窗口清理均通过 |
| REG-0026 | FR-0011 CR-0008 | editor-graph-spec：声明式规格白名单、端口存在/方向/基本类型、属性唯一性、别名、未知键、任意 C#/反射注入和 auto 路由在 MCP 前失败或确定选择 | `uv run pytest tests/test_editor_create_spec.py` | 自动通过 |
| REG-0027 | FR-0011 CR-0008 | editor-create-contract：固定 C#、参数安全编码、版本/成员门禁、Shader/模板身份、Save→Load manifest、关闭回滚与 MCP 假成功失败关闭 | `uv run pytest tests/test_editor_create_bridge.py` | 自动通过；真实正常关闭通过 |
| REG-0028 | FR-0011 CR-0008 | editor-create-transaction：已存在目标拒绝、失败无半写、暂存路径受限、结果文件 parse/validate | `uv run pytest tests/test_editor_create_cli.py` | 自动通过 |
| REG-0029 | FR-0011 CR-0008 | editor-create-real-e2e：隔离团结工程创建 Caster-like Sampler→Master 与 Receiver-like Property+CustomExpression，保存关闭重载 manifest 一致 | `ASECLI_EDITOR_CREATE_PROJECT=<隔离工程> ASECLI_TUANJIE_PATH=<编辑器> uv run pytest -m bridge tests/test_editor_create_e2e.py` | 真实团结 2022.3.61t9 + ASE 1.9.6.2 双进程通过（1 passed）；目标画面待验 |
| REG-0030 | FR-0009 CR-0010 | gui-support-asecli-installation：唯一 ASECLI GUI 的 dry-run/固定路径安装/幂等、冲突/符号链接/竞争拒绝、已存在原生 MZGUI 文件不阻断；C# 解释三类 ASECLI 标记并在无属性 API、原生同名旧 drawer 存在时只读恢复旧标记；自动技术 Tooltip | `uv run pytest tests/test_gui_support.py tests/test_custom_gui.py tests/test_cli_contract.py tests/test_material_gui_e2e.py` + `ASECLI_GUI_TEST_PROJECT=<带标记临时工程> ASECLI_TUANJIE_PATH=<团结可执行文件> uv run pytest -m bridge tests/test_material_gui_e2e.py` | 2026-09-02 定向 `67 passed, 1 skipped`，Python 3.10/3.12 全量均 `203 passed, 3 skipped`；团结 2022.3.61t9 当前实例验证新/旧分组、HelpBox、默认值以及展开/收起。用户提供的当前实例截图确认真实 Tooltip 浮层显示 `_BaseColor` 与 `RGBA(1.000, 1.000, 1.000, 1.000)` |
| REG-0031 | CR-0006 BUG-0010 AA-REL-001 | build-reproducibility-diagnostics：构建输出不进入 sdist；wheel/sdist 双构建一致；失败生成 hash/gzip/tar 成员差异 | `uv run pytest tests/test_build_reproducibility.py` + 临时 clone 仿真 CI 双构建 | 自动、本地与 GitHub run 33510909955 通过；下载 artifact 哈希/SPDX/隔离安装复验通过 |
| REG-0032 | FR-0009 BUG-0011 AA-DATA-001 CR-0010 | custom-gui-version-matrix：19109 仅使用真实 Master 契约；19602 支持 ASECLI 元数据与旧标记读取；未知未来版本及尾随数字歧义写前失败且输入不变 | `uv run pytest tests/test_custom_gui.py` | 自动通过（2026-09-02 定向 65 passed） |
| REG-0033 | FR-0004 BUG-0012 AA-PROTO-001 | json-rpc-response-correlation：SSE/JSON 当前、陈旧、重复、缺失 ID 均确定处理 | `uv run pytest tests/test_mcp_security.py` | 自动通过 |
| REG-0034 | FR-0011 BUG-0013 AA-FAIL-001 | editor-post-validation-preservation：后验失败及并发替换不删除目标/.meta，返回事务与 digest 诊断 | `uv run pytest tests/test_editor_create_cli.py tests/test_editor_create_bridge.py` | 自动通过 |
| REG-0035 | FR-0009 CR-0010 | gui-support-installation-hardening：固定目标的内容冲突、符号链接和竞争写入均拒绝；外部 MZGUI 文件不会影响 ASECLI 安装或推荐 Editor | `uv run pytest tests/test_gui_support.py` | 自动通过（2026-09-02 定向 65 passed）；无需原生反射 |

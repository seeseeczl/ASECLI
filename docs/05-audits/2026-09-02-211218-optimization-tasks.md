# 项目优化任务书

## 执行原则

- 只执行本任务书事项，先 P1，再 P2；没有 P0。每次只推进一个任务，不擅自扩大范围。
- 每完成一个步骤立即更新 TODO 和当前进展，不做顺手优化。
- 默认复用现有 Python/uv/pytest/Tuanjie/MCP 技术栈；新增依赖必须说明必要性、替代方案、成本和影响。
- 测试失败执行 Test-Fix Loop；非阻塞的计划外问题只记录。
- 不创建 commit、不 push、不打 tag、不发布 Release，除非用户在本任务书范围外另行授权。

## 总目标

- 在不改主链路行为的前提下，关闭 0.2.0 发布缺口、Editor 创建证据缺口、`reloaded` 契约歧义，并降低 C# 资源与治理门禁的误报。

## 范围

- 对应 `docs/05-audits/2026-09-02-211218-project-audit-report.md` 的开放问题 AUD-REL-001、AUD-FLOW-001、AUD-FE-001、AUD-SIZE-001、AUD-GOV-001。
- 允许修改发布记录、JSON 字段文档/兼容字段、治理配置与测试；默认不改 ASE 图语义。

## 非目标

- 不把 Windows/Linux、在线 SCA、OpenSpec、CodeGraph init、目标平台渲染扩进本轮。
- 不覆盖已关闭的基线 14 个 AUD 与 AA-COR-001/AA-FAIL-002/BUG-0017/BUG-0018。

## 问题到任务映射

| 问题 ID | 严重程度 | 优先级 | TODO ID | 处理方式 |
| --- | --- | --- | --- | --- |
| AUD-REL-001 | S2 | P1 | P1.1 | 单独处理（需用户发布授权才能完成验收） |
| AUD-FLOW-001 | S2 | P1 | P1.2 | 与 P1.3 顺序执行 |
| AUD-FE-001 | S2 | P1 | P1.3 | 单独处理契约字段 |
| AUD-SIZE-001 | S3 | P2 | P2.1 | 单独处理 |
| AUD-GOV-001 | S3 | P2 | P2.2 | 单独处理 |

## TODO

P0 必须完成
- 无 P0 任务。

P1 应该完成
- [x] P1.1 在授权后完成 0.2.0 不可变发布 — `v0.2.0` 指向 `6865aaa`；私有 Release 与 SHA256SUMS 复验通过；`v0.1.0` 回滚通过
- [ ] P1.2 补跑 Editor v2 新进程重开并归档脱敏证据 — 阻塞：隔离 Editor 环境变量未配置，且不得关闭用户正在运行的编辑器
- [x] P1.3 让 create Editor JSON 区分暂存重载与目标图重载

P2 可选优化
- [x] P2.1 将 C# 执行器纳入 LOC 门禁或具名豁免
- [x] P2.2 校准 Project Architect --strict 的 31 项历史项

当前进展：
- 已完成：P1.1、P1.3、P2.1、P2.2
- 正在做：无
- 下一步：若提供隔离团结工程和编辑器路径，再执行 P1.2
- 阻塞/风险：P1.2 缺少隔离 Editor 环境；新进程重开未纳入 v0.2.0 已验证范围

## 任务详情

### P1.1 在授权后完成 0.2.0 不可变发布

- 来源问题 ID：AUD-REL-001
- 依赖：无
- 严重程度：S2
- 目标：试用者能从私有 Release 安装与 main 契约一致的 0.2.0，并能回滚到 v0.1.0
- 范围：tag、GitHub Release、REL 记录、README 安装说明
- 非目标：不改 CLI 行为；不覆盖 v0.1.0 资产
- 涉及文件/模块/符号：`docs/04-delivery/releases/`、README.md、Git tag `v0.2.0`
- 现有技术栈复用：现有 CI artifact、REL-0002 流程、`uv tool install`
- 新增依赖：无
- 技术路径：复用 run 33625061100 已校验的 wheel/sdist 哈希；用户书面授权后再打 tag 与上传
- 执行步骤：
  1. 确认授权范围仅限 `v0.2.0`，核对 SHA256 `52b66d2a…fab0` 与 `53a63dbc…67a6` 仍指向同一 commit 产物或重新下载 HEAD artifact。
  2. 按交付协议创建 REL-0003、打 tag、上传 SHA256SUMS/SPDX，并在隔离环境安装验证 `--version`。
- 验收标准：`gh release view v0.2.0` 可下载；`shasum -a 256 -c SHA256SUMS` 通过；隔离安装 `asecli --version` 为 0.2.0；v0.1.0 仍可安装回滚。
- 验证方式：`gh release download`、隔离 `uv tool install`、`asecli --help` 列出 15 个子命令
- 风险：未授权执行会违反禁止自动发布；哈希与 tag 错位会破坏回滚
- 回滚/降级方案：删除未分发的错误 tag 仅在未有人下载前且用户明确要求时进行；已发布资产保持不可变
- 变更留档：REL-0003、timeline、traceability 的 REL 行
- 计划外问题处理规则：记录，不展开；只有阻塞 P1 时暂停并请求确认

### P1.2 补跑 Editor v2 新进程重开并归档脱敏证据

- 来源问题 ID：AUD-FLOW-001
- 依赖：无
- 严重程度：S2
- 目标：证明 v2 创建的目标 shader 可被全新 Editor 进程打开且 manifest/呈现仍成立
- 范围：隔离 Tuanjie 工程、REG-0037 证据回写、可选 `tests/test_editor_create_e2e.py`
- 非目标：不测目标平台渲染；不改用户生产工程
- 涉及文件/模块/符号：`src/asecli/bridge/editor_create.py`、`tests/test_editor_create_e2e.py`、REG-0037
- 现有技术栈复用：现有 bridge E2E 与独立 `recompile`
- 新增依赖：无
- 技术路径：关闭当前编辑器后启动新进程，只打开目标资产并比对创建 manifest
- 执行步骤：
  1. 在隔离工程用现有 v2 spec 创建临时 shader，完成独立 `recompile` 并记录 SHA-256。
  2. 完全退出编辑器后新进程打开同一资产，核对模板 GUID、节点/连接、`property_presentation.valid`，然后删除验证资产。
- 验收标准：新进程 Load 成功；manifest 一致；呈现 valid；无 `ASECLI-Temp-*`；REG-0037 更新为已验证新进程。
- 验证方式：`pytest -m bridge tests/test_editor_create_e2e.py` 加手工重开清单
- 风险：MCP 会话独占；误删非验证资产
- 回滚/降级方案：停止于证据记录，不改生产代码
- 变更留档：REG-0037、timeline、bug-register 若发现新缺陷
- 计划外问题处理规则：记录，不展开；只有阻塞 P1 时暂停并请求确认

### P1.3 让 create Editor JSON 区分暂存重载与目标图重载

- 来源问题 ID：AUD-FE-001
- 依赖：P1.2 可并行，但字段验收不依赖新进程
- 严重程度：S2
- 目标：Agent 不再把 `reloaded=true` 理解成提交后目标图已在 ASE 中重开
- 范围：`create_shader_via_mcp` 返回 JSON、CLI data、README/SKILL、editor_create 测试
- 非目标：不恢复提交后立刻 Load 目标图（会触发已知插件重连）
- 涉及文件/模块/符号：`src/asecli/bridge/editor_create.py`、`tests/test_editor_create_bridge.py`、`tests/test_editor_create_cli.py`、README.md、`skills/asecli/SKILL.md`
- 现有技术栈复用：现有单行 JSON 契约与失败优先测试
- 新增依赖：无
- 技术路径：增加显式布尔字段，保留 `reloaded` 兼容并文档化为 staging 语义，或同时输出 `target_graph_reloaded=false`
- 执行步骤：
  1. 先增加会失败的契约测试，断言当前成功 JSON 无法表达“目标图未重载”。
  2. 最小补充字段与文档，重跑 editor_create 与 CLI 测试。
- 验收标准：成功 JSON 含不可歧义的目标图重载状态；现有 saved/committed 行为不变；文档要求随后 `recompile`。
- 验证方式：`uv run --frozen pytest tests/test_editor_create_bridge.py tests/test_editor_create_cli.py tests/test_cli_contract.py`
- 风险：Agent 依赖旧字段名；需保持 `reloaded` 一段时间
- 回滚/降级方案：还原字段，仅改文档警告
- 变更留档：CR 或 TASK 回写 CLI 契约；timeline
- 计划外问题处理规则：记录，不展开；只有阻塞 P1 时暂停并请求确认

### P2.1 将 C# 执行器纳入 LOC 门禁或具名豁免

- 来源问题 ID：AUD-SIZE-001
- 依赖：无
- 严重程度：S3
- 目标：536/408 行执行器不再被报告成“LOC 全绿”
- 范围：`.project-architect.json` 或资源拆分
- 非目标：不重写 ShaderGUI 行为
- 涉及文件/模块/符号：`.project-architect.json`、`src/asecli/bridge/resources/*.cs.txt`
- 现有技术栈复用：现有 project-architect 配置
- 新增依赖：无
- 技术路径：优先具名豁免并写理由；若检查器只认 `.cs`，改为登记例外而不是改扩展名破坏打包
- 执行步骤：
  1. 确认检查器实际读取的是 `thresholds` 还是 `loc_thresholds`，避免只改无效键。
  2. 添加豁免或拆分 GUI 文件后重跑 `check_project_architecture.py`。
- 验收标准：审计能区分“已豁免的执行器”与“未扫描的盲区”；GUI 回归仍通过。
- 验证方式：`python3 .../check_project_architecture.py --root .` 与 `uv run --frozen pytest tests/test_gui_support.py tests/test_editor_create_bridge.py`
- 风险：改扩展名可能影响 Hatchling 打包
- 回滚/降级方案：恢复配置
- 变更留档：module-map 或 ADR 一句说明资源文件门禁
- 计划外问题处理规则：记录，不展开

### P2.2 校准 Project Architect --strict 的 31 项历史项

- 来源问题 ID：AUD-GOV-001
- 依赖：无
- 严重程度：S3
- 目标：`--strict` 要么退出 0，要么把剩余项写成已接受偏差
- 范围：任务卡 verification、module-map 反向 ID、`module_public_patterns` 或 core 公开导出
- 非目标：不借机重构 checks/bridge
- 涉及文件/模块/符号：`docs/04-delivery/project-plan-task-charter.md`、`docs/01-architecture/module-map.md`、`.project-architect.json`、`src/asecli/core/__init__.py`
- 现有技术栈复用：现有治理文件
- 新增依赖：无
- 技术路径：先补 TASK-0026/0028 的 REG 字段与地图反向链接；再决定公开导出 vs 放宽 public patterns
- 执行步骤：
  1. 按 `--format json` 逐条补 kickoff 与 traceability，禁止改业务逻辑。
  2. 对 4 项 fitness 私有导入做最小公开化或配置校准后重跑 `--strict`。
- 验收标准：同一 strict 命令退出 0，或偏差清单与条数一致并写入治理文档。
- 验证方式：`check_project_architecture.py --root . --check-docs --check-kickoff --check-traceability --check-fitness --strict`
- 风险：扩大 public patterns 会降低隔离信号
- 回滚/降级方案：恢复治理文件
- 变更留档：timeline 记一次治理校准
- 计划外问题处理规则：记录，不展开

## 进度更新模板

```markdown
## TODO

P1 应该完成
- [*] P1.1 当前任务
- [ ] P1.2 下一个任务

当前进展：
- 已完成：
- 正在做：
- 下一步：
- 阻塞/风险：
```

## Definition of Done

- [ ] 所有 S0/S1 和 P0/P1 问题均映射到 TODO，且每个 TODO 有完整详情。
- [ ] 已按 `.project-architect.json` 的分类阈值执行 LOC 门禁，排除项、截断和超限项均已记录。
- [ ] P0 完成并通过相关测试、构建或替代验证。
- [ ] 回归覆盖受影响模块和关键链路。
- [ ] OpenSpec 与 CodeGraph 的更新或不适用原因已说明。
- [ ] 需求变更、技术决策和实际修改文件已按现有机制增量留档并关联。
- [ ] 审计范围内每个功能模块均完成需求→入口→主路径→数据/状态→异常恢复→可观测性→回归→发布证据闭环对账。
- [ ] 审计范围内每个前端入口均有闭环结论或未验证原因。
- [ ] 七类专项工程审计均有状态，P0/P1 专项问题均映射 TODO。
- [ ] 请求/实际审计模式及降级原因已说明；增量对比已写入报告或说明不适用。
- [ ] UI 任务的 Product Design、视觉证据和可访问性验证情况已说明。
- [ ] 计划外发现已记录但未扩展处理。

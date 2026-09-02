# 对抗性审计优化计划：CR-0010 ASECLI GUI 协议迁移的发布前测试

> 生成时间：2026-09-02 12:11:55 CST
> 项目根目录：`/Users/long/GitHub/ASECLI`
> 关联报告：`docs/adversarial-audits/2026-09-02-121155-audit-report.md`

## 1. 执行摘要

- 审计对象：当前未提交的 CR-0010 ASECLI GUI 协议迁移及其发布链路。
- Findings 统计：P0=0，P1=2，P2=2，P3=0。
- 发布建议：阻塞。不得以当前工作树构建或分发试用包。
- 建议执行顺序：先修复越界写入（AA-OPT-001），再完成真实 Editor 门禁（AA-OPT-002），随后补足旧标记 fallback 与 README 工作流（AA-OPT-003、AA-OPT-004），最后重跑本地、远端与 artifact 证据链。

## 2. 修复与加固任务

| 任务 ID | 优先级 | 来源 Finding | 内容 | 验收标准 | 依赖 | 风险/回滚 |
| --- | --- | --- | --- | --- | --- | --- |
| AA-OPT-001 | P1 | AA-SEC-001 | 重写 GUI 资源创建链路：将目录创建和最终文件创建锚定到经验证的工程目录描述符；逐级拒绝符号链接，保留最终文件的排他创建与只清理本事务文件的约束。 | 现有缺失/冲突/目标符号链接/目标竞争测试通过；新增“父目录在打开前被替换为工程外符号链接”测试失败关闭，工程外文件不存在；正常临时工程安装保持成功。 | — | 平台 `dir_fd`/no-follow 语义差异。先在 macOS 与 CI Linux 测试；若不可统一实现，停止写入并返回稳定错误，不回退为普通路径写入。 |
| AA-OPT-002 | P1 | AA-REL-001 | 在隔离 Unity 或团结工程安装当前构建 wheel，真实编译当前 C# 资源；创建新标记 Shader 与旧标记 Shader（不依赖原生 MZGUI GUI 类）并做 Inspector 验收。 | 无 C# 编译 error；新/旧 Shader 的分组、Tooltip、HelpBox 都可读；Foldout 点击、Tooltip 悬停和 HelpBox 显示有可复核截图/日志；记录 Editor、ASE、wheel SHA-256 与运行命令。 | AA-OPT-001 完成后的 wheel | 只在隔离工程执行；不使用生产工程；不记录 MCP token 或用户资产路径。失败时停止发布并保留脱敏证据。 |
| AA-OPT-003 | P2 | AA-COMPAT-001 | 明确受支持的 Unity/Tuanjie API 矩阵，并处理 `GetShaderPropertyAttributes` 缺失时的旧属性读取：采用不依赖旧外部 drawer 的读取方案，或明确不支持且删除误导性 fallback/文档承诺。 | 对有/无 `GetShaderPropertyAttributes` 的目标版本分别有可执行验证；在宣称兼容的版本中，旧三标记均能产生等效 Inspector 元数据；不重新写入旧名称。 | AA-OPT-002 的实际版本信息 | 读取机制可能受 Unity 内部 API 调整影响；保留一次性告警和失败关闭，不把空元数据报告为成功。 |
| AA-OPT-004 | P2 | AA-DOC-001 | 修正 README 的逐属性工作流，使第一次写入同时设置 `--editor`，或先给可直接应用的带 `editor` JSON spec；保持所有后续命令与真实 CLI 契约一致。 | 从干净 Shader 按文档复制执行，第一次 metadata 写入 exit 0 且 JSON `written=true`；错误路径仍不写文件；README 所列唯一 editor 与 `gui-support` 输出一致。 | — | 仅更新与本流程直接有关的文档，避免重写既有安装/治理内容。 |

## 3. 测试补强任务

| 任务 ID | 优先级 | 覆盖缺口 | 内容 | 验收标准 |
| --- | --- | --- | --- | --- |
| AA-TEST-001 | P1 | 父目录 TOCTOU | 在 `tests/test_gui_support.py` 使用确定性 hook，在 `os.open` 前把 `Assets/Editor/ASECLI` 换为指向临时工程外目录的符号链接。 | 命令返回稳定错误、工程外目录无新文件、工程内无误报“installed”；旧目标竞争测试仍通过。 |
| AA-TEST-002 | P1 | 当前 C# 的真实行为 | 建立受环境变量保护的隔离 Editor 测试或人工验收脚本，覆盖新三标记和旧三标记。 | 未配置环境时明确 skip；配置后编译/属性读取/交互断言或可复核人工记录齐全。 |
| AA-TEST-003 | P2 | artifact GUI 安装路径 | 在 package job 安装 wheel 后，创建临时 `Assets`/`ProjectSettings` 并执行 `asecli gui-support ... --write`；校验 JSON 状态和资源 digest。 | CI artifact job 失败时阻断上传；成功时证明无源码工作树下的 GUI 资源可用。 |
| AA-TEST-004 | P2 | README 首条流程漂移 | 用最小 ASE 1.9.6.2 fixture 执行 README 的逐属性示例。 | 命令 exit 0，生成 ASECLI 属性名，且未省略 `--editor` 所需状态。 |

## 4. 观测与运维任务

| 任务 ID | 优先级 | 内容 | 验收标准 |
| --- | --- | --- | --- |
| AA-OBS-001 | P2 | 在发布记录中分开记录文本/自动化、真实 Editor、远端 CI 和下载 artifact 证据，并在 GUI 安装失败时保留不含绝对敏感路径的错误分类。 | 发布记录能逐项链接当前 commit、wheel SHA-256、Editor 版本和 CI run；不会把未运行门禁标成通过。 |

## 5. 发布门禁

- [ ] AA-OPT-001 与 AA-OPT-002 完成并复验。
- [ ] AA-OPT-003、AA-OPT-004 完成，或仅在有明确不支持范围、风险接受人和时间记录后继续。
- [ ] Python 3.10/3.12 回归、治理、回归目录、供应链、双构建和 artifact GUI 安装冒烟测试通过。
- [x] 当前 C# GUI 在隔离真实团结 Editor 完成新/旧标记编译与 Inspector 交互验收。
- [x] commit `e513fc5` push 后的远端 CI 通过；下载 artifact 后重算 hash，完成回滚观察。
- [x] 残留风险已在关联报告和发布记录中披露。

## 6. 未映射项（如有）

- 无。所有 P1/P2 findings 均已有修复任务；跨平台、在线漏洞数据库和目标渲染仍属于发布证据范围，不能因本地验证通过而自动接受。

## 7. 执行记录（2026-09-02）

- `AA-OPT-001` / `AA-TEST-001`：已完成。目录描述符锚定写入与父目录符号链接竞争反例已进入 `tests/test_gui_support.py`；写入失败关闭，工程外不生成资源。
- `AA-OPT-002` / `AA-TEST-002`：团结 BatchMode 部分已完成。当前 wheel 在隔离工程安装成功；隔离团结 `2022.3.61t9` 对当前资源执行 C# 编译、新/旧三标记 metadata、decorator 实例和 `_Value=1.25` 默认值验证，`tests/test_material_gui_e2e.py` 为 `1 passed`。不使用 Unity 2021 结果作为本 CR 的证据。
- `AA-OPT-003`：当前团结版本的 `ShaderUtil.GetShaderPropertyAttributes` 路径已通过真实验证；旧标记的内部读取 shim 已存在。没有可用的“API 缺失”团结目标版本，因此该 fallback 不能标为跨版本已验收，也不会扩展支持矩阵。
- `AA-OPT-004` / `AA-TEST-003` / `AA-TEST-004`：已完成，README 首次 metadata 写入携带唯一 `--editor`，CI package job 覆盖 wheel 安装后的 `gui-support --write` 烟测。
- Foldout 点击与 HelpBox 已由当前团结窗口验收；用户提供的当前实例截图确认 Tooltip 悬停浮层。完整双 Python 回归、双构建复现已通过；commit `e513fc5` 的远端 CI、下载 artifact hash 与回滚观察也已完成。

## 8. 实机执行补记（2026-09-02，团结 2022.3.61t9）

- `AA-OPT-003` 已完成并在当前运行实例验证：该版本没有 `ShaderUtil.GetShaderPropertyAttributes`；工程内已有的原生同名旧 drawer 会抢占 decorator。GUI fallback 改为只读取该 `Assets/` Shader 源文件的缺失元数据，旧标记不再依赖 ASECLI shim 被 Unity 选中。当前窗口日志验证旧标记读取到 `Legacy Group`、`Legacy tooltip`、`Legacy help text`，默认值仍为 `1.25`。
- [新增-必要] `AA-OPT-005` 已完成：将 `ShaderGUI` 的折叠状态改为静态并在切换时请求重绘，防止 IMGUI Layout/Repaint 重建实例后“箭头变化而内容未折叠”。当前窗口的新、旧样例均完成展开、收起、恢复，收起时属性、HelpBox 与 Followup 均消失。
- 自动回归：定向命令为 `67 passed, 1 skipped`；随后 Python 3.10、3.12 全量均为 `203 passed, 3 skipped`，`tools/check_regression_catalog.py` 和 `git diff --check` 通过。环境门控的 BatchMode E2E 未在本次修正后复跑，使用中的当前团结实例完成了 C# 编译与真实 Inspector 验收。
- 构建：两次 `uv build` 的 wheel/sdist 逐字节一致；wheel SHA-256 `a1e3b94cbb164d7cd9da4903bbf75ceb25083f2f718b32d69b7f5df6c7ea887f`，C# 资源 SHA-256 `97b5785812138b604898007998d6067e846e5e287e3f674940bfec37320c3109`。
- 远端交付门禁已闭合：commit `e513fc5` 的 CI、artifact hash 与隔离回滚均已完成。项目仍为内部专有工具；未创建 GitHub Release、PyPI 或公开分发。

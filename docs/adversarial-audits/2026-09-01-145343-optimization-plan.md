# 对抗性审计优化计划：ASECLI 未提交整改与 ASE 编排能力

> 生成时间：2026-09-01 14:53:43 CST
> 项目根目录：`/Users/long/GitHub/ASECLI`
> 关联报告：`docs/adversarial-audits/2026-09-01-145343-audit-report.md`

## 1. 执行摘要

- 来源 Findings：P0=0、P1=5、P2=3、P3=0。
- 发布阻断任务：AA-OPT-009、AA-OPT-010、AA-OPT-011、AA-OPT-013、AA-OPT-015。
- 建议顺序：先封堵写入与校验的灾难性风险，再恢复布局/Local Var 语义，最后补齐 roundtrip、创建和编辑器桥。
- 本文件是执行任务书，不代表任务已完成；状态以代码、自动测试和真实编辑器证据为准。

## 2. 稳定任务清单

| 任务 ID | 优先级 | 来源 | 工作内容 | 验收标准 | 依赖 | 回滚/边界 |
| --- | --- | --- | --- | --- | --- | --- |
| AA-OPT-011 | P1 | AA-SEC-011 | 重做安全写入原语：同目录唯一临时文件、独占创建、拒绝 symlink 目标/备份、`fsync` 后 replace | 预置 `.tmp/.bak` symlink 时命令失败且 victim 字节不变；正常写入仍生成可信备份 | — | 先独立提交；失败可回滚至只读命令，不能退回不安全写入 |
| AA-OPT-013 | P1 | AA-OPS-013 | 为 ASECLI 写者加入锁与源文件指纹；锁内提交前比较当前哈希，冲突返回 `WRITE_CONFLICT` | 两个旧快照修改不同节点时，后写者被拒绝；目标保留先写结果；JSON 给出 expected/actual 摘要但不泄露内容 | OPT-011 | 锁只能协调 ASECLI 进程；不宣称能约束不遵锁的 Editor |
| AA-OPT-015 | P1 | AA-COR-015 | 校验和只识别尾部独占整行 trailer；统一 `verify/fix/create` 的定位规则 | 前置注释含 `//CHKSM=` 时不截断；多标记、畸形 trailer 有明确错误；fixture 修复后图体与壳字节不丢失 | OPT-011 | 独立 checksum helper，可单任务回滚 |
| AA-OPT-010 | P1 | AA-COR-010 | 增加 Register/Get Local Var 解析、验证与删除保护 | 缺失目标、错误目标类型、名称/类型不一致、重复注册及引用环均产生 error；删除被引用 Register 被拒绝并列出 Get ID | OPT-011 | 不猜测未知 ASE 版本字段；不兼容版本先只读/拒写 |
| AA-OPT-009 | P1 | AA-COR-009 | 先加语义预检阻止不安全布局，再实现 Comment 复合单元与 Get→Register 语义边布局 | 真实回归图 `layout --write` 后 25/25 Comment 仍包围全部成员；Local Var 关系可读；节点/线/字段除位置外不变 | OPT-010 | 语义布局未完成前默认拒绝，不提供悄悄绕过的默认路径 |
| AA-OPT-012 | P2 | AA-COR-012 | 图指令逐行保存原始 EOL，新行使用明确的邻近/主导策略 | LF、CRLF、mixed-EOL、空行组合在无修改时逐字节一致；写入仅改变目标字段、checksum 与必要新行 | OPT-015 | 若无法可靠保真，先拒绝 mixed-EOL 写入 |
| AA-OPT-014 | P2 | AA-COR-014 | 严格校验 Shader 名；用解析后的 Master 语义字段改名，取消全文分号替换；写后重新解析/验证 | 引号、CR/LF、分号、控制字符被拒绝；Master 名正确更新；同名 Comment/帮助文本不变；输出 checksum 正确 | OPT-010、OPT-015 | 保持现有模板壳和 graph-from 行为，不扩展命名规则 |
| AA-OPT-016 | P2 | AA-OPS-016 | MCP C# 片段保存旧 `UIUtils.CurrentWindow`，在 `finally` 恢复并销毁临时窗口 | 静态契约测试确认 `try/finally`、restore、Destroy；真实编辑器成功与注入异常各执行一次，无残留窗口/状态污染 | — | 真实编辑器证据未取得前保持“待验收” |

## 3. 分阶段执行与门禁

### 阶段 A：写入安全闭环

完成 AA-OPT-011、013、015。

- 自动门禁：恶意 symlink、并发旧快照、多 checksum 标记、进程异常/磁盘错误模拟。
- 数据不变量：失败时目标、备份、外部 victim 都保持可证明状态；成功时输出可重新解析。
- 退出条件：所有写命令统一走一个安全提交入口，不允许 `Path.write_text/write_bytes` 绕过。

### 阶段 B：ASE 语义闭环

完成 AA-OPT-010、009、014。

- 自动门禁：真实格式的 Register/Get/Comment fixture；删除、改字段、布局、create 改名的正反用例。
- 关键不变量：Comment 成员关系、Local Var 引用、Custom GUI 文案/分组字段不得被非目标命令改变。
- 退出条件：`validate ok=true` 能覆盖工具主动创建和鼓励使用的全部隐式关系。

### 阶段 C：保真与编辑器闭环

完成 AA-OPT-012、016。

- 自动门禁：LF/CRLF/mixed-EOL 字节回归；C# 片段异常清理契约。
- 真实门禁：在 Unity/团结编辑器 + ASE 1.9.6.2 中加载、重编译并保存真实副本，检查 Console、窗口实例、Comment 框、Local Var 和 Shader 编译结果。
- 退出条件：自动测试、真实编辑器和文件哈希证据分别记录，不互相替代。

## 4. 回归测试任务矩阵

| 测试 ID | 覆盖任务 | 场景 | 预期 |
| --- | --- | --- | --- |
| AA-TST-009-A | OPT-009 | 含嵌套 Comment 的真实图布局 | 所有成员仍在框内，嵌套关系不变 |
| AA-TST-009-B | OPT-009/010 | Register 被多个 Get 复用 | 布局可读且引用完整 |
| AA-TST-010-A | OPT-010 | Get 指向不存在/非 Register 节点 | validate error，禁止写入 |
| AA-TST-010-B | OPT-010 | 删除被引用 Register | 原子失败并列出引用者 |
| AA-TST-011-A | OPT-011 | `.tmp`/`.bak` 是 symlink | victim 不变，目标不被替换为 symlink |
| AA-TST-013-A | OPT-013 | 两个旧快照先后写不同节点 | 第二次 `WRITE_CONFLICT`，无丢失更新 |
| AA-TST-015-A | OPT-015 | 源码注释含伪 checksum marker | 正确处理尾部 trailer，文件不截断 |
| AA-TST-012-A | OPT-012 | mixed-EOL 无修改 roundtrip | 输入输出字节完全相同 |
| AA-TST-014-A | OPT-014 | 注入名称与同名 Comment | 注入被拒绝；合法改名不污染 Comment |
| AA-TST-016-A | OPT-016 | Editor 成功/异常重编译 | 临时窗口销毁，原 CurrentWindow 恢复 |

## 5. 完成定义

只有同时满足以下条件，才能把本计划标为完成：

1. 8 个任务均有独立代码差异与对应回归，Finding ID 能追溯到测试。
2. Python 3.10/3.12 全量测试通过，且不再以跳过真实桥测试作为重编译完成证据。
3. 对 7 个已复现脚本重新执行，原错误结果全部转为明确拒绝或正确行为。
4. 在真实 ASE 编辑器副本完成 Comment、Local Var、Custom GUI、重编译保存验收。
5. `git diff --check` 通过；工作树中用户原有未提交修改得到保留，不执行 reset/stash/clean。

## 6. 发布与回滚策略

- 每个任务独立提交，先测试后合并；不得把安全写入、布局算法和 Editor 桥混成不可拆分的大提交。
- 阶段 A 任一门禁失败时，回滚到只读能力或禁用 `--write`，不带病发布。
- 阶段 B 语义尚不完整时，允许查询 Comment/Custom GUI/Local Var，但不允许声称可安全自动整理。
- 阶段 C 真实 Editor 未验收时，发布说明必须标注桥接能力未完成目标环境验证。

## 7. 执行结果（2026-09-01 15:20 CST）

| 任务 | 状态 | 完成证据 |
| --- | --- | --- |
| AA-OPT-009 | 已完成 | Comment 作为固定复合单元；Register→Get 进入布局边；真实 303 节点副本布局后 25/25 分组、全部成员保持框内 |
| AA-OPT-010 | 已完成 | Get 目标/名称/类型/循环校验与 Register 删除保护；对抗回归通过，真实参考图 validate 0 error |
| AA-OPT-011 | 已完成 | 唯一临时文件、nofollow、symlink 拒绝、fsync/replace 和安全备份；victim 保持不变 |
| AA-OPT-012 | 已完成 | 图内逐行 EOL 保留；mixed-EOL 从文本和磁盘读取均逐字节 roundtrip |
| AA-OPT-013 | 已完成 | 进程锁、SHA-256 源指纹和 `WRITE_CONFLICT`；双旧快照后写被拒绝，先写结果保留 |
| AA-OPT-014 | 已完成 | Shader 名严格校验与主 Master 精确字段更新；注入被拒绝，同名 Comment 保持不变 |
| AA-OPT-015 | 已完成 | 仅接受尾部独占 checksum trailer；前置 decoy 不再截断，多独占标记明确报错 |
| AA-OPT-016 | 已完成 | `try/finally` 恢复 `CurrentWindow` 并销毁窗口；团结 2022.3.62t2 实测 `saved=True successClean=True exceptionClean=True` |

最终门禁：Python 3.10/3.12 均为 `127 passed, 1 skipped`；跳过项仍是需要 `ASECLI_TEST_SHADER` 的常规 MCP pytest，但本次已用隔离 `Shader_Opt` 工程执行同等真实 ASE 成功/异常路径。治理、供应链、回归目录检查与 `git diff --check` 均通过。真实探针文件已移出工程，日志保存在 `/tmp/asecli-editor-probe-20260901-145343.log`。

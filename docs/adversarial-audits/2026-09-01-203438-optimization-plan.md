# 对抗性审计优化计划：ASECLI `acb74a0` 发布与跨版本写入链路

> 生成时间：2026-09-01 20:34:38 CST
> 项目根目录：`/Users/long/GitHub/ASECLI`
> 关联报告：`docs/adversarial-audits/2026-09-01-203438-audit-report.md`

## 1. 执行摘要

- 审计对象：`main@acb74a0` 的远程交付、ASE/MZGUI 跨版本语义写入、Editor 失败事务、MCP 响应关联与 GUI 提供者检测。
- Findings 统计：P0=0 P1=2 P2=2 P3=1。
- 计划生成时发布建议：阻塞远程 artifact 发布；不得把本地双构建或全量测试通过替代失败的 GitHub package job。已验证的 ASE 1.9.6.2 源码路径可条件使用，未知版本禁止写入。
- 建议执行顺序：先恢复远端 artifact 门禁并封闭未知版本写入，再修复文件事务与 JSON-RPC 关联，最后补齐 GUI 提供者检测。

## 2. 修复与加固任务

| 任务 ID | 优先级 | 来源 Finding | 内容 | 验收标准 | 依赖 | 风险/回滚 |
| --- | --- | --- | --- | --- | --- | --- |
| AA-OPT-001 | P1 | AA-REL-001 | 保留双构建 `cmp`，采集并比较 gzip header、tar 成员内容/顺序/mtime/mode/uid/gid，消除 Linux runner 上的 sdist 非确定字段 | 同一全新 GitHub runner 上连续两次 wheel/sdist 逐字节一致；package job 生成并上传 wheel、sdist、SHA256SUMS、SPDX、供应链结果；下载后 hash 与 manifest 一致 | — | 禁止删除/放宽一致性门禁；不能稳定时仅分发已证明可复现的格式并记录单独 CR |
| AA-OPT-002 | P1 | AA-DATA-001 | 为 Master CustomEditor 与 Property MZGUI 尾部分别建立真实样本支持矩阵和完整 schema/signature；未知版本写操作失败关闭 | `19602` 原始样本 roundtrip 通过；`25000` + `UNRELATED_FIELD_9` + `FUTURE_SEMANTIC_FLAG;0` 反例稳定拒绝且输入逐字节不变；错误在备份/写盘前发生 | — | 不把“字段数量相近”当兼容；新增 ASE 版本必须先采证、再注册，回滚为只读支持 |
| AA-OPT-003 | P2 | AA-FAIL-001 | 把失败回滚所有权收回 Editor 事务，以 nonce/manifest 识别暂存与最终资产；Python 禁止无身份路径删除 | 自动竞态用例在文件被替换或原位修改时保留新文件和 `.meta`，返回可诊断错误；正常后验失败只清理能证明属于当前 nonce 的资产 | AA-OPT-004 | 若两阶段提交改动过大，安全回滚策略是保留失败产物并提示人工删除，而非冒险 unlink |
| AA-OPT-004 | P2 | AA-PROTO-001 | `_post/_rpc` 对 SSE 与普通 JSON 响应执行精确 JSON-RPC ID 关联，拒绝缺失/重复/错 ID | 多 frame 中只返回当前 ID；仅有 `999`、重复当前 ID、普通 JSON 错 ID 均抛稳定 `McpError`；initialize/recompile/create 现有回归不变 | — | 保持 notification 无响应语义；协议不确定时失败，不回退到“最后一帧” |
| AA-OPT-005 | P3 | AA-COMPAT-001 | 扩展源码检测并增加 Unity 运行时类型反射；静态无法判定时引入 `unknown` 状态 | 裸基类、`UnityEditor.ShaderGUI`、`global::UnityEditor.ShaderGUI` 和任意文件名程序集内 `MZGUI.MZGUI` 均识别；原生存在时 `--write` 零写盘 | — | 避免用过宽正则把非 ShaderGUI 同名类当提供者；反射不可用时不得把 unknown 降级成 missing |

## 3. 测试补强任务

| 任务 ID | 优先级 | 覆盖缺口 | 内容 | 验收标准 |
| --- | --- | --- | --- | --- |
| AA-TEST-001 | P1 | 跨版本测试只换版本号 | 保存每个获准版本的最小原始节点行与来源信息，增加未来字段/尾随数字歧义反例 | 每个可写版本至少一份真实正向样本；每种未知/歧义结构均失败且序列化输入不变 |
| AA-TEST-002 | P1 | 远端失败时无可诊断差异 | package 失败时上传两份 sdist、解压清单和确定性 diff 作为诊断 artifact | 即使 `cmp` 失败也能从 artifact 定位首个不同成员/元数据；正式 dist 仍不得上传为可发布包 |
| AA-TEST-003 | P2 | JSON-RPC 关联无多帧反例 | 增加 SSE 当前帧后跟陈旧帧、错 ID error、重复 ID、notification-only 和普通 JSON 错 ID 测试 | 所有响应都与发出的 payload ID 一一对应，错误不会串到相邻调用 |
| AA-TEST-004 | P2 | 后验清理无竞态用例 | 在 RPC 返回与 parse/validate 之间注入 replace、原位写和 `.meta` 替换 | 非本事务内容全部保留；CLI 不报告成功，并给出目标身份变化诊断 |
| AA-TEST-005 | P3 | 提供者检测只覆盖裸基类源码 | 增加全限定/global/别名源码和任意文件名 DLL/asmdef 场景 | 原生存在不安装兼容层；确实缺失才允许固定路径创建 |

## 4. 观测与运维任务

| 任务 ID | 优先级 | 内容 | 验收标准 |
| --- | --- | --- | --- |
| AA-OBS-001 | P1 | package job 输出构建工具版本、两个文件 hash、gzip/tar 规范化摘要和首个差异 | 远端失败日志无需下载原始包即可区分 header、成员元数据和内容差异 |
| AA-OBS-002 | P2 | Editor 创建结果记录 transaction nonce、目标 path、Shader 名、内容 digest、提交/回滚状态 | Python 后验结果可与 Editor 事务逐字段对账，且日志不含 MCP token |
| AA-OBS-003 | P3 | `gui-support` 区分 `native_mzgui`、`asecli_compat`、`missing`、`unknown` | 自动化调用方不会把“扫描未发现”误解为“已证明不存在” |

## 5. 发布门禁

- [x] 所有 P0 任务完成（本轮无 P0）。
- [x] 所有 P1 任务完成或由 owner/批准人记录有期限的风险接受。
- [x] GitHub package job 双构建、artifact 上传、下载后 hash/SBOM/隔离安装全部通过。
- [x] 未知 ASE 版本的 CustomEditor/MZGUI 反例在任何写盘前失败关闭。
- [x] SSE 响应关联与 Editor 文件竞态回归通过。
- [x] 残留风险与真实 Inspector/目标渲染未验边界继续保留。

## 6. 未映射项（如有）

- 无。5 个 Finding 均映射到 AA-OPT；P2/P3 未获风险接受，当前仅按优先级排在两个发布阻塞项之后。

## 7. 计划生成时的执行边界

- 本轮只生成审计报告和优化计划，没有修改业务代码，也没有将任何任务标记为已修复。
- 当前自动回归为 `189 passed, 2 skipped`；GitHub Actions run `33507715846` 仍为 failure，故发布门禁保持未完成。

## 8. 执行结果（2026-09-01）

- AA-OPT-001～005、AA-TEST-001～005 与 AA-OBS-001～003 已实现；本地全量结果为 `206 passed, 2 skipped`，两个 skip 均为既有外部 Editor bridge 条件用例。
- GitHub Actions run [33510909955](https://github.com/seeseeczl/ASECLI/actions/runs/33510909955) 在 `a3e6fcda5751576a4a5ed5a8096adf67d7a2015c` 上通过 Python 3.10、Python 3.12 与 package 三个 jobs；双 wheel/sdist 构建逐字节一致，随后完成 SHA256SUMS、SPDX、离线供应链检查、隔离安装、CLI smoke 与 artifact 上传。
- 下载 artifact `asecli-0.1.0-python-X64`（artifact ID `9801594662`）后复算：wheel `6b92cfb4287c5d46a288966ca11fb92d52bf706201a1615a8cc413f158cb6446`，sdist `cb0318dd2ec275088f38d767f82a473b312982912464bad24b2c3f60a0a85558`，与 `SHA256SUMS` 和 SPDX annotation 一致；下载 wheel 在全新 Python 3.12.11 环境安装并成功执行 `asecli parse`。
- 发布门禁已恢复，但这不是 GitHub Release/PyPI 发布。`gui-support --runtime-probe` 的固定反射实现与契约测试已完成，尚未连接用户目标 Editor 执行；真实材质 Inspector 交互、ASE 画布精排感和目标渲染仍未验。

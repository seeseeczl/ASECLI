---
id: QUALITY-DEFECTS-0001
type: bug-register
status: verified
version: 1.1.0
created_at: 2026-09-01T12:54:38+08:00
owner: long
related: [AUD-20260901, CR-0002, CR-0003, CR-0004, CR-0005, CR-0011, CR-0012, BUG-0015, BUG-0016, BUG-0017, BUG-0018]
supersedes: []
evidence: [tests, docs/03-quality/regression-catalog.md]
---

# 缺陷与回归登记 — 2026-09-01

| BUG ID | 来源 | 失败表现 | 先失败 REG | 最小修复 | 当前证据 |
| --- | --- | --- | --- | --- | --- |
| BUG-0001 | AUD-FE-001 AUD-DATA-001 | schema 节点固定字段缺失且版本不匹配仍可写 | REG-0013 | 完整 fixed prefix + schema 版本门禁 | 自动已验证 |
| BUG-0002 | AUD-FE-002 | create 复制 donor 文件壳，可能出现双 Shader/YAML | REG-0014 | `AseFile.replace_graph` 仅替换图块 | 自动与隔离 Editor 已验证 |
| BUG-0003 | AUD-FE-003 | 重复 ID、输入多来源、结构字段修改可被提交 | REG-0015 | core/checks 不变量 + CLI 写前门禁 | 自动已验证 |
| BUG-0004 | AUD-FE-004 | argparse 失败 stdout 为空且不可解析 | REG-0007 | `JsonArgumentParser` 将错误映射为 JSON | 自动已验证 |
| BUG-0005 | AUD-FE-005 | JSON-RPC 成功时忽略 MCP tool `isError`/saved 失败 | REG-0016 | 集中解析 tool text 并要求 `saved=True` | mock 与真实 MCP 成功/失败路径已验证 |
| BUG-0006 | AUD-FE-006 | fix-checksum 默认隐式写盘 | REG-0018 | 默认预览，显式 `--write` 才原子写入 | 自动已验证 |
| BUG-0007 | AUD-PERF-001 | 性能测试仅 200 个附加节点且含恒真断言 | REG-0011 | 1000 个附加节点、1007 精确数量、5 轮 roundtrip | 自动已验证 |
| BUG-0008 | AUD-GOV-001 | REG/TASK 指向不存在测试和过期模块 | REG-0020 | catalog collect 检查 + 当前事实源校准 | 自动已验证 |
| BUG-0009 | AUD-ARCH-001 | CLI 跨模块导入 core 私有解析符号 | REG-0019 | 公开 API + 兼容 alias | 自动已验证 |
| BUG-0010 | AA-REL-001 | 第二次仓库内构建把第一次 `build-a` 产物重新装入 sdist，远端可复现性门禁失败 | REG-0031 | 构建输出移出 checkout；锁定 build backend；失败时保留结构化差异证据 | 已解决；GitHub run 33510909955 与下载 artifact 复验通过 |
| BUG-0011 | AA-DATA-001 | 未知 ASE 数值版本沿用已知 CustomEditor/MZGUI 字段并发生猜写 | REG-0032 | 分离真实 CustomEditor/MZGUI 版本矩阵；未知版本写入失败关闭 | 自动已验证 |
| BUG-0012 | AA-PROTO-001 | SSE/JSON 响应未与当前 JSON-RPC ID 精确关联 | REG-0033 | 所有请求响应强制 ID 一一匹配 | 自动已验证 |
| BUG-0013 | AA-FAIL-001 | Editor 后验失败按路径删除目标，可误删并发替换的用户文件 | REG-0034 | Python 保留无法证明身份的失败产物并输出事务诊断 | 自动已验证 |
| BUG-0014 | AA-COMPAT-001 | 全限定基类或预编译程序集中的原生 MZGUI 被静态漏检 | REG-0035 | 扩展源码检测；二进制不确定时阻止写入并支持 Editor 反射确认 | 自动已验证；真实反射待目标 Editor |
| BUG-0015 | 用户当前团结实例截图对照 | ASECLI 把目标轻量说明条渲染成原生 Info HelpBox，出现大图标、描边和过高容器，功能存在但视觉规范不一致 | REG-0036 | 固定 `asecli.inline-help.v1`，由 `gui-support` 报告契约并在内置资源失效时拒绝安装；C# 改为轻量自绘 | 自动回归与当前团结 `2022.3.61t9` Inspector 已验证；Console 0 error |
| BUG-0016 | CR-0012 当前团结 v2 创建实测 | MCP for Unity 3.4.7 把 C# 返回值包在 `data.result`，默认安全扫描拦截固定事务执行器的 `DeleteAsset`，提交后的第二次图重载又可能在协议返回前触发插件重连，导致目标已创建但 CLI 报 `BRIDGE_ERROR` | REG-0038 | 兼容裸文本/JSON envelope；`success=false` 失败关闭；仅固定 nonce 事务执行器关闭该次模式扫描；暂存 Save/Load+manifest 后提交并只核对目标 Shader 身份，完整目标图重载交给紧随其后的独立 `recompile` | 自动回归通过；当前团结 `2022.3.61t9`、MCP 3.4.7 的 v2 创建与再次重编译通过，无 `ASECLI-Temp-*` 残留；Inspector 视觉和 Tooltip 已由用户现场确认，验证资产已精确清理 |
| BUG-0017 | `0.2.0` 首次推送后的 GitHub Actions run 33623943475 | package job 已生成 `0.2.0` wheel，但 CI 安装、SPDX 输出和 artifact 名仍硬编码 `0.1.0`；隔离安装步骤找不到旧文件并使远端门禁失败 | REG-0039 | CI 从 `uv version --short` 注入单一版本变量；安装、SPDX 和 artifact 名统一引用该变量；SBOM 从 `uv.lock` 读取项目版本；治理检查拒绝工作流中的硬编码版本 | Python 3.10/3.12 verify 已通过；本地失败优先与修复后回归通过，等待修复提交的远端 package 复验 |
| BUG-0018 | run 33624498244 的下载 artifact 复验 | `SHA256SUMS` 在 CI 仓库根目录生成，条目包含 `dist/` 前缀；artifact 下载后文件位于解压根目录，标准 `shasum -c SHA256SUMS` 找不到 wheel/sdist | REG-0040 | 进入 `dist` 后生成清单，只记录 artifact 文件名；CI governance 拒绝重新使用 `dist/*` 输入路径 | run 33624498244 构建和实际文件哈希正常，但下载后清单校验先失败；本地修复后通过，等待远端 artifact 复验 |
| BUG-0019 | AUD-UI-001 / 真实 480px、300px Inspector | 超长中文属性显示名沿用单行标签布局，在窄 Inspector 被截断且与值字段争夺宽度 | REG-0042 | 长标签按当前视图宽度检测；标签换行独占一行，字段下一行全宽绘制 | 新测试先失败后通过；深/浅色 300px 与深色 480px 截图通过 |
| BUG-0020 | AUD-UI-001 / 真实 Tooltip 默认值反射 | Unity float 直接使用 `G9` 输出，暴露 `0.800000012`、`0.649999976` 等二进制浮点噪声 | REG-0042 | 统一使用 `0.######` invariant 格式；整数和 Toggle 语义保持不变 | 新测试先失败后通过；实机反射 `_BaseColor=(0.8, 0.2, 0.1, 1)`、`_Smoothness=0.65`、`_Intensity=1.25` |
| BUG-0021 | REG-0045 从完全清理的隔离 Assets 重跑 | `tests/test_editor_create_e2e.py` 只创建空 `Generated` 目录，团结首次 AssetDatabase Refresh 会移除无资产目录，ASE 保存 nonce 暂存 Shader 时抛 `DirectoryNotFoundException` | REG-0045 | 启动 Editor 前在 Generated 写入隐藏占位文件，保证首次刷新后目录仍存在；不改 CLI 或 ASE 事务 | 失败 `1 failed/16.78s` 后，同一干净隔离工程重跑 `1 passed/39.86s`；双进程、manifest/presentation 与零 staging 断言通过 |

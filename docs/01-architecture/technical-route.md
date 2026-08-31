# 技术路径 — AseCLI

## 架构决策记录

### ADR-0001 采用 Python + uv 的模块化单体 CLI

- 状态：已确认（2026-08-31）
- 背景：需要跨平台本地工具，被 AI Agent 以子进程方式调用。
- 决策：Python >=3.10 + uv 管理；`src/asecli` 六模块单仓；CLI 为组合根。
- 理由：用户环境 Python 3.12 已就绪；Agent 生态（skill 文档 + CLI 调用）天然匹配；打包分发用 `uv tool install`。
- 备选被拒：Node/Go 单二进制（跨语言维护成本高，无团队熟悉度收益）；纯 shell 脚本（无法承载 schema 数据库与 roundtrip 测试）。

### ADR-0002 编译桥接复用 Codely Bridge，不自建 IPC

- 状态：已确认（2026-08-31）
- 背景：ASE 编译后 HLSL 必须由 Unity/团结引擎生成；用户环境已装 Codely CLI 与 `cn.tuanjie.codely.bridge@1.0.54`。
- 决策：在目标工程放置一个 C# MenuItem 桥接脚本（ASECliBridge），经 Codely 的 `unity_menu` / `execute_custom_tool` 触发；Python 侧 bridge 模块只负责拼装调用。
- 理由：零新增基础设施；团结引擎第一方兼容。
- 备选被拒：自建 Editor WebSocket 服务（维护成本高、权限面大）；Unity batchmode 冷启动（每次 30s+，交互式使用不可接受；保留为无 Codely 环境的降级路径）。

### ADR-0003 节点 schema 由 ASE 源码静态提取 + 样本比对验证

- 状态：已确认（2026-08-31）
- 背景：400+ 节点类型的参数顺序/类型/默认值各不相同，Agent 无法可靠记忆。
- 决策：一次性提取脚本扫描 ASE C# 源码中节点序列化字段，生成版本化 `schemas.json`；对真实 `.shader` 样本逐字段抽查验证；未知节点 passthrough。
- 理由：手工维护 400+ schema 不可持续；运行时依赖 ASE 源码不可分发。
- 风险与缓解：静态分析遗漏面 → 以真实样本比对为门禁（REG-0009），遗漏项手工补录进 JSON。

### ADR-0004 发布策略：本地优先，Hub 提交后置

- 状态：已确认（2026-08-31）
- 决策：MVP 以本地 `uv tool install` + Agent 技能交付；CLI-Anything Hub 提交在稳定运行一个版本周期后评估。
- 理由：用户目标是自用自动化；发布流程不应阻塞核心链路验证。

## 质量与部署约束

- 门禁：`uv run pytest -q` 全绿；roundtrip fixture 测试覆盖真实 ASE 样本。
- 可观测性：stdout 仅 JSON（Agent 契约），诊断与进度走 stderr；退出码区分成功/校验失败/桥接失败。
- 部署：`uv tool install .` 本地安装；升级即重装，无数据迁移。

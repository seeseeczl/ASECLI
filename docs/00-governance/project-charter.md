# 项目章程 — AseCLI

- 项目 ID：PRJ-ASECLI
- 名称：AseCLI — 让 AI Agent 创建/修改 Amplify Shader Editor 文件
- 状态：active
- Owner：long
- 上游输入：`docs/first-principles/2026-08-31-231401-optimization-plan.md`（第一性原理计划书，推荐方案 B）
- 需求基线：`docs/01-architecture/project-architecture-and-requirements.md`（ARCH-REQ-0001）
- Profile：core + ai-agent

## 一句话使命

让支持 Agent Skills 的主流编码 Agent（Codex、Claude Code、Cursor、Gemini CLI、GitHub Copilot 等）通过自然语言驱动，可靠地解析、修改、校验、编译与创建 ASE Shader 文件；用户只提需求与验收效果。

## 边界

- 本项目是开发工具链（Python CLI + Agent 技能 + Unity 桥接脚本），不是 ASE 替代品，不含可视化编辑器。
- 编译能力复用团结引擎与 Codely Bridge，不自建 Unity IPC。
- 本期不发布到 CLI-Anything Hub（后置可选项，见 ADR-0004）。

## 关键决策

| 决策 | 记录 |
| --- | --- |
| 技术栈 Python + uv，模块化单体 CLI | ADR-0001 |
| 编译桥接复用 Codely Bridge | ADR-0002 |
| 节点 schema 由 ASE 源码静态提取 + 样本比对 | ADR-0003 |
| 本地优先发布，Hub 提交后置 | ADR-0004 |

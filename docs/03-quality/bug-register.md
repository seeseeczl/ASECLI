---
id: QUALITY-DEFECTS-0001
type: bug-register
status: verified
version: 1.0.0
created_at: 2026-09-01T12:54:38+08:00
owner: long
related: [AUD-20260901, CR-0002, CR-0003, CR-0004, CR-0005]
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

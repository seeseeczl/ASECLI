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
| BUG-0010 | AA-REL-001 | 第二次仓库内构建把第一次 `build-a` 产物重新装入 sdist，远端可复现性门禁失败 | REG-0031 | 构建输出移出 checkout；锁定 build backend；失败时保留结构化差异证据 | 本地已修复，远程待验 |
| BUG-0011 | AA-DATA-001 | 未知 ASE 数值版本沿用已知 CustomEditor/MZGUI 字段并发生猜写 | REG-0032 | 分离真实 CustomEditor/MZGUI 版本矩阵；未知版本写入失败关闭 | 自动已验证 |
| BUG-0012 | AA-PROTO-001 | SSE/JSON 响应未与当前 JSON-RPC ID 精确关联 | REG-0033 | 所有请求响应强制 ID 一一匹配 | 自动已验证 |
| BUG-0013 | AA-FAIL-001 | Editor 后验失败按路径删除目标，可误删并发替换的用户文件 | REG-0034 | Python 保留无法证明身份的失败产物并输出事务诊断 | 自动已验证 |
| BUG-0014 | AA-COMPAT-001 | 全限定基类或预编译程序集中的原生 MZGUI 被静态漏检 | REG-0035 | 扩展源码检测；二进制不确定时阻止写入并支持 Editor 反射确认 | 自动已验证；真实反射待目标 Editor |

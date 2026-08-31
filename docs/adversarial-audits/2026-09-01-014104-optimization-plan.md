# 对抗性审计优化计划：AseCLI 全量代码

> 生成时间：2026-09-01 01:41:04
> 项目根目录：/Users/long/GitHub/AseCLI
> 关联报告：`docs/adversarial-audits/2026-09-01-014104-audit-report.md`

## 1. 执行摘要

- 审计对象：AseCLI 全部源码与测试（commit 3898d64）
- Findings 统计：P0=0 P1=3 P2=3 P3=2
- 发布建议：条件通过——完成 AA-OPT-001~004 后进入用户验收
- 建议执行顺序：OPT-001 → OPT-002 → OPT-003 → OPT-004 → OPT-005 → OPT-007 → OPT-006（验收项）

## 2. 修复与加固任务

| 任务 ID | 优先级 | 来源 Finding | 内容 | 验收标准 | 依赖 | 风险/回滚 |
| --- | --- | --- | --- | --- | --- | --- |
| AA-OPT-001 | P1 | AA-COR-001 | EOL 感知解析/序列化：识别 `\r\n`/`\n`，按原始行尾重建；写文件 `newline=""` 禁止翻译 | CRLF fixture roundtrip 逐字节一致；既有 LF 测试不回归 | — | 影响所有序列化路径；roundtrip 全量测试把关 |
| AA-OPT-002 | P1 | AA-COR-002 | 空行作为指令保序保留 | 图尾/中部加空行后 roundtrip 一致；validate 不再误报 | — | 无 |
| AA-OPT-003 | P1 | AA-COR-003 | `create --name` 同步替换节点行内分号定界的旧名字段 | 创建后节点行不含旧名；checksum 重算正确 | — | 名字含分号时拒绝（usage error） |
| AA-OPT-004 | P2 | AA-OPS-004 | 原子写（tmp+os.replace）+ 覆盖前 `.bak` 备份 | 强制中断模拟后半写状态不存在；`.bak` 生成 | — | 磁盘占用翻倍（可接受） |
| AA-OPT-005 | P2 | AA-COR-005 | add-node 检测 32 位 hex 字段并在 JSON 输出 warnings 提示 | 含 guid 的节点插入返回 warning | OPT-001 | 无 |
| AA-OPT-006 | P2 | AA-TST-006 | MCP 空闲后执行桥接端到端并归档证据（用户验收环节） | REG-0005 changed=true 证据归档 | OPT-007 | 依赖用户环境 |
| AA-OPT-007 | P3 | AA-OPS-007/008 | recompile 片段 finally DestroyImmediate；SSE 解析收集全部 data 行取匹配响应 | 代码审查通过；现有测试不回归 | — | 无 |

## 3. 测试补强任务

| 任务 ID | 内容 | 验收 |
| --- | --- | --- |
| AA-TST-A | 新增 CRLF/空行 roundtrip 测试（含于 OPT-001/002 验收） | 全绿 |
| AA-TST-B | 新增 create rename 图内替换测试 | 全绿 |
| AA-TST-C | 新增原子写备份测试 | 全绿 |

## 4. 回滚策略

所有修复集中在 model/main/graph_ops/recompile/mcp_client；任一修复引入回归即整体 revert 该提交，roundtrip 全量测试为回归门禁。

## 5. 执行状态（2026-09-01 02:00 更新）

| 任务 | 状态 | 证据 |
| --- | --- | --- |
| AA-OPT-001 | ✅ 完成 | EOL 感知解析/序列化；`test_crlf_roundtrip_byte_identical` 等通过 |
| AA-OPT-002 | ✅ 完成 | 空行保序；`test_blank_line_roundtrip_preserved` 通过 |
| AA-OPT-003 | ✅ 完成 | create 图内改名；`test_create_renames_graph_data` 通过 |
| AA-OPT-004 | ✅ 完成 | atomic_write + .bak；`test_atomic_write_creates_backup` 通过 |
| AA-OPT-005 | ✅ 完成 | add-node hex 字段告警；`test_add_node_warns_on_hex_fields` 通过 |
| AA-OPT-006 | ⏳ 待用户验收 | 等 MCP 空闲后执行 `pytest -m bridge` |
| AA-OPT-007 | ✅ 完成 | DestroyImmediate + SSE 全帧收集 |

附加整改：main.py 超 LOC 警告拆分为 main/commands；跨模块导入收口到各包公开 `__init__`（fitness strict PASS）；29 测试全绿。

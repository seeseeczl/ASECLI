# REG-0041 真实 ASE 画布验收证据

- 环境：团结引擎 `2022.3.61t9`、ASE `1.9.6.2`
- 隔离工程：系统临时目录中的 `asecli-e2e-v2-gui.VW6VWe`，不作为可复现固定路径
- 样本：small、medium、complex-caster、complex-receiver
- 结论：2026-09-03 人工复核通过

## 自动与结构证据

- `layout-dry-run.jsonl` / `layout-write.jsonl`：四类样本均返回 `structural_validation=passed`、`visual_validation=pending`。CLI 故意不自行宣称视觉通过。
- `complex-receiver-live-*.json`：使用 ASE `TruePosition` 测量；三个 Comment 在 fit 前后均无 containment issue，写入只调整位置和尺寸。
- 语义 diff：small 为 7 nodes / 7 wires，仅节点 `raw_fields[3]`；medium 为 14 nodes / 3 wires，仅节点 `raw_fields[3]`；complex-caster 为 11 nodes / 1 wire，仅节点 `raw_fields[3]`；complex-receiver 为 28 nodes / 6 wires，13 个节点变化，仅普通位置字段及 Commentary 的位置/宽/高字段。
- 四类样本 wire 集合不变；编译正文不变，仅允许 CHKSM 更新。
- `original-project-sha256-before.txt` 与 `original-project-sha256-after-layout.txt` 完全一致，证明原工程两个 Shader 未被写入。

## 人工视觉验收

四张 `*-normal-zoom.jpg` 在正常缩放下确认：

- 数据流从左到右分阶段清晰；重复分支对齐。
- Comment 不重叠，完整包含成员并留有可读边距。
- 连线不穿过无关节点、端口或标题栏；空白通道中的线线交叉不判失败。
- 节点标题、端口和中文 Comment 在正常缩放下可读。

因此本记录把 CLI 保持的 `visual_validation=pending` 与仓库内人工签收分开：结构结果由 JSON 证明，视觉通过由本页和截图证明。

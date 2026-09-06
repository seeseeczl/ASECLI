# ASE 材质属性呈现规范

## 目标与硬契约

每个导出材质属性同时服务美术与技术人员。CLI 使用 `asecli.property-presentation.v2` 强制：

1. 公开属性使用简短、自然的中文 `display_name` / `inspector_name`。
2. 每个公开属性恰好有一条含中文的 `TooltipMzgui` 使用说明。
3. GUI 在 Tooltip 后自动追加真实英文变量名与 Shader 默认值。
4. Foldout 按实际语义选用；HelpBox 仅在用户明确提供内容时可选写入。

Tooltip 是工具默认生成和强制校验的属性说明渠道。HelpBox 不参与属性呈现合规判断，工具不会自动补写；用户可通过编辑窗口、`--help-box` 或 spec 的 `help` 字段添加自己的常驻内容。

## 中文显示名

- 显示名只回答“这是什么”，不要堆叠变量名、默认值、单位或长说明。
- AO、UV、HDR、法线等团队通用术语可以保留；其余使用自然中文。
- 同类属性保持一致词序，例如统一为“清漆强度”，不要混用“强度-清漆”“Coat Power”。
- 已发布 Shader 变量名属于 API；整理 Inspector 时优先只改显示名、顺序、Foldout 和 Tooltip。

新 Property 使用 EditorGraphSpec v2 的 `inspector_name`；已有 Property 使用完整 `custom-gui --spec` 的 `display_name`，由 CLI 同步图字段与编译 ShaderLab 标签。

## Tooltip：默认说明渠道

Tooltip 正文用一到两句说明真实用途，按属性类型覆盖必要信息：

- 开关：是否启用该层，以及关闭时的回退结果。
- 纹理：控制区域或数据来源；只写已证实的 RGB/A 通道语义与混合关系。
- 颜色：着色对象、是否与贴图相乘，以及 Alpha 是否参与效果。
- 滑条：控制对象、数值增大/减小时的可见结果；有明确物理语义时再写单位。

不要在正文重复变量名与默认值。ASECLI fallback 会动态追加：

```text
变量名：_PaintColor
默认值：(1, 1, 1, 1)
```

默认值来自默认 `Material(shader)`，不是当前材质实例值；Shader 默认值变化后无需维护第二份字符串。

单属性示例：

```bash
asecli custom-gui My.shader --editor MZGUI.MZGUI --property _PaintColor \
  --group "固有色" \
  --tooltip "控制车辆基础漆面颜色；Alpha 当前不参与透明度计算。" --write
```

默认整理只写 Tooltip，不自动创建 HelpBox。需要常驻内容时，用户可显式传入 `--help-box "内容"`；`--clear-help-box` 可单独清除它。

## Foldout 与排序

- 使用短中文功能名，例如“固有色层”“底漆层”“清漆层”“拉花层”“高级选项”。
- 每组只有第一个 PropertyNode 写 `FoldoutMzgui`；后续属性继承该组直到下一个标题。
- 顶层按美术调节和材质叠加顺序：基础外观、叠加表层、局部效果/贴图、发光/法线/AO、诊断与高级选项。
- 组内按真实依赖取子集排序：总开关 → 源输入/贴图 → 配色 → 混合/遮罩 → 表面响应 → 质量或性能项。
- 不要一个属性一个组，也不要使用“其他”“参数 1”等无语义标题。

## 变量命名

- Shader 变量名保持英文、`_` 前缀和 `PascalCase`，例如 `_FlakeTex`、`_FlakeColor`、`_FlakeBlend`。
- 开关在同一项目内统一 `_UseFeature` 或 `_FeatureEnabled`，不要混用。
- 不使用拼音、中文、序号或无语义后缀，例如 `_Tex1`、`_Value`、`_Param`、`_ColorNew`。

## 批量规范

`material-gui.json` 负责中文显示名、顺序、Foldout 和 Tooltip：

```json
{
  "editor": "MZGUI.MZGUI",
  "reorder": true,
  "properties": [
    {
      "name": "_PaintColor",
      "display_name": "车漆颜色",
      "group": "固有色",
      "tooltip": "控制车辆基础漆面颜色；Alpha 当前不参与透明度计算。"
    },
    {
      "name": "_CoatStrength",
      "display_name": "清漆强度",
      "group": "清漆层",
      "tooltip": "控制清漆反射强度；数值越大，高光与环境反射越明显。"
    }
  ]
}
```

默认不要加入 `help` 字段。用户明确需要常驻内容时可选加入 `help`，它会写为 `HelpBoxMzgui`。新规格仍必须写 `tooltip`；仅含旧 `help`、不含 `tooltip` 的旧 EditorGraphSpec v2 会把该值迁移为 Tooltip，不额外生成 HelpBox。

## GUI provider

开始前运行 `asecli gui-support <project-root>`。存在原生 `MZGUI.MZGUI` 时直接使用；确认缺失才以 `--write` 安装 fallback。目标资源冲突或 provider 不确定时停止，不覆盖工程文件。

fallback 的 ASE 编辑窗口提供 Foldout、Tooltip、HelpBox 的可视化编辑。HelpBox 默认关闭，只有用户启用并填写时才写入；已存在内容可继续编辑或清除。fallback 会以兼容 MZGUI 的轻量常驻说明样式渲染它。

需要由另一个数值属性控制控件是否可编辑时，使用 `enabled_if` 或 `--enabled-if`。它写入 ASE PropertyNode Custom Attributes 中的 `EnableIfMzgui(source,operator,value)`，不写 Shader `if`。条件不满足时只由 `EditorGUI.DisabledScope` 置灰，原值保留；控制属性缺失或多选材质并非全部满足时也置灰。可视化窗口提供控制属性、比较方式和比较值编辑，不要求用户手写 Attribute。原生 MZGUI 工程执行 `gui-support --write` 时只安装这个兼容 Drawer 与 authoring 扩展，不注入第二个 `MZGUI.MZGUI`。

## 验收

写入后做最小充分验证：

1. `asecli custom-gui <file>`：确认 `property_presentation.contract=asecli.property-presentation.v2`、`valid=true`、`violations=[]`。
2. 核对每个公开属性有中文显示名和中文 Tooltip；若用户添加了 HelpBox，再核对其内容及图/编译区同步。
3. `asecli validate <file>`：确认结构与 CHKSM 无错误。
4. 需要 ASE 正式生成 ShaderLab 声明时运行一次 `asecli recompile <file>`。
5. 只有本次修改触及 Inspector 交互或 C# Editor 资源时，才在一个 Editor 会话中集中检查 Tooltip 悬停与 Foldout；不以重复截图代替自动验证。

# ASE 材质属性呈现规范

## 目标

每个公开材质属性都应同时服务两类读者：美术人员能直接理解和调节，技术人员能快速确认 Shader 变量与默认状态。Inspector 中从上到下形成清晰的四层信息：语义分组、中文显示名、悬浮技术信息、属性下方帮助说明。

## 四层结构

### 1. 中文显示名

- 公开 Property 的 `display_name` / `inspector_name` 默认使用简短、自然、能直接说明用途的中文，例如“车漆颜色”“清漆强度”“法线贴图”。
- AO、UV、HDR、法线等团队已普遍使用的术语可以保留，但不要整项使用难读的英文句子。
- 显示名只承担“这是什么”的职责，不在主标签中堆叠变量名、默认值、单位和长说明。
- 同类属性使用一致词序和术语，例如统一使用“清漆强度”，不要在同一面板中混用“强度-清漆”“Coat Power”等表达。

创建新 Property 时，通过 EditorGraphSpec 的 `inspector_name` 写入中文显示名。整理已有 Property 时，先用 `asecli custom-gui <file>` 查询 `display_name`；需要修改时使用 ASE Editor 或经过该节点类型 schema 验证的固定字段，不得只改编译后的 ShaderLab `Properties` 文本，否则下次 ASE 重编译会被覆盖。

### 2. 悬浮提示

每个公开属性的 Tooltip 都必须包含真实变量名和 Shader 默认值，显示模板为：

```text
变量名：_PaintColor
默认值：(1, 1, 1, 1)
```

- 这两行由 ASECLI GUI 自动追加，不写进 `ASECLITooltip` 文本。ASECLI GUI 从默认 `Material(shader)` 读取 Shader 默认值，不读取当前材质实例值。
- 因为是显示时动态读取，Shader 默认值变化后无需人工同步一份字符串，也不会把旧默认值留在 ASE 节点尾部。
- `--tooltip` 仅用于可选的额外悬浮说明；用途、通道和调节结果仍优先放在 HelpBox，避免 Tooltip 过长。
- 开始前运行 `asecli gui-support <project-root>`。缺失时显式 `--write` 安装内置层，并使用唯一的 `ASECLI.MaterialGUI.ASECLIMaterialGUI`。若返回 `target_conflict`，停止写入并人工辨认固定资源 `Assets/Editor/ASECLI/ASECLIMaterialGUI.cs`，不得覆盖。

`custom-gui` 示例：

```bash
asecli custom-gui My.shader --editor ASECLI.MaterialGUI.ASECLIMaterialGUI --property _PaintColor \
  --tooltip "车身基础漆色。" \
  --help-box "控制车辆基础漆面颜色。Alpha 当前不参与透明度计算。" --write
```

### 3. 属性下方帮助说明

- 每个需要解释的公开属性使用 `ASECLIHelpBox` 在控件下方提供常驻中文说明。
- 说明优先回答：控制什么；数值调大/调小时发生什么；贴图各通道表达什么；必要的单位、范围、依赖或性能影响。
- 颜色、贴图、开关等不适合“调大/调小”的类型，改写为对选择结果、通道或启用条件的说明。
- 一到两句即可，不复述中文显示名，也不重复 Tooltip 中的变量名和默认值。
- 无法从节点图、HLSL 或项目语义确认因果时，只写已证实用途或暂不写，禁止编造效果。

### 4. 语义分组

- 使用中文 Foldout 标题按功能组织属性，例如：固有色、阴影层、底漆层、清漆层、环境层、AO 层、法线层、珠光层、伪装层。
- 排序优先满足实际调节流程：常用基础项在前，细节与高级项在后，诊断/调试项最后。
- 每组只有第一个 PropertyNode 写 `ASECLIFoldout`；后续属性继承该组，直到下一个分组标题。
- 避免一个属性一个组，也不要用“其他”“参数 1”这类无语义标题。确实只有一个独立功能时可以单项成组。

## 批量规范示例

`material-gui.json` 负责顺序、分组、可选 Tooltip 和 HelpBox；当前不负责修改 PropertyNode 的中文显示名或真实默认值。变量名与默认值由 GUI 自动显示，不应在 JSON 中重复：

```json
{
  "editor": "ASECLI.MaterialGUI.ASECLIMaterialGUI",
  "reorder": true,
  "properties": [
    {
      "name": "_PaintColor",
      "group": "固有色",
      "tooltip": "车身基础漆色。",
      "help": "控制车辆基础漆面颜色。Alpha 当前不参与透明度计算。"
    },
    {
      "name": "_CoatStrength",
      "group": "清漆层",
      "help": "控制清漆反射强度；数值越大，表面高光与环境反射越明显。"
    }
  ]
}
```

## 验收

写入后执行：

1. `asecli gui-support <project-root>`：确认 `provider`、`recommended_editor` 与 Shader 的 `CustomEditor` 一致；内置层安装后等待 Editor 脚本重编译。
2. `asecli custom-gui <file>`：确认每个公开属性的 `display_name`、`property_name`、顺序及三类 ASECLI 属性正确；旧三标记只作为兼容读取信息。
3. `asecli validate <file>`：确认图结构、属性和 CHKSM 无错误。
4. `asecli recompile <file>`：让 ASE 正式生成 ShaderLab 属性声明。
5. 在真实材质 Inspector 中检查：中文显示名可读；悬浮时同时看到准确变量名与默认值；帮助说明显示在对应控件下方；Foldout 分组与排序符合调节流程。

纯文本回归可以证明字段和编码正确，但不能证明 Tooltip 触发、HelpBox 可读性、控件布局或折叠交互已经在目标 Unity/Tuanjie 版本正常显示。

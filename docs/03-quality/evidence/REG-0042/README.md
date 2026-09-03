# REG-0042 Material Inspector UI 矩阵

- 环境：团结引擎 `2022.3.61t9`、ASE `1.9.6.2`、macOS Retina `pixelsPerPoint=2`
- 隔离工程：系统临时目录中的 `asecli-e2e-v2-gui.VW6VWe`
- 资源：Color / Float / Range / Texture / Toggle、中文显示名与常驻中文说明、Foldout、两份 Material
- 结论：2026-09-03 真实 Editor 编译 `0 error / 0 warning`，矩阵人工复核通过；主题最终恢复 `isProSkin=True`、`UserSkin=-1`

## 失败优先修复

1. 480px 与 300px 宽度下，超长中文属性名原先单行截断。`DrawProperty` 现在检测可用宽度，长标签使用自动换行，字段移到下一行全宽显示。
2. Tooltip 默认值原先出现 `0.800000012`、`0.649999976` 浮点噪声。现在统一用最多六位小数，实机反射结果为 `_BaseColor=(0.8, 0.2, 0.1, 1)`、`_Smoothness=0.65`、`_Intensity=1.25`。

两项回归测试均先失败后通过；`tests/test_gui_support.py` 定向组合共 `62 passed`。

## 截图矩阵

| 证据 | 覆盖状态 | 结果 |
| --- | --- | --- |
| `dark-480-top.jpg` / `dark-480-bottom.jpg` | 深色、480px、完整属性集 | 无裁切或遮挡 |
| `dark-narrow-top.jpg` / `dark-narrow-bottom.jpg` | 深色、300px、长中文与滚动 | 标签换行，字段和说明不重叠 |
| `light-narrow-top.jpg` / `light-narrow-bottom.jpg` | 浅色、300px | 文本、强调线和控件可辨 |
| `foldout-collapsed.jpg` | Foldout 收起 | 标题可达，组内容正确隐藏 |
| `mixed-value.jpg` | 多选 mixed-value | 三类数值字段显示 mixed 状态 |
| `disabled.jpg` | disabled | 控件与说明同步禁用且仍可辨 |
| `focus-float.jpg` / `focus-tab.jpg` | 鼠标聚焦与 Tab 导航 | 数值字段获得明确焦点框 |

Tooltip 气泡此前已由用户在同版本团结环境现场确认；本轮未重复保存悬浮截图。本轮真实 Editor 反射再次确认英文变量名和默认值生成正确，不能把反射证据冒充气泡截图。

## 安装升级边界

若目标工程已安装内容不同的旧版 `ASECLIMaterialGUI.cs`，当前 `gui-support --write` 会按安全契约返回 `target_conflict`，不会覆盖。自动升级旧版资源需要另行设计“已知旧版本哈希 + 原子备份/替换”协议，本次不扩大公共写入权限。

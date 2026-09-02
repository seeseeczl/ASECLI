# ASECLI test plan

## Current refinement: ASECLI material GUI protocol

Planned coverage before implementation:

- `tests/test_gui_support.py`: 唯一 ASECLI GUI 的 dry-run、幂等安装、冲突/符号链接/
  竞争写入拒绝、已有原生 MZGUI 文件不阻断、打包 C# 契约、`asecli.inline-help.v1`
  呈现契约报告/写前拒绝和 CLI JSON 行为。
- `tests/test_custom_gui.py`: 只生成 `ASECLIFoldout`、`ASECLITooltip`、
  `ASECLIHelpBox`；旧三标记可读取，并在同语义写入或清理时迁移。Property
  尾部按图版本探测，未知布局失败关闭而非猜测字段下标。
- `tests/test_cli_contract.py`: `gui-support` participates in the stable one-line
  JSON error contract.
- `tests/test_property_presentation.py`: `asecli.property-presentation.v1` 的逐属性
  报告、中文显示名/中文说明原子治理，以及删除说明或清空 Editor 的写前拒绝。
- `tests/test_editor_create_spec.py` / `tests/test_editor_create_cli.py`: 正式创建只接受
  每个 Property/Sampler 都提供中文 `inspector_name/help` 的 EditorGraphSpec v2；文本
  create 对不合规模板/donor 组合零写盘。

The Python suite can verify installation safety, packaged source text, metadata
contracts, and serialization. Compilation and visual behavior of the generated C#
resource require a real Unity/Tuanjie Editor gate and are reported separately.

## Current real Editor result — 2026-09-02 (CR-0010)

- 隔离团结 `2022.3.61t9`：`ASECLI_GUI_TEST_PROJECT=<带 .asecli-gui-e2e-isolated 标记的临时工程> ASECLI_TUANJIE_PATH=<Tuanjie.app/Contents/MacOS/Tuanjie> uv run --frozen pytest -q -m bridge tests/test_material_gui_e2e.py` 为 `1 passed in 10.23s`。
- 当前修复后的双构建 wheel SHA-256 均为 `a1e3b94cbb164d7cd9da4903bbf75ceb25083f2f718b32d69b7f5df6c7ea887f`；打包 C# 资源与当前实例安装资源 SHA-256 均为 `97b5785812138b604898007998d6067e846e5e287e3f674940bfec37320c3109`。
- BatchMode 验证当前资源无 C# 或 Shader 编译错误；新三标记和旧三标记均实例化 decorator、读取分组/Tooltip/HelpBox，`Material(shader)` 默认 `_Value=1.25`。当前团结 `2022.3.61t9` 运行实例还验证了无 `GetShaderPropertyAttributes` 时与原生同名旧 drawer 的冲突修复，以及新/旧分组的标题点击展开/收起和 HelpBox 可见性。本记录不使用 Unity 2021 作为 CR-0010 证据。
- 定向自动回归：`uv run pytest tests/test_gui_support.py tests/test_custom_gui.py tests/test_cli_contract.py tests/test_material_gui_e2e.py -q` 为 `67 passed, 1 skipped`。
- 修复后的全量回归：Python 3.10 与 Python 3.12 均为 `203 passed, 3 skipped`；REG catalog 校验与 `git diff --check` 通过。
- Tooltip 视觉验收：用户提供的当前团结实例实机截图显示真实悬停浮层，内容为 `变量名：_BaseColor` 与 `默认值：RGBA(1.000, 1.000, 1.000, 1.000)`；该浮层来自 Inspector 实际渲染，不以元数据读取或 C# 拼接路径替代。
- BUG-0015 / REG-0036：旧实现的原生 Info HelpBox 与参考轻量说明条不一致；新增的契约报告和失效资源拒绝用例先失败 2 项，修复后通过。当前团结实例确认 Receiver 说明条无图标/原生外框，使用弱背景、左侧强调线、小号弱化斜体并自动换行；Console 0 error。最终本地全量为 `208 passed, 3 skipped`，REG catalog、CI governance、供应链与 diff 检查通过；Project Architect strict 与 `HEAD` 同样复现 29 项既有追溯/fitness 历史问题，本次未新增。
- CR-0012 / REG-0037：新增契约用例先失败 5 项；实现后 `custom-gui` 可报告/修复属性呈现，删除说明、移除 ASECLI Editor 或通用字段修改无法绕过，文本 create 拒绝不合规结果，Editor CLI 要求 v2 并在提交后同步/复验。全量 `216 passed, 3 skipped`，REG catalog 33 条、CI governance、供应链与 diff 通过；Caster 1 个属性、Receiver 6 个属性只读检查零违规。真实 Tooltip/说明条沿用当前团结既有证据，v2 真实 Editor 创建仍待独立验收；Project Architect strict 与 `HEAD` 同为 31 项历史问题。

## Historical results — 2026-09-01 (pre-CR-0010 protocol)

- Focused GUI/CLI contract: `62 passed in 3.83s`.
- Full repository suite: `189 passed, 2 skipped in 10.69s`; the skipped tests are
  environment-gated bridge cases, not GUI-support failures.
- Skill validation: passed with the bundled `quick_validate.py`.
- REG catalog: 26 documented pytest commands collected successfully.
- CI governance: passed with no findings.
- Packaging: wheel contains `gui_support.py` and
  `asecli_material_gui.cs.txt`; packaged/resource SHA-256 both equal
  `827ed7b91df1761a62eac6780066d162a73fd22e005bf64c5d9516b864841879`;
  the wheel installed into an isolated Python 3.12 environment and its real
  `asecli gui-support` entry point detected the installed resource successfully.
- Real Editor gate: this is a pre-CR-0010 historical Unity `2021.3.7f1c1` record.
  It is retained for provenance only and is not used as current acceptance evidence;
  current GUI verification is the isolated Tuanjie result above.

Open gap: BatchMode did not exercise mouse-hover, foldout clicking, or the final
Inspector appearance. Those remain target-project UI acceptance checks.

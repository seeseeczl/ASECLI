# REG-0044 — C# 资源确定性拼装

- 环境：macOS arm64，Python 3.12，uv frozen。
- GUI 片段：300/283 行；拼装 SHA-256 `9541c541628b8404c66ca2c36e80af25f69960d6e1a07deabad53fd6233c5b7a`。
- Editor executor 片段：205/205 行；拼装 SHA-256 `52fce4c5596ac0cb0bdaae388c2bc2e68d8e2ad4d0d39e00b196856c4b216cc4`。
- `EDITOR_CREATE_SNIPPET` 保持一个 `{payload_base64}`、一个 `catch (System.Exception ex)` 和一个 `finally`；运行时仍提交单一 execute_code payload。
- `python3 tools/check_ci_governance.py`：0 finding；`.project-architect.json` 的 `loc_exemptions` 为空。
- 自动命令：`uv run --frozen pytest -q tests/test_gui_support.py tests/test_gui_upgrade.py tests/test_editor_create_bridge.py`，结果 `35 passed`。
- 真实团结证据由 REG-0045 单独记录，不以静态 hash 代替编译/运行。

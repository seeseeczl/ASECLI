# ASECLI test plan

## Current refinement: built-in material GUI compatibility

Planned coverage before implementation:

- `tests/test_gui_support.py`: GUI provider detection, dry-run, idempotent install,
  conflict refusal, native MZGUI preference, native/built-in duplicate-provider
  fail-closed behavior, packaged C# capability contract, and CLI JSON behavior.
- `tests/test_custom_gui.py`: both native `MZGUI.MZGUI` and the built-in
  `ASECLI.MaterialGUI.ASECLIMaterialGUI` are accepted for Foldout, Tooltip, and
  HelpBox metadata; Property tails are capability-probed across graph-version
  values and unknown layouts fail closed instead of using a guessed field index.
- `tests/test_cli_contract.py`: `gui-support` participates in the stable one-line
  JSON error contract.

The Python suite can verify installation safety, packaged source text, metadata
contracts, and serialization. Compilation and visual behavior of the generated C#
resource require a real Unity/Tuanjie Editor gate and are reported separately.

## Results — 2026-09-01

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
- Real Editor gate: Unity `2021.3.7f1c1` compiled the installed C# resource and a
  verifier read `FoldoutMzgui`, `TooltipMzgui`, `HelpBoxMzgui`, plus the Shader
  default `_Value=1.25` from a default Material. This compile also covers the
  dependency-hash cache invalidation path and reflective Int-property fallback;
  the verifier does not yet mutate a Shader default or exercise an Int property.

Open gap: BatchMode did not exercise mouse-hover, foldout clicking, or the final
Inspector appearance. Those remain target-project UI acceptance checks.

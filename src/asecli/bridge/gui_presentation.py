"""Executable presentation contracts for the built-in material GUI."""

from __future__ import annotations


INLINE_HELP_PRESENTATION_CONTRACT = {
    "contract": "asecli.inline-help.v1",
    "icon": "none",
    "border": "none",
    "background_rgba": [0.0, 0.0, 0.0, 0.1],
    "accent": {"edge": "left", "width": 3.0, "rgba": [1.0, 1.0, 1.0, 0.3]},
    "typography": {
        "base": "EditorStyles.miniLabel",
        "font_style": "italic",
        "dark_skin_alpha": 0.4,
        "light_skin_alpha": 0.55,
    },
    "layout": {"text_inset": [16.0, 4.0], "word_wrap": True},
}

_REQUIRED_SOURCE_MARKERS = {
    "inline_renderer": "DrawInlineHelp(metadata.Help)",
    "mini_typography": "new GUIStyle(EditorStyles.miniLabel)",
    "italic_typography": "style.fontStyle = FontStyle.Italic",
    "word_wrap": "style.wordWrap = true",
    "subtle_background": (
        "EditorGUI.DrawRect(backgroundRect, new Color(0f, 0f, 0f, 0.1f))"
    ),
    "left_accent_color": (
        "EditorGUI.DrawRect(accentRect, new Color(1f, 1f, 1f, 0.3f))"
    ),
    "left_accent_geometry": "backgroundRect.x + 6f,\n                backgroundRect.y + 6f,\n                3f,",
    "text_inset": "row.x + 16f,\n                row.y + 4f,",
    "dark_skin_text": "new Color(1f, 1f, 1f, 0.4f)",
    "light_skin_text": "new Color(0f, 0f, 0f, 0.55f)",
}
_FORBIDDEN_SOURCE_MARKERS = {
    "native_layout_help_box": "EditorGUILayout.HelpBox(",
    "native_gui_help_box": "EditorGUI.HelpBox(",
}


def inspect_inline_help_presentation(source: str) -> dict:
    """Report whether the packaged C# source satisfies the public style contract."""
    violations = [
        f"missing:{name}"
        for name, marker in _REQUIRED_SOURCE_MARKERS.items()
        if marker not in source
    ]
    violations.extend(
        f"forbidden:{name}"
        for name, marker in _FORBIDDEN_SOURCE_MARKERS.items()
        if marker in source
    )
    return {
        **INLINE_HELP_PRESENTATION_CONTRACT,
        "valid": not violations,
        "violations": violations,
    }


def require_inline_help_presentation(source: str) -> None:
    """Fail closed before installation when the packaged style has regressed."""
    result = inspect_inline_help_presentation(source)
    if result["valid"]:
        return
    raise RuntimeError(
        "packaged ASECLI GUI violates inline-help presentation contract: "
        + ", ".join(result["violations"])
    )

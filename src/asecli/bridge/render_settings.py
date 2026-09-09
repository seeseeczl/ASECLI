"""受限 URP Unlit 模板设置；值必须由 ASE 模板选项实际承接。"""

from .editor_spec import SpecError

OPTIONS = {
    "surface": ("Opaque", "Transparent"),
    "blend": ("Alpha", "Premultiply", "Additive", "Multiply"),
    "two_sided": ("On", "Cull Back", "Cull Front"),
    "vertex_position": ("Absolute", "Relative"),
    "cast_shadows": (False, True),
    "receive_shadows": (False, True),
    "fog": (False, True),
    "lod_crossfade": (False, True),
}


def validate_settings(value, guid):
    if guid != "2992e84f91cbeb14eab234972e07ea9d":
        raise SpecError("render settings require the verified URP Unlit template")
    if not isinstance(value, dict) or not value or set(value) - set(OPTIONS):
        raise SpecError("invalid or unknown template render settings")
    for key, item in value.items():
        allowed = OPTIONS[key]
        if type(item) is not type(allowed[0]) or item not in allowed:
            raise SpecError(f"invalid render setting {key}: {item!r}")
    return dict(value)

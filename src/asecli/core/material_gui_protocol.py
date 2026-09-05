"""Shared MZGUI metadata protocol and legacy migration aliases."""

PROPERTY_METADATA_ATTRIBUTE_TYPES = ("FoldoutMzgui", "TooltipMzgui", "HelpBoxMzgui")
LEGACY_PROPERTY_METADATA_ATTRIBUTE_TYPES = (
    "ASECLIFoldout",
    "ASECLITooltip",
    "ASECLIHelpBox",
)
_LEGACY_BY_CANONICAL = dict(
    zip(PROPERTY_METADATA_ATTRIBUTE_TYPES, LEGACY_PROPERTY_METADATA_ATTRIBUTE_TYPES)
)
_CANONICAL_BY_ATTRIBUTE = {
    **{name: name for name in PROPERTY_METADATA_ATTRIBUTE_TYPES},
    **{legacy: canonical for canonical, legacy in _LEGACY_BY_CANONICAL.items()},
}
MANAGED_PROPERTY_METADATA_ATTRIBUTE_TYPES = frozenset(_CANONICAL_BY_ATTRIBUTE)


def canonical_property_metadata_type(type_name: str) -> str | None:
    """Return the public MZGUI type for a public or historical ASECLI type."""
    return _CANONICAL_BY_ATTRIBUTE.get(type_name)


def equivalent_property_metadata_types(type_name: str) -> frozenset[str]:
    """Return the MZGUI type and its one legacy ASECLI alias."""
    canonical = canonical_property_metadata_type(type_name)
    if canonical is None:
        return frozenset()
    return frozenset((canonical, _LEGACY_BY_CANONICAL[canonical]))

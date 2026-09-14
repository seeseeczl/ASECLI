"""Public reports must expose actionable surface-semantic failures."""

from pathlib import Path

import pytest

from asecli.sg_export.conversion_report import assert_spec_publishable, build_public_report


def test_alpha_blend_failure_is_not_hidden_by_generic_export_failure(tmp_path: Path):
    source = tmp_path / "source.shader"
    source.write_text("Shader {}", encoding="utf-8")
    internal = {
        "verification": {
            "source_parse": {"status": "passed"},
            "semantic_mapping": {"status": "blocked"},
        },
        "diagnostics": [{
            "code": "ALPHA_BLEND_UNREPRESENTABLE",
            "reason": {"source": ["One", "Zero"], "target": ["Zero", "One"]},
        }],
    }

    report = build_public_report(
        source,
        tmp_path / "target.spec.json",
        None,
        internal,
        failure="ASE graph contains unsupported semantics",
    )

    assert "ALPHA_BLEND_UNREPRESENTABLE" in report["checks"]["alpha_equation"]["evidence"]
    assert "ALPHA_BLEND_UNREPRESENTABLE" in report["checks"]["blend_equation"]["evidence"]


def test_missing_transparent_pass_blend_cannot_be_published(tmp_path: Path):
    source = tmp_path / "source.shader"
    source.write_text("Shader {}", encoding="utf-8")
    internal = {
        "target_mapping": {"surface": "Transparent", "blend": "Multiply"},
        "surface_semantics": {
            "source_pass_blend": None,
            "target_pass_blend": {"rgb": ["DstColor", "Zero"], "alpha": ["Zero", "One"]},
            "pass_blend_parser": {"status": "missing", "candidate_count": 0},
            "rewrites": [],
        },
        "verification": {
            "source_parse": {"status": "passed"},
            "semantic_mapping": {"status": "passed"},
        },
        "dependencies": [],
        "mappings": [{"kind": "certified_template_pass_set"}],
        "output_bindings": [{"block": "SurfaceDescription.Alpha"}],
        "diagnostics": [],
    }

    report = build_public_report(
        source,
        tmp_path / "target.spec.json",
        {"schema": "sgcli.native.v3"},
        internal,
        producer_schema_validated="passed",
    )

    assert report["checks"]["alpha_equation"]["status"] == "unknown"
    assert report["checks"]["blend_equation"]["status"] == "unknown"
    evidence = report["checks"]["blend_equation"]["evidence"]
    assert "pass_parser=missing candidates=0" in evidence
    assert "source=None" in evidence
    assert "target={'rgb': ['DstColor', 'Zero'], 'alpha': ['Zero', 'One']}" in evidence
    assert "alpha_modulate=matcher-v4/not_detected" in evidence
    with pytest.raises(ValueError, match="alpha_equation, blend_equation"):
        assert_spec_publishable(report)

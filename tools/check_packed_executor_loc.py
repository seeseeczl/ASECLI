"""LOC governance for packaged Unity C# executor fragments."""

from __future__ import annotations

from datetime import date
from pathlib import Path


def _packed_executor_loc_findings(
    root: Path,
    source_warning: int,
    source_limit: int,
    exemptions: dict[str, dict],
    warning_baselines: dict[str, int],
) -> list[str]:
    findings: list[str] = []
    seen: set[str] = set()
    for path in sorted((root / "src/asecli").rglob("*.cs.txt")):
        relative = path.relative_to(root).as_posix()
        seen.add(relative)
        loc = len(path.read_text(encoding="utf-8").splitlines())
        exemption = exemptions.get(relative)
        if loc > source_limit and exemption is None:
            findings.append(
                f"{relative} has {loc} lines (source limit {source_limit}) and is not listed in loc_exemptions"
            )
        elif exemption is not None:
            findings.extend(_loc_exemption_governance_findings(relative, exemption))
        if source_warning < loc <= source_limit:
            baseline = warning_baselines.get(relative)
            if not isinstance(baseline, int) or baseline <= source_warning:
                findings.append(
                    f"{relative} has {loc} lines (source warning {source_warning}) and has no valid growth baseline"
                )
            elif loc > baseline:
                findings.append(
                    f"{relative} grew from warning baseline {baseline} to {loc} lines"
                )
    for relative, exemption in exemptions.items():
        target = root / relative
        if not target.is_file():
            findings.append(f"loc exemption missing file: {relative}")
        elif relative not in seen:
            findings.extend(_loc_exemption_governance_findings(relative, exemption))
    for relative in warning_baselines:
        target = root / relative
        if not target.is_file():
            findings.append(f"packed executor warning baseline missing file: {relative}")
            continue
        loc = len(target.read_text(encoding="utf-8").splitlines())
        if loc <= source_warning:
            findings.append(
                f"{relative} is now at {loc} lines; remove its obsolete warning baseline"
            )
    return findings


def _loc_exemption_governance_findings(
    relative: str, exemption: dict, *, today: date | None = None
) -> list[str]:
    findings: list[str] = []
    required_text = (
        "id", "path", "rule", "reason", "risk", "owner", "approved_by",
        "created_at", "expires_at", "exit_condition",
    )
    for field in required_text:
        if not isinstance(exemption.get(field), str) or not exemption[field].strip():
            findings.append(f"{relative} loc exemption is missing {field}")
    controls = exemption.get("compensating_controls")
    if not isinstance(controls, list) or not controls or any(
        not isinstance(item, str) or not item.strip() for item in controls
    ):
        findings.append(f"{relative} loc exemption has invalid compensating_controls")
    try:
        created = date.fromisoformat(str(exemption.get("created_at", "")))
        expires = date.fromisoformat(str(exemption.get("expires_at", "")))
    except ValueError:
        findings.append(f"{relative} loc exemption has invalid governance dates")
        return findings
    if expires < created or (expires - created).days > 30:
        findings.append(f"{relative} loc exemption exceeds the 30-day maximum")
    if expires < (today or date.today()):
        findings.append(f"{relative} loc exemption expired on {expires.isoformat()}")
    return findings

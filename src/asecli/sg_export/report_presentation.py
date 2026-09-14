"""Map non-rendering Inspector differences into public evidence gaps."""

import json


def presentation_degradations(items, source, target):
    result = []
    for item in items:
        location = item.get("source") or {}
        if isinstance(location, dict):
            location = str(location.get("file") or source) + (
                "#" + str(location["property"]) if "property" in location else ""
            )
        result.append({
            "rule": "SEM-PRESENTATION-001", "category": "evidence_gap",
            "source": str(location or source), "target": str(target),
            "reason": str(item.get("code", "PRESENTATION_NOT_MIGRATED")) + ": "
                      + str(item.get("impact", "Inspector presentation is not migrated"))
                      + "; details=" + json.dumps(item.get("details", []), ensure_ascii=False),
        })
    return result

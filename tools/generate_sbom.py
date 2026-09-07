#!/usr/bin/env python3
"""Generate a deterministic SPDX 2.3 JSON SBOM without extra dependencies."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path


PACKAGE_RE = re.compile(r'\[\[package\]\]\s+name = "([^"]+)"\s+version = "([^"]+)"', re.MULTILINE)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]

    locked = PACKAGE_RE.findall((root / "uv.lock").read_text(encoding="utf-8"))
    project_versions = [version for name, version in locked if name == "asecli"]
    if len(project_versions) != 1:
        raise SystemExit("uv.lock must contain exactly one asecli package version")
    project_version = project_versions[0]
    artifacts = sorted(path for path in args.dist.iterdir() if path.is_file() and path != args.output)
    digest_seed = "".join(f"{path.name}:{sha256(path)}" for path in artifacts).encode()
    namespace_id = hashlib.sha256(digest_seed).hexdigest()[:16]
    epoch = int(os.environ.get("SOURCE_DATE_EPOCH", "0"))
    created = datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    packages = [{
        "SPDXID": "SPDXRef-Package-asecli",
        "name": "asecli",
        "versionInfo": project_version,
        "downloadLocation": "NOASSERTION",
        "filesAnalyzed": False,
        "licenseConcluded": "MIT",
        "licenseDeclared": "MIT",
        "copyrightText": "Copyright (c) 2026 AseCLI contributors",
    }]
    for name, version in locked:
        if name == "asecli":
            continue
        packages.append({
            "SPDXID": f"SPDXRef-Package-{re.sub('[^A-Za-z0-9.-]', '-', name)}",
            "name": name,
            "versionInfo": version,
            "downloadLocation": f"https://pypi.org/project/{name}/{version}/",
            "filesAnalyzed": False,
            "licenseConcluded": "NOASSERTION",
            "licenseDeclared": "NOASSERTION",
            "copyrightText": "NOASSERTION",
            "externalRefs": [{
                "referenceCategory": "PACKAGE-MANAGER",
                "referenceType": "purl",
                "referenceLocator": f"pkg:pypi/{name}@{version}",
            }],
        })

    document = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"asecli-{project_version}",
        "documentNamespace": f"https://spdx.org/spdxdocs/asecli-{project_version}-{namespace_id}",
        "creationInfo": {"created": created, "creators": ["Tool: asecli-generate-sbom"]},
        "packages": packages,
        "relationships": [{
            "spdxElementId": "SPDXRef-DOCUMENT",
            "relationshipType": "DESCRIBES",
            "relatedSpdxElement": "SPDXRef-Package-asecli",
        }],
        "annotations": [{
            "annotationDate": created,
            "annotationType": "OTHER",
            "annotator": "Tool: asecli-generate-sbom",
            "comment": "Artifacts: " + ", ".join(f"{p.name}=sha256:{sha256(p)}" for p in artifacts),
        }],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "packages": len(packages), "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

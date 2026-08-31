"""Build schemas.json from the runtime dump produced by SchemaExtractor (TASK-0005).

The serialized node line layout is:
  Node;<type>;<id>;<x,y>;<precision>;<showPreview>
  <inputCount> <per input port: id;type;internalData;isEditable(;name if editable)>
  <node-specific extras (opaque, passthrough)>
  <outputCount> <per output port: type;id>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

FIXED_PREFIX = ["Node", "<type>", "<id>", "<pos>", "<precision>", "<preview>"]


def split_line(serialized: str) -> list[str]:
    return serialized.split(";")


def parse_dump(dump_path: Path) -> dict:
    data = json.loads(dump_path.read_text(encoding="utf-8"))
    schemas: dict[str, dict] = {}
    for entry in data["types"]:
        if "error" in entry:
            schemas[entry["type"]] = {"source": "unavailable", "error": entry["error"]}
            continue
        fields = split_line(entry["serialized"])
        # sanity: Node;type;id;pos;precision;preview
        if len(fields) < 7 or fields[0] != "Node":
            schemas[entry["type"]] = {"source": "unavailable", "error": "unexpected layout"}
            continue
        tail = fields[6:]
        try:
            in_count = int(tail[0])
            idx = 1
            input_region = []
            for _ in range(in_count):
                rec_start = idx
                port_id = int(tail[idx])
                dtype = tail[idx + 1]
                idx += 3  # id, type, internalData
                editable = tail[idx]
                idx += 1
                if editable in ("True", "1"):
                    idx += 1  # name
                input_region.append({"start": rec_start, "port_id": port_id, "type": dtype})
            # output region: scan from end for "<count>;<type>;<id>" triples
            out_ports = []
            p = len(tail)
            found_out_count = None
            while p >= 1:
                count = tail[p - 1]
                if not count.isdigit() or p - 1 - 3 * int(count) < 0:
                    break
                block = 3 * int(count)
                triple = tail[p - block : p]
                if not all(triple[i + 2].isdigit() for i in range(0, block, 3)):
                    break
                found_out_count = int(count)
                for i in range(0, block, 3):
                    out_ports.append({"type": triple[i], "port_id": int(triple[i + 2])})
                p = p - 1 - block
            if found_out_count is None:
                raise ValueError("no output region")
            schemas[entry["type"]] = {
                "source": "runtime",
                "ase_version": data["ase_version"],
                "name": entry.get("name", ""),
                "category": entry.get("category", ""),
                "description": entry.get("description", ""),
                "fixed_prefix_len": 6,
                "fields": tail,
                "layout_ok": True,
                "input_region": {"start": 0, "end": idx, "ports": input_region},
                "extras_region": {"start": idx, "end": p - 1},
                "output_ports": list(reversed(out_ports)),
            }
        except (ValueError, IndexError):
            # Overridden serialization layout (e.g. master nodes): keep verbatim, opaque
            schemas[entry["type"]] = {
                "source": "runtime",
                "ase_version": data["ase_version"],
                "name": entry.get("name", ""),
                "category": entry.get("category", ""),
                "description": entry.get("description", ""),
                "fixed_prefix_len": 6,
                "fields": tail,
                "layout_ok": False,
                "input_ports": entry.get("input_ports", []),
                "output_ports": entry.get("output_ports", []),
            }
    return schemas


def main() -> int:
    dump = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/private/tmp/ase-schema-dump.json")
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("src/asecli/schema/data/schemas.json")
    schemas = parse_dump(dump)
    observed_path = Path("src/asecli/schema/data/observed.json")
    if observed_path.exists():
        observed = json.loads(observed_path.read_text(encoding="utf-8"))
        for type_name, entry in observed.items():
            samples = entry["samples"]
            schemas[type_name] = {
                "source": "observed",
                "fields_count": len(samples[0].split(";")) - 6,
                "samples": samples,
                "note": "layout opaque; serialized per-pass variants; mutate via dedicated ops or full-line replace",
            }
    payload = {
        "format": "asecli-schema/1",
        "extracted_from": str(dump),
        "types": schemas,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    runtime = sum(1 for v in schemas.values() if v.get("source") == "runtime")
    observed = sum(1 for v in schemas.values() if v.get("source") == "observed")
    unavailable = sum(1 for v in schemas.values() if v.get("source") == "unavailable")
    print(f"schemas: {runtime} runtime, {observed} observed, {unavailable} unavailable -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

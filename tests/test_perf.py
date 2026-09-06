"""REG-0011 (NFR-0003): 1000+ extra nodes, correct full pipeline under 1s."""

import time
from pathlib import Path
from types import SimpleNamespace

from asecli.core import AseFile, apply_meticulous_layout, audit_meticulous_layout, meticulous_layout_positions
from asecli.core.layout import tidy


def test_big_graph_pipeline_under_one_second():
    base = (Path(__file__).parent / "fixtures" / "step-antialiasing.function.txt").read_text(encoding="utf-8")
    f = AseFile.from_text(base)
    extra = "\n".join(
        f"Node;AmplifyShaderEditor.SaturateNode;{i};0,0;Inherit;False;1;0;FLOAT;0;False;1;FLOAT;0"
        for i in range(1000, 2000)
    )
    big = f.serialize().replace("ASEEND*/", extra + "\nASEEND*/")

    elapsed_runs = []
    for _ in range(5):
        start = time.perf_counter()
        f2 = AseFile.from_text(big)
        tidy(f2.graph)
        out = f2.serialize()
        reparsed = AseFile.from_text(out)
        elapsed_runs.append(time.perf_counter() - start)

        assert len(f2.graph.nodes) == 1007
        assert f2.graph.nodes[-1].node_id == "1999"
        assert reparsed.serialize() == out
        assert len(reparsed.graph.nodes) == 1007
        assert reparsed.graph.node_by_id("1999") is not None

    elapsed_runs.sort()
    median = elapsed_runs[len(elapsed_runs) // 2]
    assert max(elapsed_runs) < 1.0, f"pipeline max={max(elapsed_runs):.2f}s median={median:.2f}s"


def test_meticulous_geometry_and_audit_avoid_quadratic_path_intersection_cost():
    count = 300
    nodes = "\n".join(
        [f"Node;Input;{index};0,0" for index in range(1, count + 1)]
        + ["Node;AmplifyShaderEditor.TemplateMultiPassMasterNode;9999;0,0"]
    )
    wires = "\n".join(
        f"WireConnection;9999;{index - 1};{index};0" for index in range(1, count + 1)
    )
    graph = AseFile.from_text(
        f"/*ASEBEGIN\nVersion=19602\n{nodes}\n{wires}\nASEEND*/\n"
    ).graph
    geometry = {
        str(index): SimpleNamespace(
            width=180.0, height=100.0, title_height=24.0,
            input_ports={}, output_ports={"0": (180.0, 50.0)},
        )
        for index in range(1, count + 1)
    }
    geometry["9999"] = SimpleNamespace(
        width=220.0, height=3640.0, title_height=24.0,
        input_ports={str(index): (0.0, 26.0 + 12.0 * index) for index in range(count)},
        output_ports={},
    )

    started = time.perf_counter()
    plan = meticulous_layout_positions(graph, geometry)
    moved = apply_meticulous_layout(graph, plan)
    report = audit_meticulous_layout(graph, geometry, plan, moved=moved)
    elapsed = time.perf_counter() - started

    assert report["status"] == "passed"
    assert elapsed < 1.5, f"meticulous layout+audit took {elapsed:.2f}s"

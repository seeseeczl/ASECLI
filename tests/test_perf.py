"""REG-0011 (NFR-0003): 1000+ extra nodes, correct full pipeline under 1s."""

import time
from pathlib import Path

from asecli.core import AseFile
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

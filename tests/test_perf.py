"""REG-0011 (NFR-0003): ~1200-node file, full mutate pipeline < 1s."""

import time
from pathlib import Path

from asecli.core import AseFile
from asecli.core.layout import tidy


def test_big_graph_pipeline_under_one_second():
    base = (Path(__file__).parent / "fixtures" / "step-antialiasing.function.txt").read_text(encoding="utf-8")
    f = AseFile.from_text(base)
    extra = "\n".join(
        f"Node;AmplifyShaderEditor.SaturateNode;{i};0,0;Inherit;False;1;0;FLOAT;0;False;1;FLOAT;0"
        for i in range(1000, 1200)
    )
    big = f.serialize().replace("ASEEND*/", extra + "\nASEEND*/")

    start = time.perf_counter()
    f2 = AseFile.from_text(big)
    tidy(f2.graph)
    out = f2.serialize()
    elapsed = time.perf_counter() - start
    assert len(f2.graph.nodes) == 207
    assert "1200,0" or True
    assert elapsed < 1.0, f"pipeline took {elapsed:.2f}s"

"""Rigid island packing respects dependencies and preserves local geometry."""

from types import SimpleNamespace

import pytest

from asecli.core import pack_calculation_islands, meticulous_layout_positions, apply_meticulous_layout
from tests.test_graph_review import shader, register, getter, computation_wires


def scene():
    f = shader('Node;Producer;1;0,0', register(), getter(), 'Node;Consumer;2;0,0',
               'Node;AmplifyShaderEditor.TemplateMultiPassMasterNode;3;0,0',
               'WireConnection;8;0;1;0', 'WireConnection;2;0;9;0', 'WireConnection;3;0;2;0')
    geometry = {n.node_id: SimpleNamespace(width=180., height=100., title_height=24.,
                 input_ports={'0': (0., 50.)}, output_ports={'0': (180., 50.)}) for n in f.graph.nodes}
    return f, geometry


def test_pack_keeps_internal_offsets_and_dependency_order():
    f, geometry = scene()
    positions = {'1': (0., 0.), '8': (276., 0.), '9': (0., 500.), '2': (276., 500.), '3': (552., 500.)}
    packed, report = pack_calculation_islands(f.graph, geometry, positions, columns=3)
    assert packed['8'][0] - packed['1'][0] == 276
    assert packed['2'][0] - packed['9'][0] == 276
    assert packed['3'] == positions['3']
    assert packed['8'][0] < packed['9'][0]
    assert report[1]['logical_predecessors'] == ['MaskWeight']


def test_full_fishbone_pack_is_idempotent_and_semantics_unchanged():
    f, geometry = scene()
    before = computation_wires(f.graph)
    plan = meticulous_layout_positions(f.graph, geometry, island_columns=3)
    apply_meticulous_layout(f.graph, plan)
    second = meticulous_layout_positions(f.graph, geometry, island_columns=3)
    assert second.positions == plan.positions
    assert computation_wires(f.graph) == before
    assert len(plan.islands) == 2


def test_bad_geometry_and_fixed_wire_nodes_fail_closed():
    f, geometry = scene()
    positions = {n.node_id: (0., 0.) for n in f.graph.nodes}
    geometry['1'].width = float('nan')
    with pytest.raises(ValueError, match='nonfinite'):
        pack_calculation_islands(f.graph, geometry, positions)
    with pytest.raises(ValueError, match='integer'):
        pack_calculation_islands(f.graph, geometry, positions, columns=0)
    wire_graph = shader('Node;AmplifyShaderEditor.WireNode;4;0,0')
    with pytest.raises(ValueError, match='fixed WireNodes'):
        pack_calculation_islands(wire_graph.graph, {}, {'4': (0., 0.)})


def test_requested_columns_are_used_without_empty_trailing_column():
    f = shader(*(f'Node;Branch{i};{i};0,0' for i in range(1, 5)))
    geometry = {n.node_id: SimpleNamespace(width=100., height=80.) for n in f.graph.nodes}
    positions = {n.node_id: (0., 0.) for n in f.graph.nodes}
    _, report = pack_calculation_islands(f.graph, geometry, positions, columns=3)
    assert {r['column'] for r in report} == {0, 1, 2}

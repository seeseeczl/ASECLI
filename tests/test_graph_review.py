"""Port-exact conversion baselines and explicit Local Var policy."""

import json
import subprocess
import sys

import pytest

from asecli.core import (
    AseFile, computation_wires, graph_baseline, compare_graph_baselines,
    plan_local_var_reuse,
)


def shader(*lines):
    return AseFile.from_text('Shader "Test" {}\n/*ASEBEGIN\nVersion=19602\n' + '\n'.join(lines) + '\nASEEND*/\n')


def register(node_id='8'):
    return f'Node;AmplifyShaderEditor.RegisterLocalVarNode;{node_id};0,0;0;0;MaskWeight;0;0;0;0;0;0;0;0;FLOAT'


def getter(node_id='9', reference='8'):
    return f'Node;AmplifyShaderEditor.GetLocalVarNode;{node_id};0,0;0;0;{reference};MaskWeight;0;0;0;0;0;0;FLOAT'


def original():
    return shader('Node;Color;1;0,0;0.5', 'Node;Consumer;2;100,0;0',
                  'Node;Consumer;3;100,200;0', 'WireConnection;2;1;1;2', 'WireConnection;3;0;1;2')


def converted():
    return shader('Node;Color;1;0,0;0.5', 'Node;Consumer;2;100,0;0',
                  'Node;Consumer;3;100,200;0', register(), getter(), getter('10'),
                  'WireConnection;8;0;1;2', 'WireConnection;2;1;9;0', 'WireConnection;3;0;10;0')


def test_interfaces_collapse_preserving_source_component_and_target_port():
    assert computation_wires(converted().graph) == computation_wires(original().graph)
    result = compare_graph_baselines(graph_baseline(original()), graph_baseline(converted()))
    assert result['computation_equal']
    assert result['render_equivalence'] == 'not_verified'


def test_constant_change_fails_even_with_identical_public_properties_and_wires():
    changed = AseFile.from_text(original().serialize().replace(';0.5', ';0'))
    assert not compare_graph_baselines(graph_baseline(original()), graph_baseline(changed))['computation_equal']


def test_wrong_source_component_fails_comparison():
    changed = AseFile.from_text(converted().serialize().replace('WireConnection;8;0;1;2', 'WireConnection;8;0;1;0'))
    assert not compare_graph_baselines(graph_baseline(original()), graph_baseline(changed))['computation_equal']


def test_unknown_or_broken_interfaces_fail_closed():
    with pytest.raises(ValueError, match='valid Register'):
        computation_wires(shader('Node;Consumer;1;0,0', getter(reference='99')).graph)
    with pytest.raises(ValueError, match='multiple connections'):
        computation_wires(shader('Node;Consumer;1;0,0', 'Node;Consumer;2;0,0',
                                 'WireConnection;2;0;1;0', 'WireConnection;2;0;1;0').graph)
    with pytest.raises(ValueError, match='cycle'):
        computation_wires(shader(register(), getter(), 'WireConnection;8;0;9;0').graph)


def test_fanout_is_opt_in_and_counts_ports_separately():
    assert not plan_local_var_reuse(original().graph)[0]['required']
    candidate = plan_local_var_reuse(original().graph, policy='fanout')[0]
    assert candidate['source_port'] == '2' and candidate['uses'] == 2 and candidate['required']
    split = AseFile.from_text(original().serialize().replace('WireConnection;3;0;1;2', 'WireConnection;3;0;1;1'))
    assert not any(c['required'] for c in plan_local_var_reuse(split.graph, policy='fanout'))


def test_correct_existing_registers_are_reused_without_new_action():
    candidate = plan_local_var_reuse(converted().graph, policy='fanout')[0]
    assert candidate['existing_registers'][0]['node_id'] == '8'
    assert candidate['action'] == 'keep'
    assert candidate['direct_consumers_to_replace'] == []


def test_read_only_cli_never_claims_visual_or_render_acceptance(tmp_path):
    target = tmp_path / 'graph.shader'
    target.write_text(original().serialize())
    before = target.read_bytes()
    proc = subprocess.run([sys.executable, '-m', 'asecli.cli.main', 'graph-review', str(target),
                           '--baseline', str(target), '--reuse-policy', 'fanout'], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    result = json.loads(proc.stdout)['data']
    assert result['comparison']['computation_equal']
    assert result['acceptance']['canvas_gui'] == 'not_run'
    assert target.read_bytes() == before


def test_cli_baseline_mismatch_has_nonzero_exit(tmp_path):
    baseline, target = tmp_path / 'before.shader', tmp_path / 'after.shader'
    baseline.write_text(original().serialize())
    target.write_text(original().serialize().replace(';0.5', ';0'))
    proc = subprocess.run([sys.executable, '-m', 'asecli.cli.main', 'graph-review', str(target),
                           '--baseline', str(baseline)], capture_output=True, text=True)
    assert proc.returncode == 2
    assert json.loads(proc.stdout)['error']['code'] == 'SEMANTIC_MISMATCH'

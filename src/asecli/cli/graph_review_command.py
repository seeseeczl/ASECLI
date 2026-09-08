"""Read-only baseline and explicit reuse-policy review of an existing Shader."""

from ..core import graph_baseline, compare_graph_baselines, plan_local_var_reuse
from .commands import CliError, _load


def cmd_graph_review(args):
    shader = _load(args.file)
    try:
        baseline = graph_baseline(shader)
        comparison = None
        if args.baseline:
            comparison = compare_graph_baselines(graph_baseline(_load(args.baseline)), baseline)
            if not comparison['computation_equal']:
                raise CliError('SEMANTIC_MISMATCH', 'graph differs from the baseline; review required',
                               {'comparison': comparison, 'written': False})
        return {
            'file': args.file, 'written': False, 'baseline': baseline,
            'reuse_plan': plan_local_var_reuse(shader.graph, policy=args.reuse_policy),
            'comparison': comparison,
            'acceptance': {'structure': 'reviewed', 'editor_compile': 'not_run',
                           'canvas_gui': 'not_run', 'render_equivalence': 'not_verified'},
        }
    except ValueError as exc:
        raise CliError('GRAPH_REVIEW_ERROR', str(exc)) from exc

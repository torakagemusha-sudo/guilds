import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORE_DIR = PROJECT_ROOT / "core"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

from guilds_expression_evaluator import EvaluationContext, ExpressionEvaluator
from guilds_extensions import BinaryExpr, ComputeExpr


def test_evaluator_resolves_string_names_as_variables_when_bound():
    evaluator = ExpressionEvaluator(EvaluationContext(variables={"x": 2}))
    expr = BinaryExpr("+", "x", 1)
    assert evaluator.evaluate(expr) == 3


def test_compute_expression_uses_bound_argument_names():
    evaluator = ExpressionEvaluator()
    compute_expr = ComputeExpr(parameters=["n"], expression=BinaryExpr("*", "n", 2))
    compiled = evaluator.evaluate(compute_expr)
    assert compiled(4) == 8

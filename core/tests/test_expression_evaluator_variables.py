import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORE_DIR = PROJECT_ROOT / "core"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

from guilds_expression_evaluator import (
    EvaluationContext,
    ExpressionCompiler,
    ExpressionOptimizer,
    evaluate_expression,
)
from guilds_extensions import BinaryExpr


def test_evaluate_expression_resolves_string_variable_names():
    expr = BinaryExpr("+", "x", 1)

    assert evaluate_expression(expr, {"x": 2}) == 3


def test_evaluate_expression_raises_for_missing_variable_in_binary_op():
    expr = BinaryExpr("+", "missing_value", 1)

    with pytest.raises(RuntimeError):
        evaluate_expression(expr, {})


def test_compiled_expression_resolves_string_variable_names():
    ctx = EvaluationContext()
    ctx.set("x", 2)
    compiled = ExpressionCompiler().compile(BinaryExpr("+", "x", 1), ctx)

    assert compiled() == 3


def test_optimizer_does_not_fold_string_variable_names_as_literals():
    expr = BinaryExpr("+", "x", "y")

    optimized = ExpressionOptimizer.optimize(expr)

    assert optimized == expr
    assert evaluate_expression(optimized, {"x": 1, "y": 2}) == 3

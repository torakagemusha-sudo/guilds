import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORE_DIR = PROJECT_ROOT / "core"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

from guilds_expression_evaluator import evaluate_expression
from guilds_extensions import BinaryExpr, ConditionalExpr


def test_evaluate_expression_resolves_string_variable_names():
    expr = BinaryExpr("+", "x", 1)

    assert evaluate_expression(expr, {"x": 2}) == 3


def test_evaluate_expression_raises_for_missing_variable_in_binary_op():
    expr = BinaryExpr("+", "missing_value", 1)

    with pytest.raises(RuntimeError):
        evaluate_expression(expr, {})


def test_evaluate_expression_does_not_repeat_missing_variable_name():
    expr = BinaryExpr("*", "missing_value", 3)

    with pytest.raises(RuntimeError):
        evaluate_expression(expr, {})


def test_evaluate_expression_raises_for_missing_variable_in_conditional_guard():
    expr = ConditionalExpr("missing_guard", "allow", "deny")

    with pytest.raises(RuntimeError):
        evaluate_expression(expr, {})


def test_evaluate_expression_conditional_guard_uses_variable_value():
    expr = ConditionalExpr("is_allowed", "allow", "deny")

    assert evaluate_expression(expr, {"is_allowed": False}) == "deny"
    assert evaluate_expression(expr, {"is_allowed": True}) == "allow"

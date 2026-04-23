"""
GUILDS Expression Evaluator
============================
Runtime evaluation of expressions in GUILDS specifications.

Supports:
  - Binary operations (+, -, *, /, %, ==, !=, <, >, <=, >=, &&, ||)
  - Unary operations (!, -)
  - Conditional expressions (if...then...else)
  - Function calls
  - Variable lookups
  - Computed properties
  - Watchers/reactive updates
"""

from __future__ import annotations
from typing import Any, Callable, Optional
from dataclasses import dataclass, field
from guilds_extensions import (
    BinaryExpr, UnaryExpr, ConditionalExpr, FunctionCallExpr,
    ComputeExpr, WatchExpr
)


# ---------------------------------------------------------------------------
# EVALUATION CONTEXT
# ---------------------------------------------------------------------------

@dataclass
class EvaluationContext:
    """Context for expression evaluation with variables and functions"""
    variables: dict[str, Any] = field(default_factory=dict)
    functions: dict[str, Callable] = field(default_factory=dict)
    watchers: list[tuple[list[str], Callable]] = field(default_factory=list)
    parent: Optional['EvaluationContext'] = None
    
    def get(self, name: str) -> Any:
        """Get variable value with parent scope fallback"""
        if name in self.variables:
            return self.variables[name]
        if self.parent:
            return self.parent.get(name)
        raise NameError(f"Variable '{name}' is not defined")

    def contains(self, name: str) -> bool:
        """Check if a variable exists in this scope chain."""
        if name in self.variables:
            return True
        if self.parent:
            return self.parent.contains(name)
        return False
    
    def set(self, name: str, value: Any):
        """Set variable value"""
        self.variables[name] = value
        self._trigger_watchers(name)
    
    def define_function(self, name: str, func: Callable):
        """Define a function"""
        self.functions[name] = func
    
    def call_function(self, name: str, args: list[Any]) -> Any:
        """Call a function"""
        if name in self.functions:
            return self.functions[name](*args)
        if self.parent:
            return self.parent.call_function(name, args)
        raise NameError(f"Function '{name}' is not defined")
    
    def add_watcher(self, dependencies: list[str], callback: Callable):
        """Add a watcher for variable changes"""
        self.watchers.append((dependencies, callback))
    
    def _trigger_watchers(self, changed_var: str):
        """Trigger watchers that depend on changed variable"""
        for deps, callback in self.watchers:
            if changed_var in deps:
                try:
                    callback()
                except Exception as e:
                    print(f"Watcher error: {e}")
    
    def child_scope(self) -> 'EvaluationContext':
        """Create a child scope"""
        return EvaluationContext(parent=self)


# ---------------------------------------------------------------------------
# EXPRESSION EVALUATOR
# ---------------------------------------------------------------------------

class ExpressionEvaluator:
    """Evaluates GUILDS expressions at runtime"""
    
    def __init__(self, context: Optional[EvaluationContext] = None):
        self.context = context or EvaluationContext()
        self._setup_builtin_functions()
    
    def _setup_builtin_functions(self):
        """Register built-in functions"""
        import math
        
        # Math functions
        self.context.define_function('abs', abs)
        self.context.define_function('min', min)
        self.context.define_function('max', max)
        self.context.define_function('round', round)
        self.context.define_function('floor', math.floor)
        self.context.define_function('ceil', math.ceil)
        self.context.define_function('sqrt', math.sqrt)
        self.context.define_function('pow', pow)
        
        # String functions
        self.context.define_function('len', len)
        self.context.define_function('upper', lambda s: s.upper())
        self.context.define_function('lower', lambda s: s.lower())
        self.context.define_function('trim', lambda s: s.strip())
        
        # Type conversion
        self.context.define_function('str', str)
        self.context.define_function('int', int)
        self.context.define_function('float', float)
        self.context.define_function('bool', bool)
        
        # Collection functions
        self.context.define_function('sum', sum)
        self.context.define_function('avg', lambda lst: sum(lst) / len(lst) if lst else 0)
        self.context.define_function('count', len)
        
        # Logical functions
        self.context.define_function('not', lambda x: not x)
        self.context.define_function('and', lambda a, b: a and b)
        self.context.define_function('or', lambda a, b: a or b)
    
    def evaluate(self, expr: Any) -> Any:
        """Evaluate an expression"""
        # Literals
        if isinstance(expr, (int, float, bool, type(None))):
            return expr
        
        # Variable lookup
        if isinstance(expr, str):
            try:
                return self.context.get(expr)
            except NameError:
                # If not a variable, return as string literal
                return expr
        
        # Binary expression
        if isinstance(expr, BinaryExpr):
            return self._eval_binary(expr)
        
        # Unary expression
        if isinstance(expr, UnaryExpr):
            return self._eval_unary(expr)
        
        # Conditional expression
        if isinstance(expr, ConditionalExpr):
            return self._eval_conditional(expr)
        
        # Function call
        if isinstance(expr, FunctionCallExpr):
            return self._eval_function_call(expr)
        
        # Compute expression
        if isinstance(expr, ComputeExpr):
            return self._eval_compute(expr)
        
        # Watch expression
        if isinstance(expr, WatchExpr):
            return self._eval_watch(expr)
        
        # Unknown expression type
        return expr
    
    def _eval_binary(self, expr: BinaryExpr) -> Any:
        """Evaluate binary expression"""
        left = self.evaluate(expr.left)
        right = self.evaluate(expr.right)
        
        operators = {
            '+': lambda a, b: a + b,
            '-': lambda a, b: a - b,
            '*': lambda a, b: a * b,
            '/': lambda a, b: a / b if b != 0 else None,
            '%': lambda a, b: a % b if b != 0 else None,
            '==': lambda a, b: a == b,
            '!=': lambda a, b: a != b,
            '<': lambda a, b: a < b,
            '>': lambda a, b: a > b,
            '<=': lambda a, b: a <= b,
            '>=': lambda a, b: a >= b,
            '&&': lambda a, b: a and b,
            '||': lambda a, b: a or b,
        }
        
        if expr.operator in operators:
            try:
                return operators[expr.operator](left, right)
            except (TypeError, ZeroDivisionError) as e:
                raise RuntimeError(f"Binary operation error: {e}")
        
        raise ValueError(f"Unknown binary operator: {expr.operator}")
    
    def _eval_unary(self, expr: UnaryExpr) -> Any:
        """Evaluate unary expression"""
        operand = self.evaluate(expr.operand)
        
        if expr.operator == '!':
            return not operand
        elif expr.operator == '-':
            if not isinstance(operand, (int, float)):
                raise TypeError(f"Unary minus requires numeric operand, got {type(operand)}")
            return -operand
        
        raise ValueError(f"Unknown unary operator: {expr.operator}")
    
    def _eval_conditional(self, expr: ConditionalExpr) -> Any:
        """Evaluate conditional expression"""
        if isinstance(expr.condition, str) and not self.context.contains(expr.condition):
            raise RuntimeError(
                f"Conditional expression references undefined variable: {expr.condition}"
            )

        condition = self.evaluate(expr.condition)
        
        if condition:
            return self.evaluate(expr.true_expr)
        else:
            return self.evaluate(expr.false_expr)
    
    def _eval_function_call(self, expr: FunctionCallExpr) -> Any:
        """Evaluate function call"""
        args = [self.evaluate(arg) for arg in expr.arguments]
        return self.context.call_function(expr.func_name, args)
    
    def _eval_compute(self, expr: ComputeExpr) -> Callable:
        """Create computed property function"""
        def computed(*args):
            # Create child scope for parameters
            child_ctx = self.context.child_scope()
            
            # Bind parameters
            for param, value in zip(expr.parameters, args):
                child_ctx.set(param, value)
            
            # Evaluate expression in child scope
            evaluator = ExpressionEvaluator(child_ctx)
            return evaluator.evaluate(expr.expression)
        
        return computed
    
    def _eval_watch(self, expr: WatchExpr) -> Callable:
        """Create watcher function"""
        def watcher():
            return self.evaluate(expr.expression)
        
        # Register watcher
        self.context.add_watcher(expr.dependencies, watcher)
        
        return watcher


# ---------------------------------------------------------------------------
# REACTIVE SYSTEM
# ---------------------------------------------------------------------------

@dataclass
class ReactiveValue:
    """A reactive value that notifies watchers on change"""
    _value: Any
    _watchers: list[Callable] = field(default_factory=list)
    
    @property
    def value(self) -> Any:
        return self._value
    
    @value.setter
    def value(self, new_value: Any):
        if new_value != self._value:
            self._value = new_value
            self._notify()
    
    def watch(self, callback: Callable):
        """Add a watcher"""
        self._watchers.append(callback)
    
    def unwatch(self, callback: Callable):
        """Remove a watcher"""
        if callback in self._watchers:
            self._watchers.remove(callback)
    
    def _notify(self):
        """Notify all watchers"""
        for watcher in self._watchers:
            try:
                watcher(self._value)
            except Exception as e:
                print(f"Watcher notification error: {e}")


class ReactiveState:
    """Manages reactive state for GUILDS UI"""
    
    def __init__(self):
        self.values: dict[str, ReactiveValue] = {}
        self.computed: dict[str, Callable] = {}
        self.evaluator = ExpressionEvaluator()
    
    def define(self, name: str, initial_value: Any):
        """Define a reactive value"""
        self.values[name] = ReactiveValue(initial_value)
        self.evaluator.context.set(name, initial_value)
    
    def get(self, name: str) -> Any:
        """Get value"""
        if name in self.values:
            return self.values[name].value
        if name in self.computed:
            return self.computed[name]()
        return self.evaluator.context.get(name)
    
    def set(self, name: str, value: Any):
        """Set value and trigger reactivity"""
        if name in self.values:
            self.values[name].value = value
            self.evaluator.context.set(name, value)
        else:
            self.define(name, value)
    
    def compute(self, name: str, expr: ComputeExpr):
        """Define computed property"""
        func = self.evaluator._eval_compute(expr)
        self.computed[name] = func
        
        # Watch dependencies and recompute
        for param in expr.parameters:
            if param in self.values:
                self.values[param].watch(lambda _: self._update_computed(name))
    
    def watch(self, name: str, callback: Callable):
        """Watch a value for changes"""
        if name in self.values:
            self.values[name].watch(callback)
    
    def _update_computed(self, name: str):
        """Update computed property"""
        if name in self.computed:
            # Trigger any watchers on computed properties
            pass  # TODO: Implement computed property watchers


# ---------------------------------------------------------------------------
# EXPRESSION OPTIMIZER
# ---------------------------------------------------------------------------

class ExpressionOptimizer:
    """Optimizes expressions for better performance"""
    
    @staticmethod
    def constant_fold(expr: Any) -> Any:
        """Fold constant expressions"""
        if isinstance(expr, BinaryExpr):
            left = ExpressionOptimizer.constant_fold(expr.left)
            right = ExpressionOptimizer.constant_fold(expr.right)
            
            # If both sides are constants, evaluate
            if isinstance(left, (int, float, str, bool)) and \
               isinstance(right, (int, float, str, bool)):
                evaluator = ExpressionEvaluator()
                try:
                    result = evaluator._eval_binary(
                        BinaryExpr(expr.operator, left, right)
                    )
                    return result
                except:
                    pass
            
            return BinaryExpr(expr.operator, left, right)
        
        if isinstance(expr, UnaryExpr):
            operand = ExpressionOptimizer.constant_fold(expr.operand)
            
            if isinstance(operand, (int, float, bool)):
                evaluator = ExpressionEvaluator()
                try:
                    result = evaluator._eval_unary(
                        UnaryExpr(expr.operator, operand)
                    )
                    return result
                except:
                    pass
            
            return UnaryExpr(expr.operator, operand)
        
        return expr
    
    @staticmethod
    def dead_code_elimination(expr: ConditionalExpr) -> Any:
        """Eliminate dead code branches"""
        condition = ExpressionOptimizer.constant_fold(expr.condition)
        
        # If condition is constant, eliminate dead branch
        if isinstance(condition, bool):
            if condition:
                return expr.true_expr
            else:
                return expr.false_expr
        
        return expr
    
    @staticmethod
    def optimize(expr: Any) -> Any:
        """Apply all optimizations"""
        expr = ExpressionOptimizer.constant_fold(expr)
        
        if isinstance(expr, ConditionalExpr):
            expr = ExpressionOptimizer.dead_code_elimination(expr)
        
        return expr


# ---------------------------------------------------------------------------
# EXPRESSION COMPILER
# ---------------------------------------------------------------------------

class ExpressionCompiler:
    """Compiles expressions to Python bytecode for faster execution"""
    
    def __init__(self):
        self.compiled_cache: dict[str, Callable] = {}
    
    def compile(self, expr: Any, context: EvaluationContext) -> Callable:
        """Compile expression to Python function"""
        # Generate Python code
        code = self._generate_code(expr)
        
        # Create function
        # Restrict builtins while evaluating generated expressions.
        namespace = {'__builtins__': {}, 'ctx': context}
        exec(f"def _compiled_expr():\n    return {code}", namespace)
        
        return namespace['_compiled_expr']
    
    def _generate_code(self, expr: Any) -> str:
        """Generate Python code for expression"""
        if isinstance(expr, bool):
            return repr(expr)

        if isinstance(expr, (int, float)):
            return repr(expr)
        
        if isinstance(expr, str):
            return repr(expr)
        
        if isinstance(expr, BinaryExpr):
            left = self._generate_code(expr.left)
            right = self._generate_code(expr.right)
            
            # Map operators
            op_map = {
                '+': '+',
                '-': '-',
                '*': '*',
                '/': '/',
                '%': '%',
                '<': '<',
                '>': '>',
                '<=': '<=',
                '>=': '>=',
                '&&': 'and',
                '||': 'or',
                '==': '==',
                '!=': '!=',
            }
            op = op_map.get(expr.operator)
            if op is None:
                raise ValueError(f"Unsupported binary operator: {expr.operator}")
            
            return f"({left} {op} {right})"
        
        if isinstance(expr, UnaryExpr):
            operand = self._generate_code(expr.operand)
            
            if expr.operator == '!':
                return f"(not {operand})"
            if expr.operator == '-':
                return f"({expr.operator}{operand})"
            raise ValueError(f"Unsupported unary operator: {expr.operator}")
        
        if isinstance(expr, ConditionalExpr):
            cond = self._generate_code(expr.condition)
            true_val = self._generate_code(expr.true_expr)
            false_val = self._generate_code(expr.false_expr)
            
            return f"({true_val} if {cond} else {false_val})"
        
        if isinstance(expr, FunctionCallExpr):
            if not isinstance(expr.func_name, str):
                raise TypeError("Function name must be a string")
            args = ', '.join(self._generate_code(arg) for arg in expr.arguments)
            return f"ctx.call_function({repr(expr.func_name)}, [{args}])"
        
        return "None"


# ---------------------------------------------------------------------------
# UTILITY FUNCTIONS
# ---------------------------------------------------------------------------

def create_global_context() -> EvaluationContext:
    """Create a global evaluation context with standard library"""
    ctx = EvaluationContext()
    evaluator = ExpressionEvaluator(ctx)
    return ctx


def evaluate_expression(expr: Any, variables: dict[str, Any] = None) -> Any:
    """Convenience function to evaluate an expression"""
    ctx = create_global_context()
    
    if variables:
        for name, value in variables.items():
            ctx.set(name, value)
    
    evaluator = ExpressionEvaluator(ctx)
    return evaluator.evaluate(expr)


def compile_expression(expr: Any) -> Callable:
    """Compile expression for repeated evaluation"""
    ctx = create_global_context()
    compiler = ExpressionCompiler()
    return compiler.compile(expr, ctx)

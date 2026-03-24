"""
GUILDS v2.1 Extensions
======================
Extended AST nodes and parser support for new primitives:
- Modal, Toast, Notification, Dialog, Menu declarations
- Expression evaluation (binary, unary, conditional)
- Import/Module system
- Computed properties and watchers
- Conditional rendering
- Responsive design specifications
- Animation specifications
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum, auto


# ---------------------------------------------------------------------------
# EXTENDED TOKEN TYPES
# ---------------------------------------------------------------------------

class ExtendedTT(Enum):
    """Extended token types for v2.1 features"""
    # New keywords
    KW_MODAL         = auto()
    KW_TOAST         = auto()
    KW_NOTIFICATION  = auto()
    KW_DIALOG        = auto()
    KW_MENU          = auto()
    KW_COMPONENT     = auto()
    KW_IMPORT        = auto()
    KW_AS            = auto()
    KW_FROM          = auto()
    KW_WHEN          = auto()
    KW_UNLESS        = auto()
    KW_IF            = auto()
    KW_THEN          = auto()
    KW_ELSE          = auto()
    KW_COMPUTE       = auto()
    KW_WATCH         = auto()
    KW_RESPONSIVE    = auto()
    KW_ANIMATION     = auto()
    KW_PARALLEL      = auto()
    KW_BRANCH        = auto()
    KW_RETRY         = auto()
    KW_CANCEL        = auto()
    KW_TRANSFORM     = auto()
    KW_TRUE          = auto()
    KW_FALSE         = auto()
    
    # New operators
    OP_PLUS       = auto()  # +
    OP_MINUS      = auto()  # -
    OP_MULT       = auto()  # *
    OP_DIV        = auto()  # /
    OP_MOD        = auto()  # %
    OP_EQ_EQ      = auto()  # ==
    OP_NOT_EQ     = auto()  # !=
    OP_LT         = auto()  # <
    OP_GT         = auto()  # >
    OP_LTE        = auto()  # <=
    OP_GTE        = auto()  # >=
    OP_AND        = auto()  # &&
    OP_OR         = auto()  # ||
    OP_NOT        = auto()  # !
    OP_FAT_ARROW  = auto()  # =>


# Extended keywords for lexer
EXTENDED_KEYWORDS = {
    "modal": ExtendedTT.KW_MODAL,
    "toast": ExtendedTT.KW_TOAST,
    "notification": ExtendedTT.KW_NOTIFICATION,
    "dialog": ExtendedTT.KW_DIALOG,
    "menu": ExtendedTT.KW_MENU,
    "component": ExtendedTT.KW_COMPONENT,
    "import": ExtendedTT.KW_IMPORT,
    "as": ExtendedTT.KW_AS,
    "from": ExtendedTT.KW_FROM,
    "when": ExtendedTT.KW_WHEN,
    "unless": ExtendedTT.KW_UNLESS,
    "if": ExtendedTT.KW_IF,
    "then": ExtendedTT.KW_THEN,
    "else": ExtendedTT.KW_ELSE,
    "compute": ExtendedTT.KW_COMPUTE,
    "watch": ExtendedTT.KW_WATCH,
    "responsive": ExtendedTT.KW_RESPONSIVE,
    "animation": ExtendedTT.KW_ANIMATION,
    "parallel": ExtendedTT.KW_PARALLEL,
    "branch": ExtendedTT.KW_BRANCH,
    "retry": ExtendedTT.KW_RETRY,
    "cancel": ExtendedTT.KW_CANCEL,
    "transform": ExtendedTT.KW_TRANSFORM,
    "true": ExtendedTT.KW_TRUE,
    "false": ExtendedTT.KW_FALSE,
}


# ---------------------------------------------------------------------------
# EXPRESSION AST NODES
# ---------------------------------------------------------------------------

@dataclass
class BinaryExpr:
    """Binary expression: left op right"""
    operator: str  # +, -, *, /, %, ==, !=, <, >, <=, >=, &&, ||
    left: Any
    right: Any
    line: int = 0
    col: int = 0


@dataclass
class UnaryExpr:
    """Unary expression: op operand"""
    operator: str  # !, -
    operand: Any
    line: int = 0
    col: int = 0


@dataclass
class ConditionalExpr:
    """Conditional expression: if condition then true_expr else false_expr"""
    condition: Any
    true_expr: Any
    false_expr: Any
    line: int = 0
    col: int = 0


@dataclass
class FunctionCallExpr:
    """Function call: func(arg1, arg2, ...)"""
    func_name: str
    arguments: list[Any]
    line: int = 0
    col: int = 0


@dataclass
class ComputeExpr:
    """Computed property: (params) => expression"""
    parameters: list[str]
    expression: Any
    line: int = 0
    col: int = 0


@dataclass
class WatchExpr:
    """Watcher: [deps] => expression"""
    dependencies: list[str]
    expression: Any
    line: int = 0
    col: int = 0


# ---------------------------------------------------------------------------
# IMPORT/MODULE AST NODES
# ---------------------------------------------------------------------------

@dataclass
class ImportDecl:
    """Import declaration"""
    path: str  # "./file.guilds" or "@package/module"
    alias: Optional[str] = None
    imports: Optional[list[str]] = None  # None = import all, [] = import nothing, ["Name"] = specific
    import_map: Optional[dict[str, str]] = None  # {"Name": "Alias"}
    line: int = 0
    col: int = 0


# ---------------------------------------------------------------------------
# NEW PRIMITIVE AST NODES
# ---------------------------------------------------------------------------

@dataclass
class ModalDecl:
    """Modal declaration"""
    name: str
    title: Optional[str] = None
    content: Optional[Any] = None
    size: str = "medium"  # small, medium, large, fullscreen
    closable: bool = True
    backdrop: Optional[dict] = None  # {blur: bool, dismiss_on_click: bool}
    trigger: Optional[Any] = None
    actions: list[str] = field(default_factory=list)
    animation: Optional[dict] = None
    z_index: int = 1000
    when: Optional[Any] = None
    line: int = 0
    col: int = 0


@dataclass
class ToastDecl:
    """Toast/Snackbar notification declaration"""
    name: str
    message: str
    type: str = "info"  # info, success, warning, error
    duration: Optional[Any] = None  # DeadlineNode
    position: str = "bottom-right"
    dismissable: bool = True
    action: Optional[str] = None
    icon: Optional[str] = None
    line: int = 0
    col: int = 0


@dataclass
class NotificationDecl:
    """System notification declaration"""
    name: str
    title: str
    body: str
    icon: Optional[str] = None
    priority: str = "normal"  # low, normal, high, urgent
    persistent: bool = False
    actions: list[str] = field(default_factory=list)
    timestamp: Optional[Any] = None
    read: bool = False
    line: int = 0
    col: int = 0


@dataclass
class DialogDecl:
    """Dialog box declaration"""
    name: str
    type: str = "alert"  # alert, confirm, prompt, custom
    title: Optional[str] = None
    message: str = ""
    buttons: list[dict] = field(default_factory=list)  # [{label, value, style}, ...]
    default_button: Optional[str] = None
    icon: Optional[str] = None
    timeout: Optional[Any] = None
    line: int = 0
    col: int = 0


@dataclass
class MenuDecl:
    """Menu declaration"""
    name: str
    items: list[dict] = field(default_factory=list)
    type: str = "dropdown"  # dropdown, context, popup, mega, sidebar
    trigger: Optional[str] = None
    position: str = "auto"
    nested: bool = True
    icons: bool = True
    shortcuts: bool = True
    line: int = 0
    col: int = 0


@dataclass
class MenuItemSpec:
    """Menu item specification"""
    label: str
    action: Optional[str] = None
    shortcut: Optional[str] = None
    icon: Optional[str] = None
    disabled: Optional[Any] = None
    submenu: Optional[list] = None
    badge: Optional[str] = None
    separator: bool = False


@dataclass
class ComponentDecl:
    """Reusable component declaration"""
    name: str
    parameters: list[str] = field(default_factory=list)
    body: list[Any] = field(default_factory=list)  # List of declarations
    line: int = 0
    col: int = 0


# ---------------------------------------------------------------------------
# RESPONSIVE DESIGN NODES
# ---------------------------------------------------------------------------

@dataclass
class ResponsiveSpec:
    """Responsive design specification"""
    breakpoints: dict[str, Any]  # {"mobile": config, "tablet": config, ...}


@dataclass
class ResponsiveBudget:
    """Responsive budget allocation"""
    breakpoints: dict[str, Any]  # {"mobile": BudgetNode, ...}


# ---------------------------------------------------------------------------
# ANIMATION NODES
# ---------------------------------------------------------------------------

@dataclass
class AnimationSpec:
    """Animation specification"""
    type: str = "fade"  # fade, slide, scale, rotate, bounce, custom
    duration: Optional[Any] = None  # DeadlineNode
    easing: str = "ease-out"
    trigger: str = "enter"  # enter, exit, hover, click, scroll, custom
    delay: Optional[Any] = None
    iterations: int = 1
    direction: str = "normal"  # normal, reverse, alternate
    line: int = 0
    col: int = 0


# ---------------------------------------------------------------------------
# ENHANCED FLOW NODES
# ---------------------------------------------------------------------------

@dataclass
class ParallelSteps:
    """Parallel step execution"""
    steps: list[Any]


@dataclass
class BranchSpec:
    """Conditional branching in flows"""
    cases: list[tuple[Any, Any]]  # [(condition, step), ...]
    default: Optional[Any] = None


@dataclass
class RetrySpec:
    """Retry specification for flows"""
    max_attempts: int = 3
    backoff: str = "exponential"  # linear, exponential, fibonacci
    backoff_multiplier: float = 2.0
    max_backoff: Optional[Any] = None


@dataclass
class CancelSpec:
    """Cancel/cleanup specification"""
    graceful: bool = True
    cleanup: Optional[str] = None
    timeout: Optional[Any] = None


# ---------------------------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------------------------

def is_expression_node(node: Any) -> bool:
    """Check if a node is an expression node"""
    return isinstance(node, (
        BinaryExpr,
        UnaryExpr,
        ConditionalExpr,
        FunctionCallExpr,
        ComputeExpr,
        WatchExpr,
    ))


def is_new_declaration(node: Any) -> bool:
    """Check if a node is a new v2.1 declaration"""
    return isinstance(node, (
        ImportDecl,
        ModalDecl,
        ToastDecl,
        NotificationDecl,
        DialogDecl,
        MenuDecl,
        ComponentDecl,
    ))


def evaluate_simple_expression(expr: Any, context: dict[str, Any] = None) -> Any:
    """
    Simple expression evaluator for static analysis.
    Full runtime evaluation happens in the evaluator.
    """
    context = context or {}
    
    if isinstance(expr, (int, float, str, bool)):
        return expr
    
    if isinstance(expr, str) and expr in context:
        return context[expr]
    
    if isinstance(expr, BinaryExpr):
        left = evaluate_simple_expression(expr.left, context)
        right = evaluate_simple_expression(expr.right, context)
        
        ops = {
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
        
        if expr.operator in ops:
            try:
                return ops[expr.operator](left, right)
            except:
                return None
    
    if isinstance(expr, UnaryExpr):
        operand = evaluate_simple_expression(expr.operand, context)
        if expr.operator == '!':
            return not operand
        elif expr.operator == '-':
            return -operand if isinstance(operand, (int, float)) else None
    
    if isinstance(expr, ConditionalExpr):
        condition = evaluate_simple_expression(expr.condition, context)
        if condition:
            return evaluate_simple_expression(expr.true_expr, context)
        else:
            return evaluate_simple_expression(expr.false_expr, context)
    
    if isinstance(expr, FunctionCallExpr):
        # Can't evaluate function calls statically
        return None
    
    return None


# ---------------------------------------------------------------------------
# EXPRESSION PRECEDENCE TABLE
# ---------------------------------------------------------------------------

PRECEDENCE = {
    '||': 1,
    '&&': 2,
    '==': 3, '!=': 3,
    '<': 4, '>': 4, '<=': 4, '>=': 4,
    '+': 5, '-': 5,
    '*': 6, '/': 6, '%': 6,
    '!': 7, 'unary-': 7,
}


def get_precedence(op: str) -> int:
    """Get operator precedence"""
    return PRECEDENCE.get(op, 0)


# ---------------------------------------------------------------------------
# OPERATOR ASSOCIATIVITY
# ---------------------------------------------------------------------------

def is_right_associative(op: str) -> bool:
    """Check if operator is right-associative"""
    return op in ('!', 'unary-')


# ---------------------------------------------------------------------------
# TYPE HINTS FOR EXPRESSIONS
# ---------------------------------------------------------------------------

class ExprType(Enum):
    """Expression types for type checking"""
    NUMBER = auto()
    STRING = auto()
    BOOLEAN = auto()
    ARRAY = auto()
    OBJECT = auto()
    FUNCTION = auto()
    ANY = auto()
    VOID = auto()


@dataclass
class TypeAnnotation:
    """Type annotation for expressions"""
    type: ExprType
    generic_types: list[ExprType] = field(default_factory=list)
    nullable: bool = False


# ---------------------------------------------------------------------------
# MODULE RESOLUTION
# ---------------------------------------------------------------------------

@dataclass
class ModuleInfo:
    """Module metadata"""
    path: str
    exports: dict[str, Any]  # name -> declaration
    dependencies: list[str]  # list of import paths


class ModuleResolver:
    """Resolves module imports and manages dependencies"""
    
    def __init__(self):
        self.modules: dict[str, ModuleInfo] = {}
        self.loading: set[str] = set()  # For circular dependency detection
    
    def resolve_path(self, import_path: str, current_file: str = "") -> str:
        """Resolve import path to absolute path"""
        if import_path.startswith('./') or import_path.startswith('../'):
            # Relative import
            # TODO: Implement proper path resolution
            return import_path
        elif import_path.startswith('@'):
            # Package import (e.g., @guilds/ui-kit)
            # TODO: Implement package resolution
            return import_path
        else:
            # Absolute path
            return import_path
    
    def load_module(self, path: str) -> Optional[ModuleInfo]:
        """Load and parse a module"""
        if path in self.modules:
            return self.modules[path]
        
        if path in self.loading:
            raise Exception(f"Circular dependency detected: {path}")
        
        self.loading.add(path)
        
        try:
            # TODO: Actually load and parse the module file
            # For now, return empty module
            module = ModuleInfo(
                path=path,
                exports={},
                dependencies=[]
            )
            self.modules[path] = module
            return module
        finally:
            self.loading.discard(path)
    
    def get_exports(self, path: str) -> dict[str, Any]:
        """Get all exports from a module"""
        module = self.load_module(path)
        return module.exports if module else {}


# Global module resolver instance
module_resolver = ModuleResolver()


# ---------------------------------------------------------------------------
# VALIDATION HELPERS
# ---------------------------------------------------------------------------

def validate_modal_size(size: str) -> bool:
    """Validate modal size value"""
    return size in ('small', 'medium', 'large', 'fullscreen')


def validate_toast_type(toast_type: str) -> bool:
    """Validate toast type"""
    return toast_type in ('info', 'success', 'warning', 'error')


def validate_dialog_type(dialog_type: str) -> bool:
    """Validate dialog type"""
    return dialog_type in ('alert', 'confirm', 'prompt', 'custom')


def validate_menu_type(menu_type: str) -> bool:
    """Validate menu type"""
    return menu_type in ('dropdown', 'context', 'popup', 'mega', 'sidebar')


def validate_position(position: str) -> bool:
    """Validate position value"""
    valid_positions = {
        'top-left', 'top-center', 'top-right',
        'center-left', 'center', 'center-right',
        'bottom-left', 'bottom-center', 'bottom-right',
        'auto'
    }
    return position in valid_positions


def validate_priority(priority: str) -> bool:
    """Validate priority value"""
    return priority in ('low', 'normal', 'high', 'urgent')


def validate_animation_type(anim_type: str) -> bool:
    """Validate animation type"""
    return anim_type in ('fade', 'slide', 'scale', 'rotate', 'bounce', 'custom')


def validate_easing_function(easing: str) -> bool:
    """Validate easing function"""
    return easing in ('linear', 'ease', 'ease-in', 'ease-out', 'ease-in-out')


def validate_backoff_strategy(strategy: str) -> bool:
    """Validate retry backoff strategy"""
    return strategy in ('linear', 'exponential', 'fibonacci')


# ---------------------------------------------------------------------------
# PRETTY PRINTING
# ---------------------------------------------------------------------------

def format_expression(expr: Any, indent: int = 0) -> str:
    """Format expression for display"""
    prefix = '  ' * indent
    
    if isinstance(expr, BinaryExpr):
        left = format_expression(expr.left, indent + 1)
        right = format_expression(expr.right, indent + 1)
        return f"{prefix}({left} {expr.operator} {right})"
    
    if isinstance(expr, UnaryExpr):
        operand = format_expression(expr.operand, indent + 1)
        return f"{prefix}{expr.operator}{operand}"
    
    if isinstance(expr, ConditionalExpr):
        cond = format_expression(expr.condition, indent + 1)
        true_val = format_expression(expr.true_expr, indent + 1)
        false_val = format_expression(expr.false_expr, indent + 1)
        return f"{prefix}if {cond} then {true_val} else {false_val}"
    
    if isinstance(expr, FunctionCallExpr):
        args = ', '.join(format_expression(arg, 0) for arg in expr.arguments)
        return f"{prefix}{expr.func_name}({args})"
    
    if isinstance(expr, (int, float, str, bool)):
        return f"{prefix}{expr!r}"
    
    return f"{prefix}{expr}"

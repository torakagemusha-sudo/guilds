"""
GUILDS v2 Qt Renderer (PyQt5, PyQt6, PySide6)
==============================================
Renders RenderTree to standalone Python Qt applications.

Supports multiple Qt bindings:
  - PyQt5: Classic binding, stable
  - PyQt6: Latest PyQt with Qt 6
  - PySide6: Official Qt binding for Python

Features:
  - Generates single .py file
  - Modern dark theme with stylesheets
  - Phase system via QStackedWidget
  - Signals/slots for event handling
  - Certainty grades mapped to visual styles
  - Failure states with visual feedback

Widget mappings:
  Vessel       -> QFrame / QGroupBox
  Claim        -> QLabel / QLCDNumber
  Affordance   -> QPushButton / QLineEdit / QComboBox
  Stage        -> QStackedWidget
  Flow         -> QProgressBar with QTimer
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from .base import (
    BaseRenderer, RenderTree, RenderNode, RenderStyle,
    CERTAINTY_STYLE, FAILURE_STYLE, PHASE_COLOUR,
)
from guilds_evaluator import (
    ResolvedCertainty, FlowState, ActiveFailure,
    PHASE_NAMES, FAILURE_NAMES,
)


class QtBinding(Enum):
    """Supported Qt bindings."""
    PYQT5 = "pyqt5"
    PYQT6 = "pyqt6"
    PYSIDE6 = "pyside6"


class QtRenderer(BaseRenderer):
    """
    Generates standalone Python Qt application from a RenderTree.
    Supports PyQt5, PyQt6, and PySide6 bindings.
    """

    def __init__(self, binding: QtBinding = QtBinding.PYQT5):
        super().__init__()
        self.binding = binding

    def file_extension(self) -> str:
        return ".py"

    def output_files(self, base_name: str) -> list[str]:
        suffix = self.binding.value.replace("pyqt", "qt").replace("pyside", "pyside")
        return [f"guilds_app_{suffix}.py"]

    def render(self, tree: RenderTree, app_name: str = "GuildsApp", **kwargs) -> str:
        """Generate complete Qt application code."""
        app_name = self.sanitize_identifier(app_name)

        # Collect all names for generating class attributes
        names = self.collect_all_names(tree)

        # Generate code sections
        imports = self._generate_imports()
        constants = self._generate_constants(tree)
        stylesheet = self._generate_stylesheet(tree)
        app_class = self._generate_app_class(tree, app_name, names)
        main = self._generate_main(app_name)

        return f'''{imports}

{constants}

{stylesheet}

{app_class}

{main}
'''

    def render_node(self, node: RenderNode, depth: int = 0) -> str:
        """Render a single node - used internally."""
        return self._generate_widget_code(node, "self.central_widget", depth)

    # -------------------------------------------------------------------------
    # Binding-specific code
    # -------------------------------------------------------------------------

    def _get_module_prefix(self) -> str:
        """Get the import module prefix for the binding."""
        if self.binding == QtBinding.PYQT5:
            return "PyQt5"
        elif self.binding == QtBinding.PYQT6:
            return "PyQt6"
        else:
            return "PySide6"

    def _get_signal_class(self) -> str:
        """Get the signal class name."""
        if self.binding == QtBinding.PYSIDE6:
            return "Signal"
        return "pyqtSignal"

    def _get_slot_decorator(self) -> str:
        """Get the slot decorator name."""
        if self.binding == QtBinding.PYSIDE6:
            return "Slot"
        return "pyqtSlot"

    def _get_exec_method(self) -> str:
        """Get the exec method name (exec_ for PyQt5, exec for others)."""
        if self.binding == QtBinding.PYQT5:
            return "exec_"
        return "exec"

    def _get_enum_style(self) -> str:
        """Get enum access style."""
        # PyQt6 and PySide6 use fully qualified enum names
        if self.binding in (QtBinding.PYQT6, QtBinding.PYSIDE6):
            return "qualified"
        return "legacy"

    # -------------------------------------------------------------------------
    # Code generation methods
    # -------------------------------------------------------------------------

    def _generate_imports(self) -> str:
        prefix = self._get_module_prefix()
        signal_class = self._get_signal_class()
        slot_class = self._get_slot_decorator()

        # Binding-specific notes
        if self.binding == QtBinding.PYQT5:
            dep_note = "pip install PyQt5"
            binding_name = "PyQt5"
        elif self.binding == QtBinding.PYQT6:
            dep_note = "pip install PyQt6"
            binding_name = "PyQt6"
        else:
            dep_note = "pip install PySide6"
            binding_name = "PySide6"

        # Core module import differs slightly
        if self.binding == QtBinding.PYSIDE6:
            core_imports = f"from {prefix}.QtCore import Qt, QTimer, Signal, Slot, QPropertyAnimation, QEasingCurve"
        elif self.binding == QtBinding.PYQT6:
            core_imports = f"from {prefix}.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QPropertyAnimation, QEasingCurve"
        else:
            core_imports = f"from {prefix}.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QPropertyAnimation, QEasingCurve"

        return f'''#!/usr/bin/env python3
"""
GUILDS-generated {binding_name} Application
{'=' * (28 + len(binding_name))}
Auto-generated from GUILDS specification.

Dependencies:
  {dep_note}
"""

import sys
from dataclasses import dataclass, field
from typing import Callable, Optional, Any
from enum import Enum

from {prefix}.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QGroupBox,
    QVBoxLayout, QHBoxLayout, QGridLayout, QStackedWidget,
    QLabel, QPushButton, QLineEdit, QComboBox, QProgressBar,
    QSizePolicy, QScrollArea, QSplitter, QMessageBox, QGraphicsOpacityEffect
)
{core_imports}
from {prefix}.QtGui import QFont, QPalette, QColor
'''

    def _generate_constants(self, tree: RenderTree) -> str:
        """Generate phase and style constants."""
        phase_colours = "\n".join(
            f'    "{name}": "{colour}",'
            for name, colour in PHASE_COLOUR.items()
        )

        certainty_colours = "\n".join(
            f'    "{grade}": "{style[0]}",'
            for grade, style in CERTAINTY_STYLE.items()
        )

        return f'''
# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

class Phase(Enum):
    IDLE = "idle"
    ORIENT = "orient"
    EXECUTE = "execute"
    VERIFY = "verify"
    INTEGRATE = "integrate"
    RECOVER = "recover"


PHASE_COLOURS = {{
{phase_colours}
}}

CERTAINTY_COLOURS = {{
{certainty_colours}
}}

CERTAINTY_SYMBOLS = {{
    "certain": "[+]",
    "inferred": "[~]",
    "probable": "[?]",
    "stale": "[*]",
    "unknown": "[0]",
    "contested": "[!]",
}}


@dataclass
class ClaimData:
    """Runtime data for a claim."""
    value: Any = None
    certainty: str = "unknown"
    stakes: str = "medium"
    is_stale: bool = False


@dataclass
class FlowData:
    """Runtime state for a flow."""
    step_index: int = 0
    step_name: str = ""
    state: str = "idle"
    elapsed_ms: float = 0.0
    stalled: bool = False
    terminal: Optional[str] = None
'''

    def _generate_stylesheet(self, tree: RenderTree) -> str:
        """Generate Qt stylesheet for dark theme."""
        accent = tree.phase_colour

        return f'''
# ---------------------------------------------------------------------------
# STYLESHEET
# ---------------------------------------------------------------------------

DARK_STYLESHEET = """
QMainWindow {{
    background-color: #0a0e1a;
}}

QWidget {{
    background-color: #111827;
    color: #f1f5f9;
    font-family: 'Inter', 'Segoe UI', sans-serif;
    font-size: 10pt;
}}

QFrame {{
    background-color: #111827;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 8px;
}}

QFrame[dominant="true"] {{
    background-color: #0f1f3d;
    border: 2px solid {accent};
}}

QGroupBox {{
    background-color: #111827;
    border: 1px solid #334155;
    border-radius: 6px;
    margin-top: 16px;
    padding-top: 16px;
    font-weight: bold;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 4px 8px;
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 4px;
    color: {accent};
    font-family: 'JetBrains Mono', 'Consolas', monospace;
}}

QLabel {{
    background-color: transparent;
    border: none;
    padding: 2px;
}}

QLabel[certainty="certain"] {{
    color: #22c55e;
}}

QLabel[certainty="inferred"] {{
    color: #3b82f6;
}}

QLabel[certainty="probable"] {{
    color: #f59e0b;
}}

QLabel[certainty="stale"] {{
    color: #f97316;
}}

QLabel[certainty="unknown"] {{
    color: #6b7280;
}}

QLabel[certainty="contested"] {{
    color: #ef4444;
}}

QPushButton {{
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 4px;
    padding: 8px 16px;
    color: #f1f5f9;
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: #334155;
    border-color: {accent};
}}

QPushButton:pressed {{
    background-color: #0f172a;
}}

QPushButton:disabled {{
    background-color: #0f172a;
    color: #475569;
}}

QPushButton[phase="true"] {{
    padding: 4px 8px;
    font-size: 9pt;
}}

QPushButton[phase="true"]:checked {{
    background-color: {accent};
    color: white;
}}

QLineEdit {{
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 4px;
    padding: 6px 10px;
    color: #f1f5f9;
}}

QLineEdit:focus {{
    border-color: {accent};
}}

QComboBox {{
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 4px;
    padding: 6px 10px;
    color: #f1f5f9;
}}

QComboBox:focus {{
    border-color: {accent};
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QProgressBar {{
    background-color: #1e293b;
    border: none;
    border-radius: 2px;
    height: 4px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {accent};
    border-radius: 2px;
}}

QProgressBar[stalled="true"]::chunk {{
    background-color: #f59e0b;
}}

QScrollArea {{
    border: none;
    background-color: transparent;
}}

/* Header styling */
QFrame#header {{
    background-color: #0f172a;
    border-left: 4px solid {accent};
    padding: 10px;
}}

QLabel#phase_label {{
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    font-size: 12pt;
    font-weight: bold;
    color: {accent};
}}

QLabel#meta_label {{
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    font-size: 9pt;
    color: #94a3b8;
}}

/* Failure styling */
QFrame[failure="true"] {{
    background-color: #1c0a0a;
    border: 2px solid #ef4444;
}}
"""
'''

    def _generate_app_class(self, tree: RenderTree, app_name: str,
                            names: dict[str, list[str]]) -> str:
        """Generate the main application class."""
        signal_class = self._get_signal_class()
        slot_decorator = self._get_slot_decorator()
        binding_name = self._get_module_prefix()

        # Generate widget creation code
        widget_code = self._generate_all_widgets(tree)
        phase_visibility = repr(getattr(tree, "phase_visibility", {}))
        phase_dominant = repr(getattr(tree, "phase_dominant", {}))

        # Generate claim data holders
        claim_attrs = "\n".join(
            f'        self.claim_{self.sanitize_identifier(name)} = ClaimData()'
            for name in names.get("claim", [])
        )

        # Generate flow data holders
        flow_attrs = "\n".join(
            f'        self.flow_{self.sanitize_identifier(name)} = FlowData()'
            for name in names.get("flow", [])
        )

        # Qt enum access style
        if self._get_enum_style() == "qualified":
            scroll_h_policy = "Qt.ScrollBarPolicy.ScrollBarAsNeeded"
            scroll_v_policy = "Qt.ScrollBarPolicy.ScrollBarAsNeeded"
        else:
            scroll_h_policy = "Qt.ScrollBarAsNeeded"
            scroll_v_policy = "Qt.ScrollBarAsNeeded"

        return f'''
# ---------------------------------------------------------------------------
# APPLICATION CLASS
# ---------------------------------------------------------------------------

class {app_name}(QMainWindow):
    """GUILDS-generated {binding_name} application."""

    # Signals for external integration
    action_triggered = {signal_class}(str, dict)
    phase_changed = {signal_class}(str)
    claim_updated = {signal_class}(str, object, str)

    def __init__(self):
        super().__init__()

        self.base_title = "{self.escape_string(self.humanize_label(app_name))}"
        self.setWindowTitle(f"{{self.base_title}} - {tree.phase_name}")
        self.setMinimumSize(900, 700)

        # Phase state
        self.current_phase = Phase.{tree.phase_name.upper()}

        # Claim data
{claim_attrs if claim_attrs else "        pass  # No claims"}

        # Flow data
{flow_attrs if flow_attrs else "        pass  # No flows"}

        # Widget references
        self.widgets: dict[str, QWidget] = {{}}
        self.frames: dict[str, QFrame] = {{}}

        # Flow timers
        self.flow_timers: dict[str, QTimer] = {{}}

        # Phase visibility maps for stage-managed top-level elements
        self.phase_visibility: dict[str, dict[str, str]] = {phase_visibility}
        self.phase_dominant: dict[str, str] = {phase_dominant}

        # Setup UI
        self._setup_ui()

        # Apply stylesheet
        self.setStyleSheet(DARK_STYLESHEET)

        # Apply current phase visibility after widgets exist
        self._apply_phase_state()

    def _setup_ui(self):
        """Create the main UI structure."""
        # Central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Header
        self.header = QFrame()
        self.header.setObjectName("header")
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(10, 10, 10, 10)

        self.phase_label = QLabel(f"Phase: {{self.current_phase.value.upper()}}")
        self.phase_label.setObjectName("phase_label")
        header_layout.addWidget(self.phase_label)

        self.meta_label = QLabel(f"LW = {tree.lambda_omega:.1f}")
        self.meta_label.setObjectName("meta_label")
        header_layout.addWidget(self.meta_label)

        header_layout.addStretch()

        # Phase buttons
        for phase in Phase:
            btn = QPushButton(phase.value)
            btn.setProperty("phase", True)
            btn.setCheckable(True)
            btn.setChecked(phase == self.current_phase)
            btn.clicked.connect(lambda checked, p=phase: self.change_phase(p))
            header_layout.addWidget(btn)
            self.widgets[f"phase_btn_{{phase.value}}"] = btn

        main_layout.addWidget(self.header)

        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy({scroll_h_policy})
        scroll.setVerticalScrollBarPolicy({scroll_v_policy})

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(10)

        scroll.setWidget(self.content_widget)
        main_layout.addWidget(scroll)

        # Create widgets from GUILDS tree
{self.indent(widget_code, 8)}

        # Add stretch at end
        self.content_layout.addStretch()

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    @{slot_decorator}(object)
    def change_phase(self, new_phase: Phase):
        """Change the current phase and update visibility."""
        if isinstance(new_phase, str):
            new_phase = Phase(new_phase)

        old_phase = self.current_phase
        self.current_phase = new_phase

        # Update phase label
        self.phase_label.setText(f"Phase: {{new_phase.value.upper()}}")
        self.setWindowTitle(f"{{self.base_title}} - {{new_phase.value}}")

        # Update phase buttons
        for phase in Phase:
            btn_name = f"phase_btn_{{phase.value}}"
            if btn_name in self.widgets:
                self.widgets[btn_name].setChecked(phase == new_phase)

        self._apply_phase_state()

        # Update stylesheet with new accent colour
        accent = PHASE_COLOURS.get(new_phase.value, "#3b82f6")
        # Note: For full theme update, would need to regenerate stylesheet

        # Emit signal
        self.phase_changed.emit(new_phase.value)

    def _set_widget_visibility(self, widget: QWidget, state: str):
        """Apply render/fade/hide semantics to a widget."""
        effect = widget.graphicsEffect()
        if effect and not isinstance(effect, QGraphicsOpacityEffect):
            widget.setGraphicsEffect(None)
            effect = None

        if state == "hide":
            widget.hide()
            return

        widget.show()

        if state == "fade":
            opacity = effect if isinstance(effect, QGraphicsOpacityEffect) else QGraphicsOpacityEffect(widget)
            opacity.setOpacity(0.42)
            widget.setGraphicsEffect(opacity)
            widget.setEnabled(False)
        else:
            if isinstance(effect, QGraphicsOpacityEffect):
                effect.setOpacity(1.0)
                widget.setGraphicsEffect(effect)
            else:
                widget.setGraphicsEffect(None)
            widget.setEnabled(True)

    def _apply_phase_state(self):
        """Apply stage-managed visibility/dominance for the active phase."""
        phase_key = self.current_phase.value
        states = self.phase_visibility.get(phase_key, {{}})
        dominant = self.phase_dominant.get(phase_key)

        for widget_key, state in states.items():
            widget = self.widgets.get(widget_key)
            if widget is None:
                continue
            self._set_widget_visibility(widget, state)
            if widget_key.startswith("vessel_"):
                widget.setProperty("dominant", widget_key == dominant and state != "hide")
                widget.style().unpolish(widget)
                widget.style().polish(widget)

    def set_claim(self, name: str, value: Any, certainty: str = "unknown"):
        """Update a claim's value and certainty."""
        attr_name = f"claim_{{name}}"
        if hasattr(self, attr_name):
            claim = getattr(self, attr_name)
            claim.value = value
            claim.certainty = certainty

            # Update widget if exists
            widget_name = f"claim_{{name}}_value"
            if widget_name in self.widgets:
                widget = self.widgets[widget_name]
                widget.setText(str(value))
                widget.setProperty("certainty", certainty)
                widget.style().unpolish(widget)
                widget.style().polish(widget)

            # Emit signal
            self.claim_updated.emit(name, value, certainty)

    def trigger_action(self, action_name: str, data: dict = None):
        """Programmatically trigger an action."""
        self.action_triggered.emit(action_name, data or {{}})

    def inject_failure(self, vessel_name: str, kind: str, cause: str = ""):
        """Inject a failure state into a vessel."""
        frame_name = f"vessel_{{vessel_name}}"
        if frame_name in self.frames:
            frame = self.frames[frame_name]
            frame.setProperty("failure", True)
            frame.style().unpolish(frame)
            frame.style().polish(frame)

            # Add failure label
            layout = frame.layout()
            if layout:
                failure_label = QLabel(f"[FAILURE] {{kind}}: {{cause}}")
                failure_label.setStyleSheet("color: #ef4444; font-weight: bold;")
                layout.insertWidget(0, failure_label)
                self.widgets[f"{{vessel_name}}_failure"] = failure_label

    def clear_failure(self, vessel_name: str):
        """Clear a failure state from a vessel."""
        frame_name = f"vessel_{{vessel_name}}"
        if frame_name in self.frames:
            frame = self.frames[frame_name]
            frame.setProperty("failure", False)
            frame.style().unpolish(frame)
            frame.style().polish(frame)

            # Remove failure label
            failure_key = f"{{vessel_name}}_failure"
            if failure_key in self.widgets:
                self.widgets[failure_key].deleteLater()
                del self.widgets[failure_key]

    def start_flow(self, flow_name: str):
        """Start animating a flow's progress bar."""
        progress_name = f"flow_{{flow_name}}_progress"
        if progress_name in self.widgets:
            progress = self.widgets[progress_name]
            progress.setValue(0)

            timer = QTimer(self)
            timer.timeout.connect(lambda: self._update_flow(flow_name))
            timer.start(50)
            self.flow_timers[flow_name] = timer

    def stop_flow(self, flow_name: str, terminal: str = "success"):
        """Stop a flow animation."""
        if flow_name in self.flow_timers:
            self.flow_timers[flow_name].stop()
            del self.flow_timers[flow_name]

        progress_name = f"flow_{{flow_name}}_progress"
        if progress_name in self.widgets:
            progress = self.widgets[progress_name]
            progress.setValue(100 if terminal == "success" else 0)

    def _update_flow(self, flow_name: str):
        """Update flow progress animation."""
        progress_name = f"flow_{{flow_name}}_progress"
        if progress_name in self.widgets:
            progress = self.widgets[progress_name]
            value = (progress.value() + 2) % 100
            progress.setValue(value)

    # -------------------------------------------------------------------------
    # Action handlers
    # -------------------------------------------------------------------------

    def _handle_action(self, action_name: str):
        """Internal action handler."""
        self.action_triggered.emit(action_name, {{"phase": self.current_phase.value}})
'''

    def _generate_all_widgets(self, tree: RenderTree) -> str:
        """Generate widget creation code for all nodes."""
        lines = []
        for i, root in enumerate(tree.roots):
            lines.append(self._generate_widget_code(root, "self.content_layout", 0))
        return "\n\n".join(lines)

    def _generate_widget_code(self, node: RenderNode, parent: str, depth: int) -> str:
        """Generate widget creation code for a single node."""
        var_name = self.sanitize_identifier(node.name)
        kind = node.kind.lower()

        lines = []

        if kind == "vessel":
            lines.append(self._generate_vessel(node, parent, var_name))
            child_parent = f"layout_{var_name}"
            for child in node.children:
                lines.append(self._generate_widget_code(child, child_parent, depth))

        elif kind == "stage":
            lines.append(self._generate_stage(node, parent, var_name))
            child_parent = f"layout_{var_name}"
            for child in node.children:
                lines.append(self._generate_widget_code(child, child_parent, depth))

        elif kind == "claim":
            lines.append(self._generate_claim(node, parent, var_name))

        elif kind == "afford":
            lines.append(self._generate_affordance(node, parent, var_name))

        elif kind == "flow":
            lines.append(self._generate_flow(node, parent, var_name))

        elif kind == "failure":
            lines.append(self._generate_failure(node, parent, var_name))

        return "\n".join(lines)

    def _generate_vessel(self, node: RenderNode, parent: str, var_name: str) -> str:
        dominant = "True" if node.style.is_dominant else "False"
        label = self.escape_string(self.humanize_label(node.label, "vessel"))
        layout_class = "QHBoxLayout" if node.arrangement_kind == "row" else "QVBoxLayout"
        return f'''
# Vessel: {node.name}
frame_{var_name} = QGroupBox("{label}")
frame_{var_name}.setProperty("dominant", {dominant})
layout_{var_name} = {layout_class}(frame_{var_name})
layout_{var_name}.setSpacing(8)
{parent}.addWidget(frame_{var_name})
self._set_widget_visibility(frame_{var_name}, "{node.visibility}")
self.frames["vessel_{var_name}"] = frame_{var_name}
self.widgets["vessel_{var_name}"] = frame_{var_name}
'''

    def _generate_stage(self, node: RenderNode, parent: str, var_name: str) -> str:
        label = self.escape_string(self.humanize_label(node.label, "stage"))
        layout_class = "QHBoxLayout" if node.arrangement_kind == "row" else "QVBoxLayout"
        return f'''
# Stage: {node.name}
frame_{var_name} = QGroupBox("{label}")
layout_{var_name} = {layout_class}(frame_{var_name})
layout_{var_name}.setSpacing(8)
{parent}.addWidget(frame_{var_name})
self._set_widget_visibility(frame_{var_name}, "{node.visibility}")
self.frames["stage_{var_name}"] = frame_{var_name}
self.widgets["stage_{var_name}"] = frame_{var_name}
'''

    def _generate_claim(self, node: RenderNode, parent: str, var_name: str) -> str:
        certainty = node.certainty.grade if node.certainty else "unknown"
        symbol = CERTAINTY_STYLE.get(certainty, CERTAINTY_STYLE["unknown"])[1]
        label = self.escape_string(self.humanize_label(node.label, "claim"))

        return f'''
# Claim: {node.name}
claim_frame_{var_name} = QFrame()
claim_layout_{var_name} = QHBoxLayout(claim_frame_{var_name})
claim_layout_{var_name}.setContentsMargins(0, 0, 0, 0)

claim_symbol_{var_name} = QLabel("{symbol}")
claim_symbol_{var_name}.setProperty("certainty", "{certainty}")
claim_symbol_{var_name}.setFixedWidth(30)
claim_layout_{var_name}.addWidget(claim_symbol_{var_name})

claim_name_{var_name} = QLabel("{label}:")
claim_name_{var_name}.setStyleSheet("font-weight: bold;")
claim_layout_{var_name}.addWidget(claim_name_{var_name})

claim_value_{var_name} = QLabel("(no value)")
claim_value_{var_name}.setProperty("certainty", "{certainty}")
claim_layout_{var_name}.addWidget(claim_value_{var_name})

claim_layout_{var_name}.addStretch()

{parent}.addWidget(claim_frame_{var_name})
self._set_widget_visibility(claim_frame_{var_name}, "{node.visibility}")
self.widgets["claim_{var_name}"] = claim_frame_{var_name}
self.widgets["claim_{var_name}_value"] = claim_value_{var_name}
'''

    def _generate_affordance(self, node: RenderNode, parent: str, var_name: str) -> str:
        label = self.escape_string(self.humanize_label(node.label, "afford"))
        return f'''
# Affordance: {node.name}
btn_{var_name} = QPushButton("{label}")
btn_{var_name}.clicked.connect(lambda: self._handle_action("{node.name}"))
{parent}.addWidget(btn_{var_name})
self._set_widget_visibility(btn_{var_name}, "{node.visibility}")
self.widgets["afford_{var_name}"] = btn_{var_name}
'''

    def _generate_flow(self, node: RenderNode, parent: str, var_name: str) -> str:
        label = self.escape_string(self.humanize_label(node.name, "flow"))
        return f'''
# Flow: {node.name}
flow_frame_{var_name} = QFrame()
flow_layout_{var_name} = QHBoxLayout(flow_frame_{var_name})
flow_layout_{var_name}.setContentsMargins(0, 0, 0, 0)

flow_label_{var_name} = QLabel("Flow: {label}")
flow_layout_{var_name}.addWidget(flow_label_{var_name})

flow_progress_{var_name} = QProgressBar()
flow_progress_{var_name}.setTextVisible(False)
flow_progress_{var_name}.setFixedHeight(4)
flow_progress_{var_name}.setValue(0)
flow_layout_{var_name}.addWidget(flow_progress_{var_name})

{parent}.addWidget(flow_frame_{var_name})
self._set_widget_visibility(flow_frame_{var_name}, "{node.visibility}")
self.widgets["flow_{var_name}"] = flow_frame_{var_name}
self.widgets["flow_{var_name}_progress"] = flow_progress_{var_name}
'''

    def _generate_failure(self, node: RenderNode, parent: str, var_name: str) -> str:
        label = self.escape_string(self.humanize_label(node.label, "failure"))
        return f'''
# Failure indicator: {node.name}
failure_frame_{var_name} = QGroupBox("{label}")
failure_frame_{var_name}.setProperty("failure", True)
failure_layout_{var_name} = QVBoxLayout(failure_frame_{var_name})

failure_msg_{var_name} = QLabel("{node.subtitle or 'Failure active'}")
failure_msg_{var_name}.setStyleSheet("color: #ef4444; font-weight: bold;")
failure_layout_{var_name}.addWidget(failure_msg_{var_name})

{parent}.addWidget(failure_frame_{var_name})
self._set_widget_visibility(failure_frame_{var_name}, "{node.visibility}")
self.widgets["failure_{var_name}"] = failure_frame_{var_name}
'''

    def _generate_main(self, app_name: str) -> str:
        exec_method = self._get_exec_method()
        return f'''
# ---------------------------------------------------------------------------
# MAIN ENTRY POINT
# ---------------------------------------------------------------------------

def main():
    app = QApplication(sys.argv)

    # Set application attributes
    app.setStyle("Fusion")

    # Create and show window
    window = {app_name}()

    # Example: Connect signals
    window.action_triggered.connect(
        lambda name, data: print(f"Action: {{name}}, Data: {{data}}")
    )
    window.phase_changed.connect(
        lambda phase: print(f"Phase changed to: {{phase}}")
    )

    window.show()
    sys.exit(app.{exec_method}())


if __name__ == "__main__":
    main()
'''


# ---------------------------------------------------------------------------
# Convenience renderer classes for each binding
# ---------------------------------------------------------------------------

class PyQt5Renderer(QtRenderer):
    """PyQt5 renderer."""
    def __init__(self):
        super().__init__(QtBinding.PYQT5)

    def output_files(self, base_name: str) -> list[str]:
        return ["guilds_app_pyqt5.py"]


class PyQt6Renderer(QtRenderer):
    """PyQt6 renderer."""
    def __init__(self):
        super().__init__(QtBinding.PYQT6)

    def output_files(self, base_name: str) -> list[str]:
        return ["guilds_app_pyqt6.py"]


class PySide6Renderer(QtRenderer):
    """PySide6 renderer."""
    def __init__(self):
        super().__init__(QtBinding.PYSIDE6)

    def output_files(self, base_name: str) -> list[str]:
        return ["guilds_app_pyside6.py"]


# Backward compatibility alias
PyQtRenderer = PyQt5Renderer

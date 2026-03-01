"""
GUILDS v2 Tkinter Renderer
==========================
Renders RenderTree to standalone Python tkinter applications.

Features:
  - Generates single .py file with all dependencies
  - Uses ttk for modern styling
  - Phase system via frame visibility
  - Certainty grades mapped to font styles/colours
  - Failure states mapped to widget states and styling
  - Flow animations with after() callbacks

Widget mappings:
  Vessel       -> ttk.LabelFrame
  Claim (text) -> ttk.Label
  Affordance   -> ttk.Button / ttk.Entry / ttk.Combobox
  Stage        -> ttk.Notebook or dynamic frame switching
  Flow         -> Animated progress with after()
"""

from __future__ import annotations

from typing import Optional

from .base import (
    BaseRenderer, RenderTree, RenderNode, RenderStyle,
    CERTAINTY_STYLE, FAILURE_STYLE, PHASE_COLOUR,
)
from guilds_evaluator import (
    ResolvedCertainty, FlowState, ActiveFailure,
    PHASE_NAMES, FAILURE_NAMES,
)


class TkinterRenderer(BaseRenderer):
    """
    Generates standalone Python tkinter application from a RenderTree.
    """

    def file_extension(self) -> str:
        return ".py"

    def output_files(self, base_name: str) -> list[str]:
        return [f"guilds_app_tk.py"]

    def render(self, tree: RenderTree, app_name: str = "GuildsApp", **kwargs) -> str:
        """Generate complete tkinter application code."""
        app_name = self.sanitize_identifier(app_name)

        # Collect all names for generating class attributes
        names = self.collect_all_names(tree)

        # Generate code sections
        imports = self._generate_imports()
        constants = self._generate_constants(tree)
        app_class = self._generate_app_class(tree, app_name, names)
        main = self._generate_main(app_name)

        return f'''{imports}

{constants}

{app_class}

{main}
'''

    def render_node(self, node: RenderNode, depth: int = 0) -> str:
        """Render a single node - used internally."""
        return self._generate_widget_code(node, "self.main_frame", depth)

    # -------------------------------------------------------------------------
    # Code generation methods
    # -------------------------------------------------------------------------

    def _generate_imports(self) -> str:
        return '''#!/usr/bin/env python3
"""
GUILDS-generated Tkinter Application
=====================================
Auto-generated from GUILDS specification.

Dependencies: Python 3.10+ (tkinter is included in standard library)
"""

import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import dataclass, field
from typing import Callable, Optional, Any
from enum import Enum
import time
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

    def _generate_app_class(self, tree: RenderTree, app_name: str,
                            names: dict[str, list[str]]) -> str:
        """Generate the main application class."""

        # Generate widget creation code
        widget_code = self._generate_all_widgets(tree)

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

        # Generate phase visibility mappings from tree
        phase_visibility = self._generate_phase_visibility(tree)

        return f'''
# ---------------------------------------------------------------------------
# APPLICATION CLASS
# ---------------------------------------------------------------------------

class {app_name}(tk.Tk):
    """GUILDS-generated tkinter application."""

    def __init__(self):
        super().__init__()

        self.title("GUILDS Application - {tree.phase_name}")
        self.geometry("900x700")
        self.configure(bg="#0a0e1a")

        # Phase state
        self.current_phase = Phase.{tree.phase_name.upper()}

        # Event callbacks (set by external programs)
        self.on_action: Optional[Callable[[str, dict], None]] = None
        self.on_phase_change: Optional[Callable[[Phase], None]] = None

        # Claim data
{claim_attrs if claim_attrs else "        pass  # No claims"}

        # Flow data
{flow_attrs if flow_attrs else "        pass  # No flows"}

        # Widget references
        self.widgets: dict[str, tk.Widget] = {{}}
        self.frames: dict[str, ttk.Frame] = {{}}

        # Setup styling
        self._setup_styles()

        # Create UI
        self._create_ui()

        # Apply initial phase visibility
        self._apply_phase_visibility()

    def _setup_styles(self):
        """Configure ttk styles for GUILDS appearance."""
        style = ttk.Style()
        style.theme_use("clam")

        # Dark theme colours
        bg_deep = "#0a0e1a"
        bg_mid = "#0f172a"
        bg_surface = "#111827"
        fg_primary = "#f1f5f9"
        fg_secondary = "#94a3b8"
        accent = PHASE_COLOURS.get(self.current_phase.value, "#3b82f6")

        # Frame styles
        style.configure("Guilds.TFrame",
                       background=bg_surface)

        style.configure("Vessel.TLabelframe",
                       background=bg_surface,
                       foreground=fg_primary,
                       borderwidth=2,
                       relief="solid")
        style.configure("Vessel.TLabelframe.Label",
                       background=bg_surface,
                       foreground=accent,
                       font=("JetBrains Mono", 10, "bold"))

        style.configure("Dominant.TLabelframe",
                       background="#0f1f3d",
                       borderwidth=3)
        style.configure("Dominant.TLabelframe.Label",
                       background="#0f1f3d",
                       foreground=accent,
                       font=("JetBrains Mono", 11, "bold"))

        # Label styles
        style.configure("Claim.TLabel",
                       background=bg_surface,
                       foreground=fg_primary,
                       font=("Inter", 10))

        style.configure("ClaimCertain.TLabel",
                       foreground="#22c55e")
        style.configure("ClaimInferred.TLabel",
                       foreground="#3b82f6")
        style.configure("ClaimProbable.TLabel",
                       foreground="#f59e0b")
        style.configure("ClaimStale.TLabel",
                       foreground="#f97316")
        style.configure("ClaimUnknown.TLabel",
                       foreground="#6b7280")
        style.configure("ClaimContested.TLabel",
                       foreground="#ef4444")

        # Button styles
        style.configure("Action.TButton",
                       background="#1e293b",
                       foreground=fg_primary,
                       font=("Inter", 10),
                       padding=(10, 5))
        style.map("Action.TButton",
                 background=[("active", "#334155"), ("disabled", "#0f172a")],
                 foreground=[("disabled", "#475569")])

        # Header styles
        style.configure("Header.TFrame",
                       background=bg_mid)
        style.configure("Phase.TLabel",
                       background=bg_mid,
                       foreground=accent,
                       font=("JetBrains Mono", 12, "bold"))
        style.configure("Meta.TLabel",
                       background=bg_mid,
                       foreground=fg_secondary,
                       font=("JetBrains Mono", 9))

        # Failure styles
        style.configure("Failure.TLabelframe",
                       background="#1c0a0a",
                       borderwidth=3)
        style.configure("Failure.TLabelframe.Label",
                       background="#1c0a0a",
                       foreground="#ef4444",
                       font=("JetBrains Mono", 10, "bold"))

    def _create_ui(self):
        """Create the main UI structure."""
        # Header
        self.header = ttk.Frame(self, style="Header.TFrame")
        self.header.pack(fill="x", padx=10, pady=10)

        phase_label = ttk.Label(self.header,
                               text=f"Phase: {{self.current_phase.value.upper()}}",
                               style="Phase.TLabel")
        phase_label.pack(side="left", padx=10)
        self.widgets["phase_label"] = phase_label

        meta_label = ttk.Label(self.header,
                              text=f"LW = {tree.lambda_omega:.1f}",
                              style="Meta.TLabel")
        meta_label.pack(side="left", padx=10)

        # Phase selector
        phase_frame = ttk.Frame(self.header, style="Header.TFrame")
        phase_frame.pack(side="right", padx=10)

        for phase in Phase:
            btn = ttk.Button(phase_frame,
                            text=phase.value,
                            style="Action.TButton",
                            command=lambda p=phase: self.change_phase(p))
            btn.pack(side="left", padx=2)
            self.widgets[f"phase_btn_{{phase.value}}"] = btn

        # Main content area
        self.main_frame = ttk.Frame(self, style="Guilds.TFrame")
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Create widgets from GUILDS tree
{self.indent(widget_code, 8)}

    def _apply_phase_visibility(self):
        """Apply visibility based on current phase."""
{self.indent(phase_visibility, 8)}

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def change_phase(self, new_phase: Phase):
        """Change the current phase and update visibility."""
        old_phase = self.current_phase
        self.current_phase = new_phase

        # Update header
        if "phase_label" in self.widgets:
            self.widgets["phase_label"].configure(
                text=f"Phase: {{new_phase.value.upper()}}"
            )

        # Update accent colour
        self._setup_styles()

        # Apply visibility
        self._apply_phase_visibility()

        # Callback
        if self.on_phase_change:
            self.on_phase_change(new_phase)

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
                widget.configure(text=str(value))

                # Update style based on certainty
                style_name = f"Claim{{certainty.title()}}.TLabel"
                try:
                    widget.configure(style=style_name)
                except tk.TclError:
                    pass

    def trigger_action(self, action_name: str, data: dict = None):
        """Programmatically trigger an action."""
        if self.on_action:
            self.on_action(action_name, data or {{}})

    def inject_failure(self, vessel_name: str, kind: str, cause: str = ""):
        """Inject a failure state into a vessel."""
        frame_name = f"vessel_{{vessel_name}}"
        if frame_name in self.frames:
            frame = self.frames[frame_name]
            frame.configure(style="Failure.TLabelframe")
            # Add failure indicator
            failure_label = ttk.Label(frame,
                                     text=f"[FAILURE] {{kind}}: {{cause}}",
                                     foreground="#ef4444",
                                     background="#1c0a0a")
            failure_label.pack(anchor="w", pady=2)
            self.widgets[f"{{vessel_name}}_failure"] = failure_label

    def clear_failure(self, vessel_name: str):
        """Clear a failure state from a vessel."""
        frame_name = f"vessel_{{vessel_name}}"
        if frame_name in self.frames:
            frame = self.frames[frame_name]
            frame.configure(style="Vessel.TLabelframe")

            failure_key = f"{{vessel_name}}_failure"
            if failure_key in self.widgets:
                self.widgets[failure_key].destroy()
                del self.widgets[failure_key]

    # -------------------------------------------------------------------------
    # Action handlers (override these or use callbacks)
    # -------------------------------------------------------------------------

    def _handle_action(self, action_name: str):
        """Internal action handler."""
        if self.on_action:
            self.on_action(action_name, {{"phase": self.current_phase.value}})
        else:
            print(f"[GUILDS] Action: {{action_name}}")
'''

    def _generate_all_widgets(self, tree: RenderTree) -> str:
        """Generate widget creation code for all nodes."""
        lines = []
        for i, root in enumerate(tree.roots):
            lines.append(self._generate_widget_code(root, "self.main_frame", 0))
        return "\n\n".join(lines)

    def _generate_widget_code(self, node: RenderNode, parent: str, depth: int) -> str:
        """Generate widget creation code for a single node."""
        if node.visibility == "hide":
            return f"# Hidden: {node.name}"

        indent = "    " * depth
        var_name = self.sanitize_identifier(node.name)
        kind = node.kind.lower()

        lines = []

        if kind == "vessel":
            lines.append(self._generate_vessel(node, parent, var_name))
            child_parent = f"self.frames['vessel_{var_name}']"
            for child in node.children:
                lines.append(self._generate_widget_code(child, child_parent, depth))

        elif kind == "stage":
            lines.append(self._generate_stage(node, parent, var_name))
            child_parent = f"self.frames['stage_{var_name}']"
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
        style = "Dominant.TLabelframe" if node.style.is_dominant else "Vessel.TLabelframe"
        return f'''
# Vessel: {node.name}
frame_{var_name} = ttk.LabelFrame({parent},
                                  text="{node.label}",
                                  style="{style}")
frame_{var_name}.pack(fill="both", expand=True, padx=5, pady=5)
self.frames["vessel_{var_name}"] = frame_{var_name}
self.widgets["vessel_{var_name}"] = frame_{var_name}
'''

    def _generate_stage(self, node: RenderNode, parent: str, var_name: str) -> str:
        return f'''
# Stage: {node.name}
frame_{var_name} = ttk.LabelFrame({parent},
                                  text="{node.label} (stage)",
                                  style="Vessel.TLabelframe")
frame_{var_name}.pack(fill="both", expand=True, padx=5, pady=5)
self.frames["stage_{var_name}"] = frame_{var_name}
self.widgets["stage_{var_name}"] = frame_{var_name}
'''

    def _generate_claim(self, node: RenderNode, parent: str, var_name: str) -> str:
        certainty = node.certainty.grade if node.certainty else "unknown"
        symbol = CERTAINTY_STYLE.get(certainty, CERTAINTY_STYLE["unknown"])[1]
        style_name = f"Claim{certainty.title()}.TLabel"

        return f'''
# Claim: {node.name}
claim_frame_{var_name} = ttk.Frame({parent}, style="Guilds.TFrame")
claim_frame_{var_name}.pack(fill="x", padx=5, pady=2)

claim_symbol_{var_name} = ttk.Label(claim_frame_{var_name},
                                    text="{symbol}",
                                    style="{style_name}")
claim_symbol_{var_name}.pack(side="left", padx=(0, 5))

claim_name_{var_name} = ttk.Label(claim_frame_{var_name},
                                  text="{node.label}:",
                                  style="Claim.TLabel")
claim_name_{var_name}.pack(side="left")

claim_value_{var_name} = ttk.Label(claim_frame_{var_name},
                                   text="(no value)",
                                   style="{style_name}")
claim_value_{var_name}.pack(side="left", padx=(5, 0))

self.widgets["claim_{var_name}"] = claim_frame_{var_name}
self.widgets["claim_{var_name}_value"] = claim_value_{var_name}
'''

    def _generate_affordance(self, node: RenderNode, parent: str, var_name: str) -> str:
        return f'''
# Affordance: {node.name}
btn_{var_name} = ttk.Button({parent},
                            text="{node.label}",
                            style="Action.TButton",
                            command=lambda: self._handle_action("{node.name}"))
btn_{var_name}.pack(pady=5)
self.widgets["afford_{var_name}"] = btn_{var_name}
'''

    def _generate_flow(self, node: RenderNode, parent: str, var_name: str) -> str:
        return f'''
# Flow: {node.name}
flow_frame_{var_name} = ttk.Frame({parent}, style="Guilds.TFrame")
flow_frame_{var_name}.pack(fill="x", padx=5, pady=2)

flow_label_{var_name} = ttk.Label(flow_frame_{var_name},
                                  text="Flow: {node.name}",
                                  style="Claim.TLabel")
flow_label_{var_name}.pack(side="left")

flow_progress_{var_name} = ttk.Progressbar(flow_frame_{var_name},
                                           mode="indeterminate",
                                           length=100)
flow_progress_{var_name}.pack(side="left", padx=10)

self.widgets["flow_{var_name}"] = flow_frame_{var_name}
self.widgets["flow_{var_name}_progress"] = flow_progress_{var_name}
'''

    def _generate_failure(self, node: RenderNode, parent: str, var_name: str) -> str:
        return f'''
# Failure indicator: {node.name}
failure_frame_{var_name} = ttk.LabelFrame({parent},
                                          text="{node.label}",
                                          style="Failure.TLabelframe")
failure_frame_{var_name}.pack(fill="x", padx=5, pady=5)

failure_msg_{var_name} = ttk.Label(failure_frame_{var_name},
                                   text="{node.subtitle or 'Failure active'}",
                                   foreground="#ef4444")
failure_msg_{var_name}.pack(padx=5, pady=5)

self.widgets["failure_{var_name}"] = failure_frame_{var_name}
'''

    def _generate_phase_visibility(self, tree: RenderTree) -> str:
        """Generate phase visibility logic."""
        # For now, generate basic visibility based on tree structure
        return '''
# Phase visibility is managed by showing/hiding frames
# Override this method for custom phase logic
for name, frame in self.frames.items():
    try:
        frame.pack(fill="both", expand=True, padx=5, pady=5)
    except tk.TclError:
        pass  # Already packed or not packable
'''

    def _generate_main(self, app_name: str) -> str:
        return f'''
# ---------------------------------------------------------------------------
# MAIN ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = {app_name}()

    # Example: Set up action handler
    def handle_action(name: str, data: dict):
        print(f"Action triggered: {{name}}")
        print(f"  Data: {{data}}")

    app.on_action = handle_action

    # Example: Set up phase change handler
    def handle_phase_change(phase: Phase):
        print(f"Phase changed to: {{phase.value}}")

    app.on_phase_change = handle_phase_change

    # Run the application
    app.mainloop()
'''

"""
GUILDS v2 Base Renderer
=======================
Abstract base class for all GUILDS renderers.

Provides common abstractions for:
  - Style mapping (certainty grades, failure states, weights)
  - Phase transition logic generation
  - Common render tree traversal patterns

All concrete renderers (HTML, tkinter, PyQt, Qt C++, ImGui) inherit from this.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

# Import types from renderer module
from guilds_evaluator import (
    ResolvedCertainty, FlowState, ActiveFailure,
    PHASE_NAMES, FAILURE_NAMES,
)
from guilds_parser import TT


# ---------------------------------------------------------------------------
# STYLE CONSTANTS (shared across all renderers)
# ---------------------------------------------------------------------------

# Certainty grade -> (colour_hex, symbol, label)
CERTAINTY_STYLE: dict[str, tuple[str, str, str]] = {
    "certain":   ("#22c55e", "T+", "certain"),
    "inferred":  ("#3b82f6", "T~", "inferred"),
    "probable":  ("#f59e0b", "T?", "probable"),
    "stale":     ("#f97316", "T*", "stale"),
    "unknown":   ("#6b7280", "T0", "unknown"),
    "contested": ("#ef4444", "T!", "contested"),
    "composite": ("#a78bfa", "Tc", "composite"),
    "ref":       ("#6b7280", "T?", "ref"),
}

# Stakes -> border width multiplier
STAKES_STYLE: dict[str, float] = {
    "low":              1.0,
    "medium":           1.5,
    "high":             2.0,
    "critical":         3.0,
    "context_dependent": 1.0,
}

# Weight -> (flex_grow, opacity)
WEIGHT_STYLE: dict[str, tuple[float, float]] = {
    "primary":    (3.0, 1.00),
    "secondary":  (2.0, 0.85),
    "tertiary":   (1.0, 0.65),
    "background": (0.5, 0.45),
    "hidden":     (0.0, 0.00),
}

# Failure kind -> (colour_hex, symbol, severity_label)
FAILURE_STYLE: dict[TT, tuple[str, str, str]] = {
    TT.PHI_DEGRADED: ("#f59e0b", "P-", "degraded"),
    TT.PHI_BLOCKED:  ("#ef4444", "P|", "blocked"),
    TT.PHI_LOST:     ("#6b7280", "P0", "lost"),
    TT.PHI_PARTIAL:  ("#f97316", "P/", "partial"),
    TT.PHI_STALE:    ("#f59e0b", "P*", "stale"),
    TT.PHI_RECOVER:  ("#3b82f6", "P>", "recovering"),
    TT.PHI_CASCADE:  ("#a78bfa", "P>", "cascade"),
    TT.PHI_UNKNOWN:  ("#6b7280", "P?", "unknown"),
    TT.PHI_FATAL:    ("#dc2626", "PX", "FATAL"),
    TT.PHI_SILENT:   ("#dc2626", "P-", "SILENT_VIOLATION"),
}

# Phase colours
PHASE_COLOUR: dict[str, str] = {
    "orient":    "#8b5cf6",
    "execute":   "#3b82f6",
    "verify":    "#22c55e",
    "integrate": "#14b8a6",
    "recover":   "#f97316",
    "idle":      "#6b7280",
}


# ---------------------------------------------------------------------------
# RENDER NODE (backend-agnostic)
# ---------------------------------------------------------------------------

@dataclass
class RenderStyle:
    """Fully resolved visual style for a node, backend-agnostic."""
    opacity:       float      = 1.0
    flex_grow:     float      = 1.0
    font_weight:   int        = 400
    font_size_em:  float      = 1.0
    border_px:     int        = 1
    border_colour: str        = "#374151"
    bg_colour:     str        = "#111827"
    fg_colour:     str        = "#f9fafb"
    accent_colour: str        = "#3b82f6"
    is_dominant:   bool       = False
    is_anchor:     bool       = False
    is_stalled:    bool       = False
    has_failure:   bool       = False
    failure_colour: str       = ""
    axis:          str        = "column"
    gap_em:        float      = 0.75


@dataclass
class RenderNode:
    """One node in the render tree, fully backend-agnostic."""
    name:           str
    kind:           str  # "vessel", "claim", "afford", "stage", "flow", "failure", "spacer"
    visibility:     str  # "render", "fade", "hide"
    style:          RenderStyle
    label:          str
    subtitle:       Optional[str]
    certainty:      Optional[ResolvedCertainty]
    flow_state:     Optional[FlowState]
    active_failure: Optional[ActiveFailure]
    children:       list["RenderNode"]
    meta:           dict[str, Any]
    arrangement_kind: str = "column"

    def is_visible(self) -> bool:
        return self.visibility in ("render", "fade")


@dataclass
class RenderTree:
    """Top-level render tree. One or more root nodes."""
    roots:          list[RenderNode]
    phase:          str
    phase_name:     str
    phase_colour:   str
    lambda_omega:   float
    budget_warnings: list[str]
    symbol_errors:  list[str]
    active_failures: list[ActiveFailure]


# ---------------------------------------------------------------------------
# ABSTRACT BASE RENDERER
# ---------------------------------------------------------------------------

class BaseRenderer(ABC):
    """
    Abstract base class for all GUILDS renderers.

    Subclasses must implement:
      - render(tree: RenderTree) -> str
      - render_node(node: RenderNode) -> str

    Common helper methods are provided for style mapping.
    """

    @abstractmethod
    def render(self, tree: RenderTree, **kwargs) -> str:
        """
        Render a complete RenderTree to the target format.

        Args:
            tree: The RenderTree to render
            **kwargs: Backend-specific options

        Returns:
            The rendered output as a string (code, markup, etc.)
        """
        pass

    @abstractmethod
    def render_node(self, node: RenderNode, depth: int = 0) -> str:
        """
        Render a single RenderNode.

        Args:
            node: The RenderNode to render
            depth: Nesting depth for indentation

        Returns:
            The rendered node as a string
        """
        pass

    @abstractmethod
    def file_extension(self) -> str:
        """Return the primary file extension for this renderer (e.g., '.html', '.py')."""
        pass

    @abstractmethod
    def output_files(self, base_name: str) -> list[str]:
        """
        Return list of output file names this renderer will produce.

        Args:
            base_name: The base name for output files (from spec name)

        Returns:
            List of file paths relative to output directory
        """
        pass

    # -------------------------------------------------------------------------
    # Common style mapping methods
    # -------------------------------------------------------------------------

    def map_certainty_colour(self, certainty: Optional[ResolvedCertainty]) -> str:
        """Map certainty grade to a colour hex value."""
        if certainty is None:
            return CERTAINTY_STYLE["unknown"][0]
        return CERTAINTY_STYLE.get(certainty.grade, CERTAINTY_STYLE["unknown"])[0]

    def map_certainty_symbol(self, certainty: Optional[ResolvedCertainty]) -> str:
        """Map certainty grade to a display symbol."""
        if certainty is None:
            return CERTAINTY_STYLE["unknown"][1]
        return CERTAINTY_STYLE.get(certainty.grade, CERTAINTY_STYLE["unknown"])[1]

    def map_certainty_label(self, certainty: Optional[ResolvedCertainty]) -> str:
        """Map certainty grade to a text label."""
        if certainty is None:
            return "unknown"
        return CERTAINTY_STYLE.get(certainty.grade, CERTAINTY_STYLE["unknown"])[2]

    def map_failure_colour(self, failure: Optional[ActiveFailure]) -> str:
        """Map failure kind to a colour hex value."""
        if failure is None:
            return "#6b7280"
        return FAILURE_STYLE.get(failure.kind, FAILURE_STYLE[TT.PHI_UNKNOWN])[0]

    def map_failure_symbol(self, failure: Optional[ActiveFailure]) -> str:
        """Map failure kind to a display symbol."""
        if failure is None:
            return ""
        return FAILURE_STYLE.get(failure.kind, FAILURE_STYLE[TT.PHI_UNKNOWN])[1]

    def map_failure_label(self, failure: Optional[ActiveFailure]) -> str:
        """Map failure kind to a text label."""
        if failure is None:
            return ""
        return FAILURE_STYLE.get(failure.kind, FAILURE_STYLE[TT.PHI_UNKNOWN])[2]

    def map_phase_colour(self, phase_name: str) -> str:
        """Map phase name to a colour hex value."""
        return PHASE_COLOUR.get(phase_name, PHASE_COLOUR["idle"])

    def map_stakes_multiplier(self, stakes: str) -> float:
        """Map stakes level to border/emphasis multiplier."""
        return STAKES_STYLE.get(stakes, 1.0)

    def map_weight_style(self, weight: str) -> tuple[float, float]:
        """Map weight to (flex_grow, opacity) tuple."""
        return WEIGHT_STYLE.get(weight, WEIGHT_STYLE["secondary"])

    # -------------------------------------------------------------------------
    # Common utility methods
    # -------------------------------------------------------------------------

    def escape_string(self, s: str) -> str:
        """Escape a string for safe inclusion in generated code."""
        return (str(s)
                .replace("\\", "\\\\")
                .replace('"', '\\"')
                .replace("'", "\\'")
                .replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("\t", "\\t"))

    def sanitize_identifier(self, name: str) -> str:
        """
        Convert a GUILDS name to a valid identifier for the target language.
        Replaces invalid characters with underscores.
        """
        import re
        # Replace non-alphanumeric (except underscore) with underscore
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        # Ensure doesn't start with a number
        if sanitized and sanitized[0].isdigit():
            sanitized = '_' + sanitized
        return sanitized or '_unnamed'

    def humanize_label(self, name: str, kind: str = "") -> str:
        """
        Convert internal GUILDS identifiers into reasonable UI labels.
        Keeps concise calculator-friendly names where possible.
        """
        import re

        special = {
            "Add": "+",
            "Subtract": "-",
            "Multiply": "x",
            "Divide": "/",
            "Equals": "=",
            "Decimal": ".",
            "Negate": "+/-",
            "Clear": "C",
            "ClearEntry": "CE",
            "Percent": "%",
            "Power": "^",
            "MemoryStore": "MS",
            "MemoryRecall": "MR",
            "MemoryClear": "MC",
            "MemoryAdd": "M+",
            "MemorySubtract": "M-",
        }

        base = name
        for suffix in ("Afford", "Claim", "Vessel", "Panel", "Stage", "Flow"):
            if base.endswith(suffix):
                base = base[:-len(suffix)]
                break

        digit_match = re.fullmatch(r"(?:Digit|Key)(\d)", base)
        if digit_match:
            return digit_match.group(1)

        if base in special:
            return special[base]

        words = re.sub(r"(?<!^)([A-Z])", r" \1", base).replace("_", " ").strip()
        if not words:
            return name

        if kind == "afford" and len(words) <= 3:
            return words.upper()

        return words

    def hex_to_rgb(self, hex_colour: str) -> tuple[int, int, int]:
        """Convert hex colour (#RRGGBB) to RGB tuple."""
        hex_colour = hex_colour.lstrip('#')
        if len(hex_colour) == 3:
            hex_colour = ''.join(c*2 for c in hex_colour)
        try:
            return (
                int(hex_colour[0:2], 16),
                int(hex_colour[2:4], 16),
                int(hex_colour[4:6], 16),
            )
        except (ValueError, IndexError):
            return (128, 128, 128)  # Default grey

    def rgb_to_hex(self, r: int, g: int, b: int) -> str:
        """Convert RGB values to hex colour string."""
        return f"#{r:02x}{g:02x}{b:02x}"

    def indent(self, text: str, spaces: int = 4) -> str:
        """Indent all lines of text by the specified number of spaces."""
        prefix = ' ' * spaces
        return '\n'.join(prefix + line if line.strip() else line
                        for line in text.split('\n'))

    def generate_phase_constants(self) -> dict[str, str]:
        """Generate phase name to constant mapping for code generation."""
        return {
            "idle":      "PHASE_IDLE",
            "orient":    "PHASE_ORIENT",
            "execute":   "PHASE_EXECUTE",
            "verify":    "PHASE_VERIFY",
            "integrate": "PHASE_INTEGRATE",
            "recover":   "PHASE_RECOVER",
        }

    def collect_all_names(self, tree: RenderTree) -> dict[str, list[str]]:
        """
        Collect all names from the render tree by kind.

        Returns:
            Dict mapping kind to list of names
        """
        names: dict[str, list[str]] = {
            "vessel": [],
            "claim": [],
            "afford": [],
            "stage": [],
            "flow": [],
        }

        def collect_node(node: RenderNode):
            kind = node.kind.lower()
            if kind in names:
                names[kind].append(node.name)
            for child in node.children:
                collect_node(child)

        for root in tree.roots:
            collect_node(root)

        return names

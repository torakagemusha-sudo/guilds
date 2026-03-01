"""
GUILDS v2 Renderer
==================
Takes:   SurfaceModel + Evaluator  (from guilds_evaluator.py)
         Optional: TransitionPlan  (for animated phase changes)

Produces via three backends:
  RenderTree      — backend-agnostic layout intermediate representation
  TerminalRenderer — ANSI terminal with box-drawing, certainty sigils, flow indicators
  HTMLRenderer    — self-contained HTML/CSS document with live transitions,
                    certainty badges, failure overlays, flow state animations

Key mappings (GUILDS axioms → visual physics):
  display_weight  → font-weight, opacity, border prominence
  lambda_omega    → layout density, spacing, information density
  certainty grade → badge colour (certain=green, inferred=blue, probable=amber,
                    unknown=grey, contested=red, stale=orange)
  Visibility      → RENDER=opacity:1.0, FADE=opacity:0.35, HIDE=display:none
  dominant        → flex-grow boost, z-index elevation, saturated colour
  anchor          → position:sticky; never in leaving set
  TransitionPlan  → CSS @keyframes with anchor_first / staggered sequencing
  FlowState       → animated spinner / progress bar / stall warning
  ActiveFailure   → failure overlay: kind badge, cause text, cascade path
  stakes          → border thickness, salience glyph prominence
  weight          → primary→full, secondary→partial, background→peripheral

File structure:
  §1  Style constants and colour palettes
  §2  RenderNode and RenderTree
  §3  RenderTreeBuilder (SurfaceModel → RenderTree)
  §4  TerminalRenderer  (RenderTree → ANSI string)
  §5  HTMLRenderer      (RenderTree → HTML document)
  §6  CSS generation helpers
  §7  Transition CSS generation
  §8  Flow state HTML
  §9  Failure overlay HTML
  §10 CLI entry point
"""

from __future__ import annotations

import json
import math
import textwrap
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional

from guilds_evaluator import (
    Evaluator, SurfaceModel, EvalContext,
    ResolvedCertainty, BudgetAllocation, FlowState,
    TransitionPlan, ActiveFailure, PhaseResult,
    PHASE_NAMES, FAILURE_NAMES,
    PHASE_ORIENT, PHASE_EXECUTE, PHASE_VERIFY,
    PHASE_INTEGRATE, PHASE_RECOVER, PHASE_IDLE,
)
from guilds_parser import TT, parse_source


# ---------------------------------------------------------------------------
# SECTION 1: STYLE CONSTANTS
# ---------------------------------------------------------------------------

# Certainty grade → (colour_hex, ANSI_code, badge_symbol, label)
CERTAINTY_STYLE: dict[str, tuple[str, str, str, str]] = {
    "certain":   ("#22c55e", "\033[32m", "τ✓", "certain"),
    "inferred":  ("#3b82f6", "\033[34m", "τ~", "inferred"),
    "probable":  ("#f59e0b", "\033[33m", "τ?", "probable"),
    "stale":     ("#f97316", "\033[33m", "τ⌛","stale"),
    "unknown":   ("#6b7280", "\033[90m", "τ∅", "unknown"),
    "contested": ("#ef4444", "\033[31m", "τ⚔", "contested"),
    "composite": ("#a78bfa", "\033[35m", "τ∘", "composite"),
    "ref":       ("#6b7280", "\033[90m", "τ?", "ref"),
}

# Stakes → border width (px) and ANSI border char intensity
STAKES_BORDER: dict[str, tuple[int, str]] = {
    "low":              (1, "─"),
    "medium":           (2, "═"),
    "high":             (3, "━"),
    "critical":         (4, "▓"),
    "context_dependent":(1, "─"),
}

# Weight → flex-grow, opacity, ANSI label
WEIGHT_STYLE: dict[str, tuple[float, float, str]] = {
    "primary":    (3.0, 1.00, "PRIMARY"),
    "secondary":  (2.0, 0.85, "SECONDARY"),
    "tertiary":   (1.0, 0.65, "TERTIARY"),
    "background": (0.5, 0.45, "BACKGROUND"),
    "hidden":     (0.0, 0.00, "HIDDEN"),
}

# Failure kind → (colour, symbol, severity label)
FAILURE_STYLE: dict[TT, tuple[str, str, str]] = {
    TT.PHI_DEGRADED: ("#f59e0b", "Φ↓", "degraded"),
    TT.PHI_BLOCKED:  ("#ef4444", "Φ⊣", "blocked"),
    TT.PHI_LOST:     ("#6b7280", "Φ∅", "lost"),
    TT.PHI_PARTIAL:  ("#f97316", "Φ½", "partial"),
    TT.PHI_STALE:    ("#f59e0b", "Φ⌛","stale"),
    TT.PHI_RECOVER:  ("#3b82f6", "Φ⟳", "recovering"),
    TT.PHI_CASCADE:  ("#a78bfa", "Φ→", "cascade"),
    TT.PHI_UNKNOWN:  ("#6b7280", "Φ?", "unknown"),
    TT.PHI_FATAL:    ("#dc2626", "Φ✗", "FATAL"),
    TT.PHI_SILENT:   ("#dc2626", "Φ—", "SILENT_VIOLATION"),
}

# ANSI reset
ANSI_RESET = "\033[0m"
ANSI_BOLD  = "\033[1m"
ANSI_DIM   = "\033[2m"
ANSI_RED   = "\033[31m"
ANSI_GRN   = "\033[32m"
ANSI_YLW   = "\033[33m"
ANSI_BLU   = "\033[34m"
ANSI_MGT   = "\033[35m"
ANSI_CYN   = "\033[36m"
ANSI_WHT   = "\033[37m"
ANSI_GRY   = "\033[90m"

# Box-drawing characters
BOX_TL = "┌"; BOX_TR = "┐"; BOX_BL = "└"; BOX_BR = "┘"
BOX_H  = "─"; BOX_V  = "│"; BOX_TM = "┬"; BOX_BM = "┴"
BOX_LM = "├"; BOX_RM = "┤"; BOX_X  = "┼"

DBL_TL = "╔"; DBL_TR = "╗"; DBL_BL = "╚"; DBL_BR = "╝"
DBL_H  = "═"; DBL_V  = "║"

# Phase colours for HTML
PHASE_COLOUR: dict[str, str] = {
    "orient":    "#8b5cf6",
    "execute":   "#3b82f6",
    "verify":    "#22c55e",
    "integrate": "#14b8a6",
    "recover":   "#f97316",
    "idle":      "#6b7280",
}


# ---------------------------------------------------------------------------
# SECTION 2: RENDER NODE AND RENDER TREE
# ---------------------------------------------------------------------------

class NodeKind(Enum):
    VESSEL   = auto()
    CLAIM    = auto()
    AFFORD   = auto()
    STAGE    = auto()
    FLOW     = auto()
    FAILURE  = auto()  # failure overlay node
    SPACER   = auto()  # layout spacer


@dataclass
class RenderStyle:
    """Fully resolved visual style for a node, backend-agnostic."""
    opacity:       float      = 1.0     # 0.0 – 1.0
    flex_grow:     float      = 1.0     # layout proportion
    font_weight:   int        = 400     # CSS font-weight: 300 – 900
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
    failure_colour:str        = ""
    axis:          str        = "column"  # row | column (layout direction)
    gap_em:        float      = 0.75


@dataclass
class RenderNode:
    """
    One node in the render tree. Corresponds to one GUILDS declaration.
    Contains fully resolved style and display data; no AST references remain.
    """
    name:           str
    kind:           NodeKind
    visibility:     str             # "render" | "fade" | "hide"
    style:          RenderStyle
    label:          str             # display label (may differ from name)
    subtitle:       Optional[str]   # secondary label (flow state, certainty)
    certainty:      Optional[ResolvedCertainty]
    flow_state:     Optional[FlowState]
    active_failure: Optional[ActiveFailure]
    children:       list["RenderNode"] = field(default_factory=list)
    meta:           dict[str, Any]     = field(default_factory=dict)

    # For arrangement: describes how children are laid out
    arrangement_kind: str = "column"  # row | column | grid | free

    def is_visible(self) -> bool:
        return self.visibility in ("render", "fade")

    def effective_opacity(self) -> float:
        base = self.style.opacity
        if self.visibility == "fade":
            base = min(base, 0.35)
        if self.visibility == "hide":
            base = 0.0
        return base


@dataclass
class RenderTree:
    """Top-level render tree. One or more root nodes."""
    roots:          list[RenderNode]
    phase:          str
    phase_name:     str
    phase_colour:   str
    transitions:    list[TransitionPlan]   # pending transitions to encode
    active_failures:list[ActiveFailure]
    lambda_omega:   float                  # total load across visible roots
    budget_warnings:list[str]
    symbol_errors:  list[str]


# ---------------------------------------------------------------------------
# SECTION 3: RENDER TREE BUILDER
# ---------------------------------------------------------------------------

class RenderTreeBuilder:
    """
    Converts SurfaceModel + Evaluator into a RenderTree.
    All style decisions happen here; backends just emit.
    """

    def __init__(self, model: SurfaceModel, ev: Evaluator):
        self.model = model
        self.ev    = ev
        self.sym   = ev.sym
        self._built: dict[str, RenderNode] = {}

    def build(self) -> RenderTree:
        # Find the primary root declarations to render
        # Prefer stages (they govern phase visibility), then vessels not contained by others
        all_contained: set[str] = set()
        for v in self.sym.vessels.values():
            all_contained.update(v.contains)

        roots = []

        # Stages first (they are the intent-coupling structures)
        for name, stage in self.sym.stages.items():
            node = self._build_stage(name)
            roots.append(node)

        # Orphan vessels (not inside any stage's phase configs)
        stage_managed: set[str] = set()
        for s in self.sym.stages.values():
            for cfg in list(s.phases.values()) + ([s.default] if s.default else []):
                stage_managed.update(cfg.visible + cfg.faded + cfg.hidden)

        for name in self.sym.vessels:
            if name not in stage_managed and name not in all_contained:
                roots.append(self._build_vessel(name))

        # Failure overlay nodes at root level
        for af in self.model.active_failures:
            roots.append(self._failure_node(af))

        # Flows not attached to any vessel
        for name, flow in self.sym.flows.items():
            roots.append(self._build_flow(name))

        # Collect all pending transitions
        pending_transitions = []
        for stage_name in self.sym.stages:
            # Build execute→verify transition plan as representative
            plan = self.ev.transition_plan(stage_name, PHASE_EXECUTE, PHASE_VERIFY)
            if plan:
                pending_transitions.append(plan)

        total_lw = sum(
            pr.lambda_omega
            for pr in self.model.phase_results.values()
            if pr.visible or pr.faded
        )

        return RenderTree(
            roots=roots,
            phase=self.model.phase,
            phase_name=self.model.phase_name,
            phase_colour=PHASE_COLOUR.get(self.model.phase_name, "#6b7280"),
            transitions=pending_transitions,
            active_failures=self.model.active_failures,
            lambda_omega=total_lw,
            budget_warnings=self.model.budget_warnings,
            symbol_errors=self.model.symbol_errors,
        )

    # ---- Stage -------------------------------------------------------

    def _build_stage(self, name: str) -> RenderNode:
        if name in self._built:
            return self._built[name]

        pr = self.model.phase_results.get(name)
        stage = self.sym.stages.get(name)
        budget = self.model.budget_map.get(name)

        visibility = "render" if (pr and (pr.visible or pr.faded)) else "hide"
        style = self._stage_style(name, pr, budget)

        children: list[RenderNode] = []

        if stage:
            all_children: list[str] = []
            seen: set[str] = set()
            configs = list(stage.phases.values())
            if stage.default:
                configs.append(stage.default)

            for cfg in configs:
                ordered = []
                if cfg.dominant:
                    ordered.append(cfg.dominant)
                ordered.extend(cfg.visible)
                ordered.extend(cfg.faded)
                ordered.extend(cfg.hidden)
                for child_name in ordered:
                    if child_name not in seen:
                        seen.add(child_name)
                        all_children.append(child_name)

            if pr and pr.dominant in seen:
                order = [pr.dominant] + [x for x in all_children if x != pr.dominant]
            else:
                order = all_children

            for child_name in order:
                child_vis = "hide"
                if pr:
                    if child_name in pr.visible:
                        child_vis = "render"
                    elif child_name in pr.faded:
                        child_vis = "fade"

                if child_name in self.sym.vessels:
                    cn = self._build_vessel(child_name, override_vis=child_vis,
                                           is_dominant=bool(pr and child_name == pr.dominant))
                    children.append(cn)
                elif child_name in self.sym.claims:
                    cn = self._build_claim(child_name, override_vis=child_vis)
                    children.append(cn)

        anchor_elems = set(stage.anchor.elements) if (stage and stage.anchor) else set()
        arrangement  = self._arrangement_from_pr(pr)

        node = RenderNode(
            name=name, kind=NodeKind.STAGE,
            visibility=visibility, style=style,
            label=name,
            subtitle=f"stage · {self.model.phase_name}",
            certainty=None,
            flow_state=None,
            active_failure=self._find_failure_for(name),
            children=children,
            arrangement_kind=arrangement,
            meta={"anchor_elements": list(anchor_elems),
                  "lambda_omega": pr.lambda_omega if pr else 0.0,
                  "dominant": pr.dominant if pr else None},
        )
        self._built[name] = node
        return node

    # ---- Vessel ------------------------------------------------------

    def _build_vessel(self, name: str,
                      override_vis: str = "render",
                      is_dominant: bool = False) -> RenderNode:
        if name in self._built and not is_dominant:
            return self._built[name]

        vessel = self.sym.vessels.get(name)
        pr     = self.model.phase_results.get(name)
        budget = self.model.budget_map.get(name)

        visibility = override_vis
        style = self._vessel_style(name, vessel, budget, is_dominant, visibility)

        children: list[RenderNode] = []
        if vessel:
            for child_name in vessel.contains:
                if child_name in self.sym.vessels:
                    cn = self._build_vessel(child_name)
                    children.append(cn)
                elif child_name in self.sym.claims:
                    cn = self._build_claim(child_name)
                    children.append(cn)
                elif child_name in self.sym.affords:
                    cn = self._build_afford(child_name)
                    children.append(cn)

        arrangement = self._arrangement_str(vessel.arrangement if vessel else None)
        weight_str  = vessel.weight if vessel else "secondary"

        subtitle = None
        if is_dominant:
            subtitle = "◉ dominant"
        elif weight_str == "background":
            subtitle = "○ peripheral"

        node = RenderNode(
            name=name, kind=NodeKind.VESSEL,
            visibility=visibility, style=style,
            label=name,
            subtitle=subtitle,
            certainty=None,
            flow_state=None,
            active_failure=self._find_failure_for(name),
            children=children,
            arrangement_kind=arrangement,
            meta={"weight": weight_str,
                  "budget_allocated": budget.allocated if budget else None,
                  "load_count": len(vessel.contains) if vessel else 0,
                  "is_dominant": is_dominant},
        )
        self._built[name] = node
        return node

    # ---- Claim -------------------------------------------------------

    def _build_claim(self, name: str, override_vis: str = "render") -> RenderNode:
        claim   = self.sym.claims.get(name)
        cert    = self.model.certainty.get(name)
        budget  = self.model.budget_map.get(name)
        style   = self._claim_style(name, cert, override_vis)

        stakes_str = "low"
        if claim and claim.stakes:
            stakes_str = claim.stakes.level

        subtitle = None
        if cert:
            c_style = CERTAINTY_STYLE.get(cert.grade, CERTAINTY_STYLE["unknown"])
            subtitle = f"{c_style[2]} {cert.grade}  ·  stakes:{stakes_str}"
            if cert.is_stale:
                subtitle += "  ⌛ STALE"

        node = RenderNode(
            name=name, kind=NodeKind.CLAIM,
            visibility=override_vis, style=style,
            label=name,
            subtitle=subtitle,
            certainty=cert,
            flow_state=None,
            active_failure=None,
            children=[],
            meta={"stakes": stakes_str,
                  "provenance_hops": cert.provenance_hops if cert else 0},
        )
        return node

    # ---- Afford ------------------------------------------------------

    def _build_afford(self, name: str) -> RenderNode:
        afford = self.sym.affords.get(name)
        style  = RenderStyle(
            opacity=0.85, flex_grow=0.5, font_weight=500,
            border_px=1, border_colour="#374151",
            bg_colour="#1e293b", fg_colour="#94a3b8",
            accent_colour="#64748b",
        )
        return RenderNode(
            name=name, kind=NodeKind.AFFORD,
            visibility="render", style=style,
            label=name,
            subtitle="affordance",
            certainty=None, flow_state=None, active_failure=None,
            children=[],
        )

    # ---- Flow --------------------------------------------------------

    def _build_flow(self, name: str) -> RenderNode:
        fs = self.model.flow_states.get(name)
        style = RenderStyle(
            opacity=1.0 if (fs and not fs.terminal) else 0.5,
            flex_grow=0.5, font_weight=400,
            border_px=2,
            border_colour="#f59e0b" if (fs and fs.stalled) else "#374151",
            bg_colour="#0f172a", fg_colour="#94a3b8",
            accent_colour="#f59e0b" if (fs and fs.stalled) else "#3b82f6",
            is_stalled=bool(fs and fs.stalled),
        )
        subtitle = None
        if fs:
            if fs.stalled:
                subtitle = f"⚠ STALLED +{fs.stall_elapsed_ms:.0f}ms"
            elif fs.terminal:
                subtitle = f"terminal: {fs.terminal}"
            else:
                subtitle = f"step:{fs.step_name}  {fs.state_kind}  {fs.elapsed_ms:.0f}ms"

        return RenderNode(
            name=name, kind=NodeKind.FLOW,
            visibility="render", style=style,
            label=f"flow:{name}",
            subtitle=subtitle,
            certainty=None,
            flow_state=fs,
            active_failure=None,
            children=[],
        )

    # ---- Failure overlay node ----------------------------------------

    def _failure_node(self, af: ActiveFailure) -> RenderNode:
        fstyle = FAILURE_STYLE.get(af.kind, ("#dc2626", "Φ?", "unknown"))
        style = RenderStyle(
            opacity=1.0, flex_grow=0.0, font_weight=700,
            border_px=3, border_colour=fstyle[0],
            bg_colour="#1c0000", fg_colour="#fca5a5",
            accent_colour=fstyle[0],
            has_failure=True, failure_colour=fstyle[0],
        )
        cause_str = af.cause or "unspecified"
        subtitle  = f"origin:{af.origin}  cause:{cause_str}"
        if af.propagated_to:
            subtitle += f"  cascade→{','.join(af.propagated_to)}"

        return RenderNode(
            name=f"__failure_{af.origin}_{af.kind.name}",
            kind=NodeKind.FAILURE,
            visibility="render", style=style,
            label=f"{fstyle[1]} {FAILURE_NAMES.get(af.kind, '?')} in {af.origin}",
            subtitle=subtitle,
            certainty=None, flow_state=None, active_failure=af,
            children=[],
        )

    # ---- Style builders ----------------------------------------------

    def _stage_style(self, name: str, pr: Optional[PhaseResult],
                     budget: Optional[BudgetAllocation]) -> RenderStyle:
        lw = pr.lambda_omega if pr else 0.0
        # Higher lambda_omega → tighter spacing (more density)
        gap = max(0.25, 1.0 - (lw / 9.0) * 0.6)
        flex = (budget.allocated * 10) if budget else 1.0
        phase_col = PHASE_COLOUR.get(self.model.phase_name, "#374151")
        return RenderStyle(
            opacity=1.0,
            flex_grow=flex,
            font_weight=600,
            font_size_em=1.0,
            border_px=2,
            border_colour=phase_col,
            bg_colour="#0f172a",
            fg_colour="#e2e8f0",
            accent_colour=phase_col,
            axis="column",
            gap_em=gap,
        )

    def _vessel_style(self, name: str, vessel: Any,
                      budget: Optional[BudgetAllocation],
                      is_dominant: bool,
                      visibility: str) -> RenderStyle:
        weight_str = vessel.weight if vessel else "secondary"
        wstyle = WEIGHT_STYLE.get(weight_str, WEIGHT_STYLE["secondary"])

        flex = wstyle[0]
        if budget:
            flex = max(wstyle[0], budget.allocated * 6)
        if is_dominant:
            flex = max(flex * 1.6, 4.0)

        opacity = wstyle[1]
        if visibility == "fade":
            opacity = min(opacity, 0.35)

        # Dominant gets accent border and elevated background
        border_col = "#4b5563"
        bg_col     = "#111827"
        accent_col = "#3b82f6"
        fw         = 500

        if is_dominant:
            border_col = PHASE_COLOUR.get(self.model.phase_name, "#3b82f6")
            bg_col     = "#0f1f3d"
            accent_col = PHASE_COLOUR.get(self.model.phase_name, "#3b82f6")
            fw         = 700

        if self._find_failure_for(name):
            border_col = "#ef4444"
            bg_col     = "#1c0a0a"

        return RenderStyle(
            opacity=opacity,
            flex_grow=flex,
            font_weight=fw,
            font_size_em=1.1 if is_dominant else 1.0,
            border_px=2 if is_dominant else 1,
            border_colour=border_col,
            bg_colour=bg_col,
            fg_colour="#f1f5f9",
            accent_colour=accent_col,
            is_dominant=is_dominant,
            is_anchor=self._is_anchor(name),
            has_failure=bool(self._find_failure_for(name)),
            failure_colour="#ef4444" if self._find_failure_for(name) else "",
            axis=self._arrangement_str(vessel.arrangement if vessel else None),
            gap_em=0.75,
        )

    def _claim_style(self, name: str,
                     cert: Optional[ResolvedCertainty],
                     visibility: str) -> RenderStyle:
        grade = cert.grade if cert else "unknown"
        cstyle = CERTAINTY_STYLE.get(grade, CERTAINTY_STYLE["unknown"])
        dw     = cert.display_weight if cert else 1.0

        # display_weight drives font weight: 0→300, 10→800
        fw = int(300 + (dw / 10.0) * 500)
        fw = max(300, min(800, fw))

        opacity = 1.0 if visibility == "render" else 0.35

        # Stakes determine border prominence
        stakes = "low"
        if cert:
            stakes = cert.stakes
        bpx = STAKES_BORDER.get(stakes, (1, "─"))[0]

        return RenderStyle(
            opacity=opacity,
            flex_grow=max(0.5, dw / 5.0),
            font_weight=fw,
            border_px=bpx,
            border_colour=cstyle[0],
            bg_colour="#0f172a",
            fg_colour="#f1f5f9",
            accent_colour=cstyle[0],
        )

    # ---- Helpers -------------------------------------------------------

    def _arrangement_str(self, arr: Optional[Any]) -> str:
        if arr is None:
            return "column"
        k = arr.kind if hasattr(arr, "kind") else str(arr)
        if "sequence" in k:
            # Check axis from args
            args = arr.args if hasattr(arr, "args") else []
            if args and "primary" in str(args[0]):
                return "row"
            return "column"
        if "grid"  in k: return "grid"
        if "equal" in k: return "row"
        return "column"

    def _arrangement_from_pr(self, pr: Optional[PhaseResult]) -> str:
        if pr and pr.arrangement:
            return self._arrangement_str(pr.arrangement)
        return "column"

    def _find_failure_for(self, name: str) -> Optional[ActiveFailure]:
        for af in self.model.active_failures:
            if af.origin == name or name in af.propagated_to:
                return af
        return None

    def _is_anchor(self, name: str) -> bool:
        for stage in self.sym.stages.values():
            if stage.anchor and name in stage.anchor.elements:
                return True
        return False


# ---------------------------------------------------------------------------
# SECTION 4: TERMINAL RENDERER
# ---------------------------------------------------------------------------

class TerminalRenderer:
    """
    Renders a RenderTree to an ANSI terminal string.
    Uses box-drawing characters, colour codes, and compact layout.
    Does NOT require a real terminal — output is a plain string.
    """

    WIDTH = 80  # default column width

    def render(self, tree: RenderTree, width: int = 80) -> str:
        self.WIDTH = width
        lines = []
        lines += self._header(tree)
        for root in tree.roots:
            lines += self._node(root, depth=0, width=width)
        lines += self._footer(tree)
        return "\n".join(lines)

    # ---- Header / Footer -------------------------------------------------

    def _header(self, tree: RenderTree) -> list[str]:
        phase_ansi = "\033[35m" if tree.phase_name == "idle" else "\033[36m"
        title = (f"{ANSI_BOLD}{phase_ansi}"
                 f"GUILDS v2 Surface  ·  phase: {tree.phase_name}"
                 f"  ·  λΩ={tree.lambda_omega:.1f}{ANSI_RESET}")
        sep   = DBL_H * self.WIDTH
        lines = [sep, f" {title}", sep]
        if tree.symbol_errors:
            lines.append(f" {ANSI_RED}▲ {len(tree.symbol_errors)} symbol error(s){ANSI_RESET}")
        if tree.budget_warnings:
            lines.append(f" {ANSI_YLW}⚠ {len(tree.budget_warnings)} budget warning(s){ANSI_RESET}")
        lines.append("")
        return lines

    def _footer(self, tree: RenderTree) -> list[str]:
        lines = ["", DBL_H * self.WIDTH]
        if tree.transitions:
            lines.append(f" {ANSI_CYN}Pending transitions:{ANSI_RESET}")
            for plan in tree.transitions:
                fp = PHASE_NAMES.get(plan.from_phase, plan.from_phase)
                tp = PHASE_NAMES.get(plan.to_phase,   plan.to_phase)
                av = f"  {ANSI_RED}⚠ ANCHOR VIOLATION{ANSI_RESET}" if plan.anchor_violation else ""
                lines.append(
                    f"   {fp} → {tp}  "
                    f"{plan.duration_ms:.0f}ms {plan.easing}  "
                    f"[{plan.sequence_kind}]{av}"
                )
                if plan.leaving:
                    lines.append(f"     leaving : {', '.join(plan.leaving)}")
                if plan.arriving:
                    lines.append(f"     arriving: {', '.join(plan.arriving)}")
                if plan.dominant_change:
                    d0, d1 = plan.dominant_change
                    lines.append(f"     dominant: {d0 or '—'} → {d1 or '—'}")
        lines.append(DBL_H * self.WIDTH)
        return lines

    # ---- Node rendering --------------------------------------------------

    def _node(self, node: RenderNode, depth: int, width: int) -> list[str]:
        if node.visibility == "hide":
            return []

        indent = "  " * depth
        inner_w = width - len(indent) - 4  # 4 for border chars

        lines = []
        is_fade = (node.visibility == "fade")

        # Choose box style
        if node.kind == NodeKind.FAILURE:
            tl, tr, bl, br, h, v = "╔", "╗", "╚", "╝", "═", "║"
            colour = ANSI_RED
        elif node.style.is_dominant:
            tl, tr, bl, br, h, v = "╔", "╗", "╚", "╝", "═", "║"
            colour = ANSI_BLU
        elif node.kind == NodeKind.STAGE:
            tl, tr, bl, br, h, v = "┌", "┐", "└", "┘", "─", "│"
            colour = ANSI_CYN
        elif node.kind == NodeKind.CLAIM:
            tl, tr, bl, br, h, v = "▸", " ", "▸", " ", "─", " "
            colour = self._cert_ansi(node.certainty)
        elif node.kind == NodeKind.AFFORD:
            tl, tr, bl, br, h, v = "[", "]", "[", "]", "─", " "
            colour = ANSI_GRY
        else:
            tl, tr, bl, br, h, v = "┌", "┐", "└", "┘", "─", "│"
            colour = ANSI_WHT

        dim   = ANSI_DIM  if is_fade else ""
        reset = ANSI_RESET

        # Top border
        title_part = self._truncate(f" {node.label} ", inner_w - 4)
        border_len = inner_w - len(title_part)
        top = f"{h}{title_part}{h * max(0, border_len)}"
        lines.append(f"{indent}{dim}{colour}{tl}{top}{tr}{reset}")

        # Subtitle line
        if node.subtitle:
            sub = self._truncate(node.subtitle, inner_w - 2)
            lines.append(f"{indent}{dim}{colour}{v}{ANSI_GRY} {sub:<{inner_w - 2}} {colour}{v}{reset}")

        # Certainty line for claims
        if node.kind == NodeKind.CLAIM and node.certainty:
            cert = node.certainty
            c    = CERTAINTY_STYLE.get(cert.grade, CERTAINTY_STYLE["unknown"])
            dw_bar = self._bar(cert.display_weight, 10.0, 12)
            cert_line = (f"{c[1]} {c[2]} {cert.grade:<10}{ANSI_RESET}"
                         f"{ANSI_GRY}  dw={cert.display_weight:.2f} "
                         f"rank={cert.rank}  {dw_bar}{ANSI_GRY}"
                         f"  hops={cert.provenance_hops}{ANSI_RESET}")
            lines.append(f"{indent}{dim}{colour}{v}{reset}"
                         f" {cert_line} "
                         f"{dim}{colour}{v}{reset}")

        # Flow state line
        if node.kind == NodeKind.FLOW and node.flow_state:
            fs = node.flow_state
            if fs.stalled:
                fc = ANSI_YLW
                bar = self._spinner()
            else:
                fc = ANSI_BLU
                bar = self._bar(min(fs.elapsed_ms, 5000), 5000, 16)
            flow_line = (f"{fc}⟳ {fs.step_name:<14} "
                         f"{fs.state_kind:<12} {bar} "
                         f"{fs.elapsed_ms:.0f}ms{ANSI_RESET}")
            lines.append(f"{indent}{dim}{colour}{v}{reset}"
                         f" {flow_line} "
                         f"{dim}{colour}{v}{reset}")

        # Failure line
        if node.active_failure:
            af = node.active_failure
            fstyle = FAILURE_STYLE.get(af.kind, ("#dc2626", "Φ?", "?"))
            f_line = (f"{ANSI_RED}{fstyle[1]} {fstyle[2].upper()}"
                      f"  cause:{af.cause or '?'}"
                      f"  →{','.join(af.propagated_to) or '(contained)'}{ANSI_RESET}")
            lines.append(f"{indent}{dim}{colour}{v}{reset}"
                         f" {self._truncate(f_line, inner_w - 2, strip_ansi=False)}"
                         f" {dim}{colour}{v}{reset}")

        # Anchor indicator
        if node.style.is_anchor and node.kind != NodeKind.CLAIM:
            anchor_line = f"{ANSI_CYN}⚓ anchor{ANSI_RESET}"
            lines.append(f"{indent}{dim}{colour}{v}{reset}"
                         f" {anchor_line:<{inner_w - 2}} "
                         f"{dim}{colour}{v}{reset}")

        # Children
        if node.children:
            lines.append(f"{indent}{dim}{colour}{v}{reset}"
                         f"{' ' * inner_w} "
                         f"{dim}{colour}{v}{reset}")
            for child in node.children:
                child_lines = self._node(child, depth + 1, width - 2)
                lines.extend(child_lines)

        # Bottom border
        lines.append(f"{indent}{dim}{colour}{bl}{h * inner_w}{br}{reset}")
        lines.append("")

        return lines

    # ---- Helpers ---------------------------------------------------------

    def _cert_ansi(self, cert: Optional[ResolvedCertainty]) -> str:
        if cert is None:
            return ANSI_GRY
        return CERTAINTY_STYLE.get(cert.grade, CERTAINTY_STYLE["unknown"])[1]

    def _truncate(self, s: str, maxlen: int, strip_ansi: bool = True) -> str:
        if strip_ansi:
            # Strip ANSI for length calculation
            import re
            clean = re.sub(r"\033\[[0-9;]*m", "", s)
        else:
            clean = s
        if len(clean) <= maxlen:
            return s
        return clean[:maxlen - 1] + "…"

    def _bar(self, value: float, maxval: float, width: int = 16) -> str:
        filled = int((value / max(maxval, 1)) * width)
        filled = max(0, min(width, filled))
        return f"[{'█' * filled}{'░' * (width - filled)}]"

    def _spinner(self) -> str:
        return "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"[int(__import__("time").time() * 8) % 10]


# ---------------------------------------------------------------------------
# SECTION 5: HTML RENDERER
# ---------------------------------------------------------------------------

class HTMLRenderer:
    """
    Produces a self-contained HTML document from a RenderTree.
    Includes:
      - CSS custom properties derived from GUILDS model
      - Flex layout matching vessel arrangements
      - Certainty badges with colour coding
      - Animated flow indicators
      - Failure overlays
      - CSS transitions generated from TransitionPlan
      - Phase selector (JS) for live demonstration
    """

    def render(self, tree: RenderTree, title: str = "GUILDS Surface") -> str:
        css   = self._global_css(tree)
        body  = self._body(tree)
        trans = self._transition_css(tree)
        return HTML_TEMPLATE.format(
            title=title,
            css=css,
            transition_css=trans,
            body=body,
            phase_name=tree.phase_name,
            phase_colour=tree.phase_colour,
            lambda_omega=f"{tree.lambda_omega:.1f}",
        )

    # ---- Global CSS ------------------------------------------------------

    def _global_css(self, tree: RenderTree) -> str:
        phase_col = tree.phase_colour
        return f"""
        :root {{
          --phase-colour: {phase_col};
          --bg-deep:      #0a0e1a;
          --bg-mid:       #0f172a;
          --bg-surface:   #111827;
          --fg-primary:   #f1f5f9;
          --fg-secondary: #94a3b8;
          --fg-dim:       #475569;
          --border-dim:   #1e293b;
          --border-mid:   #334155;
          --gap:          0.75rem;
          --radius:       6px;
          --font-mono:    'JetBrains Mono', 'Fira Code', monospace;
          --font-sans:    'Inter', system-ui, sans-serif;
          --transition-dur: 250ms;
          --transition-ease: cubic-bezier(0.4, 0, 0.2, 1);
        }}
        """

    # ---- Body ------------------------------------------------------------

    def _body(self, tree: RenderTree) -> str:
        parts = []

        # Phase header
        parts.append(self._phase_header(tree))

        # Root nodes
        parts.append('<div class="roots">')
        for node in tree.roots:
            parts.append(self._html_node(node, depth=0))
        parts.append('</div>')

        # Transition plans panel
        if tree.transitions:
            parts.append(self._transitions_panel(tree))

        # Active failures panel
        if tree.active_failures:
            parts.append(self._failures_panel(tree))

        return "\n".join(parts)

    def _phase_header(self, tree: RenderTree) -> str:
        warnings = ""
        if tree.budget_warnings or tree.symbol_errors:
            items = []
            for w in tree.budget_warnings:
                items.append(f'<span class="badge badge-warn">⚠ {_he(w)}</span>')
            for e in tree.symbol_errors:
                items.append(f'<span class="badge badge-error">✗ {_he(e)}</span>')
            warnings = f'<div class="header-warnings">{"".join(items)}</div>'

        return f"""
        <header class="surface-header">
          <div class="phase-chip" style="--chip-colour:{tree.phase_colour}">
            <span class="phase-dot"></span>
            {_he(tree.phase_name)}
          </div>
          <div class="header-meta">
            λΩ = {tree.lambda_omega:.1f}
            <span class="{'load-ok' if tree.lambda_omega <= 9 else 'load-violation'}">
              {"✓ within budget" if tree.lambda_omega <= 9 else "⚠ LOAD CEILING EXCEEDED"}
            </span>
          </div>
          {warnings}
        </header>
        """

    # ---- Node rendering --------------------------------------------------

    def _html_node(self, node: RenderNode, depth: int) -> str:
        if node.visibility == "hide":
            return ""

        classes = [f"guilds-node", f"kind-{node.kind.name.lower()}"]
        if node.visibility == "fade":
            classes.append("visibility-fade")
        if node.style.is_dominant:
            classes.append("is-dominant")
        if node.style.is_anchor:
            classes.append("is-anchor")
        if node.style.has_failure:
            classes.append("has-failure")
        if node.style.is_stalled:
            classes.append("is-stalled")

        css_vars = self._node_css_vars(node)
        flex_dir = "row" if node.arrangement_kind == "row" else "column"

        children_html = ""
        if node.children:
            child_parts = [self._html_node(c, depth + 1) for c in node.children]
            children_html = f"""
            <div class="node-children" style="flex-direction:{flex_dir};">
              {"".join(child_parts)}
            </div>"""

        header_html  = self._node_header(node)
        content_html = self._node_content(node)
        data_id      = f'data-guilds-id="{_he(node.name)}"'

        return f"""
        <div class="{' '.join(classes)}" style="{css_vars}" {data_id}>
          {header_html}
          {content_html}
          {children_html}
        </div>"""

    def _node_header(self, node: RenderNode) -> str:
        anchor_badge = ""
        if node.style.is_anchor:
            anchor_badge = '<span class="badge badge-anchor">⚓ anchor</span>'

        dom_badge = ""
        if node.style.is_dominant:
            dom_badge = '<span class="badge badge-dominant">◉ dominant</span>'

        kind_badge = f'<span class="badge badge-kind">{node.kind.name.lower()}</span>'

        subtitle = ""
        if node.subtitle:
            subtitle = f'<div class="node-subtitle">{_he(node.subtitle)}</div>'

        return f"""
        <div class="node-header">
          <div class="node-title">
            <span class="node-name">{_he(node.label)}</span>
            {kind_badge}{anchor_badge}{dom_badge}
          </div>
          {subtitle}
        </div>"""

    def _node_content(self, node: RenderNode) -> str:
        parts = []

        # Certainty widget for claims
        if node.kind == NodeKind.CLAIM and node.certainty:
            parts.append(self._certainty_widget(node.certainty))

        # Flow state widget
        if node.kind == NodeKind.FLOW and node.flow_state:
            parts.append(self._flow_widget(node.flow_state))

        # Failure overlay
        if node.active_failure:
            parts.append(self._failure_widget(node.active_failure))

        if not parts:
            return ""
        return f'<div class="node-content">{"".join(parts)}</div>'

    # ---- Widgets ---------------------------------------------------------

    def _certainty_widget(self, cert: ResolvedCertainty) -> str:
        cs      = CERTAINTY_STYLE.get(cert.grade, CERTAINTY_STYLE["unknown"])
        colour  = cs[0]
        symbol  = cs[2]
        grade   = cs[3]
        rank_w  = cert.rank * 20       # 0–100%
        dw_pct  = min(100, cert.display_weight * 10)

        stale_banner = ""
        if cert.is_stale:
            stale_banner = '<div class="cert-stale-banner">⌛ STALE — certainty has decayed</div>'

        hops_class = "hops-ok" if cert.provenance_hops <= 2 else "hops-warn"

        return f"""
        <div class="certainty-widget" style="--cert-colour:{colour}">
          {stale_banner}
          <div class="cert-header">
            <span class="cert-symbol" style="color:{colour}">{symbol}</span>
            <span class="cert-grade" style="color:{colour}">{grade}</span>
            <span class="cert-stakes stakes-{_he(cert.stakes)}">{cert.stakes}</span>
          </div>
          <div class="cert-bars">
            <label>rank {cert.rank}/5</label>
            <div class="bar-track"><div class="bar-fill" style="width:{rank_w}%;background:{colour}"></div></div>
            <label>display weight {cert.display_weight:.2f}</label>
            <div class="bar-track"><div class="bar-fill" style="width:{dw_pct:.0f}%;background:{colour}88"></div></div>
          </div>
          <div class="cert-meta">
            <span class="{hops_class}">provenance: {cert.provenance_hops} hop{'s' if cert.provenance_hops != 1 else ''}</span>
          </div>
        </div>"""

    def _flow_widget(self, fs: FlowState) -> str:
        if fs.terminal:
            return f'<div class="flow-terminal">✓ {_he(fs.terminal)}</div>'

        stall_class = "flow-stalled" if fs.stalled else ""
        progress_pct = min(100, (fs.elapsed_ms / max(5000, fs.elapsed_ms)) * 100)

        stall_html = ""
        if fs.stalled:
            stall_html = f"""
            <div class="flow-stall-warning">
              ⚠ STALLED +{fs.stall_elapsed_ms:.0f}ms past threshold
            </div>"""

        return f"""
        <div class="flow-widget {stall_class}">
          <div class="flow-header">
            <span class="flow-spinner">{'⟳' if not fs.stalled else '⚠'}</span>
            <span class="flow-step">{_he(fs.step_name)}</span>
            <span class="flow-state">{_he(fs.state_kind)}</span>
            <span class="flow-elapsed">{fs.elapsed_ms:.0f}ms</span>
          </div>
          <div class="flow-track">
            <div class="flow-fill {'flow-fill-stalled' if fs.stalled else ''}"
                 style="width:{progress_pct:.0f}%"></div>
          </div>
          {stall_html}
        </div>"""

    def _failure_widget(self, af: ActiveFailure) -> str:
        fs = FAILURE_STYLE.get(af.kind, ("#dc2626", "Φ?", "unknown"))
        colour = fs[0]
        symbol = fs[1]
        label  = fs[2]

        cascade_html = ""
        if af.propagated_to:
            items = "".join(f'<span class="cascade-item">{_he(n)}</span>'
                            for n in af.propagated_to)
            cascade_html = f'<div class="failure-cascade">cascade → {items}</div>'

        blocked_html = ""
        if af.cascade_blocked:
            blocked_html = '<div class="failure-blocked">⊣ cascade blocked at seam</div>'

        return f"""
        <div class="failure-widget" style="--failure-colour:{colour}">
          <div class="failure-header" style="color:{colour}">
            <span class="failure-symbol">{symbol}</span>
            <span class="failure-label">{_he(label)}</span>
            <span class="failure-origin">in {_he(af.origin)}</span>
          </div>
          <div class="failure-cause">cause: {_he(af.cause or 'unspecified')}</div>
          {cascade_html}
          {blocked_html}
        </div>"""

    # ---- Transitions panel -----------------------------------------------

    def _transitions_panel(self, tree: RenderTree) -> str:
        plans = []
        for plan in tree.transitions:
            fp = PHASE_NAMES.get(plan.from_phase, plan.from_phase)
            tp = PHASE_NAMES.get(plan.to_phase,   plan.to_phase)
            av = ('<span class="badge badge-error">⚠ ANCHOR VIOLATION</span>'
                  if plan.anchor_violation else "")

            def name_list(names: list[str]) -> str:
                if not names:
                    return '<span class="dim">—</span>'
                return "".join(f'<span class="name-chip">{_he(n)}</span>' for n in names)

            anchor_html = name_list(plan.anchors)
            leaving_html = name_list(plan.leaving)
            arriving_html = name_list(plan.arriving)
            stable_html = name_list(plan.stable)

            dom_html = ""
            if plan.dominant_change:
                d0, d1 = plan.dominant_change
                dom_html = (f'<tr><th>dominant</th><td>'
                            f'{_he(d0 or "—")} → {_he(d1 or "—")}'
                            f'</td></tr>')

            plans.append(f"""
            <div class="transition-card">
              <div class="transition-header">
                <span class="phase-from">{fp}</span>
                <span class="transition-arrow">→</span>
                <span class="phase-to">{tp}</span>
                <span class="transition-meta">
                  {plan.duration_ms:.0f}ms · {_he(plan.easing)} · [{_he(plan.sequence_kind)}]
                </span>
                {av}
              </div>
              <table class="transition-table">
                <tr><th>anchors</th><td>{anchor_html}</td></tr>
                <tr><th>leaving</th><td>{leaving_html}</td></tr>
                <tr><th>arriving</th><td>{arriving_html}</td></tr>
                <tr><th>stable</th><td>{stable_html}</td></tr>
                {dom_html}
              </table>
            </div>""")

        return f"""
        <section class="transitions-panel">
          <h2 class="panel-title">⟳ Phase Transitions</h2>
          {"".join(plans)}
        </section>"""

    def _failures_panel(self, tree: RenderTree) -> str:
        items = []
        for af in tree.active_failures:
            items.append(self._failure_widget(af))
        return f"""
        <section class="failures-panel">
          <h2 class="panel-title">Φ Active Failures</h2>
          {"".join(items)}
        </section>"""

    # ---- Node CSS vars ---------------------------------------------------

    def _node_css_vars(self, node: RenderNode) -> str:
        s = node.style
        return (f"--node-opacity:{s.opacity:.2f};"
                f"--node-flex-grow:{s.flex_grow:.2f};"
                f"--node-fw:{s.font_weight};"
                f"--node-fs:{s.font_size_em:.2f}em;"
                f"--node-border:{s.border_px}px solid {s.border_colour};"
                f"--node-bg:{s.bg_colour};"
                f"--node-fg:{s.fg_colour};"
                f"--node-accent:{s.accent_colour};"
                f"--node-gap:{s.gap_em:.2f}rem;")

    # ---- Transition CSS --------------------------------------------------

    def _transition_css(self, tree: RenderTree) -> str:
        return generate_transition_css(tree.transitions, tree.phase_colour)


# ---------------------------------------------------------------------------
# SECTION 6: CSS GENERATION HELPERS
# ---------------------------------------------------------------------------

def generate_transition_css(plans: list[TransitionPlan], phase_colour: str) -> str:
    """Generate CSS for all pending transition plans."""
    rules = []
    for plan in plans:
        rules.append(_transition_keyframes(plan, phase_colour))
    return "\n".join(rules)


def _transition_keyframes(plan: TransitionPlan, accent: str) -> str:
    """
    Produce CSS keyframes that honour the sequence_kind.

    anchor_first:  anchors at 0%, content changes at 30%, arrivals at 60%
    content_first: content changes at 0%, layout settles at 60%
    staggered:     each leaving/arriving element gets its own delay
    simultaneous:  everything at 0%
    """
    dur  = plan.duration_ms
    ease = plan.easing if plan.easing and "ease" in plan.easing.lower() else "ease-out"

    # Clean up easing string (our parser may have put spaces around '-')
    ease = ease.replace(" - ", "-").replace(" ", "-").strip("-")
    if ease not in ("ease", "ease-in", "ease-out", "ease-in-out", "linear"):
        ease = "ease-out"

    seq  = plan.sequence_kind

    from_phase = PHASE_NAMES.get(plan.from_phase, plan.from_phase)
    to_phase   = PHASE_NAMES.get(plan.to_phase,   plan.to_phase)

    css_id = f"guilds-transition-{from_phase}-to-{to_phase}"

    if seq == "anchor_first":
        leaving_delay  = dur * 0.30
        arriving_delay = dur * 0.60
    elif seq == "content_first":
        leaving_delay  = 0.0
        arriving_delay = dur * 0.40
    else:
        leaving_delay  = 0.0
        arriving_delay = 0.0

    rules = [f"/* Transition: {from_phase} → {to_phase}  [{seq}] {dur:.0f}ms */"]

    # Leaving elements: fade out
    for i, name in enumerate(plan.leaving):
        stagger = (i * plan.stagger_ms) if seq == "staggered" else 0
        delay   = leaving_delay + stagger
        sel     = f'[data-guilds-id="{name}"]'
        rules.append(
            f"{sel}.leaving {{"
            f" animation: {css_id}-leave {dur:.0f}ms {ease} {delay:.0f}ms both; }}"
        )

    # Arriving elements: fade in
    for i, name in enumerate(plan.arriving):
        stagger = (i * plan.stagger_ms) if seq == "staggered" else 0
        delay   = arriving_delay + stagger
        sel     = f'[data-guilds-id="{name}"]'
        rules.append(
            f"{sel}.arriving {{"
            f" animation: {css_id}-arrive {dur:.0f}ms {ease} {delay:.0f}ms both; }}"
        )

    # Anchor: only position transition, no opacity change
    for name in plan.anchors:
        sel = f'[data-guilds-id="{name}"]'
        rules.append(
            f"{sel} {{ transition: transform {dur * 0.3:.0f}ms {ease}; }}"
        )

    # Keyframes
    rules.append(f"""
@keyframes {css_id}-leave {{
  from {{ opacity: var(--node-opacity); transform: translateY(0); }}
  to   {{ opacity: 0; transform: translateY(-4px); }}
}}
@keyframes {css_id}-arrive {{
  from {{ opacity: 0; transform: translateY(4px); }}
  to   {{ opacity: var(--node-opacity); transform: translateY(0); }}
}}""")

    return "\n".join(rules)


# ---------------------------------------------------------------------------
# SECTION 7: HTML TEMPLATE
# ---------------------------------------------------------------------------

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
/* ---- Reset ---- */
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
html {{ height: 100%; }}
body {{
  font-family: var(--font-sans);
  background: var(--bg-deep);
  color: var(--fg-primary);
  min-height: 100%;
  padding: 1.5rem;
  line-height: 1.5;
}}

/* ---- Variables from model ---- */
{css}

/* ---- Layout ---- */
.roots {{
  display: flex;
  flex-direction: column;
  gap: var(--gap);
}}

/* ---- Header ---- */
.surface-header {{
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem 1rem;
  background: #0f172a;
  border: 1px solid var(--border-mid);
  border-left: 4px solid var(--phase-colour);
  border-radius: var(--radius);
  margin-bottom: 1.25rem;
  flex-wrap: wrap;
}}
.phase-chip {{
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  background: color-mix(in srgb, var(--chip-colour) 15%, transparent);
  border: 1px solid var(--chip-colour);
  color: var(--chip-colour);
  border-radius: 20px;
  padding: 0.2rem 0.75rem;
  font-weight: 600;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}}
.phase-dot {{
  width: 8px; height: 8px;
  border-radius: 50%;
  background: currentColor;
  animation: pulse 2s infinite;
}}
@keyframes pulse {{
  0%, 100% {{ opacity: 1; }}
  50% {{ opacity: 0.4; }}
}}
.header-meta {{
  font-size: 0.85rem;
  color: var(--fg-secondary);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}}
.load-ok {{ color: #22c55e; }}
.load-violation {{ color: #ef4444; font-weight: 700; }}
.header-warnings {{
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-left: auto;
}}

/* ---- GUILDS Nodes ---- */
.guilds-node {{
  opacity: var(--node-opacity, 1);
  flex-grow: var(--node-flex-grow, 1);
  font-size: var(--node-fs, 1em);
  border: var(--node-border, 1px solid #334155);
  background: var(--node-bg, #111827);
  color: var(--node-fg, #f1f5f9);
  border-radius: var(--radius);
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: var(--node-gap, 0.5rem);
  transition:
    opacity var(--transition-dur) var(--transition-ease),
    transform var(--transition-dur) var(--transition-ease),
    border-color var(--transition-dur) var(--transition-ease);
}}

.visibility-fade {{
  opacity: 0.35 !important;
  filter: saturate(0.5);
}}

.is-dominant {{
  box-shadow: 0 0 0 2px var(--node-accent), 0 8px 32px -8px color-mix(in srgb, var(--node-accent) 40%, transparent);
}}

.is-anchor {{
  position: sticky;
  top: 1rem;
  z-index: 10;
}}

.has-failure {{
  animation: failure-pulse 1.5s infinite;
}}
@keyframes failure-pulse {{
  0%, 100% {{ box-shadow: 0 0 0 0 transparent; }}
  50% {{ box-shadow: 0 0 0 4px color-mix(in srgb, var(--node-accent) 30%, transparent); }}
}}

/* ---- Node Header ---- */
.node-header {{ display: flex; flex-direction: column; gap: 0.25rem; }}
.node-title {{
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-wrap: wrap;
}}
.node-name {{
  font-weight: var(--node-fw, 600);
  font-family: var(--font-mono);
  color: var(--node-accent);
  font-size: 0.95em;
}}
.node-subtitle {{
  font-size: 0.78rem;
  color: var(--fg-secondary);
  font-family: var(--font-mono);
}}

/* ---- Badges ---- */
.badge {{
  display: inline-flex;
  align-items: center;
  padding: 0.1rem 0.45rem;
  border-radius: 4px;
  font-size: 0.72rem;
  font-weight: 600;
  font-family: var(--font-mono);
  text-transform: lowercase;
}}
.badge-kind      {{ background: #1e293b; color: var(--fg-secondary); }}
.badge-anchor    {{ background: #0c4a6e; color: #38bdf8; }}
.badge-dominant  {{ background: #1e3a5f; color: var(--node-accent); }}
.badge-warn      {{ background: #431407; color: #fb923c; }}
.badge-error     {{ background: #450a0a; color: #f87171; }}

/* ---- Children ---- */
.node-children {{
  display: flex;
  gap: var(--node-gap, 0.5rem);
  flex-wrap: wrap;
  margin-top: 0.5rem;
}}
.node-children > .guilds-node {{
  flex: 1 1 200px;
}}

/* ---- Certainty Widget ---- */
.certainty-widget {{
  background: color-mix(in srgb, var(--cert-colour) 6%, var(--bg-mid));
  border: 1px solid color-mix(in srgb, var(--cert-colour) 25%, transparent);
  border-radius: 4px;
  padding: 0.6rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  font-size: 0.82rem;
}}
.cert-stale-banner {{
  background: #431407;
  color: #fb923c;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-weight: 700;
}}
.cert-header {{
  display: flex;
  align-items: center;
  gap: 0.5rem;
}}
.cert-symbol {{ font-size: 1.1em; font-family: var(--font-mono); }}
.cert-grade  {{ font-weight: 700; font-family: var(--font-mono); }}
.cert-stakes {{
  margin-left: auto;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  font-size: 0.72rem;
  font-weight: 600;
}}
.stakes-low      {{ background: #14532d; color: #86efac; }}
.stakes-medium   {{ background: #7c2d12; color: #fdba74; }}
.stakes-high     {{ background: #7c2d12; color: #f97316; }}
.stakes-critical {{ background: #450a0a; color: #ef4444; font-weight: 900; }}
.stakes-context_dependent {{ background: #1e293b; color: #94a3b8; }}
.cert-bars {{ display: flex; flex-direction: column; gap: 0.2rem; }}
.cert-bars label {{ font-size: 0.7rem; color: var(--fg-dim); }}
.bar-track {{
  height: 4px;
  background: #1e293b;
  border-radius: 2px;
  overflow: hidden;
}}
.bar-fill {{
  height: 100%;
  border-radius: 2px;
  transition: width 0.4s ease;
}}
.cert-meta {{ font-size: 0.72rem; }}
.hops-ok   {{ color: #4ade80; }}
.hops-warn {{ color: #f97316; }}

/* ---- Flow Widget ---- */
.flow-widget {{
  background: #0f172a;
  border: 1px solid #1e293b;
  border-radius: 4px;
  padding: 0.6rem;
  font-size: 0.82rem;
}}
.flow-stalled {{
  border-color: #f59e0b;
  animation: stall-flash 1s infinite;
}}
@keyframes stall-flash {{
  0%, 100% {{ border-color: #f59e0b; }}
  50% {{ border-color: #7c5a14; }}
}}
.flow-header {{
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.4rem;
  font-family: var(--font-mono);
}}
.flow-spinner {{
  animation: spin 1s linear infinite;
  display: inline-block;
}}
@keyframes spin {{ to {{ transform: rotate(360deg); }} }}
.flow-step    {{ font-weight: 700; color: #38bdf8; }}
.flow-state   {{ color: var(--fg-secondary); }}
.flow-elapsed {{ margin-left: auto; color: var(--fg-dim); }}
.flow-track {{
  height: 3px;
  background: #1e293b;
  border-radius: 2px;
  overflow: hidden;
}}
.flow-fill {{
  height: 100%;
  background: #3b82f6;
  border-radius: 2px;
  animation: flow-pulse 2s ease-in-out infinite;
}}
.flow-fill-stalled {{ background: #f59e0b; animation: none; }}
@keyframes flow-pulse {{
  0%, 100% {{ opacity: 1; }}
  50% {{ opacity: 0.6; }}
}}
.flow-stall-warning {{
  margin-top: 0.4rem;
  color: #fb923c;
  font-weight: 700;
  font-size: 0.78rem;
}}
.flow-terminal {{
  color: #4ade80;
  font-family: var(--font-mono);
  font-size: 0.82rem;
  padding: 0.3rem;
}}

/* ---- Failure Widget ---- */
.failure-widget {{
  background: color-mix(in srgb, var(--failure-colour) 8%, #0a0000);
  border: 2px solid var(--failure-colour);
  border-radius: 4px;
  padding: 0.6rem;
  font-size: 0.82rem;
  animation: failure-pulse 1.5s infinite;
}}
.failure-header {{
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 700;
  font-family: var(--font-mono);
  margin-bottom: 0.3rem;
}}
.failure-symbol {{ font-size: 1.1em; }}
.failure-label  {{ font-size: 1.0em; }}
.failure-origin {{ font-size: 0.8em; color: var(--fg-secondary); }}
.failure-cause  {{ color: var(--fg-secondary); margin-bottom: 0.25rem; }}
.failure-cascade {{
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.78rem;
}}
.cascade-item {{
  background: #450a0a;
  color: #fca5a5;
  padding: 0.1rem 0.3rem;
  border-radius: 3px;
  font-family: var(--font-mono);
}}
.failure-blocked {{
  color: #f59e0b;
  font-size: 0.78rem;
  margin-top: 0.2rem;
}}

/* ---- Transitions Panel ---- */
.transitions-panel, .failures-panel {{
  margin-top: 1.5rem;
  background: var(--bg-mid);
  border: 1px solid var(--border-mid);
  border-radius: var(--radius);
  padding: 1rem;
}}
.panel-title {{
  font-size: 0.82rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--fg-secondary);
  margin-bottom: 0.75rem;
  font-family: var(--font-mono);
}}
.transition-card {{
  background: #0f172a;
  border: 1px solid var(--border-dim);
  border-radius: 4px;
  padding: 0.75rem;
  margin-bottom: 0.5rem;
}}
.transition-header {{
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.6rem;
  font-size: 0.85rem;
  flex-wrap: wrap;
}}
.phase-from  {{ color: #94a3b8; font-family: var(--font-mono); font-weight: 600; }}
.phase-to    {{ color: var(--phase-colour); font-family: var(--font-mono); font-weight: 600; }}
.transition-arrow {{ color: var(--fg-dim); }}
.transition-meta  {{ color: var(--fg-dim); font-size: 0.78rem; font-family: var(--font-mono); }}
.transition-table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 0.78rem;
  font-family: var(--font-mono);
}}
.transition-table th {{
  color: var(--fg-dim);
  text-align: left;
  padding: 0.15rem 0.5rem 0.15rem 0;
  width: 80px;
  vertical-align: top;
}}
.transition-table td {{ padding: 0.15rem 0; }}
.name-chip {{
  display: inline-block;
  background: #1e293b;
  color: #94a3b8;
  border-radius: 3px;
  padding: 0.05rem 0.35rem;
  margin: 0.1rem;
}}
.dim {{ color: var(--fg-dim); }}

/* ---- Transition CSS (from model) ---- */
{transition_css}
</style>
</head>
<body>
{body}
<script>
// GUILDS Surface — phase state interactive demo
document.addEventListener("DOMContentLoaded", () => {{
  console.log("[GUILDS] Surface rendered. Phase:", "{phase_name}", "λΩ:", "{lambda_omega}");
  // Annotate visible elements with data attributes for renderer targeting
  document.querySelectorAll(".guilds-node").forEach(el => {{
    el.setAttribute("data-phase", "{phase_name}");
  }});
}});
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# SECTION 8: UTILITY
# ---------------------------------------------------------------------------

def _he(s: str) -> str:
    """HTML-escape a string."""
    return (str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


# ---------------------------------------------------------------------------
# SECTION 9: CLI
# ---------------------------------------------------------------------------

def main():
    import sys, os

    if len(sys.argv) < 2:
        print("Usage: guilds_renderer.py <file.guilds> [phase] [--html]")
        print("       guilds_renderer.py --example [phase] [--html]")
        print()
        print("Outputs terminal render by default, HTML if --html given.")
        sys.exit(1)

    args = sys.argv[1:]
    html_mode = "--html" in args
    args = [a for a in args if a != "--html"]

    phase_arg = args[1] if len(args) > 1 else "execute"
    phase_map = {
        "orient":    PHASE_ORIENT, "execute":   PHASE_EXECUTE,
        "verify":    PHASE_VERIFY, "integrate": PHASE_INTEGRATE,
        "recover":   PHASE_RECOVER, "idle":     PHASE_IDLE,
    }
    phase = phase_map.get(phase_arg, PHASE_EXECUTE)

    if args[0] == "--example":
        from guilds_parser import EXAMPLE_SOURCE as src
        source_name = "example"
    else:
        with open(args[0]) as f:
            src = f.read()
        source_name = os.path.splitext(os.path.basename(args[0]))[0]

    from guilds_parser import LexError, ParseError
    import time as time_mod
    try:
        program, _violations = parse_source(src, source_name)
    except (LexError, ParseError) as e:
        print(f"FATAL: {e}")
        sys.exit(2)

    ctx   = EvalContext(phase=phase, now=time_mod.time())
    ev    = Evaluator(program, ctx)
    model = ev.evaluate()

    builder = RenderTreeBuilder(model, ev)
    tree    = builder.build()

    if html_mode:
        renderer = HTMLRenderer()
        html     = renderer.render(tree, title=f"GUILDS · {source_name}")
        out_dir  = os.path.join("outputs", source_name)
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"guilds_surface_{phase_arg}.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"HTML written: {out_path}")
    else:
        renderer = TerminalRenderer()
        print(renderer.render(tree, width=88))


if __name__ == "__main__":
    main()

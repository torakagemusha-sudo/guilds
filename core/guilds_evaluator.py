"""
GUILDS v2 Evaluator
===================
Takes: Program AST (from guilds_parser.py)
       EvalContext (current phase, time, active events, triggered failures)

Produces: SurfaceModel — fully resolved runtime surface state

Seven evaluation passes:
  1. SymbolTable     — resolve all declarations, let bindings, cross-refs
  2. BudgetEvaluator — float allocations, conservation, load ceiling
  3. CertaintyEvaluator — grade resolution, composite min, stale decay, stakes amplification
  4. PhaseEvaluator  — visibility sets (render/fade/hide) at current phase
  5. TransitionEvaluator — ordered transition plan between phases
  6. FailureEvaluator — propagation graph, cascade paths, coverage audit
  7. FlowEvaluator   — step state machine, stall detection

SurfaceModel is queryable: "what is visible?", "what certainty grade?",
"if failure X triggers at vessel Y, what cascades?", "what is the transition plan?"
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional

# Import the AST types and TT enum from the parser.
# When used standalone, copy the relevant types below.
from guilds_parser import (
    Program, LetDecl, VesselDecl, ClaimDecl, AffordDecl,
    BondDecl, SeamDecl, StageDecl, FlowDecl, ContractDecl,
    StepDecl, StallSpec, PhaseConfig, AnchorSpec,
    BudgetNode, ArrangementNode, CertaintyNode, StakesNode,
    PhaseSpec, DeadlineNode, TriggerNode, ObligationNode,
    FailureSpec as ASTFailureSpec,
    TT, FAILURE_SIGILS, PHASE_SIGILS,
    parse_source,
)


# ---------------------------------------------------------------------------
# SECTION 1: EVAL CONTEXT
# ---------------------------------------------------------------------------

# Phase name constants (sigil strings as they appear in .guilds source)
PHASE_ORIENT    = "orient"
PHASE_EXECUTE   = "execute"
PHASE_VERIFY    = "verify"
PHASE_INTEGRATE = "integrate"
PHASE_RECOVER   = "recover"
PHASE_IDLE      = "idle"

ALL_PHASES = [PHASE_ORIENT, PHASE_EXECUTE, PHASE_VERIFY,
              PHASE_INTEGRATE, PHASE_RECOVER, PHASE_IDLE]

PHASE_NAMES = {
    PHASE_ORIENT:    "orient",
    PHASE_EXECUTE:   "execute",
    PHASE_VERIFY:    "verify",
    PHASE_INTEGRATE: "integrate",
    PHASE_RECOVER:   "recover",
    PHASE_IDLE:      "idle",
}

# Failure sigil to short name
FAILURE_NAMES = {
    TT.PHI_DEGRADED: "degraded",
    TT.PHI_BLOCKED:  "blocked",
    TT.PHI_LOST:     "lost",
    TT.PHI_PARTIAL:  "partial",
    TT.PHI_STALE:    "stale",
    TT.PHI_RECOVER:  "recovering",
    TT.PHI_CASCADE:  "cascade",
    TT.PHI_UNKNOWN:  "unknown",
    TT.PHI_FATAL:    "fatal",
    TT.PHI_SILENT:   "SILENT_VIOLATION",
}

# Certainty grade ordering (lower = less certain)
CERTAINTY_RANK = {
    "certain":   5,
    "inferred":  4,
    "probable":  3,
    "stale":     2,
    "unknown":   1,
    "contested": 0,  # orthogonal; treat as lowest for composition
    "ref":       3,  # unresolved ref; treat as probable
}

# Stakes multipliers for display weight
STAKES_MULT = {"low": 1.0, "medium": 1.2, "high": 1.5, "critical": 2.0}


@dataclass
class EvalContext:
    """
    Runtime context supplied by the caller — everything that changes over time.
    """
    phase: str = PHASE_IDLE              # current task phase (sigil string)
    now: float = field(default_factory=time.time)  # unix timestamp
    active_events: set[str] = field(default_factory=set)  # fired event names
    triggered_failures: list["ActiveFailure"] = field(default_factory=list)
    stale_thresholds: dict[str, float] = field(default_factory=dict)  # claim → seconds until stale

    def in_phase(self, phase_spec: PhaseSpec) -> bool:
        if not phase_spec:
            return True
        if "any" in phase_spec.phases:
            return True
        return self.phase in phase_spec.phases


# ---------------------------------------------------------------------------
# SECTION 2: RESOLVED OUTPUT TYPES
# ---------------------------------------------------------------------------

class Visibility(Enum):
    RENDER = "render"   # fully visible; contributes to ΛΩ
    FADE   = "fade"     # present at reduced prominence; contributes partial ΛΩ
    HIDE   = "hide"     # budget maintained; does not render; zero ΛΩ contribution


@dataclass
class ResolvedCertainty:
    """
    Fully evaluated certainty for a Claim.
    """
    grade: str                   # certain | inferred | probable | unknown | contested | stale
    rank: int                    # 0-5; lower = less certain
    display_weight: float        # rank × stakes_mult; drives visual prominence
    stakes: str                  # low | medium | high | critical | context_dependent
    is_stale: bool               # τ⌛ threshold exceeded
    elapsed_s: Optional[float]   # seconds since captured (for stale claims)
    provenance_hops: int         # 1 = direct, 2 = derived, 3+ = flag
    raw: CertaintyNode           # original AST node


@dataclass
class BudgetAllocation:
    """
    Fully resolved budget for a single declaration.
    """
    name: str
    parent_name: Optional[str]
    declared: BudgetNode
    allocated: float             # [0.0, 1.0] fraction of display surface
    children_sum: float          # sum of child allocations
    overflow: bool               # children_sum > allocated
    load_count: int              # independent elements in contains
    load_violation: bool         # load_count > 9


@dataclass
class ActiveFailure:
    """
    A failure that has occurred and may be propagating.
    """
    kind: TT                     # PHI_* token type
    origin: str                  # name of vessel/stage where failure occurred
    cause: Optional[str]         # human-readable cause string
    cascade_blocked: bool        # stopped at a seam
    propagated_to: list[str]     # names of vessels failure reached


@dataclass
class TransitionPlan:
    """
    Resolved plan for a phase transition.
    """
    from_phase: str
    to_phase: str
    duration_ms: float
    easing: str
    sequence_kind: str           # simultaneous | anchor_first | content_first | staggered
    stagger_ms: float

    anchors: list[str]           # anchor elements (must settle first if anchor_first)
    leaving: list[str]           # currently visible; becoming hidden/faded
    arriving: list[str]          # currently hidden; becoming visible/faded
    stable: list[str]            # remain at same visibility
    dominant_change: Optional[tuple[str, str]]  # (from_dominant, to_dominant) if changed
    anchor_violation: bool       # True if any anchor is in leaving set


@dataclass
class FlowState:
    """
    Runtime state of a Flow declaration.
    """
    flow_name: str
    current_step: int            # index into steps list
    step_name: str
    state_kind: str              # acquiring | streaming | processing | completing | settled
    elapsed_ms: float            # ms since step entered
    stalled: bool
    stall_elapsed_ms: float
    terminal: Optional[str]      # None if still running


@dataclass
class ContractObligation:
    """
    A contract obligation that is pending or fulfilled.
    """
    contract_name: str
    context: str                 # vessel/afford/stage that owns it
    obligation_kind: str
    deadline_ms: Optional[float]
    fired_at: Optional[float]    # timestamp when trigger fired
    fulfilled: bool
    breached: bool
    breach_failure: Optional[TT]


@dataclass
class DialogueAct:
    """
    A resolved dialogue act, in order.
    """
    kind: str                    # assert | query | propose | warn | ack | silence |
                                 # correct | escalate | celebrate
    source: str                  # which contract/vessel produced this
    content: Optional[str]
    certainty: Optional[ResolvedCertainty]
    stakes: Optional[str]
    ordered_position: int        # position in dialogue sequence


@dataclass
class AffordanceState:
    """
    Runtime state of an affordance.
    """
    name: str
    active: bool                 # True if all requires conditions are met
    perceivable: bool            # True if currently visible to human
    reason_if_inactive: Optional[str]
    pending_contracts: list[ContractObligation]


# ---------------------------------------------------------------------------
# SECTION 3: SYMBOL TABLE
# ---------------------------------------------------------------------------

class SymbolTable:
    """
    First pass: resolve all declarations and let bindings into lookup maps.
    Cross-reference containment chains. Detect unresolved references.
    """
    def __init__(self, program: Program):
        self.lets:      dict[str, Any]           = {}
        self.vessels:   dict[str, VesselDecl]    = {}
        self.claims:    dict[str, ClaimDecl]     = {}
        self.affords:   dict[str, AffordDecl]    = {}
        self.bonds:     dict[str, BondDecl]      = {}
        self.seams:     dict[str, SeamDecl]      = {}
        self.stages:    dict[str, StageDecl]     = {}
        self.flows:     dict[str, FlowDecl]      = {}
        self.contracts: dict[str, ContractDecl]  = {}
        self.errors:    list[str]                = []

        for decl in program.declarations:
            if   isinstance(decl, LetDecl):      self.lets[decl.name]      = decl.value
            elif isinstance(decl, VesselDecl):   self.vessels[decl.name]   = decl
            elif isinstance(decl, ClaimDecl):    self.claims[decl.name]    = decl
            elif isinstance(decl, AffordDecl):   self.affords[decl.name]   = decl
            elif isinstance(decl, BondDecl):     self.bonds[decl.name]     = decl
            elif isinstance(decl, SeamDecl):     self.seams[decl.name]     = decl
            elif isinstance(decl, StageDecl):    self.stages[decl.name]    = decl
            elif isinstance(decl, FlowDecl):     self.flows[decl.name]     = decl
            elif isinstance(decl, ContractDecl): self.contracts[decl.name] = decl

        # Flatten inline contracts from vessels and affords
        for v in self.vessels.values():
            for c in v.contracts:
                self.contracts[c.name] = c
        for a in self.affords.values():
            for c in a.contracts:
                self.contracts[c.name] = c

        self._validate_refs()

    def resolve_certainty(self, c: CertaintyNode) -> CertaintyNode:
        """Resolve let-binding references in certainty nodes."""
        if c.kind == "ref":
            ref = self.lets.get(c.args[0])
            if isinstance(ref, CertaintyNode):
                return self.resolve_certainty(ref)
            self.errors.append(f"Unresolved certainty reference: {c.args[0]!r}")
        if c.kind == "composite":
            return CertaintyNode(
                kind="composite",
                args=[self.resolve_certainty(sub) for sub in c.args]
            )
        return c

    def lookup(self, name: str) -> Optional[Any]:
        for store in [self.vessels, self.claims, self.affords,
                      self.bonds, self.seams, self.stages, self.flows,
                      self.contracts, self.lets]:
            if name in store:
                return store[name]
        return None

    def _validate_refs(self):
        """Check that names referenced in contains, bonds, seams exist."""
        for v in self.vessels.values():
            for name in v.contains:
                if self.lookup(name) is None:
                    self.errors.append(
                        f"Vessel '{v.name}': contains unknown name '{name}'")
        for s in self.stages.values():
            for config in s.phases.values():
                for lst in [config.visible, config.faded, config.hidden]:
                    for name in lst:
                        if self.lookup(name) is None:
                            self.errors.append(
                                f"Stage '{s.name}': references unknown name '{name}'")
        for b in self.bonds.values():
            for m in b.members:
                if self.lookup(m) is None:
                    self.errors.append(
                        f"Bond '{b.name}': references unknown member '{m}'")


# ---------------------------------------------------------------------------
# SECTION 4: BUDGET EVALUATOR
# ---------------------------------------------------------------------------

class BudgetEvaluator:
    """
    Second pass: bottom-up computation of budget allocations.
    Enforces conservation law and load ceiling.
    Produces BudgetAllocation for every named declaration.
    """
    def __init__(self, sym: SymbolTable):
        self.sym = sym
        self.allocations: dict[str, BudgetAllocation] = {}
        self.warnings: list[str] = []

    def evaluate(self, root_budget: float = 1.0) -> dict[str, BudgetAllocation]:
        """
        Evaluate all vessels and stages.
        Vessels without explicit parents are treated as roots sharing root_budget.
        """
        # Find roots: vessels not referenced in any other vessel's contains
        all_contained: set[str] = set()
        for v in self.sym.vessels.values():
            all_contained.update(v.contains)
        for s in self.sym.stages.values():
            for cfg in s.phases.values():
                all_contained.update(cfg.visible + cfg.faded + cfg.hidden)

        root_vessels = [n for n in self.sym.vessels if n not in all_contained]
        root_stages  = [n for n in self.sym.stages  if n not in all_contained]

        n_roots = len(root_vessels) + len(root_stages)
        per_root = root_budget / n_roots if n_roots else root_budget

        for name in root_vessels:
            self._eval_vessel(name, per_root, parent_name=None)
        for name in root_stages:
            self._eval_stage(name, per_root, parent_name=None)

        return self.allocations

    def _eval_budget_node(self, b: Optional[BudgetNode], parent: float,
                          child_count: int) -> float:
        if b is None:
            return parent / max(child_count, 1)
        match b.kind:
            case "whole":
                return float(b.args[0]) * parent
            case "fixed":
                v = float(b.args[0])
                if v > parent:
                    self.warnings.append(
                        f"fixed({v}) exceeds parent budget ({parent:.3f})")
                return v
            case "auto":
                return parent
            case "ceiling":
                n = float(b.args[0])
                inner = self._eval_budget_node(b.args[1], parent, child_count)
                return min(n * parent, inner)
            case "shared":
                n = float(b.args[0])
                k_raw = b.args[1]
                k = float(k_raw) if isinstance(k_raw, (int, float)) else 4.0
                return (n * parent) / k
            case _:
                return parent

    def _eval_vessel(self, name: str, parent_budget: float,
                     parent_name: Optional[str]):
        if name in self.allocations:
            return
        v = self.sym.vessels.get(name)
        if not v:
            return

        alloc = self._eval_budget_node(v.budget, parent_budget, len(v.contains))

        child_alloc_total = 0.0
        n_children = len(v.contains)
        per_child = alloc / n_children if n_children else alloc

        for child_name in v.contains:
            if child_name in self.sym.vessels:
                child_v = self.sym.vessels[child_name]
                child_a = self._eval_budget_node(child_v.budget, alloc, n_children)
                child_alloc_total += child_a
                self._eval_vessel(child_name, alloc, name)
            elif child_name in self.sym.claims:
                # Claims are leaves; share remaining budget equally
                child_alloc_total += per_child
            elif child_name in self.sym.affords:
                child_alloc_total += per_child

        overflow = child_alloc_total > alloc + 1e-9
        if overflow:
            self.warnings.append(
                f"Budget overflow in '{name}': children sum {child_alloc_total:.3f} "
                f"> allocated {alloc:.3f}")

        load_count = len(v.contains)
        load_viol  = load_count > 9

        self.allocations[name] = BudgetAllocation(
            name=name,
            parent_name=parent_name,
            declared=v.budget or BudgetNode(kind="auto", args=[]),
            allocated=alloc,
            children_sum=child_alloc_total,
            overflow=overflow,
            load_count=load_count,
            load_violation=load_viol,
        )

    def _eval_stage(self, name: str, parent_budget: float,
                    parent_name: Optional[str]):
        if name in self.allocations:
            return
        s = self.sym.stages.get(name)
        if not s:
            return

        alloc = self._eval_budget_node(s.budget, parent_budget, 1)

        # Stage's children are elements across all PhaseConfigs
        all_children: set[str] = set()
        for cfg in s.phases.values():
            all_children.update(cfg.visible + cfg.faded + cfg.hidden)
        if s.default:
            all_children.update(s.default.visible + s.default.faded + s.default.hidden)

        child_alloc_total = 0.0
        per_child = alloc / len(all_children) if all_children else alloc

        for child_name in all_children:
            if child_name in self.sym.vessels:
                child_v = self.sym.vessels[child_name]
                child_a = self._eval_budget_node(child_v.budget, alloc, len(all_children))
                child_alloc_total += child_a
                self._eval_vessel(child_name, alloc, name)
            else:
                child_alloc_total += per_child

        overflow = child_alloc_total > alloc + 1e-9
        load_count = len(all_children)

        self.allocations[name] = BudgetAllocation(
            name=name,
            parent_name=parent_name,
            declared=s.budget or BudgetNode(kind="auto", args=[]),
            allocated=alloc,
            children_sum=child_alloc_total,
            overflow=overflow,
            load_count=load_count,
            load_violation=load_count > 9,
        )


# ---------------------------------------------------------------------------
# SECTION 5: CERTAINTY EVALUATOR
# ---------------------------------------------------------------------------

class CertaintyEvaluator:
    """
    Third pass: resolve all certainty grades.
    Applies composite minimum, stale decay, stakes amplification.
    """
    def __init__(self, sym: SymbolTable, ctx: EvalContext):
        self.sym = sym
        self.ctx = ctx
        self.resolved: dict[str, ResolvedCertainty] = {}

    def evaluate(self) -> dict[str, ResolvedCertainty]:
        for name, claim in self.sym.claims.items():
            self.resolved[name] = self._resolve_claim(claim)
        return self.resolved

    def _resolve_claim(self, claim: ClaimDecl) -> ResolvedCertainty:
        cert_node = claim.certainty
        if cert_node:
            cert_node = self.sym.resolve_certainty(cert_node)

        grade, rank = self._resolve_grade(cert_node)

        # Stale decay
        is_stale   = False
        elapsed_s  = None
        threshold  = self.ctx.stale_thresholds.get(claim.name)
        if threshold is not None:
            elapsed_s = self.ctx.now - (self.ctx.now - threshold)  # simplified
            if cert_node and cert_node.kind == "stale":
                if len(cert_node.args) >= 2:
                    dl: DeadlineNode = cert_node.args[1]
                    thr_s = self._deadline_to_s(dl)
                    if thr_s and elapsed_s and elapsed_s > thr_s:
                        grade = "probable"
                        rank  = CERTAINTY_RANK["probable"]
                        is_stale = True

        # Stakes
        stakes = "low"
        if claim.stakes:
            stakes = claim.stakes.level

        mult = STAKES_MULT.get(stakes, 1.0)
        display_weight = rank * mult

        # Provenance hops
        hops = self._count_provenance_hops(claim.provenance)

        return ResolvedCertainty(
            grade=grade,
            rank=rank,
            display_weight=display_weight,
            stakes=stakes,
            is_stale=is_stale,
            elapsed_s=elapsed_s,
            provenance_hops=hops,
            raw=cert_node or CertaintyNode(kind="unknown", args=[]),
        )

    def _resolve_grade(self, node: Optional[CertaintyNode]) -> tuple[str, int]:
        if node is None:
            return "unknown", CERTAINTY_RANK["unknown"]
        if node.kind == "composite":
            sub_grades = [self._resolve_grade(sub) for sub in node.args]
            if not sub_grades:
                return "unknown", 1
            # Composite minimum: take the grade with lowest rank
            return min(sub_grades, key=lambda g: g[1])
        if node.kind == "ref":
            resolved = self.sym.resolve_certainty(node)
            return self._resolve_grade(resolved)
        rank = CERTAINTY_RANK.get(node.kind, 1)
        return node.kind, rank

    def _deadline_to_s(self, dl: DeadlineNode) -> Optional[float]:
        if dl is None:
            return None
        match dl.kind:
            case "ms":  return (dl.value or 0) / 1000
            case "s":   return dl.value or 0
            case "m":   return (dl.value or 0) * 60
            case "h":   return (dl.value or 0) * 3600
            case _:     return None

    def _count_provenance_hops(self, prov: Optional[Any]) -> int:
        if prov is None:
            return 3  # unknown provenance: flag as distant
        s = str(prov)
        if "direct" in s:   return 1
        if "derived" in s:  return 2
        if "ai_generated" in s: return 2
        if "external" in s: return 2
        return 3


# ---------------------------------------------------------------------------
# SECTION 6: PHASE EVALUATOR
# ---------------------------------------------------------------------------

@dataclass
class PhaseResult:
    """Resolved visibility for a given phase."""
    phase: str
    phase_name: str
    visible:   list[str]
    faded:     list[str]
    hidden:    list[str]
    dominant:  Optional[str]
    arrangement: Optional[ArrangementNode]
    # ΛΩ: count of independently visible elements (render + partial for fade)
    lambda_omega: float
    load_violation: bool


class PhaseEvaluator:
    """
    Fourth pass: given current phase, resolve visibility sets for all
    stages and vessels. Enforce load ceiling. Flag anchor violations.
    """
    def __init__(self, sym: SymbolTable, ctx: EvalContext):
        self.sym = sym
        self.ctx = ctx
        self.results: dict[str, PhaseResult] = {}
        self.anchor_violations: list[str] = []

    def evaluate(self) -> dict[str, PhaseResult]:
        # Evaluate stages
        for name, stage in self.sym.stages.items():
            self.results[name] = self._eval_stage(name, stage)

        # Evaluate plain vessels (phase-filtered)
        for name, vessel in self.sym.vessels.items():
            if name not in self.results:
                self.results[name] = self._eval_vessel(name, vessel)

        return self.results

    def _get_phase_config(self, stage: StageDecl) -> Optional[PhaseConfig]:
        config = stage.phases.get(self.ctx.phase)
        if config is None:
            config = stage.default
        return config

    def _eval_stage(self, name: str, stage: StageDecl) -> PhaseResult:
        config = self._get_phase_config(stage)

        if config is None:
            # No config for this phase and no default — everything hidden
            return PhaseResult(
                phase=self.ctx.phase,
                phase_name=PHASE_NAMES.get(self.ctx.phase, self.ctx.phase),
                visible=[], faded=[], hidden=[], dominant=None,
                arrangement=None, lambda_omega=0.0, load_violation=False,
            )

        # Anchor stability check
        if stage.anchor:
            for elem in stage.anchor.elements:
                if elem in config.hidden:
                    self.anchor_violations.append(
                        f"Stage '{name}': anchor element '{elem}' is hidden "
                        f"in phase {PHASE_NAMES.get(self.ctx.phase, self.ctx.phase)}")

        # ΛΩ: render counts 1.0, fade counts 0.5 (peripheral, lower cost)
        lw = len(config.visible) * 1.0 + len(config.faded) * 0.5
        load_viol = lw > 9.0

        return PhaseResult(
            phase=self.ctx.phase,
            phase_name=PHASE_NAMES.get(self.ctx.phase, self.ctx.phase),
            visible=list(config.visible),
            faded=list(config.faded),
            hidden=list(config.hidden),
            dominant=config.dominant,
            arrangement=config.arrangement,
            lambda_omega=lw,
            load_violation=load_viol,
        )

    def _eval_vessel(self, name: str, vessel: VesselDecl) -> PhaseResult:
        # Check phase coupling
        in_scope = True
        if vessel.phase:
            in_scope = self.ctx.in_phase(vessel.phase)

        if not in_scope:
            return PhaseResult(
                phase=self.ctx.phase,
                phase_name=PHASE_NAMES.get(self.ctx.phase, self.ctx.phase),
                visible=[], faded=[], hidden=list(vessel.contains),
                dominant=None, arrangement=vessel.arrangement,
                lambda_omega=0.0, load_violation=False,
            )

        # All children visible when in scope
        lw = float(len(vessel.contains))
        return PhaseResult(
            phase=self.ctx.phase,
            phase_name=PHASE_NAMES.get(self.ctx.phase, self.ctx.phase),
            visible=list(vessel.contains),
            faded=[], hidden=[],
            dominant=None,
            arrangement=vessel.arrangement,
            lambda_omega=lw,
            load_violation=lw > 9.0,
        )


# ---------------------------------------------------------------------------
# SECTION 7: TRANSITION EVALUATOR
# ---------------------------------------------------------------------------

class TransitionEvaluator:
    """
    Fifth pass: compute the ordered plan for transitioning between phases.
    Works for stages only (vessels don't have phase-differentiated configs).
    """
    def __init__(self, sym: SymbolTable):
        self.sym = sym

    def plan(self, stage_name: str,
             from_phase: str, to_phase: str) -> Optional[TransitionPlan]:
        stage = self.sym.stages.get(stage_name)
        if not stage:
            return None

        def get_cfg(ph: str) -> PhaseConfig:
            return stage.phases.get(ph) or stage.default or PhaseConfig(
                arrangement=None, visible=[], faded=[], hidden=[], dominant=None)

        from_cfg = get_cfg(from_phase)
        to_cfg   = get_cfg(to_phase)

        from_vis = set(from_cfg.visible)
        to_vis   = set(to_cfg.visible)
        from_fad = set(from_cfg.faded)
        to_fad   = set(to_cfg.faded)

        # Sets moving by visibility change
        leaving  = sorted((from_vis | from_fad) - (to_vis | to_fad))
        arriving = sorted((to_vis | to_fad) - (from_vis | from_fad))
        stable   = sorted((from_vis | from_fad) & (to_vis | to_fad))

        # Anchors from stage definition
        anchors = list(stage.anchor.elements) if stage.anchor else []

        # Anchor violation: any anchor in leaving
        anchor_viol = any(a in leaving for a in anchors)

        # Transition timing
        dur_ms   = 200.0
        easing   = "ease-out"
        seq_kind = "simultaneous"
        stag_ms  = 0.0

        if stage.transition:
            tr = stage.transition
            if "duration" in tr:
                raw_dur = tr["duration"]
                dur_ms  = self._parse_duration_ms(raw_dur)
            if "curve" in tr:
                easing = str(tr["curve"])
            if "sequence" in tr:
                seq_kind = str(tr["sequence"])
                if "staggered" in seq_kind:
                    # Extract ms value from "staggered(50)" etc.
                    import re
                    m = re.search(r"staggered\s*\(?\s*(\d+)", seq_kind)
                    stag_ms = float(m.group(1)) if m else 50.0
                    seq_kind = "staggered"

        # Dominant change
        dom_change = None
        if from_cfg.dominant != to_cfg.dominant:
            dom_change = (from_cfg.dominant, to_cfg.dominant)

        return TransitionPlan(
            from_phase=from_phase,
            to_phase=to_phase,
            duration_ms=dur_ms,
            easing=easing,
            sequence_kind=seq_kind,
            stagger_ms=stag_ms,
            anchors=anchors,
            leaving=leaving,
            arriving=arriving,
            stable=stable,
            dominant_change=dom_change,
            anchor_violation=anchor_viol,
        )

    def _parse_duration_ms(self, raw: Any) -> float:
        if isinstance(raw, (int, float)):
            return float(raw)
        s = str(raw).strip()
        import re
        m = re.match(r"ms\s*\(\s*(\d+(?:\.\d+)?)\s*\)", s)
        if m: return float(m.group(1))
        m = re.match(r"s\s*\(\s*(\d+(?:\.\d+)?)\s*\)", s)
        if m: return float(m.group(1)) * 1000
        m = re.match(r"(\d+(?:\.\d+)?)", s)
        if m: return float(m.group(1))
        return 200.0


# ---------------------------------------------------------------------------
# SECTION 8: FAILURE EVALUATOR
# ---------------------------------------------------------------------------

@dataclass
class SeamEdge:
    """One directional edge in the failure propagation graph."""
    from_vessel: str
    to_vessel:   str
    seam_name:   str
    # What happens to each failure kind crossing this edge
    blocks:      set[TT]    # failure kinds stopped here
    passes:      set[TT]    # failure kinds that cross freely
    transforms:  dict[TT, TT]  # from → to transforms
    all_pass:    bool
    all_block:   bool


@dataclass
class CascadeResult:
    """Result of propagating a failure through the seam graph."""
    origin: str
    origin_failure: TT
    reached: list[tuple[str, TT]]   # (vessel_name, failure_kind_at_that_vessel)
    blocked_at: list[tuple[str, str]]  # (vessel_name, seam_name)
    path: list[str]                  # ordered list of vessels visited


class FailureEvaluator:
    """
    Sixth pass: build the failure propagation graph from SeamDecl declarations.
    Evaluate cascade paths for triggered failures.
    Audit failure coverage on all vessels.
    """
    def __init__(self, sym: SymbolTable):
        self.sym = sym
        self.graph: dict[str, list[SeamEdge]] = {}  # vessel → outbound edges
        self._build_graph()

    def _build_graph(self):
        for name, seam in self.sym.seams.items():
            if len(seam.members) < 2:
                continue
            a, b = seam.members[0], seam.members[1]
            edge = self._parse_seam_edge(a, b, seam)
            self.graph.setdefault(a, []).append(edge)
            # Seams are bidirectional for hard/soft kinds
            # For asymmetric seams the same rules apply both ways (conservative)
            rev = self._parse_seam_edge(b, a, seam)
            self.graph.setdefault(b, []).append(rev)

    def _parse_seam_edge(self, src: str, dst: str, seam: SeamDecl) -> SeamEdge:
        fp = seam.failure_prop or {}
        blocks_raw     = fp.get("blocks",     "")
        passes_raw     = fp.get("passes",     "")
        transforms_raw = fp.get("transforms", "")
        all_pass  = "all_pass"  in str(fp.get("", "")) or str(fp) == "{'all_pass': True}"
        all_block = "all_block" in str(fp.get("", "")) or str(fp) == "{'all_block': True}"

        # Parse failure kind lists from raw strings
        blocks    = self._parse_phi_set(str(blocks_raw))
        passes    = self._parse_phi_set(str(passes_raw))
        transforms: dict[TT, TT] = {}

        # Handle "all_pass" / "all_block" as string values in dict
        for k, v in fp.items():
            if str(v).strip().lower() in ("true", "1"):
                if k == "all_pass":  all_pass  = True
                if k == "all_block": all_block = True
            if k == "passes":  passes  = self._parse_phi_set(str(v))
            if k == "blocks":  blocks  = self._parse_phi_set(str(v))

        return SeamEdge(
            from_vessel=src, to_vessel=dst, seam_name=seam.name,
            blocks=blocks, passes=passes, transforms=transforms,
            all_pass=all_pass, all_block=all_block,
        )

    def _parse_phi_set(self, raw: str) -> set[TT]:
        """Extract PHI_* token types from a raw string representation."""
        result: set[TT] = set()
        # Map sigil-like substrings to TT
        phi_map = {
            "degraded":   TT.PHI_DEGRADED, "blocked":    TT.PHI_BLOCKED,
            "lost":       TT.PHI_LOST,     "partial":    TT.PHI_PARTIAL,
            "stale":      TT.PHI_STALE,    "recovering": TT.PHI_RECOVER,
            "cascade":    TT.PHI_CASCADE,  "unknown":    TT.PHI_UNKNOWN,
            "fatal":      TT.PHI_FATAL,    "silent":     TT.PHI_SILENT,
            "PHI_DEGRADED": TT.PHI_DEGRADED, "PHI_BLOCKED":  TT.PHI_BLOCKED,
            "PHI_FATAL":    TT.PHI_FATAL,    "PHI_UNKNOWN":  TT.PHI_UNKNOWN,
        }
        for sigil, tt in phi_map.items():
            if sigil in raw:
                result.add(tt)
        return result

    def cascade(self, origin: str, failure_kind: TT,
                cause: Optional[str] = None) -> CascadeResult:
        """
        BFS/DFS through the seam graph from origin.
        Returns CascadeResult describing everything the failure reached.
        """
        reached:    list[tuple[str, TT]]   = []
        blocked_at: list[tuple[str, str]]  = []
        path:       list[str]              = [origin]
        visited:    set[str]               = {origin}

        queue: list[tuple[str, TT]] = [(origin, failure_kind)]

        while queue:
            current, current_failure = queue.pop(0)
            edges = self.graph.get(current, [])

            for edge in edges:
                target = edge.to_vessel
                if target in visited:
                    continue

                result_failure = self._traverse(edge, current_failure)

                if result_failure is None:
                    blocked_at.append((target, edge.seam_name))
                else:
                    visited.add(target)
                    path.append(target)
                    reached.append((target, result_failure))
                    queue.append((target, result_failure))

        return CascadeResult(
            origin=origin,
            origin_failure=failure_kind,
            reached=reached,
            blocked_at=blocked_at,
            path=path,
        )

    def _traverse(self, edge: SeamEdge, failure: TT) -> Optional[TT]:
        """
        Returns the failure kind that exits on the far side of the seam,
        or None if the failure is blocked.
        """
        if edge.all_block:
            return None
        if edge.all_pass:
            return failure
        # Check transforms first
        if failure in edge.transforms:
            return edge.transforms[failure]
        # Check explicit blocks
        if failure in edge.blocks:
            return None
        # Check explicit passes
        if failure in edge.passes:
            return failure
        # Default: block (conservative — undeclared passage = blocked)
        return None

    def audit_coverage(self) -> list[str]:
        """
        Return list of vessels/affords with operations that have no failure contract.
        """
        missing: list[str] = []
        for name, vessel in self.sym.vessels.items():
            for contract in vessel.contracts:
                if (contract.obligation and
                        contract.obligation.kind == "execute" and
                        contract.on_breach is None):
                    missing.append(
                        f"Vessel '{name}', contract '{contract.name}': "
                        f"execute obligation with no on_breach handler")
        return missing


# ---------------------------------------------------------------------------
# SECTION 9: FLOW EVALUATOR
# ---------------------------------------------------------------------------

@dataclass
class FlowStateInternal:
    step_idx: int
    step_name: str
    entered_at: float
    stall_detected: bool
    stall_started_at: Optional[float]
    terminal: Optional[str]


class FlowEvaluator:
    """
    Seventh pass: evaluate Flow state machines.
    Given current context (time, events), advance each flow to its current step.
    """
    def __init__(self, sym: SymbolTable, ctx: EvalContext):
        self.sym   = sym
        self.ctx   = ctx
        self._states: dict[str, FlowStateInternal] = {}
        self.results: dict[str, FlowState] = {}

    def evaluate(self) -> dict[str, FlowState]:
        for name, flow in self.sym.flows.items():
            state = self._eval_flow(name, flow)
            self.results[name] = state
        return self.results

    def _eval_flow(self, name: str, flow: FlowDecl) -> FlowState:
        internal = self._states.get(name)
        if not internal:
            internal = FlowStateInternal(
                step_idx=0,
                step_name=flow.steps[0].name if flow.steps else "<empty>",
                entered_at=self.ctx.now,
                stall_detected=False,
                stall_started_at=None,
                terminal=None,
            )
            self._states[name] = internal

        if internal.terminal:
            return FlowState(
                flow_name=name, current_step=internal.step_idx,
                step_name=internal.step_name, state_kind="settled",
                elapsed_ms=0.0, stalled=False, stall_elapsed_ms=0.0,
                terminal=internal.terminal,
            )

        steps = flow.steps
        if not steps:
            return FlowState(
                flow_name=name, current_step=0, step_name="<empty>",
                state_kind="settled", elapsed_ms=0.0,
                stalled=False, stall_elapsed_ms=0.0, terminal="success",
            )

        idx = min(internal.step_idx, len(steps) - 1)
        step = steps[idx]
        elapsed_ms = (self.ctx.now - internal.entered_at) * 1000

        # Check for step exit via events
        exit_str = str(step.exit_cond or "")
        event_exit = False
        if "on_event" in exit_str:
            import re
            m = re.search(r"on_event\s*\(\s*(\w+)", exit_str)
            if m and m.group(1) in self.ctx.active_events:
                event_exit = True
        elif "on_complete" in exit_str:
            # on_complete exits after a timed duration
            dur_ms = self._step_duration_ms(step)
            if dur_ms is not None and elapsed_ms >= dur_ms:
                event_exit = True

        if event_exit:
            next_idx = idx + 1
            if next_idx >= len(steps):
                # Flow complete
                internal.terminal = "success"
                return FlowState(
                    flow_name=name, current_step=idx, step_name=step.name,
                    state_kind="settled", elapsed_ms=elapsed_ms,
                    stalled=False, stall_elapsed_ms=0.0, terminal="success",
                )
            else:
                # Advance to next step
                internal.step_idx = next_idx
                internal.step_name = steps[next_idx].name
                internal.entered_at = self.ctx.now
                internal.stall_detected = False
                internal.stall_started_at = None
                step = steps[next_idx]
                elapsed_ms = 0.0

        # Stall detection for unbounded steps
        stalled = False
        stall_elapsed_ms = 0.0
        state_kind = self._step_state_kind(step)

        dur = step.duration
        is_unbounded = (dur == "unbounded" or
                        (isinstance(dur, DeadlineNode) and dur.kind == "unbounded"))

        if is_unbounded and flow.on_stall:
            stall_threshold_ms = self._deadline_to_ms(flow.on_stall.threshold)
            if stall_threshold_ms and elapsed_ms > stall_threshold_ms:
                stalled = True
                stall_elapsed_ms = elapsed_ms - stall_threshold_ms
                if not internal.stall_detected:
                    internal.stall_detected = True
                    internal.stall_started_at = self.ctx.now

        return FlowState(
            flow_name=name,
            current_step=idx,
            step_name=step.name,
            state_kind=state_kind,
            elapsed_ms=elapsed_ms,
            stalled=stalled,
            stall_elapsed_ms=stall_elapsed_ms,
            terminal=None,
        )

    def _step_state_kind(self, step: StepDecl) -> str:
        s = str(step.state or "")
        for k in ("acquiring", "streaming", "processing", "completing", "settled"):
            if k in s:
                return k
        return "processing"

    def _step_duration_ms(self, step: StepDecl) -> Optional[float]:
        dur = step.duration
        if dur == "unbounded" or dur is None:
            return None
        if isinstance(dur, DeadlineNode):
            return self._deadline_to_ms(dur)
        return None

    def _deadline_to_ms(self, dl: Optional[DeadlineNode]) -> Optional[float]:
        if dl is None:
            return None
        match dl.kind:
            case "ms":  return dl.value
            case "s":   return (dl.value or 0) * 1000
            case "m":   return (dl.value or 0) * 60000
            case "h":   return (dl.value or 0) * 3600000
            case _:     return None

    def advance(self, flow_name: str, event: str):
        """Fire an event into a specific flow, potentially advancing its step."""
        self.ctx.active_events.add(event)
        if flow_name in self.sym.flows:
            self._eval_flow(flow_name, self.sym.flows[flow_name])
        self.ctx.active_events.discard(event)

    def reset(self, flow_name: str):
        """Reset a flow to step 0."""
        if flow_name in self._states:
            del self._states[flow_name]


# ---------------------------------------------------------------------------
# SECTION 10: SURFACE MODEL
# ---------------------------------------------------------------------------

@dataclass
class SurfaceModel:
    """
    The fully resolved runtime model. Central output of the evaluator.
    Queryable by name, by phase, by failure kind.
    """
    phase:             str
    phase_name:        str

    # Budget
    budget_map:        dict[str, BudgetAllocation]
    budget_warnings:   list[str]

    # Phase / visibility
    phase_results:     dict[str, PhaseResult]
    anchor_violations: list[str]

    # Certainty
    certainty:         dict[str, ResolvedCertainty]

    # Failure
    failure_graph_edges: int                           # total seam edges in graph
    active_failures:    list[ActiveFailure]

    # Flow states
    flow_states:        dict[str, FlowState]

    # Symbol table errors
    symbol_errors:      list[str]

    def visible_names(self, scope: Optional[str] = None) -> list[str]:
        """Return all names with Visibility.RENDER in current phase."""
        results = []
        target = [self.phase_results[scope]] if scope else self.phase_results.values()
        for pr in target:
            results.extend(pr.visible)
        return sorted(set(results))

    def faded_names(self) -> list[str]:
        results = []
        for pr in self.phase_results.values():
            results.extend(pr.faded)
        return sorted(set(results))

    def is_visible(self, name: str) -> bool:
        return any(name in pr.visible for pr in self.phase_results.values())

    def is_faded(self, name: str) -> bool:
        return any(name in pr.faded for pr in self.phase_results.values())

    def budget_for(self, name: str) -> Optional[float]:
        alloc = self.budget_map.get(name)
        return alloc.allocated if alloc else None

    def certainty_for(self, name: str) -> Optional[ResolvedCertainty]:
        return self.certainty.get(name)

    def display_weight_for(self, name: str) -> float:
        cert = self.certainty.get(name)
        return cert.display_weight if cert else 0.0

    def dominant_in(self, scope: str) -> Optional[str]:
        pr = self.phase_results.get(scope)
        return pr.dominant if pr else None

    def flow_state_for(self, name: str) -> Optional[FlowState]:
        return self.flow_states.get(name)

    def load_violations(self) -> list[tuple[str, float]]:
        """Return (name, lambda_omega) for all load ceiling violations."""
        return [(n, pr.lambda_omega)
                for n, pr in self.phase_results.items()
                if pr.load_violation]


# ---------------------------------------------------------------------------
# SECTION 11: EVALUATOR (ORCHESTRATOR)
# ---------------------------------------------------------------------------

class Evaluator:
    """
    Orchestrates all seven evaluation passes.
    Single entry point for the runtime evaluation pipeline.

    Usage:
        program, _ = parse_source(src)
        ctx = EvalContext(phase=PHASE_EXECUTE)
        ev = Evaluator(program, ctx)
        model = ev.evaluate()
        plan  = ev.transition_plan("MyStage", PHASE_EXECUTE, PHASE_VERIFY)
        cascade = ev.cascade("MyVessel", TT.PHI_FATAL)
    """
    def __init__(self, program: Program, ctx: Optional[EvalContext] = None):
        self.program = program
        self.ctx = ctx or EvalContext()

        # Build symbol table first; all other passes depend on it
        self.sym = SymbolTable(program)

        self._budget_ev     = BudgetEvaluator(self.sym)
        self._certainty_ev  = CertaintyEvaluator(self.sym, self.ctx)
        self._phase_ev      = PhaseEvaluator(self.sym, self.ctx)
        self._transition_ev = TransitionEvaluator(self.sym)
        self._failure_ev    = FailureEvaluator(self.sym)
        self._flow_ev       = FlowEvaluator(self.sym, self.ctx)

        self._model: Optional[SurfaceModel] = None

    def evaluate(self) -> SurfaceModel:
        """Run all passes. Returns the fully resolved SurfaceModel."""

        budget_map     = self._budget_ev.evaluate()
        certainty_map  = self._certainty_ev.evaluate()
        phase_results  = self._phase_ev.evaluate()
        flow_states    = self._flow_ev.evaluate()

        total_seam_edges = sum(len(v) for v in self._failure_ev.graph.values())

        self._model = SurfaceModel(
            phase      = self.ctx.phase,
            phase_name = PHASE_NAMES.get(self.ctx.phase, self.ctx.phase),

            budget_map      = budget_map,
            budget_warnings = self._budget_ev.warnings,

            phase_results     = phase_results,
            anchor_violations = self._phase_ev.anchor_violations,

            certainty        = certainty_map,

            failure_graph_edges = total_seam_edges,
            active_failures     = list(self.ctx.triggered_failures),

            flow_states    = flow_states,
            symbol_errors  = self.sym.errors,
        )
        return self._model

    def transition_plan(self, stage_name: str,
                        from_phase: str, to_phase: str) -> Optional[TransitionPlan]:
        """Compute an ordered transition plan between two phases for a stage."""
        return self._transition_ev.plan(stage_name, from_phase, to_phase)

    def cascade(self, origin: str, failure_kind: TT,
                cause: Optional[str] = None) -> CascadeResult:
        """Compute the full failure cascade from a given origin vessel."""
        return self._failure_ev.cascade(origin, failure_kind, cause)

    def advance_flow(self, flow_name: str, event: str):
        """Fire an event into a flow, advancing its state machine."""
        self._flow_ev.advance(flow_name, event)
        # Re-evaluate flows after advancing
        if self._model:
            self._model.flow_states = self._flow_ev.evaluate()

    def transition_phase(self, new_phase: str) -> SurfaceModel:
        """
        Advance to a new task phase.
        Re-runs phase and flow evaluation passes with updated context.
        Returns new SurfaceModel.
        """
        old_phase = self.ctx.phase
        self.ctx.phase = new_phase

        # Re-run phase-dependent passes
        self._phase_ev = PhaseEvaluator(self.sym, self.ctx)
        self._flow_ev  = FlowEvaluator(self.sym, self.ctx)

        return self.evaluate()

    def trigger_failure(self, origin: str, kind: TT,
                        cause: Optional[str] = None) -> CascadeResult:
        """
        Trigger a failure at origin, compute cascade, add to active failures.
        """
        result = self.cascade(origin, kind, cause)

        af = ActiveFailure(
            kind=kind, origin=origin, cause=cause,
            cascade_blocked=len(result.blocked_at) > 0,
            propagated_to=[r[0] for r in result.reached],
        )
        self.ctx.triggered_failures.append(af)
        if self._model:
            self._model.active_failures.append(af)

        return result

    def coverage_audit(self) -> list[str]:
        """Return list of uncovered failure paths (TC-7 violations)."""
        return self._failure_ev.audit_coverage()


# ---------------------------------------------------------------------------
# SECTION 12: REPORT + CLI
# ---------------------------------------------------------------------------

def format_surface_report(model: SurfaceModel, ev: Evaluator) -> str:
    lines = []
    W = 70

    lines.append("=" * W)
    lines.append("GUILDS v2 — Surface Evaluation Report")
    lines.append(f"Phase: {model.phase_name}  ({model.phase})")
    lines.append("=" * W)

    # Symbol errors
    if model.symbol_errors:
        lines.append("\n-- SYMBOL ERRORS (unresolved references)")
        for e in model.symbol_errors:
            lines.append(f"   ! {e}")

    # Budget
    lines.append("\n-- BUDGET ALLOCATIONS")
    if model.budget_map:
        lines.append(f"  {'Name':<28} {'Allocated':>10}  {'Children':>10}  {'Load':>5}  Flags")
        lines.append(f"  {'-'*28} {'-'*10}  {'-'*10}  {'-'*5}  -----")
        for name, alloc in sorted(model.budget_map.items()):
            flags = []
            if alloc.overflow:      flags.append("OVERFLOW")
            if alloc.load_violation: flags.append(f"LOAD({alloc.load_count})")
            flag_str = " ".join(flags)
            lines.append(
                f"  {name:<28} {alloc.allocated:>10.3f}  "
                f"{alloc.children_sum:>10.3f}  {alloc.load_count:>5}  {flag_str}"
            )
    else:
        lines.append("  (no budget allocations — no vessel or stage roots found)")

    if model.budget_warnings:
        lines.append("\n  Budget warnings:")
        for w in model.budget_warnings:
            lines.append(f"    ! {w}")

    # Phase / visibility
    lines.append(f"\n-- VISIBILITY  (phase: {model.phase_name})")
    for name, pr in sorted(model.phase_results.items()):
        if not (pr.visible or pr.faded):
            continue
        lines.append(f"\n  [{name}]  lw={pr.lambda_omega:.1f}"
                     + ("  LOAD VIOLATION" if pr.load_violation else ""))
        if pr.dominant:
            lines.append(f"    dominant : {pr.dominant}")
        if pr.visible:
            lines.append(f"    render   : {', '.join(pr.visible)}")
        if pr.faded:
            lines.append(f"    fade     : {', '.join(pr.faded)}")
        if pr.hidden:
            lines.append(f"    hide     : {', '.join(pr.hidden)}")

    if model.anchor_violations:
        lines.append("\n  Anchor violations:")
        for av in model.anchor_violations:
            lines.append(f"    ! {av}")

    # Certainty
    lines.append("\n-- CERTAINTY GRADES")
    if model.certainty:
        lines.append(f"  {'Claim':<28} {'Grade':<12} {'Rank':>4} {'DWeight':>8} "
                     f"{'Stakes':<10} {'Stale':<6} {'Hops':>4}")
        lines.append(f"  {'-'*28} {'-'*12} {'-'*4} {'-'*8} {'-'*10} {'-'*6} {'-'*4}")
        for name, rc in sorted(model.certainty.items()):
            stale_s = "YES" if rc.is_stale else "-"
            lines.append(
                f"  {name:<28} {rc.grade:<12} {rc.rank:>4} "
                f"{rc.display_weight:>8.2f} {rc.stakes:<10} {stale_s:<6} {rc.provenance_hops:>4}"
            )
    else:
        lines.append("  (no claims declared)")

    # Flow states
    lines.append("\n-- FLOW STATES")
    if model.flow_states:
        for name, fs in sorted(model.flow_states.items()):
            term = fs.terminal or "running"
            stall = f"  STALLED +{fs.stall_elapsed_ms:.0f}ms" if fs.stalled else ""
            lines.append(f"  [{name}]  step={fs.step_name}  "
                         f"state={fs.state_kind}  elapsed={fs.elapsed_ms:.0f}ms  "
                         f"terminal={term}{stall}")
    else:
        lines.append("  (no flows declared)")

    # Active failures
    lines.append("\n-- ACTIVE FAILURES")
    if model.active_failures:
        for af in model.active_failures:
            fname = FAILURE_NAMES.get(af.kind, str(af.kind))
            cascaded = ", ".join(af.propagated_to) or "contained"
            lines.append(f"  [{af.origin}] {fname}  "
                         f"cause={af.cause or '?'}  cascaded_to={cascaded}")
    else:
        lines.append("  (none)")

    # Coverage audit
    uncovered = ev.coverage_audit()
    lines.append("\n-- FAILURE COVERAGE AUDIT")
    if uncovered:
        for u in uncovered:
            lines.append(f"  UNCOVERED: {u}")
    else:
        lines.append("  OK — all execute obligations have breach handlers")

    lines.append("\n" + "=" * W)
    return "\n".join(lines)


def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: guilds_evaluator.py <file.guilds> [phase]")
        print("       guilds_evaluator.py --example [phase]")
        print()
        print("phase: orient | execute | verify | integrate | recover | idle")
        sys.exit(1)

    phase_arg = sys.argv[2] if len(sys.argv) > 2 else "execute"
    phase_map = {
        "orient":    PHASE_ORIENT,    "execute":   PHASE_EXECUTE,
        "verify":    PHASE_VERIFY,    "integrate": PHASE_INTEGRATE,
        "recover":   PHASE_RECOVER,   "idle":      PHASE_IDLE,
    }
    phase = phase_map.get(phase_arg, PHASE_EXECUTE)

    if sys.argv[1] == "--example":
        # Import the example source from the parser
        from guilds_parser import EXAMPLE_SOURCE as src
        source_name = "<built-in example>"
    else:
        with open(sys.argv[1]) as f:
            src = f.read()
        source_name = sys.argv[1]

    from guilds_parser import LexError, ParseError
    try:
        program, type_violations = parse_source(src, source_name)
    except (LexError, ParseError) as e:
        print(f"FATAL parse error: {e}")
        sys.exit(2)

    ctx = EvalContext(phase=phase, now=time.time())
    ev  = Evaluator(program, ctx)
    model = ev.evaluate()

    # Print type checker results first
    if type_violations:
        print("\nType checker violations from parser:")
        for v in type_violations:
            print(f"  [{v.code}] {v.severity.upper()} in '{v.node_name}': {v.message}")

    print(format_surface_report(model, ev))

    # Demo: transition plan
    for stage_name in ev.sym.stages:
        plan = ev.transition_plan(stage_name, PHASE_EXECUTE, PHASE_VERIFY)
        if plan:
            print(f"\n-- TRANSITION PLAN: {stage_name}  "
                  f"{PHASE_NAMES[PHASE_EXECUTE]} -> {PHASE_NAMES[PHASE_VERIFY]}")
            print(f"   duration    : {plan.duration_ms:.0f}ms  "
                  f"easing={plan.easing}  sequence={plan.sequence_kind}")
            print(f"   anchors     : {plan.anchors or ['(none)']}")
            print(f"   leaving     : {plan.leaving or ['(none)']}")
            print(f"   arriving    : {plan.arriving or ['(none)']}")
            print(f"   stable      : {plan.stable or ['(none)']}")
            if plan.dominant_change:
                print(f"   dominant    : {plan.dominant_change[0]} -> {plan.dominant_change[1]}")
            if plan.anchor_violation:
                print(f"   !! ANCHOR VIOLATION: an anchor is in the leaving set")

    # Demo: cascade from StreamPanel
    for vessel_name in ev.sym.vessels:
        print(f"\n-- CASCADE TEST: {TT.PHI_FATAL.name} from '{vessel_name}'")
        result = ev.cascade(vessel_name, TT.PHI_FATAL, cause="test")
        if result.reached:
            for dst, kind in result.reached:
                print(f"   -> {dst}: {FAILURE_NAMES.get(kind, str(kind))}")
        else:
            print("   (failure contained — no seams declared to propagate through)")
        if result.blocked_at:
            for dst, seam in result.blocked_at:
                print(f"   blocked at '{seam}' before reaching '{dst}'")


if __name__ == "__main__":
    main()

"""
GUILDS v2 Live Builder
======================
Compiles a .guilds spec into a fully self-contained interactive HTML SPA.

Pipeline:
  1. Parse the spec (guilds_parser)
  2. Evaluate all 6 phases (guilds_evaluator)
  3. Pre-compute all adjacent transition plans
  4. Pre-compute all cascade paths for all vessel × failure-kind pairs
  5. Serialize everything into a JSON bundle
  6. Embed bundle + SPA runtime into a single HTML file

The SPA runtime is pure JS with no external dependencies:
  Store         — current phase, flow clocks, active failures, event log
  Differ        — shallow tree diff (visibility / style / certainty changes)
  Patcher       — incremental DOM reconciliation via the diff
  Animator      — TransitionPlan → CSS class sequencing with real setTimeout
  FlowClock     — setInterval per flow; stall detection; terminal detection
  FailurePanel  — failure injection UI; shows cascade result
  EventBus      — internal EventTarget; optional SSE source
  PhaseSelector — phase tab UI

Usage:
  python3 guilds_live_builder.py <spec.guilds> [--out path.html]
  python3 guilds_live_builder.py --example [--out path.html]
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from typing import Any, Optional

from guilds_parser import parse_source, LexError, ParseError, TT
from guilds_evaluator import (
    Evaluator, EvalContext, SurfaceModel, ActiveFailure,
    PHASE_NAMES, FAILURE_NAMES,
    PHASE_ORIENT, PHASE_EXECUTE, PHASE_VERIFY,
    PHASE_INTEGRATE, PHASE_RECOVER, PHASE_IDLE,
    ALL_PHASES,
)
from guilds_renderer import (
    RenderTreeBuilder, HTMLRenderer,
    CERTAINTY_STYLE, FAILURE_STYLE, FAILURE_STYLE as FAIL_STYLE,
    PHASE_COLOUR, NodeKind,
)


# ---------------------------------------------------------------------------
# SECTION 1: SERIALIZER  (RenderTree → JSON-serialisable dict)
# ---------------------------------------------------------------------------

def serialise_style(s) -> dict:
    return {
        "opacity":       round(s.opacity, 3),
        "flexGrow":      round(s.flex_grow, 3),
        "fontWeight":    s.font_weight,
        "fontSizeEm":    round(s.font_size_em, 3),
        "borderPx":      s.border_px,
        "borderColour":  s.border_colour,
        "bgColour":      s.bg_colour,
        "fgColour":      s.fg_colour,
        "accentColour":  s.accent_colour,
        "isDominant":    s.is_dominant,
        "isAnchor":      s.is_anchor,
        "isStalled":     s.is_stalled,
        "hasFailure":    s.has_failure,
        "failureColour": s.failure_colour,
        "axis":          s.axis,
        "gapEm":         round(s.gap_em, 3),
    }


def serialise_certainty(c) -> Optional[dict]:
    if c is None:
        return None
    cs = CERTAINTY_STYLE.get(c.grade, CERTAINTY_STYLE["unknown"])
    return {
        "grade":          c.grade,
        "rank":           c.rank,
        "displayWeight":  round(c.display_weight, 3),
        "stakes":         c.stakes,
        "isStale":        c.is_stale,
        "elapsedS":       round(c.elapsed_s, 3) if c.elapsed_s else None,
        "provenanceHops": c.provenance_hops,
        "colour":         cs[0],
        "symbol":         cs[2],
        "label":          cs[3],
    }


def serialise_flow_state(fs) -> Optional[dict]:
    if fs is None:
        return None
    return {
        "flowName":      fs.flow_name,
        "currentStep":   fs.current_step,
        "stepName":      fs.step_name,
        "stateKind":     fs.state_kind,
        "elapsedMs":     round(fs.elapsed_ms, 1),
        "stalled":       fs.stalled,
        "stallElapsedMs":round(fs.stall_elapsed_ms, 1),
        "terminal":      fs.terminal,
    }


def serialise_failure(af) -> Optional[dict]:
    if af is None:
        return None
    fstyle = FAIL_STYLE.get(af.kind, ("#dc2626", "Φ?", "unknown"))
    return {
        "kind":          af.kind.name,
        "origin":        af.origin,
        "cause":         af.cause,
        "cascadeBlocked":af.cascade_blocked,
        "propagatedTo":  af.propagated_to,
        "colour":        fstyle[0],
        "symbol":        fstyle[1],
        "label":         FAILURE_NAMES.get(af.kind, "unknown"),
    }


def serialise_node(node) -> dict:
    return {
        "name":            node.name,
        "kind":            node.kind.name.lower(),
        "visibility":      node.visibility,
        "style":           serialise_style(node.style),
        "label":           node.label,
        "subtitle":        node.subtitle,
        "certainty":       serialise_certainty(node.certainty),
        "flowState":       serialise_flow_state(node.flow_state),
        "activeFailure":   serialise_failure(node.active_failure),
        "children":        [serialise_node(c) for c in node.children],
        "arrangementKind": node.arrangement_kind,
        "meta":            {k: v for k, v in node.meta.items()
                            if isinstance(v, (str, int, float, bool, list, type(None)))},
    }


def serialise_tree(tree) -> dict:
    return {
        "phase":          tree.phase,
        "phaseName":      tree.phase_name,
        "phaseColour":    tree.phase_colour,
        "lambdaOmega":    round(tree.lambda_omega, 2),
        "budgetWarnings": tree.budget_warnings,
        "symbolErrors":   tree.symbol_errors,
        "roots":          [serialise_node(r) for r in tree.roots],
        "activeFailures": [serialise_failure(af) for af in tree.active_failures],
    }


def serialise_transition(plan) -> dict:
    return {
        "fromPhase":       plan.from_phase,
        "fromPhaseName":   PHASE_NAMES.get(plan.from_phase, plan.from_phase),
        "toPhase":         plan.to_phase,
        "toPhaseName":     PHASE_NAMES.get(plan.to_phase,   plan.to_phase),
        "durationMs":      plan.duration_ms,
        "easing":          plan.easing,
        "sequenceKind":    plan.sequence_kind,
        "staggerMs":       plan.stagger_ms,
        "anchors":         plan.anchors,
        "leaving":         plan.leaving,
        "arriving":        plan.arriving,
        "stable":          plan.stable,
        "dominantChange":  list(plan.dominant_change) if plan.dominant_change else None,
        "anchorViolation": plan.anchor_violation,
    }


# ---------------------------------------------------------------------------
# SECTION 2: BUNDLE COMPILER
# ---------------------------------------------------------------------------

PHASE_ORDER = [PHASE_ORIENT, PHASE_EXECUTE, PHASE_VERIFY,
               PHASE_INTEGRATE, PHASE_RECOVER, PHASE_IDLE]

FAILURE_KINDS_UI = [
    ("PHI_DEGRADED", "Φ↓ degraded"),
    ("PHI_BLOCKED",  "Φ⊣ blocked"),
    ("PHI_PARTIAL",  "Φ½ partial"),
    ("PHI_STALE",    "Φ⌛ stale"),
    ("PHI_RECOVER",  "Φ⟳ recovering"),
    ("PHI_FATAL",    "Φ✗ FATAL"),
    ("PHI_UNKNOWN",  "Φ? unknown"),
]

def build_bundle(source: str, source_name: str) -> dict:
    """
    Evaluate all phases, pre-compute all transitions and cascades.
    Returns a JSON-serialisable bundle dict.
    """
    program, type_violations = parse_source(source, source_name)

    # ---- Per-phase render trees ----------------------------------------
    phase_trees: dict[str, dict] = {}
    evaluators:  dict[str, Evaluator] = {}

    for phase_sig in PHASE_ORDER:
        ctx = EvalContext(phase=phase_sig, now=time.time())
        ev  = Evaluator(program, ctx)
        model = ev.evaluate()
        builder = RenderTreeBuilder(model, ev)
        tree = builder.build()
        phase_trees[phase_sig]  = serialise_tree(tree)
        evaluators[phase_sig] = ev

    # Use the execute evaluator as the canonical one for symbol info
    canon_ev = evaluators.get(PHASE_EXECUTE) or list(evaluators.values())[0]

    # ---- Transition plans for every adjacent pair ----------------------
    transitions: dict[str, dict] = {}
    for i in range(len(PHASE_ORDER) - 1):
        fp = PHASE_ORDER[i]
        tp = PHASE_ORDER[i + 1]
        for stage_name in canon_ev.sym.stages:
            plan = canon_ev.transition_plan(stage_name, fp, tp)
            if plan:
                key = f"{PHASE_NAMES[fp]}->{PHASE_NAMES[tp]}:{stage_name}"
                transitions[key] = serialise_transition(plan)
        # Also backward
        plan = None
        for stage_name in canon_ev.sym.stages:
            plan = canon_ev.transition_plan(stage_name, tp, fp)
            if plan:
                key = f"{PHASE_NAMES[tp]}->{PHASE_NAMES[fp]}:{stage_name}"
                transitions[key] = serialise_transition(plan)

    # ---- Cascade index: vessel × failure → CascadeResult --------------
    cascade_index: dict[str, dict] = {}
    tt_map = {t.name: t for t in TT}

    for vessel_name in canon_ev.sym.vessels:
        for tt_name, _ in FAILURE_KINDS_UI:
            tt = tt_map.get(tt_name)
            if tt is None:
                continue
            result = canon_ev.cascade(vessel_name, tt)
            key = f"{vessel_name}:{tt_name}"
            cascade_index[key] = {
                "origin":        result.origin,
                "originFailure": result.origin_failure.name,
                "reached":  [[r[0], r[1].name] for r in result.reached],
                "blockedAt":[[b[0], b[1]]       for b in result.blocked_at],
                "path":     result.path,
            }

    # ---- Declarations summary (for UI panels) --------------------------
    decls = {
        "vessels": list(canon_ev.sym.vessels.keys()),
        "claims":  list(canon_ev.sym.claims.keys()),
        "affords": list(canon_ev.sym.affords.keys()),
        "stages":  list(canon_ev.sym.stages.keys()),
        "flows":   list(canon_ev.sym.flows.keys()),
        "seams":   list(canon_ev.sym.seams.keys()),
        "bonds":   list(canon_ev.sym.bonds.keys()),
    }

    # ---- Flow declarations summary ------------------------------------
    flow_meta: dict[str, dict] = {}
    for name, flow in canon_ev.sym.flows.items():
        steps = [{"name": s.name,
                  "duration": str(s.duration),
                  "state": str(s.state)} for s in flow.steps]
        stall = None
        if flow.on_stall:
            stall = {
                "thresholdKind":  flow.on_stall.threshold.kind,
                "thresholdValue": flow.on_stall.threshold.value,
                "surface":        flow.on_stall.surface.name,
                "recovery":       flow.on_stall.recovery,
            }
        flow_meta[name] = {
            "steps":    steps,
            "on_stall": stall,
            "terminal": flow.terminal,
        }

    # ---- Type violations summary ---------------------------------------
    violations = [
        {"code": v.code, "severity": v.severity,
         "node": v.node_name, "message": v.message}
        for v in type_violations
    ]

    return {
        "sourceName":   source_name,
        "compiledAt":   time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "phases":       phase_trees,
        "phaseOrder":   [PHASE_NAMES[p] for p in PHASE_ORDER],
        "phaseSigils":  {PHASE_NAMES[p]: p for p in PHASE_ORDER},
        "phaseColours": PHASE_COLOUR,
        "transitions":  transitions,
        "cascadeIndex": cascade_index,
        "failureKinds": FAILURE_KINDS_UI,
        "failureStyles":{
            tt_name: {
                "colour": FAIL_STYLE[tt][0],
                "symbol": FAIL_STYLE[tt][1],
                "label":  FAIL_STYLE[tt][2],
            }
            for tt_name, tt in [(t.name, t) for t in FAIL_STYLE]
        },
        "declarations": decls,
        "flowMeta":     flow_meta,
        "violations":   violations,
    }


# ---------------------------------------------------------------------------
# SECTION 3: SPA TEMPLATE
# ---------------------------------------------------------------------------

SPA_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GUILDS Live · {source_name}</title>
<style>
/* ---- Reset ---- */
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html,body{{height:100%;overflow:hidden}}
body{{
  font-family:'JetBrains Mono','Fira Code',monospace;
  background:#080e1a;color:#e2e8f0;
  display:flex;flex-direction:column;
}}

/* ---- Layout ---- */
#app{{display:flex;flex-direction:column;height:100vh;overflow:hidden}}
#topbar{{
  display:flex;align-items:center;gap:.75rem;padding:.5rem 1rem;
  background:#0a1022;border-bottom:1px solid #1e293b;
  flex-shrink:0;flex-wrap:wrap;min-height:52px;
}}
#main{{display:flex;flex:1;overflow:hidden}}
#surface-scroll{{flex:1;overflow-y:auto;padding:1rem;}}
#surface{{display:flex;flex-direction:column;gap:.75rem;min-height:100%;}}
#sidepanel{{
  width:320px;flex-shrink:0;display:flex;flex-direction:column;
  border-left:1px solid #1e293b;overflow:hidden;
}}
#sidepanel-tabs{{
  display:flex;border-bottom:1px solid #1e293b;flex-shrink:0;
}}
.stab{{
  flex:1;padding:.4rem;font-size:.72rem;font-weight:600;
  background:none;border:none;color:#475569;cursor:pointer;
  text-transform:uppercase;letter-spacing:.05em;
  border-bottom:2px solid transparent;transition:all .15s;
}}
.stab:hover{{color:#94a3b8}}
.stab.active{{color:#3b82f6;border-bottom-color:#3b82f6}}
.stab-panel{{display:none;flex:1;overflow-y:auto;padding:.75rem;}}
.stab-panel.active{{display:flex;flex-direction:column;gap:.5rem;}}

/* ---- Phase tabs ---- */
#phase-tabs{{display:flex;gap:.35rem;align-items:center;}}
.ptab{{
  padding:.25rem .7rem;border-radius:4px;border:1px solid #1e293b;
  background:none;color:#475569;cursor:pointer;font-size:.75rem;
  font-family:inherit;font-weight:600;text-transform:lowercase;
  transition:all .15s;
}}
.ptab:hover{{border-color:#334155;color:#94a3b8}}
.ptab.active{{color:#fff;}}

/* ---- Top bar widgets ---- */
#lw-chip{{
  display:flex;align-items:center;gap:.3rem;
  font-size:.75rem;padding:.2rem .5rem;
  border:1px solid #1e293b;border-radius:4px;
  color:#94a3b8;
}}
#lw-value{{font-weight:700;}}
.lw-ok{{color:#22c55e}}
.lw-warn{{color:#ef4444}}
#phase-label{{
  display:flex;align-items:center;gap:.4rem;
  font-size:.82rem;font-weight:700;color:#f1f5f9;
  margin-left:.5rem;
}}
#phase-dot{{
  width:8px;height:8px;border-radius:50%;
  background:var(--phase-colour,#3b82f6);
  animation:dot-pulse 2s infinite;
}}
@keyframes dot-pulse{{0%,100%{{opacity:1}}50%{{opacity:.3}}}}
#elapsed-clock{{
  font-size:.72rem;color:#475569;margin-left:auto;
}}

/* ---- GUILDS Nodes ---- */
.gnode{{
  border-radius:6px;padding:.75rem;display:flex;flex-direction:column;
  gap:.5rem;position:relative;
  transition:opacity .25s cubic-bezier(.4,0,.2,1),
             transform .25s cubic-bezier(.4,0,.2,1),
             border-color .25s cubic-bezier(.4,0,.2,1),
             box-shadow .25s cubic-bezier(.4,0,.2,1);
}}
.gnode.kind-stage{{border-width:2px;border-style:solid;}}
.gnode.kind-vessel{{border-width:1px;border-style:solid;}}
.gnode.kind-claim{{border-width:1px;border-style:solid;}}
.gnode.kind-flow{{border-width:1px;border-style:dashed;}}
.gnode.kind-failure{{border-width:2px;border-style:solid;}}
.gnode.kind-afford{{border-radius:3px;border-width:1px;border-style:solid;}}

.gnode.vis-fade{{opacity:.35!important;filter:saturate(.5)}}
.gnode.vis-hide{{display:none!important}}
.gnode.is-dominant{{box-shadow:0 0 0 2px var(--accent,#3b82f6),0 8px 32px -8px color-mix(in srgb,var(--accent,#3b82f6) 35%,transparent);}}
.gnode.is-anchor{{position:sticky;top:.5rem;z-index:10;}}
.gnode.has-failure{{animation:failure-pulse 1.5s infinite;}}
@keyframes failure-pulse{{0%,100%{{box-shadow:0 0 0 0 transparent}}50%{{box-shadow:0 0 0 4px color-mix(in srgb,var(--failcol,#dc2626) 30%,transparent)}}}}
.gnode.is-stalled{{border-style:dashed;animation:stall-flash 1s infinite;}}
@keyframes stall-flash{{0%,100%{{border-color:var(--accent,#f59e0b)}}50%{{border-color:#7c5a14}}}}

/* Leaving / arriving transition classes */
.g-leaving{{animation:g-leave .25s cubic-bezier(.4,0,.2,1) both}}
@keyframes g-leave{{from{{opacity:var(--node-op,1);transform:translateY(0)}}to{{opacity:0;transform:translateY(-6px)}}}}
.g-arriving{{animation:g-arrive .25s cubic-bezier(.4,0,.2,1) both}}
@keyframes g-arrive{{from{{opacity:0;transform:translateY(6px)}}to{{opacity:var(--node-op,1);transform:translateY(0)}}}}

/* ---- Node header ---- */
.nheader{{display:flex;flex-direction:column;gap:.2rem;}}
.ntitle{{display:flex;align-items:center;gap:.35rem;flex-wrap:wrap;}}
.nname{{font-weight:700;font-size:.9rem;color:var(--accent,#e2e8f0);}}
.nsub{{font-size:.72rem;color:#475569;}}
.nbadge{{
  display:inline-flex;align-items:center;padding:.08rem .35rem;
  border-radius:3px;font-size:.68rem;font-weight:600;
  background:#1e293b;color:#64748b;
}}
.nbadge.dominant{{background:#1e3a5f;color:var(--accent,#60a5fa);}}
.nbadge.anchor{{background:#0c4a6e;color:#38bdf8;}}
.nbadge.stalled{{background:#431407;color:#fb923c;}}
.nbadge.failure{{background:#450a0a;color:#f87171;}}

/* ---- Children ---- */
.nchildren{{display:flex;gap:.5rem;flex-wrap:wrap;margin-top:.25rem;}}
.nchildren.axis-column{{flex-direction:column;}}
.nchildren.axis-row{{flex-direction:row;}}
.nchildren>.gnode{{flex:1 1 180px;}}

/* ---- Certainty widget ---- */
.cert-widget{{
  border-radius:4px;padding:.5rem .6rem;
  background:color-mix(in srgb,var(--cert-col,#3b82f6) 6%,#0f172a);
  border:1px solid color-mix(in srgb,var(--cert-col,#3b82f6) 20%,transparent);
  font-size:.78rem;display:flex;flex-direction:column;gap:.3rem;
}}
.cert-row{{display:flex;align-items:center;gap:.4rem;}}
.cert-sym{{font-size:1em;font-weight:700;color:var(--cert-col,#3b82f6);}}
.cert-grade{{font-weight:700;color:var(--cert-col,#3b82f6);}}
.cert-stakes{{
  margin-left:auto;padding:.06rem .3rem;border-radius:3px;
  font-size:.68rem;font-weight:600;
}}
.stakes-low{{background:#14532d;color:#86efac}}
.stakes-medium{{background:#7c2d12;color:#fdba74}}
.stakes-high{{background:#7c2d12;color:#f97316}}
.stakes-critical{{background:#450a0a;color:#ef4444;font-weight:900}}
.stakes-context_dependent{{background:#1e293b;color:#94a3b8}}
.bar-track{{height:3px;background:#1e293b;border-radius:2px;overflow:hidden;margin:.1rem 0;}}
.bar-fill{{height:100%;border-radius:2px;transition:width .4s ease;}}
.cert-meta{{font-size:.68rem;color:#475569;}}
.stale-banner{{
  background:#431407;color:#fb923c;padding:.2rem .4rem;
  border-radius:3px;font-weight:700;font-size:.72rem;
}}

/* ---- Flow widget ---- */
.flow-widget{{
  border-radius:4px;padding:.5rem .6rem;border:1px solid #1e293b;
  background:#0f172a;font-size:.78rem;display:flex;flex-direction:column;gap:.3rem;
}}
.flow-row{{display:flex;align-items:center;gap:.4rem;}}
.flow-spinner{{display:inline-block;animation:spin 1s linear infinite;color:#3b82f6}}
.flow-stall .flow-spinner{{color:#f59e0b;animation:none;}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
.flow-step{{font-weight:700;color:#38bdf8;}}
.flow-kind{{color:#64748b;}}
.flow-ms{{margin-left:auto;color:#334155;font-size:.68rem;}}
.flow-bar-fill{{background:#3b82f6;}}
.flow-bar-stall{{background:#f59e0b;animation:none;}}
.stall-warn{{color:#fb923c;font-weight:700;font-size:.72rem;margin-top:.15rem;}}
.flow-terminal{{color:#4ade80;font-size:.78rem;padding:.2rem;}}

/* ---- Failure widget ---- */
.fail-widget{{
  border-radius:4px;padding:.5rem .6rem;
  border:2px solid var(--failcol,#dc2626);
  background:color-mix(in srgb,var(--failcol,#dc2626) 8%,#0a0000);
  font-size:.78rem;display:flex;flex-direction:column;gap:.25rem;
  animation:failure-pulse 1.5s infinite;
}}
.fail-header{{display:flex;align-items:center;gap:.4rem;color:var(--failcol,#dc2626);font-weight:700;}}
.fail-cause{{color:#94a3b8;font-size:.72rem;}}
.fail-cascade{{display:flex;flex-wrap:wrap;gap:.2rem;align-items:center;font-size:.68rem;color:#94a3b8;}}
.cascade-chip{{background:#450a0a;color:#fca5a5;padding:.04rem .25rem;border-radius:2px;}}
.fail-blocked{{color:#f59e0b;font-size:.68rem;}}

/* ---- Side panel ---- */
.sp-section{{display:flex;flex-direction:column;gap:.35rem;}}
.sp-label{{
  font-size:.68rem;font-weight:700;text-transform:uppercase;
  letter-spacing:.06em;color:#334155;margin-bottom:.15rem;
}}
.sp-row{{
  display:flex;align-items:center;gap:.35rem;flex-wrap:wrap;
}}
.sp-select{{
  flex:1;background:#0f172a;border:1px solid #1e293b;border-radius:4px;
  color:#94a3b8;font-family:inherit;font-size:.75rem;padding:.25rem .4rem;
}}
.sp-btn{{
  padding:.25rem .55rem;border-radius:4px;border:1px solid;
  font-family:inherit;font-size:.72rem;font-weight:600;cursor:pointer;
  transition:all .15s;background:none;
}}
.sp-btn.fire{{border-color:#dc2626;color:#f87171;}}
.sp-btn.fire:hover{{background:#450a0a;}}
.sp-btn.reset{{border-color:#334155;color:#64748b;}}
.sp-btn.reset:hover{{background:#1e293b;}}

/* ---- Cascade result ---- */
#cascade-result{{
  background:#0f172a;border:1px solid #1e293b;border-radius:4px;
  padding:.5rem;font-size:.72rem;min-height:48px;
  display:flex;flex-direction:column;gap:.2rem;
}}
.cr-path{{display:flex;align-items:center;gap:.2rem;flex-wrap:wrap;}}
.cr-vessel{{
  background:#1e293b;border-radius:2px;padding:.05rem .25rem;
  color:#94a3b8;
}}
.cr-arrow{{color:#475569;}}
.cr-blocked{{color:#f59e0b;font-size:.68rem;}}
.cr-empty{{color:#334155;font-style:italic;}}

/* ---- Event log ---- */
#event-log{{display:flex;flex-direction:column;gap:.2rem;}}
.log-entry{{
  display:flex;gap:.4rem;align-items:flex-start;
  font-size:.68rem;padding:.2rem .3rem;border-radius:3px;
  border-left:2px solid transparent;
}}
.log-entry.phase{{border-left-color:#3b82f6;}}
.log-entry.failure{{border-left-color:#ef4444;background:#1c0000;}}
.log-entry.flow{{border-left-color:#f59e0b;}}
.log-entry.stall{{border-left-color:#f97316;background:#1c0a00;}}
.log-entry.info{{border-left-color:#334155;}}
.log-ts{{color:#334155;flex-shrink:0;}}
.log-msg{{color:#94a3b8;}}
.log-msg b{{color:#e2e8f0;}}

/* ---- Violations panel ---- */
.viol-item{{
  border-radius:3px;padding:.3rem .5rem;font-size:.72rem;
  display:flex;gap:.4rem;align-items:flex-start;
}}
.viol-item.error{{background:#1c0000;border-left:2px solid #dc2626;}}
.viol-item.warning{{background:#1c1000;border-left:2px solid #f59e0b;}}
.viol-code{{font-weight:700;flex-shrink:0;}}
.viol-node{{color:#64748b;flex-shrink:0;}}
.viol-msg{{color:#94a3b8;}}

/* ---- Declarations list ---- */
.decl-group{{margin-bottom:.4rem;}}
.decl-kind{{font-size:.68rem;font-weight:700;color:#334155;text-transform:uppercase;margin-bottom:.15rem;}}
.decl-chips{{display:flex;flex-wrap:wrap;gap:.2rem;}}
.decl-chip{{
  background:#111827;border:1px solid #1e293b;border-radius:3px;
  padding:.1rem .3rem;font-size:.68rem;color:#64748b;cursor:default;
}}
.decl-chip:hover{{border-color:#334155;color:#94a3b8;}}

/* ---- Scrollbars ---- */
::-webkit-scrollbar{{width:4px;height:4px}}
::-webkit-scrollbar-track{{background:#080e1a}}
::-webkit-scrollbar-thumb{{background:#1e293b;border-radius:2px}}
</style>
</head>
<body>
<div id="app">

  <!-- TOP BAR -->
  <div id="topbar">
    <div id="phase-tabs"><!-- JS generated --></div>
    <div id="phase-label">
      <div id="phase-dot"></div>
      <span id="phase-name-text">—</span>
    </div>
    <div id="lw-chip">λΩ <span id="lw-value" class="lw-ok">0.0</span></div>
    <div id="flow-indicators"><!-- JS flow chips --></div>
    <div id="elapsed-clock"></div>
  </div>

  <!-- MAIN AREA -->
  <div id="main">
    <div id="surface-scroll">
      <div id="surface"><!-- patched by JS --></div>
    </div>

    <!-- SIDE PANEL -->
    <div id="sidepanel">
      <div id="sidepanel-tabs">
        <button class="stab active" data-panel="inject">Inject</button>
        <button class="stab" data-panel="cascade">Cascade</button>
        <button class="stab" data-panel="log">Log</button>
        <button class="stab" data-panel="info">Info</button>
      </div>
      <!-- Failure injection -->
      <div id="panel-inject" class="stab-panel active">
        <div class="sp-section">
          <div class="sp-label">Trigger failure</div>
          <div class="sp-row">
            <select id="fail-vessel" class="sp-select"></select>
          </div>
          <div class="sp-row">
            <select id="fail-kind" class="sp-select"></select>
            <button class="sp-btn fire" id="btn-fire">Φ Fire</button>
          </div>
          <div class="sp-row">
            <input id="fail-cause" class="sp-select" style="flex:2"
                   placeholder="cause (optional)" value="">
            <button class="sp-btn reset" id="btn-clear-failures">✕ Clear</button>
          </div>
        </div>
        <div class="sp-section" style="margin-top:.5rem">
          <div class="sp-label">Active failures</div>
          <div id="active-failures-list" style="font-size:.72rem;color:#334155;font-style:italic">none</div>
        </div>
      </div>
      <!-- Cascade viewer -->
      <div id="panel-cascade" class="stab-panel">
        <div class="sp-section">
          <div class="sp-label">Cascade preview</div>
          <div class="sp-row">
            <select id="cas-vessel" class="sp-select"></select>
            <select id="cas-kind"   class="sp-select"></select>
          </div>
        </div>
        <div id="cascade-result"><span class="cr-empty">Select vessel + failure kind</span></div>
      </div>
      <!-- Event log -->
      <div id="panel-log" class="stab-panel">
        <div id="event-log"><span style="color:#334155;font-size:.72rem;font-style:italic">Events will appear here…</span></div>
      </div>
      <!-- Info -->
      <div id="panel-info" class="stab-panel">
        <div class="sp-section">
          <div class="sp-label">Type violations</div>
          <div id="violations-list"></div>
        </div>
        <div class="sp-section" style="margin-top:.5rem">
          <div class="sp-label">Declarations</div>
          <div id="declarations-list"></div>
        </div>
      </div>
    </div>
  </div>
</div>

<script>
/* ============================================================
   GUILDS Live Runtime
   ============================================================ */

// ---- Bundle (injected by Python) --------------------------------
const BUNDLE = {bundle_json};

// ---- Store -------------------------------------------------------
const Store = {{
  phase: BUNDLE.phaseOrder[1] || BUNDLE.phaseOrder[0],  // default: execute
  failures: [],          // [{{kind,origin,cause,cascadeResult}}]
  flowClocks: {{}},       // {{flowName: {{startMs, stallStartMs, stalled, terminal, stepIdx, stepName}}}}
  startMs: Date.now(),
  listeners: [],

  get phaseData() {{ return BUNDLE.phases[this._phaseSigil()]; }},
  _phaseSigil() {{ return BUNDLE.phaseSigils[this.phase]; }},

  dispatch(event, payload) {{
    this.listeners.forEach(fn => fn(event, payload));
    EventLog.push(event, payload);
  }},
  subscribe(fn) {{ this.listeners.push(fn); }},

  setPhase(phaseName) {{
    const old = this.phase;
    this.phase = phaseName;
    this.dispatch('phase', {{from: old, to: phaseName}});
  }},

  addFailure(kind, origin, cause, cascadeResult) {{
    this.failures.push({{kind, origin, cause, cascadeResult, ts: Date.now()}});
    this.dispatch('failure', {{kind, origin, cause}});
  }},

  clearFailures() {{
    this.failures = [];
    this.dispatch('failure-clear', {{}});
  }},
}};

// ---- Event log ---------------------------------------------------
const EventLog = {{
  entries: [],
  maxEntries: 120,
  push(type, payload) {{
    const t = ((Date.now() - Store.startMs) / 1000).toFixed(1);
    this.entries.unshift({{type, payload, t}});
    if (this.entries.length > this.maxEntries) this.entries.pop();
    this._render();
  }},
  _render() {{
    const el = document.getElementById('event-log');
    if (!el) return;
    el.innerHTML = this.entries.map(e => {{
      const cls = e.type === 'phase' ? 'phase'
                : e.type === 'failure' ? 'failure'
                : e.type === 'stall' ? 'stall'
                : e.type === 'flow' ? 'flow' : 'info';
      const msg = fmtPayload(e.type, e.payload);
      return `<div class="log-entry ${{cls}}"><span class="log-ts">${{e.t}}s</span><span class="log-msg">${{msg}}</span></div>`;
    }}).join('');
  }},
}};

function fmtPayload(type, p) {{
  if (type === 'phase') return `phase <b>${{p.from}}</b> → <b>${{p.to}}</b>`;
  if (type === 'failure') return `<b>Φ ${{p.kind.replace('PHI_','')}}</b> in <b>${{p.origin}}</b> — ${{p.cause || '?'}}`;
  if (type === 'failure-clear') return 'all failures cleared';
  if (type === 'stall') return `⚠ stall in <b>${{p.flow}}</b> step ${{p.step}} +${{p.ms.toFixed(0)}}ms`;
  if (type === 'flow-advance') return `flow <b>${{p.flow}}</b> → step ${{p.step}}`;
  if (type === 'flow-terminal') return `flow <b>${{p.flow}}</b> terminal: ${{p.terminal}}`;
  return JSON.stringify(p).slice(0,80);
}}

// ---- Differ + Patcher --------------------------------------------
// Key insight: we never destroy the whole tree. We diff old/new node
// data and patch only what changed: visibility, style vars, inner HTML
// of leaf widgets. This keeps DOM mutations minimal.

const nodeCache = new Map();  // name → {{el, lastData}}

function buildNodeEl(node, depth) {{
  const el = document.createElement('div');
  el.id = 'gn-' + CSS.escape(node.name);
  el.setAttribute('data-guilds-id', node.name);
  applyNodeStyle(el, node);
  el.innerHTML = nodeInnerHTML(node);
  nodeCache.set(node.name, {{el, lastData: JSON.stringify(nodeKey(node))}});

  // Recurse children into .nchildren
  const nc = el.querySelector('.nchildren');
  if (nc && node.children && node.children.length) {{
    node.children.forEach(child => {{
      nc.appendChild(buildNodeEl(child, depth + 1));
    }});
  }}
  return el;
}}

function patchNodeEl(el, node) {{
  const key = JSON.stringify(nodeKey(node));
  const cached = nodeCache.get(node.name);
  const dirty = !cached || cached.lastData !== key;

  applyNodeStyle(el, node);

  if (dirty) {{
    // Patch header + content (not children div — that's handled recursively)
    const headerEl  = el.querySelector(':scope > .nheader');
    const contentEl = el.querySelector(':scope > .ncontent');
    if (headerEl)  headerEl.outerHTML  = nodeHeaderHTML(node);
    if (contentEl) contentEl.outerHTML = nodeContentHTML(node);
    nodeCache.set(node.name, {{el, lastData: key}});
  }}

  // Recurse children
  const nc = el.querySelector(':scope > .nchildren');
  if (nc && node.children) {{
    patchChildren(nc, node.children);
  }}
}}

function patchChildren(container, children) {{
  const rendered = [...container.children];
  const childMap = new Map(rendered.map(e => [e.getAttribute('data-guilds-id'), e]));

  // Add / patch
  const newOrder = [];
  children.forEach(child => {{
    let el = childMap.get(child.name);
    if (!el) {{
      el = buildNodeEl(child, 0);
    }} else {{
      patchNodeEl(el, child);
      childMap.delete(child.name);
    }}
    newOrder.push(el);
  }});

  // Remove stale
  childMap.forEach(el => el.remove());

  // Re-order
  newOrder.forEach((el, i) => {{
    if (container.children[i] !== el) container.insertBefore(el, container.children[i] || null);
  }});
}}

function reconcile(roots) {{
  const surface = document.getElementById('surface');
  patchChildren(surface, roots);
}}

// ---- Style application -------------------------------------------
function applyNodeStyle(el, node) {{
  const s = node.style;
  el.className = nodeClasses(node);
  el.style.setProperty('--accent',   s.accentColour);
  el.style.setProperty('--node-op',  s.opacity);
  el.style.setProperty('--failcol',  s.failureColour || '#dc2626');
  el.style.setProperty('--cert-col', node.certainty ? node.certainty.colour : '#3b82f6');
  el.style.opacity       = s.opacity;
  el.style.flexGrow      = s.flexGrow;
  el.style.fontWeight    = s.fontWeight;
  el.style.fontSize      = s.fontSizeEm + 'em';
  el.style.border        = `${{s.borderPx}}px solid ${{s.borderColour}}`;
  el.style.background    = s.bgColour;
  el.style.color         = s.fgColour;
  el.style.gap           = s.gapEm + 'rem';
}}

function nodeClasses(node) {{
  const cls = ['gnode', 'kind-' + node.kind];
  if (node.visibility === 'fade') cls.push('vis-fade');
  if (node.visibility === 'hide') cls.push('vis-hide');
  if (node.style.isDominant)   cls.push('is-dominant');
  if (node.style.isAnchor)     cls.push('is-anchor');
  if (node.style.hasFailure)   cls.push('has-failure');
  if (node.style.isStalled)    cls.push('is-stalled');
  return cls.join(' ');
}}

function nodeKey(node) {{
  // Minimal key for dirty-checking; excludes children
  return {{
    vis: node.visibility,
    dom: node.style.isDominant,
    anch: node.style.isAnchor,
    hf: node.style.hasFailure,
    stall: node.style.isStalled,
    cert: node.certainty ? node.certainty.grade + node.certainty.isStale : null,
    flow: node.flowState ? node.flowState.stalled + node.flowState.terminal + Math.floor(node.flowState.elapsedMs / 500) : null,
    fail: node.activeFailure ? node.activeFailure.kind : null,
    sub: node.subtitle,
  }};
}}

// ---- Node HTML builders ------------------------------------------
function nodeInnerHTML(node) {{
  return nodeHeaderHTML(node) + nodeContentHTML(node) + nodeChildrenHTML(node);
}}

function nodeHeaderHTML(node) {{
  const s = node.style;
  const badges = [];
  if (node.kind !== 'claim') {{
    badges.push(`<span class="nbadge">${{h(node.kind)}}</span>`);
  }}
  if (s.isDominant)  badges.push(`<span class="nbadge dominant">◉ dominant</span>`);
  if (s.isAnchor)    badges.push(`<span class="nbadge anchor">⚓ anchor</span>`);
  if (s.isStalled)   badges.push(`<span class="nbadge stalled">⚠ stalled</span>`);
  if (s.hasFailure)  badges.push(`<span class="nbadge failure">Φ failure</span>`);
  const sub = node.subtitle ? `<div class="nsub">${{h(node.subtitle)}}</div>` : '';
  return `<div class="nheader">
    <div class="ntitle"><span class="nname" style="color:${{h(s.accentColour)}}">${{h(node.label)}}</span>${{badges.join('')}}</div>
    ${{sub}}
  </div>`;
}}

function nodeContentHTML(node) {{
  const parts = [];
  if (node.certainty)    parts.push(certHTML(node.certainty));
  if (node.flowState)    parts.push(flowHTML(node.flowState));
  if (node.activeFailure) parts.push(failHTML(node.activeFailure));
  return parts.length ? `<div class="ncontent">${{parts.join('')}}</div>` : '';
}}

function nodeChildrenHTML(node) {{
  if (!node.children || !node.children.length) return '';
  const axisClass = node.style.axis === 'row' ? 'axis-row' : 'axis-column';
  return `<div class="nchildren ${{axisClass}}"></div>`;
}}

function certHTML(c) {{
  const rankPct  = (c.rank / 5) * 100;
  const dwPct    = Math.min(100, (c.displayWeight / 10) * 100);
  const stale    = c.isStale ? `<div class="stale-banner">⌛ STALE</div>` : '';
  return `<div class="cert-widget" style="--cert-col:${{h(c.colour)}}">
    ${{stale}}
    <div class="cert-row">
      <span class="cert-sym">${{h(c.symbol)}}</span>
      <span class="cert-grade">${{h(c.grade)}}</span>
      <span class="cert-stakes stakes-${{h(c.stakes)}}">${{h(c.stakes)}}</span>
    </div>
    <div class="bar-track"><div class="bar-fill" style="width:${{rankPct.toFixed(0)}}%;background:${{h(c.colour)}}"></div></div>
    <div class="bar-track"><div class="bar-fill" style="width:${{dwPct.toFixed(0)}}%;background:${{h(c.colour)}}88"></div></div>
    <div class="cert-meta">rank ${{c.rank}}/5 · dw ${{c.displayWeight.toFixed(2)}} · ${{c.provenanceHops}} hop(s)</div>
  </div>`;
}}

function flowHTML(fs) {{
  if (fs.terminal) return `<div class="flow-terminal">✓ ${{h(fs.terminal)}}</div>`;
  const pct  = Math.min(100, (fs.elapsedMs / Math.max(5000, fs.elapsedMs)) * 100);
  const stallCls = fs.stalled ? ' flow-stall' : '';
  const stallWarn = fs.stalled
    ? `<div class="stall-warn">⚠ STALLED +${{fs.stallElapsedMs.toFixed(0)}}ms past threshold</div>` : '';
  const barCls = fs.stalled ? 'flow-bar-stall' : 'flow-bar-fill';
  return `<div class="flow-widget${{stallCls}}">
    <div class="flow-row">
      <span class="flow-spinner">⟳</span>
      <span class="flow-step">${{h(fs.stepName)}}</span>
      <span class="flow-kind">${{h(fs.stateKind)}}</span>
      <span class="flow-ms">${{fs.elapsedMs.toFixed(0)}}ms</span>
    </div>
    <div class="bar-track"><div class="bar-fill ${{barCls}}" style="width:${{pct.toFixed(0)}}%"></div></div>
    ${{stallWarn}}
  </div>`;
}}

function failHTML(af) {{
  const cascParts = af.propagatedTo && af.propagatedTo.length
    ? `<div class="fail-cascade">→ ${{af.propagatedTo.map(n => `<span class="cascade-chip">${{h(n)}}</span>`).join('')}}</div>` : '';
  const blocked = af.cascadeBlocked
    ? `<div class="fail-blocked">⊣ cascade blocked at seam</div>` : '';
  return `<div class="fail-widget" style="--failcol:${{h(af.colour)}}">
    <div class="fail-header">
      <span>${{h(af.symbol)}}</span>
      <span>${{h(af.label)}}</span>
      <span style="color:#94a3b8;font-size:.8em">in ${{h(af.origin)}}</span>
    </div>
    <div class="fail-cause">cause: ${{h(af.cause || 'unspecified')}}</div>
    ${{cascParts}}${{blocked}}
  </div>`;
}}

function h(s) {{
  return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}

// ---- Animator ----------------------------------------------------
// Applies leaving/arriving classes in sequence per TransitionPlan.
const Animator = {{
  run(fromPhase, toPhase) {{
    // Find relevant transition plans
    const keys = Object.keys(BUNDLE.transitions).filter(k => {{
      const [phaseKey] = k.split(':');
      return phaseKey === `${{fromPhase}}->${{toPhase}}`;
    }});
    if (!keys.length) return;

    const plan = BUNDLE.transitions[keys[0]];
    const {{durationMs, sequenceKind, staggerMs, leaving, arriving, anchors}} = plan;

    const leaveDelay   = sequenceKind === 'anchor_first'  ? durationMs * 0.30
                       : sequenceKind === 'content_first' ? 0 : 0;
    const arriveDelay  = sequenceKind === 'anchor_first'  ? durationMs * 0.60
                       : sequenceKind === 'content_first' ? durationMs * 0.40 : 0;

    leaving.forEach((name, i) => {{
      const el = document.querySelector(`[data-guilds-id="${{name}}"]`);
      if (!el) return;
      const d = leaveDelay + (sequenceKind === 'staggered' ? i * staggerMs : 0);
      setTimeout(() => {{ el.classList.add('g-leaving'); }}, d);
      setTimeout(() => {{ el.classList.remove('g-leaving'); }}, d + durationMs);
    }});

    arriving.forEach((name, i) => {{
      const el = document.querySelector(`[data-guilds-id="${{name}}"]`);
      if (!el) return;
      const d = arriveDelay + (sequenceKind === 'staggered' ? i * staggerMs : 0);
      setTimeout(() => {{ el.classList.add('g-arriving'); }}, d);
      setTimeout(() => {{ el.classList.remove('g-arriving'); }}, d + durationMs);
    }});
  }},
}};

// ---- FlowClock ---------------------------------------------------
// Drives real elapsed-time counters for flow widgets.
// Checks stall thresholds; emits events on stall / terminal.
const FlowClock = {{
  _timers: {{}},

  start(flowName, meta) {{
    this.stop(flowName);
    const state = {{
      startMs: Date.now(),
      stepIdx: 0,
      stepName: meta.steps[0]?.name ?? '?',
      stalled: false,
      stallStart: null,
      terminal: null,
    }};
    Store.flowClocks[flowName] = state;

    this._timers[flowName] = setInterval(() => {{
      this._tick(flowName, meta, state);
    }}, 150);
  }},

  stop(flowName) {{
    if (this._timers[flowName]) {{
      clearInterval(this._timers[flowName]);
      delete this._timers[flowName];
    }}
  }},

  _tick(flowName, meta, state) {{
    if (state.terminal) {{ this.stop(flowName); return; }}
    const elapsedMs = Date.now() - state.startMs;
    const step = meta.steps[state.stepIdx];
    if (!step) {{ state.terminal = 'success'; return; }}

    // Check for timed exit (non-unbounded steps)
    if (step.duration !== 'unbounded') {{
      const durMs = parseDurationMs(step.duration);
      if (durMs && elapsedMs >= durMs) {{
        const next = state.stepIdx + 1;
        if (next >= meta.steps.length) {{
          state.terminal = 'success';
          Store.dispatch('flow-terminal', {{flow: flowName, terminal: 'success'}});
        }} else {{
          state.stepIdx = next;
          state.stepName = meta.steps[next].name;
          state.startMs = Date.now();
          state.stalled = false;
          state.stallStart = null;
          Store.dispatch('flow-advance', {{flow: flowName, step: state.stepName}});
        }}
        return;
      }}
    }}

    // Stall detection for unbounded steps
    if (step.duration === 'unbounded' && meta.on_stall) {{
      const thMs = parseDurationMs(meta.on_stall.thresholdKind + '(' + meta.on_stall.thresholdValue + ')');
      if (thMs && elapsedMs > thMs && !state.stalled) {{
        state.stalled = true;
        state.stallStart = Date.now();
        Store.dispatch('stall', {{flow: flowName, step: state.stepName, ms: elapsedMs - thMs}});
      }}
    }}

    // Update flowClocks so render loop picks up elapsed
    Store.flowClocks[flowName] = Object.assign({{}}, state, {{elapsedMs}});
    // Trigger lightweight re-render of flow widgets
    renderFlowIndicators();
  }},

  startAll() {{
    const meta = BUNDLE.flowMeta;
    Object.entries(meta).forEach(([name, m]) => this.start(name, m));
  }},
}};

function parseDurationMs(durStr) {{
  if (!durStr) return null;
  const s = String(durStr);
  let m;
  if ((m = s.match(/ms\(?(\d+\.?\d*)\)?/)))  return parseFloat(m[1]);
  if ((m = s.match(/s\(?(\d+\.?\d*)\)?/)))   return parseFloat(m[1]) * 1000;
  if ((m = s.match(/m\(?(\d+\.?\d*)\)?/)))   return parseFloat(m[1]) * 60000;
  if ((m = s.match(/h\(?(\d+\.?\d*)\)?/)))   return parseFloat(m[1]) * 3600000;
  return null;
}}

// ---- Phase tab UI ------------------------------------------------
function initPhaseTabs() {{
  const container = document.getElementById('phase-tabs');
  BUNDLE.phaseOrder.forEach(phaseName => {{
    const colour = BUNDLE.phaseColours[phaseName] || '#3b82f6';
    const btn = document.createElement('button');
    btn.className = 'ptab';
    btn.textContent = phaseName;
    btn.style.setProperty('--phase-colour', colour);
    btn.setAttribute('data-phase', phaseName);
    btn.addEventListener('click', () => {{
      const old = Store.phase;
      Animator.run(old, phaseName);
      Store.setPhase(phaseName);
      updatePhaseTabs();
    }});
    container.appendChild(btn);
  }});
  updatePhaseTabs();
}}

function updatePhaseTabs() {{
  document.querySelectorAll('.ptab').forEach(btn => {{
    const active = btn.getAttribute('data-phase') === Store.phase;
    btn.classList.toggle('active', active);
    const colour = BUNDLE.phaseColours[Store.phase] || '#3b82f6';
    if (active) {{
      btn.style.background = colour + '22';
      btn.style.borderColor = colour;
      btn.style.color = colour;
    }} else {{
      btn.style.background = '';
      btn.style.borderColor = '';
      btn.style.color = '';
    }}
  }});
  const colour = BUNDLE.phaseColours[Store.phase] || '#3b82f6';
  document.getElementById('phase-name-text').textContent = Store.phase;
  document.getElementById('phase-dot').style.background = colour;
  document.documentElement.style.setProperty('--phase-colour', colour);
}}

// ---- Side panel tabs ---- ----------------------------------------
function initSidePanelTabs() {{
  document.querySelectorAll('.stab').forEach(btn => {{
    btn.addEventListener('click', () => {{
      document.querySelectorAll('.stab').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.stab-panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      const panel = document.getElementById('panel-' + btn.getAttribute('data-panel'));
      if (panel) panel.classList.add('active');
    }});
  }});
}}

// ---- Failure injection panel ------------------------------------
function initFailurePanel() {{
  const vesselSel = document.getElementById('fail-vessel');
  const kindSel   = document.getElementById('fail-kind');
  BUNDLE.declarations.vessels.forEach(v => {{
    const opt = document.createElement('option');
    opt.value = opt.textContent = v;
    vesselSel.appendChild(opt);
  }});
  BUNDLE.failureKinds.forEach(([name, label]) => {{
    const opt = document.createElement('option');
    opt.value = name; opt.textContent = label;
    kindSel.appendChild(opt);
  }});

  document.getElementById('btn-fire').addEventListener('click', () => {{
    const vessel = vesselSel.value;
    const kind   = kindSel.value;
    const cause  = document.getElementById('fail-cause').value || undefined;
    const cascKey = `${{vessel}}:${{kind}}`;
    const cascResult = BUNDLE.cascadeIndex[cascKey] || {{reached:[], blockedAt:[], path:[vessel]}};
    Store.addFailure(kind, vessel, cause, cascResult);
    renderActiveFailures();
    requestRender();
  }});

  document.getElementById('btn-clear-failures').addEventListener('click', () => {{
    Store.clearFailures();
    renderActiveFailures();
    requestRender();
  }});
}}

function renderActiveFailures() {{
  const el = document.getElementById('active-failures-list');
  if (!Store.failures.length) {{
    el.innerHTML = '<span style="color:#334155;font-style:italic">none</span>';
    return;
  }}
  el.innerHTML = Store.failures.map(f => {{
    const fs = BUNDLE.failureStyles[f.kind] || {{}};
    return `<div style="display:flex;gap:.3rem;align-items:center;font-size:.72rem;margin:.1rem 0">
      <span style="color:${{h(fs.colour || '#dc2626')}}">${{h(fs.symbol || 'Φ?')}}</span>
      <b>${{h(f.origin)}}</b>
      <span style="color:#475569">${{h(f.cause || '')}}</span>
    </div>`;
  }}).join('');
}}

// ---- Cascade viewer ----------------------------------------------
function initCascadePanel() {{
  const vesselSel = document.getElementById('cas-vessel');
  const kindSel   = document.getElementById('cas-kind');
  BUNDLE.declarations.vessels.forEach(v => {{
    vesselSel.appendChild(Object.assign(document.createElement('option'), {{value:v,textContent:v}}));
  }});
  BUNDLE.failureKinds.forEach(([name,label]) => {{
    kindSel.appendChild(Object.assign(document.createElement('option'), {{value:name,textContent:label}}));
  }});

  const update = () => {{
    const key = `${{vesselSel.value}}:${{kindSel.value}}`;
    const r   = BUNDLE.cascadeIndex[key];
    const el  = document.getElementById('cascade-result');
    if (!r) {{ el.innerHTML = '<span class="cr-empty">No data</span>'; return; }}

    const pathHTML = r.path.map((v,i) => {{
      const arrow = i < r.path.length - 1 ? '<span class="cr-arrow">→</span>' : '';
      return `<span class="cr-vessel">${{h(v)}}</span>${{arrow}}`;
    }}).join('');

    const reachedHTML = r.reached.length
      ? r.reached.map(([v,k]) => `<div style="font-size:.68rem;color:#94a3b8">→ <b>${{h(v)}}</b>: ${{h(k.replace('PHI_',''))}}</div>`).join('')
      : '<div style="font-size:.68rem;color:#334155;font-style:italic">(failure contained)</div>';

    const blockedHTML = r.blockedAt.map(([v,seam]) =>
      `<div class="cr-blocked">⊣ blocked by '${{h(seam)}}' before '${{h(v)}}'</div>`
    ).join('');

    el.innerHTML = `<div class="cr-path">${{pathHTML}}</div>${{reachedHTML}}${{blockedHTML}}`;
  }};

  vesselSel.addEventListener('change', update);
  kindSel.addEventListener('change', update);
  update();
}}

// ---- Info panel --------------------------------------------------
function renderInfoPanel() {{
  // Violations
  const vel = document.getElementById('violations-list');
  if (!BUNDLE.violations.length) {{
    vel.innerHTML = '<span style="color:#334155;font-size:.72rem;font-style:italic">✓ No violations</span>';
  }} else {{
    vel.innerHTML = BUNDLE.violations.map(v => {{
      const cls = v.severity === 'error' ? 'error' : 'warning';
      return `<div class="viol-item ${{cls}}">
        <span class="viol-code">[${{h(v.code)}}]</span>
        <span class="viol-node">${{h(v.node)}}</span>
        <span class="viol-msg">${{h(v.message)}}</span>
      </div>`;
    }}).join('');
  }}

  // Declarations
  const del = document.getElementById('declarations-list');
  const decls = BUNDLE.declarations;
  del.innerHTML = Object.entries(decls).filter(([k,v]) => v.length).map(([kind,names]) => {{
    const chips = names.map(n => `<span class="decl-chip">${{h(n)}}</span>`).join('');
    return `<div class="decl-group">
      <div class="decl-kind">${{h(kind)}} (${{names.length}})</div>
      <div class="decl-chips">${{chips}}</div>
    </div>`;
  }}).join('');
}}

// ---- Flow indicators (top bar) -----------------------------------
function renderFlowIndicators() {{
  const el = document.getElementById('flow-indicators');
  const flows = Object.entries(Store.flowClocks);
  if (!flows.length) {{ el.innerHTML = ''; return; }}
  el.innerHTML = flows.map(([name, state]) => {{
    const stalled  = state.stalled;
    const terminal = state.terminal;
    const col      = terminal ? '#22c55e' : stalled ? '#f97316' : '#3b82f6';
    const sym      = terminal ? '✓' : stalled ? '⚠' : '⟳';
    const label    = state.stepName || '?';
    return `<div style="display:flex;align-items:center;gap:.2rem;font-size:.68rem;
                        padding:.1rem .35rem;border-radius:3px;border:1px solid ${{col}}22;
                        background:${{col}}11;color:${{col}}">
      <span style="display:inline-block;animation:${{terminal||stalled?'none':'spin 1s linear infinite'}}">${{sym}}</span>
      ${{h(name)}}:${{h(label)}}
    </div>`;
  }}).join('');
}}

// ---- Main render loop -------------------------------------------
let renderPending = false;

function requestRender() {{
  if (!renderPending) {{
    renderPending = true;
    requestAnimationFrame(doRender);
  }}
}}

function doRender() {{
  renderPending = false;
  const phaseSigil = BUNDLE.phaseSigils[Store.phase];
  const tree = BUNDLE.phases[phaseSigil];
  if (!tree) return;

  // Merge active failures into nodes
  const roots = injectFailures(tree.roots, Store.failures);

  // Inject live flow elapsed times
  injectFlowTimes(roots);

  // Patch DOM
  reconcile(roots);

  // Update λΩ
  const lwEl = document.getElementById('lw-value');
  lwEl.textContent = tree.lambdaOmega.toFixed(1);
  lwEl.className = tree.lambdaOmega > 9 ? 'lw-warn' : 'lw-ok';

  // Update clock
  const clock = ((Date.now() - Store.startMs) / 1000).toFixed(1);
  const el = document.getElementById('elapsed-clock');
  if (el) el.textContent = clock + 's';
}}

function injectFailures(roots, failures) {{
  if (!failures.length) return roots;
  // Deep clone roots so we don't mutate bundle
  const cloned = JSON.parse(JSON.stringify(roots));

  failures.forEach(f => {{
    // Mark origin and propagated vessels
    const affected = new Set([f.origin, ...(f.cascadeResult?.reached?.map(r => r[0]) || [])]);
    markFailure(cloned, affected, f);

    // Add a failure root node if it's a FATAL or it reached multiple vessels
    if (f.kind === 'PHI_FATAL' || (f.cascadeResult?.reached?.length > 0)) {{
      const fs = BUNDLE.failureStyles[f.kind] || {{colour:'#dc2626',symbol:'Φ?',label:'unknown'}};
      const cascPropagated = f.cascadeResult?.reached?.map(r => r[0]) || [];
      cloned.push({{
        name: `__fail_${{f.origin}}_${{f.kind}}_${{f.ts||Date.now()}}`,
        kind: 'failure',
        visibility: 'render',
        style: {{
          opacity: 1, flexGrow: 0, fontWeight: 700, fontSizeEm: 1,
          borderPx: 2, borderColour: fs.colour,
          bgColour: '#1c0000', fgColour: '#fca5a5', accentColour: fs.colour,
          isDominant:false,isAnchor:false,isStalled:false,
          hasFailure:true,failureColour:fs.colour,axis:'column',gapEm:.5,
        }},
        label: `${{fs.symbol}} ${{fs.label}} in ${{f.origin}}`,
        subtitle: `cause: ${{f.cause || 'unspecified'}}`,
        certainty: null,
        flowState: null,
        activeFailure: {{
          kind: f.kind, origin: f.origin, cause: f.cause,
          cascadeBlocked: (f.cascadeResult?.blockedAt?.length > 0),
          propagatedTo: cascPropagated,
          colour: fs.colour, symbol: fs.symbol, label: fs.label,
        }},
        children: [],
        arrangementKind: 'column',
        meta: {{}},
      }});
    }}
  }});
  return cloned;
}}

function markFailure(nodes, affected, f) {{
  const fs = BUNDLE.failureStyles[f.kind] || {{colour:'#dc2626',symbol:'Φ?',label:'unknown'}};
  nodes.forEach(node => {{
    if (affected.has(node.name)) {{
      node.style.hasFailure = true;
      node.style.failureColour = fs.colour;
      node.style.borderColour = fs.colour;
      node.style.bgColour = '#1c0000';
      if (!node.activeFailure) {{
        const cascPropagated = f.cascadeResult?.reached?.map(r => r[0]).filter(n => n !== node.name) || [];
        node.activeFailure = {{
          kind: f.kind, origin: f.origin, cause: f.cause,
          cascadeBlocked: (f.cascadeResult?.blockedAt?.length > 0),
          propagatedTo: cascPropagated,
          colour: fs.colour, symbol: fs.symbol, label: fs.label,
        }};
      }}
    }}
    if (node.children) markFailure(node.children, affected, f);
  }});
}}

function injectFlowTimes(nodes) {{
  nodes.forEach(node => {{
    if (node.kind === 'flow' && Store.flowClocks[node.name]) {{
      const state = Store.flowClocks[node.name];
      if (node.flowState) {{
        node.flowState.elapsedMs    = state.elapsedMs || 0;
        node.flowState.stalled      = state.stalled || false;
        node.flowState.stallElapsedMs = state.stallStart
          ? Date.now() - state.stallStart : 0;
        node.flowState.terminal     = state.terminal || null;
        node.flowState.stepName     = state.stepName || node.flowState.stepName;
        // Mirror stall to style
        node.style.isStalled = state.stalled;
        if (state.stalled) {{
          node.style.borderColour = '#f59e0b';
          node.style.accentColour = '#f59e0b';
        }}
      }}
    }}
    if (node.children) injectFlowTimes(node.children);
  }});
}}

// ---- Render loop tick -------------------------------------------
setInterval(requestRender, 500);  // 2 Hz background refresh for flow timers

// ---- Boot -------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {{
  initPhaseTabs();
  initSidePanelTabs();
  initFailurePanel();
  initCascadePanel();
  renderInfoPanel();

  // Start flow clocks
  FlowClock.startAll();

  // Subscribe to store changes
  Store.subscribe((event, payload) => {{
    updatePhaseTabs();
    requestRender();
  }});

  // Initial render
  requestRender();

  EventLog.push('info', {{msg: `GUILDS Live — ${{BUNDLE.sourceName}} compiled ${{BUNDLE.compiledAt}}`}});
  EventLog.push('info', {{msg: `${{BUNDLE.phaseOrder.length}} phases · ${{Object.keys(BUNDLE.transitions).length}} transitions · ${{Object.keys(BUNDLE.cascadeIndex).length}} cascade paths`}});
}});
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# SECTION 4: CLI
# ---------------------------------------------------------------------------

def build_html(bundle: dict, source_name: str) -> str:
    bundle_json = json.dumps(bundle, ensure_ascii=False, separators=(',', ':'))
    return SPA_TEMPLATE.format(
        source_name=source_name,
        bundle_json=bundle_json,
    )


def main():
    args = sys.argv[1:]
    if not args or args[0] in ('-h', '--help'):
        print("Usage: guilds_live_builder.py <spec.guilds> [--out path.html]")
        print("       guilds_live_builder.py --example [--out path.html]")
        sys.exit(0)

    out_path = None
    if '--out' in args:
        idx = args.index('--out')
        out_path = args[idx + 1]
        args = args[:idx] + args[idx + 2:]

    if args[0] == '--example':
        from guilds_parser import EXAMPLE_SOURCE as src
        source_name = "example"
    else:
        with open(args[0]) as f:
            src = f.read()
        source_name = os.path.splitext(os.path.basename(args[0]))[0]

    print(f"Compiling {source_name}…", file=sys.stderr)
    bundle = build_bundle(src, source_name)

    print(f"  {len(bundle['phases'])} phases evaluated", file=sys.stderr)
    print(f"  {len(bundle['transitions'])} transition plans", file=sys.stderr)
    print(f"  {len(bundle['cascadeIndex'])} cascade paths pre-computed", file=sys.stderr)

    html = build_html(bundle, source_name)

    if out_path is None:
        out_dir = os.path.join("outputs", source_name)
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, "guilds_live.html")

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)

    size_kb = os.path.getsize(out_path) / 1024
    print(f"  Written: {out_path}  ({size_kb:.0f} KB)", file=sys.stderr)


if __name__ == '__main__':
    main()

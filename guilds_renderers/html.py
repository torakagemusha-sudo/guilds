"""
GUILDS v2 HTML Renderer
=======================
Renders RenderTree to self-contained HTML/CSS/JS documents.

Features:
  - CSS custom properties from GUILDS model
  - Flex layout matching vessel arrangements
  - Certainty badges with colour coding
  - Animated flow indicators
  - Failure overlays
  - CSS transitions from TransitionPlan
  - Phase selector for live demonstration
"""

from __future__ import annotations

from typing import Optional

from .base import (
    BaseRenderer, RenderTree, RenderNode, RenderStyle,
    CERTAINTY_STYLE, FAILURE_STYLE, PHASE_COLOUR,
)
from guilds_evaluator import (
    ResolvedCertainty, FlowState, ActiveFailure, TransitionPlan,
    PHASE_NAMES, FAILURE_NAMES,
)
from guilds_parser import TT


class HTMLRenderer(BaseRenderer):
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

    def file_extension(self) -> str:
        return ".html"

    def output_files(self, base_name: str) -> list[str]:
        return [f"guilds_surface.html"]

    def render(self, tree: RenderTree, title: str = "GUILDS Surface", **kwargs) -> str:
        css = self._global_css(tree)
        body = self._body(tree)
        trans = self._transition_css(tree, kwargs.get('transitions', []))

        return HTML_TEMPLATE.format(
            title=title,
            css=css,
            transition_css=trans,
            body=body,
            phase_name=tree.phase_name,
            phase_colour=tree.phase_colour,
            lambda_omega=f"{tree.lambda_omega:.1f}",
        )

    def render_node(self, node: RenderNode, depth: int = 0) -> str:
        return self._html_node(node, depth)

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

        # Active failures panel
        if tree.active_failures:
            parts.append(self._failures_panel(tree))

        return "\n".join(parts)

    def _phase_header(self, tree: RenderTree) -> str:
        warnings = ""
        if tree.budget_warnings or tree.symbol_errors:
            items = []
            for w in tree.budget_warnings:
                items.append(f'<span class="badge badge-warn">! {_he(w)}</span>')
            for e in tree.symbol_errors:
                items.append(f'<span class="badge badge-error">X {_he(e)}</span>')
            warnings = f'<div class="header-warnings">{"".join(items)}</div>'

        load_status = "within budget" if tree.lambda_omega <= 9 else "LOAD CEILING EXCEEDED"
        load_class = "load-ok" if tree.lambda_omega <= 9 else "load-violation"

        return f"""
        <header class="surface-header">
          <div class="phase-chip" style="--chip-colour:{tree.phase_colour}">
            <span class="phase-dot"></span>
            {_he(tree.phase_name)}
          </div>
          <div class="header-meta">
            LW = {tree.lambda_omega:.1f}
            <span class="{load_class}">
              {load_status}
            </span>
          </div>
          {warnings}
        </header>
        """

    # ---- Node rendering --------------------------------------------------

    def _html_node(self, node: RenderNode, depth: int) -> str:
        if node.visibility == "hide":
            return ""

        classes = ["guilds-node", f"kind-{node.kind.lower()}"]
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

        header_html = self._node_header(node)
        content_html = self._node_content(node)
        data_id = f'data-guilds-id="{_he(node.name)}"'

        return f"""
        <div class="{' '.join(classes)}" style="{css_vars}" {data_id}>
          {header_html}
          {content_html}
          {children_html}
        </div>"""

    def _node_header(self, node: RenderNode) -> str:
        anchor_badge = ""
        if node.style.is_anchor:
            anchor_badge = '<span class="badge badge-anchor">* anchor</span>'

        dom_badge = ""
        if node.style.is_dominant:
            dom_badge = '<span class="badge badge-dominant">@ dominant</span>'

        kind_badge = f'<span class="badge badge-kind">{node.kind.lower()}</span>'

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
        if node.kind.lower() == "claim" and node.certainty:
            parts.append(self._certainty_widget(node.certainty))

        # Flow state widget
        if node.kind.lower() == "flow" and node.flow_state:
            parts.append(self._flow_widget(node.flow_state))

        # Failure overlay
        if node.active_failure:
            parts.append(self._failure_widget(node.active_failure))

        if not parts:
            return ""
        return f'<div class="node-content">{"".join(parts)}</div>'

    # ---- Widgets ---------------------------------------------------------

    def _certainty_widget(self, cert: ResolvedCertainty) -> str:
        cs = CERTAINTY_STYLE.get(cert.grade, CERTAINTY_STYLE["unknown"])
        colour = cs[0]
        symbol = cs[1]
        grade = cs[2]
        rank_w = cert.rank * 20
        dw_pct = min(100, cert.display_weight * 10)

        stale_banner = ""
        if cert.is_stale:
            stale_banner = '<div class="cert-stale-banner">* STALE - certainty has decayed</div>'

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
            return f'<div class="flow-terminal">+ {_he(fs.terminal)}</div>'

        stall_class = "flow-stalled" if fs.stalled else ""
        progress_pct = min(100, (fs.elapsed_ms / max(5000, fs.elapsed_ms)) * 100)

        stall_html = ""
        if fs.stalled:
            stall_html = f"""
            <div class="flow-stall-warning">
              ! STALLED +{fs.stall_elapsed_ms:.0f}ms past threshold
            </div>"""

        spinner = '!' if fs.stalled else '>'

        return f"""
        <div class="flow-widget {stall_class}">
          <div class="flow-header">
            <span class="flow-spinner">{spinner}</span>
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
        fs = FAILURE_STYLE.get(af.kind, ("#dc2626", "P?", "unknown"))
        colour = fs[0]
        symbol = fs[1]
        label = fs[2]

        cascade_html = ""
        if af.propagated_to:
            items = "".join(f'<span class="cascade-item">{_he(n)}</span>'
                            for n in af.propagated_to)
            cascade_html = f'<div class="failure-cascade">cascade -> {items}</div>'

        blocked_html = ""
        if af.cascade_blocked:
            blocked_html = '<div class="failure-blocked">| cascade blocked at seam</div>'

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

    def _failures_panel(self, tree: RenderTree) -> str:
        items = []
        for af in tree.active_failures:
            items.append(self._failure_widget(af))
        return f"""
        <section class="failures-panel">
          <h2 class="panel-title">P Active Failures</h2>
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

    def _transition_css(self, tree: RenderTree, transitions: list = None) -> str:
        if not transitions:
            return ""
        return generate_transition_css(transitions, tree.phase_colour)


def _he(s: str) -> str:
    """HTML-escape a string."""
    return (str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def generate_transition_css(plans: list, phase_colour: str) -> str:
    """Generate CSS for all pending transition plans."""
    rules = []
    for plan in plans:
        rules.append(_transition_keyframes(plan, phase_colour))
    return "\n".join(rules)


def _transition_keyframes(plan, accent: str) -> str:
    """Produce CSS keyframes that honour the sequence_kind."""
    dur = getattr(plan, 'duration_ms', 200)
    ease = getattr(plan, 'easing', 'ease-out')
    seq = getattr(plan, 'sequence_kind', 'simultaneous')

    ease = ease.replace(" - ", "-").replace(" ", "-").strip("-")
    if ease not in ("ease", "ease-in", "ease-out", "ease-in-out", "linear"):
        ease = "ease-out"

    from_phase = getattr(plan, 'from_phase', 'unknown')
    to_phase = getattr(plan, 'to_phase', 'unknown')

    css_id = f"guilds-transition-{from_phase}-to-{to_phase}"

    if seq == "anchor_first":
        leaving_delay = dur * 0.30
        arriving_delay = dur * 0.60
    elif seq == "content_first":
        leaving_delay = 0.0
        arriving_delay = dur * 0.40
    else:
        leaving_delay = 0.0
        arriving_delay = 0.0

    rules = [f"/* Transition: {from_phase} -> {to_phase} [{seq}] {dur:.0f}ms */"]

    leaving = getattr(plan, 'leaving', [])
    arriving = getattr(plan, 'arriving', [])
    anchors = getattr(plan, 'anchors', [])
    stagger_ms = getattr(plan, 'stagger_ms', 0)

    for i, name in enumerate(leaving):
        stagger = (i * stagger_ms) if seq == "staggered" else 0
        delay = leaving_delay + stagger
        sel = f'[data-guilds-id="{name}"]'
        rules.append(
            f"{sel}.leaving {{"
            f" animation: {css_id}-leave {dur:.0f}ms {ease} {delay:.0f}ms both; }}"
        )

    for i, name in enumerate(arriving):
        stagger = (i * stagger_ms) if seq == "staggered" else 0
        delay = arriving_delay + stagger
        sel = f'[data-guilds-id="{name}"]'
        rules.append(
            f"{sel}.arriving {{"
            f" animation: {css_id}-arrive {dur:.0f}ms {ease} {delay:.0f}ms both; }}"
        )

    for name in anchors:
        sel = f'[data-guilds-id="{name}"]'
        rules.append(
            f"{sel} {{ transition: transform {dur * 0.3:.0f}ms {ease}; }}"
        )

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
# HTML TEMPLATE
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

/* ---- Failures Panel ---- */
.failures-panel {{
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

/* ---- Transition CSS (from model) ---- */
{transition_css}
</style>
</head>
<body>
{body}
<script>
// GUILDS Surface - phase state interactive demo
document.addEventListener("DOMContentLoaded", () => {{
  console.log("[GUILDS] Surface rendered. Phase:", "{phase_name}", "LW:", "{lambda_omega}");
  document.querySelectorAll(".guilds-node").forEach(el => {{
    el.setAttribute("data-phase", "{phase_name}");
  }});
}});
</script>
</body>
</html>
"""

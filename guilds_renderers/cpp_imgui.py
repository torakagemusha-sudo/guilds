"""
GUILDS v2 Dear ImGui Renderer
=============================
Renders RenderTree to C++ Dear ImGui application files.

Generates:
  - guilds_ui.h   - State and rendering declarations
  - guilds_ui.cpp - ImGui rendering code

Features:
  - Immediate mode rendering loop
  - State struct for all UI data
  - Colour schemes for certainty/failure
  - Optional GLFW/SDL backend code

Widget mappings:
  Vessel       -> ImGui::BeginChild / ImGui::EndChild
  Claim        -> ImGui::Text / ImGui::TextColored
  Affordance   -> ImGui::Button / ImGui::InputText
  Stage        -> State machine with if/else
  Flow         -> Frame-based state updates
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


class ImGuiRenderer(BaseRenderer):
    """
    Generates C++ Dear ImGui application files from a RenderTree.
    """

    def file_extension(self) -> str:
        return ".cpp"

    def output_files(self, base_name: str) -> list[str]:
        return ["guilds_ui.h", "guilds_ui.cpp"]

    def render(self, tree: RenderTree, app_name: str = "GuildsApp", **kwargs) -> str:
        """
        Generate all ImGui files.
        Returns a formatted string that can be parsed to extract individual files.
        """
        names = self.collect_all_names(tree)

        header = self._generate_header(tree, names)
        source = self._generate_source(tree, names)

        return f'''// === FILE: guilds_ui.h ===
{header}

// === FILE: guilds_ui.cpp ===
{source}
'''

    def render_node(self, node: RenderNode, depth: int = 0) -> str:
        """Render a single node - used internally."""
        return self._generate_widget_code(node, depth)

    def render_files(self, tree: RenderTree, app_name: str = "GuildsApp") -> dict[str, str]:
        """
        Generate all ImGui files as a dictionary.

        Returns:
            Dict mapping filename to file content
        """
        names = self.collect_all_names(tree)

        return {
            "guilds_ui.h": self._generate_header(tree, names),
            "guilds_ui.cpp": self._generate_source(tree, names),
        }

    # -------------------------------------------------------------------------
    # Header generation
    # -------------------------------------------------------------------------

    def _generate_header(self, tree: RenderTree, names: dict[str, list[str]]) -> str:
        """Generate the header file."""

        # Generate claim data members
        claim_members = "\n".join(
            f"    char claim{self.sanitize_identifier(name)}Value[256] = \"(no value)\";\n"
            f"    const char* claim{self.sanitize_identifier(name)}Certainty = \"unknown\";"
            for name in names.get("claim", [])
        )

        # Generate flow data members
        flow_members = "\n".join(
            f"    float flow{self.sanitize_identifier(name)}Progress = 0.0f;\n"
            f"    bool flow{self.sanitize_identifier(name)}Running = false;"
            for name in names.get("flow", [])
        )

        # Generate vessel visibility flags
        vessel_vis = "\n".join(
            f"    bool vessel{self.sanitize_identifier(name)}Visible = true;"
            for name in names.get("vessel", [])
        )

        return f'''#ifndef GUILDS_UI_H
#define GUILDS_UI_H

/**
 * GUILDS-generated Dear ImGui Application
 * =========================================
 * Auto-generated from GUILDS specification.
 *
 * Usage:
 *   1. Include this header
 *   2. Create GuildsUI instance
 *   3. Call render() each frame in your ImGui render loop
 *
 * Dependencies:
 *   - Dear ImGui (https://github.com/ocornut/imgui)
 *   - A backend (GLFW+OpenGL, SDL+OpenGL, etc.)
 */

#include "imgui.h"
#include <functional>
#include <string>
#include <map>

namespace Guilds {{

// Phase enumeration
enum class Phase {{
    Idle = 0,
    Orient,
    Execute,
    Verify,
    Integrate,
    Recover,
    COUNT
}};

inline const char* phaseToString(Phase phase) {{
    static const char* names[] = {{"idle", "orient", "execute", "verify", "integrate", "recover"}};
    return names[static_cast<int>(phase)];
}}

inline ImVec4 phaseColor(Phase phase) {{
    switch (phase) {{
        case Phase::Idle:      return ImVec4(0.42f, 0.45f, 0.50f, 1.0f);  // #6b7280
        case Phase::Orient:    return ImVec4(0.55f, 0.36f, 0.96f, 1.0f);  // #8b5cf6
        case Phase::Execute:   return ImVec4(0.23f, 0.51f, 0.96f, 1.0f);  // #3b82f6
        case Phase::Verify:    return ImVec4(0.13f, 0.77f, 0.37f, 1.0f);  // #22c55e
        case Phase::Integrate: return ImVec4(0.08f, 0.72f, 0.65f, 1.0f);  // #14b8a6
        case Phase::Recover:   return ImVec4(0.98f, 0.45f, 0.09f, 1.0f);  // #f97316
        default:               return ImVec4(1.0f, 1.0f, 1.0f, 1.0f);
    }}
}}

// Certainty grade colours
inline ImVec4 certaintyColor(const char* grade) {{
    if (strcmp(grade, "certain") == 0)   return ImVec4(0.13f, 0.77f, 0.37f, 1.0f);  // #22c55e
    if (strcmp(grade, "inferred") == 0)  return ImVec4(0.23f, 0.51f, 0.96f, 1.0f);  // #3b82f6
    if (strcmp(grade, "probable") == 0)  return ImVec4(0.96f, 0.62f, 0.04f, 1.0f);  // #f59e0b
    if (strcmp(grade, "stale") == 0)     return ImVec4(0.98f, 0.45f, 0.09f, 1.0f);  // #f97316
    if (strcmp(grade, "unknown") == 0)   return ImVec4(0.42f, 0.45f, 0.50f, 1.0f);  // #6b7280
    if (strcmp(grade, "contested") == 0) return ImVec4(0.94f, 0.27f, 0.27f, 1.0f);  // #ef4444
    return ImVec4(0.42f, 0.45f, 0.50f, 1.0f);
}}

// UI State structure - holds all runtime state
struct GuildsState {{
    // Current phase
    Phase currentPhase = Phase::{tree.phase_name.title()};

    // Claim data
{claim_members if claim_members else "    // No claims"}

    // Flow data
{flow_members if flow_members else "    // No flows"}

    // Vessel visibility
{vessel_vis if vessel_vis else "    // No vessels"}

    // Failure states
    std::map<std::string, std::string> activeFailures;  // vessel -> failure kind
}};

// Action callback type
using ActionCallback = std::function<void(const char* actionName)>;
using PhaseCallback = std::function<void(Phase newPhase)>;

// Main UI class
class GuildsUI {{
public:
    GuildsUI();
    ~GuildsUI() = default;

    // Render the UI - call this each frame
    void render();

    // Access state
    GuildsState& state() {{ return m_state; }}
    const GuildsState& state() const {{ return m_state; }}

    // Phase control
    void setPhase(Phase phase);

    // Claim management
    void setClaim(const char* name, const char* value, const char* certainty = "unknown");

    // Flow control
    void startFlow(const char* name);
    void stopFlow(const char* name);
    void updateFlows(float deltaTime);

    // Failure management
    void injectFailure(const char* vessel, const char* kind);
    void clearFailure(const char* vessel);

    // Callbacks
    void setActionCallback(ActionCallback cb) {{ m_actionCallback = cb; }}
    void setPhaseCallback(PhaseCallback cb) {{ m_phaseCallback = cb; }}

private:
    void renderHeader();
    void renderContent();
    void setupStyle();

    GuildsState m_state;
    ActionCallback m_actionCallback;
    PhaseCallback m_phaseCallback;
    bool m_styleInitialized = false;
}};

}} // namespace Guilds

#endif // GUILDS_UI_H
'''

    # -------------------------------------------------------------------------
    # Source generation
    # -------------------------------------------------------------------------

    def _generate_source(self, tree: RenderTree, names: dict[str, list[str]]) -> str:
        """Generate the implementation file."""

        # Generate widget rendering code
        widget_code = self._generate_all_widgets(tree)

        # Generate claim setter cases
        claim_setters = "\n".join(
            f'''    if (strcmp(name, "{name}") == 0) {{
        strncpy(m_state.claim{self.sanitize_identifier(name)}Value, value, 255);
        m_state.claim{self.sanitize_identifier(name)}Certainty = certainty;
        return;
    }}'''
            for name in names.get("claim", [])
        )

        # Generate flow update code
        flow_updates = "\n".join(
            f'''    if (m_state.flow{self.sanitize_identifier(name)}Running) {{
        m_state.flow{self.sanitize_identifier(name)}Progress += deltaTime * 0.5f;
        if (m_state.flow{self.sanitize_identifier(name)}Progress >= 1.0f) {{
            m_state.flow{self.sanitize_identifier(name)}Progress = 0.0f;
        }}
    }}'''
            for name in names.get("flow", [])
        )

        return f'''/**
 * GUILDS-generated Dear ImGui Implementation
 * ==========================================
 * Auto-generated from GUILDS specification.
 */

#include "guilds_ui.h"
#include <cstring>
#include <cstdio>

namespace Guilds {{

GuildsUI::GuildsUI() {{
    setupStyle();
}}

void GuildsUI::setupStyle() {{
    if (m_styleInitialized) return;

    ImGuiStyle& style = ImGui::GetStyle();

    // Dark theme colours
    ImVec4* colors = style.Colors;
    colors[ImGuiCol_WindowBg]         = ImVec4(0.04f, 0.05f, 0.10f, 1.0f);  // #0a0e1a
    colors[ImGuiCol_ChildBg]          = ImVec4(0.07f, 0.09f, 0.15f, 1.0f);  // #111827
    colors[ImGuiCol_PopupBg]          = ImVec4(0.06f, 0.07f, 0.12f, 1.0f);
    colors[ImGuiCol_Border]           = ImVec4(0.20f, 0.25f, 0.33f, 1.0f);  // #334155
    colors[ImGuiCol_FrameBg]          = ImVec4(0.12f, 0.16f, 0.21f, 1.0f);  // #1e293b
    colors[ImGuiCol_FrameBgHovered]   = ImVec4(0.20f, 0.25f, 0.33f, 1.0f);
    colors[ImGuiCol_FrameBgActive]    = ImVec4(0.06f, 0.09f, 0.17f, 1.0f);
    colors[ImGuiCol_TitleBg]          = ImVec4(0.06f, 0.09f, 0.17f, 1.0f);  // #0f172a
    colors[ImGuiCol_TitleBgActive]    = ImVec4(0.06f, 0.09f, 0.17f, 1.0f);
    colors[ImGuiCol_MenuBarBg]        = ImVec4(0.06f, 0.09f, 0.17f, 1.0f);
    colors[ImGuiCol_ScrollbarBg]      = ImVec4(0.06f, 0.09f, 0.17f, 1.0f);
    colors[ImGuiCol_ScrollbarGrab]    = ImVec4(0.20f, 0.25f, 0.33f, 1.0f);
    colors[ImGuiCol_Button]           = ImVec4(0.12f, 0.16f, 0.21f, 1.0f);
    colors[ImGuiCol_ButtonHovered]    = ImVec4(0.20f, 0.25f, 0.33f, 1.0f);
    colors[ImGuiCol_ButtonActive]     = ImVec4(0.06f, 0.09f, 0.17f, 1.0f);
    colors[ImGuiCol_Header]           = ImVec4(0.12f, 0.16f, 0.21f, 1.0f);
    colors[ImGuiCol_HeaderHovered]    = ImVec4(0.20f, 0.25f, 0.33f, 1.0f);
    colors[ImGuiCol_HeaderActive]     = ImVec4(0.06f, 0.09f, 0.17f, 1.0f);
    colors[ImGuiCol_Text]             = ImVec4(0.95f, 0.96f, 0.97f, 1.0f);  // #f1f5f9
    colors[ImGuiCol_TextDisabled]     = ImVec4(0.58f, 0.64f, 0.72f, 1.0f);  // #94a3b8

    // Rounded corners
    style.WindowRounding = 6.0f;
    style.ChildRounding = 6.0f;
    style.FrameRounding = 4.0f;
    style.GrabRounding = 4.0f;
    style.PopupRounding = 4.0f;
    style.ScrollbarRounding = 4.0f;
    style.TabRounding = 4.0f;

    // Spacing
    style.WindowPadding = ImVec2(10, 10);
    style.FramePadding = ImVec2(8, 4);
    style.ItemSpacing = ImVec2(8, 6);
    style.ItemInnerSpacing = ImVec2(6, 4);

    m_styleInitialized = true;
}}

void GuildsUI::render() {{
    // Main window
    ImGuiWindowFlags windowFlags =
        ImGuiWindowFlags_NoTitleBar |
        ImGuiWindowFlags_NoResize |
        ImGuiWindowFlags_NoMove |
        ImGuiWindowFlags_NoCollapse;

    ImGuiViewport* viewport = ImGui::GetMainViewport();
    ImGui::SetNextWindowPos(viewport->WorkPos);
    ImGui::SetNextWindowSize(viewport->WorkSize);

    ImGui::Begin("GUILDS Application", nullptr, windowFlags);

    renderHeader();
    ImGui::Separator();
    renderContent();

    ImGui::End();
}}

void GuildsUI::renderHeader() {{
    ImVec4 phaseCol = phaseColor(m_state.currentPhase);

    // Phase indicator
    ImGui::PushStyleColor(ImGuiCol_Text, phaseCol);
    ImGui::Text("Phase: %s", phaseToString(m_state.currentPhase));
    ImGui::PopStyleColor();

    ImGui::SameLine();
    ImGui::TextDisabled("LW = {tree.lambda_omega:.1f}");

    ImGui::SameLine(ImGui::GetWindowWidth() - 400);

    // Phase buttons
    for (int i = 0; i < static_cast<int>(Phase::COUNT); i++) {{
        Phase p = static_cast<Phase>(i);
        bool isActive = (p == m_state.currentPhase);

        if (isActive) {{
            ImGui::PushStyleColor(ImGuiCol_Button, phaseColor(p));
            ImGui::PushStyleColor(ImGuiCol_ButtonHovered, phaseColor(p));
        }}

        if (ImGui::SmallButton(phaseToString(p))) {{
            setPhase(p);
        }}

        if (isActive) {{
            ImGui::PopStyleColor(2);
        }}

        if (i < static_cast<int>(Phase::COUNT) - 1) {{
            ImGui::SameLine();
        }}
    }}
}}

void GuildsUI::renderContent() {{
    ImGui::BeginChild("Content", ImVec2(0, 0), true);

{self.indent(widget_code, 4)}

    ImGui::EndChild();
}}

void GuildsUI::setPhase(Phase phase) {{
    Phase oldPhase = m_state.currentPhase;
    m_state.currentPhase = phase;

    if (m_phaseCallback) {{
        m_phaseCallback(phase);
    }}
}}

void GuildsUI::setClaim(const char* name, const char* value, const char* certainty) {{
{claim_setters if claim_setters else "    // No claims to set"}
}}

void GuildsUI::startFlow(const char* name) {{
    // Start flow animation
}}

void GuildsUI::stopFlow(const char* name) {{
    // Stop flow animation
}}

void GuildsUI::updateFlows(float deltaTime) {{
{flow_updates if flow_updates else "    // No flows to update"}
}}

void GuildsUI::injectFailure(const char* vessel, const char* kind) {{
    m_state.activeFailures[vessel] = kind;
}}

void GuildsUI::clearFailure(const char* vessel) {{
    m_state.activeFailures.erase(vessel);
}}

}} // namespace Guilds
'''

    def _generate_all_widgets(self, tree: RenderTree) -> str:
        """Generate widget rendering code for all nodes."""
        lines = []
        for root in tree.roots:
            lines.append(self._generate_widget_code(root, 0))
        return "\n\n".join(lines)

    def _generate_widget_code(self, node: RenderNode, depth: int) -> str:
        """Generate widget rendering code for a single node."""
        if node.visibility == "hide":
            return f"// Hidden: {node.name}"

        var_name = self.sanitize_identifier(node.name)
        kind = node.kind.lower()
        indent = "    " * depth

        lines = []

        if kind == "vessel":
            lines.append(self._generate_vessel(node, var_name, depth))
        elif kind == "stage":
            lines.append(self._generate_stage(node, var_name, depth))
        elif kind == "claim":
            lines.append(self._generate_claim(node, var_name, depth))
        elif kind == "afford":
            lines.append(self._generate_affordance(node, var_name, depth))
        elif kind == "flow":
            lines.append(self._generate_flow(node, var_name, depth))
        elif kind == "failure":
            lines.append(self._generate_failure(node, var_name, depth))

        return "\n".join(lines)

    def _generate_vessel(self, node: RenderNode, var_name: str, depth: int) -> str:
        children = "\n".join(
            self._generate_widget_code(child, depth + 1)
            for child in node.children
        )

        dominant_style = ""
        if node.style.is_dominant:
            dominant_style = f'''
    ImGui::PushStyleColor(ImGuiCol_Border, phaseColor(m_state.currentPhase));
    ImGui::PushStyleVar(ImGuiStyleVar_ChildBorderSize, 2.0f);'''
            pop_style = '''
    ImGui::PopStyleVar();
    ImGui::PopStyleColor();'''
        else:
            pop_style = ""

        return f'''
// Vessel: {node.name}
if (m_state.vessel{var_name}Visible) {{{dominant_style}
    if (ImGui::BeginChild("{node.name}", ImVec2(0, 0), true, ImGuiWindowFlags_AlwaysAutoResize)) {{
        // Header
        ImGui::TextColored(phaseColor(m_state.currentPhase), "{node.label}");
        ImGui::Separator();

{self.indent(children, 8)}
    }}
    ImGui::EndChild();{pop_style}
}}'''

    def _generate_stage(self, node: RenderNode, var_name: str, depth: int) -> str:
        children = "\n".join(
            self._generate_widget_code(child, depth + 1)
            for child in node.children
        )

        return f'''
// Stage: {node.name}
if (ImGui::CollapsingHeader("{node.label} (stage)", ImGuiTreeNodeFlags_DefaultOpen)) {{
{self.indent(children, 4)}
}}'''

    def _generate_claim(self, node: RenderNode, var_name: str, depth: int) -> str:
        certainty = node.certainty.grade if node.certainty else "unknown"
        symbol = CERTAINTY_STYLE.get(certainty, CERTAINTY_STYLE["unknown"])[1]

        return f'''
// Claim: {node.name}
{{
    ImVec4 certCol = certaintyColor(m_state.claim{var_name}Certainty);
    ImGui::TextColored(certCol, "{symbol}");
    ImGui::SameLine();
    ImGui::Text("{node.label}:");
    ImGui::SameLine();
    ImGui::TextColored(certCol, "%s", m_state.claim{var_name}Value);
}}'''

    def _generate_affordance(self, node: RenderNode, var_name: str, depth: int) -> str:
        return f'''
// Affordance: {node.name}
if (ImGui::Button("{node.label}")) {{
    if (m_actionCallback) {{
        m_actionCallback("{node.name}");
    }}
}}'''

    def _generate_flow(self, node: RenderNode, var_name: str, depth: int) -> str:
        return f'''
// Flow: {node.name}
{{
    ImGui::Text("Flow: {node.name}");
    ImGui::SameLine();
    ImGui::ProgressBar(m_state.flow{var_name}Progress, ImVec2(100, 4), "");
}}'''

    def _generate_failure(self, node: RenderNode, var_name: str, depth: int) -> str:
        return f'''
// Failure: {node.name}
{{
    ImGui::PushStyleColor(ImGuiCol_Text, ImVec4(0.94f, 0.27f, 0.27f, 1.0f));
    ImGui::Text("[FAILURE] {node.label}");
    if ("{node.subtitle}") {{
        ImGui::TextDisabled("{node.subtitle or ''}");
    }}
    ImGui::PopStyleColor();
}}'''

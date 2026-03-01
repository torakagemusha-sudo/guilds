"""
GUILDS v2 Qt C++ Renderer
=========================
Renders RenderTree to C++ Qt application files.

Generates:
  - guilds_ui.h    - Header with class declarations
  - guilds_ui.cpp  - Implementation
  - CMakeLists.txt - Build configuration

Features:
  - Clean, readable C++ code
  - Qt signal/slot mechanism for events
  - QStackedWidget for phase transitions
  - QStateMachine for flows
  - Supports Qt 5.x and 6.x

Widget mappings:
  Vessel       -> QFrame / QGroupBox
  Claim        -> QLabel
  Affordance   -> QPushButton / QLineEdit
  Stage        -> QStackedWidget
  Flow         -> QStateMachine with QTimer
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


class QtCppRenderer(BaseRenderer):
    """
    Generates C++ Qt application files from a RenderTree.
    """

    def file_extension(self) -> str:
        return ".cpp"

    def output_files(self, base_name: str) -> list[str]:
        return ["guilds_ui.h", "guilds_ui.cpp", "main.cpp", "CMakeLists.txt"]

    def render(self, tree: RenderTree, app_name: str = "GuildsApp", **kwargs) -> str:
        """
        Generate all C++ files.
        Returns a dict-like string that can be parsed to extract individual files.
        """
        class_name = self.sanitize_identifier(app_name)
        names = self.collect_all_names(tree)

        header = self._generate_header(tree, class_name, names)
        source = self._generate_source(tree, class_name, names)
        main = self._generate_main(class_name)
        cmake = self._generate_cmake(class_name)

        # Return as a formatted multi-file output
        return f'''// === FILE: guilds_ui.h ===
{header}

// === FILE: guilds_ui.cpp ===
{source}

// === FILE: main.cpp ===
{main}

// === FILE: CMakeLists.txt ===
{cmake}
'''

    def render_node(self, node: RenderNode, depth: int = 0) -> str:
        """Render a single node - used internally."""
        return self._generate_widget_code(node, "centralWidget", depth)

    def render_files(self, tree: RenderTree, app_name: str = "GuildsApp") -> dict[str, str]:
        """
        Generate all C++ files as a dictionary.

        Returns:
            Dict mapping filename to file content
        """
        class_name = self.sanitize_identifier(app_name)
        names = self.collect_all_names(tree)

        return {
            "guilds_ui.h": self._generate_header(tree, class_name, names),
            "guilds_ui.cpp": self._generate_source(tree, class_name, names),
            "main.cpp": self._generate_main(class_name),
            "CMakeLists.txt": self._generate_cmake(class_name),
        }

    # -------------------------------------------------------------------------
    # Header generation
    # -------------------------------------------------------------------------

    def _generate_header(self, tree: RenderTree, class_name: str,
                        names: dict[str, list[str]]) -> str:
        """Generate the header file."""

        # Generate member declarations
        claim_members = "\n".join(
            f"    QLabel* m_claim{self.sanitize_identifier(name)}Value = nullptr;"
            for name in names.get("claim", [])
        )

        afford_members = "\n".join(
            f"    QPushButton* m_afford{self.sanitize_identifier(name)} = nullptr;"
            for name in names.get("afford", [])
        )

        vessel_members = "\n".join(
            f"    QGroupBox* m_vessel{self.sanitize_identifier(name)} = nullptr;"
            for name in names.get("vessel", [])
        )

        return f'''#ifndef GUILDS_UI_H
#define GUILDS_UI_H

/**
 * GUILDS-generated Qt Application Header
 * ========================================
 * Auto-generated from GUILDS specification.
 */

#include <QMainWindow>
#include <QWidget>
#include <QFrame>
#include <QGroupBox>
#include <QLabel>
#include <QPushButton>
#include <QLineEdit>
#include <QComboBox>
#include <QProgressBar>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QScrollArea>
#include <QStackedWidget>
#include <QTimer>
#include <QMap>
#include <QString>
#include <QVariant>
#include <functional>

// Phase enumeration
enum class Phase {{
    Idle,
    Orient,
    Execute,
    Verify,
    Integrate,
    Recover
}};

// Claim data structure
struct ClaimData {{
    QVariant value;
    QString certainty = "unknown";
    QString stakes = "medium";
    bool isStale = false;
}};

// Flow data structure
struct FlowData {{
    int stepIndex = 0;
    QString stepName;
    QString state = "idle";
    qint64 elapsedMs = 0;
    bool stalled = false;
    QString terminal;
}};

class {class_name} : public QMainWindow
{{
    Q_OBJECT

public:
    explicit {class_name}(QWidget* parent = nullptr);
    ~{class_name}() override = default;

    // Phase management
    Phase currentPhase() const {{ return m_currentPhase; }}

public slots:
    // Phase control
    void changePhase(Phase newPhase);
    void changePhase(const QString& phaseName);

    // Claim management
    void setClaim(const QString& name, const QVariant& value, const QString& certainty = "unknown");
    QVariant getClaim(const QString& name) const;

    // Failure injection
    void injectFailure(const QString& vesselName, const QString& kind, const QString& cause = "");
    void clearFailure(const QString& vesselName);

    // Flow control
    void startFlow(const QString& flowName);
    void stopFlow(const QString& flowName, const QString& terminal = "success");

signals:
    // Events for external integration
    void actionTriggered(const QString& actionName, const QVariantMap& data);
    void phaseChanged(Phase newPhase);
    void claimUpdated(const QString& name, const QVariant& value, const QString& certainty);

private slots:
    void handleAction(const QString& actionName);
    void updateFlowProgress(const QString& flowName);

private:
    void setupUi();
    void setupStyles();
    void applyPhaseVisibility();

    // State
    Phase m_currentPhase = Phase::{tree.phase_name.title()};
    QMap<QString, ClaimData> m_claims;
    QMap<QString, FlowData> m_flows;
    QMap<QString, QTimer*> m_flowTimers;

    // UI components
    QWidget* m_centralWidget = nullptr;
    QVBoxLayout* m_mainLayout = nullptr;
    QFrame* m_header = nullptr;
    QLabel* m_phaseLabel = nullptr;
    QLabel* m_metaLabel = nullptr;
    QScrollArea* m_scrollArea = nullptr;
    QWidget* m_contentWidget = nullptr;
    QVBoxLayout* m_contentLayout = nullptr;

    // Claim widgets
{claim_members if claim_members else "    // No claim widgets"}

    // Affordance widgets
{afford_members if afford_members else "    // No affordance widgets"}

    // Vessel widgets
{vessel_members if vessel_members else "    // No vessel widgets"}
}};

#endif // GUILDS_UI_H
'''

    # -------------------------------------------------------------------------
    # Source generation
    # -------------------------------------------------------------------------

    def _generate_source(self, tree: RenderTree, class_name: str,
                        names: dict[str, list[str]]) -> str:
        """Generate the implementation file."""

        # Generate widget creation code
        widget_code = self._generate_all_widgets(tree)

        # Generate phase button connections
        phase_buttons = "\n".join(
            f'''    auto btn{phase.title()} = new QPushButton("{phase}");
    btn{phase.title()}->setProperty("phase", true);
    connect(btn{phase.title()}, &QPushButton::clicked, this, [this]() {{ changePhase(Phase::{phase.title()}); }});
    headerLayout->addWidget(btn{phase.title()});'''
            for phase in ["Idle", "Orient", "Execute", "Verify", "Integrate", "Recover"]
        )

        return f'''/**
 * GUILDS-generated Qt Application Implementation
 * ===============================================
 * Auto-generated from GUILDS specification.
 */

#include "guilds_ui.h"
#include <QApplication>

// Phase colour mapping
static const QMap<Phase, QString> PHASE_COLOURS = {{
    {{Phase::Idle, "#6b7280"}},
    {{Phase::Orient, "#8b5cf6"}},
    {{Phase::Execute, "#3b82f6"}},
    {{Phase::Verify, "#22c55e"}},
    {{Phase::Integrate, "#14b8a6"}},
    {{Phase::Recover, "#f97316"}}
}};

// Certainty colour mapping
static const QMap<QString, QString> CERTAINTY_COLOURS = {{
    {{"certain", "#22c55e"}},
    {{"inferred", "#3b82f6"}},
    {{"probable", "#f59e0b"}},
    {{"stale", "#f97316"}},
    {{"unknown", "#6b7280"}},
    {{"contested", "#ef4444"}}
}};

{class_name}::{class_name}(QWidget* parent)
    : QMainWindow(parent)
{{
    setWindowTitle("GUILDS Application");
    setMinimumSize(900, 700);

    setupUi();
    setupStyles();
}}

void {class_name}::setupUi()
{{
    // Central widget
    m_centralWidget = new QWidget(this);
    setCentralWidget(m_centralWidget);

    m_mainLayout = new QVBoxLayout(m_centralWidget);
    m_mainLayout->setContentsMargins(10, 10, 10, 10);
    m_mainLayout->setSpacing(10);

    // Header
    m_header = new QFrame();
    m_header->setObjectName("header");
    auto headerLayout = new QHBoxLayout(m_header);

    m_phaseLabel = new QLabel(QString("Phase: %1").arg(
        m_currentPhase == Phase::Idle ? "IDLE" :
        m_currentPhase == Phase::Orient ? "ORIENT" :
        m_currentPhase == Phase::Execute ? "EXECUTE" :
        m_currentPhase == Phase::Verify ? "VERIFY" :
        m_currentPhase == Phase::Integrate ? "INTEGRATE" : "RECOVER"
    ));
    m_phaseLabel->setObjectName("phaseLabel");
    headerLayout->addWidget(m_phaseLabel);

    m_metaLabel = new QLabel("LW = {tree.lambda_omega:.1f}");
    m_metaLabel->setObjectName("metaLabel");
    headerLayout->addWidget(m_metaLabel);

    headerLayout->addStretch();

    // Phase buttons
{phase_buttons}

    m_mainLayout->addWidget(m_header);

    // Scroll area
    m_scrollArea = new QScrollArea();
    m_scrollArea->setWidgetResizable(true);
    m_scrollArea->setHorizontalScrollBarPolicy(Qt::ScrollBarAsNeeded);
    m_scrollArea->setVerticalScrollBarPolicy(Qt::ScrollBarAsNeeded);

    m_contentWidget = new QWidget();
    m_contentLayout = new QVBoxLayout(m_contentWidget);
    m_contentLayout->setContentsMargins(0, 0, 0, 0);
    m_contentLayout->setSpacing(10);

    m_scrollArea->setWidget(m_contentWidget);
    m_mainLayout->addWidget(m_scrollArea);

    // Create widgets from GUILDS tree
{self.indent(widget_code, 4)}

    m_contentLayout->addStretch();
}}

void {class_name}::setupStyles()
{{
    QString accent = PHASE_COLOURS.value(m_currentPhase, "#3b82f6");

    QString stylesheet = QString(R"(
        QMainWindow {{
            background-color: #0a0e1a;
        }}
        QWidget {{
            background-color: #111827;
            color: #f1f5f9;
            font-family: 'Inter', 'Segoe UI', sans-serif;
        }}
        QFrame {{
            background-color: #111827;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 8px;
        }}
        QFrame#header {{
            background-color: #0f172a;
            border-left: 4px solid %1;
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
            color: %1;
        }}
        QLabel {{
            background-color: transparent;
            border: none;
        }}
        QLabel#phaseLabel {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 12pt;
            font-weight: bold;
            color: %1;
        }}
        QLabel#metaLabel {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 9pt;
            color: #94a3b8;
        }}
        QPushButton {{
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 4px;
            padding: 8px 16px;
            color: #f1f5f9;
        }}
        QPushButton:hover {{
            background-color: #334155;
            border-color: %1;
        }}
        QPushButton:pressed {{
            background-color: #0f172a;
        }}
        QProgressBar {{
            background-color: #1e293b;
            border: none;
            border-radius: 2px;
            height: 4px;
        }}
        QProgressBar::chunk {{
            background-color: %1;
            border-radius: 2px;
        }}
        QScrollArea {{
            border: none;
            background-color: transparent;
        }}
    )").arg(accent);

    setStyleSheet(stylesheet);
}}

void {class_name}::changePhase(Phase newPhase)
{{
    Phase oldPhase = m_currentPhase;
    m_currentPhase = newPhase;

    QString phaseName =
        newPhase == Phase::Idle ? "IDLE" :
        newPhase == Phase::Orient ? "ORIENT" :
        newPhase == Phase::Execute ? "EXECUTE" :
        newPhase == Phase::Verify ? "VERIFY" :
        newPhase == Phase::Integrate ? "INTEGRATE" : "RECOVER";

    m_phaseLabel->setText(QString("Phase: %1").arg(phaseName));

    setupStyles();
    applyPhaseVisibility();

    emit phaseChanged(newPhase);
}}

void {class_name}::changePhase(const QString& phaseName)
{{
    Phase phase = Phase::Idle;
    if (phaseName == "orient") phase = Phase::Orient;
    else if (phaseName == "execute") phase = Phase::Execute;
    else if (phaseName == "verify") phase = Phase::Verify;
    else if (phaseName == "integrate") phase = Phase::Integrate;
    else if (phaseName == "recover") phase = Phase::Recover;

    changePhase(phase);
}}

void {class_name}::setClaim(const QString& name, const QVariant& value, const QString& certainty)
{{
    ClaimData& claim = m_claims[name];
    claim.value = value;
    claim.certainty = certainty;

    // Update widget if exists
    // (Widget references would be stored in a map for dynamic lookup)

    emit claimUpdated(name, value, certainty);
}}

QVariant {class_name}::getClaim(const QString& name) const
{{
    if (m_claims.contains(name)) {{
        return m_claims[name].value;
    }}
    return QVariant();
}}

void {class_name}::injectFailure(const QString& vesselName, const QString& kind, const QString& cause)
{{
    // Find vessel and apply failure styling
    // Implementation depends on widget storage
}}

void {class_name}::clearFailure(const QString& vesselName)
{{
    // Clear failure styling from vessel
}}

void {class_name}::startFlow(const QString& flowName)
{{
    // Start flow animation
    auto timer = new QTimer(this);
    connect(timer, &QTimer::timeout, this, [this, flowName]() {{
        updateFlowProgress(flowName);
    }});
    timer->start(50);
    m_flowTimers[flowName] = timer;
}}

void {class_name}::stopFlow(const QString& flowName, const QString& terminal)
{{
    if (m_flowTimers.contains(flowName)) {{
        m_flowTimers[flowName]->stop();
        m_flowTimers[flowName]->deleteLater();
        m_flowTimers.remove(flowName);
    }}
}}

void {class_name}::handleAction(const QString& actionName)
{{
    QVariantMap data;
    data["phase"] = static_cast<int>(m_currentPhase);
    emit actionTriggered(actionName, data);
}}

void {class_name}::updateFlowProgress(const QString& flowName)
{{
    // Update progress bar animation
}}

void {class_name}::applyPhaseVisibility()
{{
    // Apply visibility based on current phase
    // Implementation depends on phase configuration
}}
'''

    def _generate_all_widgets(self, tree: RenderTree) -> str:
        """Generate widget creation code for all nodes."""
        lines = []
        for root in tree.roots:
            lines.append(self._generate_widget_code(root, "m_contentLayout", 0))
        return "\n\n".join(lines)

    def _generate_widget_code(self, node: RenderNode, parent: str, depth: int) -> str:
        """Generate widget creation code for a single node."""
        if node.visibility == "hide":
            return f"// Hidden: {node.name}"

        var_name = self.sanitize_identifier(node.name)
        kind = node.kind.lower()

        lines = []

        if kind == "vessel":
            lines.append(self._generate_vessel(node, parent, var_name))
        elif kind == "stage":
            lines.append(self._generate_stage(node, parent, var_name))
        elif kind == "claim":
            lines.append(self._generate_claim(node, parent, var_name))
        elif kind == "afford":
            lines.append(self._generate_affordance(node, parent, var_name))
        elif kind == "flow":
            lines.append(self._generate_flow(node, parent, var_name))

        return "\n".join(lines)

    def _generate_vessel(self, node: RenderNode, parent: str, var_name: str) -> str:
        children_code = "\n".join(
            self._generate_widget_code(child, f"layout{var_name}", 0)
            for child in node.children
        )
        return f'''
// Vessel: {node.name}
auto vessel{var_name} = new QGroupBox("{node.label}");
auto layout{var_name} = new QVBoxLayout(vessel{var_name});
layout{var_name}->setSpacing(8);
{parent}->addWidget(vessel{var_name});
m_vessel{var_name} = vessel{var_name};
{children_code}'''

    def _generate_stage(self, node: RenderNode, parent: str, var_name: str) -> str:
        children_code = "\n".join(
            self._generate_widget_code(child, f"layout{var_name}", 0)
            for child in node.children
        )
        return f'''
// Stage: {node.name}
auto stage{var_name} = new QGroupBox("{node.label} (stage)");
auto layout{var_name} = new QVBoxLayout(stage{var_name});
layout{var_name}->setSpacing(8);
{parent}->addWidget(stage{var_name});
{children_code}'''

    def _generate_claim(self, node: RenderNode, parent: str, var_name: str) -> str:
        certainty = node.certainty.grade if node.certainty else "unknown"
        colour = CERTAINTY_STYLE.get(certainty, CERTAINTY_STYLE["unknown"])[0]

        return f'''
// Claim: {node.name}
auto claimFrame{var_name} = new QFrame();
auto claimLayout{var_name} = new QHBoxLayout(claimFrame{var_name});
claimLayout{var_name}->setContentsMargins(0, 0, 0, 0);

auto claimName{var_name} = new QLabel("{node.label}:");
claimName{var_name}->setStyleSheet("font-weight: bold;");
claimLayout{var_name}->addWidget(claimName{var_name});

auto claimValue{var_name} = new QLabel("(no value)");
claimValue{var_name}->setStyleSheet("color: {colour};");
claimLayout{var_name}->addWidget(claimValue{var_name});
claimLayout{var_name}->addStretch();

{parent}->addWidget(claimFrame{var_name});
m_claim{var_name}Value = claimValue{var_name};'''

    def _generate_affordance(self, node: RenderNode, parent: str, var_name: str) -> str:
        return f'''
// Affordance: {node.name}
auto btn{var_name} = new QPushButton("{node.label}");
connect(btn{var_name}, &QPushButton::clicked, this, [this]() {{
    handleAction("{node.name}");
}});
{parent}->addWidget(btn{var_name});
m_afford{var_name} = btn{var_name};'''

    def _generate_flow(self, node: RenderNode, parent: str, var_name: str) -> str:
        return f'''
// Flow: {node.name}
auto flowFrame{var_name} = new QFrame();
auto flowLayout{var_name} = new QHBoxLayout(flowFrame{var_name});
flowLayout{var_name}->setContentsMargins(0, 0, 0, 0);

auto flowLabel{var_name} = new QLabel("Flow: {node.name}");
flowLayout{var_name}->addWidget(flowLabel{var_name});

auto flowProgress{var_name} = new QProgressBar();
flowProgress{var_name}->setTextVisible(false);
flowProgress{var_name}->setFixedHeight(4);
flowProgress{var_name}->setValue(0);
flowLayout{var_name}->addWidget(flowProgress{var_name});

{parent}->addWidget(flowFrame{var_name});'''

    def _generate_main(self, class_name: str) -> str:
        return f'''/**
 * GUILDS Application Main Entry Point
 */

#include "guilds_ui.h"
#include <QApplication>
#include <QDebug>

int main(int argc, char *argv[])
{{
    QApplication app(argc, argv);
    app.setStyle("Fusion");

    {class_name} window;

    // Connect signals for debugging
    QObject::connect(&window, &{class_name}::actionTriggered,
        [](const QString& action, const QVariantMap& data) {{
            qDebug() << "Action:" << action << "Data:" << data;
        }});

    QObject::connect(&window, &{class_name}::phaseChanged,
        [](Phase phase) {{
            qDebug() << "Phase changed to:" << static_cast<int>(phase);
        }});

    window.show();
    return app.exec();
}}
'''

    def _generate_cmake(self, class_name: str) -> str:
        return f'''# GUILDS-generated CMakeLists.txt
cmake_minimum_required(VERSION 3.16)
project({class_name} VERSION 1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

# Find Qt
find_package(Qt6 COMPONENTS Widgets QUIET)
if(NOT Qt6_FOUND)
    find_package(Qt5 5.15 COMPONENTS Widgets REQUIRED)
endif()

# Application
add_executable({class_name}
    main.cpp
    guilds_ui.h
    guilds_ui.cpp
)

if(Qt6_FOUND)
    target_link_libraries({class_name} PRIVATE Qt6::Widgets)
else()
    target_link_libraries({class_name} PRIVATE Qt5::Widgets)
endif()

# Install
install(TARGETS {class_name}
    RUNTIME DESTINATION bin
)
'''

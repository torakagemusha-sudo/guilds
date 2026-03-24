"""
GUILDS Flutter/Dart Renderer
=============================
Generates Flutter widgets from GUILDS specifications.

Outputs:
  - lib/guilds_ui.dart - Main widget file
  - lib/guilds_models.dart - Data models
  - pubspec.yaml - Dependencies
"""

from __future__ import annotations
from typing import Any
from guilds_renderers.base import BaseRenderer, RenderTree, RenderNode, RenderStyle


class FlutterRenderer(BaseRenderer):
    """Renders GUILDS specs as Flutter/Dart widgets"""
    
    def file_extension(self) -> str:
        return '.dart'
    
    def output_files(self, base_name: str) -> list[str]:
        return [
            'lib/guilds_ui.dart',
            'lib/guilds_models.dart',
            'lib/guilds_theme.dart',
            'pubspec.yaml',
        ]
    
    def render(self, tree: RenderTree, **kwargs) -> str:
        """Render complete Flutter application"""
        app_name = kwargs.get('app_name', 'GuildsApp')
        
        imports = self._generate_imports()
        models = self._generate_models(tree)
        theme = self._generate_theme(tree)
        widgets = self._generate_widgets(tree)
        main_widget = self._generate_main_widget(tree, app_name)
        
        return f"""{imports}

{models}

{theme}

{widgets}

{main_widget}
"""
    
    def render_node(self, node: RenderNode, depth: int = 0) -> str:
        """Render a single node as Flutter widget"""
        indent = '  ' * depth
        
        if node.visibility == 'hide':
            return f'{indent}// Hidden: {node.name}'
        
        widget_type = self._map_kind_to_widget(node.kind)
        
        if node.kind == 'vessel':
            return self._render_vessel(node, depth)
        elif node.kind == 'claim':
            return self._render_claim(node, depth)
        elif node.kind == 'afford':
            return self._render_afford(node, depth)
        elif node.kind == 'stage':
            return self._render_stage(node, depth)
        elif node.kind == 'flow':
            return self._render_flow(node, depth)
        else:
            return f'{indent}Container() // TODO: {node.kind}'
    
    def _generate_imports(self) -> str:
        """Generate necessary imports"""
        return """import 'package:flutter/material.dart';
import 'package:flutter/services.dart';"""
    
    def _generate_models(self, tree: RenderTree) -> str:
        """Generate data models"""
        phase_enum = f"""
enum GuildsPhase {{
  idle,
  orient,
  execute,
  verify,
  integrate,
  recover,
}}

extension GuildsPhaseExtension on GuildsPhase {{
  Color get color {{
    switch (this) {{
      case GuildsPhase.idle:
        return const Color(0xFF6B7280);
      case GuildsPhase.orient:
        return const Color(0xFF8B5CF6);
      case GuildsPhase.execute:
        return const Color(0xFF3B82F6);
      case GuildsPhase.verify:
        return const Color(0xFF22C55E);
      case GuildsPhase.integrate:
        return const Color(0xFF14B8A6);
      case GuildsPhase.recover:
        return const Color(0xFFF97316);
    }}
  }}
  
  String get label {{
    return name[0].toUpperCase() + name.substring(1);
  }}
}}"""
        
        certainty_enum = """
enum CertaintyGrade {
  certain,
  inferred,
  probable,
  unknown,
  contested,
  stale,
}

extension CertaintyExtension on CertaintyGrade {
  Color get color {
    switch (this) {
      case CertaintyGrade.certain:
        return const Color(0xFF22C55E);
      case CertaintyGrade.inferred:
        return const Color(0xFF3B82F6);
      case CertaintyGrade.probable:
        return const Color(0xFFF59E0B);
      case CertaintyGrade.stale:
        return const Color(0xFFF97316);
      case CertaintyGrade.unknown:
        return const Color(0xFF6B7280);
      case CertaintyGrade.contested:
        return const Color(0xFFEF4444);
    }
  }
  
  String get symbol {
    switch (this) {
      case CertaintyGrade.certain:
        return 'τ✓';
      case CertaintyGrade.inferred:
        return 'τ~';
      case CertaintyGrade.probable:
        return 'τ?';
      case CertaintyGrade.stale:
        return 'τ⌛';
      case CertaintyGrade.unknown:
        return 'τ∅';
      case CertaintyGrade.contested:
        return 'τ⚔';
    }
  }
}"""
        
        return f"""
// ============================================================================
// GUILDS Data Models
// ============================================================================

{phase_enum}

{certainty_enum}

class GuildsState {{
  final GuildsPhase currentPhase;
  final Map<String, dynamic> data;
  
  const GuildsState({{
    required this.currentPhase,
    this.data = const {{}},
  }});
  
  GuildsState copyWith({{
    GuildsPhase? currentPhase,
    Map<String, dynamic>? data,
  }}) {{
    return GuildsState(
      currentPhase: currentPhase ?? this.currentPhase,
      data: data ?? this.data,
    );
  }}
}}
"""
    
    def _generate_theme(self, tree: RenderTree) -> str:
        """Generate theme configuration"""
        phase_colour = tree.phase_colour
        
        return f"""
// ============================================================================
// GUILDS Theme
// ============================================================================

class GuildsTheme {{
  static const bgDeep = Color(0xFF0A0E1A);
  static const bgMid = Color(0xFF0F172A);
  static const bgSurface = Color(0xFF111827);
  static const fgPrimary = Color(0xFFF1F5F9);
  static const fgSecondary = Color(0xFF94A3B8);
  static const fgDim = Color(0xFF475569);
  static const borderDim = Color(0xFF1E293B);
  static const borderMid = Color(0xFF334155);
  
  static ThemeData get darkTheme {{
    return ThemeData.dark().copyWith(
      scaffoldBackgroundColor: bgDeep,
      primaryColor: const Color(0xFF{phase_colour.lstrip('#')}),
      cardColor: bgSurface,
      dividerColor: borderDim,
      textTheme: const TextTheme(
        displayLarge: TextStyle(color: fgPrimary, fontWeight: FontWeight.bold),
        displayMedium: TextStyle(color: fgPrimary, fontWeight: FontWeight.w600),
        bodyLarge: TextStyle(color: fgPrimary),
        bodyMedium: TextStyle(color: fgSecondary),
      ),
    );
  }}
  
  static BorderRadius get defaultRadius => BorderRadius.circular(6);
  static const double defaultGap = 12.0;
  static const double defaultPadding = 16.0;
}}
"""
    
    def _generate_widgets(self, tree: RenderTree) -> str:
        """Generate reusable widget components"""
        return """
// ============================================================================
// GUILDS Widgets
// ============================================================================

class GuildsClaim extends StatelessWidget {
  final String name;
  final String content;
  final CertaintyGrade certainty;
  final bool isVisible;
  final bool isFaded;
  
  const GuildsClaim({
    Key? key,
    required this.name,
    required this.content,
    required this.certainty,
    this.isVisible = true,
    this.isFaded = false,
  }) : super(key: key);
  
  @override
  Widget build(BuildContext context) {
    if (!isVisible) return const SizedBox.shrink();
    
    return Opacity(
      opacity: isFaded ? 0.35 : 1.0,
      child: Container(
        padding: const EdgeInsets.all(GuildsTheme.defaultPadding),
        decoration: BoxDecoration(
          color: GuildsTheme.bgSurface,
          border: Border.all(
            color: certainty.color.withOpacity(0.5),
            width: 2,
          ),
          borderRadius: GuildsTheme.defaultRadius,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(
                  certainty.symbol,
                  style: TextStyle(
                    color: certainty.color,
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    name,
                    style: const TextStyle(
                      color: GuildsTheme.fgPrimary,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              content,
              style: const TextStyle(
                color: GuildsTheme.fgSecondary,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class GuildsAfford extends StatelessWidget {
  final String name;
  final String label;
  final VoidCallback? onPressed;
  final bool enabled;
  
  const GuildsAfford({
    Key? key,
    required this.name,
    required this.label,
    this.onPressed,
    this.enabled = true,
  }) : super(key: key);
  
  @override
  Widget build(BuildContext context) {
    return ElevatedButton(
      onPressed: enabled ? onPressed : null,
      style: ElevatedButton.styleFrom(
        backgroundColor: GuildsTheme.bgSurface,
        foregroundColor: GuildsTheme.fgPrimary,
        padding: const EdgeInsets.symmetric(
          horizontal: 24,
          vertical: 16,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: GuildsTheme.defaultRadius,
          side: const BorderSide(
            color: GuildsTheme.borderMid,
            width: 1,
          ),
        ),
      ),
      child: Text(label),
    );
  }
}

class GuildsVessel extends StatelessWidget {
  final String name;
  final List<Widget> children;
  final Axis direction;
  final bool isDominant;
  final double? flexGrow;
  
  const GuildsVessel({
    Key? key,
    required this.name,
    required this.children,
    this.direction = Axis.vertical,
    this.isDominant = false,
    this.flexGrow,
  }) : super(key: key);
  
  @override
  Widget build(BuildContext context) {
    Widget content = Flex(
      direction: direction,
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: children
          .map((child) => Padding(
                padding: const EdgeInsets.all(4),
                child: child,
              ))
          .toList(),
    );
    
    if (flexGrow != null) {
      content = Flexible(
        flex: (flexGrow! * 10).round(),
        child: content,
      );
    }
    
    return Container(
      padding: const EdgeInsets.all(GuildsTheme.defaultPadding),
      decoration: BoxDecoration(
        color: isDominant ? GuildsTheme.bgSurface : GuildsTheme.bgMid,
        border: Border.all(
          color: isDominant
              ? Theme.of(context).primaryColor
              : GuildsTheme.borderDim,
          width: isDominant ? 2 : 1,
        ),
        borderRadius: GuildsTheme.defaultRadius,
      ),
      child: content,
    );
  }
}

class PhaseIndicator extends StatelessWidget {
  final GuildsPhase phase;
  final VoidCallback? onTap;
  
  const PhaseIndicator({
    Key? key,
    required this.phase,
    this.onTap,
  }) : super(key: key);
  
  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: phase.color.withOpacity(0.2),
          border: Border.all(color: phase.color, width: 2),
          borderRadius: BorderRadius.circular(20),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 8,
              height: 8,
              decoration: BoxDecoration(
                color: phase.color,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 8),
            Text(
              phase.label.toUpperCase(),
              style: TextStyle(
                color: phase.color,
                fontWeight: FontWeight.bold,
                fontSize: 12,
                letterSpacing: 0.5,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
"""
    
    def _generate_main_widget(self, tree: RenderTree, app_name: str) -> str:
        """Generate main application widget"""
        roots_widgets = []
        for root in tree.roots:
            roots_widgets.append(self.render_node(root, 3))
        
        roots_code = ',\n'.join(roots_widgets) if roots_widgets else '// No roots'
        
        return f"""
// ============================================================================
// Main Application Widget
// ============================================================================

class {app_name} extends StatefulWidget {{
  const {app_name}({{Key? key}}) : super(key: key);
  
  @override
  State<{app_name}> createState() => _{app_name}State();
}}

class _{app_name}State extends State<{app_name}> {{
  GuildsState _state = const GuildsState(
    currentPhase: GuildsPhase.{tree.phase_name},
  );
  
  void _setPhase(GuildsPhase phase) {{
    setState(() {{
      _state = _state.copyWith(currentPhase: phase);
    }});
  }}
  
  @override
  Widget build(BuildContext context) {{
    return MaterialApp(
      title: '{app_name}',
      theme: GuildsTheme.darkTheme,
      home: Scaffold(
        body: SafeArea(
          child: Column(
            children: [
              _buildHeader(),
              Expanded(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(GuildsTheme.defaultPadding),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
{roots_code}
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }}
  
  Widget _buildHeader() {{
    return Container(
      padding: const EdgeInsets.all(GuildsTheme.defaultPadding),
      decoration: const BoxDecoration(
        color: GuildsTheme.bgMid,
        border: Border(
          bottom: BorderSide(color: GuildsTheme.borderMid, width: 1),
        ),
      ),
      child: Row(
        children: [
          PhaseIndicator(
            phase: _state.currentPhase,
          ),
          const Spacer(),
          Text(
            'λΩ = {tree.lambda_omega:.1f}',
            style: const TextStyle(
              color: GuildsTheme.fgSecondary,
              fontSize: 12,
            ),
          ),
        ],
      ),
    );
  }}
}}
"""
    
    def _render_vessel(self, node: RenderNode, depth: int) -> str:
        """Render vessel as Flutter container"""
        indent = '  ' * depth
        
        children = []
        for child in node.children:
            children.append(self.render_node(child, depth + 1))
        
        children_code = ',\n'.join(children) if children else ''
        
        direction = 'Axis.vertical' if node.arrangement_kind == 'column' else 'Axis.horizontal'
        is_dominant = node.style.is_dominant
        flex_grow = node.style.flex_grow
        
        return f"""{indent}GuildsVessel(
{indent}  name: '{self.escape_string(node.name)}',
{indent}  direction: {direction},
{indent}  isDominant: {str(is_dominant).lower()},
{indent}  flexGrow: {flex_grow},
{indent}  children: [
{children_code}
{indent}  ],
{indent})"""
    
    def _render_claim(self, node: RenderNode, depth: int) -> str:
        """Render claim as Flutter widget"""
        indent = '  ' * depth
        
        certainty = node.certainty
        grade = certainty.grade if certainty else 'unknown'
        grade_dart = grade.replace('-', '_')
        
        is_faded = node.visibility == 'fade'
        
        return f"""{indent}GuildsClaim(
{indent}  name: '{self.escape_string(node.label)}',
{indent}  content: '{self.escape_string(node.subtitle or '')}',
{indent}  certainty: CertaintyGrade.{grade_dart},
{indent}  isFaded: {str(is_faded).lower()},
{indent})"""
    
    def _render_afford(self, node: RenderNode, depth: int) -> str:
        """Render affordance as button"""
        indent = '  ' * depth
        label = self.humanize_label(node.name, 'afford')
        
        return f"""{indent}GuildsAfford(
{indent}  name: '{self.escape_string(node.name)}',
{indent}  label: '{self.escape_string(label)}',
{indent}  onPressed: () {{
{indent}    // TODO: Handle {node.name} action
{indent}  }},
{indent})"""
    
    def _render_stage(self, node: RenderNode, depth: int) -> str:
        """Render stage"""
        return self._render_vessel(node, depth)
    
    def _render_flow(self, node: RenderNode, depth: int) -> str:
        """Render flow state"""
        indent = '  ' * depth
        
        if node.flow_state:
            fs = node.flow_state
            return f"""{indent}Container(
{indent}  padding: const EdgeInsets.all(12),
{indent}  decoration: BoxDecoration(
{indent}    color: GuildsTheme.bgSurface,
{indent}    border: Border.all(color: GuildsTheme.borderMid),
{indent}    borderRadius: GuildsTheme.defaultRadius,
{indent}  ),
{indent}  child: Column(
{indent}    crossAxisAlignment: CrossAxisAlignment.start,
{indent}    children: [
{indent}      Text(
{indent}        'Flow: {self.escape_string(fs.flow_name)}',
{indent}        style: const TextStyle(fontWeight: FontWeight.bold),
{indent}      ),
{indent}      const SizedBox(height: 4),
{indent}      Text('Step: {self.escape_string(fs.step_name)}'),
{indent}      Text('State: {self.escape_string(fs.state_kind)}'),
{indent}    ],
{indent}  ),
{indent})"""
        
        return f'{indent}// Flow: {node.name}'
    
    def _map_kind_to_widget(self, kind: str) -> str:
        """Map GUILDS kind to Flutter widget type"""
        mapping = {
            'vessel': 'Container',
            'claim': 'Text',
            'afford': 'ElevatedButton',
            'stage': 'Column',
            'flow': 'LinearProgressIndicator',
        }
        return mapping.get(kind, 'Container')
    
    def render_files(self, tree: RenderTree, app_name: str) -> dict[str, str]:
        """Generate all output files"""
        main_dart = self.render(tree, app_name=app_name)
        
        pubspec = f"""name: {app_name.lower()}
description: GUILDS generated Flutter application
version: 1.0.0

environment:
  sdk: '>=2.19.0 <3.0.0'

dependencies:
  flutter:
    sdk: flutter
  cupertino_icons: ^1.0.2

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^2.0.0

flutter:
  uses-material-design: true
"""
        
        return {
            'lib/guilds_ui.dart': main_dart,
            'pubspec.yaml': pubspec,
        }

"""
GUILDS Svelte Renderer
======================
Generates Svelte components from GUILDS specifications.

Outputs:
  - src/lib/GuildsUI.svelte - Main component
  - src/lib/guilds/models.ts - Type definitions
  - src/lib/guilds/store.ts - State management
  - src/lib/guilds/*.svelte - Sub-components
"""

from __future__ import annotations
from typing import Any
from guilds_renderers.base import BaseRenderer, RenderTree, RenderNode


class SvelteRenderer(BaseRenderer):
    """Renders GUILDS specs as Svelte components"""
    
    def file_extension(self) -> str:
        return '.svelte'
    
    def output_files(self, base_name: str) -> list[str]:
        return [
            f'src/lib/{base_name}UI.svelte',
            'src/lib/guilds/models.ts',
            'src/lib/guilds/store.ts',
            'src/lib/guilds/theme.ts',
        ]
    
    def render(self, tree: RenderTree, **kwargs) -> str:
        """Render complete Svelte component"""
        app_name = kwargs.get('app_name', 'Guilds')
        
        script = self._generate_script(tree, app_name)
        markup = self._generate_markup(tree)
        styles = self._generate_styles(tree)
        
        return f"""<script lang="ts">
{script}
</script>

{markup}

<style lang="scss">
{styles}
</style>"""
    
    def render_node(self, node: RenderNode, depth: int = 0) -> str:
        """Render a single node as Svelte markup"""
        indent = '  ' * depth
        
        if node.visibility == 'hide':
            return f'{indent}<!-- Hidden: {node.name} -->'
        
        if node.kind == 'vessel':
            return self._render_vessel(node, depth)
        elif node.kind == 'claim':
            return self._render_claim(node, depth)
        elif node.kind == 'afford':
            return self._render_afford(node, depth)
        elif node.kind == 'stage':
            return self._render_stage(node, depth)
        elif node.kind == 'modal':
            return self._render_modal(node, depth)
        elif node.kind == 'toast':
            return self._render_toast(node, depth)
        else:
            return f'{indent}<div><!-- TODO: {node.kind} --></div>'
    
    def _generate_script(self, tree: RenderTree, app_name: str) -> str:
        """Generate TypeScript script section"""
        return f"""  import {{ writable, derived }} from 'svelte/store';
  import type {{ GuildsPhase, GuildsState }} from './guilds/models';
  import {{ phaseStore, createGuildsStore }} from './guilds/store';
  
  // Initialize state
  const state = createGuildsStore({{
    currentPhase: '{tree.phase_name}' as GuildsPhase,
    data: {{}},
  }});
  
  // Phase management
  function setPhase(phase: GuildsPhase) {{
    state.setPhase(phase);
  }}
  
  // Reactive values
  $: phaseColor = getPhaseColor($state.currentPhase);
  $: lambdaOmega = {tree.lambda_omega:.1f};
  
  function getPhaseColor(phase: GuildsPhase): string {{
    const colors = {{
      idle: '#6B7280',
      orient: '#8B5CF6',
      execute: '#3B82F6',
      verify: '#22C55E',
      integrate: '#14B8A6',
      recover: '#F97316',
    }};
    return colors[phase] || '#6B7280';
  }}
  
  // Action handlers
  function handleAction(actionName: string) {{
    console.log('Action:', actionName);
    // Dispatch custom event or call API
  }}"""
    
    def _generate_markup(self, tree: RenderTree) -> str:
        """Generate HTML markup"""
        roots = []
        for root in tree.roots:
            roots.append(self.render_node(root, 1))
        
        roots_markup = '\n'.join(roots)
        
        return f"""<div class="guilds-app" style="--phase-color: {{phaseColor}}">
  <header class="guilds-header">
    <div class="phase-indicator">
      <span class="phase-dot"></span>
      <span class="phase-label">{{$state.currentPhase}}</span>
    </div>
    
    <div class="header-meta">
      <span>λΩ = {{lambdaOmega}}</span>
      {{#if lambdaOmega > 9}}
        <span class="load-warning">⚠ Load ceiling exceeded</span>
      {{/if}}
    </div>
    
    <div class="phase-selector">
      {{#each ['idle', 'orient', 'execute', 'verify', 'integrate', 'recover'] as phase}}
        <button
          class:active={{$state.currentPhase === phase}}
          on:click={{() => setPhase(phase)}}
        >
          {{phase}}
        </button>
      {{/each}}
    </div>
  </header>
  
  <main class="guilds-content">
{roots_markup}
  </main>
</div>"""
    
    def _generate_styles(self, tree: RenderTree) -> str:
        """Generate SCSS styles"""
        return """.guilds-app {
  --bg-deep: #0a0e1a;
  --bg-mid: #0f172a;
  --bg-surface: #111827;
  --fg-primary: #f1f5f9;
  --fg-secondary: #94a3b8;
  --fg-dim: #475569;
  --border-dim: #1e293b;
  --border-mid: #334155;
  --gap: 0.75rem;
  --radius: 6px;
  
  background: var(--bg-deep);
  color: var(--fg-primary);
  min-height: 100vh;
  font-family: system-ui, -apple-system, sans-serif;
}

.guilds-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: var(--bg-mid);
  border-bottom: 1px solid var(--border-mid);
  border-left: 4px solid var(--phase-color);
}

.phase-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0.75rem;
  background: color-mix(in srgb, var(--phase-color) 20%, transparent);
  border: 1px solid var(--phase-color);
  border-radius: 20px;
  color: var(--phase-color);
  font-weight: 600;
  font-size: 0.875rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.phase-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.header-meta {
  display: flex;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: var(--fg-secondary);
}

.load-warning {
  color: #ef4444;
  font-weight: 700;
}

.phase-selector {
  margin-left: auto;
  display: flex;
  gap: 0.25rem;
  
  button {
    padding: 0.25rem 0.75rem;
    background: transparent;
    border: 1px solid var(--border-mid);
    border-radius: 4px;
    color: var(--fg-secondary);
    font-size: 0.75rem;
    cursor: pointer;
    transition: all 0.2s;
    
    &:hover {
      background: var(--bg-surface);
      color: var(--fg-primary);
    }
    
    &.active {
      background: var(--phase-color);
      border-color: var(--phase-color);
      color: white;
      font-weight: 600;
    }
  }
}

.guilds-content {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: var(--gap);
}

.guilds-vessel {
  padding: 1rem;
  background: var(--bg-surface);
  border: 1px solid var(--border-dim);
  border-radius: var(--radius);
  display: flex;
  gap: var(--gap);
  
  &.column {
    flex-direction: column;
  }
  
  &.row {
    flex-direction: row;
  }
  
  &.dominant {
    border: 2px solid var(--phase-color);
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--phase-color) 20%, transparent);
  }
  
  &.faded {
    opacity: 0.35;
    filter: saturate(0.5);
  }
}

.guilds-claim {
  padding: 0.75rem;
  background: var(--bg-mid);
  border-radius: 4px;
  
  .claim-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
  }
  
  .certainty-badge {
    padding: 0.125rem 0.5rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
    
    &.certain { background: #22c55e; color: white; }
    &.inferred { background: #3b82f6; color: white; }
    &.probable { background: #f59e0b; color: white; }
    &.unknown { background: #6b7280; color: white; }
  }
  
  .claim-content {
    color: var(--fg-secondary);
    font-size: 0.875rem;
  }
}

.guilds-afford {
  padding: 0.75rem 1.5rem;
  background: var(--bg-surface);
  border: 1px solid var(--border-mid);
  border-radius: var(--radius);
  color: var(--fg-primary);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  
  &:hover {
    background: var(--bg-mid);
    border-color: var(--phase-color);
  }
  
  &:active {
    transform: scale(0.98);
  }
  
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.guilds-modal {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  z-index: 1000;
  
  .modal-content {
    background: var(--bg-surface);
    border: 1px solid var(--border-mid);
    border-radius: var(--radius);
    max-width: 600px;
    width: 90%;
    max-height: 80vh;
    overflow: auto;
    
    &.small { max-width: 400px; }
    &.large { max-width: 800px; }
    &.fullscreen { max-width: 95%; max-height: 95vh; }
  }
  
  .modal-header {
    padding: 1rem;
    border-bottom: 1px solid var(--border-dim);
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  
  .modal-body {
    padding: 1rem;
  }
  
  .modal-footer {
    padding: 1rem;
    border-top: 1px solid var(--border-dim);
    display: flex;
    gap: 0.5rem;
    justify-content: flex-end;
  }
}

.guilds-toast {
  position: fixed;
  padding: 1rem;
  background: var(--bg-surface);
  border: 1px solid var(--border-mid);
  border-radius: var(--radius);
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
  min-width: 300px;
  z-index: 2000;
  
  &.top-right { top: 1rem; right: 1rem; }
  &.bottom-right { bottom: 1rem; right: 1rem; }
  &.top-left { top: 1rem; left: 1rem; }
  &.bottom-left { bottom: 1rem; left: 1rem; }
  
  &.info { border-left: 4px solid #3b82f6; }
  &.success { border-left: 4px solid #22c55e; }
  &.warning { border-left: 4px solid #f59e0b; }
  &.error { border-left: 4px solid #ef4444; }
}"""
    
    def _render_vessel(self, node: RenderNode, depth: int) -> str:
        """Render vessel container"""
        indent = '  ' * depth
        
        children = []
        for child in node.children:
            children.append(self.render_node(child, depth + 1))
        
        children_markup = '\n'.join(children)
        
        direction = node.arrangement_kind
        classes = ['guilds-vessel', direction]
        if node.style.is_dominant:
            classes.append('dominant')
        if node.visibility == 'fade':
            classes.append('faded')
        
        class_str = ' '.join(classes)
        
        return f"""{indent}<div class="{class_str}" data-name="{node.name}">
{children_markup}
{indent}</div>"""
    
    def _render_claim(self, node: RenderNode, depth: int) -> str:
        """Render claim"""
        indent = '  ' * depth
        
        certainty = node.certainty
        grade = certainty.grade if certainty else 'unknown'
        
        return f"""{indent}<div class="guilds-claim">
{indent}  <div class="claim-header">
{indent}    <span class="certainty-badge {grade}">{grade}</span>
{indent}    <strong>{self.escape_string(node.label)}</strong>
{indent}  </div>
{indent}  <div class="claim-content">{self.escape_string(node.subtitle or '')}</div>
{indent}</div>"""
    
    def _render_afford(self, node: RenderNode, depth: int) -> str:
        """Render affordance button"""
        indent = '  ' * depth
        label = self.humanize_label(node.name, 'afford')
        
        return f"""{indent}<button 
{indent}  class="guilds-afford"
{indent}  on:click={{() => handleAction('{node.name}')}}
{indent}>
{indent}  {self.escape_string(label)}
{indent}</button>"""
    
    def _render_stage(self, node: RenderNode, depth: int) -> str:
        """Render stage as vessel"""
        return self._render_vessel(node, depth)
    
    def _render_modal(self, node: RenderNode, depth: int) -> str:
        """Render modal dialog"""
        indent = '  ' * depth
        
        return f"""{indent}{{#if showModal}}
{indent}<div class="guilds-modal">
{indent}  <div class="modal-content">
{indent}    <div class="modal-header">
{indent}      <h3>{self.escape_string(node.label)}</h3>
{indent}      <button on:click={{() => showModal = false}}>×</button>
{indent}    </div>
{indent}    <div class="modal-body">
{indent}      <!-- Modal content -->
{indent}    </div>
{indent}  </div>
{indent}</div>
{indent}{{/if}}"""
    
    def _render_toast(self, node: RenderNode, depth: int) -> str:
        """Render toast notification"""
        indent = '  ' * depth
        
        return f"""{indent}{{#if showToast}}
{indent}<div class="guilds-toast bottom-right info">
{indent}  <p>{self.escape_string(node.label)}</p>
{indent}</div>
{indent}{{/if}}"""
    
    def render_files(self, tree: RenderTree, app_name: str) -> dict[str, str]:
        """Generate all output files"""
        main_svelte = self.render(tree, app_name=app_name)
        
        models_ts = self._generate_models_file()
        store_ts = self._generate_store_file()
        theme_ts = self._generate_theme_file(tree)
        
        return {
            f'src/lib/{app_name}UI.svelte': main_svelte,
            'src/lib/guilds/models.ts': models_ts,
            'src/lib/guilds/store.ts': store_ts,
            'src/lib/guilds/theme.ts': theme_ts,
        }
    
    def _generate_models_file(self) -> str:
        """Generate TypeScript models"""
        return """export type GuildsPhase =
  | 'idle'
  | 'orient'
  | 'execute'
  | 'verify'
  | 'integrate'
  | 'recover';

export type CertaintyGrade =
  | 'certain'
  | 'inferred'
  | 'probable'
  | 'unknown'
  | 'contested'
  | 'stale';

export interface GuildsState {
  currentPhase: GuildsPhase;
  data: Record<string, any>;
}

export interface ClaimData {
  name: string;
  content: string;
  certainty: CertaintyGrade;
  stakes: 'low' | 'medium' | 'high' | 'critical';
}

export interface AffordanceData {
  name: string;
  label: string;
  enabled: boolean;
}"""
    
    def _generate_store_file(self) -> str:
        """Generate Svelte store"""
        return """import { writable, derived } from 'svelte/store';
import type { GuildsState, GuildsPhase } from './models';

export function createGuildsStore(initialState: GuildsState) {
  const { subscribe, set, update } = writable<GuildsState>(initialState);
  
  return {
    subscribe,
    setPhase: (phase: GuildsPhase) => {
      update(state => ({ ...state, currentPhase: phase }));
    },
    setData: (key: string, value: any) => {
      update(state => ({
        ...state,
        data: { ...state.data, [key]: value }
      }));
    },
    reset: () => set(initialState),
  };
}

export const phaseStore = writable<GuildsPhase>('idle');

export const phaseColor = derived(
  phaseStore,
  $phase => {
    const colors: Record<GuildsPhase, string> = {
      idle: '#6B7280',
      orient: '#8B5CF6',
      execute: '#3B82F6',
      verify: '#22C55E',
      integrate: '#14B8A6',
      recover: '#F97316',
    };
    return colors[$phase];
  }
);"""
    
    def _generate_theme_file(self, tree: RenderTree) -> str:
        """Generate theme configuration"""
        return """export const guildsTheme = {
  colors: {
    bgDeep: '#0a0e1a',
    bgMid: '#0f172a',
    bgSurface: '#111827',
    fgPrimary: '#f1f5f9',
    fgSecondary: '#94a3b8',
    fgDim: '#475569',
    borderDim: '#1e293b',
    borderMid: '#334155',
  },
  phases: {
    idle: '#6B7280',
    orient: '#8B5CF6',
    execute: '#3B82F6',
    verify: '#22C55E',
    integrate: '#14B8A6',
    recover: '#F97316',
  },
  spacing: {
    gap: '0.75rem',
    padding: '1rem',
  },
  borderRadius: '6px',
};"""

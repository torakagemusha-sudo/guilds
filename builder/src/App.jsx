import { useState } from "react";

const PHASES = ["idle", "orient", "execute", "verify", "integrate", "recover"];
const PHASE_SIGILS = {
  idle: "0x03C60x2205",
  orient: "0x03C60x2080",
  execute: "0x03C60x2081",
  verify: "0x03C60x2082",
  integrate: "0x03C60x2083",
  recover: "0x03C60x1D63"
};
const STATE_KIND_PHASE = {
  acquiring: "orient",
  streaming: "execute",
  processing: "execute",
  completing: "verify",
  settled: "integrate"
};
const PALETTE = [
  { type: "claim", name: "StatusClaim", description: "Visible runtime data or output." },
  { type: "afford", name: "RunAfford", description: "User-triggered action." },
  { type: "vessel", name: "ControlPanel", description: "Container for related UI elements." },
  { type: "flow", name: "JobFlow", description: "Visual flow marker linked to a machine." },
  { type: "stage", name: "WorkspaceStage", description: "Top-level orchestration." }
];
const LANES = [
  { id: "surface", name: "Surface", hint: "Primary task area." },
  { id: "support", name: "Support", hint: "Helpers and side tools." },
  { id: "recover", name: "Recover", hint: "Failure and retry surfaces." }
];

function slugify(value) {
  return value.replace(/([a-z])([A-Z])/g, "$1-$2").replace(/[^a-zA-Z0-9]+/g, "-").replace(/^-+|-+$/g, "").toLowerCase();
}

function certaintyLiteral(level) {
  if (level === "certain") return "0x03C40x2713";
  if (level === "inferred") return "0x03C4~";
  return "0x03C4?";
}

function copyText(text) {
  if (navigator.clipboard?.writeText) navigator.clipboard.writeText(text);
}

function sanitizeMermaidId(value) {
  const cleaned = String(value).replace(/[^a-zA-Z0-9]/g, "_").replace(/^_+|_+$/g, "");
  return cleaned || "state";
}

function createNode(type, laneId, name, description) {
  return {
    id: `node-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
    laneId,
    type,
    name,
    description,
    notes: "",
    phases: type === "flow" ? ["execute", "verify"] : ["idle"],
    certainty: type === "claim" ? "certain" : "inferred",
    stakes: type === "claim" ? "high" : "medium",
    anchor: type === "vessel" && laneId === "surface"
  };
}

function buildBlueprint(nodes, machines) {
  const vessels = {
    surface: nodes.filter((n) => n.type === "vessel" && n.laneId === "surface").map((n) => n.name),
    support: nodes.filter((n) => n.type === "vessel" && n.laneId === "support").map((n) => n.name),
    recover: nodes.filter((n) => n.type === "vessel" && n.laneId === "recover").map((n) => n.name)
  };
  const hooks = machines.flatMap((machine) =>
    machine.states.map((state) => ({
      machine: machine.name,
      state: state.name,
      kind: state.kind,
      phase: STATE_KIND_PHASE[state.kind] || "execute"
    }))
  );
  const primary = vessels.surface[0] || vessels.support[0] || vessels.recover[0] || "MainPanel";
  const supportLead = vessels.support[0] || primary;
  const recoverLead = vessels.recover[0] || primary;
  const phaseConfigs = {
    idle: { arrangement: "sequence(cross, [0.62, 0.38])", visible: [...vessels.surface, ...vessels.support], faded: [], hidden: vessels.recover, dominant: primary },
    orient: { arrangement: "sequence(cross, [0.58, 0.42])", visible: [...vessels.surface, ...vessels.support], faded: [], hidden: vessels.recover, dominant: supportLead },
    execute: { arrangement: "sequence(cross, [0.68, 0.32])", visible: [...vessels.surface, ...vessels.support], faded: vessels.support, hidden: vessels.recover, dominant: primary },
    verify: { arrangement: "sequence(cross, [0.56, 0.44])", visible: [...vessels.surface, ...vessels.support], faded: [], hidden: vessels.recover, dominant: supportLead },
    integrate: { arrangement: "sequence(cross, [0.56, 0.44])", visible: [...vessels.surface, ...vessels.support], faded: [], hidden: vessels.recover, dominant: supportLead },
    recover: { arrangement: "sequence(primary, [0.66, 0.34])", visible: vessels.recover, faded: vessels.surface, hidden: vessels.support, dominant: recoverLead }
  };
  return { hooks, phaseConfigs };
}

function visibilityForNode(node, phase, blueprint) {
  if (node.type === "vessel") {
    const cfg = blueprint.phaseConfigs[phase];
    if (cfg.visible.includes(node.name)) return "render";
    if (cfg.faded.includes(node.name)) return "fade";
    if (cfg.hidden.includes(node.name)) return "hide";
  }
  return node.phases.includes(phase) ? "render" : "hide";
}

function buildDiagnostics(nodes, machines, blueprint) {
  const issues = [];
  nodes.forEach((node) => {
    if (!node.name.trim()) issues.push({ severity: "error", text: `A ${node.type} has no name.` });
    if (!node.phases.length) issues.push({ severity: "warning", text: `${node.name || node.type} is assigned to no phases.` });
    if (node.type === "claim" && !node.certainty) issues.push({ severity: "error", text: `${node.name} is missing a certainty grade.` });
    if (node.type === "claim" && ["high", "critical"].includes(node.stakes) && node.certainty !== "certain") {
      issues.push({ severity: "warning", text: `${node.name} has ${node.stakes} stakes but less than certain certainty.` });
    }
  });
  nodes.filter((n) => n.type === "vessel").forEach((node) => {
    const contains = nodes.filter((child) => child.laneId === node.laneId && child.id !== node.id && (child.type === "claim" || child.type === "afford"));
    if (!contains.length) issues.push({ severity: "warning", text: `${node.name} has no claims or affords in its lane.` });
  });
  nodes.filter((n) => n.anchor).forEach((node) => {
    const hidden = PHASES.filter((phase) => blueprint.phaseConfigs[phase].hidden.includes(node.name));
    if (hidden.length) issues.push({ severity: "error", text: `${node.name} is an anchor but hidden in ${hidden.join(", ")}.` });
  });
  machines.forEach((machine) => {
    if (!machine.states.length) issues.push({ severity: "error", text: `${machine.name} has no states.` });
    machine.transitions.forEach((transition) => {
      const names = machine.states.map((state) => state.name);
      if (!names.includes(transition.from) || !names.includes(transition.to)) {
        issues.push({ severity: "error", text: `${machine.name} has a transition targeting a missing state.` });
      }
    });
  });
  if (!issues.length) issues.push({ severity: "ok", text: "Generated draft is structurally clean in the builder model." });
  return issues;
}

function buildGuildsSpec(nodes, machines, blueprint) {
  const claims = nodes.filter((n) => n.type === "claim").map((node) => [
    `claim ${node.name} {`,
    `    content:     text(${slugify(node.name)})`,
    `    certainty:   ${certaintyLiteral(node.certainty)}`,
    `    provenance:  source.direct(runtime)`,
    `    stakes:      ${node.stakes}`,
    `    freshness:   event_driven(update)`,
    `    on_stale:    mark_stale`,
    `}`
  ].join("\n"));

  const affords = nodes.filter((n) => n.type === "afford").map((node) => [
    `afford ${node.name} {`,
    `    perceivable: always_visible`,
    `    offered:     activate`,
    `    requires:    [ready]`,
    `    on_unavail:  fade_locked`,
    `}`
  ].join("\n"));

  const vessels = nodes.filter((n) => n.type === "vessel").map((node) => {
    const contains = nodes
      .filter((child) => child.laneId === node.laneId && child.id !== node.id && (child.type === "claim" || child.type === "afford"))
      .slice(0, 6)
      .map((child) => child.name)
      .join(", ");
    return [
      `vessel ${node.name} {`,
      `    budget:      whole(0.33)`,
      `    phase:       any`,
      `    weight:      ${node.stakes === "high" || node.stakes === "critical" ? "primary" : "secondary"}`,
      `    arrangement: sequence(primary, [1.0])`,
      `    contains:    [${contains}]`,
      `}`
    ].join("\n");
  });

  const hookComments = blueprint.hooks.length
    ? ["-- Auto-generated state-machine hooks", ...blueprint.hooks.map((hook) => `-- ${hook.machine}.${hook.state} (${hook.kind}) -> ${hook.phase} (${PHASE_SIGILS[hook.phase]})`)]
    : ["-- No state-machine hooks generated yet"];

  const stage = [
    "stage WorkspaceStage {",
    "    budget: whole(1.0)",
    "",
    "    phases: {",
    ...PHASES.flatMap((phase) => {
      const cfg = blueprint.phaseConfigs[phase];
      return [
        `        ${PHASE_SIGILS[phase]}: {`,
        `            arrangement: ${cfg.arrangement}`,
        `            visible:     [${cfg.visible.join(", ")}]`,
        `            faded:       [${cfg.faded.join(", ")}]`,
        `            hidden:      [${cfg.hidden.join(", ")}]`,
        `            dominant:    ${cfg.dominant}`,
        "        }"
      ];
    }),
    "    }",
    "}"
  ].join("\n");

  const flows = machines.map((machine) => {
    const steps = machine.states.map((state) => {
      const trigger = machine.transitions.find((transition) => transition.from === state.name)?.trigger || "complete";
      return [
        `        step ${state.name} {`,
        `            duration:    ms(500)`,
        `            state:       ${state.kind}`,
        `            exit:        on_event(${slugify(trigger).replace(/-/g, "_")})`,
        `            affordances: []`,
        `        }`
      ].join("\n");
    }).join("\n");
    return [
      `flow ${machine.name} {`,
      `    trigger: user_action(${machine.triggerAfford || "RunAfford"})`,
      `    steps: [`,
      steps,
      `    ]`,
      `    on_stall: {`,
      `        threshold: ms(800)`,
      `        surface:   0x03A60x22A3`,
      `        recovery:  [${nodes.filter((n) => n.type === "afford").slice(0, 1).map((n) => n.name).join(", ")}]`,
      `    }`,
      `    terminal: success | failure(0x03A60x22A3)`,
      `}`
    ].join("\n");
  });

  return [...hookComments, ...claims, ...affords, ...vessels, stage, ...flows].join("\n\n");
}

function buildStateJson(machines, blueprint) {
  return JSON.stringify({ version: "1.0", phaseHooks: blueprint.hooks, machines }, null, 2);
}

function buildMermaid(machines) {
  const lines = ["stateDiagram-v2"];
  if (!machines.length) return `${lines[0]}\n    [*] --> NoStatesDefined`;
  machines.forEach((machine) => {
    lines.push(`    state ${sanitizeMermaidId(machine.name)} {`);
    if (machine.states.length) lines.push(`        [*] --> ${sanitizeMermaidId(machine.states[0].name)}`);
    machine.transitions.forEach((transition) => {
      lines.push(`        ${sanitizeMermaidId(transition.from)} --> ${sanitizeMermaidId(transition.to)}: ${transition.trigger}`);
    });
    lines.push("    }");
  });
  return lines.join("\n");
}

function buildReactStub(nodes, machines, activePhase, blueprint) {
  const payload = {
    previewPhase: activePhase,
    lanes: LANES.map((lane) => ({
      id: lane.id,
      items: nodes.filter((node) => node.laneId === lane.id).map((node) => ({
        name: node.name,
        type: node.type,
        visibility: visibilityForNode(node, activePhase, blueprint)
      }))
    })),
    machines: machines.map((machine) => ({ name: machine.name, states: machine.states.map((state) => state.name) }))
  };
  return [
    `const workspace = ${JSON.stringify(payload, null, 2)};`,
    "",
    "export function GuildsWorkspace() {",
    "  return (",
    "    <div className=\"guilds-workspace\" data-phase={workspace.previewPhase}>",
    "      {workspace.lanes.map((lane) => (",
    "        <section key={lane.id}>",
    "          <h3>{lane.id}</h3>",
    "          {lane.items.map((item) => <div key={item.name} data-visibility={item.visibility}>{item.name}</div>)}",
    "        </section>",
    "      ))}",
    "    </div>",
    "  );",
    "}"
  ].join("\n");
}

export default function App() {
  const [nodes, setNodes] = useState([
    { id: "node-1", laneId: "surface", type: "vessel", name: "DisplayPanel", description: "Primary output.", notes: "Show key claims first.", phases: ["idle", "orient", "execute", "verify", "integrate"], certainty: "inferred", stakes: "high", anchor: true },
    { id: "node-2", laneId: "surface", type: "claim", name: "StatusClaim", description: "Runtime status text.", notes: "Operator reads this first.", phases: ["idle", "execute", "verify", "recover"], certainty: "certain", stakes: "high", anchor: false },
    { id: "node-3", laneId: "support", type: "afford", name: "RunAfford", description: "Primary action.", notes: "Keep obvious in idle.", phases: ["idle", "recover"], certainty: "inferred", stakes: "medium", anchor: false },
    { id: "node-4", laneId: "recover", type: "vessel", name: "ErrorOverlay", description: "Recovery surface.", notes: "Show what failed and how to recover.", phases: ["recover"], certainty: "inferred", stakes: "high", anchor: false },
    { id: "node-5", laneId: "recover", type: "claim", name: "ErrorClaim", description: "Failure text.", notes: "Be specific and actionable.", phases: ["recover"], certainty: "inferred", stakes: "critical", anchor: false }
  ]);
  const [machines, setMachines] = useState([
    {
      id: "machine-1",
      name: "JobFlow",
      triggerAfford: "RunAfford",
      states: [
        { id: "state-1", name: "AcquireInput", kind: "acquiring" },
        { id: "state-2", name: "ProcessWork", kind: "processing" },
        { id: "state-3", name: "CompleteRun", kind: "settled" }
      ],
      transitions: [
        { id: "transition-1", from: "AcquireInput", to: "ProcessWork", trigger: "input_ready" },
        { id: "transition-2", from: "ProcessWork", to: "CompleteRun", trigger: "work_complete" }
      ]
    }
  ]);
  const [selectedNodeId, setSelectedNodeId] = useState("node-1");
  const [selectedMachineId, setSelectedMachineId] = useState("machine-1");
  const [dragState, setDragState] = useState(null);
  const [hotLane, setHotLane] = useState(null);
  const [activePhase, setActivePhase] = useState("idle");

  const selectedNode = nodes.find((node) => node.id === selectedNodeId) || null;
  const selectedMachine = machines.find((machine) => machine.id === selectedMachineId) || null;
  const blueprint = buildBlueprint(nodes, machines);
  const diagnostics = buildDiagnostics(nodes, machines, blueprint);
  const guildsDraft = buildGuildsSpec(nodes, machines, blueprint);
  const stateJson = buildStateJson(machines, blueprint);
  const mermaid = buildMermaid(machines);
  const reactStub = buildReactStub(nodes, machines, activePhase, blueprint);
  const previewConfig = blueprint.phaseConfigs[activePhase];

  function updateNode(field, value) {
    if (!selectedNode) return;
    setNodes((current) => current.map((node) => node.id === selectedNode.id ? { ...node, [field]: value } : node));
  }

  function togglePhase(phase) {
    if (!selectedNode) return;
    updateNode("phases", selectedNode.phases.includes(phase) ? selectedNode.phases.filter((entry) => entry !== phase) : [...selectedNode.phases, phase]);
  }

  function removeNode() {
    if (!selectedNode) return;
    const next = nodes.filter((node) => node.id !== selectedNode.id);
    setNodes(next);
    setSelectedNodeId(next[0]?.id || null);
  }

  function dropIntoLane(laneId) {
    if (!dragState) return;
    if (dragState.source === "palette") {
      const next = createNode(dragState.item.type, laneId, dragState.item.name, dragState.item.description);
      setNodes((current) => [...current, next]);
      setSelectedNodeId(next.id);
    } else {
      setNodes((current) => current.map((node) => node.id === dragState.nodeId ? { ...node, laneId } : node));
      setSelectedNodeId(dragState.nodeId);
    }
    setDragState(null);
    setHotLane(null);
  }

  function addMachine() {
    const id = `machine-${Date.now()}`;
    setMachines((current) => [...current, { id, name: `Flow${current.length + 1}`, triggerAfford: "RunAfford", states: [{ id: `state-${Date.now()}`, name: "Start", kind: "acquiring" }], transitions: [] }]);
    setSelectedMachineId(id);
  }

  function updateMachine(field, value) {
    if (!selectedMachine) return;
    setMachines((current) => current.map((machine) => machine.id === selectedMachine.id ? { ...machine, [field]: value } : machine));
  }

  function addState() {
    if (!selectedMachine) return;
    const nextState = { id: `state-${Date.now()}`, name: `State${selectedMachine.states.length + 1}`, kind: "processing" };
    const nextTransition = selectedMachine.states.length ? { id: `transition-${Date.now()}`, from: selectedMachine.states[selectedMachine.states.length - 1].name, to: nextState.name, trigger: "next" } : null;
    setMachines((current) => current.map((machine) => machine.id !== selectedMachine.id ? machine : { ...machine, states: [...machine.states, nextState], transitions: nextTransition ? [...machine.transitions, nextTransition] : machine.transitions }));
  }

  function updateState(stateId, field, value) {
    if (!selectedMachine) return;
    setMachines((current) => current.map((machine) => {
      if (machine.id !== selectedMachine.id) return machine;
      const prior = machine.states.find((state) => state.id === stateId);
      const states = machine.states.map((state) => state.id === stateId ? { ...state, [field]: value } : state);
      const transitions = field === "name" && prior ? machine.transitions.map((transition) => ({ ...transition, from: transition.from === prior.name ? value : transition.from, to: transition.to === prior.name ? value : transition.to })) : machine.transitions;
      return { ...machine, states, transitions };
    }));
  }

  function removeMachine() {
    if (!selectedMachine) return;
    const next = machines.filter((machine) => machine.id !== selectedMachine.id);
    setMachines(next);
    setSelectedMachineId(next[0]?.id || null);
  }

  return (
    <div className="builder-shell">
      <header className="hero">
        <div>
          <span className="eyebrow">Vite React Builder</span>
          <h1>Phase-aware GUI and state machine drafting.</h1>
          <p className="hero-copy">Design the surface visually, preview phases live, then export a stricter GUILDS draft with machine-derived stage hooks.</p>
          <div className="metrics">
            <div className="metric"><strong>{nodes.length}</strong><span>UI nodes</span></div>
            <div className="metric"><strong>{machines.length}</strong><span>state machines</span></div>
            <div className="metric"><strong>{diagnostics.filter((issue) => issue.severity === "error").length}</strong><span>blocking issues</span></div>
          </div>
        </div>
        <div className="hero-side">
          <h2>Phase Preview</h2>
          <div className="phase-strip">
            {PHASES.map((phase) => (
              <button key={phase} type="button" className={`phase-chip ${activePhase === phase ? "phase-chip-active" : ""}`} onClick={() => setActivePhase(phase)}>
                {phase}
              </button>
            ))}
          </div>
          <p>Visible: {previewConfig.visible.join(", ") || "(none)"}<br />Faded: {previewConfig.faded.join(", ") || "(none)"}<br />Hidden: {previewConfig.hidden.join(", ") || "(none)"}</p>
          <p>Dominant: {previewConfig.dominant}</p>
        </div>
      </header>

      <section className="workspace">
        <aside className="panel">
          <div className="panel-head">
            <h2>Palette</h2>
            <button className="ghost-button" type="button" onClick={() => { setNodes([]); setSelectedNodeId(null); }}>Clear</button>
          </div>
          <div className="stack">
            {PALETTE.map((item) => (
              <div key={item.type} className={`palette-card type-${item.type}`} draggable onDragStart={() => setDragState({ source: "palette", item })} onDragEnd={() => setDragState(null)}>
                <strong>{item.name}</strong>
                <p>{item.description}</p>
              </div>
            ))}
          </div>
        </aside>

        <main className="panel">
          <div className="panel-head">
            <h2>Canvas</h2>
            <span className="microcopy">Showing the <strong>{activePhase}</strong> surface simulation.</span>
          </div>
          <div className="lane-grid">
            {LANES.map((lane) => {
              const laneNodes = nodes.filter((node) => node.laneId === lane.id);
              return (
                <section key={lane.id} className={`lane ${hotLane === lane.id ? "lane-hot" : ""}`} onDragOver={(event) => { event.preventDefault(); setHotLane(lane.id); }} onDragLeave={() => setHotLane((current) => current === lane.id ? null : current)} onDrop={(event) => { event.preventDefault(); dropIntoLane(lane.id); }}>
                  <div className="panel-head compact">
                    <div>
                      <h3>{lane.name}</h3>
                      <p className="microcopy">{lane.hint}</p>
                    </div>
                    <span className="pill">{laneNodes.length}</span>
                  </div>
                  <div className="stack">
                    {!laneNodes.length && <div className="drop-hint">Drop a node here.</div>}
                    {laneNodes.map((node) => {
                      const visibility = visibilityForNode(node, activePhase, blueprint);
                      return (
                        <article key={node.id} className={`canvas-card type-${node.type} visibility-${visibility} ${selectedNodeId === node.id ? "selected" : ""}`} draggable onDragStart={() => setDragState({ source: "node", nodeId: node.id })} onDragEnd={() => { setDragState(null); setHotLane(null); }} onClick={() => setSelectedNodeId(node.id)}>
                          <div className="card-topline">
                            <strong>{node.name}</strong>
                            <span className={`visibility-badge visibility-badge-${visibility}`}>{visibility}</span>
                          </div>
                          <p>{node.description || "No description yet."}</p>
                          <div className="pill-row">
                            <span className="pill">{node.type}</span>
                            <span className="pill">{node.stakes}</span>
                            {node.type === "claim" && <span className="pill">{node.certainty}</span>}
                            {node.anchor && <span className="pill pill-anchor">anchor</span>}
                          </div>
                        </article>
                      );
                    })}
                  </div>
                </section>
              );
            })}
          </div>

          <div className="machine-panel">
            <div className="panel-head">
              <h2>State Machines</h2>
              <button className="accent-button" type="button" onClick={addMachine}>Add Machine</button>
            </div>
            <div className="machine-grid">
              <aside className="machine-list">
                {machines.map((machine) => (
                  <button key={machine.id} type="button" className={`machine-tab ${selectedMachineId === machine.id ? "machine-tab-active" : ""}`} onClick={() => setSelectedMachineId(machine.id)}>
                    {machine.name}
                  </button>
                ))}
              </aside>
              <div className="machine-editor">
                {!selectedMachine && <div className="drop-hint">Create a machine to model flow state.</div>}
                {selectedMachine && (
                  <>
                    <div className="panel-head">
                      <h3>{selectedMachine.name}</h3>
                      <button className="danger-button" type="button" onClick={removeMachine}>Remove</button>
                    </div>
                    <label>Flow Name<input value={selectedMachine.name} onChange={(event) => updateMachine("name", event.target.value)} /></label>
                    <label>Trigger Afford<input value={selectedMachine.triggerAfford} onChange={(event) => updateMachine("triggerAfford", event.target.value)} /></label>
                    <div className="panel-head compact">
                      <h3>States</h3>
                      <button className="ghost-button" type="button" onClick={addState}>Add State</button>
                    </div>
                    <div className="stack">
                      {selectedMachine.states.map((state) => (
                        <div key={state.id} className="state-card">
                          <label>Name<input value={state.name} onChange={(event) => updateState(state.id, "name", event.target.value)} /></label>
                          <label>Kind<select value={state.kind} onChange={(event) => updateState(state.id, "kind", event.target.value)}><option value="acquiring">acquiring</option><option value="streaming">streaming</option><option value="processing">processing</option><option value="completing">completing</option><option value="settled">settled</option></select></label>
                          <div className="machine-hook">Promotes to phase <strong>{STATE_KIND_PHASE[state.kind] || "execute"}</strong></div>
                        </div>
                      ))}
                    </div>
                    <div className="transition-preview">
                      <strong>Transitions</strong>
                      <ul>{selectedMachine.transitions.map((transition) => <li key={transition.id}>{transition.from} to {transition.to} on {transition.trigger}</li>)}</ul>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        </main>

        <aside className="panel">
          <div className="panel-head">
            <h2>Inspector</h2>
            {selectedNode && <button className="danger-button" type="button" onClick={removeNode}>Delete</button>}
          </div>
          {!selectedNode && <div className="drop-hint">Select a node to edit it.</div>}
          {selectedNode && (
            <>
              <label>Node Name<input value={selectedNode.name} onChange={(event) => updateNode("name", event.target.value)} /></label>
              <label>Type<select value={selectedNode.type} onChange={(event) => updateNode("type", event.target.value)}><option value="claim">claim</option><option value="afford">afford</option><option value="vessel">vessel</option><option value="flow">flow</option><option value="stage">stage</option></select></label>
              <label>Description<textarea value={selectedNode.description} onChange={(event) => updateNode("description", event.target.value)} /></label>
              <label>Notes<textarea value={selectedNode.notes} onChange={(event) => updateNode("notes", event.target.value)} /></label>
              <label>Stakes<select value={selectedNode.stakes} onChange={(event) => updateNode("stakes", event.target.value)}><option value="low">low</option><option value="medium">medium</option><option value="high">high</option><option value="critical">critical</option></select></label>
              {selectedNode.type === "claim" && <label>Certainty<select value={selectedNode.certainty} onChange={(event) => updateNode("certainty", event.target.value)}><option value="certain">certain (0x03C40x2713)</option><option value="inferred">inferred (0x03C4~)</option><option value="probable">probable (0x03C4?)</option><option value="unknown">unknown (0x03C4?)</option></select></label>}
              {selectedNode.type === "vessel" && <button type="button" className={`toggle-anchor ${selectedNode.anchor ? "toggle-anchor-on" : ""}`} onClick={() => updateNode("anchor", !selectedNode.anchor)}>{selectedNode.anchor ? "Anchor Enabled" : "Enable Anchor"}</button>}
              <div className="phase-grid">
                {PHASES.map((phase) => (
                  <button key={phase} type="button" className={`phase-chip ${selectedNode.phases.includes(phase) ? "phase-chip-active" : ""}`} onClick={() => togglePhase(phase)}>
                    {phase}
                  </button>
                ))}
              </div>
            </>
          )}

          <section className="diagnostics-panel">
            <div className="panel-head compact">
              <h2>Diagnostics</h2>
              <span className="microcopy">{diagnostics.length} checks</span>
            </div>
            <div className="stack">
              {diagnostics.map((issue, index) => (
                <div key={`${issue.text}-${index}`} className={`diagnostic diagnostic-${issue.severity}`}>
                  <strong>{issue.severity.toUpperCase()}</strong>
                  <span>{issue.text}</span>
                </div>
              ))}
            </div>
          </section>

          <section className="diagnostics-panel">
            <div className="panel-head compact">
              <h2>Stage Hooks</h2>
              <span className="microcopy">{blueprint.hooks.length} generated</span>
            </div>
            <div className="stack">
              {!blueprint.hooks.length && <div className="diagnostic diagnostic-ok"><strong>OK</strong><span>No machine hooks yet.</span></div>}
              {blueprint.hooks.map((hook) => (
                <div key={`${hook.machine}-${hook.state}`} className="diagnostic diagnostic-ok">
                  <strong>{hook.phase}</strong>
                  <span>{hook.machine}.{hook.state} maps to {PHASE_SIGILS[hook.phase]}</span>
                </div>
              ))}
            </div>
          </section>

          <div className="export-stack">
            <section><div className="panel-head compact"><h2>GUILDS</h2><button className="accent-button" type="button" onClick={() => copyText(guildsDraft)}>Copy</button></div><pre>{guildsDraft}</pre></section>
            <section><div className="panel-head compact"><h2>React Stub</h2><button className="accent-button" type="button" onClick={() => copyText(reactStub)}>Copy</button></div><pre>{reactStub}</pre></section>
            <section><div className="panel-head compact"><h2>State JSON</h2><button className="accent-button" type="button" onClick={() => copyText(stateJson)}>Copy</button></div><pre>{stateJson}</pre></section>
            <section><div className="panel-head compact"><h2>Mermaid</h2><button className="accent-button" type="button" onClick={() => copyText(mermaid)}>Copy</button></div><pre>{mermaid}</pre></section>
          </div>
        </aside>
      </section>
    </div>
  );
}

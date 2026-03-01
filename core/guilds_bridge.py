#!/usr/bin/env python3
"""
GUILDS Bridge - Integration layer for GUILDS UIs

Enables bidirectional communication between GUILDS HTML SPAs and external programs.

Usage:
  # As a WebSocket server
  python guilds_bridge.py serve --port 8765

  # In your Python application
  from guilds_bridge import GuildsBridge

  bridge = GuildsBridge("outputs/myapp/guilds_live.html")
  bridge.on_action("PrimaryAction", handle_action)
  bridge.set_claim("StatusClaim", {"value": "Ready", "certainty": "certain"})
  bridge.change_phase("execute")
"""

import asyncio
import json
import os
import sys
import webbrowser
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:
    import websockets
except ImportError:
    websockets = None


# =============================================================================
# DATA TYPES
# =============================================================================

@dataclass
class GuildsEvent:
    """Event from GUILDS UI to external program."""
    type: str
    action: Optional[str] = None
    vessel: Optional[str] = None
    phase: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: float = 0


@dataclass
class GuildsCommand:
    """Command from external program to GUILDS UI."""
    type: str
    target: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None


# =============================================================================
# BRIDGE CLASS
# =============================================================================

class GuildsBridge:
    """
    Bridge for integrating GUILDS UIs with Python applications.

    Example:
        bridge = GuildsBridge("outputs/myapp/guilds_live.html")

        @bridge.on("action:Submit")
        def handle_submit(event):
            print(f"User submitted: {event.data}")
            bridge.set_claim("ResultClaim", {"value": "Processing..."})

        bridge.start()  # Opens browser and starts event loop
    """

    def __init__(self, html_path: str, port: int = 8765):
        self.html_path = Path(html_path)
        self.port = port
        self.handlers: Dict[str, List[Callable]] = {}
        self.clients: set = set()
        self.current_phase = "idle"
        self._running = False

    def on(self, event_type: str):
        """Decorator to register event handler."""
        def decorator(func: Callable):
            if event_type not in self.handlers:
                self.handlers[event_type] = []
            self.handlers[event_type].append(func)
            return func
        return decorator

    def on_action(self, action_name: str, handler: Callable):
        """Register handler for a specific affordance action."""
        event_type = f"action:{action_name}"
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)

    def on_phase_change(self, handler: Callable):
        """Register handler for phase changes."""
        if "phase:change" not in self.handlers:
            self.handlers["phase:change"] = []
        self.handlers["phase:change"].append(handler)

    async def _handle_event(self, event: GuildsEvent):
        """Process incoming event from GUILDS UI."""
        handlers = self.handlers.get(event.type, [])
        handlers += self.handlers.get("*", [])  # Wildcard handlers

        for handler in handlers:
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                print(f"Error in handler for {event.type}: {e}")

    async def _broadcast(self, command: GuildsCommand):
        """Send command to all connected GUILDS UIs."""
        if not self.clients:
            return

        message = json.dumps(asdict(command))
        await asyncio.gather(
            *[client.send(message) for client in self.clients],
            return_exceptions=True
        )

    def set_claim(self, claim_name: str, data: Dict[str, Any]):
        """Update a claim's data in the GUILDS UI."""
        command = GuildsCommand(
            type="claim:update",
            target=claim_name,
            payload=data
        )
        asyncio.create_task(self._broadcast(command))

    def change_phase(self, phase: str):
        """Change the current phase in the GUILDS UI."""
        valid_phases = ["idle", "orient", "execute", "verify", "integrate", "recover"]
        if phase not in valid_phases:
            raise ValueError(f"Invalid phase: {phase}. Must be one of {valid_phases}")

        self.current_phase = phase
        command = GuildsCommand(
            type="phase:change",
            payload={"phase": phase}
        )
        asyncio.create_task(self._broadcast(command))

    def inject_failure(self, vessel_name: str, failure_kind: str):
        """Inject a failure state into a vessel."""
        command = GuildsCommand(
            type="failure:inject",
            target=vessel_name,
            payload={"kind": failure_kind}
        )
        asyncio.create_task(self._broadcast(command))

    def clear_failure(self, vessel_name: str):
        """Clear failure state from a vessel."""
        command = GuildsCommand(
            type="failure:clear",
            target=vessel_name
        )
        asyncio.create_task(self._broadcast(command))

    def trigger_flow(self, flow_name: str):
        """Trigger a flow to start."""
        command = GuildsCommand(
            type="flow:trigger",
            target=flow_name
        )
        asyncio.create_task(self._broadcast(command))

    async def _ws_handler(self, websocket, path):
        """Handle WebSocket connection from GUILDS UI."""
        self.clients.add(websocket)
        print(f"Client connected. Total: {len(self.clients)}")

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    event = GuildsEvent(
                        type=data.get("type", "unknown"),
                        action=data.get("action"),
                        vessel=data.get("vessel"),
                        phase=data.get("phase"),
                        data=data.get("data"),
                        timestamp=data.get("timestamp", 0)
                    )
                    await self._handle_event(event)
                except json.JSONDecodeError:
                    print(f"Invalid JSON: {message}")
        finally:
            self.clients.remove(websocket)
            print(f"Client disconnected. Total: {len(self.clients)}")

    def start(self, open_browser: bool = True):
        """Start the bridge server and optionally open browser."""
        if websockets is None:
            print("Error: websockets package required. Install with: pip install websockets")
            return

        async def main():
            # Inject bridge script into HTML
            self._inject_bridge_script()

            # Start WebSocket server
            async with websockets.serve(self._ws_handler, "localhost", self.port):
                print(f"GUILDS Bridge running on ws://localhost:{self.port}")

                if open_browser:
                    webbrowser.open(f"file://{self.html_path.absolute()}")

                self._running = True
                while self._running:
                    await asyncio.sleep(0.1)

        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            print("\nBridge stopped.")

    def stop(self):
        """Stop the bridge server."""
        self._running = False

    def _inject_bridge_script(self):
        """Inject WebSocket bridge code into the HTML file."""
        bridge_script = f'''
<script>
// GUILDS Bridge - Auto-injected
(function() {{
  const ws = new WebSocket('ws://localhost:{self.port}');

  ws.onopen = () => console.log('GUILDS Bridge connected');
  ws.onclose = () => console.log('GUILDS Bridge disconnected');

  ws.onmessage = (event) => {{
    const cmd = JSON.parse(event.data);
    console.log('Bridge command:', cmd);

    if (cmd.type === 'phase:change' && window.GUILDS) {{
      window.GUILDS.setPhase(cmd.payload.phase);
    }}
    if (cmd.type === 'claim:update' && window.GUILDS) {{
      window.GUILDS.updateClaim(cmd.target, cmd.payload);
    }}
    if (cmd.type === 'failure:inject' && window.GUILDS) {{
      window.GUILDS.injectFailure(cmd.target, cmd.payload.kind);
    }}
  }};

  // Intercept GUILDS events and forward to bridge
  const originalEmit = window.GUILDS?.emit;
  if (originalEmit) {{
    window.GUILDS.emit = function(type, data) {{
      ws.send(JSON.stringify({{ type, ...data, timestamp: Date.now() }}));
      return originalEmit.call(this, type, data);
    }};
  }}

  // Expose bridge API
  window.GUILDSBridge = {{
    send: (type, data) => ws.send(JSON.stringify({{ type, ...data }})),
    close: () => ws.close()
  }};
}})();
</script>
'''
        # Read HTML
        with open(self.html_path, 'r', encoding='utf-8') as f:
            html = f.read()

        # Check if already injected
        if 'GUILDS Bridge' in html:
            return

        # Inject before </body>
        html = html.replace('</body>', f'{bridge_script}</body>')

        # Write back
        with open(self.html_path, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"Injected bridge script into {self.html_path}")


# =============================================================================
# CLI
# =============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="GUILDS Bridge - Integration server")
    parser.add_argument('command', choices=['serve', 'inject'], help='Command to run')
    parser.add_argument('html', help='Path to GUILDS HTML file')
    parser.add_argument('--port', '-p', type=int, default=8765, help='WebSocket port')
    parser.add_argument('--no-browser', action='store_true', help="Don't open browser")

    args = parser.parse_args()

    if args.command == 'serve':
        bridge = GuildsBridge(args.html, port=args.port)

        @bridge.on("*")
        def log_all(event):
            print(f"Event: {event.type} - {event.data}")

        bridge.start(open_browser=not args.no_browser)

    elif args.command == 'inject':
        bridge = GuildsBridge(args.html, port=args.port)
        bridge._inject_bridge_script()
        print("Bridge script injected. Open the HTML file to connect.")


if __name__ == '__main__':
    main()

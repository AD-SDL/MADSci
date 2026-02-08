# MADSci TUI Design Document

**Status**: Draft
**Date**: 2026-02-07
**Author**: Claude (AI Assistant)

## Overview

This document defines the design for the MADSci Terminal User Interface (TUI). The TUI provides an interactive, visual interface for managing and monitoring MADSci labs directly from the terminal, making the system more accessible to users who are uncomfortable with pure CLI commands.

## Design Principles

1. **Accessibility**: Usable without memorizing commands
2. **Real-time**: Live updates for status, logs, and workflows
3. **Keyboard-first**: Full keyboard navigation with mouse support
4. **Context-aware**: Shows relevant information based on current state
5. **Non-blocking**: Long operations run in background with progress indicators

## Technical Foundation

### Framework Selection

| Component | Choice | Rationale |
|-----------|--------|----------|
| TUI Framework | **Textual** | Modern async framework, rich widgets, good ecosystem |
| CLI Integration | **Trogon** | Auto-generates TUI from Click commands (already a dependency) |
| Styling | **Textual CSS** | Built-in theming, responsive layouts |
| Async Runtime | **asyncio** | Native Python async, works with httpx |

### Package Location

```
src/madsci_client/madsci/client/cli/tui/
├── __init__.py           # TUI entry point
├── app.py                # Main Textual application
├── screens/
│   ├── __init__.py
│   ├── dashboard.py      # Main dashboard screen
│   ├── status.py         # Service status screen
│   ├── logs.py           # Log viewer screen
│   ├── nodes.py          # Node management screen
│   ├── workflows.py      # Workflow management screen
│   ├── resources.py      # Resource browser screen
│   ├── experiments.py    # Experiment management screen
│   ├── wizards/          # Interactive wizards
│   │   ├── __init__.py
│   │   ├── new_lab.py
│   │   ├── new_module.py
│   │   ├── new_interface.py
│   │   └── new_experiment.py
│   └── settings.py       # Settings screen
├── widgets/
│   ├── __init__.py
│   ├── service_card.py   # Service status card
│   ├── log_viewer.py     # Log display widget
│   ├── node_list.py      # Node list widget
│   ├── workflow_graph.py # Workflow visualization
│   ├── progress_bar.py   # Progress indicator
│   └── resource_tree.py  # Resource hierarchy
├── styles/
│   ├── __init__.py
│   └── theme.tcss        # Textual CSS styles
└── utils/
    ├── __init__.py
    ├── async_client.py   # Async service clients
    └── state.py          # Application state management
```

---

## Application Architecture

### Main Application

```python
# src/madsci_client/madsci/client/cli/tui/app.py
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer
from textual.binding import Binding

from .screens.dashboard import DashboardScreen
from .screens.status import StatusScreen
from .screens.logs import LogsScreen
from .screens.nodes import NodesScreen
from .screens.workflows import WorkflowsScreen

class MadsciApp(App):
    """MADSci Terminal User Interface."""

    TITLE = "MADSci"
    SUB_TITLE = "Self-Driving Laboratory Manager"
    CSS_PATH = "styles/theme.tcss"

    BINDINGS = [
        Binding("d", "switch_screen('dashboard')", "Dashboard", show=True),
        Binding("s", "switch_screen('status')", "Status", show=True),
        Binding("l", "switch_screen('logs')", "Logs", show=True),
        Binding("n", "switch_screen('nodes')", "Nodes", show=True),
        Binding("w", "switch_screen('workflows')", "Workflows", show=True),
        Binding("q", "quit", "Quit", show=True),
        Binding("?", "show_help", "Help", show=True),
        Binding("ctrl+p", "command_palette", "Commands", show=True),
    ]

    SCREENS = {
        "dashboard": DashboardScreen,
        "status": StatusScreen,
        "logs": LogsScreen,
        "nodes": NodesScreen,
        "workflows": WorkflowsScreen,
    }

    def __init__(self, lab_url: str = "http://localhost:8000/"):
        super().__init__()
        self.lab_url = lab_url
        self.lab_client = None  # Initialized on mount

    async def on_mount(self) -> None:
        """Initialize connections when app mounts."""
        from madsci.client import LabClient
        self.lab_client = LabClient(self.lab_url)
        self.push_screen("dashboard")

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
```

---

## Screen Designs

### 1. Dashboard Screen

The main landing screen providing an overview of the lab.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  MADSci                                          Self-Driving Laboratory     │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─ Lab Status ──────────────────────────────────────────────────────────┐  │
│  │  Example Lab                                    ● Connected            │  │
│  │  http://localhost:8000                          Uptime: 2h 34m         │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌─ Services ─────────────────────┐  ┌─ Quick Actions ────────────────────┐ │
│  │  ● Lab Manager      healthy    │  │                                    │ │
│  │  ● Event Manager    healthy    │  │  [N] New Experiment                │ │
│  │  ● Workcell Manager healthy    │  │  [W] Start Workflow                │ │
│  │  ● Resource Manager healthy    │  │  [R] View Resources                │ │
│  │  ● Data Manager     healthy    │  │  [L] View Logs                     │ │
│  │  ○ Location Manager starting   │  │                                    │ │
│  └────────────────────────────────┘  └────────────────────────────────────┘ │
│                                                                              │
│  ┌─ Nodes ──────────────────────────────────────────────────────────────┐   │
│  │  ● liquidhandler_1   idle     ● robotarm_1      idle                  │   │
│  │  ● liquidhandler_2   busy     ○ platereader_1   offline               │   │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌─ Active Workflows ───────────────────────────────────────────────────┐   │
│  │  #1 sample_transfer    step 3/5   ████████░░░░░░░░  60%   00:02:34   │   │
│  │  #2 plate_measurement  step 1/3   ███░░░░░░░░░░░░░  20%   00:00:45   │   │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌─ Recent Events ──────────────────────────────────────────────────────┐   │
│  │  15:42:01  INFO   Workflow sample_transfer started                    │   │
│  │  15:41:58  INFO   Node liquidhandler_2 action transfer completed      │   │
│  │  15:41:45  WARN   Resource plate_001 capacity at 90%                  │   │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│ D Dashboard  S Status  L Logs  N Nodes  W Workflows  ? Help  Q Quit         │
└──────────────────────────────────────────────────────────────────────────────┘
```

```python
# screens/dashboard.py
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, Label
from textual.reactive import reactive

from ..widgets.service_card import ServiceStatusPanel
from ..widgets.node_list import NodeStatusList
from ..widgets.workflow_progress import ActiveWorkflowsList
from ..widgets.event_log import RecentEventsList

class DashboardScreen(Screen):
    """Main dashboard showing lab overview."""

    BINDINGS = [
        ("n", "new_experiment", "New Experiment"),
        ("w", "start_workflow", "Start Workflow"),
        ("r", "view_resources", "Resources"),
    ]

    def compose(self) -> ComposeResult:
        with Container(id="dashboard"):
            yield LabStatusHeader()

            with Horizontal(id="top-row"):
                yield ServiceStatusPanel(id="services")
                yield QuickActionsPanel(id="quick-actions")

            yield NodeStatusList(id="nodes")
            yield ActiveWorkflowsList(id="workflows")
            yield RecentEventsList(id="events")

    async def on_mount(self) -> None:
        """Start background refresh tasks."""
        self.set_interval(5.0, self.refresh_data)

    async def refresh_data(self) -> None:
        """Refresh dashboard data from services."""
        # Update service status
        # Update node status
        # Update active workflows
        # Update recent events
        pass
```

---

### 2. Status Screen

Detailed service status with health information.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  MADSci                                                    Service Status    │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─ Managers ───────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │   Service              URL                    Status   Version        │   │
│  │  ─────────────────────────────────────────────────────────────────── │   │
│  │   ● lab_manager        http://localhost:8000  healthy  0.2.0-beta    │   │
│  │   ● event_manager      http://localhost:8001  healthy  0.2.0-beta    │   │
│  │   ● experiment_manager http://localhost:8002  healthy  0.2.0-beta    │   │
│  │   ● resource_manager   http://localhost:8003  healthy  0.2.0-beta    │   │
│  │   ● data_manager       http://localhost:8004  healthy  0.2.0-beta    │   │
│  │   ● workcell_manager   http://localhost:8005  healthy  0.2.0-beta    │   │
│  │   ● location_manager   http://localhost:8006  healthy  0.2.0-beta    │   │
│  │                                                                       │   │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌─ Infrastructure ─────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │   Service     Host              Port   Status                         │   │
│  │  ─────────────────────────────────────────────────────────────────── │   │
│  │   ● MongoDB   localhost         27017  connected                      │   │
│  │   ● Postgres  localhost         5432   connected                      │   │
│  │   ● Redis     localhost         6379   connected                      │   │
│  │   ● MinIO     localhost         9000   connected                      │   │
│  │                                                                       │   │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌─ Selected: lab_manager ──────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │  URL:     http://localhost:8000                                       │   │
│  │  Status:  healthy                                                     │   │
│  │  Version: 0.2.0-beta                                                  │   │
│  │  Uptime:  2 hours, 34 minutes                                         │   │
│  │                                                                       │   │
│  │  Endpoints:                                                           │   │
│  │    /health    GET   Health check                                      │   │
│  │    /info      GET   Service information                               │   │
│  │    /managers  GET   List connected managers                           │   │
│  │                                                                       │   │
│  │  [Open in Browser]  [View Logs]  [Restart]                           │   │
│  │                                                                       │   │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│ ↑↓ Navigate  Enter Select  R Refresh  B Open Browser  L Logs  Esc Back      │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

### 3. Logs Screen

Real-time log viewer with filtering.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  MADSci                                                        Log Viewer    │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─ Filters ────────────────────────────────────────────────────────────┐   │
│  │  Service: [All Services     ▼]  Level: [INFO ▼]  Search: [________]  │   │
│  │  ☑ lab_manager  ☑ event_manager  ☑ workcell_manager  ☐ nodes         │   │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌─ Logs ───────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │  15:42:15.234  INFO   workcell   Step 4 completed: transfer          │   │
│  │  15:42:14.891  DEBUG  workcell   Executing action on liquidhandler_2 │   │
│  │  15:42:14.567  INFO   workcell   Step 3 completed: aspirate          │   │
│  │  15:42:12.123  INFO   event      Event logged: workflow_step_complete│   │
│  │  15:42:10.456  DEBUG  workcell   Validating step preconditions       │   │
│  │  15:42:08.789  INFO   workcell   Starting step 3: aspirate           │   │
│  │  15:42:05.234  WARN   resource   Resource plate_001 at 90% capacity  │   │
│  │  15:42:01.567  INFO   workcell   Workflow sample_transfer started    │   │
│  │  15:41:58.890  INFO   experiment Experiment run exp_001 created      │   │
│  │  15:41:55.123  DEBUG  lab        Health check from workcell_manager  │   │
│  │  15:41:50.456  INFO   location   Resource attached to location       │   │
│  │  15:41:45.789  DEBUG  data       Datapoint stored: measurement_001   │   │
│  │  ...                                                                  │   │
│  │                                                                       │   │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌─ Log Detail ─────────────────────────────────────────────────────────┐   │
│  │  Timestamp: 2026-02-07T15:42:05.234Z                                  │   │
│  │  Level:     WARN                                                      │   │
│  │  Service:   resource_manager                                          │   │
│  │  Message:   Resource plate_001 at 90% capacity                        │   │
│  │  Context:   {"resource_id": "01ABC...", "capacity": 0.9}             │   │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│ ↑↓ Scroll  F Follow  / Search  C Clear  E Export  Esc Back                  │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

### 4. Nodes Screen

Node management and monitoring.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  MADSci                                                    Node Management   │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─ Nodes ──────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │   Node              Type      Status   URL                   Actions  │   │
│  │  ─────────────────────────────────────────────────────────────────── │   │
│  │ > ● liquidhandler_1 device    idle     http://localhost:2000         │   │
│  │   ● liquidhandler_2 device    busy     http://localhost:2001         │   │
│  │   ● robotarm_1      device    idle     http://localhost:2002         │   │
│  │   ○ platereader_1   device    offline  http://localhost:2003         │   │
│  │   ● compute_node_1  compute   idle     http://localhost:2010         │   │
│  │                                                                       │   │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌─ liquidhandler_1 ────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │  Name:        liquidhandler_1                                         │   │
│  │  ID:          01JYFEHVSV20D60Z88RVERJ75N                              │   │
│  │  Type:        device                                                  │   │
│  │  Module:      liquidhandler v0.0.1                                    │   │
│  │  Status:      idle                                                    │   │
│  │  URL:         http://localhost:2000                                   │   │
│  │                                                                       │   │
│  │  Actions:                                                             │   │
│  │    • transfer     Transfer liquid between locations                   │   │
│  │    • aspirate     Aspirate liquid from location                       │   │
│  │    • dispense     Dispense liquid to location                         │   │
│  │    • pick_up_tips Pick up pipette tips                                │   │
│  │    • eject_tips   Eject pipette tips                                  │   │
│  │    • mix          Mix liquid at location                              │   │
│  │                                                                       │   │
│  │  [Run Action]  [View Logs]  [Stop]  [Restart]                        │   │
│  │                                                                       │   │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│ ↑↓ Navigate  Enter Select  A Run Action  L Logs  S Stop  R Restart  + New   │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

### 5. Workflows Screen

Workflow management and execution.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  MADSci                                               Workflow Management    │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─ Active Workflows ───────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │   ID    Name              Status      Progress   Started              │   │
│  │  ─────────────────────────────────────────────────────────────────── │   │
│  │ > #1    sample_transfer   running     ████████░░ 4/5     15:42:01    │   │
│  │   #2    plate_measurement running     ███░░░░░░░ 1/3     15:43:12    │   │
│  │   #3    data_collection   queued      ░░░░░░░░░░ 0/8     -           │   │
│  │                                                                       │   │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌─ Workflow: sample_transfer ──────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │  ID:       wf_01ABC...                                                │   │
│  │  Status:   running (step 4 of 5)                                      │   │
│  │  Started:  2026-02-07 15:42:01                                        │   │
│  │  Duration: 00:03:45                                                   │   │
│  │                                                                       │   │
│  │  Steps:                                                               │   │
│  │    ✓ 1. prepare        liquidhandler_1   completed  00:00:12         │   │
│  │    ✓ 2. aspirate       liquidhandler_1   completed  00:00:45         │   │
│  │    ✓ 3. transfer       robotarm_1        completed  00:01:30         │   │
│  │    ► 4. dispense       liquidhandler_2   running    00:01:18         │   │
│  │    ○ 5. measure        platereader_1     pending    -                │   │
│  │                                                                       │   │
│  │  [Pause]  [Cancel]  [View Logs]  [Retry Step]                        │   │
│  │                                                                       │   │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌─ Workflow Definitions ───────────────────────────────────────────────┐   │
│  │  • sample_transfer.workflow.yaml                                      │   │
│  │  • plate_measurement.workflow.yaml                                    │   │
│  │  • data_collection.workflow.yaml                                      │   │
│  │  [+ New Workflow]                                                     │   │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│ ↑↓ Navigate  Enter Select  S Start  P Pause  C Cancel  L Logs  + New        │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

### 6. New Module Wizard

Interactive wizard for creating new instrument modules.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  MADSci                                                  Create New Module   │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                         Step 1 of 5: Basic Information                       │
│                         ━━━━━━━━○○○○○○○○                                     │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │  Module Name                                                          │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │ my_pipette                                                      │ │  │
│  │  └─────────────────────────────────────────────────────────────────┘ │  │
│  │  A unique name for your module (lowercase, underscores allowed)      │  │
│  │  Output: my_pipette_module/                                          │  │
│  │                                                                       │  │
│  │  Description                                                          │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │ Hamilton liquid handler for 96-well plate operations           │ │  │
│  │  └─────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                       │  │
│  │  Node Type                                                            │  │
│  │    ● device   - Physical instruments and robots                      │  │
│  │    ○ compute  - Data processing and analysis                         │  │
│  │    ○ human    - Manual operation steps                               │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│                              [Cancel]  [Next →]                              │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│ Tab Next Field  ↑↓ Select Option  Enter Confirm  Esc Cancel                  │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Step 2: Template Selection**
```
┌──────────────────────────────────────────────────────────────────────────────┐
│  MADSci                                                  Create New Module   │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                         Step 2 of 5: Template Selection                      │
│                         ━━━━━━━━━━━━━━━━○○○○                                 │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │  Module Template                                                      │  │
│  │    ○ basic         - Minimal module with one action                  │  │
│  │    ● device        - Standard device lifecycle (init, shutdown)      │  │
│  │    ○ instrument    - Measurement device (measure, calibrate)         │  │
│  │    ○ liquid_handler - Pipetting operations                           │  │
│  │    ○ robot_arm     - Pick and place operations                       │  │
│  │    ○ camera        - Image capture and analysis                      │  │
│  │                                                                       │  │
│  │  Interface Communication Pattern                                      │  │
│  │    ○ serial   - Serial/USB communication (pyserial)                  │  │
│  │    ● socket   - TCP/IP socket communication                          │  │
│  │    ○ rest     - REST API wrapper                                     │  │
│  │    ○ sdk      - Vendor SDK integration                               │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│                          [← Back]  [Cancel]  [Next →]                        │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│ Tab Next Field  ↑↓ Select Option  Enter Confirm  Esc Cancel                  │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Step 3: Interface Variants**
```
┌──────────────────────────────────────────────────────────────────────────────┐
│  MADSci                                                  Create New Module   │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                         Step 3 of 5: Interface Variants                      │
│                         ━━━━━━━━━━━━━━━━━━━━━━━━○○○○                         │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │  Select interface variants to include:                                │  │
│  │                                                                       │  │
│  │    ☑ Real Interface                                                  │  │
│  │      Hardware communication (always included)                         │  │
│  │      → my_pipette_interface.py                                        │  │
│  │                                                                       │  │
│  │    ☑ Fake Interface                                                  │  │
│  │      Simulated behavior for testing without hardware                  │  │
│  │      → my_pipette_fake_interface.py                                   │  │
│  │                                                                       │  │
│  │    ☐ Simulation Interface                                            │  │
│  │      Connects to physics simulation (e.g., Omniverse)                 │  │
│  │      → my_pipette_sim_interface.py                                    │  │
│  │                                                                       │  │
│  │  💡 Tip: Fake interfaces enable testing and CI without hardware      │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│                          [← Back]  [Cancel]  [Next →]                        │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│ Tab Next Field  Space Toggle  Enter Confirm  Esc Cancel                      │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Step 4: Configuration**
```
┌──────────────────────────────────────────────────────────────────────────────┐
│  MADSci                                                  Create New Module   │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                         Step 4 of 5: Configuration                           │
│                         ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━○○                   │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │  Default Port                                                         │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │ 2000                                                            │ │  │
│  │  └─────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                       │  │
│  │  Python Package Settings                                              │  │
│  │                                                                       │  │
│  │  Author Name                                                          │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │ Lab Team                                                        │ │  │
│  │  └─────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                       │  │
│  │  Author Email                                                         │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │ team@lab.org                                                    │ │  │
│  │  └─────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│                          [← Back]  [Cancel]  [Next →]                        │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│ Tab Next Field  Enter Confirm  Esc Cancel                                    │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Step 5: Preview & Create**
```
┌──────────────────────────────────────────────────────────────────────────────┐
│  MADSci                                                  Create New Module   │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                         Step 5 of 5: Preview & Create                        │
│                         ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━              │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │  Module: my_pipette                                                   │  │
│  │  Type: device                                                         │  │
│  │  Template: device                                                     │  │
│  │  Interface: socket                                                    │  │
│  │                                                                       │  │
│  │  Files to create:                                                     │  │
│  │                                                                       │  │
│  │  my_pipette_module/                                                   │  │
│  │  ├── src/                                                             │  │
│  │  │   ├── my_pipette_rest_node.py                                      │  │
│  │  │   ├── my_pipette_interface.py                                      │  │
│  │  │   ├── my_pipette_fake_interface.py                                 │  │
│  │  │   └── my_pipette_types.py                                          │  │
│  │  ├── tests/                                                           │  │
│  │  │   ├── test_my_pipette_node.py                                      │  │
│  │  │   └── test_my_pipette_interface.py                                 │  │
│  │  ├── Dockerfile                                                       │  │
│  │  ├── pyproject.toml                                                   │  │
│  │  └── README.md                                                        │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│                          [← Back]  [Cancel]  [Create]                        │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│ Enter Create  Esc Cancel                                                     │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Wizard Steps Summary:**
1. Basic Information (name, description, node type)
2. Template Selection (module template, communication pattern)
3. Interface Variants (real, fake, sim)
4. Configuration (port, package metadata)
5. Preview & Create

---

## Widget Specifications

### ServiceCard Widget

```python
# widgets/service_card.py
from textual.widgets import Static
from textual.reactive import reactive

class ServiceCard(Static):
    """Display status of a single service."""

    status = reactive("unknown")

    def __init__(self, name: str, url: str, **kwargs):
        super().__init__(**kwargs)
        self.service_name = name
        self.service_url = url

    def render(self) -> str:
        icon = {
            "healthy": "●",
            "unhealthy": "○",
            "starting": "◐",
            "unknown": "?",
        }.get(self.status, "?")

        color = {
            "healthy": "green",
            "unhealthy": "red",
            "starting": "yellow",
            "unknown": "gray",
        }.get(self.status, "gray")

        return f"[{color}]{icon}[/] {self.service_name}"

    async def check_health(self) -> None:
        """Check service health and update status."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.service_url}/health", timeout=5.0)
                self.status = "healthy" if response.status_code == 200 else "unhealthy"
        except Exception:
            self.status = "unhealthy"
```

### LogViewer Widget

```python
# widgets/log_viewer.py
from textual.widgets import RichLog
from textual.reactive import reactive
from collections import deque

class LogViewer(RichLog):
    """Real-time log viewer with filtering."""

    follow = reactive(True)
    min_level = reactive("INFO")
    filter_pattern = reactive("")

    LEVEL_COLORS = {
        "DEBUG": "dim",
        "INFO": "blue",
        "WARNING": "yellow",
        "WARN": "yellow",
        "ERROR": "red",
        "CRITICAL": "red bold",
    }

    def __init__(self, max_lines: int = 1000, **kwargs):
        super().__init__(**kwargs)
        self.max_lines = max_lines
        self._logs = deque(maxlen=max_lines)

    def add_log(self, timestamp: str, level: str, service: str, message: str) -> None:
        """Add a log entry."""
        if not self._should_show(level, message):
            return

        color = self.LEVEL_COLORS.get(level.upper(), "white")
        self.write(
            f"[dim]{timestamp}[/]  [{color}]{level:5}[/]  "
            f"[cyan]{service:12}[/]  {message}"
        )

        if self.follow:
            self.scroll_end(animate=False)

    def _should_show(self, level: str, message: str) -> bool:
        """Check if log should be shown based on filters."""
        # Level filtering
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if levels.index(level.upper()) < levels.index(self.min_level):
            return False

        # Pattern filtering
        if self.filter_pattern and self.filter_pattern.lower() not in message.lower():
            return False

        return True
```

### WorkflowProgress Widget

```python
# widgets/workflow_progress.py
from textual.widgets import Static
from textual.reactive import reactive

class WorkflowProgress(Static):
    """Display workflow execution progress."""

    current_step = reactive(0)
    total_steps = reactive(0)
    status = reactive("pending")

    def render(self) -> str:
        if self.total_steps == 0:
            return "░░░░░░░░░░ 0%"

        progress = self.current_step / self.total_steps
        filled = int(progress * 10)
        empty = 10 - filled

        bar = "█" * filled + "░" * empty
        percent = int(progress * 100)

        color = {
            "running": "blue",
            "completed": "green",
            "failed": "red",
            "paused": "yellow",
        }.get(self.status, "white")

        return f"[{color}]{bar}[/] {percent}%"
```

---

## Styling (Textual CSS)

```css
/* styles/theme.tcss */

/* Global */
Screen {
    background: $surface;
}

Header {
    background: $primary;
    color: $text;
}

Footer {
    background: $primary-darken-2;
}

/* Dashboard */
#dashboard {
    padding: 1;
}

#dashboard Container {
    border: solid $primary;
    padding: 1;
    margin-bottom: 1;
}

#dashboard .title {
    text-style: bold;
    color: $text;
}

/* Service Status */
.service-healthy {
    color: $success;
}

.service-unhealthy {
    color: $error;
}

.service-starting {
    color: $warning;
}

/* Logs */
#log-viewer {
    height: 100%;
    border: solid $primary;
}

.log-debug {
    color: $text-muted;
}

.log-info {
    color: $primary;
}

.log-warning {
    color: $warning;
}

.log-error {
    color: $error;
}

/* Nodes */
.node-item {
    padding: 0 1;
}

.node-item:hover {
    background: $primary-lighten-2;
}

.node-item.selected {
    background: $primary;
}

/* Workflows */
.workflow-step {
    padding: 0 2;
}

.workflow-step-completed {
    color: $success;
}

.workflow-step-running {
    color: $primary;
    text-style: bold;
}

.workflow-step-pending {
    color: $text-muted;
}

.workflow-step-failed {
    color: $error;
}

/* Wizards */
.wizard-container {
    align: center middle;
    padding: 2;
}

.wizard-step-indicator {
    text-align: center;
    margin-bottom: 1;
}

.wizard-input {
    margin: 1 0;
}

.wizard-buttons {
    align: center middle;
    margin-top: 2;
}
```

---

## State Management

```python
# utils/state.py
from dataclasses import dataclass, field
from typing import Optional
from textual.reactive import reactive

@dataclass
class LabState:
    """Global state for the TUI application."""

    # Connection
    lab_url: str = "http://localhost:8000/"
    connected: bool = False

    # Services
    services: dict = field(default_factory=dict)

    # Nodes
    nodes: dict = field(default_factory=dict)
    selected_node: Optional[str] = None

    # Workflows
    active_workflows: list = field(default_factory=list)
    selected_workflow: Optional[str] = None

    # Logs
    log_filter_level: str = "INFO"
    log_filter_services: list = field(default_factory=list)
    log_follow: bool = True


class StateManager:
    """Manages application state and updates."""

    def __init__(self, app: "MadsciApp"):
        self.app = app
        self.state = LabState()
        self._subscribers = []

    def subscribe(self, callback):
        """Subscribe to state changes."""
        self._subscribers.append(callback)

    def notify(self):
        """Notify all subscribers of state change."""
        for callback in self._subscribers:
            callback(self.state)

    async def refresh_all(self):
        """Refresh all state from services."""
        await self.refresh_services()
        await self.refresh_nodes()
        await self.refresh_workflows()
        self.notify()

    async def refresh_services(self):
        """Refresh service status."""
        # Query each manager's health endpoint
        pass

    async def refresh_nodes(self):
        """Refresh node status from workcell manager."""
        pass

    async def refresh_workflows(self):
        """Refresh active workflows from workcell manager."""
        pass
```

---

## Keyboard Shortcuts

### Global Shortcuts

| Key | Action |
|-----|--------|
| `d` | Go to Dashboard |
| `s` | Go to Status |
| `l` | Go to Logs |
| `n` | Go to Nodes |
| `w` | Go to Workflows |
| `q` | Quit application |
| `?` | Show help |
| `Ctrl+P` | Command palette |
| `Esc` | Go back / Cancel |

### Screen-Specific Shortcuts

**Dashboard:**
| Key | Action |
|-----|--------|
| `N` | New experiment |
| `W` | Start workflow |
| `R` | View resources |

**Logs:**
| Key | Action |
|-----|--------|
| `f` | Toggle follow |
| `/` | Search |
| `c` | Clear logs |
| `e` | Export logs |

**Nodes:**
| Key | Action |
|-----|--------|
| `a` | Run action |
| `r` | Restart node |
| `+` | New module |

**Workflows:**
| Key | Action |
|-----|--------|
| `s` | Start workflow |
| `p` | Pause workflow |
| `c` | Cancel workflow |
| `+` | New workflow |

---

## Async Client Integration

```python
# utils/async_client.py
import httpx
from typing import Any, Optional
from contextlib import asynccontextmanager

class AsyncServiceClient:
    """Async HTTP client for MADSci services."""

    def __init__(self, base_url: str, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    async def health(self) -> bool:
        """Check service health."""
        try:
            response = await self._client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception:
            return False

    async def get(self, path: str) -> Any:
        """GET request."""
        response = await self._client.get(f"{self.base_url}{path}")
        response.raise_for_status()
        return response.json()

    async def post(self, path: str, data: dict = None) -> Any:
        """POST request."""
        response = await self._client.post(f"{self.base_url}{path}", json=data)
        response.raise_for_status()
        return response.json()


class AsyncLabClient:
    """Async client for interacting with the full lab."""

    def __init__(self, lab_url: str):
        self.lab_url = lab_url
        self.lab = AsyncServiceClient(lab_url)
        self._manager_clients = {}

    async def get_managers(self) -> dict:
        """Get all manager URLs from lab manager."""
        async with self.lab as client:
            return await client.get("/managers")

    async def get_nodes(self) -> list:
        """Get all nodes from workcell manager."""
        workcell_url = await self._get_manager_url("workcell")
        async with AsyncServiceClient(workcell_url) as client:
            return await client.get("/nodes")

    async def get_workflows(self) -> list:
        """Get active workflows from workcell manager."""
        workcell_url = await self._get_manager_url("workcell")
        async with AsyncServiceClient(workcell_url) as client:
            return await client.get("/workflows")
```

---

## Trogon Integration

For the command-palette feature, we'll use Trogon to auto-generate a TUI for Click commands:

```python
# Integration in app.py
from trogon import Trogon
from ..cli import madsci  # The Click command group

class MadsciApp(App):
    # ...

    def action_command_palette(self) -> None:
        """Show command palette using Trogon."""
        # This will show an interactive form for any CLI command
        Trogon(madsci, app_name="madsci").run()
```

---

## Testing Strategy

Textual provides built-in testing support:

```python
# tests/tui/test_dashboard.py
from textual.testing import AppTest
from madsci.client.cli.tui.app import MadsciApp

async def test_dashboard_loads():
    """Test that dashboard screen loads correctly."""
    async with AppTest(MadsciApp()) as pilot:
        # Check we're on dashboard
        assert pilot.app.screen.name == "dashboard"

        # Check key elements are present
        assert pilot.app.query_one("#services") is not None
        assert pilot.app.query_one("#nodes") is not None

async def test_keyboard_navigation():
    """Test keyboard shortcuts work."""
    async with AppTest(MadsciApp()) as pilot:
        # Press 's' to go to status
        await pilot.press("s")
        assert pilot.app.screen.name == "status"

        # Press 'd' to go back to dashboard
        await pilot.press("d")
        assert pilot.app.screen.name == "dashboard"

async def test_quit():
    """Test quit shortcut."""
    async with AppTest(MadsciApp()) as pilot:
        await pilot.press("q")
        assert pilot.app.is_running is False
```

---

## Implementation Phases

### Phase 1: Foundation
- Main app structure
- Dashboard screen (static)
- Navigation between screens
- Basic styling

### Phase 2: Status & Logs
- Status screen with service list
- Health check integration
- Log viewer with filtering
- Real-time log streaming

### Phase 3: Nodes & Workflows
- Node list and details
- Workflow list and progress
- Action execution UI

### Phase 4: Wizards
- New module wizard (with interface variant selection)
- New interface wizard (add variant to existing module)
- New experiment wizard
- New workflow wizard

### Phase 5: Polish
- Command palette (Trogon)
- Keyboard shortcut help
- Error handling and recovery
- Performance optimization

---

## Dependencies

```toml
# Add to madsci_client/pyproject.toml
dependencies = [
    # ... existing ...
    "textual>=0.50.0",
    "trogon>=0.6.0",  # Already present
]
```

---

## Design Decisions

The following decisions have been made based on review:

1. **Theming**: Support light/dark themes using Textual's built-in theming system. Full custom theme support is deferred to later - users can toggle between light and dark modes via a keyboard shortcut or settings.

2. **Accessibility**: Follow reasonable accessibility best practices:
   - Full keyboard navigation (already core to Textual)
   - High contrast color choices
   - Screen reader-friendly widget labels where possible
   - The CLI remains available as an escape hatch for users who prefer it

3. **Mobile/narrow terminals**: Best effort handling using Textual's responsive layout features. This is not a key priority - the TUI is designed for standard terminal sizes (80x24 minimum). Very small terminals may show a warning message suggesting CLI usage instead.

4. **Persistence**: No wizard state persistence. If a user exits mid-wizard, they start fresh. This keeps the implementation simple and avoids potential issues with stale partial state.

5. **Notifications**: Out of scope for initial implementation. Desktop notifications may be considered in a future version if there's demand.

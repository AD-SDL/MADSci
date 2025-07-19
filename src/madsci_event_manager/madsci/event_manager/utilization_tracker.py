"""
Autonomous Utilization Tracker for MADSci Event Manager

This module automatically tracks system and node utilization based on incoming events.
It maintains state and periodically emits utilization summary events.
"""

import time
from datetime import datetime, timedelta
import io
import base64
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pymongo.synchronous.database import Database
from typing import Dict, Set, Optional, Any
from threading import Thread, Lock
from madsci.common.types.event_types import (
    Event, 
    EventType, 
    EventLogLevel,
    NodeUtilizationData,
    SystemUtilizationData,
    UtilizationSummary,
    UtilizationTrackerSettings
)
from madsci.client.event_client import EventClient

class UtilizationTracker:
    """Autonomous utilization tracker that properly tracks actual work being done."""
    
    def __init__(self, event_client: Optional[EventClient] = None, settings: Optional[UtilizationTrackerSettings] = None):
        self.logger = event_client or EventClient()
        self.logger.event_server = None  # Prevent recursive logging
        self.settings = settings or UtilizationTrackerSettings()
        
        # State tracking
        self.system_util = SystemUtilizationData()
        self.node_utils: Dict[str, NodeUtilizationData] = {}
        self.state_lock = Lock()
        
        # Background thread control
        self.running = False
        self.reporter_thread: Optional[Thread] = None
        
        # Track start time
        self.tracker_start_time = datetime.now()
        
        # Debug counter
        self.events_processed = 0
        
        print(f"DEBUG: UtilizationTracker initialized with reporting interval: {self.settings.reporting_interval}")

    def start(self):
        """Start the background reporting thread."""
        if not self.running:
            self.running = True
            self.reporter_thread = Thread(target=self._background_reporter, daemon=True)
            self.reporter_thread.start()
            self.logger.log_info("Utilization tracker started")
            print("DEBUG: Utilization tracker background thread started")

    def stop(self):
        """Stop the background reporting thread."""
        self.running = False
        if self.reporter_thread:
            self.reporter_thread.join()
        self.logger.log_info("Utilization tracker stopped")

    def process_event(self, event: Event) -> None:
        """Process an incoming event and update utilization state accordingly."""
        # Skip all LOG events - they're just regular logging and not relevant for utilization
        if event.event_type in [
            EventType.LOG, EventType.LOG_DEBUG, EventType.LOG_INFO, 
            EventType.LOG_WARNING, EventType.LOG_ERROR, EventType.LOG_CRITICAL
        ]:
            return
        
        self.events_processed += 1
        
        try:
            with self.state_lock:
                current_time = event.event_timestamp
                
                # System-level events (experiments and workflows)
                if event.event_type in [EventType.EXPERIMENT_START, EventType.CAMPAIGN_START]:
                    self._handle_experiment_start(event, current_time)
                    
                elif event.event_type in [
                    EventType.EXPERIMENT_COMPLETE, 
                    EventType.EXPERIMENT_FAILED, 
                    EventType.EXPERIMENT_CANCELLED,
                    EventType.CAMPAIGN_COMPLETE,
                    EventType.CAMPAIGN_ABORT
                ]:
                    self._handle_experiment_end(event, current_time)
                    
                elif event.event_type == EventType.WORKFLOW_START:
                    self._handle_workflow_start(event, current_time)
                    
                elif event.event_type in [EventType.WORKFLOW_COMPLETE, EventType.WORKFLOW_ABORT]:
                    self._handle_workflow_end(event, current_time)
                
                # Node lifecycle events (active/inactive)
                elif event.event_type == EventType.NODE_START:
                    self._handle_node_start(event, current_time)
                    
                elif event.event_type == EventType.NODE_STOP:
                    self._handle_node_stop(event, current_time)
                
                # Action execution events (this is where real "busy" time happens)
                elif event.event_type == EventType.ACTION_STATUS_CHANGE:
                    self._handle_action_status_change(event, current_time)
                
                # Generic node status updates (don't assume busy)
                elif event.event_type == EventType.NODE_STATUS_UPDATE:
                    self._handle_node_status_update(event, current_time)
                    
        except Exception as e:
            print(f"ERROR: Failed to process {event.event_type} event: {e}")

    def _handle_experiment_start(self, event: Event, current_time: datetime):
        """Handle experiment start events."""
        experiment_id = self._extract_id(event, "experiment_id")
        if experiment_id:
            self.system_util.active_experiments.add(experiment_id)
            self._update_system_state("active", current_time)
            print(f"UTIL: Started tracking experiment {experiment_id}")

    def _handle_experiment_end(self, event: Event, current_time: datetime):
        """Handle experiment end events."""
        experiment_id = self._extract_id(event, "experiment_id")
        if experiment_id:
            self.system_util.active_experiments.discard(experiment_id)
            print(f"UTIL: Stopped tracking experiment {experiment_id}")
            
            if not self.system_util.active_experiments and not self.system_util.active_workflows:
                self._update_system_state("idle", current_time)

    def _handle_workflow_start(self, event: Event, current_time: datetime):
        """Handle workflow start events."""
        workflow_id = self._extract_id(event, "workflow_id")
        
        if workflow_id:
            self.system_util.active_workflows.add(workflow_id)
            self._update_system_state("active", current_time)
            
            # Extract involved nodes but DON'T mark them as busy yet
            nodes = self._extract_workflow_nodes(event)
            for node_id in nodes:
                self._update_node_active_state(node_id, "active", current_time)
            
            print(f"UTIL: Started tracking workflow {workflow_id} with {len(nodes)} nodes")

    def _handle_workflow_end(self, event: Event, current_time: datetime):
        """Handle workflow end events."""
        workflow_id = self._extract_id(event, "workflow_id")
        if workflow_id:
            self.system_util.active_workflows.discard(workflow_id)
            
            # When workflow ends, clear any remaining actions and mark nodes as available
            nodes = self._extract_workflow_nodes(event)
            for node_id in nodes:
                node_util = self.node_utils.get(node_id)
                if node_util:
                    node_util.active_actions.clear()
                    self._update_node_busy_state(node_id, "available", current_time)
            
            print(f"UTIL: Stopped tracking workflow {workflow_id}")
            
            if not self.system_util.active_experiments and not self.system_util.active_workflows:
                self._update_system_state("idle", current_time)

    def _handle_node_start(self, event: Event, current_time: datetime):
        """Handle node startup events - node becomes active/available."""
        node_id = self._extract_node_id(event)
        if node_id:
            self._get_or_create_node_util(node_id)
            self._update_node_active_state(node_id, "active", current_time)
            print(f"UTIL: Node {node_id} is now ACTIVE")

    def _handle_node_stop(self, event: Event, current_time: datetime):
        """Handle node shutdown events - node becomes inactive."""
        node_id = self._extract_node_id(event)
        if node_id:
            self._update_node_active_state(node_id, "inactive", current_time)
            # If node stops, any running actions also stop
            node_util = self.node_utils.get(node_id)
            if node_util:
                node_util.active_actions.clear()
                self._update_node_busy_state(node_id, "available", current_time)
            print(f"UTIL: Node {node_id} is now INACTIVE")

    def _handle_node_status_update(self, event: Event, current_time: datetime):
        """Handle general node status updates - don't assume busy."""
        node_id = self._extract_node_id(event)
        if node_id:
            self._update_node_active_state(node_id, "active", current_time)

    def _handle_action_status_change(self, event: Event, current_time: datetime):
        """Handle action status change events - this is where real busy time happens."""
        node_id = self._extract_node_id(event)
        action_id = self._extract_id(event, "action_id")
        
        # Safe access to status field
        status = "unknown"
        if isinstance(event.event_data, dict):
            status = event.event_data.get("status", "unknown")
        
        if node_id and action_id:
            node_util = self._get_or_create_node_util(node_id)
            
            # UPDATED: Use the actual status values from your system
            if status in ["running", "started", "in_progress"]:
                # Action is now executing - node becomes BUSY
                node_util.active_actions.add(action_id)
                self._update_node_busy_state(node_id, "busy", current_time)
                self._update_node_active_state(node_id, "active", current_time)
                print(f"UTIL: Node {node_id} is now BUSY executing action {action_id}")
                
            elif status in ["completed", "failed", "cancelled", "finished", "succeeded"]:
                # ADDED "succeeded" to the completion statuses!
                # Action finished - check if node still has other actions
                node_util.active_actions.discard(action_id)
                if not node_util.active_actions:
                    self._update_node_busy_state(node_id, "available", current_time)
                    print(f"UTIL: Node {node_id} is now AVAILABLE")
                else:
                    print(f"UTIL: Node {node_id} still BUSY with {len(node_util.active_actions)} actions")
            
            else:
                # Log unrecognized statuses for debugging
                print(f"UTIL: Unrecognized action status '{status}' for action {action_id} on node {node_id}")

    def _update_system_state(self, new_state: str, current_time: datetime):
        """Update system utilization state."""
        if self.system_util.current_state != new_state:
            # Update time for previous state
            if self.system_util.last_state_change:
                time_diff = (current_time - self.system_util.last_state_change).total_seconds()
                if self.system_util.current_state == "active":
                    self.system_util.active_time += time_diff
                else:
                    self.system_util.idle_time += time_diff
                self.system_util.total_time += time_diff
            
            # Update to new state
            self.system_util.current_state = new_state
            self.system_util.last_state_change = current_time

    def _update_node_active_state(self, node_id: str, new_state: str, current_time: datetime):
        """Update node active/inactive state (availability for work)."""
        node_util = self._get_or_create_node_util(node_id)
        
        if not hasattr(node_util, 'active_state'):
            node_util.active_state = "unknown"
            node_util.last_active_change = None
            node_util.active_time = 0.0
            node_util.inactive_time = 0.0
        
        if node_util.active_state != new_state:
            # Update time for previous state
            if node_util.last_active_change:
                time_diff = (current_time - node_util.last_active_change).total_seconds()
                if node_util.active_state == "active":
                    node_util.active_time += time_diff
                else:
                    node_util.inactive_time += time_diff
                node_util.total_time += time_diff
            
            # Update to new state
            node_util.active_state = new_state
            node_util.last_active_change = current_time

    def _update_node_busy_state(self, node_id: str, new_state: str, current_time: datetime):
        """Update node busy/available state (actually executing actions)."""
        node_util = self._get_or_create_node_util(node_id)
        
        if node_util.current_state != new_state:
            # Update time for previous state
            if node_util.last_state_change:
                time_diff = (current_time - node_util.last_state_change).total_seconds()
                if node_util.current_state == "busy":
                    node_util.busy_time += time_diff
                else:
                    node_util.idle_time += time_diff
            
            # Update to new state
            node_util.current_state = new_state
            node_util.last_state_change = current_time

    def _get_or_create_node_util(self, node_id: str) -> NodeUtilizationData:
        """Get or create a NodeUtilizationData object."""
        if node_id not in self.node_utils:
            self.node_utils[node_id] = NodeUtilizationData(node_id=node_id)
        return self.node_utils[node_id]

    def _extract_id(self, event: Event, id_field: str) -> Optional[str]:
        """Extract an ID from event data."""
        # First try direct field access (only if event_data is dict)
        if isinstance(event.event_data, dict) and id_field in event.event_data:
            return event.event_data[id_field]
        
        # For experiment events, extract from experiment object
        if isinstance(event.event_data, dict) and "experiment" in event.event_data:
            experiment = event.event_data["experiment"]
            if isinstance(experiment, dict):
                experiment_id = experiment.get("experiment_id") or experiment.get("_id")
                if experiment_id and id_field == "experiment_id":
                    return experiment_id
        
        # Fallback to source ownership info
        if hasattr(event, 'source') and event.source:
            source = event.source
            
            if id_field == "experiment_id" and hasattr(source, 'experiment_id'):
                return source.experiment_id
            elif id_field == "workflow_id" and hasattr(source, 'workflow_id'):
                return source.workflow_id
            elif id_field == "node_id" and hasattr(source, 'node_id'):
                return source.node_id
            elif hasattr(source, 'manager_id'):
                return source.manager_id
        
        return None

    def _extract_node_id(self, event: Event) -> Optional[str]:
        """Extract node ID from event."""
        # Try event data first (only if it's a dict)
        if hasattr(event, 'source') and event.source:
            if hasattr(event.source, 'node_id') and event.source.node_id:
                return event.source.node_id
            # Also try workcell_id as fallback
            if hasattr(event.source, 'workcell_id') and event.source.workcell_id:
                return event.source.workcell_id
        
        # Try event data as fallback (only if it's a dict)
        if isinstance(event.event_data, dict):
            node_id = (
                event.event_data.get("node_id") or 
                event.event_data.get("node_name")
            )
            if node_id:
                return node_id
            
        return None

    def _extract_workflow_nodes(self, event: Event) -> Set[str]:
        """Extract involved node IDs from workflow event."""
        nodes = set()
        
        if not isinstance(event.event_data, dict):
            return nodes
            
        workflow_data = event.event_data.get("workflow", {})
        steps = workflow_data.get("steps", [])
        
        for step in steps:
            if isinstance(step, dict) and "node" in step:
                nodes.add(step["node"])
        
        return nodes

    def _background_reporter(self):
        """Background thread that periodically emits utilization reports."""
        while self.running:
            try:
                time.sleep(self.settings.reporting_interval)
                if self.running:
                    self._emit_utilization_report()
            except Exception as e:
                self.logger.log_error(f"Error in utilization reporter: {e}")

    def _emit_utilization_report(self):
        """Emit utilization summary events."""
        current_time = datetime.now()
        
        with self.state_lock:
            # Update current state times
            self._update_system_state(self.system_util.current_state, current_time)
            for node_id, node_util in self.node_utils.items():
                self._update_node_busy_state(node_id, node_util.current_state, current_time)
                self._update_node_active_state(node_id, node_util.active_state, current_time)
            
            # Calculate utilization percentages
            self.system_util.utilization_percentage = self._calculate_system_utilization()
            for node_id, node_util in self.node_utils.items():
                node_util.utilization_percentage = self._calculate_node_utilization(node_util)

    def _calculate_system_utilization(self) -> float:
        """Calculate system utilization percentage."""
        if self.system_util.total_time == 0:
            if self.system_util.current_state == "active":
                return 100.0
            else:
                return 0.0
        
        utilization = (self.system_util.active_time / self.system_util.total_time) * 100
        return utilization

    def _calculate_node_utilization(self, node_util: NodeUtilizationData) -> float:
        """Calculate utilization percentage for a single node."""
        active_time = getattr(node_util, 'active_time', 0.0)
        
        if active_time == 0:
            return 0.0
        
        if node_util.busy_time == 0:
            return 0.0
        
        utilization = (node_util.busy_time / active_time) * 100
        return min(utilization, 100.0)

    def get_utilization_summary(self) -> UtilizationSummary:
        """Get current utilization summary for external queries."""
        current_time = datetime.now()
        
        with self.state_lock:
            # Update ALL current state times BEFORE calculating percentages
            self._update_system_state(self.system_util.current_state, current_time)
            for node_id, node_util in self.node_utils.items():
                self._update_node_busy_state(node_id, node_util.current_state, current_time)
                self._update_node_active_state(node_id, node_util.active_state, current_time)
            
            # Calculate utilization percentages AFTER updating times
            self.system_util.utilization_percentage = self._calculate_system_utilization()
            for node_id, node_util in self.node_utils.items():
                util_pct = self._calculate_node_utilization(node_util)
                node_util.utilization_percentage = util_pct
            
            return UtilizationSummary(
                system_utilization=self.system_util,
                node_utilizations=self.node_utils.copy(),
                reporting_interval=self.settings.reporting_interval,
                tracker_uptime=(current_time - self.tracker_start_time).total_seconds(),
                summary_timestamp=current_time
            )
        
    def create_visualizer(self, db_connection) -> 'UtilizationVisualizer':
        """
        Create a UtilizationVisualizer instance for this tracker.
        
        Args:
            db_connection: Database connection to query utilization events
            
        Returns:
            UtilizationVisualizer instance
        """
        return UtilizationVisualizer(db_connection)
    
class UtilizationVisualizer:
    """
    Generates graphs and visualizations from utilization data stored in the Event Manager.
    """
    
    def __init__(self, db_connection: Database):
        self.db_connection = db_connection
        self.events_collection = db_connection["events"]
    
    def get_utilization_data(self, hours_back: int = 24, node_id: Optional[str] = None) -> list[Dict[str, Any]]:
        """
        Query utilization events from the database.
        
        Args:
            hours_back: Number of hours to look back
            node_id: Specific node ID to filter by (None for system data)
        
        Returns:
            List of utilization events
        """
        since_time = datetime.now() - timedelta(hours=hours_back)
        
        if node_id:
            selector = {
                "event_timestamp": {"$gte": since_time},
                "event_type": "utilization_system_summary",
                "event_data.node_utilizations": {"$exists": True}
            }
        else:
            selector = {
                "event_timestamp": {"$gte": since_time},
                "event_type": "utilization_system_summary"
            }
        
        events = list(self.events_collection.find(selector).sort("event_timestamp", 1))
        return events
    
    def prepare_system_data(self, events: list[Dict[str, Any]]) -> pd.DataFrame:
        """
        Prepare system utilization data for plotting.
        
        Args:
            events: List of utilization events
            
        Returns:
            DataFrame with system utilization data
        """
        data = []
        for event in events:
            event_data = event.get("event_data", {})
            system_util = event_data.get("system_utilization", {})
            
            data.append({
                "timestamp": event["event_timestamp"],
                "utilization_percentage": system_util.get("utilization_percentage", 0),
                "active_experiments": len(system_util.get("active_experiments", [])),
                "active_workflows": len(system_util.get("active_workflows", [])),
                "current_state": system_util.get("current_state", "unknown")
            })
        
        df = pd.DataFrame(data)
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp")
        
        return df
    
    def prepare_node_data(self, events: list[Dict[str, Any]], node_id: str) -> pd.DataFrame:
        """
        Prepare node utilization data for plotting.
        
        Args:
            events: List of utilization events
            node_id: Specific node ID to extract data for
            
        Returns:
            DataFrame with node utilization data
        """
        data = []
        for event in events:
            event_data = event.get("event_data", {})
            node_utils = event_data.get("node_utilizations", {})
            
            if node_id in node_utils:
                node_util = node_utils[node_id]
                data.append({
                    "timestamp": event["event_timestamp"],
                    "utilization_percentage": node_util.get("utilization_percentage", 0),
                    "current_state": node_util.get("current_state", "unknown"),
                    "active_actions": len(node_util.get("active_actions", [])),
                    "busy_time": node_util.get("busy_time", 0),
                    "idle_time": node_util.get("idle_time", 0)
                })
        
        df = pd.DataFrame(data)
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp")
        
        return df
    
    def get_all_node_ids(self, events: list[Dict[str, Any]]) -> list[str]:
        """
        Extract all unique node IDs from utilization events.
        
        Args:
            events: List of utilization events
            
        Returns:
            List of unique node IDs
        """
        node_ids = set()
        for event in events:
            event_data = event.get("event_data", {})
            node_utils = event_data.get("node_utilizations", {})
            node_ids.update(node_utils.keys())
        
        return sorted(list(node_ids))
    
    def generate_system_utilization_graph(self, hours_back: int = 24) -> str:
        """
        Generate system utilization graph.
        
        Args:
            hours_back: Number of hours to look back
            
        Returns:
            Base64 encoded PNG image
        """
        events = self.get_utilization_data(hours_back=hours_back)
        df = self.prepare_system_data(events)
        
        if df.empty:
            return self._create_no_data_plot("No system utilization data available")
        
        plt.style.use('default')
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        
        # Plot utilization percentage
        ax1.plot(df["timestamp"], df["utilization_percentage"], 'b-', linewidth=2, label='System Utilization')
        ax1.fill_between(df["timestamp"], 0, df["utilization_percentage"], alpha=0.3)
        ax1.set_ylabel('Utilization (%)')
        ax1.set_title(f'System Utilization - Last {hours_back} Hours')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        ax1.set_ylim(0, 100)
        
        # Plot active experiments and workflows
        ax2.plot(df["timestamp"], df["active_experiments"], 'g-', linewidth=2, label='Active Experiments')
        ax2.plot(df["timestamp"], df["active_workflows"], 'r-', linewidth=2, label='Active Workflows')
        ax2.set_ylabel('Count')
        ax2.set_xlabel('Time')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        
        # Format x-axis
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax2.xaxis.set_major_locator(mdates.HourLocator(interval=max(1, hours_back // 12)))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        return self._plot_to_base64(fig)
    
    def generate_node_utilization_graph(self, node_id: str, hours_back: int = 24) -> str:
        """
        Generate node utilization graph.
        
        Args:
            node_id: Node ID to generate graph for
            hours_back: Number of hours to look back
            
        Returns:
            Base64 encoded PNG image
        """
        events = self.get_utilization_data(hours_back=hours_back)
        df = self.prepare_node_data(events, node_id)
        
        if df.empty:
            return self._create_no_data_plot(f"No utilization data available for node: {node_id}")
        
        plt.style.use('default')
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        
        # Plot utilization percentage
        ax1.plot(df["timestamp"], df["utilization_percentage"], 'b-', linewidth=2)
        ax1.fill_between(df["timestamp"], 0, df["utilization_percentage"], alpha=0.3)
        ax1.set_ylabel('Utilization (%)')
        ax1.set_title(f'Node Utilization: {node_id} - Last {hours_back} Hours')
        ax1.grid(True, alpha=0.3)
        ax1.set_ylim(0, 100)
        
        # Plot active actions
        ax2.plot(df["timestamp"], df["active_actions"], 'r-', linewidth=2, label='Active Actions')
        ax2.set_ylabel('Active Actions')
        ax2.set_xlabel('Time')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        
        # Format x-axis
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax2.xaxis.set_major_locator(mdates.HourLocator(interval=max(1, hours_back // 12)))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        return self._plot_to_base64(fig)
    
    def generate_multi_node_comparison_graph(self, hours_back: int = 24, max_nodes: int = 6) -> str:
        """
        Generate comparison graph for multiple nodes.
        
        Args:
            hours_back: Number of hours to look back
            max_nodes: Maximum number of nodes to include
            
        Returns:
            Base64 encoded PNG image
        """
        events = self.get_utilization_data(hours_back=hours_back)
        node_ids = self.get_all_node_ids(events)[:max_nodes]
        
        if not node_ids:
            return self._create_no_data_plot("No node utilization data available")
        
        plt.style.use('default')
        fig, ax = plt.subplots(figsize=(12, 8))
        
        colors = plt.cm.tab10(range(len(node_ids)))
        
        for i, node_id in enumerate(node_ids):
            df = self.prepare_node_data(events, node_id)
            if not df.empty:
                ax.plot(df["timestamp"], df["utilization_percentage"], 
                       color=colors[i], linewidth=2, label=node_id)
        
        ax.set_ylabel('Utilization (%)')
        ax.set_xlabel('Time')
        ax.set_title(f'Node Utilization Comparison - Last {hours_back} Hours')
        ax.grid(True, alpha=0.3)
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.set_ylim(0, 100)
        
        # Format x-axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=max(1, hours_back // 12)))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        return self._plot_to_base64(fig)
    
    def generate_utilization_heatmap(self, hours_back: int = 24) -> str:
        """
        Generate utilization heatmap for all nodes over time.
        
        Args:
            hours_back: Number of hours to look back
            
        Returns:
            Base64 encoded PNG image
        """
        events = self.get_utilization_data(hours_back=hours_back)
        node_ids = self.get_all_node_ids(events)
        
        if not node_ids:
            return self._create_no_data_plot("No node utilization data available for heatmap")
        
        # Create a matrix of utilization data
        timestamps = []
        utilization_matrix = []
        
        for event in events:
            event_data = event.get("event_data", {})
            node_utils = event_data.get("node_utilizations", {})
            timestamp = event["event_timestamp"]
            
            timestamps.append(timestamp)
            row = []
            for node_id in node_ids:
                if node_id in node_utils:
                    util = node_utils[node_id].get("utilization_percentage", 0)
                else:
                    util = 0
                row.append(util)
            utilization_matrix.append(row)
        
        if not utilization_matrix:
            return self._create_no_data_plot("No utilization data available for heatmap")
        
        plt.style.use('default')
        fig, ax = plt.subplots(figsize=(12, max(6, len(node_ids) * 0.5)))
        
        # Convert to numpy array for plotting
        import numpy as np
        matrix = np.array(utilization_matrix).T
        
        im = ax.imshow(matrix, cmap='RdYlGn', aspect='auto', vmin=0, vmax=100)
        
        # Set labels
        ax.set_yticks(range(len(node_ids)))
        ax.set_yticklabels(node_ids)
        
        # Format x-axis with time labels
        time_indices = range(0, len(timestamps), max(1, len(timestamps) // 10))
        ax.set_xticks(time_indices)
        time_labels = [timestamps[i].strftime('%H:%M') for i in time_indices]
        ax.set_xticklabels(time_labels, rotation=45)
        
        ax.set_xlabel('Time')
        ax.set_ylabel('Nodes')
        ax.set_title(f'Node Utilization Heatmap - Last {hours_back} Hours')
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Utilization (%)')
        
        plt.tight_layout()
        return self._plot_to_base64(fig)
    
    def _plot_to_base64(self, fig) -> str:
        """Convert matplotlib figure to base64 string."""
        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        plt.close(fig)
        
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        buffer.close()
        
        return image_base64
    
    def _create_no_data_plot(self, message: str) -> str:
        """Create a simple plot indicating no data available."""
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.text(0.5, 0.5, message, transform=ax.transAxes, 
                ha='center', va='center', fontsize=14, 
                bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.7))
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        ax.set_title('Utilization Data')
        
        plt.tight_layout()
        return self._plot_to_base64(fig)
    
    def generate_utilization_report(self, hours_back: int = 24) -> Dict[str, Any]:
        """
        Generate a comprehensive utilization report.
        
        Args:
            hours_back: Number of hours to analyze
            
        Returns:
            Dictionary containing utilization statistics and graphs
        """
        events = self.get_utilization_data(hours_back=hours_back)
        
        if not events:
            return {
                "error": "No utilization data available",
                "hours_analyzed": hours_back,
                "data_points": 0
            }
        
        # System statistics
        system_df = self.prepare_system_data(events)
        system_stats = {}
        
        if not system_df.empty:
            system_stats = {
                "average_utilization": float(system_df["utilization_percentage"].mean()),
                "max_utilization": float(system_df["utilization_percentage"].max()),
                "min_utilization": float(system_df["utilization_percentage"].min()),
                "total_experiments": int(system_df["active_experiments"].sum()),
                "total_workflows": int(system_df["active_workflows"].sum())
            }
        
        # Node statistics
        node_ids = self.get_all_node_ids(events)
        node_stats = {}
        
        for node_id in node_ids:
            node_df = self.prepare_node_data(events, node_id)
            if not node_df.empty:
                node_stats[node_id] = {
                    "average_utilization": float(node_df["utilization_percentage"].mean()),
                    "max_utilization": float(node_df["utilization_percentage"].max()),
                    "total_actions": int(node_df["active_actions"].sum())
                }
        
        # Generate graphs
        graphs = {
            "system_utilization": self.generate_system_utilization_graph(hours_back),
            "node_comparison": self.generate_multi_node_comparison_graph(hours_back),
            "utilization_heatmap": self.generate_utilization_heatmap(hours_back)
        }
        
        return {
            "hours_analyzed": hours_back,
            "data_points": len(events),
            "analysis_timestamp": datetime.now().isoformat(),
            "system_statistics": system_stats,
            "node_statistics": node_stats,
            "available_nodes": node_ids,
            "graphs": graphs
        }
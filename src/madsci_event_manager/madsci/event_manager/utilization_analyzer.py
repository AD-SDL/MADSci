"""
Complete final fixed utilization analyzer with proper dynamic calculations and UTC timezone handling.
Keep original class names: UtilizationAnalyzer and UtilizationVisualizer
"""

import time
from datetime import datetime, timedelta, timezone
import io
import base64
import matplotlib.pyplot as plt
from pymongo.synchronous.collection import Collection
from typing import Dict, Set, Optional, Any, List, Tuple
from madsci.common.types.event_types import (
    Event, 
    EventType, 
    NodeUtilizationData,
    SystemUtilizationData,
    UtilizationSummary,
)
from collections import defaultdict


class UtilizationAnalyzer:
    """
    Complete final fixed utilization analyzer that properly calculates dynamic utilization.
    """
    
    def __init__(self, events_collection: Collection):
        """Initialize with the existing events collection from FastAPI server."""
        self.events_collection = events_collection
        print(f"Initialized UtilizationAnalyzer with collection: {events_collection.name}")
    
    def analyze_utilization(
        self, 
        start_time: Optional[datetime] = None, 
        end_time: Optional[datetime] = None
    ) -> UtilizationSummary:
        """
        Analyze utilization with dynamic calculations based on actual events.
        """
        try:
            # Use UTC timezone consistently
            analysis_start, analysis_end = self._determine_timeframe_utc(start_time, end_time)
            
            print(f"Analyzing utilization from {analysis_start} to {analysis_end} (UTC)")
            
            # Get all events in timeframe
            all_events = self._get_events_utc(analysis_start, analysis_end)
            
            print(f"Found {len(all_events)} total events in timeframe")
            
            if not all_events:
                print("No events found in timeframe, using fallback calculation")
                return self._create_minimal_summary(analysis_start, analysis_end)
            
            # Analyze events for actual activity
            self._show_event_summary(all_events)
            
            # Filter to utilization-relevant events
            relevant_events = self._filter_activity_events(all_events)
            
            print(f"Found {len(relevant_events)} activity-relevant events")
            
            # Calculate real utilization based on actual events
            system_util = self._calculate_real_system_utilization(relevant_events, analysis_start, analysis_end)
            node_utils = self._calculate_real_node_utilization(relevant_events, analysis_start, analysis_end)
            
            return UtilizationSummary(
                system_utilization=system_util,
                node_utilizations=node_utils,
                reporting_interval=0,
                tracker_uptime=(analysis_end - analysis_start).total_seconds(),
                summary_timestamp=datetime.now(timezone.utc)
            )
        
        except Exception as e:
            print(f"ERROR in analyze_utilization: {e}")
            import traceback
            traceback.print_exc()
            
            fallback_start = start_time or datetime.now(timezone.utc) - timedelta(hours=1)
            fallback_end = end_time or datetime.now(timezone.utc)
            return self._create_minimal_summary(fallback_start, fallback_end)
    
    def _determine_timeframe_utc(
        self, 
        start_time: Optional[datetime], 
        end_time: Optional[datetime]
    ) -> Tuple[datetime, datetime]:
        """Determine timeframe using UTC timezone consistently."""
        
        if start_time and end_time:
            # Convert to UTC if needed
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=timezone.utc)
            return start_time.replace(tzinfo=None), end_time.replace(tzinfo=None)
        
        # Get recent events to determine proper time window
        try:
            recent_events = list(self.events_collection.find({}).sort("event_timestamp", -1).limit(20))
            
            if recent_events:
                timestamps = []
                for event in recent_events:
                    ts = self._parse_timestamp_utc(event.get("event_timestamp"))
                    if ts:
                        timestamps.append(ts)
                
                if timestamps:
                    latest = max(timestamps)
                    earliest = min(timestamps)
                    
                    # Expand window to include some buffer
                    window_start = earliest - timedelta(hours=1)
                    window_end = latest + timedelta(hours=1)
                    
                    print(f"Using event-based timeframe: {window_start} to {window_end}")
                    return window_start, window_end
        
        except Exception as e:
            print(f"Error determining timeframe: {e}")
        
        # Fallback: last 4 hours in UTC
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        fallback_start = now_utc - timedelta(hours=4)
        
        print(f"Using fallback timeframe: {fallback_start} to {now_utc}")
        return fallback_start, now_utc
    
    def _get_events_utc(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Get events with UTC timezone handling."""
        
        try:
            # Try multiple approaches to find events
            approaches = [
                # Direct datetime comparison
                {"event_timestamp": {"$gte": start_time, "$lte": end_time}},
                
                # String comparison for ISO format
                {"event_timestamp": {"$gte": start_time.isoformat(), "$lte": end_time.isoformat()}},
                
                # Get all recent events regardless of timestamp
                {}
            ]
            
            events = []
            
            for i, query in enumerate(approaches):
                try:
                    if i == 2:  # Last approach - get recent events
                        events = list(self.events_collection.find(query).sort("event_timestamp", -1).limit(200))
                    else:
                        events = list(self.events_collection.find(query).sort("event_timestamp", 1))
                    
                    if events:
                        print(f"Query approach {i+1} found {len(events)} events")
                        break
                    
                except Exception as e:
                    print(f"Query approach {i+1} failed: {e}")
                    continue
            
            # Parse all timestamps to UTC
            for event in events:
                if "event_timestamp" in event:
                    event["event_timestamp"] = self._parse_timestamp_utc(event["event_timestamp"])
            
            return events
        
        except Exception as e:
            print(f"Error getting events: {e}")
            return []
    
    def _parse_timestamp_utc(self, timestamp) -> Optional[datetime]:
        """Parse timestamp and convert to UTC (timezone-naive)."""
        
        if isinstance(timestamp, datetime):
            # Convert to UTC and remove timezone info for consistency
            if timestamp.tzinfo is not None:
                return timestamp.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                return timestamp
        
        if isinstance(timestamp, str):
            try:
                # Handle various ISO formats
                if 'T' in timestamp:
                    if timestamp.endswith('Z'):
                        # UTC timestamp
                        return datetime.fromisoformat(timestamp.replace('Z', '+00:00')).astimezone(timezone.utc).replace(tzinfo=None)
                    elif '+' in timestamp or timestamp.count('-') > 2:
                        # Timezone aware
                        return datetime.fromisoformat(timestamp).astimezone(timezone.utc).replace(tzinfo=None)
                    else:
                        # Assume UTC if no timezone
                        return datetime.fromisoformat(timestamp)
                else:
                    # Simple date format
                    return datetime.fromisoformat(timestamp)
                    
            except ValueError:
                try:
                    return datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    print(f"Could not parse timestamp: {timestamp}")
                    return None
        
        return None
    
    def _show_event_summary(self, events: List[Dict]):
        """Show summary of what events we found."""
        
        event_type_counts = defaultdict(int)
        experiment_events = []
        workflow_events = []
        action_events = []
        
        for event in events:
            event_type = event.get("event_type", "unknown")
            event_type_counts[event_type] += 1
            
            # Categorize events
            if "experiment" in event_type.lower():
                experiment_events.append(event)
            elif "workflow" in event_type.lower():
                workflow_events.append(event)
            elif "action" in event_type.lower():
                action_events.append(event)
        
        print("Event summary:")
        for event_type, count in sorted(event_type_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {event_type}: {count}")
        
        print(f"Activity events: {len(experiment_events)} experiment, {len(workflow_events)} workflow, {len(action_events)} action")
    
    def _filter_activity_events(self, events: List[Dict]) -> List[Dict]:
        """Filter events that indicate actual system activity."""
        
        relevant_events = []
        
        for event in events:
            event_type = event.get("event_type", "").lower()
            
            # Skip ALL LOG events like the working tracker does
            if any(log_type in event_type for log_type in 
                ["log", "log_debug", "log_info", "log_warning", "log_error", "log_critical"]):
                continue
            
            # Include the EXACT event types that the working tracker handles
            activity_event_types = [
                # System-level events
                "experiment_start", "experiment_complete", "experiment_failed", 
                "experiment_cancelled", "campaign_start", "campaign_complete", "campaign_abort",
                
                # Workflow events
                "workflow_start", "workflow_complete", "workflow_abort",
                
                # Node lifecycle events
                "node_start", "node_stop", "node_status_update",
                
                # Action execution events - MOST IMPORTANT FOR NODE UTILIZATION
                "action_status_change"
            ]
            
            if any(activity_type in event_type for activity_type in activity_event_types):
                relevant_events.append(event)
        
        return relevant_events
    
    def _has_operational_context(self, event: Dict) -> bool:
        """Check if event has operational context (node, experiment, etc.)."""
        
        source = event.get("source", {})
        if isinstance(source, dict):
            # Has experiment or workflow context
            if source.get("experiment_id") or source.get("workflow_id"):
                return True
            
            # Has node context that looks like actual equipment
            node_info = source.get("node_id") or source.get("workcell_id")
            if node_info and any(equipment in str(node_info).lower() for equipment in 
                               ["liquidhandler", "robotarm", "platereader", "node"]):
                return True
        
        return False
    
    def _calculate_real_system_utilization(
        self, 
        events: List[Dict], 
        start_time: datetime, 
        end_time: datetime
    ) -> SystemUtilizationData:
        """Calculate real system utilization based on actual events."""
        
        system_util = SystemUtilizationData()
        
        # Track actual experiments and workflows
        active_experiments = set()
        active_workflows = set()
        
        # Track activity periods based on actual events
        activity_periods = []
        experiment_periods = []
        workflow_periods = []
        
        print(f"Calculating system utilization from {len(events)} activity events...")
        
        # Process events chronologically
        sorted_events = sorted(events, key=lambda e: self._parse_timestamp_utc(e.get("event_timestamp")) or datetime.min)
        
        # Track experiment lifecycles
        experiment_starts = {}
        workflow_starts = {}
        
        for event in sorted_events:
            event_time = self._parse_timestamp_utc(event.get("event_timestamp"))
            if not event_time:
                continue
                
            event_type = event.get("event_type", "").lower()
            
            # Track experiment events
            if "experiment_start" in event_type:
                exp_id = self._extract_experiment_id(event)
                if exp_id:
                    active_experiments.add(exp_id)
                    experiment_starts[exp_id] = event_time
                    print(f"  Experiment started: {exp_id} at {event_time}")
            
            elif any(end_pattern in event_type for end_pattern in ["experiment_complete", "experiment_failed", "experiment_stop"]):
                exp_id = self._extract_experiment_id(event)
                if exp_id and exp_id in experiment_starts:
                    start_time_exp = experiment_starts[exp_id]
                    experiment_periods.append((start_time_exp, event_time))
                    active_experiments.discard(exp_id)
                    duration = (event_time - start_time_exp).total_seconds()
                    print(f"  Experiment completed: {exp_id}, duration: {duration:.1f}s")
            
            # Track workflow events
            elif "workflow_start" in event_type:
                workflow_id = self._extract_workflow_id(event)
                if workflow_id:
                    active_workflows.add(workflow_id)
                    workflow_starts[workflow_id] = event_time
                    print(f"  Workflow started: {workflow_id} at {event_time}")
            
            elif any(end_pattern in event_type for end_pattern in ["workflow_complete", "workflow_abort", "workflow_stop"]):
                workflow_id = self._extract_workflow_id(event)
                if workflow_id and workflow_id in workflow_starts:
                    start_time_wf = workflow_starts[workflow_id]
                    workflow_periods.append((start_time_wf, event_time))
                    active_workflows.discard(workflow_id)
                    duration = (event_time - start_time_wf).total_seconds()
                    print(f"  Workflow completed: {workflow_id}, duration: {duration:.1f}s")
        
        # Handle ongoing activities
        current_time = end_time
        for exp_id, start_time_exp in experiment_starts.items():
            if exp_id in active_experiments:
                experiment_periods.append((start_time_exp, current_time))
                print(f"  Experiment {exp_id} still active at analysis end")
        
        for workflow_id, start_time_wf in workflow_starts.items():
            if workflow_id in active_workflows:
                workflow_periods.append((start_time_wf, current_time))
                print(f"  Workflow {workflow_id} still active at analysis end")
        
        # Combine all activity periods
        all_activity_periods = experiment_periods + workflow_periods
        
        # Merge overlapping periods
        if all_activity_periods:
            merged_periods = self._merge_time_periods(all_activity_periods)
            total_active_time = sum((end - start).total_seconds() for start, end in merged_periods)
        else:
            merged_periods = []
            total_active_time = 0
        
        # Calculate totals
        total_timeframe = (end_time - start_time).total_seconds()
        total_idle_time = total_timeframe - total_active_time
        
        print(f"Activity periods: {len(merged_periods)}")
        for i, (period_start, period_end) in enumerate(merged_periods):
            duration = (period_end - period_start).total_seconds()
            print(f"  Period {i+1}: {period_start} to {period_end} ({duration:.1f}s)")
        
        # Update system utilization
        system_util.total_time = total_timeframe
        system_util.active_time = total_active_time
        system_util.idle_time = total_idle_time
        system_util.current_state = "active" if active_experiments or active_workflows else "idle"
        system_util.last_state_change = current_time
        system_util.active_experiments = active_experiments
        system_util.active_workflows = active_workflows
        
        if total_timeframe > 0:
            system_util.utilization_percentage = (total_active_time / total_timeframe) * 100
        
        print(f"System utilization calculated:")
        print(f"  Total time: {total_timeframe:.1f}s")
        print(f"  Active time: {total_active_time:.1f}s")
        print(f"  Utilization: {system_util.utilization_percentage:.1f}%")
        
        return system_util
    
    def _calculate_real_node_utilization(
        self, 
        events: List[Dict], 
        start_time: datetime, 
        end_time: datetime
    ) -> Dict[str, NodeUtilizationData]:
        """Calculate real node utilization based on actual events."""
        
        # Group events by node
        node_events = defaultdict(list)
        
        for event in events:
            # Use the FIXED node extraction logic
            node_id = self._extract_node_id(event)
            if node_id:
                node_events[node_id].append(event)
            
            # ALSO extract nodes from workflow events like the working tracker
            if event.get("event_type") in ["workflow_start", "workflow_complete", "workflow_abort"]:
                workflow_nodes = self._extract_workflow_nodes(event)
                for workflow_node in workflow_nodes:
                    node_events[workflow_node].append(event)
        
        print(f"FIXED: Calculating utilization for {len(node_events)} nodes:")
        for node_id, events_for_node in node_events.items():
            print(f"  {node_id}: {len(events_for_node)} events")
        
        node_utils = {}
        
        for node_id, events_for_node in node_events.items():
            node_util = self._calculate_single_node_utilization(
                node_id, events_for_node, start_time, end_time
            )
            node_utils[node_id] = node_util
        
        return node_utils
    
    def _calculate_single_node_utilization(
        self, 
        node_id: str, 
        events: List[Dict], 
        start_time: datetime, 
        end_time: datetime
    ) -> NodeUtilizationData:
        """Calculate utilization for a single node based on actual activity."""
        
        node_util = NodeUtilizationData(node_id=node_id)
        
        # Track action lifecycles using WORKING TRACKER LOGIC
        active_actions = set()
        busy_periods = []
        active_periods = []
        
        print(f"FIXED: Analyzing node {node_id} with {len(events)} events...")
        
        # Sort events by time
        sorted_events = sorted(events, key=lambda e: self._parse_timestamp_utc(e.get("event_timestamp")) or datetime.min)
        
        current_busy_start = None
        current_active_start = None
        
        for event in sorted_events:
            event_time = self._parse_timestamp_utc(event.get("event_timestamp"))
            if not event_time:
                continue
            
            event_type = event.get("event_type", "").lower()
            
            # Handle NODE lifecycle events (active/inactive) like working tracker
            if event_type == "node_start":
                if current_active_start is None:
                    current_active_start = event_time
                    print(f"    {event_time}: Node {node_id} became ACTIVE")
            
            elif event_type == "node_stop":
                if current_active_start is not None:
                    active_periods.append((current_active_start, event_time))
                    duration = (event_time - current_active_start).total_seconds()
                    print(f"    {event_time}: Node {node_id} became INACTIVE (was active {duration:.1f}s)")
                    current_active_start = None
                # If node stops, any running actions also stop
                if current_busy_start is not None:
                    busy_periods.append((current_busy_start, event_time))
                    current_busy_start = None
                active_actions.clear()
            
            # Handle ACTION status changes - MOST IMPORTANT for busy time
            elif event_type == "action_status_change":
                action_id = self._extract_action_id(event)
                status = self._extract_status(event)
                
                if action_id:
                    print(f"    {event_time}: Action {action_id} -> {status}")
                    
                    # Action started - using WORKING TRACKER STATUS VALUES
                    if status in ["running", "started", "in_progress"]:
                        if action_id not in active_actions:
                            active_actions.add(action_id)
                            # First action on this node - start busy period
                            if current_busy_start is None:
                                current_busy_start = event_time
                                print(f"      Node {node_id} became BUSY")
                    
                    # Action completed - using WORKING TRACKER STATUS VALUES
                    elif status in ["completed", "failed", "cancelled", "finished", "succeeded"]:
                        if action_id in active_actions:
                            active_actions.remove(action_id)
                            # No more actions - end busy period
                            if not active_actions and current_busy_start is not None:
                                busy_periods.append((current_busy_start, event_time))
                                duration = (event_time - current_busy_start).total_seconds()
                                print(f"      Node {node_id} became AVAILABLE (was busy {duration:.1f}s)")
                                current_busy_start = None
            
            # Handle workflow events to mark node as active
            elif event_type in ["workflow_start", "workflow_complete", "workflow_abort"]:
                # Workflow involving this node - assume node is active
                if current_active_start is None:
                    current_active_start = event_time
                    print(f"    {event_time}: Node {node_id} involved in workflow (marked active)")
        
        # Handle ongoing states at end of analysis
        current_time = end_time
        
        if current_active_start is not None:
            active_periods.append((current_active_start, current_time))
            print(f"  Node {node_id} still active at analysis end")
        
        if current_busy_start is not None:
            busy_periods.append((current_busy_start, current_time))
            print(f"  Node {node_id} still busy at analysis end")
        
        # Calculate times using WORKING TRACKER LOGIC
        total_timeframe = (end_time - start_time).total_seconds()
        
        # Calculate active time (when node was available for work)
        if active_periods:
            merged_active = self._merge_time_periods(active_periods)
            total_active_time = sum((end - start).total_seconds() for start, end in merged_active)
        else:
            # If no explicit active periods, assume node was active during timeframe
            total_active_time = total_timeframe
        
        # Calculate busy time (when node was executing actions)
        if busy_periods:
            merged_busy = self._merge_time_periods(busy_periods)
            total_busy_time = sum((end - start).total_seconds() for start, end in merged_busy)
        else:
            total_busy_time = 0
        
        # Update node utilization using WORKING TRACKER CALCULATION
        node_util.total_time = total_timeframe
        node_util.active_time = total_active_time
        node_util.busy_time = total_busy_time
        node_util.idle_time = max(0, total_active_time - total_busy_time)
        node_util.inactive_time = max(0, total_timeframe - total_active_time)
        
        node_util.current_state = "busy" if active_actions else "idle"
        node_util.active_state = "active" if current_active_start else "inactive"
        node_util.last_state_change = current_time
        node_util.active_actions = active_actions
        
        # Calculate utilization like working tracker: busy_time / active_time
        if total_active_time > 0:
            node_util.utilization_percentage = (total_busy_time / total_active_time) * 100
        else:
            node_util.utilization_percentage = 0.0
        
        print(f"  FIXED Node {node_id} utilization: {node_util.utilization_percentage:.1f}% " +
            f"(active: {total_active_time/3600:.2f}h, busy: {total_busy_time/3600:.2f}h)")
        
        return node_util

    
    def _merge_time_periods(self, periods: List[Tuple[datetime, datetime]]) -> List[Tuple[datetime, datetime]]:
        """Merge overlapping time periods."""
        
        if not periods:
            return []
        
        # Sort by start time
        sorted_periods = sorted(periods, key=lambda x: x[0])
        merged = [sorted_periods[0]]
        
        for current_start, current_end in sorted_periods[1:]:
            last_start, last_end = merged[-1]
            
            # If current period overlaps with last, merge them
            if current_start <= last_end:
                merged[-1] = (last_start, max(last_end, current_end))
            else:
                merged.append((current_start, current_end))
        
        return merged
    
    def _extract_experiment_id(self, event: Dict) -> Optional[str]:
        """Extract experiment ID from event."""
        
        # Check source
        source = event.get("source", {})
        if isinstance(source, dict) and source.get("experiment_id"):
            return str(source["experiment_id"])
        
        # Check event data
        event_data = event.get("event_data", {})
        if isinstance(event_data, dict):
            if event_data.get("experiment_id"):
                return str(event_data["experiment_id"])
            
            # Check nested experiment object
            if isinstance(event_data.get("experiment"), dict):
                exp = event_data["experiment"]
                return str(exp.get("experiment_id") or exp.get("_id", ""))
        
        return None
    
    def _extract_workflow_id(self, event: Dict) -> Optional[str]:
        """Extract workflow ID from event."""
        
        source = event.get("source", {})
        if isinstance(source, dict) and source.get("workflow_id"):
            return str(source["workflow_id"])
        
        event_data = event.get("event_data", {})
        if isinstance(event_data, dict):
            if event_data.get("workflow_id"):
                return str(event_data["workflow_id"])
            
            if isinstance(event_data.get("workflow"), dict):
                workflow = event_data["workflow"]
                return str(workflow.get("workflow_id") or workflow.get("_id", ""))
        
        return None
    
    def _extract_node_id(self, event: Dict) -> Optional[str]:
        """Extract node ID from event."""
        
        # Check source first
        source = event.get("source", {})
        if isinstance(source, dict):
            # Check node_id first
            if source.get("node_id"):
                return str(source["node_id"])
            # Check workcell_id as fallback (this was in working tracker)
            if source.get("workcell_id"):
                return str(source["workcell_id"])
        
        # Check event_data only as fallback (and only if it's a dict)
        event_data = event.get("event_data", {})
        if isinstance(event_data, dict):
            node_id = (
                event_data.get("node_id") or 
                event_data.get("node_name") or
                event_data.get("node")  # Add this - your test uses "node": "liquidhandler_1"
            )
            if node_id:
                return str(node_id)
        
        return None
    
    def _extract_workflow_nodes(self, event: Dict) -> Set[str]:
        """
        Extract workflow nodes using the WORKING logic from UtilizationTracker.
        """
        nodes = set()
        
        event_data = event.get("event_data", {})
        if not isinstance(event_data, dict):
            return nodes
        
        # Look for workflow data structure
        workflow_data = event_data.get("workflow", {})
        if isinstance(workflow_data, dict):
            steps = workflow_data.get("steps", [])
            
            for step in steps:
                if isinstance(step, dict) and "node" in step:
                    nodes.add(str(step["node"]))
        
        # Also check if event_data itself contains steps (alternative structure)
        steps = event_data.get("steps", [])
        if isinstance(steps, list):
            for step in steps:
                if isinstance(step, dict) and "node" in step:
                    nodes.add(str(step["node"]))
        
        return nodes
    
    def _extract_action_id(self, event: Dict) -> Optional[str]:
        """Extract action ID from event."""
        
        event_data = event.get("event_data", {})
        if isinstance(event_data, dict):
            # Try multiple field names like working tracker
            for field in ["action_id", "action", "task_id", "_id", "id"]:
                value = event_data.get(field)
                if value:
                    return str(value)
        
        return None
    
    def _extract_status(self, event: Dict) -> str:
        """Extract status from event."""
        
        event_data = event.get("event_data", {})
        if isinstance(event_data, dict):
            # Safe access like working tracker
            status = event_data.get("status", "unknown")
            return str(status)
        
        return "unknown"
    
    def _create_minimal_summary(self, start_time: datetime, end_time: datetime) -> UtilizationSummary:
        """Create minimal summary when no events found."""
        
        return UtilizationSummary(
            system_utilization=SystemUtilizationData(),
            node_utilizations={},
            reporting_interval=0,
            tracker_uptime=(end_time - start_time).total_seconds(),
            summary_timestamp=datetime.now(timezone.utc)
        )


class UtilizationVisualizer:
    """
    Complete utilization visualizer with proper dynamic data display.
    """
    
    def __init__(self, events_collection: Collection):
        self.events_collection = events_collection
        self.analyzer = UtilizationAnalyzer(events_collection)
    
    def generate_system_utilization_graph(
        self, 
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        hours_back: Optional[int] = None
    ) -> str:
        """Generate system utilization graph with real data."""
        
        if hours_back and not start_time and not end_time:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=hours_back)
        
        summary = self.analyzer.analyze_utilization(start_time, end_time)
        
        plt.style.use('default')
        fig, ax = plt.subplots(figsize=(12, 8))
        
        system_util = summary.system_utilization
        
        if system_util.total_time > 0:
            # Create detailed visualization
            categories = ['Active Time', 'Idle Time']
            values = [system_util.active_time / 3600, system_util.idle_time / 3600]
            colors = ['#2E8B57', '#D3D3D3']  # Sea green and light gray
            
            bars = ax.bar(categories, values, color=colors, alpha=0.8, edgecolor='black', linewidth=1)
            
            # Add percentage labels
            total_hours = system_util.total_time / 3600
            for i, (bar, value) in enumerate(zip(bars, values)):
                percentage = (value / total_hours) * 100 if total_hours > 0 else 0
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                       f'{percentage:.1f}%\n({value:.1f}h)', ha='center', va='bottom', 
                       fontweight='bold', fontsize=11)
            
            ax.set_ylabel('Time (hours)', fontsize=12)
            ax.set_title(f'System Utilization Analysis\nOverall: {system_util.utilization_percentage:.1f}%', 
                        fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3, axis='y')
            
            # Enhanced summary text
            summary_text = f"""Analysis Period: {total_hours:.1f} hours
Active Experiments: {len(system_util.active_experiments)}
Active Workflows: {len(system_util.active_workflows)}
Nodes Tracked: {len(summary.node_utilizations)}
Timezone: UTC"""
            
            ax.text(0.02, 0.98, summary_text.strip(), transform=ax.transAxes,
                   verticalalignment='top', fontsize=10,
                   bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))
            
            # Add node utilization summary if available
            if summary.node_utilizations:
                node_text = "Node Utilizations:\n"
                for node_id, node_util in list(summary.node_utilizations.items())[:3]:
                    short_id = node_id[-8:] if len(node_id) > 8 else node_id
                    node_text += f"{short_id}: {node_util.utilization_percentage:.1f}%\n"
                
                ax.text(0.98, 0.98, node_text.strip(), transform=ax.transAxes,
                       verticalalignment='top', horizontalalignment='right', fontsize=9,
                       bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.7))
        
        else:
            ax.text(0.5, 0.5, 'No utilization data available\nCheck if workflows are generating events', 
                    ha='center', va='center', transform=ax.transAxes, fontsize=12,
                    bbox=dict(boxstyle='round', facecolor='lightcoral', alpha=0.7))
            ax.set_title('System Utilization Analysis - No Data')
        
        plt.tight_layout()
        return self._plot_to_base64(fig)
    
    def generate_node_utilization_graph(
        self, 
        node_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        hours_back: Optional[int] = None
    ) -> str:
        """Generate node utilization graph with real data."""
        
        if hours_back and not start_time and not end_time:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=hours_back)
        
        summary = self.analyzer.analyze_utilization(start_time, end_time)
        
        plt.style.use('default')
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        if node_id in summary.node_utilizations:
            node_util = summary.node_utilizations[node_id]
            
            # Pie chart of time distribution
            if node_util.busy_time > 0:
                sizes = [node_util.busy_time, node_util.idle_time]
                labels = ['Busy Time', 'Idle Time']
                colors = ['#FF6B6B', '#4ECDC4']
                explode = (0.05, 0)
                
                ax1.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%',
                       shadow=True, startangle=90, textprops={'fontsize': 10})
                ax1.set_title(f'Node {node_id[-8:]}\nTime Distribution', fontsize=12, fontweight='bold')
            else:
                ax1.text(0.5, 0.5, 'No Activity\nDetected', ha='center', va='center', 
                        transform=ax1.transAxes, fontsize=14,
                        bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.7))
                ax1.set_title(f'Node {node_id[-8:]}\nNo Activity', fontsize=12)
            
            # Bar chart summary
            categories = ['Total Time', 'Active Time', 'Busy Time', 'Idle Time']
            values = [
                node_util.total_time / 3600,
                node_util.active_time / 3600,
                node_util.busy_time / 3600,
                node_util.idle_time / 3600
            ]
            colors = ['#95A5A6', '#3498DB', '#E74C3C', '#2ECC71']
            
            bars = ax2.bar(categories, values, color=colors, alpha=0.8, edgecolor='black', linewidth=0.5)
            
            # Add value labels on bars
            for bar, value in zip(bars, values):
                if value > 0:
                    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                           f'{value:.2f}h', ha='center', va='bottom', fontsize=9)
            
            ax2.set_ylabel('Time (hours)', fontsize=11)
            ax2.set_title(f'Node Time Analysis\nUtilization: {node_util.utilization_percentage:.1f}%', 
                         fontsize=12, fontweight='bold')
            ax2.grid(True, alpha=0.3, axis='y')
            
            # Rotate x-axis labels for readability
            plt.setp(ax2.get_xticklabels(), rotation=45, ha='right')
            
        else:
            # Node not found
            for ax in [ax1, ax2]:
                ax.text(0.5, 0.5, f'Node {node_id[-8:]} not found\nin utilization tracking', 
                        ha='center', va='center', transform=ax.transAxes, fontsize=12,
                        bbox=dict(boxstyle='round', facecolor='lightcoral', alpha=0.7))
                ax.set_title(f'Node {node_id[-8:]} - Not Tracked')
        
        plt.tight_layout()
        return self._plot_to_base64(fig)
    
    def _plot_to_base64(self, fig) -> str:
        """Convert matplotlib figure to base64 string."""
        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', dpi=150, bbox_inches='tight', facecolor='white')
        buffer.seek(0)
        plt.close(fig)
        
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        buffer.close()
        
        return image_base64
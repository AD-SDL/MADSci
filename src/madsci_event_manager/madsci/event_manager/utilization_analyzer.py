"""
 utilization analyzer that properly detects sessions and calculates utilization.
"""

import time
from datetime import datetime, timedelta, timezone
import base64
import matplotlib.pyplot as plt
import io
from pymongo.synchronous.collection import Collection
from typing import Dict, Set, Optional, Any, List, Tuple, Union
from madsci.common.types.event_types import (
    EventType,
    NodeUtilizationData,
    SystemUtilizationData,
)
from collections import defaultdict

class UtilizationAnalyzer:
    """
     utilization analyzer with proper session detection.
    """
    
    def __init__(self, events_collection):
        """Initialize with the existing events collection."""
        self.events_collection = events_collection
        
        # Try to get a count to verify it's working
        try:
            count = events_collection.count_documents({})
            print(f"Total events in DB: {count}")
        except Exception as e:
            print(f"Error counting events: {e}")
        
        # Cache for names to avoid repeated lookups
        self.name_cache = {
            "nodes": {},
            "experiments": {},
            "workcells": {}
        }
    
    def generate_session_report(
        self, 
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive session-based utilization report.
        """
        try:
            print("Generating session-based utilization report...")
            
            # Determine analysis timeframe
            analysis_start, analysis_end = self._determine_analysis_period(start_time, end_time)
            print(f"Analysis period: {analysis_start} to {analysis_end}")
            
            # Find all system sessions in the timeframe
            sessions = self._find_system_sessions(analysis_start, analysis_end)
            print(f"Found {len(sessions)} system sessions")
            
            # If no formal sessions found, create a default analysis session
            if not sessions:
                print("No formal sessions found, creating default analysis session")
                sessions = [{
                    "session_type": "default_analysis",
                    "session_id": f"analysis_{int(analysis_start.timestamp())}",
                    "start_time": analysis_start,
                    "end_time": analysis_end,
                    "duration_seconds": (analysis_end - analysis_start).total_seconds(),
                    "source": "default_analysis"
                }]
            
            # Analyze utilization for each session
            session_reports = []
            for session in sessions:
                session_report = self._analyze_session_utilization(session)
                session_reports.append(session_report)
            
            # Generate overall summary
            overall_summary = self._generate_overall_summary(session_reports, analysis_start, analysis_end)
            
            # Compile final report
            report = {
                "report_metadata": {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "analysis_start": analysis_start.isoformat(),
                    "analysis_end": analysis_end.isoformat(),
                    "total_sessions": len(sessions),
                    "analysis_duration_hours": (analysis_end - analysis_start).total_seconds() / 3600
                },
                "overall_summary": overall_summary,
                "session_details": session_reports
            }
            
            print(f"Report generated with {len(session_reports)} session analyses")
            return report
            
        except Exception as e:
            print(f"Error generating session report: {e}")
            import traceback
            traceback.print_exc()
            return {"error": f"Failed to generate report: {str(e)}"}
    
    def _determine_analysis_period(
        self, 
        start_time: Optional[datetime], 
        end_time: Optional[datetime]
    ) -> Tuple[datetime, datetime]:
        """Determine the analysis period."""
        
        if start_time and end_time:
            return self._ensure_utc(start_time), self._ensure_utc(end_time)
        
        # If no timeframe provided, analyze ALL records in database
        if not start_time and not end_time:
            print("No timeframe provided - analyzing ALL database records...")
            try:
                earliest_cursor = self.events_collection.find().sort("event_timestamp", 1).limit(1)
                earliest_events = list(earliest_cursor)
                
                latest_cursor = self.events_collection.find().sort("event_timestamp", -1).limit(1)
                latest_events = list(latest_cursor)
                
                if earliest_events and latest_events:
                    earliest_time = self._parse_timestamp_utc(earliest_events[0]["event_timestamp"])
                    latest_time = self._parse_timestamp_utc(latest_events[0]["event_timestamp"])
                    
                    if earliest_time and latest_time:
                        buffered_start = earliest_time - timedelta(minutes=1)
                        buffered_end = latest_time + timedelta(minutes=1)
                        
                        total_span = (buffered_end - buffered_start).total_seconds() / 3600
                        print(f"Full database analysis: {buffered_start} to {buffered_end} ({total_span:.1f} hours)")
                        return buffered_start, buffered_end
                        
            except Exception as e:
                print(f"Error finding full database range: {e}")
        
        # Fallback
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        return now - timedelta(days=1), now
    

    def _find_system_sessions(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """
        Find all ACTUAL system sessions - FIXED for timezone and string parsing issues.
        """
        
        sessions = []
        
        print("Looking for actual system/workcell lifecycle events...")
        print(f"DEBUG: Analysis timeframe: {start_time} to {end_time}")
        
        # The events are stored as ISO strings, so we need to handle both formats
        start_event_types = [
            EventType.LAB_START.value,
            EventType.WORKCELL_START.value,
            "lab_start",
            "workcell_start"
        ]
        
        print(f"DEBUG: Looking for event types: {start_event_types}")
        
        # CRITICAL FIX: Handle both datetime and string timestamp formats
        # Create queries for both possible timestamp formats
        queries_to_try = [
            # Query 1: Direct datetime comparison (if timestamps are datetime objects)
            {
                "event_type": {"$in": start_event_types},
                "event_timestamp": {"$gte": start_time, "$lte": end_time}
            },
            # Query 2: ISO string comparison (if timestamps are stored as strings)
            {
                "event_type": {"$in": start_event_types},
                "event_timestamp": {"$gte": start_time.isoformat(), "$lte": end_time.isoformat()}
            },
            # Query 3: Just find all events of these types (no time constraint)
            {
                "event_type": {"$in": start_event_types}
            }
        ]
        
        start_events = []
        
        for i, query in enumerate(queries_to_try):
            try:
                print(f"DEBUG: Trying query {i+1}: {query}")
                
                events = list(self.events_collection.find(query).sort("event_timestamp", 1))
                print(f"DEBUG: Query {i+1} found {len(events)} events")
                
                if events:
                    # Filter by timeframe manually if needed (for query 3)
                    if i == 2:  # No time constraint query
                        print(f"DEBUG: Manually filtering {len(events)} events by timeframe...")
                        filtered_events = []
                        for event in events:
                            event_time = self._parse_timestamp_utc(event["event_timestamp"])
                            if event_time and start_time <= event_time <= end_time:
                                filtered_events.append(event)
                                print(f"DEBUG:   Event at {event_time} is within range")
                            else:
                                print(f"DEBUG:   Event at {event_time} is outside range")
                        start_events = filtered_events
                    else:
                        start_events = events
                    
                    print(f"DEBUG: Using query {i+1}, found {len(start_events)} events in timeframe")
                    break
                    
            except Exception as e:
                print(f"DEBUG: Query {i+1} failed: {e}")
                continue
        
        print(f"DEBUG: Final result: {len(start_events)} start events found")
        
        # Process each start event
        for start_event in start_events:
            start_timestamp = self._parse_timestamp_utc(start_event["event_timestamp"])
            if not start_timestamp:
                print(f"DEBUG: Could not parse timestamp: {start_event['event_timestamp']}")
                continue
                
            # Extract session info
            event_data = start_event.get("event_data", {})
            source = start_event.get("source", {})
            
            session_id = (
                source.get("workcell_id") or 
                source.get("manager_id") or 
                event_data.get("workcell_id") or
                f"system_{int(start_timestamp.timestamp())}"
            )
            
            session_name = (
                event_data.get("workcell_name") or
                event_data.get("name") or
                f"Workcell {session_id[-8:] if session_id else 'Unknown'}"
            )
            
            print(f"DEBUG: Creating session:")
            print(f"DEBUG:   Event type: {start_event.get('event_type')}")
            print(f"DEBUG:   Session ID: {session_id}")
            print(f"DEBUG:   Session name: {session_name}")
            print(f"DEBUG:   Start time: {start_timestamp}")
            
            # For now, assume session runs until end of analysis period
            # (You can add stop event detection later)
            stop_timestamp = end_time
            
            # Determine session type
            event_type = str(start_event["event_type"]).lower()
            if "lab" in event_type:
                session_type = "lab"
            elif "workcell" in event_type:
                session_type = "workcell"
            else:
                session_type = "system"
                    
            session = {
                "session_type": session_type,
                "session_id": session_id,
                "session_name": session_name,
                "start_time": start_timestamp,
                "end_time": stop_timestamp,
                "duration_seconds": (stop_timestamp - start_timestamp).total_seconds(),
                "source": "system_lifecycle_events",
                "workcell_nodes": event_data.get("nodes", {})
            }
            
            sessions.append(session)
            
            duration_hours = session["duration_seconds"] / 3600
            print(f"DEBUG: Created {session_type} session '{session_name}': {duration_hours:.2f}h")
        
        print(f"DEBUG: Returning {len(sessions)} sessions")
        return sessions

    def _extract_system_session_id(self, event: Dict) -> Optional[str]:
        """Extract system/workcell session ID from lifecycle event."""
        source = event.get("source", {})
        if isinstance(source, dict):
            return source.get("manager_id") or source.get("workcell_id") or source.get("lab_id")
        
        event_data = event.get("event_data", {})
        if isinstance(event_data, dict):
            return event_data.get("manager_id") or event_data.get("workcell_id") or event_data.get("lab_id")
        
        return None
    
    def _extract_experiment_id(self, event: Dict) -> Optional[str]:
        """Extract experiment ID from event - FIXED for nested experiment structure."""
        
        source = event.get("source", {})
        if isinstance(source, dict) and source.get("experiment_id"):
            return str(source["experiment_id"])
        
        event_data = event.get("event_data", {})
        if isinstance(event_data, dict):
            # Direct experiment_id
            if event_data.get("experiment_id"):
                return str(event_data["experiment_id"])
            
            # Nested experiment object (this is what your data has)
            if isinstance(event_data.get("experiment"), dict):
                exp = event_data["experiment"]
                exp_id = exp.get("experiment_id") or exp.get("_id")
                if exp_id:
                    return str(exp_id)
        
        return None
    
    def _analyze_session_utilization(self, session: Dict) -> Dict[str, Any]:
        """Analyze utilization for a single session."""
        try:
            session_start = session["start_time"]
            session_end = session["end_time"] or datetime.now(timezone.utc).replace(tzinfo=None)
            
            print(f"Analyzing {session['session_type']} session {session['session_id'][-8:]}...")
            
            # ... [existing event processing logic] ...
            session_events = self._get_session_events(session_start, session_end)
            relevant_events = self._filter_activity_events(session_events)
            system_util = self._calculate_system_utilization(relevant_events, session_start, session_end)
            node_utils = self._calculate_node_utilization(relevant_events, session_start, session_end)
            
            # Resolve names
            session_name = self._resolve_session_name(session)
            
            # Improved experiment details with better names
            experiment_details = []
            for exp_id in system_util.active_experiments:
                exp_name = self._resolve_experiment_name(exp_id)
                display_name = exp_name if exp_name else f"Experiment {exp_id[-8:]}"
                experiment_details.append({
                    "experiment_id": exp_id,
                    "experiment_name": exp_name,
                    "display_name": display_name
                })
            
            # Improved node utilizations with readable times
            node_utilizations_with_names = {}
            for node_id, node_util in node_utils.items():
                node_name = self._resolve_node_name(node_id)
                display_name = f"{node_name} ({node_id[-8:]})" if node_name else f"Node {node_id[-8:]}"
                
                busy_time_seconds = node_util.busy_time
                idle_time_seconds = node_util.idle_time
                total_time_seconds = node_util.total_time
                
                node_utilizations_with_names[node_id] = {
                    "node_id": node_id,
                    "node_name": node_name,
                    "display_name": display_name,
                    "utilization_percent": round(node_util.utilization_percentage, 1),
                    "state": node_util.current_state,
                    
                    # Readable timing
                    "timing": {
                        "busy_time": self._format_duration_readable(busy_time_seconds),
                        "idle_time": self._format_duration_readable(idle_time_seconds),
                        "total_time": self._format_duration_readable(total_time_seconds)
                    },
                    
                    # Keep raw data for analysis
                    "raw_hours": {
                        "busy": node_util.busy_time / 3600,
                        "idle": node_util.idle_time / 3600,
                        "total": node_util.total_time / 3600
                    },
                    
                    # Legacy fields for compatibility
                    "busy_time_hours": node_util.busy_time / 3600,
                    "idle_time_hours": node_util.idle_time / 3600
                }
            
            # Calculate readable session times
            duration_seconds = session["duration_seconds"]
            active_time_seconds = system_util.active_time
            
            # Compile improved session report
            return {
                "session_type": session["session_type"],
                "session_id": session["session_id"],
                "session_name": session_name,
                "start_time": session_start.isoformat(),
                "end_time": session_end.isoformat() if session["end_time"] else None,
                
                # Readable timing
                "timing": {
                    "duration": self._format_duration_readable(duration_seconds),
                    "active_time": self._format_duration_readable(active_time_seconds),
                    "idle_time": self._format_duration_readable(duration_seconds - active_time_seconds)
                },
                
                # Rounded percentages
                "system_utilization_percent": round(system_util.utilization_percentage, 1),
                
                # Experiment and node details
                "total_experiments": len(system_util.active_experiments),
                "experiment_details": experiment_details,
                "nodes_active": len(node_utils),
                "node_utilizations": node_utilizations_with_names,
                
                # Keep raw data for compatibility and analysis
                "raw_hours": {
                    "duration": duration_seconds / 3600,
                    "active": active_time_seconds / 3600,
                    "idle": (duration_seconds - active_time_seconds) / 3600
                },
                
                # Legacy fields for compatibility
                "duration_hours": duration_seconds / 3600,
                "active_time_hours": active_time_seconds / 3600
            }
        except Exception as e:
            print(f"Error analyzing session utilization: {e}")
            import traceback
            traceback.print_exc()
            return {
                "error": str(e),
                "session_type": session["session_type"],
                "session_id": session["session_id"],
                "start_time": session["start_time"].isoformat(),
                "duration_hours": session["duration_seconds"] / 3600
            }
        
    def _format_duration_readable(self, seconds: float) -> dict:
        """Convert seconds to readable format."""
        hours = seconds / 3600
        minutes = seconds / 60
        
        if seconds < 60:
            primary_display = f"{seconds:.1f}s"
            primary_unit = "seconds"
            primary_value = seconds
        elif seconds < 3600:
            primary_display = f"{minutes:.1f}m"
            primary_unit = "minutes" 
            primary_value = minutes
        else:
            primary_display = f"{hours:.1f}h"
            primary_unit = "hours"
            primary_value = hours
        
        return {
            "display": primary_display,
            "seconds": seconds,
            "minutes": minutes,
            "hours": hours,
            "primary_unit": primary_unit,
            "primary_value": primary_value
        }
    
    def _get_session_events(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Get all events for a session timeframe - FIXED for timezone issues."""
        try:
            print(f"Querying events from {start_time} to {end_time}")
            
            # SAME FIX: Try multiple query approaches for timestamp formats
            queries_to_try = [
                # Query 1: Direct datetime comparison
                {"event_timestamp": {"$gte": start_time, "$lte": end_time}},
                # Query 2: ISO string comparison
                {"event_timestamp": {"$gte": start_time.isoformat(), "$lte": end_time.isoformat()}},
                # Query 3: Get all events and filter manually
                {}
            ]
            
            events = []
            
            for i, query in enumerate(queries_to_try):
                try:
                    print(f"DEBUG: Trying session events query {i+1}")
                    
                    if i == 2:  # Get all and filter manually
                        print(f"DEBUG: Getting all events and filtering manually...")
                        all_events = list(self.events_collection.find().sort("event_timestamp", 1))
                        print(f"DEBUG: Retrieved {len(all_events)} total events from database")
                        
                        # Filter manually by parsing timestamps
                        for event in all_events:
                            event_time = self._parse_timestamp_utc(event.get("event_timestamp"))
                            if event_time and start_time <= event_time <= end_time:
                                events.append(event)
                        
                        print(f"DEBUG: After manual filtering: {len(events)} events in timeframe")
                    else:
                        # Direct query
                        events = list(self.events_collection.find(query).sort("event_timestamp", 1))
                        print(f"DEBUG: Query {i+1} found {len(events)} events")
                    
                    if events:
                        print(f"DEBUG: Using query approach {i+1}")
                        break
                        
                except Exception as e:
                    print(f"DEBUG: Query {i+1} failed: {e}")
                    continue
            
            print(f"Found {len(events)} events in timeframe")
            
            # Parse all timestamps to UTC (this part was working before)
            valid_events = []
            for event in events:
                if "event_timestamp" in event:
                    parsed_ts = self._parse_timestamp_utc(event["event_timestamp"])
                    if parsed_ts:
                        event["event_timestamp"] = parsed_ts
                        valid_events.append(event)
                    else:
                        print(f"DEBUG: Could not parse timestamp for event: {event.get('event_timestamp')}")
            
            print(f"Found {len(valid_events)} valid events with parsed timestamps")
            
            # Show event summary
            if valid_events:
                self._show_event_summary(valid_events)
            
            return valid_events
            
        except Exception as e:
            print(f"Error getting session events: {e}")
            import traceback
            traceback.print_exc()
            return []
        
    def _show_event_summary(self, events: List[Dict]):
        """Show summary of events found."""
        
        event_type_counts = defaultdict(int)
        activity_events = 0
        
        for event in events:
            event_type = event.get("event_type", "unknown")
            event_type_counts[str(event_type)] += 1
            
            # Count activity events
            event_type_str = str(event_type).lower()
            if any(activity_type in event_type_str for activity_type in [
                "experiment", "workflow", "action", "node", "workcell", "lab"
            ]) and "log" not in event_type_str:
                activity_events += 1
        
        print("Event summary:")
        for event_type, count in sorted(event_type_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {event_type}: {count}")
        
        print(f"Activity events found: {activity_events}")
    
    def _filter_activity_events(self, events: List[Dict]) -> List[Dict]:
        """Filter events that indicate actual system activity."""
        
        relevant_events = []
        
        print(f"Filtering {len(events)} total events...")
        
        for event in events:
            event_type = str(event.get("event_type", "")).lower()
            
            # Skip ALL LOG events
            if any(log_type in event_type for log_type in 
                ["log", "log_debug", "log_info", "log_warning", "log_error", "log_critical"]):
                continue
            
            # Include activity events
            is_activity_event = any(activity_type in event_type for activity_type in [
                "experiment_start", "experiment_complete", "experiment_failed", "experiment_cancelled",
                "workcell_start", "workcell_stop", "lab_start", "lab_stop",
                "node_start", "node_stop", "node_status_update", 
                "action_status_change", "workflow_start", "workflow_complete"
            ])
            
            if is_activity_event:
                relevant_events.append(event)
        
        print(f"Filtered to {len(relevant_events)} activity events")
        
        # Show first few relevant events
        if relevant_events:
            print(f"First few activity events:")
            for i, event in enumerate(relevant_events[:5]):
                event_type = event.get("event_type", "unknown")
                timestamp = event.get("event_timestamp", "unknown")
                print(f"  {i+1}. {event_type} at {timestamp}")
        
        return relevant_events
    
    def _calculate_system_utilization(
        self, 
        events: List[Dict], 
        start_time: datetime, 
        end_time: datetime
    ) -> SystemUtilizationData:
        """Calculate system utilization based on actual events."""
        
        system_util = SystemUtilizationData()
        
        # Track experiments and calculate active periods
        active_experiments = set()
        experiment_periods = []
        experiment_starts = {}
        
        print(f"Calculating system utilization from {len(events)} activity events...")
        
        # Process events chronologically
        sorted_events = sorted(events, key=lambda e: self._parse_timestamp_utc(e.get("event_timestamp")) or datetime.min)
        
        for event in sorted_events:
            event_time = self._parse_timestamp_utc(event.get("event_timestamp"))
            if not event_time:
                continue
                
            event_type = str(event.get("event_type", "")).lower()
            
            # Track experiment events
            if "experiment_start" in event_type:
                exp_id = self._extract_experiment_id(event)
                if exp_id:
                    active_experiments.add(exp_id)
                    experiment_starts[exp_id] = event_time
                    print(f"  Experiment started: {exp_id[-8:]} at {event_time}")
            
            elif any(end_pattern in event_type for end_pattern in ["experiment_complete", "experiment_failed", "experiment_cancelled"]):
                exp_id = self._extract_experiment_id(event)
                if exp_id and exp_id in experiment_starts:
                    start_time_exp = experiment_starts[exp_id]
                    experiment_periods.append((start_time_exp, event_time))
                    active_experiments.discard(exp_id)
                    duration = (event_time - start_time_exp).total_seconds()
                    print(f"  Experiment completed: {exp_id[-8:]}, duration: {duration:.1f}s")
        
        # Handle ongoing experiments
        current_time = end_time
        for exp_id, start_time_exp in experiment_starts.items():
            if exp_id in active_experiments:
                experiment_periods.append((start_time_exp, current_time))
                print(f"  Experiment {exp_id[-8:]} still active at analysis end")
        
        # Calculate active time
        if experiment_periods:
            merged_periods = self._merge_time_periods(experiment_periods)
            total_active_time = sum((end - start).total_seconds() for start, end in merged_periods)
        else:
            total_active_time = 0
        
        # Calculate totals
        total_timeframe = (end_time - start_time).total_seconds()
        total_idle_time = total_timeframe - total_active_time
        
        # Update system utilization
        system_util.total_time = total_timeframe
        system_util.active_time = total_active_time
        system_util.idle_time = total_idle_time
        system_util.current_state = "active" if active_experiments else "idle"
        system_util.last_state_change = current_time
        system_util.active_experiments = set(experiment_starts.keys())
        
        if total_timeframe > 0:
            system_util.utilization_percentage = (total_active_time / total_timeframe) * 100
        
        print(f"System utilization calculated:")
        print(f"  Total time: {total_timeframe/3600:.2f} hours")
        print(f"  Active time: {total_active_time/3600:.2f} hours")
        print(f"  Utilization: {system_util.utilization_percentage:.1f}%")
        
        return system_util
    
    def _calculate_node_utilization(
        self, 
        events: List[Dict], 
        start_time: datetime, 
        end_time: datetime
    ) -> Dict[str, NodeUtilizationData]:
        """Calculate node utilization based on actual events."""
        
        # Group events by node
        node_events = defaultdict(list)
        
        for event in events:
            node_id = self._extract_node_id(event)
            if node_id:
                node_events[node_id].append(event)
        
        print(f"Calculating utilization for {len(node_events)} nodes:")
        for node_id, events_for_node in node_events.items():
            print(f"  {node_id[-8:]}: {len(events_for_node)} events")
        
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
        """Calculate utilization for a single node."""
        
        node_util = NodeUtilizationData(node_id=node_id)
        
        # Track action lifecycles
        active_actions = set()
        busy_periods = []
        active_periods = []
        
        print(f"Analyzing node {node_id[-8:]} with {len(events)} events...")
        
        # Sort events by time
        sorted_events = sorted(events, key=lambda e: self._parse_timestamp_utc(e.get("event_timestamp")) or datetime.min)
        
        current_busy_start = None
        current_active_start = None
        
        for event in sorted_events:
            event_time = self._parse_timestamp_utc(event.get("event_timestamp"))
            if not event_time:
                continue
            
            event_type = str(event.get("event_type", "")).lower()
            
            # Handle NODE lifecycle events
            if event_type == "node_start":
                if current_active_start is None:
                    current_active_start = event_time
                    print(f"    {event_time}: Node became ACTIVE")
            
            elif event_type == "node_stop":
                if current_active_start is not None:
                    active_periods.append((current_active_start, event_time))
                    current_active_start = None
                if current_busy_start is not None:
                    busy_periods.append((current_busy_start, event_time))
                    current_busy_start = None
                active_actions.clear()
            
            # Handle ACTION status changes
            elif event_type == "action_status_change":
                action_id = self._extract_action_id(event)
                status = self._extract_status(event)
                
                if action_id:
                    print(f"    {event_time}: Action {action_id[-8:]} -> {status}")
                    
                    # Action started
                    if status in ["running", "started", "in_progress"]:
                        if action_id not in active_actions:
                            active_actions.add(action_id)
                            if current_busy_start is None:
                                current_busy_start = event_time
                                print(f"      Node became BUSY")
                    
                    # Action completed
                    elif status in ["completed", "failed", "cancelled", "finished", "succeeded"]:
                        if action_id in active_actions:
                            active_actions.remove(action_id)
                            if not active_actions and current_busy_start is not None:
                                busy_periods.append((current_busy_start, event_time))
                                duration = (event_time - current_busy_start).total_seconds()
                                print(f"      Node became IDLE (was busy {duration:.1f}s)")
                                current_busy_start = None
        
        # Handle ongoing states
        current_time = end_time
        
        if current_active_start is not None:
            active_periods.append((current_active_start, current_time))
        
        if current_busy_start is not None:
            busy_periods.append((current_busy_start, current_time))
        
        # Calculate times
        total_timeframe = (end_time - start_time).total_seconds()
        
        # Calculate active time
        if active_periods:
            merged_active = self._merge_time_periods(active_periods)
            total_active_time = sum((end - start).total_seconds() for start, end in merged_active)
        else:
            # If no explicit active periods but node had events, assume active
            total_active_time = total_timeframe if events else 0
        
        # Calculate busy time
        if busy_periods:
            merged_busy = self._merge_time_periods(busy_periods)
            total_busy_time = sum((end - start).total_seconds() for start, end in merged_busy)
        else:
            total_busy_time = 0
        
        # Update node utilization
        node_util.total_time = total_timeframe
        node_util.active_time = total_active_time
        node_util.busy_time = total_busy_time
        node_util.idle_time = max(0, total_active_time - total_busy_time)
        node_util.inactive_time = max(0, total_timeframe - total_active_time)
        
        node_util.current_state = "busy" if active_actions else "idle"
        node_util.active_state = "active" if current_active_start else "inactive"
        node_util.last_state_change = current_time
        node_util.active_actions = active_actions
        
        # Calculate utilization: busy_time / active_time
        if total_active_time > 0:
            node_util.utilization_percentage = (total_busy_time / total_active_time) * 100
        else:
            node_util.utilization_percentage = 0.0
        
        print(f"  Node {node_id[-8:]} utilization: {node_util.utilization_percentage:.1f}% " +
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
    
    def _extract_node_id(self, event: Dict) -> Optional[str]:
        """Extract node ID from event."""
        
        # Check source first
        source = event.get("source", {})
        if isinstance(source, dict):
            if source.get("node_id"):
                return str(source["node_id"])
            if source.get("workcell_id"):
                return str(source["workcell_id"])
        
        # Check event_data
        event_data = event.get("event_data", {})
        if isinstance(event_data, dict):
            node_id = (
                event_data.get("node_id") or 
                event_data.get("node_name") or
                event_data.get("node")
            )
            if node_id:
                return str(node_id)
        
        return None
    
    def _extract_action_id(self, event: Dict) -> Optional[str]:
        """Extract action ID from event."""
        
        event_data = event.get("event_data", {})
        if isinstance(event_data, dict):
            for field in ["action_id", "action", "task_id", "_id", "id"]:
                value = event_data.get(field)
                if value:
                    return str(value)
        
        return None
    
    def _extract_status(self, event: Dict) -> str:
        """Extract status from event."""
        
        event_data = event.get("event_data", {})
        if isinstance(event_data, dict):
            status = event_data.get("status", "unknown")
            return str(status)
        
        return "unknown"
    
    def _parse_timestamp_utc(self, timestamp) -> Optional[datetime]:
        """Parse timestamp to UTC (timezone-naive)."""
        if isinstance(timestamp, datetime):
            if timestamp.tzinfo is not None:
                return timestamp.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                return timestamp
        
        if isinstance(timestamp, str):
            try:
                # Handle ISO format strings (which is what your DB has)
                if 'T' in timestamp:
                    if timestamp.endswith('Z'):
                        return datetime.fromisoformat(timestamp.replace('Z', '+00:00')).astimezone(timezone.utc).replace(tzinfo=None)
                    elif '+' in timestamp or timestamp.count('-') > 2:
                        return datetime.fromisoformat(timestamp).astimezone(timezone.utc).replace(tzinfo=None)
                    else:
                        # This handles your case: "2025-07-23T05:25:00.384778"
                        dt = datetime.fromisoformat(timestamp)
                        # Assume it's already UTC if no timezone info
                        return dt
                else:
                    return datetime.fromisoformat(timestamp)
            except ValueError as e:
                print(f"DEBUG: Could not parse timestamp '{timestamp}': {e}")
                try:
                    return datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    print(f"DEBUG: Could not parse timestamp with fallback format: {timestamp}")
                    return None
        
        return None
    
    def _ensure_utc(self, dt: datetime) -> datetime:
        """Ensure datetime is UTC without timezone info."""
        if dt.tzinfo is not None:
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    
    def _resolve_session_name(self, session: Dict) -> str:
        """Resolve human-readable name for a session."""
        try:
            session_type = session["session_type"]
            session_id = session["session_id"]
            
            if session_type == "default_analysis":
                return "Complete Database Analysis"
            
            # Look for session name in start events
            if session_type in ["lab", "workcell"]:
                start_events = list(self.events_collection.find({
                    "event_timestamp": session["start_time"],
                    "event_type": {"$in": [f"{session_type}_start", getattr(EventType, f"{session_type.upper()}_START", None)]}
                }).limit(1))
                
                if start_events:
                    event = start_events[0]
                    event_data = event.get("event_data", {})
                    source = event.get("source", {})
                    
                    name_candidates = [
                        event_data.get("name"),
                        event_data.get(f"{session_type}_name"),
                        source.get("name"),
                    ]
                    
                    for name in name_candidates:
                        if name and isinstance(name, str) and name.strip():
                            return name.strip()
            
            return f"{session_type.title()} {session_id[-8:]}"
            
        except Exception as e:
            print(f"Error resolving session name: {e}")
            return f"{session.get('session_type', 'Unknown')} {session.get('session_id', '')[-8:]}"
    
    def _resolve_node_name(self, node_id: str) -> Optional[str]:
        """Resolve human-readable name for a node."""
        try:
            # Check cache first
            if node_id in self.name_cache["nodes"]:
                return self.name_cache["nodes"][node_id]
            
            # Look for NODE_START events for this node
            node_start_events = list(self.events_collection.find({
                "event_type": {"$in": ["node_start", EventType.NODE_START.value]},
                "$or": [
                    {"event_data.node_id": node_id},
                    {"source.node_id": node_id},
                    {"source.workcell_id": node_id}
                ]
            }).limit(5))
            
            for event in node_start_events:
                event_data = event.get("event_data", {})
                if event_data.get("node_name"):
                    name = event_data["node_name"].strip()
                    self.name_cache["nodes"][node_id] = name
                    return name
            
            # Cache null result
            self.name_cache["nodes"][node_id] = None
            return None
            
        except Exception as e:
            print(f"Error resolving node name for {node_id}: {e}")
            return None
    
    def _resolve_experiment_name(self, experiment_id: str) -> Optional[str]:
        """Resolve human-readable name for an experiment."""
        try:
            if experiment_id in self.name_cache["experiments"]:
                return self.name_cache["experiments"][experiment_id]
            
            exp_start_events = list(self.events_collection.find({
                "event_type": {"$in": ["experiment_start", EventType.EXPERIMENT_START.value]},
                "$or": [
                    {"source.experiment_id": experiment_id},
                    {"event_data.experiment_id": experiment_id},
                    {"event_data.experiment._id": experiment_id},
                    {"event_data.experiment.experiment_id": experiment_id}
                ]
            }).limit(5))
            
            for event in exp_start_events:
                event_data = event.get("event_data", {})
                
                # Check nested experiment.experiment_design.experiment_name
                name_candidates = [
                    event_data.get("experiment_name"),
                    event_data.get("name"),
                    event_data.get("experiment", {}).get("name") if isinstance(event_data.get("experiment"), dict) else None,
                    event_data.get("experiment", {}).get("experiment_design", {}).get("experiment_name") 
                    if isinstance(event_data.get("experiment", {}).get("experiment_design"), dict) else None,
                    event_data.get("experiment", {}).get("run_name") if isinstance(event_data.get("experiment"), dict) else None,
                ]
                
                for name in name_candidates:
                    if name and isinstance(name, str) and name.strip():
                        clean_name = name.strip()
                        self.name_cache["experiments"][experiment_id] = clean_name
                        return clean_name
            
            self.name_cache["experiments"][experiment_id] = None
            return None
            
        except Exception as e:
            print(f"Error resolving experiment name for {experiment_id}: {e}")
            return None

    
    def _generate_overall_summary(self, session_reports: List[Dict], start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Generate overall summary from session reports."""
        
        try:
            total_sessions = len(session_reports)
            total_runtime = sum(s["duration_hours"] for s in session_reports)
            total_active_time = sum(s["active_time_hours"] for s in session_reports)
            total_experiments = sum(s["total_experiments"] for s in session_reports)
            
            # Calculate average system utilization
            valid_sessions = [s for s in session_reports if "error" not in s]
            avg_utilization = sum(s["system_utilization_percent"] for s in valid_sessions) / len(valid_sessions) if valid_sessions else 0
            
            # Aggregate node data
            node_summary = defaultdict(lambda: {
                "total_busy_time_hours": 0,
                "utilizations": [],
                "sessions_active": 0
            })
            
            for session in valid_sessions:
                for node_id, node_data in session["node_utilizations"].items():
                    node_summary[node_id]["total_busy_time_hours"] += node_data["busy_time_hours"]
                    node_summary[node_id]["utilizations"].append(node_data["utilization_percent"])
                    node_summary[node_id]["sessions_active"] += 1
            
            # Calculate average utilizations per node
            final_node_summary = {}
            for node_id, data in node_summary.items():
                final_node_summary[node_id] = {
                    "average_utilization_percent": sum(data["utilizations"]) / len(data["utilizations"]) if data["utilizations"] else 0,
                    "total_busy_time_hours": data["total_busy_time_hours"],
                    "sessions_active": data["sessions_active"]
                }
            
            return {
                "total_sessions": total_sessions,
                "total_system_runtime_hours": total_runtime,
                "total_active_time_hours": total_active_time,
                "average_system_utilization_percent": avg_utilization,
                "total_experiments": total_experiments,
                "nodes_tracked": len(final_node_summary),
                "node_summary": final_node_summary
            }
            
        except Exception as e:
            print(f"Error generating overall summary: {e}")
            return {"error": str(e)}
"""Session-based utilization analyzer for MADSci system components."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Set, Optional, Any, List, Tuple, Union
from collections import defaultdict

from pymongo.synchronous.collection import Collection
from madsci.common.types.event_types import (
    EventType,
    NodeUtilizationData,
    SystemUtilizationData,
)

logger = logging.getLogger(__name__)


class UtilizationAnalyzer:
    """Analyzes system utilization based on session detection and event processing."""
    
    def __init__(self, events_collection: Collection):
        """Initialize with MongoDB events collection."""
        self.events_collection = events_collection
        
        # Verify database connection
        try:
            count = events_collection.count_documents({})
            logger.info(f"Connected to events collection with {count} total events")
        except Exception as e:
            logger.error(f"Error connecting to events collection: {e}")
            raise
        
        # Cache for name resolution to avoid repeated lookups
        self.name_cache = {
            "nodes": {},
            "experiments": {},
            "workcells": {}
        }
    
    def generate_session_based_report(
        self, 
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive session-based utilization report.
        
        Sessions are defined by workcell/lab start and stop events. Each session
        represents a period when laboratory equipment was actively configured
        and available for experiments.
        
        Args:
            start_time: Analysis start time (UTC, timezone-naive)
            end_time: Analysis end time (UTC, timezone-naive)
            
        Returns:
            Dict containing session details, overall summary, and metadata
        """
        try:
            # Determine analysis timeframe
            analysis_start, analysis_end = self._determine_analysis_period(start_time, end_time)
            
            # Find all system sessions in the timeframe
            sessions = self._find_system_sessions(analysis_start, analysis_end)
            
            # If no formal sessions found, create a default analysis session
            if not sessions:
                logger.info("No formal workcell sessions found, creating default analysis session")
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
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating session-based report: {e}")
            return {"error": f"Failed to generate report: {str(e)}"}
    
    def generate_user_utilization_report(
        self, 
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Generate user utilization report based on workflow authors.
        
        Args:
            start_time: Analysis start time (UTC, timezone-naive)
            end_time: Analysis end time (UTC, timezone-naive)
            
        Returns:
            Dict containing user statistics, system summary, and metadata
        """
        try:
            logger.info("Generating user utilization report")
            
            # Determine analysis timeframe
            analysis_start, analysis_end = self._determine_analysis_period(start_time, end_time)
            
            # Get all workflow events in timeframe
            workflow_events = self._get_workflow_events_for_users(analysis_start, analysis_end)
            
            # Process events to build user statistics
            user_stats = self._calculate_user_statistics(workflow_events)
            
            # Calculate system totals for percentage calculations
            system_totals = self._calculate_system_totals(workflow_events)
            
            # Generate final report
            return {
                "report_metadata": {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "analysis_start": analysis_start.isoformat(),
                    "analysis_end": analysis_end.isoformat(),
                    "total_workflows": system_totals["total_workflows"],
                    "total_users": len(user_stats),
                    "workflows_with_authors": system_totals["workflows_with_authors"],
                    "workflows_without_authors": system_totals["workflows_without_authors"]
                },
                
                "system_summary": {
                    "total_workflows": system_totals["total_workflows"],
                    "total_runtime_hours": system_totals["total_runtime_hours"],
                    "average_workflow_duration_hours": system_totals["average_duration_hours"],
                    "completion_rate_percent": system_totals["completion_rate_percent"],
                    "workflows_with_known_authors": system_totals["workflows_with_authors"],
                    "author_attribution_rate_percent": round(
                        (system_totals["workflows_with_authors"] / system_totals["total_workflows"] * 100) 
                        if system_totals["total_workflows"] > 0 else 0, 2
                    )
                },
                
                "user_utilization": user_stats
            }
            
        except Exception as e:
            logger.error(f"Error generating user utilization report: {e}")
            return {"error": f"Failed to generate user report: {str(e)}"}
    
    def _determine_analysis_period(
        self, 
        start_time: Optional[datetime], 
        end_time: Optional[datetime]
    ) -> Tuple[datetime, datetime]:
        """Determine the analysis period, defaulting to full database range if not specified."""
        
        if start_time and end_time:
            return self._ensure_utc(start_time), self._ensure_utc(end_time)
        
        # If no timeframe provided, analyze ALL records in database
        if not start_time and not end_time:
            logger.info("No timeframe provided - analyzing full database range")
            try:
                # Get total count first to check if we have any data
                total_count = self.events_collection.count_documents({})
                if total_count == 0:
                    logger.warning("No events found in database, using default 24-hour period")
                    now = datetime.now(timezone.utc).replace(tzinfo=None)
                    return now - timedelta(days=1), now
                
                earliest_cursor = self.events_collection.find().sort("event_timestamp", 1).limit(1)
                earliest_events = list(earliest_cursor)
                
                latest_cursor = self.events_collection.find().sort("event_timestamp", -1).limit(1)
                latest_events = list(latest_cursor)
                
                if earliest_events and latest_events:
                    earliest_time = self._parse_timestamp_utc(earliest_events[0]["event_timestamp"])
                    latest_time = self._parse_timestamp_utc(latest_events[0]["event_timestamp"])
                    
                    if earliest_time and latest_time:
                        # Add small buffer to ensure we capture all data
                        buffered_start = earliest_time - timedelta(minutes=1)
                        buffered_end = latest_time + timedelta(minutes=1)
                        
                        logger.info(f"Found database range: {buffered_start} to {buffered_end}")
                        return buffered_start, buffered_end
                    else:
                        logger.warning("Could not parse timestamps from database events")
                else:
                    logger.warning("No events returned from database queries")
                            
            except Exception as e:
                logger.error(f"Error finding full database range: {e}")
        
        # Handle case where only one time is provided
        if start_time and not end_time:
            start_utc = self._ensure_utc(start_time)
            # Default to 24 hours from start time
            end_utc = start_utc + timedelta(days=1)
            logger.info(f"Only start_time provided, using 24-hour period: {start_utc} to {end_utc}")
            return start_utc, end_utc
        
        if end_time and not start_time:
            end_utc = self._ensure_utc(end_time)
            # Default to 24 hours before end time
            start_utc = end_utc - timedelta(days=1)
            logger.info(f"Only end_time provided, using 24-hour period: {start_utc} to {end_utc}")
            return start_utc, end_utc
        
        # Fallback to last 24 hours
        logger.warning("Falling back to last 24 hours as default analysis period")
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        return now - timedelta(days=1), now
        

    def _find_system_sessions(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Find all system sessions based on workcell/lab start events."""
        
        sessions = []
        start_event_types = [
            EventType.LAB_START.value,
            EventType.WORKCELL_START.value,
            "lab_start",
            "workcell_start"
        ]
        
        # Try multiple query strategies for timestamp format compatibility
        queries_to_try = [
            {
                "event_type": {"$in": start_event_types},
                "event_timestamp": {"$gte": start_time, "$lte": end_time}
            },
            {
                "event_type": {"$in": start_event_types},
                "event_timestamp": {"$gte": start_time.isoformat(), "$lte": end_time.isoformat()}
            },
            {
                "event_type": {"$in": start_event_types}
            }
        ]
        
        start_events = []
        
        for i, query in enumerate(queries_to_try):
            try:
                events = list(self.events_collection.find(query).sort("event_timestamp", 1))
                
                if events:
                    # Filter by timeframe manually if needed (for query 3)
                    if i == 2:  # No time constraint query
                        filtered_events = []
                        for event in events:
                            event_time = self._parse_timestamp_utc(event["event_timestamp"])
                            if event_time and start_time <= event_time <= end_time:
                                filtered_events.append(event)
                        start_events = filtered_events
                    else:
                        start_events = events
                    break
                        
            except Exception as e:
                logger.warning(f"Query {i+1} failed: {e}")
                continue
        
        logger.info(f"Found {len(start_events)} session start events")
        
        # Process each start event
        for start_event in start_events:
            start_timestamp = self._parse_timestamp_utc(start_event["event_timestamp"])
            if not start_timestamp:
                continue
                
            # Extract session info
            event_data = start_event.get("event_data", {})
            source = start_event.get("source", {})
            
            workcell_id = (
                source.get("workcell_id") or 
                source.get("manager_id") or 
                event_data.get("workcell_id") or
                f"system_{int(start_timestamp.timestamp())}"
            )
            
            session_name = (
                event_data.get("workcell_name") or
                event_data.get("name") or
                f"Workcell {workcell_id[-8:] if workcell_id else 'Unknown'}"
            )
            
            # Find when this session ends
            stop_timestamp = self._find_session_stop_time(
                workcell_id, start_timestamp, end_time
            )
            
            # If no explicit stop found, look for next start of same workcell
            if not stop_timestamp:
                next_start = self._find_next_workcell_start(
                    workcell_id, start_timestamp, start_events
                )
                if next_start:
                    stop_timestamp = next_start
                else:
                    # Only use analysis end time as last resort
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
                "session_id": workcell_id,
                "session_name": session_name,
                "start_time": start_timestamp,
                "end_time": stop_timestamp,
                "duration_seconds": (stop_timestamp - start_timestamp).total_seconds(),
                "source": "system_lifecycle_events",
                "workcell_nodes": event_data.get("nodes", {})
            }
            
            sessions.append(session)
            print(f"\n=== DEBUG SESSION DETECTION ===")
            print(f"Found {len(sessions)} sessions between {start_time} and {end_time}")
            
            total_duration = 0
            for i, session in enumerate(sessions):
                duration_hours = session["duration_seconds"] / 3600
                total_duration += duration_hours
                print(f"Session {i+1}: {session['session_type']} '{session['session_name']}'")
                print(f"  Duration: {duration_hours:.2f} hours")
                print(f"  Start: {session['start_time']}")
                print(f"  End: {session['end_time']}")
            
            print(f"Total session duration: {total_duration:.2f} hours")
            
        return sessions

    def _find_next_workcell_start(self, workcell_id: str, current_start: datetime, all_start_events: List[Dict]) -> Optional[datetime]:
        """Find the next start event for the same workcell to use as implicit stop time."""
        next_starts = []
        
        for event in all_start_events:
            event_time = self._parse_timestamp_utc(event.get("event_timestamp"))
            if not event_time or event_time <= current_start:
                continue
                
            # Check if this event is for the same workcell
            event_data = event.get("event_data", {})
            source = event.get("source", {})
            
            event_workcell_id = (
                source.get("workcell_id") or 
                source.get("manager_id") or 
                event_data.get("workcell_id")
            )
            
            if event_workcell_id == workcell_id:
                next_starts.append(event_time)
        
        return min(next_starts) if next_starts else None

    def _find_session_stop_time(self, workcell_id: str, start_after: datetime, end_time: datetime) -> Optional[datetime]:
        """Find when a workcell stopped, if at all."""
        try:
            stop_events = list(self.events_collection.find({
                "event_type": {"$in": ["workcell_stop", "lab_stop", "WORKCELL_STOP", "LAB_STOP"]},
                "$or": [
                    {"source.workcell_id": workcell_id},
                    {"source.manager_id": workcell_id},
                    {"event_data.workcell_id": workcell_id}
                ]
            }).sort("event_timestamp", 1))
            
            for stop_event in stop_events:
                stop_time = self._parse_timestamp_utc(stop_event.get("event_timestamp"))
                if stop_time and stop_time > start_after and stop_time <= end_time:
                    return stop_time
                    
        except Exception as e:
            logger.warning(f"Error finding stop time for workcell {workcell_id}: {e}")
        
        return None

    def _analyze_session_utilization(self, session: Dict) -> Dict[str, Any]:
        """Analyze utilization for a single session."""
        try:
            session_start = session["start_time"]
            session_end = session["end_time"] or datetime.now(timezone.utc).replace(tzinfo=None)
            
            # Get events and calculate utilization
            session_events = self._get_session_events(session_start, session_end)
            relevant_events = self._filter_activity_events(session_events)
            system_util = self._calculate_system_utilization(relevant_events, session_start, session_end)
            node_utils = self._calculate_node_utilization(relevant_events, session_start, session_end)
            
            # Resolve names
            session_name = self._resolve_session_name(session)
            
            # Build experiment details
            experiment_details = []
            for exp_id in system_util.active_experiments:
                exp_name = self._resolve_experiment_name(exp_id)
                display_name = exp_name if exp_name else f"Experiment {exp_id[-8:]}"
                experiment_details.append({
                    "experiment_id": exp_id,
                    "experiment_name": exp_name,
                    "display_name": display_name
                })
            
            # Build node utilizations with readable names
            node_utilizations_with_names = {}
            for node_id, node_util in node_utils.items():
                if self._is_workcell_id(node_id):
                    logger.info(f"Filtering out workcell {node_id} from session node summary")
                    continue

                node_name = self._resolve_node_name(node_id)
                if not node_name:
                    if self._is_workcell_id(node_id):
                        logger.info(f"Confirmed {node_id} is a workcell, excluding from session node summary")
                        continue

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
                    
                    # Raw data for analysis
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
            
            # Compile session report
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
                
                # Raw data for compatibility and analysis
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
            logger.error(f"Error analyzing session utilization: {e}")
            return {
                "error": str(e),
                "session_type": session["session_type"],
                "session_id": session["session_id"],
                "start_time": session["start_time"].isoformat(),
                "duration_hours": session["duration_seconds"] / 3600
            }
    
    def _get_session_events(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Get all events for a session timeframe."""
        try:
            # Try multiple query approaches for timestamp formats
            queries_to_try = [
                {"event_timestamp": {"$gte": start_time, "$lte": end_time}},
                {"event_timestamp": {"$gte": start_time.isoformat(), "$lte": end_time.isoformat()}},
                {}
            ]
            
            events = []
            
            for i, query in enumerate(queries_to_try):
                try:
                    if i == 2:  # Get all and filter manually
                        all_events = list(self.events_collection.find().sort("event_timestamp", 1))
                        # Filter manually by parsing timestamps
                        for event in all_events:
                            event_time = self._parse_timestamp_utc(event.get("event_timestamp"))
                            if event_time and start_time <= event_time <= end_time:
                                events.append(event)
                    else:
                        events = list(self.events_collection.find(query).sort("event_timestamp", 1))
                    
                    if events:
                        break
                        
                except Exception as e:
                    logger.warning(f"Event query {i+1} failed: {e}")
                    continue
            
            # Parse all timestamps to UTC
            valid_events = []
            for event in events:
                if "event_timestamp" in event:
                    parsed_ts = self._parse_timestamp_utc(event["event_timestamp"])
                    if parsed_ts:
                        event["event_timestamp"] = parsed_ts
                        valid_events.append(event)
            
            logger.debug(f"Found {len(valid_events)} events in session timeframe")
            return valid_events
            
        except Exception as e:
            logger.error(f"Error getting session events: {e}")
            return []
    
    def _filter_activity_events(self, events: List[Dict]) -> List[Dict]:
        """Filter events that indicate actual system activity."""
        
        relevant_events = []
        
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
        
        logger.debug(f"Filtered to {len(relevant_events)} activity events")
        return relevant_events
    
    def _calculate_system_utilization(
        self, 
        events: List[Dict], 
        start_time: datetime, 
        end_time: datetime
    ) -> SystemUtilizationData:
        """Calculate system utilization based on experiment events."""
        
        system_util = SystemUtilizationData()
        
        # Track experiments and calculate active periods
        active_experiments = set()
        experiment_periods = []
        experiment_starts = {}
        
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
            
            elif any(end_pattern in event_type for end_pattern in ["experiment_complete", "experiment_failed", "experiment_cancelled"]):
                exp_id = self._extract_experiment_id(event)
                if exp_id and exp_id in experiment_starts:
                    start_time_exp = experiment_starts[exp_id]
                    experiment_periods.append((start_time_exp, event_time))
                    active_experiments.discard(exp_id)
        
        # Handle ongoing experiments
        current_time = end_time
        for exp_id, start_time_exp in experiment_starts.items():
            if exp_id in active_experiments:
                experiment_periods.append((start_time_exp, current_time))
        
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
        
        return system_util
    
    def _is_workcell_id(self, entity_id: str) -> bool:
        """Check if an ID belongs to a workcell by looking for workcell-specific events."""
        
        if not entity_id:
            return False
        
        try:
            # Check if this ID has workcell start/stop events or appears as workcell source
            workcell_events = list(self.events_collection.find({
                "$or": [
                    {
                        "event_type": {"$in": ["workcell_start", "workcell_stop", "lab_start", "lab_stop"]},
                        "$or": [
                            {"source.workcell_id": entity_id},
                            {"source.manager_id": entity_id},
                            {"event_data.workcell_id": entity_id}
                        ]
                    },
                    {"source.workcell_id": entity_id},
                    {"source.manager_id": entity_id}
                ]
            }).limit(1))
            
            return len(workcell_events) > 0
            
        except Exception as e:
            logger.warning(f"Error checking if {entity_id} is workcell: {e}")
            return False
        
    def _calculate_node_utilization(
        self, 
        events: List[Dict], 
        start_time: datetime, 
        end_time: datetime
    ) -> Dict[str, NodeUtilizationData]:
        """Calculate node utilization based on action events."""
        
        # Group events by node
        node_events = defaultdict(list)
        
        for event in events:
            node_id = self._extract_node_id(event)
            if node_id:
                if self._is_workcell_id(node_id):
                    logger.debug(f"Skipping workcell {node_id} from node utilization calculation")
                    continue
                    
                node_events[node_id].append(event)        

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
                    # Action started
                    if status in ["running", "started", "in_progress"]:
                        if action_id not in active_actions:
                            active_actions.add(action_id)
                            if current_busy_start is None:
                                current_busy_start = event_time
                    
                    # Action completed
                    elif status in ["completed", "failed", "cancelled", "finished", "succeeded"]:
                        if action_id in active_actions:
                            active_actions.remove(action_id)
                            if not active_actions and current_busy_start is not None:
                                busy_periods.append((current_busy_start, event_time))
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
                
        return node_util
    
    def _get_workflow_events_for_users(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Get workflow start and complete events for user analysis."""
        
        workflow_event_types = [
            "workflow_start", "workflow_complete", 
            "WORKFLOW_START", "WORKFLOW_COMPLETE"
        ]
        
        # Use multi-strategy approach
        queries_to_try = [
            {
                "event_type": {"$in": workflow_event_types},
                "event_timestamp": {"$gte": start_time, "$lte": end_time}
            },
            {
                "event_type": {"$in": workflow_event_types},
                "event_timestamp": {"$gte": start_time.isoformat(), "$lte": end_time.isoformat()}
            },
            {
                "event_type": {"$in": workflow_event_types}
            }
        ]
        
        events = []
        
        for i, query in enumerate(queries_to_try):
            try:
                if i == 2:  # Filter manually
                    all_events = list(self.events_collection.find(query).sort("event_timestamp", 1))
                    for event in all_events:
                        event_time = self._parse_timestamp_utc(event.get("event_timestamp"))
                        if event_time and start_time <= event_time <= end_time:
                            events.append(event)
                else:
                    events = list(self.events_collection.find(query).sort("event_timestamp", 1))
                
                if events:
                    break
                    
            except Exception as e:
                logger.warning(f"Workflow query {i+1} failed: {e}")
                continue
        
        # Parse timestamps
        valid_events = []
        for event in events:
            event_time = self._parse_timestamp_utc(event.get("event_timestamp"))
            if event_time:
                event["parsed_timestamp"] = event_time
                valid_events.append(event)
        
        logger.info(f"Found {len(valid_events)} workflow events for user analysis")
        return valid_events

    def _calculate_user_statistics(self, events: List[Dict]) -> Dict[str, Dict[str, Any]]:
        """Calculate statistics for each user/author."""
        
        users = {}
        workflows = {}  # Track workflow lifecycle
        
        for event in events:
            event_type = str(event.get("event_type", "")).lower()
            event_data = event.get("event_data", {})
            workflow_id = event_data.get("workflow_id")
            author = event_data.get("author")
            
            if not workflow_id:
                continue
            
            # Initialize workflow tracking
            if workflow_id not in workflows:
                workflows[workflow_id] = {
                    "workflow_id": workflow_id,
                    "workflow_name": event_data.get("workflow_name", "Unknown"),
                    "author": author,
                    "start_time": None,
                    "end_time": None,
                    "status": "unknown",
                    "duration_seconds": None
                }
            
            workflow = workflows[workflow_id]
            
            # Update workflow data with any new info
            if author and not workflow["author"]:
                workflow["author"] = author
            
            # Process event types
            if "start" in event_type:
                workflow["start_time"] = event["parsed_timestamp"]
                workflow["status"] = "started"
                
            elif "complete" in event_type:
                workflow["end_time"] = event["parsed_timestamp"]
                workflow["status"] = event_data.get("status", "completed")
                
                # Use duration from event if available, otherwise calculate
                if event_data.get("duration_seconds"):
                    workflow["duration_seconds"] = event_data["duration_seconds"]
                elif workflow["start_time"] and workflow["end_time"]:
                    workflow["duration_seconds"] = (
                        workflow["end_time"] - workflow["start_time"]
                    ).total_seconds()
        
        # Aggregate statistics by user
        for workflow in workflows.values():
            author = workflow["author"]
            
            # Handle workflows without authors
            if not author or author.strip() == "":
                author = "Unknown Author"
            
            if author not in users:
                users[author] = {
                    "author": author,
                    "total_workflows": 0,
                    "completed_workflows": 0,
                    "failed_workflows": 0,
                    "cancelled_workflows": 0,
                    "total_runtime_hours": 0,
                    "average_workflow_duration_hours": 0,
                    "shortest_workflow_hours": None,
                    "longest_workflow_hours": None,
                    "completion_rate_percent": 0,
                    "workflows": []
                }
            
            user = users[author]
            user["total_workflows"] += 1
            
            # Status tracking
            if workflow["status"] == "completed":
                user["completed_workflows"] += 1
            elif workflow["status"] == "failed":
                user["failed_workflows"] += 1
            elif workflow["status"] == "cancelled":
                user["cancelled_workflows"] += 1
            
            # Duration tracking
            if workflow["duration_seconds"] is not None:
                duration_hours = workflow["duration_seconds"] / 3600
                user["total_runtime_hours"] += duration_hours
                
                if user["shortest_workflow_hours"] is None or duration_hours < user["shortest_workflow_hours"]:
                    user["shortest_workflow_hours"] = duration_hours
                    
                if user["longest_workflow_hours"] is None or duration_hours > user["longest_workflow_hours"]:
                    user["longest_workflow_hours"] = duration_hours
            
            # Add workflow to user's list
            user["workflows"].append({
                "workflow_id": workflow["workflow_id"],
                "workflow_name": workflow["workflow_name"],
                "start_time": workflow["start_time"].isoformat() if workflow["start_time"] else None,
                "end_time": workflow["end_time"].isoformat() if workflow["end_time"] else None,
                "duration_hours": workflow["duration_seconds"] / 3600 if workflow["duration_seconds"] else None,
                "status": workflow["status"]
            })
        
        # Calculate averages and percentages
        for user in users.values():
            if user["total_workflows"] > 0:
                user["completion_rate_percent"] = round(
                    (user["completed_workflows"] / user["total_workflows"]) * 100, 2
                )
                
                # Calculate average duration for workflows with known duration
                workflows_with_duration = [w for w in user["workflows"] if w["duration_hours"] is not None]
                if workflows_with_duration:
                    user["average_workflow_duration_hours"] = round(
                        sum(w["duration_hours"] for w in workflows_with_duration) / len(workflows_with_duration), 3
                    )
            
            # Round values
            user["total_runtime_hours"] = round(user["total_runtime_hours"], 2)
            if user["shortest_workflow_hours"] is not None:
                user["shortest_workflow_hours"] = round(user["shortest_workflow_hours"], 3)
            if user["longest_workflow_hours"] is not None:
                user["longest_workflow_hours"] = round(user["longest_workflow_hours"], 3)
        
        return users

    def _calculate_system_totals(self, events: List[Dict]) -> Dict[str, Any]:
        """Calculate system-wide totals for percentage calculations."""
        
        workflows = {}
        
        for event in events:
            event_data = event.get("event_data", {})
            workflow_id = event_data.get("workflow_id")
            
            if not workflow_id:
                continue
                
            if workflow_id not in workflows:
                workflows[workflow_id] = {
                    "author": event_data.get("author"),
                    "duration_seconds": None,
                    "status": "unknown"
                }
            
            # Update with completion data
            event_type = str(event.get("event_type", "")).lower()
            if "complete" in event_type:
                workflows[workflow_id]["duration_seconds"] = event_data.get("duration_seconds")
                workflows[workflow_id]["status"] = event_data.get("status", "completed")
        
        total_workflows = len(workflows)
        workflows_with_authors = sum(1 for w in workflows.values() if w["author"] and w["author"].strip())
        workflows_without_authors = total_workflows - workflows_with_authors
        
        completed_workflows = sum(1 for w in workflows.values() if w["status"] == "completed")
        
        # Calculate total runtime
        total_runtime_seconds = sum(
            w["duration_seconds"] for w in workflows.values() 
            if w["duration_seconds"] is not None
        )
        total_runtime_hours = total_runtime_seconds / 3600
        
        # Calculate average duration
        workflows_with_duration = [w for w in workflows.values() if w["duration_seconds"] is not None]
        average_duration_hours = 0
        if workflows_with_duration:
            average_duration_hours = (
                sum(w["duration_seconds"] for w in workflows_with_duration) / 
                len(workflows_with_duration)
            ) / 3600
        
        completion_rate_percent = 0
        if total_workflows > 0:
            completion_rate_percent = (completed_workflows / total_workflows) * 100
        
        return {
            "total_workflows": total_workflows,
            "workflows_with_authors": workflows_with_authors,
            "workflows_without_authors": workflows_without_authors,
            "total_runtime_hours": round(total_runtime_hours, 2),
            "average_duration_hours": round(average_duration_hours, 3),
            "completion_rate_percent": round(completion_rate_percent, 2)
        }
    
    def _generate_overall_summary(self, session_reports: List[Dict], start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Generate overall summary from session reports."""
        
        try:
            total_sessions = len(session_reports)
            total_runtime = sum(s.get("duration_hours", 0) for s in session_reports)
            total_active_time = sum(s.get("active_time_hours", 0) for s in session_reports)
            total_experiments = sum(s.get("total_experiments", 0) for s in session_reports)
            
            # Calculate average system utilization
            valid_sessions = [s for s in session_reports if "error" not in s]
            avg_utilization = sum(s.get("system_utilization_percent", 0) for s in valid_sessions) / len(valid_sessions) if valid_sessions else 0
            
            # Aggregate node data
            node_summary = defaultdict(lambda: {
                "total_busy_time_hours": 0,
                "utilizations": [],
                "sessions_active": 0
            })
            
            for session in valid_sessions:
                for node_id, node_data in session.get("node_utilizations", {}).items():
                    if self._is_workcell_id(node_id):
                        logger.debug(f"Skipping workcell {node_id} from overall node summary")
                        continue
                    
                    # Safety check for node_data
                    if not node_data or not isinstance(node_data, dict):
                        continue
                        
                    node_summary[node_id]["total_busy_time_hours"] += node_data.get("busy_time_hours", 0)
                    node_summary[node_id]["utilizations"].append(node_data.get("utilization_percent", 0))
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
            logger.error(f"Error generating overall summary: {e}")
            return {"error": str(e)}
    
    # Helper methods
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
        source = event.get("source", {})
        if isinstance(source, dict) and source.get("experiment_id"):
            return str(source["experiment_id"])
        
        event_data = event.get("event_data", {})
        if isinstance(event_data, dict):
            # Direct experiment_id
            if event_data.get("experiment_id"):
                return str(event_data["experiment_id"])
            
            # Nested experiment object
            if isinstance(event_data.get("experiment"), dict):
                exp = event_data["experiment"]
                exp_id = exp.get("experiment_id") or exp.get("_id")
                if exp_id:
                    return str(exp_id)
        
        return None
    
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
                # Handle ISO format strings
                if 'T' in timestamp:
                    if timestamp.endswith('Z'):
                        return datetime.fromisoformat(timestamp.replace('Z', '+00:00')).astimezone(timezone.utc).replace(tzinfo=None)
                    elif '+' in timestamp or timestamp.count('-') > 2:
                        return datetime.fromisoformat(timestamp).astimezone(timezone.utc).replace(tzinfo=None)
                    else:
                        # Assume it's already UTC if no timezone info
                        dt = datetime.fromisoformat(timestamp)
                        return dt
                else:
                    return datetime.fromisoformat(timestamp)
            except ValueError:
                try:
                    return datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    logger.warning(f"Could not parse timestamp: {timestamp}")
                    return None
        
        return None
    
    def _ensure_utc(self, dt: datetime) -> datetime:
        """Ensure datetime is UTC without timezone info."""
        if dt.tzinfo is not None:
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    
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
            logger.warning(f"Error resolving session name: {e}")
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
            logger.warning(f"Error resolving node name for {node_id}: {e}")
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
            logger.warning(f"Error resolving experiment name for {experiment_id}: {e}")
            return None
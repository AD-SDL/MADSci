"""Time-series analysis for MADSci utilization data with session attribution."""

import logging
import statistics
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from collections import defaultdict

import pytz

logger = logging.getLogger(__name__)


class TimeSeriesAnalyzer:
    """Analyzes utilization data over time with proper session attribution."""
    
    def __init__(self, utilization_analyzer):
        """Initialize with existing UtilizationAnalyzer instance."""
        self.analyzer = utilization_analyzer
        self.events_collection = utilization_analyzer.events_collection
    
    def generate_summary_report(
        self,
        start_time: datetime,
        end_time: datetime,
        analysis_type: str = "daily", 
        user_timezone: str = "America/Chicago"
    ) -> Dict[str, Any]:
        """Generate summary utilization report with corrected daily session handling."""
        
        # Store analysis type for use in attribution logic
        self._current_analysis_type = analysis_type
        
        logger.info(f"Generating {analysis_type} summary report for timezone {user_timezone}")
        
        # CRITICAL FIX: Get ALL real sessions for the entire period ONCE
        # Don't let daily bucketing fragment them
        all_real_sessions = self.analyzer._find_system_sessions(start_time, end_time)
        
        print(f"\n=== REAL SESSION DETECTION (BEFORE BUCKETING) ===")
        total_real_duration = 0
        for i, session in enumerate(all_real_sessions):
            duration_hours = session["duration_seconds"] / 3600
            total_real_duration += duration_hours
            print(f"Real Session {i+1}: {duration_hours:.2f} hours")
            print(f"  Start: {session['start_time']}")
            print(f"  End: {session['end_time']}")
        print(f"Total real session duration: {total_real_duration:.2f} hours")
        
        # Determine bucket type from analysis_type
        if analysis_type == "hourly":
            time_bucket_hours = 1
        elif analysis_type == "daily":
            time_bucket_hours = 24
        elif analysis_type == "weekly":
            time_bucket_hours = 168
        elif analysis_type in ["monthly", "mounthly"]:
            time_bucket_hours = "monthly"
        else:
            time_bucket_hours = 24
        
        # Create time buckets
        time_buckets = self._create_time_buckets_user_timezone(
            start_time, end_time, time_bucket_hours, user_timezone
        )
        
        logger.info(f"Created {len(time_buckets)} time buckets")
        
        # FIXED: For daily analysis, distribute real sessions across buckets
        # instead of creating new sessions per bucket
        if analysis_type == 'daily':
            bucket_reports = self._create_daily_buckets_from_real_sessions(
                time_buckets, all_real_sessions, start_time, end_time
            )
        else:
            # Original logic for weekly/monthly
            bucket_reports = []
            for i, bucket_info in enumerate(time_buckets):
                if isinstance(bucket_info, dict):
                    bucket_start, bucket_end = bucket_info['utc_times']
                    period_info = bucket_info.get('period_info', {})
                else:
                    bucket_start, bucket_end = bucket_info
                    period_info = {"type": "period", "display": bucket_start.strftime("%Y-%m-%d")}
                
                # Generate base session report for this bucket
                bucket_report = self.analyzer.generate_session_based_report(bucket_start, bucket_end)
                
                # Apply session attribution for this bucket
                bucket_report = self._apply_session_attribution(
                    bucket_report, {}, bucket_start, bucket_end
                )
                
                # Add time bucket info
                bucket_report["time_bucket"] = {
                    "bucket_index": i,
                    "start_time": bucket_start.isoformat(),
                    "end_time": bucket_end.isoformat(),
                    "duration_hours": (bucket_end - bucket_start).total_seconds() / 3600,
                    "period_info": period_info
                }
                
                bucket_reports.append(bucket_report)
        
        # Create summary report
        return self._create_summary_report(bucket_reports, start_time, end_time, analysis_type, user_timezone)
    
    def _create_daily_buckets_from_real_sessions(
        self,
        time_buckets: List,
        real_sessions: List[Dict],
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict]:
        """Create daily bucket reports by distributing real sessions across days."""
        
        bucket_reports = []
        
        for i, bucket_info in enumerate(time_buckets):
            if isinstance(bucket_info, dict):
                bucket_start, bucket_end = bucket_info['utc_times']
                user_start, user_end = bucket_info['user_times']
                period_info = bucket_info.get('period_info', {})
            else:
                bucket_start, bucket_end = bucket_info
                user_start, user_end = bucket_start, bucket_end
                period_info = {"type": "period", "display": user_start.strftime("%Y-%m-%d")}
            
            print(f"\n=== DAILY BUCKET {i+1}: {period_info.get('display', 'Unknown')} ===")
            
            # Get experiments that actually occurred within this day
            actual_experiments_in_period = self._get_experiments_in_time_period(
                bucket_start, bucket_end
            )
            print(f"Experiments in this day: {len(actual_experiments_in_period)}")
            
            # Find real sessions that overlap with this day and calculate proportional runtime
            day_sessions = []
            total_day_runtime = 0
            total_day_active_time = 0
            
            for session in real_sessions:
                session_start = session["start_time"]
                session_end = session["end_time"]
                
                # Calculate overlap between session and this day
                overlap_start = max(bucket_start, session_start)
                overlap_end = min(bucket_end, session_end)
                
                if overlap_start < overlap_end:
                    # There's overlap - calculate proportional runtime
                    overlap_seconds = (overlap_end - overlap_start).total_seconds()
                    overlap_hours = overlap_seconds / 3600
                    
                    session_duration_seconds = session["duration_seconds"]
                    session_duration_hours = session_duration_seconds / 3600
                    
                    # Calculate proportional active time
                    # Assume active time is distributed proportionally across the session
                    if session_duration_seconds > 0:
                        proportion = overlap_seconds / session_duration_seconds
                        # We need to estimate active time - for now use a small fraction
                        estimated_session_active_time = session_duration_hours * 0.01  # 1% active time estimate
                        proportional_active_time = estimated_session_active_time * proportion
                    else:
                        proportional_active_time = 0
                    
                    total_day_runtime += overlap_hours
                    total_day_active_time += proportional_active_time
                    
                    # Count experiments that occurred during this session's overlap
                    session_experiments = [
                        exp for exp in actual_experiments_in_period
                        if overlap_start <= exp["event_timestamp"] <= overlap_end
                    ]
                    
                    # Create a session fragment for this day
                    day_session = {
                        "session_type": session["session_type"],
                        "session_id": session["session_id"],
                        "session_name": session["session_name"],
                        "start_time": overlap_start.isoformat(),
                        "end_time": overlap_end.isoformat(),
                        "duration_hours": overlap_hours,
                        "active_time_hours": proportional_active_time,
                        "total_experiments": len(session_experiments),
                        "system_utilization_percent": (proportional_active_time / overlap_hours * 100) if overlap_hours > 0 else 0,
                        "node_utilizations": {},  # Simplified for now
                        "experiment_details": [
                            {
                                "experiment_id": exp.get("experiment_id", ""),
                                "experiment_name": self.analyzer._resolve_experiment_name(exp.get("experiment_id", "")),
                                "display_name": f"Experiment {exp.get('experiment_id', '')[-8:]}"
                            }
                            for exp in session_experiments
                        ],
                        "attribution_method": "proportional_from_real_session"
                    }
                    
                    day_sessions.append(day_session)
                    
                    print(f"  Session overlap: {overlap_hours:.2f}h from {session['session_name']}")
            
            print(f"  Total day runtime: {total_day_runtime:.2f} hours")
            print(f"  Total experiments: {len(actual_experiments_in_period)}")
            
            # Create bucket report
            bucket_report = {
                "session_details": day_sessions,
                "overall_summary": {
                    "total_sessions": len(day_sessions),
                    "total_system_runtime_hours": total_day_runtime,
                    "total_active_time_hours": total_day_active_time,
                    "average_system_utilization_percent": (total_day_active_time / total_day_runtime * 100) if total_day_runtime > 0 else 0,
                    "total_experiments": len(actual_experiments_in_period),
                    "nodes_tracked": 0,  # Simplified for now
                    "method": "daily_proportional_from_real_sessions"
                },
                "time_bucket": {
                    "bucket_index": i,
                    "start_time": bucket_start.isoformat(),
                    "end_time": bucket_end.isoformat(),
                    "user_start_time": user_start.strftime("%Y-%m-%dT%H:%M:%S"),
                    "user_date": user_start.strftime("%Y-%m-%d"),
                    "duration_hours": (bucket_end - bucket_start).total_seconds() / 3600,
                    "period_info": period_info
                }
            }
            
            bucket_reports.append(bucket_report)
        
        return bucket_reports
    
    def _find_active_workcells_in_timeframe(self, start_time: datetime, end_time: datetime) -> Dict[str, Dict]:
        """Find all workcells that are active during the analysis timeframe."""
        active_workcells = {}
        
        # Look for workcell/lab start events
        start_event_types = [
            "lab_start", "workcell_start", "LAB_START", "WORKCELL_START"
        ]
        
        # Query for start events
        queries_to_try = [
            {"event_type": {"$in": start_event_types}},
            {"event_type": {"$regex": "start", "$options": "i"}}
        ]
        
        start_events = []
        for query in queries_to_try:
            try:
                events = list(self.events_collection.find(query).sort("event_timestamp", 1))
                if events:
                    start_events = events
                    break
            except Exception as e:
                logger.warning(f"Start event query failed: {e}")
                continue
        
        logger.debug(f"Found {len(start_events)} potential start events")
        
        for event in start_events:
            event_time = self.analyzer._parse_timestamp_utc(event.get("event_timestamp"))
            if not event_time:
                continue
            
            # Extract workcell info
            source = event.get("source", {})
            event_data = event.get("event_data", {})
            
            workcell_id = (
                source.get("workcell_id") or 
                source.get("manager_id") or 
                event_data.get("workcell_id") or
                event_data.get("manager_id")
            )
            
            if not workcell_id:
                continue
            
            workcell_name = (
                event_data.get("workcell_name") or
                event_data.get("name") or
                f"Workcell {workcell_id[-8:]}"
            )
            
            # Determine session type
            event_type = str(event["event_type"]).lower()
            session_type = "lab" if "lab" in event_type else "workcell"
            
            # Check if this workcell overlaps with our analysis timeframe
            workcell_end = self._find_workcell_stop_time(workcell_id, event_time) or end_time
            
            # If workcell is active during our timeframe, track it
            if event_time <= end_time and workcell_end >= start_time:
                active_workcells[workcell_id] = {
                    "workcell_id": workcell_id,
                    "workcell_name": workcell_name,
                    "session_type": session_type,
                    "start_time": event_time,
                    "end_time": workcell_end,
                    "overlaps_timeframe": True
                }
        
        return active_workcells
    
    def _find_workcell_stop_time(self, workcell_id: str, start_after: datetime) -> Optional[datetime]:
        """Find when a workcell stopped, if at all."""
        try:
            stop_events = list(self.events_collection.find({
                "event_type": {"$in": ["workcell_stop", "lab_stop", "WORKCELL_STOP", "LAB_STOP"]},
                "$or": [
                    {"source.workcell_id": workcell_id},
                    {"source.manager_id": workcell_id},
                    {"event_data.workcell_id": workcell_id}
                ],
                "event_timestamp": {"$gt": start_after.isoformat()}
            }).sort("event_timestamp", 1).limit(1))
            
            if stop_events:
                stop_time = self.analyzer._parse_timestamp_utc(stop_events[0].get("event_timestamp"))
                return stop_time
                
        except Exception as e:
            logger.warning(f"Error finding stop time for workcell {workcell_id}: {e}")
        
        return None
    
    def _apply_session_attribution(
        self, 
        bucket_report: Dict, 
        active_workcells: Dict[str, Dict], 
        bucket_start: datetime, 
        bucket_end: datetime
    ) -> Dict:
        """Apply session attribution with consistent daily runtime calculation."""
        
        session_details = bucket_report.get("session_details", [])
        if not session_details:
            return bucket_report

        analysis_type = self._current_analysis_type
        
        if analysis_type == 'daily':
            # FOR DAILY: Use proportional session runtime approach
            return self._handle_daily_proportional(bucket_report, bucket_start, bucket_end)
        
        # ORIGINAL LOGIC for weekly/monthly (works fine)
        default_sessions = []
        real_workcell_sessions = []
        
        for session in session_details:
            session_type = session.get("session_type", "")
            total_experiments = session.get("total_experiments", 0)
            
            if session_type == "default_analysis" and total_experiments > 0:
                default_sessions.append(session)
            elif session_type in ["workcell", "lab"]:
                real_workcell_sessions.append(session)
        
        # If we have default sessions with experiments, try to attribute them
        if default_sessions:
            logger.debug(f"Attempting to attribute {len(default_sessions)} default sessions")
            
            if len(real_workcell_sessions) == 1:
                primary_workcell = real_workcell_sessions[0]
                for default_session in default_sessions:
                    primary_workcell = self._merge_sessions(primary_workcell, default_session)
                bucket_report["session_details"] = [primary_workcell]
                
            elif len(real_workcell_sessions) == 0 and active_workcells:
                best_workcell = self._find_best_active_workcell(
                    active_workcells, bucket_start, bucket_end
                )
                if best_workcell:
                    attributed_session = self._create_attributed_workcell_session(
                        best_workcell, default_sessions, bucket_start, bucket_end
                    )
                    bucket_report["session_details"] = [attributed_session]
        
        # Recalculate overall summary if we modified sessions
        if len(session_details) != len(bucket_report.get("session_details", [])):
            bucket_report["overall_summary"] = self._recalculate_overall_summary(
                bucket_report.get("session_details", [])
            )
        
        return bucket_report

    def _handle_daily_proportional(
        self, 
        bucket_report: Dict, 
        bucket_start: datetime, 
        bucket_end: datetime
    ) -> Dict:
        """Handle daily analysis with proportional session runtime distribution."""
        
        # Get experiments that actually occurred within this day
        actual_experiments_in_period = self._get_experiments_in_time_period(
            bucket_start, bucket_end
        )
        
        logger.debug(f"Found {len(actual_experiments_in_period)} experiments in period {bucket_start.date()}")
        
        session_details = bucket_report.get("session_details", [])
        
        # Calculate proportional runtime and attribution for this day
        day_runtime = 0
        day_active_time = 0
        day_experiments = len(actual_experiments_in_period)
        day_utilization = 0
        
        attributed_sessions = []
        
        for session in session_details:
            session_start_str = session.get("start_time", "")
            session_end_str = session.get("end_time", "")
            
            if not session_start_str:
                continue
                
            try:
                session_start = datetime.fromisoformat(session_start_str.replace('Z', '+00:00')).replace(tzinfo=None)
                if session_end_str:
                    session_end = datetime.fromisoformat(session_end_str.replace('Z', '+00:00')).replace(tzinfo=None)
                else:
                    session_end = bucket_end
                
                # Calculate overlap between session and this day
                overlap_start = max(bucket_start, session_start)
                overlap_end = min(bucket_end, session_end)
                
                if overlap_start < overlap_end:
                    # There's overlap - calculate proportional runtime
                    overlap_seconds = (overlap_end - overlap_start).total_seconds()
                    overlap_hours = overlap_seconds / 3600
                    
                    session_duration = session.get("duration_hours", 0)
                    session_active_time = session.get("active_time_hours", 0)
                    session_util = session.get("system_utilization_percent", 0)
                    
                    # Calculate proportional times
                    if session_duration > 0:
                        proportion = overlap_hours / session_duration
                        proportional_active_time = session_active_time * proportion
                    else:
                        proportion = 1.0
                        proportional_active_time = session_active_time
                    
                    day_runtime += overlap_hours
                    day_active_time += proportional_active_time
                    
                    # For utilization, weight by runtime
                    if overlap_hours > 0:
                        day_utilization += session_util * overlap_hours
                    
                    # Count experiments that actually occurred during this session's overlap
                    session_experiments = [
                        exp for exp in actual_experiments_in_period
                        if overlap_start <= exp["event_timestamp"] <= overlap_end
                    ]
                    
                    # Create attributed session for this day
                    attributed_session = session.copy()
                    attributed_session.update({
                        "start_time": overlap_start.isoformat(),
                        "end_time": overlap_end.isoformat(),
                        "duration_hours": overlap_hours,
                        "active_time_hours": proportional_active_time,
                        "total_experiments": len(session_experiments),
                        "system_utilization_percent": session_util,
                        "attribution_method": "proportional_daily_overlap",
                        "experiment_details": [
                            {
                                "experiment_id": exp.get("experiment_id", ""),
                                "experiment_name": self.analyzer._resolve_experiment_name(exp.get("experiment_id", "")),
                                "display_name": f"Experiment {exp.get('experiment_id', '')[-8:]}"
                            }
                            for exp in session_experiments
                        ]
                    })
                    
                    attributed_sessions.append(attributed_session)
                    
            except Exception as e:
                logger.warning(f"Error processing session for daily attribution: {e}")
                continue
        
        # Calculate weighted average utilization
        if day_runtime > 0:
            day_utilization = day_utilization / day_runtime
        
        # Update bucket report
        bucket_report["session_details"] = attributed_sessions
        
        # Create new overall summary
        bucket_report["overall_summary"] = {
            "total_sessions": len(attributed_sessions),
            "total_system_runtime_hours": day_runtime,
            "total_active_time_hours": day_active_time,
            "average_system_utilization_percent": day_utilization,
            "total_experiments": day_experiments,
            "nodes_tracked": len(set().union(*(s.get("node_utilizations", {}).keys() for s in attributed_sessions))),
            "method": "proportional_daily_attribution"
        }
        
        return bucket_report

    def _recalculate_daily_summary_simple(
        self, 
        session_details: List[Dict], 
        actual_experiment_count: int
    ) -> Dict[str, Any]:
        """Simple recalculation - keep original session data, just fix experiment count."""
        
        # Use original session calculations
        total_sessions = len(session_details)
        total_runtime = sum(s.get("duration_hours", 0) for s in session_details)
        total_active_time = sum(s.get("active_time_hours", 0) for s in session_details)
        
        # Calculate average utilization
        valid_sessions = [s for s in session_details if "error" not in s]
        if valid_sessions:
            avg_utilization = sum(s.get("system_utilization_percent", 0) for s in valid_sessions) / len(valid_sessions)
        else:
            avg_utilization = 0
        
        # Aggregate node data
        node_summary = defaultdict(lambda: {
            "total_busy_time_hours": 0,
            "utilizations": [],
            "sessions_active": 0
        })
        
        for session in valid_sessions:
            for node_id, node_data in session.get("node_utilizations", {}).items():
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
            "total_experiments": actual_experiment_count,  # Use actual count from this period
            "nodes_tracked": len(final_node_summary),
            "node_summary": final_node_summary,
            "method": "daily_simple_experiment_count_correction"
        }
    def _handle_daily_session_attribution(
        self, 
        bucket_report: Dict, 
        bucket_start: datetime, 
        bucket_end: datetime
    ) -> Dict:
        """Handle session attribution specifically for daily buckets."""
        
        # For daily buckets, we need to count experiments that actually occurred within this day
        actual_experiments_in_period = self._get_experiments_in_time_period(
            bucket_start, bucket_end
        )
        
        logger.debug(f"Found {len(actual_experiments_in_period)} experiments actually occurring in period {bucket_start.date()} to {bucket_end.date()}")
        
        session_details = bucket_report.get("session_details", [])
        
        if session_details:
            # Find the best session to attribute these experiments to
            best_session = self._find_best_session_for_period(
                session_details, bucket_start, bucket_end
            )
            
            if best_session:
                # Update the session with actual experiment count for this period
                best_session["total_experiments"] = len(actual_experiments_in_period)
                best_session["experiment_details"] = [
                    {
                        "experiment_id": exp.get("experiment_id", ""),
                        "experiment_name": self.analyzer._resolve_experiment_name(exp.get("experiment_id", "")),
                        "display_name": f"Experiment {exp.get('experiment_id', '')[-8:]}"
                    }
                    for exp in actual_experiments_in_period
                ]
                
                # IMPORTANT: Keep the original session runtime, don't recalculate it
                # This ensures consistency with weekly/monthly reports
                # The session duration represents the time the system was available/configured
                
                # Keep only this session for the daily bucket
                bucket_report["session_details"] = [best_session]
            else:
                # No good session found, but we still need to account for system runtime
                # Use the original session durations from the bucket report
                bucket_report["session_details"] = session_details
                
                # Update experiment counts for all sessions in this period
                for session in bucket_report["session_details"]:
                    # Only the session with the best overlap gets the experiments
                    session_start = datetime.fromisoformat(session["start_time"].replace('Z', '+00:00')).replace(tzinfo=None)
                    session_end_str = session.get("end_time")
                    if session_end_str:
                        session_end = datetime.fromisoformat(session_end_str.replace('Z', '+00:00')).replace(tzinfo=None)
                    else:
                        session_end = bucket_end
                    
                    # Check if experiments fall within this session's timeframe
                    session_experiments = [
                        exp for exp in actual_experiments_in_period
                        if session_start <= exp["event_timestamp"] <= session_end
                    ]
                    
                    session["total_experiments"] = len(session_experiments)
                    session["experiment_details"] = [
                        {
                            "experiment_id": exp.get("experiment_id", ""),
                            "experiment_name": self.analyzer._resolve_experiment_name(exp.get("experiment_id", "")),
                            "display_name": f"Experiment {exp.get('experiment_id', '')[-8:]}"
                        }
                        for exp in session_experiments
                    ]
        elif actual_experiments_in_period:
            # We have experiments but no sessions - create a minimal session
            bucket_report["session_details"] = [{
                "session_type": "daily_period",
                "session_name": "Daily Analysis Period",
                "start_time": bucket_start.isoformat(),
                "end_time": bucket_end.isoformat(),
                "total_experiments": len(actual_experiments_in_period),
                "system_utilization_percent": 0,
                "duration_hours": (bucket_end - bucket_start).total_seconds() / 3600,
                "active_time_hours": 0,  # We don't have session data to calculate this properly
                "experiment_details": [
                    {
                        "experiment_id": exp.get("experiment_id", ""),
                        "experiment_name": self.analyzer._resolve_experiment_name(exp.get("experiment_id", "")),
                        "display_name": f"Experiment {exp.get('experiment_id', '')[-8:]}"
                    }
                    for exp in actual_experiments_in_period
                ]
            }]
        
        # Recalculate overall summary - but keep original runtime calculations
        bucket_report["overall_summary"] = self._recalculate_overall_summary_for_daily(
            bucket_report.get("session_details", []), len(actual_experiments_in_period)
        )
        
        return bucket_report

    def _get_experiments_in_time_period(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Get experiments that actually started within the given time period."""
        
        experiment_events = []
        
        # Query for experiment start events in the specific time period
        queries_to_try = [
            {
                "event_type": {"$in": ["experiment_start", "EXPERIMENT_START"]},
                "event_timestamp": {"$gte": start_time, "$lte": end_time}
            },
            {
                "event_type": {"$in": ["experiment_start", "EXPERIMENT_START"]},
                "event_timestamp": {"$gte": start_time.isoformat(), "$lte": end_time.isoformat()}
            }
        ]
        
        for query in queries_to_try:
            try:
                events = list(self.events_collection.find(query).sort("event_timestamp", 1))
                if events:
                    experiment_events = events
                    break
            except Exception as e:
                logger.warning(f"Experiment query failed: {e}")
                continue
        
        # Parse and validate timestamps
        valid_experiments = []
        for event in experiment_events:
            event_time = self.analyzer._parse_timestamp_utc(event.get("event_timestamp"))
            if event_time and start_time <= event_time <= end_time:
                experiment_id = self.analyzer._extract_experiment_id(event)
                if experiment_id:
                    valid_experiments.append({
                        "experiment_id": experiment_id,
                        "event_timestamp": event_time,
                        "event_data": event.get("event_data", {})
                    })
        
        return valid_experiments

    def _find_best_session_for_period(
        self, 
        session_details: List[Dict], 
        period_start: datetime, 
        period_end: datetime
    ) -> Optional[Dict]:
        """Find the session with the most overlap with the given period."""
        
        best_session = None
        best_overlap = 0
        
        for session in session_details:
            if "error" in session:
                continue
                
            try:
                session_start = datetime.fromisoformat(session["start_time"].replace('Z', '+00:00')).replace(tzinfo=None)
                session_end_str = session.get("end_time")
                if session_end_str:
                    session_end = datetime.fromisoformat(session_end_str.replace('Z', '+00:00')).replace(tzinfo=None)
                else:
                    session_end = period_end
                
                # Calculate overlap
                overlap_start = max(period_start, session_start)
                overlap_end = min(period_end, session_end)
                
                if overlap_start < overlap_end:
                    overlap_duration = (overlap_end - overlap_start).total_seconds()
                    if overlap_duration > best_overlap:
                        best_overlap = overlap_duration
                        best_session = session.copy()
                        
            except Exception as e:
                logger.warning(f"Error calculating session overlap: {e}")
                continue
        
        return best_session

    def _recalculate_overall_summary_for_daily(
        self, 
        session_details: List[Dict], 
        actual_experiment_count: int
    ) -> Dict[str, Any]:
        """Recalculate summary with correct experiment count but keeping original runtime."""
        
        # Calculate runtime from session durations (consistent with weekly/monthly)
        total_runtime_hours = sum(s.get("duration_hours", 0) for s in session_details)
        total_active_time_hours = sum(s.get("active_time_hours", 0) for s in session_details)
        
        # Calculate average utilization weighted by session duration
        total_duration = sum(s.get("duration_hours", 0) for s in session_details)
        if total_duration > 0:
            weighted_utilization = sum(
                s.get("system_utilization_percent", 0) * s.get("duration_hours", 0) 
                for s in session_details
            ) / total_duration
        else:
            weighted_utilization = 0
        
        return {
            "total_sessions": len(session_details),
            "total_system_runtime_hours": total_runtime_hours,  # Keep original runtime
            "total_active_time_hours": total_active_time_hours,  # Keep original active time
            "average_system_utilization_percent": weighted_utilization,
            "total_experiments": actual_experiment_count,  # Use actual count
            "nodes_tracked": len(set().union(*(s.get("node_utilizations", {}).keys() for s in session_details))),
            "method": "daily_analysis_with_consistent_runtime_calculation"
        }

    def _find_best_active_workcell(
        self, 
        active_workcells: Dict[str, Dict], 
        bucket_start: datetime, 
        bucket_end: datetime
    ) -> Optional[Dict]:
        """Find the most likely active workcell for this time bucket."""
        
        candidates = []
        
        for workcell_id, workcell_info in active_workcells.items():
            workcell_start = workcell_info["start_time"]
            workcell_end = workcell_info["end_time"]
            
            # Check overlap with bucket
            overlap_start = max(bucket_start, workcell_start)
            overlap_end = min(bucket_end, workcell_end)
            
            if overlap_start < overlap_end:
                overlap_duration = (overlap_end - overlap_start).total_seconds()
                bucket_duration = (bucket_end - bucket_start).total_seconds()
                overlap_percentage = overlap_duration / bucket_duration
                
                candidates.append({
                    "workcell_info": workcell_info,
                    "overlap_percentage": overlap_percentage,
                    "overlap_duration_hours": overlap_duration / 3600
                })
        
        # Return the workcell with highest overlap
        if candidates:
            best_candidate = max(candidates, key=lambda x: x["overlap_percentage"])
            if best_candidate["overlap_percentage"] > 0.1:  # At least 10% overlap
                return best_candidate["workcell_info"]
        
        return None
    
    def _create_attributed_workcell_session(
        self, 
        workcell_info: Dict, 
        default_sessions: List[Dict], 
        bucket_start: datetime, 
        bucket_end: datetime
    ) -> Dict:
        """Create a new workcell session by attributing default sessions."""
        
        # Start with workcell info
        attributed_session = {
            "session_type": workcell_info["session_type"],
            "session_id": workcell_info["workcell_id"],
            "session_name": workcell_info["workcell_name"],
            "start_time": bucket_start.isoformat(),
            "end_time": bucket_end.isoformat(),
            "source": "session_attribution"
        }
        
        # Aggregate data from all default sessions
        total_experiments = sum(s.get("total_experiments", 0) for s in default_sessions)
        
        # Calculate timing
        duration_seconds = (bucket_end - bucket_start).total_seconds()
        
        # Use weighted average for utilization (by experiment count)
        total_exp_weight = sum(s.get("total_experiments", 0) for s in default_sessions)
        if total_exp_weight > 0:
            weighted_utilization = sum(
                s.get("system_utilization_percent", 0) * s.get("total_experiments", 0) 
                for s in default_sessions
            ) / total_exp_weight
        else:
            weighted_utilization = 0
        
        # Aggregate node utilizations
        aggregated_nodes = {}
        for session in default_sessions:
            for node_id, node_data in session.get("node_utilizations", {}).items():
                if node_id not in aggregated_nodes:
                    aggregated_nodes[node_id] = {
                        "node_id": node_id,
                        "node_name": node_data.get("node_name"),
                        "display_name": node_data.get("display_name"),
                        "utilization_percent": 0,
                        "busy_time_hours": 0,
                        "idle_time_hours": 0,
                        "timing": node_data.get("timing", {}),
                        "raw_hours": {"busy": 0, "idle": 0, "total": 0}
                    }
                
                # Sum up the hours
                aggregated_nodes[node_id]["busy_time_hours"] += node_data.get("busy_time_hours", 0)
                aggregated_nodes[node_id]["idle_time_hours"] += node_data.get("idle_time_hours", 0)
                
                # Update raw hours
                aggregated_nodes[node_id]["raw_hours"]["busy"] += node_data.get("raw_hours", {}).get("busy", 0)
                aggregated_nodes[node_id]["raw_hours"]["idle"] += node_data.get("raw_hours", {}).get("idle", 0)
                aggregated_nodes[node_id]["raw_hours"]["total"] += node_data.get("raw_hours", {}).get("total", 0)
        
        # Recalculate utilization percentages for nodes
        for node_data in aggregated_nodes.values():
            total_time = node_data["raw_hours"]["total"]
            busy_time = node_data["raw_hours"]["busy"]
            if total_time > 0:
                node_data["utilization_percent"] = round((busy_time / total_time) * 100, 1)
        
        # Update attributed session
        attributed_session.update({
            "timing": {
                "duration": self.analyzer._format_duration_readable(duration_seconds),
                "active_time": self.analyzer._format_duration_readable(duration_seconds * weighted_utilization / 100),
                "idle_time": self.analyzer._format_duration_readable(duration_seconds * (100 - weighted_utilization) / 100)
            },
            "system_utilization_percent": round(weighted_utilization, 1),
            "total_experiments": total_experiments,
            "experiment_details": [],
            "nodes_active": len(aggregated_nodes),
            "node_utilizations": aggregated_nodes,
            "raw_hours": {
                "duration": duration_seconds / 3600,
                "active": duration_seconds * weighted_utilization / (100 * 3600),
                "idle": duration_seconds * (100 - weighted_utilization) / (100 * 3600)
            },
            "duration_hours": duration_seconds / 3600,
            "active_time_hours": duration_seconds * weighted_utilization / (100 * 3600),
            "attribution_info": {
                "method": "active_workcell_attribution",
                "default_sessions_merged": len(default_sessions),
                "total_experiments_attributed": total_experiments
            }
        })
        
        return attributed_session
    
    def _merge_sessions(self, primary_session: Dict, secondary_session: Dict) -> Dict:
        """Merge a secondary session into a primary session."""
        
        # Aggregate experiments
        primary_session["total_experiments"] += secondary_session.get("total_experiments", 0)
        
        # Merge node utilizations (sum busy hours, recalculate percentages)
        primary_nodes = primary_session.get("node_utilizations", {})
        secondary_nodes = secondary_session.get("node_utilizations", {})
        
        for node_id, node_data in secondary_nodes.items():
            if node_id in primary_nodes:
                # Sum the hours
                primary_nodes[node_id]["busy_time_hours"] += node_data.get("busy_time_hours", 0)
                primary_nodes[node_id]["idle_time_hours"] += node_data.get("idle_time_hours", 0)
                
                # Update raw hours
                primary_nodes[node_id]["raw_hours"]["busy"] += node_data.get("raw_hours", {}).get("busy", 0)
                primary_nodes[node_id]["raw_hours"]["idle"] += node_data.get("raw_hours", {}).get("idle", 0)
                primary_nodes[node_id]["raw_hours"]["total"] += node_data.get("raw_hours", {}).get("total", 0)
            else:
                # Add new node
                primary_nodes[node_id] = node_data.copy()
        
        # Recalculate utilization percentages
        for node_data in primary_nodes.values():
            total_time = node_data["raw_hours"]["total"]
            busy_time = node_data["raw_hours"]["busy"]
            if total_time > 0:
                node_data["utilization_percent"] = round((busy_time / total_time) * 100, 1)
        
        # Update primary session
        primary_session["node_utilizations"] = primary_nodes
        primary_session["nodes_active"] = len(primary_nodes)
        
        # Recalculate system utilization (weighted by experiment count)
        primary_exp = primary_session.get("total_experiments", 1)
        secondary_exp = secondary_session.get("total_experiments", 0)
        total_exp = primary_exp + secondary_exp
        
        if total_exp > 0:
            primary_util = primary_session.get("system_utilization_percent", 0)
            secondary_util = secondary_session.get("system_utilization_percent", 0)
            
            weighted_util = ((primary_util * primary_exp) + (secondary_util * secondary_exp)) / total_exp
            primary_session["system_utilization_percent"] = round(weighted_util, 1)
        
        return primary_session
    
    def _recalculate_overall_summary(self, session_details: List[Dict]) -> Dict[str, Any]:
        """Recalculate overall summary from modified session details."""
        
        total_sessions = len(session_details)
        total_runtime = sum(s.get("duration_hours", 0) for s in session_details)
        total_active_time = sum(s.get("active_time_hours", 0) for s in session_details)
        total_experiments = sum(s.get("total_experiments", 0) for s in session_details)
        
        # Calculate average system utilization
        valid_sessions = [s for s in session_details if "error" not in s and s.get("total_experiments", 0) > 0]
        if valid_sessions:
            avg_utilization = sum(s.get("system_utilization_percent", 0) for s in valid_sessions) / len(valid_sessions)
        else:
            avg_utilization = 0
        
        # Aggregate node data
        node_summary = defaultdict(lambda: {
            "total_busy_time_hours": 0,
            "utilizations": [],
            "sessions_active": 0
        })
        
        for session in valid_sessions:
            for node_id, node_data in session.get("node_utilizations", {}).items():
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
    
    def _create_summary_report(
        self, 
        bucket_reports: List[Dict],
        start_time: datetime,
        end_time: datetime, 
        analysis_type: str,
        user_timezone: str
    ) -> Dict[str, Any]:
        """Create clean summary report format with experiment details included."""
        
        logger.info(f"Creating summary report from {len(bucket_reports)} bucket reports")
        
        # Aggregate data from bucket reports
        all_utilizations = []
        all_experiments = []
        all_runtime_hours = []
        all_active_time_hours = []
        
        # Node and workcell aggregation
        node_metrics = defaultdict(lambda: {
            "utilizations": [], 
            "busy_hours": 0, 
            "time_series": []
        })
        
        workcell_metrics = defaultdict(lambda: {
            "utilizations": [], 
            "experiments": [], 
            "runtime_hours": [], 
            "time_series": [],
            "active_time_hours": []
        })
        
        time_series_points = []
        
        # Track what IDs are actually nodes vs workcells
        actual_node_ids = set()
        actual_workcell_ids = set()
        
        # Collect experiment details across all buckets
        all_experiment_details = []
        
        for bucket_report in bucket_reports:
            if "error" in bucket_report:
                continue
                
            overall_summary = bucket_report.get("overall_summary", {})
            session_details = bucket_report.get("session_details", [])
            time_bucket = bucket_report.get("time_bucket", {})
            
            # Get period info for better labeling
            period_info = time_bucket.get("period_info", {
                "type": "period", 
                "display": time_bucket.get("user_date", ""),
                "short": time_bucket.get("user_date", "")
            })
            
            # System metrics
            avg_util = overall_summary.get("average_system_utilization_percent", 0)
            total_exp = overall_summary.get("total_experiments", 0)
            total_runtime = overall_summary.get("total_system_runtime_hours", 0)
            total_active_time = overall_summary.get("total_active_time_hours", 0)
            
            # Only include periods with activity for utilization calculation
            if total_exp > 0:
                all_utilizations.append(avg_util)
                all_experiments.append(total_exp)
            
            # Always include runtime
            all_runtime_hours.append(total_runtime)
            all_active_time_hours.append(total_active_time)
            
            # Collect experiment details from sessions
            for session in session_details:
                experiment_details = session.get("experiment_details", [])
                for exp in experiment_details:
                    # Avoid duplicates by checking experiment_id
                    if not any(existing.get("experiment_id") == exp.get("experiment_id") for existing in all_experiment_details):
                        all_experiment_details.append(exp)
            
            # Process sessions for workcell and node data
            for session in session_details:
                session_id = session.get("session_id")
                session_type = session.get("session_type", "")
                
                # Track workcells
                if session_type in ["workcell", "lab"] and session_id:
                    actual_workcell_ids.add(session_id)
                    
                    session_util = session.get("system_utilization_percent", 0)
                    session_exp = session.get("total_experiments", 0)
                    session_runtime = session.get("duration_hours", 0)
                    session_active_time = session.get("active_time_hours", 0)
                    
                    workcell_metrics[session_id]["utilizations"].append(session_util)
                    workcell_metrics[session_id]["experiments"].append(session_exp)
                    workcell_metrics[session_id]["runtime_hours"].append(session_runtime)
                    workcell_metrics[session_id]["active_time_hours"].append(session_active_time)
                    
                    # Time series for workcells
                    if session_runtime > 0:
                        attribution_info = session.get("attribution_info")
                        workcell_metrics[session_id]["time_series"].append({
                            "period_number": time_bucket.get("bucket_index", 0) + 1,
                            "period_type": period_info.get("type", "period"),
                            "period_display": period_info.get("display", ""),
                            "date": time_bucket.get("user_date", ""),
                            "utilization": session_util,
                            "experiments": session_exp,
                            "runtime_hours": session_runtime,
                            "active_time_hours": session_active_time,
                            "attributed": bool(attribution_info)
                        })
                
                # Extract node data from sessions
                node_utilizations = session.get("node_utilizations", {})
                
                for node_id, node_data in node_utilizations.items():
                    # Skip if this ID is actually a workcell
                    if node_id in actual_workcell_ids:
                        continue
                    
                    # Verify this is actually a node
                    node_name = self.analyzer._resolve_node_name(node_id)
                    if not node_name:
                        continue
                    
                    actual_node_ids.add(node_id)
                    
                    utilization = node_data.get("utilization_percent", 0)
                    busy_hours = node_data.get("busy_time_hours", 0)
                    
                    node_metrics[node_id]["utilizations"].append(utilization)
                    node_metrics[node_id]["busy_hours"] += busy_hours
                    
                    # Time series for nodes
                    node_metrics[node_id]["time_series"].append({
                        "period_number": time_bucket.get("bucket_index", 0) + 1,
                        "period_type": period_info.get("type", "period"),
                        "period_display": period_info.get("display", ""),
                        "date": time_bucket.get("user_date", ""),
                        "utilization": utilization,
                        "busy_hours": busy_hours
                    })
            
            # System time series
            time_series_points.append({
                "period_number": time_bucket.get("bucket_index", 0) + 1,
                "period_type": period_info.get("type", "period"),
                "period_display": period_info.get("display", ""),
                "date": time_bucket.get("user_date", ""),
                "start_time": time_bucket.get("user_start_time", ""),
                "start_time_utc": time_bucket.get("start_time", ""),
                "utilization": avg_util,
                "experiments": total_exp,
                "runtime_hours": total_runtime,
                "active_time_hours": total_active_time
            })
        
        # Get complete experiment information from database
        complete_experiment_details = self._get_complete_experiment_details(
            all_experiment_details, start_time, end_time
        )
        
        # Create clean node summary
        node_summary_clean = {}
        for node_id, data in node_metrics.items():
            if node_id not in actual_node_ids:
                continue
                
            node_name = self.analyzer._resolve_node_name(node_id)
            
            # Calculate peak info with context
            peak_info = self._calculate_period_peak_info(data, analysis_type)
            
            node_summary_clean[node_id] = {
                "node_id": node_id,
                "node_name": node_name,
                "display_name": f"{node_name} ({node_id[-8:]})" if node_name else f"Node {node_id[-8:]}",
                "average_utilization": round(statistics.mean(data["utilizations"]) if data["utilizations"] else 0, 2),
                **peak_info,
                "total_busy_hours": round(data["busy_hours"], 2)
            }
        
        # Create clean workcell summary
        workcell_summary_clean = {}
        for workcell_id, data in workcell_metrics.items():
            if workcell_id not in actual_workcell_ids:
                continue
                
            workcell_name = self._resolve_workcell_name(workcell_id)
            
            # Calculate peak info with context
            peak_info = self._calculate_period_peak_info(data, analysis_type)
            
            # Better display name
            if workcell_name.startswith("Workcell ") and workcell_id[-8:] in workcell_name:
                display_name = workcell_name
            else:
                display_name = f"{workcell_name} ({workcell_id[-8:]})"
            
            workcell_summary_clean[workcell_id] = {
                "workcell_id": workcell_id,
                "workcell_name": workcell_name,
                "display_name": display_name,
                "average_utilization": round(statistics.mean(data["utilizations"]) if data["utilizations"] else 0, 2),
                **peak_info,
                "total_experiments": sum(data["experiments"]),
                "total_runtime_hours": round(sum(data["runtime_hours"]), 2),
                "total_active_time_hours": round(sum(data["active_time_hours"]), 2)
            }
        
        # Calculate trends
        trends = self._calculate_trends_from_time_series(time_series_points)
        
        # Calculate system peak with context
        system_peak_info = self._calculate_period_peak_info({
            "utilizations": all_utilizations,
            "time_series": [point for point in time_series_points if point["utilization"] > 0]
        }, analysis_type)
        
        logger.info(f"Final summary: {len(node_summary_clean)} nodes, {len(workcell_summary_clean)} workcells")
        
        return {
            "summary_metadata": {
                "analysis_type": analysis_type,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "period_start": start_time.isoformat(),
                "period_end": end_time.isoformat(),
                "user_timezone": user_timezone,
                "total_periods": len(bucket_reports),
                "method": "session_based_analysis_with_experiment_details"
            },
            
            "key_metrics": {
                "average_utilization": round(statistics.mean(all_utilizations) if all_utilizations else 0, 2),
                **system_peak_info,
                "total_experiments": sum(all_experiments),
                "total_runtime_hours": round(sum(all_runtime_hours), 2),
                "total_active_time_hours": round(sum(all_active_time_hours), 2),
                "active_periods": len(all_utilizations),
                "total_periods": len(bucket_reports)
            },
            
            "node_summary": node_summary_clean,
            "workcell_summary": workcell_summary_clean,
            "trends": trends,
            
            "experiment_details": {
                "total_experiments": len(complete_experiment_details),
                "experiments": complete_experiment_details[:50]  # Limit to first 50 for CSV
            },
            
            "time_series": {
                "system": time_series_points,
                "nodes": {
                    node_id: node_data["time_series"] 
                    for node_id, node_data in node_metrics.items()
                    if node_id in actual_node_ids and node_data["time_series"]
                },
                "workcells": {
                    workcell_id: workcell_data["time_series"]
                    for workcell_id, workcell_data in workcell_metrics.items()
                    if workcell_id in actual_workcell_ids and workcell_data["time_series"]
                }
            }
        }
    
    def _get_complete_experiment_details(
        self, 
        experiment_list: List[Dict], 
        start_time: datetime, 
        end_time: datetime
    ) -> List[Dict]:
        """Get complete experiment details from the database."""
        
        complete_details = []
        
        # Get all experiment start and complete events in the timeframe
        experiment_events = {}
        
        # Query for experiment events
        queries_to_try = [
            {
                "event_type": {"$in": ["experiment_start", "experiment_complete", "EXPERIMENT_START", "EXPERIMENT_COMPLETE"]},
                "event_timestamp": {"$gte": start_time, "$lte": end_time}
            },
            {
                "event_type": {"$in": ["experiment_start", "experiment_complete", "EXPERIMENT_START", "EXPERIMENT_COMPLETE"]},
                "event_timestamp": {"$gte": start_time.isoformat(), "$lte": end_time.isoformat()}
            }
        ]
        
        for query in queries_to_try:
            try:
                events = list(self.events_collection.find(query).sort("event_timestamp", 1))
                if events:
                    for event in events:
                        event_time = self.analyzer._parse_timestamp_utc(event.get("event_timestamp"))
                        if event_time:
                            exp_id = self.analyzer._extract_experiment_id(event)
                            if exp_id:
                                if exp_id not in experiment_events:
                                    experiment_events[exp_id] = {}
                                
                                event_type = str(event.get("event_type", "")).lower()
                                if "start" in event_type:
                                    experiment_events[exp_id]["start"] = {
                                        "timestamp": event_time,
                                        "event_data": event.get("event_data", {})
                                    }
                                elif "complete" in event_type:
                                    experiment_events[exp_id]["complete"] = {
                                        "timestamp": event_time,
                                        "event_data": event.get("event_data", {})
                                    }
                    break
            except Exception as e:
                logger.warning(f"Error querying experiment events: {e}")
                continue
        
        # Build complete experiment details
        for exp_id, events in experiment_events.items():
            start_event = events.get("start")
            complete_event = events.get("complete")
            
            if start_event:
                start_time_exp = start_event["timestamp"]
                start_data = start_event["event_data"]
                
                # Get experiment name
                exp_name = "Unknown Experiment"
                if isinstance(start_data.get("experiment"), dict):
                    exp_design = start_data["experiment"].get("experiment_design", {})
                    exp_name = exp_design.get("experiment_name", "Unknown Experiment")
                
                # Calculate duration and status
                if complete_event:
                    end_time_exp = complete_event["timestamp"]
                    duration_seconds = (end_time_exp - start_time_exp).total_seconds()
                    duration_hours = duration_seconds / 3600
                    
                    # Format duration display
                    if duration_seconds < 60:
                        duration_display = f"{duration_seconds:.1f} seconds"
                    elif duration_seconds < 3600:
                        duration_display = f"{duration_seconds/60:.1f} minutes"
                    else:
                        duration_display = f"{duration_hours:.1f} hours"
                    
                    status = complete_event["event_data"].get("status", "completed")
                    end_time_str = end_time_exp.isoformat()
                else:
                    # No complete event found
                    end_time_str = None
                    duration_hours = None
                    duration_display = "Ongoing"
                    status = "in_progress"
                
                complete_details.append({
                    "experiment_id": exp_id,
                    "experiment_name": exp_name,
                    "start_time": start_time_exp.isoformat(),
                    "end_time": end_time_str,
                    "status": status,
                    "duration_hours": duration_hours,
                    "duration_display": duration_display
                })
        
        # Sort by start time
        complete_details.sort(key=lambda x: x["start_time"])
        
        return complete_details
     
    def _calculate_period_peak_info(self, data: Dict, analysis_type: str) -> Dict[str, Any]:
        """Calculate peak utilization info between periods."""
        if not data["utilizations"]:
            return {
                "peak_utilization": 0,
                "peak_period": None,
                "peak_context": "No active periods"
            }
        
        max_utilization = max(data["utilizations"])
        max_index = data["utilizations"].index(max_utilization)
        
        # Get the time series entry for this peak
        if max_index < len(data["time_series"]):
            peak_period_info = data["time_series"][max_index]
            
            period_display = peak_period_info.get("period_display", "Unknown")
            
            # Create contextual message based on analysis type
            if analysis_type == "daily":
                peak_context = f"Peak utilization on {period_display}"
            elif analysis_type == "weekly":
                peak_context = f"Peak utilization during {period_display}"
            elif analysis_type in ["monthly", "mounthly"]:
                peak_context = f"Peak utilization in {period_display}"
            else:
                peak_context = f"Peak utilization in {period_display}"
                
            return {
                "peak_utilization": round(max_utilization, 2),
                "peak_period": period_display,
                "peak_context": peak_context
            }
        else:
            return {
                "peak_utilization": round(max_utilization, 2),
                "peak_period": "Unknown",
                "peak_context": f"Peak utilization: {round(max_utilization, 2)}%"
            }
    
    def _calculate_trends_from_time_series(self, time_series_points: List[Dict]) -> Dict[str, Any]:
        """Calculate trends from time series data."""
        
        if len(time_series_points) < 2:
            return {
                "utilization_trend": {"direction": "insufficient_data", "change_percent": 0},
                "experiment_trend": {"direction": "insufficient_data", "change_percent": 0}
            }
        
        # Extract active periods only
        active_points = [point for point in time_series_points if point["utilization"] > 0]
        
        if len(active_points) < 2:
            return {
                "utilization_trend": {"direction": "insufficient_data", "change_percent": 0},
                "experiment_trend": {"direction": "insufficient_data", "change_percent": 0}
            }
        
        # Calculate trends
        utilizations = [point["utilization"] for point in active_points]
        experiments = [point["experiments"] for point in active_points]
        
        util_first, util_last = utilizations[0], utilizations[-1]
        exp_first, exp_last = experiments[0], experiments[-1]
        
        # Utilization trend
        if util_first == 0:
            util_change_percent, util_direction = 0, "stable"
        else:
            util_change_percent = ((util_last - util_first) / util_first) * 100
            util_direction = "increasing" if util_change_percent > 5 else "decreasing" if util_change_percent < -5 else "stable"
        
        # Experiment trend  
        if exp_first == 0:
            exp_change_percent, exp_direction = 0, "stable"
        else:
            exp_change_percent = ((exp_last - exp_first) / exp_first) * 100
            exp_direction = "increasing" if exp_change_percent > 5 else "decreasing" if exp_change_percent < -5 else "stable"
        
        return {
            "utilization_trend": {
                "direction": util_direction,
                "change_percent": round(util_change_percent, 2),
                "first_value": round(util_first, 2),
                "last_value": round(util_last, 2),
                "active_periods_analyzed": len(active_points)
            },
            "experiment_trend": {
                "direction": exp_direction,
                "change_percent": round(exp_change_percent, 2),
                "first_value": exp_first,
                "last_value": exp_last,
                "active_periods_analyzed": len(active_points)
            }
        }
    
    def _resolve_workcell_name(self, workcell_id: str) -> str:
        """Resolve human-readable name for a workcell with multiple strategies."""
        
        # Look in events collection directly
        try:
            workcell_events = list(self.events_collection.find({
                "event_type": {"$in": ["workcell_start", "lab_start"]},
                "$or": [
                    {"source.workcell_id": workcell_id},
                    {"source.manager_id": workcell_id},
                    {"event_data.workcell_id": workcell_id}
                ]
            }).limit(3))
            
            for event in workcell_events:
                event_data = event.get("event_data", {})
                name_candidates = [
                    event_data.get("name"),
                    event_data.get("workcell_name"),
                    event_data.get("lab_name"),
                    event_data.get("display_name")
                ]
                
                for name in name_candidates:
                    if name and isinstance(name, str) and name.strip() and not name.startswith("Workcell "):
                        return name.strip()
                        
        except Exception as e:
            logger.warning(f"Error looking up workcell name in events: {e}")
        
        # Fallback to generated name
        return f"Workcell {workcell_id[-8:]}"
    
    def _create_time_buckets_user_timezone(self, start_time, end_time, bucket_hours, user_timezone):
        """Create time buckets aligned to user timezone."""
        tz_handler = TimezoneHandler(user_timezone)
        buckets = []
        
        current_user_time = tz_handler.utc_to_user_time(start_time)
        end_user_time = tz_handler.utc_to_user_time(end_time)
        
        # Handle monthly as special case
        if bucket_hours == "monthly" or bucket_hours == 720:
            current_user_time = current_user_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            while current_user_time < end_user_time:
                if current_user_time.month == 12:
                    next_month = current_user_time.replace(year=current_user_time.year + 1, month=1)
                else:
                    next_month = current_user_time.replace(month=current_user_time.month + 1)
                
                bucket_end_user = min(next_month, end_user_time)
                
                bucket_start_utc = tz_handler.user_to_utc_time(current_user_time)
                bucket_end_utc = tz_handler.user_to_utc_time(bucket_end_user)
                
                period_info = {
                    "type": "month", 
                    "display": current_user_time.strftime("%B %Y"),
                    "short": current_user_time.strftime("%b %Y")
                }
                
                buckets.append({
                    'utc_times': (bucket_start_utc, bucket_end_utc),
                    'user_times': (current_user_time, bucket_end_user),
                    'period_info': period_info
                })
                
                current_user_time = next_month
                
        elif bucket_hours == 24:  # Daily buckets
            current_user_time = current_user_time.replace(hour=0, minute=0, second=0, microsecond=0)
            bucket_delta = timedelta(days=1)
            
            while current_user_time < end_user_time:
                bucket_end_user = min(current_user_time + bucket_delta, end_user_time)
                
                bucket_start_utc = tz_handler.user_to_utc_time(current_user_time)
                bucket_end_utc = tz_handler.user_to_utc_time(bucket_end_user)
                
                period_info = {
                    "type": "day",
                    "display": current_user_time.strftime("%Y-%m-%d"),
                    "short": current_user_time.strftime("%m-%d")
                }
                
                buckets.append({
                    'utc_times': (bucket_start_utc, bucket_end_utc),
                    'user_times': (current_user_time, bucket_end_user),
                    'period_info': period_info
                })
                
                current_user_time = bucket_end_user
            
        elif bucket_hours == 168:  # Weekly buckets
            days_since_monday = current_user_time.weekday()
            current_user_time = current_user_time.replace(hour=0, minute=0, second=0, microsecond=0)
            current_user_time -= timedelta(days=days_since_monday)
            bucket_delta = timedelta(weeks=1)
            
            while current_user_time < end_user_time:
                bucket_end_user = min(current_user_time + bucket_delta, end_user_time)
                
                bucket_start_utc = tz_handler.user_to_utc_time(current_user_time)
                bucket_end_utc = tz_handler.user_to_utc_time(bucket_end_user)
                
                period_info = {
                    "type": "week",
                    "display": f"Week of {current_user_time.strftime('%Y-%m-%d')}",
                    "short": f"Week {current_user_time.strftime('%m/%d')}"
                }
                
                buckets.append({
                    'utc_times': (bucket_start_utc, bucket_end_utc),
                    'user_times': (current_user_time, bucket_end_user),
                    'period_info': period_info
                })
                
                current_user_time = bucket_end_user
                
        else:  # Hourly or custom buckets
            bucket_delta = timedelta(hours=bucket_hours)
            
            while current_user_time < end_user_time:
                bucket_end_user = min(current_user_time + bucket_delta, end_user_time)
                
                bucket_start_utc = tz_handler.user_to_utc_time(current_user_time)
                bucket_end_utc = tz_handler.user_to_utc_time(bucket_end_user)
                
                period_info = {
                    "type": "period",
                    "display": current_user_time.strftime("%Y-%m-%d %H:%M"),
                    "short": current_user_time.strftime("%m/%d %H:%M")
                }
                
                buckets.append({
                    'utc_times': (bucket_start_utc, bucket_end_utc),
                    'user_times': (current_user_time, bucket_end_user),
                    'period_info': period_info
                })
                
                current_user_time = bucket_end_user
        
        return buckets


class TimezoneHandler:
    """Handle timezone conversions."""
    
    def __init__(self, user_timezone: str = "America/Chicago"):
        self.user_tz = pytz.timezone(user_timezone)
        self.utc_tz = pytz.UTC
    
    def utc_to_user_time(self, utc_datetime: datetime) -> datetime:
        if utc_datetime.tzinfo is None:
            utc_datetime = self.utc_tz.localize(utc_datetime)
        return utc_datetime.astimezone(self.user_tz)
    
    def user_to_utc_time(self, user_datetime: datetime) -> datetime:
        if user_datetime.tzinfo is None:
            user_datetime = self.user_tz.localize(user_datetime)
        return user_datetime.astimezone(self.utc_tz).replace(tzinfo=None)
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
        """Generate summary utilization report with FIXED error handling."""
        
        # Store analysis type for use in attribution logic
        self._current_analysis_type = analysis_type
        
        logger.info(f"Generating {analysis_type} summary report for timezone {user_timezone}")
        
        try:
            # Determine analysis timeframe with better error handling
            analysis_start, analysis_end = self.analyzer._determine_analysis_period(start_time, end_time)
            
            # Validate the returned times
            if not analysis_start or not analysis_end:
                logger.error("Failed to determine valid analysis period")
                return {
                    "error": "Could not determine analysis time period",
                    "summary_metadata": {
                        "analysis_type": analysis_type,
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                        "error_occurred": True,
                        "error_details": "Analysis period determination failed"
                    }
                }
            
            if analysis_start >= analysis_end:
                logger.error(f"Invalid analysis period: start ({analysis_start}) >= end ({analysis_end})")
                return {
                    "error": "Invalid analysis time period: start time must be before end time",
                    "summary_metadata": {
                        "analysis_type": analysis_type,
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                        "error_occurred": True,
                        "error_details": f"Start time {analysis_start} >= end time {analysis_end}"
                    }
                }
            
            logger.info(f"Analysis period determined: {analysis_start} to {analysis_end}")
            
        except Exception as e:
            logger.error(f"Exception in analysis period determination: {e}")
            return {
                "error": f"Failed to determine analysis period: {str(e)}",
                "summary_metadata": {
                    "analysis_type": analysis_type,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "error_occurred": True,
                    "error_details": str(e)
                }
            }
        
        # Get ALL sessions for the entire period ONCE - with safety check
        try:
            all_sessions = self.analyzer._find_system_sessions(analysis_start, analysis_end)
            if all_sessions is None:
                all_sessions = []
            logger.info(f"Found {len(all_sessions)} sessions")
        except Exception as e:
            logger.error(f"Error finding sessions: {e}")
            all_sessions = []
        
        # Determine bucket type from analysis_type
        if analysis_type == "hourly":
            time_bucket_hours = 1
        elif analysis_type == "daily":
            time_bucket_hours = 24
        elif analysis_type == "weekly":
            time_bucket_hours = 168
        elif analysis_type == "monthly":
            time_bucket_hours = "monthly"
        else:
            time_bucket_hours = 24
        
        # Create time buckets with safety check
        try:
            time_buckets = self._create_time_buckets_user_timezone(
                analysis_start, analysis_end, time_bucket_hours, user_timezone
            )
            if time_buckets is None:
                time_buckets = []
            logger.info(f"Created {len(time_buckets)} time buckets")
        except Exception as e:
            logger.error(f"Error creating time buckets: {e}")
            return {
                "error": f"Failed to create time buckets: {str(e)}",
                "summary_metadata": {
                    "analysis_type": analysis_type,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "period_start": analysis_start.isoformat() if analysis_start else None,
                    "period_end": analysis_end.isoformat() if analysis_end else None,
                    "error_occurred": True,
                    "error_details": str(e)
                }
            }
        
        # FIXED: For daily analysis, distribute sessions across buckets
        bucket_reports = []
        try:
            if analysis_type == 'daily':
                bucket_reports = self._create_daily_buckets_from_sessions(
                    time_buckets, all_sessions, analysis_start, analysis_end
                )
            elif analysis_type == 'monthly':
                # FIXED: Special handling for monthly to avoid utilization dilution
                bucket_reports = self._create_monthly_buckets_from_sessions(
                    time_buckets, all_sessions, analysis_start, analysis_end
                )
            elif analysis_type == 'weekly':
                # Weekly logic
                bucket_reports = []
                for i, bucket_info in enumerate(time_buckets):
                    if isinstance(bucket_info, dict):
                        bucket_start, bucket_end = bucket_info['utc_times']
                        period_info = bucket_info.get('period_info', {})
                    else:
                        bucket_start, bucket_end = bucket_info
                        period_info = {"type": "period", "display": bucket_start.strftime("%Y-%m-%d")}
                    
                    bucket_report = self._generate_weekly_bucket_report(
                        bucket_start, bucket_end, all_sessions, i, period_info
                    )
                    bucket_reports.append(bucket_report)
            else:
                # Fallback for other analysis types
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
                    
                    # Add time bucket info
                    bucket_report["time_bucket"] = {
                        "bucket_index": i,
                        "start_time": bucket_start.isoformat(),
                        "end_time": bucket_end.isoformat(),
                        "duration_hours": (bucket_end - bucket_start).total_seconds() / 3600,
                        "period_info": period_info
                    }
                    
                    bucket_reports.append(bucket_report)
                    
        except Exception as e:
            logger.error(f"Error creating bucket reports: {e}")
            return {
                "error": f"Failed to create bucket reports: {str(e)}",
                "summary_metadata": {
                    "analysis_type": analysis_type,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "period_start": analysis_start.isoformat() if analysis_start else None,
                    "period_end": analysis_end.isoformat() if analysis_end else None,
                    "error_occurred": True,
                    "error_details": str(e)
                }
            }
        
        # Create summary report with safety check
        try:
            return self._create_summary_report(bucket_reports, analysis_start, analysis_end, analysis_type, user_timezone)
        except Exception as e:
            logger.error(f"Error creating summary report: {e}")
            return {
                "error": f"Failed to generate summary: {str(e)}",
                "summary_metadata": {
                    "analysis_type": analysis_type,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "period_start": analysis_start.isoformat() if analysis_start else None,
                    "period_end": analysis_end.isoformat() if analysis_end else None,
                    "error_occurred": True,
                    "error_details": str(e)
                }
            }
        
    def _generate_weekly_bucket_report(
        self,
        bucket_start: datetime,
        bucket_end: datetime, 
        all_sessions: List[Dict],
        bucket_index: int,
        period_info: Dict
    ) -> Dict[str, Any]:
        """Generate bucket report for weekly analysis with proper runtime calculation."""
        
        try:
            # Get experiments that actually occurred within this week
            actual_experiments_in_period = self._get_experiments_in_time_period(
                bucket_start, bucket_end
            )
            
            # Ensure we have a valid list
            if not actual_experiments_in_period:
                actual_experiments_in_period = []
            
            # Find sessions that overlap with this week and calculate proper runtime
            week_runtime = 0
            week_active_time = 0
            week_experiments = len(actual_experiments_in_period)
            week_utilization = 0
            week_sessions = []
            
            # Track all nodes that were active during this week
            week_node_utilizations = {}
            
            # Ensure all_sessions is valid
            if not all_sessions:
                all_sessions = []
            
            for session in all_sessions:
                if not session or not isinstance(session, dict):
                    continue
                    
                session_start = session.get("start_time")
                session_end = session.get("end_time")
                
                if not session_start or not session_end:
                    continue
                
                # Calculate overlap between session and this week
                overlap_start = max(bucket_start, session_start)
                overlap_end = min(bucket_end, session_end)
                
                if overlap_start < overlap_end:
                    # There's overlap - calculate actual runtime for this week
                    overlap_seconds = (overlap_end - overlap_start).total_seconds()
                    overlap_hours = overlap_seconds / 3600
                    
                    # For weekly analysis: ONLY count actual overlapping runtime, not full week
                    week_runtime += overlap_hours
                    
                    # Calculate proportional active time based on original session utilization
                    session_duration_seconds = session.get("duration_seconds", 0)
                    if session_duration_seconds > 0:
                        try:
                            # Get the session utilization percentage from a generated session report
                            session_report = self.analyzer._analyze_session_utilization(session)
                            if session_report and isinstance(session_report, dict):
                                session_util = session_report.get("system_utilization_percent", 0)
                                
                                # Calculate active time based on overlap and utilization
                                week_active_time += overlap_hours * (session_util / 100)
                                
                                # Weight utilization by runtime
                                week_utilization += session_util * overlap_hours
                                
                                # Include node utilizations from this session
                                session_nodes = session_report.get("node_utilizations", {})
                                if session_nodes and isinstance(session_nodes, dict):
                                    for node_id, node_data in session_nodes.items():
                                        if not node_data or not isinstance(node_data, dict):
                                            continue
                                            
                                        if node_id not in week_node_utilizations:
                                            week_node_utilizations[node_id] = {
                                                "utilizations": [],
                                                "busy_hours": 0,
                                                "node_info": node_data
                                            }
                                        
                                        # Add proportional busy time for this week
                                        proportion = overlap_hours / (session_duration_seconds / 3600)
                                        proportional_busy_time = node_data.get("busy_time_hours", 0) * proportion
                                        week_node_utilizations[node_id]["busy_hours"] += proportional_busy_time
                                        week_node_utilizations[node_id]["utilizations"].append(
                                            node_data.get("utilization_percent", 0)
                                        )
                            else:
                                session_util = 0
                        except Exception as e:
                            logger.error(f"Error analyzing session for weekly report: {e}")
                            session_util = 0
                            session_report = {}
                    else:
                        session_util = 0
                        session_report = {}
                    
                    # Count experiments that occurred during this session's overlap
                    session_experiments = []
                    if actual_experiments_in_period:
                        session_experiments = [
                            exp for exp in actual_experiments_in_period
                            if (exp and isinstance(exp, dict) and 
                                exp.get("event_timestamp") and
                                overlap_start <= exp["event_timestamp"] <= overlap_end)
                        ]
                    
                    # Create a session fragment for this week
                    week_session = {
                        "session_type": session.get("session_type", "unknown"),
                        "session_id": session.get("session_id", "unknown"),
                        "session_name": session.get("session_name", "Unknown Session"),
                        "start_time": overlap_start.isoformat(),
                        "end_time": overlap_end.isoformat(),
                        "duration_hours": overlap_hours,
                        "active_time_hours": overlap_hours * (session_util / 100),
                        "total_experiments": len(session_experiments),
                        "system_utilization_percent": session_util,
                        "node_utilizations": session_report.get("node_utilizations", {}),
                        "experiment_details": [
                            {
                                "experiment_id": exp.get("experiment_id", ""),
                                "experiment_name": self.analyzer._resolve_experiment_name(exp.get("experiment_id", "")),
                                "display_name": f"Experiment {exp.get('experiment_id', '')[-8:]}"
                            }
                            for exp in session_experiments
                            if exp and exp.get("experiment_id")
                        ],
                        "attribution_method": "weekly_session_overlap"
                    }
                    
                    week_sessions.append(week_session)
            
            # Calculate weighted average utilization
            if week_runtime > 0:
                week_utilization = week_utilization / week_runtime
            
            # Process node utilizations for the week summary
            final_node_utilizations = {}
            for node_id, node_info in week_node_utilizations.items():
                if not node_info or not isinstance(node_info, dict):
                    continue
                    
                utilizations = node_info.get("utilizations", [])
                avg_utilization = statistics.mean(utilizations) if utilizations else 0
                
                base_info = node_info.get("node_info", {})
                if not isinstance(base_info, dict):
                    base_info = {}
                    
                final_node_utilizations[node_id] = {
                    "node_id": node_id,
                    "node_name": base_info.get("node_name", ""),
                    "display_name": base_info.get("display_name", f"Node {node_id[-8:]}"),
                    "utilization_percent": round(avg_utilization, 1),
                    "busy_time_hours": round(node_info.get("busy_hours", 0), 3),
                    "timing": base_info.get("timing", {}),
                    "raw_hours": {
                        "busy": node_info.get("busy_hours", 0),
                        "idle": 0,  # Simplified for weekly summary
                        "total": week_runtime
                    }
                }
            
            # Create bucket report
            bucket_report = {
                "session_details": week_sessions,
                "overall_summary": {
                    "total_sessions": len(week_sessions),
                    "total_system_runtime_hours": week_runtime,
                    "total_active_time_hours": week_active_time,
                    "average_system_utilization_percent": week_utilization,
                    "total_experiments": week_experiments,
                    "nodes_tracked": len(final_node_utilizations),
                    "node_summary": {
                        node_id: {
                            "average_utilization_percent": node_data["utilization_percent"],
                            "total_busy_time_hours": node_data["busy_time_hours"],
                            "sessions_active": 1
                        }
                        for node_id, node_data in final_node_utilizations.items()
                    },
                    "method": "weekly_proper_runtime_calculation"
                },
                "time_bucket": {
                    "bucket_index": bucket_index,
                    "start_time": bucket_start.isoformat(),
                    "end_time": bucket_end.isoformat(),
                    "duration_hours": (bucket_end - bucket_start).total_seconds() / 3600,
                    "period_info": period_info
                }
            }
            
            return bucket_report
            
        except Exception as e:
            logger.error(f"Error in weekly bucket report generation: {e}")
            # Return a minimal valid report
            return {
                "session_details": [],
                "overall_summary": {
                    "total_sessions": 0,
                    "total_system_runtime_hours": 0,
                    "total_active_time_hours": 0,
                    "average_system_utilization_percent": 0,
                    "total_experiments": 0,
                    "nodes_tracked": 0,
                    "node_summary": {},
                    "method": "weekly_error_fallback"
                },
                "time_bucket": {
                    "bucket_index": bucket_index,
                    "start_time": bucket_start.isoformat(),
                    "end_time": bucket_end.isoformat(),
                    "duration_hours": (bucket_end - bucket_start).total_seconds() / 3600,
                    "period_info": period_info
                },
                "error": f"Weekly bucket generation failed: {str(e)}"
            }
    
    def _create_daily_buckets_from_sessions(
        self,
        time_buckets: List,
        sessions: List[Dict],
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict]:
        """Create daily bucket reports with FIXED session attribution and node summary."""
        
        bucket_reports = []
        
        # Safety checks
        if not time_buckets:
            logger.warning("No time buckets provided for daily analysis")
            return []
        
        if not sessions:
            logger.warning("No sessions provided for daily analysis")
            sessions = []
        
        # ADDED: Filter sessions to only include those that overlap with analysis period
        filtered_sessions = []
        for session in sessions:
            if not session or not isinstance(session, dict):
                continue
                
            session_start = session.get("start_time")
            session_end = session.get("end_time")
            
            if not session_start or not session_end:
                continue
            
            # Check if session overlaps with analysis period
            if session_end >= start_time and session_start <= end_time:
                filtered_sessions.append(session)
        
        
        for i, bucket_info in enumerate(time_buckets):
            try:
                if isinstance(bucket_info, dict):
                    bucket_start, bucket_end = bucket_info['utc_times']
                    user_start, user_end = bucket_info['user_times']
                    period_info = bucket_info.get('period_info', {})
                else:
                    bucket_start, bucket_end = bucket_info
                    user_start, user_end = bucket_start, bucket_end
                    period_info = {"type": "period", "display": user_start.strftime("%Y-%m-%d")}
                
                # ADDED: Validate bucket times are within analysis period
                if bucket_start < start_time or bucket_end > end_time:
                    logger.warning(f"Daily bucket {i} extends outside analysis period, clipping to bounds")
                    bucket_start = max(bucket_start, start_time)
                    bucket_end = min(bucket_end, end_time)
                
                # Safety checks for bucket times
                if not bucket_start or not bucket_end or bucket_start >= bucket_end:
                    logger.warning(f"Invalid bucket times for daily bucket {i}")
                    continue
                
                # Get experiments that actually occurred within this day
                try:
                    actual_experiments_in_period = self._get_experiments_in_time_period(
                        bucket_start, bucket_end
                    )
                    if actual_experiments_in_period is None:
                        actual_experiments_in_period = []
                except Exception as e:
                    logger.error(f"Error getting experiments for daily bucket {i}: {e}")
                    actual_experiments_in_period = []
                
                # Find sessions that overlap with this day and calculate proportional data
                day_sessions = []
                total_day_runtime = 0
                total_day_active_time = 0
                day_experiments = len(actual_experiments_in_period) if actual_experiments_in_period else 0
                
                # Track nodes across all sessions for this day
                day_node_utilizations = {}
                
                # CHANGED: Use filtered_sessions instead of sessions
                for session in filtered_sessions:
                    try:
                        session_start = session.get("start_time")
                        session_end = session.get("end_time")
                        
                        if not session_start or not session_end:
                            continue
                        
                        # Calculate overlap between session and this day
                        overlap_start = max(bucket_start, session_start)
                        overlap_end = min(bucket_end, session_end)
                        
                        if overlap_start < overlap_end:
                            # There's overlap - calculate proportional runtime
                            overlap_seconds = (overlap_end - overlap_start).total_seconds()
                            overlap_hours = overlap_seconds / 3600
                            
                            # CRITICAL FIX: Get the actual session analysis with proper utilization
                            try:
                                session_report = self.analyzer._analyze_session_utilization(session)
                                if not session_report or not isinstance(session_report, dict):
                                    session_report = {}
                                    
                                session_util = session_report.get("system_utilization_percent", 0) or 0
                                session_active_time = session_report.get("active_time_hours", 0) or 0
                                session_duration = session_report.get("duration_hours", 0) or 0
                                
                            except Exception as e:
                                logger.error(f"Error analyzing session for daily bucket: {e}")
                                session_util = 0
                                session_active_time = 0
                                session_duration = 0
                                session_report = {}
                            
                            # Calculate proportional active time for this day
                            if session_duration > 0:
                                proportion = overlap_hours / session_duration
                                proportional_active_time = session_active_time * proportion
                            else:
                                proportional_active_time = overlap_hours * (session_util / 100)
                            
                            total_day_runtime += overlap_hours
                            total_day_active_time += proportional_active_time
                            
                            # CRITICAL FIX: Include node utilizations from the session
                            session_nodes = session_report.get("node_utilizations", {})
                            if session_nodes and isinstance(session_nodes, dict):
                                for node_id, node_data in session_nodes.items():
                                    if not node_data or not isinstance(node_data, dict):
                                        continue
                                        
                                    if node_id not in day_node_utilizations:
                                        day_node_utilizations[node_id] = {
                                            "utilizations": [],
                                            "busy_hours": 0,
                                            "node_info": node_data
                                        }
                                    
                                    # Add proportional busy time for this day
                                    try:
                                        if session_duration > 0:
                                            proportion = overlap_hours / session_duration
                                            node_busy_hours = node_data.get("busy_time_hours", 0) or 0
                                            proportional_busy_time = node_busy_hours * proportion
                                        else:
                                            proportional_busy_time = 0
                                        
                                        day_node_utilizations[node_id]["busy_hours"] += proportional_busy_time
                                        
                                        node_util_percent = node_data.get("utilization_percent", 0) or 0
                                        day_node_utilizations[node_id]["utilizations"].append(node_util_percent)
                                        
                                    except Exception as e:
                                        logger.error(f"Error processing node {node_id} for daily bucket: {e}")
                                        continue
                            
                            # Count experiments that occurred during this session's overlap
                            session_experiments = []
                            if actual_experiments_in_period:
                                try:
                                    session_experiments = [
                                        exp for exp in actual_experiments_in_period
                                        if (exp and isinstance(exp, dict) and 
                                            exp.get("event_timestamp") and
                                            overlap_start <= exp["event_timestamp"] <= overlap_end)
                                    ]
                                except Exception as e:
                                    logger.error(f"Error filtering session experiments: {e}")
                                    session_experiments = []
                            
                            # Create a session fragment for this day
                            day_session = {
                                "session_type": session.get("session_type", "unknown"),
                                "session_id": session.get("session_id", "unknown"),
                                "session_name": session.get("session_name", "Unknown Session"),
                                "start_time": overlap_start.isoformat(),
                                "end_time": overlap_end.isoformat(),
                                "duration_hours": overlap_hours,
                                "active_time_hours": proportional_active_time,
                                "total_experiments": len(session_experiments) if session_experiments else 0,
                                "system_utilization_percent": session_util,
                                "node_utilizations": session_nodes if session_nodes else {},
                                "experiment_details": [
                                    {
                                        "experiment_id": exp.get("experiment_id", ""),
                                        "experiment_name": self.analyzer._resolve_experiment_name(exp.get("experiment_id", "")),
                                        "display_name": f"Experiment {exp.get('experiment_id', '')[-8:]}"
                                    }
                                    for exp in (session_experiments if session_experiments else [])
                                    if exp and exp.get("experiment_id")
                                ],
                                "attribution_method": "daily_proportional_from_session_with_bounds_check"
                            }
                            
                            day_sessions.append(day_session)
                            
                    except Exception as e:
                        logger.error(f"Error processing session for daily bucket {i}: {e}")
                        continue
                
                # Process final node utilizations for this day
                final_node_utilizations = {}
                for node_id, node_info in day_node_utilizations.items():
                    try:
                        if not node_info or not isinstance(node_info, dict):
                            continue
                            
                        utilizations = node_info.get("utilizations", [])
                        if utilizations:
                            avg_utilization = statistics.mean(utilizations)
                        else:
                            avg_utilization = 0
                        
                        base_info = node_info.get("node_info", {})
                        if not isinstance(base_info, dict):
                            base_info = {}
                            
                        busy_hours = node_info.get("busy_hours", 0) or 0
                            
                        final_node_utilizations[node_id] = {
                            "node_id": node_id,
                            "node_name": base_info.get("node_name"),
                            "display_name": base_info.get("display_name"),
                            "utilization_percent": round(avg_utilization, 1),
                            "busy_time_hours": round(busy_hours, 3),
                            "timing": base_info.get("timing", {}),
                            "raw_hours": {
                                "busy": busy_hours,
                                "idle": max(0, total_day_runtime - busy_hours),
                                "total": total_day_runtime
                            }
                        }
                    except Exception as e:
                        logger.error(f"Error processing final node utilization for {node_id}: {e}")
                        continue
                
                # Calculate day utilization properly
                day_utilization = (total_day_active_time / total_day_runtime * 100) if total_day_runtime > 0 else 0
                
                bucket_report = {
                    "session_details": day_sessions,
                    "overall_summary": {
                        "total_sessions": len(day_sessions),
                        "total_system_runtime_hours": total_day_runtime,
                        "total_active_time_hours": total_day_active_time,
                        "average_system_utilization_percent": day_utilization,
                        "total_experiments": day_experiments,
                        "nodes_tracked": len(final_node_utilizations),
                        "node_summary": {
                            node_id: {
                                "average_utilization_percent": node_data["utilization_percent"],
                                "total_busy_time_hours": node_data["busy_time_hours"],
                                "sessions_active": 1
                            }
                            for node_id, node_data in final_node_utilizations.items()
                        },
                        "method": "daily_with_bounds_validation_and_comprehensive_error_handling"
                    },
                    "time_bucket": {
                        "bucket_index": i,
                        "start_time": bucket_start.isoformat(),
                        "end_time": bucket_end.isoformat(),
                        "user_start_time": user_start.strftime("%Y-%m-%dT%H:%M:%S") if user_start else "",
                        "user_date": user_start.strftime("%Y-%m-%d") if user_start else "",
                        "duration_hours": (bucket_end - bucket_start).total_seconds() / 3600,
                        "period_info": period_info
                    }
                }
                
                bucket_reports.append(bucket_report)
                
            except Exception as e:
                logger.error(f"Error processing daily bucket {i}: {e}")
                # Create minimal bucket report to avoid breaking the entire analysis
                bucket_report = {
                    "session_details": [],
                    "overall_summary": {
                        "total_sessions": 0,
                        "total_system_runtime_hours": 0,
                        "total_active_time_hours": 0,
                        "average_system_utilization_percent": 0,
                        "total_experiments": 0,
                        "nodes_tracked": 0,
                        "node_summary": {},
                        "method": "daily_error_fallback"
                    },
                    "time_bucket": {
                        "bucket_index": i,
                        "start_time": "",
                        "end_time": "",
                        "user_start_time": "",
                        "user_date": "",
                        "duration_hours": 0,
                        "period_info": {"type": "day", "display": "Error", "short": "Error"}
                    },
                    "error": f"Daily bucket processing failed: {str(e)}"
                }
                bucket_reports.append(bucket_report)

        return bucket_reports
    
    def _create_monthly_buckets_from_sessions(
        self,
        time_buckets: List,
        sessions: List[Dict],
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict]:
        """Create monthly bucket reports with FIXED session attribution and comprehensive error handling."""
        
 
        bucket_reports = []
        
        # Safety check for inputs
        if not time_buckets:
            logger.warning("No time buckets provided for monthly analysis")
            return []
        
        if not sessions:
            logger.warning("No sessions provided for monthly analysis")
            sessions = []

        filtered_sessions = []

        for session in sessions:
            if not session or not isinstance(session, dict):
                continue
                
            session_start = session.get("start_time")
            session_end = session.get("end_time")
            
            if not session_start or not session_end:
                continue
            
            # Check if session overlaps with analysis period
            if session_end >= start_time and session_start <= end_time:
                filtered_sessions.append(session)
                
        for i, bucket_info in enumerate(time_buckets):
            try:
                if isinstance(bucket_info, dict):
                    bucket_start, bucket_end = bucket_info['utc_times']
                    user_start, user_end = bucket_info['user_times']
                    period_info = bucket_info.get('period_info', {})
                else:
                    bucket_start, bucket_end = bucket_info
                    user_start, user_end = bucket_start, bucket_end
                    period_info = {"type": "period", "display": user_start.strftime("%Y-%m")}
                
                # ADDED: Validate bucket times are within analysis period
                if bucket_start < start_time or bucket_end > end_time:
                    logger.warning(f"Bucket {i} extends outside analysis period, clipping to bounds")
                    bucket_start = max(bucket_start, start_time)
                    bucket_end = min(bucket_end, end_time)
                
                # Safety checks for bucket times
                if not bucket_start or not bucket_end or bucket_start >= bucket_end:
                    logger.warning(f"Invalid bucket times for bucket {i}")
                    continue
                
                # Get experiments that actually occurred within this month with safety check
                try:
                    actual_experiments_in_period = self._get_experiments_in_time_period(
                        bucket_start, bucket_end
                    )
                    if actual_experiments_in_period is None:
                        actual_experiments_in_period = []
                except Exception as e:
                    logger.error(f"Error getting experiments for bucket {i}: {e}")
                    actual_experiments_in_period = []
                
                # Find real sessions that overlap with this month and calculate proportional data
                month_sessions = []
                total_month_runtime = 0
                total_month_active_time = 0
                month_experiments = len(actual_experiments_in_period) if actual_experiments_in_period else 0
                
                # Track nodes across all sessions for this month
                month_node_utilizations = {}
                
                # CHANGED: Use filtered_sessions instead of sessions
                for session in filtered_sessions:
                    try:
                        session_start = session.get("start_time")
                        session_end = session.get("end_time")
                        
                        # Calculate overlap between session and this month
                        overlap_start = max(bucket_start, session_start)
                        overlap_end = min(bucket_end, session_end)
                        
                        if overlap_start < overlap_end:
                            # There's overlap - calculate proportional runtime
                            overlap_seconds = (overlap_end - overlap_start).total_seconds()
                            overlap_hours = overlap_seconds / 3600
                            
                            # CRITICAL FIX: Get the actual session analysis with proper utilization
                            try:
                                session_report = self.analyzer._analyze_session_utilization(session)
                                if not session_report or not isinstance(session_report, dict):
                                    session_report = {}
                                    
                                session_util = session_report.get("system_utilization_percent", 0)
                                session_active_time = session_report.get("active_time_hours", 0)
                                session_duration = session_report.get("duration_hours", 0)
                                
                                # Safety check for session values
                                if session_util is None:
                                    session_util = 0
                                if session_active_time is None:
                                    session_active_time = 0
                                if session_duration is None:
                                    session_duration = 0
                                    
                            except Exception as e:
                                logger.error(f"Error analyzing session for month bucket: {e}")
                                session_util = 0
                                session_active_time = 0
                                session_duration = 0
                                session_report = {}
                            
                            # Calculate proportional active time for this month
                            if session_duration > 0:
                                proportion = overlap_hours / session_duration
                                proportional_active_time = session_active_time * proportion
                            else:
                                proportional_active_time = overlap_hours * (session_util / 100)
                            
                            total_month_runtime += overlap_hours
                            total_month_active_time += proportional_active_time
                            
                            # CRITICAL FIX: Include node utilizations from the session with safety checks
                            session_nodes = session_report.get("node_utilizations", {})
                            if session_nodes and isinstance(session_nodes, dict):
                                for node_id, node_data in session_nodes.items():
                                    if not node_data or not isinstance(node_data, dict):
                                        continue
                                        
                                    if node_id not in month_node_utilizations:
                                        month_node_utilizations[node_id] = {
                                            "utilizations": [],
                                            "busy_hours": 0,
                                            "node_info": node_data
                                        }
                                    
                                    # Add proportional busy time for this month
                                    try:
                                        if session_duration > 0:
                                            proportion = overlap_hours / session_duration
                                            node_busy_hours = node_data.get("busy_time_hours", 0)
                                            if node_busy_hours is None:
                                                node_busy_hours = 0
                                            proportional_busy_time = node_busy_hours * proportion
                                        else:
                                            proportional_busy_time = 0
                                        
                                        month_node_utilizations[node_id]["busy_hours"] += proportional_busy_time
                                        
                                        node_util_percent = node_data.get("utilization_percent", 0)
                                        if node_util_percent is None:
                                            node_util_percent = 0
                                        month_node_utilizations[node_id]["utilizations"].append(node_util_percent)
                                        
                                    except Exception as e:
                                        logger.error(f"Error processing node {node_id} for month bucket: {e}")
                                        continue
                            
                            # Count experiments that occurred during this session's overlap
                            session_experiments = []
                            if actual_experiments_in_period:
                                try:
                                    session_experiments = [
                                        exp for exp in actual_experiments_in_period
                                        if (exp and isinstance(exp, dict) and 
                                            exp.get("event_timestamp") and
                                            overlap_start <= exp["event_timestamp"] <= overlap_end)
                                    ]
                                except Exception as e:
                                    logger.error(f"Error filtering session experiments: {e}")
                                    session_experiments = []
                            
                            # Create a session fragment for this month
                            month_session = {
                                "session_type": session.get("session_type", "unknown"),
                                "session_id": session.get("session_id", "unknown"),
                                "session_name": session.get("session_name", "Unknown Session"),
                                "start_time": overlap_start.isoformat(),
                                "end_time": overlap_end.isoformat(),
                                "duration_hours": overlap_hours,
                                "active_time_hours": proportional_active_time,
                                "total_experiments": len(session_experiments) if session_experiments else 0,
                                "system_utilization_percent": session_util,
                                "node_utilizations": session_nodes if session_nodes else {},
                                "experiment_details": [
                                    {
                                        "experiment_id": exp.get("experiment_id", ""),
                                        "experiment_name": self.analyzer._resolve_experiment_name(exp.get("experiment_id", "")),
                                        "display_name": f"Experiment {exp.get('experiment_id', '')[-8:]}"
                                    }
                                    for exp in (session_experiments if session_experiments else [])
                                    if exp and exp.get("experiment_id")
                                ],
                                "attribution_method": "monthly_proportional_from_real_session_fixed_with_bounds_check"
                            }
                            
                            month_sessions.append(month_session)
                            
                    except Exception as e:
                        logger.error(f"Error processing session for month bucket {i}: {e}")
                        continue
                
                # Process final node utilizations for this month with safety checks
                final_node_utilizations = {}
                for node_id, node_info in month_node_utilizations.items():
                    try:
                        if not node_info or not isinstance(node_info, dict):
                            continue
                            
                        utilizations = node_info.get("utilizations", [])
                        if utilizations:
                            avg_utilization = statistics.mean(utilizations)
                        else:
                            avg_utilization = 0
                        
                        base_info = node_info.get("node_info", {})
                        if not isinstance(base_info, dict):
                            base_info = {}
                            
                        busy_hours = node_info.get("busy_hours", 0)
                        if busy_hours is None:
                            busy_hours = 0
                            
                        final_node_utilizations[node_id] = {
                            "node_id": node_id,
                            "node_name": base_info.get("node_name"),
                            "display_name": base_info.get("display_name"),
                            "utilization_percent": round(avg_utilization, 1),
                            "busy_time_hours": round(busy_hours, 3),
                            "timing": base_info.get("timing", {}),
                            "raw_hours": {
                                "busy": busy_hours,
                                "idle": max(0, total_month_runtime - busy_hours),
                                "total": total_month_runtime
                            }
                        }
                    except Exception as e:
                        logger.error(f"Error processing final node utilization for {node_id}: {e}")
                        continue
                
                # Calculate month utilization properly (same as daily logic)
                month_utilization = (total_month_active_time / total_month_runtime * 100) if total_month_runtime > 0 else 0
                
                # Create bucket report with FIXED node summary
                bucket_report = {
                    "session_details": month_sessions,
                    "overall_summary": {
                        "total_sessions": len(month_sessions),
                        "total_system_runtime_hours": total_month_runtime,
                        "total_active_time_hours": total_month_active_time,
                        "average_system_utilization_percent": month_utilization,
                        "total_experiments": month_experiments,
                        "nodes_tracked": len(final_node_utilizations),
                        "node_summary": {
                            node_id: {
                                "average_utilization_percent": node_data["utilization_percent"],
                                "total_busy_time_hours": node_data["busy_time_hours"],
                                "sessions_active": 1
                            }
                            for node_id, node_data in final_node_utilizations.items()
                        },
                        "method": "monthly_fixed_with_bounds_validation"
                    },
                    "time_bucket": {
                        "bucket_index": i,
                        "start_time": bucket_start.isoformat(),
                        "end_time": bucket_end.isoformat(),
                        "user_start_time": user_start.strftime("%Y-%m-%dT%H:%M:%S") if user_start else "",
                        "user_date": user_start.strftime("%Y-%m") if user_start else "",
                        "duration_hours": (bucket_end - bucket_start).total_seconds() / 3600,
                        "period_info": period_info
                    }
                }
                
                bucket_reports.append(bucket_report)
                
            except Exception as e:
                logger.error(f"Error processing bucket {i}: {e}")
                # Create minimal bucket report to avoid breaking the entire analysis
                bucket_report = {
                    "session_details": [],
                    "overall_summary": {
                        "total_sessions": 0,
                        "total_system_runtime_hours": 0,
                        "total_active_time_hours": 0,
                        "average_system_utilization_percent": 0,
                        "total_experiments": 0,
                        "nodes_tracked": 0,
                        "node_summary": {},
                        "method": "monthly_error_fallback"
                    },
                    "time_bucket": {
                        "bucket_index": i,
                        "start_time": "",
                        "end_time": "",
                        "user_start_time": "",
                        "user_date": "",
                        "duration_hours": 0,
                        "period_info": {"type": "month", "display": "Error", "short": "Error"}
                    },
                    "error": f"Bucket processing failed: {str(e)}"
                }
                bucket_reports.append(bucket_report)
        
        return bucket_reports

    def _get_experiments_in_time_period(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Get experiments that actually started within the given time period."""
        
        experiment_events = []
    
        # Safety checks for input parameters
        if not start_time or not end_time:
            logger.warning("Invalid time parameters for experiment query")
            return []
        
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
            try:
                if not event or not isinstance(event, dict):
                    continue
                    
                event_time = self.analyzer._parse_timestamp_utc(event.get("event_timestamp"))
                if event_time and start_time <= event_time <= end_time:
                    experiment_id = self.analyzer._extract_experiment_id(event)
                    if experiment_id:
                        valid_experiments.append({
                            "experiment_id": experiment_id,
                            "event_timestamp": event_time,
                            "event_data": event.get("event_data", {})
                        })
            except Exception as e:
                logger.warning(f"Error processing experiment event: {e}")
                continue
        
        return valid_experiments

    def _create_summary_report(
        self, 
        bucket_reports: List[Dict],
        start_time: datetime,
        end_time: datetime, 
        analysis_type: str,
        user_timezone: str
    ) -> Dict[str, Any]:
        """Create clean summary report format with experiment details included."""
        
        try:
            logger.info(f"Creating summary report from {len(bucket_reports) if bucket_reports else 0} bucket reports")
            
            # Validate input parameters
            if not start_time or not end_time:
                logger.error("start_time or end_time is None in summary report creation")
                return {
                    "error": "Invalid time parameters for summary report",
                    "summary_metadata": {
                        "analysis_type": analysis_type,
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                        "error_occurred": True,
                        "error_details": "start_time or end_time is None"
                    }
                }
            
            # Validate input
            if not bucket_reports:
                logger.warning("No bucket reports provided to summary creation")
                bucket_reports = []
            
            # Process all bucket reports and extract data
            aggregated_data = self._aggregate_bucket_data(bucket_reports)
            
            # Get complete experiment details
            complete_experiment_details = self._get_complete_experiment_details(
                aggregated_data["all_experiment_details"], start_time, end_time
            )
            
            # Create node and workcell summaries
            node_summary_clean = self._create_node_summary(aggregated_data["node_metrics"], analysis_type)
            workcell_summary_clean = self._create_workcell_summary(aggregated_data["workcell_metrics"], analysis_type)
            
            # Calculate trends
            trends = self._calculate_trends_from_time_series(aggregated_data["time_series_points"])
            
            # Calculate system-level metrics and peak info
            system_metrics = self._calculate_system_metrics(
                bucket_reports, aggregated_data, analysis_type
            )
            
            logger.info(f"Final summary: {len(node_summary_clean)} nodes, {len(workcell_summary_clean)} workcells")
            
            return {
                "summary_metadata": {
                    "analysis_type": analysis_type,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "period_start": start_time.isoformat(),
                    "period_end": end_time.isoformat(),
                    "user_timezone": user_timezone,
                    "total_periods": len(bucket_reports),
                    "method": "session_based_analysis_with_experiment_details_refactored"
                },
                
                "key_metrics": {
                    "average_utilization": system_metrics["average_utilization"],
                    **system_metrics["peak_info"],
                    "total_experiments": sum(aggregated_data["all_experiments"]) if aggregated_data["all_experiments"] else 0,
                    "total_runtime_hours": round(sum(aggregated_data["all_runtime_hours"]) if aggregated_data["all_runtime_hours"] else 0, 2),
                    "total_active_time_hours": round(sum(aggregated_data["all_active_time_hours"]) if aggregated_data["all_active_time_hours"] else 0, 2),
                    "active_periods": len(aggregated_data["all_utilizations"]),
                    "total_periods": len(bucket_reports)
                },
                
                "node_summary": node_summary_clean,
                "workcell_summary": workcell_summary_clean,
                "trends": trends,
                
                "experiment_details": {
                    "total_experiments": len(complete_experiment_details) if complete_experiment_details else 0,
                    "experiments": (complete_experiment_details[:50] if complete_experiment_details else [])
                },
                
                "time_series": {
                    "system": aggregated_data["time_series_points"],
                    "nodes": {
                        node_id: node_data["time_series"] 
                        for node_id, node_data in aggregated_data["node_metrics"].items()
                        if node_id in aggregated_data["actual_node_ids"] and node_data.get("time_series")
                    },
                    "workcells": {
                        workcell_id: workcell_data["time_series"]
                        for workcell_id, workcell_data in aggregated_data["workcell_metrics"].items()
                        if workcell_id in aggregated_data["actual_workcell_ids"] and workcell_data.get("time_series")
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Error in summary report creation: {e}")
            # Ensure we have valid start_time and end_time for error response
            period_start = start_time.isoformat() if start_time else None
            period_end = end_time.isoformat() if end_time else None
            
            return {
                "error": f"Failed to generate summary: {str(e)}",
                "summary_metadata": {
                    "analysis_type": analysis_type,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "period_start": period_start,
                    "period_end": period_end,
                    "error_occurred": True,
                    "error_details": str(e)
                }
            }

    def _aggregate_bucket_data(self, bucket_reports: List[Dict]) -> Dict[str, Any]:
        """Aggregate data from all bucket reports."""
        
        # Initialize aggregation containers
        all_utilizations = []
        all_experiments = []
        all_runtime_hours = []
        all_active_time_hours = []
        all_periods_utilizations = []
        active_periods_utilizations = []
        
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
        actual_node_ids = set()
        actual_workcell_ids = set()
        all_experiment_details = []
        
        # Process each bucket report
        for bucket_report in bucket_reports:
            if not bucket_report or not isinstance(bucket_report, dict):
                continue
                
            if "error" in bucket_report:
                logger.warning(f"Skipping bucket report with error: {bucket_report.get('error')}")
                continue
            
            # Extract basic data
            overall_summary = bucket_report.get("overall_summary", {})
            session_details = bucket_report.get("session_details", [])
            time_bucket = bucket_report.get("time_bucket", {})
            
            # Get period info for labeling
            period_info = time_bucket.get("period_info", {
                "type": "period", 
                "display": time_bucket.get("user_date", ""),
                "short": time_bucket.get("user_date", "")
            })
            
            # Extract system metrics with safety checks
            avg_util = overall_summary.get("average_system_utilization_percent", 0) or 0
            total_exp = overall_summary.get("total_experiments", 0) or 0
            total_runtime = overall_summary.get("total_system_runtime_hours", 0) or 0
            total_active_time = overall_summary.get("total_active_time_hours", 0) or 0
            
            # Track utilizations
            all_periods_utilizations.append(avg_util)
            
            if total_exp > 0:
                active_periods_utilizations.append(avg_util)
                all_utilizations.append(avg_util)
                all_experiments.append(total_exp)
            
            all_runtime_hours.append(total_runtime)
            all_active_time_hours.append(total_active_time)
            
            # Process experiment details
            self._extract_experiment_details(session_details, all_experiment_details)
            
            # Process node data
            self._process_node_data(overall_summary, time_bucket, period_info, node_metrics, actual_node_ids)
            
            # Process workcell data
            self._process_workcell_data(session_details, time_bucket, period_info, workcell_metrics, actual_workcell_ids)
            
            # Add to system time series
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
        
        return {
            "all_utilizations": all_utilizations,
            "all_experiments": all_experiments,
            "all_runtime_hours": all_runtime_hours,
            "all_active_time_hours": all_active_time_hours,
            "all_periods_utilizations": all_periods_utilizations,
            "active_periods_utilizations": active_periods_utilizations,
            "node_metrics": node_metrics,
            "workcell_metrics": workcell_metrics,
            "time_series_points": time_series_points,
            "actual_node_ids": actual_node_ids,
            "actual_workcell_ids": actual_workcell_ids,
            "all_experiment_details": all_experiment_details
        }

    def _extract_experiment_details(self, session_details: List[Dict], all_experiment_details: List[Dict]):
        """Extract experiment details from session details."""
        
        if not session_details:
            return
            
        for session in session_details:
            if not session or not isinstance(session, dict):
                continue
                
            experiment_details = session.get("experiment_details", [])
            if not experiment_details:
                continue
                
            for exp in experiment_details:
                if not exp or not isinstance(exp, dict):
                    continue
                    
                # Avoid duplicates by checking experiment_id
                exp_id = exp.get("experiment_id")
                if exp_id and not any(existing.get("experiment_id") == exp_id for existing in all_experiment_details):
                    all_experiment_details.append(exp)

    def _process_node_data(self, overall_summary: Dict, time_bucket: Dict, period_info: Dict, 
                        node_metrics: Dict, actual_node_ids: set):
        """Process node data from bucket summary."""
        
        node_summary_in_bucket = overall_summary.get("node_summary", {})
        if not node_summary_in_bucket:
            return
            
        for node_id, node_data in node_summary_in_bucket.items():
            if not node_data or not isinstance(node_data, dict):
                continue
                
            actual_node_ids.add(node_id)
            
            utilization = node_data.get("average_utilization_percent", 0) or 0
            busy_hours = node_data.get("total_busy_time_hours", 0) or 0
            
            node_metrics[node_id]["utilizations"].append(utilization)
            node_metrics[node_id]["busy_hours"] += busy_hours
            
            # Add time series point for this node
            node_metrics[node_id]["time_series"].append({
                "period_number": time_bucket.get("bucket_index", 0) + 1,
                "period_type": period_info.get("type", "period"),
                "period_display": period_info.get("display", ""),
                "date": time_bucket.get("user_date", ""),
                "utilization": utilization,
                "busy_hours": busy_hours
            })

    def _process_workcell_data(self, session_details: List[Dict], time_bucket: Dict, period_info: Dict,
                            workcell_metrics: Dict, actual_workcell_ids: set):
        """Process workcell data from session details."""
        
        if not session_details:
            return
            
        for session in session_details:
            if not session or not isinstance(session, dict):
                continue
                
            session_id = session.get("session_id")
            session_type = session.get("session_type", "")
            
            # Track workcells
            if session_type in ["workcell", "lab"] and session_id:
                actual_workcell_ids.add(session_id)
                
                session_util = session.get("system_utilization_percent", 0) or 0
                session_exp = session.get("total_experiments", 0) or 0
                session_runtime = session.get("duration_hours", 0) or 0
                session_active_time = session.get("active_time_hours", 0) or 0
                
                workcell_metrics[session_id]["utilizations"].append(session_util)
                workcell_metrics[session_id]["experiments"].append(session_exp)
                workcell_metrics[session_id]["runtime_hours"].append(session_runtime)
                workcell_metrics[session_id]["active_time_hours"].append(session_active_time)
                
                # Add time series if there's runtime
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

    def _create_node_summary(self, node_metrics: Dict, analysis_type: str) -> Dict[str, Any]:
        """Create clean node summary from aggregated metrics."""
        
        node_summary_clean = {}
        
        for node_id, data in node_metrics.items():
            try:
                node_name = self.analyzer._resolve_node_name(node_id)
                
                # Calculate peak info with context - FIXED to find actual peak
                peak_info = self._find_actual_peak_info(data, analysis_type)
                
                node_summary_clean[node_id] = {
                    "node_id": node_id,
                    "node_name": node_name,
                    "display_name": f"{node_name} ({node_id[-8:]})" if node_name else f"Node {node_id[-8:]}",
                    "average_utilization": round(statistics.mean(data["utilizations"]) if data["utilizations"] else 0, 2),
                    **peak_info,
                    "total_busy_hours": round(data["busy_hours"], 2)
                }
            except Exception as e:
                logger.error(f"Error processing node summary for {node_id}: {e}")
                continue
        
        return node_summary_clean

    def _create_workcell_summary(self, workcell_metrics: Dict, analysis_type: str) -> Dict[str, Any]:
        """Create clean workcell summary from aggregated metrics."""
        
        workcell_summary_clean = {}
        
        for workcell_id, data in workcell_metrics.items():
            try:
                workcell_name = self._resolve_workcell_name(workcell_id)
                
                # Calculate peak info with context - FIXED to find actual peak
                peak_info = self._find_actual_peak_info(data, analysis_type)
                
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
                    "total_experiments": sum(data["experiments"]) if data["experiments"] else 0,
                    "total_runtime_hours": round(sum(data["runtime_hours"]) if data["runtime_hours"] else 0, 2),
                    "total_active_time_hours": round(sum(data["active_time_hours"]) if data["active_time_hours"] else 0, 2)
                }
            except Exception as e:
                logger.error(f"Error processing workcell summary for {workcell_id}: {e}")
                continue
        
        return workcell_summary_clean

    def _calculate_system_metrics(self, bucket_reports: List[Dict], aggregated_data: Dict, 
                                analysis_type: str) -> Dict[str, Any]:
        """Calculate system-level metrics and peak information."""
        
        # Safety check for inputs
        if not aggregated_data or not isinstance(aggregated_data, dict):
            logger.warning("Invalid aggregated_data provided to system metrics calculation")
            return {
                "average_utilization": 0,
                "peak_info": {
                    "peak_utilization": 0,
                    "peak_period": None,
                    "peak_context": "No data available"
                }
            }
        
        try:
            if analysis_type == "monthly":
                # For monthly: recalculate utilization from raw runtime/active time
                all_runtime_hours = aggregated_data.get("all_runtime_hours", [])
                all_active_time_hours = aggregated_data.get("all_active_time_hours", [])
                
                total_runtime_all = sum(all_runtime_hours) if all_runtime_hours else 0
                total_active_all = sum(all_active_time_hours) if all_active_time_hours else 0
                
                if total_runtime_all > 0:
                    corrected_monthly_utilization = (total_active_all / total_runtime_all) * 100
                else:
                    corrected_monthly_utilization = 0
                
                average_utilization = round(corrected_monthly_utilization, 2)
                peak_info = self._find_system_peak_period(bucket_reports, analysis_type)
                
            else:
                # For daily/weekly: use existing logic
                all_utilizations = aggregated_data.get("all_utilizations", [])
                if all_utilizations:
                    average_utilization = round(statistics.mean(all_utilizations), 2)
                else:
                    average_utilization = 0
                    
                peak_info = self._find_system_peak_period(bucket_reports, analysis_type)
            
            # Safety check for peak_info
            if not peak_info or not isinstance(peak_info, dict):
                peak_info = {
                    "peak_utilization": 0,
                    "peak_period": None,
                    "peak_context": "No peak data available"
                }
            
            return {
                "average_utilization": average_utilization,
                "peak_info": peak_info
            }
            
        except Exception as e:
            logger.error(f"Error calculating system metrics: {e}")
            return {
                "average_utilization": 0,
                "peak_info": {
                    "peak_utilization": 0,
                    "peak_period": None,
                    "peak_context": "Error calculating peak"
                }
            }

    def _find_system_peak_period(self, bucket_reports: List[Dict], analysis_type: str) -> Dict[str, Any]:
        """Find the actual period with peak system utilization - FIXED VERSION."""
        
        if not bucket_reports:
            return {
                "peak_utilization": 0,
                "peak_period": None,
                "peak_context": "No peak data available"
            }
        
        # Find the bucket with the highest utilization
        max_utilization = 0
        peak_period_display = None
        peak_utilization_value = 0
        
        for bucket_report in bucket_reports:
            if not bucket_report or not isinstance(bucket_report, dict):
                continue
                
            overall_summary = bucket_report.get("overall_summary", {})
            bucket_utilization = overall_summary.get("average_system_utilization_percent", 0)
            
            if bucket_utilization > max_utilization:
                max_utilization = bucket_utilization
                peak_utilization_value = bucket_utilization
                
                # Get the period display from this bucket
                time_bucket = bucket_report.get("time_bucket", {})
                period_info = time_bucket.get("period_info", {})
                
                if period_info.get("display"):
                    peak_period_display = period_info["display"]
                else:
                    # Fallback to parsing start_time
                    start_time_str = time_bucket.get("start_time", "")
                    if start_time_str:
                        try:
                            bucket_date = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                            if analysis_type == "daily":
                                peak_period_display = bucket_date.strftime("%Y-%m-%d")
                            elif analysis_type == "weekly":
                                peak_period_display = f"Week of {bucket_date.strftime('%Y-%m-%d')}"
                            elif analysis_type == "monthly":
                                peak_period_display = bucket_date.strftime("%m/%y")
                            else:
                                peak_period_display = bucket_date.strftime("%Y-%m-%d")
                        except:
                            pass
        
        # Create peak info
        if peak_period_display:
            if analysis_type == "daily":
                context = f"Peak utilization on {peak_period_display}"
            elif analysis_type == "weekly":
                context = f"Peak utilization during {peak_period_display}"
            elif analysis_type == "monthly":
                context = f"Peak utilization in {peak_period_display}"
            else:
                context = f"Peak utilization in {peak_period_display}"
                
            return {
                "peak_utilization": round(peak_utilization_value, 2),
                "peak_period": peak_period_display,
                "peak_context": context
            }
        else:
            return {
                "peak_utilization": 0,
                "peak_period": None,
                "peak_context": "No peak data available"
            }

    def _find_actual_peak_info(self, data: Dict, analysis_type: str) -> Dict[str, Any]:
        """Find actual peak info from time series data - FIXED VERSION."""
        
        if not data or not data.get("utilizations") or not data.get("time_series"):
            return {
                "peak_utilization": 0,
                "peak_period": None,
                "peak_context": "No peak data available"
            }
        
        utilizations = data["utilizations"]
        time_series = data["time_series"]
        
        # Find the index of maximum utilization
        max_utilization = max(utilizations)
        max_index = utilizations.index(max_utilization)
        
        # Get the corresponding time series entry
        if max_index < len(time_series):
            peak_period_info = time_series[max_index]
            period_display = peak_period_info.get("period_display", "Unknown")
            
            # Create contextual message based on analysis type
            if analysis_type == "daily":
                peak_context = f"Peak utilization on {period_display}"
            elif analysis_type == "weekly":
                peak_context = f"Peak utilization during {period_display}"
            elif analysis_type == "monthly":
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
        
    def _get_complete_experiment_details(
        self, 
        experiment_list: List[Dict], 
        start_time: datetime, 
        end_time: datetime
    ) -> List[Dict]:
        """Get complete experiment details from the database, starting from experiment_list."""
        
        complete_details = []
        
        # Safety check for inputs
        if not experiment_list:
            logger.info("No experiment_list provided, querying database directly")
            experiment_list = []
        
        # Get experiment IDs from the provided list
        experiment_ids_from_list = set()
        for exp in experiment_list:
            if exp and isinstance(exp, dict):
                exp_id = exp.get("experiment_id")
                if exp_id:
                    experiment_ids_from_list.add(exp_id)
        
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
                        if not event or not isinstance(event, dict):
                            continue
                            
                        event_time = self.analyzer._parse_timestamp_utc(event.get("event_timestamp"))
                        if event_time:
                            exp_id = self.analyzer._extract_experiment_id(event)
                            if exp_id:
                                # FILTER: Only process experiments that were in the experiment_list (if provided)
                                if experiment_ids_from_list and exp_id not in experiment_ids_from_list:
                                    continue
                                    
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
            try:
                start_event = events.get("start")
                complete_event = events.get("complete")
                
                if start_event:
                    start_time_exp = start_event["timestamp"]
                    start_data = start_event["event_data"]
                    
                    # Get experiment name with safety checks
                    exp_name = "Unknown Experiment"
                    if isinstance(start_data.get("experiment"), dict):
                        exp_design = start_data["experiment"].get("experiment_design", {})
                        if isinstance(exp_design, dict):
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
                        
                        complete_data = complete_event.get("event_data", {})
                        status = complete_data.get("status", "completed") if isinstance(complete_data, dict) else "completed"
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
            except Exception as e:
                logger.error(f"Error processing experiment {exp_id}: {e}")
                continue
        
        # Sort by start time
        try:
            complete_details.sort(key=lambda x: x.get("start_time", ""))
        except Exception as e:
            logger.warning(f"Error sorting experiment details: {e}")
        
        return complete_details
     
    
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
        """Create time buckets aligned to user timezone with improved error handling."""
        
        # Validate inputs
        if not start_time or not end_time:
            logger.error("start_time or end_time is None in time bucket creation")
            return []
        
        if start_time >= end_time:
            logger.error(f"Invalid time range: start_time ({start_time}) >= end_time ({end_time})")
            return []
        
        try:
            tz_handler = TimezoneHandler(user_timezone)
            buckets = []
            
            current_user_time = tz_handler.utc_to_user_time(start_time)
            end_user_time = tz_handler.utc_to_user_time(end_time)
            
            # Validate converted times
            if not current_user_time or not end_user_time:
                logger.error("Failed to convert UTC times to user timezone")
                return []
            
            # Handle monthly as special case
            if bucket_hours == "monthly" or bucket_hours == 720:
                current_user_time = current_user_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                
                while current_user_time < end_user_time:
                    try:
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
                    except Exception as e:
                        logger.error(f"Error creating monthly bucket: {e}")
                        break
                        
            elif bucket_hours == 24:  # Daily buckets
                current_user_time = current_user_time.replace(hour=0, minute=0, second=0, microsecond=0)
                bucket_delta = timedelta(days=1)
                
                while current_user_time < end_user_time:
                    try:
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
                    except Exception as e:
                        logger.error(f"Error creating daily bucket: {e}")
                        break
                    
            elif bucket_hours == 168:  # Weekly buckets
                try:
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
                except Exception as e:
                    logger.error(f"Error creating weekly buckets: {e}")
                    return []
                    
            else:  # Hourly or custom buckets
                try:
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
                except Exception as e:
                    logger.error(f"Error creating hourly/custom buckets: {e}")
                    return []
            
            logger.info(f"Successfully created {len(buckets)} time buckets")
            return buckets
            
        except Exception as e:
            logger.error(f"Error in time bucket creation: {e}")
            return []

class TimezoneHandler:
    """Handle timezone conversions with improved error handling."""
    
    def __init__(self, user_timezone: str = "America/Chicago"):
        try:
            self.user_tz = pytz.timezone(user_timezone)
            self.utc_tz = pytz.UTC
        except Exception as e:
            logger.error(f"Error initializing timezone handler with {user_timezone}: {e}")
            # Fallback to UTC
            self.user_tz = pytz.UTC
            self.utc_tz = pytz.UTC
    
    def utc_to_user_time(self, utc_datetime: datetime) -> Optional[datetime]:
        """Convert UTC datetime to user timezone."""
        try:
            if not utc_datetime:
                logger.error("utc_datetime is None in utc_to_user_time")
                return None
                
            if utc_datetime.tzinfo is None:
                utc_datetime = self.utc_tz.localize(utc_datetime)
            return utc_datetime.astimezone(self.user_tz)
        except Exception as e:
            logger.error(f"Error converting UTC to user time: {e}")
            return None
    
    def user_to_utc_time(self, user_datetime: datetime) -> Optional[datetime]:
        """Convert user timezone datetime to UTC."""
        try:
            if not user_datetime:
                logger.error("user_datetime is None in user_to_utc_time")
                return None
                
            if user_datetime.tzinfo is None:
                user_datetime = self.user_tz.localize(user_datetime)
            return user_datetime.astimezone(self.utc_tz).replace(tzinfo=None)
        except Exception as e:
            logger.error(f"Error converting user time to UTC: {e}")
            return None
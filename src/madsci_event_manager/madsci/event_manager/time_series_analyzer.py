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
        """
        Generate summary utilization report with time-series analysis.
        
        Args:
            start_time: Analysis start time (UTC, timezone-naive)
            end_time: Analysis end time (UTC, timezone-naive)
            analysis_type: Time bucket type ("hourly", "daily", "weekly", "monthly")
            user_timezone: Timezone for day/week boundaries
            
        Returns:
            Dict containing time-series data, summaries, and trends
        """
        
        logger.info(f"Generating {analysis_type} summary report for timezone {user_timezone}")
        
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
        
        # Find all active workcells in the entire timeframe
        active_workcells = self._find_active_workcells_in_timeframe(start_time, end_time)
        logger.info(f"Found {len(active_workcells)} active workcells in timeframe")
        
        # Generate session report for each bucket with attribution
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
            
            # Generate base session report
            bucket_report = self.analyzer.generate_session_based_report(bucket_start, bucket_end)
            
            # Apply session attribution for this bucket
            bucket_report = self._apply_session_attribution(
                bucket_report, active_workcells, bucket_start, bucket_end
            )
            
            # Add time bucket info
            bucket_report["time_bucket"] = {
                "bucket_index": i,
                "start_time": bucket_start.isoformat(),
                "end_time": bucket_end.isoformat(),
                "user_start_time": user_start.strftime("%Y-%m-%dT%H:%M:%S"),
                "user_date": user_start.strftime("%Y-%m-%d"),
                "duration_hours": (bucket_end - bucket_start).total_seconds() / 3600,
                "period_info": period_info
            }
            
            bucket_reports.append(bucket_report)
        
        # Create summary report
        return self._create_summary_report(bucket_reports, start_time, end_time, analysis_type, user_timezone)
    
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
        """Apply session attribution logic to convert default_analysis sessions to proper workcell sessions."""
        
        session_details = bucket_report.get("session_details", [])
        if not session_details:
            return bucket_report
        
        # Find default_analysis sessions with experiments
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
            
            # Strategy 1: If there's exactly one real workcell session, merge with it
            if len(real_workcell_sessions) == 1:
                primary_workcell = real_workcell_sessions[0]
                
                # Merge all default sessions into the primary workcell
                for default_session in default_sessions:
                    primary_workcell = self._merge_sessions(primary_workcell, default_session)
                
                # Update session details
                bucket_report["session_details"] = [primary_workcell]
                
            # Strategy 2: If no real workcell sessions, find the best active workcell
            elif len(real_workcell_sessions) == 0 and active_workcells:
                # Find the workcell most likely to be responsible
                best_workcell = self._find_best_active_workcell(
                    active_workcells, bucket_start, bucket_end
                )
                
                if best_workcell:
                    # Create a new workcell session from the best match
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
        """Create clean summary report format with proper workcell attribution."""
        
        logger.info(f"Creating summary report from {len(bucket_reports)} bucket reports")
        
        # Aggregate data from bucket reports
        all_utilizations = []
        all_experiments = []
        all_runtime_hours = []
        
        # Node and workcell aggregation
        node_metrics = defaultdict(lambda: {"utilizations": [], "busy_hours": 0, "time_series": []})
        workcell_metrics = defaultdict(lambda: {"utilizations": [], "experiments": [], "runtime_hours": [], "time_series": []})
        time_series_points = []
        
        # Track what IDs are actually nodes vs workcells
        actual_node_ids = set()
        actual_workcell_ids = set()
        
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
            
            if total_exp > 0:  # Active period
                all_utilizations.append(avg_util)
                all_experiments.append(total_exp)
                all_runtime_hours.append(total_runtime)
            
            # Process sessions with attribution tracking
            for session in session_details:
                session_id = session.get("session_id")
                session_type = session.get("session_type", "")
                
                # Includes attributed sessions
                if session_type in ["workcell", "lab"] and session_id:
                    actual_workcell_ids.add(session_id)
                    
                    session_util = session.get("system_utilization_percent", 0)
                    session_exp = session.get("total_experiments", 0)
                    session_runtime = session.get("duration_hours", 0)
                    
                    workcell_metrics[session_id]["utilizations"].append(session_util)
                    workcell_metrics[session_id]["experiments"].append(session_exp)
                    workcell_metrics[session_id]["runtime_hours"].append(session_runtime)
                    
                    # Time series for workcells
                    if session_exp > 0:
                        attribution_info = session.get("attribution_info")
                        workcell_metrics[session_id]["time_series"].append({
                            "period_number": time_bucket.get("bucket_index", 0) + 1,
                            "period_type": period_info.get("type", "period"),
                            "period_display": period_info.get("display", ""),
                            "date": time_bucket.get("user_date", ""),
                            "utilization": session_util,
                            "experiments": session_exp,
                            "runtime_hours": session_runtime,
                            "attributed": bool(attribution_info)
                        })
            
            # Node metrics processing
            node_summary = overall_summary.get("node_summary", {})
            for node_id, node_data in node_summary.items():
                # Skip if this ID is actually a workcell
                if node_id in actual_workcell_ids:
                    continue
                
                # Verify this is actually a node by checking if it has a node name
                node_name = self.analyzer._resolve_node_name(node_id)
                if not node_name:
                    continue
                
                actual_node_ids.add(node_id)
                
                utilization = node_data.get("average_utilization_percent", 0)
                busy_hours = node_data.get("total_busy_time_hours", 0)
                
                node_metrics[node_id]["utilizations"].append(utilization)
                node_metrics[node_id]["busy_hours"] += busy_hours
                
                # Time series for nodes
                if total_exp > 0:  # Only add points for active periods
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
                "runtime_hours": total_runtime
            })
        
        # Create clean node summary with peak context
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
        
        # Create clean workcell summary with peak context and attribution tracking
        workcell_summary_clean = {}
        for workcell_id, data in workcell_metrics.items():
            if workcell_id not in actual_workcell_ids:
                continue
                
            # Better workcell name resolution
            workcell_name = self._resolve_workcell_name(workcell_id)
            
            # Calculate peak info with context
            peak_info = self._calculate_period_peak_info(data, analysis_type)
            
            # Check if any periods were attributed
            attributed_periods = sum(1 for point in data["time_series"] if point.get("attributed", False))
            
            # Better display name that avoids duplication
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
                "periods_tracked": len(data["time_series"]),
                "attributed_periods": attributed_periods
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
                "method": "session_based_analysis_with_attribution"
            },
            
            "key_metrics": {
                "average_utilization": round(statistics.mean(all_utilizations) if all_utilizations else 0, 2),
                **system_peak_info,
                "total_experiments": sum(all_experiments),
                "total_runtime_hours": round(sum(all_runtime_hours), 2),
                "active_periods": len(all_utilizations),
                "total_periods": len(bucket_reports)
            },
            
            "node_summary": node_summary_clean,
            "workcell_summary": workcell_summary_clean,
            "trends": trends,
            
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
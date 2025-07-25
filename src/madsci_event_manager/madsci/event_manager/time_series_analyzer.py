"""
Fixed Time-Series Analysis - Addresses node/workcell confusion and phantom sessions.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from collections import defaultdict
import statistics
import pytz

class TimeSeriesAnalyzer:
    """
    Fixed analyzer that properly separates nodes from workcells.
    """
    
    def __init__(self, utilization_analyzer):
        """Initialize with existing UtilizationAnalyzer instance."""
        self.analyzer = utilization_analyzer
        self.events_collection = utilization_analyzer.events_collection
    
    def generate_time_series_report(
        self,
        start_time: datetime,
        end_time: datetime,
        time_bucket_hours: Optional[int] = None,
        analysis_type: str = "daily",
        user_timezone: str = "America/Chicago"
    ) -> Dict[str, Any]:
        """Generate comprehensive time-series analysis with timezone support."""
        
        print(f"Generating {analysis_type} time-series analysis for timezone {user_timezone}...")
        
        # FIXED: Determine bucket type from analysis_type, not bucket_hours
        if time_bucket_hours is None:
            if analysis_type == "hourly":
                time_bucket_hours = 1
            elif analysis_type == "daily":
                time_bucket_hours = 24
            elif analysis_type == "weekly":
                time_bucket_hours = 168
            elif analysis_type in ["monthly", "mounthly"]:
                time_bucket_hours = "monthly"  # Special flag
            else:
                time_bucket_hours = 24  # Default to daily
        
        # Create time buckets
        time_buckets = self._create_time_buckets_user_timezone(
            start_time, end_time, time_bucket_hours, user_timezone
        )
        
        bucket_type = "monthly" if time_bucket_hours == "monthly" else f"{time_bucket_hours}h"
        print(f"Created {len(time_buckets)} {bucket_type} buckets aligned to {user_timezone}")
        
        # Generate session report for each bucket
        bucket_reports = []
        for i, bucket_info in enumerate(time_buckets):
            # Handle bucket format
            if isinstance(bucket_info, dict):
                bucket_start, bucket_end = bucket_info['utc_times']
                user_start, user_end = bucket_info['user_times']
                period_info = bucket_info.get('period_info', {})
            else:
                bucket_start, bucket_end = bucket_info
                user_start, user_end = bucket_start, bucket_end
                period_info = {"type": "period", "display": user_start.strftime("%Y-%m-%d")}
                
            print(f"Analyzing {period_info.get('type', 'period')} {i+1}/{len(time_buckets)}: {period_info.get('display', user_start.strftime('%Y-%m-%d'))}")
            
            bucket_report = self.analyzer.generate_session_report(bucket_start, bucket_end)
            
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
        
        # Create both detailed and summary formats
        detailed_report = self._create_detailed_report(bucket_reports, start_time, end_time, analysis_type, user_timezone)
        summary_report = self._create_summary_report(bucket_reports, start_time, end_time, analysis_type, user_timezone)
        
        return {
            "detailed": detailed_report,
            "summary": summary_report
        }
    
    def generate_summary_report(
        self,
        start_time: datetime,
        end_time: datetime,
        analysis_type: str = "daily", 
        user_timezone: str = "America/Chicago"
    ) -> Dict[str, Any]:
        """Generate ONLY the summary report format."""
        
        # FIXED: Don't use bucket_hours for monthly, use analysis_type directly
        print(f"Generating {analysis_type} summary report...")
        
        # Generate the time-series analysis with proper bucketing
        full_analysis = self.generate_time_series_report(
            start_time, end_time, None, analysis_type, user_timezone  # Pass None for bucket_hours
        )
        
        # Return only the summary portion
        return full_analysis["summary"]
    
    def _create_summary_report(
        self, 
        bucket_reports: List[Dict],
        start_time: datetime,
        end_time: datetime, 
        analysis_type: str,
        user_timezone: str
    ) -> Dict[str, Any]:
        """Create clean summary report format - FIXED for node/workcell separation."""
        
        print(f"Creating summary report from {len(bucket_reports)} bucket reports")
        
        # Aggregate data from bucket reports
        all_utilizations = []
        all_experiments = []
        all_runtime_hours = []
        
        # Node and workcell aggregation
        node_metrics = defaultdict(lambda: {"utilizations": [], "busy_hours": 0, "time_series": []})
        workcell_metrics = defaultdict(lambda: {"utilizations": [], "experiments": [], "runtime_hours": [], "time_series": []})
        time_series_points = []
        
        # FIXED: Track what IDs are actually nodes vs workcells
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
            
            # FIXED: Separate nodes from workcells using session details
            for session in session_details:
                session_id = session.get("session_id")
                session_type = session.get("session_type", "")
                
                # Skip default analysis sessions
                if session_type == "default_analysis" or session_id.startswith("analysis_"):
                    print(f"Skipping default analysis session: {session_id}")
                    continue
                
                # This is a real workcell session
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
                        workcell_metrics[session_id]["time_series"].append({
                            "period_number": time_bucket.get("bucket_index", 0) + 1,
                            "period_type": period_info.get("type", "period"),
                            "period_display": period_info.get("display", ""),
                            "date": time_bucket.get("user_date", ""),
                            "utilization": session_util,
                            "experiments": session_exp,
                            "runtime_hours": session_runtime
                        })
            
            # FIXED: Node metrics - only from actual nodes, exclude workcell IDs
            node_summary = overall_summary.get("node_summary", {})
            for node_id, node_data in node_summary.items():
                # Skip if this ID is actually a workcell
                if node_id in actual_workcell_ids:
                    print(f"Skipping {node_id} from node summary - it's a workcell")
                    continue
                
                # Verify this is actually a node by checking if it has a node name
                node_name = node_data.get("node_name") or self.analyzer._resolve_node_name(node_id)
                if not node_name:
                    print(f"Skipping {node_id} from node summary - no node name found")
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
        
        # Create clean node summary - only actual nodes
        node_summary_clean = {}
        for node_id, data in node_metrics.items():
            if node_id not in actual_node_ids:
                continue
                
            node_name = self.analyzer._resolve_node_name(node_id)
            
            node_summary_clean[node_id] = {
                "node_id": node_id,
                "node_name": node_name,
                "display_name": f"{node_name} ({node_id[-8:]})" if node_name else f"Node {node_id[-8:]}",
                "average_utilization": round(statistics.mean(data["utilizations"]) if data["utilizations"] else 0, 2),
                "peak_utilization": round(max(data["utilizations"]) if data["utilizations"] else 0, 2),
                "total_busy_hours": round(data["busy_hours"], 2)
            }
        
        # Create clean workcell summary - only actual workcells
        workcell_summary_clean = {}
        for workcell_id, data in workcell_metrics.items():
            if workcell_id not in actual_workcell_ids:
                continue
                
            # Get workcell name from session details
            workcell_name = None
            for bucket_report in bucket_reports:
                for session in bucket_report.get("session_details", []):
                    if session.get("session_id") == workcell_id:
                        workcell_name = session.get("session_name")
                        break
                if workcell_name:
                    break
            
            workcell_summary_clean[workcell_id] = {
                "workcell_id": workcell_id,
                "workcell_name": workcell_name,
                "display_name": f"{workcell_name} ({workcell_id[-8:]})" if workcell_name else f"Workcell {workcell_id[-8:]}",
                "average_utilization": round(statistics.mean(data["utilizations"]) if data["utilizations"] else 0, 2),
                "peak_utilization": round(max(data["utilizations"]) if data["utilizations"] else 0, 2),
                "total_experiments": sum(data["experiments"]),
                "total_runtime_hours": round(sum(data["runtime_hours"]), 2)
            }
        
        # Calculate trends
        trends = self._calculate_trends_from_time_series(time_series_points)
        
        print(f"Summary: {len(node_summary_clean)} nodes, {len(workcell_summary_clean)} workcells")
        
        return {
            "summary_metadata": {
                "analysis_type": analysis_type,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "period_start": start_time.isoformat(),
                "period_end": end_time.isoformat(),
                "user_timezone": user_timezone,
                "total_periods": len(bucket_reports),
                "method": "session_based_analysis"
            },
            
            "key_metrics": {
                "peak_utilization": round(max(all_utilizations) if all_utilizations else 0, 2),
                "average_utilization": round(statistics.mean(all_utilizations) if all_utilizations else 0, 2),
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
    
    def _get_period_label(self, analysis_type: str) -> str:
        """Get appropriate period label based on analysis type."""
        labels = {
            "hourly": "hour",
            "daily": "day", 
            "weekly": "week",
            "monthly": "month"
        }
        return labels.get(analysis_type, "period")
    
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
    
    # Keep essential supporting methods
    def _create_time_buckets_user_timezone(self, start_time, end_time, bucket_hours, user_timezone):
        """Create time buckets aligned to user timezone - FIXED for proper monthly/weekly aggregation."""
        tz_handler = TimezoneHandler(user_timezone)
        buckets = []
        
        current_user_time = tz_handler.utc_to_user_time(start_time)
        end_user_time = tz_handler.utc_to_user_time(end_time)
        
        # FIXED: Handle monthly as special case
        if bucket_hours == "monthly" or bucket_hours == 720:  # Monthly buckets
            # Start at beginning of month
            current_user_time = current_user_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            while current_user_time < end_user_time:
                # Get next month
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
                
                week_end = current_user_time + timedelta(days=6)
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
    
    def _get_period_info(self, period_start: datetime, bucket_hours: int) -> Dict[str, str]:
        """Get formatted period information for display."""
        if bucket_hours == 24:  # Daily
            return {
                "type": "day",
                "display": period_start.strftime("%Y-%m-%d"),
                "short": period_start.strftime("%m-%d")
            }
        elif bucket_hours == 168:  # Weekly  
            week_end = period_start + timedelta(days=6)
            return {
                "type": "week",
                "display": f"Week of {period_start.strftime('%Y-%m-%d')}",
                "short": f"Week {period_start.strftime('%m/%d')}"
            }
        elif bucket_hours == 720:  # Monthly
            return {
                "type": "month", 
                "display": period_start.strftime("%B %Y"),
                "short": period_start.strftime("%b %Y")
            }
        else:  # Hourly or custom
            return {
                "type": "period",
                "display": period_start.strftime("%Y-%m-%d %H:%M"),
                "short": period_start.strftime("%m/%d %H:%M")
            }
    
    def _create_detailed_report(self, bucket_reports, start_time, end_time, analysis_type, user_timezone):
        """Create detailed report format (placeholder for now)."""
        return {"detailed": "report"}  # Implementation would go here

# Keep TimezoneHandler class as-is
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
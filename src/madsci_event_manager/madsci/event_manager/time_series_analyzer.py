"""Time-series analysis for MADSci utilization data with session attribution."""

import logging
import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import pytz
from madsci.event_manager.utilization_analyzer import UtilizationAnalyzer

logger = logging.getLogger(__name__)


class TimeSeriesAnalyzer:
    """Analyzes utilization data over time with proper session attribution."""

    def __init__(self, utilization_analyzer: UtilizationAnalyzer) -> None:
        """Initialize with existing UtilizationAnalyzer instance."""
        self.analyzer = utilization_analyzer
        self.events_collection = utilization_analyzer.events_collection

    def generate_utilization_report_with_times(
        self,
        start_time: Optional[str],
        end_time: Optional[str],
        analysis_type: str,
        user_timezone: str,
    ) -> Dict[str, Any]:
        """Generate utilization report from string time parameters."""

        try:
            # Parse time parameters (if provided)
            parsed_start = None
            parsed_end = None

            if start_time:
                parsed_start = (
                    datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                    .astimezone(timezone.utc)
                    .replace(tzinfo=None)
                )

            if end_time:
                parsed_end = (
                    datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                    .astimezone(timezone.utc)
                    .replace(tzinfo=None)
                )

            # Generate summary report
            return self.generate_summary_report(
                parsed_start, parsed_end, analysis_type, user_timezone
            )

        except Exception as e:
            return {"error": f"Failed to generate utilization report: {e!s}"}

    def add_user_utilization_to_report(
        self, utilization: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add user utilization data to the report."""

        try:
            # Use the same time period that was actually analyzed
            actual_start = datetime.fromisoformat(
                utilization["summary_metadata"]["period_start"]
            )
            actual_end = datetime.fromisoformat(
                utilization["summary_metadata"]["period_end"]
            )

            user_report = self.analyzer.generate_user_utilization_report(
                actual_start, actual_end
            )

            if "error" not in user_report:
                user_summary = self.create_user_summary_from_report(user_report)

                # Insert user utilization after key_metrics
                enhanced_summary = {}
                for key, value in utilization.items():
                    enhanced_summary[key] = value
                    if key == "key_metrics":
                        enhanced_summary["user_utilization"] = user_summary

                return enhanced_summary
            utilization["user_utilization"] = {
                "error": user_report.get("error", "Failed to generate user summary")
            }
            return utilization

        except Exception as e:
            utilization["user_utilization"] = {
                "error": f"Failed to add user data: {e!s}"
            }
            return utilization

    def create_user_summary_from_report(
        self, user_report: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create user summary from user report."""

        user_utilization = user_report.get("user_utilization", {})
        system_summary = user_report.get("system_summary", {})

        # Sort users by total runtime (most active first)
        sorted_users = sorted(
            user_utilization.values(),
            key=lambda x: x.get("total_runtime_hours", 0),
            reverse=True,
        )

        # Create compact user summaries (top 10 users)
        top_users = [
            {
                "author": user.get("author"),
                "total_workflows": user.get("total_workflows"),
                "total_runtime_hours": user.get("total_runtime_hours"),
                "completion_rate_percent": user.get("completion_rate_percent"),
                "average_workflow_duration_hours": user.get(
                    "average_workflow_duration_hours"
                ),
            }
            for user in sorted_users[:10]
        ]

        return {
            "total_users": len(user_utilization),
            "author_attribution_rate_percent": system_summary.get(
                "author_attribution_rate_percent", 0
            ),
            "top_users": top_users,
            "system_totals": {
                "total_workflows": system_summary.get("total_workflows", 0),
                "total_runtime_hours": system_summary.get("total_runtime_hours", 0),
                "completion_rate_percent": system_summary.get(
                    "completion_rate_percent", 0
                ),
            },
        }

    def parse_time_parameters(
        self, start_time: Optional[str], end_time: Optional[str]
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Parse time parameters for utilization reports."""
        parsed_start = None
        parsed_end = None

        if start_time:
            parsed_start = (
                datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                .astimezone(timezone.utc)
                .replace(tzinfo=None)
            )
        if end_time:
            parsed_end = (
                datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                .astimezone(timezone.utc)
                .replace(tzinfo=None)
            )

        return parsed_start, parsed_end

    def generate_summary_report(
        self,
        start_time: datetime,
        end_time: datetime,
        analysis_type: str = "daily",
        user_timezone: str = "America/Chicago",
    ) -> Dict[str, Any]:
        """Generate summary utilization report with error handling."""

        # Store analysis type for use in attribution logic
        self._current_analysis_type = analysis_type
        logger.info(
            f"Generating {analysis_type} summary report for timezone {user_timezone}"
        )

        # Validate and determine analysis period
        analysis_result = self._validate_and_determine_analysis_period(
            start_time, end_time
        )

        if "error" in analysis_result:
            return analysis_result

        analysis_start, analysis_end = analysis_result["period"]

        # Get sessions and create time buckets
        setup_result = self._setup_analysis_components(
            analysis_start, analysis_end, analysis_type, user_timezone
        )

        if "error" in setup_result:
            return self._create_error_response(
                setup_result["error"], analysis_type, analysis_start, analysis_end
            )

        # Create bucket reports
        bucket_reports = self._create_all_bucket_reports(
            setup_result["time_buckets"],
            setup_result["sessions"],
            analysis_start,
            analysis_end,
            analysis_type,
        )

        if "error" in bucket_reports:
            return self._create_error_response(
                bucket_reports["error"], analysis_type, analysis_start, analysis_end
            )

        # Generate final summary report
        try:
            return self._create_summary_report(
                bucket_reports["reports"],
                analysis_start,
                analysis_end,
                analysis_type,
                user_timezone,
            )
        except Exception as e:
            logger.error(f"Error creating summary report: {e}")
            return self._create_error_response(
                f"Failed to generate summary: {e!s}",
                analysis_type,
                analysis_start,
                analysis_end,
            )

    def _validate_and_determine_analysis_period(
        self, start_time: datetime, end_time: datetime
    ) -> Dict[str, Any]:
        """Validate inputs and determine analysis period."""

        try:
            # Determine analysis timeframe with better error handling
            analysis_start, analysis_end = self.analyzer._determine_analysis_period(
                start_time, end_time
            )

            # Validate the returned times
            if not analysis_start or not analysis_end:
                return {
                    "error": "Could not determine analysis time period",
                    "details": "Analysis period determination failed",
                }

            if analysis_start >= analysis_end:
                return {
                    "error": "Invalid analysis time period: start time must be before end time",
                    "details": f"Start time {analysis_start} >= end time {analysis_end}",
                }

            logger.info(
                f"Analysis period determined: {analysis_start} to {analysis_end}"
            )
            return {"period": (analysis_start, analysis_end)}

        except Exception as e:
            logger.error(f"Exception in analysis period determination: {e}")
            return {
                "error": f"Failed to determine analysis period: {e!s}",
                "details": str(e),
            }

    def _setup_analysis_components(
        self,
        analysis_start: datetime,
        analysis_end: datetime,
        analysis_type: str,
        user_timezone: str,
    ) -> Dict[str, Any]:
        """Setup sessions and time buckets for analysis."""

        # Get sessions
        try:
            all_sessions = self.analyzer._find_system_sessions(
                analysis_start, analysis_end
            )
            if all_sessions is None:
                all_sessions = []
            logger.info(f"Found {len(all_sessions)} sessions")
        except Exception as e:
            logger.error(f"Error finding sessions: {e}")
            all_sessions = []

        # Determine bucket type and create time buckets
        time_bucket_hours = self._get_time_bucket_hours(analysis_type)

        try:
            time_buckets = self._create_time_buckets_user_timezone(
                analysis_start, analysis_end, time_bucket_hours, user_timezone
            )
            if time_buckets is None:
                time_buckets = []
            logger.info(f"Created {len(time_buckets)} time buckets")

            return {
                "sessions": all_sessions,
                "time_buckets": time_buckets,
            }

        except Exception as e:
            logger.error(f"Error creating time buckets: {e}")
            return {"error": f"Failed to create time buckets: {e!s}"}

    def _get_time_bucket_hours(self, analysis_type: str) -> Union[int, str]:
        """Get time bucket hours based on analysis type."""

        bucket_mapping = {
            "hourly": 1,
            "daily": 24,
            "weekly": 168,
            "monthly": "monthly",
        }

        return bucket_mapping.get(analysis_type, 24)  # Default to daily

    def _create_all_bucket_reports(
        self,
        time_buckets: List,
        all_sessions: List[Dict],
        analysis_start: datetime,
        analysis_end: datetime,
        analysis_type: str,
    ) -> Dict[str, Any]:
        """Create bucket reports for all time buckets based on analysis type."""

        try:
            if analysis_type == "daily":
                bucket_reports = self._create_daily_buckets_from_sessions(
                    time_buckets, all_sessions, analysis_start, analysis_end
                )
            elif analysis_type == "monthly":
                bucket_reports = self._create_monthly_buckets_from_sessions(
                    time_buckets, all_sessions, analysis_start, analysis_end
                )
            elif analysis_type == "weekly":
                bucket_reports = self._create_weekly_bucket_reports(
                    time_buckets, all_sessions
                )
            else:
                # Fallback for other analysis types (hourly, etc.)
                bucket_reports = self._create_fallback_bucket_reports(time_buckets)

            return {"reports": bucket_reports}

        except Exception as e:
            logger.error(f"Error creating bucket reports: {e}")
            return {"error": f"Failed to create bucket reports: {e!s}"}

    def _create_weekly_bucket_reports(
        self, time_buckets: List, all_sessions: List[Dict]
    ) -> List[Dict]:
        """Create weekly bucket reports."""

        bucket_reports = []
        for i, bucket_info in enumerate(time_buckets):
            if isinstance(bucket_info, dict):
                bucket_start, bucket_end = bucket_info["utc_times"]
                period_info = bucket_info.get("period_info", {})
            else:
                bucket_start, bucket_end = bucket_info
                period_info = {
                    "type": "period",
                    "display": bucket_start.strftime("%Y-%m-%d"),
                }

            bucket_report = self._generate_weekly_bucket_report(
                bucket_start, bucket_end, all_sessions, i, period_info
            )
            bucket_reports.append(bucket_report)

        return bucket_reports

    def _create_fallback_bucket_reports(self, time_buckets: List) -> List[Dict]:
        """Create fallback bucket reports for other analysis types."""

        bucket_reports = []
        for i, bucket_info in enumerate(time_buckets):
            if isinstance(bucket_info, dict):
                bucket_start, bucket_end = bucket_info["utc_times"]
                period_info = bucket_info.get("period_info", {})
            else:
                bucket_start, bucket_end = bucket_info
                period_info = {
                    "type": "period",
                    "display": bucket_start.strftime("%Y-%m-%d"),
                }

            # Generate base session report for this bucket
            bucket_report = self.analyzer.generate_session_based_report(
                bucket_start, bucket_end
            )

            # Add time bucket info
            bucket_report["time_bucket"] = {
                "bucket_index": i,
                "start_time": bucket_start.isoformat(),
                "end_time": bucket_end.isoformat(),
                "duration_hours": (bucket_end - bucket_start).total_seconds() / 3600,
                "period_info": period_info,
            }

            bucket_reports.append(bucket_report)

        return bucket_reports

    def _create_error_response(
        self,
        error_message: str,
        analysis_type: str,
        analysis_start: Optional[datetime] = None,
        analysis_end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Create standardized error response."""

        return {
            "error": error_message,
            "summary_metadata": {
                "analysis_type": analysis_type,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "period_start": analysis_start.isoformat() if analysis_start else None,
                "period_end": analysis_end.isoformat() if analysis_end else None,
                "error_occurred": True,
                "error_details": error_message,
            },
        }

    def _generate_weekly_bucket_report(
        self,
        bucket_start: datetime,
        bucket_end: datetime,
        all_sessions: List[Dict],
        bucket_index: int,
        period_info: Dict,
    ) -> Dict[str, Any]:
        """Generate bucket report for weekly analysis with proper runtime calculation."""

        try:
            # Get experiments and ensure we have valid session list
            experiments = self._get_experiments_safely(
                bucket_start, bucket_end, bucket_index
            )
            if not all_sessions:
                all_sessions = []

            # Process all sessions for this week
            week_data = self._process_all_sessions_for_week(
                all_sessions, bucket_start, bucket_end, experiments
            )

            # Build and return final weekly report
            return self._build_final_weekly_report(
                week_data, bucket_start, bucket_end, bucket_index, period_info
            )

        except Exception as e:
            logger.error(f"Error in weekly bucket report generation: {e}")
            return self._create_error_weekly_bucket_report(
                bucket_start, bucket_end, bucket_index, period_info, str(e)
            )

    def _process_all_sessions_for_week(
        self,
        all_sessions: List[Dict],
        bucket_start: datetime,
        bucket_end: datetime,
        experiments: List[Dict],
    ) -> Dict[str, Any]:
        """Process all sessions and accumulate data for the weekly bucket."""

        week_sessions = []
        week_runtime = 0
        week_active_time = 0
        week_utilization = 0
        week_node_utilizations = {}

        for session in all_sessions:
            if not session or not isinstance(session, dict):
                continue

            session_result = self._process_weekly_session_overlap_and_analysis(
                session, bucket_start, bucket_end, experiments
            )

            if session_result:
                week_sessions.append(session_result["fragment"])
                week_runtime += session_result["runtime_hours"]
                week_active_time += session_result["active_hours"]
                week_utilization += session_result["weighted_utilization"]

                # Accumulate node utilizations
                self._accumulate_node_data_for_weekly(
                    week_node_utilizations,
                    session_result["node_data"],
                    session_result["proportion"],
                )

        # Calculate weighted average utilization
        if week_runtime > 0:
            week_utilization = week_utilization / week_runtime

        return {
            "sessions": week_sessions,
            "runtime": week_runtime,
            "active_time": week_active_time,
            "utilization": week_utilization,
            "experiments_count": len(experiments),
            "node_utilizations": week_node_utilizations,
        }

    def _process_weekly_session_overlap_and_analysis(
        self,
        session: Dict,
        bucket_start: datetime,
        bucket_end: datetime,
        experiments: List[Dict],
    ) -> Optional[Dict[str, Any]]:
        """Process session overlap with weekly bucket and perform analysis."""

        session_start = session.get("start_time")
        session_end = session.get("end_time")

        if not session_start or not session_end:
            return None

        # Calculate overlap
        overlap_start = max(bucket_start, session_start)
        overlap_end = min(bucket_end, session_end)

        if overlap_start >= overlap_end:
            return None  # No overlap

        overlap_hours = (overlap_end - overlap_start).total_seconds() / 3600
        session_duration_seconds = session.get("duration_seconds", 0)

        # Get session analysis and calculate metrics
        session_report, session_util = self._get_weekly_session_analysis(session)

        # Calculate proportional active time and weighted utilization
        active_time_hours = overlap_hours * (session_util / 100)
        weighted_utilization = session_util * overlap_hours

        # Filter experiments to overlap
        session_experiments = [
            exp
            for exp in experiments
            if (
                exp
                and isinstance(exp, dict)
                and exp.get("event_timestamp")
                and overlap_start <= exp["event_timestamp"] <= overlap_end
            )
        ]

        # Create session fragment
        session_fragment = {
            "session_type": session.get("session_type", "unknown"),
            "session_id": session.get("session_id", "unknown"),
            "session_name": session.get("session_name", "Unknown Session"),
            "start_time": overlap_start.isoformat(),
            "end_time": overlap_end.isoformat(),
            "duration_hours": overlap_hours,
            "active_time_hours": active_time_hours,
            "total_experiments": len(session_experiments),
            "system_utilization_percent": session_util,
            "node_utilizations": session_report.get("node_utilizations", {}),
            "experiment_details": [
                {
                    "experiment_id": exp.get("experiment_id", ""),
                    "experiment_name": self.analyzer._resolve_experiment_name(
                        exp.get("experiment_id", "")
                    ),
                    "display_name": f"Experiment {exp.get('experiment_id', '')[-8:]}",
                }
                for exp in session_experiments
                if exp and exp.get("experiment_id")
            ],
            "attribution_method": "weekly_session_overlap",
        }

        # Calculate proportion for node utilization
        proportion = (
            overlap_hours / (session_duration_seconds / 3600)
            if session_duration_seconds > 0
            else 0
        )

        return {
            "fragment": session_fragment,
            "runtime_hours": overlap_hours,
            "active_hours": active_time_hours,
            "weighted_utilization": weighted_utilization,
            "node_data": session_report.get("node_utilizations", {}),
            "proportion": proportion,
        }

    def _get_weekly_session_analysis(
        self, session: Dict
    ) -> Tuple[Dict[str, Any], float]:
        """Get session analysis for weekly processing with error handling."""

        if session.get("duration_seconds", 0) > 0:
            try:
                session_report = self.analyzer._analyze_session_utilization(session)
                if session_report and isinstance(session_report, dict):
                    session_util = session_report.get("system_utilization_percent", 0)
                    return session_report, session_util
            except Exception as e:
                logger.error(f"Error analyzing session for weekly report: {e}")

        return {}, 0

    def _accumulate_node_data_for_weekly(
        self, week_node_utilizations: Dict, session_nodes: Dict, proportion: float
    ) -> None:
        """Accumulate node utilization data for weekly analysis."""

        if not session_nodes or not isinstance(session_nodes, dict):
            return

        for node_id, node_data in session_nodes.items():
            if not node_data or not isinstance(node_data, dict):
                continue

            if node_id not in week_node_utilizations:
                week_node_utilizations[node_id] = {
                    "utilizations": [],
                    "busy_hours": 0,
                    "node_info": node_data,
                }

            # Add proportional busy time for this week
            proportional_busy_time = node_data.get("busy_time_hours", 0) * proportion
            week_node_utilizations[node_id]["busy_hours"] += proportional_busy_time
            week_node_utilizations[node_id]["utilizations"].append(
                node_data.get("utilization_percent", 0)
            )

    def _build_final_weekly_report(
        self,
        week_data: Dict,
        bucket_start: datetime,
        bucket_end: datetime,
        bucket_index: int,
        period_info: Dict,
    ) -> Dict[str, Any]:
        """Build the final weekly bucket report."""

        # Process final node utilizations
        final_node_utilizations = {}
        for node_id, node_info in week_data["node_utilizations"].items():
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
                    "total": week_data["runtime"],
                },
            }

        return {
            "session_details": week_data["sessions"],
            "overall_summary": {
                "total_sessions": len(week_data["sessions"]),
                "total_system_runtime_hours": week_data["runtime"],
                "total_active_time_hours": week_data["active_time"],
                "average_system_utilization_percent": week_data["utilization"],
                "total_experiments": week_data["experiments_count"],
                "nodes_tracked": len(final_node_utilizations),
                "node_summary": {
                    node_id: {
                        "average_utilization_percent": node_data["utilization_percent"],
                        "total_busy_time_hours": node_data["busy_time_hours"],
                        "sessions_active": 1,
                    }
                    for node_id, node_data in final_node_utilizations.items()
                },
                "method": "weekly_proper_runtime_calculation",
            },
            "time_bucket": {
                "bucket_index": bucket_index,
                "start_time": bucket_start.isoformat(),
                "end_time": bucket_end.isoformat(),
                "duration_hours": (bucket_end - bucket_start).total_seconds() / 3600,
                "period_info": period_info,
            },
        }

    def _create_error_weekly_bucket_report(
        self,
        bucket_start: datetime,
        bucket_end: datetime,
        bucket_index: int,
        period_info: Dict,
        error_message: str,
    ) -> Dict[str, Any]:
        """Create a minimal error bucket report for weekly analysis."""

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
                "method": "weekly_error_fallback",
            },
            "time_bucket": {
                "bucket_index": bucket_index,
                "start_time": bucket_start.isoformat(),
                "end_time": bucket_end.isoformat(),
                "duration_hours": (bucket_end - bucket_start).total_seconds() / 3600,
                "period_info": period_info,
            },
            "error": f"Weekly bucket generation failed: {error_message}",
        }

    def _create_daily_buckets_from_sessions(
        self,
        time_buckets: List,
        sessions: List[Dict],
        start_time: datetime,
        end_time: datetime,
    ) -> List[Dict]:
        """Create daily bucket reports with FIXED session attribution and node summary."""

        # Validate inputs and filter sessions
        if not time_buckets:
            logger.warning("No time buckets provided for daily analysis")
            return []

        if not sessions:
            logger.warning("No sessions provided for daily analysis")
            sessions = []

        filtered_sessions = self._filter_sessions_to_analysis_period(
            sessions, start_time, end_time
        )

        # Process each time bucket
        bucket_reports = []
        for i, bucket_info in enumerate(time_buckets):
            bucket_report = self._process_single_daily_bucket(
                i, bucket_info, filtered_sessions, start_time, end_time
            )
            bucket_reports.append(bucket_report)

        return bucket_reports

    def _process_single_daily_bucket(
        self,
        bucket_index: int,
        bucket_info: Any,
        filtered_sessions: List[Dict],
        start_time: datetime,
        end_time: datetime,
    ) -> Dict[str, Any]:
        """Process a single daily bucket with comprehensive error handling."""

        try:
            # Extract and validate bucket data
            bucket_data = self._extract_and_validate_daily_bucket_data(
                bucket_info, bucket_index, start_time, end_time
            )

            if not bucket_data:
                return self._create_error_daily_bucket_report(
                    bucket_index, "Invalid bucket data"
                )

            bucket_start, bucket_end = bucket_data["times"]

            # Get experiments and process sessions for this day
            experiments = self._get_experiments_safely(
                bucket_start, bucket_end, bucket_index
            )
            day_data = self._process_all_sessions_for_day(
                filtered_sessions, bucket_start, bucket_end, experiments, bucket_index
            )

            # Create and return final report
            return self._build_final_daily_report(
                day_data, bucket_data, bucket_start, bucket_end, bucket_index
            )

        except Exception as e:
            logger.error(f"Error processing daily bucket {bucket_index}: {e}")
            return self._create_error_daily_bucket_report(bucket_index, str(e))

    def _extract_and_validate_daily_bucket_data(
        self,
        bucket_info: Any,
        bucket_index: int,
        start_time: datetime,
        end_time: datetime,
    ) -> Optional[Dict[str, Any]]:
        """Extract daily bucket data and validate/adjust times."""

        # Extract bucket information
        if isinstance(bucket_info, dict):
            bucket_start, bucket_end = bucket_info["utc_times"]
            user_start, _ = bucket_info["user_times"]
            period_info = bucket_info.get("period_info", {})
        else:
            bucket_start, bucket_end = bucket_info
            user_start, _ = bucket_start, bucket_end
            period_info = {"type": "period", "display": user_start.strftime("%Y-%m-%d")}

        # Validate and adjust bucket times
        if bucket_start < start_time or bucket_end > end_time:
            logger.warning(
                f"Daily bucket {bucket_index} extends outside analysis period, clipping to bounds"
            )
            bucket_start = max(bucket_start, start_time)
            bucket_end = min(bucket_end, end_time)

        if not bucket_start or not bucket_end or bucket_start >= bucket_end:
            logger.warning(f"Invalid bucket times for daily bucket {bucket_index}")
            return None

        return {
            "times": (bucket_start, bucket_end),
            "user_start": user_start,
            "period_info": period_info,
        }

    def _process_all_sessions_for_day(
        self,
        filtered_sessions: List[Dict],
        bucket_start: datetime,
        bucket_end: datetime,
        experiments: List[Dict],
        bucket_index: int,
    ) -> Dict[str, Any]:
        """Process all sessions and accumulate data for the daily bucket."""

        day_sessions = []
        total_day_runtime = 0
        total_day_active_time = 0
        day_node_utilizations = {}

        for session in filtered_sessions:
            try:
                session_result = self._process_daily_session_overlap_and_analysis(
                    session, bucket_start, bucket_end, experiments
                )

                if session_result:
                    day_sessions.append(session_result["fragment"])
                    total_day_runtime += session_result["runtime_hours"]
                    total_day_active_time += session_result["active_hours"]

                    # Accumulate node utilizations
                    self._accumulate_node_data(
                        day_node_utilizations, session_result["node_data"]
                    )

            except Exception as e:
                logger.error(
                    f"Error processing session for daily bucket {bucket_index}: {e}"
                )
                continue

        return {
            "sessions": day_sessions,
            "total_runtime": total_day_runtime,
            "total_active_time": total_day_active_time,
            "experiments_count": len(experiments),
            "node_utilizations": day_node_utilizations,
        }

    def _process_daily_session_overlap_and_analysis(
        self,
        session: Dict,
        bucket_start: datetime,
        bucket_end: datetime,
        experiments: List[Dict],
    ) -> Optional[Dict[str, Any]]:
        """Process session overlap with daily bucket and perform analysis."""

        session_start = session.get("start_time")
        session_end = session.get("end_time")

        if not session_start or not session_end:
            return None

        # Calculate overlap
        overlap_start = max(bucket_start, session_start)
        overlap_end = min(bucket_end, session_end)

        if overlap_start >= overlap_end:
            return None  # No overlap

        overlap_hours = (overlap_end - overlap_start).total_seconds() / 3600

        # Get session analysis with error handling
        try:
            session_report = self.analyzer._analyze_session_utilization(session)
            if not isinstance(session_report, dict):
                session_report = {}
        except Exception as e:
            logger.error(f"Error analyzing session for daily bucket: {e}")
            session_report = {}

        # Extract session metrics with safety checks
        session_util = session_report.get("system_utilization_percent", 0) or 0
        session_active_time = session_report.get("active_time_hours", 0) or 0
        session_duration = session_report.get("duration_hours", 0) or 0

        # Calculate proportional active time for this day
        if session_duration > 0:
            proportion = overlap_hours / session_duration
            proportional_active_time = session_active_time * proportion
        else:
            proportional_active_time = overlap_hours * (session_util / 100)

        # Filter experiments to overlap and create session fragment
        session_experiments = []
        if experiments:
            try:
                session_experiments = [
                    exp
                    for exp in experiments
                    if (
                        exp
                        and isinstance(exp, dict)
                        and exp.get("event_timestamp")
                        and overlap_start <= exp["event_timestamp"] <= overlap_end
                    )
                ]
            except Exception as e:
                logger.error(f"Error filtering session experiments: {e}")

        session_fragment = {
            "session_type": session.get("session_type", "unknown"),
            "session_id": session.get("session_id", "unknown"),
            "session_name": session.get("session_name", "Unknown Session"),
            "start_time": overlap_start.isoformat(),
            "end_time": overlap_end.isoformat(),
            "duration_hours": overlap_hours,
            "active_time_hours": proportional_active_time,
            "total_experiments": len(session_experiments),
            "system_utilization_percent": session_util,
            "node_utilizations": session_report.get("node_utilizations", {}),
            "experiment_details": [
                {
                    "experiment_id": exp.get("experiment_id", ""),
                    "experiment_name": self.analyzer._resolve_experiment_name(
                        exp.get("experiment_id", "")
                    ),
                    "display_name": f"Experiment {exp.get('experiment_id', '')[-8:]}",
                }
                for exp in session_experiments
                if exp and exp.get("experiment_id")
            ],
            "attribution_method": "daily_proportional_from_session_with_bounds_check",
        }

        return {
            "fragment": session_fragment,
            "runtime_hours": overlap_hours,
            "active_hours": proportional_active_time,
            "node_data": session_report.get("node_utilizations", {}),
        }

    def _build_final_daily_report(
        self,
        day_data: Dict,
        bucket_data: Dict,
        bucket_start: datetime,
        bucket_end: datetime,
        bucket_index: int,
    ) -> Dict[str, Any]:
        """Build the final daily bucket report."""

        # Process final node utilizations
        final_node_utilizations = {}
        for node_id, node_info in day_data["node_utilizations"].items():
            try:
                if not node_info or not isinstance(node_info, dict):
                    continue

                utilizations = node_info.get("utilizations", [])
                avg_utilization = statistics.mean(utilizations) if utilizations else 0

                base_info = node_info.get("node_info", {})
                busy_hours = node_info.get("busy_hours", 0) or 0

                final_node_utilizations[node_id] = {
                    "node_id": node_id,
                    "node_name": base_info.get("node_name")
                    if isinstance(base_info, dict)
                    else None,
                    "display_name": base_info.get("display_name")
                    if isinstance(base_info, dict)
                    else None,
                    "utilization_percent": round(avg_utilization, 1),
                    "busy_time_hours": round(busy_hours, 3),
                    "timing": base_info.get("timing", {})
                    if isinstance(base_info, dict)
                    else {},
                    "raw_hours": {
                        "busy": busy_hours,
                        "idle": max(0, day_data["total_runtime"] - busy_hours),
                        "total": day_data["total_runtime"],
                    },
                }
            except Exception as e:
                logger.error(
                    f"Error processing final node utilization for {node_id}: {e}"
                )
                continue

        # Calculate day utilization
        day_utilization = (
            (day_data["total_active_time"] / day_data["total_runtime"] * 100)
            if day_data["total_runtime"] > 0
            else 0
        )

        return {
            "session_details": day_data["sessions"],
            "overall_summary": {
                "total_sessions": len(day_data["sessions"]),
                "total_system_runtime_hours": day_data["total_runtime"],
                "total_active_time_hours": day_data["total_active_time"],
                "average_system_utilization_percent": day_utilization,
                "total_experiments": day_data["experiments_count"],
                "nodes_tracked": len(final_node_utilizations),
                "node_summary": {
                    node_id: {
                        "average_utilization_percent": node_data["utilization_percent"],
                        "total_busy_time_hours": node_data["busy_time_hours"],
                        "sessions_active": 1,
                    }
                    for node_id, node_data in final_node_utilizations.items()
                },
                "method": "daily_with_bounds_validation_and_comprehensive_error_handling",
            },
            "time_bucket": {
                "bucket_index": bucket_index,
                "start_time": bucket_start.isoformat(),
                "end_time": bucket_end.isoformat(),
                "user_start_time": bucket_data["user_start"].strftime(
                    "%Y-%m-%dT%H:%M:%S"
                )
                if bucket_data["user_start"]
                else "",
                "user_date": bucket_data["user_start"].strftime("%Y-%m-%d")
                if bucket_data["user_start"]
                else "",
                "duration_hours": (bucket_end - bucket_start).total_seconds() / 3600,
                "period_info": bucket_data["period_info"],
            },
        }

    def _create_error_daily_bucket_report(
        self, bucket_index: int, error_message: str
    ) -> Dict[str, Any]:
        """Create a minimal error bucket report for daily analysis."""

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
                "method": "daily_error_fallback",
            },
            "time_bucket": {
                "bucket_index": bucket_index,
                "start_time": "",
                "end_time": "",
                "user_start_time": "",
                "user_date": "",
                "duration_hours": 0,
                "period_info": {"type": "day", "display": "Error", "short": "Error"},
            },
            "error": f"Daily bucket processing failed: {error_message}",
        }

    def _create_monthly_buckets_from_sessions(
        self,
        time_buckets: List,
        sessions: List[Dict],
        start_time: datetime,
        end_time: datetime,
    ) -> List[Dict]:
        """Create monthly bucket reports with FIXED session attribution and comprehensive error handling."""

        # Validate inputs and filter sessions
        if not time_buckets:
            logger.warning("No time buckets provided for monthly analysis")
            return []

        if not sessions:
            logger.warning("No sessions provided for monthly analysis")
            sessions = []

        filtered_sessions = self._filter_sessions_to_analysis_period(
            sessions, start_time, end_time
        )

        # Process each time bucket
        bucket_reports = []
        for i, bucket_info in enumerate(time_buckets):
            bucket_report = self._process_single_monthly_bucket(
                i, bucket_info, filtered_sessions, start_time, end_time
            )
            bucket_reports.append(bucket_report)

        return bucket_reports

    def _filter_sessions_to_analysis_period(
        self, sessions: List[Dict], start_time: datetime, end_time: datetime
    ) -> List[Dict]:
        """Filter sessions to only include those overlapping with analysis period."""

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

        return filtered_sessions

    def _process_single_monthly_bucket(
        self,
        bucket_index: int,
        bucket_info: Any,
        filtered_sessions: List[Dict],
        start_time: datetime,
        end_time: datetime,
    ) -> Dict[str, Any]:
        """Process a single monthly bucket with comprehensive error handling."""

        try:
            # Extract and validate bucket data
            bucket_data = self._extract_and_validate_bucket_data(
                bucket_info, bucket_index, start_time, end_time
            )

            if not bucket_data:
                return self._create_error_bucket_report(
                    bucket_index, "Invalid bucket data"
                )

            bucket_start, bucket_end = bucket_data["times"]

            # Get experiments and process sessions for this month
            experiments = self._get_experiments_safely(
                bucket_start, bucket_end, bucket_index
            )
            month_data = self._process_all_sessions_for_month(
                filtered_sessions, bucket_start, bucket_end, experiments, bucket_index
            )

            # Create and return final report
            return self._build_final_monthly_report(
                month_data, bucket_data, bucket_start, bucket_end, bucket_index
            )

        except Exception as e:
            logger.error(f"Error processing bucket {bucket_index}: {e}")
            return self._create_error_bucket_report(bucket_index, str(e))

    def _extract_and_validate_bucket_data(
        self,
        bucket_info: Any,
        bucket_index: int,
        start_time: datetime,
        end_time: datetime,
    ) -> Optional[Dict[str, Any]]:
        """Extract bucket data and validate/adjust times."""

        # Extract bucket information
        if isinstance(bucket_info, dict):
            bucket_start, bucket_end = bucket_info["utc_times"]
            user_start, _ = bucket_info["user_times"]
            period_info = bucket_info.get("period_info", {})
        else:
            bucket_start, bucket_end = bucket_info
            user_start, _ = bucket_start, bucket_end
            period_info = {"type": "period", "display": user_start.strftime("%Y-%m")}

        # Validate and adjust bucket times
        if bucket_start < start_time or bucket_end > end_time:
            logger.warning(
                f"Bucket {bucket_index} extends outside analysis period, clipping to bounds"
            )
            bucket_start = max(bucket_start, start_time)
            bucket_end = min(bucket_end, end_time)

        if not bucket_start or not bucket_end or bucket_start >= bucket_end:
            logger.warning(f"Invalid bucket times for bucket {bucket_index}")
            return None

        return {
            "times": (bucket_start, bucket_end),
            "user_start": user_start,
            "period_info": period_info,
        }

    def _get_experiments_safely(
        self, bucket_start: datetime, bucket_end: datetime, bucket_index: int
    ) -> List[Dict]:
        """Get experiments for bucket with error handling."""

        try:
            experiments = self._get_experiments_in_time_period(bucket_start, bucket_end)
            return experiments if experiments is not None else []
        except Exception as e:
            logger.error(f"Error getting experiments for bucket {bucket_index}: {e}")
            return []

    def _process_all_sessions_for_month(
        self,
        filtered_sessions: List[Dict],
        bucket_start: datetime,
        bucket_end: datetime,
        experiments: List[Dict],
        bucket_index: int,
    ) -> Dict[str, Any]:
        """Process all sessions and accumulate data for the monthly bucket."""

        month_sessions = []
        total_month_runtime = 0
        total_month_active_time = 0
        month_node_utilizations = {}

        for session in filtered_sessions:
            try:
                session_result = self._process_session_overlap_and_analysis(
                    session, bucket_start, bucket_end, experiments
                )

                if session_result:
                    month_sessions.append(session_result["fragment"])
                    total_month_runtime += session_result["runtime_hours"]
                    total_month_active_time += session_result["active_hours"]

                    # Accumulate node utilizations
                    self._accumulate_node_data(
                        month_node_utilizations, session_result["node_data"]
                    )

            except Exception as e:
                logger.error(
                    f"Error processing session for month bucket {bucket_index}: {e}"
                )
                continue

        return {
            "sessions": month_sessions,
            "total_runtime": total_month_runtime,
            "total_active_time": total_month_active_time,
            "experiments_count": len(experiments),
            "node_utilizations": month_node_utilizations,
        }

    def _process_session_overlap_and_analysis(
        self,
        session: Dict,
        bucket_start: datetime,
        bucket_end: datetime,
        experiments: List[Dict],
    ) -> Optional[Dict[str, Any]]:
        """Process session overlap with bucket and perform analysis."""

        session_start = session.get("start_time")
        session_end = session.get("end_time")

        # Calculate overlap
        overlap_start = max(bucket_start, session_start)
        overlap_end = min(bucket_end, session_end)

        if overlap_start >= overlap_end:
            return None  # No overlap

        overlap_hours = (overlap_end - overlap_start).total_seconds() / 3600

        # Get session analysis with error handling
        try:
            session_report = self.analyzer._analyze_session_utilization(session)
            if not isinstance(session_report, dict):
                session_report = {}
        except Exception as e:
            logger.error(f"Error analyzing session: {e}")
            session_report = {}

        # Extract session metrics with safety checks
        session_util = session_report.get("system_utilization_percent", 0) or 0
        session_active_time = session_report.get("active_time_hours", 0) or 0
        session_duration = session_report.get("duration_hours", 0) or 0

        # Calculate proportional active time
        if session_duration > 0:
            proportion = overlap_hours / session_duration
            proportional_active_time = session_active_time * proportion
        else:
            proportional_active_time = overlap_hours * (session_util / 100)

        # Filter experiments to overlap and create session fragment
        session_experiments = [
            exp
            for exp in experiments
            if (
                exp
                and isinstance(exp, dict)
                and exp.get("event_timestamp")
                and overlap_start <= exp["event_timestamp"] <= overlap_end
            )
        ]

        session_fragment = {
            "session_type": session.get("session_type", "unknown"),
            "session_id": session.get("session_id", "unknown"),
            "session_name": session.get("session_name", "Unknown Session"),
            "start_time": overlap_start.isoformat(),
            "end_time": overlap_end.isoformat(),
            "duration_hours": overlap_hours,
            "active_time_hours": proportional_active_time,
            "total_experiments": len(session_experiments),
            "system_utilization_percent": session_util,
            "experiment_details": [
                {
                    "experiment_id": exp.get("experiment_id", ""),
                    "experiment_name": self.analyzer._resolve_experiment_name(
                        exp.get("experiment_id", "")
                    ),
                    "display_name": f"Experiment {exp.get('experiment_id', '')[-8:]}",
                }
                for exp in session_experiments
                if exp and exp.get("experiment_id")
            ],
            "attribution_method": "monthly_proportional_from_real_session_fixed_with_bounds_check",
        }

        return {
            "fragment": session_fragment,
            "runtime_hours": overlap_hours,
            "active_hours": proportional_active_time,
            "node_data": session_report.get("node_utilizations", {}),
        }

    def _accumulate_node_data(
        self, month_node_utilizations: Dict, session_nodes: Dict
    ) -> None:
        """Accumulate node utilization data from session."""

        if not session_nodes or not isinstance(session_nodes, dict):
            return

        for node_id, node_data in session_nodes.items():
            if not node_data or not isinstance(node_data, dict):
                continue

            if node_id not in month_node_utilizations:
                month_node_utilizations[node_id] = {
                    "utilizations": [],
                    "busy_hours": 0,
                    "node_info": node_data,
                }

            node_util_percent = node_data.get("utilization_percent", 0) or 0
            node_busy_hours = node_data.get("busy_time_hours", 0) or 0

            month_node_utilizations[node_id]["utilizations"].append(node_util_percent)
            month_node_utilizations[node_id]["busy_hours"] += node_busy_hours

    def _build_final_monthly_report(
        self,
        month_data: Dict,
        bucket_data: Dict,
        bucket_start: datetime,
        bucket_end: datetime,
        bucket_index: int,
    ) -> Dict[str, Any]:
        """Build the final monthly bucket report."""

        # Process final node utilizations
        final_node_utilizations = {}
        for node_id, node_info in month_data["node_utilizations"].items():
            try:
                if not node_info or not isinstance(node_info, dict):
                    continue

                utilizations = node_info.get("utilizations", [])
                avg_utilization = statistics.mean(utilizations) if utilizations else 0

                base_info = node_info.get("node_info", {})
                busy_hours = node_info.get("busy_hours", 0) or 0

                final_node_utilizations[node_id] = {
                    "node_id": node_id,
                    "node_name": base_info.get("node_name")
                    if isinstance(base_info, dict)
                    else None,
                    "display_name": base_info.get("display_name")
                    if isinstance(base_info, dict)
                    else None,
                    "utilization_percent": round(avg_utilization, 1),
                    "busy_time_hours": round(busy_hours, 3),
                    "timing": base_info.get("timing", {})
                    if isinstance(base_info, dict)
                    else {},
                    "raw_hours": {
                        "busy": busy_hours,
                        "idle": max(0, month_data["total_runtime"] - busy_hours),
                        "total": month_data["total_runtime"],
                    },
                }
            except Exception as e:
                logger.error(
                    f"Error processing final node utilization for {node_id}: {e}"
                )
                continue

        # Calculate month utilization
        month_utilization = (
            (month_data["total_active_time"] / month_data["total_runtime"] * 100)
            if month_data["total_runtime"] > 0
            else 0
        )

        return {
            "session_details": month_data["sessions"],
            "overall_summary": {
                "total_sessions": len(month_data["sessions"]),
                "total_system_runtime_hours": month_data["total_runtime"],
                "total_active_time_hours": month_data["total_active_time"],
                "average_system_utilization_percent": month_utilization,
                "total_experiments": month_data["experiments_count"],
                "nodes_tracked": len(final_node_utilizations),
                "node_summary": {
                    node_id: {
                        "average_utilization_percent": node_data["utilization_percent"],
                        "total_busy_time_hours": node_data["busy_time_hours"],
                        "sessions_active": 1,
                    }
                    for node_id, node_data in final_node_utilizations.items()
                },
                "method": "monthly_fixed_with_bounds_validation",
            },
            "time_bucket": {
                "bucket_index": bucket_index,
                "start_time": bucket_start.isoformat(),
                "end_time": bucket_end.isoformat(),
                "user_start_time": bucket_data["user_start"].strftime(
                    "%Y-%m-%dT%H:%M:%S"
                )
                if bucket_data["user_start"]
                else "",
                "user_date": bucket_data["user_start"].strftime("%Y-%m")
                if bucket_data["user_start"]
                else "",
                "duration_hours": (bucket_end - bucket_start).total_seconds() / 3600,
                "period_info": bucket_data["period_info"],
            },
        }

    def _create_error_bucket_report(
        self, bucket_index: int, error_message: str
    ) -> Dict[str, Any]:
        """Create a minimal error bucket report."""

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
                "method": "monthly_error_fallback",
            },
            "time_bucket": {
                "bucket_index": bucket_index,
                "start_time": "",
                "end_time": "",
                "user_start_time": "",
                "user_date": "",
                "duration_hours": 0,
                "period_info": {"type": "month", "display": "Error", "short": "Error"},
            },
            "error": f"Bucket processing failed: {error_message}",
        }

    def _get_experiments_in_time_period(
        self, start_time: datetime, end_time: datetime
    ) -> List[Dict]:
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
                "event_timestamp": {"$gte": start_time, "$lte": end_time},
            },
            {
                "event_type": {"$in": ["experiment_start", "EXPERIMENT_START"]},
                "event_timestamp": {
                    "$gte": start_time.isoformat(),
                    "$lte": end_time.isoformat(),
                },
            },
        ]

        for query in queries_to_try:
            try:
                events = list(
                    self.events_collection.find(query).sort("event_timestamp", 1)
                )
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

                event_time = self.analyzer._parse_timestamp_utc(
                    event.get("event_timestamp")
                )
                if event_time and start_time <= event_time <= end_time:
                    experiment_id = self.analyzer._extract_experiment_id(event)
                    if experiment_id:
                        valid_experiments.append(
                            {
                                "experiment_id": experiment_id,
                                "event_timestamp": event_time,
                                "event_data": event.get("event_data", {}),
                            }
                        )
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
        user_timezone: str,
    ) -> Dict[str, Any]:
        """Create clean summary report format with experiment details included."""

        try:
            logger.info(
                f"Creating summary report from {len(bucket_reports) if bucket_reports else 0} bucket reports"
            )

            # Validate input parameters
            if not start_time or not end_time:
                logger.error(
                    "start_time or end_time is None in summary report creation"
                )
                return {
                    "error": "Invalid time parameters for summary report",
                    "summary_metadata": {
                        "analysis_type": analysis_type,
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                        "error_occurred": True,
                        "error_details": "start_time or end_time is None",
                    },
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
            node_summary_clean = self._create_node_summary(
                aggregated_data["node_metrics"], analysis_type
            )
            workcell_summary_clean = self._create_workcell_summary(
                aggregated_data["workcell_metrics"], analysis_type
            )

            # Calculate trends
            trends = self._calculate_trends_from_time_series(
                aggregated_data["time_series_points"]
            )

            # Calculate system-level metrics and peak info
            system_metrics = self._calculate_system_metrics(
                bucket_reports, aggregated_data, analysis_type
            )

            logger.info(
                f"Final summary: {len(node_summary_clean)} nodes, {len(workcell_summary_clean)} workcells"
            )

            return {
                "summary_metadata": {
                    "analysis_type": analysis_type,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "period_start": start_time.isoformat(),
                    "period_end": end_time.isoformat(),
                    "user_timezone": user_timezone,
                    "total_periods": len(bucket_reports),
                    "method": "session_based_analysis_with_experiment_details_refactored",
                },
                "key_metrics": {
                    "average_utilization": system_metrics["average_utilization"],
                    **system_metrics["peak_info"],
                    "total_experiments": sum(aggregated_data["all_experiments"])
                    if aggregated_data["all_experiments"]
                    else 0,
                    "total_runtime_hours": round(
                        sum(aggregated_data["all_runtime_hours"])
                        if aggregated_data["all_runtime_hours"]
                        else 0,
                        2,
                    ),
                    "total_active_time_hours": round(
                        sum(aggregated_data["all_active_time_hours"])
                        if aggregated_data["all_active_time_hours"]
                        else 0,
                        2,
                    ),
                    "active_periods": len(aggregated_data["all_utilizations"]),
                    "total_periods": len(bucket_reports),
                },
                "node_summary": node_summary_clean,
                "workcell_summary": workcell_summary_clean,
                "trends": trends,
                "experiment_details": {
                    "total_experiments": len(complete_experiment_details)
                    if complete_experiment_details
                    else 0,
                    "experiments": (
                        complete_experiment_details[:50]
                        if complete_experiment_details
                        else []
                    ),
                },
                "time_series": {
                    "system": aggregated_data["time_series_points"],
                    "nodes": {
                        node_id: node_data["time_series"]
                        for node_id, node_data in aggregated_data[
                            "node_metrics"
                        ].items()
                        if node_id in aggregated_data["actual_node_ids"]
                        and node_data.get("time_series")
                    },
                    "workcells": {
                        workcell_id: workcell_data["time_series"]
                        for workcell_id, workcell_data in aggregated_data[
                            "workcell_metrics"
                        ].items()
                        if workcell_id in aggregated_data["actual_workcell_ids"]
                        and workcell_data.get("time_series")
                    },
                },
            }

        except Exception as e:
            logger.error(f"Error in summary report creation: {e}")
            # Ensure we have valid start_time and end_time for error response
            period_start = start_time.isoformat() if start_time else None
            period_end = end_time.isoformat() if end_time else None

            return {
                "error": f"Failed to generate summary: {e!s}",
                "summary_metadata": {
                    "analysis_type": analysis_type,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "period_start": period_start,
                    "period_end": period_end,
                    "error_occurred": True,
                    "error_details": str(e),
                },
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

        node_metrics = defaultdict(
            lambda: {"utilizations": [], "busy_hours": 0, "time_series": []}
        )

        workcell_metrics = defaultdict(
            lambda: {
                "utilizations": [],
                "experiments": [],
                "runtime_hours": [],
                "time_series": [],
                "active_time_hours": [],
            }
        )

        time_series_points = []
        actual_node_ids = set()
        actual_workcell_ids = set()
        all_experiment_details = []

        # Process each bucket report
        for bucket_report in bucket_reports:
            if not bucket_report or not isinstance(bucket_report, dict):
                continue

            if "error" in bucket_report:
                logger.warning(
                    f"Skipping bucket report with error: {bucket_report.get('error')}"
                )
                continue

            # Extract basic data
            overall_summary = bucket_report.get("overall_summary", {})
            session_details = bucket_report.get("session_details", [])
            time_bucket = bucket_report.get("time_bucket", {})

            # Get period info for labeling
            period_info = time_bucket.get(
                "period_info",
                {
                    "type": "period",
                    "display": time_bucket.get("user_date", ""),
                    "short": time_bucket.get("user_date", ""),
                },
            )

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
            self._process_node_data(
                overall_summary, time_bucket, period_info, node_metrics, actual_node_ids
            )

            # Process workcell data
            self._process_workcell_data(
                session_details,
                time_bucket,
                period_info,
                workcell_metrics,
                actual_workcell_ids,
            )

            # Add to system time series
            time_series_points.append(
                {
                    "period_number": time_bucket.get("bucket_index", 0) + 1,
                    "period_type": period_info.get("type", "period"),
                    "period_display": period_info.get("display", ""),
                    "date": time_bucket.get("user_date", ""),
                    "start_time": time_bucket.get("user_start_time", ""),
                    "start_time_utc": time_bucket.get("start_time", ""),
                    "utilization": avg_util,
                    "experiments": total_exp,
                    "runtime_hours": total_runtime,
                    "active_time_hours": total_active_time,
                }
            )

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
            "all_experiment_details": all_experiment_details,
        }

    def _extract_experiment_details(
        self, session_details: List[Dict], all_experiment_details: List[Dict]
    ) -> None:
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
                if exp_id and not any(
                    existing.get("experiment_id") == exp_id
                    for existing in all_experiment_details
                ):
                    all_experiment_details.append(exp)

    def _process_node_data(
        self,
        overall_summary: Dict,
        time_bucket: Dict,
        period_info: Dict,
        node_metrics: Dict,
        actual_node_ids: set,
    ) -> None:
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
            node_metrics[node_id]["time_series"].append(
                {
                    "period_number": time_bucket.get("bucket_index", 0) + 1,
                    "period_type": period_info.get("type", "period"),
                    "period_display": period_info.get("display", ""),
                    "date": time_bucket.get("user_date", ""),
                    "utilization": utilization,
                    "busy_hours": busy_hours,
                }
            )

    def _process_workcell_data(
        self,
        session_details: List[Dict],
        time_bucket: Dict,
        period_info: Dict,
        workcell_metrics: Dict,
        actual_workcell_ids: set,
    ) -> None:
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
                workcell_metrics[session_id]["active_time_hours"].append(
                    session_active_time
                )

                # Add time series if there's runtime
                if session_runtime > 0:
                    attribution_info = session.get("attribution_info")
                    workcell_metrics[session_id]["time_series"].append(
                        {
                            "period_number": time_bucket.get("bucket_index", 0) + 1,
                            "period_type": period_info.get("type", "period"),
                            "period_display": period_info.get("display", ""),
                            "date": time_bucket.get("user_date", ""),
                            "utilization": session_util,
                            "experiments": session_exp,
                            "runtime_hours": session_runtime,
                            "active_time_hours": session_active_time,
                            "attributed": bool(attribution_info),
                        }
                    )

    def _create_node_summary(
        self, node_metrics: Dict, analysis_type: str
    ) -> Dict[str, Any]:
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
                    "display_name": f"{node_name} ({node_id[-8:]})"
                    if node_name
                    else f"Node {node_id[-8:]}",
                    "average_utilization": round(
                        statistics.mean(data["utilizations"])
                        if data["utilizations"]
                        else 0,
                        2,
                    ),
                    **peak_info,
                    "total_busy_hours": round(data["busy_hours"], 2),
                }
            except Exception as e:
                logger.error(f"Error processing node summary for {node_id}: {e}")
                continue

        return node_summary_clean

    def _create_workcell_summary(
        self, workcell_metrics: Dict, analysis_type: str
    ) -> Dict[str, Any]:
        """Create clean workcell summary from aggregated metrics."""

        workcell_summary_clean = {}

        for workcell_id, data in workcell_metrics.items():
            try:
                workcell_name = self._resolve_workcell_name(workcell_id)

                # Calculate peak info with context - FIXED to find actual peak
                peak_info = self._find_actual_peak_info(data, analysis_type)

                # Better display name
                if (
                    workcell_name.startswith("Workcell ")
                    and workcell_id[-8:] in workcell_name
                ):
                    display_name = workcell_name
                else:
                    display_name = f"{workcell_name} ({workcell_id[-8:]})"

                workcell_summary_clean[workcell_id] = {
                    "workcell_id": workcell_id,
                    "workcell_name": workcell_name,
                    "display_name": display_name,
                    "average_utilization": round(
                        statistics.mean(data["utilizations"])
                        if data["utilizations"]
                        else 0,
                        2,
                    ),
                    **peak_info,
                    "total_experiments": sum(data["experiments"])
                    if data["experiments"]
                    else 0,
                    "total_runtime_hours": round(
                        sum(data["runtime_hours"]) if data["runtime_hours"] else 0, 2
                    ),
                    "total_active_time_hours": round(
                        sum(data["active_time_hours"])
                        if data["active_time_hours"]
                        else 0,
                        2,
                    ),
                }
            except Exception as e:
                logger.error(
                    f"Error processing workcell summary for {workcell_id}: {e}"
                )
                continue

        return workcell_summary_clean

    def _calculate_system_metrics(
        self, bucket_reports: List[Dict], aggregated_data: Dict, analysis_type: str
    ) -> Dict[str, Any]:
        """Calculate system-level metrics and peak information."""

        # Safety check for inputs
        if not aggregated_data or not isinstance(aggregated_data, dict):
            logger.warning(
                "Invalid aggregated_data provided to system metrics calculation"
            )
            return {
                "average_utilization": 0,
                "peak_info": {
                    "peak_utilization": 0,
                    "peak_period": None,
                    "peak_context": "No data available",
                },
            }

        try:
            if analysis_type == "monthly":
                # For monthly: recalculate utilization from raw runtime/active time
                all_runtime_hours = aggregated_data.get("all_runtime_hours", [])
                all_active_time_hours = aggregated_data.get("all_active_time_hours", [])

                total_runtime_all = sum(all_runtime_hours) if all_runtime_hours else 0
                total_active_all = (
                    sum(all_active_time_hours) if all_active_time_hours else 0
                )

                if total_runtime_all > 0:
                    corrected_monthly_utilization = (
                        total_active_all / total_runtime_all
                    ) * 100
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
                    "peak_context": "No peak data available",
                }

            return {"average_utilization": average_utilization, "peak_info": peak_info}

        except Exception as e:
            logger.error(f"Error calculating system metrics: {e}")
            return {
                "average_utilization": 0,
                "peak_info": {
                    "peak_utilization": 0,
                    "peak_period": None,
                    "peak_context": "Error calculating peak",
                },
            }

    def _find_system_peak_period(
        self, bucket_reports: List[Dict], analysis_type: str
    ) -> Dict[str, Any]:
        """Find the actual period with peak system utilization - FIXED VERSION."""

        if not bucket_reports:
            return self._create_no_peak_result()

        # Find the bucket with highest utilization
        peak_bucket = self._find_peak_utilization_bucket(bucket_reports)

        if not peak_bucket:
            return self._create_no_peak_result()

        # Extract peak information
        peak_info = self._extract_peak_information(peak_bucket, analysis_type)

        # Create and return result
        return self._create_peak_result(peak_info, analysis_type)

    def _create_no_peak_result(self) -> Dict[str, Any]:
        """Create result object when no peak data is available."""

        return {
            "peak_utilization": 0,
            "peak_period": None,
            "peak_context": "No peak data available",
        }

    def _find_peak_utilization_bucket(
        self, bucket_reports: List[Dict]
    ) -> Optional[Dict]:
        """Find the bucket report with the highest utilization."""

        max_utilization = 0
        peak_bucket = None

        for bucket_report in bucket_reports:
            if not bucket_report or not isinstance(bucket_report, dict):
                continue

            utilization = self._extract_bucket_utilization(bucket_report)

            if utilization > max_utilization:
                max_utilization = utilization
                peak_bucket = {
                    "bucket_report": bucket_report,
                    "utilization": utilization,
                }

        return peak_bucket

    def _extract_bucket_utilization(self, bucket_report: Dict) -> float:
        """Extract utilization value from bucket report."""

        overall_summary = bucket_report.get("overall_summary", {})
        return overall_summary.get("average_system_utilization_percent", 0)

    def _extract_peak_information(
        self, peak_bucket: Dict, analysis_type: str
    ) -> Dict[str, Any]:
        """Extract peak period information from the peak bucket."""

        bucket_report = peak_bucket["bucket_report"]
        utilization = peak_bucket["utilization"]

        time_bucket = bucket_report.get("time_bucket", {})
        period_info = time_bucket.get("period_info", {})

        # Try to get display name from period info first
        period_display = period_info.get("display")

        # Fallback to parsing start_time if needed
        if not period_display:
            period_display = self._parse_period_display_from_start_time(
                time_bucket, analysis_type
            )

        return {"utilization": utilization, "period_display": period_display}

    def _parse_period_display_from_start_time(
        self, time_bucket: Dict, analysis_type: str
    ) -> Optional[str]:
        """Parse period display from start_time as fallback."""

        start_time_str = time_bucket.get("start_time", "")
        if not start_time_str:
            return None

        try:
            bucket_date = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
            return self._format_period_display_by_type(bucket_date, analysis_type)
        except Exception as e:
            logger.warning(f"Error parsing start_time for peak period: {e}")
            return None

    def _format_period_display_by_type(
        self, bucket_date: datetime, analysis_type: str
    ) -> str:
        """Format period display based on analysis type."""

        format_mapping = {
            "daily": lambda date: date.strftime("%Y-%m-%d"),
            "weekly": lambda date: f"Week of {date.strftime('%Y-%m-%d')}",
            "monthly": lambda date: date.strftime("%m/%y"),
        }

        formatter = format_mapping.get(analysis_type)
        if formatter:
            return formatter(bucket_date)
        return bucket_date.strftime("%Y-%m-%d")

    def _create_peak_result(
        self, peak_info: Dict[str, Any], analysis_type: str
    ) -> Dict[str, Any]:
        """Create the final peak result object."""

        period_display = peak_info["period_display"]
        utilization = peak_info["utilization"]

        if not period_display:
            return self._create_no_peak_result()

        context = self._create_peak_context(analysis_type, period_display)

        return {
            "peak_utilization": round(utilization, 2),
            "peak_period": period_display,
            "peak_context": context,
        }

    def _create_peak_context(self, analysis_type: str, period_display: str) -> str:
        """Create context message for peak utilization."""

        context_templates = {
            "daily": f"Peak utilization on {period_display}",
            "weekly": f"Peak utilization during {period_display}",
            "monthly": f"Peak utilization in {period_display}",
        }

        return context_templates.get(
            analysis_type, f"Peak utilization in {period_display}"
        )

    def _find_actual_peak_info(self, data: Dict, analysis_type: str) -> Dict[str, Any]:
        """Find actual peak info from time series data - FIXED VERSION."""

        if not data or not data.get("utilizations") or not data.get("time_series"):
            return {
                "peak_utilization": 0,
                "peak_period": None,
                "peak_context": "No peak data available",
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
                "peak_context": peak_context,
            }
        return {
            "peak_utilization": round(max_utilization, 2),
            "peak_period": "Unknown",
            "peak_context": f"Peak utilization: {round(max_utilization, 2)}%",
        }

    def _get_complete_experiment_details(
        self, experiment_list: List[Dict], start_time: datetime, end_time: datetime
    ) -> List[Dict]:
        """Get complete experiment details from the database, starting from experiment_list."""

        # Get experiment IDs to filter by
        experiment_ids_filter = self._extract_experiment_ids_from_list(experiment_list)

        # Query database for experiment events
        experiment_events = self._query_experiment_events(
            start_time, end_time, experiment_ids_filter
        )

        # Build complete experiment details from events
        complete_details = self._build_experiment_details(experiment_events)

        # Sort and return results
        return self._sort_experiment_details(complete_details)

    def _extract_experiment_ids_from_list(
        self, experiment_list: List[Dict]
    ) -> Set[str]:
        """Extract experiment IDs from the provided experiment list."""

        if not experiment_list:
            logger.info("No experiment_list provided, querying database directly")
            return set()

        experiment_ids = set()
        for exp in experiment_list:
            if exp and isinstance(exp, dict):
                exp_id = exp.get("experiment_id")
                if exp_id:
                    experiment_ids.add(exp_id)

        return experiment_ids

    def _query_experiment_events(
        self, start_time: datetime, end_time: datetime, experiment_ids_filter: Set[str]
    ) -> Dict[str, Dict]:
        """Query database for experiment start and complete events."""

        experiment_event_types = [
            "experiment_start",
            "experiment_complete",
            "EXPERIMENT_START",
            "EXPERIMENT_COMPLETE",
        ]

        queries_to_try = [
            {
                "event_type": {"$in": experiment_event_types},
                "event_timestamp": {"$gte": start_time, "$lte": end_time},
            },
            {
                "event_type": {"$in": experiment_event_types},
                "event_timestamp": {
                    "$gte": start_time.isoformat(),
                    "$lte": end_time.isoformat(),
                },
            },
        ]

        experiment_events = {}

        for query in queries_to_try:
            try:
                events = list(
                    self.events_collection.find(query).sort("event_timestamp", 1)
                )
                if events:
                    self._process_experiment_events(
                        events, experiment_events, experiment_ids_filter
                    )
                    break
            except Exception as e:
                logger.warning(f"Error querying experiment events: {e}")
                continue

        return experiment_events

    def _process_experiment_events(
        self,
        events: List[Dict],
        experiment_events: Dict[str, Dict],
        experiment_ids_filter: Set[str],
    ) -> None:
        """Process experiment events and organize by experiment ID."""

        for event in events:
            if not event or not isinstance(event, dict):
                continue

            event_time = self.analyzer._parse_timestamp_utc(
                event.get("event_timestamp")
            )
            if not event_time:
                continue

            exp_id = self.analyzer._extract_experiment_id(event)
            if not exp_id:
                continue

            # Filter by experiment IDs if provided
            if experiment_ids_filter and exp_id not in experiment_ids_filter:
                continue

            # Initialize experiment entry if needed
            if exp_id not in experiment_events:
                experiment_events[exp_id] = {}

            # Categorize event by type
            self._categorize_experiment_event(
                event, event_time, experiment_events[exp_id]
            )

    def _categorize_experiment_event(
        self, event: Dict, event_time: datetime, experiment_data: Dict
    ) -> None:
        """Categorize experiment event as start or complete."""

        event_type = str(event.get("event_type", "")).lower()

        if "start" in event_type:
            experiment_data["start"] = {
                "timestamp": event_time,
                "event_data": event.get("event_data", {}),
            }
        elif "complete" in event_type:
            experiment_data["complete"] = {
                "timestamp": event_time,
                "event_data": event.get("event_data", {}),
            }

    def _build_experiment_details(
        self, experiment_events: Dict[str, Dict]
    ) -> List[Dict]:
        """Build complete experiment details from categorized events."""

        complete_details = []

        for exp_id, events in experiment_events.items():
            try:
                experiment_detail = self._create_experiment_detail(exp_id, events)
                if experiment_detail:
                    complete_details.append(experiment_detail)
            except Exception as e:
                logger.error(f"Error processing experiment {exp_id}: {e}")
                continue

        return complete_details

    def _create_experiment_detail(self, exp_id: str, events: Dict) -> Optional[Dict]:
        """Create a complete experiment detail from start and complete events."""

        start_event = events.get("start")
        if not start_event:
            return None

        start_time_exp = start_event["timestamp"]
        start_data = start_event["event_data"]

        # Extract experiment name
        exp_name = self._extract_experiment_name(start_data)

        # Process completion data
        complete_event = events.get("complete")
        completion_data = self._process_completion_data(complete_event, start_time_exp)

        return {
            "experiment_id": exp_id,
            "experiment_name": exp_name,
            "start_time": start_time_exp.isoformat(),
            **completion_data,
        }

    def _extract_experiment_name(self, start_data: Dict) -> str:
        """Extract experiment name from start event data."""

        exp_name = "Unknown Experiment"

        if isinstance(start_data.get("experiment"), dict):
            exp_design = start_data["experiment"].get("experiment_design", {})
            if isinstance(exp_design, dict):
                exp_name = exp_design.get("experiment_name", "Unknown Experiment")

        return exp_name

    def _process_completion_data(
        self, complete_event: Optional[Dict], start_time_exp: datetime
    ) -> Dict[str, Any]:
        """Process completion event data to extract duration and status."""

        if complete_event:
            return self._process_completed_experiment(complete_event, start_time_exp)
        return self._process_ongoing_experiment()

    def _process_completed_experiment(
        self, complete_event: Dict, start_time_exp: datetime
    ) -> Dict[str, Any]:
        """Process data for a completed experiment."""

        end_time_exp = complete_event["timestamp"]
        duration_seconds = (end_time_exp - start_time_exp).total_seconds()
        duration_hours = duration_seconds / 3600

        # Format duration display
        duration_display = self._format_duration_display(
            duration_seconds, duration_hours
        )

        # Extract status
        complete_data = complete_event.get("event_data", {})
        status = (
            complete_data.get("status", "completed")
            if isinstance(complete_data, dict)
            else "completed"
        )

        return {
            "end_time": end_time_exp.isoformat(),
            "status": status,
            "duration_hours": duration_hours,
            "duration_display": duration_display,
        }

    def _process_ongoing_experiment(self) -> Dict[str, Any]:
        """Process data for an ongoing experiment."""

        return {
            "end_time": None,
            "status": "in_progress",
            "duration_hours": None,
            "duration_display": "Ongoing",
        }

    def _format_duration_display(
        self, duration_seconds: float, duration_hours: float
    ) -> str:
        """Format duration for display."""

        if duration_seconds < 60:
            return f"{duration_seconds:.1f} seconds"
        if duration_seconds < 3600:
            return f"{duration_seconds / 60:.1f} minutes"
        return f"{duration_hours:.1f} hours"

    def _sort_experiment_details(self, complete_details: List[Dict]) -> List[Dict]:
        """Sort experiment details by start time."""

        try:
            complete_details.sort(key=lambda x: x.get("start_time", ""))
        except Exception as e:
            logger.warning(f"Error sorting experiment details: {e}")

        return complete_details

    def _calculate_trends_from_time_series(
        self, time_series_points: List[Dict]
    ) -> Dict[str, Any]:
        """Calculate trends from time series data."""

        if len(time_series_points) < 2:
            return {
                "utilization_trend": {
                    "direction": "insufficient_data",
                    "change_percent": 0,
                },
                "experiment_trend": {
                    "direction": "insufficient_data",
                    "change_percent": 0,
                },
            }

        # Extract active periods only
        active_points = [
            point for point in time_series_points if point["utilization"] > 0
        ]

        if len(active_points) < 2:
            return {
                "utilization_trend": {
                    "direction": "insufficient_data",
                    "change_percent": 0,
                },
                "experiment_trend": {
                    "direction": "insufficient_data",
                    "change_percent": 0,
                },
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
            util_direction = (
                "increasing"
                if util_change_percent > 5
                else "decreasing"
                if util_change_percent < -5
                else "stable"
            )

        # Experiment trend
        if exp_first == 0:
            exp_change_percent, exp_direction = 0, "stable"
        else:
            exp_change_percent = ((exp_last - exp_first) / exp_first) * 100
            exp_direction = (
                "increasing"
                if exp_change_percent > 5
                else "decreasing"
                if exp_change_percent < -5
                else "stable"
            )

        return {
            "utilization_trend": {
                "direction": util_direction,
                "change_percent": round(util_change_percent, 2),
                "first_value": round(util_first, 2),
                "last_value": round(util_last, 2),
                "active_periods_analyzed": len(active_points),
            },
            "experiment_trend": {
                "direction": exp_direction,
                "change_percent": round(exp_change_percent, 2),
                "first_value": exp_first,
                "last_value": exp_last,
                "active_periods_analyzed": len(active_points),
            },
        }

    def _resolve_workcell_name(self, workcell_id: str) -> str:
        """Resolve human-readable name for a workcell with multiple strategies."""

        # Look in events collection directly
        try:
            workcell_events = list(
                self.events_collection.find(
                    {
                        "event_type": {"$in": ["workcell_start", "lab_start"]},
                        "$or": [
                            {"source.workcell_id": workcell_id},
                            {"source.manager_id": workcell_id},
                            {"event_data.workcell_id": workcell_id},
                        ],
                    }
                ).limit(3)
            )

            for event in workcell_events:
                event_data = event.get("event_data", {})
                name_candidates = [
                    event_data.get("name"),
                    event_data.get("workcell_name"),
                    event_data.get("lab_name"),
                    event_data.get("display_name"),
                ]

                for name in name_candidates:
                    if (
                        name
                        and isinstance(name, str)
                        and name.strip()
                        and not name.startswith("Workcell ")
                    ):
                        return name.strip()

        except Exception as e:
            logger.warning(f"Error looking up workcell name in events: {e}")

        # Fallback to generated name
        return f"Workcell {workcell_id[-8:]}"

    def _create_time_buckets_user_timezone(
        self,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        bucket_hours: Union[int, str],
        user_timezone: str,
    ) -> List[Dict[str, Any]]:
        """Create time buckets aligned to user timezone with improved error handling."""

        # Validate inputs
        if not self._validate_time_inputs(start_time, end_time):
            return []

        try:
            tz_handler = TimezoneHandler(user_timezone)

            # Convert times to user timezone
            user_times = self._convert_to_user_timezone(
                tz_handler, start_time, end_time
            )
            if not user_times:
                return []

            current_user_time, end_user_time = user_times

            # Create buckets based on bucket type
            buckets = self._create_buckets_by_type(
                bucket_hours, current_user_time, end_user_time, tz_handler
            )

            logger.info(f"Successfully created {len(buckets)} time buckets")
            return buckets

        except Exception as e:
            logger.error(f"Error in time bucket creation: {e}")
            return []

    def _validate_time_inputs(
        self, start_time: Optional[datetime], end_time: Optional[datetime]
    ) -> bool:
        """Validate input time parameters."""

        if not start_time or not end_time:
            logger.error("start_time or end_time is None in time bucket creation")
            return False

        if start_time >= end_time:
            logger.error(
                f"Invalid time range: start_time ({start_time}) >= end_time ({end_time})"
            )
            return False

        return True

    def _convert_to_user_timezone(
        self, tz_handler: "TimezoneHandler", start_time: datetime, end_time: datetime
    ) -> Optional[Tuple[datetime, datetime]]:
        """Convert UTC times to user timezone."""

        current_user_time = tz_handler.utc_to_user_time(start_time)
        end_user_time = tz_handler.utc_to_user_time(end_time)

        if not current_user_time or not end_user_time:
            logger.error("Failed to convert UTC times to user timezone")
            return None

        return current_user_time, end_user_time

    def _create_buckets_by_type(
        self,
        bucket_hours: Union[int, str],
        current_user_time: datetime,
        end_user_time: datetime,
        tz_handler: "TimezoneHandler",
    ) -> List[Dict[str, Any]]:
        """Create buckets based on the specified bucket type."""

        if bucket_hours in {"monthly", 720}:
            return self._create_monthly_buckets(
                current_user_time, end_user_time, tz_handler
            )
        if bucket_hours == 24:
            return self._create_daily_buckets(
                current_user_time, end_user_time, tz_handler
            )
        if bucket_hours == 168:
            return self._create_weekly_buckets(
                current_user_time, end_user_time, tz_handler
            )
        return self._create_hourly_buckets(
            bucket_hours, current_user_time, end_user_time, tz_handler
        )

    def _create_monthly_buckets(
        self,
        current_user_time: datetime,
        end_user_time: datetime,
        tz_handler: "TimezoneHandler",
    ) -> List[Dict[str, Any]]:
        """Create monthly time buckets."""

        buckets = []
        current_user_time = current_user_time.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )

        while current_user_time < end_user_time:
            try:
                next_month = self._get_next_month(current_user_time)
                bucket_end_user = min(next_month, end_user_time)

                bucket = self._create_single_bucket(
                    current_user_time, bucket_end_user, tz_handler, "month"
                )
                buckets.append(bucket)

                current_user_time = next_month

            except Exception as e:
                logger.error(f"Error creating monthly bucket: {e}")
                break

        return buckets

    def _create_daily_buckets(
        self,
        current_user_time: datetime,
        end_user_time: datetime,
        tz_handler: "TimezoneHandler",
    ) -> List[Dict[str, Any]]:
        """Create daily time buckets."""

        buckets = []
        current_user_time = current_user_time.replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        bucket_delta = timedelta(days=1)

        while current_user_time < end_user_time:
            try:
                bucket_end_user = min(current_user_time + bucket_delta, end_user_time)

                bucket = self._create_single_bucket(
                    current_user_time, bucket_end_user, tz_handler, "day"
                )
                buckets.append(bucket)

                current_user_time = bucket_end_user

            except Exception as e:
                logger.error(f"Error creating daily bucket: {e}")
                break

        return buckets

    def _create_weekly_buckets(
        self,
        current_user_time: datetime,
        end_user_time: datetime,
        tz_handler: "TimezoneHandler",
    ) -> List[Dict[str, Any]]:
        """Create weekly time buckets."""

        try:
            buckets = []

            # Align to start of week (Monday)
            days_since_monday = current_user_time.weekday()
            current_user_time = current_user_time.replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            current_user_time -= timedelta(days=days_since_monday)
            bucket_delta = timedelta(weeks=1)

            while current_user_time < end_user_time:
                bucket_end_user = min(current_user_time + bucket_delta, end_user_time)

                bucket = self._create_single_bucket(
                    current_user_time, bucket_end_user, tz_handler, "week"
                )
                buckets.append(bucket)

                current_user_time = bucket_end_user

            return buckets

        except Exception as e:
            logger.error(f"Error creating weekly buckets: {e}")
            return []

    def _create_hourly_buckets(
        self,
        bucket_hours: int,
        current_user_time: datetime,
        end_user_time: datetime,
        tz_handler: "TimezoneHandler",
    ) -> List[Dict[str, Any]]:
        """Create hourly or custom time buckets."""

        try:
            buckets = []
            bucket_delta = timedelta(hours=bucket_hours)

            while current_user_time < end_user_time:
                bucket_end_user = min(current_user_time + bucket_delta, end_user_time)

                bucket = self._create_single_bucket(
                    current_user_time, bucket_end_user, tz_handler, "period"
                )
                buckets.append(bucket)

                current_user_time = bucket_end_user

            return buckets

        except Exception as e:
            logger.error(f"Error creating hourly/custom buckets: {e}")
            return []

    def _get_next_month(self, current_time: datetime) -> datetime:
        """Get the start of the next month."""

        if current_time.month == 12:
            return current_time.replace(year=current_time.year + 1, month=1)
        return current_time.replace(month=current_time.month + 1)

    def _create_single_bucket(
        self,
        start_user_time: datetime,
        end_user_time: datetime,
        tz_handler: "TimezoneHandler",
        bucket_type: str,
    ) -> Dict[str, Any]:
        """Create a single time bucket with all necessary information."""

        bucket_start_utc = tz_handler.user_to_utc_time(start_user_time)
        bucket_end_utc = tz_handler.user_to_utc_time(end_user_time)

        period_info = self._create_period_info(bucket_type, start_user_time)

        return {
            "utc_times": (bucket_start_utc, bucket_end_utc),
            "user_times": (start_user_time, end_user_time),
            "period_info": period_info,
        }

    def _create_period_info(
        self, bucket_type: str, start_time: datetime
    ) -> Dict[str, str]:
        """Create period information based on bucket type."""

        if bucket_type == "month":
            return {
                "type": "month",
                "display": start_time.strftime("%B %Y"),
                "short": start_time.strftime("%b %Y"),
            }
        if bucket_type == "day":
            return {
                "type": "day",
                "display": start_time.strftime("%Y-%m-%d"),
                "short": start_time.strftime("%m-%d"),
            }
        if bucket_type == "week":
            return {
                "type": "week",
                "display": f"Week of {start_time.strftime('%Y-%m-%d')}",
                "short": f"Week {start_time.strftime('%m/%d')}",
            }
        # period
        return {
            "type": "period",
            "display": start_time.strftime("%Y-%m-%d %H:%M"),
            "short": start_time.strftime("%m/%d %H:%M"),
        }


class TimezoneHandler:
    """Handle timezone conversions with improved error handling."""

    def __init__(self, user_timezone: str = "America/Chicago") -> None:
        """Initialize with user timezone, defaulting to America/Chicago."""
        try:
            self.user_tz = pytz.timezone(user_timezone)
            self.utc_tz = pytz.UTC
        except Exception as e:
            logger.error(
                f"Error initializing timezone handler with {user_timezone}: {e}"
            )
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

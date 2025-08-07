"""CSV export functionality for MADSci utilization reports - COMPLETE FIXED VERSION."""

import csv
import io
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union


class CSVExporter:
    """Handles conversion of utilization reports to CSV format."""

    @staticmethod
    def export_utilization_periods_to_csv(
        report_data: Dict[str, Any], output_path: Optional[str] = None
    ) -> Union[str, str]:
        """
        Export utilization periods report to a single comprehensive CSV.
        FIXED: Now properly handles node summary for daily reports.

        Args:
            report_data: The utilization periods report data
            output_path: Optional path to save CSV file. If None, returns CSV as string

        Returns:
            If output_path is None: CSV string
            If output_path is provided: path to saved file
        """
        if not report_data or "error" in report_data:
            CSVExporter._validate_report_data(report_data)

        output = io.StringIO()
        writer = csv.writer(output)

        # Write all sections
        CSVExporter._write_header_section(writer)
        CSVExporter._write_metadata_section(writer, report_data)
        CSVExporter._write_key_metrics_section(writer, report_data)
        CSVExporter._write_time_series_section(writer, report_data)
        CSVExporter._write_node_summary_section(writer, report_data)
        CSVExporter._write_workcell_summary_section(writer, report_data)
        CSVExporter._write_user_utilization_section(writer, report_data)
        CSVExporter._write_experiment_details_section(writer, report_data)

        csv_content = output.getvalue()

        # Save to file if output_path provided
        if output_path:
            metadata = report_data.get("summary_metadata", {})
            return CSVExporter._save_single_csv_file(
                csv_content,
                output_path,
                "utilization_periods",
                metadata.get("analysis_type", "daily"),
            )

        return csv_content

    @staticmethod
    def _validate_report_data(report_data: Dict[str, Any]) -> None:
        """Validate report data and raise appropriate errors."""
        if not report_data:
            raise ValueError("Report data is None or empty")

        if "error" in report_data and len(report_data) == 1:
            raise ValueError(f"Report contains only error: {report_data.get('error')}")

    @staticmethod
    def _write_header_section(writer: Any) -> None:
        """Write the header section."""
        writer.writerow(["=== UTILIZATION PERIODS REPORT ==="])
        writer.writerow([])

    @staticmethod
    def _write_metadata_section(writer: Any, report_data: Dict[str, Any]) -> None:
        """Write the metadata section."""
        metadata = report_data.get("summary_metadata", {})
        writer.writerow(["Metadata"])
        writer.writerow(["Analysis Type", metadata.get("analysis_type", "")])
        writer.writerow(["Generated At", metadata.get("generated_at", "")])
        writer.writerow(["Period Start", metadata.get("period_start", "")])
        writer.writerow(["Period End", metadata.get("period_end", "")])
        writer.writerow(["User Timezone", metadata.get("user_timezone", "")])
        writer.writerow(["Total Periods", metadata.get("total_periods", "")])
        writer.writerow([])

    @staticmethod
    def _write_key_metrics_section(writer: Any, report_data: Dict[str, Any]) -> None:
        """Write the key metrics section."""
        key_metrics = report_data.get("key_metrics", {})
        writer.writerow(["Key Metrics"])
        writer.writerow(
            ["Average Utilization (%)", key_metrics.get("average_utilization", "")]
        )
        writer.writerow(
            ["Peak Utilization (%)", key_metrics.get("peak_utilization", "")]
        )
        writer.writerow(["Peak Period", key_metrics.get("peak_period", "")])
        writer.writerow(["Total Experiments", key_metrics.get("total_experiments", "")])
        writer.writerow(
            ["Total Runtime (hours)", key_metrics.get("total_runtime_hours", "")]
        )
        writer.writerow(
            [
                "Total Active Time (hours)",
                key_metrics.get("total_active_time_hours", ""),
            ]
        )
        writer.writerow(["Active Periods", key_metrics.get("active_periods", "")])
        writer.writerow(["Total Periods", key_metrics.get("total_periods", "")])
        writer.writerow([])

    @staticmethod
    def _write_time_series_section(writer: Any, report_data: Dict[str, Any]) -> None:
        """Write the time series data section."""
        writer.writerow(["=== TIME SERIES DATA ==="])
        writer.writerow(
            [
                "Period Number",
                "Period Type",
                "Period Display",
                "Date",
                "Start Time",
                "Utilization (%)",
                "Experiments",
                "Runtime (hours)",
            ]
        )

        time_series = report_data.get("time_series", {}).get("system", [])
        for point in time_series:
            writer.writerow(
                [
                    point.get("period_number", ""),
                    point.get("period_type", ""),
                    point.get("period_display", ""),
                    point.get("date", ""),
                    point.get("start_time", ""),
                    point.get("utilization", ""),
                    point.get("experiments", ""),
                    point.get("runtime_hours", ""),
                ]
            )
        writer.writerow([])

    @staticmethod
    def _write_node_summary_section(writer: Any, report_data: Dict[str, Any]) -> None:
        """Write the node summary section."""
        node_summary = report_data.get("node_summary", {})
        writer.writerow(["=== NODE SUMMARY ==="])

        if node_summary:
            writer.writerow(
                [
                    "Node ID",
                    "Node Name",
                    "Display Name",
                    "Average Utilization (%)",
                    "Peak Utilization (%)",
                    "Peak Period",
                    "Total Busy (hours)",
                ]
            )

            for node_id, node_data in node_summary.items():
                writer.writerow(
                    [
                        node_data.get("node_id", node_id),
                        node_data.get("node_name", ""),
                        node_data.get("display_name", f"Node {node_id[-8:]}"),
                        node_data.get("average_utilization", ""),
                        node_data.get("peak_utilization", ""),
                        node_data.get("peak_period", ""),
                        node_data.get("total_busy_hours", ""),
                    ]
                )
        else:
            CSVExporter._write_no_node_data_message(writer, report_data)

        writer.writerow([])

    @staticmethod
    def _write_no_node_data_message(writer: Any, report_data: Dict[str, Any]) -> None:
        """Write message when no node data is available."""
        metadata = report_data.get("summary_metadata", {})
        analysis_type = metadata.get("analysis_type", "")

        if analysis_type == "daily":
            writer.writerow(
                ["No node activity detected during this daily analysis period"]
            )
        else:
            writer.writerow(["No node data available for this time period"])

    @staticmethod
    def _write_workcell_summary_section(
        writer: Any, report_data: Dict[str, Any]
    ) -> None:
        """Write the workcell summary section."""
        workcell_summary = report_data.get("workcell_summary", {})
        if not workcell_summary:
            return

        writer.writerow(["=== WORKCELL SUMMARY ==="])
        writer.writerow(
            [
                "Workcell ID",
                "Workcell Name",
                "Display Name",
                "Average Utilization (%)",
                "Peak Utilization (%)",
                "Peak Period",
                "Total Experiments",
                "Total Runtime (hours)",
                "Total Active Time (hours)",
            ]
        )

        for workcell_id, workcell_data in workcell_summary.items():
            writer.writerow(
                [
                    workcell_data.get("workcell_id", workcell_id),
                    workcell_data.get("workcell_name", ""),
                    workcell_data.get("display_name", f"Workcell {workcell_id[-8:]}"),
                    workcell_data.get("average_utilization", ""),
                    workcell_data.get("peak_utilization", ""),
                    workcell_data.get("peak_period", ""),
                    workcell_data.get("total_experiments", ""),
                    workcell_data.get("total_runtime_hours", ""),
                    workcell_data.get("total_active_time_hours", ""),
                ]
            )
        writer.writerow([])

    @staticmethod
    def _write_user_utilization_section(
        writer: Any, report_data: Dict[str, Any]
    ) -> None:
        """Write the user utilization section."""
        user_utilization = report_data.get("user_utilization", {})
        if not user_utilization:
            return

        writer.writerow(["=== USER UTILIZATION ==="])
        writer.writerow(
            [
                "Author",
                "Total Workflows",
                "Total Runtime (hours)",
                "Completion Rate (%)",
                "Average Workflow Duration (hours)",
            ]
        )

        if "top_users" in user_utilization:
            CSVExporter._write_top_users_data(writer, user_utilization)
        else:
            CSVExporter._write_direct_user_data(writer, user_utilization)

        writer.writerow([])

    @staticmethod
    def _write_top_users_data(writer: Any, user_utilization: Dict[str, Any]) -> None:
        """Write top users data format."""
        top_users = user_utilization.get("top_users", [])
        for user in top_users:
            writer.writerow(
                [
                    user.get("author", ""),
                    user.get("total_workflows", ""),
                    user.get("total_runtime_hours", ""),
                    user.get("completion_rate_percent", ""),
                    user.get("average_workflow_duration_hours", ""),
                ]
            )

    @staticmethod
    def _write_direct_user_data(writer: Any, user_utilization: Dict[str, Any]) -> None:
        """Write direct user utilization data format."""
        for user_data in user_utilization.values():
            if isinstance(user_data, dict):
                writer.writerow(
                    [
                        user_data.get("author", ""),
                        user_data.get("total_workflows", ""),
                        user_data.get("total_runtime_hours", ""),
                        user_data.get("completion_rate_percent", ""),
                        user_data.get("average_workflow_duration_hours", ""),
                    ]
                )

    @staticmethod
    def _write_experiment_details_section(
        writer: Any, report_data: Dict[str, Any]
    ) -> None:
        """Write the experiment details section."""
        experiment_details = report_data.get("experiment_details", {})
        if not experiment_details or not experiment_details.get("experiments"):
            return

        writer.writerow(["=== EXPERIMENT DETAILS ==="])
        writer.writerow(
            [
                "Experiment ID",
                "Experiment Name",
                "Start Time",
                "End Time",
                "Status",
                "Duration (hours)",
                "Duration Display",
            ]
        )

        experiments = experiment_details.get("experiments", [])
        for exp in experiments:
            writer.writerow(
                [
                    exp.get("experiment_id", ""),
                    exp.get("experiment_name", "Unknown Experiment"),
                    exp.get("start_time", ""),
                    exp.get("end_time", ""),
                    exp.get("status", ""),
                    exp.get("duration_hours", ""),
                    exp.get("duration_display", ""),
                ]
            )

        total_experiments = experiment_details.get(
            "total_experiments", len(experiments)
        )
        if len(experiments) < total_experiments:
            remaining = total_experiments - len(experiments)
            writer.writerow([f"... and {remaining} more experiments"])

        writer.writerow([])

    @staticmethod
    def export_user_utilization_to_csv(
        report_data: Dict[str, Any],
        output_path: Optional[str] = None,
        detailed: bool = False,
    ) -> Union[str, str]:
        """
        Export user utilization report to a single CSV.

        Args:
            report_data: The user utilization report data
            output_path: Optional path to save CSV file
            detailed: If True, exports detailed report; if False, exports summary

        Returns:
            If output_path is None: CSV string
            If output_path is provided: path to saved file
        """

        if not report_data or "error" in report_data:
            raise ValueError("Invalid report data provided")

        output = io.StringIO()
        writer = csv.writer(output)

        if detailed:
            # Detailed user report
            writer.writerow(["=== DETAILED USER UTILIZATION REPORT ==="])
            writer.writerow([])

            # Metadata
            metadata = report_data.get("report_metadata", {})
            writer.writerow(["Report Metadata"])
            writer.writerow(["Generated At", metadata.get("generated_at", "")])
            writer.writerow(["Analysis Start", metadata.get("analysis_start", "")])
            writer.writerow(["Analysis End", metadata.get("analysis_end", "")])
            writer.writerow(["Total Users", metadata.get("total_users", "")])
            writer.writerow(["Total Workflows", metadata.get("total_workflows", "")])
            writer.writerow([])

            # System summary
            system_summary = report_data.get("system_summary", {})
            writer.writerow(["System Summary"])
            writer.writerow(
                ["Total Workflows", system_summary.get("total_workflows", "")]
            )
            writer.writerow(
                ["Total Runtime (hours)", system_summary.get("total_runtime_hours", "")]
            )
            writer.writerow(
                [
                    "Average Workflow Duration (hours)",
                    system_summary.get("average_workflow_duration_hours", ""),
                ]
            )
            writer.writerow(
                [
                    "Completion Rate (%)",
                    system_summary.get("completion_rate_percent", ""),
                ]
            )
            writer.writerow(
                [
                    "Author Attribution Rate (%)",
                    system_summary.get("author_attribution_rate_percent", ""),
                ]
            )
            writer.writerow([])

            # User details
            writer.writerow(["=== USER DETAILS ==="])
            writer.writerow(
                [
                    "Author",
                    "Total Workflows",
                    "Completed",
                    "Failed",
                    "Cancelled",
                    "Total Runtime (hours)",
                    "Avg Duration (hours)",
                    "Completion Rate (%)",
                    "Shortest (hours)",
                    "Longest (hours)",
                ]
            )

            user_utilization = report_data.get("user_utilization", {})
            for user_data in user_utilization.values():
                writer.writerow(
                    [
                        user_data.get("author", ""),
                        user_data.get("total_workflows", ""),
                        user_data.get("completed_workflows", ""),
                        user_data.get("failed_workflows", ""),
                        user_data.get("cancelled_workflows", ""),
                        user_data.get("total_runtime_hours", ""),
                        user_data.get("average_workflow_duration_hours", ""),
                        user_data.get("completion_rate_percent", ""),
                        user_data.get("shortest_workflow_hours", ""),
                        user_data.get("longest_workflow_hours", ""),
                    ]
                )

            report_type = "detailed"
        else:
            # Summary user report
            writer.writerow(["=== USER UTILIZATION SUMMARY ==="])
            writer.writerow([])

            writer.writerow(["Summary Statistics"])
            writer.writerow(["Total Users", report_data.get("total_users", "")])
            writer.writerow(
                [
                    "Author Attribution Rate (%)",
                    report_data.get("author_attribution_rate_percent", ""),
                ]
            )
            writer.writerow([])

            # System totals
            system_totals = report_data.get("system_totals", {})
            writer.writerow(["System Totals"])
            writer.writerow(
                ["Total Workflows", system_totals.get("total_workflows", "")]
            )
            writer.writerow(
                ["Total Runtime (hours)", system_totals.get("total_runtime_hours", "")]
            )
            writer.writerow(
                [
                    "Completion Rate (%)",
                    system_totals.get("completion_rate_percent", ""),
                ]
            )
            writer.writerow([])

            # Top users
            writer.writerow(["=== TOP USERS ==="])
            writer.writerow(
                [
                    "Author",
                    "Total Workflows",
                    "Total Runtime (hours)",
                    "Completion Rate (%)",
                    "Avg Duration (hours)",
                ]
            )

            top_users = report_data.get("top_users", [])
            for user in top_users:
                writer.writerow(
                    [
                        user.get("author", ""),
                        user.get("total_workflows", ""),
                        user.get("total_runtime_hours", ""),
                        user.get("completion_rate_percent", ""),
                        user.get("average_workflow_duration_hours", ""),
                    ]
                )

            report_type = "summary"

        csv_content = output.getvalue()

        # Save to file if output_path provided
        if output_path:
            return CSVExporter._save_single_csv_file(
                csv_content, output_path, "user_utilization", report_type
            )

        return csv_content

    @staticmethod
    def export_utilization_report_to_csv(
        report_data: Dict[str, Any], output_path: Optional[str] = None
    ) -> Union[str, str]:
        """
        Export basic utilization report to a single CSV.

        Args:
            report_data: The utilization report data
            output_path: Optional path to save CSV file

        Returns:
            If output_path is None: CSV string
            If output_path is provided: path to saved file
        """

        if not report_data or "error" in report_data:
            raise ValueError("Invalid report data provided")

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(["=== UTILIZATION REPORT ==="])
        writer.writerow([])

        # Report metadata
        metadata = report_data.get("report_metadata", {})
        writer.writerow(["Report Metadata"])
        writer.writerow(["Generated At", metadata.get("generated_at", "")])
        writer.writerow(["Analysis Start", metadata.get("analysis_start", "")])
        writer.writerow(["Analysis End", metadata.get("analysis_end", "")])
        writer.writerow(["Total Sessions", metadata.get("total_sessions", "")])
        writer.writerow(
            ["Analysis Duration (hours)", metadata.get("analysis_duration_hours", "")]
        )
        writer.writerow([])

        # Overall summary
        overall_summary = report_data.get("overall_summary", {})
        writer.writerow(["Overall Summary"])
        writer.writerow(["Total Sessions", overall_summary.get("total_sessions", "")])
        writer.writerow(
            [
                "Total System Runtime (hours)",
                overall_summary.get("total_system_runtime_hours", ""),
            ]
        )
        writer.writerow(
            [
                "Total Active Time (hours)",
                overall_summary.get("total_active_time_hours", ""),
            ]
        )
        writer.writerow(
            [
                "Average System Utilization (%)",
                overall_summary.get("average_system_utilization_percent", ""),
            ]
        )
        writer.writerow(
            ["Total Experiments", overall_summary.get("total_experiments", "")]
        )
        writer.writerow(["Nodes Tracked", overall_summary.get("nodes_tracked", "")])
        writer.writerow([])

        # Session details
        session_details = report_data.get("session_details", [])
        if session_details:
            writer.writerow(["=== SESSION DETAILS ==="])
            writer.writerow(
                [
                    "Session Type",
                    "Session Name",
                    "Start Time",
                    "End Time",
                    "Duration (hours)",
                    "System Utilization (%)",
                    "Total Experiments",
                    "Nodes Active",
                ]
            )

            for session in session_details:
                if "error" not in session:
                    writer.writerow(
                        [
                            session.get("session_type", ""),
                            session.get("session_name", ""),
                            session.get("start_time", ""),
                            session.get("end_time", ""),
                            session.get("duration_hours", ""),
                            session.get("system_utilization_percent", ""),
                            session.get("total_experiments", ""),
                            session.get("nodes_active", ""),
                        ]
                    )
            writer.writerow([])

        # Node summary
        node_summary = overall_summary.get("node_summary", {})
        if node_summary:
            writer.writerow(["=== NODE SUMMARY ==="])
            writer.writerow(
                [
                    "Node ID",
                    "Average Utilization (%)",
                    "Total Busy Time (hours)",
                    "Sessions Active",
                ]
            )

            for node_id, node_data in node_summary.items():
                writer.writerow(
                    [
                        node_id,
                        node_data.get("average_utilization_percent", ""),
                        node_data.get("total_busy_time_hours", ""),
                        node_data.get("sessions_active", ""),
                    ]
                )

        csv_content = output.getvalue()

        # Save to file if output_path provided
        if output_path:
            return CSVExporter._save_single_csv_file(
                csv_content, output_path, "utilization_report", "basic"
            )

        return csv_content

    @staticmethod
    def _save_single_csv_file(
        csv_content: str, output_path: str, report_type: str, analysis_type: str
    ) -> str:
        """Save CSV content to a single file."""
        base_path = Path(output_path)
        base_path.mkdir(parents=True, exist_ok=True)

        # Generate filename
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"madsci_{report_type}_{analysis_type}_{date_str}.csv"
        file_path = base_path / filename

        with file_path.open("w", newline="", encoding="utf-8") as f:
            f.write(csv_content)

        print(f"Saved {report_type} CSV to: {file_path}")  # noqa: T201
        return str(file_path)

    @staticmethod
    def handle_api_csv_export(
        utilization: Dict[str, Any], save_to_file: bool, output_path: Optional[str]
    ) -> Dict[str, Any]:
        """
        Handle CSV export logic for API endpoints (utilization periods).

        Args:
            utilization: The utilization report data
            save_to_file: Whether to save to server filesystem
            output_path: Server path to save files (required if save_to_file=True)

        Returns:
            Dict with CSV content or save results
        """
        try:
            if save_to_file:
                if not output_path:
                    return {"error": "output_path is required when save_to_file=True"}

                result = CSVExporter.export_utilization_periods_to_csv(
                    report_data=utilization, output_path=output_path
                )

                if isinstance(result, dict):
                    return {
                        "success": True,
                        "message": "CSV files saved successfully",
                        "files_saved": result,
                        "csv_format": True,
                        "saved_to_server": True,
                        "report_type": "utilization_periods",
                    }

                return {
                    "success": True,
                    "message": "CSV file saved successfully",
                    "file_path": result,
                    "csv_format": True,
                    "saved_to_server": True,
                    "report_type": "utilization_periods",
                }

            # Return CSV content for server to handle
            csv_content = CSVExporter.export_utilization_periods_to_csv(
                report_data=utilization, output_path=None
            )

            return {"success": True, "csv_content": csv_content, "is_download": True}

        except Exception as e:
            return {"error": f"CSV generation failed: {e!s}"}

    @staticmethod
    def handle_user_csv_export(
        report: Dict[str, Any], save_to_file: bool, output_path: Optional[str]
    ) -> Dict[str, Any]:
        """
        Handle CSV export logic for user utilization endpoints.

        Args:
            report: The user utilization report data
            save_to_file: Whether to save to server filesystem
            output_path: Server path to save files (required if save_to_file=True)

        Returns:
            Dict with CSV content or save results
        """
        try:
            if save_to_file:
                if not output_path:
                    return {"error": "output_path is required when save_to_file=True"}

                file_path = CSVExporter.export_user_utilization_to_csv(
                    report_data=report, output_path=output_path, detailed=True
                )

                return {
                    "success": True,
                    "message": "CSV file saved successfully",
                    "file_path": file_path,
                    "csv_format": True,
                    "saved_to_server": True,
                    "report_type": "user_utilization",
                }

            # Return CSV content for server to handle
            csv_content = CSVExporter.export_user_utilization_to_csv(
                report_data=report, output_path=None, detailed=True
            )

            return {"success": True, "csv_content": csv_content, "is_download": True}

        except Exception as e:
            return {"error": f"CSV generation failed: {e!s}"}

    @staticmethod
    def handle_session_csv_export(
        report: Dict[str, Any], save_to_file: bool, output_path: Optional[str]
    ) -> Dict[str, Any]:
        """
        Handle CSV export logic for session utilization endpoints.

        Args:
            report: The session utilization report data
            save_to_file: Whether to save to server filesystem
            output_path: Server path to save files (required if save_to_file=True)

        Returns:
            Dict with CSV content or save results
        """
        try:
            if save_to_file:
                if not output_path:
                    return {"error": "output_path is required when save_to_file=True"}

                file_path = CSVExporter.export_utilization_report_to_csv(
                    report_data=report, output_path=output_path
                )

                return {
                    "success": True,
                    "message": "CSV file saved successfully",
                    "file_path": file_path,
                    "csv_format": True,
                    "saved_to_server": True,
                    "report_type": "session_utilization",
                }

            # Return CSV content for server to handle
            csv_content = CSVExporter.export_utilization_report_to_csv(
                report_data=report, output_path=None
            )

            return {"success": True, "csv_content": csv_content, "is_download": True}

        except Exception as e:
            return {"error": f"CSV generation failed: {e!s}"}

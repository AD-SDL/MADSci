Module madsci.event_manager.events_csv_exporter
===============================================
CSV export functionality for MADSci utilization reports - COMPLETE FIXED VERSION.

Classes
-------

`CSVExporter()`
:   Handles conversion of utilization reports to CSV format.

    ### Static methods

    `export_user_utilization_to_csv(report_data: Dict[str, Any], output_path: str | None = None, detailed: bool = False) ‑> str`
    :   Export user utilization report to a single CSV.

        Args:
            report_data: The user utilization report data
            output_path: Optional path to save CSV file
            detailed: If True, exports detailed report; if False, exports summary

        Returns:
            If output_path is None: CSV string
            If output_path is provided: path to saved file

    `export_utilization_periods_to_csv(report_data: Dict[str, Any], output_path: str | None = None) ‑> str`
    :   Export utilization periods report to a single comprehensive CSV.
        FIXED: Now properly handles node summary for daily reports.

        Args:
            report_data: The utilization periods report data
            output_path: Optional path to save CSV file. If None, returns CSV as string

        Returns:
            If output_path is None: CSV string
            If output_path is provided: path to saved file

    `export_utilization_report_to_csv(report_data: Dict[str, Any], output_path: str | None = None) ‑> str`
    :   Export basic utilization report to a single CSV.

        Args:
            report_data: The utilization report data
            output_path: Optional path to save CSV file

        Returns:
            If output_path is None: CSV string
            If output_path is provided: path to saved file

    `handle_api_csv_export(utilization: Dict[str, Any], save_to_file: bool, output_path: str | None) ‑> Dict[str, Any]`
    :   Handle CSV export logic for API endpoints (utilization periods).

        Args:
            utilization: The utilization report data
            save_to_file: Whether to save to server filesystem
            output_path: Server path to save files (required if save_to_file=True)

        Returns:
            Dict with CSV content or save results

    `handle_session_csv_export(report: Dict[str, Any], save_to_file: bool, output_path: str | None) ‑> Dict[str, Any]`
    :   Handle CSV export logic for session utilization endpoints.

        Args:
            report: The session utilization report data
            save_to_file: Whether to save to server filesystem
            output_path: Server path to save files (required if save_to_file=True)

        Returns:
            Dict with CSV content or save results

    `handle_user_csv_export(report: Dict[str, Any], save_to_file: bool, output_path: str | None) ‑> Dict[str, Any]`
    :   Handle CSV export logic for user utilization endpoints.

        Args:
            report: The user utilization report data
            save_to_file: Whether to save to server filesystem
            output_path: Server path to save files (required if save_to_file=True)

        Returns:
            Dict with CSV content or save results

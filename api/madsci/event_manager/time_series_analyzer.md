Module madsci.event_manager.time_series_analyzer
================================================
Time-series analysis for MADSci utilization data with session attribution.

Classes
-------

`TimeSeriesAnalyzer(utilization_analyzer: madsci.event_manager.utilization_analyzer.UtilizationAnalyzer)`
:   Analyzes utilization data over time with proper session attribution.

    Initialize with existing UtilizationAnalyzer instance.

    ### Methods

    `add_user_utilization_to_report(self, utilization: Dict[str, Any]) ‑> Dict[str, Any]`
    :   Add user utilization data to the report.

    `create_user_summary_from_report(self, user_report: Dict[str, Any]) ‑> Dict[str, Any]`
    :   Create user summary from user report.

    `generate_summary_report(self, start_time: datetime.datetime, end_time: datetime.datetime, analysis_type: str = 'daily', user_timezone: str = 'America/Chicago') ‑> Dict[str, Any]`
    :   Generate summary utilization report with error handling.

    `generate_utilization_report_with_times(self, start_time: str | None, end_time: str | None, analysis_type: str, user_timezone: str) ‑> Dict[str, Any]`
    :   Generate utilization report from string time parameters.

    `parse_time_parameters(self, start_time: str | None, end_time: str | None) ‑> Tuple[datetime.datetime | None, datetime.datetime | None]`
    :   Parse time parameters for utilization reports.

`TimezoneHandler(user_timezone: str = 'America/Chicago')`
:   Handle timezone conversions with improved error handling.

    Initialize with user timezone, defaulting to America/Chicago.

    ### Methods

    `user_to_utc_time(self, user_datetime: datetime.datetime) ‑> datetime.datetime | None`
    :   Convert user timezone datetime to UTC.

    `utc_to_user_time(self, utc_datetime: datetime.datetime) ‑> datetime.datetime | None`
    :   Convert UTC datetime to user timezone.

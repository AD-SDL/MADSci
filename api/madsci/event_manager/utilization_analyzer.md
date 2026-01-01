Module madsci.event_manager.utilization_analyzer
================================================
Session-based utilization analyzer for MADSci system components.

Classes
-------

`UtilizationAnalyzer(events_collection: pymongo.synchronous.collection.Collection)`
:   Analyzes system utilization based on session detection and event processing.

    Initialize with MongoDB events collection.

    ### Methods

    `generate_session_based_report(self, start_time: datetime.datetime | None = None, end_time: datetime.datetime | None = None) ‑> Dict[str, Any]`
    :   Generate comprehensive session-based utilization report.

        Sessions are defined by workcell/lab start and stop events. Each session
        represents a period when laboratory equipment was actively configured
        and available for experiments.

        Args:
            start_time: Analysis start time (UTC, timezone-naive)
            end_time: Analysis end time (UTC, timezone-naive)

        Returns:
            Dict containing session details, overall summary, and metadata

    `generate_user_utilization_report(self, start_time: datetime.datetime | None = None, end_time: datetime.datetime | None = None) ‑> Dict[str, Any]`
    :   Generate user utilization report based on workflow authors.

        Args:
            start_time: Analysis start time (UTC, timezone-naive)
            end_time: Analysis end time (UTC, timezone-naive)

        Returns:
            Dict containing user statistics, system summary, and metadata

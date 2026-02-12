"""MADSci Event Manager - Distributed event logging and querying.

The Event Manager provides centralized event logging, querying, and notification
capabilities for MADSci-powered laboratories. It serves as the central monitoring
system for tracking laboratory operations, system state changes, and real-time alerts.

Key Features
------------
- **Distributed Logging**: Centralized event collection from all lab components
- **Event Querying**: Structured filtering and search with MongoDB-backed storage
- **Real-time Notifications**: Email alerts and notification system for critical events
- **Utilization Analysis**: Resource and system utilization tracking with time-series analysis
- **Flexible Schema**: Support for arbitrary event data with standard event types

Components
----------
- :mod:`event_server`: Main FastAPI server for event ingestion and querying
- :mod:`time_series_analyzer`: Time-based event analysis and pattern detection
- :mod:`utilization_analyzer`: Resource utilization tracking and metrics
- :mod:`events_csv_exporter`: CSV export for external analysis
- :mod:`notifications`: Real-time notification system

Usage Example
-------------
The Event Manager is typically run as a standalone service:

.. code-block:: bash

    # Run the Event Manager server
    python -m madsci.event_manager.event_server

    # Or use Docker Compose
    docker compose up event-manager

For programmatic access, use the EventClient from madsci.client:

.. code-block:: python

    from madsci.client.event_client import EventClient
    from madsci.common.types.event_types import Event, EventType

    client = EventClient(event_server="http://localhost:8001")

    # Log events
    client.log_info("System initialized successfully")

    # Query events
    events = client.get_events(number=50)
    recent_errors = client.query_events({"log_level": {"$gte": 40}})

Configuration
-------------
The Event Manager uses environment variables with the ``EVENT_`` prefix:

- ``EVENT_SERVER_URL``: Server URL (default: http://localhost:8001)
- ``EVENT_DB_URL``: MongoDB connection string
- ``EVENT_COLLECTION_NAME``: MongoDB collection name
- ``EVENT_ALERT_LEVEL``: Minimum log level for alerts

See Also
--------
- :mod:`madsci.client.event_client`: Client library for event operations
- :mod:`madsci.common.types.event_types`: Event type definitions
- :mod:`madsci.common.mongodb_migration_tool`: Database migration utilities
"""

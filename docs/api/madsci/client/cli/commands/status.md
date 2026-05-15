Module madsci.client.cli.commands.status
========================================
MADSci CLI status command.

Displays status of MADSci services, using the shared utility layer for
health checking, formatting, and output rendering.

Functions
---------

`check_service_health(name: str, url: str, timeout: float = 5.0) ‑> madsci.client.cli.commands.status.ServiceInfo`
:   Check the health of a service (backward-compatible wrapper).
    
    Delegates to :func:`check_service_health_sync` from the shared
    service_health module and translates the result to :class:`ServiceInfo`.

`create_status_table(results: list[ServiceHealthResult]) ‑> Any`
:   Create a Rich table with service status.

Classes
-------

`ServiceInfo(name: str, url: str, status: ServiceStatus, version: str | None = None, details: dict[str, Any] | None = None, error: str | None = None)`
:   Information about a service (backward-compatible re-export).

    ### Instance variables

    `details: dict[str, typing.Any] | None`
    :

    `error: str | None`
    :

    `name: str`
    :

    `status: madsci.client.cli.commands.status.ServiceStatus`
    :

    `url: str`
    :

    `version: str | None`
    :

    ### Methods

    `to_dict(self) ‑> dict[str, typing.Any]`
    :   Convert to dictionary for JSON output.

`ServiceStatus(value, names=None, *, module=None, qualname=None, type=None, start=1)`
:   Status of a service (backward-compatible re-export).

    ### Ancestors (in MRO)

    * builtins.str
    * enum.Enum

    ### Class variables

    `HEALTHY`
    :

    `OFFLINE`
    :

    `UNHEALTHY`
    :

    `UNKNOWN`
    :
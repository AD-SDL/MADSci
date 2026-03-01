Module madsci.client.cli.commands.status
========================================
MADSci CLI status command.

Displays status of MADSci services.

Functions
---------

`check_service_health(name: str, url: str, timeout: float = 5.0) ‑> madsci.client.cli.commands.status.ServiceInfo`
:   Check the health of a service.

`create_status_table(services: list[ServiceInfo]) ‑> Any`
:   Create a Rich table with service status.

`get_status_icon(status: ServiceStatus) ‑> str`
:   Get the icon for a service status.

Classes
-------

`ServiceInfo(name: str, url: str, status: ServiceStatus, version: str | None = None, details: dict[str, Any] | None = None, error: str | None = None)`
:   Information about a service.

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
:   Status of a service.

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
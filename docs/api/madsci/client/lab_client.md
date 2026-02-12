Module madsci.client.lab_client
===============================
Client for the MADSci Lab Manager.

Classes
-------

`LabClient(lab_server_url: str | pydantic.networks.AnyUrl | None = None, config: madsci.common.types.client_types.LabClientConfig | None = None)`
:   Client for the MADSci Lab Manager.

    Create a new Lab Client.

    Args:
        lab_server_url: The URL of the lab server. If not provided, will use the URL from the current MADSci context.
        config: Client configuration for retry and timeout settings. If not provided, uses default LabClientConfig.

    ### Class variables

    `lab_server_url: pydantic.networks.AnyUrl`
    :

    ### Methods

    `get_definition(self, timeout: float | None = None) ‑> madsci.common.types.lab_types.LabManagerDefinition`
    :   Get the definition of the lab.

        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_lab_context(self, timeout: float | None = None) ‑> madsci.common.types.context_types.MadsciContext`
    :   Get the lab context.

        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_lab_health(self, timeout: float | None = None) ‑> madsci.common.types.lab_types.LabHealth`
    :   Get the health of the lab.

        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_manager_health(self, timeout: float | None = None) ‑> madsci.common.types.manager_types.ManagerHealth`
    :   Get the health of the lab manager.

        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

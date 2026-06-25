Module madsci.client.lab_client
===============================
Client for the MADSci Lab Manager.

Classes
-------

`LabClient(lab_server_url: Optional[Union[str, AnyUrl]] = None, config: Optional[LabClientConfig] = None)`
:   Client for the MADSci Lab Manager.
    
    Create a new Lab Client.
    
    Args:
        lab_server_url: The URL of the lab server. If not provided, will use the URL from the current MADSci context.
        config: Client configuration for retry and timeout settings. If not provided, uses default LabClientConfig.

    ### Ancestors (in MRO)

    * madsci.client.http.DualModeClientMixin

    ### Class variables

    `lab_server_url: AnyUrl`
    :

    ### Instance variables

    `session: httpx.Client`
    :   Backward-compatible accessor for the underlying HTTP client.
        
        Returns the httpx.Client so that existing code accessing
        ``client.session`` continues to work.

    ### Methods

    `async_get_lab_context(self, timeout: Optional[float] = None) ‑> madsci.common.types.context_types.MadsciContext`
    :   Get the lab context asynchronously.
        
        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `async_get_lab_health(self, timeout: Optional[float] = None) ‑> madsci.common.types.lab_types.LabHealth`
    :   Get the health of the lab asynchronously.
        
        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `async_get_manager_health(self, timeout: Optional[float] = None) ‑> madsci.common.types.manager_types.ManagerHealth`
    :   Get the health of the lab manager asynchronously.
        
        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_lab_context(self, timeout: Optional[float] = None) ‑> madsci.common.types.context_types.MadsciContext`
    :   Get the lab context.
        
        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_lab_health(self, timeout: Optional[float] = None) ‑> madsci.common.types.lab_types.LabHealth`
    :   Get the health of the lab.
        
        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_manager_health(self, timeout: Optional[float] = None) ‑> madsci.common.types.manager_types.ManagerHealth`
    :   Get the health of the lab manager.
        
        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
Module madsci.client.http
=========================
Dual-mode (sync + async) HTTP request mixin for MADSci clients.

This module provides :class:`DualModeClientMixin`, a mixin class that gives
any MADSci service client both synchronous and asynchronous HTTP request
methods backed by ``httpx``.  It is designed to be mixed into concrete client
classes (e.g. ``LabClient``, ``DataClient``) that already set up the required
instance attributes (``config``, ``_client``, ``_async_client``).

Usage
-----
::

    from madsci.client.http import DualModeClientMixin
    from madsci.common.http_client import create_httpx_client

    class LabClient(DualModeClientMixin):
        def __init__(self, ...):
            self.config = config or LabClientConfig()
            self._client = create_httpx_client(config=self.config)
            self._async_client = None  # created lazily

        def get_lab_context(self, timeout=None):
            response = self._request("GET", f"{self.url}context", timeout=timeout)
            return MadsciContext.model_validate(response.json())

        async def async_get_lab_context(self, timeout=None):
            response = await self._async_request("GET", f"{self.url}context", timeout=timeout)
            return MadsciContext.model_validate(response.json())

Classes
-------

`DualModeClientMixin()`
:   Mixin that provides shared sync/async HTTP request infrastructure.
    
    This mixin assumes the consuming class sets the following instance
    attributes in its ``__init__``:
    
    * ``self.config`` -- a :class:`~madsci.common.types.client_types.MadsciHttpClientConfig`
    * ``self._client`` -- an ``httpx.Client`` (created via
      :func:`~madsci.common.http_client.create_httpx_client`)
    * ``self._async_client`` -- initially ``None``; lazily created on the
      first call to :meth:`_async_request`.

    ### Descendants

    * madsci.client.data_client.DataClient
    * madsci.client.event_client.EventClient
    * madsci.client.experiment_client.ExperimentClient
    * madsci.client.lab_client.LabClient
    * madsci.client.location_client.LocationClient
    * madsci.client.node.rest_node_client.RestNodeClient
    * madsci.client.resource_client.ResourceClient
    * madsci.client.workcell_client.WorkcellClient

    ### Class variables

    `config: MadsciHttpClientConfig`
    :

    ### Methods

    `aclose(self) ‑> None`
    :   Async version of :meth:`close`.
        
        Properly awaits the async client's shutdown.

    `close(self) ‑> None`
    :   Close both the sync and async HTTP clients, releasing resources.
        
        Safe to call multiple times.
Module madsci.common.auth_context
=================================
Ambient ``AuthClient`` context for outbound credential propagation.

When an ``AuthClient`` is installed via ``auth_client_context()``, the MADSci
``create_httpx_client()`` factory and other in-process helpers can
transparently pick it up to inject ``Authorization: Bearer <token>`` headers
on outbound requests and to handle on-401 force-refresh-and-retry.

This module deliberately uses ``Any`` for the client type to avoid importing
the ``madsci.client`` package — ``madsci.common`` must stay
dependency-light. The protocol the client must satisfy is:

- ``get_access_token() -> str`` — return a (possibly auto-refreshed) token
- ``refresh() -> Any`` — force a refresh-grant exchange

In practice the only conforming implementation is
``madsci.client.auth_client.AuthClient``.

Functions
---------

`auth_client_context(client: Any) ‑> Iterator[Any]`
:   Install ``client`` as the ambient AuthClient for the current scope.
    
    Mirrors ``event_client_context()`` semantics. Nested contexts replace the
    binding for their lifetime; on exit the previous binding is restored.

`get_current_auth_client() ‑> Any | None`
:   Return the currently-installed ambient AuthClient, if any.
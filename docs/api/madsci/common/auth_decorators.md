Module madsci.common.auth_decorators
====================================
``@requires(permission=...)`` decorator for endpoint authorization.

Usage::

    from madsci.common.auth_decorators import requires
    from madsci.common.middleware import current_principal

    @get("/events")
    @requires(permission="event.read")
    async def get_events(self, request: Request) -> list[Event]:
        ...

When ``project_from=<field_name>`` is supplied, the decorator additionally
verifies that the principal is a member of the project identified by the
named field on the request body or path parameter.

Functions
---------

`requires(*, permission: str, project_from: Optional[str] = None) ‑> Callable`
:   Decorator that enforces a permission check on a Routable endpoint.
    
    The wrapped function MUST accept ``request: Request`` as a parameter so
    we can read ``request.state.principal``.
"""``@requires(permission=...)`` decorator for endpoint authorization.

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
"""

from __future__ import annotations

import functools
import inspect
from typing import Any, Callable, Optional

from fastapi import HTTPException, Request
from madsci.common.auth_middleware import current_principal


def _principal_has_permission(principal: Any, permission: str) -> bool:
    if principal is None:
        return False
    perms = set(principal.permissions or [])
    return permission in perms or "*" in perms


def _resolve_project_id(
    request: Request, field_name: str, kwargs: dict[str, Any]
) -> Optional[str]:
    """Best-effort lookup of a project_id from the request.

    Looked up in this order: path params, query params, then a body field.
    If a body kwarg is a Pydantic model with the named attribute, that wins.
    """
    if field_name in request.path_params:
        return str(request.path_params[field_name])
    if field_name in request.query_params:
        return str(request.query_params[field_name])
    for value in kwargs.values():
        if hasattr(value, field_name):
            v = getattr(value, field_name)
            if v:
                return str(v)
        if isinstance(value, dict) and field_name in value:
            return str(value[field_name])
    return None


def requires(
    *,
    permission: str,
    project_from: Optional[str] = None,
) -> Callable:
    """Decorator that enforces a permission check on a Routable endpoint.

    The wrapped function MUST accept ``request: Request`` as a parameter so
    we can read ``request.state.principal``.
    """

    def decorator(func: Callable) -> Callable:
        sig = inspect.signature(func)
        if "request" not in sig.parameters:
            raise TypeError(
                f"@requires-decorated endpoint {func.__qualname__} must accept"
                " a parameter named 'request: Request'"
            )

        is_coro = inspect.iscoroutinefunction(func)

        if is_coro:

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                request = _get_request_arg(sig, args, kwargs)
                _check(request, kwargs, permission, project_from)
                return await func(*args, **kwargs)

            return async_wrapper

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            request = _get_request_arg(sig, args, kwargs)
            _check(request, kwargs, permission, project_from)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def _get_request_arg(sig: inspect.Signature, args: tuple, kwargs: dict) -> Request:
    bound = sig.bind_partial(*args, **kwargs)
    request = bound.arguments.get("request")
    if not isinstance(request, Request):
        raise HTTPException(
            status_code=500,
            detail="@requires: 'request' argument is missing or wrong type",
        )
    return request


def _check(
    request: Request,
    kwargs: dict[str, Any],
    permission: str,
    project_from: Optional[str],
) -> None:
    # If AuthMiddleware isn't installed (auth_enabled=False), it never set
    # ``request.state.principal`` — not even to None. Treat that as "auth is
    # off" and no-op, preserving backwards compatibility for managers that
    # haven't enabled auth yet. The middleware ALWAYS sets ``principal``
    # (possibly to None) when it runs, so this signal is reliable.
    if not hasattr(request.state, "principal"):
        return
    principal = current_principal(request)
    if principal is None:
        raise HTTPException(status_code=401, detail="authentication required")
    if not _principal_has_permission(principal, permission):
        raise HTTPException(
            status_code=403,
            detail=f"missing required permission: {permission}",
        )
    if project_from is not None:
        project_id = _resolve_project_id(request, project_from, kwargs)
        if project_id is None:
            raise HTTPException(
                status_code=400,
                detail=f"missing project field {project_from!r} for project-scoped check",
            )
        if project_id not in (principal.project_ids or []):
            raise HTTPException(
                status_code=403,
                detail=f"principal is not a member of project {project_id}",
            )


# Canonical permission namespace
PERMISSION_NAMESPACE = {
    # Wildcard
    "*": "Full administrative privileges",
    # Experiment
    "experiment.read": "Read experiments and their metadata",
    "experiment.write": "Create or modify experiments",
    # Workflow
    "workflow.read": "Read workflow definitions and runs",
    "workflow.submit": "Submit new workflow runs",
    # Resource
    "resource.read": "Read resource state and inventory",
    "resource.write": "Mutate resource state, attach/detach to locations",
    # Workcell
    "workcell.read": "Read workcell configuration",
    "workcell.execute": "Execute workcell actions and admin commands",
    # Node
    "node.read": "Read node status and definitions",
    "node.execute_action": "Send action commands to nodes",
    # Event / observability
    "event.read": "Query the event log",
    # Auth admin
    "auth.user.read": "List / read users",
    "auth.user.write": "Create / modify users",
    "auth.project.read": "List / read projects",
    "auth.project.write": "Create / modify projects and memberships",
    "auth.role.read": "List / read roles",
    "auth.role.write": "Create / modify roles",
    "auth.role.grant": "Grant / revoke roles to principals",
    "auth.principal.write": "Register service accounts and node identities",
    "auth.credentials.rotate": "Rotate service-account / node-identity secrets",
    "auth.key.read": "List signing keys",
    "auth.key.rotate": "Rotate signing keys",
    "auth.key.retire": "Retire signing keys",
    "auth.token.introspect": "Introspect tokens (RFC 7662)",
    "auth.token.revoke": "Revoke other principals' tokens",
}


__all__ = [
    "PERMISSION_NAMESPACE",
    "requires",
]

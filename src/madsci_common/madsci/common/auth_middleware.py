"""AuthMiddleware for ``AbstractManagerBase``-based managers.

When ``auth_enabled=True`` on a manager, this middleware:

1. Extracts ``Authorization: Bearer <jwt>`` from each request.
2. Verifies the JWT against JWKS cached from ``auth_server_url``.
3. Validates ``iss``/``aud``/``exp``.
4. Populates ``request.state.principal`` with a typed ``Principal``.
5. Enters an ``ownership_context()`` for the request lifetime, sourced from
   the validated token claims.

When ``auth_required=False`` (migration mode), unauthenticated requests pass
through with ``request.state.principal = None`` and a structured warning is
logged so operators can identify unauth'd traffic during rollout.

This middleware is intentionally implemented in ``madsci.common`` (not
``madsci.client``) because ``AbstractManagerBase`` lives in
``madsci.common`` and must not depend on the auth-client package directly —
the AuthClient is dependency-injected by ``AbstractManagerBase`` when
``auth_enabled``.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from madsci.common.ownership import ownership_context
from madsci.common.types.auth_types import OwnershipInfo, Principal
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)


_DEPRECATION_LAST_LOGGED: dict[str, float] = {}
_DEPRECATION_INTERVAL_SECONDS = 60.0


def warn_caller_asserted_ownership(call_site: str) -> None:
    """Emit a sampled deprecation warning for caller-asserted OwnershipInfo.

    Per Decision 10, when ``auth_enabled=False``, caller-asserted
    ``OwnershipInfo`` continues to be accepted but a sampled warning is
    emitted (default once per process per minute per call-site).
    """
    now = time.time()
    last = _DEPRECATION_LAST_LOGGED.get(call_site, 0.0)
    if now - last < _DEPRECATION_INTERVAL_SECONDS:
        return
    _DEPRECATION_LAST_LOGGED[call_site] = now
    logger.warning(
        "DEPRECATION: caller-asserted OwnershipInfo accepted at %s. "
        "This behavior will be removed in the same MADSci release that drops "
        "auth_required=False; see docs/guides/auth_operator.md for the "
        "migration plan.",
        call_site,
    )


class AuthMiddleware(BaseHTTPMiddleware):
    """Validate JWTs and bind validated claims into request state and ownership."""

    def __init__(
        self,
        app: Any,
        *,
        auth_client: Any,
        auth_required: bool = False,
        lab_id: Optional[str] = None,
    ) -> None:
        """Configure the middleware with an injected ``AuthClient``.

        ``auth_required=False`` enables migration mode: unauth'd requests pass
        through with ``request.state.principal = None`` and a structured
        warning is logged.
        """
        super().__init__(app)
        self._auth_client = auth_client
        self._auth_required = auth_required
        self._lab_id = lab_id

    async def dispatch(
        self,
        request: Request,
        call_next: Any,
    ) -> Response:
        """Verify the bearer token and bind ownership context for the request."""
        auth_header = request.headers.get("authorization")
        principal: Optional[Principal] = None

        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            try:
                claims = self._auth_client.verify_jwt(token)
                principal = Principal.from_claims(claims)
            except Exception as exc:
                if self._auth_required:
                    return JSONResponse(
                        status_code=401,
                        content={
                            "error": "invalid_token",
                            "error_description": str(exc),
                        },
                    )
                logger.warning(
                    "AuthMiddleware: invalid token presented but auth_required=False"
                    " — passing request through (token=%s...)",
                    token[:12],
                )
        else:
            if self._auth_required:
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": "missing_token",
                        "error_description": "Authorization: Bearer header required",
                    },
                )
            if auth_header is None:
                logger.warning(
                    "AuthMiddleware: unauth'd request to %s (auth_required=False)",
                    request.url.path,
                )

        request.state.principal = principal

        if principal is not None:
            ownership = OwnershipInfo.from_jwt_claims(principal.claims)
            with ownership_context(**ownership.model_dump(exclude_none=True)):
                return await call_next(request)
        return await call_next(request)


def current_principal(request: Request) -> Optional[Principal]:
    """Return the validated principal on the current request, if any."""
    return getattr(request.state, "principal", None)


def current_ownership(request: Request) -> Any:
    """Return an OwnershipInfo derived from the request's principal."""
    principal = current_principal(request)
    if principal is None:
        return OwnershipInfo()
    return OwnershipInfo.from_jwt_claims(principal.claims)


__all__ = [
    "AuthMiddleware",
    "current_ownership",
    "current_principal",
    "warn_caller_asserted_ownership",
]

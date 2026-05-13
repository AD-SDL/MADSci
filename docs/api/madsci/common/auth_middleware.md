Module madsci.common.auth_middleware
====================================
AuthMiddleware for ``AbstractManagerBase``-based managers.

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

Functions
---------

`current_ownership(request: Request) ‑> Any`
:   Return an OwnershipInfo derived from the request's principal.

`current_principal(request: Request) ‑> madsci.common.types.auth_types.Principal | None`
:   Return the validated principal on the current request, if any.

`warn_caller_asserted_ownership(call_site: str) ‑> None`
:   Emit a sampled deprecation warning for caller-asserted OwnershipInfo.
    
    Per Decision 10, when ``auth_enabled=False``, caller-asserted
    ``OwnershipInfo`` continues to be accepted but a sampled warning is
    emitted (default once per process per minute per call-site).

Classes
-------

`AuthMiddleware(app: Any, *, auth_client: Any, auth_required: bool = False, lab_id: Optional[str] = None, unauthenticated_paths: Optional[set[str]] = None)`
:   Validate JWTs and bind validated claims into request state and ownership.
    
    Configure the middleware with an injected ``AuthClient``.
    
    ``auth_required=False`` enables migration mode: unauth'd requests pass
    through with ``request.state.principal = None`` and a structured
    warning is logged.
    
    ``unauthenticated_paths`` is an exact-match set of URL paths that
    SHALL bypass the bearer-token check entirely — used for endpoints
    that must remain reachable without a token (e.g., the Auth Manager's
    own ``/token`` and ``/.well-known/jwks.json``).

    ### Ancestors (in MRO)

    * starlette.middleware.base.BaseHTTPMiddleware

    ### Methods

    `dispatch(self, request: Request, call_next: Any) ‑> starlette.responses.Response`
    :   Verify the bearer token and bind ownership context for the request.
Module madsci.auth_manager.services.token_service
=================================================
JWT issuance, verification, and refresh-token management.

Functions
---------

`hash_refresh_token(token: str) ‑> str`
:   Public helper: SHA-256 hash a refresh token for table lookup.
    
    Hashing is deterministic — only the hash is persisted, never the raw
    token — so this helper is safe to use anywhere a lookup-by-token is
    needed (e.g., the Auth Manager's pre-rotation peek).

Classes
-------

`TokenError(*args, **kwargs)`
:   Raised on token verification / lookup failures.

    ### Ancestors (in MRO)

    * builtins.Exception
    * builtins.BaseException

`TokenService(*, engine: Any, signing_key_service: SigningKeyService, deny_list_service: DenyListService, issuer: str, audience: str, access_token_ttl: int = 900, refresh_token_ttl: int = 2592000, clock_skew_seconds: int = 30)`
:   Issue, verify, and revoke MADSci access + refresh tokens.
    
    Wire the token service to its signing-key, deny-list, and lab identity.

    ### Class variables

    `ALLOWED_ALGORITHMS: tuple[str, ...]`
    :

    ### Methods

    `consume_refresh_token(self, refresh_token: str, *, rotated_to_token_id: Optional[str] = None) ‑> madsci.auth_manager.tables.RefreshTokenTable`
    :   Atomically validate-and-revoke the matching refresh-token row.
        
        Raises ``TokenError`` for invalid / expired / already-revoked tokens.
        
        Concurrency: the revoke is implemented as a single
        ``UPDATE ... WHERE revoked_at IS NULL RETURNING ...`` so two parallel
        consumers of the same refresh token cannot both succeed. If the
        update affects zero rows, we re-fetch by ``token_hash`` to
        distinguish "doesn't exist" (invalid_grant) from "already revoked"
        (reuse — fire family-revocation).
        
        ``rotated_to_token_id`` is recorded on the parent row so future
        forensic queries can walk the rotation chain.

    `introspect(self, token: str) ‑> dict[str, typing.Any]`
    :   RFC 7662 introspection. Returns ``{'active': False}`` for any failure.

    `issue_access_token(self, *, sub: str, principal_type: PrincipalType, roles: Optional[list[str]] = None, permissions: Optional[list[str]] = None, user_id: Optional[str] = None, project_ids: Optional[list[str]] = None, manager_id: Optional[str] = None, node_id: Optional[str] = None, workcell_id: Optional[str] = None, ttl: Optional[int] = None) ‑> tuple[str, madsci.common.types.auth_types.JWTClaims]`
    :   Sign a new access token. Returns ``(jwt_str, claims_model)``.

    `issue_refresh_token(self, *, sub: str, principal_type: PrincipalType, ttl: Optional[int] = None) ‑> tuple[str, str]`
    :   Generate an opaque refresh token and persist its hash.
        
        Returns ``(opaque_token, row_token_id)`` so the caller can record the
        new row's id on the parent row's ``rotated_to`` column when this is
        issued as part of a rotation.

    `make_token_response(self, *, access_token: str, ttl: int, refresh_token: Optional[str] = None) ‑> madsci.common.types.auth_types.TokenResponse`
    :   Build the OAuth 2.0 token-endpoint response body.

    `revoke_access_token(self, jti: str, exp_unix: int) ‑> None`
    :   Add an access token's jti to the deny-list.

    `revoke_refresh_token(self, refresh_token: str) ‑> bool`
    :   Mark a refresh token as revoked. Returns True if a row was changed.

    `verify_token(self, token: str) ‑> madsci.common.types.auth_types.JWTClaims`
    :   Verify a JWT against the JWKS and return its claims.
        
        Checks signature, ``exp``, ``iss``, ``aud`` and the deny-list. Raises
        ``TokenError`` on failure.
Module madsci.auth_manager.services
===================================
Service-layer modules for the Auth Manager.

These services encapsulate the cryptographic and persistence operations the
``AuthManager`` server class depends on, keeping the FastAPI layer focused on
HTTP concerns.

Sub-modules
-----------
* madsci.auth_manager.services.audit_logger
* madsci.auth_manager.services.deny_list_service
* madsci.auth_manager.services.password_service
* madsci.auth_manager.services.signing_key_service
* madsci.auth_manager.services.token_service

Classes
-------

`AuditLogger(engine: Any)`
:   Persist security-relevant events to the ``audit_log`` table.
    
    Per the ``Audit log`` requirement in ``auth-identity-model/spec.md``, the
    table is append-only at the application level. There is no public
    ``update``/``delete`` API; any attempt to mutate a row by an admin must
    itself produce a new audit entry recording the attempt.
    
    Bind the logger to a SQLAlchemy engine.

    ### Methods

    `log(self, event_type: str, *, principal_id: Optional[str] = None, principal_type: Optional[str] = None, grant_type: Optional[str] = None, token_jti: Optional[str] = None, source_ip: Optional[str] = None, success: bool = True, details: Optional[dict] = None) ‑> madsci.auth_manager.tables.AuditLogTable`
    :   Append a new audit row and return it.

    `query(self, *, principal_id: Optional[str] = None, event_type: Optional[str] = None, limit: int = 100) ‑> list[madsci.auth_manager.tables.AuditLogTable]`
    :   Query audit rows with optional filters; newest first.

`DenyListService(engine: Any, *, persist_grace_seconds: int = 300)`
:   Persistent jti deny-list with in-memory cache and ETag support.
    
    Bind the deny-list to a SQLAlchemy engine and hydrate from the table.

    ### Instance variables

    `etag: str`
    :   Current ETag of the deny-list snapshot (sha256 over (jti, exp) tuples).

    ### Methods

    `evict_expired(self) ‑> int`
    :   Evict expired entries from cache and DB. Returns count removed.

    `is_revoked(self, jti: str) ‑> bool`
    :   Return True if ``jti`` is in the deny-list and not yet expired.

    `revoke(self, jti: str, exp_unix: int) ‑> None`
    :   Revoke a jti with the given expiration (unix seconds).

    `snapshot(self) ‑> dict[str, typing.Any]`
    :   Snapshot for the ``GET /deny-list`` response.

`PasswordService(time_cost: int = 3, memory_cost: int = 65536, parallelism: int = 4)`
:   Wrapper around argon2-cffi for password hashing and verification.
    
    Configure the underlying ``argon2.PasswordHasher``.

    ### Methods

    `hash_password(self, password: str) ‑> str`
    :   Hash a plaintext password with Argon2id.

    `needs_rehash(self, password_hash: str) ‑> bool`
    :   Whether the stored hash should be re-hashed with current params.

    `verify_password(self, password_hash: str, password: str) ‑> bool`
    :   Verify a password against a stored hash. Returns False on mismatch.

`SigningKeyService(engine: Any, key_size: int = 2048)`
:   Manage rotating RSA signing keys.
    
    Bind to a SQLAlchemy engine and choose the RSA key size in bits.

    ### Methods

    `generate_keypair(self, *, set_signing: bool = True) ‑> madsci.auth_manager.tables.SigningKeyTable`
    :   Generate a new RSA keypair and persist it.
        
        Args:
            set_signing: If True (default), the new key becomes the
                ``active_for_signing`` key and any previously-signing key is
                downgraded to verify-only.

    `get_key(self, kid: str) ‑> madsci.auth_manager.tables.SigningKeyTable | None`
    :   Look up a signing key by kid.

    `get_signing_key(self) ‑> madsci.auth_manager.tables.SigningKeyTable | None`
    :   Return the currently-active signing key, or None if none exists.

    `jwks(self) ‑> dict[str, list[dict[str, str]]]`
    :   Return a JWKS document for all currently-active keys.

    `list_active_keys(self) ‑> list[madsci.auth_manager.tables.SigningKeyTable]`
    :   All keys currently published in JWKS (i.e., active=True).

    `list_all_keys(self) ‑> list[madsci.auth_manager.tables.SigningKeyTable]`
    :   All keys including retired ones, newest first.

    `load_private_key(self, row: SigningKeyTable) ‑> Any`
    :   Load the private key for signing operations.

    `load_public_key(self, row: SigningKeyTable) ‑> Any`
    :   Load the public key for verification operations.

    `retire(self, kid: str) ‑> bool`
    :   Retire a key (remove from JWKS, delete private material).
        
        Returns True if a row was modified, False otherwise.

    `rotate(self) ‑> madsci.auth_manager.tables.SigningKeyTable`
    :   Generate a new signing key, demoting the current one to verify-only.

`TokenService(*, engine: Any, signing_key_service: SigningKeyService, deny_list_service: DenyListService, issuer: str, audience: str, access_token_ttl: int = 900, refresh_token_ttl: int = 2592000)`
:   Issue, verify, and revoke MADSci access + refresh tokens.
    
    Wire the token service to its signing-key, deny-list, and lab identity.

    ### Methods

    `consume_refresh_token(self, refresh_token: str) ‑> madsci.auth_manager.tables.RefreshTokenTable`
    :   Validate, revoke, and return the matching refresh-token row.
        
        Raises ``TokenError`` for invalid / expired / already-revoked tokens.
        
        On detected reuse of an already-revoked token, all refresh tokens for
        the same principal are revoked (per the reuse-detection requirement).

    `introspect(self, token: str) ‑> dict[str, typing.Any]`
    :   RFC 7662 introspection. Returns ``{'active': False}`` for any failure.

    `issue_access_token(self, *, sub: str, principal_type: PrincipalType, roles: Optional[list[str]] = None, permissions: Optional[list[str]] = None, user_id: Optional[str] = None, project_ids: Optional[list[str]] = None, manager_id: Optional[str] = None, node_id: Optional[str] = None, workcell_id: Optional[str] = None, ttl: Optional[int] = None) ‑> tuple[str, madsci.common.types.auth_types.JWTClaims]`
    :   Sign a new access token. Returns ``(jwt_str, claims_model)``.

    `issue_refresh_token(self, *, sub: str, principal_type: PrincipalType, ttl: Optional[int] = None) ‑> str`
    :   Generate an opaque refresh token and persist its hash.

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
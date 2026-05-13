Module madsci.auth_manager.services.deny_list_service
=====================================================
Deny-list service for revoked access-token jtis.

Revoked jtis are persisted to ``revoked_access_tokens`` and cached in memory
for fast read at the ``GET /deny-list`` endpoint. The cache is hydrated from
the database on startup so revocations survive Auth Manager restarts.

Entries whose ``exp`` is in the past are evicted both from the in-memory set
and from the database, bounding the list size to currently-revoked-and-still-
unexpired tokens.

Classes
-------

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
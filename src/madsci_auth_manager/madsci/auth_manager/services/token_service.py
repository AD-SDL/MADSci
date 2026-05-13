"""JWT issuance, verification, and refresh-token management."""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from joserfc import jwt
from joserfc.jwk import KeySet, RSAKey
from joserfc.jwt import JWTClaimsRegistry
from madsci.auth_manager.services.deny_list_service import DenyListService
from madsci.auth_manager.services.signing_key_service import SigningKeyService
from madsci.auth_manager.tables import RefreshTokenTable
from madsci.common.types.auth_types import (
    JWTClaims,
    PrincipalType,
    TokenResponse,
)
from madsci.common.utils import new_ulid_str
from sqlalchemy import update
from sqlmodel import Session, select


def _hash_refresh(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_refresh_token(token: str) -> str:
    """Public helper: SHA-256 hash a refresh token for table lookup.

    Hashing is deterministic — only the hash is persisted, never the raw
    token — so this helper is safe to use anywhere a lookup-by-token is
    needed (e.g., the Auth Manager's pre-rotation peek).
    """
    return _hash_refresh(token)


def _ensure_aware(dt: datetime) -> datetime:
    """Coerce a naive datetime to UTC.

    Some database backends (notably SQLite via SQLAlchemy) drop tzinfo on
    round-trip; we normalize to UTC so comparisons remain correct.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class TokenError(Exception):
    """Raised on token verification / lookup failures."""


class TokenService:
    """Issue, verify, and revoke MADSci access + refresh tokens."""

    # JWT verification is hard-pinned to RS256. Adding a non-RS256 algorithm
    # would be a breaking change to the issuer too, not a runtime knob.
    ALLOWED_ALGORITHMS: tuple[str, ...] = ("RS256",)

    def __init__(
        self,
        *,
        engine: Any,
        signing_key_service: SigningKeyService,
        deny_list_service: DenyListService,
        issuer: str,
        audience: str,
        access_token_ttl: int = 900,
        refresh_token_ttl: int = 60 * 60 * 24 * 30,
        clock_skew_seconds: int = 30,
    ) -> None:
        """Wire the token service to its signing-key, deny-list, and lab identity."""
        self._engine = engine
        self._sks = signing_key_service
        self._dls = deny_list_service
        self._issuer = issuer
        self._audience = audience
        self._access_ttl = access_token_ttl
        self._refresh_ttl = refresh_token_ttl
        self._clock_skew = clock_skew_seconds

    # ------------------------------------------------------------------
    # Access tokens
    # ------------------------------------------------------------------

    def issue_access_token(
        self,
        *,
        sub: str,
        principal_type: PrincipalType,
        roles: Optional[list[str]] = None,
        permissions: Optional[list[str]] = None,
        user_id: Optional[str] = None,
        project_ids: Optional[list[str]] = None,
        manager_id: Optional[str] = None,
        node_id: Optional[str] = None,
        workcell_id: Optional[str] = None,
        ttl: Optional[int] = None,
    ) -> tuple[str, JWTClaims]:
        """Sign a new access token. Returns ``(jwt_str, claims_model)``."""
        signing_row = self._sks.get_signing_key()
        if signing_row is None:
            raise TokenError("No active signing key; bootstrap required.")

        now = int(datetime.now(timezone.utc).timestamp())
        ttl = ttl or self._access_ttl
        jti = new_ulid_str()
        claims_dict: dict[str, Any] = {
            "iss": self._issuer,
            "aud": self._audience,
            "sub": sub,
            "iat": now,
            "exp": now + ttl,
            "jti": jti,
            "principal_type": principal_type.value,
            "roles": list(roles or []),
            "permissions": list(permissions or []),
        }
        if user_id is not None:
            claims_dict["user_id"] = user_id
        if project_ids is not None:
            claims_dict["project_ids"] = list(project_ids)
        if manager_id is not None:
            claims_dict["manager_id"] = manager_id
        if node_id is not None:
            claims_dict["node_id"] = node_id
        if workcell_id is not None:
            claims_dict["workcell_id"] = workcell_id

        header = {"alg": signing_row.algorithm, "kid": signing_row.kid, "typ": "JWT"}
        signing_key = RSAKey.import_key(
            signing_row.private_key_pem, parameters={"kid": signing_row.kid}
        )
        # joserfc.jwt.encode returns a str directly (authlib returned bytes).
        token_str = jwt.encode(
            header, claims_dict, signing_key, algorithms=list(self.ALLOWED_ALGORITHMS)
        )

        claims = JWTClaims(**dict(claims_dict))
        return token_str, claims

    # ------------------------------------------------------------------
    # Refresh tokens
    # ------------------------------------------------------------------

    def issue_refresh_token(
        self,
        *,
        sub: str,
        principal_type: PrincipalType,
        ttl: Optional[int] = None,
    ) -> tuple[str, str]:
        """Generate an opaque refresh token and persist its hash.

        Returns ``(opaque_token, row_token_id)`` so the caller can record the
        new row's id on the parent row's ``rotated_to`` column when this is
        issued as part of a rotation.
        """
        token = secrets.token_urlsafe(48)
        ttl = ttl or self._refresh_ttl
        now = datetime.now(timezone.utc)

        with Session(self._engine) as session:
            row = RefreshTokenTable(
                token_hash=_hash_refresh(token),
                principal_sub=sub,
                principal_type=principal_type.value,
                issued_at=now,
                expires_at=now + timedelta(seconds=ttl),
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return token, row.token_id

    def consume_refresh_token(
        self, refresh_token: str, *, rotated_to_token_id: Optional[str] = None
    ) -> RefreshTokenTable:
        """Atomically validate-and-revoke the matching refresh-token row.

        Raises ``TokenError`` for invalid / expired / already-revoked tokens.

        Concurrency: the revoke is implemented as a single
        ``UPDATE ... WHERE revoked_at IS NULL RETURNING ...`` so two parallel
        consumers of the same refresh token cannot both succeed. If the
        update affects zero rows, we re-fetch by ``token_hash`` to
        distinguish "doesn't exist" (invalid_grant) from "already revoked"
        (reuse — fire family-revocation).

        ``rotated_to_token_id`` is recorded on the parent row so future
        forensic queries can walk the rotation chain.
        """
        token_hash = _hash_refresh(refresh_token)
        now = datetime.now(timezone.utc)
        # Stamp every concurrent update with a unique marker so that AFTER
        # commit we can identify which thread actually performed the
        # transition from "active" to "revoked". This is more robust than
        # ``rowcount`` (which is unreliable across SQLite + thread pools)
        # and works for any backend.
        claim_marker = rotated_to_token_id or new_ulid_str()
        with Session(self._engine) as session:
            stmt = (
                update(RefreshTokenTable)
                .where(
                    RefreshTokenTable.token_hash == token_hash,
                    RefreshTokenTable.revoked_at.is_(None),  # type: ignore[union-attr]
                )
                .values(revoked_at=now, rotated_to=claim_marker)
            )
            session.execute(stmt)
            session.commit()

            row = session.exec(
                select(RefreshTokenTable).where(
                    RefreshTokenTable.token_hash == token_hash
                )
            ).first()

            if row is None:
                # No row at all — token doesn't exist, OR was retention-swept.
                raise TokenError("invalid_grant")
            if _ensure_aware(row.expires_at) < now:
                raise TokenError("invalid_grant: expired")
            if row.rotated_to == claim_marker:
                # WE were the thread that flipped this row.
                return row
            # Someone else (or a previous request) already revoked this.
            # Reuse detected: revoke the entire family.
            self._revoke_all_for_principal(session, row.principal_sub)
            session.commit()
            raise TokenError("invalid_grant: refresh-token reuse detected")

    def _revoke_all_for_principal(self, session: Session, principal_sub: str) -> int:
        stmt = select(RefreshTokenTable).where(
            RefreshTokenTable.principal_sub == principal_sub,
            RefreshTokenTable.revoked_at.is_(None),  # type: ignore[union-attr]
        )
        rows = list(session.exec(stmt).all())
        now = datetime.now(timezone.utc)
        for r in rows:
            r.revoked_at = now
            session.add(r)
        return len(rows)

    def revoke_refresh_token(self, refresh_token: str) -> bool:
        """Mark a refresh token as revoked. Returns True if a row was changed."""
        token_hash = _hash_refresh(refresh_token)
        with Session(self._engine) as session:
            stmt = select(RefreshTokenTable).where(
                RefreshTokenTable.token_hash == token_hash
            )
            row = session.exec(stmt).first()
            if row is None or row.revoked_at is not None:
                return False
            row.revoked_at = datetime.now(timezone.utc)
            session.add(row)
            session.commit()
            return True

    # ------------------------------------------------------------------
    # Verification / introspection
    # ------------------------------------------------------------------

    def _enforce_algorithm(self, token: str) -> None:
        """Reject tokens whose JWS header alg is not in ALLOWED_ALGORITHMS.

        Closes the classic alg-confusion attack (e.g., HS256-with-public-key
        forgery) before the token reaches joserfc's decoder.
        """
        try:
            header_b64 = token.split(".", maxsplit=1)[0]
            padding = 4 - (len(header_b64) % 4)
            if padding != 4:
                header_b64 += "=" * padding
            header = json.loads(base64.urlsafe_b64decode(header_b64))
            alg = header.get("alg")
        except Exception as e:
            raise TokenError("invalid_token: malformed header") from e
        if alg not in self.ALLOWED_ALGORITHMS:
            raise TokenError(f"invalid_token: disallowed alg {alg!r}")

    def verify_token(self, token: str) -> JWTClaims:
        """Verify a JWT against the JWKS and return its claims.

        Checks signature, ``exp``, ``iss``, ``aud`` and the deny-list. Raises
        ``TokenError`` on failure.
        """
        active_keys = self._sks.list_active_keys()
        if not active_keys:
            raise TokenError("no signing keys available")

        # Build a KeySet from the active public keys (joserfc's preferred
        # input). The SigningKeyService keeps PEMs locally, so we don't need
        # to round-trip through a JWKS dict here.
        key_set = KeySet(
            [
                RSAKey.import_key(row.public_key_pem, parameters={"kid": row.kid})
                for row in active_keys
            ]
        )

        # Defense-in-depth: pre-parse the JWS header and reject anything that
        # isn't on our allowlist before we hand the token to joserfc. This
        # closes the alg-confusion path even if a malformed key were ever
        # added to the set (e.g., an HS-typed key snuck in).
        self._enforce_algorithm(token)

        try:
            decoded = jwt.decode(
                token, key_set, algorithms=list(self.ALLOWED_ALGORITHMS)
            )
            JWTClaimsRegistry(
                iss={"essential": True, "value": self._issuer},
                aud={"essential": True, "value": self._audience},
                exp={"essential": True},
                leeway=self._clock_skew,
            ).validate(decoded.claims)
        except Exception as e:
            raise TokenError(f"invalid_token: {e}") from e

        try:
            claims = JWTClaims(**decoded.claims)
        except Exception as e:
            raise TokenError(f"invalid_token_claims: {e}") from e

        if self._dls.is_revoked(claims.jti):
            raise TokenError("invalid_token: revoked")

        return claims

    def introspect(self, token: str) -> dict[str, Any]:
        """RFC 7662 introspection. Returns ``{'active': False}`` for any failure."""
        try:
            claims = self.verify_token(token)
        except TokenError:
            return {"active": False}
        out = claims.model_dump()
        out["active"] = True
        return out

    def revoke_access_token(self, jti: str, exp_unix: int) -> None:
        """Add an access token's jti to the deny-list."""
        self._dls.revoke(jti, exp_unix)

    # ------------------------------------------------------------------
    # Composite responses
    # ------------------------------------------------------------------

    def make_token_response(
        self,
        *,
        access_token: str,
        ttl: int,
        refresh_token: Optional[str] = None,
    ) -> TokenResponse:
        """Build the OAuth 2.0 token-endpoint response body."""
        return TokenResponse(
            access_token=access_token,
            expires_in=ttl,
            refresh_token=refresh_token,
        )

"""JWT issuance, verification, and refresh-token management."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from authlib.jose import jwt
from madsci.auth_manager.services.deny_list_service import DenyListService
from madsci.auth_manager.services.signing_key_service import SigningKeyService
from madsci.auth_manager.tables import RefreshTokenTable
from madsci.common.types.auth_types import (
    JWTClaims,
    PrincipalType,
    TokenResponse,
)
from madsci.common.utils import new_ulid_str
from sqlmodel import Session, select


def _hash_refresh(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


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
    ) -> None:
        """Wire the token service to its signing-key, deny-list, and lab identity."""
        self._engine = engine
        self._sks = signing_key_service
        self._dls = deny_list_service
        self._issuer = issuer
        self._audience = audience
        self._access_ttl = access_token_ttl
        self._refresh_ttl = refresh_token_ttl

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
        private_pem = signing_row.private_key_pem
        token_bytes = jwt.encode(header, claims_dict, private_pem)
        token_str = token_bytes.decode("ascii")

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
    ) -> str:
        """Generate an opaque refresh token and persist its hash."""
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
        return token

    def consume_refresh_token(self, refresh_token: str) -> RefreshTokenTable:
        """Validate, revoke, and return the matching refresh-token row.

        Raises ``TokenError`` for invalid / expired / already-revoked tokens.

        On detected reuse of an already-revoked token, all refresh tokens for
        the same principal are revoked (per the reuse-detection requirement).
        """
        token_hash = _hash_refresh(refresh_token)
        with Session(self._engine) as session:
            stmt = select(RefreshTokenTable).where(
                RefreshTokenTable.token_hash == token_hash
            )
            row = session.exec(stmt).first()
            if row is None:
                raise TokenError("invalid_grant")

            now = datetime.now(timezone.utc)
            if _ensure_aware(row.expires_at) < now:
                raise TokenError("invalid_grant: expired")

            if row.revoked_at is not None:
                # Reuse detection: revoke all refresh tokens for this principal.
                self._revoke_all_for_principal(session, row.principal_sub)
                session.commit()
                raise TokenError("invalid_grant: refresh-token reuse detected")

            row.revoked_at = now
            session.add(row)
            session.commit()
            session.refresh(row)
            return row

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

    def verify_token(self, token: str) -> JWTClaims:
        """Verify a JWT against the JWKS and return its claims.

        Checks signature, ``exp``, ``iss``, ``aud`` and the deny-list. Raises
        ``TokenError`` on failure.
        """
        keys = self._sks.list_active_keys()
        if not keys:
            raise TokenError("no signing keys available")

        jwks = self._sks.jwks()

        try:
            decoded = jwt.decode(
                token,
                jwks,
                claims_options={
                    "iss": {"essential": True, "value": self._issuer},
                    "aud": {"essential": True, "value": self._audience},
                    "exp": {"essential": True},
                },
            )
            decoded.validate()
        except Exception as e:
            raise TokenError(f"invalid_token: {e}") from e

        # Authlib returns a dict-like JWTClaims; convert to our model
        try:
            claims = JWTClaims(**dict(decoded))
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

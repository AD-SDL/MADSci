"""RSA signing-key management for the Auth Manager.

Implements key generation, persistence, rotation, and JWKS export. RS256 is
the only supported algorithm (per Decision 1).
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from typing import Any, Optional

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import (
    load_pem_private_key,
    load_pem_public_key,
)
from madsci.auth_manager.tables import SigningKeyTable
from madsci.common.utils import new_ulid_str
from sqlmodel import Session, select


def _b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def _int_to_b64u(i: int) -> str:
    byte_len = (i.bit_length() + 7) // 8
    return _b64u(i.to_bytes(byte_len, "big"))


class SigningKeyService:
    """Manage rotating RSA signing keys."""

    def __init__(self, engine: Any, key_size: int = 2048) -> None:
        """Bind to a SQLAlchemy engine and choose the RSA key size in bits."""
        self._engine = engine
        self._key_size = key_size

    # ------------------------------------------------------------------
    # Generation / persistence
    # ------------------------------------------------------------------

    def generate_keypair(self, *, set_signing: bool = True) -> SigningKeyTable:
        """Generate a new RSA keypair and persist it.

        Args:
            set_signing: If True (default), the new key becomes the
                ``active_for_signing`` key and any previously-signing key is
                downgraded to verify-only.
        """
        private = rsa.generate_private_key(
            public_exponent=65537, key_size=self._key_size
        )
        private_pem = private.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("ascii")
        public_pem = (
            private.public_key()
            .public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            .decode("ascii")
        )
        kid = new_ulid_str()

        with Session(self._engine) as session:
            if set_signing:
                # Demote any previously-signing key to verify-only
                stmt = select(SigningKeyTable).where(
                    SigningKeyTable.active_for_signing.is_(True)
                )
                for old in session.exec(stmt).all():
                    old.active_for_signing = False
                    session.add(old)

            new_row = SigningKeyTable(
                kid=kid,
                public_key_pem=public_pem,
                private_key_pem=private_pem,
                algorithm="RS256",
                active=True,
                active_for_signing=set_signing,
            )
            session.add(new_row)
            session.commit()
            session.refresh(new_row)
            return new_row

    # ------------------------------------------------------------------
    # Lookup helpers
    # ------------------------------------------------------------------

    def get_signing_key(self) -> Optional[SigningKeyTable]:
        """Return the currently-active signing key, or None if none exists."""
        with Session(self._engine) as session:
            stmt = (
                select(SigningKeyTable)
                .where(SigningKeyTable.active_for_signing.is_(True))
                .order_by(SigningKeyTable.created_at.desc())
            )
            return session.exec(stmt).first()

    def get_key(self, kid: str) -> Optional[SigningKeyTable]:
        """Look up a signing key by kid."""
        with Session(self._engine) as session:
            return session.get(SigningKeyTable, kid)

    def list_active_keys(self) -> list[SigningKeyTable]:
        """All keys currently published in JWKS (i.e., active=True)."""
        with Session(self._engine) as session:
            stmt = (
                select(SigningKeyTable)
                .where(SigningKeyTable.active.is_(True))
                .order_by(SigningKeyTable.created_at.desc())
            )
            return list(session.exec(stmt).all())

    def list_all_keys(self) -> list[SigningKeyTable]:
        """All keys including retired ones, newest first."""
        with Session(self._engine) as session:
            stmt = select(SigningKeyTable).order_by(SigningKeyTable.created_at.desc())
            return list(session.exec(stmt).all())

    # ------------------------------------------------------------------
    # Rotation / retire
    # ------------------------------------------------------------------

    def rotate(self) -> SigningKeyTable:
        """Generate a new signing key, demoting the current one to verify-only."""
        return self.generate_keypair(set_signing=True)

    def retire(self, kid: str) -> bool:
        """Retire a key (remove from JWKS, delete private material).

        Returns True if a row was modified, False otherwise.
        """
        with Session(self._engine) as session:
            row = session.get(SigningKeyTable, kid)
            if row is None:
                return False
            row.active = False
            row.active_for_signing = False
            row.private_key_pem = ""
            row.retired_at = datetime.now(timezone.utc)
            session.add(row)
            session.commit()
            return True

    # ------------------------------------------------------------------
    # JWKS export
    # ------------------------------------------------------------------

    def jwks(self) -> dict[str, list[dict[str, str]]]:
        """Return a JWKS document for all currently-active keys."""
        keys = []
        for row in self.list_active_keys():
            pub = load_pem_public_key(row.public_key_pem.encode("ascii"))
            numbers = pub.public_numbers()  # type: ignore[attr-defined]
            keys.append(
                {
                    "kty": "RSA",
                    "use": "sig",
                    "alg": row.algorithm,
                    "kid": row.kid,
                    "n": _int_to_b64u(numbers.n),
                    "e": _int_to_b64u(numbers.e),
                }
            )
        return {"keys": keys}

    def load_private_key(self, row: SigningKeyTable) -> Any:
        """Load the private key for signing operations."""
        return load_pem_private_key(row.private_key_pem.encode("ascii"), password=None)

    def load_public_key(self, row: SigningKeyTable) -> Any:
        """Load the public key for verification operations."""
        return load_pem_public_key(row.public_key_pem.encode("ascii"))

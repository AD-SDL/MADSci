"""Argon2id password hashing helpers."""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError


class PasswordService:
    """Wrapper around argon2-cffi for password hashing and verification."""

    def __init__(
        self,
        time_cost: int = 3,
        memory_cost: int = 64 * 1024,
        parallelism: int = 4,
    ) -> None:
        """Configure the underlying ``argon2.PasswordHasher``."""
        self._hasher = PasswordHasher(
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
        )

    def hash_password(self, password: str) -> str:
        """Hash a plaintext password with Argon2id."""
        return self._hasher.hash(password)

    def verify_password(self, password_hash: str, password: str) -> bool:
        """Verify a password against a stored hash. Returns False on mismatch."""
        try:
            return self._hasher.verify(password_hash, password)
        except VerifyMismatchError:
            return False
        except Exception:
            return False

    def needs_rehash(self, password_hash: str) -> bool:
        """Whether the stored hash should be re-hashed with current params."""
        return self._hasher.check_needs_rehash(password_hash)

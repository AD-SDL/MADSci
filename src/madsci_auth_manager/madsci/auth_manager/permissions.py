"""Canonical permission strings used by the Auth Manager itself.

Every administrative endpoint on the Auth Manager carries a
``@requires(permission=...)`` decorator naming one of the strings below.
Operators grant these via the built-in ``admin`` role (which holds the ``*``
wildcard), or via a custom role for narrower delegation (e.g., a separate
``key-rotator`` role for an automated key-rotation job).
"""

from __future__ import annotations


class AuthPermissions:
    """Auth Manager admin-endpoint permission strings."""

    USER_READ = "auth.user.read"
    USER_WRITE = "auth.user.write"
    PROJECT_READ = "auth.project.read"
    PROJECT_WRITE = "auth.project.write"
    ROLE_READ = "auth.role.read"
    ROLE_WRITE = "auth.role.write"
    ROLE_GRANT = "auth.role.grant"
    PRINCIPAL_WRITE = "auth.principal.write"
    CREDENTIALS_ROTATE = "auth.credentials.rotate"
    KEY_READ = "auth.key.read"
    KEY_ROTATE = "auth.key.rotate"
    KEY_RETIRE = "auth.key.retire"
    TOKEN_INTROSPECT = "auth.token.introspect"  # noqa: S105
    TOKEN_REVOKE = "auth.token.revoke"  # noqa: S105


ALL_AUTH_PERMISSIONS: tuple[str, ...] = (
    AuthPermissions.USER_READ,
    AuthPermissions.USER_WRITE,
    AuthPermissions.PROJECT_READ,
    AuthPermissions.PROJECT_WRITE,
    AuthPermissions.ROLE_READ,
    AuthPermissions.ROLE_WRITE,
    AuthPermissions.ROLE_GRANT,
    AuthPermissions.PRINCIPAL_WRITE,
    AuthPermissions.CREDENTIALS_ROTATE,
    AuthPermissions.KEY_READ,
    AuthPermissions.KEY_ROTATE,
    AuthPermissions.KEY_RETIRE,
    AuthPermissions.TOKEN_INTROSPECT,
    AuthPermissions.TOKEN_REVOKE,
)


__all__ = ["ALL_AUTH_PERMISSIONS", "AuthPermissions"]

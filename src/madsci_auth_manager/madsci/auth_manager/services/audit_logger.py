"""Append-only audit log for the Auth Manager."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from madsci.auth_manager.tables import AuditLogTable
from sqlmodel import Session, select


class AuditLogger:
    """Persist security-relevant events to the ``audit_log`` table.

    Per the ``Audit log`` requirement in ``auth-identity-model/spec.md``, the
    table is append-only at the application level. There is no public
    ``update``/``delete`` API; any attempt to mutate a row by an admin must
    itself produce a new audit entry recording the attempt.
    """

    def __init__(self, engine: Any) -> None:
        """Bind the logger to a SQLAlchemy engine."""
        self._engine = engine

    def log(
        self,
        event_type: str,
        *,
        principal_id: Optional[str] = None,
        principal_type: Optional[str] = None,
        grant_type: Optional[str] = None,
        token_jti: Optional[str] = None,
        source_ip: Optional[str] = None,
        success: bool = True,
        details: Optional[dict] = None,
    ) -> AuditLogTable:
        """Append a new audit row and return it.

        Raises whatever the underlying DB raises — callers MUST NOT swallow
        these exceptions for state-changing operations (failure-closed).
        """
        with Session(self._engine) as session:
            row = AuditLogTable(
                event_type=event_type,
                event_time=datetime.now(timezone.utc),
                principal_id=principal_id,
                principal_type=principal_type,
                grant_type=grant_type,
                token_jti=token_jti,
                source_ip=source_ip,
                success=success,
                details=details,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return row

    def query(
        self,
        *,
        principal_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[AuditLogTable]:
        """Query audit rows with optional filters; newest first."""
        with Session(self._engine) as session:
            stmt = select(AuditLogTable).order_by(AuditLogTable.event_time.desc())
            if principal_id:
                stmt = stmt.where(AuditLogTable.principal_id == principal_id)
            if event_type:
                stmt = stmt.where(AuditLogTable.event_type == event_type)
            stmt = stmt.limit(limit)
            return list(session.exec(stmt).all())


# Canonical event-type names — kept here so callers can reference constants
# rather than naked strings, and so the docs guide can enumerate them.


class AuditEvent:
    """Canonical audit event type strings.

    These are event-type names persisted in the ``audit_log.event_type``
    column, NOT secrets. The S105 suppression on this class quiets ruff's
    hardcoded-password heuristic for the ``TOKEN_*`` and ``USER_PASSWORD_*``
    constants.
    """

    USER_CREATE = "user.create"
    USER_DEACTIVATE = "user.deactivate"
    USER_PASSWORD_CHANGE = "user.password_change"  # noqa: S105
    ROLE_GRANT = "role.grant"
    ROLE_REVOKE = "role.revoke"
    TOKEN_ISSUE = "token.issue"  # noqa: S105
    TOKEN_REFRESH = "token.refresh"  # noqa: S105
    TOKEN_REVOKE = "token.revoke"  # noqa: S105
    TOKEN_REJECT = "token.reject"  # noqa: S105
    SERVICE_ACCOUNT_REGISTER = "service_account.register"
    SERVICE_ACCOUNT_ROTATE = "service_account.rotate"
    NODE_REGISTER = "node.register"
    NODE_ROTATE = "node.rotate"
    BOOTSTRAP = "bootstrap"
    KEY_ROTATE = "key.rotate"
    KEY_RETIRE = "key.retire"
    AUDIT_TAMPER_ATTEMPT = "audit.tamper_attempt"
    RATE_LIMITED = "rate_limited"

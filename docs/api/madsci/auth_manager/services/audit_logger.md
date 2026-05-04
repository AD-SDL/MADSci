Module madsci.auth_manager.services.audit_logger
================================================
Append-only audit log for the Auth Manager.

Classes
-------

`AuditEvent()`
:   Canonical audit event type strings.
    
    These are event-type names persisted in the ``audit_log.event_type``
    column, NOT secrets. The S105 suppression on this class quiets ruff's
    hardcoded-password heuristic for the ``TOKEN_*`` and ``USER_PASSWORD_*``
    constants.

    ### Class variables

    `AUDIT_TAMPER_ATTEMPT`
    :

    `BOOTSTRAP`
    :

    `KEY_RETIRE`
    :

    `KEY_ROTATE`
    :

    `NODE_REGISTER`
    :

    `NODE_ROTATE`
    :

    `RATE_LIMITED`
    :

    `ROLE_GRANT`
    :

    `ROLE_REVOKE`
    :

    `SERVICE_ACCOUNT_REGISTER`
    :

    `SERVICE_ACCOUNT_ROTATE`
    :

    `TOKEN_ISSUE`
    :

    `TOKEN_REFRESH`
    :

    `TOKEN_REJECT`
    :

    `TOKEN_REVOKE`
    :

    `USER_CREATE`
    :

    `USER_DEACTIVATE`
    :

    `USER_PASSWORD_CHANGE`
    :

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
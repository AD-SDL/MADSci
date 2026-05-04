"""MADSci Auth Manager FastAPI server.

Implements the OAuth 2.0 token, introspection, revocation, and JWKS
endpoints, plus the admin surface for users, projects, roles,
service-accounts, node identities, signing keys, and the deny-list.

Per Decision 12, this manager is single-tenant: all data is implicitly
scoped to the deployment's ``lab_id``.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any, Optional

import fastapi
from classy_fastapi import delete, get, patch, post
from fastapi import Form, HTTPException, Request, Response
from madsci.auth_manager.server_types import (
    AddMemberRequest,
    BootstrapResponse,
    CreateProjectRequest,
    CreateRoleRequest,
    CreateUserRequest,
    CredentialResponse,
    DenyListResponse,
    GrantRoleRequest,
    IntrospectRequest,
    KeyInfo,
    KeysHealthResponse,
    ProjectResponse,
    RegisterNodeRequest,
    RegisterServiceAccountRequest,
    RevokeRequest,
    RoleResponse,
    UpdateUserRequest,
    UserResponse,
)
from madsci.auth_manager.services import (
    AuditLogger,
    DenyListService,
    PasswordService,
    SigningKeyService,
    TokenService,
)
from madsci.auth_manager.services.audit_logger import AuditEvent
from madsci.auth_manager.services.token_service import TokenError
from madsci.auth_manager.tables import (
    GlobalRoleGrantTable,
    LabBindingTable,
    NodeIdentityTable,
    ProjectMembershipTable,
    ProjectTable,
    RolePermissionTable,
    RoleTable,
    ServiceAccountTable,
    UserTable,
    metadata,
)
from madsci.common.db_handlers.postgres_handler import (
    PostgresHandler,
    SQLAlchemyHandler,
)
from madsci.common.manager_base import AbstractManagerBase
from madsci.common.types.auth_types import (
    AuthManagerSettings,
    GrantType,
    PrincipalType,
    TokenResponse,
)
from madsci.common.types.event_types import EventType
from madsci.common.utils import new_ulid_str
from sqlmodel import Session, select

# Built-in role definitions seeded by ``bootstrap``.
BUILTIN_ROLES: list[dict[str, Any]] = [
    {
        "name": "admin",
        "description": "Full administrative privileges over the lab.",
        "permissions": ["*"],
    },
    {
        "name": "experimenter",
        "description": "Run experiments, submit workflows, manage resources.",
        "permissions": [
            "experiment.read",
            "experiment.write",
            "workflow.read",
            "workflow.submit",
            "resource.read",
            "resource.write",
        ],
    },
    {
        "name": "operator",
        "description": "Operate workcells and nodes.",
        "permissions": [
            "workcell.read",
            "workcell.execute",
            "node.read",
            "node.execute_action",
        ],
    },
    {
        "name": "read_only",
        "description": "Read-only access to all observable state.",
        "permissions": [
            "experiment.read",
            "workflow.read",
            "resource.read",
            "workcell.read",
            "node.read",
            "event.read",
        ],
    },
]


def _client_ip(request: Request) -> Optional[str]:
    """Get the client IP, preferring X-Forwarded-For when present.

    Operators terminating TLS at a reverse proxy MUST configure the proxy to
    forward real client IPs (see ``docs/guides/auth_operator.md``).
    """
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None


class AuthManager(AbstractManagerBase[AuthManagerSettings]):
    """MADSci Auth Manager REST server."""

    SETTINGS_CLASS = AuthManagerSettings

    def __init__(
        self,
        settings: Optional[AuthManagerSettings] = None,
        postgres_handler: Optional[PostgresHandler] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the Auth Manager, optionally injecting a database handler."""
        self._postgres_handler = postgres_handler
        super().__init__(settings=settings, **kwargs)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self, **kwargs: Any) -> None:  # noqa: ARG002
        """Initialize handlers, schema, and service objects."""
        if self._postgres_handler is None:
            try:
                self._postgres_handler = SQLAlchemyHandler.from_url(
                    self.settings.database_url
                )
            except Exception:
                self.logger.warning(
                    "Could not connect to PostgreSQL via settings.database_url;"
                    " AuthManager initialized without persistence",
                    event_type=EventType.MANAGER_ERROR,
                    exc_info=True,
                )
                return

        engine = self._postgres_handler.get_engine()
        # Ensure tables exist (idempotent). In production, Alembic migrations
        # handle schema; this also covers dev / SQLite test paths.
        self._postgres_handler.create_all_tables(metadata)

        self._password_service = PasswordService(
            time_cost=self.settings.argon2_time_cost,
            memory_cost=self.settings.argon2_memory_cost,
            parallelism=self.settings.argon2_parallelism,
        )
        self._signing_key_service = SigningKeyService(engine)
        self._deny_list_service = DenyListService(
            engine, persist_grace_seconds=self.settings.deny_list_persist_grace
        )
        self._audit = AuditLogger(engine)

        # Resolve / persist lab_id binding (Decision 12)
        self._lab_id = self._resolve_lab_binding()

        self._token_service = TokenService(
            engine=engine,
            signing_key_service=self._signing_key_service,
            deny_list_service=self._deny_list_service,
            issuer=str(self.settings.server_url).rstrip("/"),
            audience=self._lab_id or "lab-unbound",
            access_token_ttl=self.settings.access_token_ttl,
            refresh_token_ttl=self.settings.refresh_token_ttl,
        )

        self.logger.info(
            "AuthManager initialized",
            event_type=EventType.MANAGER_START,
            lab_id=self._lab_id,
        )

    def _resolve_lab_binding(self) -> Optional[str]:
        """Read or create the lab_id binding row."""
        engine = self._postgres_handler.get_engine()
        with Session(engine) as session:
            existing = session.get(LabBindingTable, 1)
            if existing is None:
                if self.settings.lab_id is None:
                    return None
                row = LabBindingTable(id=1, lab_id=self.settings.lab_id)
                session.add(row)
                session.commit()
                return self.settings.lab_id

            if (
                self.settings.lab_id is not None
                and existing.lab_id != self.settings.lab_id
            ):
                raise RuntimeError(
                    f"AuthManager database is bound to lab_id={existing.lab_id!r}"
                    f" but settings supplied lab_id={self.settings.lab_id!r}."
                    " Refusing to start (Decision 12)."
                )
            return existing.lab_id

    # ------------------------------------------------------------------
    # Bootstrap (callable from CLI as well as direct API)
    # ------------------------------------------------------------------

    def bootstrap(
        self,
        *,
        admin_username: str,
        admin_password: str,
        admin_email: Optional[str] = None,
    ) -> BootstrapResponse:
        """Idempotent bootstrap: create admin user, signing key, built-in roles."""
        engine = self._postgres_handler.get_engine()

        signing_kid: Optional[str] = None
        with Session(engine) as session:
            # Seed built-in roles
            existing_roles = {r.name: r for r in session.exec(select(RoleTable)).all()}
            for role_def in BUILTIN_ROLES:
                if role_def["name"] in existing_roles:
                    continue
                role = RoleTable(
                    name=role_def["name"], description=role_def["description"]
                )
                session.add(role)
                session.flush()
                for perm in role_def["permissions"]:
                    session.add(
                        RolePermissionTable(role_id=role.role_id, permission=perm)
                    )
                existing_roles[role_def["name"]] = role
            session.commit()

            admin_role = session.exec(
                select(RoleTable).where(RoleTable.name == "admin")
            ).first()
            if admin_role is None:
                raise RuntimeError("admin role missing after seeding")

            # Create admin user (idempotent on username)
            admin = session.exec(
                select(UserTable).where(UserTable.username == admin_username)
            ).first()
            if admin is None:
                admin = UserTable(
                    username=admin_username,
                    email=admin_email,
                    password_hash=self._password_service.hash_password(admin_password),
                )
                session.add(admin)
                session.flush()
                session.add(
                    GlobalRoleGrantTable(
                        role_id=admin_role.role_id, user_id=admin.user_id
                    )
                )
                session.commit()
                session.refresh(admin)

            # Generate signing key if none exists
            current = self._signing_key_service.get_signing_key()
            if current is None:
                key_row = self._signing_key_service.generate_keypair()
                signing_kid = key_row.kid
            else:
                signing_kid = current.kid

            self._audit.log(
                AuditEvent.BOOTSTRAP,
                principal_id=admin.user_id,
                principal_type="user",
                details={
                    "username": admin_username,
                    "signing_kid": signing_kid,
                },
            )
            return BootstrapResponse(
                user_id=admin.user_id,
                username=admin.username,
                admin_role_id=admin_role.role_id,
                signing_kid=signing_kid,
            )

    # ------------------------------------------------------------------
    # Helpers used by token endpoints
    # ------------------------------------------------------------------

    def _collect_user_grants(
        self, session: Session, user: UserTable
    ) -> tuple[list[str], list[str], list[str]]:
        """Return ``(role_ids, permissions, project_ids)`` for a user."""
        # Global role grants
        role_ids: list[str] = []
        global_grants = session.exec(
            select(GlobalRoleGrantTable).where(
                GlobalRoleGrantTable.user_id == user.user_id
            )
        ).all()
        role_ids.extend([g.role_id for g in global_grants])

        # Project memberships
        memberships = session.exec(
            select(ProjectMembershipTable).where(
                ProjectMembershipTable.user_id == user.user_id
            )
        ).all()
        project_ids = sorted({m.project_id for m in memberships})
        role_ids.extend([m.role_id for m in memberships])
        role_ids = sorted(set(role_ids))

        permissions: set[str] = set()
        if role_ids:
            perm_rows = session.exec(
                select(RolePermissionTable).where(
                    RolePermissionTable.role_id.in_(role_ids)  # type: ignore[union-attr]
                )
            ).all()
            permissions = {p.permission for p in perm_rows}
        return role_ids, sorted(permissions), project_ids

    def _collect_principal_grants(
        self,
        session: Session,
        *,
        user_id: Optional[str] = None,
        service_account_client_id: Optional[str] = None,
        node_identity_client_id: Optional[str] = None,
    ) -> tuple[list[str], list[str]]:
        """Return ``(role_ids, permissions)`` for a service-account or node."""
        stmt = select(GlobalRoleGrantTable)
        if service_account_client_id:
            stmt = stmt.where(
                GlobalRoleGrantTable.service_account_client_id
                == service_account_client_id
            )
        elif node_identity_client_id:
            stmt = stmt.where(
                GlobalRoleGrantTable.node_identity_client_id == node_identity_client_id
            )
        elif user_id:
            stmt = stmt.where(GlobalRoleGrantTable.user_id == user_id)
        rows = list(session.exec(stmt).all())
        role_ids = sorted({r.role_id for r in rows})
        if not role_ids:
            return [], []
        perm_rows = session.exec(
            select(RolePermissionTable).where(
                RolePermissionTable.role_id.in_(role_ids)  # type: ignore[union-attr]
            )
        ).all()
        return role_ids, sorted({p.permission for p in perm_rows})

    # ------------------------------------------------------------------
    # /token endpoint (RFC 6749)
    # ------------------------------------------------------------------

    @post("/token")
    async def token_endpoint(
        self,
        request: Request,
        grant_type: str = Form(...),
        username: Optional[str] = Form(None),
        password: Optional[str] = Form(None),
        refresh_token: Optional[str] = Form(None),
        client_id: Optional[str] = Form(None),
        client_secret: Optional[str] = Form(None),
    ) -> TokenResponse:
        """OAuth 2.0 token endpoint (password, refresh_token, client_credentials)."""
        ip = _client_ip(request)
        try:
            gt = GrantType(grant_type)
        except ValueError:
            self._audit.log(
                AuditEvent.TOKEN_REJECT,
                source_ip=ip,
                success=False,
                details={"reason": "unsupported_grant_type", "grant_type": grant_type},
            )
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "unsupported_grant_type",
                    "error_description": (
                        "grant_type must be one of password, refresh_token,"
                        " client_credentials"
                    ),
                },
            ) from None

        if gt == GrantType.PASSWORD:
            return self._handle_password_grant(username, password, ip)
        if gt == GrantType.REFRESH_TOKEN:
            return self._handle_refresh_grant(refresh_token, ip)
        return self._handle_client_credentials_grant(client_id, client_secret, ip)

    def _handle_password_grant(
        self, username: Optional[str], password: Optional[str], ip: Optional[str]
    ) -> TokenResponse:
        if not username or not password:
            raise HTTPException(status_code=400, detail="missing username or password")
        engine = self._postgres_handler.get_engine()
        with Session(engine) as session:
            user = session.exec(
                select(UserTable).where(UserTable.username == username)
            ).first()
            if user is None or not user.is_active:
                self._audit.log(
                    AuditEvent.TOKEN_REJECT,
                    source_ip=ip,
                    success=False,
                    details={
                        "username": username,
                        "reason": "no_such_user_or_inactive",
                    },
                )
                raise HTTPException(status_code=401, detail="invalid_grant")
            if not self._password_service.verify_password(user.password_hash, password):
                self._audit.log(
                    AuditEvent.TOKEN_REJECT,
                    principal_id=user.user_id,
                    principal_type="user",
                    source_ip=ip,
                    success=False,
                    details={"reason": "bad_password"},
                )
                raise HTTPException(status_code=401, detail="invalid_grant")

            role_ids, permissions, project_ids = self._collect_user_grants(
                session, user
            )

        access, claims = self._token_service.issue_access_token(
            sub=user.user_id,
            principal_type=PrincipalType.USER,
            roles=role_ids,
            permissions=permissions,
            user_id=user.user_id,
            project_ids=project_ids,
        )
        refresh = self._token_service.issue_refresh_token(
            sub=user.user_id, principal_type=PrincipalType.USER
        )
        self._audit.log(
            AuditEvent.TOKEN_ISSUE,
            principal_id=user.user_id,
            principal_type="user",
            grant_type=GrantType.PASSWORD.value,
            token_jti=claims.jti,
            source_ip=ip,
        )
        return self._token_service.make_token_response(
            access_token=access,
            ttl=self.settings.access_token_ttl,
            refresh_token=refresh,
        )

    def _handle_refresh_grant(
        self, refresh_token: Optional[str], ip: Optional[str]
    ) -> TokenResponse:
        if not refresh_token:
            raise HTTPException(status_code=400, detail="missing refresh_token")
        try:
            row = self._token_service.consume_refresh_token(refresh_token)
        except TokenError as e:
            self._audit.log(
                AuditEvent.TOKEN_REJECT,
                source_ip=ip,
                success=False,
                details={"reason": str(e)},
            )
            raise HTTPException(status_code=401, detail="invalid_grant") from e

        engine = self._postgres_handler.get_engine()
        with Session(engine) as session:
            if row.principal_type == PrincipalType.USER.value:
                user = session.get(UserTable, row.principal_sub)
                if user is None or not user.is_active:
                    raise HTTPException(status_code=401, detail="invalid_grant")
                role_ids, permissions, project_ids = self._collect_user_grants(
                    session, user
                )
                access, claims = self._token_service.issue_access_token(
                    sub=user.user_id,
                    principal_type=PrincipalType.USER,
                    roles=role_ids,
                    permissions=permissions,
                    user_id=user.user_id,
                    project_ids=project_ids,
                )
            else:
                # Refresh tokens are typically not issued for service accounts /
                # nodes (client_credentials flow), but if present, re-issue.
                ptype = PrincipalType(row.principal_type)
                role_ids, permissions = self._collect_principal_grants(
                    session,
                    service_account_client_id=row.principal_sub
                    if ptype == PrincipalType.SERVICE_ACCOUNT
                    else None,
                    node_identity_client_id=row.principal_sub
                    if ptype == PrincipalType.NODE
                    else None,
                )
                access, claims = self._token_service.issue_access_token(
                    sub=row.principal_sub,
                    principal_type=ptype,
                    roles=role_ids,
                    permissions=permissions,
                )

        new_refresh = self._token_service.issue_refresh_token(
            sub=row.principal_sub, principal_type=PrincipalType(row.principal_type)
        )
        self._audit.log(
            AuditEvent.TOKEN_REFRESH,
            principal_id=row.principal_sub,
            principal_type=row.principal_type,
            grant_type=GrantType.REFRESH_TOKEN.value,
            token_jti=claims.jti,
            source_ip=ip,
        )
        return self._token_service.make_token_response(
            access_token=access,
            ttl=self.settings.access_token_ttl,
            refresh_token=new_refresh,
        )

    def _handle_client_credentials_grant(
        self,
        client_id: Optional[str],
        client_secret: Optional[str],
        ip: Optional[str],
    ) -> TokenResponse:
        if not client_id or not client_secret:
            raise HTTPException(
                status_code=400, detail="missing client_id or client_secret"
            )

        engine = self._postgres_handler.get_engine()
        with Session(engine) as session:
            sa = session.get(ServiceAccountTable, client_id)
            node = session.get(NodeIdentityTable, client_id) if sa is None else None

            if (
                sa is not None
                and sa.is_active
                and self._password_service.verify_password(
                    sa.client_secret_hash, client_secret
                )
            ):
                role_ids, permissions = self._collect_principal_grants(
                    session, service_account_client_id=client_id
                )
                access, claims = self._token_service.issue_access_token(
                    sub=client_id,
                    principal_type=PrincipalType.SERVICE_ACCOUNT,
                    roles=role_ids,
                    permissions=permissions,
                    manager_id=sa.manager_id,
                )
                self._audit.log(
                    AuditEvent.TOKEN_ISSUE,
                    principal_id=client_id,
                    principal_type="service_account",
                    grant_type=GrantType.CLIENT_CREDENTIALS.value,
                    token_jti=claims.jti,
                    source_ip=ip,
                )
                return self._token_service.make_token_response(
                    access_token=access, ttl=self.settings.access_token_ttl
                )

            if (
                node is not None
                and node.is_active
                and self._password_service.verify_password(
                    node.client_secret_hash, client_secret
                )
            ):
                role_ids, permissions = self._collect_principal_grants(
                    session, node_identity_client_id=client_id
                )
                access, claims = self._token_service.issue_access_token(
                    sub=client_id,
                    principal_type=PrincipalType.NODE,
                    roles=role_ids,
                    permissions=permissions,
                    node_id=node.node_id,
                    workcell_id=node.workcell_id,
                )
                self._audit.log(
                    AuditEvent.TOKEN_ISSUE,
                    principal_id=client_id,
                    principal_type="node",
                    grant_type=GrantType.CLIENT_CREDENTIALS.value,
                    token_jti=claims.jti,
                    source_ip=ip,
                )
                return self._token_service.make_token_response(
                    access_token=access, ttl=self.settings.access_token_ttl
                )

        self._audit.log(
            AuditEvent.TOKEN_REJECT,
            source_ip=ip,
            success=False,
            details={"reason": "bad_client_credentials", "client_id": client_id},
        )
        raise HTTPException(status_code=401, detail="invalid_client")

    # ------------------------------------------------------------------
    # /introspect, /revoke, JWKS
    # ------------------------------------------------------------------

    @post("/introspect")
    async def introspect_endpoint(self, body: IntrospectRequest) -> dict[str, Any]:
        """OAuth 2.0 Token Introspection (RFC 7662)."""
        return self._token_service.introspect(body.token)

    @post("/revoke")
    async def revoke_endpoint(self, body: RevokeRequest) -> dict[str, bool]:
        """Revoke an access token and/or refresh token."""
        if body.refresh_token:
            self._token_service.revoke_refresh_token(body.refresh_token)
        if body.token:
            try:
                claims = self._token_service.verify_token(body.token)
                self._token_service.revoke_access_token(claims.jti, claims.exp)
                self._audit.log(
                    AuditEvent.TOKEN_REVOKE,
                    principal_id=claims.sub,
                    principal_type=claims.principal_type.value,
                    token_jti=claims.jti,
                )
            except TokenError:
                # Already invalid; nothing to do
                pass
        return {"revoked": True}

    @get("/.well-known/jwks.json")
    async def jwks_endpoint(self) -> dict[str, Any]:
        """Public JWKS document — no authentication required."""
        return self._signing_key_service.jwks()

    # ------------------------------------------------------------------
    # /users
    # ------------------------------------------------------------------

    @post("/users")
    async def create_user(self, body: CreateUserRequest) -> UserResponse:
        """Create a new user account."""
        engine = self._postgres_handler.get_engine()
        with Session(engine) as session:
            existing = session.exec(
                select(UserTable).where(UserTable.username == body.username)
            ).first()
            if existing is not None:
                raise HTTPException(status_code=409, detail="username already exists")
            user = UserTable(
                username=body.username,
                email=body.email,
                password_hash=self._password_service.hash_password(body.password),
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            self._audit.log(
                AuditEvent.USER_CREATE,
                principal_id=user.user_id,
                principal_type="user",
                details={"username": user.username},
            )
            return UserResponse(
                user_id=user.user_id,
                username=user.username,
                email=user.email,
                is_active=user.is_active,
            )

    @get("/users")
    async def list_users(self) -> list[UserResponse]:
        """List all user accounts."""
        engine = self._postgres_handler.get_engine()
        with Session(engine) as session:
            rows = session.exec(select(UserTable)).all()
            return [
                UserResponse(
                    user_id=r.user_id,
                    username=r.username,
                    email=r.email,
                    is_active=r.is_active,
                )
                for r in rows
            ]

    @get("/users/{user_id}")
    async def get_user(self, user_id: str) -> UserResponse:
        """Fetch a single user by id."""
        engine = self._postgres_handler.get_engine()
        with Session(engine) as session:
            row = session.get(UserTable, user_id)
            if row is None:
                raise HTTPException(status_code=404, detail="user not found")
            return UserResponse(
                user_id=row.user_id,
                username=row.username,
                email=row.email,
                is_active=row.is_active,
            )

    @patch("/users/{user_id}")
    async def update_user(self, user_id: str, body: UpdateUserRequest) -> UserResponse:
        """Patch user fields (deactivate, change password, update email)."""
        engine = self._postgres_handler.get_engine()
        with Session(engine) as session:
            row = session.get(UserTable, user_id)
            if row is None:
                raise HTTPException(status_code=404, detail="user not found")
            changed = False
            if body.is_active is not None and body.is_active != row.is_active:
                row.is_active = body.is_active
                changed = True
                self._audit.log(
                    AuditEvent.USER_DEACTIVATE
                    if not body.is_active
                    else "user.activate",
                    principal_id=row.user_id,
                    principal_type="user",
                )
            if body.email is not None:
                row.email = body.email
                changed = True
            if body.new_password:
                row.password_hash = self._password_service.hash_password(
                    body.new_password
                )
                changed = True
                self._audit.log(
                    AuditEvent.USER_PASSWORD_CHANGE,
                    principal_id=row.user_id,
                    principal_type="user",
                )
            if changed:
                row.updated_at = datetime.now(timezone.utc)
                session.add(row)
                session.commit()
                session.refresh(row)
            return UserResponse(
                user_id=row.user_id,
                username=row.username,
                email=row.email,
                is_active=row.is_active,
            )

    # ------------------------------------------------------------------
    # /projects
    # ------------------------------------------------------------------

    @post("/projects")
    async def create_project(self, body: CreateProjectRequest) -> ProjectResponse:
        """Create a new project."""
        engine = self._postgres_handler.get_engine()
        with Session(engine) as session:
            existing = session.exec(
                select(ProjectTable).where(ProjectTable.name == body.name)
            ).first()
            if existing is not None:
                raise HTTPException(
                    status_code=409, detail="project name already exists"
                )
            row = ProjectTable(name=body.name, description=body.description)
            session.add(row)
            session.commit()
            session.refresh(row)
            return ProjectResponse(
                project_id=row.project_id,
                name=row.name,
                description=row.description,
            )

    @get("/projects")
    async def list_projects(self) -> list[ProjectResponse]:
        """List all projects."""
        engine = self._postgres_handler.get_engine()
        with Session(engine) as session:
            rows = session.exec(select(ProjectTable)).all()
            return [
                ProjectResponse(
                    project_id=r.project_id, name=r.name, description=r.description
                )
                for r in rows
            ]

    @post("/projects/{project_id}/members")
    async def add_project_member(
        self, project_id: str, body: AddMemberRequest
    ) -> dict[str, str]:
        """Add a user to a project with a role."""
        engine = self._postgres_handler.get_engine()
        with Session(engine) as session:
            project = session.get(ProjectTable, project_id)
            if project is None:
                raise HTTPException(status_code=404, detail="project not found")
            user = session.get(UserTable, body.user_id)
            role = session.get(RoleTable, body.role_id)
            if user is None or role is None:
                raise HTTPException(status_code=404, detail="user or role not found")
            session.add(
                ProjectMembershipTable(
                    user_id=body.user_id,
                    project_id=project_id,
                    role_id=body.role_id,
                )
            )
            session.commit()
            return {"status": "ok"}

    @delete("/projects/{project_id}/members/{user_id}")
    async def remove_project_member(
        self, project_id: str, user_id: str
    ) -> dict[str, str]:
        """Remove all memberships for a user from a project."""
        engine = self._postgres_handler.get_engine()
        with Session(engine) as session:
            stmt = select(ProjectMembershipTable).where(
                ProjectMembershipTable.project_id == project_id,
                ProjectMembershipTable.user_id == user_id,
            )
            rows = list(session.exec(stmt).all())
            for r in rows:
                session.delete(r)
            session.commit()
            return {"removed": str(len(rows))}

    # ------------------------------------------------------------------
    # /roles
    # ------------------------------------------------------------------

    @post("/roles")
    async def create_role(self, body: CreateRoleRequest) -> RoleResponse:
        """Create a new role with permissions."""
        engine = self._postgres_handler.get_engine()
        with Session(engine) as session:
            existing = session.exec(
                select(RoleTable).where(RoleTable.name == body.name)
            ).first()
            if existing is not None:
                raise HTTPException(status_code=409, detail="role name already exists")
            role = RoleTable(name=body.name, description=body.description)
            session.add(role)
            session.flush()
            for perm in body.permissions:
                session.add(RolePermissionTable(role_id=role.role_id, permission=perm))
            session.commit()
            session.refresh(role)
            return RoleResponse(
                role_id=role.role_id,
                name=role.name,
                description=role.description,
                permissions=list(body.permissions),
            )

    @get("/roles")
    async def list_roles(self) -> list[RoleResponse]:
        """List all roles, including their permission strings."""
        engine = self._postgres_handler.get_engine()
        with Session(engine) as session:
            roles = list(session.exec(select(RoleTable)).all())
            results: list[RoleResponse] = []
            for role in roles:
                perms = session.exec(
                    select(RolePermissionTable).where(
                        RolePermissionTable.role_id == role.role_id
                    )
                ).all()
                results.append(
                    RoleResponse(
                        role_id=role.role_id,
                        name=role.name,
                        description=role.description,
                        permissions=[p.permission for p in perms],
                    )
                )
            return results

    @post("/roles/grant")
    async def grant_role(self, body: GrantRoleRequest) -> dict[str, str]:
        """Grant a role to a user (optionally project-scoped), service account, or node."""
        engine = self._postgres_handler.get_engine()
        with Session(engine) as session:
            role = session.get(RoleTable, body.role_id)
            if role is None:
                raise HTTPException(status_code=404, detail="role not found")
            if body.user_id and body.project_id:
                session.add(
                    ProjectMembershipTable(
                        user_id=body.user_id,
                        project_id=body.project_id,
                        role_id=body.role_id,
                    )
                )
            else:
                session.add(
                    GlobalRoleGrantTable(
                        role_id=body.role_id,
                        user_id=body.user_id,
                        service_account_client_id=body.service_account_client_id,
                        node_identity_client_id=body.node_identity_client_id,
                    )
                )
            session.commit()
            self._audit.log(
                AuditEvent.ROLE_GRANT,
                principal_id=body.user_id
                or body.service_account_client_id
                or body.node_identity_client_id,
                details=body.model_dump(exclude_none=True),
            )
            return {"status": "ok"}

    # ------------------------------------------------------------------
    # /service-accounts and /node-identities
    # ------------------------------------------------------------------

    @post("/service-accounts")
    async def register_service_account(
        self, body: RegisterServiceAccountRequest
    ) -> CredentialResponse:
        """Create a service-account principal and return its plaintext secret once."""
        engine = self._postgres_handler.get_engine()
        client_id = f"sa-{new_ulid_str()}"
        client_secret = secrets.token_urlsafe(32)
        with Session(engine) as session:
            session.add(
                ServiceAccountTable(
                    client_id=client_id,
                    client_secret_hash=self._password_service.hash_password(
                        client_secret
                    ),
                    manager_id=body.manager_id,
                )
            )
            for role_id in body.role_ids:
                session.add(
                    GlobalRoleGrantTable(
                        role_id=role_id, service_account_client_id=client_id
                    )
                )
            session.commit()
        self._audit.log(
            AuditEvent.SERVICE_ACCOUNT_REGISTER,
            principal_id=client_id,
            principal_type="service_account",
            details={"manager_id": body.manager_id},
        )
        return CredentialResponse(client_id=client_id, client_secret=client_secret)

    @post("/node-identities")
    async def register_node_identity(
        self, body: RegisterNodeRequest
    ) -> CredentialResponse:
        """Create a node-identity principal and return its plaintext secret once."""
        engine = self._postgres_handler.get_engine()
        client_id = f"node-{new_ulid_str()}"
        client_secret = secrets.token_urlsafe(32)
        with Session(engine) as session:
            session.add(
                NodeIdentityTable(
                    client_id=client_id,
                    client_secret_hash=self._password_service.hash_password(
                        client_secret
                    ),
                    node_id=body.node_id,
                    workcell_id=body.workcell_id,
                )
            )
            for role_id in body.role_ids:
                session.add(
                    GlobalRoleGrantTable(
                        role_id=role_id, node_identity_client_id=client_id
                    )
                )
            session.commit()
        self._audit.log(
            AuditEvent.NODE_REGISTER,
            principal_id=client_id,
            principal_type="node",
            details={
                "node_id": body.node_id,
                "workcell_id": body.workcell_id,
            },
        )
        return CredentialResponse(client_id=client_id, client_secret=client_secret)

    @post("/credentials/{client_id}/rotate")
    async def rotate_credentials(self, client_id: str) -> CredentialResponse:
        """Rotate the client_secret for a service-account or node-identity."""
        engine = self._postgres_handler.get_engine()
        new_secret = secrets.token_urlsafe(32)
        new_hash = self._password_service.hash_password(new_secret)
        with Session(engine) as session:
            sa = session.get(ServiceAccountTable, client_id)
            node = session.get(NodeIdentityTable, client_id) if sa is None else None
            target = sa or node
            if target is None:
                raise HTTPException(status_code=404, detail="client_id not found")
            target.client_secret_hash = new_hash
            session.add(target)
            session.commit()
        event = (
            AuditEvent.SERVICE_ACCOUNT_ROTATE
            if isinstance(target, ServiceAccountTable)
            else AuditEvent.NODE_ROTATE
        )
        self._audit.log(event, principal_id=client_id)
        return CredentialResponse(client_id=client_id, client_secret=new_secret)

    # ------------------------------------------------------------------
    # /keys
    # ------------------------------------------------------------------

    @post("/keys/rotate")
    async def rotate_keys(self) -> KeyInfo:
        """Generate a new signing keypair, demoting the previous one to verify-only."""
        new_row = self._signing_key_service.rotate()
        self._audit.log(AuditEvent.KEY_ROTATE, details={"kid": new_row.kid})
        return KeyInfo(
            kid=new_row.kid,
            algorithm=new_row.algorithm,
            active=new_row.active,
            active_for_signing=new_row.active_for_signing,
            created_at=new_row.created_at.isoformat() if new_row.created_at else None,
        )

    @get("/keys")
    async def list_keys(self) -> list[KeyInfo]:
        """List all signing keys (active, retired, signing flag)."""
        return [
            KeyInfo(
                kid=k.kid,
                algorithm=k.algorithm,
                active=k.active,
                active_for_signing=k.active_for_signing,
                created_at=k.created_at.isoformat() if k.created_at else None,
                retired_at=k.retired_at.isoformat() if k.retired_at else None,
            )
            for k in self._signing_key_service.list_all_keys()
        ]

    @delete("/keys/{kid}")
    async def retire_key(self, kid: str) -> dict[str, bool]:
        """Retire a signing key (remove from JWKS, delete private material)."""
        ok = self._signing_key_service.retire(kid)
        if ok:
            self._audit.log(AuditEvent.KEY_RETIRE, details={"kid": kid})
        return {"retired": ok}

    @get("/health/keys")
    async def keys_health(self) -> KeysHealthResponse:
        """Report active key count, oldest-key age, and current signing kid."""
        keys = self._signing_key_service.list_active_keys()
        signing = self._signing_key_service.get_signing_key()
        oldest_age: Optional[int] = None
        if keys:
            now = datetime.now(timezone.utc)
            ages = []
            for k in keys:
                created = k.created_at
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                ages.append(int((now - created).total_seconds()))
            oldest_age = max(ages)
        return KeysHealthResponse(
            active_keys=len(keys),
            oldest_key_age_seconds=oldest_age,
            signing_kid=signing.kid if signing else None,
        )

    # ------------------------------------------------------------------
    # /deny-list
    # ------------------------------------------------------------------

    @get("/deny-list")
    async def deny_list_endpoint(
        self, request: Request, response: Response
    ) -> DenyListResponse:
        """Return the persistent jti deny-list, with ETag conditional-fetch support."""
        snapshot = self._deny_list_service.snapshot()
        etag = f'"{snapshot["etag"]}"'
        if request.headers.get("if-none-match") == etag:
            response.status_code = 304
            return Response(status_code=304)  # type: ignore[return-value]
        response.headers["ETag"] = etag
        return DenyListResponse(etag=snapshot["etag"], entries=snapshot["entries"])

    # ------------------------------------------------------------------
    # Server lifecycle
    # ------------------------------------------------------------------

    def create_server(self, **kwargs: Any) -> fastapi.FastAPI:
        """Build the FastAPI application with all Auth Manager endpoints registered."""
        return super().create_server(**kwargs)


# Main entry point for running the server
if __name__ == "__main__":
    manager = AuthManager()
    manager.run_server()

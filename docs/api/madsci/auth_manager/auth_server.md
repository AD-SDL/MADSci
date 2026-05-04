Module madsci.auth_manager.auth_server
======================================
MADSci Auth Manager FastAPI server.

Implements the OAuth 2.0 token, introspection, revocation, and JWKS
endpoints, plus the admin surface for users, projects, roles,
service-accounts, node identities, signing keys, and the deny-list.

Per Decision 12, this manager is single-tenant: all data is implicitly
scoped to the deployment's ``lab_id``.

Classes
-------

`AuthManager(settings: Optional[AuthManagerSettings] = None, postgres_handler: Optional[PostgresHandler] = None, **kwargs: Any)`
:   MADSci Auth Manager REST server.
    
    Initialize the Auth Manager, optionally injecting a database handler.

    ### Ancestors (in MRO)

    * madsci.common.manager_base.AbstractManagerBase
    * madsci.client.client_mixin.MadsciClientMixin
    * typing.Generic
    * classy_fastapi.routable.Routable

    ### Class variables

    `SETTINGS_CLASS: type[madsci.common.types.base_types.MadsciBaseSettings] | None`
    :   Settings for the Auth Manager.

    ### Methods

    `add_project_member(self, project_id: str, body: AddMemberRequest) ‑> dict[str, str]`
    :   Add a user to a project with a role.

    `bootstrap(self, *, admin_username: str, admin_password: str, admin_email: Optional[str] = None) ‑> madsci.auth_manager.server_types.BootstrapResponse`
    :   Idempotent bootstrap: create admin user, signing key, built-in roles.

    `create_project(self, body: CreateProjectRequest) ‑> madsci.auth_manager.server_types.ProjectResponse`
    :   Create a new project.

    `create_role(self, body: CreateRoleRequest) ‑> madsci.auth_manager.server_types.RoleResponse`
    :   Create a new role with permissions.

    `create_server(self, **kwargs: Any) ‑> fastapi.applications.FastAPI`
    :   Build the FastAPI application with all Auth Manager endpoints registered.

    `create_user(self, body: CreateUserRequest) ‑> madsci.auth_manager.server_types.UserResponse`
    :   Create a new user account.

    `deny_list_endpoint(self, request: Request, response: Response) ‑> madsci.auth_manager.server_types.DenyListResponse`
    :   Return the persistent jti deny-list, with ETag conditional-fetch support.

    `get_user(self, user_id: str) ‑> madsci.auth_manager.server_types.UserResponse`
    :   Fetch a single user by id.

    `grant_role(self, body: GrantRoleRequest) ‑> dict[str, str]`
    :   Grant a role to a user (optionally project-scoped), service account, or node.

    `initialize(self, **kwargs: Any) ‑> None`
    :   Initialize handlers, schema, and service objects.

    `introspect_endpoint(self, body: IntrospectRequest) ‑> dict[str, typing.Any]`
    :   OAuth 2.0 Token Introspection (RFC 7662).

    `jwks_endpoint(self) ‑> dict[str, typing.Any]`
    :   Public JWKS document — no authentication required.

    `keys_health(self) ‑> madsci.auth_manager.server_types.KeysHealthResponse`
    :   Report active key count, oldest-key age, and current signing kid.

    `list_keys(self) ‑> list[madsci.auth_manager.server_types.KeyInfo]`
    :   List all signing keys (active, retired, signing flag).

    `list_projects(self) ‑> list[madsci.auth_manager.server_types.ProjectResponse]`
    :   List all projects.

    `list_roles(self) ‑> list[madsci.auth_manager.server_types.RoleResponse]`
    :   List all roles, including their permission strings.

    `list_users(self) ‑> list[madsci.auth_manager.server_types.UserResponse]`
    :   List all user accounts.

    `register_node_identity(self, body: RegisterNodeRequest) ‑> madsci.auth_manager.server_types.CredentialResponse`
    :   Create a node-identity principal and return its plaintext secret once.

    `register_service_account(self, body: RegisterServiceAccountRequest) ‑> madsci.auth_manager.server_types.CredentialResponse`
    :   Create a service-account principal and return its plaintext secret once.

    `remove_project_member(self, project_id: str, user_id: str) ‑> dict[str, str]`
    :   Remove all memberships for a user from a project.

    `retire_key(self, kid: str) ‑> dict[str, bool]`
    :   Retire a signing key (remove from JWKS, delete private material).

    `revoke_endpoint(self, body: RevokeRequest) ‑> dict[str, bool]`
    :   Revoke an access token and/or refresh token.

    `rotate_credentials(self, client_id: str) ‑> madsci.auth_manager.server_types.CredentialResponse`
    :   Rotate the client_secret for a service-account or node-identity.

    `rotate_keys(self) ‑> madsci.auth_manager.server_types.KeyInfo`
    :   Generate a new signing keypair, demoting the previous one to verify-only.

    `token_endpoint(self, request: Request, grant_type: str = Form(PydanticUndefined), username: Optional[str] = Form(None), password: Optional[str] = Form(None), refresh_token: Optional[str] = Form(None), client_id: Optional[str] = Form(None), client_secret: Optional[str] = Form(None)) ‑> madsci.common.types.auth_types.TokenResponse`
    :   OAuth 2.0 token endpoint (password, refresh_token, client_credentials).

    `update_user(self, user_id: str, body: UpdateUserRequest) ‑> madsci.auth_manager.server_types.UserResponse`
    :   Patch user fields (deactivate, change password, update email).
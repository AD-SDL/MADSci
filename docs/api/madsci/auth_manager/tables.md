Module madsci.auth_manager.tables
=================================
SQLModel tables for the Auth Manager.

All entities are scoped to a single ``lab_id`` (Decision 12). The schema is
single-tenant and intentionally has no ``tenant_id`` column.

Tables:

- ``users`` — local user accounts with Argon2id password hashes
- ``projects`` — project records
- ``project_memberships`` — many-to-many user ↔ project ↔ role
- ``roles`` — named bundles of permissions
- ``role_permissions`` — many-to-many role ↔ permission string
- ``service_accounts`` — manager principals
- ``node_identities`` — node principals (with reserved ``mtls_cert_fingerprint``)
- ``refresh_tokens`` — opaque refresh tokens, server-stored
- ``revoked_access_tokens`` — persistent deny-list (jti, exp, revoked_at)
- ``signing_keys`` — RSA keypairs for JWT signing
- ``audit_log`` — append-only security event log

The ``mtls_cert_fingerprint`` column on ``node_identities`` is forward-compat
with the future mTLS follow-on; it is not validated or used by this change.

Classes
-------

`AuditLogTable(**data)`
:   Append-only audit log.

    ### Ancestors (in MRO)

    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    ### Instance variables

    `details: dict | None`
    :

    `event_id: str`
    :

    `event_time: datetime.datetime`
    :

    `event_type: str`
    :

    `grant_type: str | None`
    :

    `id: int | None`
    :

    `principal_id: str | None`
    :

    `principal_type: str | None`
    :

    `source_ip: str | None`
    :

    `success: bool`
    :

    `token_jti: str | None`
    :

`GlobalRoleGrantTable(**data)`
:   Global (non-project-scoped) role grants for users / service accounts / nodes.
    
    A row applies to exactly one principal. The unused id columns are NULL.

    ### Ancestors (in MRO)

    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    ### Instance variables

    `created_at: datetime.datetime`
    :

    `id: int | None`
    :

    `node_identity_client_id: str | None`
    :

    `role_id: str`
    :

    `service_account_client_id: str | None`
    :

    `user_id: str | None`
    :

`LabBindingTable(**data)`
:   Records the lab_id this Auth Manager database is bound to.
    
    Per Decision 12, an Auth Manager refuses to start later against a
    different lab_id without an explicit operator-acknowledged migration.

    ### Ancestors (in MRO)

    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    ### Instance variables

    `bootstrapped_at: datetime.datetime`
    :

    `id: int`
    :

    `lab_id: str`
    :

`NodeIdentityTable(**data)`
:   Node principal.

    ### Ancestors (in MRO)

    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    ### Instance variables

    `client_id: str`
    :

    `client_secret_hash: str`
    :

    `created_at: datetime.datetime`
    :

    `is_active: bool`
    :

    `mtls_cert_fingerprint: str | None`
    :

    `node_id: str`
    :

    `workcell_id: str | None`
    :

`ProjectMembershipTable(**data)`
:   A user's role grant within a project.

    ### Ancestors (in MRO)

    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    ### Instance variables

    `created_at: datetime.datetime`
    :

    `id: int | None`
    :

    `project_id: str`
    :

    `role_id: str`
    :

    `user_id: str`
    :

`ProjectTable(**data)`
:   Project record.

    ### Ancestors (in MRO)

    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    ### Instance variables

    `created_at: datetime.datetime`
    :

    `description: str | None`
    :

    `name: str`
    :

    `project_id: str`
    :

`RefreshTokenTable(**data)`
:   Opaque refresh token, server-stored.

    ### Ancestors (in MRO)

    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    ### Instance variables

    `expires_at: datetime.datetime`
    :

    `issued_at: datetime.datetime`
    :

    `principal_sub: str`
    :

    `principal_type: str`
    :

    `revoked_at: datetime.datetime | None`
    :

    `rotated_to: str | None`
    :

    `token_hash: str`
    :

    `token_id: str`
    :

`RevokedAccessTokenTable(**data)`
:   Persistent deny-list of revoked access-token jtis.

    ### Ancestors (in MRO)

    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    ### Instance variables

    `exp: datetime.datetime`
    :

    `jti: str`
    :

    `revoked_at: datetime.datetime`
    :

`RolePermissionTable(**data)`
:   Many-to-many between roles and permission strings.
    
    Permissions are stored as plain strings (``<resource>.<action>``) drawn
    from the canonical namespace documented in ``docs/guides/auth.md``.

    ### Ancestors (in MRO)

    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    ### Instance variables

    `id: int | None`
    :

    `permission: str`
    :

    `role_id: str`
    :

`RoleTable(**data)`
:   Role record (a named bundle of permissions).

    ### Ancestors (in MRO)

    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    ### Instance variables

    `created_at: datetime.datetime`
    :

    `description: str | None`
    :

    `name: str`
    :

    `role_id: str`
    :

`ServiceAccountTable(**data)`
:   Service account principal (a manager service).

    ### Ancestors (in MRO)

    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    ### Instance variables

    `client_id: str`
    :

    `client_secret_hash: str`
    :

    `created_at: datetime.datetime`
    :

    `is_active: bool`
    :

    `manager_id: str`
    :

`SigningKeyTable(**data)`
:   RSA signing keypair for JWT issuance.

    ### Ancestors (in MRO)

    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    ### Instance variables

    `active: bool`
    :

    `active_for_signing: bool`
    :

    `algorithm: str`
    :

    `created_at: datetime.datetime`
    :

    `kid: str`
    :

    `private_key_pem: str`
    :

    `public_key_pem: str`
    :

    `retired_at: datetime.datetime | None`
    :

`UserTable(**data)`
:   Local user account.

    ### Ancestors (in MRO)

    * sqlmodel.main.SQLModel
    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    ### Instance variables

    `created_at: datetime.datetime`
    :

    `email: str | None`
    :

    `is_active: bool`
    :

    `password_hash: str`
    :

    `updated_at: datetime.datetime`
    :

    `user_id: str`
    :

    `username: str`
    :
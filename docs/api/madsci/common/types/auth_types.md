Module madsci.common.types.auth_types
=====================================
Types related to authentication, authorization, and ownership of MADSci objects.

Classes
-------

`AuthManagerSettings(**kwargs: Any)`
:   Settings for the Auth Manager.
    
    Initialize settings with walk-up file discovery.
    
    Configuration file paths (YAML, JSON, TOML, .env) are resolved via
    walk-up discovery from a starting directory. Each filename walks up
    independently, so ``node.settings.yaml`` can resolve in the node dir
    while ``settings.yaml`` resolves in the lab root.
    
    The starting directory is determined by (in priority order):
    1. ``_settings_dir`` keyword argument
    2. ``MADSCI_SETTINGS_DIR`` environment variable
    3. Current working directory (default)
    
    Args:
        _settings_dir: Starting directory for walk-up file discovery.
        **kwargs: Forwarded to ``BaseSettings.__init__``.

    ### Ancestors (in MRO)

    * madsci.common.types.manager_types.ManagerSettings
    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Class variables

    `access_token_ttl: int`
    :

    `argon2_memory_cost: int`
    :

    `argon2_parallelism: int`
    :

    `argon2_time_cost: int`
    :

    `database_url: str`
    :

    `deny_list_persist_grace: int`
    :

    `lab_id: str | None`
    :

    `local_audit_log_max_bytes: int`
    :

    `local_audit_log_path: str | None`
    :

    `manager_type: madsci.common.types.manager_types.ManagerType | None`
    :

    `refresh_token_ttl: int`
    :

    `server_url: pydantic.networks.AnyUrl`
    :

    `signing_key_ttl: int`
    :

`GrantType(value, names=None, *, module=None, qualname=None, type=None, start=1)`
:   OAuth 2.0 grant types supported by the Auth Manager.

    ### Ancestors (in MRO)

    * builtins.str
    * enum.Enum

    ### Class variables

    `CLIENT_CREDENTIALS`
    :

    `PASSWORD`
    :

    `REFRESH_TOKEN`
    :

`JWTClaims(**data: Any)`
:   The decoded claims of a MADSci access token.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `aud: str`
    :

    `exp: int`
    :

    `iat: int`
    :

    `iss: str`
    :

    `jti: str`
    :

    `manager_id: str | None`
    :

    `model_config`
    :

    `node_id: str | None`
    :

    `permissions: list[str]`
    :

    `principal_type: madsci.common.types.auth_types.PrincipalType`
    :

    `project_ids: list[str]`
    :

    `roles: list[str]`
    :

    `sub: str`
    :

    `user_id: str | None`
    :

    `workcell_id: str | None`
    :

`NodeIdentity(**data: Any)`
:   A principal representing a laboratory node.
    
    ``client_secret`` is never stored or returned in plaintext after the
    initial registration; only the Argon2 hash is persisted.
    
    The ``mtls_cert_fingerprint`` field is reserved for the future mTLS
    follow-on change.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `client_id: str`
    :

    `created_at: datetime.datetime | None`
    :

    `is_active: bool`
    :

    `model_config`
    :

    `mtls_cert_fingerprint: str | None`
    :

    `node_id: str`
    :

    `role_ids: list[str]`
    :

    `workcell_id: str | None`
    :

    ### Methods

    `is_ulid_node(id: str, info: pydantic_core.core_schema.ValidationInfo) ‑> str`
    :   Validates that a string field is a valid ULID.

    `is_ulid_workcell(id: str | None, info: pydantic_core.core_schema.ValidationInfo) ‑> str`
    :   Validates that a string field is a valid ULID.

`OwnershipInfo(**data: Any)`
:   Information about the ownership of a MADSci object.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `campaign_id: str | None`
    :

    `experiment_id: str | None`
    :

    `lab_id: str | None`
    :

    `manager_id: str | None`
    :

    `model_config`
    :

    `node_id: str | None`
    :

    `project_id: str | None`
    :

    `step_id: str | None`
    :

    `user_id: str | None`
    :

    `workcell_id: str | None`
    :

    `workflow_id: str | None`
    :

    ### Static methods

    `from_jwt_claims(claims: JWTClaims) ‑> madsci.common.types.auth_types.OwnershipInfo`
    :   Build an OwnershipInfo from validated JWT claims.
        
        - ``lab_id``      ← ``claims.aud``
        - ``user_id``     ← ``claims.user_id`` (when ``principal_type=user``)
        - ``node_id``     ← ``claims.node_id`` (when ``principal_type=node``)
        - ``workcell_id`` ← ``claims.workcell_id``
        - ``manager_id``  ← ``claims.manager_id`` (when ``principal_type=service_account``)
        
        ``project_id`` is intentionally left unset; project context is
        established per-operation via ``@requires(project_from=...)``.

    ### Methods

    `check(self, other: OwnershipInfo) ‑> bool`
    :   Check if this ownership is the same as another.

    `exclude_unset_by_default(self, nxt: pydantic_core.core_schema.SerializerFunctionWrapHandler, info: pydantic_core.core_schema.SerializationInfo) ‑> dict[str, typing.Any]`
    :   Exclude unset fields by default.

    `is_ulid(id: str | None, info: pydantic_core.core_schema.ValidationInfo) ‑> str`
    :   Validates that a string field is a valid ULID.

`Permission(**data: Any)`
:   A permission string in the canonical ``<resource>.<action>`` namespace.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `description: str | None`
    :

    `model_config`
    :

    `name: str`
    :

`Principal(**data: Any)`
:   The validated principal of an authenticated request.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `claims: madsci.common.types.auth_types.JWTClaims`
    :

    `model_config`
    :

    `permissions: list[str]`
    :

    `principal_type: madsci.common.types.auth_types.PrincipalType`
    :

    `project_ids: list[str]`
    :

    `roles: list[str]`
    :

    `sub: str`
    :

    ### Static methods

    `from_claims(claims: madsci.common.types.auth_types.JWTClaims) ‑> madsci.common.types.auth_types.Principal`
    :   Build a Principal from validated JWT claims.

`PrincipalType(value, names=None, *, module=None, qualname=None, type=None, start=1)`
:   Type of principal a token represents.

    ### Ancestors (in MRO)

    * builtins.str
    * enum.Enum

    ### Class variables

    `NODE`
    :

    `SERVICE_ACCOUNT`
    :

    `USER`
    :

`ProjectInfo(**data: Any)`
:   Information about a project.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    `project_description: str`
    :

    `project_id: str`
    :

    `project_members: list[madsci.common.types.auth_types.UserInfo]`
    :

    `project_name: str`
    :

    `project_owner: madsci.common.types.auth_types.UserInfo`
    :

    ### Methods

    `is_ulid(id: str, info: pydantic_core.core_schema.ValidationInfo) ‑> str`
    :   Validates that a string field is a valid ULID.

`ProjectMembership(**data: Any)`
:   A user's membership in a project, with one or more roles scoped to it.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    `project_id: str`
    :

    `role_ids: list[str]`
    :

    `user_id: str`
    :

    ### Methods

    `is_ulid_project(id: str, info: pydantic_core.core_schema.ValidationInfo) ‑> str`
    :   Validates that a string field is a valid ULID.

    `is_ulid_user(id: str, info: pydantic_core.core_schema.ValidationInfo) ‑> str`
    :   Validates that a string field is a valid ULID.

`Role(**data: Any)`
:   A named bundle of permissions that can be granted to principals.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `description: str | None`
    :

    `model_config`
    :

    `name: str`
    :

    `permissions: list[str]`
    :

    `role_id: str`
    :

    ### Methods

    `is_ulid(id: str, info: pydantic_core.core_schema.ValidationInfo) ‑> str`
    :   Validates that a string field is a valid ULID.

`ServiceAccount(**data: Any)`
:   A non-human principal representing a manager service.
    
    ``client_secret`` is never stored or returned in plaintext after the
    initial registration; only the Argon2 hash is persisted.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `client_id: str`
    :

    `created_at: datetime.datetime | None`
    :

    `is_active: bool`
    :

    `manager_id: str`
    :

    `model_config`
    :

    `role_ids: list[str]`
    :

    ### Methods

    `is_ulid_manager(id: str, info: pydantic_core.core_schema.ValidationInfo) ‑> str`
    :   Validates that a string field is a valid ULID.

`TokenResponse(**data: Any)`
:   The OAuth 2.0 token-endpoint response.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `access_token: str`
    :

    `expires_in: int`
    :

    `model_config`
    :

    `refresh_token: str | None`
    :

    `scope: str | None`
    :

    `token_type: str`
    :

`UserInfo(**data: Any)`
:   Information about a user.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    `user_email: str`
    :

    `user_id: str`
    :

    `user_name: str`
    :

    ### Methods

    `is_ulid(id: str, info: pydantic_core.core_schema.ValidationInfo) ‑> str`
    :   Validates that a string field is a valid ULID.
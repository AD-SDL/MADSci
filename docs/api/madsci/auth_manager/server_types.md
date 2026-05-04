Module madsci.auth_manager.server_types
=======================================
Pydantic request/response models specific to the Auth Manager server.

Classes
-------

`AddMemberRequest(**data: Any)`
:   Request body for ``POST /projects/{id}/members``.
    
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

    `role_id: str`
    :

    `user_id: str`
    :

`BootstrapResponse(**data: Any)`
:   Response body for the bootstrap CLI / API call.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `admin_role_id: str`
    :

    `model_config`
    :

    `note: str`
    :

    `signing_kid: str`
    :

    `user_id: str`
    :

    `username: str`
    :

`CreateProjectRequest(**data: Any)`
:   Request body for ``POST /projects``.
    
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

`CreateRoleRequest(**data: Any)`
:   Request body for ``POST /roles``.
    
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

`CreateUserRequest(**data: Any)`
:   Request body for ``POST /users``.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `email: str | None`
    :

    `model_config`
    :

    `password: str`
    :

    `username: str`
    :

`CredentialResponse(**data: Any)`
:   Response that returns a freshly-issued client_id + plaintext secret.
    
    The plaintext secret is returned exactly once; only its Argon2 hash is
    stored. Callers are responsible for distributing the secret out-of-band.
    
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

    `client_secret: str`
    :

    `model_config`
    :

    `note: str`
    :

`DenyListEntry(**data: Any)`
:   A single entry in the deny-list (jti + its access-token expiration).
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `exp: int`
    :

    `jti: str`
    :

    `model_config`
    :

`DenyListResponse(**data: Any)`
:   Response body for ``GET /deny-list``.
    
    Consumers SHOULD send ``If-None-Match: "<etag>"`` on subsequent polls
    to receive HTTP 304 when the list is unchanged.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `entries: list[madsci.auth_manager.server_types.DenyListEntry]`
    :

    `etag: str`
    :

    `model_config`
    :

`GrantRoleRequest(**data: Any)`
:   Request body for ``POST /roles/grant``.
    
    Exactly one of ``user_id`` (with or without ``project_id``),
    ``service_account_client_id``, or ``node_identity_client_id`` should be
    supplied to identify the grant target.
    
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

    `node_identity_client_id: str | None`
    :

    `project_id: str | None`
    :

    `role_id: str`
    :

    `service_account_client_id: str | None`
    :

    `user_id: str | None`
    :

`IntrospectRequest(**data: Any)`
:   Request body for ``POST /introspect`` (RFC 7662).
    
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

    `token: str`
    :

`KeyInfo(**data: Any)`
:   Public summary of a signing key (``private_key_pem`` is never returned).
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `active: bool`
    :

    `active_for_signing: bool`
    :

    `algorithm: str`
    :

    `created_at: str | None`
    :

    `kid: str`
    :

    `model_config`
    :

    `retired_at: str | None`
    :

`KeysHealthResponse(**data: Any)`
:   Response body for ``GET /health/keys``.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `active_keys: int`
    :

    `model_config`
    :

    `oldest_key_age_seconds: int | None`
    :

    `signing_kid: str | None`
    :

`ProjectResponse(**data: Any)`
:   Project-resource response.
    
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

    `project_id: str`
    :

`RegisterNodeRequest(**data: Any)`
:   Request body for ``POST /node-identities``.
    
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

    `node_id: str`
    :

    `role_ids: list[str]`
    :

    `workcell_id: str | None`
    :

`RegisterServiceAccountRequest(**data: Any)`
:   Request body for ``POST /service-accounts``.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `manager_id: str`
    :

    `model_config`
    :

    `role_ids: list[str]`
    :

`RevokeRequest(**data: Any)`
:   Request body for ``POST /revoke``.
    
    Either ``token`` (an access-token JWT) or ``refresh_token`` may be set;
    callers usually send both during logout.
    
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

    `refresh_token: str | None`
    :

    `token: str | None`
    :

`RoleResponse(**data: Any)`
:   Role-resource response, including its flattened permission strings.
    
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

`TokenErrorResponse(**data: Any)`
:   OAuth 2.0 token-endpoint error body (RFC 6749 §5.2).
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `error: str`
    :

    `error_description: str | None`
    :

    `model_config`
    :

`UpdateUserRequest(**data: Any)`
:   Partial-update body for ``PATCH /users/{id}``.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `email: str | None`
    :

    `is_active: bool | None`
    :

    `model_config`
    :

    `new_password: str | None`
    :

`UserResponse(**data: Any)`
:   User-resource response (``password_hash`` is never returned).
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `email: str | None`
    :

    `is_active: bool`
    :

    `model_config`
    :

    `user_id: str`
    :

    `username: str`
    :
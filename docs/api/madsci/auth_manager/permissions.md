Module madsci.auth_manager.permissions
======================================
Canonical permission strings used by the Auth Manager itself.

Every administrative endpoint on the Auth Manager carries a
``@requires(permission=...)`` decorator naming one of the strings below.
Operators grant these via the built-in ``admin`` role (which holds the ``*``
wildcard), or via a custom role for narrower delegation (e.g., a separate
``key-rotator`` role for an automated key-rotation job).

Classes
-------

`AuthPermissions()`
:   Auth Manager admin-endpoint permission strings.

    ### Class variables

    `CREDENTIALS_ROTATE`
    :

    `KEY_READ`
    :

    `KEY_RETIRE`
    :

    `KEY_ROTATE`
    :

    `PRINCIPAL_WRITE`
    :

    `PROJECT_READ`
    :

    `PROJECT_WRITE`
    :

    `ROLE_GRANT`
    :

    `ROLE_READ`
    :

    `ROLE_WRITE`
    :

    `TOKEN_INTROSPECT`
    :

    `TOKEN_REVOKE`
    :

    `USER_READ`
    :

    `USER_WRITE`
    :
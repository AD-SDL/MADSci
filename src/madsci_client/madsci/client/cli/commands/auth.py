"""MADSci CLI ``auth`` command group.

Subcommands target the Auth Manager via ``AuthClient``. The bootstrap
command runs locally against an Auth Manager instance (operator must already
have access to the database / process); all other commands talk to a running
Auth Manager over HTTP.
"""

from __future__ import annotations

import getpass
import json
import os
import sys
from typing import TYPE_CHECKING, Optional

import click

BOOTSTRAP_PASSWORD_ENV_VAR = "MADSCI_AUTH_BOOTSTRAP_PASSWORD"  # noqa: S105


def _auth_url(ctx: click.Context, auth_url: Optional[str]) -> str:
    if auth_url:
        return auth_url
    # Try MadsciContext if present
    context = ctx.obj.get("context") if ctx.obj else None
    if context is not None:
        # Auth URL isn't yet a first-class field on MadsciContext; fall back to default.
        pass
    return "http://localhost:8007/"


if TYPE_CHECKING:
    from madsci.client.auth_client import AuthClient


def _client(auth_url: str) -> AuthClient:
    from madsci.client.auth_client import AuthClient

    return AuthClient(auth_server_url=auth_url)


def _print(value: object) -> None:
    if isinstance(value, (dict, list)):
        click.echo(json.dumps(value, indent=2, sort_keys=True))
    else:
        click.echo(str(value))


@click.group()
@click.option(
    "--auth-url",
    envvar="AUTH_SERVER_URL",
    default=None,
    help="Auth Manager URL (default: http://localhost:8007/).",
)
@click.pass_context
def auth(ctx: click.Context, auth_url: Optional[str]) -> None:
    """Auth Manager commands (users, projects, roles, keys, credentials)."""
    ctx.ensure_object(dict)
    ctx.obj["auth_url"] = _auth_url(ctx, auth_url)


# ---------------------------------------------------------------------------
# bootstrap (in-process)
# ---------------------------------------------------------------------------


def _resolve_bootstrap_password(username: str) -> str:
    """Source the admin password from env var, then interactive prompt.

    Refuses to fall back to argv-passed passwords: those leak via ``ps``.
    Refuses to silently accept an empty password.
    """
    env_value = os.environ.get(BOOTSTRAP_PASSWORD_ENV_VAR)
    if env_value:
        return env_value
    if not sys.stdin.isatty():
        raise click.ClickException(
            f"No password available. Set ${BOOTSTRAP_PASSWORD_ENV_VAR} or run"
            " interactively (TTY required for the password prompt)."
        )
    pw = click.prompt(
        f"Password for {username}",
        hide_input=True,
        confirmation_prompt=True,
    )
    if not pw:
        raise click.ClickException("Password may not be empty.")
    return pw


@auth.command()
@click.option("--username", default="admin", show_default=True)
@click.option("--email", default=None)
@click.option(
    "--lab-id",
    default=None,
    envvar="AUTH_LAB_ID",
    help="lab_id to bind the Auth Manager to (Decision 12).",
)
@click.option(
    "--database-url",
    default=None,
    envvar="AUTH_DATABASE_URL",
    help="Override AUTH_DATABASE_URL for this run (e.g. sqlite:///./test.db).",
)
def bootstrap(
    username: str,
    email: Optional[str],
    lab_id: Optional[str],
    database_url: Optional[str],
) -> None:
    """Initialize an empty Auth Manager database (idempotent).

    Creates the admin user, generates the first signing keypair, and seeds
    the built-in roles. Safe to re-run against a populated database.

    The admin password MUST be supplied via the
    ``MADSCI_AUTH_BOOTSTRAP_PASSWORD`` environment variable or via the
    interactive prompt. Passing the password on the command line is no longer
    supported (it would leak via ``ps``/process listings).
    """
    from madsci.auth_manager.auth_server import AuthManager
    from madsci.common.types.auth_types import AuthManagerSettings

    password = _resolve_bootstrap_password(username)

    overrides: dict = {"enable_registry_resolution": False}
    if lab_id:
        overrides["lab_id"] = lab_id
    if database_url:
        overrides["database_url"] = database_url

    settings = AuthManagerSettings(**overrides)
    mgr = AuthManager(settings=settings)
    result = mgr.bootstrap(
        admin_username=username, admin_password=password, admin_email=email
    )
    _print(
        {
            "user_id": result.user_id,
            "username": result.username,
            "admin_role_id": result.admin_role_id,
            "signing_kid": result.signing_kid,
            "note": result.note,
        }
    )


# ---------------------------------------------------------------------------
# user
# ---------------------------------------------------------------------------


@auth.group()
@click.pass_context
def user(ctx: click.Context) -> None:
    """User account commands."""
    ctx.ensure_object(dict)


@user.command("create")
@click.argument("username")
@click.option("--password", default=None)
@click.option("--email", default=None)
@click.pass_context
def user_create(
    ctx: click.Context, username: str, password: Optional[str], email: Optional[str]
) -> None:
    """Create a new user account."""
    if password is None:
        password = getpass.getpass(f"Password for {username}: ")
    with _client(ctx.obj["auth_url"]) as c:
        _print(c.create_user(username, password, email))


@user.command("deactivate")
@click.argument("user_id")
@click.pass_context
def user_deactivate(ctx: click.Context, user_id: str) -> None:
    """Deactivate a user (no future logins; existing tokens still verify until exp)."""
    with _client(ctx.obj["auth_url"]) as c:
        _print(c.update_user(user_id, is_active=False))


@user.command("password")
@click.argument("user_id")
@click.option("--new-password", default=None)
@click.pass_context
def user_password(
    ctx: click.Context, user_id: str, new_password: Optional[str]
) -> None:
    """Set a new password for a user."""
    if new_password is None:
        new_password = getpass.getpass("New password: ")
    with _client(ctx.obj["auth_url"]) as c:
        _print(c.update_user(user_id, new_password=new_password))


@user.command("list")
@click.pass_context
def user_list(ctx: click.Context) -> None:
    """List all user accounts."""
    with _client(ctx.obj["auth_url"]) as c:
        _print(c.list_users())


@user.command("grant")
@click.argument("role_id")
@click.argument("user_id")
@click.option("--project-id", default=None)
@click.pass_context
def user_grant(
    ctx: click.Context, role_id: str, user_id: str, project_id: Optional[str]
) -> None:
    """Grant a role to a user, optionally scoped to a project."""
    with _client(ctx.obj["auth_url"]) as c:
        body: dict = {"role_id": role_id, "user_id": user_id}
        if project_id:
            body["project_id"] = project_id
        _print(c.grant_role(**body))


# ---------------------------------------------------------------------------
# project
# ---------------------------------------------------------------------------


@auth.group()
@click.pass_context
def project(ctx: click.Context) -> None:
    """Project commands."""
    ctx.ensure_object(dict)


@project.command("create")
@click.argument("name")
@click.option("--description", default=None)
@click.pass_context
def project_create(ctx: click.Context, name: str, description: Optional[str]) -> None:
    """Create a new project."""
    with _client(ctx.obj["auth_url"]) as c:
        _print(c.create_project(name, description))


@project.command("list")
@click.pass_context
def project_list(ctx: click.Context) -> None:
    """List all projects."""
    with _client(ctx.obj["auth_url"]) as c:
        _print(c.list_projects())


@project.command("members")
@click.argument("project_id")
@click.argument("user_id")
@click.argument("role_id")
@click.pass_context
def project_members(
    ctx: click.Context, project_id: str, user_id: str, role_id: str
) -> None:
    """Add a user to a project with a role."""
    with _client(ctx.obj["auth_url"]) as c:
        _print(c.add_project_member(project_id, user_id, role_id))


# ---------------------------------------------------------------------------
# manager / node register
# ---------------------------------------------------------------------------


@auth.group()
@click.pass_context
def manager(ctx: click.Context) -> None:
    """Service-account commands for managers."""
    ctx.ensure_object(dict)


@manager.command("register")
@click.option("--manager-id", required=True)
@click.option("--role-id", "role_ids", multiple=True)
@click.pass_context
def manager_register(
    ctx: click.Context, manager_id: str, role_ids: tuple[str, ...]
) -> None:
    """Register a manager service account; returns the plaintext secret once."""
    with _client(ctx.obj["auth_url"]) as c:
        _print(c.register_service_account(manager_id, list(role_ids)))


@manager.command("list")
@click.pass_context
def manager_list(ctx: click.Context) -> None:
    """List managers via roles (placeholder — see /service-accounts)."""
    with _client(ctx.obj["auth_url"]) as c:
        # No dedicated list endpoint in v1; show roles + a hint.
        _print(c.list_roles())


@auth.group()
@click.pass_context
def node(ctx: click.Context) -> None:
    """Node-identity commands."""
    ctx.ensure_object(dict)


@node.command("register")
@click.option("--node-id", required=True)
@click.option("--workcell-id", default=None)
@click.option("--role-id", "role_ids", multiple=True)
@click.pass_context
def node_register(
    ctx: click.Context,
    node_id: str,
    workcell_id: Optional[str],
    role_ids: tuple[str, ...],
) -> None:
    """Register a node identity; returns the plaintext secret once."""
    with _client(ctx.obj["auth_url"]) as c:
        _print(c.register_node(node_id, workcell_id, list(role_ids)))


@node.command("list")
@click.pass_context
def node_list(ctx: click.Context) -> None:
    """List nodes via roles (placeholder — see /node-identities)."""
    with _client(ctx.obj["auth_url"]) as c:
        _print(c.list_roles())


# ---------------------------------------------------------------------------
# credentials
# ---------------------------------------------------------------------------


@auth.group()
@click.pass_context
def credentials(ctx: click.Context) -> None:
    """Credential rotation commands."""
    ctx.ensure_object(dict)


@credentials.command("rotate")
@click.argument("client_id")
@click.pass_context
def credentials_rotate(ctx: click.Context, client_id: str) -> None:
    """Rotate a service-account or node-identity secret; returns the new secret once."""
    with _client(ctx.obj["auth_url"]) as c:
        _print(c.rotate_credentials(client_id))


# ---------------------------------------------------------------------------
# keys
# ---------------------------------------------------------------------------


@auth.group()
@click.pass_context
def keys(ctx: click.Context) -> None:
    """Signing-key commands."""
    ctx.ensure_object(dict)


@keys.command("rotate")
@click.pass_context
def keys_rotate(ctx: click.Context) -> None:
    """Generate a new signing keypair; previous one stays in JWKS for verification."""
    with _client(ctx.obj["auth_url"]) as c:
        _print(c.rotate_keys())


@keys.command("list")
@click.pass_context
def keys_list(ctx: click.Context) -> None:
    """List all signing keys."""
    with _client(ctx.obj["auth_url"]) as c:
        _print(c.list_keys())


@keys.command("retire")
@click.argument("kid")
@click.pass_context
def keys_retire(ctx: click.Context, kid: str) -> None:
    """Retire a signing key (remove from JWKS, delete private material)."""
    with _client(ctx.obj["auth_url"]) as c:
        _print(c.retire_key(kid))

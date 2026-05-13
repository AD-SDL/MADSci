# alembic/env.py
# ruff: noqa
# flake8: noqa
"""Alembic environment configuration for MADSci Auth Manager."""

import os
import sys
from logging.config import fileConfig
from pathlib import Path

import sqlmodel
import sqlmodel.sql.sqltypes
from alembic import context
from sqlalchemy import engine_from_config, pool


def setup_python_path() -> Path:
    """Ensure Python path includes the package root for imports."""
    env_file_dir = Path(__file__).resolve().parent
    package_root = env_file_dir.parent
    if not (package_root / "alembic.ini").exists():
        for parent in package_root.parents:
            if (parent / "alembic.ini").exists():
                package_root = parent
                break
    package_root_str = str(package_root)
    if package_root_str not in sys.path:
        sys.path.insert(0, package_root_str)
    return package_root


package_root = setup_python_path()

from madsci.auth_manager.tables import metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = metadata


def get_database_url() -> str:
    """Get database URL from environment variables set by migration tool."""
    db_url = os.getenv("AUTH_DB_URL") or os.getenv("AUTH_DATABASE_URL")
    if db_url:
        return db_url
    db_url = config.get_main_option("sqlalchemy.url")
    if db_url and db_url.strip():
        return db_url
    raise RuntimeError(
        "Database URL not provided to Alembic. Set AUTH_DB_URL or pass via "
        "the migration tool."
    )


def include_object(
    object,
    name: str,
    type_: str,
    reflected: bool,
    compare_to,
) -> bool:
    """Exclude alembic_version table from autogenerate."""
    if type_ == "table" and name == "alembic_version":
        return False
    return True


def render_item(type_: str, obj, autogen_context) -> object:
    """Apply custom rendering for SQLModel types."""
    if type_ == "type" and hasattr(obj, "__class__"):
        if "AutoString" in str(obj.__class__):
            return "sa.String()"
    return False


def run_migrations_offline() -> None:
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = get_database_url()
    config.set_main_option("sqlalchemy.url", url)
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            render_item=render_item,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

# alembic/env.py
# flake8: noqa
"""Alembic environment configuration for MADSci resources."""

import sys
import os
from pathlib import Path
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Import SQLModel types to ensure they're available during migration generation
import sqlmodel  # noqa: F401
import sqlmodel.sql.sqltypes  # noqa: F401


# Add the package root to Python path for imports to work from any directory
def setup_python_path():
    """Ensure Python path includes the package root for imports."""
    # Get the directory containing this env.py file
    env_file_dir = Path(__file__).resolve().parent

    # Navigate up to find the package root (should contain alembic.ini)
    package_root = env_file_dir.parent

    # Look for alembic.ini to confirm we have the right directory
    if not (package_root / "alembic.ini").exists():
        # If not found, check parent directories
        for parent in package_root.parents:
            if (parent / "alembic.ini").exists():
                package_root = parent
                break

    # Add to Python path if not already there
    package_root_str = str(package_root)
    if package_root_str not in sys.path:
        sys.path.insert(0, package_root_str)

    return package_root


# Setup the Python path before any imports
package_root = setup_python_path()

# Import your models - now this should work from any directory
try:
    from madsci.resource_manager.resource_tables import (
        ResourceTable,
        ResourceHistoryTable,
        ResourceTemplateTable,
        SchemaVersionTable,
    )
except ImportError as e:
    print(f"Warning: Could not import resource tables: {e}")
    print(f"Package root: {package_root}")
    print(f"Python path: {sys.path}")
    raise

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# Set target metadata from your models
target_metadata = ResourceTable.metadata


def get_database_url():
    """Get database URL from environment variables set by migration tool."""
    # First try: URL passed from migration tool
    db_url = os.getenv("RESOURCES_DB_URL")
    if db_url:
        return db_url

    # Second try: URL from alembic config (usually empty)
    db_url = config.get_main_option("sqlalchemy.url")
    if db_url and db_url.strip():
        return db_url

    # If no URL found, this should not happen if migration tool is working correctly
    raise RuntimeError(
        "Database URL not provided to Alembic. "
        "This should be set by the migration tool via RESOURCES_DB_URL environment variable."
    )


def include_object(object, name, type_, reflected, compare_to):
    """Include only our tables, exclude alembic_version table from autogenerate."""
    if type_ == "table" and name == "alembic_version":
        return False
    return True


def render_item(type_, obj, autogen_context):
    """Apply custom rendering for SQLModel types."""
    # Convert SQLModel AutoString to regular String
    if type_ == "type" and hasattr(obj, "__class__"):
        if "AutoString" in str(obj.__class__):
            return "sa.String()"
    # Return None to use default rendering
    return False


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
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
    """Run migrations in 'online' mode."""
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

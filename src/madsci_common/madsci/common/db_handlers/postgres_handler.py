"""PostgreSQL/SQLite handler abstraction.

Provides an ABC for relational database access via SQLAlchemy and two implementations:
- SQLAlchemyHandler: wraps a real PostgreSQL connection
- SQLiteHandler: wraps an in-memory or file-based SQLite connection for testing
"""

from __future__ import annotations

import contextlib
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Optional, Union

if TYPE_CHECKING:
    from sqlalchemy import Engine, MetaData


class PostgresHandler(ABC):
    """Abstract interface for relational database access via SQLAlchemy.

    Managers use this interface instead of directly depending on
    ``sqlalchemy.Engine``, enabling SQLite substitution for tests.
    """

    @abstractmethod
    def get_engine(self) -> Union[Engine, Any]:
        """Return the SQLAlchemy Engine instance."""

    @abstractmethod
    def create_all_tables(self, metadata: Union[MetaData, Any]) -> None:
        """Create all tables defined in the given metadata.

        Args:
            metadata: A ``sqlalchemy.MetaData`` or ``sqlmodel.SQLModel.metadata`` object.
        """

    @abstractmethod
    def ping(self) -> bool:
        """Check connectivity to the database.

        Returns:
            True if the database is reachable, False otherwise.
        """

    @abstractmethod
    def close(self) -> None:
        """Release database connections and resources."""


class SQLAlchemyHandler(PostgresHandler):
    """PostgreSQL handler backed by a real SQLAlchemy engine.

    Usage::

        handler = SQLAlchemyHandler.from_url("postgresql://localhost/mydb")
        engine = handler.get_engine()
    """

    def __init__(self, engine: Any) -> None:
        """Initialize with an existing SQLAlchemy Engine.

        Args:
            engine: A ``sqlalchemy.Engine`` instance.
        """
        self._engine = engine

    @classmethod
    def from_url(
        cls,
        url: str,
        pool_size: int = 20,
        pool_pre_ping: bool = True,
    ) -> SQLAlchemyHandler:
        """Create a handler by connecting to a PostgreSQL database.

        Args:
            url: SQLAlchemy database URL.
            pool_size: Connection pool size.
            pool_pre_ping: Whether to verify connections before use.

        Returns:
            A new SQLAlchemyHandler instance.
        """
        from sqlalchemy import create_engine  # noqa: PLC0415

        engine = create_engine(
            url,
            pool_size=pool_size,
            pool_pre_ping=pool_pre_ping,
        )
        return cls(engine)

    def get_engine(self) -> Any:
        """Return the SQLAlchemy Engine."""
        return self._engine

    def create_all_tables(self, metadata: Any) -> None:
        """Create all tables using the engine."""
        metadata.create_all(self._engine)

    def ping(self) -> bool:
        """Execute ``SELECT 1`` to verify connectivity."""
        from sqlalchemy import text  # noqa: PLC0415

        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def close(self) -> None:
        """Dispose of the engine's connection pool."""
        with contextlib.suppress(Exception):
            self._engine.dispose()


class SQLiteHandler(PostgresHandler):
    """SQLite handler for testing, using SQLAlchemy with a SQLite backend.

    Defaults to an in-memory database (``sqlite:///:memory:``) but can
    also use a file-based SQLite database.  In-memory databases use
    ``StaticPool`` so the same connection is shared across threads (required
    for ``TestClient`` and similar multi-threaded test harnesses).

    Usage::

        handler = SQLiteHandler()  # in-memory
        handler = SQLiteHandler("sqlite:///path/to/db.sqlite")  # file-based
    """

    def __init__(self, url: Optional[str] = None) -> None:
        """Initialize with an optional SQLite URL.

        Args:
            url: SQLite connection URL. Defaults to ``sqlite:///:memory:``.
        """
        from sqlalchemy import create_engine  # noqa: PLC0415
        from sqlalchemy.pool import StaticPool  # noqa: PLC0415

        self._url = url or "sqlite:///:memory:"
        if self._url == "sqlite:///:memory:":
            # Share a single connection across threads so that tables created
            # in one thread are visible in another (e.g. Starlette TestClient).
            self._engine = create_engine(
                self._url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        else:
            self._engine = create_engine(self._url)

    def get_engine(self) -> Any:
        """Return the SQLAlchemy Engine."""
        return self._engine

    def create_all_tables(self, metadata: Any) -> None:
        """Create compatible tables using the SQLite engine.

        When a table uses PostgreSQL-specific features (e.g. ``AUTOINCREMENT``
        on a composite primary key), the handler builds SQLite-compatible DDL
        where the autoincrement column becomes the sole ``INTEGER PRIMARY KEY
        AUTOINCREMENT`` and other PK columns become regular ``NOT NULL`` columns.
        """
        from sqlalchemy.exc import CompileError  # noqa: PLC0415

        for table in metadata.sorted_tables:
            try:
                table.create(self._engine, checkfirst=True)
            except CompileError:
                self._create_table_sqlite_compat(table)

    def _create_table_sqlite_compat(self, table: Any) -> None:
        """Create a table using SQLite-compatible DDL.

        For tables with autoincrement columns in composite primary keys,
        the autoincrement column becomes the sole ``INTEGER PRIMARY KEY
        AUTOINCREMENT`` and other PK columns become regular ``NOT NULL``
        columns.
        """
        from sqlalchemy import text  # noqa: PLC0415

        col_defs = []
        for col in table.columns:
            col_type = col.type.compile(dialect=self._engine.dialect)
            if col.autoincrement is True:
                col_defs.append(f'"{col.name}" INTEGER PRIMARY KEY AUTOINCREMENT')
            else:
                parts = [f'"{col.name}" {col_type}']
                if not col.nullable:
                    parts.append("NOT NULL")
                if col.server_default is not None:
                    default_arg = col.server_default.arg
                    if hasattr(default_arg, "text"):
                        default_arg = default_arg.text
                    parts.append(f"DEFAULT {default_arg}")
                col_defs.append(" ".join(parts))

        ddl = f'CREATE TABLE IF NOT EXISTS "{table.name}" ({", ".join(col_defs)})'
        with self._engine.connect() as conn:
            conn.execute(text(ddl))
            conn.commit()

    def ping(self) -> bool:
        """Execute ``SELECT 1`` to verify connectivity."""
        from sqlalchemy import text  # noqa: PLC0415

        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def close(self) -> None:
        """Dispose of the engine's connection pool."""
        with contextlib.suppress(Exception):
            self._engine.dispose()

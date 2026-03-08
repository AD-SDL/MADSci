Module madsci.common.db_handlers.postgres_handler
=================================================
PostgreSQL/SQLite handler abstraction.

Provides an ABC for relational database access via SQLAlchemy and two implementations:
- SQLAlchemyHandler: wraps a real PostgreSQL connection
- SQLiteHandler: wraps an in-memory or file-based SQLite connection for testing

Classes
-------

`PostgresHandler()`
:   Abstract interface for relational database access via SQLAlchemy.
    
    Managers use this interface instead of directly depending on
    ``sqlalchemy.Engine``, enabling SQLite substitution for tests.

    ### Ancestors (in MRO)

    * abc.ABC

    ### Descendants

    * madsci.common.db_handlers.postgres_handler.SQLAlchemyHandler
    * madsci.common.db_handlers.postgres_handler.SQLiteHandler

    ### Methods

    `close(self) ‑> None`
    :   Release database connections and resources.

    `create_all_tables(self, metadata: Any) ‑> None`
    :   Create all tables defined in the given metadata.
        
        Args:
            metadata: A ``sqlalchemy.MetaData`` or ``sqlmodel.SQLModel.metadata`` object.

    `get_engine(self) ‑> Any`
    :   Return the SQLAlchemy Engine instance.

    `ping(self) ‑> bool`
    :   Check connectivity to the database.
        
        Returns:
            True if the database is reachable, False otherwise.

`SQLAlchemyHandler(engine: Any)`
:   PostgreSQL handler backed by a real SQLAlchemy engine.
    
    Usage::
    
        handler = SQLAlchemyHandler.from_url("postgresql://localhost/mydb")
        engine = handler.get_engine()
    
    Initialize with an existing SQLAlchemy Engine.
    
    Args:
        engine: A ``sqlalchemy.Engine`` instance.

    ### Ancestors (in MRO)

    * madsci.common.db_handlers.postgres_handler.PostgresHandler
    * abc.ABC

    ### Static methods

    `from_url(url: str, pool_size: int = 20, pool_pre_ping: bool = True) ‑> madsci.common.db_handlers.postgres_handler.SQLAlchemyHandler`
    :   Create a handler by connecting to a PostgreSQL database.
        
        Args:
            url: SQLAlchemy database URL.
            pool_size: Connection pool size.
            pool_pre_ping: Whether to verify connections before use.
        
        Returns:
            A new SQLAlchemyHandler instance.

    ### Methods

    `close(self) ‑> None`
    :   Dispose of the engine's connection pool.

    `create_all_tables(self, metadata: Any) ‑> None`
    :   Create all tables using the engine.

    `get_engine(self) ‑> Any`
    :   Return the SQLAlchemy Engine.

    `ping(self) ‑> bool`
    :   Execute ``SELECT 1`` to verify connectivity.

`SQLiteHandler(url: Optional[str] = None)`
:   SQLite handler for testing, using SQLAlchemy with a SQLite backend.
    
    Defaults to an in-memory database (``sqlite:///:memory:``) but can
    also use a file-based SQLite database.  In-memory databases use
    ``StaticPool`` so the same connection is shared across threads (required
    for ``TestClient`` and similar multi-threaded test harnesses).
    
    Usage::
    
        handler = SQLiteHandler()  # in-memory
        handler = SQLiteHandler("sqlite:///path/to/db.sqlite")  # file-based
    
    Initialize with an optional SQLite URL.
    
    Args:
        url: SQLite connection URL. Defaults to ``sqlite:///:memory:``.

    ### Ancestors (in MRO)

    * madsci.common.db_handlers.postgres_handler.PostgresHandler
    * abc.ABC

    ### Methods

    `close(self) ‑> None`
    :   Dispose of the engine's connection pool.

    `create_all_tables(self, metadata: Any) ‑> None`
    :   Create compatible tables using the SQLite engine.
        
        When a table uses PostgreSQL-specific features (e.g. ``AUTOINCREMENT``
        on a composite primary key), the handler builds SQLite-compatible DDL
        where the autoincrement column becomes the sole ``INTEGER PRIMARY KEY
        AUTOINCREMENT`` and other PK columns become regular ``NOT NULL`` columns.

    `get_engine(self) ‑> Any`
    :   Return the SQLAlchemy Engine.

    `ping(self) ‑> bool`
    :   Execute ``SELECT 1`` to verify connectivity.
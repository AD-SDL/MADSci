Module madsci.common.backup_tools.cli
=====================================
Unified CLI for MADSci backup operations across all database types.

Functions
---------

`detect_database_type(db_url: str) ‑> Literal['postgresql', 'mongodb']`
:   Auto-detect database type from connection URL.

    Args:
        db_url: Database connection URL

    Returns:
        Database type: "postgresql" or "mongodb"

    Raises:
        ValueError: If database type cannot be detected

`load_config(config_path: str) ‑> dict`
:   Load configuration from JSON file.

    Args:
        config_path: Path to configuration file

    Returns:
        Configuration dictionary

`main() ‑> None`
:   Entry point for madsci-backup CLI.

# MADSci Database Backup Tools

## Overview

MADSci provides standalone backup tools for PostgreSQL and MongoDB databases. These tools can be used independently or integrated with MADSci's database migration workflows.

## Features

- **Standalone Backup Tools**: Use backup functionality without running migrations
- **Multiple Database Support**: PostgreSQL (via pg_dump/pg_restore) and MongoDB (via mongodump/mongorestore)
- **Unified CLI**: Single command-line interface for all database types
- **Auto-Detection**: Automatically detects database type from connection URL
- **Integrity Validation**: SHA256 checksums and backup verification
- **Backup Rotation**: Automatic cleanup of old backups based on retention policies
- **Migration Integration**: Seamlessly integrated with MADSci migration tools

## Installation

### For PostgreSQL Backups

```bash
pip install madsci-resource-manager
```

This provides both the PostgreSQL backup tool and the unified CLI.

### For MongoDB Backups

```bash
pip install madsci-common
```

This provides the MongoDB backup tool and CLI.

### For Both

```bash
pip install madsci-common madsci-resource-manager
```

## Quick Start

### Using the Unified CLI

The `madsci-backup` command automatically detects your database type:

```bash
# PostgreSQL backup
madsci-backup create --db-url postgresql://user:pass@localhost/mydb

# MongoDB backup
madsci-backup create --db-url mongodb://localhost:27017/mydb

# Custom backup directory
madsci-backup create --db-url postgresql://localhost/mydb --backup-dir /backups/prod

# Named backup (adds suffix)
madsci-backup create --db-url mongodb://localhost/mydb --name pre-deploy
```

### Restoring Backups

```bash
# Restore PostgreSQL backup
madsci-backup restore --backup /path/to/backup.dump --db-url postgresql://localhost/mydb

# Restore MongoDB backup
madsci-backup restore --backup /path/to/backup_dir --db-url mongodb://localhost/mydb
```

### Validating Backups

```bash
# Validate backup integrity
madsci-backup validate --backup /path/to/backup.dump --db-url postgresql://localhost/mydb
```

## Database-Specific CLIs

For more control, use the database-specific CLI tools:

### PostgreSQL

```bash
# Located in madsci-resource-manager package
from madsci.resource_manager.backup_tools.cli import main_postgres_backup

# Or use entry point (if configured)
madsci-postgres-backup create --db-url postgresql://localhost/db
```

### MongoDB

```bash
# Use the MongoDB-specific CLI
madsci-mongodb-backup create --mongo-url mongodb://localhost/db --database mydb
```

## Programmatic Usage

### PostgreSQL Backups

```python
from pathlib import Path
from madsci.resource_manager.backup_tools import (
    PostgreSQLBackupTool,
    PostgreSQLBackupSettings
)

# Configure backup settings
settings = PostgreSQLBackupSettings(
    db_url="postgresql://user:pass@localhost/mydb",
    backup_dir=Path("./backups"),
    max_backups=10,          # Keep last 10 backups
    validate_integrity=True,  # Validate after creation
    backup_format="custom"    # Use custom pg_dump format
)

# Create backup tool
backup_tool = PostgreSQLBackupTool(settings)

# Create a backup
backup_path = backup_tool.create_backup("before_migration")
print(f"Backup created: {backup_path}")

# List available backups
backups = backup_tool.list_available_backups()
for backup in backups:
    print(f"  {backup.backup_path} - {backup.created_at} - {backup.backup_size} bytes")

# Restore from backup
backup_tool.restore_from_backup(backup_path)

# Validate backup integrity
is_valid = backup_tool.validate_backup_integrity(backup_path)
print(f"Backup valid: {is_valid}")
```

### MongoDB Backups

```python
from pathlib import Path
from pydantic import AnyUrl
from madsci.common.backup_tools import (
    MongoDBBackupTool,
    MongoDBBackupSettings
)

# Configure backup settings
settings = MongoDBBackupSettings(
    mongo_db_url=AnyUrl("mongodb://localhost:27017"),
    database="mydb",
    backup_dir=Path("./backups"),
    max_backups=10,
    validate_integrity=True,
    collections=["users", "experiments"]  # Optional: specific collections
)

# Create backup tool
backup_tool = MongoDBBackupTool(settings)

# Create a backup
backup_path = backup_tool.create_backup("hourly")
print(f"Backup created: {backup_path}")

# Restore from backup
backup_tool.restore_from_backup(backup_path, target_database="mydb_restored")

# Validate backup
is_valid = backup_tool.validate_backup_integrity(backup_path)
print(f"Backup valid: {is_valid}")
```

## Integration with Migrations

The backup tools are automatically used by MADSci's migration tools:

```python
from madsci.resource_manager.migration_tool import DatabaseMigrator
from madsci.resource_manager.migration_types import DatabaseMigrationSettings

# Configure migration
settings = DatabaseMigrationSettings(
    db_url="postgresql://localhost/mydb",
    backup_dir=Path("./migration_backups")
)

# Create migrator (includes backup tool)
migrator = DatabaseMigrator(settings)

# Run migration (automatically creates backup first)
migrator.run_migration(target_version="head")
# If migration fails, automatically restores from backup
```

## Configuration Options

### PostgreSQL Backup Settings

```python
class PostgreSQLBackupSettings(BaseBackupSettings):
    db_url: str                    # Database connection URL
    backup_dir: Path               # Where to store backups
    backup_format: str = "custom"  # pg_dump format: custom, plain, directory, tar
    max_backups: int = 10          # Number of backups to retain
    validate_integrity: bool = True # Validate backups after creation
    compression: bool = True        # Enable compression (format dependent)
```

### MongoDB Backup Settings

```python
class MongoDBBackupSettings(BaseBackupSettings):
    mongo_db_url: AnyUrl          # MongoDB connection URL
    database: str                  # Database name to backup
    backup_dir: Path               # Where to store backups
    collections: Optional[List[str]] = None  # Specific collections (None = all)
    max_backups: int = 10          # Number of backups to retain
    validate_integrity: bool = True # Validate backups after creation
```

## Backup File Structure

### PostgreSQL Backups

```
backups/
├── postgres_backup_20240124_120000.dump
├── postgres_backup_20240124_120000.dump.meta
├── postgres_backup_20240124_120000.dump.sha256
└── postgres_backup_20240124_150000_pre_migration.dump
```

### MongoDB Backups

```
backups/
├── mongodb_mydb_20240124_120000/
│   ├── users.bson
│   ├── users.metadata.json
│   ├── experiments.bson
│   └── experiments.metadata.json
├── mongodb_mydb_20240124_120000.meta
└── mongodb_mydb_20240124_120000.sha256
```

## Backup Metadata

Each backup includes metadata in a `.meta` JSON file:

```json
{
  "backup_path": "/backups/postgres_backup_20240124_120000.dump",
  "created_at": "2024-01-24T12:00:00",
  "database_version": "PostgreSQL 15.3",
  "backup_size": 1048576,
  "checksum": "a1b2c3d4e5f6...",
  "backup_type": "postgresql",
  "is_valid": true,
  "settings": {
    "backup_format": "custom",
    "validate_integrity": true
  }
}
```

## Best Practices

### 1. Regular Backups

Schedule regular backups using cron:

```bash
# Daily backup at 2 AM
0 2 * * * madsci-backup create --db-url postgresql://localhost/prod --name daily

# Hourly backups
0 * * * * madsci-backup create --db-url mongodb://localhost/events --name hourly
```

### 2. Backup Rotation

Configure appropriate retention policies:

```python
# Keep last 10 backups (default)
settings = PostgreSQLBackupSettings(
    db_url="postgresql://localhost/db",
    max_backups=10
)

# Keep more backups for production
settings = PostgreSQLBackupSettings(
    db_url="postgresql://localhost/prod",
    max_backups=30  # Keep last 30 days
)
```

### 3. Backup Validation

Always validate critical backups:

```bash
# Validate after creation
madsci-backup validate --backup /path/to/backup.dump --db-url postgresql://localhost/db

# Validate programmatically
is_valid = backup_tool.validate_backup_integrity(backup_path)
if not is_valid:
    alert_ops_team("Backup validation failed!")
```

### 4. Test Restores

Regularly test backup restoration:

```python
# Restore to test database
backup_tool.restore_from_backup(
    backup_path,
    target_db="postgresql://localhost/test_restore"
)

# Verify data integrity
run_verification_queries()
```

### 5. Backup Storage

Store backups securely and redundantly:

```python
# Local backups
settings = PostgreSQLBackupSettings(
    db_url="postgresql://localhost/db",
    backup_dir=Path("/backups/local")
)

# Additional copy to network storage
import shutil
shutil.copy(backup_path, "/mnt/network_backup/")
```

## Troubleshooting

### PostgreSQL Backups Fail

**Problem**: `pg_dump: command not found`

**Solution**: Ensure PostgreSQL client tools are installed:
```bash
# Ubuntu/Debian
sudo apt-get install postgresql-client

# macOS
brew install postgresql
```

### MongoDB Backups Fail

**Problem**: `mongodump: command not found`

**Solution**: Ensure MongoDB database tools are installed:
```bash
# Ubuntu/Debian
sudo apt-get install mongodb-database-tools

# macOS
brew install mongodb-database-tools
```

### Validation Failures

**Problem**: Backup validation fails

**Possible Causes**:
1. Backup was interrupted during creation
2. Disk corruption
3. Insufficient disk space during backup

**Solution**: Delete corrupted backup and create new one:
```python
backup_tool.delete_backup(corrupted_path)
backup_path = backup_tool.create_backup()
```

### Permission Errors

**Problem**: Permission denied when creating backups

**Solution**: Ensure backup directory has proper permissions:
```bash
mkdir -p /backups
chmod 755 /backups
chown myuser:mygroup /backups
```

## Advanced Usage

### Custom Backup Locations

```python
from datetime import datetime

# Date-based backup organization
today = datetime.now().strftime("%Y-%m-%d")
backup_dir = Path(f"/backups/{today}")
backup_dir.mkdir(parents=True, exist_ok=True)

settings = PostgreSQLBackupSettings(
    db_url="postgresql://localhost/db",
    backup_dir=backup_dir
)
```

### Selective MongoDB Collections

```python
# Backup only specific collections
settings = MongoDBBackupSettings(
    mongo_db_url=AnyUrl("mongodb://localhost:27017"),
    database="mydb",
    collections=["critical_data", "user_configs"]  # Skip large log collections
)
```

### Integration with Monitoring

```python
from madsci.client import EventClient

# Log backup operations
logger = EventClient()

try:
    backup_path = backup_tool.create_backup()
    logger.info(f"Backup successful: {backup_path}")
except Exception as e:
    logger.error(f"Backup failed: {e}")
    raise
```

## API Reference

### PostgreSQLBackupTool

```python
class PostgreSQLBackupTool(AbstractBackupTool):
    def __init__(self, settings: PostgreSQLBackupSettings, logger: Optional[EventClient] = None)
    def create_backup(self, name_suffix: Optional[str] = None) -> Path
    def restore_from_backup(self, backup_path: Path, target_database: Optional[str] = None) -> None
    def validate_backup_integrity(self, backup_path: Path) -> bool
    def list_available_backups(self) -> List[BackupInfo]
    def delete_backup(self, backup_path: Path) -> None
```

### MongoDBBackupTool

```python
class MongoDBBackupTool(AbstractBackupTool):
    def __init__(self, settings: MongoDBBackupSettings, logger: Optional[EventClient] = None)
    def create_backup(self, name_suffix: Optional[str] = None) -> Path
    def restore_from_backup(self, backup_path: Path, target_database: Optional[str] = None) -> None
    def validate_backup_integrity(self, backup_path: Path) -> bool
    def list_available_backups(self) -> List[BackupInfo]
    def delete_backup(self, backup_path: Path) -> None
```

## Related Documentation

- [Database Migrations](./MIGRATIONS.md) - MADSci database migration tools
- [Configuration Guide](../Configuration.md) - Environment variable configuration
- [Architecture Overview](./ARCHITECTURE.md) - MADSci system architecture

## Support

For issues or questions:
- GitHub Issues: https://github.com/AD-SDL/MADSci/issues
- Documentation: https://github.com/AD-SDL/MADSci/tree/main/docs
# MADSci Backup Tools - Usage Examples

This guide provides practical examples for common backup scenarios using MADSci's backup tools.

## Table of Contents

- [Basic Backup Operations](#basic-backup-operations)
- [Production Backup Strategies](#production-backup-strategies)
- [Automated Backup Workflows](#automated-backup-workflows)
- [Disaster Recovery](#disaster-recovery)
- [Integration Examples](#integration-examples)

## Basic Backup Operations

### Example 1: Simple PostgreSQL Backup

```python
from pathlib import Path
from madsci.resource_manager.backup_tools import (
    PostgreSQLBackupTool,
    PostgreSQLBackupSettings
)

# Configure and create backup
settings = PostgreSQLBackupSettings(
    db_url="postgresql://madsci:password@localhost/resources",
    backup_dir=Path("./backups")
)

tool = PostgreSQLBackupTool(settings)
backup_path = tool.create_backup()

print(f"✓ Backup created: {backup_path}")
```

### Example 2: MongoDB Backup with Specific Collections

```python
from pathlib import Path
from pydantic import AnyUrl
from madsci.common.backup_tools import (
    MongoDBBackupTool,
    MongoDBBackupSettings
)

# Backup only critical collections
settings = MongoDBBackupSettings(
    mongo_db_url=AnyUrl("mongodb://localhost:27017"),
    database="events",
    backup_dir=Path("./backups"),
    collections=["system_events", "experiment_logs"]  # Skip large debug collections
)

tool = MongoDBBackupTool(settings)
backup_path = tool.create_backup("critical_only")

print(f"✓ Critical data backed up: {backup_path}")
```

### Example 3: Backup Before Maintenance

```python
from pathlib import Path
from madsci.resource_manager.backup_tools import PostgreSQLBackupTool, PostgreSQLBackupSettings

def perform_maintenance():
    # Create backup before maintenance
    settings = PostgreSQLBackupSettings(
        db_url="postgresql://localhost/resources",
        backup_dir=Path("./maintenance_backups")
    )

    tool = PostgreSQLBackupTool(settings)
    backup_path = tool.create_backup("pre_maintenance")

    try:
        # Perform maintenance operations
        run_data_cleanup()
        optimize_indexes()
        update_statistics()

        print("✓ Maintenance completed successfully")

    except Exception as e:
        # Restore if maintenance fails
        print(f"✗ Maintenance failed: {e}")
        print("Restoring from backup...")
        tool.restore_from_backup(backup_path)
        print("✓ Database restored to pre-maintenance state")
        raise

perform_maintenance()
```

## Production Backup Strategies

### Example 4: Multi-Tier Backup Strategy

```python
from pathlib import Path
from datetime import datetime
from madsci.resource_manager.backup_tools import PostgreSQLBackupTool, PostgreSQLBackupSettings

class BackupStrategy:
    def __init__(self, db_url: str, base_dir: Path):
        self.db_url = db_url
        self.base_dir = base_dir

    def hourly_backup(self):
        """Quick hourly backups - keep 24 hours."""
        settings = PostgreSQLBackupSettings(
            db_url=self.db_url,
            backup_dir=self.base_dir / "hourly",
            max_backups=24  # Keep last 24 hours
        )
        tool = PostgreSQLBackupTool(settings)
        backup_path = tool.create_backup("hourly")
        print(f"✓ Hourly backup: {backup_path}")
        return backup_path

    def daily_backup(self):
        """Daily backups - keep 30 days."""
        settings = PostgreSQLBackupSettings(
            db_url=self.db_url,
            backup_dir=self.base_dir / "daily",
            max_backups=30  # Keep last 30 days
        )
        tool = PostgreSQLBackupTool(settings)
        backup_path = tool.create_backup("daily")
        print(f"✓ Daily backup: {backup_path}")

        # Copy to long-term storage
        self._archive_to_long_term(backup_path)
        return backup_path

    def weekly_backup(self):
        """Weekly backups - keep 12 weeks."""
        settings = PostgreSQLBackupSettings(
            db_url=self.db_url,
            backup_dir=self.base_dir / "weekly",
            max_backups=12  # Keep last 12 weeks
        )
        tool = PostgreSQLBackupTool(settings)
        backup_path = tool.create_backup("weekly")
        print(f"✓ Weekly backup: {backup_path}")
        return backup_path

    def _archive_to_long_term(self, backup_path: Path):
        """Archive important backups to long-term storage."""
        import shutil
        archive_dir = Path("/mnt/archive/backups")
        archive_dir.mkdir(parents=True, exist_ok=True)

        shutil.copy2(backup_path, archive_dir / backup_path.name)
        print(f"  ✓ Archived to: {archive_dir}")

# Usage
strategy = BackupStrategy(
    db_url="postgresql://localhost/production",
    base_dir=Path("/backups/production")
)

# Schedule these with cron or similar
strategy.hourly_backup()  # Run every hour
strategy.daily_backup()   # Run daily at 2 AM
strategy.weekly_backup()  # Run Sunday at 3 AM
```

### Example 5: Backup with Verification

```python
from pathlib import Path
from madsci.resource_manager.backup_tools import PostgreSQLBackupTool, PostgreSQLBackupSettings
from madsci.client import EventClient

def create_verified_backup(db_url: str) -> Path:
    """Create backup with comprehensive verification."""

    logger = EventClient()
    settings = PostgreSQLBackupSettings(
        db_url=db_url,
        backup_dir=Path("./verified_backups"),
        validate_integrity=True  # Auto-validate
    )

    tool = PostgreSQLBackupTool(settings)

    # Create backup
    logger.info("Starting backup creation...")
    backup_path = tool.create_backup("verified")

    # Additional validation
    logger.info("Validating backup integrity...")
    if not tool.validate_backup_integrity(backup_path):
        logger.error("Backup validation failed!")
        raise RuntimeError("Backup integrity check failed")

    # Get backup info
    backups = tool.list_available_backups()
    latest = backups[0] if backups else None

    if latest:
        logger.info(f"Backup details:")
        logger.info(f"  Size: {latest.backup_size:,} bytes")
        logger.info(f"  Checksum: {latest.checksum[:16]}...")
        logger.info(f"  Valid: {latest.is_valid}")

    logger.info(f"✓ Verified backup created: {backup_path}")
    return backup_path

# Create verified backup
backup = create_verified_backup("postgresql://localhost/critical_data")
```

## Automated Backup Workflows

### Example 6: Scheduled Backup Script

```python
#!/usr/bin/env python3
"""
Automated backup script for MADSci databases.
Schedule with cron: 0 2 * * * /path/to/backup_script.py
"""

import sys
from pathlib import Path
from datetime import datetime
from madsci.resource_manager.backup_tools import PostgreSQLBackupTool, PostgreSQLBackupSettings
from madsci.common.backup_tools import MongoDBBackupTool, MongoDBBackupSettings
from pydantic import AnyUrl

def backup_all_databases():
    """Backup all MADSci databases."""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_base = Path("/backups/madsci")
    success_count = 0
    failed_databases = []

    # PostgreSQL - Resource Manager
    try:
        print(f"[{timestamp}] Backing up Resource Manager (PostgreSQL)...")
        settings = PostgreSQLBackupSettings(
            db_url="postgresql://localhost/resources",
            backup_dir=backup_base / "resources",
            max_backups=30
        )
        tool = PostgreSQLBackupTool(settings)
        backup_path = tool.create_backup("auto")
        print(f"  ✓ Success: {backup_path}")
        success_count += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        failed_databases.append(("resources", str(e)))

    # MongoDB - Event Manager
    try:
        print(f"[{timestamp}] Backing up Event Manager (MongoDB)...")
        settings = MongoDBBackupSettings(
            mongo_db_url=AnyUrl("mongodb://localhost:27017"),
            database="events",
            backup_dir=backup_base / "events",
            max_backups=30
        )
        tool = MongoDBBackupTool(settings)
        backup_path = tool.create_backup("auto")
        print(f"  ✓ Success: {backup_path}")
        success_count += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        failed_databases.append(("events", str(e)))

    # MongoDB - Data Manager
    try:
        print(f"[{timestamp}] Backing up Data Manager (MongoDB)...")
        settings = MongoDBBackupSettings(
            mongo_db_url=AnyUrl("mongodb://localhost:27017"),
            database="data",
            backup_dir=backup_base / "data",
            max_backups=30
        )
        tool = MongoDBBackupTool(settings)
        backup_path = tool.create_backup("auto")
        print(f"  ✓ Success: {backup_path}")
        success_count += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        failed_databases.append(("data", str(e)))

    # Summary
    print(f"\n{'='*60}")
    print(f"Backup Summary for {timestamp}")
    print(f"{'='*60}")
    print(f"Successful: {success_count}")
    print(f"Failed: {len(failed_databases)}")

    if failed_databases:
        print("\nFailed databases:")
        for db_name, error in failed_databases:
            print(f"  - {db_name}: {error}")
        sys.exit(1)
    else:
        print("\n✓ All backups completed successfully")
        sys.exit(0)

if __name__ == "__main__":
    backup_all_databases()
```

### Example 7: Pre-Deployment Backup Hook

```python
"""
Git pre-deployment hook to create backups before deploying.
Place in .git/hooks/pre-push or deployment script.
"""

from pathlib import Path
from madsci.resource_manager.backup_tools import PostgreSQLBackupTool, PostgreSQLBackupSettings

def pre_deployment_backup():
    """Create backup before deployment."""

    print("Creating pre-deployment backup...")

    settings = PostgreSQLBackupSettings(
        db_url="postgresql://localhost/production",
        backup_dir=Path("/backups/deployments")
    )

    tool = PostgreSQLBackupTool(settings)

    # Create backup with deployment info
    import subprocess
    git_hash = subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"]
    ).decode().strip()

    backup_path = tool.create_backup(f"deploy_{git_hash}")

    print(f"✓ Pre-deployment backup created: {backup_path}")
    print(f"  Git commit: {git_hash}")
    print("Deployment can proceed safely")

    return backup_path

if __name__ == "__main__":
    pre_deployment_backup()
```

## Disaster Recovery

### Example 8: Complete Disaster Recovery

```python
"""
Disaster recovery script to restore all MADSci databases.
"""

from pathlib import Path
from madsci.resource_manager.backup_tools import PostgreSQLBackupTool, PostgreSQLBackupSettings
from madsci.common.backup_tools import MongoDBBackupTool, MongoDBBackupSettings
from pydantic import AnyUrl

def disaster_recovery(backup_date: str):
    """
    Restore all databases from a specific backup date.

    Args:
        backup_date: Date string like "20240124"
    """

    backup_base = Path("/backups/madsci")

    print(f"{'='*60}")
    print(f"DISASTER RECOVERY PROCEDURE")
    print(f"Restoring from backups dated: {backup_date}")
    print(f"{'='*60}\n")

    # Confirm with operator
    response = input("This will overwrite current databases. Continue? (yes/NO): ")
    if response.lower() != "yes":
        print("Recovery cancelled.")
        return

    # PostgreSQL - Resource Manager
    print("\n[1/3] Restoring Resource Manager (PostgreSQL)...")
    try:
        settings = PostgreSQLBackupSettings(
            db_url="postgresql://localhost/resources",
            backup_dir=backup_base / "resources"
        )
        tool = PostgreSQLBackupTool(settings)

        # Find backup for specific date
        backups = tool.list_available_backups()
        target_backup = None
        for backup in backups:
            if backup_date in backup.backup_path.name:
                target_backup = backup.backup_path
                break

        if not target_backup:
            raise FileNotFoundError(f"No backup found for date: {backup_date}")

        print(f"  Restoring from: {target_backup}")
        tool.restore_from_backup(target_backup)
        print("  ✓ Resource Manager restored")

    except Exception as e:
        print(f"  ✗ Failed to restore Resource Manager: {e}")
        raise

    # MongoDB - Event Manager
    print("\n[2/3] Restoring Event Manager (MongoDB)...")
    try:
        settings = MongoDBBackupSettings(
            mongo_db_url=AnyUrl("mongodb://localhost:27017"),
            database="events",
            backup_dir=backup_base / "events"
        )
        tool = MongoDBBackupTool(settings)

        backups = tool.list_available_backups()
        target_backup = None
        for backup in backups:
            if backup_date in backup.backup_path.name:
                target_backup = backup.backup_path
                break

        if not target_backup:
            raise FileNotFoundError(f"No backup found for date: {backup_date}")

        print(f"  Restoring from: {target_backup}")
        tool.restore_from_backup(target_backup)
        print("  ✓ Event Manager restored")

    except Exception as e:
        print(f"  ✗ Failed to restore Event Manager: {e}")
        raise

    # MongoDB - Data Manager
    print("\n[3/3] Restoring Data Manager (MongoDB)...")
    try:
        settings = MongoDBBackupSettings(
            mongo_db_url=AnyUrl("mongodb://localhost:27017"),
            database="data",
            backup_dir=backup_base / "data"
        )
        tool = MongoDBBackupTool(settings)

        backups = tool.list_available_backups()
        target_backup = None
        for backup in backups:
            if backup_date in backup.backup_path.name:
                target_backup = backup.backup_path
                break

        if not target_backup:
            raise FileNotFoundError(f"No backup found for date: {backup_date}")

        print(f"  Restoring from: {target_backup}")
        tool.restore_from_backup(target_backup)
        print("  ✓ Data Manager restored")

    except Exception as e:
        print(f"  ✗ Failed to restore Data Manager: {e}")
        raise

    print(f"\n{'='*60}")
    print("✓ DISASTER RECOVERY COMPLETED SUCCESSFULLY")
    print(f"{'='*60}")
    print("\nNext steps:")
    print("1. Verify database integrity")
    print("2. Check application functionality")
    print("3. Review logs for any issues")
    print("4. Notify team of recovery completion")

# Usage
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: disaster_recovery.py <backup_date>")
        print("Example: disaster_recovery.py 20240124")
        sys.exit(1)

    disaster_recovery(sys.argv[1])
```

## Integration Examples

### Example 9: Integration with Experiment Workflow

```python
"""
Example: Backup before and after experiment runs.
"""

from pathlib import Path
from madsci.resource_manager.backup_tools import PostgreSQLBackupTool, PostgreSQLBackupSettings
from madsci.common.backup_tools import MongoDBBackupTool, MongoDBBackupSettings
from pydantic import AnyUrl

class ExperimentBackupManager:
    """Manage backups for experiment lifecycle."""

    def __init__(self, experiment_id: str):
        self.experiment_id = experiment_id
        self.backup_dir = Path(f"./experiment_backups/{experiment_id}")
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def backup_before_experiment(self):
        """Backup state before experiment starts."""
        print(f"Creating pre-experiment backup for {self.experiment_id}...")

        # Backup resource database
        resource_settings = PostgreSQLBackupSettings(
            db_url="postgresql://localhost/resources",
            backup_dir=self.backup_dir / "resources"
        )
        resource_tool = PostgreSQLBackupTool(resource_settings)
        resource_backup = resource_tool.create_backup("pre_experiment")

        # Backup data database
        data_settings = MongoDBBackupSettings(
            mongo_db_url=AnyUrl("mongodb://localhost:27017"),
            database="data",
            backup_dir=self.backup_dir / "data"
        )
        data_tool = MongoDBBackupTool(data_settings)
        data_backup = data_tool.create_backup("pre_experiment")

        print(f"✓ Pre-experiment backups created")
        return {
            "resources": resource_backup,
            "data": data_backup
        }

    def backup_after_experiment(self):
        """Backup state after experiment completes."""
        print(f"Creating post-experiment backup for {self.experiment_id}...")

        # Similar to pre-experiment, but with "post_experiment" suffix
        resource_settings = PostgreSQLBackupSettings(
            db_url="postgresql://localhost/resources",
            backup_dir=self.backup_dir / "resources"
        )
        resource_tool = PostgreSQLBackupTool(resource_settings)
        resource_backup = resource_tool.create_backup("post_experiment")

        data_settings = MongoDBBackupSettings(
            mongo_db_url=AnyUrl("mongodb://localhost:27017"),
            database="data",
            backup_dir=self.backup_dir / "data"
        )
        data_tool = MongoDBBackupTool(data_settings)
        data_backup = data_tool.create_backup("post_experiment")

        print(f"✓ Post-experiment backups created")
        return {
            "resources": resource_backup,
            "data": data_backup
        }

    def rollback_experiment(self, pre_backups: dict):
        """Rollback to pre-experiment state if needed."""
        print(f"Rolling back experiment {self.experiment_id}...")

        # Restore resources
        resource_settings = PostgreSQLBackupSettings(
            db_url="postgresql://localhost/resources",
            backup_dir=self.backup_dir / "resources"
        )
        resource_tool = PostgreSQLBackupTool(resource_settings)
        resource_tool.restore_from_backup(pre_backups["resources"])

        # Restore data
        data_settings = MongoDBBackupSettings(
            mongo_db_url=AnyUrl("mongodb://localhost:27017"),
            database="data",
            backup_dir=self.backup_dir / "data"
        )
        data_tool = MongoDBBackupTool(data_settings)
        data_tool.restore_from_backup(pre_backups["data"])

        print(f"✓ Experiment rolled back successfully")

# Usage in experiment workflow
def run_experiment_with_backup(experiment_id: str):
    """Run experiment with automatic backup/rollback."""

    manager = ExperimentBackupManager(experiment_id)

    # Backup before experiment
    pre_backups = manager.backup_before_experiment()

    try:
        # Run experiment
        print(f"Running experiment {experiment_id}...")
        run_experiment()

        # Backup after successful experiment
        post_backups = manager.backup_after_experiment()
        print("✓ Experiment completed successfully")

    except Exception as e:
        # Rollback on failure
        print(f"✗ Experiment failed: {e}")
        print("Rolling back to pre-experiment state...")
        manager.rollback_experiment(pre_backups)
        raise

# Run experiment
run_experiment_with_backup("EXP-2024-001")
```

### Example 10: Backup Health Monitoring

```python
"""
Monitor backup health and send alerts.
"""

from pathlib import Path
from datetime import datetime, timedelta
from madsci.resource_manager.backup_tools import PostgreSQLBackupTool, PostgreSQLBackupSettings

class BackupHealthMonitor:
    """Monitor backup health and integrity."""

    def __init__(self, backup_dir: Path):
        self.backup_dir = backup_dir

    def check_backup_freshness(self, max_age_hours: int = 24) -> dict:
        """Check if backups are recent enough."""

        settings = PostgreSQLBackupSettings(
            db_url="postgresql://localhost/resources",  # Not used for listing
            backup_dir=self.backup_dir
        )
        tool = PostgreSQLBackupTool(settings)

        backups = tool.list_available_backups()

        if not backups:
            return {
                "status": "CRITICAL",
                "message": "No backups found!",
                "action_required": True
            }

        latest = backups[0]
        age = datetime.now() - latest.created_at
        max_age = timedelta(hours=max_age_hours)

        if age > max_age:
            return {
                "status": "WARNING",
                "message": f"Latest backup is {age.total_seconds()/3600:.1f} hours old",
                "latest_backup": str(latest.backup_path),
                "age_hours": age.total_seconds() / 3600,
                "action_required": True
            }

        return {
            "status": "OK",
            "message": f"Latest backup is {age.total_seconds()/3600:.1f} hours old",
            "latest_backup": str(latest.backup_path),
            "age_hours": age.total_seconds() / 3600,
            "action_required": False
        }

    def check_backup_integrity(self) -> dict:
        """Validate integrity of all backups."""

        settings = PostgreSQLBackupSettings(
            db_url="postgresql://localhost/resources",
            backup_dir=self.backup_dir
        )
        tool = PostgreSQLBackupTool(settings)

        backups = tool.list_available_backups()
        invalid_backups = []

        for backup in backups:
            if not tool.validate_backup_integrity(backup.backup_path):
                invalid_backups.append(str(backup.backup_path))

        if invalid_backups:
            return {
                "status": "CRITICAL",
                "message": f"Found {len(invalid_backups)} invalid backups",
                "invalid_backups": invalid_backups,
                "action_required": True
            }

        return {
            "status": "OK",
            "message": f"All {len(backups)} backups are valid",
            "action_required": False
        }

    def check_disk_space(self, min_free_gb: float = 10.0) -> dict:
        """Check available disk space for backups."""

        import shutil
        stats = shutil.disk_usage(self.backup_dir)
        free_gb = stats.free / (1024**3)

        if free_gb < min_free_gb:
            return {
                "status": "WARNING",
                "message": f"Low disk space: {free_gb:.1f} GB free",
                "free_gb": free_gb,
                "action_required": True
            }

        return {
            "status": "OK",
            "message": f"Sufficient disk space: {free_gb:.1f} GB free",
            "free_gb": free_gb,
            "action_required": False
        }

    def generate_health_report(self) -> dict:
        """Generate comprehensive backup health report."""

        report = {
            "timestamp": datetime.now().isoformat(),
            "checks": {
                "freshness": self.check_backup_freshness(),
                "integrity": self.check_backup_integrity(),
                "disk_space": self.check_disk_space()
            },
            "overall_status": "OK"
        }

        # Determine overall status
        for check in report["checks"].values():
            if check["status"] == "CRITICAL":
                report["overall_status"] = "CRITICAL"
                break
            elif check["status"] == "WARNING":
                report["overall_status"] = "WARNING"

        return report

# Usage
monitor = BackupHealthMonitor(Path("/backups/production"))
report = monitor.generate_health_report()

print(f"Backup Health Report - {report['timestamp']}")
print(f"Overall Status: {report['overall_status']}")
print()

for check_name, result in report["checks"].items():
    print(f"{check_name.upper()}: {result['status']}")
    print(f"  {result['message']}")
    if result["action_required"]:
        print("  ⚠️  ACTION REQUIRED")
    print()

# Send alert if action required
if report["overall_status"] in ["WARNING", "CRITICAL"]:
    send_alert_to_ops_team(report)
```

## Next Steps

After reviewing these examples:

1. **Choose your backup strategy** based on your requirements
2. **Set up automated backups** using cron or similar scheduler
3. **Test your disaster recovery** procedure in a safe environment
4. **Monitor backup health** regularly
5. **Document your specific backup procedures** for your team

For more information, see:
- [Backup Tools Documentation](./BACKUP_TOOLS.md)
- [Migration Tools Documentation](./MIGRATIONS.md)

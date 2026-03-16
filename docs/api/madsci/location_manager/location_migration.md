Module madsci.location_manager.location_migration
=================================================
One-time migration tool for Location Manager: 0.7.1 Redis → MongoDB.

The 0.7.1 system stores locations in Redis indexed by location_id under key
``madsci:location_manager:{manager_id}:locations``. This tool reads from that
old format, maps fields to the current ``Location`` model, and writes to MongoDB.

Usage (CLI)::

    python -m madsci.location_manager.location_migration         --redis-host localhost --redis-port 6379         --mongo-url mongodb://localhost:27017/         --manager-id <MANAGER_ID>

Functions
---------

`main() ‑> None`
:   CLI entry point for manual migration.

Classes
-------

`LocationMigrator(redis_handler: RedisHandler, mongo_handler: MongoHandler, manager_id: str, event_logger: Optional[Any] = None)`
:   Migrates locations from 0.7.1 Redis format to MongoDB.
    
    Initialize the migrator with Redis/MongoDB handlers and manager ID.

    ### Methods

    `migrate_from_redis(self) ‑> madsci.location_manager.location_migration.MigrationResult`
    :   Read old Redis data, transform, and write to MongoDB.
        
        The 0.7.1 format stores locations in a Redis dict at
        ``madsci:location_manager:{manager_id}:locations`` keyed by
        location name (or in some older deployments, location_id).

    `migrate_from_settings(self, locations: list[dict[str, Any]]) ‑> madsci.location_manager.location_migration.MigrationResult`
    :   Import from old inline settings format (LocationDefinition list).

`MigrationResult(migrated: int = 0, skipped: int = 0, errors: list[str] = <factory>)`
:   Summary of a migration run.

    ### Instance variables

    `errors: list[str]`
    :

    `migrated: int`
    :

    `skipped: int`
    :

`SchemaUpgrader(mongo_handler: MongoHandler, event_logger: Optional[Any] = None)`
:   Handles schema upgrades for the Location Manager MongoDB.
    
    Initialize the schema upgrader.

    ### Methods

    `upgrade_1_to_2(self) ‑> madsci.location_manager.location_migration.MigrationResult`
    :   Upgrade schema from 1.0.0 to 2.0.0.
        
        Additive only: creates new collections (representation_templates,
        location_templates) and their indexes. Existing locations data is
        not modified. Idempotent — safe to run multiple times.
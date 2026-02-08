Module madsci.common.types.mongodb_migration_types
==================================================
"MongoDB migration configuration types.

Classes
-------

`CollectionDefinition(**data: Any)`
:   MongoDB collection definition.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * pydantic.main.BaseModel

    ### Class variables

    `description: str | None`
    :

    `indexes: List[madsci.common.types.mongodb_migration_types.IndexDefinition]`
    :

    `model_config`
    :

    ### Static methods

    `validate_indexes(v: Any) ‑> List[madsci.common.types.mongodb_migration_types.IndexDefinition]`
    :   Validate and convert indexes from various formats.

    ### Methods

    `to_schema_dict(self) ‑> Dict[str, Any]`
    :   Convert to schema.json format.

`IndexDefinition(**data: Any)`
:   MongoDB index definition.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * pydantic.main.BaseModel

    ### Class variables

    `background: bool`
    :

    `description: str | None`
    :

    `keys: List[madsci.common.types.mongodb_migration_types.IndexKey]`
    :

    `model_config`
    :

    `name: str`
    :

    `unique: bool`
    :

    ### Static methods

    `validate_keys(v: Any) ‑> List[madsci.common.types.mongodb_migration_types.IndexKey]`
    :   Validate and convert keys from various formats.

    ### Methods

    `get_keys_as_tuples(self) ‑> List[tuple[str, int]]`
    :   Get index keys as tuples for MongoDB operations.

    `to_mongo_format(self) ‑> Dict[str, Any]`
    :   Convert to MongoDB index creation format.

    `to_schema_dict(self) ‑> Dict[str, Any]`
    :   Convert to schema.json format.

`IndexKey(**data: Any)`
:   Represents a single key in a MongoDB index.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * pydantic.main.BaseModel

    ### Class variables

    `direction: int`
    :

    `field: str`
    :

    `model_config`
    :

    ### Static methods

    `from_list(key_list: List[Any]) ‑> madsci.common.types.mongodb_migration_types.IndexKey`
    :   Create IndexKey from list format [field, direction].

    `validate_direction(v: int) ‑> int`
    :   Validate index direction is 1 or -1.

    ### Methods

    `to_list(self) ‑> list`
    :   Convert to list format for schema.json.

    `to_tuple(self) ‑> tuple[str, int]`
    :   Convert to tuple format for MongoDB operations.

`MongoDBMigrationSettings(**values: Any)`
:   Configuration settings for MongoDB migration operations.

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseSettings
    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Class variables

    `backup_dir: str | pathlib.Path`
    :

    `backup_only: bool`
    :

    `check_version: bool`
    :

    `database: str | None`
    :

    `mongo_db_url: pydantic.networks.AnyUrl`
    :

    `restore_from: str | pathlib.Path | None`
    :

    `schema_file: str | pathlib.Path | None`
    :

    `target_version: str | None`
    :

    `validate_schema: bool`
    :

    ### Methods

    `get_effective_schema_file_path(self) ‑> pathlib.Path`
    :   Get the effective schema file path as a Path object.

`MongoDBSchema(**data: Any)`
:   Complete MongoDB database schema definition using Pydantic models

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * pydantic.main.BaseModel

    ### Class variables

    `collections: Dict[str, madsci.common.types.mongodb_migration_types.CollectionDefinition]`
    :

    `database: str`
    :

    `description: str | None`
    :

    `model_config`
    :

    `schema_version: pydantic_extra_types.semantic_version.SemanticVersion`
    :

    ### Static methods

    `from_file(file_path: str) ‑> madsci.common.types.mongodb_migration_types.MongoDBSchema`
    :   Load schema from a JSON file.

    `from_mongodb_database(database_name: str, mongo_client: Any, schema_version: str = '0.0.0') ‑> madsci.common.types.mongodb_migration_types.MongoDBSchema`
    :   Extract schema from an existing MongoDB database.

        Args:
            database_name: Name of the database
            mongo_client: PyMongo MongoClient instance
            schema_version: Version to assign to the extracted schema

        Returns:
            MongoDBSchema instance representing the database's current schema

    `validate_collections(v: Any) ‑> Dict[str, madsci.common.types.mongodb_migration_types.CollectionDefinition]`
    :   Validate and convert collections from various formats.

    `validate_version(v: Any) ‑> pydantic_extra_types.semantic_version.SemanticVersion`
    :   Validate and parse semantic version.

    ### Methods

    `compare_with_database_schema(self, db_schema: MongoDBSchema) ‑> Dict[str, Any]`
    :   Compare this schema with a database schema and return differences.

        Returns:
            Dictionary with differences:
            - missing_collections: Collections in expected schema but not in DB
            - extra_collections: Collections in DB but not in expected schema
            - collection_differences: Per-collection index differences

    `get_collection(self, collection_name: str) ‑> madsci.common.types.mongodb_migration_types.CollectionDefinition | None`
    :   Get collection definition by name.

    `get_collection_names(self) ‑> List[str]`
    :   Get list of collection names.

    `has_collection(self, collection_name: str) ‑> bool`
    :   Check if collection exists in schema.

    `to_file(self, file_path: str, indent: int = 2) ‑> None`
    :   Save schema to a JSON file.

    `to_schema_dict(self) ‑> Dict[str, Any]`
    :   Convert to schema.json format.

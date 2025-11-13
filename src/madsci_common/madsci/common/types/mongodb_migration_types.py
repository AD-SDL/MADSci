""" "MongoDB migration configuration types."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from madsci.common.types.base_types import MadsciBaseSettings, PathLike
from pydantic import AliasChoices, AnyUrl, BaseModel, Field, field_validator
from pydantic_extra_types.semantic_version import SemanticVersion


class MongoDBMigrationSettings(
    MadsciBaseSettings,
    env_file=(".env", "mongodb.env", "migration.env"),
    toml_file=("settings.toml", "mongodb.settings.toml", "migration.settings.toml"),
    yaml_file=("settings.yaml", "mongodb.settings.yaml", "migration.settings.yaml"),
    json_file=("settings.json", "mongodb.settings.json", "migration.settings.json"),
    env_prefix="MONGODB_MIGRATION_",
):
    """Configuration settings for MongoDB migration operations."""

    mongo_db_url: AnyUrl = Field(
        default=AnyUrl("mongodb://localhost:27017"),
        title="MongoDB URL",
        description="MongoDB connection URL (e.g., mongodb://localhost:27017). "
        "Defaults to localhost MongoDB instance.",
        validation_alias=AliasChoices(
            "mongo_db_url", "MONGODB_URL", "MONGO_URL", "DATABASE_URL", "db_url"
        ),
    )
    database: str = Field(
        title="Database Name",
        description="Database name to migrate (e.g., madsci_events, madsci_data)",
    )
    schema_file: PathLike = Field(
        title="Schema File Path",
        description="Explicit path to schema.json (required).",
        validation_alias=AliasChoices("schema_file", "MONGODB_SCHEMA_FILE"),
    )
    backup_dir: PathLike = Field(
        default=Path(".madsci/mongodb/backups"),
        title="Backup Directory",
        description="Directory where database backups will be stored. Relative to CWD unless absolute is provided.",
    )
    target_version: Optional[str] = Field(
        default=None,
        title="Target Version",
        description="Target version to migrate to (defaults to current MADSci version)",
    )
    backup_only: bool = Field(
        default=False,
        title="Backup Only",
        description="Only create a backup, do not run migration",
    )
    restore_from: Optional[PathLike] = Field(
        default=None,
        title="Restore From",
        description="Restore from specified backup directory instead of migrating",
    )
    check_version: bool = Field(
        default=False,
        title="Check Version Only",
        description="Only check version compatibility, do not migrate",
    )
    validate_schema: bool = Field(
        default=False,
        title="Validate Schema",
        description="Validate current database schema against expected schema",
    )

    @field_validator("backup_dir", mode="before")
    @classmethod
    def _normalize_backup_dir(cls, v: Any) -> Optional[str]:
        """Normalize backup directory path."""
        # do NOT expanduser here; just coerce to str/Path-like
        return str(v) if v is not None else v

    def get_effective_schema_file_path(self) -> Path:
        """Get the effective schema file path as a Path object."""
        p = Path(self.schema_file)
        if not p.exists():
            raise FileNotFoundError(f"Schema file not found: {p}")
        return p


class IndexKey(BaseModel):
    """Represents a single key in a MongoDB index."""

    field: str = Field(description="Field name to index")
    direction: int = Field(
        description="Sort direction: 1 for ascending, -1 for descending"
    )

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v: int) -> int:
        """Validate index direction is 1 or -1."""
        if v not in (1, -1):
            raise ValueError("Index direction must be 1 (ascending) or -1 (descending)")
        return v

    def to_tuple(self) -> tuple[str, int]:
        """Convert to tuple format for MongoDB operations."""
        return (self.field, self.direction)

    def to_list(self) -> list:
        """Convert to list format for schema.json."""
        return [self.field, self.direction]

    @classmethod
    def from_list(cls, key_list: List[Any]) -> "IndexKey":
        """Create IndexKey from list format [field, direction]."""
        if len(key_list) != 2:
            raise ValueError(
                f"Index key must have exactly 2 elements, got {len(key_list)}"
            )
        return cls(field=key_list[0], direction=key_list[1])


class IndexDefinition(BaseModel):
    """MongoDB index definition."""

    keys: List[IndexKey] = Field(description="List of index keys with directions")
    name: str = Field(description="Name of the index")
    unique: bool = Field(
        default=False, description="Whether the index enforces uniqueness"
    )
    background: bool = Field(
        default=True, description="Whether to build index in background"
    )
    description: Optional[str] = Field(
        default=None, description="Human-readable description of the index"
    )

    @field_validator("keys", mode="before")
    @classmethod
    def validate_keys(cls, v: Any) -> List[IndexKey]:
        """Validate and convert keys from various formats."""
        if not v:
            raise ValueError("Index must have at least one key")

        if isinstance(v, list):
            result = []
            for item in v:
                if isinstance(item, IndexKey):
                    result.append(item)
                elif isinstance(item, (list, tuple)) and len(item) == 2:
                    result.append(IndexKey.from_list(item))
                elif isinstance(item, dict):
                    result.append(IndexKey(**item))
                else:
                    raise ValueError(f"Invalid key format: {item}")
            return result

        raise ValueError(f"Keys must be a list, got {type(v)}")

    def to_mongo_format(self) -> Dict[str, Any]:
        """Convert to MongoDB index creation format."""
        return {
            "name": self.name,
            "unique": self.unique,
            "background": self.background,
        }

    def to_schema_dict(self) -> Dict[str, Any]:
        """Convert to schema.json format."""
        result = {
            "keys": [key.to_list() for key in self.keys],
            "name": self.name,
            "background": self.background,
        }
        if self.unique:
            result["unique"] = True
        if self.description:
            result["description"] = self.description
        return result

    def get_keys_as_tuples(self) -> List[tuple[str, int]]:
        """Get index keys as tuples for MongoDB operations."""
        return [key.to_tuple() for key in self.keys]


class CollectionDefinition(BaseModel):
    """MongoDB collection definition."""

    description: Optional[str] = Field(
        default=None, description="Human-readable description of the collection"
    )
    indexes: List[IndexDefinition] = Field(
        default_factory=list, description="List of indexes for this collection"
    )

    @field_validator("indexes", mode="before")
    @classmethod
    def validate_indexes(cls, v: Any) -> List[IndexDefinition]:
        """Validate and convert indexes from various formats."""
        if v is None:
            return []

        if isinstance(v, list):
            result = []
            for item in v:
                if isinstance(item, IndexDefinition):
                    result.append(item)
                elif isinstance(item, dict):
                    result.append(IndexDefinition(**item))
                else:
                    raise ValueError(f"Invalid index format: {item}")
            return result

        raise ValueError(f"Indexes must be a list, got {type(v)}")

    def to_schema_dict(self) -> Dict[str, Any]:
        """Convert to schema.json format."""
        result = {}
        if self.description:
            result["description"] = self.description
        if self.indexes:
            result["indexes"] = [idx.to_schema_dict() for idx in self.indexes]
        return result


class MongoDBSchema(BaseModel):
    """Complete MongoDB database schema definition using Pydantic models"""

    database: str = Field(description="Database name")
    schema_version: SemanticVersion = Field(
        description="Schema version using semantic versioning"
    )
    description: Optional[str] = Field(
        default=None, description="Human-readable description of the schema"
    )
    collections: Dict[str, CollectionDefinition] = Field(
        default_factory=dict,
        description="Dictionary of collection definitions keyed by collection name",
    )

    @field_validator("schema_version", mode="before")
    @classmethod
    def validate_version(cls, v: Any) -> SemanticVersion:
        """Validate and parse semantic version."""
        if isinstance(v, SemanticVersion):
            return v
        if isinstance(v, str):
            return SemanticVersion.parse(v)
        raise ValueError(f"Invalid schema_version format: {v}")

    @field_validator("collections", mode="before")
    @classmethod
    def validate_collections(cls, v: Any) -> Dict[str, CollectionDefinition]:
        """Validate and convert collections from various formats."""
        if v is None:
            return {}

        if isinstance(v, dict):
            result = {}
            for name, definition in v.items():
                if isinstance(definition, CollectionDefinition):
                    result[name] = definition
                elif isinstance(definition, dict):
                    result[name] = CollectionDefinition(**definition)
                else:
                    raise ValueError(
                        f"Invalid collection definition for {name}: {definition}"
                    )
            return result

        raise ValueError(f"Collections must be a dict, got {type(v)}")

    def to_schema_dict(self) -> Dict[str, Any]:
        """Convert to schema.json format."""
        result = {
            "database": self.database,
            "schema_version": str(self.schema_version),
        }
        if self.description:
            result["description"] = self.description
        if self.collections:
            result["collections"] = {
                name: coll.to_schema_dict() for name, coll in self.collections.items()
            }
        return result

    @classmethod
    def from_file(cls, file_path: str) -> "MongoDBSchema":
        """Load schema from a JSON file."""
        import json  # noqa
        from pathlib import Path  # noqa

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Schema file not found: {path}")

        with open(path) as f:  # noqa
            data = json.load(f)

        return cls(**data)

    def to_file(self, file_path: str, indent: int = 2) -> None:
        """Save schema to a JSON file."""
        import json  # noqa
        from pathlib import Path  # noqa

        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:  # noqa
            json.dump(self.to_schema_dict(), f, indent=indent)

    def get_collection_names(self) -> List[str]:
        """Get list of collection names."""
        return list(self.collections.keys())

    def has_collection(self, collection_name: str) -> bool:
        """Check if collection exists in schema."""
        return collection_name in self.collections

    def get_collection(self, collection_name: str) -> Optional[CollectionDefinition]:
        """Get collection definition by name."""
        return self.collections.get(collection_name)

    def compare_with_database_schema(
        self, db_schema: "MongoDBSchema"
    ) -> Dict[str, Any]:
        """
        Compare this schema with a database schema and return differences.

        Returns:
            Dictionary with differences:
            - missing_collections: Collections in expected schema but not in DB
            - extra_collections: Collections in DB but not in expected schema
            - collection_differences: Per-collection index differences
        """
        differences = {
            "missing_collections": [],
            "extra_collections": [],
            "collection_differences": {},
        }

        expected_collections = set(self.collections.keys())
        db_collections = set(db_schema.collections.keys())

        differences["missing_collections"] = sorted(
            expected_collections - db_collections
        )
        differences["extra_collections"] = sorted(db_collections - expected_collections)

        # Check collections that exist in both
        common_collections = expected_collections & db_collections
        for coll_name in common_collections:
            expected_coll = self.collections[coll_name]
            db_coll = db_schema.collections[coll_name]

            expected_indexes = {idx.name: idx for idx in expected_coll.indexes}
            db_indexes = {idx.name: idx for idx in db_coll.indexes}

            coll_diff = {
                "missing_indexes": [],
                "extra_indexes": [],
                "different_indexes": [],
            }

            missing_idx_names = set(expected_indexes.keys()) - set(db_indexes.keys())
            extra_idx_names = set(db_indexes.keys()) - set(expected_indexes.keys())
            common_idx_names = set(expected_indexes.keys()) & set(db_indexes.keys())

            coll_diff["missing_indexes"] = sorted(missing_idx_names)
            coll_diff["extra_indexes"] = sorted(extra_idx_names)

            # Check if common indexes are identical
            for idx_name in common_idx_names:
                expected_idx = expected_indexes[idx_name]
                db_idx = db_indexes[idx_name]

                if (
                    expected_idx.get_keys_as_tuples() != db_idx.get_keys_as_tuples()
                    or expected_idx.unique != db_idx.unique
                ):
                    coll_diff["different_indexes"].append(
                        {
                            "name": idx_name,
                            "expected": expected_idx.to_schema_dict(),
                            "actual": db_idx.to_schema_dict(),
                        }
                    )

            if any(coll_diff.values()):
                differences["collection_differences"][coll_name] = coll_diff

        return differences

    @classmethod
    def from_mongodb_database(
        cls, database_name: str, mongo_client: Any, schema_version: str = "0.0.0"
    ) -> "MongoDBSchema":
        """
        Extract schema from an existing MongoDB database.

        Args:
            database_name: Name of the database
            mongo_client: PyMongo MongoClient instance
            schema_version: Version to assign to the extracted schema

        Returns:
            MongoDBSchema instance representing the database's current schema
        """
        database = mongo_client[database_name]
        collections = {}

        collection_names = [
            name
            for name in database.list_collection_names()
            if not name.startswith("system.")
        ]

        for coll_name in collection_names:
            collection = database[coll_name]
            indexes = []

            for index in collection.list_indexes():
                if index["name"] == "_id_":
                    continue

                keys = [
                    IndexKey(field=field, direction=direction)
                    for field, direction in index["key"].items()
                ]

                index_def = IndexDefinition(
                    keys=keys,
                    name=index["name"],
                    unique=index.get("unique", False),
                    background=index.get("background", False),
                )
                indexes.append(index_def)

            collections[coll_name] = CollectionDefinition(indexes=indexes)

        return cls(
            database=database_name,
            schema_version=schema_version,
            collections=collections,
        )

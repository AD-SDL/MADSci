Module madsci.client.cli.commands.add
=====================================
CLI command for adding components to existing module projects.

Functions
---------

`detect_module_description(target_dir: Path, data: dict[str, Any] | None = None) ‑> str | None`
:   Detect module description from pyproject.toml in target_dir.

`detect_module_name(target_dir: Path, data: dict[str, Any] | None = None) ‑> str | None`
:   Detect module_name from pyproject.toml in target_dir.
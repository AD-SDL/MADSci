"""
Template registry for MADSci.

This module provides discovery and management of templates from multiple sources:
bundled templates, user templates, and remote templates.
"""

import importlib.resources
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from madsci.common.templates.engine import TemplateEngine, TemplateError
from madsci.common.types.template_types import (
    TemplateCategory,
    TemplateInfo,
    TemplateManifest,
)

logger = logging.getLogger(__name__)


class TemplateNotFoundError(Exception):
    """Template not found in registry."""


class TemplateRegistry:
    """Registry for discovering and loading templates.

    Templates can come from three sources:
    1. Bundled templates (shipped with MADSci)
    2. User templates (~/.madsci/templates/)
    3. Remote templates (installed from git repos)

    Example:
        registry = TemplateRegistry()

        # List all templates
        templates = registry.list_templates()

        # Filter by category
        module_templates = registry.list_templates(category="module")

        # Get a specific template
        engine = registry.get_template("module/device")

        # Install from remote
        registry.install_template("https://github.com/org/my-templates.git")
    """

    def __init__(
        self,
        user_template_dir: Optional[Path] = None,
    ) -> None:
        """Initialize the template registry.

        Args:
            user_template_dir: Directory for user templates.
                              Defaults to ~/.madsci/templates/.
        """
        self.user_template_dir = user_template_dir or self._default_user_dir()

    @staticmethod
    def _default_user_dir() -> Path:
        """Get default user template directory.

        Returns:
            Path to ~/.madsci/templates/
        """
        return Path.home() / ".madsci" / "templates"

    def _bundled_template_dir(self) -> Optional[Path]:
        """Get bundled template directory from package.

        Returns:
            Path to bundled templates, or None if not found.
        """
        try:
            # Use importlib.resources.files() directly — it returns a
            # Traversable that, for on-disk packages, is already a real
            # Path.  This avoids the as_file() context-manager whose
            # temporary path can become invalid after the ``with`` exits.
            resource = importlib.resources.files("madsci.common") / "bundled_templates"
            path = Path(str(resource))
            if path.exists():
                return path
        except (TypeError, FileNotFoundError):
            pass
        return None

    def list_templates(
        self,
        category: Optional[TemplateCategory] = None,
        tags: Optional[list[str]] = None,
    ) -> list[TemplateInfo]:
        """List available templates.

        Args:
            category: Filter by category (module, node, experiment, etc.).
            tags: Filter by tags (templates matching any tag are included).

        Returns:
            List of template info objects.
        """
        templates: list[TemplateInfo] = []

        # Scan bundled templates
        bundled_dir = self._bundled_template_dir()
        if bundled_dir and bundled_dir.exists():
            templates.extend(self._scan_directory(bundled_dir, "bundled"))

        # Scan user templates
        if self.user_template_dir.exists():
            templates.extend(self._scan_directory(self.user_template_dir, "user"))

        # Apply filters
        if category:
            templates = [t for t in templates if t.category == category]

        if tags:
            templates = [t for t in templates if any(tag in t.tags for tag in tags)]

        return templates

    def _scan_directory(self, base_dir: Path, source: str) -> list[TemplateInfo]:
        """Scan a directory for templates.

        Args:
            base_dir: Directory to scan.
            source: Source identifier (bundled, user, etc.).

        Returns:
            List of template info found.
        """
        templates: list[TemplateInfo] = []

        for category_dir in base_dir.iterdir():
            if not category_dir.is_dir():
                continue

            for template_dir in category_dir.iterdir():
                if not template_dir.is_dir():
                    continue

                manifest_path = template_dir / "template.yaml"
                if not manifest_path.exists():
                    continue

                try:
                    manifest = TemplateManifest.from_yaml(manifest_path)
                    templates.append(
                        TemplateInfo(
                            id=f"{category_dir.name}/{template_dir.name}",
                            name=manifest.name,
                            version=manifest.version,
                            description=manifest.description,
                            category=manifest.category,
                            tags=manifest.tags,
                            source=source,
                            path=template_dir,
                        )
                    )
                except Exception as e:
                    logger.debug(
                        "Skipping invalid template: template_dir=%s error=%s",
                        str(template_dir),
                        str(e),
                    )

        return templates

    @staticmethod
    def _validate_path_component(component: str) -> None:
        """Reject path components that could cause path traversal.

        Raises:
            ValueError: If the component contains ``..`` or path separators.
        """
        if ".." in component or "/" in component or "\\" in component:
            raise ValueError(
                f"Invalid path component: {component!r} (path traversal not allowed)"
            )

    def get_template(self, template_id: str) -> TemplateEngine:
        """Get a template engine by ID.

        Args:
            template_id: Template identifier (e.g., "module/device").

        Returns:
            TemplateEngine for the template.

        Raises:
            TemplateNotFoundError: If template is not found.
            ValueError: If template_id format is invalid.
        """
        # Parse template ID
        parts = template_id.split("/")
        if len(parts) != 2:
            raise ValueError(
                f"Invalid template ID: {template_id}. Expected format: category/name"
            )

        category, name = parts
        self._validate_path_component(category)
        self._validate_path_component(name)

        # Check user templates first (sandboxed — user-installed content)
        user_path = self.user_template_dir / category / name
        if user_path.exists() and (user_path / "template.yaml").exists():
            return TemplateEngine(user_path, sandboxed=True)

        # Check bundled templates (trusted, no sandbox)
        bundled_dir = self._bundled_template_dir()
        if bundled_dir:
            bundled_path = bundled_dir / category / name
            if bundled_path.exists() and (bundled_path / "template.yaml").exists():
                return TemplateEngine(bundled_path)

        raise TemplateNotFoundError(f"Template not found: {template_id}")

    def install_template(
        self,
        source: str,
        name: Optional[str] = None,
        local: bool = False,
    ) -> Path:
        """Install a template from a source.

        Args:
            source: Path to template directory or git URL.
            name: Optional name override for the installed template.
            local: If True, treat source as local path (for air-gapped environments).

        Returns:
            Path to installed template.

        Raises:
            TemplateNotFoundError: If source path doesn't exist.
            TemplateError: If template is invalid or installation fails.
        """
        source_path = Path(source)

        if local or source_path.exists():
            # Local directory installation (supports air-gapped environments)
            if not source_path.exists():
                raise TemplateNotFoundError(f"Local path not found: {source}")

            manifest_path = source_path / "template.yaml"
            if not manifest_path.exists():
                raise TemplateError(f"No template.yaml found in {source}")

            manifest = TemplateManifest.from_yaml(manifest_path)
            template_name = name or f"{manifest.category.value}/{source_path.name}"

            # Validate path components to prevent traversal
            for component in template_name.split("/"):
                self._validate_path_component(component)

            dest_path = self.user_template_dir / template_name
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy template to user directory
            if dest_path.exists():
                shutil.rmtree(dest_path)
            shutil.copytree(source_path, dest_path)

            logger.info(
                "Installed template: source=%s dest_path=%s", source, str(dest_path)
            )
            return dest_path

        if source.startswith(("http://", "https://", "git@")):
            # Git repository installation (requires network)
            with tempfile.TemporaryDirectory() as tmpdir:
                try:
                    subprocess.run(  # noqa: S603
                        ["git", "clone", "--depth", "1", source, tmpdir],  # noqa: S607
                        check=True,
                        capture_output=True,
                    )
                except subprocess.CalledProcessError as e:
                    raise TemplateError(
                        f"Failed to clone template repository: {e.stderr.decode() if e.stderr else str(e)}"
                    ) from e

                # Recursively install from cloned directory
                return self.install_template(tmpdir, name=name, local=True)

        else:
            raise TemplateError(f"Unknown source format: {source}")

    def uninstall_template(self, template_id: str) -> bool:
        """Uninstall a user-installed template.

        Args:
            template_id: Template identifier to uninstall.

        Returns:
            True if template was uninstalled, False if not found.

        Note:
            Bundled templates cannot be uninstalled.
        """
        parts = template_id.split("/")
        if len(parts) != 2:
            raise ValueError(f"Invalid template ID: {template_id}")

        category, name = parts
        template_path = self.user_template_dir / category / name

        if template_path.exists():
            shutil.rmtree(template_path)
            logger.info("Uninstalled template: template_id=%s", template_id)
            return True

        return False

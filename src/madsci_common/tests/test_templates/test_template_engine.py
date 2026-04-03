"""Tests for the MADSci template engine and registry.

These tests validate that the template engine correctly renders templates,
the registry discovers templates, and generated code is valid.
"""

import ast
import importlib
import importlib.resources
import json
import sys
from pathlib import Path

import pytest
import yaml

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ModuleNotFoundError:
        tomllib = None  # type: ignore[assignment]
from madsci.common.templates.engine import (
    TemplateEngine,
    TemplateValidationError,
    camel_case,
    kebab_case,
    pascal_case,
)
from madsci.common.templates.registry import (
    TemplateNotFoundError,
    TemplateRegistry,
)
from madsci.common.types.template_types import (
    TemplateCategory,
)

# --- Shared parametrize data ---

# All templates with render parameters, used by multiple parametrized tests.
TEMPLATE_RENDER_PARAMS: list[tuple[str, dict]] = [
    ("module/basic", {"module_name": "test_gen", "port": 2000}),
    ("module/device", {"module_name": "test_gen", "port": 2000}),
    ("module/camera", {"module_name": "test_gen", "port": 2000}),
    ("module/instrument", {"module_name": "test_gen", "port": 2000}),
    ("module/liquid_handler", {"module_name": "test_gen", "port": 2000}),
    ("module/robot_arm", {"module_name": "test_gen", "port": 2000}),
    ("interface/fake", {"module_name": "test_gen"}),
    ("interface/real", {"module_name": "test_gen"}),
    ("interface/sim", {"module_name": "test_gen"}),
    ("interface/mock", {"module_name": "test_gen"}),
    ("node/basic", {"node_name": "test_gen", "port": 2000}),
    ("experiment/script", {"experiment_name": "test_gen"}),
    ("experiment/tui", {"experiment_name": "test_gen"}),
    ("experiment/node", {"experiment_name": "test_gen", "server_port": 6000}),
    (
        "workflow/basic",
        {"workflow_name": "test_gen", "node_name": "n1", "action_name": "a1"},
    ),
    (
        "workflow/multi_step",
        {
            "workflow_name": "test_gen",
            "node_1_name": "n1",
            "node_1_action": "a1",
            "node_2_name": "n2",
            "node_2_action": "a2",
        },
    ),
    ("lab/minimal", {"lab_name": "test_gen"}),
    ("lab/standard", {"lab_name": "test_gen"}),
    ("lab/distributed", {"lab_name": "test_gen"}),
    ("workcell/basic", {"workcell_name": "test_gen"}),
    ("comm/serial", {"interface_name": "test_gen"}),
    ("comm/socket", {"interface_name": "test_gen"}),
    ("comm/rest", {"interface_name": "test_gen"}),
    ("comm/sdk", {"interface_name": "test_gen"}),
    ("comm/modbus", {"interface_name": "test_gen"}),
    ("addon/docs", {"module_name": "test_gen"}),
    ("addon/drivers", {"module_name": "test_gen"}),
    ("addon/notebooks", {"module_name": "test_gen", "port": 2000}),
    ("addon/gitignore", {"module_name": "test_gen"}),
    ("addon/compose", {"module_name": "test_gen", "port": 2000}),
    (
        "addon/dev_tools",
        {"module_name": "test_gen", "port": 2000, "include_dockerfile": True},
    ),
    (
        "addon/agent_config",
        {"module_name": "test_gen", "include_agent_config": ["claude", "agents"]},
    ),
    (
        "addon/all",
        {
            "module_name": "test_gen",
            "port": 2000,
            "include_agent_config": ["claude", "agents"],
        },
    ),
]

# Deprecated patterns that must not appear in generated Python code.
# Add new entries when APIs are removed or renamed.
DEPRECATED_PYTHON_PATTERNS: list[tuple[str, str]] = [
    ("ActionHandler", "Use @action decorator instead"),
    ("self.node_definition", "Use self.node_info instead"),
    ("NodeDefinition", "Use NodeConfig instead"),
    ("load_definition(", "Definition files were removed in v0.7.0"),
    ("load_or_create_definition(", "Definition files were removed in v0.7.0"),
    ("SquidServer", "Use LabManager from madsci.squid.lab_server instead"),
    (
        "SquidSettings",
        "Use LabManagerSettings from madsci.common.types.lab_types instead",
    ),
    ("create_minio_client", "Use create_object_storage_client instead"),
    ("PyMongoHandler", "Use PyDocumentStorageHandler instead"),
    ("InMemoryMongoHandler", "Use InMemoryDocumentStorageHandler instead"),
]


# --- Filter tests ---


class TestJinja2Filters:
    """Test custom Jinja2 filters."""

    def test_pascal_case_simple(self) -> None:
        assert pascal_case("my_module") == "MyModule"

    def test_pascal_case_multi_word(self) -> None:
        assert pascal_case("my_cool_device") == "MyCoolDevice"

    def test_pascal_case_single_word(self) -> None:
        assert pascal_case("device") == "Device"

    def test_camel_case_simple(self) -> None:
        assert camel_case("my_module") == "myModule"

    def test_camel_case_multi_word(self) -> None:
        assert camel_case("my_cool_device") == "myCoolDevice"

    def test_camel_case_single_word(self) -> None:
        assert camel_case("device") == "device"

    def test_kebab_case_simple(self) -> None:
        assert kebab_case("my_module") == "my-module"

    def test_kebab_case_multi_word(self) -> None:
        assert kebab_case("my_cool_device") == "my-cool-device"

    def test_kebab_case_single_word(self) -> None:
        assert kebab_case("device") == "device"


# --- TemplateRegistry tests ---


class TestTemplateRegistry:
    """Test template discovery and lookup."""

    @pytest.fixture
    def registry(self, tmp_path: Path) -> TemplateRegistry:
        """Create a registry with a non-existent user dir to isolate from system."""
        return TemplateRegistry(user_template_dir=tmp_path / "user_templates")

    def test_list_all_templates(self, registry: TemplateRegistry) -> None:
        """Test listing all bundled templates."""
        templates = registry.list_templates()
        assert len(templates) > 0
        # Check that IDs follow category/name format
        for t in templates:
            assert "/" in t.id
            assert t.source == "bundled"

    def test_list_module_templates(self, registry: TemplateRegistry) -> None:
        """Test filtering templates by module category."""
        templates = registry.list_templates(category=TemplateCategory.MODULE)
        assert len(templates) >= 3  # basic, device, and robot_arm
        for t in templates:
            assert t.category == TemplateCategory.MODULE

    def test_list_experiment_templates(self, registry: TemplateRegistry) -> None:
        """Test filtering templates by experiment category."""
        templates = registry.list_templates(category=TemplateCategory.EXPERIMENT)
        assert len(templates) >= 4  # script, notebook, tui, node
        for t in templates:
            assert t.category == TemplateCategory.EXPERIMENT

    def test_list_workflow_templates(self, registry: TemplateRegistry) -> None:
        """Test filtering templates by workflow category."""
        templates = registry.list_templates(category=TemplateCategory.WORKFLOW)
        assert len(templates) >= 2  # basic and multi_step
        for t in templates:
            assert t.category == TemplateCategory.WORKFLOW

    def test_list_comm_templates(self, registry: TemplateRegistry) -> None:
        """Test filtering templates by comm category."""
        templates = registry.list_templates(category=TemplateCategory.COMM)
        assert len(templates) >= 5  # serial, socket, rest, sdk, modbus
        for t in templates:
            assert t.category == TemplateCategory.COMM

    def test_list_lab_templates(self, registry: TemplateRegistry) -> None:
        """Test filtering templates by lab category."""
        templates = registry.list_templates(category=TemplateCategory.LAB)
        assert len(templates) >= 3  # minimal, standard, distributed
        for t in templates:
            assert t.category == TemplateCategory.LAB

    def test_list_templates_by_tag(self, registry: TemplateRegistry) -> None:
        """Test filtering templates by tag."""
        templates = registry.list_templates(tags=["starter"])
        assert len(templates) > 0
        for t in templates:
            assert "starter" in t.tags

    def test_get_template_basic_module(self, registry: TemplateRegistry) -> None:
        """Test getting a specific template by ID."""
        engine = registry.get_template("module/basic")
        assert isinstance(engine, TemplateEngine)
        assert engine.manifest.name == "Basic Module"

    def test_get_template_device_module(self, registry: TemplateRegistry) -> None:
        """Test getting the device module template."""
        engine = registry.get_template("module/device")
        assert isinstance(engine, TemplateEngine)
        assert engine.manifest.name == "Device Module"

    def test_get_template_camera_module(self, registry: TemplateRegistry) -> None:
        """Test getting the camera module template."""
        engine = registry.get_template("module/camera")
        assert isinstance(engine, TemplateEngine)
        assert engine.manifest.name == "Camera Module"

    def test_get_template_not_found(self, registry: TemplateRegistry) -> None:
        """Test that missing templates raise TemplateNotFoundError."""
        with pytest.raises(TemplateNotFoundError):
            registry.get_template("module/nonexistent")

    def test_get_template_invalid_id(self, registry: TemplateRegistry) -> None:
        """Test that invalid template IDs raise ValueError."""
        with pytest.raises(ValueError, match="Invalid template ID"):
            registry.get_template("invalid_id_no_slash")

    def test_install_local_template(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Test installing a template from a local path."""
        # Create a minimal template
        template_dir = tmp_path / "my_template"
        template_dir.mkdir()
        (template_dir / "template.yaml").write_text(
            'name: "Test Template"\n'
            'version: "1.0.0"\n'
            'description: "A test template"\n'
            'category: "module"\n'
            "tags: []\n"
            "parameters: []\n"
            "files: []\n"
        )

        result = registry.install_template(str(template_dir), local=True)
        assert result.exists()
        assert (result / "template.yaml").exists()

    def test_uninstall_template(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Test uninstalling a user template."""
        # Create a user template
        template_dir = registry.user_template_dir / "module" / "test"
        template_dir.mkdir(parents=True)
        (template_dir / "template.yaml").write_text("name: test\n")

        assert registry.uninstall_template("module/test") is True
        assert not template_dir.exists()

    def test_uninstall_nonexistent_template(self, registry: TemplateRegistry) -> None:
        """Test uninstalling a template that doesn't exist."""
        assert registry.uninstall_template("module/nonexistent") is False


# --- TemplateEngine tests ---


class TestTemplateEngine:
    """Test template loading, validation, and rendering."""

    @pytest.fixture
    def registry(self, tmp_path: Path) -> TemplateRegistry:
        return TemplateRegistry(user_template_dir=tmp_path / "user_templates")

    @pytest.fixture
    def basic_engine(self, registry: TemplateRegistry) -> TemplateEngine:
        """Get the basic module template engine."""
        return registry.get_template("module/basic")

    @pytest.fixture
    def device_engine(self, registry: TemplateRegistry) -> TemplateEngine:
        """Get the device module template engine."""
        return registry.get_template("module/device")

    @pytest.fixture
    def script_engine(self, registry: TemplateRegistry) -> TemplateEngine:
        """Get the script experiment template engine."""
        return registry.get_template("experiment/script")

    @pytest.fixture
    def workflow_engine(self, registry: TemplateRegistry) -> TemplateEngine:
        """Get the basic workflow template engine."""
        return registry.get_template("workflow/basic")

    def test_manifest_loaded(self, basic_engine: TemplateEngine) -> None:
        """Test that manifest is loaded correctly."""
        assert basic_engine.manifest.name == "Basic Module"
        assert basic_engine.manifest.category == TemplateCategory.MODULE
        assert len(basic_engine.manifest.parameters) > 0
        assert len(basic_engine.manifest.files) > 0

    def test_get_default_values(self, basic_engine: TemplateEngine) -> None:
        """Test getting default parameter values."""
        defaults = basic_engine.get_default_values()
        assert "module_name" in defaults
        assert defaults["module_name"] == "my_device"
        assert "port" in defaults
        assert defaults["port"] == 2000

    def test_validate_valid_params(self, basic_engine: TemplateEngine) -> None:
        """Test validation with valid parameters."""
        errors = basic_engine.validate_parameters(
            {
                "module_name": "test_device",
                "module_description": "A test device",
                "port": 3000,
            }
        )
        assert errors == []

    def test_validate_missing_required(self, basic_engine: TemplateEngine) -> None:
        """Test validation with missing required parameter."""
        errors = basic_engine.validate_parameters({"port": 3000})
        assert any("module_name" in e for e in errors)

    def test_validate_invalid_pattern(self, basic_engine: TemplateEngine) -> None:
        """Test validation with invalid pattern."""
        errors = basic_engine.validate_parameters(
            {"module_name": "Invalid-Name!", "port": 3000}
        )
        assert any("pattern" in e for e in errors)

    def test_validate_port_below_min(self, basic_engine: TemplateEngine) -> None:
        """Test validation with port below minimum."""
        errors = basic_engine.validate_parameters({"module_name": "test", "port": 100})
        assert any("minimum" in e.lower() or "below" in e.lower() for e in errors)

    def test_validate_port_above_max(self, basic_engine: TemplateEngine) -> None:
        """Test validation with port above maximum."""
        errors = basic_engine.validate_parameters(
            {"module_name": "test", "port": 70000}
        )
        assert any("maximum" in e.lower() or "above" in e.lower() for e in errors)

    def test_validate_wrong_type(self, basic_engine: TemplateEngine) -> None:
        """Test validation with wrong type."""
        errors = basic_engine.validate_parameters(
            {"module_name": "test", "port": "not_a_number"}
        )
        assert any("number" in e.lower() for e in errors)


# --- Shared directory resolution tests ---


class TestSharedDirectoryResolution:
    """Test the _shared/ directory fallback mechanism."""

    def _make_template(
        self,
        tmp_path: Path,
        files_yaml: str,
        *,
        shared_files: dict[str, str] | None = None,
    ) -> TemplateEngine:
        """Create a minimal template with optional _shared/ directory."""
        template_dir = tmp_path / "bundled" / "category" / "my_template"
        template_dir.mkdir(parents=True)
        manifest = (
            "name: Test Template\nversion: '1.0.0'\ndescription: test\n"
            "category: module\nparameters: []\nfiles:\n" + files_yaml
        )
        (template_dir / "template.yaml").write_text(manifest)

        if shared_files:
            shared_dir = tmp_path / "bundled" / "_shared"
            for rel_path, content in shared_files.items():
                full = shared_dir / rel_path
                full.parent.mkdir(parents=True, exist_ok=True)
                full.write_text(content)

        return TemplateEngine(template_dir)

    def test_shared_file_found_via_fallback(self, tmp_path: Path) -> None:
        """A source file not in template_dir is found in _shared/."""
        engine = self._make_template(
            tmp_path,
            '  - source: "shared.txt"\n    destination: "shared.txt"\n',
            shared_files={"shared.txt": "shared content"},
        )
        output = tmp_path / "output"
        output.mkdir()
        result = engine.render(output_dir=output, parameters={})
        assert (output / "shared.txt").exists()
        assert (output / "shared.txt").read_text() == "shared content"
        assert len(result.files_created) == 1

    def test_shared_jinja_template_found_via_fallback(self, tmp_path: Path) -> None:
        """A .j2 source file not in template_dir is found in _shared/."""
        engine = self._make_template(
            tmp_path,
            '  - source: "greeting.txt.j2"\n    destination: "greeting.txt"\n',
            shared_files={"greeting.txt.j2": "Hello {{ name }}!"},
        )
        output = tmp_path / "output"
        output.mkdir()
        result = engine.render(output_dir=output, parameters={"name": "World"})
        assert (output / "greeting.txt").read_text() == "Hello World!"
        assert len(result.files_created) == 1

    def test_local_file_takes_precedence_over_shared(self, tmp_path: Path) -> None:
        """When a file exists in both template_dir and _shared/, template_dir wins."""
        engine = self._make_template(
            tmp_path,
            '  - source: "config.txt"\n    destination: "config.txt"\n',
            shared_files={"config.txt": "from shared"},
        )
        # Also create the file in the template directory
        (engine.template_dir / "config.txt").write_text("from local")

        output = tmp_path / "output"
        output.mkdir()
        engine.render(output_dir=output, parameters={})
        assert (output / "config.txt").read_text() == "from local"

    def test_local_file_renders_without_shared(self, tmp_path: Path) -> None:
        """Engine renders local files correctly regardless of _shared/ presence."""
        engine = self._make_template(
            tmp_path,
            '  - source: "local.txt"\n    destination: "local.txt"\n',
        )
        # Create the file in the template directory
        (engine.template_dir / "local.txt").write_text("local only")

        output = tmp_path / "output"
        output.mkdir()
        engine.render(output_dir=output, parameters={})
        assert (output / "local.txt").read_text() == "local only"

    def test_shared_dir_with_subdirectory(self, tmp_path: Path) -> None:
        """Shared files in subdirectories are resolved correctly."""
        engine = self._make_template(
            tmp_path,
            '  - source: "docs/README.md"\n    destination: "docs/README.md"\n',
            shared_files={"docs/README.md": "# Documentation"},
        )
        output = tmp_path / "output"
        output.mkdir()
        engine.render(output_dir=output, parameters={})
        assert (output / "docs" / "README.md").read_text() == "# Documentation"

    def test_dry_run_with_shared_files(self, tmp_path: Path) -> None:
        """Dry run reports shared files without creating them."""
        engine = self._make_template(
            tmp_path,
            '  - source: "shared.txt"\n    destination: "shared.txt"\n',
            shared_files={"shared.txt": "content"},
        )
        output = tmp_path / "output"
        output.mkdir()
        result = engine.render(output_dir=output, parameters={}, dry_run=True)
        assert len(result.files_created) == 1
        assert not (output / "shared.txt").exists()


# --- Template rendering tests ---


class TestTemplateRendering:
    """Test that templates render correctly and produce valid code."""

    @pytest.fixture
    def registry(self, tmp_path: Path) -> TemplateRegistry:
        return TemplateRegistry(user_template_dir=tmp_path / "user_templates")

    def test_render_basic_module_dry_run(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Test dry-run rendering of basic module template."""
        engine = registry.get_template("module/basic")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = engine.render(
            output_dir=output_dir,
            parameters={"module_name": "test_mod", "port": 2000},
            dry_run=True,
        )

        assert len(result.files_created) > 0
        assert result.template_name == "Basic Module"
        # Dry run should not create files
        for f in result.files_created:
            assert not f.exists()

    def test_render_basic_module(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Test full rendering of basic module template."""
        engine = registry.get_template("module/basic")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = engine.render(
            output_dir=output_dir,
            parameters={"module_name": "test_mod", "port": 2000},
        )

        assert len(result.files_created) > 0
        # Verify files were actually created
        for f in result.files_created:
            assert f.exists(), f"Expected file to exist: {f}"

    def test_render_basic_module_python_syntax(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Test that generated Python files have valid syntax."""
        engine = registry.get_template("module/basic")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = engine.render(
            output_dir=output_dir,
            parameters={"module_name": "test_mod", "port": 2000},
        )

        for f in result.files_created:
            if f.suffix == ".py":
                content = f.read_text()
                # Verify Python syntax is valid
                try:
                    ast.parse(content)
                except SyntaxError as e:
                    pytest.fail(f"Invalid Python syntax in {f}: {e}")

    def test_render_device_module(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Test rendering of device module template."""
        engine = registry.get_template("module/device")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = engine.render(
            output_dir=output_dir,
            parameters={"module_name": "my_sensor", "port": 3000},
        )

        assert len(result.files_created) > 0
        # Verify key files exist
        file_names = [f.name for f in result.files_created]
        assert "my_sensor_rest_node.py" in file_names
        assert "my_sensor_interface.py" in file_names
        assert "my_sensor_fake_interface.py" in file_names
        assert "my_sensor_types.py" in file_names

    def test_render_device_module_python_syntax(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Test that device module generates valid Python."""
        engine = registry.get_template("module/device")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = engine.render(
            output_dir=output_dir,
            parameters={"module_name": "my_sensor", "port": 3000},
        )

        for f in result.files_created:
            if f.suffix == ".py":
                content = f.read_text()
                try:
                    ast.parse(content)
                except SyntaxError as e:
                    pytest.fail(f"Invalid Python syntax in {f}: {e}")

    def test_render_robot_arm_module(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Test rendering of robot arm module template."""
        engine = registry.get_template("module/robot_arm")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = engine.render(
            output_dir=output_dir,
            parameters={"module_name": "my_arm", "port": 3000},
        )

        assert len(result.files_created) > 0
        # Verify key files exist
        file_names = [f.name for f in result.files_created]
        assert "my_arm_rest_node.py" in file_names
        assert "my_arm_interface.py" in file_names
        assert "my_arm_fake_interface.py" in file_names
        assert "my_arm_types.py" in file_names
        assert "test_my_arm_interface.py" in file_names

    def test_render_robot_arm_module_python_syntax(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Test that robot arm module generates valid Python."""
        engine = registry.get_template("module/robot_arm")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = engine.render(
            output_dir=output_dir,
            parameters={"module_name": "my_arm", "port": 3000},
        )

        for f in result.files_created:
            if f.suffix == ".py":
                content = f.read_text()
                try:
                    ast.parse(content)
                except SyntaxError as e:
                    pytest.fail(f"Invalid Python syntax in {f}: {e}")

    def test_render_robot_arm_module_content(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Test that robot arm module content has correct class names and actions."""
        engine = registry.get_template("module/robot_arm")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = engine.render(
            output_dir=output_dir,
            parameters={"module_name": "my_arm", "port": 3000},
        )

        # Check types file for robot arm specific types
        types_file = None
        for f in result.files_created:
            if f.name == "my_arm_types.py":
                types_file = f
                break
        assert types_file is not None
        types_content = types_file.read_text()
        assert "MyArmNodeConfig" in types_content
        assert "MyArmInterfaceConfig" in types_content
        assert "MyArmPosition" in types_content
        assert "MyArmResult" in types_content
        assert "default_speed" in types_content
        assert "workspace_bounds" in types_content

        # Check interface file for robot arm operations
        interface_file = None
        for f in result.files_created:
            if f.name == "my_arm_interface.py":
                interface_file = f
                break
        assert interface_file is not None
        interface_content = interface_file.read_text()
        assert "def home(" in interface_content
        assert "def pick(" in interface_content
        assert "def place(" in interface_content
        assert "def move(" in interface_content
        assert "def get_position(" in interface_content
        assert "is_homed" in interface_content
        assert "_holding_item" in interface_content

        # Check rest node file for action methods
        rest_file = None
        for f in result.files_created:
            if f.name == "my_arm_rest_node.py":
                rest_file = f
                break
        assert rest_file is not None
        rest_content = rest_file.read_text()
        assert "def home(" in rest_content
        assert "def pick(" in rest_content
        assert "def place(" in rest_content
        assert "def move_to(" in rest_content
        assert "def get_arm_status(" in rest_content

    def test_render_camera_module(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Test rendering of camera module template."""
        engine = registry.get_template("module/camera")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = engine.render(
            output_dir=output_dir,
            parameters={"module_name": "my_cam", "port": 3000},
        )

        assert len(result.files_created) > 0
        # Verify key files exist
        file_names = [f.name for f in result.files_created]
        assert "my_cam_rest_node.py" in file_names
        assert "my_cam_interface.py" in file_names
        assert "my_cam_fake_interface.py" in file_names
        assert "my_cam_types.py" in file_names
        assert "test_my_cam_interface.py" in file_names

    def test_render_camera_module_python_syntax(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Test that camera module generates valid Python."""
        engine = registry.get_template("module/camera")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = engine.render(
            output_dir=output_dir,
            parameters={"module_name": "my_cam", "port": 3000},
        )

        for f in result.files_created:
            if f.suffix == ".py":
                content = f.read_text()
                try:
                    ast.parse(content)
                except SyntaxError as e:
                    pytest.fail(f"Invalid Python syntax in {f}: {e}")

    def test_render_camera_module_content(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Test that camera module content has correct class names and actions."""
        engine = registry.get_template("module/camera")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = engine.render(
            output_dir=output_dir,
            parameters={"module_name": "my_cam", "port": 3000},
        )

        # Check types file for camera-specific types
        types_file = None
        for f in result.files_created:
            if f.name == "my_cam_types.py":
                types_file = f
                break
        assert types_file is not None
        types_content = types_file.read_text()
        assert "MyCamNodeConfig" in types_content
        assert "MyCamInterfaceConfig" in types_content
        assert "MyCamCaptureResult" in types_content
        assert "MyCamResult" in types_content
        assert "default_exposure_ms" in types_content
        assert "default_resolution" in types_content

        # Check interface file for camera operations
        interface_file = None
        for f in result.files_created:
            if f.name == "my_cam_interface.py":
                interface_file = f
                break
        assert interface_file is not None
        interface_content = interface_file.read_text()
        assert "def capture(" in interface_content
        assert "def configure(" in interface_content
        assert "def get_image_info(" in interface_content
        assert "def get_status(" in interface_content
        assert "_capture_count" in interface_content
        assert "_last_capture" in interface_content

        # Check rest node file for action methods
        rest_file = None
        for f in result.files_created:
            if f.name == "my_cam_rest_node.py":
                rest_file = f
                break
        assert rest_file is not None
        rest_content = rest_file.read_text()
        assert "def capture(" in rest_content
        assert "def configure_camera(" in rest_content
        assert "def get_camera_status(" in rest_content
        assert "def reset_camera(" in rest_content

    def test_render_instrument_module(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Test rendering of instrument module template."""
        engine = registry.get_template("module/instrument")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = engine.render(
            output_dir=output_dir,
            parameters={"module_name": "my_spec", "port": 3000},
        )

        assert len(result.files_created) > 0
        file_names = [f.name for f in result.files_created]
        assert "my_spec_rest_node.py" in file_names
        assert "my_spec_interface.py" in file_names
        assert "my_spec_fake_interface.py" in file_names
        assert "my_spec_types.py" in file_names
        assert "test_my_spec_interface.py" in file_names

    def test_render_instrument_module_python_syntax(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Test that instrument module generates valid Python."""
        engine = registry.get_template("module/instrument")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = engine.render(
            output_dir=output_dir,
            parameters={"module_name": "my_spec", "port": 3000},
        )

        for f in result.files_created:
            if f.suffix == ".py":
                content = f.read_text()
                try:
                    ast.parse(content)
                except SyntaxError as e:
                    pytest.fail(f"Invalid Python syntax in {f}: {e}")

    def test_render_instrument_module_content(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Test that instrument module content has correct class names and actions."""
        engine = registry.get_template("module/instrument")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = engine.render(
            output_dir=output_dir,
            parameters={"module_name": "my_spec", "port": 3000},
        )

        # Check types file for instrument-specific types
        types_file = None
        for f in result.files_created:
            if f.name == "my_spec_types.py":
                types_file = f
                break
        assert types_file is not None
        types_content = types_file.read_text()
        assert "MySpecNodeConfig" in types_content
        assert "MySpecInterfaceConfig" in types_content
        assert "MySpecReading" in types_content
        assert "MySpecCalibrationData" in types_content
        assert "MySpecResult" in types_content
        assert "measurement_units" in types_content

        # Check interface file for instrument operations
        interface_file = None
        for f in result.files_created:
            if f.name == "my_spec_interface.py":
                interface_file = f
                break
        assert interface_file is not None
        interface_content = interface_file.read_text()
        assert "def connect(" in interface_content
        assert "def initialize(" in interface_content
        assert "def measure(" in interface_content
        assert "def calibrate(" in interface_content
        assert "def get_status(" in interface_content
        assert "is_connected" in interface_content
        assert "is_calibrated" in interface_content

        # Check rest node file for action methods
        rest_file = None
        for f in result.files_created:
            if f.name == "my_spec_rest_node.py":
                rest_file = f
                break
        assert rest_file is not None
        rest_content = rest_file.read_text()
        assert "def measure(" in rest_content
        assert "def calibrate(" in rest_content
        assert "def get_instrument_status(" in rest_content
        assert "def reset_instrument(" in rest_content

    def test_render_liquid_handler_module(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Test rendering of liquid handler module template."""
        engine = registry.get_template("module/liquid_handler")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = engine.render(
            output_dir=output_dir,
            parameters={"module_name": "my_pipette", "port": 3000},
        )

        assert len(result.files_created) > 0
        file_names = [f.name for f in result.files_created]
        assert "my_pipette_rest_node.py" in file_names
        assert "my_pipette_interface.py" in file_names
        assert "my_pipette_fake_interface.py" in file_names
        assert "my_pipette_types.py" in file_names
        assert "test_my_pipette_interface.py" in file_names

    def test_render_liquid_handler_module_python_syntax(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Test that liquid handler module generates valid Python."""
        engine = registry.get_template("module/liquid_handler")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = engine.render(
            output_dir=output_dir,
            parameters={"module_name": "my_pipette", "port": 3000},
        )

        for f in result.files_created:
            if f.suffix == ".py":
                content = f.read_text()
                try:
                    ast.parse(content)
                except SyntaxError as e:
                    pytest.fail(f"Invalid Python syntax in {f}: {e}")

    def test_render_liquid_handler_module_content(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Test that liquid handler module content has correct class names and actions."""
        engine = registry.get_template("module/liquid_handler")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = engine.render(
            output_dir=output_dir,
            parameters={"module_name": "my_pipette", "port": 3000},
        )

        # Check types file for liquid handler specific types
        types_file = None
        for f in result.files_created:
            if f.name == "my_pipette_types.py":
                types_file = f
                break
        assert types_file is not None
        types_content = types_file.read_text()
        assert "MyPipetteNodeConfig" in types_content
        assert "MyPipetteInterfaceConfig" in types_content
        assert "MyPipetteAspirateCommand" in types_content
        assert "MyPipetteDispenseCommand" in types_content
        assert "MyPipetteResult" in types_content
        assert "tip_capacity" in types_content
        assert "max_volume_ul" in types_content

        # Check interface file for liquid handler operations
        interface_file = None
        for f in result.files_created:
            if f.name == "my_pipette_interface.py":
                interface_file = f
                break
        assert interface_file is not None
        interface_content = interface_file.read_text()
        assert "def aspirate(" in interface_content
        assert "def dispense(" in interface_content
        assert "def transfer(" in interface_content
        assert "def pick_up_tips(" in interface_content
        assert "def drop_tips(" in interface_content
        assert "def get_status(" in interface_content
        assert "_has_tips" in interface_content
        assert "_current_volume_ul" in interface_content

        # Check rest node file for action methods
        rest_file = None
        for f in result.files_created:
            if f.name == "my_pipette_rest_node.py":
                rest_file = f
                break
        assert rest_file is not None
        rest_content = rest_file.read_text()
        assert "def aspirate(" in rest_content
        assert "def dispense(" in rest_content
        assert "def transfer(" in rest_content
        assert "def pick_up_tips(" in rest_content
        assert "def drop_tips(" in rest_content
        assert "def get_handler_status(" in rest_content

    def test_render_experiment_script(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Test rendering of experiment script template."""
        engine = registry.get_template("experiment/script")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = engine.render(
            output_dir=output_dir,
            parameters={"experiment_name": "my_exp"},
        )

        assert len(result.files_created) == 2  # 1 script + 1 skill
        py_file = next(f for f in result.files_created if f.name == "my_exp.py")
        assert py_file.exists()

        # Verify syntax
        content = py_file.read_text()
        ast.parse(content)
        assert "MyExpExperiment" in content

    def test_render_experiment_tui(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Test rendering of experiment TUI template."""
        engine = registry.get_template("experiment/tui")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = engine.render(
            output_dir=output_dir,
            parameters={"experiment_name": "my_tui_exp"},
        )

        assert len(result.files_created) == 2  # 1 script + 1 skill
        py_file = next(f for f in result.files_created if f.name == "my_tui_exp_tui.py")
        assert py_file.exists()

        content = py_file.read_text()
        ast.parse(content)
        assert "ExperimentTUI" in content
        assert "run_tui" in content

    def test_render_experiment_node(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Test rendering of experiment node template."""
        engine = registry.get_template("experiment/node")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = engine.render(
            output_dir=output_dir,
            parameters={"experiment_name": "my_node_exp", "server_port": 7000},
        )

        assert len(result.files_created) == 2  # 1 script + 1 skill
        py_file = next(
            f for f in result.files_created if f.name == "my_node_exp_node.py"
        )
        assert py_file.exists()

        content = py_file.read_text()
        ast.parse(content)
        assert "ExperimentNode" in content
        assert "start_server" in content
        assert "7000" in content

    def test_render_workflow_basic(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Test rendering of basic workflow template."""
        engine = registry.get_template("workflow/basic")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = engine.render(
            output_dir=output_dir,
            parameters={
                "workflow_name": "my_wf",
                "node_name": "sensor_1",
                "action_name": "read_data",
            },
        )

        assert len(result.files_created) == 4  # 1 workflow + 3 skills
        yaml_file = next(
            f for f in result.files_created if f.name == "my_wf.workflow.yaml"
        )
        assert yaml_file.exists()

        content = yaml_file.read_text()
        assert "sensor_1" in content
        assert "read_data" in content

    def test_render_workflow_multi_step(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Test rendering of multi-step workflow template."""
        engine = registry.get_template("workflow/multi_step")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = engine.render(
            output_dir=output_dir,
            parameters={
                "workflow_name": "transfer_wf",
                "node_1_name": "robot_arm",
                "node_1_action": "pick",
                "node_2_name": "plate_reader",
                "node_2_action": "read_plate",
            },
        )

        assert len(result.files_created) == 4  # 1 workflow + 3 skills
        yaml_file = next(
            f for f in result.files_created if f.name == "transfer_wf.workflow.yaml"
        )
        assert yaml_file.exists()

        content = yaml_file.read_text()
        assert "robot_arm" in content
        assert "pick" in content
        assert "plate_reader" in content
        assert "read_plate" in content

    def test_render_conditional_files(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Test that conditional files are excluded when condition is false."""
        engine = registry.get_template("module/basic")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = engine.render(
            output_dir=output_dir,
            parameters={
                "module_name": "test_mod",
                "port": 2000,
                "include_tests": False,
                "include_dockerfile": False,
            },
        )

        file_names = [f.name for f in result.files_created]
        assert "Dockerfile" not in file_names
        assert "test_test_mod_interface.py" not in file_names

    def test_render_module_name_in_content(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Test that module_name is properly substituted in file content."""
        engine = registry.get_template("module/basic")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = engine.render(
            output_dir=output_dir,
            parameters={"module_name": "cool_device", "port": 5000},
        )

        # Check the types file for proper substitution
        types_file = None
        for f in result.files_created:
            if f.name == "cool_device_types.py":
                types_file = f
                break

        assert types_file is not None
        content = types_file.read_text()
        assert "CoolDeviceNodeConfig" in content
        assert "CoolDeviceInterfaceConfig" in content

    def test_render_validation_error(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Test that invalid parameters raise TemplateValidationError."""
        engine = registry.get_template("module/basic")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with pytest.raises(TemplateValidationError) as exc_info:
            engine.render(
                output_dir=output_dir,
                parameters={"module_name": "INVALID!", "port": 2000},
            )
        assert len(exc_info.value.errors) > 0

    def test_render_lab_minimal(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Test rendering of minimal lab template."""
        engine = registry.get_template("lab/minimal")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = engine.render(
            output_dir=output_dir,
            parameters={"lab_name": "test_lab"},
        )

        assert len(result.files_created) == 11  # 7 files + 4 skills
        file_names = [f.name for f in result.files_created]
        assert "start_lab.py" in file_names
        assert "settings.yaml" in file_names
        assert ".env" in file_names
        assert ".gitignore" in file_names
        assert "pyproject.toml" in file_names
        assert "README.md" in file_names
        assert "example.workflow.yaml" in file_names

    def test_render_lab_standard(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Test rendering of standard lab template."""
        engine = registry.get_template("lab/standard")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = engine.render(
            output_dir=output_dir,
            parameters={"lab_name": "test_lab"},
        )

        assert len(result.files_created) == 12  # 8 files + 4 skills
        file_names = [f.name for f in result.files_created]
        assert "start_lab.py" in file_names
        assert "settings.yaml" in file_names
        assert ".env" in file_names
        assert ".gitignore" in file_names
        assert "pyproject.toml" in file_names
        assert "README.md" in file_names
        assert "compose.yaml" in file_names
        assert "example.workflow.yaml" in file_names

    def test_render_lab_distributed(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Test rendering of distributed lab template."""
        engine = registry.get_template("lab/distributed")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = engine.render(
            output_dir=output_dir,
            parameters={"lab_name": "test_lab"},
        )

        assert len(result.files_created) == 13  # 9 files + 4 skills
        file_names = [f.name for f in result.files_created]
        assert "start_lab.py" in file_names
        assert "settings.yaml" in file_names
        assert ".env" in file_names
        assert ".gitignore" in file_names
        assert "pyproject.toml" in file_names
        assert "README.md" in file_names
        assert "compose.yaml" in file_names
        assert "compose.nodes.yaml" in file_names
        assert "example.workflow.yaml" in file_names

    def test_render_workcell_basic(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Test rendering of basic workcell template."""
        engine = registry.get_template("workcell/basic")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = engine.render(
            output_dir=output_dir,
            parameters={"workcell_name": "my_workcell"},
        )

        assert len(result.files_created) > 0
        file_names = [f.name for f in result.files_created]
        assert any("workcell" in name.lower() for name in file_names)


# --- Template completeness tests ---


class TestTemplateCompleteness:
    """Test that all templates referenced in the CLI actually exist."""

    @pytest.fixture
    def registry(self, tmp_path: Path) -> TemplateRegistry:
        return TemplateRegistry(user_template_dir=tmp_path / "user_templates")

    @pytest.mark.parametrize(
        "template_id",
        [
            "module/basic",
            "module/device",
            "module/camera",
            "module/instrument",
            "module/liquid_handler",
            "module/robot_arm",
            "interface/fake",
            "interface/real",
            "interface/sim",
            "interface/mock",
            "node/basic",
            "experiment/script",
            "experiment/notebook",
            "experiment/tui",
            "experiment/node",
            "workflow/basic",
            "workflow/multi_step",
            "workcell/basic",
            "lab/minimal",
            "lab/standard",
            "lab/distributed",
            "comm/serial",
            "comm/socket",
            "comm/rest",
            "comm/sdk",
            "comm/modbus",
        ],
    )
    def test_template_exists(
        self, registry: TemplateRegistry, template_id: str
    ) -> None:
        """Test that each expected template can be loaded."""
        engine = registry.get_template(template_id)
        assert engine.manifest.name
        assert engine.manifest.version
        assert len(engine.manifest.files) > 0

    @pytest.mark.parametrize(
        "template_id",
        [
            "module/basic",
            "module/device",
            "module/camera",
            "module/instrument",
            "module/liquid_handler",
            "module/robot_arm",
            "interface/fake",
            "interface/real",
            "interface/sim",
            "interface/mock",
            "node/basic",
            "experiment/script",
            "experiment/tui",
            "experiment/node",
            "comm/serial",
            "comm/socket",
            "comm/rest",
            "comm/sdk",
            "comm/modbus",
        ],
    )
    def test_template_defaults_are_valid(
        self, registry: TemplateRegistry, template_id: str
    ) -> None:
        """Test that default parameter values pass validation."""
        engine = registry.get_template(template_id)
        defaults = engine.get_default_values()
        errors = engine.validate_parameters(defaults)
        assert errors == [], (
            f"Default values for {template_id} failed validation: {errors}"
        )

    @pytest.mark.parametrize("template_id,params", TEMPLATE_RENDER_PARAMS)
    def test_template_renders_successfully(
        self,
        registry: TemplateRegistry,
        tmp_path: Path,
        template_id: str,
        params: dict,
    ) -> None:
        """Test that each template renders without errors."""
        engine = registry.get_template(template_id)
        output_dir = tmp_path / f"output_{template_id.replace('/', '_')}"
        output_dir.mkdir()

        result = engine.render(output_dir=output_dir, parameters=params)
        assert len(result.files_created) > 0
        for f in result.files_created:
            assert f.exists(), f"File not created: {f}"

    @pytest.mark.parametrize("template_id,params", TEMPLATE_RENDER_PARAMS)
    def test_generated_python_syntax(
        self,
        registry: TemplateRegistry,
        tmp_path: Path,
        template_id: str,
        params: dict,
    ) -> None:
        """Test that all generated Python files have valid syntax."""
        engine = registry.get_template(template_id)
        output_dir = tmp_path / f"output_{template_id.replace('/', '_')}"
        output_dir.mkdir()

        result = engine.render(output_dir=output_dir, parameters=params)

        for f in result.files_created:
            if f.suffix == ".py":
                content = f.read_text()
                try:
                    ast.parse(content)
                except SyntaxError as e:
                    pytest.fail(
                        f"Invalid Python syntax in {f.name} "
                        f"(template: {template_id}): {e}"
                    )


# --- Skills copying tests ---


class TestSkillsCopying:
    """Test that agent skills are correctly copied into generated projects."""

    @pytest.fixture
    def registry(self, tmp_path: Path) -> TemplateRegistry:
        return TemplateRegistry(user_template_dir=tmp_path / "user_templates")

    def test_skills_copied_for_module_template(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Module templates should include the madsci-nodes skill."""
        engine = registry.get_template("module/basic")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        engine.render(
            output_dir=output_dir,
            parameters={"module_name": "test_mod", "port": 2000},
        )

        # Skills should be placed inside the project root (test_mod_module/),
        # not at the top-level output_dir
        skill_file = (
            output_dir
            / "test_mod_module"
            / ".agents"
            / "skills"
            / "madsci-nodes"
            / "SKILL.md"
        )
        assert skill_file.exists()
        content = skill_file.read_text()
        assert "madsci-nodes" in content

    def test_skills_copied_for_experiment_template(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Experiment templates should include the madsci-experiments skill."""
        engine = registry.get_template("experiment/script")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        engine.render(
            output_dir=output_dir,
            parameters={"experiment_name": "test_exp"},
        )

        skill_file = (
            output_dir / ".agents" / "skills" / "madsci-experiments" / "SKILL.md"
        )
        assert skill_file.exists()
        content = skill_file.read_text()
        assert "madsci-experiments" in content

    def test_skills_copied_for_lab_template(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Lab templates should include all 4 skills."""
        engine = registry.get_template("lab/minimal")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        engine.render(
            output_dir=output_dir,
            parameters={"lab_name": "test_lab"},
        )

        # Skills should be placed inside the project root (test_lab/)
        for skill_name in [
            "madsci-nodes",
            "madsci-experiments",
            "madsci-managers",
            "madsci-cli",
        ]:
            skill_file = (
                output_dir / "test_lab" / ".agents" / "skills" / skill_name / "SKILL.md"
            )
            assert skill_file.exists(), f"Missing skill: {skill_name}"

    def test_skills_dry_run(self, registry: TemplateRegistry, tmp_path: Path) -> None:
        """Skills should be listed in files_created but not written during dry run."""
        engine = registry.get_template("module/basic")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = engine.render(
            output_dir=output_dir,
            parameters={"module_name": "test_mod", "port": 2000},
            dry_run=True,
        )

        skill_paths = [f for f in result.files_created if "SKILL.md" in f.name]
        # Default include_agent_config selects both "claude" and "agents",
        # so the skill is copied to both .claude/skills/ and .agents/skills/.
        assert len(skill_paths) == 2
        # Files should NOT exist on disk
        for path in skill_paths:
            assert not path.exists()

    def test_skills_included_in_result(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Result should list skill names in skills_included."""
        engine = registry.get_template("lab/minimal")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = engine.render(
            output_dir=output_dir,
            parameters={"lab_name": "test_lab"},
        )

        assert sorted(result.skills_included) == sorted(
            [
                "madsci-nodes",
                "madsci-experiments",
                "madsci-managers",
                "madsci-cli",
            ]
        )

    def test_no_skills_when_empty(self, tmp_path: Path) -> None:
        """Template with no skills field should copy nothing."""
        # Create a minimal template with no skills
        template_dir = tmp_path / "template"
        template_dir.mkdir()
        manifest = (
            'name: "Test"\n'
            'version: "1.0.0"\n'
            'description: "Test template"\n'
            'category: "module"\n'
            "tags: []\n"
            "skills: []\n"
            "parameters: []\n"
            "files: []\n"
        )
        (template_dir / "template.yaml").write_text(manifest)

        engine = TemplateEngine(template_dir)
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = engine.render(output_dir=output_dir, parameters={})

        assert result.skills_included == []
        skill_dir = output_dir / ".agents" / "skills"
        assert not skill_dir.exists()

    @pytest.mark.parametrize(
        "template_id",
        [
            "module/basic",
            "module/device",
            "module/camera",
            "module/instrument",
            "module/liquid_handler",
            "module/robot_arm",
            "interface/fake",
            "interface/real",
            "interface/sim",
            "interface/mock",
            "node/basic",
            "experiment/script",
            "experiment/notebook",
            "experiment/tui",
            "experiment/node",
            "workflow/basic",
            "workflow/multi_step",
            "workcell/basic",
            "lab/minimal",
            "lab/standard",
            "lab/distributed",
            "comm/serial",
            "comm/socket",
            "comm/rest",
            "comm/sdk",
            "comm/modbus",
        ],
    )
    def test_all_templates_declare_skills(
        self, registry: TemplateRegistry, template_id: str
    ) -> None:
        """Every bundled template should have at least one skill declared."""
        engine = registry.get_template(template_id)
        assert len(engine.manifest.skills) > 0, (
            f"Template {template_id} has no skills declared"
        )

    def test_resolve_skills_dir_importlib_fallback(self, tmp_path: Path) -> None:
        """_resolve_skills_dir falls back to importlib.resources for isolated templates."""
        # Create a template in an isolated directory with no _skills/ ancestor
        template_dir = tmp_path / "isolated" / "deep" / "template"
        template_dir.mkdir(parents=True)
        (template_dir / "template.yaml").write_text(
            'name: "Test"\n'
            'version: "1.0.0"\n'
            'description: "Test"\n'
            'category: "module"\n'
            "tags: []\n"
            'skills: ["madsci-nodes"]\n'
            "parameters: []\n"
            "files: []\n"
        )

        engine = TemplateEngine(template_dir)
        skills_dir = engine._resolve_skills_dir()

        assert skills_dir is not None
        assert skills_dir.is_dir()
        assert (skills_dir / "madsci-nodes" / "SKILL.md").exists()

    def test_bundled_skills_match_repo_skills(self) -> None:
        """Bundled _skills/ content should match .agents/skills/ (via symlinks)."""
        bundled_skills = (
            Path(str(importlib.resources.files("madsci.common")))
            / "bundled_templates"
            / "_skills"
        )

        # Walk up from this file to find the repo root via .git/
        repo_root = Path(__file__).resolve()
        while repo_root != repo_root.parent:
            if (repo_root / ".git").is_dir():
                break
            repo_root = repo_root.parent
        else:
            pytest.skip("Could not find repo root (.git directory)")

        repo_skills = repo_root / ".agents" / "skills"
        if not repo_skills.exists():
            pytest.skip("Repo .agents/skills/ not found (installed package test)")

        for skill_name in [
            "madsci-nodes",
            "madsci-experiments",
            "madsci-managers",
            "madsci-cli",
        ]:
            bundled_file = bundled_skills / skill_name / "SKILL.md"
            repo_file = repo_skills / skill_name / "SKILL.md"
            assert bundled_file.exists(), f"Missing bundled skill: {skill_name}"
            assert repo_file.exists(), f"Missing repo skill: {skill_name}"
            assert bundled_file.read_text() == repo_file.read_text(), (
                f"Content mismatch for {skill_name}/SKILL.md"
            )


# --- Generated code quality tests ---


class TestGeneratedCodeQuality:
    """Cross-cutting quality checks on rendered template output.

    These tests complement the syntax-level checks in TestTemplateCompleteness
    by validating that generated code uses current APIs, produces parseable
    config files, and avoids deprecated patterns.
    """

    @pytest.fixture
    def registry(self, tmp_path: Path) -> TemplateRegistry:
        return TemplateRegistry(user_template_dir=tmp_path / "user_templates")

    @pytest.mark.parametrize("template_id,params", TEMPLATE_RENDER_PARAMS)
    def test_generated_madsci_imports(
        self,
        registry: TemplateRegistry,
        tmp_path: Path,
        template_id: str,
        params: dict,
    ) -> None:
        """Verify that all 'from madsci.* import X' resolve to real names.

        This catches bugs like importing a removed name (e.g., ActionHandler)
        that ast.parse() alone would not detect.
        """
        engine = registry.get_template(template_id)
        output_dir = tmp_path / f"output_{template_id.replace('/', '_')}"
        output_dir.mkdir()
        result = engine.render(output_dir=output_dir, parameters=params)

        for f in result.files_created:
            if f.suffix != ".py":
                continue
            tree = ast.parse(f.read_text())
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom):
                    continue
                if not node.module or not node.module.startswith("madsci."):
                    continue
                try:
                    mod = importlib.import_module(node.module)
                except ModuleNotFoundError:
                    pytest.fail(
                        f"Cannot import module '{node.module}' "
                        f"in {f.name} (template: {template_id})"
                    )
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    assert hasattr(mod, alias.name), (
                        f"Cannot import name '{alias.name}' from '{node.module}' "
                        f"in {f.name} (template: {template_id})"
                    )

    @pytest.mark.parametrize("template_id,params", TEMPLATE_RENDER_PARAMS)
    def test_generated_config_file_syntax(
        self,
        registry: TemplateRegistry,
        tmp_path: Path,
        template_id: str,
        params: dict,
    ) -> None:
        """Verify that generated YAML, TOML, and JSON files are parseable."""
        engine = registry.get_template(template_id)
        output_dir = tmp_path / f"output_{template_id.replace('/', '_')}"
        output_dir.mkdir()
        result = engine.render(output_dir=output_dir, parameters=params)

        for f in result.files_created:
            content = f.read_text()
            if not content.strip():
                continue
            try:
                if f.suffix in (".yaml", ".yml"):
                    yaml.safe_load(content)
                elif f.suffix == ".toml" and tomllib is not None:
                    tomllib.loads(content)
                elif f.suffix == ".json":
                    json.loads(content)
            except Exception as e:
                pytest.fail(
                    f"Invalid {f.suffix} in {f.name} (template: {template_id}): {e}"
                )

    @pytest.mark.parametrize("template_id,params", TEMPLATE_RENDER_PARAMS)
    def test_no_deprecated_patterns(
        self,
        registry: TemplateRegistry,
        tmp_path: Path,
        template_id: str,
        params: dict,
    ) -> None:
        """Verify that generated Python code does not use deprecated APIs.

        Patterns are maintained in DEPRECATED_PYTHON_PATTERNS at the top of
        this module. Add a new entry when an API is removed or renamed.
        """
        engine = registry.get_template(template_id)
        output_dir = tmp_path / f"output_{template_id.replace('/', '_')}"
        output_dir.mkdir()
        result = engine.render(output_dir=output_dir, parameters=params)

        for f in result.files_created:
            if f.suffix != ".py":
                continue
            content = f.read_text()
            for pattern, reason in DEPRECATED_PYTHON_PATTERNS:
                assert pattern not in content, (
                    f"Deprecated pattern '{pattern}' found in {f.name} "
                    f"(template: {template_id}). {reason}"
                )


class TestExpandedModuleTemplates:
    """Tests for the expanded module template files (docs, notebooks, etc.)."""

    @pytest.fixture
    def registry(self, tmp_path: Path) -> TemplateRegistry:
        return TemplateRegistry(user_template_dir=tmp_path / "user_templates")

    def test_module_renders_all_new_files(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Module template should produce all new scaffolding files."""
        engine = registry.get_template("module/basic")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = engine.render(
            output_dir=output_dir,
            parameters={
                "module_name": "test_dev",
                "port": 2000,
                "include_dev_tooling": True,
                "include_agent_config": ["claude", "agents"],
            },
        )

        rel_paths = [str(f.relative_to(output_dir)) for f in result.files_created]

        # Always-included files
        assert any("docs/README.md" in p for p in rel_paths)
        assert any("docs/private/.gitkeep" in p for p in rel_paths)
        assert any("drivers/__init__.py" in p for p in rel_paths)
        assert any("drivers/private/.gitkeep" in p for p in rel_paths)
        assert any("interface_testing.ipynb" in p for p in rel_paths)
        assert any("node_testing.ipynb" in p for p in rel_paths)
        assert any(".gitignore" in p for p in rel_paths)
        assert any("docker-compose.yaml" in p for p in rel_paths)

        # Conditional dev tooling
        assert any(".pre-commit-config.yaml" in p for p in rel_paths)
        assert any("ruff.toml" in p for p in rel_paths)
        assert any("justfile" in p for p in rel_paths)

        # Conditional agent config
        assert any("CLAUDE.md" in p for p in rel_paths)
        assert any("AGENTS.md" in p for p in rel_paths)

    def test_dev_tooling_excluded_when_disabled(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Dev tooling files should be excluded when include_dev_tooling=False."""
        engine = registry.get_template("module/device")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = engine.render(
            output_dir=output_dir,
            parameters={
                "module_name": "test_dev",
                "port": 2000,
                "include_dev_tooling": False,
                "include_agent_config": ["claude", "agents"],
            },
        )

        file_names = [f.name for f in result.files_created]
        assert ".pre-commit-config.yaml" not in file_names
        assert "ruff.toml" not in file_names
        assert "justfile" not in file_names

    def test_agent_config_claude_only(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Only CLAUDE.md and .claude/skills/ when agent config is ['claude']."""
        engine = registry.get_template("module/basic")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = engine.render(
            output_dir=output_dir,
            parameters={
                "module_name": "test_dev",
                "port": 2000,
                "include_agent_config": ["claude"],
            },
        )

        file_names = [f.name for f in result.files_created]
        rel_paths = [str(f.relative_to(output_dir)) for f in result.files_created]

        assert "CLAUDE.md" in file_names
        assert "AGENTS.md" not in file_names
        assert any(".claude/skills/" in p for p in rel_paths)
        assert not any(".agents/skills/" in p for p in rel_paths)

    def test_rendered_notebooks_are_valid_json(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Rendered .ipynb files should be valid JSON with correct structure."""
        engine = registry.get_template("module/basic")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = engine.render(
            output_dir=output_dir,
            parameters={"module_name": "test_nb", "port": 2000},
        )

        notebook_files = [f for f in result.files_created if f.suffix == ".ipynb"]
        assert len(notebook_files) == 2

        for f in notebook_files:
            content = f.read_text()
            data = json.loads(content)
            assert "cells" in data, f"{f.name} missing 'cells'"
            assert "metadata" in data, f"{f.name} missing 'metadata'"
            assert data["nbformat"] == 4, f"{f.name} has wrong nbformat"

    def test_skills_dual_destination(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Skills should be copied to both .claude/ and .agents/ when both selected."""
        engine = registry.get_template("module/basic")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = engine.render(
            output_dir=output_dir,
            parameters={
                "module_name": "test_sk",
                "port": 2000,
                "include_agent_config": ["claude", "agents"],
            },
        )

        rel_paths = [str(f.relative_to(output_dir)) for f in result.files_created]
        assert any(".claude/skills/madsci-nodes/SKILL.md" in p for p in rel_paths)
        assert any(".agents/skills/madsci-nodes/SKILL.md" in p for p in rel_paths)

    def test_skills_backward_compat_no_agent_config(
        self, registry: TemplateRegistry, tmp_path: Path
    ) -> None:
        """Templates without include_agent_config should still copy to .agents/."""
        engine = registry.get_template("lab/minimal")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = engine.render(
            output_dir=output_dir,
            parameters={"lab_name": "test_lab"},
        )

        rel_paths = [str(f.relative_to(output_dir)) for f in result.files_created]
        assert any(".agents/skills/" in p for p in rel_paths)
        assert not any(".claude/skills/" in p for p in rel_paths)

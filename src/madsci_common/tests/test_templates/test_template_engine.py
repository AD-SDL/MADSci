"""Tests for the MADSci template engine and registry.

These tests validate that the template engine correctly renders templates,
the registry discovers templates, and generated code is valid.
"""

import ast
from pathlib import Path

import pytest
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
        assert len(templates) >= 2  # basic and device
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
        assert defaults["module_name"] == "my_module"
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

        assert len(result.files_created) == 1
        py_file = result.files_created[0]
        assert py_file.name == "my_exp.py"
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

        assert len(result.files_created) == 1
        py_file = result.files_created[0]
        assert py_file.name == "my_tui_exp_tui.py"
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

        assert len(result.files_created) == 1
        py_file = result.files_created[0]
        assert py_file.name == "my_node_exp_node.py"
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

        assert len(result.files_created) == 1
        yaml_file = result.files_created[0]
        assert yaml_file.name == "my_wf.workflow.yaml"
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

        assert len(result.files_created) == 1
        yaml_file = result.files_created[0]
        assert yaml_file.name == "transfer_wf.workflow.yaml"
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

        assert len(result.files_created) == 6
        file_names = [f.name for f in result.files_created]
        assert "start_lab.py" in file_names
        assert ".env" in file_names
        assert ".gitignore" in file_names
        assert "pyproject.toml" in file_names
        assert "README.md" in file_names
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
            "interface/fake",
            "node/basic",
            "experiment/script",
            "experiment/notebook",
            "experiment/tui",
            "experiment/node",
            "workflow/basic",
            "workflow/multi_step",
            "workcell/basic",
            "lab/minimal",
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
            "node/basic",
            "experiment/script",
            "experiment/tui",
            "experiment/node",
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

    @pytest.mark.parametrize(
        "template_id,params",
        [
            ("module/basic", {"module_name": "test_gen", "port": 2000}),
            ("module/device", {"module_name": "test_gen", "port": 2000}),
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
            ("workcell/basic", {"workcell_name": "test_gen"}),
        ],
    )
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

    @pytest.mark.parametrize(
        "template_id,params",
        [
            ("module/basic", {"module_name": "syntax_test", "port": 2000}),
            ("module/device", {"module_name": "syntax_test", "port": 2000}),
            ("node/basic", {"node_name": "syntax_test", "port": 2000}),
            ("experiment/script", {"experiment_name": "syntax_test"}),
            ("experiment/tui", {"experiment_name": "syntax_test"}),
            (
                "experiment/node",
                {"experiment_name": "syntax_test", "server_port": 6000},
            ),
        ],
    )
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

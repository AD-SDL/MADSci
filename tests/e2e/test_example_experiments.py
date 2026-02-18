"""Tests for the example experiment script and notebook.

Validates syntax, imports, linting compliance, and structural correctness
of the example files without requiring a running lab.
"""

import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_SCRIPT = REPO_ROOT / "examples" / "example_experiment.py"
EXAMPLE_NOTEBOOK = REPO_ROOT / "examples" / "notebooks" / "experiment_notebook.ipynb"


class TestExampleExperimentScript:
    """Tests for examples/example_experiment.py."""

    def test_file_exists(self):
        assert EXAMPLE_SCRIPT.exists(), f"{EXAMPLE_SCRIPT} not found"

    def test_valid_python_syntax(self):
        source = EXAMPLE_SCRIPT.read_text()
        ast.parse(source, filename=str(EXAMPLE_SCRIPT))

    def test_imports_successfully(self):
        """Verify the script can be imported without side effects."""
        result = subprocess.run(  # noqa: S603
            [
                sys.executable,
                "-c",
                "import importlib.util, sys; "
                f"spec = importlib.util.spec_from_file_location('example_experiment', '{EXAMPLE_SCRIPT}'); "
                "mod = importlib.util.module_from_spec(spec); "
                "spec.loader.exec_module(mod); "
                "assert hasattr(mod, 'ExampleExperiment'); "
                "assert hasattr(mod, 'WORKFLOW_DEFINITION'); "
                "print('OK')",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert result.returncode == 0, (
            f"Import failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "OK" in result.stdout

    def test_ruff_compliance(self):
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-m", "ruff", "check", str(EXAMPLE_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert result.returncode == 0, f"ruff check failed:\n{result.stdout}"

    def test_script_defines_experiment_class(self):
        source = EXAMPLE_SCRIPT.read_text()
        tree = ast.parse(source)
        class_names = [
            node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
        ]
        assert "ExampleExperiment" in class_names

    def test_script_defines_workflow(self):
        source = EXAMPLE_SCRIPT.read_text()
        assert "WORKFLOW_DEFINITION" in source

    def test_script_has_main_block(self):
        source = EXAMPLE_SCRIPT.read_text()
        assert 'if __name__ == "__main__"' in source

    def test_script_overrides_run_experiment(self):
        source = EXAMPLE_SCRIPT.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "ExampleExperiment":
                method_names = [
                    n.name
                    for n in node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                assert "run_experiment" in method_names, (
                    "ExampleExperiment must override run_experiment()"
                )
                return
        pytest.fail("ExampleExperiment class not found")


class TestExperimentNotebook:
    """Tests for examples/notebooks/experiment_notebook.ipynb."""

    @pytest.fixture()
    def notebook(self) -> dict:
        with EXAMPLE_NOTEBOOK.open() as f:
            return json.load(f)

    def test_file_exists(self):
        assert EXAMPLE_NOTEBOOK.exists(), f"{EXAMPLE_NOTEBOOK} not found"

    def test_valid_json(self, notebook):
        assert "cells" in notebook
        assert "metadata" in notebook
        assert notebook.get("nbformat") == 4

    def test_has_code_and_markdown_cells(self, notebook):
        cell_types = {c["cell_type"] for c in notebook["cells"]}
        assert "code" in cell_types, "Notebook should have code cells"
        assert "markdown" in cell_types, "Notebook should have markdown cells"

    def test_uses_experiment_notebook_class(self, notebook):
        code_sources = [
            "".join(c["source"]) for c in notebook["cells"] if c["cell_type"] == "code"
        ]
        all_code = "\n".join(code_sources)
        assert "ExperimentNotebook" in all_code, (
            "Notebook code cells should import/use ExperimentNotebook"
        )

    def test_does_not_import_experiment_script_in_code(self, notebook):
        code_sources = [
            "".join(c["source"]) for c in notebook["cells"] if c["cell_type"] == "code"
        ]
        all_code = "\n".join(code_sources)
        assert "ExperimentScript" not in all_code, (
            "Notebook code cells should not import ExperimentScript"
        )

    def test_has_start_and_end_calls(self, notebook):
        code_sources = [
            "".join(c["source"]) for c in notebook["cells"] if c["cell_type"] == "code"
        ]
        all_code = "\n".join(code_sources)
        assert ".start(" in all_code, "Notebook should call experiment.start()"
        assert ".end()" in all_code, "Notebook should call experiment.end()"

    def test_references_example_script(self, notebook):
        all_sources = "".join("".join(c["source"]) for c in notebook["cells"])
        assert "example_experiment.py" in all_sources, (
            "Notebook should reference examples/example_experiment.py"
        )

    def test_code_cells_have_valid_python_syntax(self, notebook):
        for i, cell in enumerate(notebook["cells"]):
            if cell["cell_type"] != "code":
                continue
            source = "".join(cell["source"])
            if not source.strip():
                continue
            try:
                ast.parse(source)
            except SyntaxError as e:
                pytest.fail(f"Code cell {i} has invalid syntax: {e}")

    def test_no_markdown_in_code_cells(self, notebook):
        """Verify code cells don't contain markdown content (swapped cell type)."""
        for i, cell in enumerate(notebook["cells"]):
            if cell["cell_type"] != "code":
                continue
            source = "".join(cell["source"]).lstrip()
            # Code cells should not start with markdown headers (## or ###)
            assert not source.startswith("## "), (
                f"Code cell {i} starts with '## ' - likely a markdown cell with wrong type"
            )
            assert not source.startswith("### "), (
                f"Code cell {i} starts with '### ' - likely a markdown cell with wrong type"
            )

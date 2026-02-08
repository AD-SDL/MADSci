# E2E Test Harness Research & Recommendation

**Status**: Research Complete
**Date**: 2026-02-07
**Last Updated**: 2026-02-08

## Executive Summary

After researching available E2E testing frameworks, I recommend a **layered approach** using:
1. **pytest** as the core test runner (already in use)
2. **Click's CliRunner** for CLI command testing (Click is already a dependency)
3. **pytest-docker** for Docker-based integration tests
4. **Custom fixtures/helpers** for MADSci-specific validation (template validation, tutorial steps)

This approach maximizes reuse of existing tools and minimizes new dependencies while providing the flexibility we need.

---

## Frameworks Evaluated

### 1. pytest-bdd
**What it is**: BDD (Behavior-Driven Development) plugin for pytest using Gherkin syntax.

**Pros**:
- Integrates directly with pytest (no separate runner)
- Can reuse existing pytest fixtures
- Human-readable `.feature` files
- Good for documenting expected behavior

**Cons**:
- Gherkin syntax adds overhead for technical tests
- Step definitions require boilerplate
- May be overkill for our use case (we're not doing traditional BDD)

**Verdict**: **Not recommended** - Gherkin adds complexity without proportional benefit for our technical validation needs.

---

### 2. Robot Framework
**What it is**: Generic automation framework with keyword-driven testing.

**Pros**:
- Very readable test syntax
- Large ecosystem of libraries
- Good for non-programmers
- Built-in reporting

**Cons**:
- Separate tool from pytest (would need to run both)
- Different paradigm from our existing tests
- Steeper learning curve for contributors
- Keyword-driven approach is verbose for programmatic validation

**Verdict**: **Not recommended** - Too different from our existing test infrastructure; would fragment testing.

---

### 3. behave
**What it is**: Standalone BDD framework for Python (like Cucumber).

**Pros**:
- Clean Gherkin implementation
- Good documentation
- Active community

**Cons**:
- Separate runner from pytest
- Same Gherkin overhead as pytest-bdd
- Would need to maintain two test suites

**Verdict**: **Not recommended** - Same issues as pytest-bdd, plus separate runner.

---

### 4. pytest-docker
**What it is**: Pytest plugin for Docker-based integration tests.

**Pros**:
- Native pytest integration
- Fixtures for starting/stopping Docker Compose services
- Waits for services to be ready
- We already use Docker Compose

**Cons**:
- Requires Docker (but so does our current setup)
- 440 stars, smaller community than some alternatives

**Verdict**: **Recommended** for Docker-based integration tests.

---

### 5. testinfra (pytest-testinfra)
**What it is**: Pytest plugin for infrastructure testing (files, services, ports, etc.).

**Pros**:
- Native pytest integration
- Can test Docker containers, SSH hosts, local system
- Good for validating system state
- Useful modules: File, Service, Socket, Package, etc.

**Cons**:
- More focused on infrastructure than application behavior
- May be overkill for most of our needs

**Verdict**: **Consider for specific use cases** - useful for validating service health, file creation, port availability.

---

### 6. Click CliRunner
**What it is**: Built-in testing utilities for Click CLI applications.

**Pros**:
- Already available (Click is a dependency)
- Native support for testing Click commands
- File system isolation
- Input stream simulation (for prompts)
- Captures output, exit codes, exceptions

**Cons**:
- Only for Click commands (not general E2E)
- Modifies interpreter state (not thread-safe)

**Verdict**: **Strongly recommended** for CLI testing - it's the official way to test Click apps.

---

### 7. nox
**What it is**: Flexible test automation tool (like tox but with Python config).

**Pros**:
- Python-based configuration
- Good for running tests across environments
- CI/CD friendly

**Cons**:
- Test orchestration, not test framework
- We already have `just` for task running
- Would add another layer

**Verdict**: **Not recommended** - overlaps with our existing `just`/`pdm` workflow.

---

### 8. Avocado Framework
**What it is**: Full-featured test framework with unittest pattern.

**Pros**:
- Comprehensive feature set
- Good for system-level testing
- Built-in reporting

**Cons**:
- Heavy framework, different paradigm
- Would replace rather than complement pytest
- Overkill for our needs

**Verdict**: **Not recommended** - too heavy, different paradigm.

---

## Recommended Approach

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Test Infrastructure                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │   Unit Tests    │  │ Integration     │  │    E2E / Tutorial Tests    │  │
│  │   (existing)    │  │ Tests           │  │    (new)                   │  │
│  │                 │  │                 │  │                            │  │
│  │  pytest         │  │  pytest         │  │  pytest                    │  │
│  │                 │  │  pytest-docker  │  │  pytest-docker             │  │
│  │                 │  │                 │  │  Click CliRunner           │  │
│  │                 │  │                 │  │  MADSci test helpers       │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────┘  │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                    MADSci Test Helpers (new package)                    ││
│  │                                                                          ││
│  │  - TemplateValidator: Instantiate & validate templates                  ││
│  │  - TutorialRunner: Execute tutorial steps, validate outcomes            ││
│  │  - ServiceHealthChecker: Wait for services, check endpoints             ││
│  │  - CLITestRunner: Wrapper around Click CliRunner with MADSci context    ││
│  │  - OutputValidator: Check files, logs, generated code                   ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Components

#### 1. Click CliRunner for CLI Tests
```python
# tests/cli/test_madsci_cli.py
from click.testing import CliRunner
from madsci.client.cli import madsci

def test_madsci_version():
    runner = CliRunner()
    result = runner.invoke(madsci, ['version'])
    assert result.exit_code == 0
    assert 'madsci' in result.output.lower()

def test_madsci_new_node():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(madsci, [
            'new', 'node',
            '--name', 'test_node',
            '--template', 'basic',
            '--no-interactive'
        ])
        assert result.exit_code == 0
        assert Path('test_node/test_node.py').exists()
```

#### 2. pytest-docker for Service Tests
```python
# tests/e2e/conftest.py
import pytest

@pytest.fixture(scope="session")
def docker_compose_file():
    return "compose.yaml"

@pytest.fixture(scope="session")
def docker_compose_project_name():
    return "madsci-test"

# tests/e2e/test_lab_startup.py
def test_lab_manager_starts(docker_services):
    """Test that lab manager starts and responds to health checks."""
    docker_services.wait_until_responsive(
        timeout=60.0,
        pause=1.0,
        check=lambda: is_responsive("http://localhost:8000/health")
    )
```

#### 3. MADSci Test Helpers
```python
# src/madsci_common/madsci/common/testing/template_validator.py
from pathlib import Path
from dataclasses import dataclass

@dataclass
class TemplateValidationResult:
    success: bool
    errors: list[str]
    warnings: list[str]
    generated_files: list[Path]

class TemplateValidator:
    """Validates MADSci templates by instantiating and checking output."""

    def validate_template(self, template_name: str, test_values: dict) -> TemplateValidationResult:
        """Instantiate template with test values and validate output."""
        # 1. Instantiate template
        # 2. Check files are valid Python (syntax check)
        # 3. Run ruff on generated code
        # 4. Optionally run the generated code
        ...

# src/madsci_common/madsci/common/testing/tutorial_runner.py
@dataclass
class TutorialStep:
    name: str
    command: str | None = None
    python_code: str | None = None
    validations: list[Validation] = field(default_factory=list)
    timeout: int | None = None  # Per-step timeout in seconds (overrides default)

@dataclass
class Validation:
    type: str  # "file_exists", "file_contains", "http_health", "exit_code", etc.
    params: dict

class TutorialRunner:
    """Executes tutorial steps and validates outcomes."""

    def run_tutorial(self, tutorial_path: Path) -> TutorialResult:
        """Load and execute a tutorial definition."""
        ...
```

#### 4. Tutorial Definition Format
```yaml
# tests/e2e/tutorials/02-first-node.tutorial.yaml
name: "First Node Tutorial"
description: "Create and run your first MADSci node"
requirements:
  - python: ">=3.10"
  - docker: false  # Not required for this tutorial

steps:
  - name: "Create a new node"
    command: "madsci new node --name my_pipette --template basic --no-interactive"
    validations:
      - type: exit_code
        expected: 0
      - type: file_exists
        path: "my_pipette/my_pipette.py"
      - type: file_contains
        path: "my_pipette/my_pipette.py"
        pattern: "class MyPipette"

  - name: "Validate generated code passes linting"
    command: "ruff check my_pipette/"
    validations:
      - type: exit_code
        expected: 0

  - name: "Start the node"
    command: "python my_pipette/my_pipette.py &"
    background: true
    timeout: 60  # Allow up to 60 seconds for this step
    wait_for:
      type: http_health
      url: "http://localhost:2000/health"
      timeout: 30

  - name: "Query node info"
    command: "curl -s http://localhost:2000/info"
    validations:
      - type: json_field
        path: "node_name"
        expected: "my_pipette"

cleanup:
  - command: "pkill -f 'my_pipette.py'"
  - command: "rm -rf my_pipette/"
```

### Directory Structure

```
tests/
├── unit/                      # Existing unit tests
├── integration/               # Existing integration tests
├── cli/                       # NEW: CLI tests using Click CliRunner
│   ├── test_madsci_version.py
│   ├── test_madsci_new.py
│   ├── test_madsci_doctor.py
│   └── ...
├── e2e/                       # NEW: End-to-end tests
│   ├── conftest.py            # pytest-docker fixtures
│   ├── tutorials/             # Tutorial definitions
│   │   ├── 01-exploration.tutorial.yaml
│   │   ├── 02-first-node.tutorial.yaml
│   │   └── ...
│   ├── test_tutorials.py      # Runs all tutorials
│   ├── test_lab_startup.py    # Docker-based lab tests
│   └── test_templates.py      # Template validation tests
└── fixtures/                  # Shared test fixtures
    └── ...

src/madsci_common/madsci/common/testing/
├── __init__.py
├── template_validator.py
├── tutorial_runner.py
├── service_health.py
└── cli_runner.py              # MADSci-specific CliRunner wrapper
```

### CI Integration

```yaml
# .github/workflows/e2e-tests.yml
name: E2E Tests

on:
  push:
    branches: [main]
  pull_request:

jobs:
  cli-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install pdm && pdm install -G:all
      - run: pytest tests/cli/ -v

  template-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install pdm && pdm install -G:all
      - run: pytest tests/e2e/test_templates.py -v

  tutorial-tests:
    runs-on: ubuntu-latest
    needs: [cli-tests, template-tests]  # Only run if basic tests pass
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install pdm && pdm install -G:all
      - run: pytest tests/e2e/test_tutorials.py -v --tutorial-filter="no-docker"

  docker-e2e-tests:
    runs-on: ubuntu-latest
    needs: [tutorial-tests]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install pdm && pdm install -G:all
      - run: docker compose build
      - run: pytest tests/e2e/ -v --docker-enabled
```

---

## Implementation Plan

### Phase 0.1: Core Infrastructure
1. Add `pytest-docker` to dev dependencies
2. Create `src/madsci_common/madsci/common/testing/` package
3. Implement basic `TemplateValidator` class
4. Implement basic `TutorialRunner` class
5. Create `tests/cli/` and `tests/e2e/` directories

### Phase 0.2: CLI Test Suite
1. Create Click CliRunner-based tests for existing backup CLI
2. Establish patterns for future CLI tests
3. Add to CI

### Phase 0.3: Template Validation
1. Define template validation criteria
2. Implement template instantiation and validation
3. Create tests for existing example code as templates

### Phase 0.4: Tutorial Runner
1. Define YAML format for tutorials
2. Implement tutorial execution engine
3. Convert existing README steps to tutorial format
4. Add to CI

---

## Dependencies to Add

```toml
# In pyproject.toml [project.optional-dependencies] or PDM dev group
pytest-docker = "^3.0"
# testinfra = "^10.0"  # Optional, add if needed
```

---

## Next Steps

1. Review and approve this recommendation
2. Create initial test infrastructure (Phase 0.1)
3. Write first CLI tests using existing backup CLI as guinea pig
4. Iterate on tutorial format and runner

# Example Lab Test Suite

This directory contains automated tests for the MADSci example lab, validating functionality, integration, and proper operation of example workflows and lab setup procedures.

## Test Categories

### Lab Setup Tests (`test_lab_setup.py`)
- Service health checks and connectivity
- Lab configuration validation
- Lab initialization sequence

### Resource Template Tests (`test_resource_templates.py`)
- Template creation and structure validation
- Template inheritance patterns
- Template library functionality
- Template validation and error handling

### Workflow Tests (`test_workflows.py`)
- Basic workflow execution
- Workflow dependencies and monitoring
- Step execution and timeout handling

### Workflow Parameter Tests (`test_workflow_parameters.py`)
- Input vs feed forward parameter separation (PR #104)
- File-based parameters and automatic promotion
- Parameter validation and dataflow

### Error Handling Tests (`test_error_handling.py`)
- Capped error message lengths (PR #104)
- Retry mechanisms and backoff strategies
- Internal workcell actions
- Error recovery and logging

### Context Management Tests (`test_context_management.py`)
- OwnershipInfo propagation
- MadsciContext usage across services
- Context-aware resource management
- Ownership transfer patterns

## Running Tests

### Prerequisites

1. **Install Dependencies**:
   ```bash
   pdm install
   ```

2. **Start Services** (for integration tests):
   ```bash
   just build
   just up -d
   ```

### Test Execution

**Run All Tests**:
```bash
pytest tests/example_lab/
```

**Run Specific Test Category**:
```bash
python tests/example_lab/run_tests.py --category lab_setup
python tests/example_lab/run_tests.py --category workflows --verbose
```

**Run with Coverage**:
```bash
pytest tests/example_lab/ --cov --cov-report=term-missing
# or
python tests/example_lab/run_tests.py --coverage
```

**Run Unit Tests Only** (no services required):
```bash
pytest tests/example_lab/ -m "not requires_services"
```

**Run Integration Tests** (requires services):
```bash
pytest tests/example_lab/ -m "requires_services"
```

### CI/CD Integration

Tests are automatically run in the GitHub Actions workflow (`pytests.yml`):

1. **Unit Tests**: Run as part of the standard test suite
2. **Integration Tests**: Run with Docker services started via `just up -d`
3. **Coverage**: Combined with main test suite coverage reporting

### Test Configuration

- **pytest.ini**: Test-specific configuration and markers
- **conftest.py**: Shared fixtures and test utilities
- **TestConfig**: Configuration constants for service URLs and timeouts

### Test Markers

- `@pytest.mark.smoke`: Basic connectivity tests
- `@pytest.mark.integration`: Tests requiring external services
- `@pytest.mark.slow`: Tests with longer execution times
- `@pytest.mark.requires_services`: Tests needing MADSci services running

### Service Dependencies

Integration tests require the following MADSci services:
- Event Manager (port 8001)
- Experiment Manager (port 8002)
- Resource Manager (port 8003)
- Data Manager (port 8004)
- Workcell Manager (port 8005)

Use `just up -d` to start all services, or `just down` to stop them.

## Test Development

When adding new tests:

1. **Use Appropriate Markers**: Mark tests that require services
2. **Follow Naming Conventions**: Test files should start with `test_`
3. **Use Shared Fixtures**: Leverage fixtures from `conftest.py`
4. **Clean Up Resources**: Ensure tests don't interfere with each other
5. **Document Test Purpose**: Include clear docstrings for test intent

## Troubleshooting

**Services Not Starting**: Check Docker is running and ports are available
**Test Failures**: Verify services are healthy with `just health` (if available)
**Import Errors**: Ensure all MADSci packages are installed with `pdm install`

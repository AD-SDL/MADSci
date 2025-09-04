# Automated Jupyter Notebook Execution

MADSci supports automated execution of Jupyter notebooks for CI/CD, testing, and reproducible lab setup using Papermill.

## Papermill Execution

**Best for:** Parameterized execution, production workflows, CI/CD

Papermill executes notebooks with parameter injection and proper error handling:

```bash
# Execute single notebook
python scripts/run_notebooks.py --notebook example_lab/test_notebook.ipynb

# Execute with custom parameters
python scripts/run_notebooks.py --notebook example_lab/test_notebook.ipynb \
  --parameters '{"test_parameter": "production", "numeric_param": 500}'

# Execute full setup sequence
python scripts/run_notebooks.py
```

**Features:**
- ✅ Parameter injection via tagged cells
- ✅ Clean output notebooks with execution results
- ✅ Proper error handling and reporting
- ✅ Integration with CI/CD systems
- ✅ Execution metrics and timing

## Just Commands (Recommended Usage)

The project includes `just` commands for easy notebook execution:

```bash
# Execute all setup notebooks
just notebooks

# Execute single notebook
just notebook example_lab/test_notebook.ipynb

# Execute notebooks and run tests
just setup-and-test
```

## Notebook Parameter System

### Parameter Cells
Mark cells with `"tags": ["parameters"]` for papermill injection:

```python
# Parameters cell (papermill will inject parameters here)
lab_id = "default_lab"
experiment_name = "default_experiment"
create_resources = True
```

### Parameter Usage
Reference parameters in subsequent cells:

```python
# Use the injected parameters
print(f"Setting up lab: {lab_id}")
print(f"Running experiment: {experiment_name}")

if create_resources:
    # Create lab resources
    pass
```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Execute Setup Notebooks
on: [push, pull_request]

jobs:
  notebook-execution:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install pdm
          pdm install -G:all

      - name: Start MADSci services
        run: just up -d

      - name: Execute setup notebooks
        run: just notebooks

      - name: Run tests
        run: just test

      - name: Upload notebook outputs
        uses: actions/upload-artifact@v4
        with:
          name: executed-notebooks
          path: example_lab/executed_*.ipynb
```

### Docker Integration
```dockerfile
# Add to existing MADSci Dockerfile
RUN pdm add -d papermill nbconvert

# Execute notebooks during container build
RUN just notebooks
```

## Error Handling

### Notebook-Level Error Handling
```python
# Add to notebook cells for graceful error handling
try:
    # Potentially failing operation
    client = ResourceClient(resource_server_url="http://localhost:8003")
    resources = client.list_resources()
    print(f"✅ Found {len(resources)} resources")
except Exception as e:
    print(f"⚠️  Service not available: {e}")
    # Set default values or skip operation
    resources = []
```

### Script-Level Error Handling
The execution script provides:
- ✅ Capture and report execution errors
- ✅ Continue execution after individual notebook failures
- ✅ Summary reporting of success/failure rates
- ✅ Proper exit codes for CI/CD

## Best Practices

### 1. Notebook Design
- **Use parameter cells** for configurable values
- **Include error handling** for service dependencies
- **Add progress indicators** for long-running operations
- **Clean up temporary files** created during execution

### 2. Production Usage
- **Test notebooks locally** before CI/CD integration
- **Use specific parameter values** for production environments
- **Archive output notebooks** for audit trails
- **Monitor execution times** and optimize slow notebooks

### 3. Development Workflow
- **Execute notebooks after code changes** to validate functionality
- **Use notebooks for integration testing** of MADSci services
- **Create notebook-based documentation** that stays up-to-date
- **Parameterize notebooks** for different environments (dev/staging/prod)

## Troubleshooting

### Common Issues

**Import Errors:**
```python
# Add to notebook cells
import sys
sys.path.append('/path/to/madsci')
```

**Service Connectivity:**
```python
# Test service health before proceeding
import requests
try:
    response = requests.get("http://localhost:8003/", timeout=5)
    print("✅ Resource service available")
except:
    print("❌ Resource service unavailable")
```

**Parameter Issues:**
```python
# Provide defaults for all parameters
lab_id = locals().get('lab_id', 'default_lab')
```

### Debugging Failed Executions
```bash
# View detailed error output
python scripts/run_notebooks.py --notebook failing_notebook.ipynb 2>&1 | tee execution.log

# Execute with detailed error output
python scripts/run_notebooks.py --notebook failing_notebook.ipynb
```

## Advanced Usage

### Custom Execution Environments
```python
# In run_notebooks.py, modify kernel selection:
cmd = ["papermill", str(notebook_path), str(output_path), "--kernel", "custom_kernel"]
```

### Distributed Execution
```python
# Execute notebooks in parallel (future enhancement)
import concurrent.futures

with concurrent.futures.ProcessPoolExecutor() as executor:
    futures = [executor.submit(run_notebook, nb) for nb in notebooks]
```

### Integration with External Systems
```python
# Post execution results to external systems
def post_results(notebook_path, success, execution_time):
    # Send to monitoring system, Slack, etc.
    pass
```

This automated execution system enables MADSci to be used in production workflows, CI/CD pipelines, and automated testing scenarios while maintaining the interactive nature of Jupyter notebooks for development and exploration.

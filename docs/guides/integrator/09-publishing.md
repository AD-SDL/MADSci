# Publishing

**Audience**: Equipment Integrator
**Prerequisites**: [Packaging & Deployment](./08-packaging-deployment.md)
**Time**: ~15 minutes

## Overview

Sharing your module allows other labs to use your instrument integration. This guide covers:

1. Preparing a module for publication
2. Version management
3. Publishing as a Python package
4. Publishing as a Docker image
5. Contributing to the MADSci ecosystem

## 1. Preparing for Publication

### Repository Structure

Ensure your module repository follows the standard structure:

```
my_sensor_module/
├── src/
│   ├── my_sensor_rest_node.py
│   ├── my_sensor_interface.py
│   ├── my_sensor_fake_interface.py
│   ├── my_sensor_types.py
│   └── __init__.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_interface.py
│   ├── test_node.py
│   └── test_integration.py
├── docs/
│   └── README.md
├── .env.example
├── .github/
│   └── workflows/
│       └── ci.yml
├── Dockerfile
├── pyproject.toml
├── LICENSE
└── README.md
```

### README Checklist

Your README should include:

- [ ] Module description and purpose
- [ ] Supported hardware models and firmware versions
- [ ] Installation instructions
- [ ] Quick start example
- [ ] Available actions with parameter descriptions
- [ ] Configuration reference (environment variables)
- [ ] Hardware setup instructions (wiring, drivers, etc.)
- [ ] Known limitations

### Example README Section

```markdown
## Actions

| Action | Description | Parameters |
|--------|-------------|------------|
| `measure` | Take a sensor reading | `samples` (int, default: 1) |
| `calibrate` | Calibrate against reference | `reference_temp` (float) |
| `get_reading` | Get last reading | None |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `MY_SENSOR_INTERFACE_TYPE` | `fake` | Interface variant: `real`, `fake`, `sim` |
| `MY_SENSOR_SERIAL_PORT` | `/dev/ttyUSB0` | Serial port for real interface |
| `MY_SENSOR_BAUD_RATE` | `9600` | Serial baud rate |
| `MY_SENSOR_DEFAULT_SAMPLES` | `10` | Default number of samples |
```

## 2. Version Management

Use semantic versioning (SemVer) for your module:

- **MAJOR** (1.0.0 -> 2.0.0): Breaking changes to action signatures or interface API
- **MINOR** (1.0.0 -> 1.1.0): New actions, new features, backward-compatible
- **PATCH** (1.0.0 -> 1.0.1): Bug fixes, documentation updates

### Version in `pyproject.toml`

```toml
[project]
version = "1.2.3"
```

### Git Tags

```bash
# Tag a release
git tag -a v1.2.3 -m "Release v1.2.3: Add calibration action"
git push origin v1.2.3
```

### Changelog

Maintain a `CHANGELOG.md`:

```markdown
# Changelog

## [1.2.3] - 2026-02-09

### Added
- `calibrate` action for sensor calibration
- Fake interface now simulates calibration drift

### Fixed
- Serial timeout handling on Windows

## [1.2.2] - 2026-02-01

### Fixed
- Humidity readings capped at 100%
```

## 3. Publishing as a Python Package

### To PyPI

```bash
# Install build tools
pip install build twine

# Build the package
python -m build

# Upload to PyPI
twine upload dist/*

# Upload to Test PyPI first (recommended)
twine upload --repository testpypi dist/*
```

### Automated Release with GitHub Actions

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      id-token: write  # For trusted publishing
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install build
      - run: python -m build
      - uses: pypa/gh-action-pypi-publish@release/v1
```

## 4. Publishing as a Docker Image

### To Docker Hub

```bash
# Build and tag
docker build -t myorg/my-sensor-module:1.2.3 .
docker tag myorg/my-sensor-module:1.2.3 myorg/my-sensor-module:latest

# Push
docker push myorg/my-sensor-module:1.2.3
docker push myorg/my-sensor-module:latest
```

### To GitHub Container Registry

```bash
# Login
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Build, tag, and push
docker build -t ghcr.io/myorg/my-sensor-module:1.2.3 .
docker push ghcr.io/myorg/my-sensor-module:1.2.3
```

### Automated Docker Release

```yaml
# .github/workflows/docker.yml
name: Docker

on:
  push:
    tags:
      - 'v*'

jobs:
  docker:
    runs-on: ubuntu-latest
    permissions:
      packages: write
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v5
        with:
          push: true
          tags: |
            ghcr.io/${{ github.repository }}:${{ github.ref_name }}
            ghcr.io/${{ github.repository }}:latest
```

## 5. Contributing to the MADSci Ecosystem

### Module Compatibility

To ensure your module works well with MADSci labs:

1. **Pin MADSci version ranges**: Use `madsci_node_module>=0.6.0,<1.0.0`
2. **Test with the latest MADSci release**: Include in your CI
3. **Follow naming conventions**: `{instrument}_module` for repositories
4. **Use standard action names**: Prefer established names like `measure`, `calibrate`, `initialize`, `shutdown` when applicable

### Sharing with the Community

- Open-source your module on GitHub
- Add the `madsci-module` topic to your repository
- Document hardware requirements clearly
- Include a working fake interface so others can test without hardware
- Consider contributing instrument-specific templates to the MADSci template library

### Template Contribution

If your module represents a common instrument pattern, consider contributing a template:

```bash
# Structure for a contributed template
my_template/
├── template.yaml       # Template manifest
├── files/              # Jinja2 template files
│   ├── src/
│   │   ├── {{module_name}}_rest_node.py.j2
│   │   ├── {{module_name}}_interface.py.j2
│   │   └── ...
│   └── ...
└── README.md           # Template documentation
```

## What's Next?

- [Understanding Modules](./01-understanding-modules.md) - Review the fundamentals
- [Tutorial: Full Lab](../../tutorials/05-full-lab.md) - See modules in a complete lab context
- [Operator Guide](../operator/README.md) - Learn about lab operations

# List available commands
default:
  @just --list --justfile {{justfile()}}

# initialize the project
init:
  @which pdm || echo "pdm not found, you'll need to install it: https://github.com/pdm-project/pdm"
  @#pdm config use_uv true
  @pdm install -G:all
  @OSTYPE="" . .venv/bin/activate
  @which pre-commit && pre-commit install && pre-commit autoupdate || true
  @mkdir -p $(dirname {{justfile()}})/.madsci

# Create a .env file for the docker compose
env:
  @test -e .env || cp .env.example .env

# Source the venv
venv:
  @$(pdm venv activate)

# Run the full check test and build pipeline
pipe: check tests build
pipeline: pipe

# Run ci plus start the example lab
pipeup: pipe up
pipelineup: pipeup

# Same as pipeup, but detached
pipeupd: pipe upd
pipelineupd: pipeupd

# Run the pre-commit checks
checks:
  @pre-commit run --all-files || { echo "" && echo "Some checks failed! Running one more time to see if any automatic fixes worked:" && echo "" ; pre-commit run --all-files; }
# Run the pre-commit checks
check: checks
ruff-unsafe:
  @ruff check . --fix --unsafe-fixes

# Export OpenAPI specs from all managers
api-specs:
  @python scripts/export_openapi.py
  @echo "✅ OpenAPI specs exported to docs/api-specs/"

# Generate REST API documentation (Redoc HTML pages)
rest-api-docs: api-specs
  @python scripts/generate_redoc.py
  @echo "✅ Redoc pages generated in docs/rest-api/"

# Check that committed OpenAPI specs are up-to-date
api-specs-check:
  @python scripts/export_openapi.py --check

# Generate API documentation with pdoc
docs: rest-api-docs
  @pdm run pdoc --output-dir docs/api/ --force madsci
  @# Strip machine-specific pointer addresses from generated docs to avoid noisy diffs
  @python -c "import re, pathlib; [f.write_text(re.sub(r'[\s\xa0]at[\s\xa0]0x[0-9a-fA-F]+>', '>', f.read_text())) for f in pathlib.Path('docs/api').rglob('*.md')]"
  @echo "✅ API documentation generated in docs/api/"

# Build the project
build: dcb

# Python tasks

# Update the pdm version
pdm-update:
  @pdm self update

# Install the default dependencies
pdm-install:
  @pdm install

# Install a specific group of dependencies
pdm-install-group group:
  @pdm install --group {{group}}

# Install all dependencies
pdm-install-all:
  @just pdm-install-group :all

# Build the python package
pdm-build:
  @pdm build

# Run the full UX verification suite
verify-ux: checks test
  @echo "UX verification complete"

# Run automated tests
test *args:
  @pytest {{args}}
# Run automated tests
tests: test
# Run automated tests
pytest: test

# Run tests with coverage report
coverage:
  @pytest --cov --cov-report=term-missing

# Run tests with HTML coverage report
coverage-html:
  @pytest --cov --cov-report=html

# Run tests with XML coverage report (for CI)
coverage-xml:
  @pytest --cov --cov-report=xml

# Build docker images
dcb: env
  @docker compose --profile build build madsci
  @docker compose --profile build build madsci_dashboard

# Start the example lab
up *args: env
  @docker compose up {{args}}

upd: env
  @docker compose up -d

# Build + up
bup: build up
# Build + up detached
bupd: build upd

# Stop the example lab and remove the containers
down:
  @docker compose down

# Alias for docker compose
dc *args:
  @docker compose {{args}}

# Update version across all pyproject.toml and package.json files
update-version version:
  #!/usr/bin/env bash
  set -euo pipefail

  # Validate version format (basic semver check)
  if ! echo "{{version}}" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.-]+)?(\+[a-zA-Z0-9.-]+)?$'; then
    echo "❌ Error: Version '{{version}}' is not a valid semantic version (e.g., 1.0.0, 1.0.0-rc.1)"
    exit 1
  fi

  echo "📦 Updating version to {{version}} across all files..."

  # Store current version for comparison
  current_version=$(grep '^version = ' pyproject.toml | head -1 | sed 's/version = "\(.*\)"/\1/')
  echo "   Current version: $current_version"
  echo "   New version: {{version}}"

  if [ "$current_version" = "{{version}}" ]; then
    echo "ℹ️  Version is already {{version}}, no changes needed"
    exit 0
  fi

  # Update root pyproject.toml
  sed -i.bak 's/^version = ".*"/version = "{{version}}"/' pyproject.toml

  # Update all Python package pyproject.toml files
  find src -name "pyproject.toml" -not -path '*/.*' -exec sed -i.bak 's/^version = ".*"/version = "{{version}}"/' {} \;

  # Update UI package.json
  if [ -f ui/package.json ]; then
    sed -i.bak 's/"version": ".*"/"version": "{{version}}"/' ui/package.json
  fi

  # Clean up backup files
  find . -name "*.bak" -delete

  echo "✅ Updated version to {{version}} in:"
  echo "  - Root pyproject.toml"
  echo "  - All Python package pyproject.toml files ($(find src -name "pyproject.toml" -not -path '*/.*' | wc -l | xargs echo) files)"
  echo "  - UI package.json"
  echo ""

  # Show changed files if in git repo
  if git rev-parse --git-dir > /dev/null 2>&1; then
    changed_files=$(git diff --name-only | grep -E "(pyproject\.toml|package\.json)" | head -20 || true)
    if [ -n "$changed_files" ]; then
      echo "📝 Files updated:"
      echo "$changed_files" | sed 's/^/  - /'
    fi
  fi

# Show current version across all files
show-version:
  #!/usr/bin/env bash
  echo "📦 Current versions across the repository:"
  echo ""
  echo "Root:"
  echo "  - pyproject.toml: $(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')"
  echo ""
  echo "Python packages:"
  find src -name "pyproject.toml" -not -path '*/.*' | sort | while read file; do
    version=$(grep '^version = ' "$file" | sed 's/version = "\(.*\)"/\1/')
    package_name=$(grep '^name = ' "$file" | sed 's/name = "\(.*\)"/\1/')
    echo "  - $package_name: $version"
  done
  echo ""
  if [ -f ui/package.json ]; then
    echo "UI:"
    ui_version=$(grep '"version":' ui/package.json | sed 's/.*"version": "\(.*\)".*/\1/')
    echo "  - package.json: $ui_version"
  fi

# Validate the node example notebook
validate_nb_node:
  docker compose --profile testing run --rm --no-deps notebook_validator papermill /home/madsci/notebooks/node_notebook.ipynb /dev/null --cwd /home/madsci/notebooks --log-output --execution-timeout 120

# Validate the experiment example notebook
validate_nb_experiment:
  docker compose --profile testing run --rm notebook_validator papermill /home/madsci/notebooks/experiment_notebook.ipynb /dev/null --cwd /home/madsci/notebooks --log-output --execution-timeout 120

# Validate the backup & migration example notebook
validate_nb_backup:
  docker compose --profile testing run --rm --no-deps notebook_validator papermill /home/madsci/notebooks/backup_and_migration.ipynb /dev/null --cwd /home/madsci/notebooks --log-output --execution-timeout 120

# Validate the SiLA node example notebook (starts SiLA server, runs notebook, stops server)
validate_nb_sila:
  docker compose up -d sila_example_server
  docker compose --profile testing run --rm --no-deps notebook_validator papermill /home/madsci/notebooks/sila_node_notebook.ipynb /dev/null --cwd /home/madsci/notebooks --log-output --execution-timeout 120

# Validate all example notebooks
validate_notebooks: validate_nb_node validate_nb_experiment validate_nb_backup validate_nb_sila

# Start with observability stack
otel *args: env
  @docker compose --profile otel up {{args}}

oteld: env
  @docker compose --profile otel up -d

boteld: env build oteld

# Run the full pipeline including notebook validation
all: down pipeupd validate_notebooks down docs checks

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

# Create a .env file for the docker compose
env:
  @test -e .env || cp .env.example .env
  @sed -i "s|^REPO_PATH=.*|REPO_PATH=$(dirname {{justfile()}})|" .env
  @mkdir -p $(dirname {{justfile()}})/.madsci

# Source the venv
venv:
  @$(pdm venv activate)


# Run the pre-commit checks
checks:
  @pre-commit run --all-files || { echo "Checking fixes\n" ; pre-commit run --all-files; }
# Run the pre-commit checks
check: checks

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

# Run automated tests
test:
  @pytest
# Run automated tests
tests: test
# Run automated tests
pytest: test

# Build docker images
dcb: env
  @docker compose build

# Start the example lab
up *args: env
  @docker compose up {{args}}

# Stop the example lab and remove the containers
down:
  @docker compose down

# Alias for docker compose
dc *args:
  @docker compose {{args}}

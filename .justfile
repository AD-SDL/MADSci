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
  @docker compose build

# Start the example lab
up *args: env
  @docker compose up {{args}}

upd: env
  @docker compose up -d

# Stop the example lab and remove the containers
down:
  @docker compose down

# Alias for docker compose
dc *args:
  @docker compose {{args}}

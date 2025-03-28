# List available commands
default:
  @just --list --justfile {{justfile()}}

# initialize the project
init:
  @which pdm || echo "pdm not found, you'll need to install it: https://github.com/pdm-project/pdm"
  @pdm config use_uv true
  @pdm install -G:all
  @#test -e .env || cp .env.example .env
  @OSTYPE="" . .venv/bin/activate
  @which pre-commit && pre-commit install && pre-commit autoupdate || true

# Run the pre-commit checks
checks:
  @pre-commit run --all-files || { echo "Checking fixes\n" ; pre-commit run --all-files; }
check: checks


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
tests: test
pytest: test

# Build docker image
docker-build:
  @docker build -t ghcr.io/ad-sdl/madsci:dev .

# List available commands
default:
  @just --list --justfile {{justfile()}}

# initialize the project
init: hooks
  @which pdm || echo "pdm not found, you'll need to install it: https://github.com/pdm-project/pdm"
  @pdm install
  @cd madsci/madsci_common && pdm install && cd -
  @pdm update
  @#test -e .env || cp .env.example .env

# Install the pre-commit hooks
hooks:
  @pre-commit install

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

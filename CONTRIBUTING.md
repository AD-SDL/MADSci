# Contributing to MADSci

Thank you for your interest in contributing to MADSci! This guide will help you get started with development and understand how to submit contributions.

## Table of Contents

- [Developer Guide](#developer-guide)
- [Submitting Feedback and Contributions](#submitting-feedback-and-contributions)
- [Configuration](#configuration)

## Developer Guide

### Prerequisites

- **Python 3.9+**: Required for all MADSci components
- **[PDM](https://pdm-project.org/)**: For dependency management and virtual environments
- **[Docker](https://docs.docker.com/engine/install/)**: Required for services, integration tests, and end-to-end tests
  - Alternatives: [Rancher Desktop](https://rancherdesktop.io/), [Podman](https://podman.io/)
  - If you're new to Docker, please see our [Docker Guide](https://github.com/AD-SDL/MADSci/wiki/Docker-Guide).
- **[just](https://github.com/casey/just)**: Task runner for development commands
   - Commands are defined in the hidden `.justfile` in the repository root, and can be used without `just` if desired
   - Run `just` without a subcommand for a list of all available commands
- **Node.js/yarn**: Only needed for dashboard development

### Quick Setup

```bash
# Clone and initialize
git clone https://github.com/AD-SDL/MADSci.git
cd MADSci
just init  # Installs all dependencies and sets up pre-commit hooks

# See all available commands
just list

# Start example lab for testing
just up
```

### Development Commands

```bash
# Testing
pytest                    # Run all tests
just test                 # Alternative test runner
pytest -k workcell        # Run specific component tests

# Code Quality
just checks               # Run all pre-commit checks (ruff, formatting, etc.)
ruff check               # Manual linting
ruff format              # Manual formatting

# Services
just build               # Build Docker images
just up                  # Start example lab
just down               # Stop services

# Dashboard Development
cd ui/
yarn dev                # Start Vue dev server
yarn build              # Build for production
```

### Development Patterns

**Manager Implementation:**
Each manager service follows this structure:
- Settings class inheriting from `MadsciBaseSettings`
- FastAPI server with REST endpoints
- Client class for programmatic interaction
- Database models (SQLModel/Pydantic)

**Testing:**
- Integration tests use Docker containers via pytest-mock-resources
- Component tests are in each package's `tests/` directory
- Use `pytest -k EXPRESSION` to filter tests

**Configuration:**
- Environment variables with hierarchical precedence
- Each manager has unique prefix (e.g., `WORKCELL_`, `EVENT_`)
- See [Configuration.md](./Configuration.md) for full details

### Dev Container Support

For VS Code users, use the included [.devcontainer](./.devcontainer) for instant setup:
- Automatic dependency installation
- Pre-configured development environment
- Docker services ready to run

## Submitting Feedback and Contributions

We welcome all forms of contribution to MADSci! Whether you've found a bug, have a feature request, or want to contribute code, here's how to get involved:

### Reporting Bugs

If you encounter a bug or issue:

1. **Check existing issues**: Search the [issue tracker](https://github.com/AD-SDL/MADSci/issues) to see if it's already been reported
2. **Create a new issue**: If not found, [open a new issue](https://github.com/AD-SDL/MADSci/issues/new) with:
   - A clear, descriptive title
   - Steps to reproduce the problem
   - Expected vs. actual behavior
   - Your environment details (OS, Python version, MADSci version)
   - Relevant logs or error messages
   - Minimal code example if applicable

### Feature Requests

Have an idea for improving MADSci?

1. **Check existing issues**: See if someone has already suggested it
2. **Open a feature request**: [Create a new issue](https://github.com/AD-SDL/MADSci/issues/new) describing:
   - The problem you're trying to solve
   - Your proposed solution
   - Any alternatives you've considered
   - How it would benefit other users

### Contributing Code

We love code contributions! Here's the process:

1. **Fork the repository** on GitHub
2. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes**:
   - Follow existing code style and patterns (see [CLAUDE.md](./CLAUDE.md))
   - Add tests for new functionality
   - Update documentation as needed
4. **Run quality checks**:
   ```bash
   just checks  # Lint and format
   pytest       # Run tests
   ```
5. **Commit your changes** with clear, descriptive messages
6. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```
7. **Open a Pull Request** with:
   - Clear description of changes
   - Reference to any related issues
   - Screenshots/examples if applicable

### Pull Request Guidelines

- Keep changes focused and atomic
- Ensure all tests pass
- Maintain or improve code coverage
- Follow the existing code style (enforced by pre-commit hooks)
- Update relevant documentation
- Be responsive to review feedback

### Getting Help

- **Questions**: Open a [discussion](https://github.com/AD-SDL/MADSci/discussions) or issue
- **Documentation**: Review the [README](./README.md) and component-specific docs (each madsci system component has a dedicated README under `src/madsci_<component_name>/README.md)

## Configuration

### Using the .env.example File

MADSci uses environment variables for configuration. The repository includes a `.env.example` file that demonstrates all available configuration options.

**Important Guidelines:**

1. **Leave values commented by default**: All values in `.env.example` are intentionally commented out. This allows MADSci to use its sensible defaults for most use cases.

2. **Only uncomment what you need**: When you need to override a specific setting, copy `.env.example` to `.env` and uncomment only the specific variables you want to change:
   ```bash
   cp .env.example .env
   # Edit .env and uncomment only the settings you need to override
   ```

3. **Common scenarios for overriding**:
   - Setting the USER_ID and GROUP_ID when using the docker compose, to ensure files created by the containers match host user file permissions
   - Changing database connection strings for non-localhost deployments
   - Adjusting file storage paths
   - Modifying server URLs for distributed deployments
   - Configuring rate limiting for production environments
   - Setting up object storage credentials

4. **Example workflow**:
   ```bash
   # Copy the example file
   cp .env.example .env

   # Edit .env and uncomment only what you need, for example:
   # RESOURCE_DB_URL="postgresql://user:pass@prod-db:5432/resources"
   # DATA_FILE_STORAGE_PATH="/mnt/lab-storage/datapoints"
   ```

5. **Docker Compose**: When using Docker Compose, the `.env` file is automatically loaded. Ensure it's in the same directory as your `docker-compose.yml` file.

6. **Development vs Production**:
   - **Development**: Most developers can use the defaults and don't need a `.env` file at all
   - **Production**: Create a `.env` file with only production-specific overrides

For a complete list of available configuration options, see [Configuration.md](./Configuration.md).

## Code of Conduct

Please be respectful and constructive in all interactions. We're building a welcoming community for scientific software development.

## License

By contributing to MADSci, you agree that your contributions will be licensed under the same license as the project (see [LICENSE](./LICENSE) file).

## Questions?

Don't hesitate to reach out! Open an issue or discussion if you need clarification on anything in this guide.

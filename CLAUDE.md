# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

MADSci (Modular Autonomous Discovery for Science) is a Python-based framework for scientific laboratory automation and experimentation. The codebase is organized as a monorepo with multiple packages under the `src/` directory, each providing different components of the MADSci ecosystem.

## Architecture

The system follows a microservices architecture with the following main components:

### Core Components
- **madsci_common**: Shared types, utilities, and base classes used across all components
- **madsci_client**: Client libraries for interacting with MADSci services
- **madsci_squid**: Central lab configuration manager and dashboard provider (Lab Manager)
- **madsci_node_module**: Framework for creating laboratory instrument nodes
- **madsci_experiment_application**: Provides a class for managing automated and autonomous experiments using MADSci-powered labs.

### Manager Services
- **madsci_event_manager**: Distributed event logging and querying (Port 8001)
- **madsci_experiment_manager**: Experimental runs and campaigns management (Port 8002)
- **madsci_resource_manager**: Laboratory resource and inventory tracking (Port 8003)
- **madsci_data_manager**: Data capture, storage, and querying (Port 8004)
- **madsci_workcell_manager**: Workflow coordination and scheduling (Port 8005)
- **madsci_location_manager**: Laboratory location management, resource attachments, and node-specific references (Port 8006)

### Frontend
- **ui/**: Vue 3 + Vuetify dashboard for lab management and monitoring

## Development Commands

This project uses PDM for Python dependency management and `just` for task running.

### Setup
```bash
just init                    # Initialize project and install all dependencies
```

### Testing
```bash
pytest                       # Run all tests
just test                    # Alternative way to run tests
just coverage                # Run tests with coverage report
just coverage-html           # Generate HTML coverage report
just coverage-xml            # Generate XML coverage report (for CI)
```

### Code Quality
```bash
just checks                  # Run pre-commit checks (ruff, formatting, etc.)
ruff check                   # Run linter manually
ruff format                  # Format code manually
```

### Docker & Services
```bash
just build                   # Build docker images
just up                      # Start example lab services
just down                    # Stop services and remove containers
```

### Frontend Development
```bash
cd ui/
yarn dev                     # Start Vue development server
yarn build                   # Build for production
```

### Python Package Management
```bash
pdm install                  # Install default dependencies
pdm install -G:all           # Install all dependency groups
pdm build                    # Build python packages
```

## Configuration

Configuration is handled through environment variables with a hierarchical precedence system. See `Configuration.md` for comprehensive configuration options.

Key configuration patterns:
- Each manager has its own settings class with environment prefix (e.g., `WORKCELL_`, `EVENT_`, `LOCATION_`)
- Server URLs default to localhost with specific ports
- Database connections default to MongoDB/PostgreSQL on localhost
- File storage paths default to `~/.madsci/` subdirectories

## Development Patterns

### Manager Implementation
Each manager service follows this pattern:
1. Settings class inheriting from `MadsciBaseSettings`
2. Server class inheriting from `AbstractManagerBase` with FastAPI endpoints
3. Client class for programmatic interaction
4. Database models (SQLModel for PostgreSQL, Pydantic for MongoDB)

The `AbstractManagerBase` class provides:
- Common functionality for all managers (settings, logging, CORS middleware)
- Standard endpoints (definition, health)
- FastAPI app configuration and server lifecycle management
- Generic typing for settings and definition classes

### Type System
- All types are defined in `madsci_common/types/`
- Uses Pydantic v2 for data validation and serialization
- SQLModel for database ORM with PostgreSQL
- Enum types for status and state management

### ID Generation
- **ULID (Universally Unique Lexicographically Sortable Identifier)** is used for all IDs throughout MADSci
- ULIDs provide better performance than UUIDs while maintaining uniqueness and sortability
- When generating new IDs, use `new_ulid_str()` from `madsci.common.utils`
- Example usage: `resource_id = new_ulid_str()`

### Node Development
Laboratory instruments implement the Node interface:
1. Inherit from `AbstractNodeModule`
2. Implement required action methods
3. Define node configuration in YAML
4. Use REST endpoints for communication

### Testing
- Uses pytest with docker containers for integration tests
- Mock resources for database testing
- Component tests are located in each package's `tests/` directory
- **IMPORTANT**: Use `pytest` directly instead of `python -m pytest` for running tests

## File Structure Conventions

```
src/madsci_*/
├── madsci/package_name/     # Python package code
│   └── *_server.py           # FastAPI server (for managers)
├── tests/                  # Package-specific tests
├── README.md               # Package documentation
└── pyproject.toml          # Package dependencies
src/madsci_client/
└── madsci/client/*_client.py     # Client implementation
src/madsci_common/
└── madsci/common/types/*_types.py     # Pydantic Data Models and Enums
```

## Important Notes

- Python 3.9+ required
- Docker required for running services and some tests
- Pre-commit hooks enforce code quality standards
- The project is currently in beta with potential breaking changes
- Each package can be used independently or composed together
- Use PDM virtual environments for development isolation
- **IMPORTANT**: if you try to run python commands and see missing modules, ensure that the correct virtual environment is activated.
- **IMPORTANT**: Use `yarn` for managing Node.js dependencies in the `ui/` directory, not npm
- Ignore minor linting errors that will be fixed by autoformatting, such as "No newline at end of file"
- Always use pydantic's `AnyUrl` to store URL's, and note that AnyUrl always ensures a trailing forward slash
- Imports should generally be done at the top of the file, unless there are circular dependencies or other factors which require localized importing.

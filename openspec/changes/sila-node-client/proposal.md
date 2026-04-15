## Why

MADSci currently only supports controlling lab instruments via REST-based node modules. Instruments that implement the SiLA 2 standard require an intermediate REST node wrapper to integrate with MADSci workcells, adding complexity and latency. A native SiLA client would let MADSci workcells communicate directly with SiLA2 servers over gRPC, reducing integration overhead and broadening the ecosystem of instruments MADSci can orchestrate out of the box.

## What Changes

- Add a `SilaNodeClient` class implementing `AbstractNodeClient` that connects to SiLA2 servers via the `unitelabs-sila` Python SDK over gRPC
- Register `sila://` as a new URL scheme for node client dispatch, enabling zero-config workcell integration via the existing `find_node_client()` mechanism
- Add `SilaNodeClientConfig` settings class for SiLA-specific connection parameters (TLS, timeouts, polling)
- Add `unitelabs-sila` as an optional dependency (`pip install "madsci.client[sila]"`)
- Map SiLA Features/Commands to MADSci Actions using dot notation (`"FeatureName.CommandName"`)
- Support both unobservable (synchronous) and observable (long-running) SiLA commands

## Capabilities

### New Capabilities
- `sila-command-execution`: Send MADSci ActionRequests to SiLA2 servers, mapping SiLA commands (both observable and unobservable) to the MADSci action lifecycle
- `sila-server-introspection`: Query SiLA2 server features, commands, and properties to build MADSci NodeInfo/NodeStatus/state representations
- `sila-client-dispatch`: Automatic routing of `sila://` URLs to SilaNodeClient via the existing node client dispatch mechanism

### Modified Capabilities
_(none — no existing spec-level requirements change)_

## Impact

- **Code**: New file in `src/madsci_client/madsci/client/node/`, edits to client `__init__.py`, `client_types.py`, and `pyproject.toml`
- **APIs**: No REST API changes. Workcell config `nodes` dict now accepts `sila://host:port` URLs alongside `http://` URLs
- **Dependencies**: `unitelabs-sila` added as optional extra; brings `grpcio`, `lxml`, `zeroconf` transitively
- **Systems**: Workcell engine gains ability to dispatch actions to SiLA servers without code changes (URL-driven)

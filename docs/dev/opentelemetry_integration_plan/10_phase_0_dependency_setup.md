# Phase 0: Dependency Setup and Verification

**Estimated Effort:** Small (1 day)
**Breaking Changes:** None

## Goals

- Verify all required OpenTelemetry dependencies are installed
- Add missing dependencies to appropriate packages
- Ensure optional OTLP exporters are available
- Establish a single canonical OTEL bootstrap location (`madsci.common.otel`)

## 0.1 Current Dependency Status

**Already present in `src/madsci_client/pyproject.toml`:**

```toml
dependencies = [
  "opentelemetry-api>=1.20.0",
  "opentelemetry-sdk>=1.20.0",
  "structlog>=24.1.0",
]

[project.optional-dependencies]
otel-exporters = [
  "opentelemetry-exporter-otlp>=1.20.0",
]
```

## 0.1.1 Versioning Strategy (Normative)

OpenTelemetry Python packages are split across multiple distributions (api, sdk, exporters, instrumentation). They are
intended to be used at compatible versions.

Rules:

- Pin OTEL packages to compatible versions across all MADSci subpackages.
- Keep `opentelemetry-api` and `opentelemetry-sdk` on the same released minor version.
- Keep `opentelemetry-exporter-otlp` on a compatible version with the SDK.
- Keep `opentelemetry-instrumentation-*` packages on a consistent version line (they are often released as `0.xx b0`).

Implementation guidance:

- Prefer a single internal "OTEL version policy" that all `src/madsci_*/pyproject.toml` files follow.
- Avoid mixing wide ranges like `>=1.20.0` across multiple packages; prefer bounded ranges (or exact pins) to prevent
  dependency resolution from selecting mismatched OTEL components.

## 0.2 Required Additions

### 0.2.1 Add OTEL Dependencies to madsci_common

Manager-level tracing lives in `src/madsci_common/madsci/common/manager_base.py`, so OTEL API dependencies must be available in `madsci.common`.

Important note: `opentelemetry-api` alone provides no-op defaults. To enable real exporting/sampling/resources in managers, the OTEL SDK must be configured somewhere in the manager process. This plan requires introducing a shared OTEL bootstrap in `madsci_common` so both managers and clients use the same setup logic.

Proposed shared module (required):

- `src/madsci_common/madsci/common/otel/` (imported as `madsci.common.otel`)

This is not only a code organization preference; it is a correctness requirement because OTEL provider/exporter setup
is process-global and must be consistent across managers, nodes, and clients.

Minimum Phase 0 deliverable:

- Create the `madsci.common.otel` package with a stable API surface (see `docs/dev/opentelemetry_integration_plan/12_phase_2_managers.md`).
- Move (or adapt) existing OTEL setup logic currently in `src/madsci_client/madsci/client/otel_config.py` into this package.
- Ensure `madsci_client` imports OTEL bootstrap helpers from `madsci.common.otel`.
- Remove OTEL SDK/provider/exporter configuration code from `madsci_client` once migrated (no compatibility shim required).

Update `src/madsci_common/pyproject.toml`:

```toml
dependencies = [
  # ... existing dependencies ...
  "opentelemetry-api>=1.20.0",
]

[project.optional-dependencies]
otel = [
  "opentelemetry-sdk>=1.20.0",
  "opentelemetry-exporter-otlp>=1.20.0",
]
```

Recommended tightening for OTEL dependency specifiers:

- Use consistent constraints across packages, e.g. `opentelemetry-api>=1.20,<2` and `opentelemetry-sdk>=1.20,<2`.
- For instrumentation packages, use a consistent beta line, e.g. `opentelemetry-instrumentation-...>=0.41b0,<0.42`.

### 0.2.2 Add Context Propagation Dependencies (Optional)

If the project chooses to support B3 propagation in addition to W3C Trace Context:

```toml
# In madsci_client/pyproject.toml (add to an optional group)
  "opentelemetry-exporter-otlp>=1.20.0",
  "opentelemetry-propagator-b3>=1.20.0",
]
```

W3C Trace Context propagation support is included by default via OTEL core packages. Additional propagators (B3, Jaeger)
should remain optional to avoid pulling in unnecessary dependencies.

### 0.2.3 Add Auto-Instrumentation Dependencies (Recommended)

Because Phase 2 adopts auto-instrumentation for HTTP boundaries (server + client), include OTEL instrumentation
packages as optional dependencies.

Recommended optional group (names are illustrative; pin versions consistently in Phase 0/5):

```toml
[project.optional-dependencies]
otel-instrumentation = [
  "opentelemetry-instrumentation-fastapi>=0.41b0",
  "opentelemetry-instrumentation-asgi>=0.41b0",
  # Choose the HTTP client actually used by MADSci managers/clients:
  # "opentelemetry-instrumentation-httpx>=0.41b0",
  # "opentelemetry-instrumentation-requests>=0.41b0",
]
```

Notes:

- Prefer enabling instrumentation programmatically in `madsci.common.otel` rather than relying on `opentelemetry-instrument`
  CLI to keep behavior consistent in tests and packaged deployments.
- If MADSci standardizes on one HTTP client library (e.g., `httpx`), prefer instrumenting that one and avoid including both.

## 0.3 Verification Steps

1. Run `pdm install -G:all` to install all optional dependencies
2. Verify imports work:

```python
from opentelemetry import metrics, trace
from opentelemetry.propagate import extract, inject
```

3. Run existing OTEL demo: `python examples/otel_demo.py`

## 0.4 Acceptance Criteria

- [ ] All OTEL dependencies added to appropriate packages
- [ ] OTEL dependency specifiers are consistent across all `src/madsci_*/pyproject.toml` files
- [ ] `pdm install -G:all` succeeds without errors
- [ ] Import verification passes
- [ ] Existing `otel_demo.py` runs successfully

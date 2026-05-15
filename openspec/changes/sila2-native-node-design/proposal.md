## Why

MADSci is migrating from REST as the default device-integration protocol to SiLA2 (project #293, child issue #294). Before any implementation work, we need a single design pass that resolves *how* MADSci's existing concepts (Actions, state, NodeStatus, NodeInfo, ActionFiles, admin commands) map onto SiLA's primitives (Commands, Properties, Observables, Features, Binary Transfer), *which* of the standard SiLA core features we adopt outright vs. extend vs. supplant with MADSci-specific Features, *which* of those MADSci-specific Features are upstream-contribution candidates, and *what* shape `AbstractNodeClient` needs in order to fully abstract REST- and SiLA-based nodes for internal consumers.

This proposal is **design-only**. It produces no code and no spec deltas. It produces:

1. A coherent set of recommendations across the seven scope areas of #294, with open questions called out explicitly.
2. A draft list of downstream implementation issues to open against #293.

Each downstream implementation issue will carry its own OpenSpec change with concrete spec deltas at implementation time.

## What Changes

This proposal commits to the following design directions; the detailed rationale, tradeoffs, and resolved decisions (RD1–RD8) are in `design.md`:

- **Action mapping.** Default `@action` produces an Observable Command. Add an `observable=False` kwarg (and `@unobservable_action`/`@observable_action` sugar) to opt out / opt in explicitly.
- **State decomposition.** New typed-Property authoring path is preferred; the legacy `state_handler` blob is exposed as `MadsciState.LegacyState : String` with a persistent deprecation warning. Per RD7, projected legacy keys appear under `MadsciState.LegacyState.<key>` namespacing — consumers must update direct state-dict reads. Shim removed before 1.0.
- **Standard SiLA core features.** Adopt `SiLAService`, `LockController`, `CancelController`, `PauseController`, `SimulationController`. Per RD8, missing standard Features are vendored under `madsci.common.sila_features.*` against canonical FDL and contributed back upstream to `sila2`. Defer `AuthenticationService`/`AuthorizationService` until REST grows a parity story. Skip `ConnectionConfigurationService` (server-initiated mode is not in scope).
- **MADSci-specific Features.** Introduce `MadsciAdminController` (SafetyStop, Reset, Shutdown, PauseAll, ResumeAll), `MadsciNodeStatus`, `MadsciNodeInfo`, `MadsciActionHistory`, `MadsciNodeLog`. `SafetyStop`, `Shutdown`, and `PauseAll`/`ResumeAll` are upstream-contribution candidates.
- **Resources capability is removed wholesale.** Per RD5, confirmed unused. Resources live in the Resource Manager; node-direct queries are a REST artifact and disappear from `AbstractNodeClient` entirely.
- **NodeStatus / NodeInfo.** Become projections in `AbstractNodeClient` over a mix of standard SiLA features and MADSci-specific Features. Per RD3, the field-by-field FDL is split into its own follow-up subissue.
- **File and binary handling.** Drop the `__madsci_bytes__` sentinel pattern; use SiLA Binary Transfer end-to-end. `ActionFiles` parameters/responses generate `Binary` Parameters/Responses; the SDK handles chunking transparently.
- **AbstractNodeClient.** Becomes a capability-enforcing facade. `NodeClientCapabilities` is checked at the abstraction boundary, not by consumers. `SilaNodeClient` gains `async_*` parity by wrapping `sila2` SDK calls in `asyncio.to_thread()`; revisit when upstream ships native async (RD1).
- **Push observability is sketched but deferred to v2.** Per RD4, the v1 abstraction does not preclude push-style state/status subscriptions; full adoption (and the workcell-scheduler migration that requires) is its own follow-up.

## Capabilities

This proposal does not add or modify capabilities. It is a design exploration whose output authorizes downstream changes. Each downstream implementation issue (see `tasks.md`) will declare and modify capabilities in its own change.

## Impact

- **Code:** None directly. Authorizes downstream implementation work.
- **Issues:** ~12 new implementation issues opened against #293 (see `tasks.md` for #A–#M). Closes #294 once the issues exist.
- **Specs:** None directly. Each implementation issue lands its own deltas (notably new `sila2-node`, `madsci-admin-feature`, `madsci-node-status-feature`, `madsci-state-shim`, `madsci-action-history-feature`, `madsci-node-log-feature` capabilities; modifications to `sila-command-execution`, `sila-server-introspection`, `sila-client-dispatch`).
- **Backwards compatibility:** The whole project is bounded by the "side-by-side with full parity until REST removal" strategy in #293. This proposal preserves that — the legacy `state_handler` shim, the legacy `__madsci_bytes__` fallback, and the existing `RestNodeClient` all stay supported through the transition window.
- **Upstream:** Three SiLA-standards contribution candidates surfaced (`SafetyStop`, `Shutdown`, `PauseController.PauseAll/ResumeAll`). Those become their own outreach to the SiLA standards body, not landed in MADSci until accepted.

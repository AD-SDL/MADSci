## Context

This document is the design output for issue #294 (the standards-exploration deliverable for the SiLA2 migration project, #293). The design decisions below are intended to be specific enough that downstream implementation issues can be written against them; they are not implementation themselves.

The current state at the time of writing:

- `SilaNodeClient` exists on the `sila_node_client` branch (~800 lines). It implements client-side dispatch (`sila://` URLs), action execution (observable + unobservable), introspection (`get_info` / `get_state` / `get_status`), and a transitional bytes-as-`ActionFile` pattern (sentinel-encoded, top-level only). It does **not** implement: admin commands, async methods, observable cancel, lock/pause integration, file-input upload, set_config, get_log, get_resources, get_action_history.
- The Python SiLA SDK in use is `sila2 v0.14.0` (Niklas Mertsch / wega-it lineage). It bundles SiLAService, AuthenticationService, AuthorizationService, AuthorizationProviderService, LockController. It does **not** bundle CancelController, PauseController, SimulationController, ErrorRecoveryService, ConnectionConfigurationService, AuthorizationConfigurationService, ParameterConstraintsProvider — those are standardized at `org.silastandard/core` but require either a different SDK distribution (e.g. `unitelabs-sila`, which the existing `ImportError` hint mistakenly references) or hand-rolled implementations.
- Binary Transfer is a **protocol-level** concern in the SDK, not a SiLA Feature. Any field of type `Binary` whose value exceeds 2 MiB is automatically chunked over a separate gRPC service.
- `AbstractNodeClient` exists (~100 lines) but is too thin: no async methods, no capability enforcement, several REST-leaking methods (`*_by_name`, `get_action_history`, `get_action_files_zip`).
- The recently archived `sila-bytes-to-action-files` change established the *transitional* bytes pattern this design proposes to replace.

## Goals / Non-Goals

**Goals:**

- Resolve the seven scope areas of #294 with concrete enough recommendations to write implementation issues.
- Identify open questions explicitly; do not paper over uncertainty.
- Preserve the "side-by-side with full parity until REST removal" transition strategy from #293.
- Surface upstream-contribution candidates distinctly.
- Keep the design pragmatic — a working `Sila2Node` for the existing example device is more valuable than a perfect SiLA-idiomatic spec on day one.

**Non-Goals:**

- Implementing `Sila2Node` or any of the new Features.
- Final disposition of `RestNode` deprecation timing (covered at the project level in #293).
- Redesigning MADSci's experiment, workcell, or location managers around SiLA.
- Decisions about non-SiLA / non-Python lightweight integrations (also project-level in #293).
- A complete FDL draft for the proposed MADSci Features — sketches only; the implementation issues land the FDL.

## Decisions

### 1. SiLA core standards audit — adopt / extend / replace / propose-upstream

The standard `org.silastandard/core` features and the recommended disposition for each:

| Feature | Maturity | Bundled in `sila2` SDK | Disposition | Notes |
|---|---|---|---|---|
| SiLAService | Normative | yes | **Adopt** | Mandatory; covers identity (Name, UUID, Type, Version, VendorURL, Description), feature discovery (ImplementedFeatures, GetFeatureDefinition). Maps onto most of `NodeInfo` identity. |
| LockController v1/v2 | Verified | v1 | **Adopt** | Maps onto `LOCK`/`UNLOCK` admin commands and `NodeStatus.locked`. The `LockIdentifier` Metadata is a richer model than today (today's lock is server-wide unconditional). |
| CancelController | Verified | no | **Adopt** | Maps onto `CANCEL` admin command and per-action cancel. Will require shipping a hand-rolled implementation (or switching SDK) since it's not bundled. |
| PauseController v2 | Verified | no | **Adopt + extend** | Per-execution pause/resume. MADSci's server-wide PAUSE/RESUME maps to "pause every running observable command via PauseController". A `PauseAll`/`ResumeAll` extension is also added to `MadsciAdminController` for atomicity, and proposed upstream as `PauseController v3`. |
| SimulationController | Verified | no | **Adopt** | Optional; a node author may opt in. Does not replace `RestNode`'s implicit simulation patterns. |
| ErrorRecoveryService v2 | Verified | no | **Adopt later** | Richer "recoverable error with continuation options" model. Worth adopting eventually, but not on the critical migration path; the simple `errored=True + errors[]` shape continues to work. |
| AuthenticationService | (varies) | yes | **Defer** | REST has no parity story today. Defer until both protocols can speak it. |
| AuthorizationService | (varies) | yes | **Defer** | Same as above. |
| AuthorizationProviderService | (varies) | yes | **Defer** | Same. |
| AuthorizationConfigurationService | Normative | no | **Defer** | Same. |
| ConnectionConfigurationService | Normative | no | **Skip** | Covers server-initiated client connections; out of scope for the workcell-as-orchestrator architecture. |
| ParameterConstraintsProvider | Verified | no | **Defer** | Useful future addition for richer Parameter validation; not blocking. |

MADSci-specific Features that have no SiLA-core analog:

| MADSci concept | Recommendation | Upstream candidate? |
|---|---|---|
| `SAFETY_STOP` admin command | `MadsciAdminController.SafetyStop` | **Yes** — universal device concern |
| `RESET` admin command | `MadsciAdminController.Reset` | Probably not (semantics too domain-specific) |
| `SHUTDOWN` admin command | `MadsciAdminController.Shutdown` | **Yes** — universal device concern |
| Server-wide `PAUSE`/`RESUME` | `MadsciAdminController.PauseAll`/`ResumeAll` | **Yes** — extension to PauseController |
| `GET_LOCATION` admin command | `MadsciAdminController.GetLocation` (or move to a MADSci-Locations Feature) | Not directly; MADSci-specific |
| `NodeStatus` rollup (busy/ready/stopped/disconnected/errors) | `MadsciNodeStatus` Feature with typed Properties | Not yet — wait until shape is proven |
| `NodeInfo` rollup (module_name, module_version, config_schema, intrinsic_locations, location_representation_templates) | `MadsciNodeInfo` Feature | Not yet — these are MADSci-specific concerns |
| Action history | `MadsciActionHistory` Feature, **or** declared client-only and capability-flagged | Open — see Open Question 5 |
| Resources / Log endpoints | Likely stay client-only and capability-flagged off on SiLA | Not appropriate as Features |

### 2. Action → Command mapping

**Default rule:** every method decorated with `@action(...)` produces a SiLA **Observable Command**. This matches existing MADSci semantics — actions today already run on a worker thread, return an `action_id`, support status polling, and may be long-running. Observable Commands are the SiLA primitive for that shape.

**Decorator surface:**

- `@action(...)` — defaults to Observable.
- `@action(observable=False, ...)` — explicit Unobservable. For cheap synchronous actions (read-a-sensor, format-a-string).
- Convenience: `@observable_action(...)` and `@unobservable_action(...)` are thin wrappers that just set `observable=`. Pure ergonomics; same metadata graph.
- The existing `blocking=True/False` kwarg stays orthogonal. It controls MADSci's worker-thread dispatch, not SiLA observability.

**Argument representation:** `type_analyzer.py` already produces `ArgumentDefinition`s from Python type hints. Extend it to emit a SiLA `<Parameter>` schema for each. Pydantic models map to SiLA `<Structure>`s; primitives map to `<Basic>`; lists map to `<List>`; `Path` parameters map to `<Binary>` (see decision 5).

**Return value representation:**

- `ActionJSON` subclasses → fields become typed `<Response>` entries on the Command. Pydantic→SiLA structure rules apply.
- `ActionFiles` subclasses → each `Path` field becomes a `<Response>` of type `<Binary>` (handled via Binary Transfer, see decision 5).
- A void `@action` → no `<Response>`.

**Intermediate status / progress:** SiLA's `IntermediateResponse` maps onto a typed `ActionProgress` model (new, follow-on). MADSci today uses free-form status updates; this becomes a typed channel. Not blocking for the first migration cut.

**Cancellation:** the `CANCEL` admin command and per-action cancel both dispatch to `CancelController.CancelCommand(action_id)` on the server. The action's worker thread receives a cancellation signal it can poll/check (mechanism similar to `asyncio.CancelledError`). gRPC-level stream cancellation is *not* the surface — that only terminates the client subscription, it doesn't tell the server to stop work.

**Error mapping:** MADSci's `Error(message, error_type, traceback)` → SiLA `DefinedExecutionError` if the `error_type` is statically declared on the Command, else `UndefinedExecutionError` carrying the message and traceback. The `@action` decorator gains a `defined_errors=[...]` kwarg so node authors can declare the static error vocabulary; this also lets the generated FDL list `<DefinedExecutionErrors>` entries.

**Locking interaction:** When the node has been `LockServer`'d, every action call must carry the `LockIdentifier` Metadata. `SilaNodeClient.send_action` propagates the lock identifier (held in client state after a successful `LockServer`) automatically. Action authors don't need to think about it.

**Action ID:** SiLA assigns a `CommandExecutionUUID` to every observable command. MADSci's `ActionRequest.action_id` (a ULID) is the canonical client-side ID; we map it 1:1 onto the SiLA UUID by passing the action_id at command-create time. Mapping is held in `_running_commands`.

### 3. State → Properties decomposition

Three layers, opt-in for the typed path, deprecated-shim for the legacy path:

```
Layer 1 (preferred, new): declared typed Properties
─────────────────────────────────────────────────────
class MyNode(Sila2Node):
    temperature: Property[float] = property_field(observable=True)
    lid_open:    Property[bool]  = property_field()
→ generates SiLA <Property> entries with the correct DataType
→ updates push to subscribed clients (when observability is enabled)
→ also surfaced in the get_state() projection for back-compat

Layer 2 (transitional): legacy state_handler shim
─────────────────────────────────────────────────
state_handler() sets self.node_state = {...}  (existing API, unchanged)
→ exposed as MadsciState.LegacyState : String  (JSON-encoded)
→ persistent deprecation warning on first state_handler call AND in the
  generated NodeInfo (so consumers see the deprecation in tooling)
→ scheduled for removal before 1.0

Layer 3 (consumer-facing): AbstractNodeClient.get_state() projection
────────────────────────────────────────────────────────────────────
The get_state() result merges:
- typed Properties (read via .get()) keyed as "FeatureName.PropertyName"
- legacy state (parsed from MadsciState.LegacyState JSON), keyed as in
  the original state dict (no "MadsciState." prefix, for back-compat)
→ single dict[str, Any], same shape as today
```

**Feature grouping:** the rule of thumb is "if you'd give it its own README section, give it its own Feature." A node author may declare multiple Features per node (e.g. a microscope might expose `Imaging`, `StagePosition`, `Illumination` as three Features). The framework supports but does not require this. Default for a node that declares no explicit Features: a single Feature named after the module identifier.

**Property observability (subscribe vs. poll):** SiLA's `Observable=Yes` Properties push changes as a gRPC stream. Adopting this adds a real subscribe-style capability to MADSci, replacing today's poll loop in the workcell scheduler. **Out of scope for the first migration cut**, but the shape worth being explicit about so we don't paint ourselves into a corner — see decision 8.

### 4. NodeStatus and NodeInfo evolution

This is the load-bearing decomposition and **should be split into its own follow-up subissue**. The shape sketched here is the design direction; the exact field-by-field FDL is the subissue's job.

**NodeStatus decomposition:**

```
Today's NodeStatus (one Pydantic blob):
  busy, running_actions, paused, locked, stopped,
  errored, disconnected, errors[], active_actions, ready

▼ projection by SilaNodeClient.get_status() ▼

Sourced from standard SiLA features:
  LockController.IsLocked              → locked
  PauseController.PausedCommands       → paused (any non-empty → True)
  ErrorRecoveryService.RecoverableErrors → errored (when present)

Sourced from observable command tracking (client-side):
  _running_commands keys               → running_actions, busy

Sourced from connection state (client-side):
  gRPC channel health                  → disconnected

Sourced from MadsciNodeStatus Feature (NEW MADSci Feature):
  Ready : Boolean (Observable)         → ready
  Stopped : Boolean (Observable)       → stopped (set after SafetyStop)
  Errors : List<MadsciError> (Obs.)    → errors[]
```

The `NodeStatus` Pydantic model on `AbstractNodeClient` stays — it just becomes a projection, not a primitive carried in a single response.

**NodeInfo decomposition:**

```
Today's NodeInfo (one Pydantic blob):
  node_name, node_id, module_name, module_version, node_type,
  capabilities, actions{}, config, config_schema,
  intrinsic_locations[], location_representation_templates[]

▼ projection by SilaNodeClient.get_info() ▼

Sourced from SiLAService:
  ServerName, ServerType, ServerUUID, ServerVersion,
  ServerDescription, ServerVendorURL → identity fields
  ImplementedFeatures + GetFeatureDefinition → actions{} introspection

Sourced from MadsciNodeInfo Feature (NEW MADSci Feature):
  ModuleName, ModuleVersion : String → module_*
  ConfigSchema : String (JSON) → config_schema
  Config : String (JSON) → config (current values)
  IntrinsicLocations : List<MadsciLocationDef> → intrinsic_locations
  LocationRepresentationTemplates : List<...> → templates
  NodeType : String → node_type
  Capabilities : MadsciCapabilities → capabilities
```

This keeps the consumer-facing Pydantic shape unchanged; the projection lives entirely in `SilaNodeClient.get_info()`.

### 5. File and binary handling

Replace the `__madsci_bytes__` sentinel pattern (transitional) with native SiLA Binary Transfer end-to-end:

- **`ActionFiles` parameters (input):** each `Path` field on the parameter type becomes a SiLA `<Parameter>` of type `<Binary>`. `SilaNodeClient.send_action()` reads the file bytes and passes them as `Binary` parameter values; the SDK chunks anything > 2 MiB transparently via the Binary Transfer service.
- **`ActionFiles` responses (output):** each `Path` field on the result type becomes a SiLA `<Response>` of type `<Binary>`. `SilaNodeClient` reads the binary, writes it under `~/.madsci/sila_files/{action_id}/{name}` (same directory the transitional code uses), and surfaces it as an `ActionFiles` on the resulting `ActionResult`. Consumers see the same `ActionFiles(Path)` shape as on REST.
- **MIME / extension:** SiLA's `Binary` doesn't carry MIME. We default to whatever extension the original `Path` field name carries, falling back to `.bin`. A future improvement could add a SiLA `<DefinedDataTypeIdentifier>` with a `MimeType` constraint, but it's not required.
- **Migration story for the transitional pattern:** the existing `__madsci_bytes__` sentinel + post-hoc file extraction stays working as a fallback when an action returns raw `bytes` instead of an `ActionFiles` field. Emits a deprecation warning. Removed before 1.0.

### 6. Admin Commands as a SiLA Feature

The dispatch table (client-side) and the resulting Feature surface (server-side):

```
AdminCommand    → SiLA target
─────────────     ───────────────────────────────────────────
LOCK            → LockController.LockServer(LockIdentifier=<auto>)
UNLOCK          → LockController.UnlockServer(<auto>)
CANCEL          → CancelController.CancelAll()  (or .CancelCommand(id))
PAUSE           → MadsciAdminController.PauseAll()
                  (server-side iterates running observables, calls
                   PauseController.Pause for each)
RESUME          → MadsciAdminController.ResumeAll()
                  (mirrors PauseAll)
SAFETY_STOP     → MadsciAdminController.SafetyStop()
RESET           → MadsciAdminController.Reset()
SHUTDOWN        → MadsciAdminController.Shutdown()
GET_LOCATION    → MadsciAdminController.GetLocation()
                  (or MadsciLocations.GetLocation if/when split off)
```

`MadsciAdminController` Feature shape (sketch — the implementation issue lands the actual FDL):

```xml
<Feature Identifier="MadsciAdminController" Originator="org.madsci"
         Category="core" FeatureVersion="1.0" MaturityLevel="Draft">
  <Command><Identifier>SafetyStop</Identifier> ...</Command>
  <Command><Identifier>Reset</Identifier> ...</Command>
  <Command><Identifier>Shutdown</Identifier> ...</Command>
  <Command><Identifier>PauseAll</Identifier> ...</Command>
  <Command><Identifier>ResumeAll</Identifier> ...</Command>
  <Command><Identifier>GetLocation</Identifier> ...
    <Response><Identifier>Location</Identifier>
      <DataType><Basic>String</Basic></DataType>  <!-- JSON or struct -->
    </Response>
  </Command>
  <DefinedExecutionError>
    <Identifier>OperationNotSupported</Identifier> ...
  </DefinedExecutionError>
</Feature>
```

**Authoring API on the server side:**

```python
class MyNode(Sila2Node):
    @admin_command(AdminCommands.SAFETY_STOP)
    def safety_stop(self) -> None: ...

    @admin_command(AdminCommands.RESET)
    def reset(self) -> None: ...
```

The decorator registers the method against the `MadsciAdminController` Feature. Node authors don't write FDL — the framework generates it from the decorator metadata, same way `@action` works.

**Upstream-contribution candidates:** `SafetyStop` and `Shutdown` should be proposed to the SiLA standards body as a new core feature (working title: `DeviceAdministrationController`). `PauseAll`/`ResumeAll` are an obvious extension to the existing PauseController and should be proposed as PauseController v3. `Reset` is too domain-specific to propose; keep MADSci-only.

### 7. AbstractNodeClient abstraction story

Two structural problems to solve before SilaNodeClient and RestNodeClient are interchangeable:

**A. Async parity.** RestNodeClient has 30+ `async_*` methods via `DualModeClientMixin`; SilaNodeClient has zero. Recommendation: add async parity to `SilaNodeClient` by wrapping sila2 SDK calls in `asyncio.to_thread()`. Acceptable performance for the typical workcell scheduler load. When sila2 grows native async (on their roadmap), revisit.

**B. Capability negotiation.** `NodeClientCapabilities` exists but is ornamental — consumers (Workcell scheduler, UI, CLI) do `if hasattr(client, ...)` or rely on `NotImplementedError`. Recommendation: `AbstractNodeClient.send_admin_command(...)` (and peers) raise a typed `CapabilityNotSupported(method, client_type)` exception when the supported_capabilities bit is False, before dispatching. Consumers check the bit; the abstraction enforces it.

**Method surface tightening:**

| Method | Status | Action |
|---|---|---|
| `*_by_name` family | REST-leaking | Remove from `AbstractNodeClient`; promote to `RestNodeClient`-only with a documented capability bit |
| `get_action_history` | REST-only today | Decide via Open Question 5 — either lift to a SiLA Feature, or accept as REST-only |
| `get_action_files_zip` | REST-only | Stay REST-only; SiLA fetches files individually via Binary Transfer |
| `set_config` | both can support | SiLA path: write through `MadsciNodeInfo.Config` Property (writable) |
| `get_resources` | REST-only today | Decide via Open Question 5 |
| `get_log` | REST-only today | Likely stays REST-only; logs are out-of-band on SiLA (an EventManager concern) |
| `get_action_status` / `get_action_result` / `await_action_result` | both | Already in both; tighten signatures |
| `close` / `async_close` | both | Add `async_close` to `AbstractNodeClient` |

**`ActionRequest.action_name` semantics:** today freeform. Recommendation: keep freeform, document that nodes resolve it deterministically. Cross-protocol portable action names are a node-author concern, not a framework concern. SiLA resolves via `_resolve_sila_command` (qualified `Feature.Command` or unambiguous short form); REST resolves via route map.

### 8. Property observability — push semantics (sketched, not adopted in v1)

Documented here so the abstraction we ship in v1 doesn't preclude push later. Adoption is **deferred**; the immediate `SilaNodeClient.get_state()` / `get_status()` paths continue to poll.

What push would look like in `AbstractNodeClient`:

```python
class AbstractNodeClient:
    def subscribe_state(
        self,
        on_change: Callable[[str, Any], None],
        keys: Optional[Iterable[str]] = None,
    ) -> SubscriptionHandle:
        """Subscribe to state changes. on_change(key, new_value) fires per update."""

    def subscribe_status(
        self,
        on_change: Callable[[NodeStatus], None],
    ) -> SubscriptionHandle:
        """Subscribe to status changes. on_change(new_status) fires per update."""
```

Wire layer:

- `SilaNodeClient` — for each `Observable=Yes` Property of interest, the SDK exposes `feature.PropertyName.subscribe(callback)` returning a stream subscription. The client multiplexes those into one `subscribe_state` callback per MADSci consumer, projecting SiLA `FeatureName.PropertyName` events onto MADSci state-dict keys.
- `RestNodeClient` — for parity, implement subscribe-style as a poll loop hidden inside the client (configurable interval). Consumers see the same callback API; the cost is just latency. This avoids "you can subscribe on SiLA but must poll on REST" leaking into consumer code.

Data flow (push path):

```
   SiLA server                Sila2Node                  SilaNodeClient                consumer
   ───────────                ─────────                  ──────────────                ────────
   Property change            framework picks up         gRPC stream callback          on_change(key, val)
        │                     value via observable           │                            │
        ▼                     SDK plumbing                   │                            │
   <Observable Property                                      │                            │
    PropertyName>      ─────────────────────────────▶  feature.X.subscribe()  ──────▶  callback dispatch
                                                            │
                                                       project FeatureName.X
                                                       into state-dict key
```

Workcell scheduler implications: today the scheduler polls `get_status()` every N seconds. With push, it'd subscribe once at node-attach time and react to `NodeStatus` deltas. **Important:** the scheduler still needs a fallback poll (a heartbeat) to detect dead-channel cases — push subscriptions can silently fail if the gRPC stream dies. So the v1 polling code is not wasted; it becomes the heartbeat in v2.

Why we're deferring even though we now have a sketch:

- The benefits accrue mostly to UI responsiveness (status changes visible faster) and request-load reduction. Neither is a blocker today.
- Adopting it requires the scheduler, UI, CLI, and experiment apps to all add subscribe paths. Big consumer-side change — appropriate for its own follow-up.
- Push semantics on top of polling-only `RestNodeClient` is awkward to implement well during the transition window.

The implementation issue list (`tasks.md`) has a follow-up issue (`#M`) to add push observability after `Sila2Node` is in production.

## Risks / Trade-offs

- **SDK gap.** The bundled `sila2` SDK doesn't ship CancelController, PauseController, or SimulationController. We either (a) hand-roll the implementations against the published FDL (works, modest code), (b) switch to `unitelabs-sila` if it ships them (need to verify, may bring API churn), or (c) fork-and-vendor the missing features. Recommend (a) for the first cut; revisit SDK choice as part of the implementation work. **Risk:** a hand-rolled implementation of a "standard" feature is fragile against future SDK changes. **Mitigation:** the FDL is canonical and stable; the implementation just wires it up.
- **Pydantic-to-FDL generation is non-trivial.** `type_analyzer.py` does some of the work today, but the SiLA FDL is richer (constraints, units, observables, defined errors). The first cut accepts a slightly lossy mapping (no constraints, no units, basic types only) and adds richness incrementally.
- **Binary Transfer for file inputs requires the parameter type to be `Binary` at the FDL level.** Today's REST-side `ActionFile` is implemented via a separate file-upload endpoint after action create. The SiLA shape is structurally different — files are *part of the parameter set*. This is fine for new code; for migrating an existing REST-style node, the action body needs to receive files as bytes/Path arguments instead of fishing them out of a separate dict. The migration guide must call this out.
- **Server-wide `PauseAll` is racy.** Iterating running observables and calling `PauseController.Pause(uuid)` for each is not atomic. New commands can start in between. **Mitigation:** combine with a server-side `accept_new_commands=False` flag flipped before the iteration. Document the semantics.
- **Property observability later, polling now.** Adopting SiLA's push semantics later means consumers (Workcell scheduler) keep polling for the first cut. Adds latency to status-change visibility. Acceptable for v1; prioritized for follow-up.
- **`MadsciNodeStatus` and `MadsciNodeInfo` are large Features.** They risk becoming a junk drawer. The follow-up subissue should keep them disciplined — typed Properties for everything, no string-encoded JSON blobs (the legacy `state` shim is the only sanctioned escape hatch).
- **`CommandExecutionUUID` collision.** SiLA UUIDs are server-assigned; MADSci `action_id`s are client-assigned (ULIDs). Mapping the two means we either (a) ignore SiLA's UUID and key everything by `action_id`, or (b) keep both and translate. Recommend (a) — `action_id` is the canonical key; SiLA's UUID is an internal SDK detail. Risk: if a non-MADSci SiLA client also talks to the same server, its `CancelController.CancelCommand(uuid)` wouldn't be honored unless we accept either ID. Acceptable trade-off for MADSci-managed nodes.

## Resolved Decisions

The eight forks-in-the-road called out during the exploration, with their resolutions. Each links back to the parts of the design they shape.

### RD1 — Async sila2: wrap with `to_thread()` now

`sila2` is sync today; native async is on their roadmap (timeline unclear). Wrapping with `asyncio.to_thread()` gives us `async_*` parity immediately at the cost of an extra threadpool hop per call. Acceptable for typical workcell load. **When upstream ships native async, we adopt it.** Affects implementation issue #B.

### RD2 — One `MadsciAdminController` Feature for now

Single Feature is simpler for the framework and for node authors. Can subdivide later if upstream review of our contribution candidates (`SafetyStop`/`Shutdown` and `PauseAll`/`ResumeAll`) pushes us toward separate Features. Affects implementation issue #D.

### RD3 — NodeStatus/NodeInfo evolution is its own follow-up subissue

The field-by-field decomposition is the load-bearing design call for consumer behavior (Workcell scheduler, UI, CLI all read `NodeStatus`/`NodeInfo`). Doing it in the same PR as `Sila2Node` would balloon scope. This proposal commits to the *direction* (projection in `AbstractNodeClient` over a mix of standard + MADSci-specific Features per design §4); the subissue ratifies the field-by-field FDL. Implementation issue #G.

### RD4 — Property observability (push) deferred to v2

Sketched in design §8 so the abstraction we ship in v1 doesn't preclude push later. Adoption deferred — v1 keeps polling. The push capability has its own follow-up implementation issue #M.

### RD5 — Action history and log get MADSci Features; resources capability is dropped

- **Action history** → new `MadsciActionHistory` Feature (UI depends on it).
- **Log** → new `MadsciNodeLog` Feature.
- **Resources capability** → **removed wholesale** from `AbstractNodeClient`, not just on the SiLA path. Confirmed unused; the Resource Manager owns resources, node-direct queries are a REST artifact that should never have been exposed to begin with.

This *expands* the work in P3 (was one feature, now two) and *contracts* the work in P1 (`get_resources` deletion is bookkeeping, not feature work). Affects implementation issues #B, #G, #H.

### RD6 — Cancel always means `CancelController.CancelCommand`

gRPC stream cancel terminates the SDK observable subscription on the client; it doesn't tell the server to stop work — that's `CancelController`. The two are separate concepts that happen to share terminology. The MADSci client always calls `CancelController.CancelCommand(action_id)`; gRPC-level cancel is not surfaced as a MADSci concept. Affects implementation issue #E.

### RD7 — Legacy `state` keys appear under `MadsciState.LegacyState.<key>` (namespaced)

When `SilaNodeClient.get_state()` projects the legacy state blob, keys appear under the `MadsciState.LegacyState.<key>` prefix — *not* hoisted to the top level. This:

- Forces existing consumers to update their state-dict reads as part of the migration (`state["temperature"]` → `state["MadsciState.LegacyState.temperature"]`). No silent back-compat.
- Keeps the keying rule consistent: every key in the projected dict is `FeatureName.PropertyName.*`.
- Eliminates the collision hazard between a typed `Imaging.Temperature` Property and a legacy `temperature` key.
- Consumer-side migration cost is acceptable — direct state-dict reads are not widely used in the consumer surface, and the namespaced keys steer authors hard toward typed Properties.

Affects implementation issue #F.

### RD8 — Stay on `sila2`; vendor missing core Features and contribute upstream

The "missing standard features" gap (CancelController, PauseController, SimulationController, ErrorRecoveryService) is identical across all candidate Python SDKs (`sila2`, `unitelabs-sila`, UniteLabs CDK). Switching SDKs doesn't fix it. `sila2` is the gitlab-canonical reference Python SDK with the most mature introspection (`SiLAService.ImplementedFeatures` + `GetFeatureDefinition`) and binary transfer support that we already lean on in the existing `SilaNodeClient`. Authoring style differences across SDKs are invisible to MADSci node authors because *we* are the decorator layer.

**Vendor-and-PR strategy:** for each missing standard Feature, MADSci ships the implementation under `madsci.common.sila_features.<feature_name>` (matching the canonical FDL) AND files a PR upstream against `sila2`. When upstream merges, our `Sila2Node` runtime prefers the upstream implementation:

```python
try:
    from sila2.features.cancel_controller import CancelControllerBase
except ImportError:
    from madsci.common.sila_features.cancel_controller import CancelControllerBase
```

The vendored copies retire themselves cleanly when upstream PRs land. Each vendored module carries a `# TODO: remove when sila2 merges <PR-link>` marker.

Why this over a hard fork: forks rot, couple our release cadence to upstream's, and require either local-only fork use (awkward) or PyPI republishing (more awkward). Vendor-and-PR achieves the same upstream-citizenship outcome without the maintenance burden.

Side-effect cleanup: the misleading `ImportError` hint in `sila_node_client.py` (currently says "install unitelabs-sila") gets corrected. Affects implementation issue #E and a small cleanup in #294 close-out.

## Implementation issue list

See `tasks.md` for the draft list of downstream implementation issues to open against #293.

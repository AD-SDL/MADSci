## Tasks for this exploration deliverable

This change is design-only. The tasks below are the steps to *finish the exploration*, not implementation work.

- [ ] 1. Open issues for the deliverables below against #293 (P1 → P5)
- [ ] 2. Cross-link each new issue to this proposal as design rationale
- [ ] 3. Close #294 once issues 1.x exist and reference back here

## Downstream implementation issues to open against #293

Each item below is one implementation issue. Each issue lands its own OpenSpec change with concrete spec deltas at implementation time.

### P1 — Foundation

- [ ] **#A — `Sila2Node` base class + decorator surface**
  - Implement `Sila2Node(AbstractNode)` with action-as-Observable-Command default.
  - Add `observable=True/False` kwarg to `@action`; ship `@observable_action` / `@unobservable_action` sugar.
  - Add `defined_errors=[...]` kwarg to `@action` for static error vocabulary.
  - Generate a SiLA Feature (FDL) per node from the decorated methods.
  - Wire ULID `action_id` ↔ SiLA `CommandExecutionUUID` mapping.
  - Tests: example-server-style node with one of each (Observable/Unobservable; with/without args; with errors).
  - Spec deltas: NEW capability `sila2-node`.

- [ ] **#B — `AbstractNodeClient` capability enforcement + async parity + surface tightening**
  - Add `CapabilityNotSupported` exception type.
  - `AbstractNodeClient` methods raise it when `supported_capabilities` says no.
  - Add `async_*` methods to `SilaNodeClient` (wrap sync SDK calls in `asyncio.to_thread()`); revisit when `sila2` ships native async.
  - Add `async_close()` to the abstract interface.
  - Remove `*_by_name` and `get_action_files_zip` from the abstract surface; document them as REST-only.
  - **Remove `get_resources` and the `get_resources` capability bit wholesale** (per RD5 — confirmed unused; resources live in the Resource Manager).
  - Tests: capability checks raise; async parity with the existing notebook flow.
  - Spec deltas: MODIFIED `sila-client-dispatch`, `sila-command-execution`, `sila-server-introspection`.

- [ ] **#C — Migrate file/binary handling to SiLA Binary Transfer**
  - `ActionFiles` parameters → SiLA `<Parameter>` of type `<Binary>`.
  - `ActionFiles` responses → SiLA `<Response>` of type `<Binary>`.
  - `SilaNodeClient.send_action()` reads file inputs, encodes as `Binary`; SDK chunks > 2 MiB transparently.
  - `SilaNodeClient` writes binary responses to `~/.madsci/sila_files/{action_id}/{name}` and surfaces via `ActionFiles`.
  - Keep the `__madsci_bytes__` sentinel pattern as a deprecated fallback; emit warning.
  - Tests: round-trip a small (< 2 MiB) and a large (> 2 MiB) file in both directions.
  - Spec deltas: MODIFIED `sila-command-execution`; deprecation note on `sila-bytes-handling`.

### P2 — Standard SiLA Features

- [ ] **#D — `MadsciAdminController` Feature + `send_admin_command` dispatch**
  - Author the `MadsciAdminController` FDL (SafetyStop, Reset, Shutdown, PauseAll, ResumeAll, GetLocation).
  - Server-side: `@admin_command(AdminCommands.X)` decorator registers methods against the Feature.
  - Client-side: `SilaNodeClient.send_admin_command(cmd)` dispatches via the table in design.md §6.
  - Tests: each admin command works end-to-end against the example server.
  - Spec deltas: NEW capability `madsci-admin-feature`.

- [ ] **#E — Adopt `LockController`, `CancelController`, `PauseController` in `SilaNodeClient` (vendor-and-PR)**
  - Per RD8: vendor implementations under `madsci.common.sila_features.{lock_controller,cancel_controller,pause_controller}` matching the canonical `org.silastandard/core` FDL.
  - File upstream PRs against `sila2` for each (CancelController and PauseController are not bundled; LockController is bundled at v1 — vendor v2 only if needed).
  - `Sila2Node` runtime prefers the upstream import where present, falls back to the vendored copy. Each vendored module carries a `# TODO: remove when sila2 merges <PR-link>` marker.
  - `SilaNodeClient` reads `IsLocked`, `PausedCommands` into the projected `NodeStatus`.
  - `LockController.LockServer` returns a `LockIdentifier` the client retains; subsequent action calls auto-attach it as `LockIdentifier` Metadata.
  - `CancelController.CancelCommand(action_id)` is the surface for action cancel (not gRPC stream cancel — see RD6).
  - Side-effect cleanup: fix the misleading `unitelabs-sila` hint in the existing `SilaNodeClient` `ImportError`.
  - Tests: lock/unlock; cancel a running observable; pause/resume; verify upstream-fallback path.
  - Spec deltas: NEW capabilities for each adopted feature wrapper.

- [ ] **#F — Legacy `state_handler` shim**
  - Expose `node_state` dict as `MadsciState.LegacyState : String` (JSON-encoded).
  - Persistent deprecation warning on first `state_handler` invocation AND in the generated `NodeInfo`.
  - `SilaNodeClient.get_state()` projects typed Properties + parsed legacy state into one `dict[str, Any]`. Per RD7, **legacy keys appear under `MadsciState.LegacyState.<key>` namespacing — not hoisted to top level**. Existing consumer reads of `state["temperature"]` will need updating to `state["MadsciState.LegacyState.temperature"]` as part of the migration.
  - Migration guide (#I) must call out the consumer-side rename pattern.
  - Tests: state_handler-only node vs. typed-Property-only vs. mixed; verify no top-level hoisting; verify collision-safety (a typed `Foo.Temperature` Property does not collide with a legacy `temperature` key).
  - Spec deltas: NEW capability `madsci-state-shim`.

### P3 — Model evolution (own subissue, per design.md OQ3)

- [ ] **#G — NodeStatus / NodeInfo evolution under SiLA**
  - This is the field-by-field decomposition called out in design.md §4 and OQ3.
  - Author `MadsciNodeStatus` and `MadsciNodeInfo` FDLs.
  - Implement the projection in `SilaNodeClient.get_status()` and `get_info()` over a mix of standard SiLA Features and the new MADSci Features.
  - Update consumers (Workcell scheduler, UI, CLI, experiment apps) to consume the projected models — they shouldn't change, but verify.
  - Spec deltas: NEW capabilities `madsci-node-status-feature`, `madsci-node-info-feature`; MODIFIED `sila-server-introspection`.

- [ ] **#H — `SimulationController` (vendor-and-PR) + `MadsciActionHistory` Feature + `MadsciNodeLog` Feature** *(later, lower priority)*
  - Per RD8: vendor `SimulationController` under `madsci.common.sila_features.simulation_controller` matching the canonical FDL; file upstream PR; `Sila2Node` opt-in via decorator.
  - Per RD5: author `MadsciActionHistory` Feature (UI depends on `get_action_history` parity).
  - Per RD5: author `MadsciNodeLog` Feature (replaces `RestNodeClient.get_log`).
  - Note on RD5: `get_resources` removal is handled in #B (capability bit dropped wholesale, not migrated to a Feature).

### P4 — Author experience

- [ ] **#I — Migration guide: `RestNode` → `Sila2Node`**
  - Per-pattern recipes (action with args, action with file input, action with file output, state vs. typed Properties, admin commands).
  - Call out the structural differences (file inputs as Parameters, not separate uploads; cancel via CancelController; lock via LockController).
  - Land in `docs/guides/`.

- [ ] **#J — Migrate 2–3 example nodes end-to-end**
  - Per the success criteria in #293: at least 2–3 real device integrations validated end-to-end on the SiLA path.
  - Candidates: the existing `sila_example_server` (already SiLA), plus two of the higher-traffic REST nodes from the example lab.
  - Each migration is its own PR; all reference this design and the migration guide.

### P5 — Upstream-contribution candidates

- [ ] **#K — Propose `DeviceAdministrationController` (SafetyStop, Shutdown) to SiLA standards body**
  - Draft FDL based on the `MadsciAdminController` shape.
  - Open a discussion on the SiLA-2 working-group channels.
  - This is *outreach*, not implementation; tracked separately so it doesn't gate MADSci work.

- [ ] **#L — Propose `PauseController v3` (PauseAll, ResumeAll) to SiLA standards body**
  - Same shape as #K. Targeted as an extension to the existing `PauseController`.

- [ ] **(P5 — bundled with #E and #H) — File upstream `sila2` PRs for the vendored core Features**
  - Per RD8: as part of #E (CancelController, PauseController, optionally LockController v2) and #H (SimulationController, ErrorRecoveryService when adopted), file PRs against `gitlab.com/SiLA2/sila_python` upstreaming the vendored implementations.
  - Track each PR in the relevant module's `# TODO: remove when sila2 merges <PR-link>` marker.
  - When merged, drop the vendored module; the runtime fallback chain (`try: from sila2.features ... except ImportError: from madsci.common.sila_features ...`) automatically prefers upstream.

### P6 — Future (post-v1)

- [ ] **#M — Property observability (push) adoption**
  - Per RD4 / design §8: add `subscribe_state` and `subscribe_status` to `AbstractNodeClient`.
  - SiLA path uses gRPC streams from `Observable=Yes` Properties.
  - REST path uses internal poll loop hidden behind the same callback API (parity-preserving).
  - Workcell scheduler migrates from `get_status()` polling to subscribe + heartbeat poll.
  - Spec deltas: NEW capability `madsci-node-subscribe`; MODIFIED `sila-server-introspection`.

## Resolution of #294

#294 is the exploration deliverable for #293. It is closed when:

1. This OpenSpec change (`sila2-native-node-design`) is reviewed and accepted (or accepted with explicitly-noted open questions resolved).
2. Implementation issues #A–#L (or whatever subset survives review) are open against #293, each cross-linked back to this proposal.
3. The misleading `ImportError` hint in `sila_node_client.py` is corrected to match the actual install path (`pip install "madsci.client[sila]"` resolves to `sila2`, not `unitelabs-sila`). This is a one-line fix bundled with #E (per RD8); if #E slips, do it as a standalone close-out fix.

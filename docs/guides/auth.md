# Authentication & Authorization (Auth Manager)

> **Status:** Foundation (v0.8). Default-disabled. Per-deployment opt-in.

## Architecture

MADSci's Auth Manager (port **8007**) is a per-lab, single-tenant OAuth 2.0 + OIDC-style identity service:

```
+-------------+        +---------------+         +-------------------+
|  User       | login  |  Auth Manager | issues  |  Other Managers   |
|  Service    +------->+  (port 8007)  +-------->+  + Nodes          |
|  Node       |        |               | JWT     |  (verify via JWKS)|
+-------------+        +-------+-------+         +-------------------+
                               |                            ^
                               | revoke -> /deny-list       | poll
                               +----------------------------+
```

**Key properties:**

- **RS256 JWT access tokens** (15-min default TTL) signed by a rotating keypair, verified at every consuming manager via cached JWKS — no per-request introspection round-trip.
- **Opaque refresh tokens** stored server-side, rotated on every refresh, with reuse-detection.
- **Lab-scoped (1:1 with Lab Manager).** `aud = lab_id`, `iss = <auth_server_url>`. Tokens from one lab are unintelligible to another (cross-lab federation deferred to the Globus/ORCID follow-on).
- **RBAC with project scoping.** Roles bundle permissions in the canonical `<resource>.<action>` namespace; users hold roles within projects; service accounts and nodes hold roles globally.
- **Persistent deny-list.** Revoked `jti` values live in PostgreSQL and are served via `GET /deny-list` with `ETag` / `If-None-Match` conditional fetch. Consumers poll every 30s by default.

## Token model

Every access token includes the standard JWT claims (`iss`, `aud`, `sub`, `iat`, `exp`, `jti`) plus MADSci-specific claims:

| Claim            | User token | Service-account token | Node token | Notes                                    |
|------------------|------------|----------------------|-----------|------------------------------------------|
| `principal_type` | `user`     | `service_account`    | `node`    |                                          |
| `roles`          | ✓          | ✓                    | ✓         | Role IDs                                 |
| `permissions`    | ✓          | ✓                    | ✓         | Flattened permission strings             |
| `user_id`        | ✓          | —                    | —         |                                          |
| `project_ids`    | ✓          | —                    | —         | Memberships at issuance                  |
| `manager_id`     | —          | ✓                    | —         | Distinct from `sub`/`client_id`          |
| `node_id`        | —          | —                    | ✓         |                                          |
| `workcell_id`    | —          | —                    | ✓ (opt.)  |                                          |

`OwnershipInfo.from_jwt_claims(claims)` is the canonical mapping from these claims to MADSci's existing `OwnershipInfo` type (used by `AuthMiddleware` to populate `request.state.principal` and the ambient `ownership_context`).

## Permission namespace

Defined in `madsci.common.auth_decorators.PERMISSION_NAMESPACE`:

| Permission                | Grants                                       |
|---------------------------|----------------------------------------------|
| `*`                       | Full administrative privileges               |
| `experiment.read/write`   | Experiment metadata                          |
| `workflow.read/submit`    | Workflow definitions and submission          |
| `resource.read/write`     | Resource state and inventory                 |
| `workcell.read/execute`   | Workcell config and admin commands           |
| `node.read/execute_action`| Node status / action submission              |
| `event.read`              | Event log queries                            |
| `auth.user.write`         | User CRUD on the Auth Manager                |
| `auth.role.write`         | Role grant / revoke                          |
| `auth.key.rotate`         | Signing-key rotation                         |

The built-in roles seeded by `madsci auth bootstrap` are `admin` (`*`), `experimenter`, `operator`, and `read_only`.

## Integration points

### `AuthMiddleware`

`AbstractManagerBase` installs `AuthMiddleware` automatically when the manager's settings have `auth_enabled=True`. The middleware:

1. Extracts `Authorization: Bearer <jwt>`.
2. Verifies signature against cached JWKS from `auth_server_url`.
3. Validates `iss`/`aud`/`exp` and the deny-list.
4. Populates `request.state.principal: Principal | None`.
5. Enters an `ownership_context()` for the request lifetime.

Behavior with `auth_required=False` (the migration mode): unauth'd requests pass through with `request.state.principal = None`, and a structured warning is logged so operators can identify gaps during rollout.

### `AuthClient`

`madsci.client.auth_client.AuthClient` provides:

- `login()`, `refresh()`, `client_credentials_login()`
- `verify_jwt()` — JWKS-cached, force-refresh on signature failure
- `introspect()`, `revoke()`
- Background-friendly deny-list polling (`force_deny_list_refresh()` for tests)
- Admin surface (`create_user`, `register_service_account`, `register_node`, `rotate_keys`, `rotate_credentials`, …)

### Ambient propagation

```python
from madsci.client.auth_client import AuthClient
from madsci.common.auth_context import auth_client_context

with AuthClient(auth_server_url="http://localhost:8007/") as ac:
    ac.client_credentials_login(client_id, client_secret)
    with auth_client_context(ac):
        # Any other MADSci client built via create_httpx_client()
        # automatically receives Authorization: Bearer <jwt>
        events = event_client.get_events()
```

### `@requires` decorator

```python
from madsci.common.auth_decorators import requires
from fastapi import Request

@get("/projects/{project_id}/items")
@requires(permission="experiment.write", project_from="project_id")
async def list_items(self, request: Request, project_id: str) -> list[Item]:
    ...
```

`@requires` returns 401 if no principal is on the request, 403 if the required permission is absent, and 403 if `project_from` is supplied and the principal is not a member of the resolved project.

## Migration plan

See `docs/guides/auth_operator.md` for the operator runbook. The high-level rollout:

1. Deploy Auth Manager; `madsci auth bootstrap`.
2. Register every manager and node; distribute secrets.
3. Set `auth_enabled=True, auth_required=False` on each consuming manager — observe.
4. Flip `auth_required=True` once traffic is clean.
5. Future MADSci release deprecates `auth_required=False` (removed alongside caller-asserted `OwnershipInfo` per Decision 10).

## Follow-on changes

Tracked separately as additional OpenSpec changes:

- `auth-globus-orcid-federation` — upstream IdP federation (cross-lab user identity)
- `auth-node-mtls` — mTLS trust for nodes (slots into the reserved `mtls_cert_fingerprint` field)
- `auth-per-manager-rbac-rollout` — apply `@requires` across every manager endpoint
- `auth-per-principal-aud-narrowing` — narrow the single-`aud` model
- `auth-node-enrollment-tokens` — replace pre-provisioned NodeIdentity registration with kubelet-bootstrap-style enrollment
- `auth-registry-and-auth-cli-merge` — optional CLI convenience that does `madsci registry add` + `madsci auth node register` atomically

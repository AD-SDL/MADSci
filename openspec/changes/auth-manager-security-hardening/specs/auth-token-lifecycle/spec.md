## ADDED Requirements

### Requirement: JWT verification pins RS256

Every JWT verification path — `token_service.verify_token` on the Auth Manager and `AuthClient` token verification on the consumer side — SHALL pass `algorithms=["RS256"]` to the underlying JWT library. Tokens whose JWS header declares any other algorithm (including `none`, `HS256`, `HS384`, `HS512`, `RS384`, `RS512`, `ES256`, etc.) SHALL be rejected with the same error path as a signature failure.

#### Scenario: Token signed with HS256 using public key as secret is rejected
- **GIVEN** an attacker constructs a JWT with `alg=HS256` whose HMAC secret is the lab's RS256 public key (the classic alg-confusion attack)
- **WHEN** the token is presented to either the Auth Manager or any consumer with `AuthMiddleware` enabled
- **THEN** verification SHALL fail and the request SHALL be treated as unauthenticated

#### Scenario: Token with alg=none is rejected
- **GIVEN** a JWT whose JWS header declares `alg=none`
- **WHEN** the token is verified
- **THEN** verification SHALL fail

### Requirement: JWT verification accepts a configurable clock-skew leeway

JWT verification SHALL apply a clock-skew leeway when validating `iat` and `exp`. The default leeway SHALL be 30 seconds. The leeway SHALL be configurable via `AuthManagerSettings.token_clock_skew_seconds` and SHALL be used uniformly by both the Auth Manager's verifier and the consumer-side `AuthClient`.

#### Scenario: Token issued by a slightly-fast issuer verifies on a slightly-slow consumer
- **GIVEN** a token whose `iat` is 5 seconds in the future relative to the verifier's clock
- **WHEN** the token is verified with the default leeway
- **THEN** verification SHALL succeed

#### Scenario: Token outside leeway is rejected
- **GIVEN** a token whose `exp` is 60 seconds in the past and the leeway is 30 seconds
- **WHEN** the token is verified
- **THEN** verification SHALL fail

### Requirement: Refresh-token consumption is atomic and reuse-safe under concurrency

The Auth Manager SHALL consume a refresh token via a single atomic database operation: `UPDATE refresh_tokens SET revoked_at = now(), rotated_to = <new_jti> WHERE token_hash = <hash> AND revoked_at IS NULL RETURNING ...`. If the affected-row count is zero, the implementation SHALL determine whether the row exists in revoked state (reuse) or does not exist (invalid grant), and SHALL fire the family-revocation response on detected reuse.

A partial unique index `refresh_tokens(token_hash) WHERE revoked_at IS NULL` SHALL be added via Alembic migration `0002` to provide a database-enforced invariant.

#### Scenario: Two concurrent refresh requests of the same token — only one succeeds
- **GIVEN** a valid refresh token T held by a client
- **WHEN** the client (or an attacker who stole T) issues two `grant_type=refresh_token` requests for T at the same moment
- **THEN** at most one request SHALL succeed; the other SHALL fail with HTTP 401 and the principal's entire refresh-token family SHALL be revoked

#### Scenario: Reuse of a revoked refresh token revokes the family
- **WHEN** a refresh token whose `revoked_at` is already set is presented
- **THEN** the Auth Manager SHALL respond HTTP 401 AND SHALL revoke every currently-active refresh token for the same `principal_sub`

### Requirement: Refresh-token rotation populates `rotated_to` for forensics

When a refresh token is consumed and a new refresh token is issued, the parent row's `rotated_to` column SHALL be populated with the new token's `jti` (or row identifier). This SHALL be done in the same atomic UPDATE that revokes the parent.

#### Scenario: Parent row links to child after rotation
- **GIVEN** a refresh token T1 is consumed and a new refresh token T2 is issued
- **WHEN** an operator queries the `refresh_tokens` table for T1
- **THEN** T1's `rotated_to` column SHALL contain T2's identifier

### Requirement: Token introspection requires authentication

`POST /introspect` SHALL require an authenticated caller. Unauthenticated callers SHALL receive `{"active": false}` (per RFC 7662 §2.2 — never leak claims to unauthenticated parties). Authenticated callers holding the `auth.token.introspect` permission SHALL receive the full claims response for active tokens.

#### Scenario: Unauthenticated introspect returns inactive
- **GIVEN** no `Authorization` header
- **WHEN** a client posts a valid token to `/introspect`
- **THEN** the response SHALL be HTTP 200 with body `{"active": false}` and SHALL NOT include any claims

#### Scenario: Authenticated, privileged introspect returns claims
- **GIVEN** an authenticated caller whose token includes `auth.token.introspect`
- **WHEN** the caller posts a valid, unrevoked, unexpired token
- **THEN** the response SHALL be HTTP 200 with `{"active": true, ...claims}`

### Requirement: Token revocation requires authentication

`POST /revoke` SHALL require an authenticated caller. A caller MAY revoke a token whose `sub` matches the caller's own `sub`. Revocation of any other principal's token SHALL require the `auth.token.revoke` permission. Unauthenticated revocation requests SHALL be rejected with HTTP 401.

#### Scenario: Unauthenticated revoke is rejected
- **GIVEN** no `Authorization` header
- **WHEN** a client posts any token to `/revoke`
- **THEN** the response SHALL be HTTP 401 and the token SHALL NOT be revoked

#### Scenario: Self-revocation succeeds
- **GIVEN** a caller authenticated as principal P
- **WHEN** the caller revokes a token whose `sub` is P
- **THEN** the token SHALL be revoked and HTTP 200 returned

#### Scenario: Cross-principal revocation requires permission
- **GIVEN** a caller authenticated as principal P with no `auth.token.revoke` permission
- **WHEN** the caller revokes a token whose `sub` is some other principal Q
- **THEN** the response SHALL be HTTP 403 and the token SHALL NOT be revoked

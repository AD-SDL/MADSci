## ADDED Requirements

### Requirement: JWT access token format

The Auth Manager SHALL issue access tokens as JWTs signed with RS256 using the active signing key from its rotating keypair set. Tokens MUST include standard claims `iss` (the Auth Manager URL), `aud` (the deployment's `lab_id` as a single string value, not an array), `sub` (the canonical principal identifier — `user_id` for users, `client_id` for service accounts and nodes), `iat`, `exp`, and `jti`, plus MADSci-specific claims `principal_type` (`user` | `service_account` | `node`), `roles` (list of role ids), `permissions` (flattened list of permission strings), and ownership claims populated as appropriate for the principal type:

- For `user` tokens: `user_id`, `project_ids`, `lab_id`
- For `service_account` tokens: `manager_id` (the operational manager identity this service account represents — distinct from `sub`/`client_id`), `lab_id`
- For `node` tokens: `node_id`, `workcell_id` (when scoped), `lab_id`

The distinction between `sub` (the principal record's id, e.g., `client_id`) and operational identity claims (`manager_id`, `node_id`, `user_id`) preserves the canonical OAuth semantics of `sub` while still letting consuming managers populate `OwnershipInfo` with the operational identifiers they care about.

#### Scenario: Issued token contains required claims
- **WHEN** any token is issued
- **THEN** the JWT SHALL contain at minimum `iss`, `aud`, `sub`, `iat`, `exp`, `jti`, `principal_type`, `roles`, and `permissions` claims

#### Scenario: aud is the deployment's lab_id
- **WHEN** any token is issued, regardless of principal type
- **THEN** the `aud` claim SHALL be a single string equal to the deployment's `lab_id` (per-principal audience narrowing is deferred to a follow-on change)

#### Scenario: Verifier rejects tokens with wrong aud
- **WHEN** a manager verifies a token whose `aud` claim does not match its configured `lab_id`
- **THEN** verification SHALL fail and the request SHALL be treated as unauthenticated

#### Scenario: iss is the lab's Auth Manager URL
- **WHEN** any token is issued
- **THEN** the `iss` claim SHALL be the URL of this lab's Auth Manager (sourced from its `server_url` setting), and verifiers SHALL fetch JWKS from that URL's `/.well-known/jwks.json`

#### Scenario: User token includes project memberships
- **WHEN** a token is issued for a user with project memberships
- **THEN** the JWT SHALL include `project_ids` listing every project the user is a member of at issuance time

#### Scenario: Default access token TTL is short
- **WHEN** an access token is issued without an explicit lifetime override
- **THEN** the `exp` claim SHALL be no more than 15 minutes after `iat`

### Requirement: Password grant for local users

The Auth Manager SHALL expose a token endpoint accepting `grant_type=password` with `username` and `password` form parameters. On success it SHALL return a JSON response containing `access_token`, `refresh_token`, `token_type=Bearer`, and `expires_in`.

#### Scenario: Successful password authentication
- **WHEN** a user submits `grant_type=password` with valid credentials for an active user
- **THEN** the Auth Manager SHALL return HTTP 200 with `access_token`, `refresh_token`, `token_type`, and `expires_in` fields

#### Scenario: Invalid password rejected
- **WHEN** the submitted password fails the Argon2 verification
- **THEN** the Auth Manager SHALL return HTTP 401 and an audit log entry SHALL record the failed attempt

#### Scenario: Inactive user rejected
- **WHEN** the credentials are valid but the user is `is_active=False`
- **THEN** the Auth Manager SHALL return HTTP 401

### Requirement: Refresh grant rotates the refresh token

The Auth Manager SHALL accept `grant_type=refresh_token` with a `refresh_token` parameter. On success, it MUST issue a new access token AND a new refresh token, and MUST revoke the presented refresh token.

#### Scenario: Refresh issues new tokens and revokes the old one
- **WHEN** a client presents a valid, unrevoked refresh token
- **THEN** the Auth Manager SHALL return new `access_token` and `refresh_token` values, persist the new refresh token, and mark the presented refresh token as revoked

#### Scenario: Reuse of a revoked refresh token is detected
- **WHEN** a refresh token that has previously been used (and therefore revoked) is presented
- **THEN** the Auth Manager SHALL return HTTP 401 AND SHALL revoke all currently-active refresh tokens for the same principal as a security response

### Requirement: Client-credentials grant for service accounts and nodes

The Auth Manager SHALL accept `grant_type=client_credentials` with `client_id` and `client_secret` parameters, issuing access tokens (no refresh token) to ServiceAccount and NodeIdentity principals.

#### Scenario: Service account exchanges credentials for a token
- **WHEN** a manager submits its `client_id` and matching `client_secret` with `grant_type=client_credentials`
- **THEN** the Auth Manager SHALL return an access token whose `principal_type` is `service_account` and whose claims include the manager's granted roles

#### Scenario: Wrong client secret rejected
- **WHEN** an incorrect `client_secret` is submitted
- **THEN** the Auth Manager SHALL return HTTP 401 and an audit log entry SHALL record the failed attempt

### Requirement: Token endpoint rate limiting and grant-type validation

The `/token` endpoint SHALL apply per-source-IP rate limiting using the existing `RateLimitMiddleware` infrastructure. The Auth Manager SHALL reject requests whose `grant_type` value is not one of the supported grants (`password`, `refresh_token`, `client_credentials`) with HTTP 400 and SHALL NOT log the request body in the audit log (to avoid persisting bad credentials).

#### Scenario: Unsupported grant_type rejected with 400
- **WHEN** a request to `/token` is submitted with `grant_type=authorization_code` (or any other unsupported value)
- **THEN** the Auth Manager SHALL return HTTP 400 with an `unsupported_grant_type` error response per RFC 6749 §5.2

#### Scenario: Excessive failed attempts rate limited
- **WHEN** a single source IP exceeds the configured failed-token-request threshold within the rate-limit window
- **THEN** subsequent requests from that IP SHALL receive HTTP 429 until the window resets, and an audit log entry SHALL be written

### Requirement: JWKS publication

The Auth Manager SHALL expose a `/.well-known/jwks.json` endpoint returning the public half of every currently-active signing key in standard JWKS format.

#### Scenario: JWKS endpoint returns active public keys
- **WHEN** any client requests `/.well-known/jwks.json`
- **THEN** the Auth Manager SHALL return HTTP 200 with a JWKS document containing the public key material and `kid` for each active signing key

#### Scenario: Endpoint requires no authentication
- **WHEN** an unauthenticated client requests `/.well-known/jwks.json`
- **THEN** the Auth Manager SHALL serve the response without requiring a bearer token

### Requirement: Token introspection

The Auth Manager SHALL expose an OAuth 2.0 Token Introspection endpoint (`POST /introspect`, RFC 7662) accepting a token and returning `active`, `sub`, `exp`, `aud`, `iss`, and the MADSci-specific claims (or `{ "active": false }` for revoked/expired/unknown tokens).

#### Scenario: Active token returns full claims
- **WHEN** a service submits a valid, unrevoked, unexpired access token to `/introspect`
- **THEN** the Auth Manager SHALL return `{ "active": true, ... }` with the token's claims

#### Scenario: Revoked token returns inactive
- **WHEN** a service submits a token whose `jti` has been revoked
- **THEN** the Auth Manager SHALL return `{ "active": false }`

### Requirement: Token revocation and deny-list distribution

The Auth Manager SHALL expose a `POST /revoke` endpoint allowing a principal to revoke its own tokens, and admins to revoke any token. Refresh-token revocation MUST be effective immediately at the Auth Manager. Access-token revocation MUST become effective at all consuming managers within a bounded SLA via a `jti` deny-list distribution mechanism specified below.

The Auth Manager SHALL expose a `GET /deny-list` endpoint returning the set of currently-revoked-but-not-yet-expired access-token `jti` values, with each entry including its `exp` (so consumers can age entries out). The endpoint SHALL support an `If-None-Match` / `ETag` conditional-fetch flow to avoid retransmitting unchanged data. Entries SHALL be removed from the deny-list once their `exp` is in the past, bounding the list size to "currently-issued + revoked + still-valid" tokens.

The deny-list SHALL be **persisted** in the Auth Manager's database (a `revoked_access_tokens` table keyed by `jti` with `exp` and `revoked_at` columns). On Auth Manager startup, the in-memory deny-list cache SHALL be hydrated from this table, filtering out entries whose `exp` is already in the past. Entries SHALL only be deleted from the table once their `exp` is in the past — so a revoked token cannot silently re-validate after an Auth Manager restart.

The `AuthClient` (used by `AuthMiddleware` in every consuming manager) SHALL poll `/deny-list` at a configurable interval (default 30 seconds) and reject tokens whose `jti` appears in the locally-cached deny-list, even when the token's signature and `exp` are otherwise valid.

The revocation-effectiveness SLA at any consuming manager SHALL therefore be bounded by `deny_list_poll_interval + max_clock_skew` (≤ 60 seconds at default settings). Operators requiring tighter bounds MAY shorten the poll interval at the cost of additional load on the Auth Manager.

#### Scenario: User logs out
- **WHEN** a user calls `/revoke` with their refresh token
- **THEN** the refresh token SHALL be revoked, the principal's access-token `jti` SHALL be added to the deny-list for the access-token TTL window, and an audit log entry SHALL be written

#### Scenario: Revoked access token rejected at consuming manager within SLA
- **GIVEN** an access token has been revoked at the Auth Manager
- **WHEN** a request bearing that token reaches a consuming manager AFTER `deny_list_poll_interval` has elapsed
- **THEN** the consuming manager SHALL reject the request with HTTP 401, citing token revocation

#### Scenario: Deny-list bounded by token TTL
- **WHEN** an entry on the deny-list has an `exp` in the past
- **THEN** the entry SHALL be removed from the deny-list response on the next request, bounding response size to currently-revoked-and-still-unexpired tokens

#### Scenario: Conditional-fetch reduces poll cost
- **WHEN** an `AuthClient` polls `/deny-list` with an `If-None-Match` header matching the current `ETag`
- **THEN** the Auth Manager SHALL return HTTP 304 with no body

#### Scenario: Revoked token stays revoked across Auth Manager restart
- **GIVEN** an access token has been revoked at the Auth Manager and the `jti` is in the persisted `revoked_access_tokens` table
- **WHEN** the Auth Manager process restarts
- **THEN** the in-memory deny-list cache SHALL be hydrated from the persisted table on startup and the revoked `jti` SHALL still appear in `GET /deny-list` responses (until its `exp` passes)

### Requirement: Signing-key rotation

The Auth Manager SHALL support multiple active signing keys at once. Operators MUST be able to add a new key (which becomes the active signing key for new tokens) while keeping the old key in JWKS for verification of in-flight tokens, then retire old keys after their tokens have expired.

#### Scenario: Rotate the signing key
- **WHEN** an operator runs `madsci auth keys rotate`
- **THEN** a new keypair SHALL be generated and marked active, the previous key SHALL remain in JWKS marked inactive-for-signing, and tokens issued before rotation SHALL continue to verify until they expire

#### Scenario: Retire a key after grace period
- **WHEN** an operator runs `madsci auth keys retire --kid <old_kid>` and no unexpired token references that key
- **THEN** the key SHALL be removed from JWKS and the private key material SHALL be deleted from persistent storage

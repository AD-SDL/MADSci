## ADDED Requirements

### Requirement: JWT access token format

The Auth Manager SHALL issue access tokens as JWTs signed with RS256 using the active signing key from its rotating keypair set. Tokens MUST include standard claims `iss` (the Auth Manager URL), `aud` (the deployment's `lab_id` as a single string value, not an array), `sub` (the principal id), `iat`, `exp`, and `jti`, plus MADSci-specific claims `principal_type` (`user` | `service_account` | `node`), `roles` (list of role ids), `permissions` (flattened list of permission strings), and ownership claims (`user_id`, `project_ids`, `node_id`, `workcell_id`, `lab_id`) populated as appropriate for the principal.

#### Scenario: Issued token contains required claims
- **WHEN** any token is issued
- **THEN** the JWT SHALL contain at minimum `iss`, `aud`, `sub`, `iat`, `exp`, `jti`, `principal_type`, `roles`, and `permissions` claims

#### Scenario: aud is the deployment's lab_id
- **WHEN** any token is issued, regardless of principal type
- **THEN** the `aud` claim SHALL be a single string equal to the deployment's `lab_id` (per-principal audience narrowing is deferred to a follow-on change)

#### Scenario: Verifier rejects tokens with wrong aud
- **WHEN** a manager verifies a token whose `aud` claim does not match its configured `lab_id`
- **THEN** verification SHALL fail and the request SHALL be treated as unauthenticated

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

### Requirement: Token revocation

The Auth Manager SHALL expose a `POST /revoke` endpoint allowing a principal to revoke its own tokens, and admins to revoke any token. Revocation MUST be effective for refresh tokens immediately and for access tokens on next introspection (or by `jti` deny-list distribution to manager caches).

#### Scenario: User logs out
- **WHEN** a user calls `/revoke` with their refresh token
- **THEN** the refresh token SHALL be revoked, the principal's `jti` SHALL be added to the deny-list for the access-token TTL window, and an audit log entry SHALL be written

### Requirement: Signing-key rotation

The Auth Manager SHALL support multiple active signing keys at once. Operators MUST be able to add a new key (which becomes the active signing key for new tokens) while keeping the old key in JWKS for verification of in-flight tokens, then retire old keys after their tokens have expired.

#### Scenario: Rotate the signing key
- **WHEN** an operator runs `madsci auth keys rotate`
- **THEN** a new keypair SHALL be generated and marked active, the previous key SHALL remain in JWKS marked inactive-for-signing, and tokens issued before rotation SHALL continue to verify until they expire

#### Scenario: Retire a key after grace period
- **WHEN** an operator runs `madsci auth keys retire --kid <old_kid>` and no unexpired token references that key
- **THEN** the key SHALL be removed from JWKS and the private key material SHALL be deleted from persistent storage

## ADDED Requirements

### Requirement: AuthClient pins RS256 on JWT verification

`AuthClient`'s JWT verification path SHALL pass `algorithms=["RS256"]` to the underlying JWT library. Tokens whose JWS header declares any other algorithm SHALL be rejected.

#### Scenario: AuthClient rejects HS256-confused token
- **GIVEN** a token forged with `alg=HS256` using the lab's RS256 public key as the HMAC secret
- **WHEN** `AuthClient.verify(...)` is called on that token
- **THEN** verification SHALL fail and SHALL NOT return claims

### Requirement: Bootstrap CLI accepts password only via prompt or env var

The `madsci auth bootstrap` CLI SHALL NOT accept the admin password as a command-line argument or option. The password SHALL be sourced from one of:

1. The environment variable `MADSCI_AUTH_BOOTSTRAP_PASSWORD`.
2. An interactive prompt with hidden input (using `click.prompt(..., hide_input=True, confirmation_prompt=True)`).

If neither is available (e.g., non-interactive run with no env var), the command SHALL exit non-zero with a clear error message.

#### Scenario: --password flag is rejected
- **WHEN** an operator runs `madsci auth bootstrap --username admin --password hunter2`
- **THEN** the CLI SHALL exit non-zero and SHALL NOT accept the password from argv

#### Scenario: Env var supplies password for automation
- **GIVEN** `MADSCI_AUTH_BOOTSTRAP_PASSWORD=hunter2` is set in the environment
- **WHEN** an operator runs `madsci auth bootstrap --username admin`
- **THEN** the CLI SHALL use the env var value and SHALL NOT prompt

#### Scenario: Interactive prompt for an operator
- **GIVEN** no `MADSCI_AUTH_BOOTSTRAP_PASSWORD` env var and an interactive TTY
- **WHEN** an operator runs `madsci auth bootstrap --username admin`
- **THEN** the CLI SHALL prompt for the password with hidden input and require confirmation

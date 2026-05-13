Module madsci.auth_manager.services.signing_key_service
=======================================================
RSA signing-key management for the Auth Manager.

Implements key generation, persistence, rotation, and JWKS export. RS256 is
the only supported algorithm (per Decision 1).

Functions
---------

`load_pem_private_key(data, password, backend=None, *, unsafe_skip_rsa_key_validation=False)`
:   

`load_pem_public_key(data, backend=None)`
:   

Classes
-------

`SigningKeyService(engine: Any, key_size: int = 2048)`
:   Manage rotating RSA signing keys.
    
    Bind to a SQLAlchemy engine and choose the RSA key size in bits.

    ### Methods

    `generate_keypair(self, *, set_signing: bool = True) ‑> madsci.auth_manager.tables.SigningKeyTable`
    :   Generate a new RSA keypair and persist it.
        
        Args:
            set_signing: If True (default), the new key becomes the
                ``active_for_signing`` key and any previously-signing key is
                downgraded to verify-only.

    `get_key(self, kid: str) ‑> madsci.auth_manager.tables.SigningKeyTable | None`
    :   Look up a signing key by kid.

    `get_signing_key(self) ‑> madsci.auth_manager.tables.SigningKeyTable | None`
    :   Return the currently-active signing key, or None if none exists.

    `jwks(self) ‑> dict[str, list[dict[str, str]]]`
    :   Return a JWKS document for all currently-active keys.

    `list_active_keys(self) ‑> list[madsci.auth_manager.tables.SigningKeyTable]`
    :   All keys currently published in JWKS (i.e., active=True).

    `list_all_keys(self) ‑> list[madsci.auth_manager.tables.SigningKeyTable]`
    :   All keys including retired ones, newest first.

    `load_private_key(self, row: SigningKeyTable) ‑> Any`
    :   Load the private key for signing operations.

    `load_public_key(self, row: SigningKeyTable) ‑> Any`
    :   Load the public key for verification operations.

    `retire(self, kid: str) ‑> bool`
    :   Retire a key (remove from JWKS, delete private material).
        
        Returns True if a row was modified, False otherwise.

    `rotate(self) ‑> madsci.auth_manager.tables.SigningKeyTable`
    :   Generate a new signing key, demoting the current one to verify-only.
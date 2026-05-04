Module madsci.auth_manager.services.password_service
====================================================
Argon2id password hashing helpers.

Classes
-------

`PasswordService(time_cost: int = 3, memory_cost: int = 65536, parallelism: int = 4)`
:   Wrapper around argon2-cffi for password hashing and verification.
    
    Configure the underlying ``argon2.PasswordHasher``.

    ### Methods

    `hash_password(self, password: str) ‑> str`
    :   Hash a plaintext password with Argon2id.

    `needs_rehash(self, password_hash: str) ‑> bool`
    :   Whether the stored hash should be re-hashed with current params.

    `verify_password(self, password_hash: str, password: str) ‑> bool`
    :   Verify a password against a stored hash. Returns False on mismatch.
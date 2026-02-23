Module madsci.common.local_backends
===================================
In-memory drop-in replacements for external services (Redis, MongoDB).

These backends enable running the full MADSci stack without Docker by providing
thread-safe, in-memory implementations that match the exact interfaces used by
managers. Data is ephemeral (in-memory), making this ideal for development,
testing, and demos.

Sub-modules
-----------
* madsci.common.local_backends.inmemory_collection
* madsci.common.local_backends.inmemory_redis
* madsci.common.local_backends.local_runner

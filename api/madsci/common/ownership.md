Module madsci.common.ownership
==============================
Provides the OwnershipHandler class for managing global ownership context of objects throughout a MADSci system component.

Variables
---------

`global_ownership_info`
:   Global ownership info
    To change the ownership info for a system component, set fields on this object.
    This is then used by the ownership_context context manager to create temporary ownership contexts as needed.

Functions
---------

`get_current_ownership_info() ‑> madsci.common.types.auth_types.OwnershipInfo`
:   Returns the current OwnershipInfo object.

`ownership_context(**overrides: Any) ‑> Generator[None, madsci.common.types.auth_types.OwnershipInfo, None]`
:   Updates the current OwnershipInfo (as returned by get_ownership_info) with the provided overrides.

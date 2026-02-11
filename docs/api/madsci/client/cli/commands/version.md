Module madsci.client.cli.commands.version
=========================================
MADSci CLI version command.

Displays version information for MADSci and all installed packages.

Functions
---------

`get_installed_packages() ‑> dict[str, str]`
:   Get versions of all installed MADSci packages.

    Returns:
        Dictionary mapping package names to versions.

`get_package_version(package_name: str) ‑> str | None`
:   Get the version of an installed package.

    Args:
        package_name: The name of the package to check.

    Returns:
        The version string if installed, None otherwise.

`get_system_info() ‑> dict[str, str]`
:   Get system information.

    Returns:
        Dictionary with system information.

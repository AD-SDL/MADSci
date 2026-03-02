Module madsci.client.cli.commands.doctor
========================================
MADSci CLI doctor command.

Performs comprehensive system diagnostics to ensure MADSci is properly configured.

Functions
---------

`check_docker() ‑> madsci.client.cli.commands.doctor.CheckResult`
:   Check Docker availability and version.

`check_docker_compose() ‑> madsci.client.cli.commands.doctor.CheckResult`
:   Check Docker Compose availability and version.

`check_port(port: int, service_name: str) ‑> madsci.client.cli.commands.doctor.CheckResult`
:   Check if a port is available.

`check_python_version() ‑> madsci.client.cli.commands.doctor.CheckResult`
:   Check Python version meets requirements.

`check_required_packages() ‑> madsci.client.cli.commands.doctor.CheckResult`
:   Check that required packages are installed.

`check_virtual_env() ‑> madsci.client.cli.commands.doctor.CheckResult`
:   Check if running in a virtual environment.

`format_status_icon(status: CheckStatus) ‑> str`
:   Get the icon for a check status.

`run_all_checks(categories: list[str] | None = None) ‑> madsci.client.cli.commands.doctor.DiagnosticResults`
:   Run all diagnostic checks.

Classes
-------

`CheckResult(name: str, status: CheckStatus, message: str, details: str | None = None, fix_suggestion: str | None = None)`
:   Result of a diagnostic check.

    ### Instance variables

    `details: str | None`
    :

    `fix_suggestion: str | None`
    :

    `message: str`
    :

    `name: str`
    :

    `status: madsci.client.cli.commands.doctor.CheckStatus`
    :

    ### Methods

    `to_dict(self) ‑> dict[str, typing.Any]`
    :   Convert to dictionary for JSON output.

`CheckStatus(value, names=None, *, module=None, qualname=None, type=None, start=1)`
:   Status of a diagnostic check.

    ### Ancestors (in MRO)

    * builtins.str
    * enum.Enum

    ### Class variables

    `FAIL`
    :

    `PASSED`
    :

    `SKIP`
    :

    `WARN`
    :

`DiagnosticResults(checks: list[CheckResult] = <factory>)`
:   Collection of diagnostic check results.

    ### Instance variables

    `checks: list[madsci.client.cli.commands.doctor.CheckResult]`
    :

    `failed: int`
    :   Count of failed checks.

    `passed: int`
    :   Count of passed checks.

    `warnings: int`
    :   Count of warning checks.

    ### Methods

    `add(self, result: CheckResult) ‑> None`
    :   Add a check result.

    `to_dict(self) ‑> dict[str, typing.Any]`
    :   Convert to dictionary for JSON output.
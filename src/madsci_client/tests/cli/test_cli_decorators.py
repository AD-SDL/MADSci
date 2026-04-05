"""Tests for madsci.client.cli.utils.cli_decorators."""

from __future__ import annotations

import click
from click.testing import CliRunner
from madsci.client.cli.utils.cli_decorators import (
    output_options,
    service_url_option,
    timeout_option,
    with_service_error_handling,
)
from madsci.common.types.error_types import (
    MadsciServiceError,
    ServiceResponseError,
    ServiceTimeoutError,
    ServiceUnavailableError,
)

# ---------------------------------------------------------------------------
# output_options
# ---------------------------------------------------------------------------


class TestOutputOptions:
    """Tests for the output_options decorator."""

    def test_json_flag(self) -> None:
        @click.command()
        @output_options
        @click.pass_context
        def cmd(ctx: click.Context) -> None:
            click.echo(f"json={ctx.obj.get('json')}")

        runner = CliRunner()
        result = runner.invoke(cmd, ["--json"], obj={})
        assert result.exit_code == 0
        assert "json=True" in result.output

    def test_yaml_flag(self) -> None:
        @click.command()
        @output_options
        @click.pass_context
        def cmd(ctx: click.Context) -> None:
            click.echo(f"yaml={ctx.obj.get('yaml')}")

        runner = CliRunner()
        result = runner.invoke(cmd, ["--yaml"], obj={})
        assert result.exit_code == 0
        assert "yaml=True" in result.output

    def test_quiet_flag(self) -> None:
        @click.command()
        @output_options
        @click.pass_context
        def cmd(ctx: click.Context) -> None:
            click.echo(f"quiet={ctx.obj.get('quiet')}")

        runner = CliRunner()
        result = runner.invoke(cmd, ["-q"], obj={})
        assert result.exit_code == 0
        assert "quiet=True" in result.output

    def test_no_flags(self) -> None:
        @click.command()
        @output_options
        @click.pass_context
        def cmd(ctx: click.Context) -> None:  # noqa: ARG001
            click.echo("ok")

        runner = CliRunner()
        result = runner.invoke(cmd, [], obj={})
        assert result.exit_code == 0
        assert "ok" in result.output


# ---------------------------------------------------------------------------
# service_url_option
# ---------------------------------------------------------------------------


class TestServiceUrlOption:
    """Tests for the service_url_option factory."""

    def test_default_value(self) -> None:
        @click.command()
        @service_url_option("event-manager", "EVENT_SERVER_URL", 8001)
        def cmd(event_manager_url: str) -> None:
            click.echo(event_manager_url)

        runner = CliRunner()
        result = runner.invoke(cmd, [])
        assert result.exit_code == 0
        assert "8001" in result.output

    def test_explicit_value(self) -> None:
        @click.command()
        @service_url_option("event-manager", "EVENT_SERVER_URL", 8001)
        def cmd(event_manager_url: str) -> None:
            click.echo(event_manager_url)

        runner = CliRunner()
        result = runner.invoke(cmd, ["--event-manager-url", "http://custom:9999/"])
        assert result.exit_code == 0
        assert "http://custom:9999/" in result.output

    def test_env_var(self) -> None:
        @click.command()
        @service_url_option("event-manager", "EVENT_SERVER_URL", 8001)
        def cmd(event_manager_url: str) -> None:
            click.echo(event_manager_url)

        runner = CliRunner()
        result = runner.invoke(cmd, [], env={"EVENT_SERVER_URL": "http://env:7777/"})
        assert result.exit_code == 0
        assert "http://env:7777/" in result.output


# ---------------------------------------------------------------------------
# timeout_option
# ---------------------------------------------------------------------------


class TestTimeoutOption:
    """Tests for the timeout_option decorator."""

    def test_default_timeout(self) -> None:
        @click.command()
        @timeout_option(default=5.0)
        def cmd(timeout: float) -> None:
            click.echo(f"timeout={timeout}")

        runner = CliRunner()
        result = runner.invoke(cmd, [])
        assert result.exit_code == 0
        assert "timeout=5.0" in result.output

    def test_explicit_timeout(self) -> None:
        @click.command()
        @timeout_option()
        def cmd(timeout: float) -> None:
            click.echo(f"timeout={timeout}")

        runner = CliRunner()
        result = runner.invoke(cmd, ["--timeout", "30.0"])
        assert result.exit_code == 0
        assert "timeout=30.0" in result.output


# ---------------------------------------------------------------------------
# with_service_error_handling
# ---------------------------------------------------------------------------


class TestWithServiceErrorHandling:
    """Tests for the with_service_error_handling decorator."""

    def test_unavailable_error(self) -> None:
        @click.command()
        @with_service_error_handling
        def cmd() -> None:
            raise ServiceUnavailableError("event", "http://localhost:8001/", "refused")

        runner = CliRunner()
        result = runner.invoke(cmd, [])
        assert result.exit_code == 1
        assert (
            "unavailable" in result.output.lower()
            or "unavailable" in (result.output + (result.output or "")).lower()
        )

    def test_timeout_error(self) -> None:
        @click.command()
        @with_service_error_handling
        def cmd() -> None:
            raise ServiceTimeoutError("data", "http://localhost:8004/", "slow")

        runner = CliRunner()
        result = runner.invoke(cmd, [])
        assert result.exit_code == 1

    def test_response_error(self) -> None:
        @click.command()
        @with_service_error_handling
        def cmd() -> None:
            raise ServiceResponseError(
                "resource", "http://localhost:8003/", "not found", 404, "detail"
            )

        runner = CliRunner()
        result = runner.invoke(cmd, [])
        assert result.exit_code == 1

    def test_generic_service_error(self) -> None:
        @click.command()
        @with_service_error_handling
        def cmd() -> None:
            raise MadsciServiceError("svc", "http://x/", "boom")

        runner = CliRunner()
        result = runner.invoke(cmd, [])
        assert result.exit_code == 1

    def test_no_error(self) -> None:
        @click.command()
        @with_service_error_handling
        def cmd() -> None:
            click.echo("success")

        runner = CliRunner()
        result = runner.invoke(cmd, [])
        assert result.exit_code == 0
        assert "success" in result.output

    def test_non_service_error_propagates(self) -> None:
        @click.command()
        @with_service_error_handling
        def cmd() -> None:
            raise ValueError("not a service error")

        runner = CliRunner()
        result = runner.invoke(cmd, [])
        # ValueError should propagate and cause a non-zero exit
        assert result.exit_code != 0

"""Tests for madsci.client.cli.utils.cli_decorators."""

from __future__ import annotations

from unittest.mock import MagicMock

import click
from click.testing import CliRunner
from madsci.client.cli.utils.cli_decorators import (
    output_options,
    resolve_service_url,
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

    def test_httpx_connect_error(self) -> None:
        """Raw httpx.ConnectError should be caught and produce a friendly message."""
        import httpx

        @click.command()
        @with_service_error_handling
        def cmd() -> None:
            request = httpx.Request("GET", "http://localhost:9999/api/test")
            raise httpx.ConnectError("[Errno 61] Connection refused", request=request)

        runner = CliRunner()
        result = runner.invoke(cmd, [])
        assert result.exit_code == 1
        output = result.output.lower()
        assert "connection refused" in output
        assert "localhost:9999" in output
        assert "madsci status" in output

    def test_httpx_timeout_error(self) -> None:
        """Raw httpx.TimeoutException should be caught and produce a friendly message."""
        import httpx

        @click.command()
        @with_service_error_handling
        def cmd() -> None:
            request = httpx.Request("GET", "http://localhost:8005/api/workflows")
            raise httpx.ReadTimeout("timed out", request=request)

        runner = CliRunner()
        result = runner.invoke(cmd, [])
        assert result.exit_code == 1
        output = result.output.lower()
        assert "timed out" in output
        assert "--timeout" in output

    def test_httpx_http_status_error(self) -> None:
        """Raw httpx.HTTPStatusError should be caught and produce a friendly message."""
        import httpx

        @click.command()
        @with_service_error_handling
        def cmd() -> None:
            request = httpx.Request("GET", "http://localhost:8005/api/workflows/bad-id")
            response = httpx.Response(404, request=request, text="Not found")
            raise httpx.HTTPStatusError(
                "404 Not Found", request=request, response=response
            )

        runner = CliRunner()
        result = runner.invoke(cmd, [])
        assert result.exit_code == 1
        assert "404" in result.output
        assert "localhost:8005" in result.output


# ---------------------------------------------------------------------------
# resolve_service_url
# ---------------------------------------------------------------------------


class TestResolveServiceUrl:
    """Tests for the resolve_service_url helper."""

    def _make_ctx(self, context_obj=None) -> click.Context:
        """Build a minimal Click context with ctx.obj."""

        @click.command()
        @click.pass_context
        def dummy(ctx: click.Context) -> None:
            pass

        runner = CliRunner()
        with runner.isolated_filesystem():
            ctx_holder = {}

            @click.command()
            @click.pass_context
            def probe(ctx: click.Context) -> None:
                ctx_holder["ctx"] = ctx

            runner.invoke(
                probe,
                [],
                obj={"context": context_obj} if context_obj is not None else {},
            )
            if ctx_holder:
                return ctx_holder["ctx"]
        return None

    def test_explicit_url_takes_precedence(self) -> None:
        """Explicit URL should override context and default."""

        @click.command()
        @click.pass_context
        def cmd(ctx: click.Context) -> None:
            result = resolve_service_url(
                ctx, "http://explicit:9999/", "workcell_server_url", 8005
            )
            click.echo(result)

        runner = CliRunner()
        result = runner.invoke(cmd, [], obj={})
        assert result.exit_code == 0
        assert "http://explicit:9999/" in result.output

    def test_context_url_used_when_no_explicit(self) -> None:
        """Context attribute should be used when no explicit URL is given."""
        mock_context = MagicMock()
        mock_context.workcell_server_url = "http://context-host:8005/"

        @click.command()
        @click.pass_context
        def cmd(ctx: click.Context) -> None:
            result = resolve_service_url(ctx, None, "workcell_server_url", 8005)
            click.echo(result)

        runner = CliRunner()
        result = runner.invoke(cmd, [], obj={"context": mock_context})
        assert result.exit_code == 0
        assert "http://context-host:8005/" in result.output

    def test_default_used_when_no_explicit_or_context(self) -> None:
        """Default localhost URL should be returned when nothing else is set."""

        @click.command()
        @click.pass_context
        def cmd(ctx: click.Context) -> None:
            result = resolve_service_url(ctx, None, "workcell_server_url", 8005)
            click.echo(result)

        runner = CliRunner()
        result = runner.invoke(cmd, [], obj={})
        assert result.exit_code == 0
        assert "http://localhost:8005/" in result.output

    def test_default_used_when_ctx_obj_is_none(self) -> None:
        """Default should be returned when ctx.obj is None."""

        @click.command()
        @click.pass_context
        def cmd(ctx: click.Context) -> None:
            result = resolve_service_url(ctx, None, "event_server_url", 8001)
            click.echo(result)

        runner = CliRunner()
        result = runner.invoke(cmd, [])
        assert result.exit_code == 0
        assert "http://localhost:8001/" in result.output

    def test_context_url_none_falls_back_to_default(self) -> None:
        """When context attribute is None, fall back to default."""
        mock_context = MagicMock()
        mock_context.resource_server_url = None

        @click.command()
        @click.pass_context
        def cmd(ctx: click.Context) -> None:
            result = resolve_service_url(ctx, None, "resource_server_url", 8003)
            click.echo(result)

        runner = CliRunner()
        result = runner.invoke(cmd, [], obj={"context": mock_context})
        assert result.exit_code == 0
        assert "http://localhost:8003/" in result.output

    def test_different_ports(self) -> None:
        """Should use the given default_port for different services."""

        @click.command()
        @click.pass_context
        def cmd(ctx: click.Context) -> None:
            click.echo(resolve_service_url(ctx, None, "data_server_url", 8004))
            click.echo(resolve_service_url(ctx, None, "location_server_url", 8006))
            click.echo(resolve_service_url(ctx, None, "experiment_server_url", 8002))

        runner = CliRunner()
        result = runner.invoke(cmd, [], obj={})
        assert result.exit_code == 0
        assert "8004" in result.output
        assert "8006" in result.output
        assert "8002" in result.output

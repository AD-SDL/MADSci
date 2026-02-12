import json
import subprocess
import sys


def test_event_client_metrics_collected_in_subprocess() -> None:
    """Verify OTEL metrics collection in an isolated interpreter.

    OpenTelemetry providers are process-global and cannot be reliably reset once
    installed. To make the metric assertions deterministic, run in a subprocess.
    """

    code = r"""
import json

from madsci.client.event_client import EventClient
from madsci.common.otel import OtelBootstrapConfig, collect_metrics, configure_otel
from madsci.common.types.event_types import EventClientConfig

configure_otel(
    OtelBootstrapConfig(
        enabled=True,
        service_name="madsci.test",
        exporter="none",
        test_mode=True,
    )
)

client = EventClient(
    config=EventClientConfig(
        event_server_url=None,
        otel_enabled=True,
        otel_exporter="none",
    )
)

client.event_server = "http://localhost:8001"
client._send_event_to_event_server = lambda *a, **k: None
client.info("hello", foo="bar")

data = collect_metrics(client._otel_runtime)

out = {"ok": False}
if data is not None:
    names = []
    for rm in data.resource_metrics:
        for sm in rm.scope_metrics:
            for m in sm.metrics:
                names.append(m.name)
    out = {
        "ok": "madsci.eventclient.events" in set(names),
        "metric_names": sorted(set(names)),
    }

print(json.dumps(out))
"""

    proc = subprocess.run(  # noqa: S603
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=False,
        # Input is a constant string defined in this test.
    )

    assert proc.returncode == 0, proc.stderr

    last_line = (proc.stdout.strip().splitlines() or ["{}"])[-1]
    payload = json.loads(last_line)
    assert payload.get("ok") is True, payload

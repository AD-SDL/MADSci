from __future__ import annotations

from typing import Any

from madsci.common.manager_base import AbstractManagerBase
from madsci.common.otel import OtelBootstrapConfig, configure_otel
from madsci.common.types.manager_types import (
    ManagerHealth,
    ManagerSettings,
)


class _TestManager(AbstractManagerBase[ManagerSettings]):
    SETTINGS_CLASS = ManagerSettings

    def create_server(self, **_kwargs: Any):  # pragma: no cover
        raise RuntimeError("not needed")

    def get_health(self) -> ManagerHealth:
        return ManagerHealth(healthy=True, description="ok")


def test_manager_reuses_process_global_otel_runtime_when_disabled() -> None:
    runtime = configure_otel(
        OtelBootstrapConfig(
            enabled=True,
            service_name="madsci.test",
            exporter="none",
            test_mode=True,
        )
    )

    mgr = _TestManager(
        settings=ManagerSettings(
            otel_enabled=False,
            enable_registry_resolution=False,
        )
    )
    assert mgr._otel_runtime is runtime


def test_manager_uses_existing_runtime_when_enabled() -> None:
    runtime = configure_otel(
        OtelBootstrapConfig(
            enabled=True,
            service_name="madsci.test",
            exporter="none",
            test_mode=True,
        )
    )

    mgr = _TestManager(
        settings=ManagerSettings(
            otel_enabled=True,
            otel_exporter="none",
            otel_service_name="madsci.test",
            enable_registry_resolution=False,
        )
    )
    assert mgr._otel_runtime is runtime

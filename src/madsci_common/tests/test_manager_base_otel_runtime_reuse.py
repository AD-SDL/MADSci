from __future__ import annotations

from pathlib import Path
from typing import Any

from madsci.common.manager_base import AbstractManagerBase
from madsci.common.otel import OtelBootstrapConfig, configure_otel
from madsci.common.types.manager_types import (
    ManagerDefinition,
    ManagerHealth,
    ManagerSettings,
)


class _TestManager(AbstractManagerBase[ManagerSettings, ManagerDefinition]):
    SETTINGS_CLASS = ManagerSettings
    DEFINITION_CLASS = ManagerDefinition

    def create_default_definition(self) -> ManagerDefinition:
        return ManagerDefinition(name="test", manager_type="event_manager")

    def create_server(self, **_kwargs: Any):  # pragma: no cover
        raise RuntimeError("not needed")

    def get_health(self) -> ManagerHealth:
        return ManagerHealth(healthy=True, description="ok")


def test_manager_reuses_process_global_otel_runtime_when_disabled(
    tmp_path: Path,
) -> None:
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
            manager_definition=tmp_path / "manager.yaml",
        )
    )
    assert mgr._otel_runtime is runtime


def test_manager_uses_existing_runtime_when_enabled(tmp_path: Path) -> None:
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
            manager_definition=tmp_path / "manager.yaml",
        )
    )
    assert mgr._otel_runtime is runtime

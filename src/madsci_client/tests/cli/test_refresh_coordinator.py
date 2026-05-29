"""Tests for ScreenRefreshCoordinator."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from madsci.client.cli.tui.refresh_coordinator import ScreenRefreshCoordinator


class TestScreenRefreshCoordinator:
    """Tests for ScreenRefreshCoordinator."""

    def _make_screen(self, refresh_data=None) -> MagicMock:
        """Return a mock screen with auto_refresh_enabled=True and a refresh_data method."""
        screen = MagicMock()
        screen.auto_refresh_enabled = True
        screen.refresh_data = refresh_data or AsyncMock()
        return screen

    @pytest.mark.asyncio
    async def test_refresh_data_is_called(self) -> None:
        """refresh_data() should be called on an eligible screen."""
        screen = self._make_screen()
        coordinator = ScreenRefreshCoordinator()

        await coordinator.refresh(screen)

        screen.refresh_data.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_concurrent_call_is_skipped(self) -> None:
        """A second concurrent refresh on the same screen should be skipped."""
        call_count = 0

        async def slow_refresh() -> None:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.05)

        screen = self._make_screen(refresh_data=slow_refresh)
        coordinator = ScreenRefreshCoordinator()

        await asyncio.gather(
            coordinator.refresh(screen),
            coordinator.refresh(screen),
        )

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_different_screens_refresh_independently(self) -> None:
        """Two different screens should each be refreshed, regardless of the other."""
        screen_a = self._make_screen()
        screen_b = self._make_screen()
        coordinator = ScreenRefreshCoordinator()

        await asyncio.gather(
            coordinator.refresh(screen_a),
            coordinator.refresh(screen_b),
        )

        screen_a.refresh_data.assert_awaited_once()
        screen_b.refresh_data.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_screen_eligible_again_after_completion(self) -> None:
        """A screen should be refreshable again after a previous refresh completes."""
        screen = self._make_screen()
        coordinator = ScreenRefreshCoordinator()

        await coordinator.refresh(screen)
        await coordinator.refresh(screen)

        assert screen.refresh_data.await_count == 2

    @pytest.mark.asyncio
    async def test_exception_in_refresh_data_is_suppressed(self) -> None:
        """Exceptions raised by refresh_data() should be suppressed."""
        screen = self._make_screen(
            refresh_data=AsyncMock(side_effect=RuntimeError("network error"))
        )
        coordinator = ScreenRefreshCoordinator()

        await coordinator.refresh(screen)  # should not raise

    @pytest.mark.asyncio
    async def test_ineligible_screen_is_skipped(self) -> None:
        """A screen with auto_refresh_enabled=False should not be refreshed."""
        screen = self._make_screen()
        screen.auto_refresh_enabled = False
        coordinator = ScreenRefreshCoordinator()

        await coordinator.refresh(screen)

        screen.refresh_data.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_force_refresh_always_runs(self) -> None:
        """force_refresh() should run even if a refresh is already in progress."""
        call_count = 0

        async def slow_refresh() -> None:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.05)

        screen = self._make_screen(refresh_data=slow_refresh)
        coordinator = ScreenRefreshCoordinator()

        await asyncio.gather(
            coordinator.force_refresh(screen),
            coordinator.force_refresh(screen),
        )

        assert call_count == 2

    @pytest.mark.asyncio
    async def test_force_refresh_blocks_auto_refresh(self) -> None:
        """auto-refresh should be skipped while force_refresh() is in progress."""
        call_count = 0

        async def slow_refresh() -> None:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.05)

        screen = self._make_screen(refresh_data=slow_refresh)
        coordinator = ScreenRefreshCoordinator()

        await asyncio.gather(
            coordinator.force_refresh(screen),
            coordinator.refresh(screen),
        )

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_force_refresh_does_not_suppress_exceptions(self) -> None:
        """force_refresh() should propagate exceptions from refresh_data()."""
        screen = self._make_screen(
            refresh_data=AsyncMock(side_effect=RuntimeError("network error"))
        )
        coordinator = ScreenRefreshCoordinator()

        with pytest.raises(RuntimeError):
            await coordinator.force_refresh(screen)

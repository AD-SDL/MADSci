"""
Dual-mode (sync + async) HTTP request mixin for MADSci clients.

This module provides :class:`DualModeClientMixin`, a mixin class that gives
any MADSci service client both synchronous and asynchronous HTTP request
methods backed by ``httpx``.  It is designed to be mixed into concrete client
classes (e.g. ``LabClient``, ``DataClient``) that already set up the required
instance attributes (``config``, ``_client``, ``_async_client``).

Usage
-----
::

    from madsci.client.http import DualModeClientMixin
    from madsci.common.http_client import create_httpx_client

    class LabClient(DualModeClientMixin):
        def __init__(self, ...):
            self.config = config or LabClientConfig()
            self._client = create_httpx_client(config=self.config)
            self._async_client = None  # created lazily

        def get_lab_context(self, timeout=None):
            response = self._request("GET", f"{self.url}context", timeout=timeout)
            return MadsciContext.model_validate(response.json())

        async def async_get_lab_context(self, timeout=None):
            response = await self._async_request("GET", f"{self.url}context", timeout=timeout)
            return MadsciContext.model_validate(response.json())
"""

from __future__ import annotations

import contextlib
import logging
import threading
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from types import TracebackType

    from madsci.common.types.client_types import MadsciClientConfig

logger = logging.getLogger(__name__)

__all__ = ["DualModeClientMixin"]


class DualModeClientMixin:
    """
    Mixin that provides shared sync/async HTTP request infrastructure.

    This mixin assumes the consuming class sets the following instance
    attributes in its ``__init__``:

    * ``self.config`` -- a :class:`~madsci.common.types.client_types.MadsciClientConfig`
    * ``self._client`` -- an ``httpx.Client`` (created via
      :func:`~madsci.common.http_client.create_httpx_client`)
    * ``self._async_client`` -- initially ``None``; lazily created on the
      first call to :meth:`_async_request`.
    """

    # Declared here for type-checkers; actual values are set by the
    # consuming class's __init__.
    config: MadsciClientConfig
    _client: httpx.Client
    _async_client: httpx.AsyncClient | None

    # Module-level lock guards per-instance lock creation in _ensure_async_client
    _class_lock: threading.Lock = threading.Lock()

    # ------------------------------------------------------------------
    # Sync request
    # ------------------------------------------------------------------

    def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """
        Send a synchronous HTTP request via ``self._client``.

        Parameters
        ----------
        method : str
            HTTP method (``"GET"``, ``"POST"``, etc.).
        url : str
            Fully-qualified URL.
        **kwargs
            Extra keyword arguments forwarded to ``httpx.Client.request``
            (e.g. ``json``, ``params``, ``timeout``, ``headers``).

        Returns
        -------
        httpx.Response
            The server response.

        Raises
        ------
        httpx.ConnectError
            If the connection to the server fails.
        httpx.TimeoutException
            If the request times out.
        """
        return self._client.request(method, url, **kwargs)

    # ------------------------------------------------------------------
    # Async request
    # ------------------------------------------------------------------

    def _ensure_async_client(self) -> httpx.AsyncClient:
        """
        Lazily create the async HTTP client on first use.

        This method is thread-safe: a per-instance lock ensures that
        concurrent callers do not create duplicate async clients.

        Returns
        -------
        httpx.AsyncClient
            The (possibly newly created) async client.
        """
        with self._class_lock:
            if not hasattr(self, "_async_client_lock"):
                self._async_client_lock = threading.Lock()
        with self._async_client_lock:
            if self._async_client is None:
                from madsci.common.http_client import create_httpx_client  # noqa: I001, PLC0415

                self._async_client = create_httpx_client(
                    config=self.config,
                    async_mode=True,
                )
            return self._async_client

    async def _async_request(
        self, method: str, url: str, **kwargs: Any
    ) -> httpx.Response:
        """
        Send an asynchronous HTTP request via ``self._async_client``.

        The async client is created lazily on the first call.

        Parameters
        ----------
        method : str
            HTTP method (``"GET"``, ``"POST"``, etc.).
        url : str
            Fully-qualified URL.
        **kwargs
            Extra keyword arguments forwarded to ``httpx.AsyncClient.request``
            (e.g. ``json``, ``params``, ``timeout``, ``headers``).

        Returns
        -------
        httpx.Response
            The server response.

        Raises
        ------
        httpx.ConnectError
            If the connection to the server fails.
        httpx.TimeoutException
            If the request times out.
        """
        client = self._ensure_async_client()
        return await client.request(method, url, **kwargs)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self) -> None:
        """
        Close both the sync and async HTTP clients, releasing resources.

        Safe to call multiple times.
        """
        if hasattr(self, "_client") and self._client is not None:
            self._client.close()
        if hasattr(self, "_async_client") and self._async_client is not None:
            import asyncio  # noqa: PLC0415

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop is None:
                with contextlib.suppress(Exception):
                    asyncio.run(self._async_client.aclose())
            self._async_client = None

    async def aclose(self) -> None:
        """
        Async version of :meth:`close`.

        Properly awaits the async client's shutdown.
        """
        if hasattr(self, "_client") and self._client is not None:
            self._client.close()
            self._client = None
        if hasattr(self, "_async_client") and self._async_client is not None:
            await self._async_client.aclose()
            self._async_client = None

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> DualModeClientMixin:
        """Enter sync context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit sync context manager and close clients."""
        self.close()

    async def __aenter__(self) -> DualModeClientMixin:
        """Enter async context manager."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context manager and close clients."""
        await self.aclose()

"""
httpx client factory for MADSci.

This module provides a factory function for creating configured httpx clients
(sync and async) with retry logic, connection pooling, rate limit tracking,
and timeouts. It is the httpx equivalent of ``create_http_session()`` in
``madsci.common.utils`` and is intended to replace it as the canonical HTTP
client factory across all MADSci components.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Union

import httpx

if TYPE_CHECKING:
    from madsci.common.types.client_types import MadsciClientConfig
    from madsci.common.utils import RateLimitTracker

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Retry transports
# ---------------------------------------------------------------------------


class RetryTransport(httpx.BaseTransport):
    """
    Synchronous transport wrapper that retries on configurable status codes.

    Wraps an ``httpx.HTTPTransport`` and adds status-code-level retry logic
    with exponential backoff, mirroring the retry behaviour previously provided
    by ``urllib3.util.retry.Retry`` in the requests-based session factory.

    Parameters
    ----------
    transport : httpx.HTTPTransport
        The underlying transport to delegate to.
    retries : int
        Maximum number of retry attempts (0 = no retries).
    status_forcelist : list[int]
        HTTP status codes that trigger a retry.
    backoff_factor : float
        Multiplier for exponential backoff between retries.
        Delay = ``backoff_factor * (2 ** (attempt - 1))``.
    allowed_methods : list[str] | None
        HTTP methods eligible for retry.  ``None`` means *all* methods.
    """

    def __init__(
        self,
        transport: httpx.HTTPTransport,
        *,
        retries: int = 3,
        status_forcelist: list[int] | None = None,
        backoff_factor: float = 0.3,
        allowed_methods: list[str] | None = None,
    ) -> None:
        """Initialise the retry transport with the given configuration."""
        self._transport = transport
        self._retries = retries
        self._status_forcelist = status_forcelist or [429, 500, 502, 503, 504]
        self._backoff_factor = backoff_factor
        self._allowed_methods = (
            [m.upper() for m in allowed_methods]
            if allowed_methods is not None
            else None
        )

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        """Send *request*, retrying on qualifying failures."""
        # If the method isn't eligible for retry, pass through directly.
        if (
            self._allowed_methods is not None
            and request.method.upper() not in self._allowed_methods
        ):
            return self._transport.handle_request(request)

        last_response: httpx.Response | None = None
        for attempt in range(1 + self._retries):
            response = self._transport.handle_request(request)

            if response.status_code not in self._status_forcelist:
                return response

            last_response = response

            if attempt < self._retries:
                delay = self._backoff_factor * (2**attempt)
                logger.debug(
                    "Retry %d/%d for %s %s (status %d), sleeping %.2fs",
                    attempt + 1,
                    self._retries,
                    request.method,
                    request.url,
                    response.status_code,
                    delay,
                )
                time.sleep(delay)

        # All retries exhausted; return the last response.
        assert last_response is not None  # noqa: S101
        return last_response

    def close(self) -> None:  # noqa: D102
        self._transport.close()

    def __enter__(self) -> RetryTransport:
        """Enter the context manager."""
        return self

    def __exit__(self, *args: object) -> None:
        """Exit the context manager and close the underlying transport."""
        self.close()


class AsyncRetryTransport(httpx.AsyncBaseTransport):
    """
    Asynchronous transport wrapper that retries on configurable status codes.

    Async counterpart of :class:`RetryTransport`.  Uses ``asyncio.sleep``
    for non-blocking backoff delays.

    Parameters
    ----------
    transport : httpx.AsyncHTTPTransport
        The underlying async transport to delegate to.
    retries : int
        Maximum number of retry attempts (0 = no retries).
    status_forcelist : list[int]
        HTTP status codes that trigger a retry.
    backoff_factor : float
        Multiplier for exponential backoff between retries.
    allowed_methods : list[str] | None
        HTTP methods eligible for retry.  ``None`` means *all* methods.
    """

    def __init__(
        self,
        transport: httpx.AsyncHTTPTransport,
        *,
        retries: int = 3,
        status_forcelist: list[int] | None = None,
        backoff_factor: float = 0.3,
        allowed_methods: list[str] | None = None,
    ) -> None:
        """Initialise the async retry transport with the given configuration."""
        self._transport = transport
        self._retries = retries
        self._status_forcelist = status_forcelist or [429, 500, 502, 503, 504]
        self._backoff_factor = backoff_factor
        self._allowed_methods = (
            [m.upper() for m in allowed_methods]
            if allowed_methods is not None
            else None
        )

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        """Send *request* asynchronously, retrying on qualifying failures."""
        if (
            self._allowed_methods is not None
            and request.method.upper() not in self._allowed_methods
        ):
            return await self._transport.handle_async_request(request)

        last_response: httpx.Response | None = None
        for attempt in range(1 + self._retries):
            response = await self._transport.handle_async_request(request)

            if response.status_code not in self._status_forcelist:
                return response

            last_response = response

            if attempt < self._retries:
                delay = self._backoff_factor * (2**attempt)
                logger.debug(
                    "Async retry %d/%d for %s %s (status %d), sleeping %.2fs",
                    attempt + 1,
                    self._retries,
                    request.method,
                    request.url,
                    response.status_code,
                    delay,
                )
                await asyncio.sleep(delay)

        assert last_response is not None  # noqa: S101
        return last_response

    async def aclose(self) -> None:  # noqa: D102
        await self._transport.aclose()

    async def __aenter__(self) -> AsyncRetryTransport:
        """Enter the async context manager."""
        return self

    async def __aexit__(self, *args: object) -> None:
        """Exit the async context manager and close the underlying transport."""
        await self.aclose()


# ---------------------------------------------------------------------------
# Rate-limit response hook
# ---------------------------------------------------------------------------


def _make_rate_limit_hook(
    tracker: RateLimitTracker,
) -> callable:
    """
    Create an httpx response event hook that feeds headers into *tracker*.

    The returned callable has the signature expected by ``httpx.Client``'s
    ``event_hooks={"response": [hook]}``.
    """

    def _hook(response: httpx.Response) -> None:
        # Pass the httpx Headers object directly -- it is a case-insensitive
        # mapping, which is what RateLimitTracker expects (it checks for
        # mixed-case keys like "X-RateLimit-Limit").  Converting to a plain
        # dict would lowercase all keys and break the lookups.
        tracker.update_from_headers(response.headers)

    return _hook


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_httpx_client(
    config: MadsciClientConfig | None = None,
    *,
    async_mode: bool = False,
) -> Union[httpx.Client, httpx.AsyncClient]:
    """
    Create an ``httpx.Client`` or ``httpx.AsyncClient`` with standardised configuration.

    This mirrors the behaviour of :func:`madsci.common.utils.create_http_session`
    but uses *httpx* instead of *requests*, supporting both synchronous and
    asynchronous usage.

    The returned client is configured with:

    * **Retry logic** -- via :class:`RetryTransport` / :class:`AsyncRetryTransport`
      wrapping the default transport.
    * **Connection pooling** -- via ``httpx.Limits``.
    * **Timeouts** -- sensible per-phase timeouts derived from the config.
    * **Rate-limit tracking** -- via an httpx response event hook that feeds
      ``X-RateLimit-*`` headers into :class:`~madsci.common.utils.RateLimitTracker`.
    * **Redirect following** -- ``follow_redirects=True`` (httpx defaults to
      ``False``, unlike requests).

    Parameters
    ----------
    config : MadsciClientConfig | None
        Client configuration.  Falls back to ``MadsciClientConfig()`` defaults.
    async_mode : bool
        If ``True`` return an ``httpx.AsyncClient``; otherwise a sync
        ``httpx.Client``.

    Returns
    -------
    httpx.Client | httpx.AsyncClient
        A fully-configured HTTP client ready for use.

    Examples
    --------
    >>> from madsci.common.http_client import create_httpx_client
    >>>
    >>> # Sync client with defaults
    >>> client = create_httpx_client()
    >>>
    >>> # Async client with custom retry count
    >>> from madsci.common.types.client_types import MadsciClientConfig
    >>> aclient = create_httpx_client(
    ...     config=MadsciClientConfig(retry_total=5),
    ...     async_mode=True,
    ... )
    """
    # Lazy import to avoid circular dependencies (same pattern as create_http_session)
    from madsci.common.types.client_types import MadsciClientConfig  # noqa: PLC0415
    from madsci.common.utils import RateLimitTracker  # noqa: PLC0415

    if config is None:
        config = MadsciClientConfig()

    # -- Limits (connection pooling) ----------------------------------------
    limits = httpx.Limits(
        max_connections=config.pool_maxsize,
        max_keepalive_connections=config.pool_connections,
    )

    # -- Timeout ------------------------------------------------------------
    timeout = httpx.Timeout(
        connect=5.0,
        read=config.timeout_default,
        write=config.timeout_default,
        pool=5.0,
    )

    # -- Event hooks (rate limit tracking) ----------------------------------
    event_hooks: dict[str, list] = {"request": [], "response": []}
    rate_limit_tracker: RateLimitTracker | None = None

    if getattr(config, "rate_limit_tracking_enabled", False):
        rate_limit_tracker = RateLimitTracker(
            warning_threshold=getattr(config, "rate_limit_warning_threshold", 0.8),
            respect_limits=getattr(config, "rate_limit_respect_limits", False),
        )
        event_hooks["response"].append(_make_rate_limit_hook(rate_limit_tracker))

    # -- Build transport & client -------------------------------------------
    retry_kwargs = {
        "retries": config.retry_total,
        "status_forcelist": list(config.retry_status_forcelist),
        "backoff_factor": config.retry_backoff_factor,
        "allowed_methods": config.retry_allowed_methods,
    }

    if async_mode:
        base_transport = httpx.AsyncHTTPTransport(limits=limits)
        if config.retry_enabled:
            transport = AsyncRetryTransport(base_transport, **retry_kwargs)
        else:
            transport = base_transport

        client = httpx.AsyncClient(
            transport=transport,
            timeout=timeout,
            follow_redirects=True,
            event_hooks=event_hooks,
        )
    else:
        base_transport = httpx.HTTPTransport(limits=limits)
        if config.retry_enabled:
            transport = RetryTransport(base_transport, **retry_kwargs)
        else:
            transport = base_transport

        client = httpx.Client(
            transport=transport,
            timeout=timeout,
            follow_redirects=True,
            event_hooks=event_hooks,
        )

    # Attach tracker to client for caller access (mirrors requests session pattern)
    if rate_limit_tracker is not None:
        client.rate_limit_tracker = rate_limit_tracker  # type: ignore[attr-defined]

    return client

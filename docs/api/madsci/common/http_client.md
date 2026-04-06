Module madsci.common.http_client
================================
httpx client factory for MADSci.

This module provides a factory function for creating configured httpx clients
(sync and async) with retry logic, connection pooling, rate limit tracking,
and timeouts. It is the httpx equivalent of ``create_http_session()`` in
``madsci.common.utils`` and is intended to replace it as the canonical HTTP
client factory across all MADSci components.

Functions
---------

`create_httpx_client(config: MadsciClientConfig | None = None, *, async_mode: bool = False) ‑> Union[httpx.Client, httpx.AsyncClient]`
:   Create an ``httpx.Client`` or ``httpx.AsyncClient`` with standardised configuration.
    
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

Classes
-------

`AsyncRetryTransport(transport: httpx.AsyncHTTPTransport, *, retries: int = 3, status_forcelist: list[int] | None = None, backoff_factor: float = 0.3, allowed_methods: list[str] | None = None)`
:   Asynchronous transport wrapper that retries on configurable status codes.
    
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
    
    Initialise the async retry transport with the given configuration.

    ### Ancestors (in MRO)

    * httpx.AsyncBaseTransport

    ### Methods

    `aclose(self) ‑> None`
    :

    `handle_async_request(self, request: httpx.Request) ‑> httpx.Response`
    :   Send *request* asynchronously, retrying on qualifying failures.

`RetryTransport(transport: httpx.HTTPTransport, *, retries: int = 3, status_forcelist: list[int] | None = None, backoff_factor: float = 0.3, allowed_methods: list[str] | None = None)`
:   Synchronous transport wrapper that retries on configurable status codes.
    
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
    
    Initialise the retry transport with the given configuration.

    ### Ancestors (in MRO)

    * httpx.BaseTransport

    ### Methods

    `close(self) ‑> None`
    :

    `handle_request(self, request: httpx.Request) ‑> httpx.Response`
    :   Send *request*, retrying on qualifying failures.
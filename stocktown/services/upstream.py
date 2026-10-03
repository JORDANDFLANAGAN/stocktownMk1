"""Turning a data provider's failure into the API's 503, shared by every service that calls one."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Final

import httpx

from stocktown.exceptions import UpstreamUnavailableError

HTTP_TOO_MANY_REQUESTS: Final[int] = 429
DEFAULT_RETRY_AFTER_SECONDS: Final[int] = 60


@contextmanager
def reported_as_unavailable(provider: str) -> Iterator[None]:
    """Turns a provider's failure into UpstreamUnavailableError (a 503), keeping a rate limit's
    Retry-After. An unreadable reply counts as a failure too."""
    try:
        yield
    except httpx.HTTPStatusError as error:
        rate_limited = error.response.status_code == HTTP_TOO_MANY_REQUESTS
        retry_after = retry_after_seconds(error.response) if rate_limited else None
        raise UpstreamUnavailableError(provider, retry_after_seconds=retry_after) from error
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as error:
        raise UpstreamUnavailableError(provider) from error


def retry_after_seconds(response: httpx.Response) -> int:
    header = response.headers.get("Retry-After", "")
    return int(header) if header.isdigit() else DEFAULT_RETRY_AFTER_SECONDS

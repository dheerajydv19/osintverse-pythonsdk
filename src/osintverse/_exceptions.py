from __future__ import annotations

from typing import Any


class OSINTverseError(Exception):
    """Base error for the OSINTverse Python SDK."""


class APIError(OSINTverseError):
    """HTTP error returned by the SearchIn API."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        body: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body
        self.detail = message


class AuthenticationError(APIError):
    """Missing, invalid, disabled, or expired API key (HTTP 401)."""


class PaymentRequiredError(APIError):
    """Insufficient prepaid balance (HTTP 402)."""


class ForbiddenError(APIError):
    """Account is banned (HTTP 403)."""


class NotFoundError(APIError):
    """Search not found or not owned by this account (HTTP 404)."""


class ValidationError(APIError):
    """Invalid request body or provider/input_type pair (HTTP 422)."""


class WaitTimeoutError(OSINTverseError):
    """Timed out waiting for an async search to finish."""


class SearchFailedError(OSINTverseError):
    """Search finished with status ``failed`` (typically insufficient balance)."""

    def __init__(self, search: Any) -> None:
        message = getattr(search, "error", None) or f"Search {getattr(search, 'id', '?')} failed"
        super().__init__(message)
        self.search = search


class SearchRefundedError(OSINTverseError):
    """Search finished with status ``refunded`` after an upstream failure."""

    def __init__(self, search: Any) -> None:
        message = getattr(search, "error", None) or (
            f"Search {getattr(search, 'id', '?')} was refunded after an upstream failure"
        )
        super().__init__(message)
        self.search = search

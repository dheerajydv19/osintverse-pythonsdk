"""Official Python client for the OSINTverse SearchIn API.

This package talks to ``https://apiv1.osintverse.com`` (osintverse.com). It is
not affiliated with other products that reuse the OSINTverse name.
"""

from osintverse._async_client import AsyncOSINTverse
from osintverse._client import OSINTverse
from osintverse._config import config_path, delete_credentials, read_credentials
from osintverse._constants import VERSION as __version__
from osintverse._device import DeviceLoginError, device_login
from osintverse._exceptions import (
    APIError,
    AuthenticationError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    OSINTverseError,
    PaymentRequiredError,
    SearchFailedError,
    SearchRefundedError,
    ValidationError,
    WaitTimeoutError,
)
from osintverse._models import (
    BulkSearch,
    BulkSummary,
    InputType,
    InputTypePrice,
    Provider,
    ProviderId,
    ProviderResult,
    Quote,
    Search,
    SearchStatus,
)

__all__ = [
    "APIError",
    "AsyncOSINTverse",
    "AuthenticationError",
    "BulkSearch",
    "BulkSummary",
    "ConflictError",
    "DeviceLoginError",
    "ForbiddenError",
    "InputType",
    "InputTypePrice",
    "NotFoundError",
    "OSINTverse",
    "OSINTverseError",
    "PaymentRequiredError",
    "Provider",
    "ProviderId",
    "ProviderResult",
    "Quote",
    "Search",
    "SearchFailedError",
    "SearchRefundedError",
    "SearchStatus",
    "ValidationError",
    "WaitTimeoutError",
    "__version__",
    "config_path",
    "delete_credentials",
    "device_login",
    "read_credentials",
]

from __future__ import annotations

import os
from typing import Any

import httpx

from osintverse._constants import (
    API_KEY_ENV,
    DEFAULT_BASE_URL,
    DEFAULT_TIMEOUT,
    USER_AGENT,
)
from osintverse._exceptions import AuthenticationError
from osintverse._http import raise_for_status
from osintverse._models import Provider
from osintverse._search import SearchResource


class ProvidersResource:
    def __init__(self, client: OSINTverse) -> None:
        self._client = client

    def list(self) -> list[Provider]:
        """Return the live provider catalog via ``GET /v1/providers``."""
        payload = self._client.request("GET", "/v1/providers", auth=False)
        return [Provider.model_validate(item) for item in payload]


class OSINTverse:
    """Synchronous client for the OSINTverse SearchIn API.

    Parameters
    ----------
    api_key:
        Secret from Dashboard → API keys. Defaults to ``OSINTVERSE_API_KEY``.
        Required for search routes; optional for ``health()`` and ``providers.list()``.
    base_url:
        API host. Defaults to ``https://apiv1.osintverse.com``.
    timeout:
        httpx timeout in seconds.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.environ.get(API_KEY_ENV)
        self.base_url = base_url.rstrip("/")
        self._owns_http_client = http_client is None
        self._http = http_client or httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
        self.providers = ProvidersResource(self)
        self.search = SearchResource(self)

    def health(self) -> dict[str, Any]:
        """Service health check via ``GET /health``."""
        payload = self.request("GET", "/health", auth=False)
        return payload if isinstance(payload, dict) else {"status": payload}

    def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        auth: bool = True,
    ) -> Any:
        headers: dict[str, str] = {}
        if auth:
            if not self.api_key:
                raise AuthenticationError(
                    f"Missing API key. Pass api_key= or set {API_KEY_ENV}.",
                    status_code=401,
                )
            headers["x-api-key"] = self.api_key
        response = self._http.request(method, path, headers=headers, json=json)
        raise_for_status(response)
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    def close(self) -> None:
        if self._owns_http_client:
            self._http.close()

    def __enter__(self) -> OSINTverse:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

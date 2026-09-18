from __future__ import annotations

import os
from typing import Any

import httpx

from osintverse._async_search import AsyncSearchResource
from osintverse._constants import (
    API_KEY_ENV,
    DEFAULT_BASE_URL,
    DEFAULT_TIMEOUT,
    USER_AGENT,
)
from osintverse._exceptions import AuthenticationError
from osintverse._http import raise_for_status
from osintverse._models import Provider


class AsyncProvidersResource:
    def __init__(self, client: AsyncOSINTverse) -> None:
        self._client = client

    async def list(self) -> list[Provider]:
        """Return the live provider catalog via ``GET /v1/providers``."""
        payload = await self._client.request("GET", "/v1/providers", auth=False)
        return [Provider.model_validate(item) for item in payload]


class AsyncOSINTverse:
    """Async client for the OSINTverse SearchIn API.

    Parameters match :class:`osintverse.OSINTverse`.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.environ.get(API_KEY_ENV)
        self.base_url = base_url.rstrip("/")
        self._owns_http_client = http_client is None
        self._http = http_client or httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
        self.providers = AsyncProvidersResource(self)
        self.search = AsyncSearchResource(self)

    async def health(self) -> dict[str, Any]:
        """Service health check via ``GET /health``."""
        payload = await self.request("GET", "/health", auth=False)
        return payload if isinstance(payload, dict) else {"status": payload}

    async def request(
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
        response = await self._http.request(method, path, headers=headers, json=json)
        raise_for_status(response)
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    async def aclose(self) -> None:
        if self._owns_http_client:
            await self._http.aclose()

    async def __aenter__(self) -> AsyncOSINTverse:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()

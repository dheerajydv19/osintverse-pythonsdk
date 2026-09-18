from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any

from osintverse._constants import DEFAULT_POLL_INTERVAL, DEFAULT_WAIT_TIMEOUT, TERMINAL_STATUSES
from osintverse._exceptions import WaitTimeoutError
from osintverse._models import BulkSearch, Search
from osintverse._search import _raise_if_unsuccessful, _summarize


class AsyncSearchResource:
    def __init__(self, client: Any) -> None:
        self._client = client

    async def create(
        self,
        *,
        provider: str,
        input_type: str,
        query: str,
        premium: bool = False,
        wait: bool = False,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        timeout: float = DEFAULT_WAIT_TIMEOUT,
    ) -> Search:
        """Create a SearchIn job via ``POST /v1/search``."""
        body: dict[str, Any] = {
            "provider": provider,
            "input_type": input_type,
            "query": query,
        }
        if premium:
            body["premium"] = True
        search = Search.model_validate(await self._client.request("POST", "/v1/search", json=body))
        if wait:
            return await self.wait(search, poll_interval=poll_interval, timeout=timeout)
        return search

    async def bulk(
        self,
        *,
        input_type: str,
        queries: Sequence[str],
        providers: Sequence[str],
        premium: bool = False,
        wait: bool = False,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        timeout: float = DEFAULT_WAIT_TIMEOUT,
    ) -> BulkSearch:
        """Create many jobs via ``POST /v1/search/bulk``."""
        body: dict[str, Any] = {
            "input_type": input_type,
            "queries": list(queries),
            "providers": list(providers),
        }
        if premium:
            body["premium"] = True
        batch = BulkSearch.model_validate(
            await self._client.request("POST", "/v1/search/bulk", json=body)
        )
        if wait:
            return await self.wait_bulk(batch, poll_interval=poll_interval, timeout=timeout)
        return batch

    async def retrieve(self, search_id: str) -> Search:
        """Fetch a job via ``GET /v1/search/{id}``."""
        return Search.model_validate(await self._client.request("GET", f"/v1/search/{search_id}"))

    get = retrieve

    async def unlock(self, search_id: str) -> Search:
        """Unlock remaining LeakRadar credentials via ``POST /v1/search/{id}/unlock``."""
        return Search.model_validate(
            await self._client.request(
                "POST",
                f"/v1/search/{search_id}/unlock",
                json={"unlock_remaining": True},
            )
        )

    async def premium(self, search_id: str) -> Search:
        """Run OSINT Industries premium modules via ``POST /v1/search/{id}/premium``."""
        return Search.model_validate(
            await self._client.request(
                "POST",
                f"/v1/search/{search_id}/premium",
                json={"premium": True},
            )
        )

    async def wait(
        self,
        search: Search | str,
        *,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        timeout: float = DEFAULT_WAIT_TIMEOUT,
    ) -> Search:
        """Poll until the job leaves ``running``, then raise on ``failed`` / ``refunded``."""
        current = await self.retrieve(search) if isinstance(search, str) else search
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while current.status == "running":
            if loop.time() >= deadline:
                raise WaitTimeoutError(f"Timed out waiting for search {current.id}")
            if poll_interval > 0:
                await asyncio.sleep(poll_interval)
            current = await self.retrieve(current.id)
        return _raise_if_unsuccessful(current)

    async def wait_bulk(
        self,
        batch: BulkSearch,
        *,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        timeout: float = DEFAULT_WAIT_TIMEOUT,
    ) -> BulkSearch:
        """Poll every ``running`` job in a bulk batch to a terminal status."""
        searches: list[Search] = []
        for search in batch.searches:
            if search.status == "running":
                searches.append(
                    await self._wait_terminal(
                        search,
                        poll_interval=poll_interval,
                        timeout=timeout,
                    )
                )
            else:
                searches.append(search)
        return batch.model_copy(update={"searches": searches, "summary": _summarize(searches)})

    async def _wait_terminal(
        self,
        search: Search,
        *,
        poll_interval: float,
        timeout: float,
    ) -> Search:
        current = search
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while current.status not in TERMINAL_STATUSES:
            if loop.time() >= deadline:
                raise WaitTimeoutError(f"Timed out waiting for search {current.id}")
            if poll_interval > 0:
                await asyncio.sleep(poll_interval)
            current = await self.retrieve(current.id)
        return current

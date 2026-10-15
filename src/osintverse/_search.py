from __future__ import annotations

import time
import uuid
from collections.abc import Sequence
from typing import Any

from osintverse._constants import DEFAULT_POLL_INTERVAL, DEFAULT_WAIT_TIMEOUT, TERMINAL_STATUSES
from osintverse._exceptions import SearchFailedError, SearchRefundedError, WaitTimeoutError
from osintverse._models import BulkSearch, BulkSummary, Quote, Search


class SearchResource:
    def __init__(self, client: Any) -> None:
        self._client = client

    def webhook_secret(self) -> str:
        """Secret for verifying ``callback_url`` events. One per wallet."""
        payload = self._client.request("GET", "/v1/webhooks/secret")
        return str(payload["secret"])

    def quote(
        self,
        *,
        provider: str,
        input_type: str,
        premium: bool = False,
        count: int = 1,
    ) -> Quote:
        """Price ``count`` lookups and check the wallet. Never charges."""
        payload = self._client.request(
            "POST",
            "/v1/search/quote",
            json={
                "provider": provider,
                "input_type": input_type,
                "premium": premium,
                "count": count,
            },
        )
        return Quote.model_validate(payload)

    def create(
        self,
        *,
        provider: str,
        input_type: str,
        query: str,
        premium: bool = False,
        idempotency_key: str | None = None,
        callback_url: str | None = None,
        wait: bool = False,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        timeout: float = DEFAULT_WAIT_TIMEOUT,
    ) -> Search:
        """Create a SearchIn job via ``POST /v1/search``.

        Set ``wait=True`` to poll until the job is no longer ``running``.
        Terminal ``failed`` / ``refunded`` statuses raise.
        """
        body: dict[str, Any] = {
            "provider": provider,
            "input_type": input_type,
            "query": query,
        }
        if premium:
            body["premium"] = True
        if callback_url:
            # Signed POST when the search settles; verify with osintverse.verify_webhook.
            body["callback_url"] = callback_url
        # A retry with the same key returns the original search instead of charging again.
        headers = {"Idempotency-Key": idempotency_key or str(uuid.uuid4())}
        payload = self._client.request("POST", "/v1/search", json=body, headers=headers)
        search = Search.model_validate(payload)
        if wait:
            return self.wait(search, poll_interval=poll_interval, timeout=timeout)
        return search

    def bulk(
        self,
        *,
        input_type: str,
        queries: Sequence[str],
        providers: Sequence[str],
        premium: bool = False,
        callback_url: str | None = None,
        wait: bool = False,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        timeout: float = DEFAULT_WAIT_TIMEOUT,
    ) -> BulkSearch:
        """Create many jobs via ``POST /v1/search/bulk``.

        Partial success is normal. ``wait=True`` polls every ``running`` job;
        failed or refunded jobs stay on the returned batch (inspect ``summary``).
        """
        body: dict[str, Any] = {
            "input_type": input_type,
            "queries": list(queries),
            "providers": list(providers),
        }
        if premium:
            body["premium"] = True
        if callback_url:
            body["callback_url"] = callback_url
        payload = self._client.request("POST", "/v1/search/bulk", json=body)
        batch = BulkSearch.model_validate(payload)
        if wait:
            return self.wait_bulk(batch, poll_interval=poll_interval, timeout=timeout)
        return batch

    def retrieve(self, search_id: str) -> Search:
        """Fetch a job via ``GET /v1/search/{id}``."""
        return Search.model_validate(self._client.request("GET", f"/v1/search/{search_id}"))

    get = retrieve

    def unlock(self, search_id: str) -> Search:
        """Unlock remaining LeakRadar credentials via ``POST /v1/search/{id}/unlock``."""
        return Search.model_validate(
            self._client.request(
                "POST",
                f"/v1/search/{search_id}/unlock",
                json={"unlock_remaining": True},
            )
        )

    def premium(self, search_id: str) -> Search:
        """Run OSINT Industries premium modules via ``POST /v1/search/{id}/premium``."""
        return Search.model_validate(
            self._client.request(
                "POST",
                f"/v1/search/{search_id}/premium",
                json={"premium": True},
            )
        )

    def wait(
        self,
        search: Search | str,
        *,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        timeout: float = DEFAULT_WAIT_TIMEOUT,
    ) -> Search:
        """Poll until the job leaves ``running``, then raise on ``failed`` / ``refunded``."""
        current = self.retrieve(search) if isinstance(search, str) else search
        deadline = time.monotonic() + timeout
        while current.status == "running":
            if time.monotonic() >= deadline:
                raise WaitTimeoutError(f"Timed out waiting for search {current.id}")
            if poll_interval > 0:
                time.sleep(poll_interval)
            current = self.retrieve(current.id)
        return _raise_if_unsuccessful(current)

    def wait_bulk(
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
                    self._wait_terminal(
                        search,
                        poll_interval=poll_interval,
                        timeout=timeout,
                    )
                )
            else:
                searches.append(search)
        return batch.model_copy(update={"searches": searches, "summary": _summarize(searches)})

    def _wait_terminal(
        self,
        search: Search,
        *,
        poll_interval: float,
        timeout: float,
    ) -> Search:
        current = search
        deadline = time.monotonic() + timeout
        while current.status not in TERMINAL_STATUSES:
            if time.monotonic() >= deadline:
                raise WaitTimeoutError(f"Timed out waiting for search {current.id}")
            if poll_interval > 0:
                time.sleep(poll_interval)
            current = self.retrieve(current.id)
        return current


def _raise_if_unsuccessful(search: Search) -> Search:
    if search.status == "failed":
        raise SearchFailedError(search)
    if search.status == "refunded":
        raise SearchRefundedError(search)
    return search


def _summarize(searches: list[Search]) -> BulkSummary:
    counts = {"completed": 0, "running": 0, "failed": 0, "refunded": 0, "pending": 0}
    for search in searches:
        if search.status in counts:
            counts[search.status] += 1
    return BulkSummary.model_validate(counts)

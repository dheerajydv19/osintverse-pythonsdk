from __future__ import annotations

import pytest
import respx
from httpx import Response

from osintverse import AsyncOSINTverse, SearchFailedError
from tests.fixtures import COMPLETED, FAILED, PROVIDERS, RUNNING

BASE = "https://apiv1.osintverse.com"


@pytest.fixture
def client() -> AsyncOSINTverse:
    return AsyncOSINTverse(api_key="ov_test")


@respx.mock
async def test_async_health_and_providers(client: AsyncOSINTverse) -> None:
    respx.get(f"{BASE}/health").mock(return_value=Response(200, json={"status": "ok"}))
    respx.get(f"{BASE}/v1/providers").mock(return_value=Response(200, json=PROVIDERS))
    async with client:
        assert (await client.health())["status"] == "ok"
        providers = await client.providers.list()
        assert providers[0].id == "leakradar-lite"


@respx.mock
async def test_async_create_and_wait(client: AsyncOSINTverse) -> None:
    respx.post(f"{BASE}/v1/search").mock(return_value=Response(200, json=RUNNING))
    respx.get(f"{BASE}/v1/search/{COMPLETED['id']}").mock(
        return_value=Response(200, json=COMPLETED)
    )
    search = await client.search.create(
        provider="facecheck",
        input_type="image",
        query="https://example.com/photo.jpg",
        wait=True,
        poll_interval=0,
    )
    assert search.status == "completed"
    await client.aclose()


@respx.mock
async def test_async_wait_failed(client: AsyncOSINTverse) -> None:
    respx.post(f"{BASE}/v1/search").mock(return_value=Response(200, json=FAILED))
    with pytest.raises(SearchFailedError):
        await client.search.create(
            provider="leakradar-lite",
            input_type="email",
            query="user@example.com",
            wait=True,
            poll_interval=0,
        )
    await client.aclose()


@respx.mock
async def test_async_unlock_premium_bulk(client: AsyncOSINTverse) -> None:
    respx.post(f"{BASE}/v1/search/{COMPLETED['id']}/unlock").mock(
        return_value=Response(200, json=COMPLETED)
    )
    respx.post(f"{BASE}/v1/search/{COMPLETED['id']}/premium").mock(
        return_value=Response(200, json=COMPLETED)
    )
    batch = {
        "batch_id": "batch-async",
        "input_type": "email",
        "total": 1,
        "estimated_cost_usd": "1.00",
        "summary": {"completed": 1, "running": 0, "failed": 0, "refunded": 0, "pending": 0},
        "searches": [COMPLETED],
    }
    respx.post(f"{BASE}/v1/search/bulk").mock(return_value=Response(200, json=batch))
    unlocked = await client.search.unlock(COMPLETED["id"])
    premium = await client.search.premium(COMPLETED["id"])
    result = await client.search.bulk(
        input_type="email",
        queries=["user@example.com"],
        providers=["leakradar-lite"],
        wait=True,
        poll_interval=0,
    )
    assert unlocked.completed
    assert premium.completed
    assert result.total == 1
    await client.aclose()

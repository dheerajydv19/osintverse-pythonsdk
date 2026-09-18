from __future__ import annotations

import pytest
import respx
from httpx import Response

from osintverse import (
    APIError,
    AuthenticationError,
    ForbiddenError,
    NotFoundError,
    OSINTverse,
    PaymentRequiredError,
    SearchFailedError,
    SearchRefundedError,
    ValidationError,
    WaitTimeoutError,
)
from tests.fixtures import COMPLETED, FAILED, PROVIDERS, REFUNDED, RUNNING

BASE = "https://apiv1.osintverse.com"


@pytest.fixture
def client() -> OSINTverse:
    return OSINTverse(api_key="ov_test")


@respx.mock
def test_health(client: OSINTverse) -> None:
    respx.get(f"{BASE}/health").mock(return_value=Response(200, json={"status": "ok"}))
    assert client.health()["status"] == "ok"


@respx.mock
def test_providers_list(client: OSINTverse) -> None:
    respx.get(f"{BASE}/v1/providers").mock(return_value=Response(200, json=PROVIDERS))
    providers = client.providers.list()
    assert providers[0].id == "leakradar-lite"
    assert providers[0].input_types[0].price_usd == "1.00"


@respx.mock
def test_create_search(client: OSINTverse) -> None:
    route = respx.post(f"{BASE}/v1/search").mock(return_value=Response(200, json=COMPLETED))
    search = client.search.create(
        provider="leakradar-lite",
        input_type="email",
        query="user@example.com",
    )
    assert search.id == COMPLETED["id"]
    assert search.completed
    assert search.result is not None
    assert len(search.result.matches) == 1
    sent = route.calls.last.request
    assert sent.headers["x-api-key"] == "ov_test"
    assert sent.headers["user-agent"].startswith("osintverse-python/")
    assert b'"premium"' not in sent.content


@respx.mock
def test_create_search_premium_flag(client: OSINTverse) -> None:
    route = respx.post(f"{BASE}/v1/search").mock(return_value=Response(200, json=COMPLETED))
    client.search.create(
        provider="osint-industries",
        input_type="email",
        query="user@example.com",
        premium=True,
    )
    assert b'"premium":true' in route.calls.last.request.content.replace(b" ", b"")


@respx.mock
def test_wait_polls_until_completed(client: OSINTverse) -> None:
    respx.post(f"{BASE}/v1/search").mock(return_value=Response(200, json=RUNNING))
    respx.get(f"{BASE}/v1/search/{COMPLETED['id']}").mock(
        side_effect=[
            Response(200, json=RUNNING),
            Response(200, json=COMPLETED),
        ]
    )
    search = client.search.create(
        provider="facecheck",
        input_type="image",
        query="https://example.com/photo.jpg",
        wait=True,
        poll_interval=0,
    )
    assert search.status == "completed"


@respx.mock
def test_wait_raises_on_failed(client: OSINTverse) -> None:
    respx.post(f"{BASE}/v1/search").mock(return_value=Response(200, json=FAILED))
    with pytest.raises(SearchFailedError) as exc:
        client.search.create(
            provider="leakradar-lite",
            input_type="email",
            query="user@example.com",
            wait=True,
            poll_interval=0,
        )
    assert "Insufficient balance" in str(exc.value)
    assert exc.value.search.status == "failed"


@respx.mock
def test_wait_raises_on_refunded(client: OSINTverse) -> None:
    respx.post(f"{BASE}/v1/search").mock(return_value=Response(200, json=RUNNING))
    respx.get(f"{BASE}/v1/search/{COMPLETED['id']}").mock(return_value=Response(200, json=REFUNDED))
    with pytest.raises(SearchRefundedError):
        client.search.create(
            provider="facecheck",
            input_type="image",
            query="https://example.com/photo.jpg",
            wait=True,
            poll_interval=0,
        )


@respx.mock
def test_wait_timeout(client: OSINTverse) -> None:
    respx.get(f"{BASE}/v1/search/{COMPLETED['id']}").mock(return_value=Response(200, json=RUNNING))
    with pytest.raises(WaitTimeoutError):
        client.search.wait(RUNNING["id"], poll_interval=0, timeout=0)


@respx.mock
def test_retrieve_and_get_alias(client: OSINTverse) -> None:
    respx.get(f"{BASE}/v1/search/{COMPLETED['id']}").mock(
        return_value=Response(200, json=COMPLETED)
    )
    assert client.search.retrieve(COMPLETED["id"]).id == COMPLETED["id"]
    assert client.search.get(COMPLETED["id"]).query == "user@example.com"


@respx.mock
def test_unlock_and_premium(client: OSINTverse) -> None:
    unlock = respx.post(f"{BASE}/v1/search/{COMPLETED['id']}/unlock").mock(
        return_value=Response(200, json=COMPLETED)
    )
    premium = respx.post(f"{BASE}/v1/search/{COMPLETED['id']}/premium").mock(
        return_value=Response(200, json=COMPLETED)
    )
    client.search.unlock(COMPLETED["id"])
    client.search.premium(COMPLETED["id"])
    assert b'"unlock_remaining":true' in unlock.calls.last.request.content.replace(b" ", b"")
    assert b'"premium":true' in premium.calls.last.request.content.replace(b" ", b"")


@respx.mock
def test_bulk_and_wait_running_jobs(client: OSINTverse) -> None:
    running_job = {**RUNNING, "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"}
    done_job = {**COMPLETED, "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"}
    batch = {
        "batch_id": "batch-1",
        "input_type": "email",
        "total": 2,
        "estimated_cost_usd": "1.30",
        "summary": {"completed": 1, "running": 1, "failed": 0, "refunded": 0, "pending": 0},
        "searches": [running_job, done_job],
    }
    finished = {**running_job, "status": "completed", "result": COMPLETED["result"], "error": None}
    respx.post(f"{BASE}/v1/search/bulk").mock(return_value=Response(200, json=batch))
    respx.get(f"{BASE}/v1/search/{running_job['id']}").mock(
        return_value=Response(200, json=finished)
    )
    result = client.search.bulk(
        input_type="email",
        queries=["alice@example.com", "bob@example.com"],
        providers=["leakradar-lite"],
        wait=True,
        poll_interval=0,
    )
    assert result.summary.running == 0
    assert result.summary.completed == 2
    assert all(item.status == "completed" for item in result.searches)


@respx.mock
def test_bulk_wait_keeps_failed_jobs(client: OSINTverse) -> None:
    batch = {
        "batch_id": "batch-2",
        "input_type": "email",
        "total": 2,
        "estimated_cost_usd": "2.00",
        "summary": {"completed": 1, "running": 0, "failed": 1, "refunded": 0, "pending": 0},
        "searches": [COMPLETED, FAILED],
    }
    respx.post(f"{BASE}/v1/search/bulk").mock(return_value=Response(200, json=batch))
    result = client.search.bulk(
        input_type="email",
        queries=["a@example.com", "b@example.com"],
        providers=["leakradar-lite"],
        wait=True,
        poll_interval=0,
    )
    assert result.summary.failed == 1
    assert result.searches[1].status == "failed"


@pytest.mark.parametrize(
    ("status_code", "exc"),
    [
        (401, AuthenticationError),
        (402, PaymentRequiredError),
        (403, ForbiddenError),
        (404, NotFoundError),
        (422, ValidationError),
        (502, APIError),
    ],
)
@respx.mock
def test_http_errors(client: OSINTverse, status_code: int, exc: type[Exception]) -> None:
    respx.post(f"{BASE}/v1/search").mock(
        return_value=Response(status_code, json={"detail": f"error-{status_code}"})
    )
    with pytest.raises(exc) as raised:
        client.search.create(
            provider="leakradar-lite", input_type="email", query="user@example.com"
        )
    assert f"error-{status_code}" in str(raised.value)
    assert raised.value.status_code == status_code  # type: ignore[attr-defined]


@respx.mock
def test_validation_error_array(client: OSINTverse) -> None:
    respx.post(f"{BASE}/v1/search").mock(
        return_value=Response(
            422,
            json={
                "detail": [
                    {"loc": ["body", "provider"], "msg": "Field required", "type": "missing"}
                ]
            },
        )
    )
    with pytest.raises(ValidationError) as raised:
        client.search.create(provider="leakradar-lite", input_type="email", query="x")
    assert "body.provider" in str(raised.value)


def test_missing_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OSINTVERSE_API_KEY", raising=False)
    client = OSINTverse()
    with pytest.raises(AuthenticationError, match="Missing API key"):
        client.search.create(provider="leakradar-lite", input_type="email", query="x")


def test_reads_env_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OSINTVERSE_API_KEY", "ov_from_env")
    client = OSINTverse()
    assert client.api_key == "ov_from_env"

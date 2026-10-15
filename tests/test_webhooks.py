from __future__ import annotations

import json

import pytest
import respx
from httpx import Response

from osintverse import AsyncOSINTverse, OSINTverse, WebhookVerificationError, verify_webhook
from tests.fixtures import COMPLETED

BASE = "https://apiv1.osintverse.com"

# Published Standard Webhooks example.
SECRET = "whsec_MfKQ9r8GKYqrTwjUPD8ILPZIo2LaLaSw"
BODY = '{"test": 2432232314}'
HEADERS = {
    "Webhook-Id": "msg_p5jXN8AQM9LWM0D4loKWxJek",
    "Webhook-Timestamp": "1614265330",
    "Webhook-Signature": "v1,g0hM9SsE+OTPJTGt/tmIKtSyZlE3uFJELVlNIOLJ1OE=",
}


def test_verify_accepts_a_valid_event() -> None:
    assert verify_webhook(SECRET, HEADERS, BODY, now=1614265330) == {"test": 2432232314}
    assert verify_webhook(SECRET, HEADERS, BODY.encode(), now=1614265400) == {"test": 2432232314}


@pytest.mark.parametrize(
    ("headers", "body", "now"),
    [
        (HEADERS, '{"test": 1}', 1614265330),  # tampered body
        (HEADERS, BODY, 1614265330 + 301),  # too old
        ({**HEADERS, "Webhook-Signature": "v1,AAAA"}, BODY, 1614265330),
        ({"Webhook-Id": "x"}, BODY, 1614265330),
    ],
)
def test_verify_rejects(headers: dict, body: str, now: int) -> None:
    with pytest.raises(WebhookVerificationError):
        verify_webhook(SECRET, headers, body, now=now)


@respx.mock
def test_callback_url_is_sent_and_secret_is_fetched() -> None:
    create = respx.post(f"{BASE}/v1/search").mock(return_value=Response(200, json=COMPLETED))
    bulk = respx.post(f"{BASE}/v1/search/bulk").mock(
        return_value=Response(200, json={"batch_id": "b", "searches": [], "summary": {}})
    )
    respx.get(f"{BASE}/v1/webhooks/secret").mock(
        return_value=Response(200, json={"secret": SECRET})
    )
    client = OSINTverse(api_key="ov_test")
    client.search.create(
        provider="leakradar",
        input_type="email",
        query="a@b.co",
        callback_url="https://hooks.example.com/x",
    )
    assert (
        json.loads(create.calls.last.request.content)["callback_url"]
        == "https://hooks.example.com/x"
    )
    client.search.create(provider="leakradar", input_type="email", query="a@b.co")
    assert "callback_url" not in json.loads(create.calls.last.request.content)
    try:
        client.search.bulk(
            input_type="email",
            queries=["a@b.co"],
            providers=["leakradar"],
            callback_url="https://h.example.com",
        )
    except Exception:
        pass  # Only the request body matters here.
    assert json.loads(bulk.calls.last.request.content)["callback_url"] == "https://h.example.com"
    assert client.search.webhook_secret() == SECRET


@respx.mock
async def test_async_webhook_secret() -> None:
    respx.get(f"{BASE}/v1/webhooks/secret").mock(
        return_value=Response(200, json={"secret": SECRET})
    )
    async with AsyncOSINTverse(api_key="ov_test") as client:
        assert await client.search.webhook_secret() == SECRET

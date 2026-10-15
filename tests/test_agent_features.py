from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx
from httpx import Response

from osintverse import (
    APIError,
    AsyncOSINTverse,
    ConflictError,
    DeviceLoginError,
    OSINTverse,
    PaymentRequiredError,
    device_login,
    read_credentials,
)
from osintverse.__main__ import main
from tests.fixtures import COMPLETED

BASE = "https://apiv1.osintverse.com"
SITE = "https://osintverse.com"

QUOTE = {
    "provider": "leakradar",
    "input_type": "email",
    "count": 2,
    "premium": False,
    "available": True,
    "unit_cost_usd": "0.50",
    "total_cost_usd": "1.00",
    "balance_usd": "0.40",
    "sufficient_balance": False,
    "shortfall_usd": "0.60",
    "top_up_url": "https://osintverse.com/dashboard/billing",
}


@respx.mock
def test_quote_never_charges_and_parses() -> None:
    route = respx.post(f"{BASE}/v1/search/quote").mock(return_value=Response(200, json=QUOTE))
    quote = OSINTverse(api_key="ov_test").search.quote(
        provider="leakradar", input_type="email", count=2
    )
    assert quote.total_cost_usd == "1.00"
    assert not quote.sufficient_balance
    assert json.loads(route.calls.last.request.content) == {
        "provider": "leakradar",
        "input_type": "email",
        "premium": False,
        "count": 2,
    }


@respx.mock
def test_create_sends_an_idempotency_key() -> None:
    route = respx.post(f"{BASE}/v1/search").mock(return_value=Response(200, json=COMPLETED))
    client = OSINTverse(api_key="ov_test")
    client.search.create(provider="leakradar", input_type="email", query="user@example.com")
    client.search.create(provider="leakradar", input_type="email", query="user@example.com")
    first, second = (call.request.headers["idempotency-key"] for call in route.calls)
    assert first and second and first != second

    client.search.create(
        provider="leakradar",
        input_type="email",
        query="user@example.com",
        idempotency_key="retry-1",
    )
    assert route.calls.last.request.headers["idempotency-key"] == "retry-1"


@respx.mock
async def test_async_quote_and_idempotency_key() -> None:
    respx.post(f"{BASE}/v1/search/quote").mock(return_value=Response(200, json=QUOTE))
    route = respx.post(f"{BASE}/v1/search").mock(return_value=Response(200, json=COMPLETED))
    async with AsyncOSINTverse(api_key="ov_test") as client:
        assert (await client.search.quote(provider="leakradar", input_type="email")).count == 2
        await client.search.create(
            provider="leakradar", input_type="email", query="user@example.com", idempotency_key="k"
        )
    assert route.calls.last.request.headers["idempotency-key"] == "k"


@respx.mock
def test_error_code_hint_and_conflict() -> None:
    respx.post(f"{BASE}/v1/search").mock(
        return_value=Response(
            409,
            json={
                "detail": "Idempotency-Key reused",
                "error": {
                    "code": "conflict",
                    "message": "Key reused for another search.",
                    "hint": "Use a new key.",
                },
            },
        )
    )
    with pytest.raises(ConflictError) as exc:
        OSINTverse(api_key="ov_test").search.create(
            provider="leakradar", input_type="email", query="a@b.co"
        )
    assert exc.value.code == "conflict"
    assert exc.value.hint == "Use a new key."
    assert "Key reused for another search." in str(exc.value)


@respx.mock
def test_error_without_envelope_has_no_code() -> None:
    respx.post(f"{BASE}/v1/search").mock(
        return_value=Response(402, json={"detail": "Insufficient balance"})
    )
    with pytest.raises(PaymentRequiredError) as exc:
        OSINTverse(api_key="ov_test").search.create(
            provider="leakradar", input_type="email", query="a@b.co"
        )
    assert isinstance(exc.value, APIError)
    assert exc.value.code is None and exc.value.hint is None


def _save_key(config_dir: Path, key: str = "ov_saved") -> None:
    (config_dir / "config.json").write_text(json.dumps({"api_key": key}), encoding="utf-8")


def test_saved_key_is_used_after_env(
    isolated_config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("OSINTVERSE_API_KEY", raising=False)
    _save_key(isolated_config)
    assert OSINTverse().api_key == "ov_saved"
    assert AsyncOSINTverse().api_key == "ov_saved"

    monkeypatch.setenv("OSINTVERSE_API_KEY", "ov_env")
    assert OSINTverse().api_key == "ov_env"
    assert OSINTverse(api_key="ov_explicit").api_key == "ov_explicit"


DEVICE = {
    "device_code": "dev_123",
    "user_code": "ABCD-EFGH",
    "verification_uri": f"{SITE}/device",
    "verification_uri_complete": f"{SITE}/device?code=ABCD-EFGH",
    "interval": 1,
    "expires_in": 60,
}


def _site() -> httpx.Client:
    return httpx.Client(base_url=SITE)


@respx.mock
def test_device_login_polls_then_saves(isolated_config: Path) -> None:
    respx.post(f"{SITE}/api/cli/device/code").mock(return_value=Response(200, json=DEVICE))
    respx.post(f"{SITE}/api/cli/device/token").mock(
        side_effect=[
            Response(400, json={"error": "authorization_pending"}),
            Response(400, json={"error": "slow_down"}),
            Response(
                200,
                json={
                    "api_key": "ov_new",
                    "key_id": "k1",
                    "key_name": "laptop",
                    "workspace": {"name": "Personal"},
                },
            ),
        ]
    )
    sleeps: list[float] = []
    shown: list[dict] = []
    result = device_login(
        open_browser=False, http_client=_site(), sleep=sleeps.append, on_code=shown.append
    )
    assert result["api_key"] == "ov_new"
    assert shown[0]["user_code"] == "ABCD-EFGH"
    assert sleeps == [1, 1, 6]  # slow_down adds five seconds
    saved = read_credentials()
    assert saved is not None and saved["api_key"] == "ov_new" and saved["key_name"] == "laptop"


@respx.mock
@pytest.mark.parametrize("error", ["access_denied", "expired_token"])
def test_device_login_stops_on_terminal_errors(error: str) -> None:
    respx.post(f"{SITE}/api/cli/device/code").mock(return_value=Response(200, json=DEVICE))
    respx.post(f"{SITE}/api/cli/device/token").mock(
        return_value=Response(400, json={"error": error})
    )
    with pytest.raises(DeviceLoginError) as exc:
        device_login(
            open_browser=False, http_client=_site(), sleep=lambda _s: None, on_code=lambda _d: None
        )
    assert exc.value.code == error
    assert read_credentials() is None


def test_cli_whoami_and_logout(
    isolated_config: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.delenv("OSINTVERSE_API_KEY", raising=False)
    assert main(["whoami", "--json"]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "not_logged_in"

    _save_key(isolated_config)
    assert main(["whoami", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["key_source"] == "config"

    assert main(["logout", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "logged_out"
    assert read_credentials() is None

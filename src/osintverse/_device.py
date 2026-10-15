"""Browser sign-in without copying a key (RFC 8628 device flow against osintverse.com).

The site issues a code, the person approves it at ``/device`` while signed in and
picks the wallet, and the approved code is exchanged once for a new ``ov_`` key.
The key is created at that moment, so its secret is never stored server-side.
"""

from __future__ import annotations

import platform
import time
import webbrowser
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

import httpx

from osintverse._config import write_credentials
from osintverse._constants import USER_AGENT
from osintverse._exceptions import OSINTverseError

DEFAULT_SITE_URL = "https://osintverse.com"


class DeviceLoginError(OSINTverseError):
    """Sign-in was denied, expired, or failed. ``code`` is the RFC 8628 error."""

    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.code = code


def _post(client: httpx.Client, path: str, data: dict[str, str]) -> httpx.Response:
    return client.post(
        path, data=data, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    )


def device_login(
    *,
    site_url: str = DEFAULT_SITE_URL,
    client_name: str | None = None,
    open_browser: bool = True,
    on_code: Callable[[dict[str, Any]], None] | None = None,
    save: bool = True,
    http_client: httpx.Client | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Run the device flow and return ``{api_key, key_id, key_name, workspace}``.

    ``on_code`` receives the code details (``user_code``, ``verification_uri_complete``)
    so you can show them; by default they are printed. With ``save=True`` the key is
    written to the shared config file the JS CLI also reads (see ``config_path()``).
    """
    owns = http_client is None
    client = http_client or httpx.Client(base_url=site_url.rstrip("/"), timeout=30.0)
    try:
        started = _post(
            client,
            "/api/cli/device/code",
            {"client_name": client_name or platform.node() or "python"},
        )
        if started.status_code != 200:
            raise DeviceLoginError(
                f"Could not start sign-in (HTTP {started.status_code}).", "login_failed"
            )
        device = started.json()

        if on_code:
            on_code(device)
        else:
            print(
                f"\nYour code: {device['user_code']}\n\nOpen {device['verification_uri_complete']}"
            )
            print("and approve it while signed in to OSINTverse. Waiting...")
        if open_browser:
            try:
                webbrowser.open(device["verification_uri_complete"])
            except Exception:
                pass  # No browser here; the link is shown anyway.

        interval = max(int(device.get("interval", 5)), 1)
        deadline = time.monotonic() + int(device.get("expires_in", 600))
        while time.monotonic() < deadline:
            sleep(interval)
            try:
                polled = _post(
                    client, "/api/cli/device/token", {"device_code": device["device_code"]}
                )
            except httpx.HTTPError:
                continue
            body = polled.json() if polled.content else {}
            if polled.status_code == 200 and body.get("api_key"):
                if save:
                    write_credentials(
                        {
                            "api_key": body["api_key"],
                            "key_id": body.get("key_id"),
                            "key_name": body.get("key_name"),
                            "workspace": body.get("workspace"),
                            "site_url": site_url,
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                return body
            error = body.get("error")
            if error == "authorization_pending":
                continue
            if error == "slow_down":
                interval += 5
                continue
            if error == "access_denied":
                raise DeviceLoginError("Sign-in was denied.", "access_denied")
            if error == "expired_token":
                raise DeviceLoginError("The code expired. Run login again.", "expired_token")
            raise DeviceLoginError(
                f"Sign-in failed ({error or polled.status_code}).", str(error or "login_failed")
            )
        raise DeviceLoginError("The code expired. Run login again.", "expired_token")
    finally:
        if owns:
            client.close()

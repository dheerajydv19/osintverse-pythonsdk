"""``python -m osintverse login | logout | whoami``.

Shares its saved key with the JS CLI (``npx osintverse``), so signing in with
either works for both. Searches from Python use :class:`osintverse.OSINTverse`.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from osintverse._config import config_path, delete_credentials, read_credentials
from osintverse._constants import API_KEY_ENV, VERSION
from osintverse._device import DEFAULT_SITE_URL, DeviceLoginError, device_login


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m osintverse", description=f"osintverse {VERSION}"
    )
    parser.add_argument("command", choices=["login", "logout", "whoami", "version"])
    parser.add_argument("--json", action="store_true", help="print JSON only")
    parser.add_argument("--no-browser", action="store_true", help="do not open a browser")
    parser.add_argument("--site", default=DEFAULT_SITE_URL, help="site to sign in to")
    args = parser.parse_args(argv)

    def out(value: dict, text: str) -> None:
        print(json.dumps(value) if args.json else text)

    if args.command == "version":
        print(VERSION)
        return 0

    if args.command == "login":

        def show(device: dict) -> None:
            out(
                {
                    "status": "awaiting_approval",
                    "user_code": device["user_code"],
                    "verification_uri_complete": device["verification_uri_complete"],
                },
                f"\nYour code: {device['user_code']}\n\n"
                f"Open {device['verification_uri_complete']}\n"
                "and approve it while signed in to OSINTverse. Waiting...",
            )
            sys.stdout.flush()

        try:
            result = device_login(
                site_url=args.site, open_browser=not args.no_browser, on_code=show
            )
        except DeviceLoginError as error:
            out(
                {"status": "error", "error": {"code": error.code, "message": str(error)}},
                str(error),
            )
            return 1
        workspace = (result.get("workspace") or {}).get("name", "your wallet")
        out(
            {
                "status": "logged_in",
                "key_name": result.get("key_name"),
                "workspace": result.get("workspace"),
                "config_path": str(config_path()),
            },
            f'Signed in. Key "{result.get("key_name")}" bills {workspace}. '
            f"Saved to {config_path()}",
        )
        return 0

    if args.command == "logout":
        removed = delete_credentials()
        out(
            {
                "status": "logged_out" if removed else "not_logged_in",
                "config_path": str(config_path()),
            },
            "Forgot the saved key. It still works until you revoke it at https://osintverse.com/dashboard/api."
            if removed
            else "No saved key.",
        )
        return 0

    saved = read_credentials()
    source = "env" if os.environ.get(API_KEY_ENV) else "config" if saved else None
    out(
        {
            "status": "ok" if source else "not_logged_in",
            "key_source": source,
            "key_name": saved.get("key_name") if source == "config" and saved else None,
            "workspace": saved.get("workspace") if source == "config" and saved else None,
            "config_path": str(config_path()),
        },
        "Not signed in. Run: python -m osintverse login"
        if not source
        else f"Using the API key from {API_KEY_ENV}."
        if source == "env"
        else f'Using saved key "{saved.get("key_name") if saved else ""}".',
    )
    return 0 if source else 1


if __name__ == "__main__":
    raise SystemExit(main())

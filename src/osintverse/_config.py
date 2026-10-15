"""Saved credentials, shared with the JavaScript CLI (``npx osintverse login``).

Location: ``OSINTVERSE_CONFIG_DIR``, else ``%APPDATA%\\osintverse`` on Windows,
else ``$XDG_CONFIG_HOME/osintverse`` or ``~/.config/osintverse``. The file is
``config.json`` with at least ``{"api_key": "ov_..."}``.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


def config_path() -> Path:
    override = os.environ.get("OSINTVERSE_CONFIG_DIR")
    if override:
        return Path(override) / "config.json"
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "osintverse" / "config.json"


def read_credentials(path: Path | None = None) -> dict[str, Any] | None:
    try:
        data = json.loads((path or config_path()).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if isinstance(data, dict) and isinstance(data.get("api_key"), str) and data["api_key"]:
        return data
    return None


def saved_api_key() -> str | None:
    credentials = read_credentials()
    return credentials["api_key"] if credentials else None


def write_credentials(credentials: dict[str, Any], path: Path | None = None) -> Path:
    target = path or config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(credentials, indent=2) + "\n", encoding="utf-8")
    try:
        target.chmod(0o600)
    except OSError:
        pass  # Windows ignores POSIX modes; the file lives in the user's own profile.
    return target


def delete_credentials(path: Path | None = None) -> bool:
    target = path or config_path()
    try:
        target.unlink()
    except FileNotFoundError:
        return False
    return True

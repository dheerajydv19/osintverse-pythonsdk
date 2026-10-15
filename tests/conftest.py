from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Keep tests away from the real saved key written by `osintverse login`."""
    monkeypatch.setenv("OSINTVERSE_CONFIG_DIR", str(tmp_path))
    return tmp_path

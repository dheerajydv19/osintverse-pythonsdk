from __future__ import annotations

from typing import Any

COMPLETED: dict[str, Any] = {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "completed",
    "provider": "leakradar-lite",
    "input_type": "email",
    "query": "user@example.com",
    "cost_usd": "1.00",
    "balance_after": "9.00",
    "result": {
        "sources": [{"name": "leakradar", "total": 1}],
        "matches": [{"type": "leak", "username": "user@example.com"}],
        "raw": None,
    },
    "error": None,
    "poll_url": None,
}

RUNNING: dict[str, Any] = {
    **COMPLETED,
    "status": "running",
    "provider": "facecheck",
    "input_type": "image",
    "query": "https://example.com/photo.jpg",
    "cost_usd": "0.50",
    "balance_after": "9.45",
    "result": None,
    "poll_url": "/v1/search/550e8400-e29b-41d4-a716-446655440000",
}

FAILED: dict[str, Any] = {
    **COMPLETED,
    "status": "failed",
    "result": None,
    "error": "Insufficient balance. Required $1.00, available $0.00.",
}

REFUNDED: dict[str, Any] = {
    **COMPLETED,
    "status": "refunded",
    "result": None,
    "error": "Upstream provider failed after billing.",
}

PROVIDERS: list[dict[str, Any]] = [
    {
        "id": "leakradar-lite",
        "name": "LeakRadar",
        "category": "Breach intelligence",
        "max_unlocks": 1000,
        "extra_unlock_usd_per_1k": "0.50",
        "premium_usd": None,
        "input_types": [
            {"id": "email", "price_usd": "1.00"},
            {"id": "username", "price_usd": "1.00"},
        ],
    }
]

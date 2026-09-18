from __future__ import annotations

from typing import Any

import httpx

from osintverse._exceptions import (
    APIError,
    AuthenticationError,
    ForbiddenError,
    NotFoundError,
    PaymentRequiredError,
    ValidationError,
)


def extract_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        text = response.text.strip()
        return text or f"HTTP {response.status_code}"

    detail = payload.get("detail") if isinstance(payload, dict) else payload
    if isinstance(detail, str) and detail:
        return detail
    if isinstance(detail, list):
        parts: list[str] = []
        for item in detail:
            if isinstance(item, dict):
                loc = item.get("loc")
                msg = item.get("msg") or str(item)
                if loc:
                    parts.append(f"{_format_loc(loc)}: {msg}")
                else:
                    parts.append(str(msg))
            else:
                parts.append(str(item))
        if parts:
            return "; ".join(parts)
    if detail is not None:
        return str(detail)
    return f"HTTP {response.status_code}"


def _format_loc(loc: Any) -> str:
    if isinstance(loc, (list, tuple)):
        return ".".join(str(part) for part in loc)
    return str(loc)


def raise_for_status(response: httpx.Response) -> None:
    if response.is_success:
        return

    message = extract_detail(response)
    body: Any
    try:
        body = response.json()
    except ValueError:
        body = response.text

    mapping: dict[int, type[APIError]] = {
        401: AuthenticationError,
        402: PaymentRequiredError,
        403: ForbiddenError,
        404: NotFoundError,
        422: ValidationError,
    }
    error_cls = mapping.get(response.status_code, APIError)
    raise error_cls(message, status_code=response.status_code, body=body)

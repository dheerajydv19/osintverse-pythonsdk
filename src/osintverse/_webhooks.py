"""Verify ``callback_url`` events (Standard Webhooks, https://www.standardwebhooks.com)."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import time
from collections.abc import Mapping
from typing import Any

from osintverse._exceptions import OSINTverseError

DEFAULT_TOLERANCE_SECONDS = 300


class WebhookVerificationError(OSINTverseError):
    """The event is unsigned, signed with another secret, tampered with, or too old."""


def verify_webhook(
    secret: str,
    headers: Mapping[str, str],
    body: bytes | str,
    *,
    tolerance: int = DEFAULT_TOLERANCE_SECONDS,
    now: float | None = None,
) -> dict[str, Any]:
    """Check a callback's signature and timestamp and return the parsed event.

    ``secret`` comes from ``client.search.webhook_secret()``. Pass the raw request body
    (bytes or the exact string), not re-serialized JSON. Header names are matched
    case-insensitively. Raises :class:`WebhookVerificationError` when the check fails.
    """
    lowered = {key.lower(): value for key, value in headers.items()}
    message_id = lowered.get("webhook-id")
    timestamp = lowered.get("webhook-timestamp")
    signatures = lowered.get("webhook-signature")
    if not message_id or not timestamp or not signatures:
        raise WebhookVerificationError("Missing webhook-id, -timestamp, or -signature header.")
    try:
        sent_at = int(timestamp)
    except ValueError as exc:
        raise WebhookVerificationError("Invalid webhook-timestamp.") from exc
    if abs((now if now is not None else time.time()) - sent_at) > tolerance:
        raise WebhookVerificationError("Webhook timestamp is outside the allowed window.")

    try:
        key = base64.b64decode(secret.removeprefix("whsec_"), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise WebhookVerificationError("Secret is not a whsec_ value.") from exc
    raw = body if isinstance(body, bytes) else body.encode("utf-8")
    digest = hmac.new(key, f"{message_id}.{timestamp}.".encode() + raw, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("ascii")

    for part in signatures.split():
        version, _, value = part.partition(",")
        if version == "v1" and hmac.compare_digest(value, expected):
            return json.loads(raw)
    raise WebhookVerificationError("No matching signature.")

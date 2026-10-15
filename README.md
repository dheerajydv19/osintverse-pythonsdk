# Official Python client for the OSINTverse SearchIn API

Official client for [SearchIn](https://osintverse.com/searchin) on [osintverse.com](https://osintverse.com): one API for LeakRadar, OSINT Industries, Facecheck.id, SecurityTrails, and every other SearchIn provider. Same prepaid wallet as the UI.

```bash
pip install osintverse
```

Python **3.10+**. Talks to `https://apiv1.osintverse.com`. Not affiliated with other products that reuse the OSINTverse name.

For local open-source tools on Linux, [OTinstaller](https://github.com/OSINTVerseHQ/OTinstaller) installs them by name (`pipx install otinstaller`). This client is the SearchIn API, not that installer.

Full guide: [osintverse.com/docs/python](https://osintverse.com/docs/python)

## Auth

Sign in once from a terminal. It shows a code, you approve it at osintverse.com/device, and a new key is saved to the same config file the JS CLI uses (`%APPDATA%\osintverse` on Windows, `~/.config/osintverse` elsewhere), so `npx osintverse login` works for both:

```bash
python -m osintverse login     # --json for agents, --no-browser on servers
python -m osintverse whoami
python -m osintverse logout    # forgets the saved key; revoke it in the dashboard
```

Or create a key at [Dashboard → API keys](https://osintverse.com/dashboard/api) (`ov_` prefix, shown once).

```python
from osintverse import OSINTverse

client = OSINTverse()  # api_key="ov_…", else OSINTVERSE_API_KEY, else the saved key
```

`device_login()` runs the same sign-in from code.

`health()` and `providers.list()` work without a key. Search methods require one.

## Quick start

```python
from osintverse import OSINTverse

with OSINTverse() as client:
    search = client.search.create(
        provider="leakradar-lite",
        input_type="email",
        query="user@example.com",
        wait=True,  # poll while status is running (~2s, 120s timeout)
    )
    print(search.status, search.cost_usd)
    print(search.result.matches if search.result else [])
```

Async:

```python
from osintverse import AsyncOSINTverse

async with AsyncOSINTverse() as client:
    search = await client.search.create(
        provider="leakradar-lite",
        input_type="email",
        query="user@example.com",
        wait=True,
    )
```

## Methods

| SDK | HTTP |
| --- | --- |
| `client.health()` | `GET /health` |
| `client.providers.list()` | `GET /v1/providers` |
| `client.search.quote(...)` | `POST /v1/search/quote` (never charges) |
| `client.search.webhook_secret()` | `GET /v1/webhooks/secret` |
| `client.search.create(...)` | `POST /v1/search` |
| `client.search.bulk(...)` | `POST /v1/search/bulk` |
| `client.search.retrieve(id)` | `GET /v1/search/{id}` |
| `client.search.wait(id)` | poll retrieve |
| `client.search.unlock(id)` | `POST /v1/search/{id}/unlock` |
| `client.search.premium(id)` | `POST /v1/search/{id}/premium` |

```python
batch = client.search.bulk(
    input_type="email",
    queries=["alice@example.com", "bob@example.com"],
    providers=["leakradar-lite", "dehashed"],
    wait=True,
)
print(batch.summary)

client.search.unlock(search.id)   # LeakRadar leftover credentials
client.search.premium(search.id)  # OSINT Industries premium modules
```

Quote before you run, and stop when the wallet is short:

```python
quote = client.search.quote(provider="leakradar-lite", input_type="email", count=2)
if not quote.sufficient_balance:
    print(f"Add ${quote.shortfall_usd} at {quote.top_up_url}")
```

Every `create` sends an `Idempotency-Key` (a fresh UUID unless you pass `idempotency_key=`). Pass your own and reuse it when you retry after a timeout, and the API returns the original search instead of charging again.

`wait=True` on **create** raises `SearchFailedError` / `SearchRefundedError` if the job ends `failed` or `refunded`. Bulk wait polls running jobs and returns the batch — inspect `summary` for partial success (max 50 queries, 100 jobs).

This package is **SearchIn lookups only**. GraphIn (canvas, path, share) is the web desk.

## Webhooks

Pass `callback_url` to `create` or `bulk` and the API POSTs a signed event there when each search completes, fails, or is refunded, so you need not poll. The event has ids, status, and cost, never the query or results; fetch those with `retrieve`.

```python
from osintverse import OSINTverse, verify_webhook

client = OSINTverse()
secret = client.search.webhook_secret()  # once; one per wallet
client.search.create(
    provider="facecheck",
    input_type="image",
    query="https://example.com/photo.jpg",
    callback_url="https://hooks.example.com/osintverse",
)

# In your web handler, with the raw body:
event = verify_webhook(secret, request.headers, request.body)  # raises WebhookVerificationError
search = client.search.retrieve(event["data"]["id"])
```

The URL must be public `https` on port 443. Events follow [Standard Webhooks](https://www.standardwebhooks.com); details at [osintverse.com/docs/api/search](https://osintverse.com/docs/api/search#webhooks).

## Errors

| HTTP | Exception |
| --- | --- |
| 401 | `AuthenticationError` |
| 402 | `PaymentRequiredError` |
| 403 | `ForbiddenError` |
| 404 | `NotFoundError` |
| 409 | `ConflictError` (idempotency key reused for a different search) |
| 422 | `ValidationError` |
| 5xx | `APIError` |

Every `APIError` has `status_code`, `detail`, and, when the API sends them, `code` (for example `insufficient_balance`) and `hint` (what to do next).

Job `status: failed` / `refunded` on HTTP 200 raise `SearchFailedError` / `SearchRefundedError` when you pass `wait=True` on create. Poll timeout raises `WaitTimeoutError`.

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check src tests
```

## License

MIT

## Publishing

PyPI project: [osintverse](https://pypi.org/project/osintverse/). GitHub Actions publishes on `v*` tags via Trusted Publishing (workflow `publish.yml` in `dheerajydv19/osintverse-pythonsdk`).

Bump `version` in `pyproject.toml` and `VERSION` in `src/osintverse/_constants.py`, then `git tag vX.Y.Z && git push origin vX.Y.Z`.

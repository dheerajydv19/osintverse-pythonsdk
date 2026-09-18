# Official Python client for the OSINTverse SearchIn API (osintverse.com).

This is the **official** client for [OSINTverse](https://osintverse.com) SearchIn: one REST API for LeakRadar, OSINT Industries, Facecheck.id, SecurityTrails, and every other SearchIn provider.

It talks to **`https://apiv1.osintverse.com`**. It is not affiliated with other products that reuse the OSINTverse name.

## Install

```bash
pip install osintverse
```

Create an API key at [Dashboard → API keys](https://osintverse.com/dashboard/api). Keys use the `ov_` prefix and are shown only once.

## Quick start

```python
from osintverse import OSINTverse

client = OSINTverse()  # reads OSINTVERSE_API_KEY, or pass api_key="ov_…"

providers = client.providers.list()
search = client.search.create(
    provider="leakradar-lite",
    input_type="email",
    query="user@example.com",
    wait=True,  # poll GET /v1/search/{id} every ~2s when status is running
)
print(search.status, search.cost_usd, len(search.result.matches if search.result else []))
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

## Auth

- Header: `x-api-key` (the SDK sets this for you)
- Env: `OSINTVERSE_API_KEY`
- Docs: [https://osintverse.com/docs/python](https://osintverse.com/docs/python)

`GET /health` and `GET /v1/providers` do not require a key. Search routes do.

## Methods

| SDK | HTTP |
| --- | --- |
| `client.health()` | `GET /health` |
| `client.providers.list()` | `GET /v1/providers` |
| `client.search.create(...)` | `POST /v1/search` |
| `client.search.bulk(...)` | `POST /v1/search/bulk` |
| `client.search.retrieve(id)` | `GET /v1/search/{id}` |
| `client.search.unlock(id)` | `POST /v1/search/{id}/unlock` |
| `client.search.premium(id)` | `POST /v1/search/{id}/premium` |

```python
batch = client.search.bulk(
    input_type="email",
    queries=["alice@example.com", "bob@example.com"],
    providers=["leakradar-lite", "dehashed"],
    wait=True,
)

client.search.unlock(search.id)   # LeakRadar leftover credentials
client.search.premium(search.id)  # OSINT Industries premium modules
```

`wait=True` on **create** raises `SearchFailedError` / `SearchRefundedError` if the job ends in `failed` or `refunded`. Bulk wait polls running jobs and returns the batch — inspect `summary` for partial success.

## Errors

HTTP `{ "detail": "…" }` maps to `AuthenticationError` (401), `PaymentRequiredError` (402), `ForbiddenError` (403), `NotFoundError` (404), `ValidationError` (422), and `APIError` (5xx).

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check src tests
```

## License

MIT

## Publishing

CI runs lint and tests on every push. PyPI publishes from `.github/workflows/publish.yml` on `v*` tags using [Trusted Publishing](https://docs.pypi.org/trusted-publishers/).

1. On PyPI, add a pending trusted publisher for project **osintverse**: GitHub owner `dheerajydv19`, repo `osintverse-pythonsdk`, workflow `publish.yml`, environment blank.
2. Tag a release: `git tag v0.1.0 && git push origin v0.1.0`.


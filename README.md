# Official Python client for the OSINTverse SearchIn API

Official client for [SearchIn](https://osintverse.com/searchin) on [osintverse.com](https://osintverse.com): one API for LeakRadar, OSINT Industries, Facecheck.id, SecurityTrails, and every other SearchIn provider. Same prepaid wallet as the UI.

```bash
pip install osintverse
```

Python **3.10+**. Talks to `https://apiv1.osintverse.com`. Not affiliated with other products that reuse the OSINTverse name.

Full guide: [osintverse.com/docs/python](https://osintverse.com/docs/python)

## Auth

Create a key at [Dashboard → API keys](https://osintverse.com/dashboard/api) (`ov_` prefix, shown once).

```python
from osintverse import OSINTverse

client = OSINTverse()  # OSINTVERSE_API_KEY, or api_key="ov_…"
```

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

`wait=True` on **create** raises `SearchFailedError` / `SearchRefundedError` if the job ends `failed` or `refunded`. Bulk wait polls running jobs and returns the batch — inspect `summary` for partial success (max 50 queries, 100 jobs).

This package is **SearchIn lookups only**. GraphIn (canvas, path, share) is the web desk.

## Errors

| HTTP | Exception |
| --- | --- |
| 401 | `AuthenticationError` |
| 402 | `PaymentRequiredError` |
| 403 | `ForbiddenError` |
| 404 | `NotFoundError` |
| 422 | `ValidationError` |
| 5xx | `APIError` |

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

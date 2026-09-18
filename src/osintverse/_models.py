from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SearchStatus = Literal["pending", "running", "completed", "failed", "refunded"]
InputType = Literal["email", "username", "phone", "domain", "name", "image", "ip"]
ProviderId = Literal[
    "osint-industries",
    "leakradar-lite",
    "leakosintbot",
    "facecheck",
    "picarta",
    "predicta-search",
    "dehashed",
    "whoxy",
    "whoisxml",
    "securitytrails",
    "snusbase",
    "shodan",
]


class InputTypePrice(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    price_usd: str | None = None


class Provider(BaseModel):
    """Provider catalog row from ``GET /v1/providers``."""

    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    category: str
    max_unlocks: int | None = None
    extra_unlock_usd_per_1k: str | None = None
    premium_usd: str | None = None
    input_types: list[InputTypePrice]


class ProviderResult(BaseModel):
    """Normalized search results from the upstream provider."""

    model_config = ConfigDict(extra="allow")

    sources: list[dict[str, Any]] = Field(default_factory=list)
    matches: list[dict[str, Any]] = Field(default_factory=list)
    raw: Any = None


class Search(BaseModel):
    """Search job status and results."""

    model_config = ConfigDict(extra="allow")

    id: str
    status: SearchStatus
    provider: str
    input_type: str
    query: str
    cost_usd: str | None = None
    balance_after: str | None = None
    result: ProviderResult | None = None
    error: str | None = None
    poll_url: str | None = None
    has_stored_result: bool = False
    result_expires_at: str | None = None
    batch_id: str | None = None

    @property
    def completed(self) -> bool:
        return self.status == "completed"

    @property
    def running(self) -> bool:
        return self.status == "running"


class BulkSummary(BaseModel):
    model_config = ConfigDict(extra="allow")

    completed: int = 0
    running: int = 0
    failed: int = 0
    refunded: int = 0
    pending: int = 0


class BulkSearch(BaseModel):
    """Bulk search batch: one :class:`Search` per (query, provider) job."""

    model_config = ConfigDict(extra="allow")

    batch_id: str
    input_type: str
    total: int
    estimated_cost_usd: str
    summary: BulkSummary
    searches: list[Search]

from datetime import datetime
from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    content: str | None = None
    source: str
    published_at: datetime | None = None
    score: float | None = None
    summary: str | None = None


class RankedListing(BaseModel):
    title: str
    url: str
    snippet: str
    source: str
    published_at: datetime | None = None
    deadline: datetime | None = None
    content_hash: str | None = None
    match_score: float = 0.0
    rationale: str = ""
    red_flags: list[str] = Field(default_factory=list)
    role_category: str = "other"


class SearchCreate(BaseModel):
    name: str
    interval_minutes: int = Field(ge=1)
    config: dict[str, object]


class SearchRead(BaseModel):
    id: int
    name: str
    interval_minutes: int
    config: dict[str, object]
    enabled: bool

    class Config:
        from_attributes = True

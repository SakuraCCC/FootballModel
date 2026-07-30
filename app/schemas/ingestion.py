from datetime import date

from pydantic import BaseModel, Field


class CompetitionSyncRequest(BaseModel):
    season: int | None = Field(default=None, ge=2000, le=2100)


class MatchSyncRequest(BaseModel):
    competition_code: str = Field(min_length=1, max_length=32)
    season: int = Field(ge=2000, le=2100)
    match_date: date | None = None


class IngestionSummaryRead(BaseModel):
    source_name: str
    snapshot_id: str
    processed: int
    saved: int
    skipped: int
    quality_levels: dict[str, int]

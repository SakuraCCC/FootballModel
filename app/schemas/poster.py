from datetime import datetime

from pydantic import BaseModel, Field


class PosterGenerateRequest(BaseModel):
    report_id: str = Field(min_length=1, max_length=36)


class PosterGenerateResponse(BaseModel):
    poster_id: str
    poster_version: str | None = None


class PosterRead(BaseModel):
    id: str
    report_id: str
    prediction_id: str
    competition_style: str
    image_url: str
    template_version: str
    created_at: datetime
    review_status: str = "draft"
    reviewed_at: datetime | None = None
    review_notes: str | None = None
    model_version: str | None = None
    feature_version: str | None = None
    data_version: str | None = None
    prompt_version: str | None = None
    poster_version: str | None = None

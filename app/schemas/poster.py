from datetime import datetime

from pydantic import BaseModel, Field


class PosterGenerateRequest(BaseModel):
    report_id: str = Field(min_length=1, max_length=36)


class PosterGenerateResponse(BaseModel):
    poster_id: str


class PosterRead(BaseModel):
    id: str
    report_id: str
    prediction_id: str
    competition_style: str
    image_url: str
    template_version: str
    created_at: datetime

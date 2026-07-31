from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ManualImportRequest(BaseModel):
    source_name: str = Field(min_length=1, max_length=160)
    source_url: str | None = None
    retrieved_at: datetime | None = None
    certainty: str = "reported"
    imported_by: str = "admin"
    format: str = "json"
    records: list[dict[str, Any]] | None = None
    payload: Any | None = None


class SetupCheckRead(BaseModel):
    name: str
    status: str


class SetupStatusRead(BaseModel):
    checks: list[SetupCheckRead]
    data_mode: str


class DataModeRequest(BaseModel):
    mode: str = Field(pattern="^(api_football|hybrid|manual|offline)$")


class BatchExportRead(BaseModel):
    batch_id: str
    export_id: str
    status: str
    download_url: str

from datetime import datetime

from pydantic import BaseModel


class AutomationFailureRead(BaseModel):
    id: str
    match_id: str
    task_id: str | None
    retry_count: int
    failed_step: str | None
    failure_reason: str | None
    last_retry_time: datetime | None
    created_at: datetime


class ProviderStatusRead(BaseModel):
    provider: str
    status: str
    response_time_ms: float | None
    last_sync: datetime | None
    data_quality: str
    plan_name: str | None = None
    daily_remaining: int | None = None
    quota_state: str | None = None

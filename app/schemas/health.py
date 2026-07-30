from typing import Literal

from pydantic import BaseModel


class DependencyStatus(BaseModel):
    status: Literal["ok", "error"]


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    database: DependencyStatus
    redis: DependencyStatus


class ServiceHealthResponse(BaseModel):
    status: Literal["ok", "error"]


class SchedulerHealthResponse(BaseModel):
    status: Literal["ok", "error"]
    database: DependencyStatus
    redis: DependencyStatus
    beat_status: Literal["ok", "error"]
    last_task_execution: str | None = None

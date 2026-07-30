from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.models import AutomationRun
from app.schemas.automation import AutomationFailureRead, ProviderStatusRead
from app.services.provider_health import ProviderHealthService

router = APIRouter(tags=["automation"])


@router.get("/automation/failures", response_model=list[AutomationFailureRead])
def automation_failures(session: Session = Depends(get_db_session)) -> list[AutomationFailureRead]:
    records = session.scalars(
        select(AutomationRun)
        .where(AutomationRun.status == "failed")
        .order_by(AutomationRun.updated_at.desc())
        .limit(50)
    )
    return [
        AutomationFailureRead(
            id=item.id,
            match_id=item.match_id,
            task_id=item.task_id,
            retry_count=item.retry_count,
            failed_step=item.failed_step,
            failure_reason=item.failure_reason,
            last_retry_time=item.last_retry_time,
            created_at=item.created_at,
        )
        for item in records
    ]


@router.get("/providers/status", response_model=list[ProviderStatusRead])
def provider_status(session: Session = Depends(get_db_session)) -> list[ProviderStatusRead]:
    return [ProviderStatusRead(**item) for item in ProviderHealthService(session).statuses()]

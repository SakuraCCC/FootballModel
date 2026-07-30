from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SchedulerHeartbeat


def record_heartbeat(session: Session, task_name: str, task_id: str | None = None) -> None:
    heartbeat = session.scalar(
        select(SchedulerHeartbeat).where(SchedulerHeartbeat.task_name == task_name)
    )
    if heartbeat is None:
        heartbeat = SchedulerHeartbeat(
            task_name=task_name, last_executed_at=datetime.now(UTC), task_id=task_id
        )
        session.add(heartbeat)
    else:
        heartbeat.last_executed_at = datetime.now(UTC)
        heartbeat.task_id = task_id
    session.commit()

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.models import Competition, ConfidenceCalibration, ModelVersion
from app.services.evaluation import CalibrationService

router = APIRouter(prefix="/calibration", tags=["calibration"])


@router.post("/refresh")
def refresh_calibration(
    competition_code: str | None = None, session: Session = Depends(get_db_session)
) -> list[dict]:
    competition_id = None
    if competition_code:
        competition = session.scalar(
            select(Competition).where(Competition.code == competition_code.upper())
        )
        if competition is None:
            return []
        competition_id = competition.id
    records = CalibrationService(session).refresh(competition_id)
    return [
        {
            "id": item.id,
            "probability_bin": item.probability_bin,
            "sample_count": item.sample_count,
            "calibration_error": item.calibration_error,
            "reliability": item.reliability,
        }
        for item in records
    ]


@router.get("/summary")
def calibration_summary(
    competition_code: str | None = None, session: Session = Depends(get_db_session)
) -> list[dict]:
    statement = select(ConfidenceCalibration, ModelVersion).join(
        ModelVersion, ModelVersion.id == ConfidenceCalibration.model_version_id
    )
    if competition_code:
        competition = session.scalar(
            select(Competition).where(Competition.code == competition_code.upper())
        )
        if competition is None:
            return []
        statement = statement.where(ConfidenceCalibration.competition_id == competition.id)
    return [
        {
            "model": f"{version.name}:{version.version}",
            "probability_bin": record.probability_bin,
            "sample_count": record.sample_count,
            "observed_frequency": record.observed_frequency,
            "calibration_error": record.calibration_error,
            "reliability": record.reliability,
        }
        for record, version in session.execute(
            statement.order_by(ModelVersion.name, ConfidenceCalibration.probability_bin)
        )
    ]

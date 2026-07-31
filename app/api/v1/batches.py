from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.models import BatchExport
from app.schemas.phase11 import BatchExportRead
from app.services.batch_export import BatchExportError, BatchExportService

router = APIRouter(prefix="/batches", tags=["batches"])


@router.post("/{batch_id}/export", response_model=BatchExportRead)
def export_batch(batch_id: str, session: Session = Depends(get_db_session)) -> BatchExportRead:
    try:
        export = BatchExportService(session).export(batch_id)
    except BatchExportError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return BatchExportRead(batch_id=batch_id, export_id=export.id, status=export.status, download_url=f"/api/v1/batches/{batch_id}/download")


@router.get("/{batch_id}/download")
def download_batch(batch_id: str, session: Session = Depends(get_db_session)) -> FileResponse:
    export = session.query(BatchExport).filter_by(batch_id=batch_id).first()
    if export is None or not Path(export.file_path).is_file():
        raise HTTPException(status_code=404, detail="batch_export_not_found")
    return FileResponse(export.file_path, media_type="application/zip", filename=f"{batch_id}.zip")

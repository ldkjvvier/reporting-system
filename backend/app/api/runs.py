"""Consulta de corridas y descarga de los archivos generados."""
import os
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth.permissions import require_report_access
from app.auth.security import get_current_user
from app.db import get_db
from app.models import ReportRun, User
from app.schemas import ReportRunOut

router = APIRouter(prefix="/api", tags=["runs"])


@router.get("/reports/{report_id}/runs", response_model=List[ReportRunOut])
def list_runs(
    report_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_report_access(db, report_id, user)
    runs = (
        db.query(ReportRun)
        .filter(ReportRun.report_id == report_id)
        .order_by(ReportRun.id.desc())
        .limit(limit)
        .all()
    )
    return runs


@router.get("/runs/{run_id}/download")
def download_run(run_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    run = db.get(ReportRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Corrida no encontrada")
    require_report_access(db, run.report_id, user)
    if not run.file_path or not os.path.exists(run.file_path):
        raise HTTPException(status_code=404, detail="Archivo no disponible")
    return FileResponse(
        run.file_path,
        filename=os.path.basename(run.file_path),
        media_type="application/octet-stream",
    )

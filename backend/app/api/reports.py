"""CRUD de reportes y ejecución manual."""
from datetime import datetime
from typing import List, Optional
from zoneinfo import ZoneInfo

from croniter import croniter
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.permissions import require_report_access, team_role, user_team_ids
from app.auth.security import get_current_user
from app.config import settings
from app.db import get_db, session_scope
from app.models import Report, User
from app.reporting.service import run_report
from app.schemas import ReportCreate, ReportOut, ReportUpdate
from app.scheduling import sync

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _run_in_process(report_id: int) -> None:
    """Ejecuta el reporte de forma síncrona (modo local sin Celery)."""
    with session_scope() as db:
        run_report(db, report_id, trigger="manual")


def _next_run(report: Report) -> Optional[datetime]:
    """Próxima ejecución, calculada en la zona del scheduler (horario de Chile).

    Coincide con el disparo real de Celery Beat, que interpreta el cron en
    ``settings.SCHEDULER_TIMEZONE``. Se devuelve como datetime con offset.
    """
    if not report.enabled:
        return None
    try:
        tz = ZoneInfo(settings.SCHEDULER_TIMEZONE)
        base = datetime.now(tz)
        return croniter(report.cron, base).get_next(datetime)
    except Exception:  # noqa: BLE001
        return None


def _to_out(report: Report) -> ReportOut:
    out = ReportOut.model_validate(report)
    out.next_run = _next_run(report)
    return out


def _require_editor_team(db: Session, user: User, team_id: int) -> None:
    """Verifica que el usuario pueda crear/editar reportes en el equipo indicado."""
    if team_role(db, user, team_id) != "editor":
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso de edición en este equipo",
        )


@router.get("", response_model=List[ReportOut])
def list_reports(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(Report)
    if not user.is_admin:
        team_ids = user_team_ids(db, user)
        if not team_ids:
            return []
        query = query.filter(Report.team_id.in_(team_ids))
    reports = query.order_by(Report.id.desc()).all()
    return [_to_out(r) for r in reports]


@router.post("", response_model=ReportOut, status_code=201)
def create_report(
    payload: ReportCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_editor_team(db, user, payload.team_id)
    report = Report(
        created_by_id=user.id,
        **payload.model_dump(mode="json"),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    if settings.USE_CELERY:
        sync.upsert_schedule(report)
    return _to_out(report)


@router.get("/{report_id}", response_model=ReportOut)
def get_report(report_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _to_out(require_report_access(db, report_id, user))


@router.put("/{report_id}", response_model=ReportOut)
def update_report(
    report_id: int,
    payload: ReportUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    report = require_report_access(db, report_id, user, need_edit=True)
    # Si se mueve el reporte a otro equipo, exige permiso de edición también allí.
    if payload.team_id != report.team_id:
        _require_editor_team(db, user, payload.team_id)
    for key, value in payload.model_dump(mode="json").items():
        setattr(report, key, value)
    db.commit()
    db.refresh(report)
    if settings.USE_CELERY:
        sync.upsert_schedule(report)  # reprograma o elimina según 'enabled'
    return _to_out(report)


@router.delete("/{report_id}", status_code=204)
def delete_report(report_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    report = require_report_access(db, report_id, user, need_edit=True)
    if settings.USE_CELERY:
        sync.remove_schedule(report.id)
    db.delete(report)
    db.commit()


@router.post("/{report_id}/run", status_code=202)
def run_now(
    report_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Dispara la ejecución del reporte de inmediato.

    Con Celery: lo encola en el worker. En modo local: lo ejecuta en segundo plano.
    """
    report = require_report_access(db, report_id, user, need_edit=True)
    if settings.USE_CELERY:
        from app.scheduling.tasks import run_report_task

        task = run_report_task.delay(report.id, "manual")
        return {"task_id": task.id, "report_id": report.id, "status": "queued"}

    background_tasks.add_task(_run_in_process, report.id)
    return {"report_id": report.id, "status": "queued"}

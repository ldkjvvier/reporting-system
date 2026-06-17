"""Tareas Celery: ejecución de reportes disparada por Beat o manualmente."""
import logging

from app.db import session_scope
from app.reporting.service import run_report
from app.scheduling.celery_app import celery_app

logger = logging.getLogger("scheduling.tasks")


@celery_app.task(name="reportes.run_report")
def run_report_task(report_id: int, trigger: str = "scheduled") -> dict:
    """Ejecuta un reporte dentro de su propia sesión de BD."""
    with session_scope() as db:
        run = run_report(db, report_id, trigger=trigger)
        return {
            "run_id": run.id,
            "status": run.status,
            "row_count": run.row_count,
            "delivery_status": run.delivery_status,
        }

"""Alta/baja de schedules dinámicos en RedBeat al crear/editar/borrar un reporte.

Cada reporte habilitado registra una entrada RedBeat con su expresión cron; al
deshabilitarlo o borrarlo, la entrada se elimina. No requiere reiniciar Beat.
"""
import logging

from celery.schedules import crontab

from app.models import Report
from app.scheduling.celery_app import celery_app

logger = logging.getLogger("scheduling.sync")

KEY_PREFIX = "report-"


def _entry_name(report_id: int) -> str:
    return f"{KEY_PREFIX}{report_id}"


def _crontab_from_expr(expr: str) -> crontab:
    """Convierte 'm h dom mon dow' en un objeto crontab de Celery.

    Celery Beat interpreta el crontab en la zona horaria de la app
    (``settings.SCHEDULER_TIMEZONE``, hoy horario de Chile), no en UTC.
    """
    minute, hour, dom, month, dow = expr.split()
    return crontab(
        minute=minute,
        hour=hour,
        day_of_month=dom,
        month_of_year=month,
        day_of_week=dow,
    )


def upsert_schedule(report: Report) -> None:
    """Crea o actualiza la entrada de schedule del reporte."""
    from redbeat import RedBeatSchedulerEntry

    name = _entry_name(report.id)
    if not report.enabled:
        remove_schedule(report.id)
        return

    try:
        schedule = _crontab_from_expr(report.cron)
        entry = RedBeatSchedulerEntry(
            name=name,
            task="reportes.run_report",
            schedule=schedule,
            args=[report.id, "scheduled"],
            app=celery_app,
        )
        entry.save()
        logger.info("Schedule actualizado para reporte %s (cron=%s)", report.id, report.cron)
    except Exception:  # noqa: BLE001
        logger.exception("No se pudo registrar el schedule del reporte %s", report.id)


def remove_schedule(report_id: int) -> None:
    """Elimina la entrada de schedule del reporte si existe."""
    from redbeat import RedBeatSchedulerEntry

    name = _entry_name(report_id)
    prefix = celery_app.conf.get("redbeat_key_prefix", "redbeat:")
    key = f"{prefix}{name}"
    try:
        entry = RedBeatSchedulerEntry.from_key(key, app=celery_app)
        entry.delete()
        logger.info("Schedule eliminado para reporte %s", report_id)
    except KeyError:
        pass
    except Exception:  # noqa: BLE001
        logger.exception("No se pudo eliminar el schedule del reporte %s", report_id)

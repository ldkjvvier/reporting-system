"""Orquestación de la ejecución de un reporte: fetch -> build -> send -> registrar corrida."""
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.integrations.datadog.factory import get_datadog_client
from app.integrations.email.factory import get_email_sender
from app.models import Report, ReportRun
from app.reporting.builder import build_file

logger = logging.getLogger("reporting.service")


def run_report(db: Session, report_id: int, trigger: str = "manual") -> ReportRun:
    """Ejecuta un reporte de principio a fin y devuelve la corrida registrada."""
    report = db.get(Report, report_id)
    if report is None:
        raise ValueError(f"Reporte {report_id} no existe")

    run = ReportRun(report_id=report.id, status="running", trigger=trigger)
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        # 1. Consultar Datadog
        client = get_datadog_client()
        result = client.search(
            source_type=report.source_type,
            query=report.query,
            time_window=report.time_window,
        )

        # 2. Construir archivo CSV/Excel
        path, filename, row_count = build_file(
            report_name=report.name,
            output_format=report.output_format,
            result=result,
            columns=report.columns,
        )
        run.file_path = path
        run.row_count = row_count

        # 3. Enviar por correo (mock por defecto)
        sender = get_email_sender()
        subject = f"[Reporte] {report.name} — {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}"
        body = (
            f"Reporte automático '{report.name}'.\n"
            f"Fuente: Datadog Cloud SIEM ({report.source_type}).\n"
            f"Filas: {row_count}.\n"
            f"Generado: {datetime.now(timezone.utc).isoformat()}\n"
        )
        email_result = sender.send(
            recipients=[str(r) for r in (report.recipients or [])],
            subject=subject,
            body=body,
            attachment_path=path,
            attachment_name=filename,
        )
        run.delivery_status = email_result.status

        run.status = "success"
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)
        logger.info("Reporte %s ejecutado: %d filas, envío=%s", report.id, row_count, email_result.status)
        return run

    except Exception as exc:  # noqa: BLE001
        logger.exception("Fallo ejecutando reporte %s", report_id)
        run.status = "failed"
        run.error_message = str(exc)
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)
        return run

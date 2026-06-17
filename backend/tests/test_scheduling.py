"""Pruebas del cálculo de próxima ejecución (zona horaria del scheduler)."""
from app.api.reports import _next_run
from app.config import settings
from app.models import Report


def test_next_run_is_chile_timezone_aware():
    settings_tz = settings.SCHEDULER_TIMEZONE
    assert settings_tz == "America/Santiago"

    report = Report(name="x", team_id=1, cron="0 8 * * *", enabled=True)
    nr = _next_run(report)
    assert nr is not None
    # Aware (con offset) y el próximo disparo es a las 08:00 hora local de Chile.
    assert nr.utcoffset() is not None
    assert nr.hour == 8


def test_next_run_none_when_disabled():
    report = Report(name="x", team_id=1, cron="0 8 * * *", enabled=False)
    assert _next_run(report) is None

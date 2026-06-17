"""Pruebas del generador de archivos y del cliente Datadog mock."""
import os

import pandas as pd

from app.integrations.datadog.mock import MockDatadogClient
from app.reporting.builder import build_dataframe, build_file


def _strip_ts(rows):
    return [{k: v for k, v in r.items() if k != "timestamp"} for r in rows]


def test_mock_is_deterministic():
    client = MockDatadogClient()
    a = client.search("signals", "*", "last_24h")
    b = client.search("signals", "*", "last_24h")
    # El contenido (sin el instante exacto) es reproducible para la misma config.
    assert _strip_ts(a.rows) == _strip_ts(b.rows)
    assert a.total == b.total
    assert a.total > 0
    assert "severity" in a.fields


def test_mock_query_changes_data():
    client = MockDatadogClient()
    a = client.search("signals", "@severity:high", "last_24h")
    b = client.search("signals", "@severity:low", "last_24h")
    assert _strip_ts(a.rows) != _strip_ts(b.rows)


def test_build_dataframe_selects_columns():
    client = MockDatadogClient()
    result = client.search("signals", "*", "last_24h")
    df = build_dataframe(result, ["timestamp", "severity"])
    assert list(df.columns) == ["timestamp", "severity"]
    assert len(df) == result.total


def test_build_csv(tmp_path, monkeypatch):
    monkeypatch.setattr("app.reporting.builder.settings.OUTBOX_DIR", str(tmp_path))
    client = MockDatadogClient()
    result = client.search("logs", "*", "last_1h")
    path, filename, rows = build_file("Mi Reporte", "csv", result, ["timestamp", "host"])
    assert os.path.exists(path)
    assert filename.endswith(".csv")
    df = pd.read_csv(path)
    assert list(df.columns) == ["timestamp", "host"]
    assert len(df) == rows


def test_build_xlsx(tmp_path, monkeypatch):
    monkeypatch.setattr("app.reporting.builder.settings.OUTBOX_DIR", str(tmp_path))
    client = MockDatadogClient()
    result = client.search("signals", "*", "last_24h")
    path, filename, rows = build_file("Reporte SIEM", "xlsx", result, [])
    assert os.path.exists(path)
    assert filename.endswith(".xlsx")
    df = pd.read_excel(path)
    assert len(df) == rows


def test_metrics_deterministic_and_fields():
    client = MockDatadogClient()
    a = client.search("metrics", "avg:system.cpu.user{*}", "last_24h")
    b = client.search("metrics", "avg:system.cpu.user{*}", "last_24h")
    assert _strip_ts(a.rows) == _strip_ts(b.rows)
    assert a.total > 0
    assert "value" in a.fields and "metric" in a.fields
    # El parseo del query separa métrica y scope.
    assert a.rows[0]["metric"] == "system.cpu.user"
    assert a.rows[0]["scope"] == "*"


def test_metrics_query_changes_data():
    client = MockDatadogClient()
    a = client.search("metrics", "avg:system.cpu.user{*}", "last_24h")
    b = client.search("metrics", "avg:system.mem.used{*}", "last_24h")
    assert _strip_ts(a.rows) != _strip_ts(b.rows)


def test_build_csv_metrics(tmp_path, monkeypatch):
    monkeypatch.setattr("app.reporting.builder.settings.OUTBOX_DIR", str(tmp_path))
    client = MockDatadogClient()
    result = client.search("metrics", "avg:system.load.1{host:web-01}", "last_1h")
    path, filename, rows = build_file("Metricas CPU", "csv", result, [])
    assert os.path.exists(path)
    df = pd.read_csv(path)
    assert list(df.columns) == ["timestamp", "metric", "scope", "value", "unit"]
    assert len(df) == rows


def test_schema_accepts_metrics_rejects_unknown():
    import pytest
    from pydantic import ValidationError

    from app.schemas import ReportCreate

    ok = ReportCreate(name="m", team_id=1, source_type="metrics")
    assert ok.source_type == "metrics"
    with pytest.raises(ValidationError):
        ReportCreate(name="x", team_id=1, source_type="events")

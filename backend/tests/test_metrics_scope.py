"""Pruebas del desglose del 'scope' de métricas en columnas seleccionables.

Cuando una query agrupa con 'by {tagA,tagB,...}', Datadog devuelve cada par
tag:valor apelmazado en el campo 'scope'. Estas pruebas verifican que se
desglose en una columna por tag, y que esos tags queden disponibles como
campos seleccionables del reporte.
"""
from app.integrations.datadog.base import discover_fields
from app.integrations.datadog.flatten import parse_group_by, parse_scope
from app.integrations.datadog.mock import MockDatadogClient, _parse_metric_query

GROUPED_QUERY = (
    "sum:reporte_dlp_bfcl_politicas{*} by "
    "{action,usr.id,alert_name,severity,app}.as_count()"
)


def test_parse_scope_splits_pairs():
    out = parse_scope("action:block,usr.id:123,alert_name:DLP Policy")
    assert out == {"action": "block", "usr.id": "123", "alert_name": "DLP Policy"}


def test_parse_scope_handles_empty_and_star():
    assert parse_scope("*") == {}
    assert parse_scope("") == {}
    assert parse_scope(None) == {}


def test_parse_group_by_extracts_keys():
    assert parse_group_by(GROUPED_QUERY) == [
        "action", "usr.id", "alert_name", "severity", "app",
    ]
    assert parse_group_by("avg:system.cpu.user{*}") == []


def test_parse_metric_query_cleans_name_with_by_and_modifier():
    metric, scope = _parse_metric_query(GROUPED_QUERY)
    assert metric == "reporte_dlp_bfcl_politicas"
    assert scope == "*"


def test_mock_metrics_breaks_scope_into_columns():
    client = MockDatadogClient()
    result = client.search("metrics", GROUPED_QUERY, "last_24h", limit=50)
    available = discover_fields(result.rows, result.fields)
    # Cada tag del 'by' debe ofrecerse como columna seleccionable.
    for tag in ("action", "usr.id", "alert_name", "severity", "app"):
        assert tag in available, f"falta la columna '{tag}'"
    # Y cada fila debe traer esos tags como valores propios, no solo en 'scope'.
    first = result.rows[0]
    assert first["action"]
    assert first["metric"] == "reporte_dlp_bfcl_politicas"

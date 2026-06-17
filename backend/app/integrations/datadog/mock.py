"""Cliente Datadog simulado: genera datos deterministas para desarrollo sin credenciales."""
import hashlib
import random
from datetime import timedelta

from app.integrations.datadog.base import (
    DatadogClient,
    QueryResult,
    fields_for,
    window_to_range,
)

_SEVERITIES = ["info", "low", "medium", "high", "critical"]
_STATUSES_SIGNAL = ["open", "under_review", "archived"]
_STATUSES_LOG = ["ok", "warning", "error"]
_RULES = [
    "Brute force attack detected", "Impossible travel", "Suspicious AWS API call",
    "Malware signature match", "Privilege escalation attempt", "Anomalous login",
]
_TACTICS = ["Initial Access", "Execution", "Persistence", "Privilege Escalation", "Exfiltration"]
_TECHNIQUES = ["T1110", "T1078", "T1059", "T1068", "T1567"]
_HOSTS = ["web-01", "web-02", "api-03", "db-01", "worker-05", "bastion-01"]
_SERVICES = ["auth", "payments", "gateway", "ingest", "billing"]
_USERS = ["alice", "bob", "carol", "svc-deploy", "root", "admin"]
_METHODS = ["GET", "POST", "PUT", "DELETE"]


def _seed(source_type: str, query: str, time_window: str) -> int:
    raw = f"{source_type}|{query}|{time_window}".encode("utf-8")
    return int(hashlib.sha256(raw).hexdigest(), 16) % (2**32)


def _ip(rng: random.Random) -> str:
    return ".".join(str(rng.randint(1, 254)) for _ in range(4))


def _parse_metric_query(query: str) -> tuple[str, str]:
    """Extrae (metric, scope) de un query estilo 'avg:system.cpu.user{host:web-01}'."""
    q = (query or "").strip() or "system.load.1"
    scope = "*"
    if "{" in q and q.endswith("}"):
        head, scope_part = q[:-1].split("{", 1)
        scope = scope_part.strip() or "*"
        q = head
    if ":" in q:
        q = q.split(":", 1)[1]  # quita el agregador (avg:, sum:, max:, ...)
    metric = q.strip() or "system.load.1"
    return metric, scope


def _metric_unit(metric: str) -> str:
    """Unidad plausible derivada del nombre de la métrica (solo para el mock)."""
    m = metric.lower()
    if "cpu" in m or "percent" in m or "pct" in m:
        return "percent"
    if "byte" in m or "mem" in m:
        return "byte"
    if "latency" in m or "duration" in m or "time" in m:
        return "millisecond"
    return ""


class MockDatadogClient(DatadogClient):
    def search(
        self, source_type: str, query: str, time_window: str, limit: int = 1000
    ) -> QueryResult:
        rng = random.Random(_seed(source_type, query, time_window))
        start, end = window_to_range(time_window)
        # Anclamos al minuto para que llamadas seguidas con la misma config sean
        # reproducibles (la vista previa coincide con el reporte generado).
        end = end.replace(second=0, microsecond=0)
        start = start.replace(second=0, microsecond=0)
        span = (end - start).total_seconds()

        # Métricas: timeseries con puntos equiespaciados (cada punto es una fila).
        if source_type == "metrics":
            rows = self._metric_rows(rng, start, span, query, time_window, limit)
            rows.sort(key=lambda r: r["timestamp"], reverse=True)
            return QueryResult(fields=fields_for(source_type), rows=rows)

        # Cantidad de filas determinista según la ventana
        base_count = {"last_1h": 8, "last_24h": 40, "last_7d": 120, "last_30d": 300}
        count = min(limit, base_count.get(time_window, 40))

        rows = []
        for _ in range(count):
            ts = start + timedelta(seconds=rng.uniform(0, span))
            ts_iso = ts.isoformat()
            if source_type == "signals":
                rows.append({
                    "timestamp": ts_iso,
                    "title": rng.choice(_RULES),
                    "severity": rng.choice(_SEVERITIES),
                    "status": rng.choice(_STATUSES_SIGNAL),
                    "rule_name": rng.choice(_RULES),
                    "host": rng.choice(_HOSTS),
                    "service": rng.choice(_SERVICES),
                    "source_ip": _ip(rng),
                    "user": rng.choice(_USERS),
                    "technique": rng.choice(_TECHNIQUES),
                    "tactic": rng.choice(_TACTICS),
                })
            else:
                rows.append({
                    "timestamp": ts_iso,
                    "host": rng.choice(_HOSTS),
                    "service": rng.choice(_SERVICES),
                    "source": "syslog",
                    "status": rng.choice(_STATUSES_LOG),
                    "message": f"Request handled in {rng.randint(1, 900)}ms",
                    "source_ip": _ip(rng),
                    "user": rng.choice(_USERS),
                    "http_method": rng.choice(_METHODS),
                    "http_status_code": rng.choice([200, 201, 301, 400, 401, 403, 404, 500]),
                    "url": rng.choice(["/login", "/api/v1/data", "/checkout", "/health"]),
                })

        rows.sort(key=lambda r: r["timestamp"], reverse=True)
        return QueryResult(fields=fields_for(source_type), rows=rows)

    def _metric_rows(self, rng, start, span, query, time_window, limit):
        """Genera una serie temporal determinista para una métrica."""
        metric, scope = _parse_metric_query(query)
        unit = _metric_unit(metric)
        counts = {"last_1h": 12, "last_24h": 24, "last_7d": 84, "last_30d": 120}
        points = min(limit, counts.get(time_window, 24))
        base = rng.uniform(10, 90)
        rows = []
        for i in range(points):
            ts = start + timedelta(seconds=span * (i / max(points - 1, 1)))
            value = round(max(base + rng.uniform(-15, 15), 0.0), 2)
            rows.append({
                "timestamp": ts.isoformat(),
                "metric": metric,
                "scope": scope,
                "value": value,
                "unit": unit,
            })
        return rows

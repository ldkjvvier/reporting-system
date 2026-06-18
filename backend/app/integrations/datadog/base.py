"""Interfaz común para clientes de Datadog Cloud SIEM."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List

WINDOW_DELTAS = {
    "last_1h": timedelta(hours=1),
    "last_24h": timedelta(hours=24),
    "last_7d": timedelta(days=7),
    "last_30d": timedelta(days=30),
}


def window_to_range(time_window: str) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    delta = WINDOW_DELTAS.get(time_window, WINDOW_DELTAS["last_24h"])
    return now - delta, now


@dataclass
class QueryResult:
    """Resultado normalizado de una consulta a Datadog."""
    fields: List[str]      # nombres de columnas disponibles
    rows: List[dict]       # filas (cada una un dict campo->valor)

    @property
    def total(self) -> int:
        return len(self.rows)


# Campos disponibles por tipo de fuente (Cloud SIEM)
SIGNAL_FIELDS = [
    "timestamp", "title", "severity", "status", "rule_name",
    "host", "service", "source_ip", "user", "technique", "tactic",
]
LOG_FIELDS = [
    "timestamp", "host", "service", "source", "status", "message",
    "source_ip", "user", "http_method", "http_status_code", "url",
]
# Métricas (timeseries): cada fila es un punto de la serie.
METRIC_FIELDS = ["timestamp", "metric", "scope", "value", "unit"]

# Agregadores de espacio válidos para la Metrics Query API v1 de Datadog.
# La query debe tener la forma 'agregador:metrica{scope}', p. ej. 'avg:system.cpu.user{*}'.
METRIC_AGGREGATORS = {"avg", "sum", "min", "max", "count"}


def validate_metric_query(query: str) -> str:
    """Valida que la query de métricas tenga el formato 'agregador:metrica{scope}'
    que exige la API v1 «Query timeseries points» de Datadog y la devuelve normalizada.

    Lanza ``ValueError`` con un mensaje claro si es inválida, para evitar que Datadog
    responda un 400 que terminaría como un 500 opaco en la vista previa.
    """
    q = (query or "").strip()
    if not q or q == "*":
        raise ValueError(
            "La query de métrica debe tener el formato 'agregador:metrica{scope}', "
            "por ejemplo 'avg:system.cpu.user{*}'."
        )
    head = q.split("{", 1)[0]
    aggregator = head.split(":", 1)[0].strip().lower() if ":" in head else ""
    if aggregator not in METRIC_AGGREGATORS:
        raise ValueError(
            "La query de métrica debe iniciar con un agregador "
            f"({', '.join(sorted(METRIC_AGGREGATORS))}), p. ej. 'avg:system.cpu.user{{*}}'. "
            f"Recibido: '{q}'."
        )
    return q


def fields_for(source_type: str) -> List[str]:
    if source_type == "signals":
        return SIGNAL_FIELDS
    if source_type == "metrics":
        return METRIC_FIELDS
    return LOG_FIELDS


def discover_fields(rows: List[dict], curated: List[str]) -> List[str]:
    """Combina los campos curados (primero, en su orden) con los descubiertos en la
    muestra. Permite ofrecer al usuario también los campos anidados que realmente
    trae el dato, más allá de la lista fija."""
    seen = set(curated)
    extra = set()
    for row in rows:
        for k in row.keys():
            if k not in seen:
                extra.add(k)
    return list(curated) + sorted(extra)


class DatadogClient(ABC):
    """Cliente abstracto. Implementaciones: Mock y Real."""

    @abstractmethod
    def search(
        self, source_type: str, query: str, time_window: str, limit: int = 1000
    ) -> QueryResult:
        ...

    def available_fields(self, source_type: str) -> List[str]:
        return fields_for(source_type)

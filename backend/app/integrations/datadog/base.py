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


def fields_for(source_type: str) -> List[str]:
    if source_type == "signals":
        return SIGNAL_FIELDS
    if source_type == "metrics":
        return METRIC_FIELDS
    return LOG_FIELDS


class DatadogClient(ABC):
    """Cliente abstracto. Implementaciones: Mock y Real."""

    @abstractmethod
    def search(
        self, source_type: str, query: str, time_window: str, limit: int = 1000
    ) -> QueryResult:
        ...

    def available_fields(self, source_type: str) -> List[str]:
        return fields_for(source_type)

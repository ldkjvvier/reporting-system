"""Cliente Datadog real usando datadog-api-client (Logs v2, Security Monitoring Signals v2 y Metrics v1).

Se activa cuando DATADOG_MODE=real y existen DATADOG_API_KEY / DATADOG_APP_KEY.
Implementación lista para usar; no se ejercita hasta cargar credenciales reales.
"""
from datetime import datetime, timezone
from typing import List

from app.config import settings
from app.integrations.datadog.base import (
    DatadogClient,
    QueryResult,
    fields_for,
    window_to_range,
)
from app.integrations.datadog.flatten import flatten_record


def _raw_attributes(attrs) -> dict:
    """Aplana el objeto attributes completo a notación de punto (attributes.*),
    para exponer también los campos anidados que no están en la lista curada."""
    to_dict = getattr(attrs, "to_dict", None)
    if not callable(to_dict):
        return {}
    try:
        return flatten_record(to_dict(), "attributes")
    except Exception:
        return {}


class RealDatadogClient(DatadogClient):
    def _configuration(self):
        from datadog_api_client import Configuration

        configuration = Configuration()
        configuration.api_key["apiKeyAuth"] = settings.DATADOG_API_KEY
        configuration.api_key["appKeyAuth"] = settings.DATADOG_APP_KEY
        configuration.server_variables["site"] = settings.DATADOG_SITE
        return configuration

    def search(
        self, source_type: str, query: str, time_window: str, limit: int = 1000
    ) -> QueryResult:
        from datadog_api_client import ApiClient

        start, end = window_to_range(time_window)
        if source_type == "signals":
            rows = self._search_signals(query, start, end, limit)
        elif source_type == "metrics":
            rows = self._search_metrics(query, start, end, limit)
        else:
            rows = self._search_logs(query, start, end, limit)
        return QueryResult(fields=fields_for(source_type), rows=rows)

    def _search_signals(self, query, start, end, limit) -> List[dict]:
        from datadog_api_client import ApiClient
        from datadog_api_client.v2.api.security_monitoring_api import SecurityMonitoringApi
        from datadog_api_client.v2.model.security_monitoring_signal_list_request import (
            SecurityMonitoringSignalListRequest,
        )
        from datadog_api_client.v2.model.security_monitoring_signal_list_request_filter import (
            SecurityMonitoringSignalListRequestFilter,
        )
        from datadog_api_client.v2.model.security_monitoring_signal_list_request_page import (
            SecurityMonitoringSignalListRequestPage,
        )

        body = SecurityMonitoringSignalListRequest(
            filter=SecurityMonitoringSignalListRequestFilter(
                _from=start, to=end, query=query or "*"
            ),
            page=SecurityMonitoringSignalListRequestPage(limit=min(limit, 1000)),
        )
        rows = []
        with ApiClient(self._configuration()) as api_client:
            api = SecurityMonitoringApi(api_client)
            resp = api.search_security_monitoring_signals(body=body)
            for sig in resp.data or []:
                attrs = sig.attributes
                custom = getattr(attrs, "custom", {}) or {}
                row = {
                    "timestamp": str(getattr(attrs, "timestamp", "")),
                    "title": getattr(attrs, "title", ""),
                    "severity": str(custom.get("severity", "")),
                    "status": str(getattr(attrs, "status", "")),
                    "rule_name": str(custom.get("rule_name", "")),
                    "host": str(custom.get("host", "")),
                    "service": str(custom.get("service", "")),
                    "source_ip": str(custom.get("source_ip", "")),
                    "user": str(custom.get("user", "")),
                    "technique": str(custom.get("technique", "")),
                    "tactic": str(custom.get("tactic", "")),
                }
                # Campos curados primero; el resto del árbol queda disponible como attributes.*
                row.update(_raw_attributes(attrs))
                rows.append(row)
        return rows

    def _search_metrics(self, query, start, end, limit) -> List[dict]:
        """Consulta métricas (timeseries) con la Metrics API v1 y aplana cada punto a una fila."""
        from datadog_api_client import ApiClient
        from datadog_api_client.v1.api.metrics_api import MetricsApi

        rows: List[dict] = []
        with ApiClient(self._configuration()) as api_client:
            api = MetricsApi(api_client)
            resp = api.query_metrics(
                _from=int(start.timestamp()),
                to=int(end.timestamp()),
                query=query or "system.load.1{*}",
            )
            for series in getattr(resp, "series", None) or []:
                metric = str(getattr(series, "metric", "") or "")
                scope = str(getattr(series, "scope", "") or "*")
                unit_list = getattr(series, "unit", None) or []
                unit = str(getattr(unit_list[0], "name", "")) if unit_list else ""
                for point in getattr(series, "pointlist", None) or []:
                    # pointlist: [[timestamp_ms, value], ...]
                    if len(point) < 2 or point[1] is None:
                        continue
                    ts = datetime.fromtimestamp(point[0] / 1000, tz=timezone.utc)
                    rows.append({
                        "timestamp": ts.isoformat(),
                        "metric": metric,
                        "scope": scope,
                        "value": round(float(point[1]), 4),
                        "unit": unit,
                    })
                    if len(rows) >= limit:
                        return rows
        return rows

    def _search_logs(self, query, start, end, limit) -> List[dict]:
        from datadog_api_client import ApiClient
        from datadog_api_client.v2.api.logs_api import LogsApi
        from datadog_api_client.v2.model.logs_list_request import LogsListRequest
        from datadog_api_client.v2.model.logs_list_request_page import LogsListRequestPage
        from datadog_api_client.v2.model.logs_query_filter import LogsQueryFilter

        body = LogsListRequest(
            filter=LogsQueryFilter(
                _from=start.isoformat(), to=end.isoformat(), query=query or "*"
            ),
            page=LogsListRequestPage(limit=min(limit, 1000)),
        )
        rows = []
        with ApiClient(self._configuration()) as api_client:
            api = LogsApi(api_client)
            resp = api.list_logs(body=body)
            for log in resp.data or []:
                attrs = log.attributes
                a = getattr(attrs, "attributes", {}) or {}
                row = {
                    "timestamp": str(getattr(attrs, "timestamp", "")),
                    "host": str(getattr(attrs, "host", "")),
                    "service": str(getattr(attrs, "service", "")),
                    "source": str(a.get("source", "")),
                    "status": str(getattr(attrs, "status", "")),
                    "message": str(getattr(attrs, "message", "")),
                    "source_ip": str(a.get("network", {}).get("client", {}).get("ip", "")),
                    "user": str(a.get("usr", {}).get("id", "")),
                    "http_method": str(a.get("http", {}).get("method", "")),
                    "http_status_code": str(a.get("http", {}).get("status_code", "")),
                    "url": str(a.get("http", {}).get("url", "")),
                }
                # El objeto 'attributes.attributes' de Datadog trae todo el detalle anidado.
                row.update(flatten_record(a, "attributes"))
                rows.append(row)
        return rows

"""Selecciona la implementación de DatadogClient según configuración."""
from app.config import settings
from app.integrations.datadog.base import DatadogClient


def get_datadog_client() -> DatadogClient:
    use_real = (
        settings.DATADOG_MODE == "real"
        and settings.DATADOG_API_KEY
        and settings.DATADOG_APP_KEY
    )
    if use_real:
        from app.integrations.datadog.real import RealDatadogClient

        return RealDatadogClient()
    from app.integrations.datadog.mock import MockDatadogClient

    return MockDatadogClient()

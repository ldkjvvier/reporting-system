"""Configuración central leída desde variables de entorno."""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_NAME: str = "Sistema de Reportería Automatizado"
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12
    # Lista separada por comas (se parsea con la propiedad cors_origins_list).
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:8080"

    # Base de datos
    DATABASE_URL: str = "postgresql+psycopg2://reportes:reportes@db:5432/reportes"

    # Redis / Celery
    REDIS_URL: str = "redis://redis:6379/0"
    # En Docker se usa Celery (worker+beat). En local sin infraestructura se pone en
    # false: la ejecución de reportes corre en proceso y se omite el scheduling RedBeat.
    USE_CELERY: bool = True

    # Almacenamiento de archivos generados
    OUTBOX_DIR: str = "/data/outbox"

    # Zona horaria del scheduler: las expresiones cron de los reportes se interpretan
    # en esta zona (por ahora, horario local de Chile). Debe ser una zona IANA válida.
    SCHEDULER_TIMEZONE: str = "America/Santiago"

    # Integración Datadog: "mock" | "real"
    DATADOG_MODE: str = "mock"
    DATADOG_API_KEY: str = ""
    DATADOG_APP_KEY: str = ""
    DATADOG_SITE: str = "datadoghq.com"

    # Integración Email (Microsoft Graph / Azure): "mock" | "real"
    EMAIL_MODE: str = "mock"
    AZURE_TENANT_ID: str = ""
    AZURE_CLIENT_ID: str = ""
    AZURE_CLIENT_SECRET: str = ""
    MAIL_SENDER: str = ""

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

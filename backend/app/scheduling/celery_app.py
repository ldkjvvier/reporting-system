"""Aplicación Celery con RedBeat para schedules dinámicos por reporte."""
from celery import Celery

from app.config import settings

celery_app = Celery(
    "reportes",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.scheduling.tasks"],
)

celery_app.conf.update(
    # Las expresiones cron de los reportes se interpretan en esta zona (horario de Chile).
    timezone=settings.SCHEDULER_TIMEZONE,
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_max_tasks_per_child=200,
    # RedBeat: almacena las entradas de schedule en Redis
    redbeat_redis_url=settings.REDIS_URL,
    beat_scheduler="redbeat.RedBeatScheduler",
    redbeat_lock_timeout=90,
)

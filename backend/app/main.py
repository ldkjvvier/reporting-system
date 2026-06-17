"""Punto de entrada de la API FastAPI."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, auth, datadog, reports, runs
from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title=settings.APP_NAME, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(reports.router)
app.include_router(runs.router)
app.include_router(datadog.router)


@app.get("/api/health", tags=["health"])
def health():
    return {
        "status": "ok",
        "datadog_mode": settings.DATADOG_MODE,
        "email_mode": settings.EMAIL_MODE,
    }

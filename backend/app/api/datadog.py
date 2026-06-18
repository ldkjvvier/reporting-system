"""Endpoints de apoyo para la UI: campos disponibles y vista previa de datos Datadog."""
import logging

from fastapi import APIRouter, Depends, HTTPException

from app.auth.security import get_current_user
from app.integrations.datadog.base import discover_fields, fields_for
from app.integrations.datadog.factory import get_datadog_client
from app.models import User
from app.schemas import PreviewRequest, PreviewResponse

router = APIRouter(prefix="/api/datadog", tags=["datadog"])
logger = logging.getLogger("api.datadog")


@router.get("/fields")
def get_fields(source_type: str = "signals", _: User = Depends(get_current_user)):
    """Lista de campos disponibles para construir el reporte según la fuente."""
    return {"source_type": source_type, "fields": fields_for(source_type)}


@router.post("/preview", response_model=PreviewResponse)
def preview(payload: PreviewRequest, _: User = Depends(get_current_user)):
    """Devuelve una muestra de datos (mock o real) para previsualizar el reporte."""
    client = get_datadog_client()
    try:
        result = client.search(
            source_type=payload.source_type,
            query=payload.query,
            time_window=payload.time_window,
            limit=payload.limit,
        )
    except ValueError as exc:
        # Query inválida (p. ej. métrica sin agregador): error del usuario, 400.
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # noqa: BLE001 — Datadog rechazó/falló la consulta
        # Evita un 500 opaco: surfacea el motivo real al usuario en la vista previa.
        logger.exception("Fallo en la vista previa de Datadog")
        raise HTTPException(
            status_code=502, detail=f"Datadog no pudo procesar la consulta: {exc}"
        )
    rows = result.rows[: payload.limit]
    return PreviewResponse(
        fields=result.fields,
        rows=rows,
        total=result.total,
        available_fields=discover_fields(rows, result.fields),
    )

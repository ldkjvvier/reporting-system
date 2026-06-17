"""Endpoints de apoyo para la UI: campos disponibles y vista previa de datos Datadog."""
from fastapi import APIRouter, Depends

from app.auth.security import get_current_user
from app.integrations.datadog.base import fields_for
from app.integrations.datadog.factory import get_datadog_client
from app.models import User
from app.schemas import PreviewRequest, PreviewResponse

router = APIRouter(prefix="/api/datadog", tags=["datadog"])


@router.get("/fields")
def get_fields(source_type: str = "signals", _: User = Depends(get_current_user)):
    """Lista de campos disponibles para construir el reporte según la fuente."""
    return {"source_type": source_type, "fields": fields_for(source_type)}


@router.post("/preview", response_model=PreviewResponse)
def preview(payload: PreviewRequest, _: User = Depends(get_current_user)):
    """Devuelve una muestra de datos (mock o real) para previsualizar el reporte."""
    client = get_datadog_client()
    result = client.search(
        source_type=payload.source_type,
        query=payload.query,
        time_window=payload.time_window,
        limit=payload.limit,
    )
    rows = result.rows[: payload.limit]
    return PreviewResponse(fields=result.fields, rows=rows, total=result.total)

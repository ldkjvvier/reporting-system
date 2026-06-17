"""Construye archivos CSV/Excel a partir de los resultados de Datadog."""
import os
import re
from datetime import datetime, timezone
from typing import List

import pandas as pd

from app.config import settings
from app.integrations.datadog.base import QueryResult


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_") or "reporte"


def build_dataframe(result: QueryResult, columns: List[str]) -> pd.DataFrame:
    """Crea un DataFrame seleccionando solo las columnas pedidas (en orden)."""
    selected = columns or result.fields
    df = pd.DataFrame(result.rows)
    # Garantiza que existan todas las columnas seleccionadas
    for col in selected:
        if col not in df.columns:
            df[col] = None
    if not df.empty:
        df = df[selected]
    else:
        df = pd.DataFrame(columns=selected)
    return df


def build_file(
    report_name: str,
    output_format: str,
    result: QueryResult,
    columns: List[str],
) -> tuple[str, str, int]:
    """Genera el archivo en OUTBOX_DIR.

    Devuelve (ruta_absoluta, nombre_archivo, num_filas).
    """
    os.makedirs(settings.OUTBOX_DIR, exist_ok=True)
    df = build_dataframe(result, columns)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    base = f"{_safe_name(report_name)}_{ts}"

    if output_format == "xlsx":
        filename = f"{base}.xlsx"
        path = os.path.join(settings.OUTBOX_DIR, filename)
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Reporte")
    else:
        filename = f"{base}.csv"
        path = os.path.join(settings.OUTBOX_DIR, filename)
        df.to_csv(path, index=False, encoding="utf-8-sig")

    return path, filename, len(df)

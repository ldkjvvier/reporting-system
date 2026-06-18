"""Crea las tablas a partir de los modelos (idempotente).

Se ejecuta al arrancar los contenedores antes de levantar la API/worker.
Para un proyecto con migraciones formales, ver alembic/.
"""
import logging

from sqlalchemy import inspect, text

from app.db import Base, engine
from app import models  # noqa: F401  (registra los modelos en Base.metadata)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("init_db")


def _ensure_column(table: str, column: str, ddl_type: str) -> None:
    """Añade una columna a una tabla existente si falta (create_all no altera
    tablas ya creadas). Idempotente; sirve para SQLite y Postgres."""
    insp = inspect(engine)
    if table not in insp.get_table_names():
        return
    existing = {c["name"] for c in insp.get_columns(table)}
    if column in existing:
        return
    logger.info("Añadiendo columna %s.%s", table, column)
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}"))


def main() -> None:
    logger.info("Creando tablas si no existen...")
    Base.metadata.create_all(bind=engine)
    # Migraciones ligeras para bases ya existentes (sin Alembic).
    _ensure_column("reports", "column_labels", "JSON")
    logger.info("Listo.")


if __name__ == "__main__":
    main()

"""Crea las tablas a partir de los modelos (idempotente).

Se ejecuta al arrancar los contenedores antes de levantar la API/worker.
Para un proyecto con migraciones formales, ver alembic/.
"""
import logging

from app.db import Base, engine
from app import models  # noqa: F401  (registra los modelos en Base.metadata)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("init_db")


def main() -> None:
    logger.info("Creando tablas si no existen...")
    Base.metadata.create_all(bind=engine)
    logger.info("Listo.")


if __name__ == "__main__":
    main()

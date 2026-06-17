#!/usr/bin/env bash
set -e

# Espera a que la base de datos esté lista e inicializa el esquema.
echo "Inicializando base de datos..."
python -m app.init_db

echo "Arrancando API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000

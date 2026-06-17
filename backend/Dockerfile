# Python 3.13: versión estable con wheels precompilados para todas las
# dependencias (pandas, psycopg2, etc.). Con 3.14 muchos paquetes se compilan
# desde el código fuente y el build falla por headers de C ausentes.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Toolchain de compilación + headers (libc6-dev aporta assert.h y demás
# cabeceras de C) y libpq-dev para psycopg2, por si algún paquete necesita
# compilarse desde fuente.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Carpeta de salida para los archivos generados
RUN mkdir -p /data/outbox

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

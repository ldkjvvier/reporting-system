# Sistema de Reportería Automatizado (Datadog Cloud SIEM)

[![CI](https://github.com/ldkjvvier/reporting-system/actions/workflows/ci.yml/badge.svg)](https://github.com/ldkjvvier/reporting-system/actions/workflows/ci.yml)

Sistema web para **crear, gestionar y ejecutar automáticamente** reportes basados en
**Datadog**: Cloud SIEM (Logs / Security Signals) y **Métricas** (timeseries). Cada reporte:

1. Consulta Datadog según una query y ventana de tiempo.
2. Genera un archivo **CSV** o **Excel** con las columnas elegidas.
3. Lo **envía por correo** a los destinatarios (vía Microsoft Graph / Azure).
4. Se ejecuta **automáticamente** en el horario (cron) que defina el usuario.

> Las integraciones externas (**Datadog** y **Azure/Microsoft Graph**) están en modo
> **mock** por defecto: el sistema funciona de extremo a extremo sin credenciales.
> Cuando cargues las credenciales, basta cambiar `DATADOG_MODE`/`EMAIL_MODE` a `real`.

## Arquitectura

| Servicio   | Rol                                                       |
|------------|-----------------------------------------------------------|
| `frontend` | React + Vite + Mantine (Nginx). Interfaz web.             |
| `api`      | FastAPI. REST + auth (JWT).                               |
| `worker`   | Celery. Ejecuta los reportes (genera archivo + envía).    |
| `beat`     | Celery Beat + RedBeat. Dispara los reportes según su cron.|
| `db`       | PostgreSQL. Usuarios, reportes y corridas.                |
| `redis`    | Broker de Celery + almacén de schedules RedBeat.          |

```
Frontend ─▶ API ─▶ PostgreSQL
                     ▲
        Beat ─▶ Redis ─▶ Worker ─▶ DatadogClient (mock/real)
                                 └▶ EmailSender   (mock/real)
```

## Puesta en marcha (Docker)

Requisitos: Docker + Docker Compose.

```bash
cp .env.example .env          # ajusta SECRET_KEY si quieres
docker compose up --build -d  # levanta los 6 servicios
```

- **Frontend:** http://localhost:8080
- **API (docs OpenAPI):** http://localhost:8000/docs
- **Health:** http://localhost:8000/api/health

Crea una cuenta desde la pantalla de login (o `make seed` para un usuario demo:
`demo@empresa.com` / `demo1234`).

## Uso

1. Inicia sesión.
2. **Nuevo reporte** → asistente de pasos:
   - Datos (nombre/descripción).
   - Fuente Datadog (Signals/Logs/Métricas) + query + ventana + **Vista previa** + columnas.
   - Formato (CSV/Excel) + destinatarios.
   - Programación (presets diario/semanal/mensual o cron personalizado) + zona horaria.
3. En el **Dashboard** puedes editar, pausar, eliminar, ver el **historial** o
   **Ejecutar ahora**.
4. En el **Historial** se ven todas las corridas (estado, filas, envío) y se puede
   **descargar** el archivo generado. La página se autorefresca.

Para probar el disparo automático, crea un reporte con frecuencia **“Cada minuto (pruebas)”**
y observa cómo aparecen corridas `scheduled` en el historial.

## Conectar servicios reales

En `.env`:

```ini
# Datadog
DATADOG_MODE=real
DATADOG_API_KEY=...
DATADOG_APP_KEY=...
DATADOG_SITE=datadoghq.com      # o datadoghq.eu, us3.datadoghq.com, etc.

# Email vía Microsoft Graph (App registration en Azure con permiso Mail.Send)
EMAIL_MODE=real
AZURE_TENANT_ID=...
AZURE_CLIENT_ID=...
AZURE_CLIENT_SECRET=...
MAIL_SENDER=reportes@tu-dominio.com
```

Luego `docker compose up -d --build`. No se requieren cambios de código: las fábricas
(`integrations/*/factory.py`) seleccionan la implementación real automáticamente.

## Modo local rápido (sin Docker, sin Postgres/Redis)

Para pruebas locales basta con **Python 3.14** y **Node**. Se usa SQLite y la
ejecución de reportes corre en proceso (sin Celery/Redis). Un solo comando:

```powershell
./run-local.ps1
```

Abre la API en http://localhost:8000 y el frontend en http://localhost:5173.
Usuario demo: `demo@empresa.com` / `demo1234`. La configuración local vive en
`backend/.env` (`USE_CELERY=false`, `DATABASE_URL=sqlite:///./local.db`, modos mock).

> En este modo el disparo **automático por cron** no se ejecuta (eso requiere el
> stack Docker con Redis/Celery). Sí puedes crear reportes y usar **“Ejecutar ahora”**
> para generarlos y descargarlos.

## Desarrollo local (sin Docker)

Backend:
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# Requiere Postgres y Redis locales, o ajusta DATABASE_URL/REDIS_URL a localhost
python -m app.init_db
uvicorn app.main:app --reload
# En otra terminal:
celery -A app.scheduling.celery_app.celery_app worker --loglevel=info
celery -A app.scheduling.celery_app.celery_app beat --scheduler redbeat.RedBeatScheduler
```

Frontend:
```bash
cd frontend
npm install
npm run dev    # http://localhost:5173 (proxy /api -> localhost:8000)
```

## Tests

```bash
make test
# o:  cd backend && pytest -q
```

Cubren el cliente Datadog mock (determinismo) y la generación de archivos CSV/XLSX.

## Estructura

```
backend/   FastAPI, Celery, integraciones (datadog/email), reporting, scheduling
frontend/  React + Vite + Mantine (login, dashboard, wizard, historial)
docker-compose.yml   Orquesta los 6 servicios
.env.example         Variables (modos mock/real para Datadog y Azure)
```

## Notas de alcance

- Auth simple usuario/contraseña (JWT). SSO Azure/Entra queda como evolución futura.
- Esquema de BD creado al arranque con `init_db` (idempotente).
- Mock de Datadog genera datos deterministas para que la vista previa y los reportes
  sean reproducibles.
- **Fuentes soportadas:** Security Signals, Logs y Métricas (timeseries; cada punto de la
  serie es una fila CSV/Excel).

## Programación y zona horaria

- **La programación se ejecuta en horario local de Chile** (`America/Santiago`). Celery Beat
  interpreta el cron de cada reporte en esa zona (con DST), y la "próxima ejecución" mostrada
  coincide con el disparo real.
- Configurable con `SCHEDULER_TIMEZONE` (zona IANA) en `.env` / `config.py`.
- Limitación actual: la zona es **global**, no por reporte (el campo `timezone` del reporte es
  informativo). Soportar tz por reporte = trabajo futuro (`nowfun` con `ZoneInfo` en el `crontab`).
```

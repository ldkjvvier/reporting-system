# AGENTS.md — Contexto del proyecto para modelos LLM

> Documento de contexto destinado a un **agente LLM** (p. ej. Fable 5) que va a leer,
> razonar o modificar este repositorio. Es denso y factual a propósito. Para humanos
> ver `README.md` (cómo ejecutar) y `CONTEXTO.md` (propósito y alcance). Si hay conflicto,
> el código es la fuente de verdad; este archivo orienta dónde mirar.

## TL;DR

Sistema de reportería que genera reportes desde **Datadog** — Cloud SIEM (Logs / Security
Signals) y **Métricas** (timeseries) — los exporta a **CSV/Excel** y los **envía por correo** (Microsoft Graph), de
forma **programada (cron por reporte)** o manual. Web (React) + API (FastAPI) + Celery
(worker/beat) + PostgreSQL + Redis, orquestado con Docker. Las integraciones externas
(Datadog, Azure) son **mock-first** y se cambian a real por variable de entorno.

## Stack y versiones

- **Backend:** Python (3.12 en Docker, 3.14 en local), FastAPI, SQLAlchemy 2.x,
  Pydantic v2 + pydantic-settings, Celery 5 + celery-redbeat, pandas + openpyxl, PyJWT, bcrypt.
- **Frontend:** React 18 + TypeScript, Vite 6, Mantine 7, react-router-dom 6, axios.
- **Infra:** PostgreSQL 16, Redis 7, Nginx (sirve el frontend en prod), Docker Compose.

## Mapa del repositorio (rutas exactas)

```
backend/
  app/
    main.py                      # App FastAPI; monta routers; CORS; GET /api/health
    config.py                    # Settings (pydantic-settings). USE_CELERY, *_MODE, etc.
    db.py                        # engine/SessionLocal/Base; get_db(); session_scope()
    models.py                    # ORM: User, Report, ReportRun
    schemas.py                   # Pydantic I/O + validadores (cron, source_type, format, window)
    init_db.py                   # create_all idempotente (en vez de migraciones)
    auth/security.py             # hash/verify (bcrypt), JWT, get_current_user
    api/
      auth.py                    # POST /api/auth/register, /api/auth/login
      reports.py                 # CRUD /api/reports + POST /{id}/run (manual)
      runs.py                    # GET /api/reports/{id}/runs, GET /api/runs/{id}/download
      datadog.py                 # GET /api/datadog/fields, POST /api/datadog/preview
    integrations/
      datadog/{base,mock,real,factory}.py   # DatadogClient + impls + selector
      email/{base,mock,real,factory}.py     # EmailSender + impls + selector
    reporting/
      builder.py                 # QueryResult -> DataFrame -> CSV/XLSX en OUTBOX_DIR
      service.py                 # run_report(): orquesta fetch->build->send->registra run
    scheduling/
      celery_app.py              # instancia Celery (broker/back Redis; RedBeat)
      tasks.py                   # run_report_task (Celery)
      sync.py                    # alta/baja de schedule RedBeat por reporte
  tests/test_builder.py          # pytest: mock determinista + CSV/XLSX
  requirements.txt               # deps Docker (incluye psycopg2, redis, datadog-api-client)
  requirements-local.txt         # deps local (SQLite; sin redis/psycopg2/datadog-client)
  Dockerfile, entrypoint.sh
  .env                           # SOLO local; gitignored; no va a la imagen
frontend/
  src/
    main.tsx                     # bootstrap React + Mantine + Router + AuthProvider
    App.tsx                      # rutas + AppShell + Protected
    api.ts                       # axios; interceptores de token; reportsApi/datadogApi/auth
    auth.tsx                     # AuthContext (login/register/logout, token en localStorage)
    types.ts                     # tipos TS espejo de los schemas
    pages/{Login,Dashboard,ReportForm,RunHistory}.tsx
  vite.config.ts                 # proxy /api -> http://localhost:8000 en dev
  Dockerfile (multi-stage Nginx), nginx.conf
docker-compose.yml               # 6 servicios: db, redis, api, worker, beat, frontend
run-local.ps1                    # arranque local sin Docker
.env.example                     # plantilla de variables (modos mock por defecto)
README.md / CONTEXTO.md / AGENTS.md
```

## Cómo ejecutar

**Local (sin Docker, SQLite, ejecución en proceso):**
```powershell
./run-local.ps1     # API :8000, Frontend :5173, usuario demo@empresa.com / demo1234
```
Config local en `backend/.env`: `USE_CELERY=false`, `DATABASE_URL=sqlite:///./local.db`,
`OUTBOX_DIR=./outbox`, modos mock. El backend lee `.env` desde su CWD (`backend/`).

**Docker (stack completo con scheduling real):**
```bash
cp .env.example .env && docker compose up --build -d
# frontend :8080, api :8000
```

**Tests:** `cd backend && pytest -q` (o `make test` en Docker).

## Flujos clave

**Ejecución de un reporte** (`app/reporting/service.py::run_report`):
1. `get_datadog_client().search(source_type, query, time_window)` → `QueryResult`.
2. `builder.build_file(...)` → escribe CSV/XLSX en `OUTBOX_DIR`, devuelve (path, filename, rows).
3. `get_email_sender().send(...)` → envía adjunto (mock por defecto).
4. Crea/actualiza fila en `report_runs` (status, row_count, file_path, delivery_status, error).

**"Ejecutar ahora"** (`api/reports.py::run_now`): si `USE_CELERY` → `run_report_task.delay()`;
si no → `BackgroundTasks` ejecuta `run_report` en proceso con `session_scope()`.

**Programado:** al crear/editar/borrar un reporte, `scheduling/sync.py` registra/elimina una
entrada RedBeat (cron→`celery.schedules.crontab`). Beat la dispara → `run_report_task`.
**Solo activo con `USE_CELERY=true` (Docker).** En local el cron NO se dispara.

## Selección mock/real (patrón factory)

- `integrations/datadog/factory.py::get_datadog_client()` → `RealDatadogClient` si
  `DATADOG_MODE=real` y hay `DATADOG_API_KEY`+`DATADOG_APP_KEY`; si no, `MockDatadogClient`.
  - `source_type` ∈ {`signals`, `logs`, `metrics`}. Campos por fuente en `datadog/base.py`
    (`SIGNAL_FIELDS`/`LOG_FIELDS`/`METRIC_FIELDS`); `metrics` aplana cada punto de la serie
    a una fila (`timestamp, metric, scope, value, unit`). Real: Metrics API v1 `query_metrics`.
- `integrations/email/factory.py::get_email_sender()` → `GraphEmailSender` si `EMAIL_MODE=real`
  y hay credenciales Azure (`AZURE_*`, `MAIL_SENDER`); si no, `MockEmailSender`.
- Las impls `real.py` **importan sus SDKs de forma perezosa** (dentro de métodos), así que
  no se requieren `datadog-api-client`/`httpx` en local. **No muevas esos imports al top-level.**

## Variables de entorno relevantes (`config.py`)

`SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `CORS_ORIGINS` (string CSV; usar
`settings.cors_origins_list`), `DATABASE_URL`, `REDIS_URL`, `USE_CELERY`, `OUTBOX_DIR`,
`DATADOG_MODE`/`DATADOG_API_KEY`/`DATADOG_APP_KEY`/`DATADOG_SITE`,
`EMAIL_MODE`/`AZURE_TENANT_ID`/`AZURE_CLIENT_ID`/`AZURE_CLIENT_SECRET`/`MAIL_SENDER`.

## Convenciones

- Comentarios y textos de UI en **español**; identificadores de código en **inglés**.
- Endpoints bajo prefijo `/api`. Auth por `Bearer` JWT (`get_current_user`).
- Cada `Report` pertenece a un `User` (`owner_id`); los endpoints filtran por propietario.
- Tipos TS en `frontend/src/types.ts` deben mantenerse en sincronía con `schemas.py`.
- `columns`/`recipients` se guardan como JSON; cron en formato `m h dom mon dow`.

## Gotchas / decisiones no obvias (no romper)

- **`CORS_ORIGINS` es `str`**, no `list`: pydantic-settings v2 intenta parsear listas como
  JSON desde `.env` y falla. Se divide en la propiedad `cors_origins_list`.
- **SQLite** requiere `connect_args={"check_same_thread": False}` (ya en `db.py`) por las
  BackgroundTasks en otro hilo.
- **Mock Datadog determinista:** la ventana se ancla al minuto y los datos derivan de un seed
  `sha256(source_type|query|time_window)`. Misma config ⇒ mismos datos (la preview coincide
  con el reporte). El test compara filas ignorando el timestamp exacto.
- **Esquema BD:** se crea con `app/init_db.py` (`Base.metadata.create_all`). **No hay Alembic.**
  Si cambias `models.py`, en local borra `backend/local.db` o ajusta el esquema a mano.
- **bcrypt** trunca la contraseña a 72 bytes (límite del algoritmo) — ver `auth/security.py`.
- **Celery import perezoso:** `run_report_task` se importa dentro de la rama `USE_CELERY` en
  `reports.py` para que el modo local no necesite broker. `sync.py` importa `redbeat` dentro de
  funciones. Mantener esa pereza.
- **Build frontend:** `tsc && vite build`. `vite.config.ts` queda fuera de `include` de
  `tsconfig.json` a propósito (usa `process` en contexto Node).

## Estado actual

- Funcional de extremo a extremo con **mocks**; verificado: register/login/preview/create/run
  (success, ~40 filas)/download (XLSX). Corriendo en modo local (SQLite).
- **Pendiente:** credenciales reales de Datadog y de Azure (correo) para activar `*_MODE=real`.
- En local el **cron automático no dispara** (necesita Docker con worker+beat).
- **Timezone del scheduler:** los cron se interpretan en `settings.SCHEDULER_TIMEZONE`
  (por defecto `America/Santiago`, horario de Chile). `celery_app.timezone` usa ese valor y
  `reports._next_run` calcula con `ZoneInfo(SCHEDULER_TIMEZONE)`. La zona es **global**, no por
  reporte (el campo `Report.timezone` es informativo); tz por-reporte = trabajo futuro.

## Si vas a extender el proyecto

- **Nuevo endpoint:** crea router en `app/api/`, móntalo en `main.py`, agrega schema en
  `schemas.py` y, si toca, tipo en `frontend/src/types.ts` + método en `frontend/src/api.ts`.
- **Nueva fuente/canal:** añade una impl a la interfaz correspondiente en `integrations/` y
  amplía el factory; mantén imports de SDK perezosos.
- **Disparo automático en local:** opción sugerida no implementada = APScheduler en proceso
  cuando `USE_CELERY=false` (ver §"Evoluciones" en `CONTEXTO.md`).
- Cambios de modelo ⇒ recordar que no hay migraciones (Alembic es trabajo futuro).

# Contexto del Proyecto — Sistema de Reportería Automatizado

> Documento de contexto y alcance. Resume **qué es** el proyecto, **para qué sirve**,
> **cómo está construido**, **qué entra y qué no entra** en el alcance, y el **estado actual**.
> Para instrucciones de ejecución, ver [`README.md`](./README.md).

---

## 1. Propósito

Plataforma web para **crear, gestionar y ejecutar automáticamente** reportes basados en
**Datadog Cloud SIEM**. La feature central es que cada reporte se **ejecuta solo** en el
horario que define su creador, sin intervención manual.

Flujo de un reporte:

```
Usuario (web) → define query + columnas + formato + destinatarios + horario
                                   │
        (en el horario programado) ▼
   Consulta Datadog SIEM → genera CSV/Excel → envía por correo a los destinatarios
```

## 2. Problema que resuelve

Hoy los reportes de métricas/seguridad de Datadog se arman de forma manual y recurrente:
alguien entra, filtra, exporta y envía por correo. Esto es repetitivo, propenso a errores
y no escala. El sistema **automatiza ese ciclo completo**: se configura una vez vía web y
el reporte se genera y distribuye solo en la frecuencia deseada.

## 3. Usuarios y caso de uso principal

- **Usuario objetivo:** equipos de seguridad/SOC y operaciones que consumen datos de
  Datadog Cloud SIEM.
- **Caso de uso típico:** "Cada lunes a las 08:00, enviar a `soc@empresa.com` un Excel con
  todas las *security signals* de severidad alta/crítica de los últimos 7 días."

## 4. Funcionalidades

| # | Funcionalidad | Estado |
|---|---------------|--------|
| 1 | Autenticación usuario/contraseña (JWT) | ✅ |
| 2 | CRUD de reportes vía interfaz web (asistente por pasos) | ✅ |
| 3 | Fuentes Datadog: **Logs**, **Security Signals** (Cloud SIEM) y **Métricas** (timeseries) | ✅ |
| 4 | Vista previa de datos antes de guardar el reporte | ✅ |
| 5 | Selección de columnas a incluir | ✅ |
| 6 | Salida en **CSV** o **Excel (.xlsx)** | ✅ |
| 7 | Envío por correo a destinatarios (Microsoft Graph / Azure) | ✅ (mock) |
| 8 | **Ejecución automática programada** (cron por reporte) | ✅ (requiere stack Docker) |
| 9 | Ejecución manual ("Ejecutar ahora") | ✅ |
| 10 | Historial de ejecuciones con estado, nº de filas y descarga del archivo | ✅ |
| 11 | Activar/pausar/editar/eliminar reportes | ✅ |

## 5. Arquitectura

Seis servicios orquestados con Docker Compose:

| Servicio   | Tecnología                | Rol |
|------------|---------------------------|-----|
| `frontend` | React + Vite + Mantine    | Interfaz web (servida con Nginx) |
| `api`      | FastAPI                   | REST + autenticación (JWT) |
| `worker`   | Celery                    | Ejecuta los reportes (genera archivo + envía) |
| `beat`     | Celery Beat + RedBeat     | Dispara los reportes según su cron (schedules dinámicos) |
| `db`       | PostgreSQL                | Usuarios, reportes y ejecuciones |
| `redis`    | Redis                     | Broker de Celery + almacén de schedules RedBeat |

```
Frontend ─▶ API ─▶ PostgreSQL
                     ▲
        Beat ─▶ Redis ─▶ Worker ─▶ DatadogClient (mock/real)
                                 └▶ EmailSender   (mock/real)
```

**Por qué Celery + RedBeat:** el horario lo define cada usuario, por lo que se necesitan
schedules **dinámicos** (alta/baja en caliente al crear/editar/borrar un reporte) sin
reiniciar el planificador.

### Modelo de datos
- `users` — credenciales y estado.
- `reports` — definición del reporte: fuente, query, ventana, columnas, formato,
  destinatarios, cron, timezone, activo.
- `report_runs` — historial de ejecuciones: estado, filas, archivo generado, estado de envío, error.

## 6. Integraciones externas (patrón *mock-first*)

Cada integración tiene una **interfaz** y dos implementaciones (mock/real) seleccionadas por
variable de entorno mediante un *factory*. **No requiere cambios de código** para pasar a real.

| Integración | Mock (por defecto) | Real |
|-------------|--------------------|------|
| **Datadog** | Datos de ejemplo deterministas | API de Datadog (Logs v2 + Security Signals v2 + Metrics v1) |
| **Email (Azure)** | Simula el envío y registra en log | Microsoft Graph `sendMail` con adjunto |

Activación del modo real en `.env`: `DATADOG_MODE=real` / `EMAIL_MODE=real` + credenciales.

## 7. Alcance

### ✅ Dentro del alcance (entregado)
- Sistema completo web + API + ejecución programada + generación de archivos + envío.
- Fuentes de datos **Datadog**: Cloud SIEM (Logs + Security Signals) y **Métricas** (timeseries).
- Servicios externos limitados a **Datadog** y **Microsoft Azure (correo)**, ambos mockeables.
- Despliegue con **Docker Compose**.
- Modo de ejecución **local sin Docker** (SQLite + ejecución en proceso) para pruebas.

### ❌ Fuera del alcance (por ahora)
- Otras fuentes de datos distintas a Datadog SIEM.
- SSO / Azure AD (Entra) — se usa login propio usuario/contraseña.
- Multi-tenancy avanzado, roles y permisos granulares.
- Programación con zona horaria **por reporte**: hoy el scheduling es global en horario de
  Chile (`America/Santiago`, configurable con `SCHEDULER_TIMEZONE`); el campo `timezone` del
  reporte es informativo. Ver "Programación y zona horaria" en README.
- Paginación masiva / exportación de volúmenes muy grandes.
- Dashboards o visualización de datos dentro de la app (solo genera archivos).
- Otros canales de entrega (Slack, S3, etc.) — solo correo.

## 8. Decisiones clave

| Decisión | Elección | Motivo |
|----------|----------|--------|
| Backend | Python + FastAPI | SDK de Datadog, pandas/openpyxl, ecosistema de datos |
| Fuente Datadog | Logs / Security Signals (Cloud SIEM) + Métricas (timeseries) | Confirmado con el usuario |
| Autenticación | Usuario/contraseña + JWT | Simple; SSO queda como evolución futura |
| Scheduler | Celery Beat + RedBeat | Schedules dinámicos por reporte sin reiniciar |
| Servicios externos | Mock-first vía factory | Avanzar sin credenciales; switch por env var |
| Esquema BD | `init_db` (create_all) idempotente | Primer arranque sin pasos extra (Alembic = futuro) |

## 9. Estado actual

- **Funcional de extremo a extremo** con datos mock.
- Verificado: registro, login, vista previa, creación de reporte, ejecución
  exitosa (40 filas), generación y descarga de Excel.
- **Pendiente de credenciales del usuario** para activar Datadog real y correo real (Azure).
- Corriendo en **modo local** (SQLite, sin Docker) para pruebas inmediatas; el stack Docker
  completo añade ejecución automática por cron (worker + beat).

## 10. Evoluciones posibles (no comprometidas)

- Scheduler en proceso (APScheduler) para disparo automático también en modo local.
- SSO con Azure AD / Entra.
- Migraciones formales con Alembic.
- Más canales de entrega y más fuentes de datos.
- Roles/permisos y reportes compartidos entre usuarios.

## 11. Estructura del repositorio

```
backend/    FastAPI, Celery, integraciones (datadog/email), reporting, scheduling, tests
frontend/   React + Vite + Mantine (login, dashboard, asistente, historial)
docker-compose.yml   Orquesta los 6 servicios
run-local.ps1        Arranque local sin Docker (SQLite + en proceso)
.env.example         Variables (modos mock/real de Datadog y Azure)
README.md            Instrucciones de ejecución
CONTEXTO.md          Este documento
```

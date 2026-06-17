# Arranca el sistema en modo LOCAL (sin Docker): SQLite + ejecucion en proceso.
# Abre dos ventanas: API (uvicorn :8000) y Frontend (Vite :5173).
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"

# --- Backend: crear venv e instalar si falta ---
$venvPy = Join-Path $backend ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
  Write-Host "Creando entorno virtual e instalando dependencias..." -ForegroundColor Cyan
  py -3.14 -m venv (Join-Path $backend ".venv")
  & $venvPy -m pip install --upgrade pip -q
  & $venvPy -m pip install -r (Join-Path $backend "requirements-local.txt")
}

# Inicializa la base de datos (idempotente)
Push-Location $backend
& $venvPy -m app.init_db
Pop-Location

# --- Frontend: instalar deps si faltan ---
if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
  Write-Host "Instalando dependencias del frontend..." -ForegroundColor Cyan
  Push-Location $frontend; npm install; Pop-Location
}

Write-Host "`nIniciando servicios..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit","-Command","cd '$backend'; .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
Start-Process powershell -ArgumentList "-NoExit","-Command","cd '$frontend'; npm run dev"

Write-Host "`n  Frontend:  http://localhost:5173" -ForegroundColor Yellow
Write-Host "  API/docs:  http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host "  Usuario demo: demo@empresa.com / demo1234`n" -ForegroundColor Yellow

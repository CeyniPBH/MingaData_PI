# =============================================================================
# Script de inicio rápido - Tablero MingaData (Streamlit)
# Ejecutar: .\run_tablero.ps1
# =============================================================================

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  TABLERO MINGADATA - Streamlit" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Verificar que estamos en la carpeta correcta
if (!(Test-Path "src/dashboard/app.py")) {
    Write-Host "ERROR: No se encontró src/dashboard/app.py" -ForegroundColor Red
    Write-Host "Asegúrate de ejecutar este script desde la raíz del proyecto MingaData_PI" -ForegroundColor Red
    exit 1
}

# 2. Activar entorno virtual si existe
if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "Activando entorno virtual..." -ForegroundColor Yellow
    .\.venv\Scripts\Activate.ps1
} else {
    Write-Host "ADVERTENCIA: No se encontró .venv. Se usará Python global." -ForegroundColor Yellow
}

# 3. Verificar que streamlit esté instalado
$streamlitCheck = python -m streamlit --version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Instalando dependencias (streamlit, folium, plotly, streamlit-folium, ortools)..." -ForegroundColor Yellow
    python -m pip install streamlit streamlit-folium plotly folium ortools -q
    Write-Host "Dependencias instaladas." -ForegroundColor Green
}

# 4. Configurar Streamlit para no pedir email
if (!(Test-Path ".streamlit\config.toml")) {
    New-Item -ItemType Directory -Path ".streamlit" -Force | Out-Null
}
@"
[browser]
gatherUsageStats = false

[server]
headless = true
"@ | Set-Content ".streamlit/config.toml"

# 5. Ejecutar el tablero
Write-Host ""
Write-Host "Iniciando tablero en http://localhost:8501 ..." -ForegroundColor Green
Write-Host "Presiona Ctrl+C para detener el servidor." -ForegroundColor Gray
Write-Host ""

python -m streamlit run src/dashboard/app.py --server.port 8501
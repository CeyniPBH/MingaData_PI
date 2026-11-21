# Evidencia de despliegue en la nube — MingaData_PI

Fecha de verificación: 2026-11-21 (UTC).

Este documento registra la evidencia del despliegue de la API, el modelo versionado en S3, el motor SQL DuckDB y el tablero. Complementa la matriz de rúbrica (`docs/evaluacion/matriz_rubrica_evidencias.md`), en especial el criterio SI7006-6.

## 1. API REST en Render

- URL pública: <https://mingadata-api.onrender.com>
- Servicio: `mingadata-api`
- Build Command: `pip install -r requirements-api.txt`
- Start Command: `uvicorn src.api.main:app --host 0.0.0.0 --port $PORT`
- Python: `3.12.7` (`PYTHON_VERSION`)
- Commit verificado con `GET /version`: `d8d180e` (antes del ajuste de DuckDB; se actualiza tras el siguiente redeploy).
- Modelo verificado: `20261121_032739`, commit de entrenamiento `c2d8d2807546`.

### Endpoints

| Endpoint | Evidencia |
|---|---|
| `GET /health` | `{"status":"ok","modelo_cargado":true,"error":null}` |
| `GET /version` | `{"commit":"d8d180e...","rama":"main","servicio":"mingadata-api","modelo_version":"20261121_032739","modelo_cargado":true}` |
| `GET /modelo/info` | Metadata completa del modelo descargada desde S3 (`n_features=14`, `n_filas_entrenamiento=50453`). |
| `POST /predict` | `{"producto":"Caña de azúcar","cod_dane":"76113","horizonte":1,"anio_objetivo":2024,"prediccion_t":1426611.3487248344,"unidad":"toneladas","modelo_version":"20261121_032739","commit":"c2d8d2807546","fuente":"s3"}` |
| `GET /metricas` | `fuente: duckdb` (tras configurar `MINGA_DUCKDB_S3_URL`) o `fuente: csv` como respaldo. |

> En `/predict`, `commit` es el commit con el que se entrenó el modelo. En `/version`, `commit` es el commit del código que Render está ejecutando.

## 2. Modelo y motor SQL en S3

Bucket: `mingadata-pi-2026`, región `us-east-1`.

| Objeto | Clave S3 |
|---|---|
| Modelo versionado | `/20261121_034051/modelo_lgbm_20261121_032739.joblib` |
| Metadata del modelo | `/20261121_034051/modelo_metadata.json` |
| Índice de versiones | `/indice_versiones.json` |
| DuckDB estable | `/duckdb/mingadata.duckdb` |
| DuckDB versionado | `/duckdb/20261121_161640/mingadata.duckdb` |
| Metadata de DuckDB | `/duckdb/duckdb_metadata.json` |

La API descarga el DuckDB desde `MINGA_DUCKDB_S3_URL` a un archivo temporal al arrancar y consulta las tablas `metricas_modelo`, `metrica_negocio`, `excedentes`, `diagnostico` y `predicciones`.

Verificación local de la base:

```text
tablas: diagnostico, excedentes, metrica_negocio, metricas_modelo, predicciones
metricas_modelo: 115 filas
metrica_negocio: 13 filas
excedentes: 31.230 filas
```

## 3. Tablero en Streamlit Cloud

- Main file: `src/dashboard/app.py`
- Secrets requeridos: `MINGA_API_URL = "https://mingadata-api.onrender.com"`
- No requiere credenciales AWS: lee los Parquet/CSV versionados del repositorio y consume la API para estado, métricas y predicción en vivo.
- Pantalla 0 (Resumen): muestra el estado de la API, la fuente de métricas (`duckdb` o `csv`) y un formulario para probar `POST /predict`.
- URL pública del tablero: **pendiente de publicar** (se actualiza cuando Streamlit Cloud termine el despliegue).

## 4. Comandos de verificación

```powershell
$api = "https://mingadata-api.onrender.com"

Invoke-RestMethod "$api/version" | Format-List
Invoke-RestMethod "$api/health" | Format-List
Invoke-RestMethod "$api/metricas" |
  Select-Object fuente, aviso, @{n='cantidad';e={$_.metricas.Count}} |
  Format-List

$body = @{
    producto = "Caña de azúcar"
    cod_dane = "76113"
    horizonte = 1
    anio_objetivo = 2024
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "$api/predict" `
  -ContentType 'application/json; charset=utf-8' `
  -Body ([Text.Encoding]::UTF8.GetBytes($body)) | Format-List
```

Resultado esperado en `/predict`: `prediccion_t ≈ 1.426.611,35`, `unidad = toneladas`, `modelo_version = 20261121_032739`.

## 5. Limitaciones y respaldos

- Si el modelo no se puede descargar de S3, `/health` devuelve `modelo_cargado: false` y `/predict` responde `503`.
- Si DuckDB no se puede descargar, `/metricas` cae al CSV `data/results/ML_Ce/metricas_comparacion.csv` y devuelve `fuente: csv`.
- Render Free puede tardar ~50 s en responder tras un periodo de inactividad; usar timeouts de 60-120 s en la verificación.

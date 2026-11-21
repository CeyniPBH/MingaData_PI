# MingaData_PI

Proyecto para planear una central de acopio agrícola en el Valle del Cauca. El flujo previsto es: pronóstico de oferta → zonas de acopio → optimización y tablero → informe.

## Autores

- **Carlos Guillermo Zúñiga Méndez** — Diagramas, informes y documentación
- **Ceyni Paola Beltrán Hoyos** — Datos, baselines, modelo LightGBM y escenarios de oferta
- **Samuel Gutiérrez Jaramillo** — Optimización (OR-Tools), tablero Streamlit y excedentes
- **Alejandro Rendón Correa** — Zonas de acopio, escenarios de optimización y tablero

## Ejecutar el proyecto (Windows)

Necesitas Python 3.10+ y Git. Desde PowerShell:

```powershell
git clone https://github.com/CeyniPBH/MingaData_PI.git
cd MingaData_PI
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python src\ML_C\ejecutar_todo.py
```

La primera ejecución descarga los datos SIPSA desde el [Release `datos-v1`](https://github.com/CeyniPBH/MingaData_PI/releases/tag/datos-v1) si no están en `data/raw/SIPSA/`. Se requiere internet; el ZIP se verifica y se descomprime automáticamente. **No subas `data/raw/SIPSA/` ni el ZIP al repositorio.**

Para correr las pruebas:

```powershell
python -m pytest tests\ML_C -q
```

## Archivos para continuar el trabajo

- `data/clean/`: tablas compartidas, coordenadas y matriz de tiempos.
- `data/clean/` y `data/results/` también se publican como Parquet derivados (regenerables con `python src/pipeline/exportar_parquet.py`); el catálogo está en `data/metadata/catalogo.yaml` (37 tablas). Las lecturas prefieren Parquet con fallback a CSV.
- `data/results/ML_Ce/oferta_escenarios.csv`: oferta por producto, municipio y año (2024–2028), en escenarios bajo, base y alto.
- `data/results/ML_Ce/oferta_departamento.csv`: totales departamentales.
- `data/results/ML_Ce/oferta_escenarios_detalle.csv`: oferta más modelo y horizonte.
- `data/results/opt/`: Pareto, estabilidad por escenario y comparación libre vs zonas para el informe (ver `data/results/opt/LEEME.md`).
- `docs/ML_C/`: metodología, diccionario de datos, fuentes, formulación, EDA, tuning, diagnóstico, métrica de negocio y caso aplicado.
- `docs/arquitectura/`: arquitectura de referencia, diagrama del pipeline, almacenamiento por zonas, justificación del procesamiento y rendimiento.
- `docs/dashboard/`: narrativa visual, auditoría de mensajes y mejoras de usabilidad.
- `docs/evaluacion/matriz_rubrica_evidencias.md`: matriz de criterios de rúbrica y evidencias.

Al leer CSV, conserva `cod_dane` como texto para no perder ceros iniciales:

```python
import pandas as pd

oferta = pd.read_csv(
    "data/results/ML_Ce/oferta_escenarios.csv",
    dtype={"cod_dane": str},
)
```

## Estado y pendientes

Los módulos de pronóstico, zonas de acopio, excedentes, escenarios, optimización, tablero, arquitectura, documentación y pruebas están implementados. Queda como pendiente el informe final (sustentación), que está fuera del alcance de este entregable por instrucción.

- La matriz de tiempos actual es aproximada (línea recta × 1,4 / 45 km/h); OSM/OSRM no está incorporado.
- La población municipal DANE está procesada en `data/clean/poblacion_municipal.csv`.
- Los parámetros del pronóstico están en `config/ML_C/parametros.yaml`. Más detalles de columnas y resultados: `docs/ML_C/diccionario_datos.md`.

## Pipeline y orquestación

El pipeline completo se ejecuta con:

```powershell
# Ejecuta validación, pronóstico (ML), diagnóstico, métrica de negocio,
# exportación a Parquet + catálogo y pruebas (pytest). Omite tuning y optimización.
python src\pipeline\run_all.py --rapido

# Fuerza también tuning y optimización arendonc2
python src\pipeline\run_all.py --con-tuning --con-arendonc2

# Ejecutar solo el módulo ML (orden original)
python src\ML_C\ejecutar_todo.py
```

`run_all.py` acepta `--skip <etapa>`, `--rapido`, `--con-tuning`, `--con-arendonc2`, `--continuar` y `--dry-run`; deja log en `data/logs/pipeline_YYYYMMDD_HHMMSS.log`.


## Ejecutar el tablero interactivo (Streamlit)

El tablero tiene seis opciones: `0. Resumen` (pantalla de aterrizaje, por defecto), `1. Oferta`, `2. Zonas`, `2b. Zonas de acopio`, `3. Ubicación` y `4. Tablero central`.

```powershell
.\.venv\Scripts\Activate.ps1
streamlit run src/dashboard/app.py
```

Luego abre http://localhost:8501 en tu navegador.

## Despliegue en la nube (opcional — Opción B)

Se puede alcanzar el nivel "Excelente" de SI7006-6 desplegando la API y el tablero en la nube. Esto es opcional; todo funciona igualmente en local.

### API REST en Render

**Build Command:** `pip install -r requirements-api.txt`

**Start Command:** `uvicorn src.api.main:app --host 0.0.0.0 --port $PORT`

**Variables de entorno:**
- `MINGA_DATA_BUCKET` = `mingadata-pi-2026`
- `MINGA_DATA_REGION` = `us-east-1`
- `AWS_ACCESS_KEY_ID` = tu clave AWS
- `AWS_SECRET_ACCESS_KEY` = tu clave secreta AWS
- `MINGA_MODELO_S3_URL` = `s3://mingadata-pi-2026//20261121_034051/modelo_lgbm_20261121_032739.joblib`
- `PYTHON_VERSION` = `3.12.7` (evita problemas de wheels con la versión por defecto de Render)

Endpoints: `GET /health`, `GET /version`, `GET /modelo/info`, `POST /predict`, `GET /metricas`, `GET /docs`.

`GET /version` devuelve el commit que Render está ejecutando (`RENDER_GIT_COMMIT`) y la versión del modelo; úsalo para confirmar que el despliegue sí tomó el último push.

### Tablero en Streamlit Cloud

**Main file:** `src/dashboard/app.py`

**Secrets** (en Settings → Secrets de Streamlit Cloud):
```toml
MINGA_API_URL = "https://TU-API.onrender.com"
MINGA_DATA_BUCKET = "mingadata-pi-2026"
MINGA_DATA_REGION = "us-east-1"
AWS_ACCESS_KEY_ID = "TU_ACCESS_KEY_ID"
AWS_SECRET_ACCESS_KEY = "TU_SECRET_ACCESS_KEY"
```

### Pantallas del tablero

0. **Resumen**: landing con KPIs globales (productos, municipios, horizonte, años de historial, exposición con y sin modelo en t·min y COP), callout de alcance, tarjetas de navegación con drill-down y descarga del resumen en CSV. Es la pantalla que se abre por defecto.
1. **Oferta**: selecciona producto y municipio para ver la serie histórica (2000-2023) y el pronóstico con intervalo bajo/base/alto (2024-2028). Drill-down producto → municipios.
2. **Zonas**: mapa con los 42 municipios coloreados por oferta pronosticada, por producto y año.
2b. **Zonas de acopio**: polígonos de zona, centros de referencia, volúmenes nacional/exportación y advertencia de cobertura parcial. Drill-down zona → municipios y descargas filtradas.
3. **Ubicación**: mapa con la central y acopios satélite, frontera de Pareto (costo de recolección vs distribución) y tabla de estabilidad por escenario. Optimización bajo demanda al pulsar "Calcular optimización".
4. **Tablero central**: vista de cobertura con datos históricos (promedio 2021-2023). Responde cuánta área y producción alcanza cada sede; no reemplaza la pantalla 3, que minimiza el costo logístico (t·min) con el pronóstico 2024-2028. El indicador "recuperable" es una referencia del análisis original y no se recalcula desde el CSV.

Cada pantalla tiene título declarativo, subtítulo, unidades explícitas (t, t·min, COP, %) y callouts informativos. Las cadenas requeridas por `test_tarea3.py` (`Pantalla 1 - Oferta`, `Pantalla 2 - Zonas`, `Pantalla 3 - Ubicacion`) se conservan intactas.

La vista 0 se abre por defecto para presentar primero el resumen ejecutivo. Las pantallas 1, 2, 2b, 3 y 4 conservan el flujo de pronóstico, zonas, costo logístico y cobertura.


## Módulo de optimización (OR-Tools)

El esqueleto del modelo de localización de instalaciones está en `src/optimizacion/modelo_esqueleto.py`. Ejecuta con:

```powershell
python src/optimizacion/modelo_esqueleto.py
```

La formulación matemática está documentada en `docs/formulacion_optimizacion.md`.

### Resultados de optimización para el informe

El modelo real se ejecuta con:

```powershell
# Genera Pareto, estabilidad 2024/2028 y comparación libre vs zonas
python src/optimizacion/generar_resultados.py

# Opcional: los 5 años de escenarios.csv (135 escenarios)
python src/optimizacion/generar_resultados.py --anios 2024 2025 2026 2027 2028
```

Los CSV quedan en `data/results/opt/`:

- `frontera_pareto_base.csv` y `barrido_lambda_base.csv`: central, satélites y costos por lambda.
- `estabilidad_escenarios.csv`: 27 escenarios por año (2024 y 2028 por defecto), con central, satélites y costos.
- `comparacion_libre_vs_zonas.csv` y `comparacion_libre_vs_zonas_resumen.csv`: mismo escenario con y sin las zonas de Alejandro.
- `metadata.json`: parámetros, solver, commit y huellas SHA256.

Definiciones: `costo_total = λ·A + (1−λ)·B` es el objetivo del solver;
`costo_total_suma = A1 + A2 + B` es la suma física de los tres tramos. El detalle
de columnas está en `data/results/opt/LEEME.md`.

### Sensibilidad por valor (SIPSA)

La ubicación también se probó ponderando el excedente por valor (toneladas × precio SIPSA):

```powershell
python src/optimizacion/corrida_valor.py
```

Genera `comparacion_toneladas_vs_valor.csv` y su resumen. En el escenario base la
central no cambia (Bugalagrande), pero en 21 de 54 escenarios de 2024/2028 sí
cambia. El detalle metodológico y los resultados están en
`data/results/opt/LEEME_valor.md`.

## Pruebas automatizadas

```powershell
# Verificar Tarea 1 (optimización)
python src/optimizacion/test_tarea1.py

# Verificar los CSV de optimización para el informe
python src/optimizacion/test_resultados_opt.py

# Verificar Tarea 3 (tablero)
python src/dashboard/test_tarea3.py

# Verificar el tablero central (sincronización con el CSV)
python src/dashboard/test_tablero_central.py
```

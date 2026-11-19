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
- `data/results/ML_Ce/oferta_escenarios.csv`: oferta por producto, municipio y año (2024–2028), en escenarios bajo, base y alto.
- `data/results/ML_Ce/oferta_departamento.csv`: totales departamentales.
- `data/results/ML_Ce/oferta_escenarios_detalle.csv`: oferta más modelo y horizonte.
- `data/results/opt/`: Pareto, estabilidad por escenario y comparación libre vs zonas para el informe (ver `data/results/opt/LEEME.md`).
- `docs/ML_C/`: metodología, diccionario de datos, fuentes y limitaciones.

Al leer CSV, conserva `cod_dane` como texto para no perder ceros iniciales:

```python
import pandas as pd

oferta = pd.read_csv(
    "data/results/ML_Ce/oferta_escenarios.csv",
    dtype={"cod_dane": str},
)
```

## Estado y pendientes

Los módulos de pronóstico, zonas de acopio, excedentes, escenarios, optimización y tablero están implementados. Quedan como pendientes el informe final y el despliegue en la nube.

- La matriz de tiempos actual es aproximada.
- La población municipal DANE está procesada en `data/clean/poblacion_municipal.csv`.

Los parámetros del pronóstico están en `config/ML_C/parametros.yaml`. Más detalles de columnas y resultados: `docs/ML_C/diccionario_datos.md`.

## Ejecutar el tablero interactivo (Streamlit)

El tablero tiene cinco opciones: Oferta, Zonas, Zonas de acopio (2b), Ubicación y Tablero central.

```powershell
.\.venv\Scripts\Activate.ps1
streamlit run src/dashboard/app.py
```

Luego abre http://localhost:8501 en tu navegador.

### Pantallas del tablero

1. **Oferta**: selecciona producto y municipio para ver la serie histórica (2000-2023) y el pronóstico con intervalo bajo/base/alto (2024-2028).
2. **Zonas**: mapa con los 42 municipios coloreados por oferta pronosticada, por producto y año.
2b. **Zonas de acopio**: polígonos de zona, centros de referencia, volúmenes nacional/exportación y advertencia de cobertura parcial.
3. **Ubicación**: mapa con la central y acopios satélite, frontera de Pareto (costo de recolección vs distribución) y tabla de estabilidad por escenario.
4. **Tablero central**: vista de cobertura con datos históricos (promedio 2021-2023). Responde cuánta área y producción alcanza cada sede; no reemplaza la pantalla 3, que minimiza el costo logístico (t·min) con el pronóstico 2024-2028. El indicador "recuperable" es una referencia del análisis original y no se recalcula desde el CSV.

La vista 4 se abre por defecto para presentar primero la cobertura. Las pantallas 1, 2, 2b y 3 conservan el flujo de pronóstico, zonas y costo logístico.

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

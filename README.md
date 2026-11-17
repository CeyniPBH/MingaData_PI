# MingaData_PI

Proyecto para planear una central de acopio agrícola en el Valle del Cauca. El flujo previsto es: pronóstico de oferta → zonas de acopio → optimización y tablero → informe.

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

El módulo de pronóstico está implementado en `src/ML_C/`. El siguiente trabajo previsto es desarrollar zonas de acopio, optimización, tablero e informe usando las tablas compartidas.

- La matriz de tiempos actual es aproximada.
- La tabla de población municipal DANE está pendiente; el pipeline puede terminar sin ella.

Los parámetros del pronóstico están en `config/ML_C/parametros.yaml`. Más detalles de columnas y resultados: `docs/ML_C/diccionario_datos.md`.

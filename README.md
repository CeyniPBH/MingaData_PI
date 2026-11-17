# MingaData_PI.

## 1. Qué produce esta parte y para quién

| Entrega | Archivo | Para |
|---|---|---|
| Tabla limpia y lista de productos | `data/clean/produccion_valle_clean.csv`, `lista_productos.csv` | Todos |
| Coordenadas y matriz de tiempos | `data/clean/municipios_coordenadas.csv`, `destinos_coordenadas.csv`, `matriz_tiempos.csv` | Samuel, Alejandro |
| Producción promedio 2019-2023 | `data/clean/produccion_promedio_municipio.csv` | Alejandro (zonas) |
| Valor por producto (SIPSA) | `data/clean/valor_producto.csv` *(pendiente)* | Alejandro |
| Población y consumo per cápita | `poblacion_municipal.csv`, `consumo_percapita.csv` *(pendientes)* | Alejandro (excedentes) |
| ONI | `data/clean/oni.csv` *(pendiente, opcional)* | Ceyni |
| Escenarios de oferta 2024-2028 | `data/results/oferta_escenarios.csv` (+ `_detalle`, `oferta_departamento`) | Samuel, Alejandro |
| Diagnóstico, decisiones y resultados del modelado | `data/results/diagnostico_calidad.csv`, `decisiones_armonizacion.csv`, `metricas_*.csv`, `docs/*.md` | Carlos |

El diccionario de columnas de cada archivo está en `docs/diccionario_datos.md`.

---

## 2. Instalación (una sola vez)

Requisitos: Python 3.10 o superior y Git.

**Windows (PowerShell)**
```powershell
cd ruta\a\MingaData_PI
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Mac / Linux**
```bash
cd ruta/a/MingaData_PI
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Para esta parte basta con `pandas`, `numpy`, `pyarrow`, `scikit-learn`, `statsmodels` y `lightgbm`; todas están en el `requirements.txt` del repo. `osmnx` solo se usa si calculas la matriz de tiempos con OSM (sección 5).

Si no activa el entorno en PowerShell, ejecuta una vez `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

---

## 3. Dónde va cada cosa

```
MingaData_PI/
├── data/raw/        datos originales, NO se editan (los FRONTERA pesados están en .gitignore)
├── data/clean/      tablas limpias que consumen los demás
├── data/results/    resultados del modelado y escenarios
├── docs/            diccionario, resumen del pronóstico, lectura del diagnóstico
└── src/             scripts 00 a 06 + common.py
```

Todos los scripts se corren **desde la raíz del repo** (`python src/01_limpieza.py`) y encuentran las rutas solos.

---

## 4. Paso a paso: correr lo que ya está hecho

Orden obligatorio, porque cada script lee lo que escribe el anterior.

| Paso | Comando | Qué hace | Archivos que crea |
|---|---|---|---|
| 1 | `python src/01_limpieza.py` | Lee el CSV de permanentes, quita duplicados exactos, unifica familias, suma Hass a aguacate y limón/mandarina/naranja a cítricos, define los 22 detallados | `produccion_valle_clean.csv/.parquet`, `lista_productos.csv`, `decisiones_armonizacion.csv` |
| 2 | `python src/02_diagnostico.py` | % de valores repetidos, saltos atípicos y nivel de confianza por producto | `diagnostico_series.csv`, `diagnostico_calidad.csv` |
| 3 | `python src/03_geo_tiempos.py` | Coordenadas de los 42 municipios y 5 destinos, matriz de tiempos aproximada y producción promedio | `municipios_coordenadas.csv`, `destinos_coordenadas.csv`, `matriz_tiempos.csv`, `produccion_promedio_municipio.csv` |
| 4 | `python src/04_baselines.py` | Ingenuo, deriva, ETS amortiguado y promedio 5 años con walk-forward (orígenes 2018-2022, horizontes 1-5) | `predicciones_baselines.csv`, `metricas_baselines.csv` |
| 5 | `python src/05_lgbm.py` | LightGBM global sobre los 22 detallados con el mismo walk-forward; compara contra los baselines | `predicciones_lgbm.csv`, `metricas_comparacion.csv`, `importancia_variables.csv` |
| 6 | `python src/06_escenarios.py` | Escenarios bajo/base/alto 2024-2028, cobertura de intervalos y suma municipal = departamental | `oferta_escenarios.csv`, `oferta_escenarios_detalle.csv`, `oferta_departamento.csv`, `cobertura_intervalos.csv`, `coherencia_jerarquica.csv` |
| 7 | `python src/00_validar_entregas.py` | Revisa formato, conteos y consistencia de todo lo anterior | Imprime OK / FALLA / PENDIENTE |

Resultados de la última corrida: 57 → 44 productos (22 detallados, 22 simplificados, 13 excluidos); 724 series activas; LightGBM empata técnicamente con el ingenuo; cobertura de intervalos 75,9 % frente al 80 % nominal. Los detalles están en `docs/resumen_pronostico.md`.

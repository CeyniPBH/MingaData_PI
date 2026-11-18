# Integración — módulos de Alejandro (arendonc2)

Entrega de las tareas **#2 (zonas)**, **#3 (excedentes)**, **#4 (escenarios)** y la
**integración con Samuel** (adaptador + pantalla del tablero), sobre el trabajo ya
hecho por Ceyni (pronóstico) y Samuel (OR-Tools + tablero).

## Instalación

Requiere Python 3.10+. Desde la raíz del repo:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

`requirements.txt` ya incluye geopandas, libpysal, scikit-learn, ortools y las
dependencias del tablero. Se añadió `openpyxl` (lectura del Excel de población DANE).

## Ejecución reproducible (un comando)

```bash
python src/arendonc2/ejecutar_todo.py
```

Esto, en orden:
1. Descarga polígonos municipales GADM (`data/raw/geo/`, ~1 MB) si faltan.
2. Descarga y procesa la población municipal DANE → `data/clean/poblacion_municipal.csv`.
3. Tarea #2 → `data/results/zonas.csv` + geometrías, vecindad y métricas.
4. Tarea #3 → `data/results/excedentes.csv` + agregados, cobertura, pendientes y auditoría.
5. Tarea #4 → `data/results/escenarios.csv`.
6. Demostración del adaptador para Samuel.

Tarda unos segundos (la primera vez, más por las descargas). Requiere internet sólo
la primera vez (GADM y DANE).

### Paso a paso (opcional)

```bash
python src/arendonc2/descargar_geometrias.py
python src/arendonc2/poblacion.py
python src/arendonc2/zonas_acopio.py
python src/arendonc2/excedentes.py
python src/arendonc2/escenarios.py
python src/arendonc2/adaptador.py --id 2024_Obase_Cbase_M80_20 --anio 2024
```

## Pruebas

```bash
python -m pytest tests/arendonc2 -q
```

Verifica: 42 municipios asignados una vez, zonas conexas, sin duplicados de claves,
cuotas de consumo que no duplican categorías, consumos desconocidos marcados,
excedentes no negativos, totales municipales = zonales, 27 combinaciones por año,
conservación nacional+exportación, el adaptador selecciona el año exacto y la
cobertura parcial aparece en los archivos.

El resto del proyecto sigue funcionando:
```bash
python -m pytest tests/ML_C -q          # Ceyni
python src/optimizacion/test_tarea1.py  # Samuel (optimización)
python src/dashboard/test_tarea3.py     # Samuel (tablero)
```

## Tablero

```bash
streamlit run src/dashboard/app.py
```

Se añadió la pantalla **"2b. Zonas de acopio"**: polígonos de zona + centros de
referencia, selección de año y escenario, volúmenes nacional/exportación por zona,
botón de descarga y **advertencia visible cuando la cobertura es parcial**. Reutiliza
los cargadores de `utils.py` y las convenciones de mapas de `app.py`.

## Adaptador para Samuel

```python
from arendonc2.adaptador import preparar_para_solver, listar_escenarios

listar_escenarios(2024)                       # ids disponibles
pkg = preparar_para_solver("2024_Obase_Cbase_M80_20", 2024)

pkg.excedente_municipio   # cod_dane, municipio, zona, excedente_t (42 filas)
pkg.volumen_por_zona      # zona, volumen_nacional, volumen_exportacion, excedente_t
pkg.pct_nacional, pkg.pct_exportacion
pkg.zonas                 # cod_dane, municipio, zona, es_centro_zona
pkg.cobertura_oferta_pct, pkg.cobertura_parcial, pkg.alcance
pkg.advertencias
```

El adaptador valida claves, unidades, duplicados y coherencia municipal↔zonal, y
**selecciona exactamente el año solicitado** (rechaza un año que no coincida con el
`id_escenario`). Entrega datos; no corre el solver.

## Archivos de resultados

Entregables de contrato (en `data/results/`):
- `zonas.csv` — cod_dane, municipio, zona, es_centro_zona.
- `excedentes.csv` — excedente municipal por producto/año/combinación.
- `escenarios.csv` — 27 escenarios/año con volúmenes por zona.

Intermedios y auditoría (en `data/results/arendonc2/`): geometrías de zona,
vecindad, métricas de k, cobertura, pendientes, cuotas FAOSTAT, auditoría de recortes.

## Documentación

- `docs/arendonc2/estado_entrega.md` — estado de #2, #3, #4 frente a sus criterios.
- `docs/arendonc2/zonas_metodologia.md` — método, espacio proyectado y selección de k.
- `docs/arendonc2/supuestos_excedentes.md` — supuestos, FAOSTAT auditado, población, cobertura.
- `docs/arendonc2/escenarios_definicion.md` — definición de los 27 escenarios.
- `docs/arendonc2/geometrias_fuente_y_desviacion.md` — GADM vs MGN DANE (desviación declarada).
- `docs/arendonc2/reproducibilidad_evidencia.md` — pruebas A/B/C de reproducibilidad.
- `docs/arendonc2/decisiones_pendientes_samuel.md` — observaciones al modelo de Samuel.
- `notebooks/arendonc2/zonas_excedentes_escenarios.ipynb` — notebook reproducible con mapa.

### Artefactos de auditoría (en `data/results/arendonc2/`)

- `auditoria_mapeo_faostat.csv` — tabla producto↔FAOSTAT con unidad, tipo, factor y estado.
- `emparejamiento_gadm_dane.csv` — emparejamiento completo GADM↔DANE con alias.
- `faostat_mapeo_cuotas.csv`, `excedentes_cobertura.csv`, `excedentes_pendientes.csv`.

Scripts de auditoría: `src/arendonc2/auditar_mapeo.py`, `src/arendonc2/auditar_geometrias.py`.

## Configuración

Todo supuesto configurable está en:
- `config/arendonc2/parametros.yaml` — k, factores de consumo, umbrales, año base.
- `config/arendonc2/mapeo_faostat.yaml` — correspondencia producto ↔ FAOSTAT.

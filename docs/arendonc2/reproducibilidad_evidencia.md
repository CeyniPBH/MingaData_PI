# Evidencia de reproducibilidad (Auditoría 4)

Autor: Alejandro Rendón Correa (arendonc2). Se reportan **sólo** las comprobaciones
realmente ejecutadas, distinguiendo tres niveles.

Se compararon cuatro salidas por md5: `data/results/zonas.csv`,
`data/results/excedentes.csv`, `data/results/escenarios.csv`,
`data/clean/poblacion_municipal.csv`.

## Nivel A — Regenerar resultados desde insumos ya descargados

- **Entorno:** venv ya instalado; insumos crudos presentes
  (`data/raw/geo/gadm41_COL_2.json.zip` 1 133 733 B,
  `data/raw/poblacion/DCD-area-proypoblacion-Mun-2020-2035-ActPostCOVID-19.xlsx`
  1 878 067 B).
- **Comando:** `python src/arendonc2/ejecutar_todo.py`.
- **Resultado:** ejecución en ~3 s; las cuatro salidas quedaron **byte-idénticas**
  a las versionadas. El pipeline es determinista (Ward, reparto y agregaciones no
  usan aleatoriedad).

## Nivel B — Ejecutar desde una instalación nueva

- **Entorno:** venv **nuevo** creado desde cero
  (`python -m venv .venv_fresh`), dependencias instaladas con
  `pip install -r requirements.txt`. Versiones resultantes: geopandas 1.2.0,
  libpysal 4.15.1, scikit-learn 1.9.1, ortools, openpyxl (todas satisfacen los
  mínimos de `requirements.txt`).
- **Comando:** `python src/arendonc2/ejecutar_todo.py`.
- **Resultado:** pipeline OK en ~10 s; las cuatro salidas **byte-idénticas**.
  Pruebas en el venv nuevo: `pytest tests/arendonc2 tests/ML_C` → **33 pasan**.
- El venv de prueba se eliminó tras la comprobación.

## Nivel C — Descargar nuevamente las fuentes externas

- **Entorno:** se **borraron** los crudos (`data/raw/geo/*.zip`,
  `data/raw/poblacion/*.xlsx`).
- **Comandos:** `python src/arendonc2/descargar_geometrias.py`,
  `python src/arendonc2/poblacion.py`, `python src/arendonc2/ejecutar_todo.py`.
- **Resultado:** GADM se re-descargó a 1 133 733 B y el Excel DANE a 1 878 067 B
  (mismos tamaños), y las cuatro salidas quedaron **byte-idénticas**. Las dos
  fuentes externas tienen URL estable y descarga reproducible:
  - GADM 4.1: `https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_COL_2.json.zip`
  - DANE proyecciones: `https://www.dane.gov.co/files/censo2018/proyecciones-de-poblacion/Municipal/DCD-area-proypoblacion-Mun-2020-2035-ActPostCOVID-19.xlsx`

## Qué permanece disponible y qué se regenera

| Elemento | ¿Versionado? | Cómo se obtiene |
|----------|--------------|-----------------|
| `data/raw/geo/*.zip` (GADM) | No (ignorado) | `descargar_geometrias.py` (internet) |
| `data/raw/poblacion/*.xlsx` (DANE) | No (ignorado) | `poblacion.py` (internet) |
| `data/clean/poblacion_municipal.csv` | Sí | `poblacion.py` (procesa el Excel) |
| `data/results/zonas.csv`, `excedentes.csv`, `escenarios.csv` | Sí | `ejecutar_todo.py` |
| Intermedios `data/results/arendonc2/*` | Sí | `ejecutar_todo.py` |

**Única dependencia de red:** la primera descarga de GADM y del Excel DANE. Una vez
en `data/raw/`, el resto es offline y determinista. Los insumos de Ceyni
(`oferta_escenarios*.csv`, coordenadas, matriz de tiempos) y la lista de productos
ya están versionados en el repo y no se re-descargan.

## Alcance de las comprobaciones

- No se probó en otro sistema operativo ni con otras versiones de Python; sólo el
  entorno local (macOS, Python 3.12) en los tres niveles anteriores.
- La igualdad byte a byte depende de versiones de librerías dentro de los rangos de
  `requirements.txt`; cambios mayores de geopandas/sklearn podrían alterar decimales
  sin cambiar las conclusiones.

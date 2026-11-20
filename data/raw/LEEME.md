# data/raw — fuentes originales (no editar)

Esta carpeta contiene las fuentes originales del proyecto. **No se modifica a mano**: cualquier transformación va en `src/ML_C/` o `src/arendonc2/` y produce salidas en `data/clean/` o `data/results/`.

## Contenido

| Ruta | Fuente | Uso |
|---|---|---|
| `Consolidado_agrícola_por_municipios_de_los_cultivos_permanentes_del_Valle_del_Cauca_20260925.csv` | Gobernación del Valle del Cauca | Producción municipal de cultivos permanentes (2000-2023) |
| `Consolidado_agrícola_por_municipios_de_los_cultivos_transitorios_del_Valle_del_Cauca_20261113.csv` | Gobernación del Valle del Cauca | Cultivos transitorios; extensión y validación |
| `DIVIPOLA-_Códigos_municipios_20261114.csv` | DANE | Códigos DANE y coordenadas |
| `FAOSTAT_data_en_11-17-2026.csv` | FAO | Consumo per cápita |
| `ONI_NOAA_CPC_1998_2026.csv` | NOAA CPC | Índice ONI (El Niño/La Niña) |
| `Monthly Oceanic Nino Index (ONI) - Long.csv` | NOAA | Serie alterna de ONI |
| `doi_10.57924_GH6KPE-PANEL_AGRICULTURA_Y_TIERRA(2021)-endnote_EVA.csv` | DNP/CEDE | Referencia bibliográfica EVA |
| `MingaData_raw_SIPSA.zip` | Release `datos-v1` | ZIP con SIPSA precios e ICA FRONTERA |
| `SIPSA/` | DANE / ICA | Precios mayoristas y archivos `FRONTERA_*.csv` |
| `geo/gadm41_COL_2.json.zip` | GADM | Polígonos municipales para zonas de acopio |
| `poblacion/` | DANE | Proyecciones municipales (puede no estar; ver nota) |

## Reglas

1. **No editar, renombrar ni borrar** archivos de `data/raw/`.
2. Los ZIP y las carpetas pesadas (`SIPSA/`, `geo/`, `poblacion/`) están en `.gitignore`; no se suben al repositorio.
3. Para regenerar las tablas limpias: `python src/pipeline/run_all.py` o `python src/ML_C/ejecutar_todo.py`.
4. Para validar las fuentes antes de procesar: `python src/ML_C/00b_validar_ingesta.py`.
5. Si falta SIPSA/ICA, el pipeline descarga el ZIP del Release `datos-v1` con `python src/ML_C/00_descargar_datos.py`.
6. Si falta el archivo de población, se conserva `data/clean/poblacion_municipal.csv` ya generado por `src/arendonc2/poblacion.py`.

## Verificación

```powershell
python src/ML_C/00b_validar_ingesta.py
```

El resultado queda en `data/logs/ingesta_YYYYMMDD.log` y en `data/logs/ingesta_ultima.json`. La última corrida reportó **9 fuentes OK, 0 fallas**.

## Licencias

- Gobernación del Valle / datos.gov.co: datos abiertos, CC BY 4.0 (verificar ficha).
- DANE: datos abiertos; citar “Fuente: DANE”.
- ICA: datos abiertos; citar “Fuente: ICA, FRONTERA”.
- FAO: CC BY 4.0; citar “FAO, FAOSTAT”.
- NOAA: dominio público; citar “NOAA CPC, ONI”.
- OpenStreetMap: ODbL si se usa la fuente OSM.
- GADM: uso no comercial; revisar términos antes de redistribuir.

La caracterización completa está en `docs/ML_C/fuentes_caracterizacion.md`.

# Almacenamiento por zonas y catálogo de datos

## 1. Organización por zonas

MingaData_PI usa un data lake ligero de tres zonas sobre el sistema de archivos local. La separación evita que un cambio de modelo altere las fuentes y permite reconstruir cualquier tabla derivada.

| Zona | Ruta | Contenido | Regla de escritura | Formato |
|---|---|---|---|---|
| `raw` | `data/raw/` | Fuentes originales: consolidados de Gobernación, SIPSA, ICA FRONTERA, DIVIPOLA, FAOSTAT, NOAA, EVA | **Inmutable.** No se edita ni se sobrescribe. | CSV, XLSX, ZIP |
| `trusted` | `data/clean/` | Tablas tipadas, armonizadas y validadas: producción, productos, coordenadas, tiempos, precios, valor, población, consumo, comercio | Se regenera con scripts; el CSV es la fuente versionada. | CSV + Parquet |
| `refined` | `data/results/` | Pronósticos, escenarios, diagnóstico, métrica de negocio, zonas, excedentes y optimización | Se regenera con el pipeline; Parquet es derivado. | CSV + Parquet |

Los artefactos Parquet son **derivados regenerables**. Nunca reemplazan al CSV: si se borra un Parquet, los lectores usan el CSV y `exportar_parquet.py` lo reconstruye.

## 2. Formatos y convenciones

| Convención | Regla |
|---|---|
| `cod_dane` | Texto de 5 dígitos en todos los formatos. Se preserva con `dtype={"cod_dane": str}`; nunca se convierte a entero. |
| Codificación CSV | `utf-8-sig` (compatible con Excel y con acentos). |
| Separador decimal | Punto; los CSV de Gobernación traen separador de miles con coma y se normalizan en `01_limpieza.py`. |
| Nombres de archivo | `snake_case`, sin espacios; los resultados conservan el nombre del script que los genera. |
| Fechas | `anio` entero; no se usan fechas completas para el panel anual. |
| Nulos | Se documentan en el catálogo; no se imputan silenciosamente. |
| Compresión Parquet | `snappy`. |
| Particionamiento | `anio=YYYY` solo en las tablas que se consultan por año y tienen volumen suficiente: producción (24 particiones, 2000-2023) y excedentes (5 particiones, 2024-2028). |

### ¿Por qué Parquet?

- Conserva tipos (por ejemplo, `cod_dane` como texto y `anio` como entero).
- Reduce el tamaño: 4,2 MB de CSV limpios → 0,9 MB de Parquet; 8,8 MB de CSV de resultados → 1,0 MB de Parquet.
- Permite leer solo columnas y filtrar por partición.
- Es interoperable con pandas, pyarrow, DuckDB y cualquier motor que se añada en el futuro.

### ¿Por qué no particionar todo?

Particionar tablas pequeñas (por ejemplo, 42 municipios o 5 destinos) crea muchos archivos y añade latencia sin beneficio. Solo se particiona cuando el volumen o el patrón de consulta lo justifican. En tablas pequeñas, CSV y Parquet tienen tiempos similares; el beneficio es la estabilidad de tipos.

## 3. Catálogo

El catálogo es `data/metadata/catalogo.yaml`. Se genera con:

```powershell
python src/pipeline/exportar_parquet.py
```

Cada entrada registra: `dataset`, `zona`, `ruta`, `formato`, `particion`, `filas`, `columnas`, `dtypes`, `fuente` y `fecha_generacion`. La versión actual tiene **37 tablas** y **1,73 MB** de Parquet.

| Dataset | Ruta | Zona | Partición | Filas |
|---|---|---|---:|---:|
| `produccion_valle_clean` | `data/clean/produccion` | trusted | anio | 15.019 |
| `lista_productos` | `data/clean/lista_productos.parquet` | trusted | ninguna | 57 |
| `municipios_coordenadas` | `data/clean/municipios_coordenadas.parquet` | trusted | ninguna | 42 |
| `destinos_coordenadas` | `data/clean/destinos_coordenadas.parquet` | trusted | ninguna | 5 |
| `matriz_tiempos` | `data/clean/matriz_tiempos.parquet` | trusted | ninguna | 1.974 |
| `precio_producto_anual` | `data/clean/precio_producto_anual.parquet` | trusted | ninguna | 222 |
| `valor_producto` | `data/clean/valor_producto.parquet` | trusted | ninguna | 15.019 |
| `poblacion_municipal` | `data/clean/poblacion_municipal.parquet` | trusted | ninguna | 210 |
| `consumo_percapita` | `data/clean/consumo_percapita.parquet` | trusted | ninguna | 273 |
| `comercio_ica_frontera` | `data/clean/comercio_ica_frontera.parquet` | trusted | ninguna | 15.526 |
| `produccion_promedio_municipio` | `data/clean/produccion_promedio_municipio.parquet` | trusted | ninguna | 745 |
| `precios_sipsa_anual` | `data/clean/precios_sipsa_anual.parquet` | trusted | ninguna | 3.010 |
| `oferta_escenarios` | `data/results/ML_Ce/oferta_escenarios.parquet` | refined | ninguna | 3.620 |
| `oferta_departamento` | `data/results/ML_Ce/oferta_departamento.parquet` | refined | ninguna | 220 |
| `predicciones_comparacion` | `data/results/ML_Ce/predicciones_comparacion.parquet` | refined | ninguna | 8.323 |
| `metricas_comparacion` | `data/results/ML_Ce/metricas_comparacion.parquet` | refined | ninguna | 115 |
| `importancia_variables` | `data/results/ML_Ce/importancia_variables.parquet` | refined | ninguna | 14 |
| `cobertura_intervalos` | `data/results/ML_Ce/cobertura_intervalos.parquet` | refined | ninguna | 16 |
| `coherencia_jerarquica` | `data/results/ML_Ce/coherencia_jerarquica.parquet` | refined | ninguna | 220 |
| `tuning_resultados` | `data/results/ML_Ce/tuning_resultados.parquet` | refined | ninguna | 14 |
| `tuning_holdout_resumen` | `data/results/ML_Ce/tuning_holdout_resumen.parquet` | refined | ninguna | 2 |
| `diagnostico_horizonte` | `data/results/ML_Ce/diagnostico_horizonte.parquet` | refined | ninguna | 5 |
| `diagnostico_producto` | `data/results/ML_Ce/diagnostico_producto.parquet` | refined | ninguna | 22 |
| `diagnostico_municipio` | `data/results/ML_Ce/diagnostico_municipio.parquet` | refined | ninguna | 3 |
| `diagnostico_confianza` | `data/results/ML_Ce/diagnostico_confianza.parquet` | refined | ninguna | 3 |
| `residuales_resumen` | `data/results/ML_Ce/residuales_resumen.parquet` | refined | ninguna | 1 |
| `curva_aprendizaje` | `data/results/ML_Ce/curva_aprendizaje.parquet` | refined | ninguna | 6 |
| `metrica_negocio_resumen` | `data/results/ML_Ce/metrica_negocio_resumen.parquet` | refined | ninguna | 13 |
| `metrica_negocio_producto` | `data/results/ML_Ce/metrica_negocio_producto.parquet` | refined | ninguna | 22 |
| `metrica_negocio_horizonte` | `data/results/ML_Ce/metrica_negocio_horizonte.parquet` | refined | ninguna | 5 |
| `excedentes` | `data/results/excedentes` | refined | anio | 31.230 |
| `escenarios` | `data/results/escenarios.parquet` | refined | ninguna | 675 |
| `zonas` | `data/results/zonas.parquet` | refined | ninguna | 42 |
| `frontera_pareto_base` | `data/results/opt/frontera_pareto_base.parquet` | refined | ninguna | 2 |
| `estabilidad_escenarios` | `data/results/opt/estabilidad_escenarios.parquet` | refined | ninguna | 54 |
| `comparacion_libre_vs_zonas` | `data/results/opt/comparacion_libre_vs_zonas.parquet` | refined | ninguna | 2 |
| `comparacion_toneladas_vs_valor` | `data/results/opt/comparacion_toneladas_vs_valor.parquet` | refined | ninguna | 54 |

## 4. Linaje de las tablas principales

| Tabla refinada | Depende de | Script |
|---|---|---|
| `oferta_escenarios` | `produccion_valle_clean`, `lista_productos`, `oni`, `predicciones_*` | `07_escenarios.py` |
| `predicciones_comparacion` | `produccion_valle_clean`, `oni`, calibración walk-forward | `06_lgbm.py` |
| `valor_producto` | producción + precios SIPSA | `04_fuentes_externas.py` |
| `excedentes` | producción, población, consumo FAOSTAT, precios | `src/arendonc2/excedentes.py` |
| `escenarios` | excedentes y oferta | `src/arendonc2/escenarios.py` |
| `zonas` | producción, geometrías GADM y población | `src/arendonc2/zonas_acopio.py` |
| `frontera_pareto_base` / `estabilidad_escenarios` | `escenarios`, `excedentes`, `matriz_tiempos` | `src/optimizacion/generar_resultados.py` |
| `metrica_negocio_*` | `predicciones_comparacion`, `matriz_tiempos`, red logística | `10_metrica_negocio.py` |

## 5. Lectura recomendada

```python
import pandas as pd

# Parquet particionado: pandas infiere anio como categoría; se convierte a entero.
produccion = pd.read_parquet("data/clean/produccion")
produccion["anio"] = produccion["anio"].astype(int)
produccion["cod_dane"] = produccion["cod_dane"].astype(str).str.zfill(5)

# Tabla plana: Parquet primero y CSV como respaldo.
try:
    oferta = pd.read_parquet("data/results/ML_Ce/oferta_escenarios.parquet")
except FileNotFoundError:
    oferta = pd.read_csv(
        "data/results/ML_Ce/oferta_escenarios.csv",
        dtype={"cod_dane": str},
        encoding="utf-8-sig",
    )
```

## 6. Reglas de retención y limpieza

- `data/raw/` se conserva completo; los ZIP y carpetas pesadas están en `.gitignore`.
- Los CSV de `data/clean/` y `data/results/` se versionan; los Parquet son derivados y se pueden regenerar.
- No se borran datos para “limpiar” el repositorio. Cualquier exclusión se documenta en `lista_productos.csv` o en `decisiones_armonizacion.csv`.
- Los logs de `data/logs/` son evidencia de ejecución; se pueden conservar o rotar manualmente.

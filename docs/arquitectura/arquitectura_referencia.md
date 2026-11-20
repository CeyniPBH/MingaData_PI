# Arquitectura de referencia y flujo de datos

## 1. Propósito y alcance

Este documento describe la arquitectura que efectivamente ejecuta MingaData_PI para pasar de las fuentes crudas a un tablero de decisión. La arquitectura es un **data lake ligero por zonas** (`raw` → `trusted` → `refined`) sobre el sistema de archivos local, con procesamiento **batch en un solo nodo** y consumo mediante Streamlit.

El alcance excluye deliberadamente el despliegue en nube, las APIs, los contenedores y los servicios administrados. La solución se ejecuta en el equipo del equipo de trabajo con Python 3.10+ y las dependencias de `requirements.txt`. Esa decisión se justifica en [`justificacion_procesamiento.md`](justificacion_procesamiento.md) y en [`rendimiento.md`](rendimiento.md).

## 2. Decisión de arquitectura

| Alternativa | ¿Se adoptó? | Motivo |
|---|---|---|
| Data lake por zonas `raw`/`trusted`/`refined` en disco local | **Sí** | Volumen pequeño, trazabilidad completa, cero costo de infraestructura y reproducibilidad con un comando. |
| Arquitectura Lambda (batch + velocidad) | No | No hay fuentes en streaming ni requisitos de latencia subminuto. Añadiría componentes sin uso real. |
| Arquitectura Kappa (solo streaming) | No | Los datos son anuales/mensuales y se procesan por lotes. |
| Lakehouse con motor distribuido (Spark/EMR/Glue) | No | El mayor conjunto de entrenamiento tiene 47.659 filas; un clúster no aporta y encarece la operación. Se deja como evolución opcional, no implementada. |
| Base relacional o NoSQL para servir el tablero | No | El tablero lee Parquet/CSV locales con pandas; añadir un motor no mejora la latencia actual. |

**Patrón elegido:** batch, single-node, idempotente y con artefactos versionables. El CSV es la fuente versionada; el Parquet es un derivado regenerable que acelera lecturas y conserva tipos.

## 3. Componentes

| Componente | Implementación | Entradas | Salidas |
|---|---|---|---|
| Descarga | `src/ML_C/00_descargar_datos.py` | Release `datos-v1` (ZIP SIPSA/ICA) | `data/raw/SIPSA/` |
| Validación de ingesta | `src/ML_C/00b_validar_ingesta.py` | 9 fuentes crudas/derivadas | Log y `data/logs/ingesta_ultima.json` |
| Limpieza y armonización | `src/ML_C/01_limpieza.py` | Consolidados de Gobernación | `produccion_valle_clean.csv`, `lista_productos.csv` |
| Diagnóstico de series | `src/ML_C/02_diagnostico.py` | Producción limpia | `diagnostico_calidad.csv`, `diagnostico_series.csv` |
| Geografía y tiempos | `src/ML_C/03_geo_tiempos.py` | DIVIPOLA + configuración | `municipios_coordenadas.csv`, `matriz_tiempos.csv` |
| Fuentes externas | `src/ML_C/04_fuentes_externas.py` | SIPSA, ICA, FAOSTAT, NOAA, DANE | Precios, valor, ONI, consumo, comercio, población |
| Baselines | `src/ML_C/05_baselines.py` | Panel de producción | `predicciones_baselines.csv`, `metricas_baselines.csv` |
| LightGBM | `src/ML_C/06_lgbm.py` | Panel + ONI | `predicciones_lgbm.csv`, `predicciones_comparacion.csv`, importancia |
| Escenarios | `src/ML_C/07_escenarios.py` | Predicciones y calibración | `oferta_escenarios.csv`, `oferta_departamento.csv`, cobertura |
| Validación de entregas | `src/ML_C/08_validar_entregas.py` | Tablas limpias y de resultados | Reporte OK/FALLA |
| Diagnóstico del modelo | `src/ML_C/09_diagnostico_modelo.py` | Predicciones walk-forward | Tablas y figuras por segmento |
| Métrica de negocio | `src/ML_C/10_metrica_negocio.py` | Predicciones + matriz de tiempos | `metrica_negocio_*.csv` |
| Tuning opcional | `src/ML_C/06b_tuning.py` | Orígenes ≤ 2021 | `tuning_*.csv`, configuración candidata |
| Zonas, excedentes y escenarios | `src/arendonc2/ejecutar_todo.py` | Producción, población, GADM | `zonas.csv`, `excedentes.csv`, `escenarios.csv` |
| Optimización | `src/optimizacion/generar_resultados.py`, `corrida_valor.py` | Escenarios y matriz de tiempos | Pareto, estabilidad, libre vs zonas, valor |
| Exportación columnar | `src/pipeline/exportar_parquet.py` | CSV de `data/clean` y `data/results` | Parquet + `data/metadata/catalogo.yaml` |
| Orquestación | `src/pipeline/run_all.py` | Todo lo anterior | Log `data/logs/pipeline_*.log` |
| Consumo | `src/dashboard/app.py` | Parquet/CSV | Tablero Streamlit |
| Calidad | `pytest`, `test_tarea3.py`, `test_tablero_central.py`, `test_resultados_opt.py` | Artefactos | Pruebas y verificaciones |

## 4. Flujo de extremo a extremo

1. **Ingesta:** se descargan los ZIP pesados desde el Release y se descomprimen en `data/raw/`. Los archivos crudos no se editan.
2. **Validación:** `00b_validar_ingesta.py` revisa existencia, codificación, columnas, tipos, rangos, nulos, duplicados y conteos mínimos. Escribe un log y un JSON de auditoría.
3. **Trusted:** limpieza, armonización de cultivos, geografía, tiempos y fuentes externas producen tablas tipadas en `data/clean/`.
4. **Modelado:** baselines y LightGBM se evalúan con walk-forward (orígenes 2018-2022, objetivos 2019-2023) y se generan escenarios 2024-2028.
5. **Refined:** los resultados de pronóstico, diagnóstico, métrica de negocio, zonas, excedentes y optimización quedan en `data/results/`.
6. **Optimización:** OR-Tools resuelve la localización central + satélites, la frontera de Pareto, la estabilidad por escenario y la comparación libre vs zonas.
7. **Publicación columnar:** `exportar_parquet.py` convierte las tablas clave a Parquet, particiona producción y excedentes por año y actualiza el catálogo.
8. **Consumo:** el tablero lee Parquet si existe y cae a CSV si no. El resumen inicial conecta los KPIs con las pantallas de detalle.
9. **Calidad:** `run_all.py` ejecuta la validación, el pipeline, la exportación y `pytest`; el resultado queda en un log con tiempos por etapa.

El diagrama está en [`pipeline.mmd`](pipeline.mmd). Se puede renderizar con cualquier visor de Mermaid o con la extensión de Markdown de VS Code.

## 5. Contratos entre etapas

| Contrato | Regla |
|---|---|
| `cod_dane` | Siempre texto de 5 dígitos; nunca entero. |
| Codificación CSV | `utf-8-sig` para conservar compatibilidad con Excel. |
| Grano de producción | `(anio, cod_dane, producto)` sin duplicados. |
| Oferta | `producto, cod_dane, año, oferta_bajo, oferta_base, oferta_alto`, con `bajo ≤ base ≤ alto`. |
| Validación temporal | Ningún objetivo de 2022/2023 participa en la selección de hiperparámetros. |
| Lectura | Parquet primero, CSV como respaldo; nunca se sobrescribe el CSV con Parquet. |
| Idempotencia | Volver a ejecutar una etapa regenera sus salidas a partir de las fuentes, sin editar `data/raw`. |

## 6. Atributos de calidad

- **Trazabilidad:** cada tabla del catálogo registra ruta, zona, partición, filas, columnas, tipos, fuente y fecha de generación.
- **Reproducibilidad:** un solo comando (`python src/pipeline/run_all.py`) encadena validación, modelo, optimización, Parquet y pruebas.
- **Auditabilidad:** logs de ingesta y de pipeline; `metadata.json` de optimización con huellas SHA256.
- **Resiliencia:** si falta un Parquet, los lectores usan el CSV; si falta un insumo crudo descargable, `run_all.py` reutiliza las salidas ya generadas y lo advierte.
- **Costo:** cero servicios de pago; todo corre en el equipo local.

## 7. Fuera de alcance

No forman parte de esta arquitectura: despliegue en Streamlit Cloud, APIs, Docker, S3, CI/CD, MLflow, credenciales, SageMaker, Kafka, Kinesis, Flink, EMR, Glue, Redshift, Athena ni QuickSight. La sustentación también queda fuera del alcance de estos artefactos.

# Justificación del procesamiento: pandas en un solo nodo

## 1. Pregunta

¿Se justifica usar un framework distribuido (Spark, Flink, EMR, Glue) para MingaData_PI, o pandas en un solo nodo es suficiente?

**Respuesta:** pandas es suficiente para el volumen y la frecuencia actuales. Un clúster distribuido añadiría infraestructura, costo y complejidad operativa sin mejorar el tiempo de ejecución ni la calidad del resultado. La rúbrica de arquitectura otorga el nivel “Excelente” al procesamiento distribuido; este proyecto declara explícitamente un techo **“Aceptable”** en ese criterio y compensa con validación, orquestación, catálogo, Parquet y trazabilidad.

## 2. Volumen real del proyecto

| Medida | Valor | Fuente |
|---|---:|---|
| Archivos crudos | 61 | `data/raw/` |
| Tamaño crudo total | 786,2 MB | `data/raw/` (incluye 719,7 MB de ICA FRONTERA) |
| CSV limpios (`trusted`) | 13 archivos, 4,2 MB | `data/clean/` |
| CSV de resultados (`refined`) | 52 archivos, 8,8 MB | `data/results/` |
| Parquet generados | 65 archivos, 1,73 MB | catálogo |
| Filas de producción limpia | 15.019 | `produccion_valle_clean.csv` |
| Filas de excedentes | 31.230 | `excedentes.csv` |
| Filas de predicciones evaluadas | 8.323 | `predicciones_comparacion.csv` |
| Mayor matriz de entrenamiento | 47.659 filas × 14 variables | `curva_aprendizaje.csv` |
| Municipios | 42 | DIVIPOLA |
| Series modeladas | 571 | `metricas_comparacion.csv` |
| Productos modelados | 22 | `lista_productos.csv` |
| Años de panel | 2000-2023 (24) | producción |
| Horizonte de pronóstico | 2024-2028 (5) | `oferta_escenarios.csv` |

**Lectura:** el mayor conjunto de datos analítico cabe holgadamente en memoria. La tabla más pesada en memoria es `excedentes` con 6,56 MB; la matriz de entrenamiento tiene menos de 50.000 filas. No hay una tabla que se acerque a los umbrales típicos de un framework distribuido.

## 3. Umbrales de decisión

| Criterio | Umbral típico para distribuido | MingaData_PI | ¿Distribuido? |
|---|---|---|---|
| Volumen total | > 100 GB | 0,79 GB crudo; 0,013 GB derivado | No |
| Filas por tabla analítica | > 50-100 millones | 47.659 máx. en entrenamiento | No |
| Frecuencia de actualización | Streaming o micro-lotes < 1 min | Anual/mensual, batch | No |
| Latencia requerida | Segundos | Minutos; el tablero lee resultados precalculados | No |
| Usuarios concurrentes | Decenas o cientos | 1-5 analistas | No |
| Necesidad de paralelismo | CPU-bound con millones de registros | LightGBM y OR-Tools en un equipo | No |
| Equipo de plataforma | Dedicado | 4 integrantes | No |
| Costo | Cluster 24/7 | 0 COP de infraestructura | No |

## 4. Tiempos observados

Medición en el equipo de referencia (Windows 11, Python 3.13, AMD64, 1 nodo):

| Etapa | Tiempo | Observación |
|---|---:|---|
| Validación de ingesta (`00b`) | 0,9 s | 9 fuentes, 0 fallas |
| Pipeline ML completo (`00`-`08`) | 73,1 s | Incluye 43 s de baselines (ETS por serie) |
| Exportación Parquet + catálogo | ~3 s | 37 tablas |
| Diagnóstico del modelo (`09`) | ~5 s | Tablas y 4 figuras |
| Métrica de negocio (`10`) | ~3 s | t·min y COP |
| Tuning opcional (`06b`, 14 candidatos) | ~60 s | Solo se ejecuta con `--con-tuning` |
| Pruebas `pytest` | ~207 s | 58 pruebas |
| Pipeline `--rapido` completo | ~5 min | Incluye ML, diagnóstico, métrica, Parquet y pruebas |

Los tiempos exactos de la corrida quedan en `data/logs/pipeline_*.log`.

## 5. Por qué pandas y no Spark

1. **El volumen no lo exige.** 786 MB crudos, de los cuales 719,7 MB son inspecciones ICA que se leen con selección de 9 columnas y se agregan a 15.526 filas. El resto son archivos de pocos MB.
2. **El costo de operación no se justifica.** Un clúster requiere aprovisionamiento, credenciales, monitoreo y un equipo de plataforma. El proyecto es académico y corre en un portátil.
3. **La latencia ya es adecuada.** El pipeline completo tarda minutos y el tablero consume resultados precalculados; no hay usuarios esperando consultas interactivas sobre terabytes.
4. **La reproducibilidad es más simple.** Un `requirements.txt`, un comando y archivos locales son más fáciles de auditar que un clúster.
5. **El cuello de botella es el modelo, no el volumen.** Los 43 s de baselines vienen de ajustar ETS por serie, no de leer datos. Spark no acelera ese paso sin reescribir el modelado.

## 6. Técnicas de eficiencia usadas

| Técnica | Dónde | Efecto |
|---|---|---|
| Lectura por columnas | `04_fuentes_externas.py` (`usecols` en ICA) | Evita cargar 719,7 MB completos. |
| Tipos explícitos | `cod_dane` como texto, `anio` entero | Evita conversiones y pérdida de ceros. |
| Parquet + Snappy | `exportar_parquet.py` | 4,2 MB → 0,9 MB en limpios; 8,8 MB → 1,0 MB en resultados. |
| Partición por año | Producción y excedentes | Filtrar un año no lee los demás. |
| Vectorización | pandas/NumPy en limpieza y métricas | Evita bucles fila a fila. |
| Caché del tablero | `@st.cache_data` en `utils.py` | Evita releer en cada interacción. |
| Resultados precalculados | Optimización y escenarios | El tablero no resuelve OR-Tools al abrir. |
| `n_jobs=1` en tuning | `06b_tuning.py` | Resultados deterministas y comparables. |

## 7. Cuándo migrar

La migración a un framework distribuido se justificaría si ocurre alguno de estos cambios:

- El volumen supera 50-100 GB o decenas de millones de filas por tabla.
- Se incorporan fuentes en streaming con latencia subminuto.
- Varios equipos consultan el lago simultáneamente con cargas analíticas pesadas.
- Se requiere entrenar cientos de modelos en paralelo sobre ventanas móviles.
- Se necesita un catálogo central y gobierno de datos multiusuario.

Si eso ocurre, la ruta natural es subir los Parquet a un almacenamiento de objetos, usar un catálogo y ejecutar Spark o un motor SQL distribuido. **No se implementa en este proyecto** porque no responde al volumen ni al problema actual.

## 8. Conclusión

El procesamiento en pandas es una decisión de ingeniería, no una omisión: el volumen es pequeño, la frecuencia es batch, el equipo es reducido y el costo de un clúster no se recupera en ningún indicador del negocio. La arquitectura conserva las puertas abiertas (Parquet, catálogo, particiones y scripts idempotentes) para migrar sin rehacer el modelo. En la matriz de evaluación, el criterio de procesamiento distribuido se declara en nivel **Aceptable (3,0-4,4)**, con la justificación cuantitativa de este documento.

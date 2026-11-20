# Rendimiento y escalabilidad

## 1. Entorno de referencia

| Elemento | Valor |
|---|---|
| Sistema operativo | Windows 11 (10.0.26300) |
| Arquitectura | AMD64, 1 nodo |
| Python | 3.13.14 |
| pandas | 3.1.1 |
| pyarrow | 26.0.1 |
| LightGBM | 4.7.0 |
| scikit-learn | 1.9.1 |
| statsmodels | 0.15.0 |
| OR-Tools | 9.15.6755 |
| Streamlit | 1.67.0 |

Las mediciones son orientativas: dependen del equipo, del estado de la caché del sistema operativo y de si los Parquet ya existen.

## 2. Tamaño de los datos

| Conjunto | Archivos | Tamaño |
|---|---:|---:|
| `data/raw/` | 61 | 786,2 MB |
| `data/clean/` CSV | 13 | 4,2 MB |
| `data/clean/` Parquet | 36 | 0,9 MB |
| `data/results/` CSV | 52 | 8,8 MB |
| `data/results/` Parquet | 29 | 1,0 MB |
| Catálogo Parquet total | 37 tablas | 1,73 MB |

La mayor parte del peso crudo son las inspecciones ICA FRONTERA (12 archivos, 719,7 MB), que se leen con selección de columnas y se agregan a 15.526 filas.

## 3. Lectura CSV vs Parquet

Tiempo mínimo de 5 repeticiones, en milisegundos:

| Tabla | CSV | Parquet | Ganancia |
|---|---:|---:|---:|
| Producción (15.019 filas, particionada) | 4,9 ms | 11,4 ms | 0,4× |
| Predicciones (8.323 filas) | 6,1 ms | 3,5 ms | 1,7× |
| Excedentes (31.230 filas, particionada) | 35,6 ms | 5,7 ms | **6,2×** |
| Oferta (3.620 filas) | 1,3 ms | 1,7 ms | 0,8× |
| Matriz de tiempos (1.974 filas) | 1,0 ms | 1,8 ms | 0,6× |

**Interpretación honesta:** Parquet no siempre es más rápido en tablas pequeñas, porque abrir la carpeta particionada o el archivo Parquet tiene un costo fijo. La ganancia aparece en la tabla grande (`excedentes`, 6,2×) y en predicciones (1,7×). En las tablas pequeñas el beneficio real es la **estabilidad de tipos** (`cod_dane` como texto, `anio` entero) y la compresión, no la velocidad.

Por eso la estrategia es “Parquet primero, CSV como respaldo”: el tablero aprovecha Parquet cuando existe y sigue funcionando en un clon recién descargado, donde solo están los CSV.

## 4. Memoria

| Tabla | Filas | Columnas | Memoria en RAM |
|---|---:|---:|---:|
| Producción | 15.019 | 9 | 1,43 MB |
| Excedentes | 31.230 | 17 | 6,56 MB |
| Predicciones | 8.323 | 13 | 1,00 MB |
| Oferta | 3.620 | 6 | 0,21 MB |
| Comercio ICA agregado | 15.526 | 9 | 2,52 MB |

Ninguna tabla supera 7 MB en memoria. El entrenamiento de LightGBM usa 47.659 filas × 14 variables, muy por debajo de los límites de un equipo de trabajo.

## 5. Tiempos por etapa

| Etapa | Tiempo | Comentario |
|---|---:|---|
| Validación de ingesta (`00b`) | 0,9 s | 9 fuentes, 0 fallas |
| Pipeline ML (`00`-`08`) | 73,1 s | 43 s corresponden a baselines (ETS por serie) |
| Diagnóstico (`09`) | ~5 s | Tablas y 4 figuras |
| Métrica de negocio (`10`) | ~3 s | t·min y COP |
| Exportación Parquet + catálogo | ~3 s | 37 tablas |
| Tuning opcional (`06b`, 14 candidatos) | ~60 s | No forma parte del modelo final |
| `pytest` | ~207 s | 58 pruebas |
| `run_all.py --rapido` | ~5 min | Incluye ML, diagnóstico, métrica, Parquet y pruebas |
| `run_all.py` completo | Depende de OR-Tools | Añade optimización y, si se pide, tuning |

Los tiempos exactos quedan en `data/logs/pipeline_YYYYMMDD_HHMMSS.log`; el orquestador imprime un resumen por etapa.

## 6. Cuellos de botella identificados

| Cuello de botella | Causa | Mitigación |
|---|---|---|
| Baselines (43 s) | Ajuste de ETS por cada serie | Se ejecuta una vez; los resultados se reutilizan. |
| `pytest` (207 s) | Pruebas de integración y de optimización | Se ejecuta al final del pipeline; se puede omitir con `--skip pruebas`. |
| Lectura de ICA FRONTERA | 719,7 MB en 12 CSV | `usecols` con 9 columnas y agregación inmediata. |
| Tuning (60 s) | 14 candidatos × walk-forward | Es opcional (`--con-tuning`); no bloquea el pipeline. |
| Optimización OR-Tools | Muchos escenarios de estabilidad | Resultados precalculados en `data/results/opt/`; el tablero los lee. |

## 7. Escalabilidad

- **Vertical:** el proyecto escala aumentando RAM/CPU del equipo; no requiere cambios de código.
- **Por datos:** si el volumen crece, el primer paso es particionar más tablas y leer por columnas; el segundo, migrar a un motor distribuido.
- **Por usuarios:** el tablero usa caché de Streamlit; para más concurrencia se puede servir con un proceso por usuario o migrar a un servicio administrado (fuera de alcance).
- **Por frecuencia:** el pipeline es idempotente; se puede programar con el Programador de tareas de Windows o un cron, sin necesidad de un orquestador distribuido.

## 8. Conclusión

El rendimiento es adecuado para el tamaño y la frecuencia del proyecto. La combinación de pandas, Parquet, particiones, caché y resultados precalculados mantiene el pipeline por debajo de los 5 minutos en modo rápido y evita servicios de pago. La principal deuda es el tiempo de `pytest` y el ajuste de ETS, no el volumen de datos.

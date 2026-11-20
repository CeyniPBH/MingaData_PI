# EDA, hallazgos e ingeniería de características

## 1. Alcance del EDA

El EDA se hizo sobre el panel limpio de producción (15.019 filas, 42 municipios, 57 productos, 2000-2023) y sobre las series activas (724). El objetivo no fue describir por describir, sino decidir **qué transformar, qué excluir y qué variables crear** antes de modelar.

## 2. Hallazgos de calidad

| Hallazgo | Valor | Implicación |
|---|---:|---|
| Filas crudas de permanentes | 15.282 | — |
| Duplicados exactos eliminados | 18 | Se eliminan en `01_limpieza.py`; no se edita el crudo. |
| Filas limpias | 15.019 | Panel final. |
| Cultivos originales | 61 | Se armonizan a 57. |
| Productos detallados | 22 | Modelo LightGBM + ensamble. |
| Productos simplificados | 22 | Ingenuo por serie. |
| Productos excluidos | 13 | Sin producción reciente (2019-2023). |
| Municipios | 42 | Cobertura completa del Valle. |
| Años | 2000-2023 (24) | Panel anual. |
| Ceros en producción | 1,95 % | Series intermitentes; no se imputan. |
| Series activas | 724 | 571 detalladas + 153 simplificadas. |
| Transiciones | 12.501 | Base para medir repetidos y saltos. |
| Valores repetidos | 2.613 (20,9 %) | Señal de suavizado/estancamiento. |
| Saltos > 100 % | 949 (7,6 %) | Volatilidad; el modelo necesita deltas. |
| Saltos > 3 desviaciones | 327 | Outliers; se conservan y se acotan con log. |

### Confianza de las series

| Confianza | Productos | Municipios promedio | Años mediana | % repetidos | % saltos > 100 % | % saltos > 3 sd |
|---|---:|---:|---:|---:|---:|---:|
| Alta | 19 | 27,63 | 21,42 | 19,94 | 7,75 | 2,66 |
| Media | 7 | 16,71 | 20,71 | 32,93 | 8,04 | 2,93 |
| Baja | 18 | 4,56 | 12,33 | 34,44 | 5,28 | 1,36 |

**Lectura:** los productos de confianza baja tienen pocos municipios y pocos años; forzar LightGBM allí produce sobreajuste. Por eso se pronostican con el ingenuo. La confianza no es un juicio de valor sobre el cultivo, sino una medida de densidad histórica.

### Detallados vs simplificados

| Grupo | Municipios promedio | Años mediana | % repetidos | % saltos > 100 % |
|---|---:|---:|---:|---:|
| Detallado | 26,05 | 20,86 | 21,40 | 8,17 |
| Simplificado | 6,86 | 14,32 | 34,48 | 5,40 |

Los simplificados son más cortos y más repetitivos; el ingenuo es una línea base razonable y evita un modelo con demasiada varianza.

## 3. Hallazgos de distribución y valor

### Volumen (2019-2023)

| Producto | Toneladas |
|---|---:|
| Caña de azúcar | 120.379.543 |
| Caña panelera | 1.474.380 |
| Plátano | 1.454.851 |
| Cítricos | 754.285 |
| Piña | 714.545 |
| Banano | 385.654 |
| Aguacate | 360.400 |
| Café | 236.831 |

La caña de azúcar concentra el 84 % del volumen y distorsiona cualquier promedio simple. Por eso se usa **WAPE** (ponderado por volumen) además de MASE (por serie) y se reporta el error absoluto en toneladas.

### Valor (2019-2023, precios SIPSA)

| Producto | Valor (miles de millones COP) |
|---|---:|
| Caña de azúcar | 48,72 |
| Café | 3,78 |
| Plátano | 2,74 |
| Aguacate | 1,84 |
| Cítricos | 1,80 |
| Piña | 1,29 |
| Caña panelera | 0,62 |
| Vid | 0,58 |

El ranking por valor cambia 4 posiciones frente al ranking por toneladas. El proyecto conserva el ranking por toneladas para el pronóstico y usa el valor en la sensibilidad de optimización (`corrida_valor.py`), no en el target.

## 4. Hallazgos que guiaron la ingeniería

| Hallazgo | Decisión de ingeniería | Evidencia |
|---|---|---|
| Distribución muy sesgada por la caña | Target en `log1p` y error en log-cambio | La caña domina el volumen; el log estabiliza la escala. |
| 20,9 % de valores repetidos | Incluir `log_last`, `d1`, `d2`, `m3`, `m5` | El modelo necesita distinguir estancamiento de tendencia. |
| 7,6 % de saltos > 100 % | Incluir deltas y `max_rel` | Captura volatilidad y distancia al pico. |
| Series con ceros | Incluir `pct_ceros5` | Marca intermitencia sin imputar. |
| Series cortas | Incluir `hist` | Permite al modelo desconfiar de series con poca historia. |
| 42 municipios y 22 productos | Variables categóricas `cod_dane` y `producto` | La importancia relativa es 34,8 % y 21,0 %. |
| Error crece con el horizonte | Incluir `horizonte` | WAPE 7,1 % (h=1) → 13,6 % (h=5). |
| Señal climática débil pero disponible | Incluir `oni_t`, `oni_t1` | Importancia combinada ≈ 2 %; se conserva por bajo costo. |
| Productos sin precio | No usar valor en el target | 37 productos con precio; 11 activos sin precio. |
| Series simplificadas inestables | Ingenuo en lugar de LightGBM | 18 productos de confianza baja. |

## 5. Preprocesamiento reproducible

1. **Limpieza:** lectura UTF-8-SIG, normalización de separador de miles, eliminación de duplicados exactos, armonización de cultivos (limón, mandarina y naranja se suman a cítricos) y recálculo de rendimiento.
2. **Exclusión:** productos sin producción 2019-2023 se marcan como `excluido` en `lista_productos.csv`; no se borran del crudo.
3. **Panel:** se construye una serie por `(producto, cod_dane)` desde su primer año hasta 2023; los años sin registro se completan con 0.
4. **Variables:** se calculan en el punto de origen `T` con información ≤ `T`; nunca se usan valores futuros.
5. **Codificación:** `producto` y `cod_dane` se tratan como categorías; LightGBM maneja categorías nativas.
6. **Validación:** walk-forward con orígenes 2018-2022; el escalado y la selección se hacen dentro de cada ventana.

## 6. Decisiones de exclusión y armonización

| Decisión | Detalle | Motivo |
|---|---|---|
| Sumar limón, mandarina y naranja a Cítricos | Desagregación desde 2021 | Evita una serie quebrada por cambio de desagregación. |
| Excluir 13 productos | Sin producción 2019-2023 | No hay señal reciente que pronosticar. |
| No imputar precios faltantes | 11 productos activos sin precio | Se conserva el volumen; el valor solo se usa donde hay precio. |
| No eliminar outliers | Se conservan y se transforman | Eliminarlos sesgaría el volumen real. |
| Población 2024-2028 | Solo proyecciones disponibles | Se usa el primer año como tamaño estructural del municipio. |

## 7. Limitaciones del EDA

- No hay estacionalidad mensual; el panel es anual.
- No hay variables de tecnología, riego, crédito o precio pagado al productor.
- La producción reportada puede mezclar calidades y unidades; la armonización es una aproximación documentada.
- La confianza de la serie es una heurística basada en densidad y repetidos, no una validación de campo.
- El EDA no prueba causalidad; solo informa decisiones de transformación.

## 8. Artefactos

| Artefacto | Ruta |
|---|---|
| Diagnóstico de calidad | `data/results/ML_Ce/diagnostico_calidad.csv` |
| Diagnóstico por serie | `data/results/ML_Ce/diagnostico_series.csv` |
| Ranking valor vs toneladas | `data/results/ML_Ce/ranking_valor_vs_toneladas.csv` |
| Decisiones de armonización | `data/results/ML_Ce/decisiones_armonizacion.csv` |
| Importancia de variables | `data/results/ML_Ce/importancia_variables.csv` |
| Código | `src/ML_C/01_limpieza.py`, `02_diagnostico.py`, `04_fuentes_externas.py`, `06_lgbm.py` |

# Formulación del problema de pronóstico

## 1. Pregunta de negocio

¿Cuánta oferta agrícola tendrá cada municipio del Valle del Cauca en 2024-2028, por producto, para dimensionar una central de acopio, sus satélites y la logística de recolección?

La decisión que apoya el modelo es de **planificación**: qué capacidad construir, qué productos priorizar, dónde ubicar la central y cómo programar la recolección. No es una decisión de trading ni de precio; por eso el objetivo es el **volumen físico** (toneladas), no el valor.

## 2. Traducción a tarea de ML

| Elemento | Definición |
|---|---|
| Tipo de tarea | Pronóstico de series de tiempo multivariadas, multi-horizonte, con un modelo global de regresión supervisada. |
| Unidad de observación | `(producto, cod_dane, año)` para el panel histórico; `(producto, cod_dane, origen, horizonte)` para la evaluación. |
| Variable objetivo | Producción observada en toneladas (`produccion_t`) en el año objetivo. |
| Transformación del objetivo | El modelo aprende el cambio en logaritmo: `log1p(produccion_objetivo) − log1p(produccion_última)`. |
| Horizonte | 1 a 5 años. Evaluación con orígenes 2018-2022 y objetivos 2019-2023; pronóstico 2024-2028. |
| Cobertura | 42 municipios, 22 productos detallados (571 series) y 22 productos simplificados (153 series). |
| Salida | Oferta puntual y escenarios bajo/base/alto por producto, municipio y año. |
| Métrica principal | MASE (error absoluto escalado por la serie) y WAPE (error absoluto ponderado por volumen). |

### ¿Por qué un modelo global y no uno por serie?

Muchas series tienen pocos años, ceros y alta variabilidad. Un modelo por serie sería inestable y difícil de mantener. El modelo global comparte patrones entre productos y municipios, usa variables de historia y clima, y deja el ingenuo como respaldo por serie. La comparación con baselines por serie evita afirmar que el modelo es mejor cuando no lo es.

### ¿Por qué la transformación logarítmica?

La producción está muy sesgada: la caña de azúcar concentra la mayor parte del volumen. El cambio en logaritmo estabiliza la escala, reduce el efecto de los valores extremos y permite que el modelo aprenda tasas de crecimiento en lugar de niveles absolutos. La predicción se devuelve a toneladas con `expm1`.

## 3. Datos y panel

| Elemento | Valor |
|---|---|
| Fuente principal | Consolidados agrícolas de la Gobernación del Valle (permanentes y transitorios) |
| Periodo | 2000-2023 |
| Municipios | 42 |
| Cultivos originales | 61 |
| Productos armonizados | 57 |
| Productos detallados | 22 |
| Productos simplificados | 22 |
| Productos excluidos | 13 (sin producción reciente) |
| Series activas | 724 |
| Series evaluadas con LightGBM | 571 |
| Observaciones de evaluación | 8.323 |

**Supuesto de panel:** una serie existe desde su primer año con dato hasta 2023; un año sin registro se considera 0 t. Es un supuesto conservador y está documentado en `docs/ML_C/diccionario_datos.md`.

**Productos simplificados:** se pronostican con el ingenuo (último año observado) porque tienen pocas observaciones o alta dispersión. No se fuerza LightGBM donde no hay señal suficiente.

## 4. Variables del modelo

| Variable | Descripción | Justificación |
|---|---|---|
| `log_last` | `log1p` del último año observado | Nivel de partida. |
| `d1`, `d2` | Cambio logarítmico a 1 y 2 años | Tendencia de corto plazo. |
| `m3`, `m5` | Media logarítmica de 3 y 5 años menos el último año | Suavizado y reversión a la media. |
| `pct_ceros5` | Proporción de ceros en los últimos 5 años | Series intermitentes. |
| `hist` | Años de historia disponibles | Madurez de la serie. |
| `max_rel` | Último año menos el máximo histórico (log) | Distancia al pico. |
| `T` | Año de origen | Tendencia global. |
| `horizonte` | 1 a 5 | El modelo puede ajustar el error por horizonte. |
| `producto` | Categoría del producto | Patrón específico por cultivo. |
| `cod_dane` | Categoría del municipio | Patrón territorial. |
| `oni_t`, `oni_t1` | ONI del año y del año anterior | Señal climática. |

La importancia relativa observada está dominada por `cod_dane` (34,8 %), `producto` (21,0 %), `log_last` (10,2 %) y `max_rel` (8,2 %). Las variables climáticas aportan poco (ONI combinado ≈ 2 %), pero se conservan porque el costo de incluirlas es bajo y el modelo las usa cuando aportan.

## 5. Validación

- **Walk-forward:** para cada origen `O` se entrena con objetivos ≤ `O` y se evalúa en `O+1 … min(O+5, 2023)`.
- **Orígenes:** 2018, 2019, 2020, 2021 y 2022.
- **Sin fuga:** ninguna fila futura entra en el entrenamiento; el escalado y la selección de variables se hacen solo con el pasado.
- **Holdout intacto:** 2022 y 2023 no participan en la selección de hiperparámetros. El tuning usa orígenes ≤ 2020 y objetivos ≤ 2021; 2022/2023 solo se reportan al final.
- **Baselines:** ingenuo (último año), media de 5 años, deriva y ETS amortiguado.
- **Ensamble:** `(ingenuo + LightGBM) / 2` cuando LightGBM tiene predicción; si no, ingenuo.

## 6. Métricas

| Métrica | Fórmula | Uso |
|---|---|---|
| MASE | Media de `|error| / escala` con escala = error absoluto medio del ingenuo en la serie | Métrica principal; comparable entre series de distinta escala. |
| WAPE | `Σ|error| / Σ|real|` | Error ponderado por volumen; mide el impacto agregado. |
| Sesgo | Media de `predicción − real` | Detecta sobre/subestimación sistemática. |
| Cobertura | Proporción de observaciones dentro del intervalo | Calibración de escenarios. |

No se usa RMSE como métrica principal porque penaliza demasiado los picos de la caña de azúcar y no es comparable entre series. No se usa MAPE porque hay ceros y series de bajo volumen.

## 7. Escenarios bajo/base/alto

1. El modelo produce la predicción puntual.
2. Se calculan los errores históricos de calibración por producto y horizonte.
3. Se aplican cuantiles empíricos 10 % y 90 % (con corrección por horizonte cuando hay pocas observaciones).
4. Se verifica que `bajo ≤ base ≤ alto` y que la suma municipal coincida con el total departamental.

La cobertura nominal es 80 %; la cobertura observada es cercana a 76 % en la evaluación, lo que se considera aceptable para planificación.

## 8. Supuestos y limitaciones

- La producción es anual; no se modela estacionalidad intra-anual.
- El panel no distingue rendimiento por hectárea ni tecnología; solo volumen.
- Los productos simplificados usan el ingenuo, no LightGBM.
- La matriz de tiempos es aproximada; afecta la métrica de negocio, no el pronóstico.
- El modelo no es causal: no estima el efecto de un precio, un crédito o una política.
- La configuración declara `usar_oni: false`, pero la implementación carga `oni.csv` si existe; el modelo final reportado usa ONI. Se documenta la inconsistencia y no se altera el resultado.
- Los años 2022 y 2023 son escasos para estimar errores de horizontes largos; por eso la calibración usa h=4 y extiende a h=5.

## 9. Criterios de éxito

| Criterio | Umbral |
|---|---|
| MASE del ensamble ≤ MASE del ingenuo | Sí/No, por horizonte y global |
| WAPE del ensamble ≤ WAPE del ingenuo | Sí/No |
| Cobertura de intervalos | 70-85 % |
| Coherencia municipal vs departamental | 0 diferencia |
| Sin fuga temporal | Auditoría de orígenes |
| Métrica de negocio favorable vs sin modelo | Reducción de t·min |

## 10. Artefactos

| Artefacto | Ruta |
|---|---|
| Panel limpio | `data/clean/produccion_valle_clean.csv` |
| Lista de productos | `data/clean/lista_productos.csv` |
| Predicciones comparadas | `data/results/ML_Ce/predicciones_comparacion.csv` |
| Métricas | `data/results/ML_Ce/metricas_comparacion.csv` |
| Escenarios | `data/results/ML_Ce/oferta_escenarios.csv` |
| Importancia de variables | `data/results/ML_Ce/importancia_variables.csv` |
| Código | `src/ML_C/01_limpieza.py` a `07_escenarios.py` |
| Diagnóstico | `docs/ML_C/diagnostico_modelo.md` |
| Métrica de negocio | `docs/ML_C/metrica_negocio.md` |

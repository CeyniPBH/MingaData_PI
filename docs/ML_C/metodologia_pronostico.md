# Metodología del pronóstico de oferta (Ceyni → Carlos)

## 1. Problema
Pronosticar la producción anual (toneladas) de cada producto agrícola en cada municipio del Valle del Cauca para 2024-2028, con intervalos, de modo que los módulos de zonas de acopio, excedentes y optimización trabajen con una oferta futura y su incertidumbre, no solo con el promedio histórico.

- **Unidad de pronóstico:** producto × municipio. 724 series activas (44 productos con producción en 2019-2023 en 42 municipios).
- **Datos:** 24 observaciones anuales por serie como máximo (2000-2023), con 20,9 % de transiciones que repiten el valor del año anterior (ver `lectura_diagnostico.md`).
- **Grupos:** 22 productos *detallados* (todos los modelos) y 22 *simplificados* (solo ingenuo y promedio de 5 años). Los 13 productos sin producción en 2019-2023 se excluyen.

## 2. Por qué estos modelos y no redes por serie
Con ≤ 24 datos por serie no hay información suficiente para entrenar un modelo complejo por serie (redes, ARIMA con muchos parámetros) sin sobreajustar. Por eso se combinan:
1. **Baselines por serie** (sin aprendizaje o con muy pocos parámetros): ingenuo (último valor), deriva (pendiente entre el primer y el último dato), ETS con tendencia amortiguada (statsmodels) y promedio de los últimos 5 años.
2. **Un modelo global** (LightGBM) que aprende de todas las series detalladas a la vez, compartiendo patrones entre productos y municipios.

## 3. Modelo global LightGBM
- **Objetivo:** `log1p(y[T+h]) − log1p(y[T])` (cambio logarítmico respecto al último valor). Así el modelo aprende cuánto se aleja del ingenuo, y la escala de la caña de azúcar no domina el entrenamiento.
- **Variables:** último valor en log, cambios de 1 y 2 años, medias móviles de 3 y 5 años relativas al último valor, % de ceros en los últimos 5 años, longitud de la historia, distancia al máximo histórico, horizonte, año de origen, producto y municipio (categóricas). Opcional: ONI del año de origen y del anterior (`usar_oni` en `config/ML_C/parametros.yaml`).
- **Parámetros:** pérdida L1, 300 árboles, tasa 0,03, 15 hojas, mínimo 30 observaciones por hoja, submuestreo 0,8 (todo en `parametros.yaml`).
- **ONI:** el ONI futuro no se conoce al pronosticar, por lo que solo entra con rezago (años T y T−1). El experimento con/sin ONI se corre con `python src/ML_C/06_lgbm.py --comparar-oni`.

## 4. Validación walk-forward
Se simula lo que habría pasado si se hubiera pronosticado en el pasado, con ventana que se expande:

| Origen | Entrena con | Evalúa | Horizontes |
|---|---|---|---|
| 2018 | 2000-2018 | 2019-2023 | 1-5 |
| 2019 | 2000-2019 | 2020-2023 | 1-4 |
| 2020 | 2000-2020 | 2021-2023 | 1-3 |
| 2021 | 2000-2021 | 2022-2023 | 1-2 |
| 2022 | 2000-2022 | 2023 | 1 |

- En LightGBM, para cada origen O el modelo solo ve filas cuyo **año objetivo es ≤ O** (sin fugas hacia adelante).
- Todos los modelos se comparan sobre **exactamente las mismas filas** (8.323 observaciones de los 22 detallados).
- Supuesto: una serie existe desde su primer año con dato hasta 2023 y un año sin registro cuenta como 0 t.

## 5. Medición de efectividad
- **MASE:** error absoluto dividido por el error medio del ingenuo dentro del entrenamiento de esa serie. < 1 sería mejor que el ingenuo dentro de muestra; lo relevante aquí es la comparación entre modelos.
- **WAPE:** Σ|error| / Σ|real|. Interpretable como % de error sobre las toneladas; dominado por los productos de mayor volumen.
- **Mejora relativa frente al ingenuo:** `1 − métrica_modelo / métrica_ingenuo` en las mismas filas. **Criterio de éxito:** mejora positiva en MASE y WAPE.

## 6. Resultados
| Modelo | MASE | WAPE | Mejora MASE | Mejora WAPE |
|---|---|---|---|---|
| Promedio ingenuo + LightGBM | 3,899 | 0,101 | +0,5 % | −0,1 % |
| LightGBM | 3,904 | 0,103 | +0,3 % | −1,9 % |
| Ingenuo | 3,918 | 0,101 | 0 | 0 |
| Deriva | 4,049 | 0,106 | −3,3 % | −5,1 % |
| ETS amortiguado | 4,212 | 0,131 | −7,5 % | −29,5 % |
| Promedio 5 años | 4,291 | 0,150 | −9,5 % | −48,5 % |

**Conclusión honesta:** ningún modelo supera de forma material al ingenuo. LightGBM empata técnicamente y mejora MASE y WAPE a la vez en 12 de 22 productos, con márgenes pequeños. Ver `decisiones_modelado.md` para la elección del modelo final.

## 7. Escenarios de oferta 2024-2028
- **Base:** promedio de ingenuo y LightGBM en los detallados; ingenuo en los simplificados. Origen 2023.
- **Bajo / alto:** percentiles 10 y 90 del error logarítmico del walk-forward (`log1p(real) − log1p(pred)`), por producto y horizonte si hay ≥ 30 observaciones; si no, por grupo (detallado/simplificado) y horizonte. El horizonte 5 solo tiene un origen, así que se calibra con h = 4 y se ensancha por √(5/4).
- **Cobertura empírica** (calibrando sin el origen evaluado): 75,9 % frente al 80 % nominal.
- **Coherencia jerárquica:** el total departamental es la suma de los municipios (bottom-up); diferencia 0.

## 8. Cómo se evalúan los otros módulos (para el informe)
- **Zonas de acopio (Samuel):** 100 % de zonas contiguas, homogeneidad interna, oferta mínima por zona y tiempo promedio al centro de la zona.
- **Optimización (Alejandro):** frontera de Pareto con ≥ 5 puntos distintos y estabilidad de la central entre escenarios.

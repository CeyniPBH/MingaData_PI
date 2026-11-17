# Decisiones de modelado

| # | Decisión | Alternativas consideradas | Motivo |
|---|---|---|---|
| 1 | Pronosticar a nivel **producto × municipio** | Solo nivel departamental; nivel zona | Samuel y Alejandro necesitan la oferta por municipio para armar zonas y costos. El departamento se obtiene sumando (bottom-up), así siempre cuadra. |
| 2 | **22 productos detallados** por toneladas 2019-2023 | Ranking por valor SIPSA | Ver sección *Ranking por toneladas vs valor*. |
| 3 | Sumar Aguacate Hass a Aguacate y Limón/Mandarina/Naranja a Cítricos | Dejarlos separados | Conserva la serie larga desde 2000; separados tendrían 3-4 años y un quiebre artificial. |
| 4 | Un año sin registro = 0 t | Dejarlo como faltante | La serie es de producción reportada; la ausencia de registro en un municipio activo se interpreta como no producción. Se declara como supuesto. |
| 5 | **LightGBM global** y no modelos complejos por serie | Redes/ARIMA por serie | Con ≤ 24 datos por serie un modelo por serie sobreajusta; el modelo global comparte información entre series. |
| 6 | Objetivo = cambio logarítmico respecto al último valor | Predecir toneladas directamente | Evita que la caña de azúcar domine la pérdida y hace que el modelo aprenda la desviación respecto al ingenuo. |
| 7 | **Modelo final: promedio ingenuo + LightGBM** (detallados) e ingenuo (simplificados) | Solo ingenuo; solo LightGBM | Es el de menor MASE con el mismo WAPE del ingenuo. Combinar dos pronósticos de error parecido reduce varianza. **No se presenta como mejora**: es la mejor opción disponible en un empate. |
| 8 | Intervalos por **cuantiles empíricos del error walk-forward** | Cuantiles de LightGBM; intervalos paramétricos | Se basan en errores reales fuera de muestra y sirven igual para series sin LightGBM. Se mide su cobertura en lugar de suponerla. |
| 9 | ONI solo con **rezago** y desactivado por defecto | ONI contemporáneo | El ONI futuro no se conoce al pronosticar. Queda como experimento (`--comparar-oni`); se activa solo si mejora sobre las mismas filas. |
| 10 | Precios SIPSA a **precio constante** (promedio 2021-2023) | Precio corriente de cada año | SIPSA en el repo cubre 2021-2026; valorar 2000-2020 exige un precio de referencia. Se guardan también precio y valor corrientes cuando existen. |
| 11 | Precios derivados para caña de azúcar, caña panelera y café | Dejarlos sin precio | Son los productos de más peso; sin precio la ponderación por valor los ignoraría. Se marcan `tipo_precio = derivado`. |

## Ranking por toneladas vs valor
El ranking por valor (SIPSA) está en `data/results/ML_Ce/ranking_valor_vs_toneladas.csv`. Cambiaría 4 productos de grupo: entrarían **Granadilla** y **Pitaya**, y saldrían **Cebolla Larga** y **Sábila** (esta última no tiene precio en SIPSA).

Se mantuvo el ranking por toneladas porque:
1. Los 17 productos de mayor valor ya están entre los detallados; el cambio afecta solo a productos pequeños en el borde del corte (puestos 18 a 23).
2. Cambiar el grupo obliga a reentrenar LightGBM y recalibrar los escenarios a días de la integración. Granadilla, Pitaya y Cebolla Larga tienen confianza alta; la diferencia práctica es pequeña.
3. Los precios derivados (caña, café) son aproximaciones; ordenar por un valor con supuestos fuertes no es más defendible que ordenar por un dato observado.

Para cambiarlo: poner `criterio_ranking: valor` en `config/ML_C/parametros.yaml` y correr `python src/ML_C/ejecutar_todo.py`.

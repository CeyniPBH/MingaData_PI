# Calidad de los datos y limitaciones

Este documento resume el diagnóstico de calidad del consolidado agrícola, las decisiones de limpieza que se tomaron a partir de él y las limitaciones que hay que tener en cuenta al leer los resultados. Todo lo que se describe aquí se aplica en los scripts `src/ML_C/01_limpieza.py` y `src/ML_C/02_diagnostico.py`, que se corren en ese orden desde la raíz del repositorio. Las cifras salen de `data/results/ML_Ce/diagnostico_calidad.csv`, `diagnostico_series.csv` y `decisiones_armonizacion.csv`.

## 1. Datos de partida

La fuente principal es el consolidado agrícola por municipio de los cultivos permanentes del Valle del Cauca, publicado por la Gobernación del Valle en su portal de datos abiertos. Tiene 15.282 registros anuales entre 2000 y 2023, con 61 cultivos en 42 municipios. Cada registro trae hectáreas sembradas, hectáreas cosechadas, producción en toneladas y rendimiento.

Después de la limpieza quedan 15.019 registros de 57 productos, sin valores nulos en área ni en producción. La tabla limpia está en `data/clean/produccion_valle_clean.csv` (también en Parquet).

## 2. Hallazgos de calidad y decisión tomada en cada caso

| Hallazgo | Evidencia | Decisión | Script |
|---|---|---|---|
| Números guardados como texto con coma de miles | Años como "2,000" y códigos DANE como "76,001" | Se quitan las comas antes de convertir a número | 01 |
| Código de municipio sin formato | El código no coincidía con DIVIPOLA | Se convierte a texto de 5 dígitos; coincide para los 42 municipios | 01 |
| Filas duplicadas | 18 filas idénticas de brevo y té | Se eliminan antes de armonizar | 01 |
| Una familia escrita de dos formas | "Raíces y tubérculos" y "Raíces y Tubérculos" | Se unifica la escritura | 01 |
| Cultivo mal clasificado | Los cartuchos, que son flores, figuran como raíces y tubérculos | Se reclasifican como flores | 01 |
| Cambios de desagregación en el tiempo | Aguacate Hass aparece aparte desde 2020; limón, mandarina y naranja salen de "Cítricos" desde 2021 | Se suman a Aguacate y a Cítricos para conservar series continuas desde 2000 | 01 |
| Rendimiento no sumable | Al unir categorías, el rendimiento original deja de ser válido | Se recalcula como producción sobre hectáreas cosechadas | 01 |
| Productos sin producción reciente | 13 productos sin producción entre 2019 y 2023 | Se excluyen del modelado | 01 |
| Valores repetidos de un año a otro | 2.613 de 12.501 transiciones anuales (20,9 %) repiten exactamente el valor del año anterior | Se conservan, porque no se puede saber cuál es real, y el desempeño del pronóstico se reporta como mejora frente al modelo ingenuo | 02 y 04 |
| Saltos atípicos | 949 transiciones (7,6 %) cambian más de 100 % y 327 se alejan más de 3 desviaciones estándar de su serie | Se conservan y se usan para asignar un nivel de confianza a cada producto | 02 |
| Producción en cero | 293 registros con 0 toneladas | Se conservan; un año sin registro dentro de una serie se trata como 0 toneladas | 04 |
| Más área cosechada que sembrada | 152 registros (1,0 %), sobre todo yuca (53) y arracacha (33) | No se corrigen. En raíces puede haber más de una cosecha al año sobre la misma área. El exceso suma 2.143 hectáreas frente a 7,2 millones de hectáreas cosechadas en toda la serie | sin cambio |

Los 13 productos excluidos son anturios, astromelias, cartuchos, ciruela, cúrcuma, heliconias, higuerilla, iraca, manzana, morera, orellana, papa y ulluco.

Sobre los valores repetidos y los saltos: una parte de la serie parece estimación por consenso y no medición anual, y varios saltos coinciden con cambios de metodología o de cobertura más que con cambios reales de la producción. Por eso no se corrigen a mano. Se hacen visibles con el nivel de confianza y se tienen en cuenta al interpretar el pronóstico.

## 3. Nivel de confianza por producto

Se evaluaron 724 series activas (combinaciones de producto y municipio con producción entre 2019 y 2023) de 44 productos. Cada producto recibe un nivel de confianza con estas reglas:

- Baja: menos de 3 municipios, una mediana de menos de 12 años por serie o más de 50 % de valores repetidos.
- Media: más de 30 % de valores repetidos o más de 15 % de saltos mayores a 100 %.
- Alta: el resto.

| Grupo | Productos | Alta | Media | Baja |
|---|---|---|---|---|
| Detallados | 22 | 15 | 4 | 3 |
| Simplificados | 22 | 4 | 3 | 15 |
| Total | 44 | 19 | 7 | 18 |

Entre los detallados, los de confianza media son guanábana, mango, guayaba y papaya, y los de confianza baja son borojó, sábila y ají.

Los 22 productos detallados son los que tienen suficientes municipios y años para modelarse uno a uno. Suman el 99,9 % de las toneladas producidas entre 2019 y 2023, y el 98,7 % si se excluye la caña de azúcar, que por sí sola es el 95,2 % del total. Los otros 22 se estiman de forma simplificada.

## 4. Qué implica esto para el modelado

1. El pronóstico ingenuo, que repite el último valor, es difícil de superar. Se revisó si los valores repetidos lo favorecen artificialmente: la correlación entre el porcentaje de repetidos de cada serie y el error del ingenuo es prácticamente nula (Spearman 0,01). La dificultad viene más bien de que las series son cortas y de nivel casi constante.
2. Los productos de confianza baja no deben leerse como pronósticos independientes, sino como escenarios.
3. Como la caña de azúcar domina las toneladas, el error total del pronóstico (WAPE) refleja sobre todo a la caña. Por eso el desempeño también se reporta por producto.
4. El borojó aparece en un solo municipio con 26.600 toneladas entre 2019 y 2023. Conviene verificar ese dato en la fuente antes de usarlo en una decisión.

## 5. Limitaciones

Granularidad. La unidad mínima es el municipio. Las distancias se calculan entre puntos de referencia de cada municipio, no entre fincas, y los datos no dicen cuántos productores hay ni dónde están los lotes.

Frecuencia y extensión. Los datos son anuales y llegan hasta 2023, así que no hay estacionalidad dentro del año y ninguna serie tiene más de 24 puntos. Una central es una inversión a diez años o más, y 24 datos anuales no sostienen un pronóstico puntual a ese plazo. Por eso la oferta se trabaja con escenarios bajo, base y alto para 2024-2028.

Intervalos del pronóstico. Los intervalos cubren el 76,0 % de los valores reales, frente al 80 % esperado (`data/results/ML_Ce/cobertura_intervalos.csv`). Los errores con que se calibran vienen de 2019-2023, un periodo con caídas fuertes en algunos productos (el café pasó de 69.500 toneladas en 2019 a 37.400 en 2023), y por eso algunos intervalos quedan sesgados; en el café de 2028 el escenario alto coincide con el base.

Suma de escenarios. La oferta del departamento es la suma de los municipios. La suma de los escenarios bajos (o altos) de todos los municipios describe un caso extremo en el que todos caen o suben a la vez, así que el rango real del departamento es más angosto que esa suma.

Valoración y fuentes externas. La producción ya se valora con precios mayoristas de SIPSA a precio constante (promedio 2021-2023). Once productos activos no tienen precio en SIPSA, y la caña de azúcar, la caña panelera y el café usan precios derivados del producto procesado, que sobreestiman el valor en finca. Los 22 productos detallados se mantienen elegidos por toneladas; ordenarlos por valor cambiaría solo 4 productos pequeños. Los excedentes dependen del consumo por persona (FAOSTAT) y de la población municipal (proyecciones del DANE 2024-2028), y se calculan con tres escenarios de consumo en `data/results/excedentes.csv`. Trece productos, entre ellos el café y la caña panelera, no tienen un consumo equivalente en FAOSTAT; su excedente queda marcado como pendiente en lugar de suponer consumo cero. Los tiempos de viaje son aproximados: distancia en línea recta multiplicada por 1,4 y recorrida a 45 km/h.

Las limitaciones propias de los modelos y de cada fuente externa están detalladas en `docs/ML_C/limitaciones_pronostico.md`, las decisiones de modelado en `docs/ML_C/decisiones_modelado.md` y el efecto del ONI en `docs/ML_C/sensibilidad_oni.md`. Las cifras del análisis descriptivo que cita el informe (sección 4.2.3) se reproducen con `python src/informe/cifras_4_2_3.py`.

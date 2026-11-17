# Resumen del pronóstico (Ceyni → Carlos) 

## Esquema de validación (walk-forward)
- Nivel: **producto × municipio**, 724 series activas (44 productos con producción 2019-2023; 22 detallados y 22 simplificados).
- Orígenes 2018, 2019, 2020, 2021 y 2022 con ventana que se expande; horizontes de 1 a 5 años (hasta 2023).
- Una serie existe desde su primer año con dato hasta 2023, y un año sin registro cuenta como 0 t (supuesto).
- Métricas: MASE (escala = error del ingenuo dentro de la muestra de entrenamiento) y WAPE; mejora relativa frente al ingenuo sobre exactamente las mismas filas.
- Detallados: ingenuo, deriva, ETS amortiguado, promedio de 5 años y LightGBM global. Simplificados: ingenuo y promedio de 5 años.

## Resultados (22 detallados, 8.323 observaciones, mismas filas para todos los modelos)
| Modelo | MASE | WAPE | Mejora MASE vs ingenuo | Mejora WAPE vs ingenuo |
|---|---|---|---|---|
| Ingenuo | 3,918 | 0,101 | 0 % | 0 % |
| Promedio ingenuo + LightGBM | 3,899 | 0,101 | +0,5 % | −0,1 % |
| LightGBM global | 3,904 | 0,103 | +0,3 % | −1,9 % |
| Deriva | 4,049 | 0,106 | −3,3 % | −5,1 % |
| ETS amortiguado | 4,212 | 0,131 | −7,5 % | −29,5 % |
| Promedio 5 años | 4,291 | 0,150 | −9,5 % | −48,5 % |

## Para el informe (5 líneas)
1. Se probaron ingenuo, deriva, ETS amortiguado, promedio de 5 años y un LightGBM global (log del cambio respecto al último valor; rezagos, medias móviles, producto, municipio y horizonte).
2. Ningún modelo supera de forma material al ingenuo: LightGBM queda en empate técnico (MASE +0,3 %, WAPE −1,9 %) y solo mejora MASE y WAPE a la vez en 12 de 22 productos, con márgenes pequeños.
3. ETS, deriva y promedio de 5 años empeoran: con 24 datos anuales y cambios de nivel bruscos, extrapolar la tendencia no ayuda.
4. Para la oferta se usa el promedio ingenuo + LightGBM en los detallados y el ingenuo en los simplificados; no se vende como una mejora, sino como la mejor opción disponible en un empate.
5. El ONI no se probó porque aún no está en data/clean/oni.csv; el script lo incorpora (con rezago) apenas exista el archivo.

## Sobre los valores repetidos
El 20,9 % de las transiciones anuales repiten exactamente el valor del año anterior. Pero en estos datos **no encontré evidencia de que eso explique** un buen desempeño del ingenuo: a nivel de serie la correlación entre % de repetidos y WAPE del ingenuo es ≈ 0 (Spearman 0,01), y los productos con más de 25 % de repetidos tienen un MASE del ingenuo mayor (mediana 3,1 vs 1,8). El ingenuo es difícil de superar por otras razones (series cortas y de nivel casi constante).

## Escenarios 2024-2028
- Base = pronóstico anterior; bajo y alto = percentiles 10 y 90 del error logarítmico del walk-forward, por producto y horizonte (si hay ≥ 30 observaciones) o por estado y horizonte.
- Cobertura con calibración dejando un origen afuera: **75,9 %** frente al 80 % nominal (horizontes 1-5: 76,4; 76,2; 76,0; 73,7; 76,4). El horizonte 5 solo tiene un origen, así que se calibra con h = 4 y se ensancha por √(5/4).
- Coherencia: la oferta departamental es la suma de los municipios (bottom-up), diferencia 0. Las sumas de bajo y de alto describen un caso extremo en el que todos los municipios caen o suben a la vez; el rango real del departamento es más angosto.

## Limitaciones
- Los errores del walk-forward cubren 2019-2023, un periodo con caídas (por ejemplo café: 69,5 mil t en 2019 a 37,4 mil t en 2023). Por eso algunos intervalos quedan sesgados (café 2028: alto = base).
- Los 22 detallados se eligen provisionalmente por toneladas 2019-2023; falta reordenarlos por valor cuando haya precios SIPSA. La caña de azúcar es ≈ 96 % de las toneladas, así que el WAPE total de toneladas lo domina.
- Borojó aparece con un solo municipio y 26,6 mil t en 2019-2023: conviene verificarlo en la fuente.

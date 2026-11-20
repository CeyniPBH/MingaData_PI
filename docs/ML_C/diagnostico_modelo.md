# Diagnóstico del modelo final

## 1. Qué se diagnosticó

El modelo final es el **ensamble `(ingenuo + LightGBM) / 2`** para los 22 productos detallados y el **ingenuo** para los 22 simplificados. Este diagnóstico usa las predicciones walk-forward ya generadas (`predicciones_comparacion.csv`, 8.323 observaciones, 571 series) y **no reentrena** el modelo final.

Se analizan cinco dimensiones:

1. Horizonte de pronóstico (1 a 5 años).
2. Producto.
3. Tamaño del municipio (población).
4. Nivel de confianza de la serie.
5. Residuales y curva de aprendizaje.

## 2. Resultado global

| Métrica | Modelo final | Ingenuo | Diferencia |
|---|---:|---:|---:|
| MASE | **3,9067** | 3,9175 | −0,28 % |
| WAPE | 10,13 % | **10,10 %** | +0,03 pp |
| Error absoluto total | 38,83 M t | 38,69 M t | +0,35 % |
| Sesgo medio | −662,8 t | — | Subestima en promedio |
| Error absoluto medio | 4.665 t | — | — |
| Real total | 383,18 M t | 383,18 M t | — |

**Lectura:** el ensamble empata prácticamente con el ingenuo en el agregado. Mejora el MASE (por serie) pero pierde ligeramente en WAPE (por volumen). No se puede afirmar que sea mejor en todos los segmentos; el diagnóstico sirve para decidir **dónde usarlo y dónde no**.

### Residuales

| Estadístico | Valor |
|---|---:|
| Residual medio | −662,8 t |
| Residual mediano | +3,87 t |
| Desviación estándar | 29.975 t |
| Percentil 5 | −3.189,9 t |
| Percentil 95 | 2.942,5 t |
| % sobreestima | 54,73 % |
| % subestima | 45,08 % |

La mediana está cerca de cero, pero la media es negativa por los grandes errores de la caña de azúcar. La distribución tiene colas: los 20 mayores residuales absolutos están dominados por caña de azúcar en municipios como 76895, 76130, 76497 y 76113. El detalle está en `residuales_top.csv`.

## 3. Por horizonte

| Horizonte | Observaciones | MASE | WAPE | Sesgo (t) | Mejora absoluta vs ingenuo |
|---:|---:|---:|---:|---:|---:|
| 1 | 2.794 | 1,8484 | 7,14 % | −396 | **−6,83 %** |
| 2 | 2.223 | 3,2457 | 9,92 % | −524 | **−3,57 %** |
| 3 | 1.657 | 5,0194 | 11,88 % | −741 | +0,02 % |
| 4 | 1.102 | 6,8862 | 13,49 % | −956 | **+6,31 %** |
| 5 | 547 | 7,7154 | 13,61 % | −1.759 | **+8,17 %** |

**Lectura:** el error crece con el horizonte, como es esperable. El ensamble **pierde** en h=1 y h=2, empata en h=3 y **gana** en h=4 y h=5. El sesgo negativo también crece: en horizontes largos el modelo subestima de forma sistemática. Para planificación de largo plazo el ensamble aporta; para el corto plazo el ingenuo es más seguro.

## 4. Por producto

Los productos con mayor error absoluto acumulado:

| Producto | Error absoluto (t) | Real (t) | WAPE | Mejora vs ingenuo |
|---|---:|---:|---:|---:|
| Caña de azúcar | 32.703.190 | 364.908.147 | 8,96 % | −0,44 % |
| Caña panelera | 1.359.962 | 4.349.167 | 31,27 % | −3,42 % |
| Plátano | 1.129.694 | 4.620.211 | 24,45 % | +0,41 % |
| Aguacate | 718.756 | 1.251.341 | 57,44 % | +0,31 % |
| Piña | 617.920 | 2.118.237 | 29,17 % | +2,11 % |
| Cítricos | 602.068 | 2.357.952 | 25,53 % | +2,99 % |
| Banano | 542.909 | 1.198.334 | 45,31 % | −3,24 % |
| Café | 299.279 | 633.377 | 47,25 % | +2,77 % |

Productos donde el ensamble mejora más de 5 % en error absoluto:

| Producto | Mejora vs ingenuo |
|---|---:|
| Maracuyá | +6,91 % |
| Papaya | +5,39 % |
| Yuca | +5,34 % |
| Sábila | +5,11 % |
| Ají | +5,10 % |

**Lectura:** la caña de azúcar concentra el 84 % del volumen y el 84 % del error absoluto. No es un problema del modelo, es la naturaleza del dato: pequeños errores porcentuales en caña son millones de toneladas. Los productos de fruta (maracuyá, papaya, yuca, ají) sí muestran mejoras claras, aunque su volumen sea menor.

## 5. Por tamaño de municipio

Se usó la población proyectada 2024 como tamaño estructural (las proyecciones limpias empiezan en 2024). Se dividieron los municipios en terciles.

| Tamaño | Observaciones | Series | MASE | WAPE | Sesgo (t) | Mejora vs ingenuo |
|---|---:|---:|---:|---:|---:|---:|
| Grande | 2.774 | 192 | 2,3698 | 6,47 % | −2.238 | +0,81 % |
| Mediano | 2.774 | 193 | 3,8461 | 15,74 % | +1.325 | −1,94 % |
| Pequeño | 2.775 | 188 | 5,5006 | 19,46 % | −1.076 | +0,39 % |

**Lectura:** el WAPE se dispara en municipios pequeños y medianos. La causa es el bajo volumen: un error de pocas toneladas pesa mucho en el denominador. El sesgo cambia de signo por tamaño, lo que sugiere que el modelo no captura bien la heterogeneidad territorial. Para decisión municipal conviene agregar por zona; para decisión departamental el error es aceptable.

## 6. Por confianza de la serie

| Confianza | Observaciones | Series | MASE | WAPE | Sesgo (t) | Mejora vs ingenuo |
|---|---:|---:|---:|---:|---:|---:|
| Alta | 6.544 | 449 | 3,6890 | 10,04 % | −843 | −0,37 % |
| Media | 1.361 | 93 | 5,4790 | 49,81 % | −43 | +1,56 % |
| Baja | 418 | 29 | 2,2448 | 87,37 % | +133 | +2,02 % |

**Lectura contraintuitiva:** las series de confianza baja tienen MASE bajo pero WAPE altísimo. La confianza mide densidad histórica, no predictibilidad; las series bajas tienen volúmenes pequeños y el WAPE se vuelve muy sensible. El ensamble mejora levemente en media y baja, pero no en alta. La confianza debe usarse como **bandera de comunicación** (“serie con poca historia”), no como garantía de precisión.

## 7. Curva de aprendizaje

Se entrenó un LightGBM con origen 2022 y validación 2023, variando el número de iteraciones:

| Iteraciones | RMSE entrenamiento (log) | RMSE validación (log) |
|---:|---:|---:|
| 25 | 1,5736 | 0,8866 |
| 50 | 1,5299 | **0,8797** |
| 100 | 1,4538 | 0,8872 |
| 200 | 1,4065 | 0,8955 |
| 300 | 1,3802 | 0,8962 |
| 500 | 1,3434 | 0,9033 |

**Lectura:** la validación se estabiliza y luego empeora lentamente, mientras el entrenamiento sigue bajando. Hay **sobreajuste leve**. El mínimo de validación está en 50 iteraciones; la configuración final usa 300. La diferencia en log-RMSE es pequeña (0,8797 vs 0,8962, ≈1,8 %), pero sugiere que un early stopping en 50-100 sería más conservador. No se cambió el modelo final para no alterar los resultados ya documentados.

## 8. Interpretación y acciones

| Hallazgo | Acción recomendada |
|---|---|
| El ensamble pierde en h=1 y h=2 | Usar el ingenuo para planificación de corto plazo; reservar el ensamble para h=4 y h=5. |
| El ensamble gana en h=4 y h=5 | Usarlo en planes de inversión y capacidad de largo plazo. |
| La caña de azúcar domina el error absoluto | Reportar error porcentual y no solo toneladas; revisar los municipios 76895, 76130 y 76497. |
| Municipios pequeños con WAPE alto | Agregar por zona de acopio antes de decidir; no usar el pronóstico municipal aislado. |
| Sesgo negativo creciente | Aplicar una corrección de sesgo por horizonte si se usa el nivel absoluto. |
| Confianza baja con WAPE alto | Etiquetar esas series en el tablero y no presentarlas como pronóstico firme. |
| Sobreajuste leve | Si se reentrena, usar early stopping en 50-100 iteraciones y validación temporal. |

## 9. Artefactos

| Artefacto | Ruta |
|---|---|
| Diagnóstico por horizonte | `data/results/ML_Ce/diagnostico_horizonte.csv` |
| Diagnóstico por producto | `data/results/ML_Ce/diagnostico_producto.csv` |
| Diagnóstico por municipio | `data/results/ML_Ce/diagnostico_municipio.csv` |
| Diagnóstico por confianza | `data/results/ML_Ce/diagnostico_confianza.csv` |
| Residuales resumen | `data/results/ML_Ce/residuales_resumen.csv` |
| Top residuales | `data/results/ML_Ce/residuales_top.csv` |
| Curva de aprendizaje | `data/results/ML_Ce/curva_aprendizaje.csv` |
| Figuras | `data/results/ML_Ce/figuras/` |
| Código | `src/ML_C/09_diagnostico_modelo.py` |

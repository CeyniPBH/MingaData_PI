# Criterios de éxito

Proyecto Minga Data: central de acopio y procesamiento de productos agrícolas en el Valle del Cauca. Versión del 23 de noviembre de 2026.

Este documento dice cómo se sabe si cada parte del proyecto salió bien y qué pasó al medirlo. Los criterios se fijaron antes de correr los modelos. Las cifras son las del informe final (secciones 3.1.5, 3.3.4 y 3.4.3) y se reproducen con los scripts de `src/`.

## Cómo leer los criterios

Hay dos grupos. Los criterios técnicos comparan cada modelo con una referencia sencilla: si el modelo no le gana a la referencia, no aporta. Los criterios de negocio preguntan si el resultado le sirve a quien decide dónde poner la central y de qué tamaño.

La referencia del pronóstico es el modelo ingenuo, que repite el último valor observado de cada serie. Es como pronosticar que mañana hará el clima de hoy: no tiene ciencia, pero acierta seguido, y un método más complejo solo se justifica si le gana. Aquí es un rival todavía más difícil, porque el 20,9 % de los valores de la fuente repite el del año anterior. Medir contra él evita presentar como acierto lo que es repetición.

## Criterios técnicos

| Parte | Criterio | Cómo se mide | Resultado | ¿Se cumple? |
|---|---|---|---|---|
| Pronóstico | Mejorar el MASE y el WAPE del ingenuo sobre las mismas observaciones | Validación walk-forward, orígenes 2018 a 2022, 8.323 observaciones de los 22 productos detallados | MASE 0,28 % mejor y WAPE 0,35 % peor. Sin caña de azúcar, 0,31 % y 0,13 % mejor | No en el total. Sí sin caña, por un margen mínimo |
| Pronóstico | La cobertura del intervalo entre los escenarios bajo y alto se acerca al 80 % | Porcentaje de valores reales que caen dentro del intervalo, con percentiles calibrados sin los errores del mismo origen | 76,0 % (entre 73,8 % y 77,3 % según el horizonte) | A medias: el intervalo es algo estrecho |
| Pronóstico | La suma de los municipios coincide con el total del departamento | Diferencia entre la suma y el total, por producto y año | Diferencia cero en los 44 productos y los cinco años | Sí |
| Zonas | Todas las zonas son contiguas | Cada zona forma un solo grupo conectado con la vecindad tipo reina | Las cinco zonas son contiguas | Sí |
| Optimización | Cada solución es óptima según el solver | Estado que reporta SCIP y brecha de optimalidad | Todas las ejecuciones óptimas; la mayor brecha fue 0,0025 % | Sí |
| Optimización | La frontera de Pareto solo tiene soluciones no dominadas | Se descarta toda solución que otra iguala o supera en los dos costos | Dos puntos en el escenario base: Sevilla y Bugalagrande. La solución con λ = 0 quedó dominada y se sacó | Sí |

En la propuesta se pedía además que las zonas fueran homogéneas. Ese criterio no se fijó como umbral, porque la contigüidad obliga a unir municipios vecinos aunque su oferta sea distinta. La homogeneidad se reporta con la silueta, que para cinco zonas es 0,211, un valor bajo. Las zonas sirven para organizar la recolección y no deben leerse como grupos de municipios parecidos.

## Criterios de negocio

| Criterio | Cómo se mide | Resultado | ¿Se cumple? |
|---|---|---|---|
| La central recomendada es la misma en más de la mitad de los escenarios | Frecuencia del municipio elegido en los 54 escenarios de 2024 y 2028 | Bugalagrande sale en 18 de 54 (33 %). Por subregión, la central cae en el Centro en los 54 | No por municipio. Sí por subregión |
| El error del pronóstico se expresa en pesos | Errores por producto y municipio valorados con precios mayoristas del SIPSA | A un año suman el 25 % del valor de la oferta sin caña, unos 735.000 millones de pesos por año. En el total del departamento la desviación es de 7 % a un año | Sí |
| La capacidad se reporta con su utilización en los escenarios bajo, base y alto | Toneladas captadas divididas por la capacidad | Con sede en Bugalagrande, radio de 40 km y captación de 20 %: 86.300 toneladas al año. En el peor año de 2014 a 2023 se usaría al 67 %; en el mejor faltaría 30 % de capacidad | Sí |
| Hipótesis: la mejor sede del centro o del norte alcanza más del 50 % del área de fruta y plátano y necesita al menos el doble de capacidad que la mejor sede del sur | Área a 40 km y capacidad necesaria de cada sede | Bugalagrande alcanza el 52,1 % del área y Vijes, la mejor del sur, el 17,1 %. La capacidad es 1,89 veces la de Vijes | Primera parte sí, segunda no. La hipótesis se rechaza |

## Qué dicen los resultados en conjunto

El pronóstico no supera con claridad al ingenuo. Por eso la oferta futura se entrega en tres escenarios (bajo, base y alto) y la optimización se corre en todos, en lugar de apoyarse en un solo número.

La optimización distingue bien la subregión y mal el municipio. El costo se parece al fondo de una olla: en el centro del departamento es casi plano, y entre esas ubicaciones cambia menos de 0,7 %. La recomendación que el proyecto puede sostener es "la central va en el centro del departamento"; el municipio exacto necesita datos que el modelo no tiene, como costos de terreno y vías reales.

La hipótesis de tamaño falló por la piña. El área de Vijes produce muchas toneladas por hectárea porque más de la mitad es piña. Sin piña, las dos áreas rinden casi lo mismo.

## Reglas que se fijaron antes de mirar los resultados

- La búsqueda de hiperparámetros usó los orígenes 2018 a 2020. Los años 2022 y 2023 se reservaron y se usaron una sola vez, para confirmar.
- Para decidir si el índice ONI se quedaba en el modelo, se fijó que quitarlo no debía mover la oferta del departamento más de 1 %. Se movió entre 1,05 % y 1,48 %, así que se revisó la decisión de negocio: la central es la misma en los 54 escenarios con ONI y sin él.
- La hipótesis se acepta solo si se cumplen sus dos partes.

## Dónde está el detalle

- Métricas del pronóstico: `docs/ML_C/metodologia_pronostico.md` y `docs/ML_C/metrica_negocio.md`.
- Zonas: `docs/arendonc2/zonas_metodologia.md`.
- Optimización: `docs/formulacion_optimizacion.md`.
- Método completo: `docs/metodologia_efectividad.md`.

# Metodología y medición de la efectividad

Proyecto Minga Data: central de acopio y procesamiento de productos agrícolas en el Valle del Cauca. Versión del 23 de noviembre de 2026.

Este documento responde dos preguntas de la retroalimentación a la propuesta: cómo se aborda el problema y cómo se mide si el método funciona. Cubre el pronóstico de la oferta, las zonas de acopio, los excedentes y la optimización. Las cifras son las del informe final.

## El problema en una frase

Hay que decidir dónde poner una central de acopio y sus acopios satélite. Para decidirlo hace falta saber cuánto va a producir cada municipio en los próximos cinco años, y eso no se conoce: se pronostica.

El trabajo tiene dos etapas. El aprendizaje automático pronostica la oferta y agrupa los municipios en zonas. La optimización toma esos dos resultados y escoge la ubicación. La frontera entre las dos está en el diagrama `docs/diagramas/diagrama2_frontera.png`.

## El problema de pronóstico

Se pronostica la producción anual, en toneladas, de cada producto en cada municipio entre 2024 y 2028. La fuente es el consolidado agrícola de la Gobernación del Valle del Cauca, con datos anuales de 2000 a 2023.

Hay 724 series activas: combinaciones de producto y municipio con producción entre 2019 y 2023, de 44 productos en 42 municipios. Cada serie tiene 24 datos como máximo, uno por año. Esa es la restricción que manda en todo el método. Con 24 puntos, y varios de ellos repetidos o con saltos, una serie sola da muy poco para aprender.

## Qué se probó

Se compararon tres familias de modelos.

La primera son cuatro modelos de referencia, ajustados serie por serie: el ingenuo, que repite el último valor; la deriva, que prolonga la tendencia entre el primer dato y el último; el suavizamiento exponencial con tendencia amortiguada (ETS), y el promedio de los últimos cinco años.

La segunda es un modelo global, LightGBM, que se entrena a la vez con las series de los 22 productos con más toneladas. Un modelo global compensa la falta de historia de cada serie con la cantidad de series: aprende patrones que se repiten entre productos y municipios. En lugar de las toneladas, pronostica cuánto cambia la producción frente al último año, en logaritmos, para que la caña de azúcar, que es enorme, no domine el entrenamiento.

La tercera es la combinación: el promedio del ingenuo y LightGBM.

## Por qué no redes neuronales por serie

Una red neuronal o un ARIMA con muchos parámetros, ajustados a una sola serie, tendrían casi tantos parámetros como datos. Con 24 puntos memorizarían la historia en vez de aprender de ella. Es como dibujar el contorno de un país con 24 puntos: una regla sencilla da una silueta burda pero estable, y una curva muy flexible pasa por todos los puntos y en el medio hace cualquier cosa. Por eso se probaron modelos simples por serie y un solo modelo flexible para todas juntas.

## Cómo se valida

Se usa walk-forward con ventana creciente. Se escoge un año de origen, se entrena solo con los datos hasta ese año y se evalúa en los años siguientes, que el modelo no ha visto. Después se avanza el origen un año y se repite.

Los orígenes van de 2018 a 2022. Con el origen 2018 se entrena hasta 2018 y se evalúan 2019 a 2023, es decir, los horizontes de 1 a 5 años. Con el origen 2022 solo queda 2023 para evaluar. En total salen 8.323 observaciones de los 22 productos detallados, y todos los modelos se comparan sobre esas mismas observaciones.

Es el equivalente a un examen con preguntas que no estaban en el taller. Si el modelo se evaluara con datos que usó para entrenarse, la nota mediría su memoria.

Para los hiperparámetros de LightGBM se tuvo el mismo cuidado. La búsqueda entre 14 configuraciones usó los orígenes 2018 a 2020. Los años 2022 y 2023 quedaron guardados y se usaron una sola vez, al final, para confirmar. La configuración que ganó la búsqueda empeoró en esos dos años, así que se mantuvo la configuración de referencia, que se había fijado de antemano.

## Cómo se mide

Se usan dos métricas, las dos sobre el error absoluto.

El MASE divide el error de cada serie por el error que tendría el ingenuo dentro de los datos de entrenamiento de esa misma serie. Así una serie de 50 toneladas y una de 50.000 pesan lo mismo, y las grandes no esconden a las pequeñas.

El WAPE suma todos los errores en toneladas y los divide por las toneladas reales. Se lee como un porcentaje de error sobre el volumen. Lo dominan los productos grandes: la caña de azúcar pone el 95,2 % de las toneladas, así que el WAPE total es en la práctica el de la caña. Por eso se reporta también sin caña, que es el que importa para dimensionar la central.

La efectividad se mide como mejora relativa frente al ingenuo: uno menos el cociente entre la métrica del modelo y la del ingenuo, en las mismas filas. Un valor positivo quiere decir que el modelo se equivoca menos que repetir el último dato. El ingenuo es la vara porque es lo que haría cualquiera sin modelo, como suponer que mañana hará el clima de hoy. Suena pobre, pero acierta mucho, y un modelo que no le gane no justifica su complejidad.

Además de las dos métricas se revisan tres cosas: la cobertura del intervalo entre los escenarios bajo y alto, que debería contener el 80 % de los valores reales; la coherencia, es decir, que la suma de los municipios dé el total del departamento, y el error traducido a pesos con los precios del SIPSA.

## Qué resultó

| Modelo | MASE | WAPE | Mejora MASE | Mejora WAPE | Mejora WAPE sin caña |
|---|---|---|---|---|---|
| Ingenuo | 3,918 | 10,1 % | 0 % | 0 % | 0 % |
| Deriva | 4,049 | 10,6 % | -3,34 % | -5,14 % | -8,32 % |
| ETS amortiguado | 4,212 | 13,1 % | -7,53 % | -29,55 % | -14,09 % |
| Promedio de 5 años | 4,291 | 15,0 % | -9,54 % | -48,47 % | -20,20 % |
| LightGBM | 3,919 | 10,4 % | -0,04 % | -2,74 % | -1,71 % |
| Promedio del ingenuo y LightGBM (final) | 3,907 | 10,1 % | 0,28 % | -0,35 % | 0,13 % |

Un valor negativo indica un error mayor que el del ingenuo.

Ningún modelo supera con claridad al ingenuo. El modelo final, el promedio del ingenuo y LightGBM, queda empatado con él: mejora el MASE en 0,28 % y, sin caña, el WAPE en 0,13 %. Se escogió el promedio porque combinar dos pronósticos de precisión parecida y errores distintos reduce la varianza del error.

Darle más capacidad al modelo no ayuda. Con 25 a 500 árboles, el error de validación casi no se mueve. El límite está en los datos: darle más árboles al modelo es como ampliar una foto borrosa, que muestra más píxeles y no más detalle.

La consecuencia práctica es que la oferta futura no se entrega como un número. Se entrega en tres escenarios, bajo, base y alto, que salen de los percentiles 10 y 90 de los errores de la validación. Esos escenarios contienen el valor real en el 76,0 % de los casos, algo menos que el 80 % esperado.

En pesos, a un año los errores por producto y municipio suman el 25 % del valor de la oferta sin caña. En el total del departamento buena parte se compensa y la desviación baja a 7 %. El pronóstico sirve para la oferta agregada con la que se dimensiona la central. Para un municipio aislado el error es demasiado grande.

## Cómo se evalúan las zonas de acopio

Las zonas agrupan los 42 municipios según su ubicación y el valor de su oferta. Se forman con el agrupamiento jerárquico de Ward, con la restricción de que solo se pueden unir municipios vecinos. Dos municipios son vecinos si comparten frontera en los polígonos de GADM.

Como es una tarea sin respuesta correcta conocida, se evalúa con cuatro medidas:

- Contigüidad: que cada zona sea un solo bloque en el mapa. Es el requisito, y se cumple en todas las particiones.
- Silueta: qué tan parecidos son los municipios de una misma zona frente a los de las otras.
- Balance: cuántos municipios tiene cada zona y qué tan pareja queda la oferta entre zonas.
- Tiempo de viaje al centro de la zona, promedio y máximo, que es lo que le importa a la recolección.

Se compararon particiones de 3 a 8 zonas. Se escogieron cinco: dan el menor tiempo promedio al centro (45,8 minutos) entre las opciones que no dejan una zona gigante ni una zona de un solo municipio. La silueta de cinco zonas es baja, 0,211. Es el precio de exigir contigüidad, parecido a armar los barrios de una ciudad por manzanas vecinas: quedan compactos, pero en el mismo barrio conviven casas muy distintas.

## Cómo se calculan los excedentes

Los excedentes no salen de un modelo. Son una resta: la oferta pronosticada menos el consumo local estimado, con piso en cero. El consumo local es el consumo por persona de FAOSTAT multiplicado por la población proyectada del DANE. Se calculan nueve escenarios, con tres niveles de oferta y tres de consumo. Sus supuestos están en `docs/calidad_y_limitaciones.md`.

## Cómo se evalúa la optimización

La optimización es un programa lineal entero mixto que se resuelve con SCIP desde OR-Tools. Decide en qué municipio va la central, dónde van los acopios satélite y a cuál acopio entrega cada municipio. Compiten dos costos, medidos en toneladas por minutos de viaje: la recolección, de los municipios a los acopios y de ahí a la central, y la distribución, de la central a los mercados y puertos. El modelo minimiza λ por la recolección más (1 − λ) por la distribución, y λ se mueve entre 0 y 1 para recorrer los compromisos entre los dos.

Se evalúa con tres preguntas.

La primera es si cada solución es de verdad la mejor. Se revisa el estado que reporta el solver y la brecha de optimalidad. Todas las ejecuciones terminaron óptimas, con una brecha máxima de 0,0025 %, y el costo de recolección se recalculó por fuera del solver para comprobarlo.

La segunda es qué tan buena es la frontera de Pareto. Se resuelve el escenario base con 11 valores de λ y se descartan las soluciones dominadas. Quedan dos puntos, Sevilla y Bugalagrande, separados por menos de 0,4 % en el costo total.

La tercera es qué tan estable es la ubicación. Se resuelven los 27 escenarios de 2024 y los 27 de 2028, que combinan oferta, consumo y mezcla entre mercado nacional y exportación, y se cuenta cuántas veces sale cada municipio. Bugalagrande sale en 18 de 54, Riofrío en 15, Yotoco en 12, Sevilla en 6 y Andalucía en 3. Los cinco están en la subregión Centro. Se repitió todo pesando los municipios por el valor de su excedente y forzando un acopio por zona, para ver si la respuesta cambiaba.

El resultado es que el costo se parece al fondo de una olla: en el centro del departamento es casi plano. El modelo distingue con claridad la subregión, pero no un municipio en particular.

## Cómo se mide la efectividad para el negocio

La pregunta final es si usar el modelo deja mejor a quien planea que no usarlo. La situación sin modelo se representó con la regla de quien planea a mano: el promedio de los últimos cinco años. Cada tonelada mal estimada se multiplicó por los minutos hasta el acopio más cercano y cada tonelada por minuto se valoró en 250 pesos, que salen de un camión de 8 toneladas a 120.000 pesos la hora.

Sin caña de azúcar, en los pronósticos a un año de 2019 a 2023, el modelo final reduce esa exposición 30 % frente al promedio de cinco años, unos 1.500 millones de pesos por año. El ingenuo la reduce 32 %. Casi toda la ganancia frente a planear a mano viene de usar el dato más reciente, y LightGBM no la aumenta. La cifra mide la exposición de la planeación. No es un ahorro contable.

## Cómo reproducirlo

Todo corre con `python src/pipeline/run_all.py`, que ejecuta las nueve etapas en orden. El detalle de cada parte está en `docs/ML_C/metodologia_pronostico.md`, `docs/arendonc2/zonas_metodologia.md` y `docs/formulacion_optimizacion.md`.

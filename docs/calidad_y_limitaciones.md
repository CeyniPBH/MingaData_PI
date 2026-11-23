# Calidad de datos y limitaciones

Proyecto Minga Data: central de acopio y procesamiento de productos agrícolas en el Valle del Cauca. Versión del 23 de noviembre de 2026.

Este documento describe los problemas de calidad de los datos, qué se hizo con cada uno y hasta dónde se puede confiar en los resultados. Incluye los supuestos del cálculo de excedentes. Las cifras son las del informe final (secciones 3.2 y 3.3).

## La fuente principal

La producción viene del consolidado agrícola por municipio de los cultivos permanentes del Valle del Cauca, que publica la Gobernación en datos.gov.co. Tiene 15.282 registros anuales entre 2000 y 2023, de 61 cultivos en 42 municipios. Cada registro trae hectáreas sembradas, hectáreas cosechadas, toneladas y rendimiento.

No todo en ella es una medición anual. Los valores repetidos de un año al siguiente indican que parte de la serie es una estimación por consenso, y eso explica varios de los problemas que siguen.

## Los cuatro problemas que afectan el modelado

Valores repetidos. De las 12.501 transiciones de un año al siguiente, 2.613 (20,9 %) repiten exactamente el valor del año anterior. Una finca no produce las mismas toneladas dos años seguidos, así que una parte de la serie es una estimación que se copió y no una medición nueva. Es como un medidor de agua que algunos meses no se lee y se factura con la lectura anterior: el consumo real cambió, pero el registro no.

Saltos atípicos. 949 transiciones (7,6 %) cambian más de 100 % de un año a otro, y 327 se alejan más de tres desviaciones estándar de su serie. Varios coinciden con cambios de metodología o de cobertura y no con cambios reales en el campo.

Producción en cero. 293 registros reportan 0 toneladas.

Más área cosechada que sembrada. Pasa en 152 registros (1,0 %), sobre todo de yuca (53) y arracacha (33). En las raíces puede haber más de una cosecha al año sobre la misma área. El exceso suma 2.143 hectáreas, frente a 7,2 millones cosechadas en toda la serie.

## Qué se hizo con cada problema

| Problema | Evidencia | Decisión |
|---|---|---|
| Números guardados como texto | Años como 2,000 y códigos DANE como 76,001 | Se quitan las comas antes de convertir a número |
| Código de municipio sin formato | No coincidía con la DIVIPOLA | Se convierte a texto de 5 dígitos; coincide en los 42 municipios |
| Filas duplicadas | 18 filas idénticas de brevo y té | Se eliminan antes de armonizar |
| Familia escrita de dos formas | Raíces y tubérculos, con mayúscula y sin ella | Se unifica la escritura |
| Cultivo mal clasificado | Los cartuchos, que son flores, figuran como raíces y tubérculos | Se reclasifican como flores |
| Cambios de desagregación | Aguacate Hass aparte desde 2020; limón, mandarina y naranja separados de los cítricos desde 2021 | Se suman a aguacate y a cítricos, para conservar series continuas desde 2000 |
| Rendimiento no sumable | Al unir categorías, el rendimiento original deja de valer | Se recalcula como producción sobre hectáreas cosechadas |
| Productos sin producción reciente | 13 productos sin producción entre 2019 y 2023 | Se excluyen |
| Valores repetidos | 20,9 % de las transiciones | Se conservan, y el pronóstico se mide como mejora frente al ingenuo |
| Saltos atípicos | 7,6 % de las transiciones cambian más de 100 % | Se conservan y entran al nivel de confianza de cada producto |
| Producción en cero | 293 registros | Se conservan; un año sin registro dentro de una serie cuenta como 0 toneladas |
| Más área cosechada que sembrada | 152 registros (1,0 %) | No se corrigen |

Los valores repetidos y los saltos se conservan a propósito. No hay forma de saber cuál dato repetido es una copia y cuál es real, ni cuál salto es un error. Corregirlos sería reemplazar una estimación de la fuente por una del equipo. Se prefirió dejarlos y medir sus efectos.

Después de la limpieza quedan 15.019 registros de 57 productos, sin valores nulos en área ni en producción.

## Categorías armonizadas

La fuente cambió su nivel de detalle con los años. Desde 2020 reporta el aguacate Hass aparte del aguacate, y desde 2021 separa el limón, la mandarina y la naranja de los cítricos. Si se dejaran así, el aguacate parecería caer en 2020 y aparecería un cultivo nuevo sin historia. Se sumaron a su cultivo de origen para tener series continuas desde 2000. El costo es que el proyecto no puede decir nada del aguacate Hass por separado, aunque es el que más creció: pasó de 19.466 toneladas en 2020 a 76.167 en 2023.

## Los 13 productos excluidos

De los 57 productos, 13 no registran producción entre 2019 y 2023 y quedan por fuera: anturios, astromelias, cartuchos, ciruela, cúrcuma, heliconias, higuerilla, iraca, manzana, morera, orellana, papa y ulluco. No hay nada reciente que pronosticar en ellos.

Quedan 44 productos. Los 22 con más toneladas se modelan con todos los métodos y suman el 99,9 % de las toneladas de 2019 a 2023 (98,7 % sin caña de azúcar). Los otros 22 solo se pronostican con métodos simples.

## Nivel de confianza por producto

A cada uno de los 44 productos se le asignó un nivel de confianza con reglas fijas:

- Baja, si el producto está en menos de 3 municipios, si la mediana de años por serie es menor que 12 o si más del 50 % de sus valores se repiten.
- Media, si más del 30 % de sus valores se repiten o si más del 15 % de sus transiciones son saltos mayores a 100 %.
- Alta, en los demás casos.

| Grupo | Productos | Alta | Media | Baja |
|---|---|---|---|---|
| Detallados | 22 | 15 | 4 | 3 |
| Simplificados | 22 | 4 | 3 | 15 |
| Total | 44 | 19 | 7 | 18 |

Entre los detallados, tienen confianza media la guanábana, el mango, la guayaba y la papaya, y confianza baja el borojó, la sábila y el ají. El borojó aparece en un solo municipio, Buenaventura, con 26.558 toneladas entre 2019 y 2023. Conviene verificar ese dato en la fuente antes de usarlo en una decisión.

Los pronósticos de los productos de confianza baja deben leerse como escenarios y no como pronósticos independientes.

## Por qué el pronóstico es limitado

Hay pocos datos por serie. Cada serie tiene 24 puntos como máximo, uno por año. Con tan poco, ningún modelo aprende mucho más que "el año que viene se parecerá a este".

Parte de los datos no son mediciones. Los valores repetidos y los saltos por cambios de metodología hacen que la serie refleje también cómo se recogió el dato.

El resultado se ve en la validación. El modelo final empata con el pronóstico ingenuo, que repite el último valor: mejora el MASE en 0,28 % y, sin caña de azúcar, el WAPE en 0,13 %. Darle más capacidad al modelo no cambia nada.

Se comprobó que el empate no sale de los valores repetidos. La correlación entre el porcentaje de valores repetidos de una serie y el error del ingenuo es prácticamente nula (Spearman 0,01, p = 0,72, 717 series).

De ahí salen cuatro advertencias de uso:

- La oferta se entrega en escenarios bajo, base y alto, no como un número.
- Los escenarios son algo estrechos: contienen el valor real en el 76,0 % de los casos, cuando deberían contenerlo en el 80 %.
- El pronóstico de un municipio pequeño no debe leerse aislado. El error relativo crece al bajar el tamaño: el MASE es 2,4 en el tercio de municipios más poblados y 5,5 en el menos poblado. En el total del departamento buena parte de los errores se compensa, como en una encuesta, donde el promedio de muchas respuestas es más confiable que cualquier respuesta suelta.
- Los totales de los escenarios bajo y alto del departamento son extremos. Salen de suponer que todos los municipios y productos se desvían a la vez hacia el mismo lado. Se usan como prueba de estrés.

## Supuestos de los excedentes

El excedente de un producto en un municipio es la oferta pronosticada menos el consumo local estimado, con piso en cero. El consumo local es el consumo por persona de FAOSTAT multiplicado por la población proyectada del DANE. No es ventas ni demanda comprobada: es oferta que supera un consumo estimado.

Estos son sus supuestos:

1. El consumo por persona es el promedio de Colombia, porque FAOSTAT no tiene datos por municipio ni por departamento. Se supone que una persona del Valle come lo mismo que el colombiano promedio.
2. Se usa el consumo de 2023, el último año disponible, para todos los años de 2024 a 2028. Es decir, el consumo por persona se supone constante.
3. Los escenarios de consumo bajo, base y alto multiplican ese consumo por 0,8, 1,0 y 1,2.
4. FAOSTAT reporta varias frutas en una sola categoría. Cuando una categoría cubre varios cultivos del Valle, su consumo se reparte entre ellos según su producción de 2019 a 2023. Por ejemplo, la categoría de otras frutas (60,26 kilos por persona) se reparte entre 21 frutas, y al aguacate le toca el 45,5 %. Las cuotas suman 1 en cada categoría, para no contar el mismo consumo varias veces.
5. Una equivalencia entre un cultivo y un producto de FAOSTAT solo se acepta si los dos están en la misma forma física, fresco contra fresco. Si en el medio hay una transformación, como de caña a panela o de café pergamino a café tostado, y no hay un factor de conversión respaldado, el producto queda pendiente.
6. La población es el total municipal de las proyecciones del DANE con base en el censo de 2018.
7. La caña de azúcar queda por fuera, porque es de uso industrial.

Con la regla del punto 5 quedan 30 productos con consumo definido y 13 pendientes. Diez están pendientes por falta de un factor de conversión: café, caña panelera, cacao, coco, macadamia, sacha inchi, stevia, té, ají y cebolla larga. Tres no son alimentos o no tienen producto equivalente en FAOSTAT: flores y follajes, aromáticas y sábila.

Estos 13 productos pendientes son distintos de los 13 excluidos por no tener producción reciente. Los pendientes sí se pronostican, pero su excedente queda vacío y no entra a la optimización. Se dejó vacío y no en cero porque un cero diría que no hay excedente, y lo cierto es que no se sabe.

La consecuencia es que los excedentes cubren entre el 74 % y el 91 % de la oferta sin caña, según el año y el escenario. En 2024, con oferta y consumo base, el 26 % de la oferta queda sin consumo estimado, casi todo de caña panelera (22,7 %) y café (2,8 %). Esos dos tienen sus propias cadenas de acopio, los trapiches y las cooperativas de caficultores, así que tampoco eran el objetivo de la central.

## Otras limitaciones que afectan la decisión

Tiempos de viaje. No vienen de un mapa de vías. Se aproximan con la distancia en línea recta entre cabeceras municipales, multiplicada por 1,4 y recorrida a 45 km/h. Es medir el viaje con una regla sobre el mapa y sumarle un porcentaje por las curvas: sirve para comparar municipios, pero ignora que hay una cordillera en el medio. Buenaventura y los municipios de ladera pueden quedar más cerca en el modelo que en la carretera.

Precios. El valor de la producción usa precios mayoristas del SIPSA, que son precios de plaza y no de finca. Once productos activos no tienen precio. La caña de azúcar, la caña panelera y el café se valoran con el precio del producto procesado convertido con un factor de rendimiento, que aun así sobreestima el valor en finca.

Mezcla de mercados. Las proporciones entre mercado nacional y exportación (80/20, 50/50 y 20/80) son supuestos para probar la sensibilidad. No son participaciones observadas. Y son lo que más mueve la ubicación de la central.

Acopios satélite. Con tiempos en línea recta, pasar por un acopio nunca acorta el recorrido ni abarata la tonelada. Para el modelo, un acopio es como una escala que no baja el precio del pasaje: da lo mismo en qué ciudad quede. Por eso, cuando los acopios se ubican libremente, el modelo sustenta la ubicación de la central pero no la de los acopios. Tampoco hay capacidades por acopio, porque no hay valores que las respalden.

Capacidad de la central. El radio de 40 km y la captación del 20 % son supuestos del equipo. El tablero permite cambiarlos.

Zonas. Las cinco zonas son contiguas, pero poco homogéneas (silueta de 0,211). Cuatro zonas también serían defendibles.

Cultivos transitorios. El consolidado de cultivos transitorios está descargado, pero no entra al análisis.

## Qué mejoraría los resultados

- Tiempos de viaje por carretera, calculados con las vías de OpenStreetMap.
- Factores de conversión respaldados para el café y la caña panelera, que sacarían del grupo de pendientes al 25 % de la oferta.
- Participaciones reales de exportación por producto.
- Un costo menor por tonelada en el tramo del acopio a la central, o costos fijos y capacidades por acopio, para que el modelo pueda ubicar los acopios.
- Clima por municipio e índices de vegetación, que son las variables externas que hoy no tiene el pronóstico.

## Dónde está el detalle

- Diagnóstico de calidad por serie: `docs/ML_C/calidad_y_limitaciones.md` y `docs/ML_C/diagnostico_modelo.md`.
- Supuestos de excedentes y tabla de equivalencias con FAOSTAT: `docs/arendonc2/supuestos_excedentes.md`.
- Formulación de la optimización: `docs/formulacion_optimizacion.md`.

# Matriz de trazabilidad: de los datos a la decisión

Este documento aplica la matriz de correspondencia de la Sesión 4 del curso Visualización y Comunicación de Datos a las dos preguntas de negocio del proyecto y a la hipótesis que las une. Cada fila conecta la pregunta con la decisión que apoya, con la evidencia que la responde y con la forma en que se muestra en el tablero (pantalla 4. Tablero central). La versión resumida está en la sección 5.2 del informe; aquí va el detalle de los cálculos.

Cliente: Secretaría de Agricultura del Valle del Cauca. Usuarios del tablero: los profesionales de planeación que formulan proyectos de inversión y el secretario o secretaria que los aprueba.

Datos: consolidado agrícola de cultivos permanentes del Valle del Cauca (Gobernación del Valle, portal de datos abiertos), tipo de cultivo Frutales, que incluye el plátano. El tablero promedia las hectáreas sembradas de 2021 a 2023 de cada municipio y cultivo: 71.426 hectáreas en 42 municipios. La caña de azúcar, la caña panelera y el café quedan fuera porque no son fruta ni plátano y tienen cadenas de acopio propias.

Supuestos comunes a las dos preguntas:

- Un municipio queda cubierto si la distancia en línea recta entre su centroide y el de la sede es de 40 km o menos.
- La central recibe el 20 % de la producción de los municipios cubiertos.

## Pregunta 1. Ubicación

| Elemento | Contenido |
|---|---|
| Pregunta de negocio | ¿Qué municipio, como sede, deja más hectáreas de fruta y plátano a 40 km o menos? |
| Decisión asociada | Escoger dos o tres municipios candidatos y ordenar el estudio de costos para esos sitios. |
| Hallazgo exploratorio | El área de fruta y plátano se concentra en el centro (46 %) y el norte (36 %) del departamento. El sur tiene el 12 % y el Pacífico el 6 %. |
| Hipótesis | La sede que alcanza más área está en el centro o el norte. |
| Variables | Hectáreas sembradas por municipio y cultivo (promedio 2021-2023), coordenadas del centroide de los 42 municipios y subregión según la Ordenanza 513 de 2019. |
| Análisis | Para cada uno de los 42 municipios como sede se suman las hectáreas de los municipios a 40 km o menos (distancia haversine). Se ordenan las sedes y se repite el cálculo con radios de 20 a 80 km para ver si el resultado depende del radio. |
| Resultado | Bugalagrande (Centro) alcanza 14 municipios y 37.224 hectáreas, el 52,1 % del Valle. Andalucía (51,6 %) y Zarzal (51,4 %) quedan casi empatadas con ella; la cuarta, La Victoria, baja a 37,8 %. Con cualquier radio entre 20 y 80 km las cinco mejores sedes están en el centro o el norte, aunque la primera cambia entre Trujillo, Zarzal y Bugalagrande. |
| Visualización | Mapa de puntos: un punto por cada 100 hectáreas, color según el cultivo y gris para el área que queda fuera del radio. Al lado, barras con el área alcanzada por cultivo. |
| KPI | Porcentaje del área de fruta y plátano del Valle a 40 km o menos de la sede. |
| Recomendación | Estudiar como zona de ubicación el corredor Zarzal, Andalucía y Bugalagrande, y no un único municipio, porque las tres sedes alcanzan casi la misma área. |

## Pregunta 2. Tamaño

| Elemento | Contenido |
|---|---|
| Pregunta de negocio | Si capta el 20 % de la producción a 40 km, ¿de cuántas toneladas al año debe ser la central para usarse al 100 %? |
| Decisión asociada | Fijar la capacidad de la central, que define el tamaño de la inversión. |
| Hallazgo exploratorio | La producción de fruta y plátano del Valle no crece desde 2013. Entre 2013 y 2023 osciló entre 754.000 toneladas (2020) y 961.000 toneladas (2022), aunque el área cosechada aumentó 26 %. |
| Hipótesis | En el centro o el norte la central necesita cerca del doble de capacidad que en el sur. |
| Variables | Producción en toneladas por municipio entre 2014 y 2023, escenarios bajo, base y alto, porcentaje de captación y capacidad de la central. |
| Análisis | Toneladas captadas = producción de los municipios cubiertos × 20 %. Utilización = toneladas captadas ÷ capacidad, en los tres escenarios. El escenario base es el promedio 2021-2023; el bajo y el alto son el peor y el mejor año de cada municipio entre 2014 y 2023. |
| Resultado | Con sede en Bugalagrande, la central recibiría 86.348 toneladas al año en el escenario base, 58.211 en el bajo y 112.324 en el alto. Una central de unas 86.300 toneladas se usaría al 100 % en el escenario base y al 67 % en el bajo; en el alto necesitaría 30 % más de capacidad, unas 26.000 toneladas. |
| Visualización | Cifra grande con la utilización y una barra de llenado (bullet chart) con la marca del 100 % y las marcas de los tres escenarios. |
| KPI | Utilización de la central: toneladas captadas sobre capacidad instalada. |
| Recomendación | Empezar cerca de 86.000 toneladas al año y crecer por etapas, en vez de construir desde el inicio para el mejor año. Antes de fijar el tamaño hay que confirmar con los productores qué parte de su producción entregarían, porque ese porcentaje mueve la capacidad en proporción directa. |

## Hipótesis que une las dos preguntas

En el centro o el norte, la central alcanza más de la mitad del área y necesita el doble de capacidad que en el sur.

Se contrasta con la secuencia de la Sesión 4: hallazgo, hipótesis, contraste y conclusión. El criterio quedó fijado antes del cálculo (sección 3.1.5 del informe).

| Paso | Contenido |
|---|---|
| Hallazgo | El 82 % del área de fruta y plátano del Valle está en el centro y el norte. |
| Contraste | Se compara la mejor sede del centro o el norte con la mejor sede del sur, con el mismo radio (40 km), la misma captación (20 %) y el escenario base. La hipótesis se sostiene si la primera alcanza más del 50 % del área y necesita al menos el doble de capacidad que la segunda. |
| Evidencia | Bugalagrande alcanza el 52,1 % del área y necesita 86.348 toneladas al año. Vijes, la mejor sede del sur, alcanza el 17,1 % y necesita 45.802 toneladas. Bugalagrande alcanza 3,0 veces el área de Vijes y necesita 1,89 veces su capacidad. |
| Conclusión | La hipótesis se rechaza. La parte de ubicación se cumple: con 40 km la mejor sede del centro-norte pasa del 50 % del área, y con radios de 20 a 80 km la mejor sede sigue en el centro o el norte. La parte de tamaño no se cumple, porque 1,89 veces queda por debajo del doble. La parte de área también depende del radio: con 20 km la mejor sede alcanza el 22 % y con 30 km el 30 %. |

La misma zona tiene además producción por recuperar sin sembrar más área. Si los municipios que alcanza Bugalagrande y rinden menos que el promedio del Valle para el mismo cultivo llegaran a ese promedio, producirían 61.297 toneladas más al año, y con la captación del 20 % la central pasaría de 86.300 a 98.600 toneladas. En la zona de Vijes esa brecha es de 19.684 toneladas. Esta cifra es un valor de referencia del tablero que no se recalcula desde los datos depurados. Muestra cuánta producción hay por recuperar; no prueba que la central la vaya a recuperar.

## Supuestos y límites

- Los escenarios bajo y alto del tablero son el peor y el mejor año entre 2014 y 2023. Los escenarios 2024-2028 del pronóstico están en `data/results/ML_Ce/oferta_escenarios.csv` y se usan en el caso aplicado de la sección 3.4.4 del informe: con el pronóstico base de 2024, que ya incorpora el salto de 2022, la central necesitaría unas 95.800 toneladas.
- El radio de 40 km y la captación del 20 % son supuestos del equipo y deben confirmarse.
- La distancia es en línea recta entre centroides. La optimización usa en cambio la matriz de tiempos de viaje (`data/clean/matriz_tiempos.csv`), con la distancia en línea recta multiplicada por 1,4 y recorrida a 45 km/h.
- El rendimiento se calcula como toneladas sobre hectáreas cosechadas, con el promedio 2021-2023, y siempre se compara contra el mismo cultivo.

Fuente de las cifras: consolidado agrícola de cultivos permanentes del Valle del Cauca, cálculos de Minga Data con el mismo procedimiento del tablero. Se reproducen con `python src/informe/cifras_hipotesis.py`, y las verifica `python src/dashboard/test_tablero_central.py`.

# Fuentes y licencias

Proyecto Minga Data: central de acopio y procesamiento de productos agrícolas en el Valle del Cauca. Versión del 23 de noviembre de 2026.

Este documento lista cada fuente de datos del proyecto: qué aporta, qué variables se usan, qué cubre, dónde está y bajo qué condiciones se puede usar. Incluye las fuentes que estaban en la propuesta y no se usaron, con la razón.

## Fuentes que entran a los modelos

| Fuente | Qué aporta | Variables usadas | Cobertura | Enlace | Licencia o condición de uso |
|---|---|---|---|---|---|
| Gobernación del Valle del Cauca: consolidado agrícola por municipio, cultivos permanentes | La producción que se pronostica. Es la fuente que define el problema | Año, municipio, cultivo, familia, hectáreas sembradas, hectáreas cosechadas, toneladas, rendimiento | 2000 a 2023, 42 municipios, 61 cultivos, 15.282 registros. Descargado el 25 de septiembre de 2026 | https://www.datos.gov.co/d/exfh-span | CC BY-SA 4.0, según los metadatos del conjunto. Atribución: Gobernación del Valle del Cauca |
| DANE: DIVIPOLA, códigos de municipios | Códigos oficiales y coordenadas de las cabeceras, para unir tablas y calcular distancias | Código DANE, nombre, latitud, longitud | 1.122 municipios del país. Descargado el 14 de noviembre de 2026 | https://www.datos.gov.co/d/gdxc-w37w | CC BY-SA 4.0, según los metadatos del conjunto. Atribución: DANE |
| DANE: SIPSA, precios mayoristas | Precio por kilo, para pasar de toneladas a valor | Fecha, producto, mercado, precio promedio por kilo | Enero de 2021 a octubre de 2026, 294.557 precios en 39 archivos mensuales | https://www.dane.gov.co/index.php/estadisticas-por-tema/agropecuario/sistema-de-informacion-de-precios-sipsa | Información pública del DANE. Sus términos de uso piden citar la fuente: "Fuente: Departamento Administrativo Nacional de Estadística: www.dane.gov.co" |
| DANE: proyecciones de población municipal 2020-2035, actualización posterior al COVID-19 | Población de cada municipio, para estimar el consumo local | Código DANE, año, población total | 42 municipios, 2024 a 2028 (210 registros usados). Base: censo de 2018 | https://www.dane.gov.co/files/censo2018/proyecciones-de-poblacion/Municipal/DCD-area-proypoblacion-Mun-2020-2035-ActPostCOVID-19.xlsx | La misma condición del DANE: citar la fuente |
| FAOSTAT: hojas de balance de alimentos (2010-) | Consumo aparente por persona, para estimar el consumo local | Cantidad de alimento disponible, en kilos por persona al año, por producto | Colombia, 2020 a 2023, 273 registros. Descargado el 17 de noviembre de 2026 | https://www.fao.org/faostat/en/#data/FBS | CC BY 4.0, según los términos de FAOSTAT. Atribución: FAO |
| NOAA, Climate Prediction Center: índice ONI | Indicador de El Niño y La Niña. Es la única variable externa del modelo | Anomalía de temperatura por trimestre móvil | 1998 a 2026, 345 trimestres. Consultado el 17 de noviembre de 2026 | https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt | Obra del gobierno de Estados Unidos, de dominio público. Se cita a la NOAA |
| GADM 4.1: polígonos municipales de Colombia | Saber qué municipios son vecinos, para formar zonas contiguas y dibujar los mapas | Polígono de cada municipio, nivel administrativo 2 | 42 municipios del Valle del Cauca, tomados del archivo de Colombia | https://gadm.org/download_country.html | Gratis para uso académico y no comercial. No permite redistribuir los datos ni usarlos comercialmente sin permiso. Ver la nota 2 |

## Fuente de contexto

| Fuente | Qué aporta | Variables usadas | Cobertura | Enlace | Licencia o condición de uso |
|---|---|---|---|---|---|
| ICA: inspecciones en frontera (tablero BI Frontera) | Contexto del comercio exterior agrícola. No entra a ningún modelo | Tipo de comercio, producto, puerto, cantidad, unidad | 12 archivos semestrales de 2021 a 2026, 15.526 registros agregados. Subidos al repositorio el 16 de noviembre de 2026 | https://www.ica.gov.co/servicios_linea/sispap_principal/Estadisticas/RESUMEN-TABLERO-BI-FRONTERA | Sin verificar. El enlace lleva al tablero general del ICA y no a los 12 archivos. Ver la nota 3 |

## Insumo calculado por el equipo

La matriz de tiempos de viaje no viene de ninguna fuente externa. Se calcula con la distancia en línea recta entre cabeceras municipales (coordenadas de la DIVIPOLA), multiplicada por un factor de rodeo de 1,4 y recorrida a 45 km/h. Cubre los 42 municipios y los cinco destinos: Cali, Bogotá, Medellín, el puerto de Buenaventura y el aeropuerto de Palmira. Es una aproximación y está descrita como tal en `docs/calidad_y_limitaciones.md`.

## Fuentes de la propuesta que no se usaron

| Fuente | Para qué se pensó | Qué pasó | Licencia, si se llegara a usar |
|---|---|---|---|
| EVA (Evaluaciones Agropecuarias Municipales, UPRA) | Producción municipal | No se descargó. Los consolidados de la Gobernación ya traen la producción por municipio y cultivo | CC BY 4.0, según la licencia de datos abiertos de la UPRA |
| CEDE, Universidad de los Andes: panel municipal de agricultura y tierra | Extender la serie a otros departamentos | En el repositorio solo está la referencia bibliográfica, no los datos | Uso académico con cita al CEDE. https://doi.org/10.57924/GH6KPE |
| OpenStreetMap | Tiempos de viaje por carretera | No se usaron sus datos de vías. Los tiempos se aproximan con línea recta. Sí se usan sus mapas de fondo en el tablero. Ver la nota 4 | ODbL 1.0, con atribución obligatoria |
| UN Comtrade | Participación de la exportación por producto | Se evaluó y no se incorporó. El comercio exterior se tomó del ICA, que tiene más detalle por puerto | No aplica |
| Gobernación del Valle del Cauca: consolidado de cultivos transitorios | Ampliar el análisis a cultivos de ciclo corto | Está descargado, pero no entra a los modelos. Queda como extensión | CC BY-SA 4.0, igual que el de permanentes |

## Notas sobre las licencias

1. CC BY-SA 4.0 obliga a dar crédito y a compartir las obras derivadas con la misma licencia. Funciona como una receta que se presta con dos condiciones: decir de quién es y, si uno la modifica, prestar la nueva versión en los mismos términos. Las tablas limpias de `data/clean/` que salen del consolidado de la Gobernación y de la DIVIPOLA son obras derivadas. El repositorio no tiene archivo de licencia. Como es público, conviene agregar uno o decirlo en el README.

2. GADM no permite redistribuir sus datos sin permiso. El archivo original no está en el repositorio: lo descarga un script. Pero el repositorio sí guarda dos archivos GeoJSON con las geometrías de los municipios y de las zonas (`data/results/arendonc2/`), que salen de GADM. Queda pendiente decidir si se quitan del repositorio público y se generan con el script, o si se pide permiso a GADM. El uso en el informe y en los mapas sí está permitido: GADM autoriza hacer mapas para publicaciones académicas.

3. Los archivos del ICA no tienen identificada su página exacta de descarga. Quien los bajó debe confirmar de dónde salieron y revisar la licencia en esa página antes de darla por verificada.

4. Atribución de OpenStreetMap. Los mapas del tablero usan los mapas de fondo de OpenStreetMap, y esa licencia exige mostrar el crédito. El texto es: "© colaboradores de OpenStreetMap". El tablero lo muestra en la esquina de cada mapa, y hay que conservarlo en las capturas que vayan al informe o a la presentación. Si más adelante la matriz de tiempos se calcula con las vías de OpenStreetMap, la misma atribución va en el informe y en el repositorio. Las condiciones están en https://www.openstreetmap.org/copyright.

5. Los archivos crudos del SIPSA y del ICA pesan cerca de 750 MB y no están en Git. Se publican como archivo adjunto de un release de GitHub y se descargan con `python src/ML_C/00_descargar_datos.py`, que verifica su huella SHA-256.

## Cómo citar

Las referencias completas, en formato APA 7, están en la sección 8 del informe final. Las fuentes que se actualizan de forma continua (SIPSA, FAOSTAT, ONI e ICA) se citan sin año de publicación y con la fecha en que se recuperaron.

# CENTRAL INTELIGENTE DE ACOPIO Y PROCESAMIENTO DE PRODUCTOS AGRÍCOLAS EN EL VALLE DEL CAUCA

**Minga Data**

*Carlos Guillermo Zúñiga Méndez, Ceyni Paola Beltrán Hoyos, Samuel Gutiérrez Jaramillo, Alejandro Rendón Correa*

## Descripción general de una industria, negocio o problema

La producción agrícola colombiana depende en buena medida de pequeños productores dispersos en zonas rurales y de ladera, que venden volúmenes pequeños a través de intermediarios y con altos costos de transporte. Las centrales de acopio con capacidad de transformación agregan esa oferta, la clasifican y la conservan o transforman según el producto: empaque en fresco con cadena de frío para frutas y hortalizas, pulpas y jugos, trilla y tostión de café, fermentación y secado de cacao, elaboración de panela, harinas y almidones de yuca y plátano, y deshidratados de aromáticas, entre otros. Vender en conjunto les permite a los productores negociar mejores precios. El procesamiento reduce las pérdidas y abre la puerta a mercados más exigentes, incluida la exportación.

Según el consolidado agrícola de la Gobernación, el Valle del Cauca registra producción reciente de 44 cultivos permanentes, distribuidos en sus 42 municipios, con un promedio de cerca de 25,3 millones de toneladas anuales entre 2019 y 2023. El 95 % de ese volumen es caña de azúcar, que se procesa en los ingenios y ya tiene su propia cadena industrial. Sin ella quedan cerca de 1,2 millones de toneladas anuales: alrededor del 70 % son frutales (la fuente incluye el plátano en este grupo), el 24 % caña panelera y el 4 % café.

El departamento tiene además el puerto de Buenaventura, la principal salida de Colombia al Pacífico, y un aeropuerto internacional en Palmira. Pero los polos productivos no siempre coinciden con esas salidas, y ubicar una central de acopio y procesamiento exige equilibrar la cercanía a la producción con la cercanía a los mercados.

## Problema a resolver

La producción agrícola del Valle del Cauca está dispersa, y su patrón cambia según el producto. El café se cultiva en 39 municipios y los tres principales apenas concentran el 29 % de la producción. El maracuyá está en 37 municipios, con el 38 % en los tres primeros. En cambio, el 69 % de la guayaba sale de tres municipios del norte, y productos como el borojó, el chontaduro y el coco se concentran casi exclusivamente en Buenaventura. Las tendencias también difieren: entre 2014 y 2023 la producción de aguacate creció en promedio cerca del 20 % anual, mientras que la de café cayó cerca del 6 % anual y la de caña panelera cerca del 5 % anual.

La dispersión encarece la recolección y deja a los productores con poco poder de negociación. Además, como la oferta crece en unos productos y cae en otros, es difícil comprometer volúmenes estables con la agroindustria o con compradores de exportación.

**Pregunta de negocio: ¿dónde ubicar una central de acopio y procesamiento de productos agrícolas en el Valle del Cauca, y qué red de acopios satélite necesita, para minimizar el costo de recoger la producción y de distribuir los productos a los mercados nacionales e internacionales?**

Para responder, el proyecto construirá un sistema analítico con la serie histórica 2000–2023 de producción municipal de los 44 cultivos permanentes con producción reciente, complementada con los cultivos transitorios.

Los modelos detallados se harán para los 22 productos que tienen datos suficientes y concentran el 99,9 % del volumen (97,9 % si se excluye la caña de azúcar). El sistema cumplirá cinco tareas:

1. Pronosticar la oferta por producto y municipio.
2. Identificar excedentes, comparando la oferta con el consumo local estimado y detectando sobreofertas coyunturales.
3. Agrupar los municipios productores en zonas de acopio contiguas.
4. Proponer rutas de procesamiento adaptadas a cada producto y agrupar los productos por estacionalidad para que compartan líneas de proceso.
5. Evaluar ubicaciones de la central en distintos escenarios de proporción entre mercado nacional y exportación, con base en un análisis de mercado por familia de productos.

La caña de azúcar entrará en el análisis de oferta, pero no en el dimensionamiento de la central, porque ya tiene su propia cadena de transformación. Los resultados se entregarán en un tablero interactivo con mapas.

## ¿Por qué es importante este problema?

Una central de este tipo es una inversión de largo plazo: su ubicación fija por muchos años los costos logísticos y el acceso a mercados de cientos de productores. Ubicarla solo cerca de la producción puede alejarla de las salidas hacia los mercados, y ubicarla solo cerca del puerto puede encarecer la recolección de productos perecederos. El proyecto cuantifica ese equilibrio con datos abiertos.

La central, además, agregaría valor en origen a una producción que en buena parte se vende sin transformar. Los resultados están pensados para quienes pueden tomar esa decisión, como la Secretaría de Agricultura departamental, las asociaciones de productores o los inversionistas privados.

## ¿Cuáles son los conjuntos de datos que considerará para resolver este problema?

- **Dataset 1**: Consolidado agrícola por municipios de los cultivos permanentes del Valle del Cauca. Contiene 15.282 registros de 61 cultivos en 42 municipios entre 2000 y 2023, agrupados en frutales, cultivos tropicales tradicionales, raíces y tubérculos, hortalizas, flores, oleaginosas y aromáticas. Cada registro trae año, municipio (código DANE), cultivo, hectáreas sembradas y cosechadas, producción en toneladas y rendimiento.
- **Dataset 2:** Consolidado agrícola por municipios de los cultivos transitorios del Valle del Cauca, del mismo portal, para incorporar los productos de ciclo corto, como hortalizas y granos.
- **Base de datos:** Evaluaciones Agropecuarias Municipales (EVA) de la UPRA y Panel Municipal del CEDE (Universidad de los Andes), para incorporar la producción de departamentos vecinos y entrenar modelos globales con más series.
- **Archivos:** Sistema de Información de Precios y Abastecimiento del Sector Agropecuario (SIPSA) del DANE, con precios mayoristas y abastecimiento en más de 60 mercados, para estimar la estacionalidad, detectar sobreofertas y caracterizar el mercado nacional.
- **Datos de API 1**: OpenStreetMap y la División Político-Administrativa (DIVIPOLA) del DANE, para obtener coordenadas municipales, red vial, puerto y aeropuerto, y calcular tiempos de viaje.
- **Datos de API 2**: UN Comtrade y estadísticas de exportaciones del DANE, para caracterizar la demanda internacional por familia de productos (frutas frescas y procesadas, café, cacao y sus derivados, panela, harinas y almidones, entre otros).
- **Archivos complementarios:** proyecciones de población municipal del DANE y hojas de balance de alimentos de FAOSTAT, para estimar el consumo local y los excedentes; y el índice ONI de la NOAA, como variable climática (El Niño y La Niña) en los modelos de pronóstico.

## ¿El problema a resolver y los datos son abiertos?

Sí. Todas las fuentes son abiertas y provienen de entidades oficiales colombianas (Gobernación del Valle del Cauca, DANE, UPRA), de organismos internacionales (FAO, Naciones Unidas, NOAA) o de plataformas de acceso libre (OpenStreetMap y el catálogo de datos del CEDE). Los datos están agregados a nivel municipal y no contienen información personal, por lo que no requieren anonimización.

## ¿Qué tipo de restricciones tendrá este proyecto?

- **En datos:** la unidad mínima es el municipio y no el productor individual, por lo que las distancias se calcularán entre cabeceras municipales. Los datos de producción son anuales y llegan hasta 2023. Provienen de estimaciones por consenso, con una proporción importante de valores repetidos de un año a otro y saltos atípicos que requieren un diagnóstico de calidad.

  Hay inconsistencias de categoría que deben armonizarse: los cítricos se desagregan desde 2021, el aguacate Hass aparece por separado desde 2020, el grupo de raíces y tubérculos aparece escrito de dos formas y algunos cultivos están mal clasificados (los cartuchos, que son flores, figuran como raíces y tubérculos). De los 57 productos resultantes, 13 no registran producción entre 2019 y 2023 y se excluyen. De los 44 restantes, 22 tienen muy pocos municipios o años de registro y se estimarán de forma simplificada.

  El dataset de cultivos transitorios aún debe revisarse en estructura y cobertura. El excedente y la proporción exportable dependen de supuestos que se manejarán como escenarios.

- **En código:** el código se publicará en un repositorio público de GitHub para que el análisis se pueda reproducir. Se usarán herramientas de código abierto (Python, pandas, scikit-learn, LightGBM, PyTorch, OR-Tools) y servicios de nube en su capa gratuita.
- **En divulgación:** sin restricciones, porque los datos son públicos. Se citarán todas las fuentes y se respetarán sus licencias, incluida la atribución que exige OpenStreetMap.
- **En alcance:** la central es hipotética. La caña de azúcar se excluye del dimensionamiento de la central porque ya tiene su propia cadena industrial. No se incluyen costos de construcción, diseño de planta, evaluación financiera completa ni requisitos sanitarios, que quedan como trabajo futuro.

  El análisis de mercado se hará por familia de productos y no por producto individual.

- **En tiempo:** el desarrollo se hará en ocho semanas. El ruteo detallado de vehículos y la optimización de la mezcla de productos se abordarán como extensiones si el tiempo lo permite.

# CENTRAL INTELIGENTE DE ACOPIO Y PROCESAMIENTO DE PRODUCTOS AGRÍCOLAS EN EL VALLE DEL CAUCA.

**Minga Data.**

*Carlos Guillermo Zúñiga Méndez, Ceyni Paola Beltrán Hoyos, Samuel Gutiérrez Jaramillo, Alejandro Rendón Correa*

## Problema del negocio:

La producción agrícola del Valle del Cauca se encuentra distribuida entre sus diferentes municipios, con diferencias importantes en los volúmenes producidos, los tipos de cultivos y su comportamiento a lo largo del tiempo. Mientras algunos productos se concentran en unos pocos municipios, otros se encuentran distribuidos en gran parte del departamento. Esta situación representa un reto para la recolección, el almacenamiento y la comercialización de los productos, especialmente cuando se trata de alimentos perecederos que requieren condiciones adecuadas de conservación y transporte.

La dispersión de la producción puede incrementar los costos de transporte y dificultar la consolidación de volúmenes suficientes para abastecer de manera constante a compradores industriales, mercados nacionales y potenciales compradores internacionales. Adicionalmente, las variaciones históricas de la producción hacen más difícil anticipar la oferta disponible, identificar posibles excedentes y planificar el aprovechamiento de los productos agrícolas mediante procesos de transformación que permitan agregarles valor.

En este contexto, se plantea desarrollar una central inteligente de acopio y procesamiento de productos agrícolas que permita analizar la información histórica de producción por municipio y cultivo, con el propósito de identificar las zonas más convenientes para la recolección, estimar la oferta futura y proponer alternativas para la ubicación de una central principal y sus posibles puntos de acopio satélite. Para ello, se tendrán en cuenta factores como la distribución geográfica de la producción, las tendencias de los cultivos, la cercanía entre municipios y las conexiones con los principales mercados nacionales e internacionales.

La pregunta de negocio que orienta el proyecto es: ¿dónde conviene ubicar una central de acopio y procesamiento de productos agrícolas en el Valle del Cauca, y qué red de puntos de acopio complementarios permitiría reducir los costos de recolección y distribución, considerando la disponibilidad de productos y el acceso a los mercados?

La solución se desarrollará mediante técnicas de análisis de datos, aprendizaje automático, procesamiento de información y visualización interactiva. De esta manera, se busca proporcionar una herramienta de apoyo a la toma de decisiones para entidades públicas, asociaciones de productores e inversionistas interesados en fortalecer la cadena de valor agrícola del departamento. El análisis se centrará en los productos que cuenten con información histórica suficiente, considerando la caña de azúcar dentro del estudio de la oferta agrícola, pero excluyéndose del dimensionamiento de la central, debido a que ya cuenta con una cadena industrial de transformación establecida.

## Impacto de la solución:

La solución propuesta permitirá integrar y analizar información agrícola, geográfica y comercial para comprender mejor la distribución de la producción en el Valle del Cauca y evaluar alternativas para organizar su recolección y procesamiento. A partir de los resultados obtenidos, se espera facilitar la identificación de zonas con potencial para establecer puntos de acopio, así como comparar posibles ubicaciones para una central principal, teniendo en cuenta tanto la cercanía a las zonas productoras como el acceso a los mercados de destino.

Entre los principales impactos esperados se encuentran:

- **Mejor planificación logística:** la identificación de zonas productoras y la agrupación de municipios con características similares permitirán plantear alternativas para consolidar la recolección de productos y reducir desplazamientos innecesarios. Esto contribuiría a evaluar opciones de distribución más eficientes y a disminuir los costos logísticos asociados al transporte de la producción.
- **Aprovechamiento de la producción agrícola**: los pronósticos de oferta y la identificación de posibles excedentes permitirán reconocer oportunidades para aprovechar productos que puedan destinarse a procesos de transformación, como la elaboración de pulpas, jugos, harinas, almidones y otros productos agroindustriales, según las características de cada cultivo.
- **Apoyo a la toma de decisiones de inversión:** la comparación de escenarios de ubicación y distribución de la central ofrecerá información útil para entidades gubernamentales, asociaciones de productores e inversionistas privados interesados en desarrollar infraestructura de acopio y procesamiento. El análisis permitirá considerar diferentes condiciones de abastecimiento y acceso a mercados nacionales e internacionales antes de plantear una posible inversión.
- **Mayor conocimiento del comportamiento agrícola regional**: el análisis histórico permitirá identificar tendencias de producción, diferencias entre municipios y variaciones en la disponibilidad de los principales cultivos. Esta información podrá utilizarse para anticipar cambios en la oferta y mejorar la planificación de las actividades de abastecimiento y procesamiento.
- **Acceso claro a la información**: mediante un tablero interactivo con indicadores y mapas, los resultados se presentarán de forma que los usuarios puedan consultar la distribución de los cultivos, comparar municipios y explorar los escenarios evaluados sin necesidad de procesar directamente las bases de datos.

En conjunto, el proyecto busca demostrar cómo el uso de la ciencia de datos puede contribuir a una mejor planificación de la cadena de valor agrícola, conectando la información sobre producción con decisiones relacionadas con la logística, el procesamiento y la comercialización. Aunque la central será una propuesta hipotética y no se implementará físicamente durante el desarrollo del proyecto, los resultados servirán como una base analítica para evaluar oportunidades de desarrollo agroindustrial en el Valle del Cauca.

## Marco Teórico.

**Pronóstico de series de tiempo con pocos datos.** Con datos anuales de 2000 a 2023, ninguna serie supera los 24 puntos, por lo que los modelos locales (uno por serie) solo admiten métodos simples. Se usan como referencia el pronóstico ingenuo (último valor observado), la deriva (crecimiento promedio histórico) y el suavizamiento exponencial ETS con tendencia amortiguada, que da más peso a los años recientes sin extrapolar un crecimiento ilimitado (Hyndman y Athanasopoulos, 2021). Un enfoque alternativo son los modelos globales, entrenados con muchas series a la vez y con producto y municipio como variables, popularizados en competencias como M5 con modelos de árboles de gradiente como LightGBM (Ke et al., 2017; Makridakis et al., 2022). Esto permite aprovechar series de otros departamentos para compensar la corta longitud de las series del Valle.

**Validación y medición del error.** La validación *walk-forward* por año respeta el orden temporal: por ejemplo, se entrena hasta 2018 y se evalúa en 2019–2023. Como los valores repetidos de un año a otro favorecen al pronóstico ingenuo, el desempeño se reporta como mejora relativa frente a él (por ejemplo con MASE o WAPE) y no solo como error absoluto. Además, la cobertura de los intervalos y la coherencia jerárquica (los municipios deben sumar la zona y el departamento) son criterios de calidad.

**Agrupamiento con restricción espacial.** Algoritmos como k-means no garantizan que los grupos sean geográficamente contiguos. La regionalización con restricción espacial, como el agrupamiento jerárquico con una matriz de vecindad entre municipios o los métodos basados en árboles de expansión mínima, produce zonas conexas y homogéneas (Assunção et al., 2006; Duque et al., 2007).

**Localización de instalaciones y optimización multiobjetivo.** El problema de ubicar una central y acopios satélite se formula como un problema de localización de instalaciones con costos de transporte (Farahani y Hekmatfar, 2009). Cuando los objetivos compiten, como el costo de recolección y el de distribución, no existe una única solución óptima sino un conjunto de soluciones no dominadas, la frontera de Pareto (Deb et al., 2002). El proyecto usa esta frontera y el análisis por escenarios para evaluar la robustez de la ubicación, y trata la optimización como una etapa que consume los resultados del aprendizaje automático.

## Descripción de datos a utilizar

**datasets 1:** Consolidado agrícola por municipio de los cultivos permanentes del Valle del Cauca.

**Descripción:**

Serie histórica 2000-2023 con 15,282 registros de 61 cultivos en 42 municipios, publicada en el portal de datos abiertos de la Gobernación del Valle del Cauca. Los cultivos se agrupan en frutales, cultivos tropicales tradicionales, raíces y tubérculos, hortalizas, flores, oleaginosas y aromáticas. Es la base del pronóstico, el agrupamiento y la oferta de la optimización.

**Variables:**

Año, municipio (código DANE), cultivo, grupo de cultivo, hectáreas sembradas, hectáreas cosechadas, producción (toneladas) y rendimiento. Los nombres exactos de las columnas se confirmará con el archivo.

**Anonimización.**

SI___ | NO X

(datos agregados a nivel municipal, sin información personal).

**¿Esta base de datos es pública?**

SI X | NO___

**datasets 2:** Consolidado agrícola por municipios de los cultivos transitorios del Valle del Cauca.

**Descripción:**

Del mismo portal, incorpora productos de ciclo corto como hortalizas y granos. Se usará para añadir variables como extensión del primer dataset.

**Variables:**

Año, municipio, cultivo, área, hectáreas sembradas, hectáreas cosechadas, producción y rendimiento.

**Anonimización.**

SI___ | NO X

(datos agregados a nivel municipal, sin información personal).

**¿Esta base de datos es pública?**

SI X | NO___

## Fuentes complementarias.

| Fuente. | Uso en el proyecto. | Variables principales. |
|---|---|---|
| EVA (UPRA) y Panel Municipal CEDE. | Series de otros departamentos para entrenar el modelo global. | Año, municipio, cultivo, área, producción. |
| SIPSA (DANE). | Precios mayoristas para ponderar por valor; abastecimiento mensual para estacionalidad como indicadores de mercado. | Fecha, producto, mercado, precio, cantidad. |
| DIVIPOLA (DANE) y OpenStreetMap. | Coordenadas municipales, red vial, puerto, aeropuerto y tiempos de viaje. | Código DANE, coordenadas, red vial. |
| Proyecciones de población (DANE) y balances de alimentos (FAOSTAT). | Consumo local estimado y excedentes, tratados como escenario. | Población municipal, consumo per cápita. |
| Índice ONI (NOAA). | Variable climática (El Niño y La Niña) en el pronóstico. | Fecha, índice ONI. |
| Un comtrade y exportaciones DANE. | Caracterización de la demanda internacional para los escenarios de exportación. | Producto, país, valor, volumen |

## Calidad y limitaciones de los datos.

La unidad mínima es el municipio, por lo que las distancias se calculan entre cabeceras municipales. Los datos son anuales, llegan hasta 2023 y provienen de estimaciones por consenso, con valores repetidos de un año a otro y saltos atípicos que requieren un diagnóstico de calidad. Hay inconsistencias de categoría que deben armonizarse: los cítricos se desagregan desde 2021, el aguacate Hass aparece por separado desde 2020, el grupo de raíces y tubérculos aparece escrito de dos formas y algunos cultivos están mal clasificados (los cartuchos, que son flores, figuran como raíces y tubérculos). De los 57 productos resultantes, 13 no registran producción entre 2019 y 2023 y se excluyen; de los 44 restantes, 22 tienen suficientes municipios y años para el modelado detallado (99,9 % del volumen; 97,9 % sin caña de azúcar) y 22 se estiman de forma simplificada.

## Metodología a emplear.

Se usa CRISP-DM, adaptado a las dos etapas del proyecto.

1. **Entendimiento del negocio.** Se definen la pregunta de decisión, la frontera entre el aprendizaje automático y la optimización, los usuarios (Secretaría de Agricultura, asociaciones de productores, inversionistas) y los criterios de éxito.
2. **Entendimiento de los datos.** Se examinan la integridad, extensión y estado general de los conjuntos de datos mediante un diagnóstico exploratorio, registrando observaciones sobre registros duplicados, atipicidades y discrepancias en la clasificación de las variables.
3. **Preparación de los datos.** Se armonizan las categorías, se excluyen los productos sin producción reciente, se separan los 22 productos de modelado detallado de los de estimación simplificada, se calcula la ponderación por valor con precios SIPSA y se construyen las coordenadas y la matriz de tiempos de viaje.
4. **Modelado.** (a) Pronóstico de oferta por producto y municipio con baselines (ingenuo, deriva, ETS amortiguado) y un modelo global con producto, municipio, ONI y series de otros departamentos, con intervalos o escenarios. (b) Excedentes como oferta menos consumo local estimado, tratados como escenario. (c) Agrupamiento con restricción espacial para las zonas de acopio. (d) Optimización multiobjetivo para la ubicación de la central y los acopios satélite.
5. **Evaluación.** El pronóstico se valida con walk-forward por año (entrenar hasta 2018, evaluar 2019–2023) y se reporta la mejora sobre el ingenuo, la cobertura de intervalos y la coherencia entre municipio, zona y departamento. Las zonas se evalúan por contigüidad y homogeneidad. La optimización se evalúa por la frontera de Pareto y por la estabilidad de la ubicación entre escenarios de oferta, excedente y mezcla nacional/exportación; si la ubicación cambia, eso se reporta como resultado.
6. **Despliegue.** Un tablero interactivo con mapas, publicado en la nube (capa gratuita) y alimentado por un pipeline reproducible con el código en un repositorio público de GitHub.

## Lista de actividades a realizar en el proyecto para lograr el objetivo:

- Definición del problema y de la frontera ML/optimización.
- Definición de los criterios de éxito
- Adquisición de datos y armonización de categorías.
- Diagnóstico de calidad y análisis exploratorio.
- Ponderación por valor con precios SIPSA y construcción de la matriz de tiempo de viaje.
- Arquitectura de referencia preliminar y selección de tecnologías.
- Baselines de pronóstico y esquema de validación walk-forward.
- Modelo global de pronóstico con intervalos o escenarios.
- Cálculo de excedentes como escenarios.
- Agrupamiento con restricción espacial.
- Optimización multiobjetivo y análisis de escenarios.
- Visualización de datos y analítica visual (tablero con mapas).
- Despliegue en la nube, validación y pruebas.
- Difusión y comunicación del proyecto.

Cronograma por semana (Octubre y Noviembre).

| | W1 | W2 | W3 | W4 | W5 | W6 | W7 | W8 |
|---|---|---|---|---|---|---|---|---|
| Definición del problema y adquisición de datos. | x | | | | | | | |
| Armonización y diagnóstico de calidad. | x | x | | | | | | |
| EDA y ponderación por valor (SIPSA). | | x | | | | | | |
| Baselines y validación walk-forward. | | | x | | | | | |
| Modelo global con intervalos o escenarios. | | | | x | | | | |
| Agrupamiento espacial y excedentes. | | | | | x | | | |
| Optimización multiobjetivo y escenarios. | | | | | | x | | |
| Tablero con mapas y despliegue en nube. | | | | | | | x | |
| Validación final, documentación y difusión. | | | | | | | | x |

**Extensiones si el tiempo lo permite:** rutas de procesamiento por producto, agrupamiento de productos por estacionalidad, análisis de mercado por familia y ruteo detallado de vehículos.

## Métodos, Modelos, aplicación, tecnología en cada una de las materias del proyecto integrador 1

*Modelos/técnicas/tecnologías a usar:*

*Curso 1: SI7009/SI6002 Aprendizaje Automático*

Es el núcleo del proyecto. Se aplican baselines de series de tiempo (ingenuo, deriva, ETS con tendencia amortiguada) y un modelo global de pronóstico con LightGBM, entrenado con todas las series y con producto, municipio, ONI y series de las EVA como variables. Se generan intervalos o escenarios de oferta. Se aplica agrupamiento jerárquico con matriz de vecindad para definir zonas de acopio contiguas. La validación es walk-forward y la mejora se mide frente al pronóstico ingenuo. La optimización (OR-Tools) se usa como etapa posterior que consume los resultados de estos modelos. Tecnologías: Python, pandas, scikit-learn, statsmodels y LightGBM.

*Modelos/técnicas/tecnologías a usar:*

*Curso 2: SI7006/SI6003 Almacenamiento y Procesamiento de grandes datos*

Se diseña un pipeline reproducible para ingerir y transformar las fuentes (Gobernación, EVA, SIPSA, DIVIPOLA, OSM, FAOSTAT, NOAA, Comtrade), con almacenamiento por capas (datos crudos, depurados y resultados) y procesamiento por lotes de las series. El pipeline se despliega en servicios de nube en su capa gratuita y el código se publica en GitHub para que el análisis se pueda reproducir.

*Modelos/técnicas/tecnologías a usar:*

*Curso 2: SI7007/SI6004 Visualización de datos*

Se construye un tablero interactivo con mapas que permite consultar la oferta pronosticada por producto y municipio con sus intervalos, ver las zonas de acopio, explorar los escenarios de oferta, excedente y mercado, y comparar las ubicaciones candidatas mediante la frontera de Pareto. Los gráficos priorizan la comunicación de la incertidumbre para quienes toman la decisión.

## Consideraciones requeridas para el desarrollo del proyecto:

- **Condiciones sobre los datos:** series anuales cortas (máximo 24 puntos), estimaciones por consenso con valores repetidos y saltos atípicos, datos hasta 2023, categorías por armonizar y distancias calculadas entre cabeceras municipales. El dataset de transitorios debe revisarse antes de incorporarlo.
- **Condiciones sobre la tecnología:** herramientas de código abierto (Python, pandas, scikit-learn, LightGBM, OR-Tools) y servicios de nube en su capa gratuita.
- **Restricciones:** la central es hipotética; no se incluyen costos de construcción, diseño de planta, evaluación financiera completa ni requisitos sanitarios. El tiempo es de ocho semanas, y las rutas de procesamiento y el análisis de mercado por familia son extensiones.
- **Riesgos:** (1) un pronóstico a diez años no se sostiene con 24 datos anuales; se mitiga con intervalos y escenarios y mostrando si la ubicación cambia entre ellos. (2) El supuesto de excedentes (consumo per cápita nacional × población municipal) es fuerte; se trata como escenario y se mide cuánto mueve la ubicación. (3) Los valores repetidos hacen que el pronóstico ingenuo parezca muy bueno; se reporta la mejora relativa. (4) El alcance puede exceder el tiempo; se prioriza la cadena pronóstico, zonas y ubicación.
- **Propiedad intelectual y derechos de autor:** los datos son públicos y de acceso libre. Se citarán todas las fuentes y se respetarán sus licencias, incluida la atribución que exige OpenStreetMap. No hay restricciones de divulgación.

## Referencias bibliográficas

- Assunção, R. M., Neves, M. C., Câmara, G., y Freitas, C. da C. (2006). Efficient regionalization techniques for socio-economic geographical units using minimum spanning trees. *International Journal of Geographical Information Science, 20*(7), 797–811.
- Deb, K., Pratap, A., Agarwal, S., y Meyarivan, T. (2002). A fast and elitist multiobjective genetic algorithm: NSGA-II. *IEEE Transactions on Evolutionary Computation, 6*(2), 182–197.
- Duque, J. C., Ramos, R., y Suriñach, J. (2007). Supervised regionalization methods: A survey. *International Regional Science Review, 30*(3), 195–220.
- Farahani, R. Z., y Hekmatfar, M. (Eds.). (2009). *Facility location: Concepts, models, algorithms and case studies.* Physica-Verlag.
- Hyndman, R. J., y Athanasopoulos, G. (2021). *Forecasting: Principles and practice* (3.ª ed.). OTexts. https://otexts.com/fpp3/
- Ke, G., Meng, Q., Finley, T., Wang, T., Chen, W., Ma, W., Ye, Q., y Liu, T.-Y. (2017). LightGBM: A highly efficient gradient boosting decision tree. *Advances in Neural Information Processing Systems, 30.*
- Makridakis, S., Spiliotis, E., y Assimakopoulos, V. (2022). M5 accuracy competition: Results, findings, and conclusions. *International Journal of Forecasting, 38*(4), 1346–1364.
- Wirth, R., y Hipp, J. (2000). CRISP-DM: Towards a standard process model for data mining. *Proceedings of the 4th International Conference on the Practical Applications of Knowledge Discovery and Data Mining.*

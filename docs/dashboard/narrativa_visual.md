# Narrativa visual del tablero (dashboard)

Este documento describe la narrativa que sigue cada pantalla del tablero Streamlit de MingaData_PI, los títulos declarativos, los subtítulos, las unidades de medida y los callouts (alertas informativas). Se mantiene la estructura de cinco pantallas existentes y se añade una pantalla inicial "0. Resumen".

## Principio rector

Cada pantalla responde una pregunta de negocio con un **título declarativo** (lo que se ve), un **subtítulo** (para qué sirve y con qué datos) y **unidades explícitas** en ejes, métricas y tablas. Los callouts comunican advertencias de calidad de datos sin ocultar la información.

## Pantalla 0 — Resumen (landing, nueva)

**Título declarativo:** "MingaData — Resumen ejecutivo: central de acopio Valle del Cauca"

**Subtítulo:** "Estado de la oferta pronosticada 2024-2028, exposición logística con y sin modelo, y acceso rápido a las pantallas de detalle. Datos: Gobernación del Valle, DANE, SIPSA, ICA, NOAA, FAOSTAT, OpenStreetMap."

**Contenido:**
- KPIs principales: productos modelados, municipios cubiertos, horizonte de pronóstico, años de historial, exposición sin modelo vs con modelo (t·min y COP), reducción de exposición.
- Callout de alcance: "El tablero soporta decisiones de planificación (volumen, ubicación, capacidad). No es un sistema de trading ni de precios."
- Tarjetas de navegación con drill-down: "Oferta por producto y municipio", "Zonas de acopio", "Ubicación de central y satélites", "Tablero central de cobertura".
- Descarga del resumen en CSV.

**Unidades:** toneladas (t), millones de toneladas × minutos (M t·min), miles de millones de COP, años.

## Pantalla 1 — Oferta por producto y municipio

**Título declarativo:** "Pantalla 1 - Oferta por Producto y Municipio"

**Subtítulo:** "Pronóstico de oferta agrícola con intervalos de confianza (bajo/base/alto) para el horizonte 2024-2028, por producto y municipio del Valle del Cauca."

**Filtros:** producto (selectbox), municipio (selectbox dependiente del producto).

**Gráfico principal:** serie histórica (2000-2023, toneladas) + pronóstico base (línea desmarcada) + banda bajo-alto (sombreada). Eje Y en toneladas, eje X en año.

**Tabla de pronóstico:** año, oferta_bajo, oferta_base, oferta_alto (t), con formato de miles y separador de miles.

**Callouts:**
- "No hay datos de oferta para este producto en el año seleccionado" (cuando aplica).
- Cobertura de intervalos cercana al 76 % (nominal 80 %).

**Drill-down:** al cambiar producto se actualizan los municipios disponibles; al cambiar municipio se actualiza la serie y el pronóstico.

## Pantalla 2 — Zonas de acopio

**Título declarativo:** "Pantalla 2 - Zonas de Acopio"

**Subtítulo:** "Mapa de los 42 municipios del Valle del Cauca coloreados por su oferta base pronosticada, por producto y año. El agrupamiento en zonas de acopio depende de la tarea de zonas; mientras tanto se muestran municipios individuales."

**Filtros:** producto, año.

**Mapa:** CircleMarker por municipio, radio e intensidad de color proporcionales a la oferta base (t). Popup con nombre, código DANE y valor. Destinos logísticos como marcadores azules.

**Resumen por municipio:** tabla ordenada descendente por oferta, con métricas de oferta total, oferta promedio y cantidad de municipios con producción.

**Unidades:** toneladas (t) en eje, popup y tabla.

## Pantalla 2b — Zonas de acopio (vecindad + agrupamiento espacial)

**Título declarativo:** "Pantalla 2b - Zonas de Acopio (vecindad + agrupamiento espacial)"

**Subtítulo:** "Zonas de acopio espacialmente conexas (contigüidad Queen + Ward con restricción de conectividad). Los centros de zona son referencias (tiempos ponderados por oferta), no la ubicación óptima del modelo de optimización."

**Filtros:** año, escenario de optimización.

**Mapa:** polígonos de zona (GeoJSON, si existen) y municipios como puntos coloreados por zona; centros de zona con radio mayor.

**Tabla de volúmenes:** zona, volumen nacional, volumen exportación, excedente por zona, cobertura de oferta (%). Advertencia de cobertura parcial cuando < 100 %.

**Descarga:** volúmenes del escenario y zonas.csv.

**Callout de advertencia:** cobertura parcial de consumo (productos sin equivalencia de unidad quedan con excedente desconocido).

## Pantalla 3 — Ubicación de central y acopios satélite (logística)

**Título declarativo:** "Pantalla 3 - Ubicacion de Central y Acopios Satelite (logística)"

**Subtítulo:** "Minimiza el costo logístico (toneladas × minutos) de ubicar una central y sus acopios satélite, usando excedentes proyectados y OR-Tools con flujo satélite→central explícito."

**Parámetros:** año, oferta (base/bajo/alto), consumo, mezcla nacional/exportación, configuración territorial (libre/zonas), λ, parámetros del solver.

**Botón explícito:** "Calcular optimización" (no se resuelve al cargar).

**Resultados:** mapa con central (roja), satélites (naranjas) y municipios (azules); líneas de asignación municipio→satélite y satélite→central. Métricas de costo A1, A2, B, A, B, objetivo. Diagnóstico del solver (estado, objetivo, mejor cota, brecha, tiempo).

**Comparación libre vs zonas:** tabla lado a lado con central, costos, objetivo, brecha y tiempo por modo.

**Frontera de Pareto:** gráfico A vs B con soluciones no dominadas del barrido de λ.

**Estabilidad por nivel de oferta:** tabla con oferta baja/base/alta para el año seleccionado; callout de ubicación estable o variable.

**Unidades:** t·min en costos, toneladas en volumen.

## Pantalla 4 — Tablero central de acopio

**Título declarativo:** "Pantalla 4 - Tablero central de Acopio (HTML)"

**Subtítulo:** "Vista de cobertura histórica (promedio 2021-2023): qué área y producción alcanza cada sede. No reemplaza la pantalla 3, que minimiza el costo logístico con el pronóstico."

**Contenido:** HTML embebido del tablero central con mapa de puntos y respuestas por sede.

**Capa:** "recuperable" es una referencia del análisis original, no recalculada desde el CSV.

**Unidades:** toneladas y hectáreas (referencia histórica).

## Unidades y convenciones usadas en todo el tablero

| Magnitud | Unidad | Formato ejemplo |
|---|---|---|
| Producción / oferta | toneladas | 251.724 t |
| Exposición logística | t·min | 450,71 M t·min |
| Costo logístico (supuesto) | COP | 112,68 miles de millones COP |
| Año | año | 2024 |
| Código DANE | texto de 5 dígitos | 76113 |
| Cobertura | porcentaje | 76,0 % |

**Nota de datos:** los cod_dane se conservan siempre como texto para no perder ceros iniciales. Los datos se leen en Parquet si existen y caen a CSV si no.

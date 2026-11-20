# Mejoras de usabilidad del tablero (dashboard)

Este documento describe los cambios de usabilidad aplicados a `src/dashboard/app.py`: una nueva pantalla de aterrizaje, KPIs, navegación, títulos declarativos, subtítulos, unidades, callouts, drill-down y descargas filtradas. Se conserva intacta la estructura de las cinco pantallas existentes y las cadenas que exige `test_tarea3.py`.

## Cambio principal: pantalla "0. Resumen" como punto de entrada

- Se añade `"0. Resumen"` como primera opción del `st.sidebar.radio`.
- El índice por defecto cambia de `4` (Tablero central) a `0` (Resumen), de modo que el usuario aterriza primero en el resumen ejecutivo antes de entrar al detalle.
- El resumen muestra KPIs globales (productos, municipios, horizonte, años de historial, exposición con y sin modelo) y tarjetas de navegación con drill-down a cada pantalla.

## Navegación

- Sidebar con título "🌱 MingaData", subtítulo "Central de Acopio y Procesamiento" y ubicación "Valle del Cauca - Proyecto Integrador 1".
- Radio de selección con las seis opciones: `0. Resumen`, `1. Oferta`, `2. Zonas`, `2b. Zonas de acopio`, `3. Ubicacion`, `4. Tablero central`.
- Los filtros globales (año de pronóstico, escenario de oferta) se muestran en pantallas 1, 2, 2b y 3; en la pantalla 4 se indica que usa vista histórica 2021-2023 y no los filtros de pronóstico.
- Panel "Estado de los datos" con conteos de productos, municipios y años de pronóstico.

## Títulos declarativos y subtítulos

Cada pantalla tiene un `st.title` declarativo seguido de un `st.markdown` de subtítulo que explica qué se muestra, para qué sirve y con qué datos:

| Pantalla | Título (conservado) | Subtítulo |
|---|---|---|
| 0 | Resumen ejecutivo | Estado de la oferta pronosticada 2024-2028, exposición logística y acceso a pantallas de detalle |
| 1 | Pantalla 1 - Oferta por Producto y Municipio | Pronóstico de oferta agrícola con intervalos bajo/base/alto, horizonte 2024-2028 |
| 2 | Pantalla 2 - Zonas de Acopio | Mapa de municipios coloreados por oferta base, por producto y año |
| 2b | Pantalla 2b - Zonas de Acopio (vecindad + agrupamiento espacial) | Zonas espaciales conexas; centros de zona son referencias, no ubicación óptima |
| 3 | Pantalla 3 - Ubicacion de Central y Acopios Satelite (logística) | Minimiza costo logístico (t·min) con OR-Tools, flujo satélite→central explícito |
| 4 | Pantalla 4 - Tablero central de Acopio (HTML) | Cobertura histórica promedio 2021-2023 por sede |

## Unidades

Todas las métricas numéricas llevan unidad explícita:
- Producción y oferta: toneladas (`t`), formato `{:,.0f} t`.
- Exposición logística: `t·min`, agregado en millones (`M t·min`).
- Costo en COP con supuesto 250 COP/(t·min), en miles de millones.
- Cobertura: porcentaje con dos decimales.
- Código DANE: texto de 5 dígitos, con ceros iniciales preservados.

## Callouts (alertas informativas)

Se usan `st.info`, `st.warning`, `st.success` y `st.error` según la severidad:

- `st.warning` cuando falta cobertura de consumo (< 100 %) o no hay datos para un producto/año.
- `st.error` cuando faltan archivos de entrada o el solver no encuentra solución.
- `st.info` para explicar alcance, supuestos y que la optimización se ejecuta bajo demanda.
- `st.success` cuando la ubicación es estable en todos los niveles de oferta.

## Drill-down

- **Zona → municipios:** en pantalla 2b, el usuario selecciona año y escenario; la tabla muestra volúmenes por zona y la asignación municipio → zona. Al cambiar el escenario se recalculan los volúmenes.
- **Producto → municipios:** en pantalla 1, al seleccionar un producto se actualizan los municipios disponibles; al seleccionar un municipio se actualizan la serie histórica y el pronóstico.
- **Año → escenarios:** en pantallas 2, 2b y 3, el año seleccionado condiciona los escenarios y ofertas disponibles.

## Descargas filtradas

- Pantalla 2b: `⬇️ Descargar volúmenes de este escenario (CSV)` — CSV del escenario y año seleccionados.
- Pantalla 2b: `⬇️ Descargar zonas.csv` — tabla completa de asignación municipio → zona.

## Conservación de requisitos de test_tarea3.py

Se preservan exactamente:
- `def pantalla_oferta()`
- `def pantalla_zonas()`
- `def pantalla_ubicacion()`
- Las cadenas `"Pantalla 1 - Oferta"`, `"Pantalla 2 - Zonas"` y `"Pantalla 3 - Ubicacion"` en los `st.title`.
- La compilación sin errores de sintaxis de `app.py`.

## Pantallas sin cambios funcionales

Las pantallas 1, 2, 2b, 3 y 4 conservan su lógica original de cargas, mapas, gráficos y controles. Solo se añaden títulos declarativos, subtítulos, unidades y callouts donde faltaban, sin alterar su comportamiento.

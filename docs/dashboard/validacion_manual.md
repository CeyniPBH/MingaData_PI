# Validación del rediseño frente al manual

Manual de referencia: "Dashboards para responder preguntas de negocio" (Mauricio Arias
Correa). Estado: **cumple**, **no cumple** o **pendiente**, con evidencia concreta.

La **prueba de cinco segundos** requiere una persona real; no se realizó en este entorno,
así que queda **pendiente**. La verificación visual a 1440 × 900 también queda pendiente de
una sesión con navegador (ver `docs/dashboard/capturas/README.md`).

| Regla del manual | Estado | Evidencia |
|---|---|---|
| Rama nueva desde main actualizado (`tablero-manual`) | Cumple | Rama creada tras `git merge --ff-only origin/main`; trabajo previo conservado en ramas remotas. |
| No modificar `data/`, `src/informe/`, `src/ML_C/`, `src/arendonc2/`, `src/optimizacion/`, API | Cumple | `git status`: solo `src/dashboard/{app,utils,cobertura}.py` y `tests/dashboard/`. |
| Conservar nombres de navegación (0–4) | Cumple | `pantalla = st.sidebar.radio([...])` intacto; test `test_navegacion_conserva_pantallas`. |
| Pantalla 0 = resumen ejecutivo; demás = detalle | Cumple | `_pantalla_resumen_impl`; pantallas 1-4 conservan su función. |
| Distinguir cobertura histórica, oferta pronosticada, excedentes, optimización | Cumple | Captions por visual; P4 advierte alcance distinto; pantalla 3 vs 4 diferenciadas. |
| Título dinámico "[Sede] cubre [X] % … [Y] t/año captables al 20 %" | Cumple | `cobertura.titulo_resumen`; AppTest: "Bugalagrande cubre 52,1 % … 86.348 t". |
| Pregunta principal y subtítulo (base/radio/captación) | Cumple | Texto en el encabezado del resumen. |
| Distancia geográfica, no vial | Cumple | Caption explícita; `cobertura` usa haversine. |
| Filtro de sede (42 municipios), por defecto mayor cobertura calculada | Cumple | `st.sidebar.selectbox` con `index=ranking.iloc[0]`. |
| Radio y captación fijos en el resumen; explorables en pantalla 4 | Cumple | Constantes en `cobertura`; caption remite a la pantalla 4. |
| No afirmar actualización automática anual | Cumple | Caption: "No hay un proceso de actualización automática anual". |
| Cuatro indicadores de decisión con base 2021-2023 | Cumple | 4 tarjetas: área %, puesto, volumen captable, razón vs sur. |
| Tarjeta 1: pp frente al referente del sur | Cumple | `fmt_puntos(pct_sede − pct_sur)`. |
| Tarjeta 2: distancia al líder o siguientes; empates documentados | Cumple | Caption de ventaja/distancia; empates en `fichas_kpi.md`. |
| Tarjeta 3: t/año y comparación pertinente | Cumple | Muestra sede y referente del sur. |
| Tarjeta 4: razón y los dos valores que la originan | Cumple | Caption con ambos volúmenes. |
| No llamar KPI sin objetivo/umbral/responsable; documentar clasificación | Cumple | Caption + `fichas_kpi.md`. |
| No rojo/verde ni flechas de tendencia entre sedes | Cumple | `st.metric` sin `delta`; AppTest confirma delta vacío. |
| Cuadrícula 2×2 con pregunta, unidades, comparación y respuesta de una frase | Cumple | `st.columns(2)` × 2; cada visual con caption y `st.info`. |
| P1 barras horizontales, top 10 + sede + sur, azul/gris, umbral 50 % rotulado | Cumple | `_visual_p1`; línea punteada "umbral de hipótesis 50 %". |
| P1 reconocer diferencias pequeñas sin significancia | Cumple | Respuesta P1 para líder con diferencia < 2 pp. |
| P2 bajo/base/alto, línea base, % vs base, explicar extremos municipales | Cumple | `_visual_p2`; respuesta sin probabilidades ni "mejor/peor año observado". |
| P2 no afirmar operación al 100 % demostrada | Cumple | Respuesta: "El 100 % es la definición de la base…". |
| P3 100 % apiladas por cultivo, piña destacada, % en toneladas | Cumple | `_visual_p3`; piña en color propio; eje "% de toneladas". |
| P3 producción, superficie, t/ha sembrada, sin piña | Cumple | Expander con tabla; caption aclara "no rendimiento agronómico". |
| P3 adaptable a cualquier sede; si es el sur, indicarlo | Cumple | `es_referente_sur` → nota específica. |
| P4 frecuencia por municipio, resaltar sede, 0 si no aparece | Cumple | `_visual_p4`; respuesta "no implica inviable". |
| P4 años, nº de escenarios, separar sin solución, no probabilidades | Cumple | Caption + respuesta; `cobertura.frecuencia_centrales`. |
| P4 no afirmar mezcla como factor sin comparar entradas iguales | Cumple | Caption: "describir, no afirmar causa". |
| P4 filtro cambia solo resaltado, no recalcula universo | Cumple | Respuesta lo indica; AppTest confirma sin nuevos solves. |
| Secciones plegadas: pronóstico/exposición y API/BD | Cumple | `_resumen_detalle_pronostico`, `_resumen_detalle_api`. |
| Exposición sin caña y referencia reconciliadas | Cumple | 100,08 → 69,69 M t·min, −30,4 %; ingenuo −32 %. |
| Valoración monetaria solo si reconciliada; denominarla valoración de exposición | Cumple | Caption: anualización ÷ 5, factor 250 COP/(t·min), "no ahorro realizado". |
| Conservar API/DuckDB, formulario, manejo de fallos, modelo real | Cumple | Sección API conservada; identifica /predict como LightGBM. |
| No cambiar contrato de /predict | Cumple | No se tocó `src/api/`. |
| No presentar LightGBM como modelo final combinado | Cumple | Caption lo aclara. |
| Descarga del resumen con filtros, unidades, periodos, supuestos | Cumple | `_resumen_descarga`: CSV con columnas unidad/periodo/supuesto. |
| Retirar botones "Ir a Pantalla…" que no navegan | Cumple | Eliminados del resumen. |
| Quitar nota "depende de la tarea de Alejandro" | Cumple | Pantalla 2 reescrita. |
| Sustituir "modelo de Samuel" por referencia funcional | Cumple | "optimización de la pantalla 3". |
| Diferenciar títulos de oferta municipal y zonas de acopio | Cumple | Pantalla 2: "Oferta municipal pronosticada"; 2b: "Zonas de acopio por agrupamiento espacial". |
| Sustituir 38,2 % / "22 %–38 %" solo tras reproducir el cálculo del informe | Cumple | Reemplazado por 30,4 % reproducido con `cobertura.exposicion_sin_cana`. |
| Conservar advertencias de cobertura parcial, GADM, capacidades | Cumple | Pantallas 2b y 3 sin cambios en esas advertencias. |
| `src/dashboard/cobertura.py` con cobertura, ranking, referente, volúmenes, composición | Cumple | Módulo creado; reutiliza `tablero_central` y método de `cifras_hipotesis`. |
| Extraer payload con mecanismo validado, no por posiciones del HTML | Cumple | Usa `PATRON_DATOS`/`generar_html_tablero`, verificado por `test_tablero_central.py`. |
| Función de exposición sin caña en `src/dashboard/` equivalente al informe | Cumple | `cobertura.exposicion_sin_cana`; test de equivalencia. |
| Formatos colombianos en `utils.py` | Cumple | `fmt_pct`, `fmt_toneladas`, `fmt_millones_cop`, `fmt_puntos`, `fmt_razon`. |
| No ejecutar optimizador al cambiar la sede del resumen | Cumple | `test_cambiar_sede_no_ejecuta_optimizador`. |
| Resumen funciona si falla la API | Cumple | `test_resumen_funciona_si_falla_la_api`. |
| Paleta del manual (azul #002855, grises, referencia #18212D) | Cumple | Constantes `AZUL`, `GRIS_CTX`, `GRIS_CLARO`, `REFERENCIA`. |
| Pruebas de cálculo y comportamiento | Cumple | `tests/dashboard/test_resumen.py` (19) y `test_resumen_app.py` (5). |
| Panel de hipótesis pantalla 4: título "3,0 veces el área … 1,9 veces … no alcanza el doble" | Cumple | `tComp` en el HTML ahora se genera de los datos: para Bugalagrande vs Vijes produce "Bugalagrande alcanza 3,0 veces el área de Vijes y presenta 1,9 veces su volumen captable: no alcanza el doble". JS verificado con `node --check`. |
| Figura 10 actualizada porque quedó afectada | Pendiente | El título del panel de hipótesis cambió, así que la Figura 10 (captura de la pantalla 4 con la hipótesis desplegada) **debe recapturarse** con la configuración de `docs/informe/README.md` (1440 px, Bugalagrande, 40 km, 20 %, escenario base). Requiere navegador; procedimiento en `capturas/README.md`. |
| Prueba de cinco segundos (persona real) | Pendiente | No se realizó; requiere usuario. |
| Verificación visual 1440 × 900, zoom 100 % | Pendiente | Entorno headless sin navegador; procedimiento en `capturas/README.md`. |
| `pytest -q` de todo el repo | Pendiente (limitación de entorno) | Falla en colección por `src/api/test_api.py` (sin `fastapi`), preexistente. `pytest -q tests/` pasa (60). |
| `python src/api/test_api.py` | Pendiente (limitación de entorno) | `fastapi` no instalado (está en `requirements-api.txt`, fuera de alcance). |

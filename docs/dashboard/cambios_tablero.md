# Cambios del tablero conforme al manual

Rama: `tablero-manual` (desde `origin/main` actualizado). Alcance: dashboard, funciones
de cálculo, pruebas, documentación y capturas. **No** se tocaron `data/`, `src/informe/`,
`src/ML_C/`, `src/arendonc2/`, `src/optimizacion/`, API ni infraestructura.

## Cambios visibles

### Pantalla 0. Resumen (rediseño completo)

- **Título dinámico** por sede: "[Sede] cubre [X] % del área y presenta [Y] t/año
  captables al 20 %".
- Pregunta principal y subtítulo "Base 2021-2023 · Radio 40 km · Captación supuesta 20 %".
- **Filtro de sede** entre los 42 municipios, por defecto la de mayor cobertura
  (calculada). Radio y captación fijos en el resumen.
- **Cuatro indicadores de decisión** (base 2021-2023): área cubierta a 40 km (con pp frente
  al referente del sur), puesto entre los 42, volumen anual captable al 20 % y razón de
  volumen frente al sur (con ambos valores).
- **Cuadrícula 2×2** de visuales con pregunta, unidades, comparación y respuesta de una
  frase: P1 área por sede (barras horizontales, azul/gris, umbral 50 % rotulado), P2
  volumen por escenario histórico (línea base, % vs base), P3 composición productiva en
  % de toneladas con piña destacada, P4 frecuencia de centrales en los 54 escenarios de
  optimización.
- Secciones **plegadas**: "Pronóstico y exposición logística" (exposición sin caña
  reconciliada y valoración de exposición anualizada) y "API y base de datos" (estado de
  API/DuckDB, formulario de predicción LightGBM, manejo de fallos).
- **Descarga** del resumen por sede en CSV con unidades, periodos y supuestos.
- Se **retiraron** los botones "Ir a Pantalla…" que no navegaban.
- Se **reemplazó** la lectura rápida "entre un 22 % y un 38 %" (ámbito con caña, de
  `metrica_negocio_resumen.csv`) por la reducción del informe (**30,4 %**), reproducida
  con `cobertura.exposicion_sin_cana`.

### Otras pantallas (correcciones puntuales)

- Pantalla 2: título "Oferta municipal pronosticada (mapa)"; se eliminó la nota "depende de
  la tarea de Alejandro".
- Pantalla 2b: título "Zonas de acopio por agrupamiento espacial"; "modelo de optimización
  de Samuel" → "optimización de la pantalla 3".
- Pantalla 3: "adaptador de Alejandro" → "módulo de escenarios de optimización".
- Pantalla 4 (HTML): el título del panel de hipótesis (`tComp`) ahora se genera de los
  datos y expresa ambas razones y la conclusión: "Bugalagrande alcanza 3,0 veces el área
  de Vijes y presenta 1,9 veces su volumen captable: no alcanza el doble". Cambio limitado
  a la comunicación; no altera cálculos ni geometría.

## Módulos nuevos o modificados

- `src/dashboard/cobertura.py` (nuevo): cobertura de área, ranking, referente del sur,
  volúmenes por escenario, composición, frecuencia de centrales y exposición sin caña.
  Reutiliza el payload del tablero (`tablero_central.generar_html_tablero` + `PATRON_DATOS`,
  el mismo mecanismo validado por `test_tablero_central.py`) y el método de
  `cifras_hipotesis.py`. No hay fórmulas duplicadas entre tarjetas, gráficos y descargas.
- `src/dashboard/utils.py`: formatos colombianos (`fmt_pct`, `fmt_puntos`, `fmt_entero`,
  `fmt_toneladas`, `fmt_millones_cop`, `fmt_razon`) y `cargar_estabilidad_opt`.
- `src/dashboard/app.py`: rediseño de `pantalla_resumen` y correcciones de texto.

## Diferencias numéricas encontradas y su causa

- **Exposición logística, 38,2 % vs 30,4 %.** El resumen anterior usaba
  `data/results/ML_Ce/metrica_negocio_resumen.csv`, ámbito `h1_2019_2023`, que **incluye la
  caña de azúcar** (95,2 % de las toneladas): 729,06 → 450,71 M t·min, −38,2 % (y el
  callout "22 %–38 %"). El informe (sección 3.4.3) mide la exposición **sin caña**, porque
  la caña no entra a la central: 100,08 → 69,69 M t·min, **−30,4 %**. No es un error de
  ninguno de los dos; son **alcances distintos**. El resumen ahora usa el alcance del
  informe (sin caña) y lo rotula.
- **Valoración monetaria, 1.500 millones.** 100,08 − 69,69 = 30,39 M t·min. A 250
  COP/(t·min) eso da **7.598 millones** (acumulado de 5 años), no 1.500. Solo al
  **anualizar** (÷ 5 años) se obtienen ~1.520 millones/año ≈ 1.500 millones. El tablero la
  presenta como **valoración de exposición anualizada** con factor supuesto 250
  COP/(t·min), no como ahorro financiero realizado.
- **Razón de áreas 3,05 vs 3,15.** El tablero agrupa la fruta en 5 categorías y usa su
  campo `ha` (37.224 ha para Bugalagrande); el consolidado crudo da 37.184 ha sembradas.
  La diferencia (~40 ha) viene del agrupamiento, no de un error. El resumen usa el mismo
  payload del tablero para que todas las vistas sean coherentes; ambas razones redondean a
  "3,0 veces".
- **t/ha sin piña: 11,6 Bugalagrande, 11,2 Vijes.** El manual pedía verificar a qué sede
  corresponde cada cifra; 11,58 → Bugalagrande, 11,21 → Vijes.

## Impacto en el informe y figuras

- **Figura 10** (captura de la pantalla 4 con la hipótesis desplegada) quedó afectada por
  el nuevo título del panel y **debe recapturarse** con la configuración de
  `docs/informe/README.md`. Pendiente de una sesión con navegador (ver `capturas/`).
- Las figuras 1-9 y las cifras de `src/informe/` **no** cambian (no se tocaron esos
  scripts). Las cifras del informe se reproducen sin alterarlas.

## Limitaciones pendientes

- Prueba de cinco segundos (persona real) y verificación visual a 1440 × 900: pendientes;
  entorno headless sin navegador.
- `pytest -q` de todo el repo falla en colección por `src/api/test_api.py` (sin `fastapi`,
  preexistente). `pytest -q tests/` pasa (60 pruebas).
- La composición productiva (P3) usa toneladas promedio 2021-2023 por producto; algunos
  productos menores quedan agrupados en "Otros frutales".

## Rediseño de la pantalla 4 (tablero central → herramienta de exploración)

Cambio posterior, limitado a `src/dashboard/assets/tablero_central_acopio_valle.html`, su
integración en `app.py` y las pruebas. No cambian fórmulas, fuentes ni valores iniciales.

- **Encabezado:** título "Cobertura y capacidad de una central de acopio de fruta y
  plátano" y descripción de exploración. Se retiraron los bloques "Pregunta 1", "Pregunta 2"
  e "Hipótesis" y su numeración.
- **Se eliminó el modo de presentación:** la función `enfocar()`, las clases `f1/f2/f3` y los
  listeners `toggle` de pregunta/veredicto que cambiaban `st.sede`/`st.cap` al abrir un
  texto. Abrir o cerrar un desplegable ya no cambia parámetros, ni oculta o atenúa paneles.
  No se usó `opacity:1!important`: se retiró la lógica de presentación y se adaptaron las
  referencias del DOM (se eliminaron `#frase`, `#q1`, `#q2` y `pintar()` ya no las toca).
- **Controles visibles** debajo del título: municipio sede, radio de cobertura, captación,
  capacidad anual de referencia y escenario de oferta. Radio y captación salieron del
  desplegable "Ajustes" (eliminado). Rangos y valores por defecto sin cambios. Cada control
  modifica solo su parámetro; cambiar sede/escenario/radio/captación no ajusta la capacidad.
- **Resultados siempre explorables:** mapa de cobertura, superficie y composición, municipios
  cubiertos, volumen captable, utilización y ranking, con títulos descriptivos. El ranking
  ya no depende de `solo-f1`; si la sede no está entre las primeras, se añade con su puesto
  real sin duplicados. La capacidad se rotula como referencia, no dimensionamiento; la
  utilización como estimación, no operación garantizada; bajo/alto como escenarios históricos
  sintéticos.
- **Comparación territorial** en sección independiente "Comparación territorial: centro-norte
  y sur", siempre visible, descriptiva (sin hipótesis ni veredicto ni "alcanza el doble").
  Aclara que compara las mejores sedes de cada región por área y que puede diferir de la sede
  del usuario; usa **siempre el escenario base** (rotulado). Solo el radio la afecta. El
  "recuperable" quedó en un `<details>` con su aclaración de referencia no sincronizada.
- **Integración Streamlit:** la pantalla 4 pasa de `st.iframe(html, …)` (que en Streamlit
  1.67 espera una URL, no HTML) a `st.components.v1.html(html, height=1400, scrolling=True)`,
  que embebe el HTML y permite desplazamiento vertical sin recortes.
- **Figuras del informe afectadas:** Figuras 9 y 10 (capturas de la pantalla 4) quedan
  desactualizadas; ver `docs/dashboard/capturas/README.md`.

## Controles de la pantalla 4 en la barra lateral de Streamlit

Cambio posterior que traslada los cinco controles de la pantalla 4 del HTML a la barra
lateral nativa, manteniendo el tablero HTML/CSS/JS para visualizar los resultados.

- **Ubicación (§1):** debajo del selector de pantalla y antes de "Estado de los datos", bajo
  "Filtros de esta vista": Municipio sede, Radio de cobertura (km), Captación (%), Capacidad
  anual de referencia (t/año) y Escenario de oferta (bajo/base/alto). Widgets nativos
  (`selectbox`, `slider`, `radio`), coherentes con las demás pestañas. Se conservan opciones,
  rangos, pasos y valores iniciales. Se retiraron los controles del HTML; queda una línea
  compacta de contexto (`#ctxLinea`) que muestra la configuración activa, sin duplicar
  controles. El mapa ya no cambia la sede al hacer clic (la sede se elige en la barra
  lateral), evitando estados que se contradigan.
- **Estado (§2):** Streamlit es la única fuente de verdad. Claves propias de la pantalla 4
  (`t4_sede`, `t4_radio`, `t4_captacion`, `t4_capacidad`, `t4_escenario`) para no colisionar
  con otras vistas. Como Streamlit descarta el estado de un widget cuando no se instancia
  (al navegar a otra pantalla), se guarda un espejo persistente (`*_val`) y se re-siembra el
  widget al volver; así la selección persiste, se inicializa solo si no hay estado previo y
  cambiar un control no reinicia los demás (en particular, cambiar sede/radio/captación/
  escenario no toca la capacidad).
- **Paso al HTML (§3):** `tablero_central.construir_config()` valida tipos, rangos y opciones
  y **resuelve el código DANE contra los municipios del payload** (no por posición en el
  selector). `generar_html_tablero(..., config=...)` inyecta `window.__CFG__` con
  `json.dumps` (sin concatenar valores a mano), escapando `< > &` para que no pueda cerrar el
  `<script>` ni el HTML. Sin `config`, no inyecta nada y conserva los valores predeterminados
  (compatibilidad con las llamadas existentes). El JSON lleva: `cod_dane`, `radio_km`,
  `captacion_pct` (porcentaje, no fracción), `capacidad_t` (t/año) y `escenario`.
- **JavaScript (§4):** `const CFG = window.__CFG__ || {}`; `st` se inicializa desde `CFG`
  (resolviendo el índice por `cod_dane`) y `pintar()` se ejecuta con esos valores. Se
  retiraron los listeners de los controles HTML y el selector `#sede`; no quedan referencias
  a nodos eliminados. No se reintroduce sombreado, modo de presentación ni cambios
  automáticos de sede/capacidad. No cambian fórmulas ni datos.
- **Comparación territorial (§5):** se corrigió el texto. Ahora dice que el radio cambia la
  cobertura y puede cambiar las sedes comparadas, y que la captación cambia los volúmenes;
  usa siempre el escenario base, y la sede seleccionada y la capacidad no la alteran (sus
  fórmulas no las usan).
- **Integración (§6):** se mantiene `st.components.v1.html(..., scrolling=True)` (funciona
  con Streamlit 1.67; `st.iframe` espera una URL, no HTML). Altura ajustada a 1320 px tras
  quitar la fila de controles.

## UX de la pantalla 3 (Ubicación) para público no experto

Cambio limitado a la experiencia de usuario de la pantalla 3 en `src/dashboard/app.py`
(y sus pruebas). **No** se tocaron fórmulas, restricciones, datos ni resultados del modelo
(`src/optimizacion/`, `src/arendonc2/`), ni otras pantallas.

- **Decisiones vs. parámetros técnicos (§1):** se retiraron de la interfaz el límite de
  tiempo, la brecha solicitada y cualquier ajuste del motor/tolerancias. Sus valores
  predeterminados quedan en un único lugar (`OPT_TIEMPO_LIMITE_S=120`,
  `OPT_GAP_RELATIVO=0.0`, `OPT_K_ZONAS=5`), con los mismos valores de antes. El respaldo
  entre motores (SCIP/CBC) no se alteró. Los valores efectivos se documentan y quedan en el
  desplegable "Detalles técnicos del cálculo" de cada resultado.
- **Controles de negocio (§2):** en la barra lateral, bajo "Filtros de esta vista", antes de
  "Estado de los datos": Año del análisis, Escenario de producción, Escenario de consumo
  local, Distribución entre mercado nacional y exportación, Organización de los acopios
  (Libre/Por zonas), Número de acopios (solo en modo Libre; en Por zonas se muestra el número
  fijado por las zonas) y Prioridad del transporte. "λ" se renombró a "Prioridad del
  transporte" con extremos "Hacia los destinos" (0) y "Recolección y traslado a la central"
  (1); la correspondencia matemática (objetivo λ·A+(1−λ)·B) no cambió. Se conservan opciones,
  rango, paso y valores iniciales (base/base/80_20/libre, k=5, prioridad 0,5).
- **Cálculo explícito (§3):** botón "Calcular ubicación". Cambiar controles no ejecuta
  cálculos; si la configuración cambia tras calcular, se muestra "La configuración cambió.
  Calcula nuevamente para actualizar los resultados" y se retira el resultado anterior. La
  configuración con la que se obtuvo cada resultado queda visible.
- **Resultado a ancho completo (§4):** municipio recomendado y estado → configuración en una
  línea → indicadores (volumen considerado, cobertura de datos, acopios abiertos) → mapa →
  transporte por tramos → alternativas/comparación/estabilidad bajo demanda → detalles
  técnicos plegados. Las limitaciones (cobertura parcial, exclusión de productos pendientes,
  ausencia de capacidades respaldadas) quedan visibles, no escondidas en el diagnóstico.
- **Estados en lenguaje claro (§5):** OPTIMAL → "Solución óptima del modelo"; FEASIBLE →
  "Solución válida; podría existir una mejor"; INFEASIBLE → "No existe una solución que
  cumpla las restricciones de esta configuración"; sin solución → "El cálculo terminó sin
  encontrar una solución" (distinto de inviabilidad). Errores muestran mensaje comprensible
  con detalle técnico, sin convertirse en resultado vacío ni éxito. Solo se muestran central,
  asignaciones y métricas cuando hay solución válida. "Diagnóstico del solver" pasó a
  "Detalles técnicos del cálculo"; la brecha solo se muestra si hay dato (no se muestra
  brecha 0 cuando falta).
- **Gráficas comprensibles (§6, §7):** la unidad t·min se explica; los tramos
  (municipio→acopio, acopio→central, central→destinos) se nombran. La gráfica de alternativas
  conserva los ejes A y B pero rotulados "Recolección y traslado a la central (millones de
  t·min)" y "Transporte desde la central a destinos (millones de t·min)", con valores
  convertidos a millones; título "Alternativas de ubicación y transporte"; puntos como
  "no dominadas encontradas"; tooltip con central, ambos componentes con unidades, prioridad
  en lenguaje claro y estado. La notación λ/A/B/Z queda solo en los detalles técnicos. Los
  análisis se ejecutan bajo demanda con botones "Explorar alternativas", "Comparar libre y
  por zonas" y "Evaluar estabilidad"; se aclara que la frecuencia entre escenarios no es una
  probabilidad.
- **Equivalencia (§8):** la configuración por defecto produce el mismo `id_escenario`
  (`2024_Obase_Cbase_M80_20`), los mismos argumentos del modelo (k=5, λ=0,5, tiempo 120 s,
  gap 0,0) y, por tanto, resultados equivalentes (p. ej. volumen considerado 836.034 t,
  central Bugalagrande, estado OPTIMAL).

## Presentación de la pantalla 0 (encabezado y gráfica P3)

Ajustes solo de presentación; no cambian cálculos, datos, filtros ni otras pantallas.

- **Encabezado orientado al propósito (§1):** el título más grande es fijo —"Selección de
  municipios y estimación de volumen para una central de acopio"— con el subtítulo "Compara
  cobertura agrícola, volumen captable y alternativas de ubicación para priorizar municipios
  del Valle del Cauca". El hallazgo dinámico de la sede ("[Sede] cubre X % … Y t/año captables
  al 20 %") pasa a una línea secundaria de menor jerarquía (encabezado `######`), sin competir
  con el título ni afirmar dimensionamiento definitivo. Se retiró la pregunta larga que
  duplicaba la explicación; el periodo, radio y captación siguen en una línea compacta de
  contexto.
- **Gráfica P3 de composición (§2):** título "Composición de la producción por cultivo" y
  subtítulo "Participación en toneladas · Promedio 2021-2023"; se identifican la sede
  seleccionada (barra superior) y el referente del sur (barra inferior). Eje X fijo 0–100 %
  con marcas cada 25 %; se eliminó el título largo del eje (la unidad está en el subtítulo y
  las marcas). La leyenda va debajo del gráfico, en su propio espacio, con margen inferior
  reservado (96 px) y orden coherente con los segmentos. Etiquetas interiores solo cuando
  caben, nunca giradas ni recortadas; los segmentos pequeños se consultan por tooltip (nombre,
  porcentaje y toneladas). Color consistente por cultivo entre ambas barras, con la piña en un
  único color de énfasis y color de texto fijado para contraste en tema claro y oscuro. Altura
  aumentada a 360 px y barra de herramientas reducida a acciones útiles. El detalle de
  producción, superficie y t/ha sembrada sigue debajo del gráfico. Los porcentajes y toneladas
  no cambian (piña 0,6 % Bugalagrande / 51,8 % Vijes; cada barra suma 100 %).
- **Validación visual (§3): pendiente.** El spec de la figura se verificó por programa (eje
  0–100 con marcas, leyenda separada, sin rotación, valores intactos, tooltip con t) y el
  encabezado con AppTest, pero la revisión visual en navegador a zoom 100 % (1440×900 y una
  ventana más estrecha, Bugalagrande/Vijes/otra sede) no se realizó por falta de navegador
  utilizable en el entorno. No se declara hecha. Procedimiento en `capturas/README.md`.

## Documentado por separado (no implementado en este PR)

Estas mejoras se registran como pendientes y **no** se implementan aquí:

- Ampliar `/predict` para devolver también el ingenuo y el modelo final combinado
  (hoy devuelve LightGBM). Requiere cambiar el contrato de la API: fuera de alcance.
- Revisar la descripción de las tablas que consulta `/metricas`.
- Entrenamiento opcional en `run_all.py`.
- Normalización de prefijos S3 con doble barra (`//`).

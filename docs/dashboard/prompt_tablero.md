# Prompt para ajustar el tablero al manual de dashboards

Para el equipo: abran Claude Code (u otro asistente con acceso al repositorio) en la raíz de `MingaData_PI` y peguen todo lo que está debajo de la línea. El asistente trabaja en una rama nueva y abre un pull request; Carlos lo revisa antes de unirlo a `main`, porque Streamlit Cloud publica desde `main`. El manual que se cita es "Dashboards para responder preguntas de negocio" (Mauricio Arias Correa, curso de Comunicación y Visualización de Datos); aquí va resumido.

---

Vas a ajustar el tablero del proyecto Minga Data en este repositorio. Antes de cambiar nada, lee `README.md`, `docs/dashboard/matriz_trazabilidad.md`, `docs/informe/README.md`, `src/dashboard/app.py`, `src/dashboard/utils.py`, `src/dashboard/tablero_central.py`, `src/dashboard/test_tablero_central.py`, `src/informe/cifras_hipotesis.py` y `src/informe/cifras_3_3_y_3_4.py`.

No cambies los datos ni los resultados de `data/`, ni los scripts de `src/informe/`, `src/ML_C/`, `src/arendonc2/` y `src/optimizacion/`. El informe final ya está escrito con esas cifras, y el tablero tiene que mostrar las mismas.

## 1. Contexto

Minga Data busca dónde ubicar una central de acopio y procesamiento de fruta y plátano en el Valle del Cauca y de qué tamaño hacerla. Decide la Secretaría de Agricultura del Valle: los profesionales de planeación formulan el proyecto y el secretario o la secretaria lo aprueba. La acción esperada es escoger dos o tres municipios candidatos para el estudio de costos y fijar un rango de capacidad.

El tablero tiene dos piezas:

- El tablero de cobertura, `src/dashboard/assets/tablero_central_acopio_valle.html`. Lo llena `tablero_central.py` con los datos de `data/clean/produccion_valle_clean.csv` y se ve en la pantalla "4. Cobertura y capacidad". Las Figuras 9 y 10 del informe son capturas de esa vista.
- La aplicación de Streamlit, `src/dashboard/app.py`, publicada en https://mingadatapi-4puozskgkscj82yxoxmc3q.streamlit.app. Tiene seis pantallas: "0. Resumen", "1. Oferta", "2. Zonas", "2b. Zonas de acopio", "3. Ubicacion" y "4. Cobertura y capacidad". El resumen consulta la API publicada en Render (https://mingadata-api.onrender.com).

No cambies los nombres de las pantallas en la barra lateral: el informe se refiere a ellas por esos nombres.

## 2. Cifras que deben coincidir con el informe

| Cifra | Valor | De dónde sale |
|---|---|---|
| Área de fruta y plátano a 40 km de Bugalagrande (promedio 2021-2023) | 52,1 % (37.224 de 71.426 ha) | `cifras_hipotesis.py` |
| Siguientes sedes y mejor sede del sur | Andalucía 51,6 %, Zarzal 51,4 %; Vijes 17,1 % | `cifras_hipotesis.py` |
| Capacidad para usarse al 100 % (Bugalagrande, captación del 20 %) | 86.300 t al año (86.348) | `cifras_hipotesis.py` |
| Escenario bajo (peor año de cada municipio, 2014-2023) y alto (mejor año) | 58.211 t, uso de 67 %; 112.324 t, 30 % más que la capacidad | `cifras_hipotesis.py` |
| Hipótesis | Bugalagrande alcanza 3,0 veces el área de Vijes, pero necesita 1,89 veces su capacidad (Vijes: 45.802 t), no el doble | `cifras_hipotesis.py` |
| Piña | 51,8 % de las toneladas del área de Vijes y 0,6 % en la de Bugalagrande; sin piña, 11,2 y 11,6 t por hectárea sembrada | Calcular (ver P3) |
| Central en los 54 escenarios de 2024 y 2028 | Siempre en la subregión Centro; Bugalagrande 18, Riofrío 15, Yotoco 12, Sevilla 6, Andalucía 3 | `data/results/opt/estabilidad_escenarios.csv` |
| Mezcla de mercados | Con 80 % para el mercado nacional sale Bugalagrande o Sevilla; con 80 % para exportación, Yotoco o Riofrío | `estabilidad_escenarios.csv` |
| Exposición logística del pronóstico a un año, sin caña de azúcar, 2019-2023 | El modelo final la reduce 30 % (30,4 %) frente a planear con el promedio de los últimos cinco años: de 100,08 a 69,69 millones de t·min, unos 1.500 millones de pesos al año a 250 pesos por t·min. El ingenuo la reduce 32 % | Bloque "3.4.3 exposición" de `cifras_3_3_y_3_4.py` |
| Escenarios del pronóstico | Contienen el valor real en el 76 % de los casos (80 % nominal) | `data/results/ML_Ce/cobertura_intervalos.csv` |
| Error a un año en pesos, sin caña | 25 % del valor de la oferta en las series por producto y municipio (unos 735.000 millones al año) y 7 % en el total del departamento | `cifras_3_3_y_3_4.py` |

Hoy la pantalla de resumen muestra 38,2 % de reducción de la exposición (`metrica_negocio_resumen.csv`, ámbito `h1_2019_2023`) y un recuadro que dice "entre un 22 % y un 38 %". Esas cifras incluyen la caña de azúcar, que no entra a la central, y usan otra red de acopios. El informe usa 30 % sin caña: muestra esa.

El informe final empieza en "1. Introducción": 2 es el marco teórico, 3 los modelos, 4 la ingeniería de datos, 5 la visualización, 6 las conclusiones y 7 las referencias. Si el tablero o un documento cita una sección del informe, usa esa numeración.

## 3. Lo que pide el manual

1. Una pregunta principal con cinco piezas: qué se mide, de quién o de qué, en qué periodo, frente a qué referencia y para decidir qué acción. Tiene que ser específica, medible, comparable, acotada en el tiempo, accionable y con dueño.
2. La pregunta principal se divide en 3 a 5 preguntas secundarias. Van de lo general (qué pasó, descriptivas) a lo específico (por qué, diagnósticas), y cada una tiene su visual.
3. Una métrica es un dato; un indicador es una métrica comparada con una referencia; un KPI es un indicador con objetivo, umbral y dueño, y son pocos. Cada KPI se documenta en una ficha técnica: fórmula, referencia, si es mejor que suba o que baje, y fuente.
4. Cada tarjeta de KPI lleva nombre y periodo, un valor grande y redondeado, la comparación con la referencia con ▲ o ▼ y texto, y una tendencia mínima (sparkline) cuando hay serie. El color nunca va solo. Prueba de los 5 segundos: sin explicación, se entiende qué pasó y si es bueno o malo.
5. Entre 3 y 7 KPIs, en una sola fila arriba, del resultado a sus causas, todos con el mismo formato y el mismo periodo. Sin velocímetros, sin 3D, sin decimales de más y con formato local.
6. El gráfico sale de la pregunta: comparar, barras ordenadas; evolución, línea; composición, barras 100 % apiladas; distribución, histograma; relación, dispersión; desviación frente a una meta, barras divergentes. Nada de tortas para comparar.
7. La pantalla se lee de arriba a la izquierda hacia abajo: título, pregunta principal y filtros; la fila de KPIs; después P1 y P2 (qué pasó) y P3 y P4 (por qué). Una sola pantalla sin desplazarse, de 4 a 6 visuales, con los paneles alineados en una cuadrícula.
8. El color tiene una función: gris para el contexto, un color protagonista para lo que responde la pregunta, la referencia en línea punteada, y los colores de estado (cumple, alerta) solo para estado, siempre con ícono y texto. Una misma entidad conserva su color en todo el tablero. Uno o dos colores de énfasis por visual, como máximo.
9. Debajo de cada visual va un recuadro "Respuesta Pn:" con la respuesta en una frase con cifras. Los filtros redibujan todo.

## 4. Tareas, en orden de prioridad

### Prioridad 0: correcciones

1. Pantalla 2 de `app.py`: borra la nota que dice que el agrupamiento "depende de la tarea de Alejandro. Mientras tanto, …". Pantalla 2b: cambia "del modelo de optimización de Samuel" por "de la optimización (pantalla 3)". Las pantallas 2 y 2b tienen casi el mismo título: la 2 muestra la oferta pronosticada por municipio y la 2b las cinco zonas de acopio, y sus títulos deben decirlo.
2. Resumen: quita el 38,2 % y el recuadro "Lectura rápida" del 22 % al 38 %, y usa las cifras de la sección 2. Quita también los botones "Ir a Pantalla…": no navegan, y la navegación ya está en la barra lateral.
3. Tablero de cobertura: el título del panel de la hipótesis (`tComp`, cerca de la línea 491 del HTML) hoy dice "El centro-norte alcanza 3,0 veces el área del sur". Debe decir, con los valores calculados y los nombres de las dos sedes: "Bugalagrande alcanza 3,0 veces el área de Vijes, pero necesita 1,9 veces su capacidad", y agregar ", no el doble" cuando la razón de capacidad sea menor que 2. Agrega esa verificación a `test_tablero_central.py`. No cambies nada más de esa vista, porque el informe la muestra en las Figuras 9 y 10. Después vuelve a capturar la Figura 10 con los ajustes de `docs/informe/README.md` (ventana de 1440 px, Bugalagrande, 40 km, 20 %, escenario base, hipótesis desplegada) y reemplaza `docs/informe/figuras/figura_10_tablero_hipotesis.png`, con el mismo nombre.

### Prioridad 1: rediseñar "0. Resumen" según el manual

El resumen es la vista para quien aprueba; las otras pantallas quedan como detalle para quien formula el proyecto.

Encabezado:

- Título con el hallazgo, que cambie con la sede. Con Bugalagrande: "Bugalagrande alcanza el 52 % del área de fruta y plátano a 40 km y necesita una central de 86.300 t al año".
- Debajo, la pregunta principal: "¿Qué municipio del Valle del Cauca, como sede de la central, alcanza más área de fruta y plátano a 40 km, y con qué capacidad se usaría al 100 % con la producción de 2014 a 2023, frente a la mejor sede del sur, para escoger los candidatos del estudio de costos y fijar el rango de inversión?"
- Una línea gris: "Usuario: Secretaría de Agricultura del Valle · Se actualiza cada año con el consolidado agrícola · Radio de 40 km, captación del 20 %, base = promedio 2021-2023".
- Un filtro: la sede, entre los 42 municipios, con la que más área alcanza por defecto. El radio y la captación quedan fijos en esta vista; quien quiera cambiarlos usa la pantalla 4.

Fila de KPIs, cuatro tarjetas con el mismo periodo:

| KPI | Valor con Bugalagrande | Comparación y estado |
|---|---|---|
| Área de fruta y plátano a 40 km | 52,1 % | ▲ 35,0 pp más que la mejor sede del sur (Vijes, 17,1 %). Estado: cumple (la hipótesis pedía 50 % o más). Sparkline: porcentaje del área a 40 km por año, 2014-2023 |
| Puesto de la sede | N.º 1 de 42 | Andalucía (51,6 %) y Zarzal (51,4 %) quedan a menos de 1 pp. Sin color de estado |
| Capacidad para usarse al 100 % | 86.300 t al año | ▼ 1,9 veces la de Vijes; la hipótesis pedía 2,0 o más. Estado: alerta. Sparkline: toneladas captables por año, 2014-2023 |
| Uso en el escenario bajo | 67 % | ▼ 33 pp por debajo del 100 %; en el alto haría falta 30 % más de capacidad. Sin color de estado, porque el informe no fija un umbral |

Cuatro visuales en una cuadrícula de 2 × 2:

- P1 · Descriptiva · "¿Qué sede deja más área de fruta y plátano a 40 km o menos?". Barras horizontales ordenadas con las 10 mejores sedes, la elegida en azul y las demás en gris, una línea punteada en 50 % (el umbral de la hipótesis) y el porcentaje como etiqueta. Respuesta P1, con Bugalagrande: "Bugalagrande, Andalucía y Zarzal quedan casi empatados (52,1 %, 51,6 % y 51,4 %): conviene estudiar ese corredor y no un solo municipio. La mejor sede del sur, Vijes, llega al 17,1 %."
- P2 · Descriptiva · "¿Cuánto se usaría la central en el peor año, en el base y en el mejor?". Barras con las toneladas captables en el escenario bajo (peor año de cada municipio), el base (promedio 2021-2023) y el alto (mejor año), una línea punteada en la capacidad y el porcentaje de uso como etiqueta. Respuesta P2: "Una central de 86.300 t se usaría al 67 % en el peor año y le faltaría 30 % en el mejor: conviene que crezca por etapas."
- P3 · Diagnóstica · "¿Por qué la sede del centro no necesita el doble de capacidad que la del sur?". Barras 100 % apiladas con las toneladas por cultivo en el área de la sede y en la de la mejor sede del sur, con la piña en azul y los demás cultivos en grises. Se calcula con `produccion_valle_clean.csv`, familia Frutales, promedio 2021-2023, sumando los municipios cuyo centroide queda a 40 km o menos de la sede (el mismo criterio del tablero de cobertura). Respuesta P3: "La piña es el 51,8 % de las toneladas del área de Vijes y rinde mucho por hectárea; sin piña, las dos áreas rinden unas 11 t por hectárea sembrada (11,2 y 11,6). Por eso Bugalagrande alcanza 3,0 veces el área, pero necesita 1,9 veces la capacidad."
- P4 · Diagnóstica · "¿La ubicación se sostiene si cambian la oferta, el consumo y la mezcla de mercados?". Barras ordenadas con el número de escenarios, de los 54, en que cada municipio sale como central; la sede elegida en azul si aparece. Respuesta P4: "La central cae en el Centro en los 54 escenarios, y en Bugalagrande en 18. Lo que más la mueve es la mezcla de mercados: con 80 % para exportación pasa a Yotoco o Riofrío."

Arma los títulos y las respuestas con los datos (f-strings), para que sigan siendo ciertos cuando cambie la sede. Con Bugalagrande deben decir lo mismo que arriba.

Debajo de los cuatro visuales, en secciones plegadas (`st.expander`, cerradas al abrir):

- "Pronóstico y exposición logística": el alcance del pronóstico (2024-2028, número de productos, 42 municipios, 24 años de historia), la exposición logística a un año sin caña (30 %, unos 1.500 millones de pesos al año, el ingenuo 32 %), la cobertura de los escenarios (76 % frente a 80 % nominal) y el error a un año en pesos (25 % por serie, 7 % en el total). La exposición sin caña se calcula con una función nueva en `src/dashboard/`, con el mismo método del bloque "3.4.3 exposición" de `cifras_3_3_y_3_4.py`; no copies el número a mano y no modifiques ese script.
- "API y base de datos": el estado de la API y de DuckDB y el formulario de predicción en vivo que ya existen. El informe dice que el resumen consume la API, así que no los quites.
- La descarga del CSV del resumen.

Al pie, la fuente: "Fuente: Gobernación del Valle del Cauca, consolidado agrícola de cultivos permanentes; DANE, SIPSA; optimización y cálculos de Minga Data."

Cómo implementarlo:

- Crea `src/dashboard/cobertura.py` con las funciones de cobertura (área, toneladas por escenario, ranking de sedes, mejor sede del sur, composición por cultivo y series anuales) a partir de los mismos datos del tablero, `generar_html_tablero` y `PATRON_DATOS`, como hace `src/informe/cifras_hipotesis.py`. La pantalla solo llama esas funciones.
- Agrega a `utils.py` funciones de formato colombiano: punto para miles, coma para decimales, "52,1 %", "86.300 t", "1.500 millones".
- En Plotly: fondo blanco, grilla tenue o ninguna, ejes con unidades, barras que empiezan en cero y etiquetas directas en lugar de leyendas cuando alcancen. Colores: azul `#002855` (el mismo `--accent` del tablero de cobertura) para el protagonista; grises `#B8BEC8` y `#D0D5DD` para el contexto; línea punteada `#18212D` para las referencias; un verde y un rojo solo para estado, siempre con ▲ o ▼ y texto. Nada de escalas de rojo a verde.
- Con una ventana de 1440 × 900, la vista debe mostrar hasta P3 y P4 sin desplazarse: gráficos de unos 260 px de alto y márgenes pequeños.
- Documenta las cuatro tarjetas en `docs/dashboard/fichas_kpi.md`: KPI, fórmula, referencia, si es mejor que suba o que baje, umbral o estado, fuente y función que lo calcula.

### Prioridad 2: otras pantallas, API y documentos

1. Pantallas 1, 2, 2b y 3: el título dice el hallazgo o la pregunta que responde, y un subtítulo gris da el periodo, las unidades y la fuente. Números en formato colombiano, unidades en las métricas de la pantalla 3 (millones de t·min) y títulos sin emojis. En `agregar_municipios_al_mapa` la escala va de rojo a verde: cámbiala por una de un solo tono, de gris claro a azul, con leyenda y unidades.
2. API: en `/predict` deja `prediccion_t` como está (LightGBM, así lo describe el informe) y agrega `prediccion_ingenuo_t` (el último valor observado) y `prediccion_final_t`, con la regla de `src/ML_C/07_escenarios.py`: promedio del ingenuo y LightGBM en los productos detallados y solo el ingenuo en los simplificados. Caso de prueba: caña de azúcar, Bugalagrande (76113), 2024, horizonte 1, da LightGBM 1.426.611 t, ingenuo 1.463.840 t y modelo final 1.445.226 t. Agrega ese caso a `src/api/test_api.py`. En el formulario del resumen, el modelo final es la cifra principal y LightGBM va como detalle. Si el redespliegue en Render falla, revierte: es mejor la API actual funcionando que una nueva caída.
3. `docs/evaluacion/evidencia_despliegue.md` dice que la API consulta cinco tablas, pero `/metricas` solo consulta `metricas_modelo`. Corrige esa frase; la base sí tiene las cinco tablas.
4. `src/pipeline/run_all.py` no llama a `src/pipeline/entrenar_modelo_final.py`. Agrégalo como etapa opcional antes de la persistencia, o explica en el README que se corre aparte. No cambies ningún resultado.
5. Cuando el prefijo está vacío, las claves de S3 quedan con doble barra (`s3://mingadata-pi-2026//20261121_034051/...`). Deja anotado el arreglo en `docs/evaluacion/evidencia_despliegue.md`, pero no lo apliques antes de la sustentación: cambiaría la ruta del modelo publicado y las variables de entorno de Render.

## 5. Reglas

- Trabaja en la rama `tablero-manual` y abre un pull request hacia `main`. Commits pequeños, con mensajes que digan qué cambió.
- No subas secretos. Las credenciales de AWS van solo en variables de entorno.
- No subas `.DS_Store` ni archivos generados que no estén en el repositorio.
- No agregues librerías nuevas si las actuales alcanzan. Si agregas una, fija su versión en `requirements.txt`, porque Streamlit Cloud instala desde ahí.
- Todo el texto del tablero va en español de Colombia.

## 6. Cómo se revisa

- Pasan `pytest -q`, `python src/dashboard/test_tablero_central.py` (24 verificaciones, 25 con la del título nuevo) y `python src/api/test_api.py`.
- Una prueba nueva, `tests/dashboard/test_resumen.py`, comprueba con Bugalagrande: 52,1 %; N.º 1 de 42; 86.348 t; uso de 67,4 % en el bajo y 30,1 % más en el alto; razón de área 3,05 y de capacidad 1,89; piña 51,8 % del área de Vijes; 18 de 54 escenarios; exposición 30,4 % menor que la del promedio de cinco años.
- `streamlit run src/dashboard/app.py` abre en el resumen, y el resumen responde la pregunta principal sin tocar ningún control.
- Capturas a 1440 × 900 del resumen y de la pantalla 4 en `docs/dashboard/capturas/`.
- `docs/dashboard/validacion_manual.md`: cada regla de la sección 3 marcada como "cumple" o "no cumple", con una línea de evidencia, y el resultado de la prueba de los 5 segundos con alguien que no haya visto el tablero.
- `docs/dashboard/cambios_tablero.md`: la lista de cambios visibles y qué parte del informe toca cada uno (sección 5.4, sección 4.7 si cambió la API, Figuras 9 y 10). Con esa lista, Carlos actualiza el informe.

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

## Documentado por separado (no implementado en este PR)

Estas mejoras se registran como pendientes y **no** se implementan aquí:

- Ampliar `/predict` para devolver también el ingenuo y el modelo final combinado
  (hoy devuelve LightGBM). Requiere cambiar el contrato de la API: fuera de alcance.
- Revisar la descripción de las tablas que consulta `/metricas`.
- Entrenamiento opcional en `run_all.py`.
- Normalización de prefijos S3 con doble barra (`//`).

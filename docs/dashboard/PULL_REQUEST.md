# PR: Rediseño de la pantalla "0. Resumen" conforme al manual de dashboards

Rama: `tablero-manual` → `main`. **No** hacer merge automático.
Crear en: https://github.com/CeyniPBH/MingaData_PI/pull/new/tablero-manual

## Qué se implementó

- **Pantalla 0. Resumen** rediseñada: título dinámico por sede, pregunta principal y
  subtítulo (base 2021-2023 · radio 40 km · captación 20 %), filtro de sede entre los 42
  municipios (por defecto la de mayor cobertura), cuatro indicadores de decisión,
  cuadrícula 2×2 de visuales (P1-P4), secciones plegadas (pronóstico/exposición y API/BD) y
  descarga CSV con unidades, periodos y supuestos.
- **Correcciones (§4):** se quitaron los botones "Ir a Pantalla…" que no navegaban; se
  eliminó la nota "depende de la tarea de Alejandro"; "modelo de Samuel" → "optimización de
  la pantalla 3"; títulos diferenciados de pantallas 2 (oferta municipal) y 2b (zonas de
  acopio); se reemplazó la exposición de otro alcance (38,2 % / "22 %–38 %", con caña) por
  la del informe (30,4 %, sin caña), reproducida. El panel de hipótesis de la pantalla 4
  genera su título desde los datos.
- **`src/dashboard/cobertura.py`** (nuevo): cobertura, ranking, referente del sur,
  volúmenes por escenario, composición, frecuencia de centrales y exposición sin caña.
  Reutiliza el payload del tablero (`generar_html_tablero` + `PATRON_DATOS`) y el método de
  `cifras_hipotesis.py` / `cifras_3_3_y_3_4.py`. Sin fórmulas duplicadas.
- **`src/dashboard/utils.py`**: formatos colombianos y `cargar_estabilidad_opt`.

## Cifras reproducidas (no hardcodeadas)

Bugalagrande 52,1 % / 86.348 t / puesto 1 / 14 municipios · Andalucía 51,6 % · Zarzal
51,4 % · Vijes 17,1 % / 45.802 t · razón área 3,05 · razón volumen 1,89 · bajo 58.211 t
(67,4 %) · alto 112.324 t (130,1 %) · piña 51,8 % Vijes / 0,6 % Bugalagrande (toneladas) ·
t/ha sin piña 11,6 Bugalagrande / 11,2 Vijes · exposición sin caña 100,08 → 69,69 M t·min
(−30,4 %), ingenuo −31,7 % · 54 escenarios de optimización (Buga 18, Riofrío 15, Yotoco 12,
Sevilla 6, Andalucía 3), todos OPTIMAL.

## Discrepancias encontradas (documentadas, no ocultadas)

- Exposición **38,2 % vs 30,4 %**: distinto alcance (con caña vs sin caña). El resumen usa
  el del informe.
- Valoración **1.500 millones**: es una **valoración de exposición anualizada** (÷ 5 años) a
  250 COP/(t·min), no el acumulado de 5 años (7.598 millones) ni un ahorro realizado.
- Razón de áreas 3,05 vs 3,15: agrupamiento en 5 categorías del tablero; ambas → "3,0".

Detalle en `docs/dashboard/cambios_tablero.md`.

## Pruebas ejecutadas

- `pytest -q tests/` → **60 passed** (incluye `tests/dashboard/`: 24).
- `python src/dashboard/test_tablero_central.py` → 24 OK.
- AppTest: 0 excepciones en resumen (Bugalagrande/Vijes/Cali/Buenaventura) y pantalla 4.
- JS del HTML validado con `node --check`.

## Limitaciones / pendientes reales

- `pytest -q` de **todo** el repo falla en colección por `src/api/test_api.py` (sin
  `fastapi`, en `requirements-api.txt`): limitación de entorno, preexistente.
- `python src/api/test_api.py`: no corre (sin `fastapi`).
- **Prueba de cinco segundos** (persona real): pendiente.
- **Verificación visual 1440 × 900** y **capturas** (resumen y pantalla 4): pendientes;
  entorno headless. Procedimiento en `docs/dashboard/capturas/README.md`.
- **Figura 10**: debe recapturarse porque cambió el título del panel de hipótesis.

No se declara cumplimiento completo del manual: quedan validaciones visuales y humanas.

## Alcance respetado

Solo se tocaron `src/dashboard/` y `docs/dashboard/` (+ `tests/dashboard/`). No se
modificaron `data/`, `src/informe/`, `src/ML_C/`, `src/arendonc2/`, `src/optimizacion/`,
API, pipeline ni infraestructura. El contrato de `/predict` no cambió.

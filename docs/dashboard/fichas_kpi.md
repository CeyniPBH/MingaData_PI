# Fichas de métricas, indicadores y KPI de la pantalla "0. Resumen"

Clasificación conforme a la Sesión 4 del curso y al manual "Dashboards para responder
preguntas de negocio": una **métrica** es una medición directa; un **indicador** es una
métrica elegida para apoyar una decisión; un **KPI** es un indicador con meta, umbral y
responsable definidos.

En este proyecto el **único umbral** definido es el de la **hipótesis** del informe
(más del 50 % del área y al menos el doble de capacidad que la mejor sede del sur). Las
demás cifras del resumen son **métricas e indicadores de decisión**, no KPI: el equipo no
ha fijado meta ni responsable para ellas. No se inventan metas para completar el número de
tarjetas del manual.

Todas las cifras de cobertura y volumen usan el **mismo cálculo del tablero central**
(`src/dashboard/cobertura.py`, que reutiliza el payload de
`src/dashboard/tablero_central.py` y el método de `src/informe/cifras_hipotesis.py`).

## Supuestos comunes

- Base temporal de área y volumen base: promedio 2021-2023.
- Escenarios bajo/alto: peor y mejor año municipal de 2014-2023 (años posiblemente
  distintos por municipio).
- Radio: 40 km. Distancia: **geográfica en línea recta entre centroides (haversine)**, no
  vial.
- Captación supuesta: 20 % de la producción de los municipios cubiertos.
- Nulos/ceros: un municipio sin producción aporta 0 t; no se excluye del denominador de
  área. Denominador de área total = 71.426 ha (42 municipios).

## Fichas

### 1. Área cubierta a 40 km (indicador de decisión)

| Campo | Contenido |
|---|---|
| Tipo | Indicador de decisión (no KPI: sin meta/responsable). |
| Fórmula | Σ hectáreas de fruta y plátano de los municipios a ≤ 40 km de la sede ÷ 71.426 ha. |
| Referencia | `cobertura.ModeloCobertura.pct_area`; `cifras_hipotesis.py` (52,1 % Bugalagrande). |
| Unidad y periodo | % del área · promedio 2021-2023. |
| Alcance / exclusiones | Familia Frutales (incluye plátano); excluye caña, café, caña panelera. |
| Objetivo / responsable | No definidos. El umbral de 50 % pertenece a la hipótesis, no a esta métrica. |
| Subir / bajar | Subir = más área potencialmente servible; no "bueno/malo" por sí solo. |
| Fuente / función | Consolidado agrícola de la Gobernación del Valle · `cobertura.pct_area`. |
| Nulos / ceros / empates | Municipio sin ha aporta 0; a igualdad exacta de área el orden es alfabético. |

### 2. Puesto entre los 42 municipios (indicador de decisión)

| Campo | Contenido |
|---|---|
| Tipo | Indicador de decisión. |
| Fórmula | Rango (método mínimo) de la sede al ordenar las 42 por área cubierta descendente. |
| Referencia | `cobertura.ModeloCobertura.puesto` / `ranking_area`. |
| Unidad y periodo | Puesto (1 = mayor área) · promedio 2021-2023. |
| Alcance / exclusiones | Igual que el área cubierta. |
| Objetivo / responsable | No definidos. |
| Subir / bajar | Puesto menor = mayor área. Las diferencias entre los primeros son pequeñas (pp), no significancia estadística. |
| Fuente / función | `cobertura.ranking_area`. |
| Nulos / ceros / empates | Empates exactos comparten puesto por rango mínimo; desempate alfabético estable. En los datos vigentes no hay empates exactos entre los primeros. |

### 3. Volumen anual captable al 20 % (indicador de decisión)

| Campo | Contenido |
|---|---|
| Tipo | Indicador de decisión. |
| Fórmula | 0,20 × Σ producción de los municipios cubiertos (escenario base = promedio 2021-2023). |
| Referencia | `cobertura.volumen_captable`; `cifras_hipotesis.py` (86.348 t Bugalagrande). |
| Unidad y periodo | t/año · base 2021-2023 (bajo/alto: extremos municipales 2014-2023). |
| Alcance / exclusiones | Fruta y plátano; no es capacidad instalada ni dimensionamiento. |
| Objetivo / responsable | No definidos. El 100 % de la base es definición, no meta operativa. |
| Subir / bajar | Más volumen captable = más potencial de acopio; no implica viabilidad. |
| Fuente / función | `cobertura.volumen_captable`, `cobertura.volumenes_escenarios`. |
| Nulos / ceros / empates | Municipio sin producción aporta 0 t; sin probabilidades asignadas a los escenarios. |

### 4. Razón de volumen captable frente al referente del sur (indicador de decisión)

| Campo | Contenido |
|---|---|
| Tipo | Indicador de contraste de hipótesis. |
| Fórmula | Volumen captable de la sede ÷ volumen captable de la mejor sede del sur (Vijes). |
| Referencia | `cifras_hipotesis.py` (Bugalagrande/Vijes = 1,89). |
| Unidad y periodo | Veces (adimensional) · base 2021-2023. |
| Alcance / exclusiones | La hipótesis pide ≥ 2,0 (el doble). 1,89 < 2,0: la parte de tamaño **no** se cumple. |
| Objetivo / responsable | Umbral de hipótesis = 2,0 (identificado como umbral, no como KPI). |
| Subir / bajar | "No alcanzar el doble" es el resultado de un contraste, no un juicio económico negativo. |
| Fuente / función | `cobertura.volumen_captable` (numerador y denominador se muestran por separado). |
| Nulos / ceros / empates | Si el denominador fuera 0 se muestra "n.d.". |

## Visuales del resumen (métricas de apoyo)

- **P1** área por sede (top 10 + sede + referente del sur). La línea de 50 % es el **umbral
  de la hipótesis**, rotulada como tal.
- **P2** volumen por escenario histórico; el 100 % es la definición de la base.
- **P3** composición productiva en **% de toneladas** (no área); piña destacada. "t por ha
  sembrada" es una razón descriptiva sobre área sembrada, **no** rendimiento agronómico.
- **P4** frecuencia de cada central entre los 54 escenarios de optimización (2024 y 2028).
  Son **frecuencias**, no probabilidades. Alcance distinto del histórico de área.

## Exposición logística (detalle plegado)

- Exposición sin caña: Σ |predicción − real| × minutos al nodo más cercano de la red base,
  horizonte 1, 2019-2023, sin caña de azúcar. Reducción del modelo ≈ 30,4 % frente al
  promedio de cinco años; ingenuo ≈ 32 %. Función: `cobertura.exposicion_sin_cana`
  (equivalente a `src/informe/cifras_3_3_y_3_4.py`, bloque 3.4.3).
- La valoración en COP es una **valoración de exposición anualizada** (÷ 5 años) con factor
  supuesto 250 COP/(t·min), **no un ahorro financiero realizado**.

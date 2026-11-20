# Caso aplicado: lectura del diagnóstico y la métrica de negocio en tres productos

Este documento aplica los resultados ya generados a tres decisiones concretas de planificación de la central de acopio. No se reentrena ni se reemplaza el modelo final; solo se interpretan las salidas existentes de `09_diagnostico_modelo.py` y `10_metrica_negocio.py` (horizonte h=1, año 2023, costo base 250 COP/(t·min)).

Los tres casos ilustran cuándo el modelo aporta, cuándo el ingenuo es mejor y cómo la **compuerta** (gate) evita usar el modelo donde no tiene evidencia previa.

## Caso 1 — Vid: el modelo sí aporta (h=1, 2023)

**Contexto.** Vid es un producto detallado con **confianza alta** (16 municipios, 24 años de historia, solo 12 % de valores repetidos). En 2023 su producción real fue de 19.618 t.

**Decisión.** ¿Se planifica la recolección de Vid con el pronóstico del modelo o con el ingenuo (último año observado)?

**Cifras (exposición logística bruta, 2023, t·min):**

| Alternativa | Exposición (t·min) | COP base | Δ vs sin modelo |
|---|---:|---:|---:|
| Sin modelo (promedio 5 años) | 149.084 | 37,3 M COP | 0,00 % |
| Ingenuo (último año) | 27.625 | 6,9 M COP | −81,47 % |
| Modelo final (ensamble) | **14.732** | **3,7 M COP** | **−90,12 %** |

**Interpretación.** El modelo reduce la exposición un **47 % adicional frente al ingenuo** (27.625 → 14.732 t·min). La compuerta 2022→2023 **incluye a Vid** porque en 2022 el ensamble mejoró al ingenuo un 5,16 % y su volumen (19.975 t) supera el umbral de 5.000 t.

**Acción.** Usar el pronóstico del modelo para programar la recolección de Vid en 2024. Etiquetar la serie como "confianza alta" en el tablero.

## Caso 2 — Caña panelera: el modelo no aporta, la compuerta lo excluye

**Contexto.** Caña panelera es detallada con **confianza alta** (32 municipios, 24 años). En 2023 produjo 299.193 t, pero su serie tiene saltos de más del 100 % y el diagnóstico muestra que el modelo empeora la exposición.

**Cifras (2023, t·min):**

| Alternativa | Exposición (t·min) | COP base | Δ vs ingenuo |
|---|---:|---:|---:|
| Sin modelo | 3.424.182 | 856 M COP | — |
| Ingenuo | 499.765 | 125 M COP | 0,00 % (referencia) |
| Modelo final | 795.482 | 199 M COP | **+59,17 %** (empeora) |
| Con compuerta | **499.765** | **125 M COP** | **0,00 %** (usa ingenuo) |

**Interpretación.** El modelo aislado aumenta la exposición un 59 % frente al ingenuo. La compuerta 2022→2023 **no selecciona** caña panelera: su mejora en 2022 fue solo del 3,90 % (por debajo del umbral del 5 %). En 2023 se usa el ingenuo, que es la opción más segura.

**Acción.** No usar el modelo para caña panelera. Mantener el ingenuo y revisar la serie en el próximo ciclo de validación antes de volver a considerar el modelo.

## Caso 3 — Horizonte largo (h=4 y h=5): el modelo gana para planificación de capacidad

**Contexto.** El diagnóstico por horizonte muestra que el error crece con el horizonte, pero el ensamble relativa al ingenuo mejora a partir de h=4.

**Cifras (todos los productos, 2019-2023, millones de t·min):**

| Horizonte | Sin modelo | Ingenuo | Modelo | Modelo vs ingenuo |
|---:|---:|---:|---:|---:|
| h=1 | 729,06 | 419,65 | 450,71 | −7,40 % (pierde) |
| h=2 | 733,86 | 471,81 | 489,46 | −3,74 % (pierde) |
| h=3 | 641,39 | 434,39 | 433,78 | +0,14 % (empata) |
| **h=4** | 481,21 | 337,21 | **310,67** | **+7,88 %** (gana) |
| **h=5** | 258,15 | 180,70 | **159,16** | **+11,92 %** (gana) |

**Interpretación.** En h=1 y h=2 el ingenuo es más difícil de superar (datos anuales, series cortas). En h=4 y h=5 el ensamble reduce la exposición entre un 7,9 % y un 11,9 % adicional frente al ingenuo. Estos son precisamente los horizontes que importan para dimensionar la central, definir zonas de acopio y negociar contratos de recolección.

**Acción.** Usar el ingenuo para decisiones operativas de corto plazo (h=1, h=2) y el ensamble para decisiones de inversión y capacidad de mediano/largo plazo (h=4, h=5).

## Resumen ejecutivo para el comité

| Caso | Producto / horizonte | Recomendación | Evidencia clave |
|---|---|---|---|
| 1 | Vid, h=1, 2023 | Usar modelo | −47 % exposición vs ingenuo; gate lo incluye |
| 2 | Caña panelera, h=1, 2023 | Usar ingenuo | +59 % exposición con modelo; gate lo excluye |
| 3 | Todos, h=4/h=5 | Usar modelo | +7,9 % y +11,9 % reducción vs ingenuo |

**Mensaje general:** el modelo no es universalmente mejor que el ingenuo. Su valor está en los horizontes largos y en productos con evidencia previa (gate). La métrica de negocio cuantifica esta decisión en t·min y COP, sin pretender ser un costo contable.

# Decisiones pendientes del modelo de optimización (para Samuel)

Autor: Alejandro Rendón Correa (arendonc2).

Este documento **no modifica** el código de Samuel. Reporta observaciones sobre el
modelo de optimización (`src/optimizacion/modelo_real.py` y `modelo_esqueleto.py`)
para que Samuel decida. Mi entrega de datos (zonas, excedentes, escenarios y el
adaptador) **ya está lista** y es independiente de estas decisiones.

Distinción clave:
- **Entrega de datos (mía):** está validada y funciona. El adaptador
  `src/arendonc2/adaptador.py` entrega excedentes municipales, zonas, proporciones
  y cobertura por `id_escenario` y año.
- **Validación del modelo (de Samuel):** los puntos de abajo afectan la
  interpretación de los resultados del solver, no la entrega de datos.

---

## P1 — La cuota nacional/exportación se aplica completa a cada destino

**Dónde:** `modelo_real.py` L107–113 y L156–159 (`costo_unitario_dist`).

```python
costo_unitario_dist[c] = sum(
    tiempos.get((c, d), 0) * (pct_nac if d in ("DEST_CALI","DEST_BOGOTA","DEST_MEDELLIN") else pct_exp)
    for d in [r["id_destino"] for _, r in destinos.iterrows()]
)
```

**Problema:** `pct_nac` (p. ej. 0.8) se multiplica por el tiempo a **cada** destino
nacional (Cali, Bogotá, Medellín) y `pct_exp` por **cada** destino de exportación
(Buenaventura, aeropuerto). El volumen nacional termina contándose 3 veces (una por
mercado nacional) y el de exportación 2 veces. El costo de distribución queda
inflado y sesga la elección de central hacia quien esté cerca de *todos* los
destinos, no hacia una asignación realista a un destino por flujo.

**Efecto:** la frontera de Pareto y la central elegida pueden cambiar.

**Decisión requerida:** repartir el volumen nacional entre los mercados nacionales
(p. ej. por población o a un único mercado) y el de exportación entre los puntos de
salida, de modo que las cuotas sumen 1 **a través** de los destinos de cada grupo,
no por destino.

---

## P2 — Falta el costo del tramo satélite → central

**Dónde:** función objetivo de `modelo_real.py` (L100–118). Sólo hay Z1 (municipio→
satélite, L101–104) y Z2 (central→destinos, L116–118). La variable `w[(s,c)]`
(satélite→central, L80, L95–97) **no aparece en ningún término de costo**.

**Problema:** el segundo eslabón de la red (acopio satélite → central) no tiene
costo, aunque la formulación en `docs/formulacion_optimizacion.md` (R6) habla de
conservación de flujo entre ambos niveles. El modelo elige satélites y central sin
penalizar la distancia entre ellos.

**Decisión requerida:** ¿se agrega `sum oferta_satélite * tiempo(s,c) * w[s,c]` al
objetivo? Si no, dejar explícito que el tramo satélite→central es gratuito por
supuesto.

---

## P3 — No está definido si las zonas restringen las asignaciones

**Dónde:** `modelo_real.py` L85–97 (restricciones de asignación). `z[(m,s)]` permite
asignar cualquier municipio a cualquier satélite, sin referencia a `zonas.csv`.

**Problema:** mi tarea #2 produce zonas de acopio contiguas, pero el solver no las
usa como restricción (un municipio podría asignarse a un satélite de otra zona).

**Decisión requerida:** ¿las zonas son (a) sólo informativas, (b) una restricción
dura (`z[m,s]=0` si m y s están en zonas distintas), o (c) el conjunto de satélites
candidatos se limita a un municipio por zona? Mi adaptador entrega la columna `zona`
por municipio para cualquiera de las tres opciones.

---

## P4 — "Frontera de Pareto" sin filtrar dominancia

**Dónde:** `calcular_frontera_pareto` (L181–205) y uso en `app.py`
(`calcular_frontera_pareto`, pantalla 3).

**Problema:** se barren 11 valores de λ y se grafican todos los puntos (z1, z2). No
se filtran puntos **dominados** (otro con menor z1 **y** menor z2). Dos λ distintos
pueden dar la misma solución o una dominada, y el gráfico los muestra como si fueran
frontera.

**Efecto:** el gráfico puede mostrar puntos que no pertenecen a la frontera eficiente.

**Decisión requerida:** filtrar por no-dominancia antes de graficar y de reportar
"frontera de Pareto", o renombrar a "barrido de λ".

---

## P5 — Conservación de flujo: formulación vs implementación

**Dónde:** `docs/formulacion_optimizacion.md` R6 (conservación de flujo en el
satélite) vs `modelo_real.py`, que **no implementa R6 ni R7** (capacidad).

**Problema:** la formulación documenta que lo que entra a un satélite sale hacia la
central (R6) y una capacidad opcional (R7), pero el código no incluye esas
restricciones. El modelo funciona, pero no corresponde 1:1 con el documento.

**Decisión requerida:** implementar R6/R7 o actualizar la formulación para marcar
esas restricciones como "no activas en la versión actual".

---

## P6 — Tiempos faltantes tratados silenciosamente como cero

**Dónde:** `modelo_real.py` L102, L112, L154, L158: `tiempos.get((m, s), 0)` y
`tiempos.get((c, d), 0)`.

**Problema:** si un par (origen, destino) falta en la matriz, el tiempo se toma como
**0**, es decir, "gratis e instantáneo". Eso favorecería artificialmente ubicaciones
con datos faltantes y lo haría en silencio (sin error ni aviso).

**Verificación (realizada):** la matriz actual **sí está completa**: 1 722 pares
municipio×municipio y 210 pares municipio×destino (incluye `DEST_CALI`,
`DEST_BOGOTA`, `DEST_MEDELLIN`, `DEST_BUENAVENTURA`, `DEST_AEROPUERTO_PALMIRA`), sin
faltantes. Es decir, **hoy** el `0` por defecto no se activa y Z2 no es cero. El
riesgo es latente: si la matriz cambia (otros destinos, otros municipios, otra
versión), los huecos se volverían 0 sin que nadie lo note.

**Decisión requerida:** reemplazar `tiempos.get((a, b), 0)` por una búsqueda que
lance excepción o registre advertencia cuando falte un par, en lugar de asumir 0.
Además, toda la matriz tiene `metodo = "aproximado"` (distancia recta × 1.4 ÷ 45
km/h), no tiempos de ruteo reales; conviene dejarlo explícito en el informe.

---

## Resumen para Samuel

| # | Problema | Efecto | Bloquea mi entrega |
|---|----------|--------|--------------------|
| P1 | Cuota completa por destino | Z2 inflado, central sesgada | No |
| P2 | Sin costo satélite→central | Red sin penalizar 2º tramo | No |
| P3 | Zonas no restringen asignación | Zonas sólo informativas | No |
| P4 | Pareto sin filtrar dominancia | Puntos dominados en el gráfico | No |
| P5 | R6/R7 no implementadas | Doc ≠ código | No |
| P6 | Tiempos faltantes = 0 (riesgo latente; matriz hoy completa) | Huecos futuros = gratis sin aviso | No |

Ninguno bloquea la entrega de datos. Para resolver P1, P3 y P6, el adaptador ya
entrega zonas, proporciones y excedentes por municipio con unidades validadas.

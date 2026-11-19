# Corrida ponderada por valor (SIPSA) vs toneladas

Estos archivos comparan la ubicación óptima cuando el costo logístico se mide en
**toneladas × minutos** (modelo actual) contra una ponderación por **valor**
(toneladas × precio SIPSA). Los genera `src/optimizacion/corrida_valor.py`.

## Comando

```powershell
# Compara los 54 escenarios de 2024 y 2028 (27 por año)
python src/optimizacion/corrida_valor.py

# Solo un año o un escenario
python src/optimizacion/corrida_valor.py --anios 2024
python src/optimizacion/corrida_valor.py --escenario 2024_Obase_Cbase_M50_50
```

Parámetros de la corrida guardada: `k = 5`, `lambda = 0.5`, brecha solicitada
`0` y límite de 120 s por solve, con reintento de 600 s si un solve queda
`FEASIBLE`. Los 54 escenarios quedaron `OPTIMAL`; la brecha efectiva máxima fue
`4,3e-6` (cero en la práctica).

## Método

Para cada escenario se calcula el valor del excedente municipal:

\[
V_m = \sum_{p} \text{excedente}_{p,m} \times 1000 \times \text{precio\_SIPSA}_{p}
\]

y se reemplaza el excedente que ve el solver por:

\[
q^{eq}_m = Q \times \frac{V_m}{V_{total}}
\]

donde \(Q\) es el total de toneladas conocidas. Así, el modelo resuelve la misma
formulación de localización, pero cada municipio pesa según el valor de su
producción. El total de \(q^{eq}\) se normaliza a \(Q\) para conservar la escala.

- Se usa `precio_cop_kg` de `data/results/ML_Ce/oferta_escenarios_valor.csv`,
  no `valor_*_cop`, porque este último valora la oferta total y aquí interesa el
  excedente que realmente se transporta.
- Los productos sin precio reciben el precio de referencia ponderado del
  escenario. Su participación se reporta en `cobertura_valor_pct`; en 2024/2028
  es **99,37 %–100 %**.
- No se modifica `modelo_real.py`: se usa `dataclasses.replace` para cambiar
  solo el excedente que recibe el solver.
- Si un solve no certifica optimalidad en 120 s, se reintenta con 600 s para no
  reportar como resultado un artefacto del límite de tiempo. La corrida guardada
  no necesitó reintentos: todos los solves fueron `OPTIMAL`.

## Archivos

| Archivo | Contenido |
|---|---|
| `comparacion_toneladas_vs_valor.csv` | Una fila por escenario: central y satélites en cada criterio, objetivos en t·min y COP·min, deltas y cobertura de valor. |
| `comparacion_toneladas_vs_valor_resumen.csv` | Resumen por año: número de cambios de central/satélites y magnitudes de los deltas. |
| `metadata_valor.json` | Parámetros, commit y huellas SHA256 de las entradas y salidas. |

## Columnas principales

| Columna | Significado |
|---|---|
| `central_ton` | Central elegida minimizando t·min. |
| `central_valor` | Central elegida minimizando el costo ponderado por valor. |
| `misma_central` | `True` si ambos criterios eligen la misma central. |
| `satelites_ton`, `satelites_valor` | Conjuntos de satélites de cada red. |
| `obj_ton_red_ton` | Objetivo en t·min de la red optimizada por toneladas. |
| `obj_ton_red_valor` | Objetivo en COP·min de la red optimizada por toneladas. |
| `obj_valor_red_ton` | Objetivo en t·min de la red optimizada por valor. |
| `obj_valor_red_valor` | Objetivo en COP·min de la red optimizada por valor. |
| `delta_ton_pct` | Cuánto más cuesta la red por valor en t·min (positivo = más caro). |
| `delta_valor_pct` | Cuánto cambia la red por valor en COP·min (negativo = ahorra). |
| `cobertura_valor_pct` | % del excedente con precio SIPSA observado. |
| `precio_ref_cop_kg` | Precio promedio ponderado por excedente, COP/kg. |

## Resultados principales

- **La central cambia en 21 de 54 escenarios**: 12 de 27 en 2024 y 9 de 27 en
  2028. En los 33 restantes coincide.
- **El escenario base se mantiene**: `2024_Obase_Cbase_M80_20` y
  `2028_Obase_Cbase_M80_20` siguen eligiendo **Bugalagrande**. El escenario base
  es robusto al criterio de valor.
- Patrones de cambio:
  - `M50_50` con oferta base/baja: **Riofrío → Andalucía** (2024 y 2028).
  - `M50_50` con oferta alta: **Riofrío → Bugalagrande** en 2024 (consumo alto)
    y **Andalucía → Bugalagrande** en 2028.
  - `M80_20` con oferta alta: **Bugalagrande → Bolívar** (2024 y 2028).
  - `M80_20` con oferta baja en 2024: **Sevilla → Zarzal**.
- **Costo del cambio**: en los casos con cambio de central, la red por valor
  cuesta entre **0,05 % y 0,70 % más en t·min** y ahorra entre **0,07 % y
  0,63 % en COP·min**. En promedio, +0,25 % en t·min y −0,22 % en COP·min.
  Es un tradeoff pequeño pero consistente: se sacrifica muy poco costo logístico
  para alinear la ubicación con el valor de la producción.
- **Satélites**: cambian en los 54 escenarios. En muchos casos son óptimos
  alternativos con el mismo costo; la comparación robusta es la central y el
  costo, no la identidad exacta de los satélites.

## Lectura para el informe

La ponderación por valor no invalida el modelo en toneladas: lo complementa.
Para el escenario base la decisión es estable (Bugalagrande), lo que permite
defender el costo logístico en t·min como criterio principal. En escenarios de
mezcla 50/50 o de oferta alta, el valor sí mueve la central hacia Andalucía,
Bolívar o Zarzal, con un sobrecosto logístico inferior al 1 %. Esa sensibilidad
es la que el profesor pidió mostrar.

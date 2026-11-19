# Resultados de optimización para el informe final

Estos archivos los genera `src/optimizacion/generar_resultados.py` y contienen los
resultados que antes solo se veían en la pantalla 3 del tablero o en consola.

## Comando

```powershell
# Genera Pareto + estabilidad 2024/2028 + comparación libre vs zonas
python src/optimizacion/generar_resultados.py

# Si se quieren los 5 años de escenarios.csv (135 escenarios)
python src/optimizacion/generar_resultados.py --anios 2024 2025 2026 2027 2028

# Regenerar solo una parte
python src/optimizacion/generar_resultados.py --solo pareto
python src/optimizacion/generar_resultados.py --solo estabilidad comparacion
```

Parámetros de la corrida guardada: escenario base `2024_Obase_Cbase_M80_20`,
`k = 5` satélites, `lambda = 0.5` para estabilidad/comparación, brecha solicitada
`0` y límite de 120 s por solve. Todos los escenarios reportados quedaron
`OPTIMAL` con brecha efectiva `0`.

## Archivos

| Archivo | Contenido |
|---|---|
| `barrido_lambda_base.csv` | Los 11 valores de lambda (0.0 a 1.0) del escenario base, con central, satélites y costos. |
| `frontera_pareto_base.csv` | Soluciones no dominadas del barrido anterior. |
| `estabilidad_escenarios.csv` | Los 27 escenarios de `escenarios.csv` para 2024 y 2028 (54 filas), con central, satélites, costos y si cambian respecto al escenario base del mismo año. |
| `comparacion_libre_vs_zonas.csv` | Mismo escenario base resuelto en modo `libre` y en modo `zonas`, con deltas. |
| `comparacion_libre_vs_zonas_resumen.csv` | Una fila con la comparación directa libre vs zonas. |
| `metadata.json` | Parámetros, solver, commit y huellas SHA256 de entradas y salidas. |

## Columnas de costos (t·min = toneladas × minutos)

| Columna | Significado |
|---|---|
| `costo_recoleccion` | A1: municipio → satélite. |
| `costo_satelite_central` | A2: satélite → central. |
| `costo_distribucion` | B: central → destinos. |
| `A` | A1 + A2. |
| `B` | Igual a `costo_distribucion`. |
| `costo_total` | Objetivo que minimiza el solver: `lambda*A + (1-lambda)*B`. |
| `costo_total_suma` | Suma física de los tres tramos: `A1 + A2 + B` (sin ponderar). |

`costo_total` y `costo_total_suma` no son lo mismo. El primero es el objetivo
ponderado de la optimización; el segundo es el costo físico total. Para el
escenario base con `lambda=0.5`, `costo_total = 0.5 * costo_total_suma`.

Las columnas `satelites`, `satelites_cods` y `satelites_zonas` listan los mismos
k satélites en el mismo orden: nombre, código DANE y zona.

## Resultados principales de esta corrida

### Frontera de Pareto (escenario base)

| lambda | Central | A (t·min) | B (t·min) | Objetivo (t·min) |
|---:|---|---:|---:|---:|
| 0.4 | Bugalagrande | 71.191.244 | 263.230.918 | 167.211.081 |
| 0.1 | Sevilla | 74.049.808 | 261.684.255 | 242.920.810 |

El barrido completo está en `barrido_lambda_base.csv`; los demás lambda
produjeron soluciones dominadas o duplicadas.

### Estabilidad (2024 y 2028)

- 54 escenarios resueltos: 27 por año (3 ofertas × 3 consumos × 3 mezclas).
- En 2024 la central cambia en **18 de 27** escenarios respecto al base
  `2024_Obase_Cbase_M80_20`; en 2028 también en **18 de 27**.
- Centrales observadas: Bugalagrande (18), Riofrío (15), Yotoco (12), Sevilla (6),
  Andalucía (3).
- La mezcla nacional/exportación es el factor que más mueve la central:
  - `80_20`: Bugalagrande o Sevilla.
  - `50_50`: Bugalagrande, Riofrío o Andalucía.
  - `20_80`: Yotoco o Riofrío.

### Comparación libre vs zonas (escenario base)

| Modo | Central | Objetivo (t·min) | Diferencia |
|---|---|---|---:|
| libre | Bugalagrande | 167.211.081 | — |
| zonas | Bugalagrande | 168.052.318 | +0,50 % |

La central coincide, pero los satélites cambian: el modo zonas usa uno por zona
(Bugalagrande, San Pedro, Versalles, Yotoco, Zarzal) y encarece el objetivo en
0,50 % (841.237 t·min). No es un artefacto de tolerancia: ambas soluciones son
`OPTIMAL` con brecha 0.

## Notas

- **Cobertura parcial:** 73,82 % de la oferta tiene consumo FAOSTAT definido; los
  productos pendientes quedan fuera del volumen de optimización.
- **Óptimos alternativos:** cuando hay empates exactos, el solver puede devolver
  otro conjunto de satélites con el mismo costo. La central y los costos son la
  referencia; el conjunto de satélites puede variar entre corridas.
- **No editar a mano:** estos CSV se regeneran con el script. Si cambian los datos
  de entrada, vuelve a ejecutarlo.
- La verificación de estos archivos está en
  `python src/optimizacion/test_resultados_opt.py`.

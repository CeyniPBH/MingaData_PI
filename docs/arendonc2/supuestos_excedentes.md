# Supuestos de excedentes (Tarea #3)

Autor: Alejandro Rendón Correa (arendonc2). Resultados reproducibles con
`python src/arendonc2/excedentes.py`.

## Qué calcula

Por producto, municipio y año de pronóstico (2024–2028), y para las 9 combinaciones
de escenario de oferta (bajo/base/alto) × escenario de consumo (bajo/base/alto):

```
consumo_local_t      = kg_per_capita_anio * poblacion * factor_consumo / 1000
excedente_municipal_t = max(0, oferta_t - consumo_local_t)
```

El excedente municipal se recorta a ≥ 0 **antes** de agregar por zona.

El excedente potencial **no** es ventas, demanda comprobada ni aptitud para
exportación. Es sólo oferta pronosticada que supera un consumo local estimado.

## Fuentes y unidades

| Insumo | Fuente | Unidad | Cobertura |
|--------|--------|--------|-----------|
| Oferta pronosticada | `data/results/ML_Ce/oferta_escenarios.csv` (Ceyni) | t/año | 44 productos, 42 municipios, 2024–2028 |
| Consumo per cápita | `data/clean/consumo_percapita.csv` (FAOSTAT, Colombia) | kg/persona/año | 2020–2023 |
| Población municipal | `data/clean/poblacion_municipal.csv` (DANE) | personas | 42 municipios, 2024–2028 |
| Zonas | `data/results/zonas.csv` (Tarea #2) | — | 42 municipios en 5 zonas |

**Población:** DANE, *Proyecciones de población a nivel municipal por área
2020–2035, actualización post COVID-19* (base CNPV 2018). Se usa **únicamente el
TOTAL municipal anual** (fila `ÁREA GEOGRÁFICA = Total`). No se suman
Total + Cabecera + Rural. Generada con `src/arendonc2/poblacion.py`.

## Supuestos autorizados y cómo se aplicaron

1. **Factores de consumo** bajo/base/alto = 0.8 / 1.0 / 1.2 sobre el consumo base
   (`config/arendonc2/parametros.yaml`).
2. **Año de consumo de referencia:** se usa el último año FAOSTAT disponible
   (**2023**) y se aplica a todos los años proyectados 2024–2028, porque no hay
   serie futura de consumo per cápita. Es una aproximación conservadora: supone
   consumo per cápita constante en el horizonte.
3. **Reparto de categorías FAOSTAT amplias:** cuando una categoría FAOSTAT abarca
   varios cultivos del Valle, su consumo per cápita se **reparte** entre ellos
   según su producción histórica regional 2019–2023. Las cuotas suman 1 dentro de
   cada categoría, de modo que el consumo de una categoría **no se cuenta varias
   veces**. Es una aproximación para no sobreestimar el consumo por cultivo.
4. **Productos sin equivalencia defendible** quedan **pendientes y visibles**: su
   consumo local se fija en 0 pero con la bandera `consumo_pendiente = 1`. Nunca
   se sustituye un consumo desconocido por cero de forma silenciosa.
5. **Caña de azúcar** se excluye del análisis (industrial, no consumo local directo).

## Correspondencia FAOSTAT y cuotas de reparto

Mapeo completo en `config/arendonc2/mapeo_faostat.yaml`; tabla con cuotas en
`data/results/arendonc2/faostat_mapeo_cuotas.csv` y consumo per cápita resultante
por producto en `data/results/arendonc2/faostat_consumo_percapita_producto.csv`.

### Mapeos directos (suma de ítems, sin reparto)

| Producto | Ítem(s) FAOSTAT | kg/persona (2023) |
|----------|-----------------|-------------------|
| Plátano | Plantains | 37.18 |
| Cítricos | Oranges/Mandarines + Lemons/Limes + Grapefruit + Citrus Other | 27.31 |
| Yuca | Cassava and products | 16.85 |
| Piña | Pineapples and products | 12.14 |
| Cebolla Larga | Onions | 10.98 |
| Caña panelera | Sugar non-centrifugal | 20.03 |
| Vid | Grapes (excl wine) | 1.29 |
| Cacao | Cocoa Beans and products | 0.81 |
| Café | Coffee and products | 1.44 |
| Coco | Coconuts – Incl Copra | 1.97 |
| Té | Tea (including mate) | 0.02 |
| Stevia | Sweeteners, Other | 2.16 |

### Categorías repartidas por producción 2019–2023 (cuotas suman 1)

- **Fruits, other (60.26 kg/persona)** se reparte entre 21 frutas. Cuotas
  principales: Aguacate 45.5 %, Papaya 10.7 %, Lulo 10.7 %, Guayaba 8.7 %,
  Maracuyá 7.4 %, Borojó 3.4 %, Guanábana 3.2 %, Mora 2.8 %, Mango 2.0 %,
  Chontaduro 1.9 %, Granadilla 1.7 %, resto < 1 %.
- **Bananas (13.37 kg)** → Banano 97.5 %, Bananito 2.5 %.
- **Roots, Other (1.30 kg)** → Arracacha 84.0 %, Papachina 16.0 %.
- **Nuts and products (1.30 kg)** → Sacha Inchi 53.5 %, Macadamia 46.5 %.
- **Vegetables, other (22.42 kg)** → Ají 100 % (único del Valle en la categoría).

> El reparto es una **aproximación**: FAOSTAT reporta consumo por categoría, no
> por cultivo específico del Valle. Se usa producción regional como proxy de la
> estructura de consumo, suponiendo que lo producido refleja lo consumido.

### Productos pendientes (sin equivalencia alimentaria FAOSTAT)

| Producto | Motivo |
|----------|--------|
| Flores y follajes | Ornamental, no alimentario. Excedente = oferta completa (consumo no asumido cero, marcado pendiente). |
| Aromáticas | Hierbas aromáticas/medicinales sin ítem de consumo FAOSTAT equivalente. |
| Sábila | Aloe vera, uso cosmético/medicinal; sin ítem de consumo alimentario. |

Estos tres productos aportan < 0.3 % de la oferta total, por lo que la cobertura
de consumo definido se mantiene ≈ 99.7–99.98 % según año y escenario (ver
`data/results/arendonc2/excedentes_cobertura.csv`).

## Sobreoferta (alerta coyuntural)

Regla: `oferta_t > media_hist + 1·desv_estándar_muestral` de la producción
2019–2023 (producto × municipio). Si hay menos de 3 años de historia, la alerta
queda **sin determinar** (`sobreoferta = NaN`). Depende sólo de la oferta, no del
escenario de consumo, para **no triplicar** los conteos entre los tres escenarios
de consumo. En el escenario oferta base / consumo base 2024: 519 marcas de
sobreoferta sobre 3 150 series evaluadas; 320 quedaron sin determinar por historia
insuficiente.

## Auditoría de recortes

El pronóstico de oferta puede tener límites inferiores negativos (escenario bajo).
Se recortan a 0 en esta etapa y se registran los valores originales en
`data/results/arendonc2/excedentes_auditoria_recortes.csv` (601 filas). Los
archivos fuente (`oferta_escenarios.csv`) quedan intactos.

## Salidas

| Archivo | Contenido |
|---------|-----------|
| `data/results/excedentes.csv` | Excedente municipal por producto, año y las 9 combinaciones. Claves: producto, cod_dane, anio, escenario_oferta, escenario_consumo. |
| `data/results/arendonc2/excedentes_por_zona.csv` | Excedente agregado por zona. |
| `data/results/arendonc2/excedentes_cobertura.csv` | Cobertura en toneladas y % por año y escenario. |
| `data/results/arendonc2/excedentes_pendientes.csv` | Productos pendientes y motivo. |
| `data/results/arendonc2/faostat_mapeo_cuotas.csv` | Correspondencia FAOSTAT y cuotas de reparto. |
| `data/results/arendonc2/excedentes_auditoria_recortes.csv` | Auditoría de recortes negativos. |

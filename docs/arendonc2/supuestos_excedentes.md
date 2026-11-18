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

## Correspondencia FAOSTAT y cuotas de reparto (auditada)

Regla de unidades (auditoría): la producción del Valle se mide en toneladas de
cultivo **cosechado en finca** (forma primaria); FAOSTAT mide disponibilidad del
**producto consumible** (kg/cápita/año, Food Balance Sheets). Una equivalencia es
**utilizable** sólo si ambas formas físicas coinciden (fresco vs fresco). Si media
una transformación materia prima → consumible que requiere un factor de conversión
**no respaldado** por una fuente del repositorio, el producto queda **pendiente**.
El reparto por producción histórica **no** sustituye esa conversión.

Tabla completa (una fila por producto, con unidad, tipo, factor, fuente y estado):
`data/results/arendonc2/auditoria_mapeo_faostat.csv`
(generada por `src/arendonc2/auditar_mapeo.py`). Mapeo en
`config/arendonc2/mapeo_faostat.yaml`; cuotas en
`data/results/arendonc2/faostat_mapeo_cuotas.csv`.

**Resultado: 30 productos utilizables, 13 pendientes.** Ningún ítem FAOSTAT se usa
en dos grupos distintos (verificado en código).

### Utilizables — mapeos directos (suma de ítems, fresco vs fresco)

| Producto | Ítem(s) FAOSTAT | kg/persona (2023) |
|----------|-----------------|-------------------|
| Plátano | Plantains | 37.18 |
| Cítricos | Oranges/Mandarines + Lemons/Limes + Grapefruit + Citrus Other | 27.31 |
| Yuca | Cassava and products | 16.85 |
| Piña | Pineapples and products | 12.14 |
| Vid | Grapes (excl wine) | 1.29 |

### Utilizables — categorías repartidas por producción 2019–2023 (cuotas suman 1)

- **Fruits, other (60.26 kg/persona)** se reparte entre 21 frutas frescas. Cuotas
  principales: Aguacate 45.5 %, Papaya 10.7 %, Lulo 10.7 %, Guayaba 8.7 %,
  Maracuyá 7.4 %, Borojó 3.4 %, Guanábana 3.2 %, Mora 2.8 %, Mango 2.0 %,
  Chontaduro 1.9 %, resto < 2 %.
- **Bananas (13.37 kg)** → Banano 97.5 %, Bananito 2.5 %.
- **Roots, Other (1.30 kg)** → Arracacha 84.0 %, Papachina 16.0 %.

> El reparto es una **aproximación**: FAOSTAT reporta consumo por categoría, no por
> cultivo. Se usa producción regional como proxy de la estructura de consumo.
> Sólo se aplica entre cultivos frescos de la misma forma física que el ítem.

### Pendientes — conversión materia prima → consumible no respaldada (10)

| Producto | Unidad producción | Ítem FAOSTAT | Motivo (factor faltante) |
|----------|-------------------|--------------|--------------------------|
| Café | café pergamino | Coffee and products | pergamino → verde/tostado (0.63 es sólo para precio, no masa) |
| Caña panelera | caña (tallo) | Sugar non-centrifugal | caña → panela ~10 % (0.10 es sólo para precio); mismatch ~10× |
| Cacao | grano de cacao | Cocoa Beans and products | consumo (incl. chocolate e importaciones) > producción local |
| Coco | coco fresco | Coconuts – Incl Copra | fresco → copra (seca) sin factor |
| Macadamia | nuez con cáscara | Nuts and products | cáscara → almendra sin factor |
| Sacha Inchi | semilla (oleaginosa) | Nuts and products | oleaginosa, no fruto seco de mesa |
| Stevia | hoja | Sweeteners, Other | hoja → glucósidos refinados sin factor |
| Té | hoja/procesado | Tea (including mate) | forma/origen incierto; volumen marginal |
| Ají | ají fresco | Vegetables, other | asignar toda una categoría amplia a un condimento menor sobreestima ~17× |
| Cebolla Larga | cebolla larga (rama) | Onions | Onions es bulbo, no cebolla de rama |

### Pendientes — no alimentario / sin ítem FAOSTAT (3)

| Producto | Motivo |
|----------|--------|
| Flores y follajes | Ornamental, no alimentario. |
| Aromáticas | Hierbas aromáticas/medicinales sin ítem de consumo FAOSTAT. |
| Sábila | Aloe vera, uso cosmético/medicinal. |

Los 13 pendientes entran al análisis con su excedente completo (consumo 0 pero
marcado `consumo_pendiente = 1`, nunca cero silencioso). Esto **baja la cobertura**
de consumo definido frente al ≈ 99.8 % de la versión anterior no auditada. El
cambio es deliberado: no se infla la cobertura con equivalencias de unidad
indefendibles.

### Cobertura por año y escenario de oferta

**Definición:** `cobertura = oferta_con_consumo_t / oferta_total_t`, ambas en
toneladas. El **denominador** es la oferta total pronosticada de todos los
productos (excepto Caña de azúcar) para ese año y escenario de oferta. El numerador
es la oferta de los 30 productos con consumo FAOSTAT definido (los 13 pendientes
quedan fuera del numerador). La cobertura **no depende del escenario de consumo**
(los pendientes tienen consumo 0 en bajo/base/alto por igual); por eso se reporta
por año × escenario de oferta.

| Año | Oferta (bajo) | Oferta (base) | Oferta (alto) |
|-----|--------------:|--------------:|--------------:|
| 2024 | 77.4 % | 73.8 % | 79.8 % |
| 2025 | 81.9 % | 74.0 % | 83.7 % |
| 2026 | 84.5 % | 74.1 % | 85.5 % |
| 2027 | 89.4 % | 74.2 % | 88.0 % |
| 2028 | 90.7 % | 74.2 % | 89.3 % |

Tabla completa (toneladas y %) en `data/results/arendonc2/excedentes_cobertura.csv`.
La cobertura sube en años y escenarios de oferta altos porque el peso relativo de
los productos pendientes (varios de ellos de alto volumen, como café y caña
panelera) cae cuando crece la oferta de los productos frescos cubiertos.

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

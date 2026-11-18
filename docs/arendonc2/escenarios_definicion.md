# Definición de escenarios para la optimización (Tarea #4)

Autor: Alejandro Rendón Correa (arendonc2). Reproducible con
`python src/arendonc2/escenarios.py`. Salida: `data/results/escenarios.csv`.

## Espacio de escenarios

Cada escenario cruza tres ejes, para **27 combinaciones por año**:

1. **Oferta** (de Ceyni): bajo / base / alto — intervalos del pronóstico.
2. **Consumo** (de mi tarea #3): bajo / base / alto — factores 0.8 / 1.0 / 1.2
   sobre el consumo per cápita FAOSTAT.
3. **Mezcla nacional/exportación:** 80/20, 50/50, 20/80.

Con 5 años (2024–2028) y 5 zonas, `escenarios.csv` tiene
27 × 5 × 5 = **675 filas**. El identificador es
`{anio}_O{oferta}_C{consumo}_M{mezcla}`, p. ej. `2024_Obase_Cbase_M80_20`.

## Cómo se calcula cada fila

Para una zona, año y combinación:

```
excedente_zona     = suma del excedente municipal (recortado a >= 0) de la zona,
                     SÓLO de productos con consumo conocido (pendientes excluidos)
volumen_nacional    = excedente_zona * pct_nacional
volumen_exportacion = excedente_zona * pct_exportacion
```

Los productos pendientes (consumo desconocido) tienen excedente nulo y **no
aportan volumen**: su oferta no entra en `excedente_zona` ni en los volúmenes de
optimización.

Se cumple por construcción `pct_nacional + pct_exportacion = 1` y
`volumen_nacional + volumen_exportacion = excedente_zona`.

El excedente de cada año/combinación sale directo de la tarea #3; **nunca se suman
años distintos** para una ejecución anual.

## Columnas

Contrato de Samuel (se conserva): `id_escenario, oferta, consumo, pct_nacional,
pct_exportacion, zona, volumen_nacional, volumen_exportacion`.
Añadidas: `anio`, `alcance`, `cobertura_oferta_pct`.

- **alcance:** `productos_alimentarios_con_equivalencia_FAOSTAT`. Los 13 productos
  pendientes (sin equivalencia de unidad defendible) **no aportan volumen**; su
  oferta queda fuera de `volumen_nacional`/`volumen_exportacion`. Se reflejan en
  `cobertura_oferta_pct` < 100.
- **cobertura_oferta_pct:** % de la oferta de la zona con consumo FAOSTAT definido
  (denominador = oferta total del alcance, incluidos los pendientes).

## Las mezclas son escenarios de sensibilidad, no observaciones

Las proporciones 80/20, 50/50 y 20/80 son **supuestos de sensibilidad**, elegidos
para cubrir un rango amplio (predominio nacional, equilibrio, predominio
exportador). **No** representan participaciones observadas de exportación.

> **Pendiente de justificación empírica (backlog #4):** falta cruzar con UN Comtrade
> o DANE la participación histórica de exportación por familia (frutas, café, cacao,
> panela, almidones) para decir cuál de las tres mezclas es la más realista por
> producto. Mientras eso siga pendiente, las mezclas deben presentarse como
> **sensibilidad**, no como porcentajes reales. Esta tarea entrega la estructura
> (27 escenarios) lista para re-ponderar cuando llegue ese dato.

El excedente potencial **no** es demanda comprobada ni aptitud para exportación.

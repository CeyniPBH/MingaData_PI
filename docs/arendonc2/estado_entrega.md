# Estado de la entrega — tareas #2, #3, #4 (arendonc2)

Autor: Alejandro Rendón Correa. Rama `feat/arendonc2-zonas-excedentes`.
Estado frente a los criterios de aceptación de cada issue.

## #2 — Zonas de acopio

**Estado: implementada. Pendiente de aceptación de GADM como sustituto del MGN del DANE.**

- 42 municipios asignados una sola vez; 5 zonas; un centro de referencia por zona.
- Vecindad Queen: 1 componente conexa, 0 islas. Todas las particiones k = 3..8 son
  100 % espacialmente conexas.
- Ward con restricción de conectividad; espacio en coordenadas proyectadas
  (EPSG:3116, escala común). k = 5 publicado y configurable.
- Entregables: `data/results/zonas.csv`, geometrías de zona, vecindad, métricas de k.
- **Desviación del backlog:** el issue pedía polígonos del MGN del DANE; se usó
  GADM 4.1. Documentado en `geometrias_fuente_y_desviacion.md`; emparejamiento
  1:1 publicado en `emparejamiento_gadm_dane.csv`. Requiere aceptación del equipo.

## #3 — Excedentes como escenario

**Estado: implementada con cobertura parcial. 13 productos pendientes.**

- 9 combinaciones (oferta × consumo) por producto, municipio y año (2024–2028).
- 0 excedentes negativos; totales municipales = zonales; sin duplicados de clave.
- 30 productos con consumo FAOSTAT utilizable (fresco vs fresco); **13 pendientes**:
  10 por conversión materia prima → consumible no respaldada (café, caña panelera,
  cacao, coco, macadamia, sacha inchi, stevia, té, ají, cebolla larga) y 3 no
  alimentarios (flores, aromáticas, sábila).
- Tratamiento de los pendientes (criterio acordado): **consumo desconocido = nulo
  (NaN) con motivo**; **excedente desconocido = nulo (NaN)**; **oferta original
  conservada**; **excluidos de los volúmenes de escenarios y del adaptador de
  optimización**. No se sustituye por 0 ni se cuentan como excedente disponible.
- **Cobertura parcial** (oferta con consumo definido / oferta total, en toneladas),
  por año y escenario de oferta: base ≈ 74 %, bajo 77–91 %, alto 80–89 %
  (`excedentes_cobertura.csv`).
- Entregables: `data/results/excedentes.csv`, agregados por zona, cobertura,
  pendientes, cuotas FAOSTAT, auditoría de recortes; `supuestos_excedentes.md`.

## #4 — Tabla de escenarios para la optimización

**Estado: implementada como análisis de sensibilidad. Pendiente justificación empírica de las mezclas.**

- 27 combinaciones por año (3 oferta × 3 consumo × 3 mezclas), 675 filas, 5 zonas.
- `pct_nacional + pct_exportacion = 1`; `volumen_nacional + volumen_exportacion =`
  excedente de la zona en esa combinación y año (verificado).
- Contrato de Samuel conservado + `anio`, `alcance`, `cobertura_oferta_pct`.
- **Pendiente:** las mezclas 80/20, 50/50, 20/80 son escenarios de **sensibilidad**,
  sin respaldo empírico (falta cruzar participación de exportación por familia con
  Comtrade/DANE). Se mantienen como sensibilidad, no como porcentajes observados
  (`escenarios_definicion.md`).
- Entregable: `data/results/escenarios.csv`.

## Integración con Samuel

- Adaptador `src/arendonc2/adaptador.py` (por `id_escenario` y año; valida claves,
  unidades, duplicados y coherencia municipal↔zonal; selecciona el año exacto).
- Pantalla "2b. Zonas de acopio" en el tablero, con advertencia de cobertura parcial.
- Observaciones al modelo de Samuel (P1–P6) en `decisiones_pendientes_samuel.md`,
  **sin modificar su formulación**.

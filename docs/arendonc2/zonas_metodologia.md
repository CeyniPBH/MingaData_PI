# Zonas de acopio: metodología y selección de k (Tarea #2)

Autor: Alejandro Rendón Correa (arendonc2). Reproducible con
`python src/arendonc2/zonas_acopio.py`.

## Objetivo

Agrupar los 42 municipios del Valle del Cauca en zonas de acopio **espacialmente
conexas**, cada una con sentido como área de recolección de un acopio satélite.
Los **centros de zona son referencias**; no son la ubicación óptima del modelo de
optimización de Samuel.

## Insumos

- **Polígonos municipales:** GADM 4.1 nivel 2 (Colombia), filtrado a los 42
  municipios de Valle del Cauca. Se descarga con
  `src/arendonc2/descargar_geometrias.py`. GADM no trae código DANE, así que los
  polígonos se emparejan por nombre normalizado con alias explícitos
  (Cali→SantiagodeCali, Buga→GuadalajaradeBuga, Calima Darién→Calima). Los 42
  municipios emparejan 1:1 (ver `data/results/arendonc2/emparejamiento_gadm_dane.csv`).
  **El backlog pedía polígonos del MGN del DANE; se usó GADM. La desviación y su
  motivo están documentados en `docs/arendonc2/geometrias_fuente_y_desviacion.md`.**
- **Oferta valorizada:** `oferta_escenarios_valor.csv` (año 2024, escenario base),
  excluyendo Caña de azúcar.
- **Coordenadas** municipales y **matriz de tiempos** para los centros.

## Método

1. **Validación de geometrías:** 42 polígonos, 0 nulos, 0 inválidos, sin
   duplicados de cod_dane.
2. **Vecindad Queen** (`libpysal.weights.Queen`): grafo de contigüidad. Diagnóstico:
   **1 componente conexa, 0 islas**, promedio 4.29 vecinos (min 1, max 9).
   > Nota: el issue advertía que Buenaventura podía quedar como isla. Con los
   > polígonos GADM **no** queda aislada (comparte frontera terrestre con Dagua,
   > Jamundí y otros). No se inventó ninguna arista para corregir datos.
3. **Variables de agrupamiento** (`config/arendonc2/parametros.yaml`):
   - oferta valorizada (COP): `log1p` (colas largas) → z-score.
   - latitud, longitud: z-score.
4. **Agrupamiento:** Ward con **restricción de conectividad**
   (`AgglomerativeClustering(linkage="ward", connectivity=grafo_queen)` de
   scikit-learn). Alternativa a SKATER; se eligió Ward+connectivity porque
   garantiza zonas contiguas, es determinista y no requiere `spopt`. No se usa
   k-means porque no garantiza contigüidad.
5. **Centro de zona:** municipio que minimiza el tiempo total a los demás de su
   zona, ponderado por oferta valorizada.

## Representación del espacio (auditoría 3)

La versión inicial estandarizaba `lat` y `lon` **por separado** (z-score). Eso es
incorrecto para representar distancias: el Valle mide ~190 km N-S y ~144 km E-W
(desv. estándar 52.7 km N-S vs 29.8 km E-W), y el z-score independiente fuerza
ambos ejes a desviación 1, **estirando el eje E-W ~1.77×** respecto a la realidad.
El cambio de representación altera la partición de forma apreciable (ARI ≈ 0.29
entre ambos métodos a k = 5), así que no es un detalle cosmético.

**Corrección aplicada:** se usan **coordenadas proyectadas** (EPSG:3116,
MAGNA-SIRGAS / Colombia Bogotá, metros) del centroide municipal, escaladas por un
**factor común** (desviación estándar conjunta de x e y). Así 1 km al este pesa
igual que 1 km al norte y se conserva la geometría real. La oferta valorizada
(log1p + z-score) entra como tercera variable con `peso_oferta = 1`. El método es
configurable (`espacio: proyectado_escala_comun | latlon_zscore` en el config).

## Comparación de k (3–8)

Todas las particiones son **100 % conexas** (requisito duro). Métricas con
coordenadas proyectadas, en `data/results/arendonc2/zonas_metricas_k.csv`:

| k | silhouette | inercia_intra | tam min–max | oferta_cv | tiempo prom. al centro (min) | tiempo máx. (min) |
|---|-----------:|--------------:|:-----------:|----------:|-----------------------------:|------------------:|
| 3 | 0.328 | 51.1 | 9–19 | 0.250 | 52.9 | 57.6 |
| 4 | 0.252 | 43.7 | 7–14 | 0.515 | 51.2 | 66.1 |
| **5** | **0.211** | **37.8** | **5–12** | **0.637** | **45.8** | **66.1** |
| 6 | 0.222 | 32.6 | 4–9 | 0.809 | 49.4 | 84.2 |
| 7 | 0.173 | 27.6 | 1–9 | 0.946 | 42.4 | 84.2 |
| 8 | 0.191 | 24.5 | 1–9 | 0.613 | 37.4 | 84.2 |

## Selección de k: criterios cuantitativos vs decisión operativa

`k_seleccionado` es **configurable**; se publica **k = 5**. Separo lo que dicen los
números de la decisión operativa, sin inventar umbrales de viabilidad económica.

**Criterios cuantitativos (lo que miden las métricas):**
- **Silhouette** (separación/cohesión): favorece k bajos — 0.328 (k=3) > 0.252
  (k=4) > 0.222 (k=6) > 0.211 (k=5). Por silhouette puro, k = 3 o 4 serían mejores.
- **Inercia intra-zona:** decrece de forma monótona con k (esperado; no sirve para
  elegir por sí sola).
- **Homogeneidad de oferta (oferta_cv, menor = más parejo):** mejor en k = 3 (0.250)
  y k = 4 (0.515); empeora en k = 5 (0.637) y k = 6 (0.809).
- **Tiempo promedio municipio→centro:** mínimo entre k≤6 en **k = 5 (45.8 min)**;
  el tiempo **máximo** salta de 66.1 min (k≤5) a 84.2 min (k≥6).
- **Tamaño mínimo de zona:** k = 7 y k = 8 crean una zona de **1 municipio**
  (acopio satélite con un solo municipio), lo que resta sentido operativo.

**Decisión operativa (explícita, no derivada de las métricas):**
- Se busca una red de **varios acopios satélite** (el issue plantea k entre 3 y 8);
  k = 3 da zonas muy grandes (hasta 19 municipios, una sola zona cubre casi medio
  departamento) y poca diferenciación de áreas de recolección.
- Se descartan k = 7 y 8 por la zona de 1 municipio y por el salto del tiempo máximo.
- Entre k = 4, 5 y 6: **k = 5** ofrece el **menor tiempo promedio y máximo al
  centro** del rango operativo, sin zonas singleton. k = 4 es una alternativa
  igualmente defendible (mejor silhouette y oferta_cv, menos zonas); k = 6 reparte
  en más zonas pero empeora oferta_cv (0.809) y el tiempo máximo (84.2 min).

**Conclusión honesta:** los números no señalan un k óptimo único. k = 5 se publica
por el criterio de tiempo de recolección dentro de un rango operativo razonable
(sin zonas de 1 municipio), no porque domine en todas las métricas. La elección es
reversible: cambiar `k_seleccionado` en `config/arendonc2/parametros.yaml` y
re-ejecutar. **No se usan umbrales de viabilidad económica** (no hay costos de
construcción ni evaluación financiera en el proyecto).

## Zonas resultantes (k = 5, coordenadas proyectadas)

| Zona | Centro (referencia) | n |
|------|---------------------|---|
| Z1 | Candelaria | 12 |
| Z2 | Obando | 9 |
| Z3 | Sevilla | 9 |
| Z4 | Restrepo | 7 |
| Z5 | Argelia | 5 |

Composición completa en `data/results/zonas.csv`. Tamaños 5–12 (más parejos que la
versión previa con lat/lon z-score, que daba 4–15).

## Salidas

| Archivo | Contenido |
|---------|-----------|
| `data/results/zonas.csv` | cod_dane, municipio, zona, es_centro_zona |
| `data/results/arendonc2/zonas_geometrias.geojson` | Polígonos disueltos por zona (mapa) |
| `data/results/arendonc2/municipios_zonas_geometrias.geojson` | Polígonos municipales con su zona |
| `data/results/arendonc2/vecindad_queen.csv` | Lista de adyacencia Queen |
| `data/results/arendonc2/zonas_metricas_k.csv` | Métricas comparativas de k = 3..8 |
| `data/results/arendonc2/zonas_features.csv` | Variables de agrupamiento por municipio |
| `data/results/arendonc2/zonas_diagnostico.json` | Diagnóstico de geometrías y vecindad |

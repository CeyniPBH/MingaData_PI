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
  municipios emparejan 1:1.
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

## Comparación de k (3–8)

Todas las particiones son **100 % conexas**. Métricas en
`data/results/arendonc2/zonas_metricas_k.csv`:

| k | silhouette | inercia_intra | tam min–max | oferta_cv | tiempo prom. al centro (min) |
|---|-----------:|--------------:|:-----------:|----------:|-----------------------------:|
| 3 | 0.302 | 55.6 | 9–19 | 0.250 | 52.9 |
| 4 | 0.274 | 47.1 | 4–15 | 0.515 | 51.4 |
| **5** | **0.226** | **41.1** | **4–15** | **0.636** | **45.9** |
| 6 | 0.254 | 35.3 | 2–15 | 0.283 | 38.7 |
| 7 | 0.246 | 29.9 | 1–15 | 0.502 | 31.1 |
| 8 | 0.171 | 26.1 | 1–15 | 0.639 | 27.3 |

## Selección: k = 5

`k_seleccionado` es configurable. Se publica **k = 5** (verificando la justificación
previa de 5 zonas) por estos criterios:

- **Contigüidad:** 100 % (requisito duro, lo cumplen todos los k).
- **Tamaño operativo:** con k = 5 ninguna zona queda con 1–2 municipios (sí ocurre
  en k = 6, 7, 8), lo que evita acopios satélite con un solo municipio.
- **Tiempo al centro:** 45.9 min promedio, intermedio y razonable para recolección.
- **Equilibrio homogeneidad/granularidad:** k = 6 tiene mejor oferta_cv (0.283) y
  silhouette (0.254) que k = 5, y sería una alternativa defendible. Se prefiere
  k = 5 por simplicidad operativa (5 acopios) y porque evita la zona de 2
  municipios de k = 6. **k es un parámetro de decisión, no un óptimo único**; el
  archivo de métricas permite revisar la elección.

> Advertencia honesta: a k = 5 la zona Z4 agrupa 15 municipios (incluye Cali y el
> corredor Palmira–Buga), con alta oferta. Si Samuel quiere zonas más parejas en
> oferta, k = 6 reparte mejor (ver métricas). Cambiar `k_seleccionado` en el config
> y re-ejecutar.

## Zonas resultantes (k = 5)

| Zona | Centro (referencia) | n | Municipios |
|------|---------------------|---|------------|
| Z1 | Sevilla | 9 | Andalucía, Bolívar, Bugalagrande, Caicedonia, Riofrío, Roldanillo, Sevilla, Trujillo, Tuluá |
| Z2 | Dagua | 4 | Buenaventura, Dagua, La Cumbre, Restrepo |
| Z3 | Obando | 9 | Alcalá, Cartago, El Dovio, La Unión, La Victoria, Obando, Toro, Ulloa, Zarzal |
| Z4 | El Cerrito | 15 | Buga, Cali, Calima Darién, Candelaria, El Cerrito, Florida, Ginebra, Guacarí, Jamundí, Palmira, Pradera, San Pedro, Vijes, Yotoco, Yumbo |
| Z5 | Argelia | 5 | Ansermanuevo, Argelia, El Águila, El Cairo, Versalles |

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

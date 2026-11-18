# Geometrías municipales: fuente, versión y desviación del backlog (Auditoría 2)

Autor: Alejandro Rendón Correa (arendonc2).

## Requisito del backlog

El issue #2 pedía:
> Polígonos municipales (GeoJSON/shapefile del **Marco Geoestadístico Nacional del
> DANE**, filtrado a los 42 municipios del Valle). Es el único insumo que Ceyni no
> entrega: bájenlo ustedes.

## Qué se usó y por qué (desviación declarada)

**Se usó GADM 4.1, nivel administrativo 2 (municipios), Colombia**, filtrado a los
42 municipios del Valle del Cauca. **No** se usó el MGN del DANE.

- **Fuente:** GADM (Database of Global Administrative Areas), versión 4.1.
- **Archivo:** `gadm41_COL_2.json.zip` (~1.1 MB).
- **URL:** `https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_COL_2.json.zip`
- **Descarga:** `python src/arendonc2/descargar_geometrias.py` (no se versiona el crudo).
- **Licencia:** GADM es gratuito para uso académico y no comercial; no permite
  redistribución comercial. Este proyecto es académico (Proyecto Integrador).

### Motivo de la sustitución

No se logró obtener el MGN del DANE mediante una descarga directa desde script en
el tiempo de este trabajo. Intentos realizados y su resultado:

- URLs directas de archivo probadas en el geoportal DANE
  (`geoportal.dane.gov.co/descargas/mgn_2018/...` y
  `.../descargas/mgn/MGN_MPIO_POLITICO.zip`): respondieron **HTTP 404**.
- Dos servicios ArcGIS REST de terceros que reexponen capas municipales:
  respondieron HTTP 200 pero con metadatos nulos (`name`/`maxRecordCount` vacíos),
  por lo que no se pudo confirmar que correspondieran al MGN oficial ni descargar
  la capa de forma verificable.

No se afirma que ArcGIS impida la reproducibilidad: es posible que exista una ruta
de descarga del MGN (por ejemplo, exportación manual desde el geoportal o un
servicio REST correcto) que no se identificó aquí. La decisión de usar GADM es por
no haber confirmado una descarga del MGN reproducible desde script, no por una
limitación inherente de la plataforma.

Para el **único uso** que se les da a los polígonos —construir la vecindad por
contigüidad Queen (qué municipios comparten frontera)— GADM es adecuado: la
topología de fronteras municipales del Valle coincide con la realidad
administrativa. No se usan las geometrías para cálculos de área ni de distancia
(esos vienen de la matriz de tiempos y de las coordenadas DANE/DIVIPOLA).

### Consecuencia y mitigación

- El emparejamiento GADM→DANE se hace por **nombre normalizado + alias**, no por
  código oficial (GADM no trae código DANE). Se publica el emparejamiento completo
  (ver abajo) y se verifica 1:1.
- Si en el futuro se consigue el MGN del DANE como archivo estable, basta cambiar
  `cargar_geometrias` en `src/arendonc2/zonas_acopio.py` para leerlo por `cod_dane`
  directamente (eliminando el emparejamiento por nombre), y re-ejecutar.

## Verificación del emparejamiento (sin ambigüedad)

`python src/arendonc2/auditar_geometrias.py` →
`data/results/arendonc2/emparejamiento_gadm_dane.csv`.

- 42 polígonos GADM en Valle del Cauca, **42 emparejados 1:1** con los 42 códigos DANE.
- **0** municipios sin emparejar, **0** polígonos GADM usados más de una vez,
  **0** polígonos GADM del Valle sin usar.
- **3 alias** (nombre repo → nombre GADM `NAME_2`):
  - Cali → SantiagodeCali
  - Buga → GuadalajaradeBuga
  - Calima Darién → Calima
- Validación de geometrías: 42 polígonos, 0 nulos, 0 inválidos.
- Vecindad Queen resultante: **1 componente conexa, 0 islas** (Buenaventura
  **no** queda aislada).

## Reproducir

```bash
python src/arendonc2/descargar_geometrias.py
python src/arendonc2/auditar_geometrias.py   # publica el emparejamiento y lo valida
```

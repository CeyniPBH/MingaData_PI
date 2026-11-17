# Limitaciones del pronóstico y de los datos

## Datos
- **Series cortas:** máximo 24 datos anuales por serie; muchas series de productos simplificados tienen menos de 12.
- **Valores repetidos:** 20,9 % de las transiciones anuales repiten exactamente el valor anterior. Parte de la serie parece estimación por consenso y no medición anual.
- **Saltos atípicos:** 7,6 % de las transiciones cambian más de 100 %; muchos coinciden con cambios de cobertura o de metodología.
- **Cambios de desagregación:** cítricos (2021) y aguacate Hass (2020) se agregaron para conservar la serie larga; se pierde el detalle por variedad.
- **Productos de baja confianza:** 18 de 44 (3 entre los detallados: Borojó, Sábila y Ají). Sus pronósticos deben leerse como escenarios, no como predicciones independientes.
- **Borojó:** un solo municipio con 26,6 mil t en 2019-2023; conviene verificarlo en la fuente.
- **Supuesto de ceros:** un año sin registro dentro de una serie activa se toma como 0 t.

## Modelos
- **Sin mejora material sobre el ingenuo:** LightGBM empata (MASE +0,3 %, WAPE −1,9 %). El valor del pronóstico está en los intervalos y escenarios, no en una mayor precisión puntual.
- **Dominio de la caña de azúcar:** ≈ 96 % de las toneladas, así que el WAPE total refleja sobre todo la caña. Por eso se reportan métricas por producto.
- **ONI no evaluado todavía:** el índice está integrado (`data/clean/oni.csv`), pero el experimento con/sin ONI requiere correr LightGBM (`06_lgbm.py --comparar-oni`).

## Escenarios
- **Cobertura 75,9 % vs 80 % nominal:** los intervalos son algo angostos; no deben presentarse como perfectamente calibrados.
- **Periodo de calibración 2019-2023** con caídas fuertes (por ejemplo café, de 69,5 mil t en 2019 a 37,4 mil t en 2023), lo que sesga algunos intervalos (café 2028: alto ≈ base).
- **Horizonte 5** calibrado con h = 4 y ensanchado por √(5/4), porque solo un origen (2018) llega a 5 años.
- **Suma de extremos:** la banda departamental suma los bajos y los altos municipales; describe el caso en que todos los municipios se mueven a la vez y es más ancha que el rango real.

## Fuentes externas
- **Precios SIPSA:** cubren 2021-2026 (2026 hasta octubre). Para valorar todos los años se usa un precio constante (promedio 2021-2023), en pesos corrientes sin deflactar.
- **Precios derivados (aproximados):** caña de azúcar = azúcar sulfitada × 0,115; caña panelera = panela × 0,10; café pergamino = café molido × 0,63. Usan precio mayorista del producto procesado, así que **sobreestiman el valor en finca** (incluyen márgenes de transformación). Se identifican con `tipo_precio = derivado`.
- **Productos sin precio SIPSA (11 activos):** Arazá, Aromáticas, Cacao, Chontaduro, Flores y follajes, Macadamia, Papachina, Sacha Inchi, Stevia, Sábila y Té. Su valor queda vacío.
- **Mercados:** se usa el promedio de los mercados mayoristas del Valle; si el producto no se cotiza allí, la mediana nacional (columna `ambito`).
- **ONI:** el archivo descargado originalmente era una versión antigua que terminaba en 2017. Se reemplazó por la serie vigente de NOAA CPC (`oni.ascii.txt`) transcrita el 17-nov-2026 (1998-2026). Las dos versiones difieren en ≈ 0,1 en promedio (correlación 0,98); conviene reemplazar `data/raw/ONI_NOAA_CPC_1998_2026.csv` por la descarga directa de `oni.ascii.txt`.
- **Matriz de tiempos aproximada:** línea recta × 1,4 a 45 km/h; no considera la cordillera ni el estado de las vías (Buenaventura queda subestimada). Se puede reemplazar por OSRM manteniendo columnas.
- **Población municipal:** pendiente (no se encontró el archivo DANE en el repo).
- **Comercio ICA (FRONTERA):** son inspecciones fitosanitarias, no estadísticas oficiales de exportación; mezclan unidades (kg, unidades de flor). Sirven como respaldo de proporciones exportables, no como volumen exacto. 2024-2026 es información provisional/preliminar.

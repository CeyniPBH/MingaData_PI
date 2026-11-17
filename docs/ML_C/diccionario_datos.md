# Diccionario de datos

Todos los CSV están en UTF-8 con BOM; `cod_dane` es texto de 5 dígitos. Los scripts se corren en orden desde la raíz del repo: `python src/01_limpieza.py` … `python src/06_escenarios.py`.

| Archivo | Columnas | Lo usa |
|---|---|---|
| data/clean/produccion_valle_clean.csv (.parquet) | anio, cod_dane, municipio, producto, ha_sembradas, ha_cosechadas, produccion_t, familia, rendimiento_t_ha | Todos |
| data/clean/lista_productos.csv | producto, familia, anio_ini, anio_fin, n_municipios, n_filas, produccion_t_2019_2023, n_municipios_2019_2023, estado (detallado / simplificado / excluido), ranking_toneladas | Samuel, Alejandro |
| data/clean/municipios_coordenadas.csv | cod_dane, municipio, lat, lon | Samuel, Alejandro |
| data/clean/destinos_coordenadas.csv | id_destino, nombre, lat, lon | Alejandro |
| data/clean/matriz_tiempos.csv | origen, destino, minutos, distancia_km, metodo (`aproximado` = línea recta × 1,4 / 45 km/h) | Samuel, Alejandro |
| data/clean/produccion_promedio_municipio.csv | cod_dane, municipio, producto, prod_prom_t_2019_2023 (toneladas, aún no ponderada por valor) | Samuel |
| data/results/oferta_escenarios.csv | producto, cod_dane, año, oferta_bajo, oferta_base, oferta_alto | Samuel, Alejandro |
| data/results/oferta_escenarios_detalle.csv | lo anterior + modelo, horizonte | Alejandro (pantalla 1) |
| data/results/oferta_departamento.csv | producto, año, oferta_bajo, oferta_base, oferta_alto (suma de municipios) | Alejandro |
| data/results/diagnostico_calidad.csv / diagnostico_series.csv | por producto / por serie | Carlos |
| data/results/decisiones_armonizacion.csv | decision, producto_o_campo, accion, motivo | Carlos |
| data/results/predicciones_baselines.csv, metricas_baselines.csv, predicciones_lgbm.csv, metricas_comparacion.csv, importancia_variables.csv, cobertura_intervalos.csv, coherencia_jerarquica.csv | resultados del modelado | Carlos |

Pendiente (no se pudo descargar aquí): valor_producto.csv (SIPSA), oni.csv, poblacion_municipal.csv y consumo_percapita.csv (FAOSTAT), y la matriz de tiempos por OSM (reemplaza la aproximada manteniendo columnas e ids).

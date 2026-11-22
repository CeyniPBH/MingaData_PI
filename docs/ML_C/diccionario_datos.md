# Diccionario de datos

Todos los CSV están en UTF-8 con BOM; `cod_dane` es texto de 5 dígitos. Los scripts se corren en orden desde la raíz del repo con `python src/ML_C/ejecutar_todo.py` (de `00_descargar_datos.py` a `08_validar_entregas.py`).

| Archivo | Columnas | Lo usa |
|---|---|---|
| data/clean/produccion_valle_clean.csv (.parquet) | anio, cod_dane, municipio, producto, ha_sembradas, ha_cosechadas, produccion_t, familia, rendimiento_t_ha | Todos |
| data/clean/lista_productos.csv | producto, familia, anio_ini, anio_fin, n_municipios, n_filas, produccion_t_2019_2023, n_municipios_2019_2023, estado (detallado / simplificado / excluido), ranking_toneladas | Samuel, Alejandro |
| data/clean/municipios_coordenadas.csv | cod_dane, municipio, lat, lon | Samuel, Alejandro |
| data/clean/destinos_coordenadas.csv | id_destino, nombre, lat, lon | Alejandro |
| data/clean/matriz_tiempos.csv | origen, destino, minutos, distancia_km, metodo (`aproximado` = línea recta × 1,4 / 45 km/h) | Samuel, Alejandro |
| data/clean/produccion_promedio_municipio.csv | cod_dane, municipio, producto, prod_prom_t_2019_2023 (toneladas, aún no ponderada por valor) | Samuel |
| data/results/ML_Ce/oferta_escenarios.csv | producto, cod_dane, año, oferta_bajo, oferta_base, oferta_alto | Samuel, Alejandro |
| data/results/ML_Ce/oferta_escenarios_detalle.csv | lo anterior + modelo, horizonte | Alejandro (pantalla 1) |
| data/results/ML_Ce/oferta_departamento.csv | producto, año, oferta_bajo, oferta_base, oferta_alto (suma de municipios) | Alejandro |
| data/results/ML_Ce/diagnostico_calidad.csv / diagnostico_series.csv | por producto / por serie | Carlos |
| data/results/ML_Ce/decisiones_armonizacion.csv | decision, producto_o_campo, accion, motivo | Carlos |
| data/results/ML_Ce/predicciones_baselines.csv, metricas_baselines.csv, predicciones_lgbm.csv, metricas_comparacion.csv, importancia_variables.csv, cobertura_intervalos.csv, coherencia_jerarquica.csv | resultados del modelado | Carlos |
| data/results/ML_Ce/metricas_modelo_final.csv | alcance (todos / sin_cana), horizonte (todos / 1-5), producto, modelo (naive, lgbm, naive_lgbm), n_obs, n_series, pct_obs_escala0, MASE, WAPE, mejora_MASE_vs_naive, mejora_WAPE_vs_naive | Informe (Tabla 4) |
| data/results/ML_Ce/metricas_oni.csv | producto (TOTAL), modelo, n_obs, n_series, pct_obs_escala0, MASE, WAPE, mejoras frente al ingenuo, variante (con_oni / sin_oni), alcance (todos / sin_cana) | `sensibilidad_oni.md` |
| data/results/ML_Ce/sensibilidad_oni.csv | nivel, producto, cod_dane, año, oferta_bajo, oferta_base, oferta_alto, base_sin_oni, dif_rel_sin_oni, bajo_rel, alto_rel; en el nivel backtest_origen, MASE y WAPE con y sin ONI por origen | `sensibilidad_oni.md` |
| data/results/ML_Ce/sensibilidad_oni_optimizacion.csv | anio, id_escenario, oferta, consumo, mezcla, es_base; central, satélites, cobertura, A, B y costo total oficiales y sin ONI; diferencias relativas | `sensibilidad_oni.md` |

Pendiente: la matriz de tiempos por OSM, que reemplazaría la aproximada manteniendo columnas e ids. Las tablas de precios y valor (SIPSA), ONI, población y consumo (FAOSTAT) ya están en `data/clean/` (ver `fuentes_y_licencias.md`).

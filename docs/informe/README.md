# Figuras y cifras del informe final

Las figuras del informe y las cifras que no están guardadas en `data/results` se generan con los scripts de `src/informe/`. Leen solo archivos del repositorio, así que basta con clonarlo e instalar `requirements.txt`. Desde la raíz:

```bash
python src/informe/ejecutar_todo.py
```

El comando guarda las figuras 1 a 8 en `docs/informe/figuras/` y muestra las cifras en la terminal. Cada script también se puede correr por separado. Cada figura tiene un solo archivo, con el mismo nombre que usa el informe; al volver a generarla, el archivo se reemplaza.

Los números de sección son los del informe final, que empieza en "1. Introducción".

## Figuras

| Figura | Sección | Script | Datos que lee |
|---|---|---|---|
| 1. Frontera entre el aprendizaje automático y la optimización | 3.1.4 | `figura_1_frontera.py` | Ninguno (esquema) |
| 2. Área sembrada por cultivo | 3.2.3 | `figura_2_area_sembrada.py` | `data/clean/produccion_valle_clean.csv`, `data/results/arendonc2/municipios_zonas_geometrias.geojson` |
| 3. Toneladas frente a valor | 3.2.3 | `figura_3_4_valor_y_tendencias.py` | `data/results/ML_Ce/ranking_valor_vs_toneladas.csv` |
| 4. Índice de producción 2014 = 100 | 3.2.3 | `figura_3_4_valor_y_tendencias.py` | `data/clean/produccion_valle_clean.csv` |
| 5. Validación walk-forward | 3.3.3 | `figura_5_walk_forward.py` | Ninguno (esquema) |
| 6. Central en los 54 escenarios | 3.4.2 | `figura_6_centrales.py` | `data/results/opt/estabilidad_escenarios.csv`, `data/clean/destinos_coordenadas.csv` y geometrías de `data/results/arendonc2/` |
| 7. Caso aplicado de Bugalagrande | 3.4.4 | `figura_7_caso_bugalagrande.py` | Panel de producción, `predicciones_comparacion.csv` y `oferta_escenarios.csv` |
| 8. Arquitectura del pipeline | 4.1 | `figura_8_arquitectura.py` | Ninguno (esquema hecho con `docs/arquitectura/` y `docs/evaluacion/evidencia_despliegue.md`) |
| 9. Vista de cobertura del tablero | 5.4 | Captura de pantalla | Pantalla 4. Cobertura y capacidad |
| 10. Comparación territorial entre sedes | 5.4 | Captura de pantalla | Pantalla 4. Cobertura y capacidad |
| 11. Arquitectura a escala | 6 | Diagrama hecho a mano | Ninguno (esquema) |
| 12. Modelos a escala | 6 | Diagrama hecho a mano | Ninguno (esquema) |
| 13. Tableros a escala | 6 | Diagrama hecho a mano | Ninguno (esquema) |

En la Figura 2 cada punto equivale a 500 hectáreas y se ubica al azar dentro de su municipio. La semilla es fija, así que la figura sale igual en cada ejecución.

Las Figuras 9 y 10 son capturas de la pantalla 4. Cobertura y capacidad de la aplicación de Streamlit, tomadas el 23 de noviembre de 2026. Los archivos son `figura_9_tablero_cobertura.png` y `figura_10_tablero_comparacion.png`. La vista de cobertura no cabe en una sola ventana, así que la Figura 9 une dos capturas. La Figura 10 muestra el bloque de comparación territorial. La pantalla genera el tablero desde `data/clean/produccion_valle_clean.csv` cada vez que se abre, con `src/dashboard/tablero_central.py`. Si cambia algo visible de esa vista, hay que volver a capturarlas.

Las Figuras 11, 12 y 13 (`figura_11_arquitectura_escala.png`, `figura_12_modelos_escala.png` y `figura_13_tableros_escala.png`) son los diagramas de la sección 6. No salen de ningún script.

La tipografía es Liberation Sans en Linux y Arial en macOS y Windows. Las dos tienen las mismas medidas, así que la composición no cambia entre equipos.

## Cifras

| Script | Secciones | Qué calcula |
|---|---|---|
| `cifras_3_2_3.py` | 3.2.3 | Área por cultivo y subregión, toneladas frente a valor, concentración por municipio, tendencias 2014-2023, correlaciones de control (valores repetidos y ONI) y rendimiento por subregión |
| `cifras_3_3_y_3_4.py` | 3.3.4, 3.4.1, 3.4.2 y 3.4.3 | Tabla 4 con el modelo final, oferta y excedentes, frecuencia de cada central en los 54 escenarios, error del pronóstico en pesos y exposición logística a un año sin caña de azúcar frente al promedio de cinco años |
| `cifras_hipotesis.py` | 3.4.3, 5.2, 5.4, 5.5 y 6 | Cobertura a 40 km, sensibilidad al radio, tamaño de la central y contraste de la hipótesis, con el mismo cálculo del tablero |

Las métricas del pronóstico salen de `data/results/ML_Ce/metricas_modelo_final.csv` y la sensibilidad al ONI de `docs/ML_C/sensibilidad_oni.md`.

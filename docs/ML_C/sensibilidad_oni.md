# Sensibilidad del modelo final al ONI

## Qué pasó

`config/ML_C/parametros.yaml` decía `usar_oni: false`, pero `cargar_oni()` cargaba `data/clean/oni.csv` siempre que el archivo existiera, y existe desde el 17 de noviembre de 2026. Por eso el modelo final, los escenarios, la optimización y el modelo de la API desplegada (14 variables) se calcularon con el ONI rezagado de los años T y T−1. El registro de la corrida del 20 de noviembre lo muestra: `06_lgbm.py` imprime `ONI: usado`.

Desde esta revisión `cargar_oni()` respeta el parámetro, y la configuración dice `usar_oni: true`, que es lo que de verdad usa el modelo. Se decidió mantener el ONI y no recalcular la cadena. Este documento reúne la evidencia de esa decisión.

## 1. Backtest con y sin ONI

Archivo: `data/results/ML_Ce/metricas_oni.csv`, generado con `python src/ML_C/06_lgbm.py --comparar-oni`. Las dos variantes se evalúan sobre las mismas 8.323 observaciones de los 22 productos detallados.

| Variante | MASE LightGBM | MASE modelo final | Mejora MASE del modelo final | Mejora WAPE del modelo final |
|---|---|---|---|---|
| Con ONI (oficial) | 3,919 | 3,907 | +0,28 % | −0,35 % |
| Sin ONI | 3,904 | 3,899 | +0,47 % | −0,12 % |

Sin caña de azúcar, el modelo final mejora el MASE en 0,31 % con ONI y en 0,51 % sin ONI. El WAPE mejora 0,13 % con ONI y empeora 0,12 % sin ONI. Las dos variables del ONI suman el 2,0 % de la ganancia del modelo, y en las dos variantes el modelo queda empatado con el ingenuo.

La variante con ONI reproduce las cifras oficiales hasta el sexto decimal en macOS con LightGBM 4.7.0, aunque la corrida original se hizo en Windows. La variante sin ONI reproduce los 3,904 y 3,899 que quedaron en el notebook 06 de una corrida anterior.

Por origen (`sensibilidad_oni.csv`, nivel `backtest_origen`), el modelo sin ONI tiene menor MASE en 4 de los 5 orígenes:

| Origen | MASE con ONI | MASE sin ONI | Diferencia |
|---|---|---|---|
| 2018 | 5,109 | 5,105 | −0,09 % |
| 2019 | 4,767 | 4,746 | −0,44 % |
| 2020 | 3,401 | 3,402 | +0,03 % |
| 2021 | 1,615 | 1,612 | −0,20 % |
| 2022 | 0,791 | 0,785 | −0,70 % |

## 2. Oferta pronosticada 2024-2028

Archivo: `data/results/ML_Ce/sensibilidad_oni.csv`, generado con `python src/ML_C/07b_sensibilidad_oni.py`. El script repite el cálculo de `07_escenarios.py` con y sin ONI sin tocar las salidas oficiales. Como control, la variante con ONI reproduce `oferta_escenarios.csv` con una diferencia máxima de 0,005 t, que es el redondeo del archivo.

- La oferta departamental sin caña es menor sin ONI: −0,8 % en 2024, −1,0 % en 2025, −1,2 % en 2026 y −1,5 % en 2027 y 2028. Con caña, la diferencia es menor a 0,3 %.
- Por producto, el plátano baja hasta 1,6 % (unas 5.700 t en 2028) y la caña panelera entre 1,1 % y 1,3 %. La cebolla larga sube 53 %, pero son 318 t, el 0,02 % de la oferta sin caña.
- Por municipio, sin caña, el cambio más grande es 4,3 % (Trujillo, 2027). La mediana es 0,7 % en 2024 y 0,9 % en 2028.
- En el 99,2 % de las filas producto × municipio × año, la oferta base sin ONI queda dentro de la banda bajo-alto oficial.

## 3. Ubicación de la central

Archivo: `data/results/ML_Ce/sensibilidad_oni_optimizacion.csv`, generado con `python src/ML_C/07c_comparar_oni_optimizacion.py`. En una copia del proyecto con `usar_oni: false` se recalcularon el pronóstico, los escenarios de oferta, los excedentes y la estabilidad de la central en los 54 escenarios. Las zonas quedaron iguales porque la ubicación libre no las usa.

- La central es la misma en los 54 escenarios, con las mismas frecuencias: Bugalagrande 18, Riofrío 15, Yotoco 12, Sevilla 6 y Andalucía 3.
- El costo físico total baja entre 0,4 % y 2,4 % (mediana 1,3 %), porque la oferta sin ONI es un poco menor.
- En el escenario base de 2024 la distribución sigue siendo el 78,7 % del costo, y la cobertura pasa de 73,82 % a 73,71 %.
- Los satélites cambian en 53 de los 54 escenarios. Es lo esperado: con tiempos en línea recta y sin descuento por consolidación, pasar por un satélite cuesta lo mismo que ir directo a la central, así que el solver puede devolver satélites distintos con el mismo costo.

## 4. Criterios y decisión

Los tres primeros criterios se fijaron antes de ver los resultados de la oferta.

| Criterio | Resultado | ¿Se cumple? |
|---|---|---|
| La variante con ONI reproduce la oferta oficial | Diferencia máxima de 0,005 t | Sí |
| La oferta departamental sin caña cambia menos de 1 % | Entre −1,05 % y −1,48 % de 2025 a 2028 | No |
| Ningún municipio cambia más de 5 % | Máximo 4,3 % | Sí |
| La central no cambia en ningún escenario | Igual en los 54 | Sí |

El segundo criterio no se cumplió por poco. Por eso se agregó la prueba de la optimización, que mide la decisión de negocio de forma directa. Quitar el ONI no cambia la central en ningún escenario, mueve los costos alrededor de 1 % y no cambia ninguna conclusión del modelado. Con esa evidencia se mantiene el ONI, y no se recalculan la cadena ni el modelo de la API a dos días de la entrega.

Queda una simplificación pendiente. El modelo sin ONI es más simple, tiene menor MASE en 4 de 5 orígenes, y el análisis exploratorio del informe (sección 3.2.3) no encontró relación entre el ONI y el cambio anual de la producción sin caña (Spearman −0,07). Si el proyecto se vuelve a calcular, conviene quitarlo.

## 5. Cómo reproducir

Desde la raíz del repositorio, con el entorno activo:

```bash
python src/ML_C/06_lgbm.py --comparar-oni     # metricas_oni.csv
python src/ML_C/07b_sensibilidad_oni.py        # sensibilidad_oni.csv
```

La corrida sin ONI se hace en una copia, para no tocar los resultados oficiales (comandos de macOS; en Windows se copia la carpeta sin `.venv` ni `.git` y se cambia `usar_oni` a mano):

```bash
cd ..
rsync -a --exclude .venv --exclude .git MingaData_PI/ MingaData_PI_sinONI/
cd MingaData_PI_sinONI
sed -i '' 's/^  usar_oni: true/  usar_oni: false/' config/ML_C/parametros.yaml
python src/ML_C/06_lgbm.py
python src/ML_C/07_escenarios.py
python -c "import sys; sys.path.insert(0, 'src'); from arendonc2 import common, excedentes, escenarios; cfg = common.cargar_config(); excedentes.ejecutar(cfg, guardar=True); escenarios.ejecutar(cfg, guardar=True)"
python src/optimizacion/generar_resultados.py --solo estabilidad
cd ../MingaData_PI
python src/ML_C/07c_comparar_oni_optimizacion.py --sin-oni ../MingaData_PI_sinONI
```

La copia se puede borrar después; la comparación queda en `sensibilidad_oni_optimizacion.csv`.

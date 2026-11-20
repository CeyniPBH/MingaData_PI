# Ajuste de hiperparámetros (tuning) sin fuga temporal

## 1. Objetivo

Buscar una configuración de LightGBM que mejore el error del ensamble sin contaminar el conjunto de prueba. La pregunta no es “¿cuál configuración tiene el menor error en todos los datos?”, sino “¿alguna configuración mejora de forma estable cuando se valida en años que no participaron en la búsqueda?”.

## 2. Diseño anti-fuga

| Elemento | Decisión |
|---|---|
| Orígenes de tuning | 2018, 2019 y 2020 |
| Objetivos usados en tuning | ≤ 2021 |
| Orígenes de holdout | 2021 y 2022 (objetivos 2022 y 2023) |
| Uso del holdout | Solo reporte final; **no** selecciona la configuración |
| Configuración de referencia | `config/ML_C/parametros.yaml` (candidato 0) |
| Modelo final | No se reemplaza; el tuning es un experimento |
| Semilla | `random_state = 42`, `n_jobs = 1` |

El corte ≤ 2021 deja 2022 y 2023 completamente fuera de la búsqueda. Cualquier mejora que dependa de esos años se considera sospechosa y no se adopta.

## 3. Espacio de búsqueda

Se evaluaron 14 candidatos. Cada uno cambia uno o varios hiperparámetros respecto de la configuración actual:

| ID | Cambio respecto de la configuración actual |
|---:|---|
| 0 | Ninguno (referencia) |
| 1 | `learning_rate = 0.02` |
| 2 | `learning_rate = 0.05` |
| 3 | `num_leaves = 7` |
| 4 | `num_leaves = 31` |
| 5 | `min_child_samples = 10` |
| 6 | `min_child_samples = 50` |
| 7 | `n_estimators = 500`, `learning_rate = 0.02` |
| 8 | `n_estimators = 200`, `learning_rate = 0.05` |
| 9 | `subsample = 0.7`, `colsample_bytree = 0.7` |
| 10 | `subsample = 1.0`, `colsample_bytree = 1.0` |
| 11 | `reg_lambda = 0.0` |
| 12 | `reg_lambda = 5.0` |
| 13 | `num_leaves = 31`, `min_child_samples = 10`, `learning_rate = 0.02`, `n_estimators = 500` |

La configuración de referencia usa `objective = l1`, `n_estimators = 300`, `learning_rate = 0.03`, `num_leaves = 15`, `min_child_samples = 30`, `subsample = 0.8`, `colsample_bytree = 0.8`, `reg_lambda = 1.0`.

## 4. Resultados en tuning (objetivos ≤ 2021)

Ordenados por MASE del ensamble:

| ID | Cambio | MASE LightGBM | WAPE LightGBM | MASE ensamble | WAPE ensamble | Δ MASE vs actual |
|---:|---|---:|---:|---:|---:|---:|
| 13 | `num_leaves=31`, `min_child_samples=10`, `lr=0.02`, `n_estimators=500` | 3,3209 | 0,0815 | **3,3000** | 0,0737 | −0,0119 |
| 11 | `reg_lambda=0.0` | 3,3240 | 0,0802 | 3,3038 | 0,0732 | −0,0081 |
| 12 | `reg_lambda=5.0` | 3,3305 | 0,0816 | 3,3065 | 0,0739 | −0,0055 |
| 10 | `subsample=1.0`, `colsample=1.0` | 3,3309 | 0,0845 | 3,3076 | 0,0754 | −0,0043 |
| 5 | `min_child_samples=10` | 3,3303 | 0,0823 | 3,3077 | 0,0741 | −0,0043 |
| 6 | `min_child_samples=50` | 3,3306 | 0,0810 | 3,3086 | 0,0736 | −0,0033 |
| 1 | `learning_rate=0.02` | 3,3292 | 0,0811 | 3,3087 | 0,0737 | −0,0033 |
| 9 | `subsample=0.7`, `colsample=0.7` | 3,3330 | 0,0800 | 3,3088 | 0,0730 | −0,0031 |
| 3 | `num_leaves=7` | 3,3311 | 0,0841 | 3,3097 | 0,0750 | −0,0023 |
| 7 | `n_estimators=500`, `lr=0.02` | 3,3374 | 0,0815 | 3,3109 | 0,0738 | −0,0011 |
| 0 | **Actual** | 3,3392 | 0,0840 | **3,3120** | 0,0751 | 0,0000 |
| 4 | `num_leaves=31` | 3,3479 | 0,0798 | 3,3127 | 0,0729 | +0,0007 |
| 8 | `n_estimators=200`, `lr=0.05` | 3,3441 | 0,0844 | 3,3139 | 0,0752 | +0,0020 |
| 2 | `learning_rate=0.05` | 3,3505 | 0,0832 | 3,3144 | 0,0741 | +0,0024 |

La mejora máxima en tuning es **0,0119 de MASE** (0,36 %). Es pequeña y proviene de un candidato que combina cuatro cambios, no de una señal robusta.

## 5. Verificación en holdout (2022-2023)

| Configuración | MASE LightGBM | WAPE LightGBM | MASE ensamble | WAPE ensamble |
|---|---:|---:|---:|---:|
| Actual | **1,2368** | **0,0904** | **1,2031** | **0,0863** |
| Mejor en tuning (ID 13) | 1,2480 | 0,0917 | 1,2057 | 0,0875 |

La configuración que ganó en tuning **pierde en el holdout** en las cuatro métricas. La diferencia es pequeña, pero consistente en dirección: no hay evidencia de que la mejora sea transferible.

## 6. Decisión

**Se mantiene `config/ML_C/parametros.yaml` sin cambios.** El modelo final sigue siendo el documentado en `06_lgbm.py` y `07_escenarios.py`. El tuning se conserva como evidencia y como experimento reproducible:

```powershell
python src/ML_C/06b_tuning.py
python src/ML_C/06b_tuning.py --rapido   # 7 candidatos
```

Salidas:

- `data/results/ML_Ce/tuning_resultados.csv`
- `data/results/ML_Ce/tuning_holdout.csv`
- `data/results/ML_Ce/tuning_holdout_resumen.csv`
- `data/results/ML_Ce/tuning_mejor_config.yaml`

## 7. Interpretación

1. **El modelo ya está cerca de su techo con estas variables.** Cambiar la capacidad del árbol o la regularización mueve el MASE menos de 0,4 %.
2. **La señal es débil.** La mayor parte del error viene de series cortas, ceros y cambios de desagregación; los hiperparámetros no corrigen eso.
3. **El holdout manda.** Una mejora en tuning que no se replica en 2022/2023 no se adopta, aunque el número sea más bonito.
4. **El espacio es pequeño.** No se hizo una búsqueda exhaustiva (grid/random de cientos de combinaciones) porque el riesgo de sobreajustar la validación crece y el retorno esperado es bajo. Se prefirió un conjunto interpretable de 14 candidatos.
5. **El ensamble es robusto.** La combinación 50/50 con el ingenuo reduce la varianza y explica por qué el MASE del ensamble es menor que el de LightGBM solo.

## 8. Limitaciones

- No se usó validación cruzada anidada; el holdout es único (2022-2023).
- El tuning se hizo con `n_jobs=1` por determinismo; una búsqueda paralela no cambiaría la conclusión, solo el tiempo.
- Los candidatos son cambios discretos alrededor de la configuración actual, no una exploración global.
- El conjunto de 2022/2023 es pequeño; una diferencia de 0,002 en MASE no es significativa en términos prácticos.
- El flag `usar_oni` no se modificó; el modelo actual usa ONI. Cambiarlo habría alterado la comparación y los resultados del modelo final.

## 9. Conclusión

El tuning fue sistemático, con test intacto y comparación contra la configuración actual. La mejor configuración en la ventana ≤ 2021 no generalizó al holdout 2022/2023. **No se cambia el modelo final.** La evidencia queda registrada para que la decisión sea auditable.

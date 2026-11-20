# Matriz de rúbrica y evidencias — MingaData_PI

Esta matriz asocia cada criterio de rúbrica (SI7006 arquitectura/ingesta, SI7009 modelado ML, SI7007 dashboard visual) con los artefactos y evidencias del repositorio. Se declara el nivel alcanzado y se señala qué criterios quedan **fuera de alcance** por decisión del proyecto (despliegue/ambiente y sustentación, omitidos por instrucción).

Convenciones:
- Los artefactos en `data/clean/` y `data/results/` son CSV versionados + Parquet derivados (ver `data/metadata/catalogo.yaml`, 37 tablas).
- Los lectores prefieren Parquet con fallback a CSV (`src/dashboard/utils.py`, `src/ML_C/common.py`).
- `cod_dane` se conserva siempre como texto de 5 dígitos.
- Nada depende de servicios de pago; todo ejecuta localmente con `requirements.txt`.

## SI7006 — Arquitectura, ingesta y almacenamiento

| # | Criterio | Peso | Nivel declarado | Artefactos / evidencias | Notas |
|---|---|---:|---|---|---|
| 1 | Arquitectura de referencia y flujo de datos | 15% | Excelente | `docs/arquitectura/arquitectura_referencia.md`, `docs/arquitectura/pipeline.mmd`, `docs/arquitectura/almacenamiento_zonas.md`, `docs/arquitectura/justificacion_procesamiento.md`, `docs/arquitectura/rendimiento.md` | Data lake ligero por zonas raw/trusted/refined, diagrama Mermaid, flujos y contratos entre etapas. |
| 2 | Entorno tecnológico | 10% | Fuera de alcance | — | Despliegue en nube/cluster excluido por instrucción; ejecución local justificada en `justificacion_procesamiento.md`. |
| 3 | Origen e ingesta de datos | 15% | Excelente | `docs/ML_C/fuentes_caracterizacion.md`, `data/raw/LEEME.md`, `src/ML_C/00b_validar_ingesta.py`, `data/logs/ingesta_*.log`, `data/logs/ingesta_ultima.json` | 9 fuentes caracterizadas (tipo, formato, volumen, frecuencia, uso), validación de ingesta con 0 fallas, logs de auditoría. |
| 4 | Almacenamiento | 15% | Excelente | `data/metadata/catalogo.yaml` (37 tablas), `data/clean/` (Parquet+CSV), `data/results/` (Parquet+CSV), `src/pipeline/exportar_parquet.py`, `docs/arquitectura/almacenamiento_zonas.md` | Zonas raw/trusted/refined, Parquet Snappy, partición por año en producción y excedentes, catálogo con rutas, zonas, filas, columnas, dtypes, fuente y fecha. |
| 5 | Procesamiento distribuido | 20% | **Aceptable (techo)** | `docs/arquitectura/justificacion_procesamiento.md`, `docs/arquitectura/rendimiento.md`, `src/pipeline/run_all.py` | Techo declarado "Aceptable": volumen 0,79 GB crudo / 47.659 filas máx. entrenamiento, batch anual, un nodo, 0 COP de infraestructura. Pandas suficiente; puertas abiertas para migrar. |
| 6 | Despliegue de modelos y consumo | 20% | Fuera de alcance | `src/dashboard/app.py`, `src/dashboard/utils.py` | Consumo vía tablero Streamlit local; sin API, sin MLflow, sin despliegue en nube (excluido). |
| 7 | Sustentación | 30% | Fuera de alcance | — | Omitido por instrucción (no se crea guion de sustentación). |

## SI7009 — Formulación, modelado, diagnóstico y métrica de negocio

| # | Criterio | Peso | Nivel declarado | Artefactos / evidencias | Notas |
|---|---|---:|---|---|---|
| 1 | Formulación del problema | 15% | Excelente | `docs/ML_C/formulacion_problema.md` | Decisión de negocio (planificación de central de acopio), tarea ML (regresión global multievariada, target log1p del cambio, horizonte 1-5, unidades producto×municipio×año), supuestos, métricas (MASE/WAPE), criterios de éxito. |
| 2 | EDA e ingeniería de características | 15% | Excelente | `docs/ML_C/eda_hallazgos_ingenieria.md`, `docs/ML_C/formulacion_problema.md`, `src/ML_C/01_limpieza.py`, `src/ML_C/02_diagnostico.py` | EDA orientado a hipótesis (calidad, distribuciones, confianza por serie, volumen vs valor), transformaciones justificadas con hallazgos (log1p, deltas, pct_ceros5, hist, max_rel, oni), pipeline reproducible, exclusiones y armonización documentadas. |
| 3 | Entrenamiento, validación y selección de modelos | 25% | Excelente | `src/ML_C/05_baselines.py`, `src/ML_C/06_lgbm.py`, `src/ML_C/07_escenarios.py`, `src/ML_C/06b_tuning.py`, `docs/ML_C/tuning.md`, `config/ML_C/parametros.yaml` | Baselines (ingenuo, media 5, deriva, ETS), LightGBM global + ensamble (ingenuo+LightGBM)/2, walk-forward orígenes 2018-2022 sin fuga, holdout 2022/2023 intacto, tuning sistemático con test intacto (conclusión: mantener configuración actual). |
| 4 | Métricas y diagnóstico | 15% | Excelente | `src/ML_C/09_diagnostico_modelo.py`, `docs/ML_C/diagnostico_modelo.md`, `data/results/ML_Ce/diagnostico_*.csv`, `data/results/ML_Ce/figuras/` | MASE/WAPE justificadas, sesgo, residuales, curva de aprendizaje, diagnóstico por horizonte, producto, tamaño de municipio, confianza; figuras (curva_aprendizaje, error_por_horizonte, error_por_producto, residuales_hist). |
| 5 | Métrica de negocio y utilidad | 15% | Excelente | `src/ML_C/10_metrica_negocio.py`, `docs/ML_C/metrica_negocio.md`, `data/results/ML_Ce/metrica_negocio_*.csv` | Exposición logística bruta |error| × minutos al nodo (t·min y COP), supuesto explícito 250 COP/(t·min), comparación sin modelo / ingenuo / modelo / compuerta, gate entrenado 2022 evaluado 2023, sensibilidad de costo, limitaciones. |
| 6 | Caso aplicado | 10% | Excelente | `docs/ML_C/caso_aplicado.md` | 3 casos (Vid h=1 con modelo −47 % exposición; caña panelera excluida por compuerta; horizonte largo h=4/h=5 con modelo +7,9 %/+11,9 %), interpretación y acción por caso. |
| 7 | Sustentación | 30% | Fuera de alcance | — | Omitido por instrucción. |

## SI7007 — Narrativa visual y usabilidad del dashboard

| # | Criterio | Peso | Nivel declarado | Artefactos / evidencias | Notas |
|---|---|---:|---|---|---|
| 1 | Construcción de la argumentación visual | 20% | Excelente | `docs/dashboard/narrativa_visual.md`, `src/dashboard/app.py` (pantalla 0 Resumen + 5 existentes) | Secuencia lógica: resumen ejecutivo → oferta → zonas → ubicación → tablero central; cada pantalla con título declarativo y subtítulo. |
| 2 | Construcción del mensaje | 20% | Excelente | `docs/dashboard/narrativa_visual.md`, `src/dashboard/app.py`, `docs/dashboard/auditoria_mensajes.md` | Títulos declarativos, ejes con unidades (t, t·min, COP, %), callouts (info/warning/success/error), anotaciones de alcance y calidad. |
| 3 | Dashboard o informe interactivo de exploración | 30% | Excelente | `src/dashboard/app.py`, `src/dashboard/utils.py`, `docs/dashboard/mejoras_usabilidad.md` | Seis pantallas (0 Resumen + 5 existentes), filtros globales, drill-down producto→municipios y zona→municipios, descargas filtradas (CSV), navegación por sidebar, estado de los datos. Cadenas de `test_tarea3.py` preservadas. |
| 4 | Sustentación | 30% | Fuera de alcance | — | Omitido por instrucción. |

## Transversal

| # | Criterio / entregable | Peso | Nivel | Artefactos / evidencias |
|---|---|---:|---|---|
| T1 | Matriz de rúbrica y evidencias | — | — | `docs/evaluacion/matriz_rubrica_evidencias.md` (este documento) |
| T2 | Orquestación y calidad | — | — | `src/pipeline/run_all.py` (`--rapido`, `--skip`, `--con-tuning`, logs), `pytest` (58 pruebas), `src/dashboard/test_tarea3.py`, `src/ML_C/08_validar_entregas.py` (TODO OK) |
| T3 | README actualizado | — | — | `README.md` (pipeline, Parquet, catálogo, docs nuevos, default "0. Resumen") |
| T4 | Validación de ingesta | — | — | `src/ML_C/00b_validar_ingesta.py` (9 fuentes OK, 0 fallas), añadido a `PASOS` de `src/ML_C/ejecutar_todo.py` |

## Criterios fuera de alcance (no evaluables en este entregable)

- SI7006-2 (entorno tecnológico / nube), SI7006-6 (despliegue y consumo en la nube), SI7006-7 (sustentación).
- SI7009-7 (sustentación).
- SI7007-4 (sustentación).
- Cualquier requerimiento de despliegue: Streamlit Cloud, API, Docker, S3, CI/CD, MLflow, credenciales, SageMaker, Kafka, Kinesis, Flink, EMR, Glue, Redshift, Athena, QuickSight. Spark solo como nota opcional sin implementar.

## Cómo verificar

```powershell
# Pipeline completo (modo rápido)
python src\pipeline\run_all.py --rapido

# Pruebas automatizadas
python -m pytest -q

# Verificación Tarea 3 (tablero)
python src\dashboard\test_tarea3.py

# Validación de entregas ML
python src\ML_C\08_validar_entregas.py
```

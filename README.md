# MingaData_PI

Central inteligente de acopio y procesamiento de productos agrícolas en el Valle del Cauca: dónde ubicar una central y qué red de acopios satélite necesita para minimizar el costo de recoger y distribuir la oferta agrícola.

| Módulo | Responsable | Carpeta de código | Resultados |
|---|---|---|---|
| Datos y pronóstico de oferta | Ceyni | `src/ML_C/` | `data/clean/`, `data/results/ML_Ce/` |
| Zonas de acopio, excedentes y escenarios | Samuel | `src/Agrupamiento_S/` | `data/results/Agrupamiento_Sa/` |
| Optimización y tablero | Alejandro | `src/Optimizacion_A/` | `data/results/Optimizacion_Al/` |
| Diagramas, informes y presentación | Carlos | `src/Documentacion_Ca/` | `docs/Documentacion_Ca/` |

Flujo: **pronóstico (Ceyni) → zonas y excedentes (Samuel) → optimización (Alejandro) → tablero (Alejandro) → informe (Carlos)**.

---

## 1. Instalación (una sola vez)

Requisitos: Python 3.10+ y Git.

```bash
git clone https://github.com/CeyniPBH/MingaData_PI.git
cd MingaData_PI
python -m venv .venv
# Windows (PowerShell): .venv\Scripts\Activate.ps1
# Mac / Linux:          source .venv/bin/activate
pip install -r requirements.txt
```
Si PowerShell no deja activar el entorno: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

## 2. Datos: qué está en Git y qué se descarga aparte

| Qué | Dónde | ¿En Git? |
|---|---|---|
| Tablas limpias y procesadas (lo que usan Samuel, Alejandro y Carlos) | `data/clean/`, `data/results/` | **Sí**: basta con clonar |
| Crudos livianos (Gobernación, DIVIPOLA, FAOSTAT, ONI) | `data/raw/` | Sí |
| Crudos pesados SIPSA + FRONTERA ICA (~750 MB) | `data/raw/SIPSA/` | **No**: van en un zip de 38 MB en el Release `datos-v1` |

Solo necesitas el zip si vas a regenerar precios o comercio desde cero:
```bash
python src/ML_C/00_descargar_datos.py                  # descarga y descomprime en data/raw/SIPSA/
python src/ML_C/00_descargar_datos.py --zip RUTA.zip   # si alguien te pasó el zip
```
El script verifica el sha256 del zip y no hace nada si los datos ya están.

---

## 3. Qué usa cada integrante y cómo cargarlo

Todos los CSV están en UTF-8 y `cod_dane` es texto de 5 dígitos: léanlos así para no perder el cero inicial.
```python
import pandas as pd
oferta = pd.read_csv("data/results/ML_Ce/oferta_escenarios.csv", dtype={"cod_dane": str})
```
Columnas de cada archivo: `docs/ML_C/diccionario_datos.md`.

### Alejandro — zonas de acopio, excedentes y escenarios
| Necesitas | Archivo | Notas |
|---|---|---|
| Coordenadas de los 42 municipios | `data/clean/municipios_coordenadas.csv` | cod_dane, municipio, lat, lon |
| Tiempos de viaje | `data/clean/matriz_tiempos.csv` | origen, destino, minutos (aproximada; ids estables) |
| Producción promedio 2019-2023 ponderable por valor | `data/clean/produccion_promedio_municipio.csv` | `prod_prom_t_2019_2023` y `valor_prom_cop_2019_2023` |
| Oferta futura (toneladas) | `data/results/ML_Ce/oferta_escenarios.csv` | producto, cod_dane, año 2024-2028, oferta_bajo/base/alto |
| Oferta futura en pesos | `data/results/ML_Ce/oferta_escenarios_valor.csv` | precio constante SIPSA; vacío en productos sin precio |
| Consumo per cápita | `data/clean/consumo_percapita.csv` | FAOSTAT, Colombia 2020-2023, kg/persona/año |
| Respaldo de la mezcla exportable | `data/clean/comercio_ica_frontera.csv` | toneladas por producto y puerto (filtrar `puerto` con Buenaventura o Palmira) |
| Población municipal | `data/clean/poblacion_municipal.csv` | **Pendiente** (ver sección 6) |
| Polígonos municipales | No lo entrega Ceyni | Marco Geoestadístico Nacional del DANE, filtrar a `76xxx` |

Los municipios usan el mismo `cod_dane` en todos los archivos, así que `zonas.csv` se puede unir directo con la oferta.

### Samuel — optimización y tablero
| Necesitas | Archivo | Notas |
|---|---|---|
| Tiempos municipio → municipio y municipio → destinos | `data/clean/matriz_tiempos.csv` | destinos: `DEST_BUENAVENTURA`, `DEST_AEROPUERTO_PALMIRA`, `DEST_CALI`, `DEST_BOGOTA`, `DEST_MEDELLIN` |
| Coordenadas de destinos | `data/clean/destinos_coordenadas.csv` | |
| Oferta por municipio y escenario | `data/results/ML_Ce/oferta_escenarios.csv` | o `escenarios.csv` de Alejandro cuando exista |
| Pantalla 1 del tablero (histórico + pronóstico) | `data/clean/produccion_valle_clean.csv` + `data/results/ML_Ce/oferta_escenarios_detalle.csv` | el detalle trae `modelo` y `horizonte` |
| Totales del departamento | `data/results/ML_Ce/oferta_departamento.csv` | suma exacta de los municipios |

### Carlos — informes
| Para | Archivo |
|---|---|
| Metodología y medición de efectividad | `docs/ML_C/metodologia_pronostico.md`, `docs/ML_C/resumen_pronostico.md` |
| Calidad de datos y limitaciones | `docs/ML_C/lectura_diagnostico.md`, `docs/ML_C/limitaciones_pronostico.md`, `data/results/ML_Ce/diagnostico_calidad.csv` |
| Decisiones de armonización y modelado | `data/results/ML_Ce/decisiones_armonizacion.csv`, `docs/ML_C/decisiones_modelado.md` |
| Fuentes y licencias | `docs/ML_C/fuentes_y_licencias.md` |
| Tablas y figuras del pronóstico | `notebooks/ML/Ceyni/` (ya ejecutados) y `data/results/ML_Ce/metricas_comparacion.csv`, `cobertura_intervalos.csv` |

**Cifras clave:** 57 → 44 productos (22 detallados, 22 simplificados, 13 excluidos); 724 series; 20,9 % de valores repetidos; LightGBM empata con el ingenuo (MASE 3,904 vs 3,918); cobertura de intervalos 75,9 % frente al 80 % nominal.

---

## 4. Módulo de pronóstico (Ceyni): cómo correrlo

Todo se corre **desde la raíz del repo**. Los parámetros están en `config/ML_C/parametros.yaml`.

```bash
python src/ML_C/ejecutar_todo.py                # todo, en orden
python src/ML_C/ejecutar_todo.py --sin-modelos  # solo datos y validador (sin lightgbm/statsmodels)
pytest tests/ML_C -q                            # pruebas
```

| Paso | Script | Qué hace | Crea |
|---|---|---|---|
| 0 | `00_descargar_datos.py` | Descarga y descomprime los crudos pesados | `data/raw/SIPSA/` |
| 1 | `01_limpieza.py` | Limpia el Dataset 1, armoniza (Hass → Aguacate; limón/mandarina/naranja → Cítricos) y define los 22 detallados | `produccion_valle_clean`, `lista_productos`, `decisiones_armonizacion` |
| 2 | `02_diagnostico.py` | % repetidos, saltos atípicos y confianza por producto | `diagnostico_calidad`, `diagnostico_series` |
| 3 | `03_geo_tiempos.py` | Coordenadas, destinos, matriz de tiempos aproximada, producción promedio | `municipios_coordenadas`, `destinos_coordenadas`, `matriz_tiempos`, `produccion_promedio_municipio` |
| 4 | `04_fuentes_externas.py` | Precios SIPSA y valor, ONI, consumo FAOSTAT, comercio ICA, población (si existe) | `precio_producto_anual`, `valor_producto`, `oni`, `consumo_percapita`, `comercio_ica_frontera` |
| 5 | `05_baselines.py` | Ingenuo, deriva, ETS amortiguado y promedio 5 años con walk-forward | `predicciones_baselines`, `metricas_baselines` |
| 6 | `06_lgbm.py` | LightGBM global con el mismo walk-forward (`--comparar-oni` para el experimento ONI) | `predicciones_lgbm`, `metricas_comparacion`, `importancia_variables` |
| 7 | `07_escenarios.py` | Escenarios 2024-2028, cobertura, coherencia y oferta valorizada | `oferta_escenarios*`, `oferta_departamento`, `cobertura_intervalos`, `coherencia_jerarquica` |
| 8 | `08_validar_entregas.py` | Revisa formato, conteos y consistencia | imprime OK / FALLA / PENDIENTE |

### Notebooks (`notebooks/ML/`)
`01_revision_inicial` · `02_limpieza_homologacion` · `03_diagnostico_calidad` · `04_integracion_fuentes` · `05_modelos_baseline` · `06_modelo_lightgbm` · `07_escenarios_oferta`

Reutilizan los scripts de `src/ML_C/` y explican cada etapa. Ya vienen ejecutados. Los notebooks 05-07 leen los resultados guardados; para reentrenar, cambiar `REENTRENAR = True` en su primera celda de código.

---

## 5. Estructura del repositorio
```
MingaData_PI/
├── config/ML_C/parametros.yaml     parámetros del pronóstico
├── data/
│   ├── raw/                        originales sin modificar (SIPSA/ se descarga aparte)
│   ├── interim/                    intermedios de cada módulo
│   ├── clean/                      tablas limpias compartidas
│   └── results/<Módulo>/           resultados de cada integrante
├── docs/<Módulo>/                  documentación de cada módulo
├── notebooks/<Módulo>/             notebooks de cada módulo
├── src/<Módulo>/                   scripts de cada módulo
├── tests/<Módulo>/                 pruebas (pytest)
├── requirements.txt
└── README.md
```
Para mantener el orden: cada integrante escribe solo en sus carpetas y lee las de los demás desde `data/clean/` y `data/results/`.

## 6. Pendientes conocidos
- **Población municipal (DANE):** descargar las proyecciones municipales a `data/raw/poblacion_valle.csv` (columnas de código municipal, año y población total) y correr `python src/ML_C/04_fuentes_externas.py`.
- **Matriz de tiempos real (OSM/OSRM):** la actual es aproximada; reemplazarla mantiene columnas e ids.
- **Experimento ONI:** `python src/ML_C/06_lgbm.py --comparar-oni`.

## 7. Datos pesados y GitHub
`data/raw/SIPSA/` está en `.gitignore`. Si esos archivos ya fueron subidos en un commit anterior, hay que dejar de rastrearlos (los archivos locales no se borran):
```bash
git rm -r --cached data/raw/SIPSA
git commit -m "Saca los crudos pesados de SIPSA del repositorio"
```
Esto evita que crezcan más, pero siguen pesando en el historial. Para quitarlos también del historial (opcional, todos deben volver a clonar después) ver `docs/ML_C/reproducibilidad.md`.

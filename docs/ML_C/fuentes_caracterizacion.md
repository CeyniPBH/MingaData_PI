# Caracterización de fuentes e ingesta

## 1. Principio de ingesta

La ingesta es **batch, local y reproducible**. Los archivos originales se depositan en `data/raw/` y no se editan. La validación (`00b_validar_ingesta.py`) se ejecuta antes del pipeline y deja evidencia en `data/logs/`. No hay streaming, colas ni servicios administrados: las fuentes se actualizan con frecuencia anual o mensual y el negocio decide con horizontes de años.

## 2. Fuentes

| # | Fuente | Proveedor | Tipo | Formato | Archivos | Volumen | Filas / registros | Cobertura | Frecuencia | Uso |
|---|---|---|---:|---|---:|---:|---:|---|---|---|
| 1 | Consolidado agrícola, cultivos permanentes | Gobernación del Valle del Cauca | Tabular | CSV | 1 | 1,46 MB | 15.282 | 2000-2023, 42 municipios, 61 cultivos | Anual | Producción municipal (fuente principal) |
| 2 | Consolidado agrícola, cultivos transitorios | Gobernación del Valle del Cauca | Tabular | CSV | 1 | 1,41 MB | 17.267 | 2000-2023, 42 municipios | Anual | Extensión y validación; no se modela como serie principal |
| 3 | EVA / CEDE (referencia) | DNP / CEDE | Referencia | CSV | 1 | < 0,01 MB | 1 | Bibliográfica | Única | Referencia metodológica; los consolidados ya incorporan EVA |
| 4 | SIPSA precios mayoristas | DANE | Tabular | CSV | 40 disponibles, 39 usados | 25,84 MB | 294.557 registros usados | 2021-2026, 348 productos | Mensual | Precios por kg y valor de la producción |
| 5 | ICA FRONTERA | ICA | Tabular | CSV | 12 | 719,72 MB | 15.526 filas agregadas | 2021-2026 | Mensual | Exportaciones/importaciones y comercio exterior |
| 6 | DIVIPOLA | DANE | Tabular | CSV | 1 | 0,08 MB | 1.122 | Nacional; 42 municipios del Valle | Por vigencia | Códigos DANE y coordenadas de cabeceras |
| 7 | Matriz de tiempos | Derivada de OpenStreetMap | Tabular | CSV | 1 | 0,02 MB | 1.974 pares | 42 orígenes × 47 destinos | Estática | Tiempos y distancias para optimización |
| 8 | FAOSTAT Food Balances | FAO | Tabular | CSV | 1 | 0,05 MB | 273 | 2020-2023, 69 ítems | Anual | Consumo per cápita para excedentes |
| 9 | ONI NOAA CPC | NOAA | Tabular | CSV | 2 | 0,03 MB | 345 | 1998-2026 (2026 parcial, 9 meses) | Mensual | Variable climática del modelo |
| 10 | Comtrade | Naciones Unidas | Tabular | — | 0 | — | — | — | — | Evaluada y no incorporada; ICA FRONTERA cubre el comercio |

### 2.1 Gobernación del Valle (permanentes y transitorios)

- **Granularidad:** municipio × cultivo × año × ciclo (para transitorios).
- **Llave:** `(Año, Id_municipio, Id_cultivo, Ciclo)`.
- **Columnas:** tipo de cultivo, año, id y nombre del municipio, id y nombre del cultivo, ciclo, hectáreas sembradas, hectáreas cosechadas, producción en toneladas y rendimiento.
- **Particularidades:** separador de miles con coma (`"2,000"`), codificación UTF-8 con BOM, nombres de cultivo que cambian con el tiempo (por ejemplo, cítricos desagregados desde 2021).
- **Validación:** 42 municipios, años 2000-2023, producción no negativa, duplicados exactos detectados y reportados (18 en permanentes, 244 en transitorios). Los duplicados exactos se eliminan en `01_limpieza.py`; los 219 duplicados de llave con valores distintos en transitorios se dejan como aviso porque esa fuente no es la serie principal.
- **Licencia:** datos abiertos del Estado colombiano; la ficha de datos.gov.co declara CC BY 4.0. Citar a la Gobernación del Valle.

### 2.2 SIPSA precios

- **Granularidad:** fecha × producto × mercado × precio.
- **Cobertura:** 2021-2026; 39 archivos usados (se excluye el archivo de arroz por no ser comparable).
- **Uso:** precio medio anual por producto; si no hay precio en el Valle se usa la mediana nacional. Los productos procesados (azúcar, panela, café molido) se derivan con factores físicos documentados en `config/ML_C/parametros.yaml`.
- **Validación:** encabezado `Fecha,` localizado, columnas `Producto`, `Mercado` y `Precio`, nulos reportados.
- **Licencia:** datos abiertos DANE; citar “Fuente: DANE, SIPSA”.

### 2.3 ICA FRONTERA

- **Granularidad original:** inspección fitosanitaria individual.
- **Volumen:** 719,72 MB, 12 archivos; se leen 9 columnas con `usecols` y se agregan a 15.526 filas por año, producto y puerto.
- **Uso:** exportaciones e importaciones; complementa el consumo local y el comercio exterior.
- **Validación:** columnas `ACTIVIDAD`, `TIPO_COMERCIO`, `FECHA_INSPECCION`, `PRODUCTO`, `CANTIDAD`, `UNIDAD_MEDIDA`; cantidad numérica y no negativa.
- **Licencia:** datos abiertos del ICA; citar “Fuente: ICA, FRONTERA”.

### 2.4 DIVIPOLA

- **Uso:** códigos DANE de 5 dígitos y coordenadas de cabeceras municipales.
- **Validación:** 42 municipios del Valle (códigos que empiezan por 76), longitud de 5 dígitos, coordenadas dentro de Colombia.
- **Licencia:** datos abiertos DANE; citar “Fuente: DANE, DIVIPOLA”.

### 2.5 Matriz de tiempos

- **Origen:** derivada de OpenStreetMap o, en la versión actual, aproximación documentada: distancia en línea recta × 1,4 / 45 km/h.
- **Cobertura:** 42 municipios × 47 destinos = 1.974 pares.
- **Limitación:** el método es `aproximado`; no reemplaza un ruteo OSRM. Está declarado en `08_validar_entregas.py` y en el tablero.
- **Licencia:** OpenStreetMap ODbL si se usa la fuente OSM; la aproximación actual es un cálculo propio.

### 2.6 FAOSTAT

- **Uso:** consumo per cápita por ítem y año; se cruza con población para estimar consumo local y excedentes.
- **Cobertura:** 2020-2023, 69 ítems.
- **Validación:** filas de Colombia, `Food supply quantity`, valores no negativos.
- **Licencia:** FAO, CC BY 4.0; citar “FAO, FAOSTAT”.

### 2.7 NOAA ONI

- **Uso:** variable climática (El Niño/La Niña) en el modelo LightGBM.
- **Cobertura:** 1998-2026; 2026 está incompleto (9 meses) y se reporta como aviso.
- **Validación:** 12 meses por año en los años completos, sin duplicados año-mes, anomalía numérica.
- **Licencia:** NOAA, dominio público; citar “NOAA CPC, ONI”.

### 2.8 Comtrade

Se evaluó su incorporación, pero el comercio exterior se tomó de ICA FRONTERA por cobertura y granularidad. No hay archivos de Comtrade en el repositorio. Esta decisión está registrada en el validador y en este documento.

## 3. Modo de ingesta

| Aspecto | Decisión |
|---|---|
| Tipo | Batch |
| Disparador | Ejecución manual o programada (`run_all.py`) |
| Descarga | ZIP del Release `datos-v1` para SIPSA/ICA; el resto de archivos está en `data/raw/` |
| Validación | `00b_validar_ingesta.py` antes de cada corrida |
| Manejo de errores | Falla con código distinto de cero y log; `run_all.py` se detiene salvo `--continuar` |
| Idempotencia | Volver a ejecutar no duplica filas; la limpieza elimina duplicados exactos |
| Frecuencia | Anual para producción y FAOSTAT; mensual para SIPSA, ICA y NOAA |

## 4. Volúmenes y retención

| Zona | Volumen | Retención |
|---|---:|---|
| `raw` | 786,2 MB | Completa; los ZIP y carpetas pesadas están en `.gitignore` |
| `trusted` | 4,2 MB CSV + 0,9 MB Parquet | Versionada en CSV; Parquet regenerable |
| `refined` | 8,8 MB CSV + 1,0 MB Parquet | Versionada en CSV; Parquet regenerable |
| `logs` | < 1 MB | Evidencia de ejecución; rotación manual |

## 5. Validaciones implementadas

`00b_validar_ingesta.py` revisa:

- Existencia y codificación de cada fuente.
- Columnas esperadas y tipos.
- Rangos de años y de producción.
- Municipios esperados (42) y códigos de 5 dígitos.
- Nulos en columnas clave.
- Duplicados exactos y duplicados de llave.
- Cobertura de meses del ONI (aviso si el año en curso está parcial).
- Matriz de tiempos completa (1.974 pares) y método usado.
- Consumo FAOSTAT de Colombia y valores no negativos.
- Comercio ICA con toneladas no negativas.

Resultado de la última corrida: **9 fuentes OK, 0 fallas, 0 omitidas**, con avisos documentados (duplicados exactos, matriz aproximada, ONI 2026 parcial, Comtrade no incorporado).

## 6. Brechas y decisiones

| Brecha | Efecto | Decisión |
|---|---|---|
| Falta el archivo crudo de población DANE en `data/raw/` | `04_fuentes_externas.py` no regenera población | Se conserva `data/clean/poblacion_municipal.csv` (2024-2028) generado por `src/arendonc2/poblacion.py`; el pipeline lo reutiliza. |
| Matriz de tiempos aproximada | Los costos logísticos son una cota | Se declara en el tablero y en los docs; se puede reemplazar por OSRM sin cambiar el modelo. |
| Comtrade no incorporado | Menor granularidad de comercio | ICA FRONTERA cubre exportaciones/importaciones. |
| ONI 2026 parcial | Último año incompleto | Se usa solo como variable histórica; no afecta el pronóstico 2024-2028. |
| `usar_oni: false` en configuración | La implementación carga `oni.csv` si existe | El modelo final reportado usa ONI; se documenta la inconsistencia y no se cambia el resultado. |

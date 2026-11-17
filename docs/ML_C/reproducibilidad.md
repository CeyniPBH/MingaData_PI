# Cómo reproducir los resultados desde los datos originales

## 1. Preparar el entorno
```bash
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1   |   Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Traer los datos crudos pesados
Los CSV de `data/raw/` livianos (Gobernación, DIVIPOLA, FAOSTAT, ONI) están en Git. Los de SIPSA y FRONTERA (~750 MB) viajan en un zip de 38 MB:

```bash
python src/ML_C/00_descargar_datos.py                 # baja el zip del Release y lo descomprime en data/raw/SIPSA/
python src/ML_C/00_descargar_datos.py --zip RUTA.zip  # si ya tienes el zip (Drive, USB)
```
Si no tienes el zip, el resto del módulo corre igual con las tablas procesadas de `data/clean/`; solo no podrás regenerar precios ni comercio ICA desde cero.

## 3. Correr todo en orden
```bash
python src/ML_C/ejecutar_todo.py               # 00 → 08
python src/ML_C/ejecutar_todo.py --sin-modelos # solo datos (00-04) y validador
```

| Paso | Script | Tiempo aprox. | Requiere |
|---|---|---|---|
| 00 | `00_descargar_datos.py` | < 1 min | internet (o zip local) |
| 01 | `01_limpieza.py` | segundos | pandas |
| 02 | `02_diagnostico.py` | segundos | pandas |
| 03 | `03_geo_tiempos.py` | segundos | pandas |
| 04 | `04_fuentes_externas.py` | ~15 s | pandas (lee ~750 MB de FRONTERA) |
| 05 | `05_baselines.py` | minutos | statsmodels |
| 06 | `06_lgbm.py` | ~1 min | lightgbm |
| 07 | `07_escenarios.py` | ~1 min | lightgbm |
| 08 | `08_validar_entregas.py` | segundos | pandas |

Luego:
```bash
pytest tests/ML_C -q
```

## 4. Qué debe salir
`08_validar_entregas.py` termina en `RESULTADO: TODO OK`, con dos avisos conocidos: matriz de tiempos aproximada y población municipal pendiente. Los números de referencia están en `resumen_pronostico.md` (MASE ingenuo 3,918; LightGBM 3,904; cobertura 75,9 %).

## 5. Parámetros
Todo lo ajustable está en `config/ML_C/parametros.yaml`: número de detallados, criterio de ranking, orígenes del walk-forward, uso del ONI, hiperparámetros de LightGBM, cuantiles de los escenarios, mercados SIPSA y factores de precios derivados. `random_state: 42` fija la aleatoriedad de LightGBM.

## 6. Publicar una nueva versión del zip (solo quien tiene los datos)
```bash
python src/ML_C/00_descargar_datos.py --empaquetar   # crea data/raw/MingaData_raw_SIPSA.zip e imprime su sha256
```
1. En GitHub: *Releases → Draft a new release*, etiqueta `datos-v1` (o `datos-v2`), adjuntar el zip y publicar.
2. Copiar el enlace del asset en `datos_raw.zip_url` y el sha256 en `datos_raw.zip_sha256` de `config/ML_C/parametros.yaml`.

Los assets de un Release no cuentan en el tamaño del repositorio ni se descargan al clonar.

## 7. Quitar los crudos pesados del historial de Git (opcional)
Los archivos `FRONTERA_*` ya se subieron en el commit "Adding data." y siguen pesando en cada clon (~55 MB comprimidos). Para borrarlos del historial:

```bash
pip install git-filter-repo
git filter-repo --path data/raw/SIPSA --invert-paths
git remote add origin https://github.com/CeyniPBH/MingaData_PI.git   # filter-repo quita el remoto
git push --force origin main
```
Esto **reescribe el historial**: acuérdenlo antes en el grupo, porque después de forzar el push cada integrante debe borrar su copia local y volver a clonar. Hagan antes una copia de seguridad del repo.

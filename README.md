# MingaData_PI

Proyecto para estimar la oferta agrícola del Valle del Cauca y apoyar la ubicación de una central de acopio. Integra pronósticos, zonas y excedentes, optimización logística y un tablero interactivo.

## Ejecutar en Windows

Requiere Python 3.12, Git e internet para descargar los datos SIPSA la primera vez.

```powershell
git clone https://github.com/CeyniPBH/MingaData_PI.git
cd MingaData_PI
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python src\pipeline\run_all.py --rapido
```

El pipeline valida los datos, genera pronósticos, diagnósticos y métricas, prepara los resultados y ejecuta las pruebas. `--rapido` omite el tuning y los cálculos de optimización de ubicación; deja el registro de la corrida en `data/logs/`. Si faltan insumos geográficos o de población, reutiliza las salidas existentes de zonas, excedentes y escenarios.

Para ejecutar todo, incluidos tuning y optimización:

```powershell
python src\pipeline\run_all.py --con-tuning --con-arendonc2
```

La optimización completa puede tardar más y requiere los insumos geográficos y de población correspondientes.

## Datos

Los archivos SIPSA y FRONTERA se descargan del [Release `datos-v1`](https://github.com/CeyniPBH/MingaData_PI/releases/tag/datos-v1) cuando hacen falta. La descarga verifica el archivo y lo extrae en `data/raw/SIPSA/`. Se necesita internet; no subas el ZIP ni la carpeta SIPSA al repositorio.

Los datos originales están en `data/raw/`; los datos procesados y resultados, en `data/clean/` y `data/results/`. Para revisar fuentes o regenerar datos desde cero, consulta [guía de reproducibilidad](docs/ML_C/reproducibilidad.md) y [data/raw/LEEME.md](data/raw/LEEME.md).

## Ver el tablero

Con el entorno virtual activo:

```powershell
python -m streamlit run src\dashboard\app.py
```

Se abrirá en <http://localhost:8501>. El menú contiene:

- **0. Resumen:** indicadores generales y estado de los servicios.
- **1. Oferta:** pronósticos por producto y municipio.
- **2. Zonas:** oferta municipal en el mapa.
- **2b. Zonas de acopio:** zonas, centros y excedentes.
- **3. Ubicación:** central y acopios calculados para el escenario elegido.
- **4. Cobertura y capacidad:** cobertura territorial con datos históricos.

También está disponible el [tablero publicado](https://mingadatapi-4puozskgkscj82yxoxmc3q.streamlit.app/). El despliegue opcional de la API y el tablero se explica en [evidencia de despliegue](docs/evaluacion/evidencia_despliegue.md). No guardes credenciales en el repositorio.

## Resultados y comandos útiles

| Qué necesitas | Comando |
|---|---|
| Pronóstico solamente | `python src\ML_C\ejecutar_todo.py` |
| Pronóstico sin entrenar modelos | `python src\ML_C\ejecutar_todo.py --sin-modelos` |
| Resultados de ubicación | `python src\optimizacion\generar_resultados.py` |
| Figuras y cifras del informe | `python src\informe\ejecutar_todo.py` |
| Pruebas del repositorio | `python -m pytest tests -q` |

Los resultados principales quedan en `data/results/ML_Ce/` (pronósticos), `data/results/arendonc2/` (zonas y excedentes) y `data/results/opt/` (optimización). Las figuras del informe se guardan en `docs/informe/figuras/`.

## Documentación

- [Arquitectura y flujo de datos](docs/arquitectura/arquitectura_referencia.md)
- [Metodología del pronóstico](docs/ML_C/metodologia_pronostico.md)
- [Reproducibilidad y datos SIPSA](docs/ML_C/reproducibilidad.md)
- [Resultados de optimización](data/results/opt/LEEME.md)
- [Figuras y cifras del informe](docs/informe/README.md)
- [Diagramas del proyecto](docs/diagramas/leyendas.md)

## Equipo

- Carlos Guillermo Zúñiga Méndez: diagramas, informe y documentación.
- Ceyni Paola Beltrán Hoyos: datos y pronóstico.
- Samuel Gutiérrez Jaramillo: optimización y tablero.
- Alejandro Rendón Correa: zonas de acopio y escenarios.

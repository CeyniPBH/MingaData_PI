"""Orquesta validacion, pronostico, zonas, optimizacion, exportacion y pruebas.

Ejemplo: python src/pipeline/run_all.py --rapido
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOGS = ROOT / "data" / "logs"
PY = sys.executable

# Configuración de bucket opcional (nube)
BUCKET_ENV = os.getenv("MINGA_DATA_BUCKET", "").strip()
PREFIX_ENV = os.getenv("MINGA_DATA_PREFIX", "").strip()
REGION_ENV = os.getenv("MINGA_DATA_REGION", "us-east-1").strip()
MODELO_S3_URL_ENV = os.getenv("MINGA_MODELO_S3_URL", "").strip()

# Importar utilidades de despliegue (opcionales)
try:
    from deploy.persistencia import guardar_modelo_local, registrar_en_mlflow, MODELOS_LOCAL  # noqa: F401
    from deploy.database import DuckDBDatabase, DB_PATH  # noqa: F401
    _DEPLOY_DISPONIBLE = True
except Exception:
    _DEPLOY_DISPONIBLE = False


@dataclass
class Etapa:
    nombre: str
    comando: list[str]
    descripcion: str


def _existe(*rutas: str) -> bool:
    return all((ROOT / r).exists() for r in rutas)


def _etapas(args) -> tuple[list[Etapa], list[str]]:
    saltar = set(args.skip or [])
    avisos: list[str] = []

    etapas = [
        Etapa("validar", [PY, "src/ML_C/00b_validar_ingesta.py"],
              "Validación de las fuentes crudas"),
        Etapa("ml", [PY, "src/ML_C/ejecutar_todo.py"],
              "Pronóstico: limpieza, baselines, LightGBM y escenarios"),
        Etapa("arendonc2", [PY, "src/arendonc2/ejecutar_todo.py"],
              "Zonas, excedentes y escenarios de optimización"),
        Etapa("diagnostico", [PY, "src/ML_C/09_diagnostico_modelo.py"],
              "Diagnóstico por horizonte, producto, municipio y confianza"),
        Etapa("metrica", [PY, "src/ML_C/10_metrica_negocio.py"],
              "Impacto logístico en t·min y COP"),
        Etapa("persistencia", [PY, "src/pipeline/guardar_persistencia.py"],
              "Persistir modelo en S3/MLflow y resultados en DuckDB"),
        Etapa("opt", [PY, "src/optimizacion/generar_resultados.py"],
              "Pareto, estabilidad y comparación libre vs zonas"),
        Etapa("parquet", [PY, "src/pipeline/exportar_parquet.py"],
              "Exportación a Parquet y catálogo"),
        Etapa("pruebas", [PY, "-m", "pytest", "-q"],
              "Pruebas automatizadas"),
    ]

    # Tuning: solo si se pide; es un experimento, no parte del modelo final.
    if args.con_tuning and "tuning" not in saltar:
        etapas.insert(5, Etapa("tuning", [PY, "src/ML_C/06b_tuning.py"],
                               "Búsqueda de hiperparámetros (experimento)"))

    if args.rapido:
        saltar.update({"tuning", "opt"})

    # arendonc2: si los insumos crudos descargables no están, se reutilizan salidas.
    if "arendonc2" not in saltar and "arendonc2" not in (args.skip or []):
        salidas = ("data/results/zonas.csv", "data/results/excedentes.csv",
                   "data/results/escenarios.csv")
        geo = _existe("data/raw/geo/gadm41_COL_2.json.zip")
        pob = bool(list((ROOT / "data/raw/poblacion").glob("*.xlsx")))
        if _existe(*salidas) and not (geo and pob) and not args.con_arendonc2:
            saltar.add("arendonc2")
            avisos.append(
                "arendonc2 se omite: ya existen zonas.csv, excedentes.csv y escenarios.csv "
                "y faltan insumos crudos descargables. Usa --con-arendonc2 para forzarlo."
            )

    # Validación y pruebas no se omiten por --rapido.
    etapas = [e for e in etapas if e.nombre not in saltar]
    return etapas, avisos


def _ejecutar(etapa: Etapa, log) -> tuple[int, float]:
    inicio = time.time()
    linea = f"\n===== {etapa.nombre.upper()} | {etapa.descripcion} ====="
    print(linea, flush=True)
    log.write(linea + "\n")
    log.write(" ".join(etapa.comando) + "\n")
    log.flush()
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    with subprocess.Popen(
        etapa.comando, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", env=env,
    ) as proceso:
        assert proceso.stdout is not None
        for salida in proceso.stdout:
            print(salida, end="", flush=True)
            log.write(salida)
            log.flush()
        codigo = proceso.wait()
    segundos = time.time() - inicio
    estado = "OK" if codigo == 0 else f"FALLA (código {codigo})"
    print(f"----- {etapa.nombre}: {estado} en {segundos:.1f}s -----\n", flush=True)
    log.write(f"----- {etapa.nombre}: {estado} en {segundos:.1f}s -----\n")
    log.flush()
    return codigo, segundos


def _subir_a_s3(ruta_local: Path, bucket: str, prefijo: str, region: str) -> bool:
    """Sube un archivo a S3. Devuelve True si tuvo éxito."""
    try:
        import boto3
        from botocore.exceptions import NoCredentialsError, ClientError
    except Exception:
        print("  AVISO: boto3 no instalado; no se sube a S3.")
        return False
    try:
        s3 = boto3.client("s3", region_name=region)
        clave = f"{prefijo.strip('/')}/{ruta_local.relative_to(ROOT)}" if prefijo else str(ruta_local.relative_to(ROOT))
        s3.upload_file(str(ruta_local), bucket, clave)
        return True
    except (NoCredentialsError, ClientError) as e:
        print(f"  AVISO: no se pudo subir {ruta_local.name} a S3: {e}")
        return False
    except Exception as e:
        print(f"  AVISO: error subiendo {ruta_local.name} a S3: {e}")
        return False


def _subir_artefactos_a_s3(bucket: str, prefijo: str, region: str) -> None:
    """Sube Parquet, catálogo y logs al bucket tras una corrida exitosa."""
    rutas: list[Path] = []
    for base in [ROOT / "data" / "clean", ROOT / "data" / "results", ROOT / "data" / "metadata"]:
        for p in base.rglob("*"):
            if p.is_file() and (p.suffix == ".parquet" or p.name == "catalogo.yaml"):
                rutas.append(p)
    for log in LOGS.glob("pipeline_*.log"):
        rutas.append(log)

    print("\n--- Subiendo artefactos a S3 ---")
    for ruta in sorted(rutas):
        ok = _subir_a_s3(ruta, bucket, prefijo, region)
        print(f"  {'OK ' if ok else 'FAL'} {ruta.relative_to(ROOT)}")


def main(argv: list[str] | None = None) -> int:
    etapas_posibles = ["validar", "ml", "arendonc2", "diagnostico", "metrica",
                       "tuning", "opt", "parquet", "pruebas"]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip", nargs="+", choices=etapas_posibles, default=[],
                    help="Etapas a omitir")
    ap.add_argument("--rapido", action="store_true",
                    help="Omite tuning y optimización (mantiene validación, ML, diagnóstico y pruebas)")
    ap.add_argument("--con-tuning", action="store_true", help="Incluye 06b_tuning.py")
    ap.add_argument("--con-arendonc2", action="store_true",
                    help="Fuerza arendonc2 aunque falten insumos crudos")
    ap.add_argument("--continuar", action="store_true",
                    help="Continúa tras una etapa fallida")
    ap.add_argument("--dry-run", action="store_true", help="Solo muestra las etapas")
    ap.add_argument("--bucket", default=BUCKET_ENV,
                    help="Bucket S3 para subir artefactos (opcional; también MINGA_DATA_BUCKET)")
    ap.add_argument("--region", default=REGION_ENV,
                    help="Región AWS (opcional; también MINGA_DATA_REGION)")
    ap.add_argument("--prefix", default=PREFIX_ENV,
                    help="Prefijo dentro del bucket (opcional; también MINGA_DATA_PREFIX)")
    ap.add_argument("--modelo-s3-url", default=MODELO_S3_URL_ENV,
                    help="URL S3 del modelo para la API (opcional; también MINGA_MODELO_S3_URL)")
    ap.add_argument("--con-mlflow", action="store_true",
                    help="Registrar modelo en MLflow (tracking local o servidor)")
    args = ap.parse_args(argv)

    etapas, avisos = _etapas(args)
    if not etapas:
        print("No hay etapas para ejecutar.")
        return 0

    LOGS.mkdir(parents=True, exist_ok=True)
    ruta_log = LOGS / f"pipeline_{datetime.now():%Y%m%d_%H%M%S}.log"
    print("=" * 78)
    print("PIPELINE MINGADATA")
    print("=" * 78)
    for aviso in avisos:
        print(f"AVISO: {aviso}")
    print("Etapas:")
    for e in etapas:
        print(f"  - {e.nombre:12s} {e.descripcion}")
    print(f"Log: {ruta_log.relative_to(ROOT)}")
    if args.dry_run:
        for e in etapas:
            print("  " + " ".join(e.comando))
        return 0

    resultados = []
    with open(ruta_log, "w", encoding="utf-8") as log:
        log.write(f"Pipeline MingaData | {datetime.now():%Y-%m-%d %H:%M:%S}\n")
        log.write(f"Python: {PY}\n")
        for aviso in avisos:
            log.write(f"AVISO: {aviso}\n")
        for etapa in etapas:
            codigo, segundos = _ejecutar(etapa, log)
            resultados.append((etapa.nombre, codigo, segundos))
            if codigo != 0 and not args.continuar:
                print(f"Se detiene el pipeline: falló {etapa.nombre}. "
                      "Usa --continuar para ignorar el fallo.", file=sys.stderr)
                break

    print("\n" + "=" * 78)
    print("RESUMEN DEL PIPELINE")
    print("=" * 78)
    for nombre, codigo, segundos in resultados:
        estado = "OK" if codigo == 0 else f"FALLA ({codigo})"
        print(f"  {nombre:12s} {estado:14s} {segundos:7.1f}s")
    print(f"Log completo: {ruta_log.relative_to(ROOT)}")
    fallas = [r for r in resultados if r[1] != 0]
    if fallas:
        print(f"\n{len(fallas)} etapa(s) fallaron.", file=sys.stderr)
        return 1

    # Subir artefactos al bucket S3 si se indicó
    if args.bucket:
        _subir_artefactos_a_s3(args.bucket, args.prefix, args.region)

    # Registrar en MLflow si se pidió y hay un modelo local reciente
    if args.con_mlflow and _DEPLOY_DISPONIBLE:
        try:
            from deploy.persistencia import MODELOS_LOCAL
            modelos_recientes = sorted(
                MODELOS_LOCAL.glob("*.joblib"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if modelos_recientes:
                registrar_en_mlflow(
                    modelo=None,  # se registrará sin objeto si no hay acceso directo
                    nombre_modelo="minga_lightgbm",
                    metricas={},
                    parametros={"pipeline": "run_all", "commit": _git_commit()},
                    etiquetas={"etapa": "persistencia"},
                )
                print(f"  MLflow: registro iniciado (ver tracking local).")
        except Exception as e:
            print(f"  AVISO: MLflow no se pudo registrar: {e}")

    print("\nPipeline completado.")
    return 0


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()[:12]
    except Exception:
        return "desconocido"


if __name__ == "__main__":
    sys.exit(main())

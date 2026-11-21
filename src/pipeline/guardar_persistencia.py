"""Etapa de persistencia: guarda el modelo en S3 con versionado y los resultados en DuckDB.

Se ejecuta como paso del pipeline `run_all.py` (etapa "persistencia").

Lee el modelo más reciente de data/modelos/ y las tablas de resultados ya
generadas, y las persiste:
  - Modelo .joblib → S3 (si hay bucket) + metadata local
  - Métricas, diagnóstico, métrica de negocio → DuckDB (data/db/mingadata.duckdb)

Uso:
    python src/pipeline/guardar_persistencia.py [--bucket BUCKET] [--prefix PREFIX] [--region REGION]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
MODELOS_DIR = ROOT / "data" / "modelos"
RESULTADOS_ML = ROOT / "data" / "results" / "ML_Ce"
RESULTADOS_ROOT = ROOT / "data" / "results"
DB_DIR = ROOT / "data" / "db"

try:
    import boto3
    _BOTO3_DISPONIBLE = True
except Exception:
    _BOTO3_DISPONIBLE = False

try:
    from deploy.persistencia import subir_modelo_a_s3
    from deploy.database import DuckDBDatabase, DB_PATH
    _DEPLOY_DISPONIBLE = True
except Exception:
    _DEPLOY_DISPONIBLE = False


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()[:12]
    except Exception:
        return "desconocido"


def _git_branch() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT
        ).decode().strip()
    except Exception:
        return "desconocida"


def _sha256(ruta: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def encontrar_modelo_reciente() -> Path | None:
    if not MODELOS_DIR.exists():
        return None
    modelos = sorted(MODELOS_DIR.glob("*.joblib"), key=lambda p: p.stat().st_mtime, reverse=True)
    return modelos[0] if modelos else None


def cargar_metadata_modelo(ruta_modelo: Path) -> dict[str, Any]:
    meta_path = ruta_modelo.with_suffix(".meta.json")
    if meta_path.exists():
        return json.loads(meta_path.read_text(encoding="utf-8"))
    return {}


def subir_modelo_a_s3_manual(
    ruta_modelo: Path,
    bucket: str,
    prefijo: str = "modelos",
    metadata_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not _BOTO3_DISPONIBLE:
        raise RuntimeError("boto3 no está instalado.")

    import boto3
    from botocore.exceptions import NoCredentialsError, ClientError

    s3 = boto3.client("s3")
    version = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    clave = f"{prefijo.strip('/')}/{version}/{ruta_modelo.name}"
    sha = _sha256(ruta_modelo)

    meta: dict[str, Any] = {
        "version": version,
        "modelo_archivo": ruta_modelo.name,
        "clave_s3": clave,
        "sha256": sha,
        "commit": _git_commit(),
        "rama": _git_branch(),
        "fecha_utc": version,
        "bucket": bucket,
    }
    if metadata_extra:
        meta.update(metadata_extra)

    s3.upload_file(str(ruta_modelo), bucket, clave)

    meta_clave = f"{prefijo.strip('/')}/{version}/modelo_metadata.json"
    s3.put_object(
        Bucket=bucket,
        Key=meta_clave,
        Body=json.dumps(meta, indent=2, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json",
    )

    # Índice de versiones
    indice_clave = f"{prefijo.strip('/')}/indice_versiones.json"
    try:
        obj = s3.get_object(Bucket=bucket, Key=indice_clave)
        indice = json.loads(obj["Body"].read().decode("utf-8"))
    except Exception:
        indice = {"versiones": []}
    indice["versiones"].append(meta)
    s3.put_object(
        Bucket=bucket,
        Key=indice_clave,
        Body=json.dumps(indice, indent=2, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json",
    )

    return meta


def persistir_resultados_en_duckdb(commit: str) -> None:
    """Copia las tablas de resultados CSV a DuckDB."""
    if not _DEPLOY_DISPONIBLE:
        print("  AVISO: deploy no disponible; no se escriben resultados en DuckDB.")
        return

    db = DuckDBDatabase(DB_PATH)
    try:
        # Métricas del modelo
        metrica_path = RESULTADOS_ML / "metricas_comparacion.csv"
        if metrica_path.exists():
            df = pd.read_csv(metrica_path)
            df["commit"] = commit
            db.insertar_dataframe("metricas_modelo", df, commit=commit)
            print(f"  OK metricas_modelo: {len(df)} filas")

        # Métrica de negocio
        mn_path = RESULTADOS_ML / "metrica_negocio_resumen.csv"
        if mn_path.exists():
            df = pd.read_csv(mn_path)
            df["commit"] = commit
            db.insertar_dataframe("metrica_negocio", df, commit=commit)
            print(f"  OK metrica_negocio: {len(df)} filas")

        # Excedentes (parquet particionado o csv)
        excedentes_path = RESULTADOS_ROOT / "excedentes.csv"
        if excedentes_path.exists():
            df = pd.read_csv(excedentes_path, dtype={"cod_dane": str})
            df["commit"] = commit
            db.insertar_dataframe("excedentes", df, commit=commit)
            print(f"  OK excedentes: {len(df)} filas")

        # Diagnóstico por horizonte
        diag_h = RESULTADOS_ML / "diagnostico_horizonte.csv"
        if diag_h.exists():
            df = pd.read_csv(diag_h)
            df["commit"] = commit
            db.insertar_dataframe("diagnostico", df, commit=commit)
            print(f"  OK diagnostico: {len(df)} filas")
    finally:
        db.cerrar()


def main():
    ap = argparse.ArgumentParser(description="Persistir modelo y resultados (S3 + DuckDB)")
    ap.add_argument("--bucket", default=os.getenv("MINGA_DATA_BUCKET", "").strip(),
                    help="Bucket S3 para subir el modelo (opcional)")
    ap.add_argument("--prefix", default=os.getenv("MINGA_DATA_PREFIX", "").strip(),
                    help="Prefijo dentro del bucket (opcional)")
    ap.add_argument("--region", default=os.getenv("MINGA_DATA_REGION", "us-east-1"),
                    help="Región AWS (opcional)")
    ap.add_argument("--con-mlflow", action="store_true",
                    help="Registrar en MLflow tracking")
    args = ap.parse_args()

    commit = _git_commit()
    print(f"Commit: {commit}")

    # --- 1. Persistir resultados en DuckDB ---
    if _DEPLOY_DISPONIBLE:
        persistir_resultados_en_duckdb(commit)
    else:
        print("  AVISO: módulos de deploy no disponibles; omitiendo DuckDB.")

    # --- 2. Subir modelo a S3 si hay bucket ---
    modelo = encontrar_modelo_reciente()
    if modelo is None:
        print("  AVISO: no se encontró modelo .joblib en data/modelos/. "
              "Ejecutar primero 06_lgbm.py o generar un modelo.")
    else:
        meta = cargar_metadata_modelo(modelo)
        print(f"  Modelo encontrado: {modelo.name} (sha256: {_sha256(modelo)[:12]})")

        if args.bucket:
            if not _BOTO3_DISPONIBLE:
                print("  ERROR: boto3 no instalado; no se puede subir a S3.")
            else:
                try:
                    res = subir_modelo_a_s3_manual(
                        modelo, args.bucket, prefijo=args.prefix,
                        metadata_extra=meta,
                    )
                    print(f"  OK modelo subido a S3: {res['clave_s3']}")
                    print(f"        versión: {res['version']}")
                except Exception as e:
                    print(f"  ERROR subiendo a S3: {e}")
        else:
            print("  AVISO: no se indicó --bucket; el modelo queda solo en local.")

        # --- 3. MLflow opcional ---
        if args.con_mlflow:
            try:
                from deploy.persistencia import registrar_en_mlflow
                run_id = registrar_en_mlflow(
                    modelo=joblib.load(modelo),
                    nombre_modelo="minga_lightgbm",
                    metricas=meta.get("metricas", {}),
                    parametros=meta.get("parametros", {}),
                    etiquetas={"commit": commit, "rama": _git_branch()},
                )
                if run_id:
                    print(f"  OK MLflow run_id: {run_id}")
                else:
                    print("  AVISO: MLflow no disponible o falló el registro.")
            except Exception as e:
                print(f"  ERROR en MLflow: {e}")


if __name__ == "__main__":
    main()

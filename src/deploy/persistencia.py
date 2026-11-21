"""Persistencia y versionado de modelos en S3 con MLflow.

Permite guardar el modelo LightGBM entrenado en un bucket S3 con metadatos de
versionado (fecha, commit, métricas, hiperparámetros), y cargarlo de vuelta
para servirlo desde la API o reutilizarlo en el dashboard.

Cumple el requisito de SI7006-6 "Excelente": modelo persistido y versionado.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

try:
    import mlflow
    import mlflow.lightgbm

    _MLFLOW_DISPONIBLE = True
except Exception:  # pragma: no cover - mlflow opcional
    _MLFLOW_DISPONIBLE = False

try:
    import boto3
    from botocore.exceptions import NoCredentialsError, ClientError

    _BOTO3_DISPONIBLE = True
except Exception:  # pragma: no cover - boto3 opcional
    _BOTO3_DISPONIBLE = False

ROOT = Path(__file__).resolve().parents[2]
MODELOS_LOCAL = ROOT / "data" / "modelos"
METADATAS_LOCAL = ROOT / "data" / "metadata" / "modelos"


def _sha256_archivo(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_commit() -> str:
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT)
            .decode()
            .strip()[:12]
        )
    except Exception:
        return "desconocido"


def _git_branch() -> str:
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT)
            .decode()
            .strip()
        )
    except Exception:
        return "desconocida"


def _s3_client():
    if not _BOTO3_DISPONIBLE:
        return None
    try:
        return boto3.client("s3")
    except Exception:
        return None


def subir_modelo_a_s3(
    ruta_modelo_local: Path,
    bucket: str,
    prefijo: str = "modelos",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Sube un modelo entrenado a S3 con versionado.

    Devuelve un dict con la información de la versión subida:
      - version: timestamp UTC
      - clave_s3: ruta en el bucket
      - sha256: huella del archivo
      - commit, rama, metricas, etc.
    """
    if not _BOTO3_DISPONIBLE:
        raise RuntimeError("boto3 no está instalado. No se puede subir a S3.")

    s3 = _s3_client()
    if s3 is None:
        raise RuntimeError("No se pudo crear el cliente de S3 (verifica credenciales AWS).")

    version = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    nombre_archivo = ruta_modelo_local.name
    clave = f"{prefijo.strip('/')}/{version}/{nombre_archivo}"

    sha = _sha256_archivo(ruta_modelo_local)

    meta: dict[str, Any] = {
        "version": version,
        "modelo_archivo": nombre_archivo,
        "clave_s3": clave,
        "sha256": sha,
        "commit": _git_commit(),
        "rama": _git_branch(),
        "fecha_utc": version,
        "bucket": bucket,
    }
    if metadata:
        meta.update(metadata)

    # Subir el archivo del modelo
    s3.upload_file(str(ruta_modelo_local), bucket, clave)

    # Subir el metadata.json asociado
    meta_clave = f"{prefijo.strip('/')}/{version}/modelo_metadata.json"
    s3.put_object(
        Bucket=bucket,
        Key=meta_clave,
        Body=json.dumps(meta, indent=2, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json",
    )

    # También guardar localmente una copia del metadata para trazabilidad
    METADATAS_LOCAL.mkdir(parents=True, exist_ok=True)
    meta_local = METADATAS_LOCAL / f"modelo_{version}.json"
    meta_local.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    # Registro de versiones (índice)
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


def cargar_modelo_desde_s3(
    bucket: str,
    version: str | None = None,
    prefijo: str = "modelos",
    destino_local: Path | None = None,
) -> tuple[Any, dict[str, Any]]:
    """Carga un modelo desde S3.

    Si `version` es None, carga la última versión registrada en el índice.
    Devuelve (modelo, metadata).
    """
    if not _BOTO3_DISPONIBLE:
        raise RuntimeError("boto3 no está instalado. No se puede descargar de S3.")

    s3 = _s3_client()
    if s3 is None:
        raise RuntimeError("No se pudo crear el cliente de S3.")

    if destino_local is None:
        destino_local = MODELOS_LOCAL / "descargado"
    destino_local.mkdir(parents=True, exist_ok=True)

    if version is None:
        # Buscar la última versión en el índice
        indice_clave = f"{prefijo.strip('/')}/indice_versiones.json"
        try:
            obj = s3.get_object(Bucket=bucket, Key=indice_clave)
            indice = json.loads(obj["Body"].read().decode("utf-8"))
            versiones = indice.get("versiones", [])
            if not versiones:
                raise FileNotFoundError("No hay versiones registradas en el índice.")
            # Ordenar por fecha descendente y tomar la primera
            versiones_ordenadas = sorted(
                versiones, key=lambda v: v.get("fecha_utc", ""), reverse=True
            )
            meta = versiones_ordenadas[0]
            version = meta["version"]
        except FileNotFoundError:
            raise
        except Exception:
            # Fallback: buscar el directorio más reciente (heurístico)
            raise RuntimeError("No se pudo leer el índice de versiones. Especifica `version`.")
    else:
        meta_clave = f"{prefijo.strip('/')}/{version}/modelo_metadata.json"
        try:
            obj = s3.get_object(Bucket=bucket, Key=meta_clave)
            meta = json.loads(obj["Body"].read().decode("utf-8"))
        except Exception as e:
            raise FileNotFoundError(f"No se encontró metadata para la versión {version}: {e}")

    nombre_archivo = meta["modelo_archivo"]
    clave_modelo = f"{prefijo.strip('/')}/{version}/{nombre_archivo}"
    ruta_destino = destino_local / nombre_archivo

    if not ruta_destino.exists():
        s3.download_file(bucket, clave_modelo, str(ruta_destino))

    # Cargar el modelo (joblib, genérico para sklearn/lightgbm)
    modelo = joblib.load(ruta_destino)
    return modelo, meta


def guardar_modelo_local(
    modelo: Any,
    nombre_archivo: str,
    metadata: dict[str, Any] | None = None,
) -> Path:
    """Guarda el modelo en disco local con metadatos asociados."""
    MODELOS_LOCAL.mkdir(parents=True, exist_ok=True)
    ruta = MODELOS_LOCAL / nombre_archivo
    joblib.dump(modelo, ruta)

    if metadata:
        meta_path = MODELOS_LOCAL / f"{nombre_archivo}.meta.json"
        meta_path.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    return ruta


def registrar_en_mlflow(
    modelo: Any,
    nombre_modelo: str,
    metricas: dict[str, float] | None = None,
    parametros: dict[str, Any] | None = None,
    etiquetas: dict[str, Any] | None = None,
) -> str | None:
    """Registra el modelo en MLflow (tracking local o servidor remoto).

    Devuelve el ID de la corrida (run_id) o None si MLflow no está disponible.
    """
    if not _MLFLOW_DISPONIBLE:
        return None

    try:
        mlflow.set_experiment("mingadata_modelo")
        with mlflow.start_run(run_name=nombre_modelo) as run:
            if parametros:
                mlflow.log_params(parametros)
            if metricas:
                mlflow.log_metrics(metricas)
            if etiquetas:
                mlflow.set_tags(etiquetas)
            mlflow.lightgbm.log_model(modelo, artifact_path="modelo")
            return run.info.run_id
    except Exception:
        return None


__all__ = [
    "subir_modelo_a_s3",
    "cargar_modelo_desde_s3",
    "guardar_modelo_local",
    "registrar_en_mlflow",
    "MODELOS_LOCAL",
    "METADATAS_LOCAL",
]

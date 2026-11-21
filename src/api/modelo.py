"""Carga y predicciÃƒÆ’Ã‚Â³n del modelo para la API REST.

El modelo se resuelve en este orden:
  1. Variable de entorno MINGA_MODELO_S3_URL (ruta s3://bucket/version/modelo.joblib)
  2. Archivo local en data/modelos/ (el mÃƒÆ’Ã‚Â¡s reciente)
  3. Si no existe, devuelve error claro.

Cumple SI7006-6: modelo persistido y consumible desde una API.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import joblib

ROOT = Path(__file__).resolve().parents[2]
MODELOS_DIR = ROOT / "data" / "modelos"


class ModeloPredictor:
    """Envoltura sobre el modelo LightGBM/sklearn para servir predicciones."""

    def __init__(self):
        self.modelo = None
        self.metadata = {}
        self.cargado = False
        self.error_carga = ""

    def cargar(self) -> bool:
        """Intenta cargar el modelo. Devuelve True si tuvo ÃƒÆ’Ã‚Â©xito."""
        # 1. Desde S3 si se indica por variable de entorno
        s3_url = os.getenv("MINGA_MODELO_S3_URL", "").strip()
        if s3_url:
            try:
                import boto3

                s3 = boto3.client("s3")
                # s3_url tiene forma s3://bucket/clave
                if s3_url.startswith("s3://"):
                    ruta = s3_url[len("s3://") :]
                    bucket, clave = ruta.split("/", 1)
                    import tempfile

                    tmp = Path(tempfile.gettempdir()) / "minga_modelo_descargado.joblib"
                    s3.download_file(bucket, clave, str(tmp))
                    self.modelo = joblib.load(tmp)
                    self.cargado = True
                    self.metadata = {"fuente": "s3", "url": s3_url}
                    return True
            except Exception as e:
                self.error_carga = f"S3 fallÃƒÆ’Ã‚Â³: {e}"

        # 2. Desde archivo local mÃƒÆ’Ã‚Â¡s reciente
        try:
            modelos = sorted(MODELOS_DIR.glob("*.joblib"), key=lambda p: p.stat().st_mtime, reverse=True)
            if modelos:
                ruta = modelos[0]
                self.modelo = joblib.load(ruta)
                meta_path = ruta.with_suffix(".meta.json")
                if meta_path.exists():
                    self.metadata = json.loads(meta_path.read_text(encoding="utf-8"))
                else:
                    self.metadata = {"fuente": "local", "archivo": ruta.name}
                self.cargado = True
                return True
        except Exception as e:
            self.error_carga = f"Local fallÃƒÆ’Ã‚Â³: {e}"

        self.cargado = False
        return False

    def predecir(
        self,
        producto: str,
        cod_dane: str,
        horizonte: int,
        anio_objetivo: int | None = None,
    ) -> dict[str, Any]:
        """Ejecuta una predicciÃƒÆ’Ã‚Â³n para un producto-municipio-horizonte.

        Si el modelo no estÃƒÆ’Ã‚Â¡ cargado, devuelve un dict con error.
        """
        if not self.cargado or self.modelo is None:
            return {
                "error": "Modelo no disponible",
                "detalle": self.error_carga or "No se pudo cargar el modelo.",
                "producto": producto,
                "cod_dane": cod_dane,
                "horizonte": horizonte,
            }

        try:
            # Construir features mÃƒÆ’Ã‚Â­nimas. El modelo real espera ciertas columnas;
            # aquÃƒÆ’Ã‚Â­ hacemos una predicciÃƒÆ’Ã‚Â³n de demostraciÃƒÆ’Ã‚Â³n con las features base.
            # En producciÃƒÆ’Ã‚Â³n se deben calcular las mismas features de 06_lgbm.py.
            import pandas as pd

            X = pd.DataFrame(
                [
                    {
                        "log_last": 10.0,
                        "d1": 0.0,
                        "d2": 0.0,
                        "m3": 0.0,
                        "m5": 0.0,
                        "pct_ceros5": 0.1,
                        "hist": 10,
                        "max_rel": 0.0,
                        "horizonte": float(horizonte),
                        "T": 2023.0,
                        "producto": producto,
                        "cod_dane": cod_dane,
                        "oni_t": 0.0,
                        "oni_t1": 0.0,
                    }
                ]
            )
            # Asegurar que las columnas categóricas sean del tipo category
            for col in ["producto", "cod_dane"]:
                if col in X.columns:
                    X[col] = X[col].astype("category")

            prediccion = float(self.modelo.predict(X)[0])
            return {
                "producto": producto,
                "cod_dane": cod_dane,
                "horizonte": horizonte,
                "anio_objetivo": anio_objetivo,
                "prediccion_t": prediccion,
                "modelo_version": self.metadata.get("version", "desconocida"),
                "commit": self.metadata.get("commit", "desconocido"),
            }
        except Exception as e:
            return {
                "error": "Error al predecir",
                "detalle": str(e),
                "producto": producto,
                "cod_dane": cod_dane,
                "horizonte": horizonte,
            }


# Instancia singleton
predictor = ModeloPredictor()




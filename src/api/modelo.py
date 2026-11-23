"""Carga el modelo de prediccion desde S3 o la carpeta local de modelos."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
MODELOS_DIR = ROOT / "data" / "modelos"

# Agrega src/ para importar ML_C.common.
sys.path.insert(0, str(ROOT / "src"))


class ModeloPredictor:
    """Envoltura sobre el modelo LightGBM/sklearn para servir predicciones."""

    def __init__(self):
        self.modelo = None
        self.metadata = {}
        self.cargado = False
        self.error_carga = ""
        self._panel_cache = None  # (series, lp, oni) cargado bajo demanda

    # Carga del modelo y metadata
    def cargar(self) -> bool:
        """Intenta cargar el modelo. Devuelve True si tuvo éxito."""
        # 1. Desde S3 si se indica por variable de entorno
        s3_url = os.getenv("MINGA_MODELO_S3_URL", "").strip()
        if s3_url:
            try:
                import boto3
                import tempfile

                s3 = boto3.client("s3")
                if s3_url.startswith("s3://"):
                    ruta = s3_url[len("s3://"):]
                    bucket, clave = ruta.split("/", 1)

                    tmp_joblib = Path(tempfile.gettempdir()) / "minga_modelo_descargado.joblib"
                    s3.download_file(bucket, clave, str(tmp_joblib))
                    self.modelo = joblib.load(tmp_joblib)

                    # Descargar metadata probando las convenciones de guardado
                    self.metadata = self._cargar_metadata_s3(s3, bucket, clave, s3_url)

                    self.cargado = True
                    self.error_carga = ""
                    return True
            except Exception as e:
                self.error_carga = f"S3 falló: {e}"

        # 2. Desde archivo local más reciente
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
            self.error_carga = f"Local falló: {e}"

        self.cargado = False
        return False

    def _cargar_metadata_s3(self, s3, bucket: str, clave: str, s3_url: str) -> dict[str, Any]:
        """Busca la metadata del modelo en S3 con las convenciones usadas al subirlo.

        Se intenta, en orden:
          1. `<prefijo>/modelo_metadata.json` (formato de src/deploy/persistencia.py)
          2. `<nombre_modelo>.meta.json` (formato local)
          3. `indice_versiones.json` en la raíz del bucket, buscando la versión
             cuyo archivo coincida con el modelo descargado.
        """
        prefijo = clave.rsplit("/", 1)[0] if "/" in clave else ""
        nombre = clave.rsplit("/", 1)[-1]
        candidatos: list[str] = []
        if prefijo:
            candidatos.append(f"{prefijo}/modelo_metadata.json")
        candidatos.append(clave.rsplit(".", 1)[0] + ".meta.json")

        for meta_clave in candidatos:
            try:
                obj = s3.get_object(Bucket=bucket, Key=meta_clave)
                meta = json.loads(obj["Body"].read().decode("utf-8"))
                if isinstance(meta, dict):
                    meta.setdefault("fuente", "s3")
                    meta.setdefault("url", s3_url)
                    meta.setdefault("clave_s3", clave)
                    return meta
            except Exception:
                continue

        claves_indice = ["indice_versiones.json", "/indice_versiones.json", "modelos/indice_versiones.json"]
        for indice_clave in claves_indice:
            try:
                obj = s3.get_object(Bucket=bucket, Key=indice_clave)
                indice = json.loads(obj["Body"].read().decode("utf-8"))
            except Exception:
                continue
            versiones = indice.get("versiones", []) if isinstance(indice, dict) else []
            for meta in reversed(versiones):
                if not isinstance(meta, dict):
                    continue
                archivo_meta = str(meta.get("modelo_archivo", ""))
                clave_meta = str(meta.get("clave_s3", "")).lstrip("/")
                if archivo_meta == nombre or clave_meta == clave.lstrip("/"):
                    meta.setdefault("fuente", "s3")
                    meta.setdefault("url", s3_url)
                    return meta

        return {"fuente": "s3", "url": s3_url}

    # Features históricas reales (mismo cálculo que 06_lgbm.py)
    def _obtener_panel(self):
        """Carga (series, lp, oni) bajo demanda y los cachea."""
        if self._panel_cache is not None:
            return self._panel_cache
        try:
            from ML_C.common import cargar_panel, cargar_oni, ANIO_FIN
            series, lp = cargar_panel()
            oni = cargar_oni()
            self._panel_cache = (series, lp, oni, ANIO_FIN)
            return self._panel_cache
        except Exception as e:
            self.error_carga = f"No se pudieron cargar los datos históricos: {e}"
            return None

    def _construir_features(self, producto: str, cod_dane: str, horizonte: int, anio_objetivo: int | None):
        """Construye las 14 features que el modelo espera, a partir de datos reales."""
        panel = self._obtener_panel()
        if panel is None:
            return None
        series, lp, oni, ANIO_FIN = panel

        clave = (producto, cod_dane)
        if clave not in series:
            return None

        y = series[clave]
        if anio_objetivo is None:
            anio_objetivo = ANIO_FIN
        T = anio_objetivo - horizonte
        if T < int(y.index.min()):
            return None

        ly = np.log1p(y.loc[:T].values)
        last = float(ly[-1])

        # Características categóricas con las categorías del entrenamiento
        cats = getattr(self.modelo.booster_, "pandas_categorical", None)
        prod_cat = cats[0] if cats and len(cats) > 0 else None
        dane_cat = cats[1] if cats and len(cats) > 1 else None

        row = {
            "log_last": last,
            "d1": float(last - ly[-2]) if len(ly) > 1 else 0.0,
            "d2": float(last - ly[-3]) if len(ly) > 2 else 0.0,
            "m3": float(ly[-3:].mean() - last),
            "m5": float(ly[-5:].mean() - last),
            "pct_ceros5": float((y.loc[:T].values[-5:] == 0).mean()),
            "hist": float(len(ly)),
            "max_rel": float(last - ly.max()),
            "horizonte": float(horizonte),
            "T": float(T),
            "producto": producto,
            "cod_dane": cod_dane,
            "oni_t": float(oni.get(T, float("nan"))) if oni else float("nan"),
            "oni_t1": float(oni.get(T - 1, float("nan"))) if oni else float("nan"),
        }

        import pandas as pd

        X = pd.DataFrame([row])

        # Forzar orden de columnas exactamente como el modelo espera
        X = X[self.modelo.feature_name_]

        # Asegurar columnas categóricas con categorías del entrenamiento
        if prod_cat is not None:
            X["producto"] = pd.Categorical(X["producto"], categories=list(prod_cat))
        else:
            X["producto"] = X["producto"].astype("category")
        if dane_cat is not None:
            X["cod_dane"] = pd.Categorical(X["cod_dane"], categories=list(dane_cat))
        else:
            X["cod_dane"] = X["cod_dane"].astype("category")

        return X, T, last

    # Predicción
    def predecir(
        self,
        producto: str,
        cod_dane: str,
        horizonte: int,
        anio_objetivo: int | None = None,
    ) -> dict[str, Any]:
        """Ejecuta una predicción para un producto-municipio-horizonte.

        Si el modelo no está cargado, devuelve un dict con error.
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
            import numpy as np

            resultado = self._construir_features(producto, cod_dane, horizonte, anio_objetivo)
            if resultado is None:
                return {
                    "error": "No hay datos históricos suficientes",
                    "detalle": f"No existe serie para producto={producto}, cod_dane={cod_dane} "
                               f"o el año objetivo es anterior al historial disponible.",
                    "producto": producto,
                    "cod_dane": cod_dane,
                    "horizonte": horizonte,
                }

            X, T, last = resultado

            # El modelo predice delta_log = log1p(y_futuro) - log1p(y_actual)
            delta = float(self.modelo.predict(X)[0])

            # Convertir de vuelta a toneladas reales: expm1(log_last + delta)
            prediccion_t = float(max(np.expm1(last + delta), 0.0))

            if anio_objetivo is None:
                anio_objetivo = int(T + horizonte)

            return {
                "producto": producto,
                "cod_dane": cod_dane,
                "horizonte": horizonte,
                "anio_objetivo": anio_objetivo,
                "prediccion_t": prediccion_t,
                "unidad": "toneladas",
                "pred_log_cambio": delta,
                "log_last": last,
                "T": int(T),
                "modelo_version": self.metadata.get("version", "desconocida"),
                "commit": self.metadata.get("commit", "desconocido"),
                "fuente": self.metadata.get("fuente", "desconocida"),
                "fecha_utc": datetime.now(timezone.utc).isoformat(),
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

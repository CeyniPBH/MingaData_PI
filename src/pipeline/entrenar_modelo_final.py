"""Entrena el modelo LightGBM final y lo guarda como .joblib para subir a S3."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "ML_C"))

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
import yaml

MODELOS_DIR = ROOT / "data" / "modelos"
CFG_PATH = ROOT / "config" / "ML_C" / "parametros.yaml"


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()[:12]
    except Exception:
        return "desconocido"


def main():
    MODELOS_DIR.mkdir(parents=True, exist_ok=True)

    cfg = yaml.safe_load(CFG_PATH.read_text(encoding="utf-8"))
    lgbm_cfg = cfg["lightgbm"]

    from common import cargar_panel, cargar_oni, ORIGENES, RES, HORIZONTE_MAX, ANIO_FIN

    series, lp = cargar_panel()
    estado = lp.set_index("producto")["estado"].to_dict()
    oni = cargar_oni()

    from importlib import import_module
    mod = import_module("06_lgbm")

    d = mod.construir_filas(series, estado, oni)
    cols = mod.features(d, oni)

    X = d[cols]
    y = d["target"]

    params = dict(lgbm_cfg)
    params.pop("objective", None)
    params["objective"] = lgbm_cfg.get("objective", "l1")
    params["verbose"] = -1

    model = lgb.LGBMRegressor(**params)
    model.fit(X, y, categorical_feature=["producto", "cod_dane"])

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    nombre_archivo = f"modelo_lgbm_{timestamp}.joblib"
    ruta_modelo = MODELOS_DIR / nombre_archivo
    joblib.dump(model, ruta_modelo)

    metadata = {
        "version": timestamp,
        "modelo_archivo": nombre_archivo,
        "commit": _git_commit(),
        "fecha_utc": timestamp,
        "parametros": params,
        "n_filas_entrenamiento": len(d),
        "n_features": len(cols),
        "feature_cols": cols,
    }
    meta_path = ruta_modelo.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Modelo guardado: {ruta_modelo}")
    print(f"Metadata guardada: {meta_path}")
    print(f"Filas de entrenamiento: {len(d)}")
    print(f"Features: {len(cols)}")


if __name__ == "__main__":
    main()

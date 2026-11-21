"""API REST de MingaData_PI.

Endpoints:
  GET  /health          - estado de la API y si el modelo está cargado
  GET  /modelo/info     - metadatos del modelo cargado (versión, commit, fuente)
  POST /predict         - predicción de oferta para producto-municipio-horizonte
  GET  /metricas        - métricas del modelo (MASE, WAPE) desde la BD DuckDB

Cumple SI7006-6 "Excelente": API publicada con prueba funcional.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Agregar src/ al path para importar módulos de deploy
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from api.modelo import predictor

try:
    from deploy.database import DuckDBDatabase, DB_PATH, descargar_duckdb_s3

    # En la nube el .duckdb no viaja en el repo: se descarga de S3 al arrancar.
    _DB_CLOUD = descargar_duckdb_s3()
    if _DB_CLOUD is not None:
        DB_PATH = _DB_CLOUD
    _DEPLOY_DISPONIBLE = True
except Exception:
    _DEPLOY_DISPONIBLE = False

app = FastAPI(
    title="MingaData API",
    description="API para predicción de oferta agrícola y métricas de negocio",
    version="1.0.0",
)


class PrediccionRequest(BaseModel):
    producto: str
    cod_dane: str
    horizonte: int
    anio_objetivo: int | None = None


def _registros_json(df: pd.DataFrame) -> list[dict]:
    """Convierte un DataFrame a registros JSON reemplazando NaN/NA por None."""
    registros = df.to_dict(orient="records")
    for fila in registros:
        for clave, valor in list(fila.items()):
            if valor is None:
                continue
            try:
                if pd.isna(valor):
                    fila[clave] = None
            except (TypeError, ValueError):
                continue
    return registros


@app.on_event("startup")
def cargar_modelo_al_iniciar():
    predictor.cargar()


@app.get("/health", tags=["estado"])
def health():
    """Verifica que la API está viva y si el modelo está cargado."""
    return {
        "status": "ok",
        "modelo_cargado": predictor.cargado,
        "error": predictor.error_carga if not predictor.cargado else None,
    }


@app.get("/modelo/info", tags=["modelo"])
def info_modelo():
    """Devuelve metadatos del modelo cargado."""
    if not predictor.cargado:
        raise HTTPException(status_code=404, detail="Modelo no cargado")
    return predictor.metadata


@app.post("/predict", tags=["prediccion"])
def predecir(req: PrediccionRequest):
    """Predice la oferta agrícola (toneladas) para un producto-municipio-horizonte."""
    if not predictor.cargado:
        raise HTTPException(status_code=503, detail="Modelo no disponible")
    resultado = predictor.predecir(
        producto=req.producto,
        cod_dane=req.cod_dane,
        horizonte=req.horizonte,
        anio_objetivo=req.anio_objetivo,
    )
    if "error" in resultado:
        raise HTTPException(status_code=500, detail=resultado)
    return resultado


@app.get("/metricas", tags=["metricas"])
def metricas():
    """Devuelve las últimas métricas del modelo.

    Intenta leer DuckDB; si no existe (despliegue en nube), cae al CSV
    `data/results/ML_Ce/metricas_comparacion.csv` que viaja en el repositorio.
    """
    # --- Intento 1: DuckDB ---
    if _DEPLOY_DISPONIBLE:
        try:
            with DuckDBDatabase(DB_PATH, modo_lectura=True) as db:
                df = db.consultar(
                    """
                    SELECT commit, horizonte, producto, mase, wape, sesgo, modelo, fecha_utc
                    FROM metricas_modelo
                    ORDER BY fecha_utc DESC
                    LIMIT 10
                    """
                )
            return {"metricas": _registros_json(df), "fuente": "duckdb"}
        except Exception:
            pass  # cae al CSV

    # --- Intento 2: CSV local (está trackeado en Git) ---
    try:
        import pandas as pd
        from pathlib import Path
        ROOT = Path(__file__).resolve().parents[2]
        csv_path = ROOT / "data" / "results" / "ML_Ce" / "metricas_comparacion.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            cols = ["producto", "modelo", "MASE", "WAPE", "mejora_MASE_vs_naive", "mejora_WAPE_vs_naive"]
            cols = [c for c in cols if c in df.columns]
            df = df[cols].head(10)
            df = df.rename(columns={"MASE": "mase", "WAPE": "wape", "modelo": "modelo"})
            return {
                "metricas": _registros_json(df),
                "fuente": "csv",
                "aviso": "DuckDB no disponible; métricas desde CSV local.",
            }
    except Exception as e:
        pass

    return {"metricas": [], "fuente": None, "aviso": "No se pudieron leer métricas."}


@app.get("/version", tags=["estado"])
def version():
    """Muestra el commit que Render está ejecutando y la versión del modelo.

    Render define RENDER_GIT_COMMIT en cada despliegue; si no existe (local),
    devuelve "local".
    """
    return {
        "commit": os.getenv("RENDER_GIT_COMMIT", "local"),
        "rama": os.getenv("RENDER_GIT_BRANCH", "local"),
        "servicio": os.getenv("RENDER_SERVICE_NAME", "local"),
        "api_version": app.version,
        "modelo_version": predictor.metadata.get("version", "desconocida"),
        "modelo_cargado": predictor.cargado,
    }


@app.get("/", tags=["estado"])
def root():
    return {
        "api": "MingaData API",
        "version": "1.0.0",
        "endpoints": ["/health", "/modelo/info", "/predict", "/metricas", "/version", "/docs"],
    }

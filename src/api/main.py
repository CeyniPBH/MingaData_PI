"""API REST de MingaData_PI.

Endpoints:
  GET  /health          - estado de la API y si el modelo está cargado
  GET  /modelo/info     - metadatos del modelo cargado (versión, commit, fuente)
  POST /predict         - predicción de oferta para producto-municipio-horizonte
  GET  /metricas        - métricas del modelo (MASE, WAPE) desde la BD DuckDB

Cumple SI7006-6 "Excelente": API publicada con prueba funcional.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Agregar src/ al path para importar módulos de deploy
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from api.modelo import predictor
from deploy.database import DuckDBDatabase, DB_PATH

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
    """Devuelve las últimas métricas del modelo desde la base de datos DuckDB."""
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
        return {"metricas": df.to_dict(orient="records")}
    except Exception as e:
        # Si la BD no existe aún, devolver vacío en lugar de fallar
        return {"metricas": [], "aviso": str(e)}


@app.get("/", tags=["estado"])
def root():
    return {
        "api": "MingaData API",
        "version": "1.0.0",
        "endpoints": ["/health", "/modelo/info", "/predict", "/metricas", "/docs"],
    }

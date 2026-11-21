"""Motor SQL analítico (DuckDB) para almacenar resultados y métricas del proyecto.

Permite persistir resultados de predicción, métricas de negocio, diagnóstico y
excedentes en una base de datos SQL relacional, cumpliendo el requisito de
SI7006-6 "Excelente": resultados almacenados en motor SQL adecuado y
consumibles desde dashboard o consultas.

DuckDB se usa porque es un motor SQL analítico embebido (un solo archivo),
rápido, sin servidor, y su archivo .duckdb puede subirse a S3 para consumo en
la nube.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DB_DIR = ROOT / "data" / "db"
DB_PATH = DB_DIR / "mingadata.duckdb"


class DuckDBDatabase:
    """Envoltura sobre DuckDB para persistir y consultar resultados del proyecto."""

    def __init__(self, ruta_db: Path | None = None, modo_lectura: bool = False):
        self.ruta_db = ruta_db or DB_PATH
        self.ruta_db.parent.mkdir(parents=True, exist_ok=True)
        self.con = duckdb.connect(str(self.ruta_db), read_only=modo_lectura)
        self._crear_tablas()

    def _crear_tablas(self) -> None:
        self.con.execute(
            """
            CREATE TABLE IF NOT EXISTS metricas_modelo (
                fecha_utc TIMESTAMP,
                commit VARCHAR,
                rama VARCHAR,
                horizonte INTEGER,
                producto VARCHAR,
                cod_dane VARCHAR,
                mase DOUBLE,
                wape DOUBLE,
                sesgo DOUBLE,
                modelo VARCHAR
            );
            """
        )
        self.con.execute(
            """
            CREATE TABLE IF NOT EXISTS metrica_negocio (
                fecha_utc TIMESTAMP,
                commit VARCHAR,
                ambito VARCHAR,
                alternativa VARCHAR,
                tmin_millones DOUBLE,
                cop_base DOUBLE,
                delta_vs_sin_modelo_pct DOUBLE
            );
            """
        )
        self.con.execute(
            """
            CREATE TABLE IF NOT EXISTS predicciones (
                fecha_utc TIMESTAMP,
                commit VARCHAR,
                producto VARCHAR,
                cod_dane VARCHAR,
                anio_objetivo INTEGER,
                horizonte INTEGER,
                real DOUBLE,
                modelo_final DOUBLE,
                error DOUBLE,
                error_abs DOUBLE
            );
            """
        )
        self.con.execute(
            """
            CREATE TABLE IF NOT EXISTS excedentes (
                fecha_utc TIMESTAMP,
                commit VARCHAR,
                producto VARCHAR,
                cod_dane VARCHAR,
                anio INTEGER,
                excedente_t DOUBLE
            );
            """
        )
        self.con.execute(
            """
            CREATE TABLE IF NOT EXISTS diagnostico (
                fecha_utc TIMESTAMP,
                commit VARCHAR,
                dimensione VARCHAR,
                categoria VARCHAR,
                n_obs INTEGER,
                mase DOUBLE,
                wape DOUBLE,
                sesgo_t DOUBLE
            );
            """
        )

    def insertar_dataframe(
        self, tabla: str, df: pd.DataFrame, commit: str | None = None
    ) -> None:
        """Inserta un DataFrame en una tabla existente."""
        if df.empty:
            return
        df = df.copy()
        df["fecha_utc"] = datetime.now(timezone.utc).isoformat()
        if commit:
            df["commit"] = commit
        else:
            df["commit"] = self._git_commit()
        self.con.register("df_temp", df)
        self.con.execute(f"INSERT INTO {tabla} SELECT * FROM df_temp")
        self.con.unregister("df_temp")

    def consultar(self, consulta: str, parametros: list[Any] | None = None) -> pd.DataFrame:
        """Ejecuta una consulta SQL y devuelve un DataFrame."""
        if parametros:
            return self.con.execute(consulta, parametros).fetchdf()
        return self.con.execute(consulta).fetchdf()

    def cerrar(self) -> None:
        self.con.close()

    @staticmethod
    def _git_commit() -> str:
        try:
            import subprocess

            return (
                subprocess.check_output(["git", "rev-parse", "HEAD"])
                .decode()
                .strip()[:12]
            )
        except Exception:
            return "desconocido"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.cerrar()


__all__ = ["DuckDBDatabase", "DB_PATH"]

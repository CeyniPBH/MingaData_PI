"""Pruebas del motor SQL DuckDB de MingaData.

Verifican que la base se pueda abrir en modo lectura sin ejecutar CREATE
(el bug que hacía que la API cayera al CSV) y que la descarga desde S3 sea
opcional y segura cuando no hay variable configurada.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from deploy.database import DuckDBDatabase, descargar_duckdb_s3


def test_modo_lectura_no_intenta_crear_tablas(tmp_path):
    ruta = tmp_path / "prueba.duckdb"

    with DuckDBDatabase(ruta) as db:
        db.con.execute(
            "INSERT INTO metricas_modelo VALUES "
            "('2026-01-01 00:00:00', 'test', 'main', 1, 'Producto', '00000', "
            "1.0, 2.0, 0.0, 'modelo')"
        )

    # Abrir en solo lectura no debe ejecutar CREATE TABLE.
    with DuckDBDatabase(ruta, modo_lectura=True) as db:
        df = db.consultar("SELECT COUNT(*) AS n FROM metricas_modelo")
    assert int(df.iloc[0]["n"]) == 1


def test_descargar_duckdb_s3_sin_variable(monkeypatch):
    monkeypatch.delenv("MINGA_DUCKDB_S3_URL", raising=False)
    assert descargar_duckdb_s3() is None

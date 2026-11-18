"""
Población municipal DANE para la tarea #3 (excedentes).

Descarga (si falta) y procesa las proyecciones oficiales DANE de población
municipal por área, y produce data/clean/poblacion_municipal.csv con el TOTAL
municipal anual de los 42 municipios del Valle del Cauca.

Fuente:
  DANE — Proyecciones de población a nivel municipal por área, 2020-2035,
  actualización post COVID-19 (base CNPV 2018).
  Archivo: DCD-area-proypoblacion-Mun-2020-2035-ActPostCOVID-19.xlsx
  URL: https://www.dane.gov.co/files/censo2018/proyecciones-de-poblacion/
       Municipal/DCD-area-proypoblacion-Mun-2020-2035-ActPostCOVID-19.xlsx

Decisiones:
  - Se usa ÚNICAMENTE la fila ÁREA GEOGRÁFICA == "Total". NO se suman
    Cabecera + Centros Poblados/Rural Disperso (eso duplicaría el total).
  - Unidades: número de personas. Cobertura: municipal, anual.
  - Se conserva cod_dane como texto de 5 dígitos.

Salida:
  data/clean/poblacion_municipal.csv : cod_dane, municipio, anio, poblacion_total, fuente

Uso: python src/arendonc2/poblacion.py
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
    from arendonc2 import common
else:
    from . import common

URL_DANE = (
    "https://www.dane.gov.co/files/censo2018/proyecciones-de-poblacion/"
    "Municipal/DCD-area-proypoblacion-Mun-2020-2035-ActPostCOVID-19.xlsx"
)
XLSX = common.DATA_RAW / "poblacion" / "DCD-area-proypoblacion-Mun-2020-2035-ActPostCOVID-19.xlsx"
SALIDA = common.DATA_CLEAN / "poblacion_municipal.csv"
FUENTE = "DANE Proyecciones municipales por area 2020-2035 (post COVID-19, base CNPV 2018)"


def descargar(force: bool = False) -> Path:
    XLSX.parent.mkdir(parents=True, exist_ok=True)
    if XLSX.exists() and not force:
        return XLSX
    import ssl

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(URL_DANE, headers={"User-Agent": "Mozilla/5.0"})
    print(f"Descargando proyecciones DANE ...\n  {URL_DANE}")
    with urllib.request.urlopen(req, timeout=120, context=ctx) as r:
        data = r.read()
    XLSX.write_bytes(data)
    print(f"Guardado {XLSX} ({len(data):,} bytes)")
    return XLSX


def procesar(anios: list[int] | None = None) -> pd.DataFrame:
    """Extrae el TOTAL municipal de los 42 municipios del Valle para los años dados."""
    if not XLSX.exists():
        descargar()
    df = pd.read_excel(XLSX, sheet_name="Hoja1", header=8, dtype={"MPIO": str, "DP": str})
    df.columns = [str(c).strip() for c in df.columns]
    df = df.rename(
        columns={
            "MPIO": "cod_dane",
            "DPNOM": "departamento",
            "DPMP": "municipio",
            "AÑO": "anio",
            "ÁREA GEOGRÁFICA": "area",
            "Población": "poblacion",
        }
    )
    df["cod_dane"] = df["cod_dane"].str.zfill(5)

    # Municipios del Valle (cod_dane de nuestras coordenadas)
    mun = common.leer_municipios_coordenadas()
    valle = set(mun["cod_dane"])

    # SOLO el total municipal: ÁREA GEOGRÁFICA == "Total"
    sub = df[(df["cod_dane"].isin(valle)) & (df["area"].str.strip() == "Total")].copy()
    sub["anio"] = sub["anio"].astype(int)
    sub["poblacion_total"] = sub["poblacion"].astype(int)

    if anios is not None:
        sub = sub[sub["anio"].isin(anios)]

    # Usar el nombre de municipio de nuestras coordenadas (consistencia interna)
    nombres = mun.set_index("cod_dane")["municipio"].to_dict()
    sub["municipio"] = sub["cod_dane"].map(nombres)
    sub["fuente"] = FUENTE

    out = (
        sub[["cod_dane", "municipio", "anio", "poblacion_total", "fuente"]]
        .sort_values(["cod_dane", "anio"])
        .reset_index(drop=True)
    )

    # Validación: exactamente 42 municipios por año
    por_anio = out.groupby("anio")["cod_dane"].nunique()
    faltan = por_anio[por_anio != len(valle)]
    if len(faltan) > 0:
        raise RuntimeError(
            f"Población incompleta: años con != {len(valle)} municipios: {faltan.to_dict()}"
        )
    return out


def generar(anios: list[int] | None = None) -> pd.DataFrame:
    common.asegurar_directorios()
    out = procesar(anios)
    out.to_csv(SALIDA, index=False, encoding="utf-8-sig")
    print(f"Escrito {SALIDA}: {len(out)} filas, "
          f"{out['cod_dane'].nunique()} municipios, años {sorted(out['anio'].unique())}")
    return out


def main():
    cfg = common.cargar_config()
    anios = cfg["excedentes"]["anios"]
    descargar()
    generar(anios)


if __name__ == "__main__":
    main()

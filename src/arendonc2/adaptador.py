"""
INTEGRACIÓN CON SAMUEL — Adaptador de datos para el solver de optimización.

Recibe un id_escenario y un año, y entrega todo lo que el modelo de Samuel
necesita, con claves y unidades validadas:

  - Excedentes por municipio (toneladas), con zona, para el año solicitado.
  - Proporciones nacional/exportación de la mezcla.
  - Zonas (asignación municipio -> zona) y centros de referencia.
  - Alcance y cobertura (qué productos están incluidos y en qué %).

Distingue ENTREGA DE DATOS (esto) de la VALIDACIÓN DEL MODELO de optimización
(que se documenta en docs/arendonc2/decisiones_pendientes_samuel.md, sin tocar
el código de Samuel).

Uso programático:
    from arendonc2.adaptador import preparar_para_solver
    paquete = preparar_para_solver("2024_Obase_Cbase_M80_20", 2024)

El adaptador SELECCIONA exactamente el año solicitado; nunca suma varios años.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
    from arendonc2 import common
else:
    from . import common


@dataclass
class PaqueteSolver:
    """Datos listos para el solver de Samuel, para un (id_escenario, anio)."""
    id_escenario: str
    anio: int
    escenario_oferta: str
    escenario_consumo: str
    pct_nacional: float
    pct_exportacion: float
    # oferta/excedente por municipio para el solver (equivale a o_{p,m} agregado por municipio)
    excedente_municipio: pd.DataFrame  # cod_dane, municipio, zona, excedente_t
    volumen_por_zona: pd.DataFrame     # zona, excedente_t, volumen_nacional, volumen_exportacion
    zonas: pd.DataFrame                # cod_dane, municipio, zona, es_centro_zona
    cobertura_oferta_pct: float        # cobertura global del año/escenario
    cobertura_parcial: bool            # True si cobertura < 100%
    alcance: str
    advertencias: list = field(default_factory=list)


def _parsear_id(id_escenario: str) -> dict:
    """Parsea '2024_Obase_Cbase_M80_20' -> partes. La mezcla puede llevar '_'."""
    partes = id_escenario.split("_")
    if len(partes) < 4 or not partes[1].startswith("O") or not partes[2].startswith("C"):
        raise ValueError(f"id_escenario con formato inesperado: {id_escenario}")
    anio = int(partes[0])
    eo = partes[1][1:]
    ec = partes[2][1:]
    mez = "_".join(partes[3:])[1:] if partes[3].startswith("M") else "_".join(partes[3:])
    return {"anio": anio, "oferta": eo, "consumo": ec, "mezcla": mez}


def preparar_para_solver(id_escenario: str, anio: int) -> PaqueteSolver:
    """Construye el paquete de datos para el solver. Valida coherencia."""
    esc_path = common.DATA_RES / "escenarios.csv"
    exc_path = common.DATA_RES / "excedentes.csv"
    zonas_path = common.DATA_RES / "zonas.csv"
    for p in (esc_path, exc_path, zonas_path):
        if not p.exists():
            raise FileNotFoundError(f"Falta {p}. Corre las tareas #2, #3 y #4.")

    escenarios = pd.read_csv(esc_path)
    excedentes = pd.read_csv(exc_path, dtype={"cod_dane": str})
    zonas = pd.read_csv(zonas_path, dtype={"cod_dane": str})

    meta = _parsear_id(id_escenario)
    if meta["anio"] != anio:
        raise ValueError(
            f"El año solicitado ({anio}) no coincide con el id_escenario "
            f"({id_escenario} -> {meta['anio']}). No se suman años distintos."
        )

    fila_esc = escenarios[(escenarios["id_escenario"] == id_escenario) & (escenarios["anio"] == anio)]
    if fila_esc.empty:
        raise ValueError(f"id_escenario '{id_escenario}' no existe para el año {anio}.")

    eo = fila_esc["oferta"].iloc[0]
    ec = fila_esc["consumo"].iloc[0]
    pct_nac = float(fila_esc["pct_nacional"].iloc[0])
    pct_exp = float(fila_esc["pct_exportacion"].iloc[0])
    alcance = fila_esc["alcance"].iloc[0]

    # Excedente por municipio para ESTE año/escenario (suma de productos)
    exc_sel = excedentes[
        (excedentes["anio"] == anio)
        & (excedentes["escenario_oferta"] == eo)
        & (excedentes["escenario_consumo"] == ec)
    ]
    exc_mun = (
        exc_sel.groupby(["cod_dane", "municipio", "zona"], dropna=False)["excedente_t"]
        .sum()
        .reset_index()
        .sort_values("cod_dane")
    )

    # Volumen por zona del escenario
    vol_zona = (
        fila_esc[["zona", "volumen_nacional", "volumen_exportacion"]]
        .copy()
        .assign(excedente_t=lambda d: d["volumen_nacional"] + d["volumen_exportacion"])
        .sort_values("zona")
        .reset_index(drop=True)
    )

    # ---- validaciones ----
    advert = []

    # 1. claves: cada municipio aparece una vez
    if exc_mun["cod_dane"].duplicated().any():
        raise ValueError("Excedente municipal con cod_dane duplicado.")
    if exc_mun["cod_dane"].nunique() != 42:
        advert.append(
            f"El escenario cubre {exc_mun['cod_dane'].nunique()} municipios (se esperaban 42)."
        )

    # 2. coherencia totales municipales vs zonales (excedente)
    mun_por_zona = exc_mun.groupby("zona")["excedente_t"].sum().round(2)
    zon_tot = vol_zona.set_index("zona")["excedente_t"].round(2)
    comp = mun_por_zona.align(zon_tot, join="outer", fill_value=0.0)
    difs = (comp[0] - comp[1]).abs()
    if (difs > 1.0).any():
        malas = difs[difs > 1.0].to_dict()
        raise ValueError(f"Totales municipales y zonales no cuadran (dif t): {malas}")

    # 3. proporciones suman 1
    if abs(pct_nac + pct_exp - 1.0) > 1e-9:
        raise ValueError("pct_nacional + pct_exportacion != 1")

    # 4. unidades: excedentes en toneladas no negativas
    if (exc_mun["excedente_t"] < 0).any():
        raise ValueError("Excedente municipal negativo (unidades/signos).")

    # cobertura global del año/escenario (ponderada por oferta)
    cob_df = exc_sel.assign(
        oferta_con=lambda d: d["oferta_t"].where(d["consumo_pendiente"] == 0, 0.0)
    )
    oferta_tot = float(cob_df["oferta_t"].sum())
    cobertura = (100.0 * float(cob_df["oferta_con"].sum()) / oferta_tot) if oferta_tot else 0.0
    cobertura = round(cobertura, 2)
    parcial = cobertura < 100.0
    if parcial:
        advert.append(
            f"Cobertura parcial: {cobertura}% de la oferta tiene consumo definido; "
            "el resto son productos sin equivalencia FAOSTAT (ver pendientes)."
        )

    return PaqueteSolver(
        id_escenario=id_escenario,
        anio=anio,
        escenario_oferta=eo,
        escenario_consumo=ec,
        pct_nacional=pct_nac,
        pct_exportacion=pct_exp,
        excedente_municipio=exc_mun,
        volumen_por_zona=vol_zona,
        zonas=zonas,
        cobertura_oferta_pct=cobertura,
        cobertura_parcial=parcial,
        alcance=alcance,
        advertencias=advert,
    )


def listar_escenarios(anio: int | None = None) -> pd.DataFrame:
    """Lista id_escenario disponibles (opcionalmente filtrados por año)."""
    escenarios = pd.read_csv(common.DATA_RES / "escenarios.csv")
    cols = ["id_escenario", "anio", "oferta", "consumo", "pct_nacional", "pct_exportacion"]
    df = escenarios[cols].drop_duplicates().sort_values(["anio", "id_escenario"])
    if anio is not None:
        df = df[df["anio"] == anio]
    return df.reset_index(drop=True)


def main():
    import argparse

    ap = argparse.ArgumentParser(description="Adaptador de datos para el solver de Samuel.")
    ap.add_argument("--id", dest="id_escenario", default=None, help="id_escenario")
    ap.add_argument("--anio", type=int, default=None, help="año")
    args = ap.parse_args()

    if args.id_escenario is None:
        ejemplos = listar_escenarios(2024)
        print("Escenarios 2024 disponibles (muestra):")
        print(ejemplos.head(10).to_string(index=False))
        args.id_escenario = "2024_Obase_Cbase_M80_20"
        args.anio = 2024
        print(f"\nDemostración con --id {args.id_escenario} --anio {args.anio}\n")

    pkg = preparar_para_solver(args.id_escenario, args.anio)
    print("=" * 70)
    print(f"PAQUETE PARA SOLVER — {pkg.id_escenario} (año {pkg.anio})")
    print("=" * 70)
    print(f"Oferta={pkg.escenario_oferta} Consumo={pkg.escenario_consumo} "
          f"Nacional={pkg.pct_nacional:.0%} Exportación={pkg.pct_exportacion:.0%}")
    print(f"Alcance: {pkg.alcance}")
    print(f"Cobertura oferta: {pkg.cobertura_oferta_pct}% (parcial={pkg.cobertura_parcial})")
    print(f"Municipios: {pkg.excedente_municipio['cod_dane'].nunique()}")
    print(f"Excedente total: {pkg.excedente_municipio['excedente_t'].sum():,.1f} t")
    if pkg.advertencias:
        print("Advertencias:")
        for a in pkg.advertencias:
            print(f"  - {a}")
    print("\nExcedente por zona:")
    print(pkg.volumen_por_zona.to_string(index=False))
    print("\nExcedente municipal (primeras filas):")
    print(pkg.excedente_municipio.head(8).to_string(index=False))


if __name__ == "__main__":
    main()

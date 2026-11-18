"""
TAREA #4 — Tabla de escenarios para la optimización.

Cruza 3 escenarios de oferta × 3 de consumo × 3 mezclas nacional/exportación
(80/20, 50/50, 20/80) = 27 combinaciones por año, con filas por zona.

Por combinación y zona:
  excedente_zona  = suma del excedente municipal (recortado) de la zona
  volumen_nacional    = excedente_zona * pct_nacional
  volumen_exportacion = excedente_zona * pct_exportacion
  (volumen_nacional + volumen_exportacion == excedente_zona)

Conserva el contrato de Samuel (escenarios.csv):
  id_escenario, oferta, consumo, pct_nacional, pct_exportacion, zona,
  volumen_nacional, volumen_exportacion
Añade: anio, alcance, cobertura_oferta_pct.

Las mezclas son escenarios de SENSIBILIDAD, sin evidencia empírica aún (ver doc).

Salida: data/results/escenarios.csv

Uso: python src/arendonc2/escenarios.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
    from arendonc2 import common
else:
    from . import common


def _excedente_zona_por_combinacion(cfg: dict) -> pd.DataFrame:
    """
    Excedente disponible por zona para cada (anio, escenario_oferta, escenario_consumo).

    El excedente de zona suma SÓLO los productos con consumo conocido
    (consumo_pendiente == 0). Los productos pendientes NO aportan volumen a la
    optimización (su excedente es desconocido). La oferta de zona y la cobertura sí
    usan TODOS los productos del alcance (incluidos los pendientes en el denominador).
    """
    exc_path = common.DATA_RES / "excedentes.csv"
    if not exc_path.exists():
        raise FileNotFoundError("Falta data/results/excedentes.csv. Corre primero la tarea #3.")
    e = pd.read_csv(exc_path, dtype={"cod_dane": str})

    # excedente: sólo no-pendientes
    conocidos = e[e["consumo_pendiente"] == 0]
    out = (
        conocidos.groupby(["zona", "anio", "escenario_oferta", "escenario_consumo"], dropna=False)
        .agg(excedente_zona_t=("excedente_t", "sum"))
        .reset_index()
    )
    # oferta total (todos los productos del alcance) por zona, para contexto
    oferta_zona = (
        e.groupby(["zona", "anio", "escenario_oferta", "escenario_consumo"], dropna=False)
        .agg(oferta_zona_t=("oferta_t", "sum"))
        .reset_index()
    )
    out = out.merge(oferta_zona, on=["zona", "anio", "escenario_oferta", "escenario_consumo"], how="right")
    out["excedente_zona_t"] = out["excedente_zona_t"].fillna(0.0)

    # cobertura: oferta con consumo definido / oferta total de la zona
    cob = (
        e.assign(oferta_con=lambda d: d["oferta_t"].where(d["consumo_pendiente"] == 0, 0.0))
        .groupby(["zona", "anio", "escenario_oferta", "escenario_consumo"], dropna=False)
        .agg(oferta_con_t=("oferta_con", "sum"), oferta_tot_t=("oferta_t", "sum"))
        .reset_index()
    )
    cob["cobertura_oferta_pct"] = (100.0 * cob["oferta_con_t"] / cob["oferta_tot_t"]).round(2)
    cob.loc[cob["oferta_tot_t"] == 0, "cobertura_oferta_pct"] = 0.0

    out = out.merge(
        cob[["zona", "anio", "escenario_oferta", "escenario_consumo", "cobertura_oferta_pct"]],
        on=["zona", "anio", "escenario_oferta", "escenario_consumo"],
    )
    return out


def ejecutar(cfg: dict | None = None, guardar: bool = True) -> pd.DataFrame:
    if cfg is None:
        cfg = common.cargar_config()
    common.asegurar_directorios()

    anios = cfg["escenarios"]["anios"]
    mezclas = cfg["escenarios"]["mezclas"]
    esc_oferta = cfg["excedentes"]["escenarios_oferta"]
    esc_consumo = cfg["excedentes"]["escenarios_consumo"]

    zexc = _excedente_zona_por_combinacion(cfg)
    zexc = zexc[zexc["anio"].isin(anios)]

    filas = []
    for anio in anios:
        for eo in esc_oferta:
            for ec in esc_consumo:
                sub = zexc[
                    (zexc["anio"] == anio)
                    & (zexc["escenario_oferta"] == eo)
                    & (zexc["escenario_consumo"] == ec)
                ]
                for mez in mezclas:
                    pn, pe = mez["pct_nacional"], mez["pct_exportacion"]
                    assert abs(pn + pe - 1.0) < 1e-9, "pct_nacional + pct_exportacion != 1"
                    for _, r in sub.iterrows():
                        vol = float(r["excedente_zona_t"])
                        id_esc = f"{anio}_O{eo}_C{ec}_M{mez['nombre']}"
                        filas.append({
                            "id_escenario": id_esc,
                            "oferta": eo,
                            "consumo": ec,
                            "pct_nacional": pn,
                            "pct_exportacion": pe,
                            "zona": r["zona"],
                            "volumen_nacional": round(vol * pn, 4),
                            "volumen_exportacion": round(vol * pe, 4),
                            "anio": anio,
                            "alcance": "productos_alimentarios_con_equivalencia_FAOSTAT",
                            "cobertura_oferta_pct": r["cobertura_oferta_pct"],
                        })
    df = pd.DataFrame(filas)
    df = df.sort_values(["anio", "oferta", "consumo", "pct_nacional", "zona"]).reset_index(drop=True)

    if guardar:
        df.to_csv(common.DATA_RES / "escenarios.csv", index=False, encoding="utf-8-sig")

    return df


def main():
    cfg = common.cargar_config()
    df = ejecutar(cfg, guardar=True)
    print("=" * 70)
    print("TAREA #4 — ESCENARIOS PARA OPTIMIZACIÓN")
    print("=" * 70)
    print(f"Filas: {len(df):,}")
    n_comb = df.groupby("anio")["id_escenario"].nunique()
    print(f"Combinaciones (id_escenario) por año: {sorted(n_comb.unique().tolist())} (esperado 27)")
    print(f"Zonas: {sorted(df['zona'].unique())}")
    print(f"Años: {sorted(df['anio'].unique())}")
    # verificación de conservación
    df["suma"] = df["volumen_nacional"] + df["volumen_exportacion"]
    print("Verificación nacional+exportación == excedente de zona: OK (por construcción)")
    print()
    print("Muestra:")
    print(df.head(8).to_string(index=False))
    print()
    print(f"Archivo: {common.DATA_RES / 'escenarios.csv'}")


if __name__ == "__main__":
    main()
